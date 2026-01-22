"""
Weed Detector Module - YOLO11 Multi-Class Detection
ตรวจจับทั้ง "หญ้า (weed)" และ "ต้นพริก (chili)" 
เพื่อพ่นยาเฉพาะหญ้า ไม่ทำลายต้นพริก

Author: AgriBot Team
"""

import cv2
import numpy as np
import logging
from pathlib import Path
from typing import List, Tuple, Optional
from dataclasses import dataclass
from enum import Enum

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# ==================== MODELS DIRECTORY ====================
MODELS_DIR = Path(__file__).parent / "models"
DEFAULT_MODEL_NAME = "best.pt"


# ==================== V4L2 CAMERA DETECTION (คล้าย Cheese) ====================
def find_usb_cameras() -> List[str]:
    """
    ค้นหา USB cameras ด้วย V4L2 (คล้ายแอพ Cheese)
    
    อ่าน /sys/class/video4linux/ เพื่อหา USB cameras จริง
    กรอง devices ที่ไม่ใช่กล้อง เช่น decoder, ISP ออก
    
    Returns:
        List[str]: รายการ device paths เช่น ['/dev/video0', '/dev/video1']
    """
    import os
    cameras = []
    
    video4linux_path = '/sys/class/video4linux'
    if not os.path.exists(video4linux_path):
        return []
    
    for device_name in sorted(os.listdir(video4linux_path)):
        device_path = f'/dev/{device_name}'
        sys_path = f'{video4linux_path}/{device_name}'
        
        try:
            # ตรวจสอบว่าเป็น USB device หรือไม่
            device_link = os.path.realpath(f'{sys_path}/device')
            is_usb = 'usb' in device_link.lower()
            
            # อ่านชื่อ device
            name_file = f'{sys_path}/name'
            cam_name = ''
            if os.path.exists(name_file):
                with open(name_file, 'r') as f:
                    cam_name = f.read().strip().lower()
            
            # กรอง devices ที่ไม่ใช่กล้อง
            skip_keywords = ['pispbe', 'decoder', 'encoder', 'isp', 'hevc', 'h264']
            if any(kw in cam_name for kw in skip_keywords):
                continue
            
            # ตรวจสอบว่ารองรับ video capture (index 0)
            # video0, video2, video4... มักเป็น capture device
            # video1, video3, video5... มักเป็น metadata
            index_file = f'{sys_path}/index'
            if os.path.exists(index_file):
                with open(index_file, 'r') as f:
                    index = int(f.read().strip())
                if index != 0:  # ข้าม metadata devices
                    continue
            
            # USB cameras ใส่ก่อน
            if is_usb:
                cameras.insert(0, device_path)
            else:
                cameras.append(device_path)
                
        except Exception:
            continue
    
    logger.info(f"🔍 V4L2 found cameras: {cameras}")
    return cameras


class PlantClass(Enum):
    """ประเภทพืชที่ตรวจจับได้"""
    WEED = "weed"           # หญ้า - ต้องพ่นยา
    CHILI = "chili"         # ต้นพริก - ห้ามพ่น
    UNKNOWN = "unknown"     # ไม่รู้จัก


@dataclass
class Detection:
    """
    ข้อมูลการตรวจจับวัตถุ
    
    ระบบพิกัดใหม่:
    - Origin (0,0) อยู่ที่กลางล่างของภาพ (pixel 320, 480)
    - X-axis: ซ้าย(-) ← 0 → ขวา(+) = ทิศทางรถ
    - Y-axis: 0 → บน(+) เท่านั้น (ไม่มี Y ติดลบ)
    - coord_x = x - 320 (center of image)
    - coord_y = 480 - y (from bottom of image, always positive)
    """
    x: int                  # พิกัด X ของจุดกลาง (pixel)
    y: int                  # พิกัด Y ของจุดกลาง (pixel)
    width: int              # ความกว้าง bounding box
    height: int             # ความสูง bounding box (h)
    confidence: float       # ความมั่นใจ (0-1)
    class_name: str         # ชื่อ class เช่น "weed", "chili"
    class_id: int           # ID ของ class
    is_target: bool         # True = ต้องพ่นยา (เฉพาะหญ้า)
    
    # ระยะทางจากแกนกลาง (legacy - สำหรับ compatibility)
    distance_from_center_x: int = 0  # pixel (x - center_x)
    distance_from_center_y: int = 0  # pixel (y - center_y)
    
    # ==================== NEW COORDINATE SYSTEM ====================
    @property
    def coord_x(self) -> int:
        """
        X ในระบบพิกัดใหม่ (origin ที่กลางล่าง)
        X+ = ขวา = Forward, X- = ซ้าย = Backward
        """
        return self.x - 320  # center of image
    
    @property
    def coord_y(self) -> int:
        """
        Y ในระบบพิกัดใหม่ (origin ที่กลางล่าง)
        Y = 480 - pixel_y (always positive, 0 at bottom)
        """
        return 480 - self.y
    
    @property
    def bottom_y_from_image_bottom(self) -> int:
        """
        ระยะ pixel จากขอบล่างของภาพถึงขอบล่างของวัตถุ
        ใช้สำหรับคำนวณระยะพ่น
        """
        bottom_edge = self.y + (self.height // 2)  # bottom edge of object
        return 480 - bottom_edge
    
    @property
    def h(self) -> int:
        """Alias for height (for compatibility with main.py)"""
        return self.height


class WeedDetector:
    """
    YOLO11 Multi-Class Detector
    
    ตรวจจับหลาย class และเลือก target ได้:
    - สามารถเลือก class ที่ต้องการพ่นได้ผ่าน set_target_classes()
    - รองรับการเปลี่ยน target แบบ runtime
    
    การโหลดโมเดล:
    1. ถ้าระบุ model_path → ใช้ไฟล์นั้น
    2. ถ้าไม่ระบุ → ค้นหาใน models/ folder (best.pt)
    """
    
    def __init__(
        self,
        model_path: str = None,
        camera_id: int = 0,
        frame_width: int = 640,
        frame_height: int = 480,
        confidence_threshold: float = 0.25,
        auto_load_model: bool = True
    ):
        """
        Initialize YOLO11 Detector
        
        Args:
            model_path: พาธไฟล์โมเดล YOLO11 (.pt) - ถ้าไม่ใส่จะหาใน models/
            camera_id: ID ของกล้อง (0 = default camera)
            frame_width: ความกว้างภาพ
            frame_height: ความสูงภาพ
            confidence_threshold: ความมั่นใจขั้นต่ำ
            auto_load_model: โหลดโมเดลจาก models/ อัตโนมัติ
        """
        self.model_path = model_path
        self.camera_id = camera_id
        self.frame_width = frame_width
        self.frame_height = frame_height
        self.confidence_threshold = confidence_threshold
        
        # Image center (สำหรับคำนวณ Z-axis)
        self.center_x = frame_width // 2
        self.center_y = frame_height // 2
        
        self.cap: Optional[cv2.VideoCapture] = None
        self.model = None
        
        # Dynamic target classes - ชื่อ class ที่ต้องการพ่น (เปลี่ยนได้)
        # Default: พ่นเฉพาะ "weed"
        self.target_class_names: set = {"weed"}
        
        # โหลดโมเดล
        if model_path:
            self.load_yolo_model(model_path)
        elif auto_load_model:
            self._auto_load_model()
    
    def set_confidence_threshold(self, threshold: float) -> None:
        """ปรับ confidence threshold (0.0 - 1.0)"""
        self.confidence_threshold = max(0.1, min(1.0, threshold))
        logger.info(f"🎚️ Confidence threshold set to: {self.confidence_threshold}")
    
    def get_confidence_threshold(self) -> float:
        """ดึงค่า confidence threshold ปัจจุบัน"""
        return self.confidence_threshold
    
    def set_target_classes(self, class_names: List[str]) -> None:
        """
        ตั้งค่า classes ที่ต้องการเป็น target (พ่นยา)
        
        Args:
            class_names: รายชื่อ class ที่ต้องการพ่น เช่น ["weed"] หรือ ["weed", "chili"]
        """
        self.target_class_names = set(name.lower() for name in class_names)
        logger.info(f"🎯 Target classes updated: {self.target_class_names}")
    
    def add_target_class(self, class_name: str) -> None:
        """เพิ่ม class เป็น target"""
        self.target_class_names.add(class_name.lower())
        logger.info(f"➕ Added target class: {class_name}")
    
    def remove_target_class(self, class_name: str) -> None:
        """ลบ class ออกจาก target"""
        self.target_class_names.discard(class_name.lower())
        logger.info(f"➖ Removed target class: {class_name}")
    
    def get_target_classes(self) -> List[str]:
        """ดึงรายชื่อ target classes"""
        return list(self.target_class_names)
    
    def is_class_target(self, class_name: str) -> bool:
        """ตรวจสอบว่า class นี้เป็น target หรือไม่"""
        return class_name.lower() in self.target_class_names
    
    def load_yolo_model(self, model_path: str) -> bool:
        """
        โหลด YOLO11 Model
        
        Args:
            model_path: พาธไฟล์โมเดล (.pt)
            
        Returns:
            bool: True ถ้าโหลดสำเร็จ
        """
        try:
            from ultralytics import YOLO
            self.model = YOLO(model_path)
            self.model_path = model_path
            
            # ดึง class names จากโมเดล
            if hasattr(self.model, 'names'):
                logger.info(f"✅ YOLO11 loaded: {model_path}")
                logger.info(f"   Classes: {self.model.names}")
            return True
            
        except ImportError:
            logger.error("❌ ultralytics not installed")
            logger.error("   Run: pip install ultralytics")
            return False
        except Exception as e:
            logger.error(f"❌ Failed to load model: {e}")
            return False
    
    def _auto_load_model(self) -> bool:
        """
        ค้นหาและโหลดโมเดลจาก models/ folder อัตโนมัติ
        
        ลำดับการค้นหา:
        1. best.pt (default)
        2. ไฟล์ .pt ตัวแรกที่เจอ
        """
        if not MODELS_DIR.exists():
            logger.info(f"📁 Creating models directory: {MODELS_DIR}")
            MODELS_DIR.mkdir(exist_ok=True)
            return False
        
        # ลองหา best.pt ก่อน
        default_model = MODELS_DIR / DEFAULT_MODEL_NAME
        if default_model.exists():
            logger.info(f"🔍 Found default model: {default_model}")
            return self.load_yolo_model(str(default_model))
        
        # หาไฟล์ .pt ตัวแรก
        pt_files = list(MODELS_DIR.glob("*.pt"))
        if pt_files:
            model_file = pt_files[0]
            logger.info(f"🔍 Found model: {model_file}")
            return self.load_yolo_model(str(model_file))
        
        logger.warning(f"⚠️ No models found in {MODELS_DIR}")
        logger.warning("   Place your YOLO11 model (.pt) in the models/ folder")
        logger.warning("   Or use: detector.load_yolo_model('path/to/model.pt')")
        return False
    
    @staticmethod
    def list_available_models() -> List[str]:
        """
        แสดงรายการโมเดลที่มีใน models/ folder
        """
        if not MODELS_DIR.exists():
            return []
        
        models = list(MODELS_DIR.glob("*.pt"))
        return [str(m.name) for m in models]
    
    def get_model_info(self) -> dict:
        """
        ดึงข้อมูลโมเดลที่โหลดอยู่
        """
        info = {
            "loaded": self.model is not None,
            "model_path": self.model_path,
            "model_name": Path(self.model_path).name if self.model_path else None,
            "class_names": {},
            "num_classes": 0,
            "using_gpu": False
        }
        
        if self.model and hasattr(self.model, 'names'):
            info["class_names"] = self.model.names
            info["num_classes"] = len(self.model.names)
            
            # Check if using GPU
            try:
                if hasattr(self.model, 'device'):
                    info["using_gpu"] = 'cuda' in str(self.model.device)
            except:
                pass
        
        return info
    
    def start_camera(self) -> bool:
        """เปิดกล้อง - ใช้ V4L2 หา USB cameras (คล้าย Cheese)"""
        # หา USB cameras ก่อน (วิธีเดียวกับแอพ Cheese)
        usb_cameras = find_usb_cameras()
        
        # รายการ device ที่จะลอง: USB cameras ก่อน แล้ว fallback
        devices_to_try = usb_cameras + [
            self.camera_id,           # ค่าที่กำหนด
            0, 1, 2                   # Fallback indices
        ]
        
        # ลบ duplicates และ None
        seen = set()
        unique_devices = []
        for d in devices_to_try:
            if d is not None and d not in seen:
                seen.add(d)
                unique_devices.append(d)
        
        for device in unique_devices:
            try:
                logger.info(f"📷 Trying camera: {device}")
                
                # Release previous
                if self.cap is not None:
                    self.cap.release()
                
                self.cap = cv2.VideoCapture(device)
                
                if not self.cap.isOpened():
                    logger.warning(f"   ❌ Failed to open {device}")
                    continue
                
                # Test read
                self.cap.set(cv2.CAP_PROP_FRAME_WIDTH, self.frame_width)
                self.cap.set(cv2.CAP_PROP_FRAME_HEIGHT, self.frame_height)
                self.cap.set(cv2.CAP_PROP_FPS, 30)
                
                ret, test_frame = self.cap.read()
                if not ret or test_frame is None:
                    logger.warning(f"   ❌ Cannot read from {device}")
                    self.cap.release()
                    continue
                
                # Success!
                actual_width = int(self.cap.get(cv2.CAP_PROP_FRAME_WIDTH))
                actual_height = int(self.cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
                self.center_x = actual_width // 2
                self.center_y = actual_height // 2
                self.camera_id = device  # อัพเดทค่าที่ใช้ได้
                
                logger.info(f"✅ Camera opened: {device} ({actual_width}x{actual_height})")
                logger.info(f"   Center: ({self.center_x}, {self.center_y})")
                return True
                
            except Exception as e:
                logger.warning(f"   ❌ Error with {device}: {e}")
                continue
        
        logger.error("❌ Failed to open any camera device")
        return False
    
    def stop_camera(self):
        """ปิดกล้อง"""
        if self.cap:
            self.cap.release()
            logger.info("📷 Camera stopped")
    
    def capture_frame(self) -> Optional[np.ndarray]:
        """จับภาพ 1 เฟรม"""
        if self.cap and self.cap.isOpened():
            ret, frame = self.cap.read()
            if ret:
                return frame
        return None
    
    def detect(self, frame: np.ndarray) -> List[Detection]:
        """
        ตรวจจับวัตถุด้วย YOLO11
        
        Args:
            frame: ภาพ BGR จากกล้อง
            
        Returns:
            List[Detection]: รายการวัตถุที่ตรวจพบ
        """
        if self.model is None:
            logger.warning("⚠️ YOLO model not loaded, using color detection")
            return self._detect_by_color(frame)
        
        return self._detect_by_yolo(frame)
    
    def _detect_by_yolo(self, frame: np.ndarray) -> List[Detection]:
        """ตรวจจับด้วย YOLO11"""
        detections = []
        
        try:
            # Run inference
            results = self.model(frame, verbose=False)
            
            for result in results:
                boxes = result.boxes
                
                for box in boxes:
                    # Get confidence
                    confidence = float(box.conf[0])
                    if confidence < self.confidence_threshold:
                        continue
                    
                    # Get class info
                    class_id = int(box.cls[0])
                    class_name = self.model.names.get(class_id, "unknown")
                    
                    # ตรวจสอบว่าเป็น target หรือไม่ (ใช้ dynamic target classes)
                    is_target = self.is_class_target(class_name)
                    
                    # Get coordinates
                    x1, y1, x2, y2 = box.xyxy[0].cpu().numpy()
                    center_x = int((x1 + x2) / 2)
                    center_y = int((y1 + y2) / 2)
                    width = int(x2 - x1)
                    height = int(y2 - y1)
                    
                    # คำนวณระยะจากแกนกลาง (สำหรับ Z-axis)
                    dist_x = center_x - self.center_x
                    dist_y = center_y - self.center_y
                    
                    detections.append(Detection(
                        x=center_x,
                        y=center_y,
                        width=width,
                        height=height,
                        confidence=confidence,
                        class_name=class_name,
                        class_id=class_id,
                        is_target=is_target,
                        distance_from_center_x=dist_x,
                        distance_from_center_y=dist_y
                    ))
                    
        except Exception as e:
            logger.error(f"❌ YOLO detection error: {e}")
        
        # เรียงตามความมั่นใจ
        detections.sort(key=lambda d: d.confidence, reverse=True)
        return detections
    
    def _detect_by_color(self, frame: np.ndarray) -> List[Detection]:
        """Fallback: ตรวจจับด้วยสี (ถ้าไม่มี YOLO)"""
        detections = []
        
        # แปลงเป็น HSV
        hsv = cv2.cvtColor(frame, cv2.COLOR_BGR2HSV)
        
        # สีเขียววัชพืช
        hsv_lower = np.array([35, 50, 50])
        hsv_upper = np.array([85, 255, 255])
        mask = cv2.inRange(hsv, hsv_lower, hsv_upper)
        
        # กรอง Noise
        kernel = np.ones((5, 5), np.uint8)
        mask = cv2.morphologyEx(mask, cv2.MORPH_OPEN, kernel)
        mask = cv2.morphologyEx(mask, cv2.MORPH_CLOSE, kernel)
        
        # หา Contours
        contours, _ = cv2.findContours(mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
        
        for contour in contours:
            area = cv2.contourArea(contour)
            if area < 500:
                continue
            
            x, y, w, h = cv2.boundingRect(contour)
            center_x = x + w // 2
            center_y = y + h // 2
            
            dist_x = center_x - self.center_x
            dist_y = center_y - self.center_y
            
            detections.append(Detection(
                x=center_x,
                y=center_y,
                width=w,
                height=h,
                confidence=min(area / 10000, 1.0),
                class_name="weed",
                class_id=0,
                is_target=True,
                distance_from_center_x=dist_x,
                distance_from_center_y=dist_y
            ))
        
        detections.sort(key=lambda d: d.confidence, reverse=True)
        return detections
    
    def get_targets_only(self, detections: List[Detection]) -> List[Detection]:
        """
        กรองเฉพาะ targets (หญ้า) ที่ต้องพ่นยา
        ไม่รวมต้นพริกและพืชอื่น
        """
        return [d for d in detections if d.is_target]
    
    def get_nearest_target(self, detections: List[Detection]) -> Optional[Detection]:
        """
        หา target ที่ใกล้แกนกลางที่สุด (สำหรับการ align)
        
        Returns:
            Detection ที่ใกล้ที่สุด หรือ None
        """
        targets = self.get_targets_only(detections)
        if not targets:
            return None
        
        # เรียงตามระยะห่างจากแกนกลาง
        targets.sort(key=lambda d: abs(d.distance_from_center_x))
        return targets[0]
    
    def is_target_aligned(self, detection: Detection, tolerance: int = 30) -> bool:
        """
        ตรวจสอบว่า target อยู่ตรงกลาง (aligned) หรือไม่
        
        Args:
            detection: วัตถุที่ตรวจจับ
            tolerance: ค่าคลาดเคลื่อนที่ยอมรับ (pixel)
            
        Returns:
            bool: True ถ้าอยู่ตรงกลาง
        """
        return abs(detection.distance_from_center_x) <= tolerance
    
    def draw_detections(
        self, 
        frame: np.ndarray, 
        detections: List[Detection],
        show_center: bool = True
    ) -> np.ndarray:
        """วาด Bounding Box บนภาพ"""
        output = frame.copy()
        
        # วาดเส้นแกนกลาง
        if show_center:
            cv2.line(output, (self.center_x, 0), (self.center_x, frame.shape[0]), 
                     (255, 255, 0), 1)
            cv2.line(output, (0, self.center_y), (frame.shape[1], self.center_y), 
                     (255, 255, 0), 1)
        
        for det in detections:
            # สีตาม class
            if det.is_target:
                color = (0, 0, 255)    # แดง = หญ้า (ต้องพ่น)
            else:
                color = (0, 255, 0)    # เขียว = ต้นพริก (ห้ามพ่น)
            
            # Bounding box
            x1 = det.x - det.width // 2
            y1 = det.y - det.height // 2
            x2 = det.x + det.width // 2
            y2 = det.y + det.height // 2
            cv2.rectangle(output, (x1, y1), (x2, y2), color, 2)
            
            # Label
            label = f"{det.class_name}: {det.confidence:.2f}"
            target_label = " [TARGET]" if det.is_target else " [SAFE]"
            cv2.putText(output, label + target_label, (x1, y1 - 10),
                        cv2.FONT_HERSHEY_SIMPLEX, 0.5, color, 2)
            
            # Center point
            cv2.circle(output, (det.x, det.y), 5, color, -1)
            
            # Distance info
            dist_text = f"Z: {det.distance_from_center_x}px"
            cv2.putText(output, dist_text, (det.x + 10, det.y),
                        cv2.FONT_HERSHEY_SIMPLEX, 0.4, (255, 255, 255), 1)
        
        return output


# ==================== MAIN EXECUTION ====================
if __name__ == "__main__":
    import argparse
    
    parser = argparse.ArgumentParser()
    parser.add_argument('--model', type=str, default=None, 
                        help='Path to YOLO11 model (.pt)')
    parser.add_argument('--camera', type=int, default=0)
    args = parser.parse_args()
    
    detector = WeedDetector(
        model_path=args.model,
        camera_id=args.camera
    )
    
    if detector.start_camera():
        print("Press 'q' to quit")
        print("Red = WEED (target), Green = CHILI (safe)")
        
        while True:
            frame = detector.capture_frame()
            if frame is None:
                continue
            
            # ตรวจจับ
            all_detections = detector.detect(frame)
            targets = detector.get_targets_only(all_detections)
            
            # วาด
            output = detector.draw_detections(frame, all_detections)
            
            # แสดงสถิติ
            info = f"All: {len(all_detections)} | Targets: {len(targets)}"
            cv2.putText(output, info, (10, 30),
                        cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 255, 255), 2)
            
            # แสดง nearest target
            nearest = detector.get_nearest_target(all_detections)
            if nearest:
                aligned = detector.is_target_aligned(nearest)
                status = "ALIGNED ✓" if aligned else f"Move: {nearest.distance_from_center_x}px"
                cv2.putText(output, status, (10, 60),
                            cv2.FONT_HERSHEY_SIMPLEX, 0.7, 
                            (0, 255, 0) if aligned else (0, 255, 255), 2)
            
            cv2.imshow("YOLO11 Weed/Chili Detection", output)
            
            if cv2.waitKey(1) & 0xFF == ord('q'):
                break
        
        detector.stop_camera()
        cv2.destroyAllWindows()
