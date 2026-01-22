"""
AgriBot Advanced Calibration Tool
เครื่องมือ Calibrate ค่าต่างๆ รองรับกล้องเฉียง + วัดหลายจุด

Features:
- วัดหลายจุด (ใกล้/กลาง/ไกล) แล้วหาค่าเฉลี่ย
- บันทึกองศากล้อง
- Auto-save ไปที่ calibration.json
- robot_brain.py โหลดค่าอัตโนมัติ
- Live camera preview for Raspberry Pi 5

Author: AgriBot Team
Version: 2.1 (Raspberry Pi 5 Compatible)
"""

import json
from pathlib import Path
from dataclasses import dataclass, asdict, field
from datetime import datetime
from typing import List, Optional, Tuple
import math

try:
    import cv2
    CV2_AVAILABLE = True
except ImportError:
    CV2_AVAILABLE = False
    print("⚠️ OpenCV not available. Camera features disabled.")


# ==================== CONFIG ====================
CONFIG_FILE = Path(__file__).parent / "calibration.json"


@dataclass
class MeasurementPoint:
    """จุดที่วัด"""
    position: str          # "near", "center", "far"
    pixel_distance: float  # ระยะใน pixel
    real_distance_cm: float  # ระยะจริง cm
    pixel_to_cm: float = 0.0  # คำนวณแล้ว
    
    def calculate(self):
        if self.pixel_distance > 0:
            self.pixel_to_cm = self.real_distance_cm / self.pixel_distance
        return self.pixel_to_cm


@dataclass 
class CalibrationData:
    """ค่า Calibration ทั้งหมด"""
    
    # === Image dimensions ===
    img_width: int = 640
    img_height: int = 480
    
    # === Camera Setup ===
    camera_angle_deg: float = 45.0      # องศากล้อง (0=บน, 90=หน้าตรง)
    camera_height_cm: float = 50.0      # ความสูงกล้องจากพื้น
    
    # === Z-Axis Calibration (แขนยืด) ===
    pixel_to_cm_z: float = 0.05         # 1 pixel = กี่ cm
    pixel_to_cm_z_near: float = 0.0     # ค่าที่วัดได้ (ใกล้)
    pixel_to_cm_z_center: float = 0.0   # ค่าที่วัดได้ (กลาง)
    pixel_to_cm_z_far: float = 0.0      # ค่าที่วัดได้ (ไกล)
    arm_speed_cm_per_sec: float = 10.0  # ความเร็วแขน (cm/s)
    arm_base_offset_cm: float = 5.0     # ระยะจากแกนกลางถึงจุดเริ่มยืด
    max_arm_extend_cm: float = 50.0     # ระยะยืดสูงสุด (cm)
    
    # === X-Axis Calibration (ล้อ) ===
    pixel_to_cm_x: float = 0.1          # 1 pixel = กี่ cm (แกน X)
    wheel_speed_cm_per_sec: float = 20.0
    
    # === Alignment ===
    alignment_tolerance_px: int = 30    # ค่าคลาดเคลื่อน align (pixel)
    
    # === Spray ===
    default_spray_duration: float = 1.0 # เวลาพ่นยา (วินาที)
    
    # === Encoder (ESP32) ===
    encoder_ppr: int = 20               # Pulses per revolution
    wheel_diameter_mm: float = 30.0     # เส้นผ่านศูนย์กลางเพลา
    
    # === Metadata ===
    calibrated_at: str = ""
    calibrated_by: str = ""
    notes: str = ""
    
    def to_dict(self):
        return asdict(self)
    
    def save(self, filepath: Path = CONFIG_FILE):
        self.calibrated_at = datetime.now().isoformat()
        with open(filepath, 'w', encoding='utf-8') as f:
            json.dump(self.to_dict(), f, indent=2, ensure_ascii=False)
        print(f"\n✅ บันทึกไปที่: {filepath}")
    
    @classmethod
    def load(cls, filepath: Path = CONFIG_FILE):
        if filepath.exists():
            with open(filepath, 'r', encoding='utf-8') as f:
                data = json.load(f)
            return cls(**{k: v for k, v in data.items() if k in cls.__dataclass_fields__})
        return cls()


# ==================== CAMERA FUNCTIONS (Raspberry Pi 5) ====================

class CameraCalibrator:
    """Camera helper for calibration with live preview"""
    
    def __init__(self, camera_id: int = 0, width: int = 640, height: int = 480):
        self.camera_id = camera_id
        self.width = width
        self.height = height
        self.cap = None
        self.click_points: List[Tuple[int, int]] = []
        self.measuring = False
        self.guided_mode = False  # If true, don't auto-clear points
        
    def _mouse_callback(self, event, x, y, flags, param):
        """Mouse callback for measuring pixels"""
        if event == cv2.EVENT_LBUTTONDOWN:
            # In guided mode, only allow 2 points max (don't clear automatically)
            if self.guided_mode:
                if len(self.click_points) >= 2:
                    # Already have 2 points, clear and start new measurement
                    self.click_points = []
                self.click_points.append((x, y))
                print(f"📍 Point {len(self.click_points)}: ({x}, {y})")
                
                if len(self.click_points) == 2:
                    p1, p2 = self.click_points
                    distance = math.sqrt((p2[0]-p1[0])**2 + (p2[1]-p1[1])**2)
                    print(f"📏 Distance: {distance:.1f} pixels → กด SPACE เพื่อยืนยัน!")
                    # DON'T clear - wait for SPACE to confirm
            else:
                # Normal mode - clear after measuring
                self.click_points.append((x, y))
                print(f"📍 Point {len(self.click_points)}: ({x}, {y})")
                
                if len(self.click_points) == 2:
                    p1, p2 = self.click_points
                    distance = math.sqrt((p2[0]-p1[0])**2 + (p2[1]-p1[1])**2)
                    print(f"📏 Distance: {distance:.1f} pixels")
                    self.click_points = []
    
    def open_camera(self) -> bool:
        """Open camera with Raspberry Pi 5 compatible settings"""
        if not CV2_AVAILABLE:
            print("❌ OpenCV not installed. Run: pip install opencv-python")
            return False
        
        # For Raspberry Pi 5, use device path directly
        device_path = f"/dev/video{self.camera_id}"
        
        print(f"🔍 Trying to open: {device_path}")
        
        # Try with device path first (more reliable on RPi5)
        self.cap = cv2.VideoCapture(device_path, cv2.CAP_V4L2)
        
        if not self.cap.isOpened():
            print(f"⚠️ Device path failed, trying index {self.camera_id}...")
            self.cap = cv2.VideoCapture(self.camera_id)
        
        if not self.cap or not self.cap.isOpened():
            print(f"❌ Cannot open camera {device_path}")
            print("   Check: v4l2-ctl --list-devices")
            return False
        
        print(f"✅ Camera opened successfully")
        
        # Set resolution
        self.cap.set(cv2.CAP_PROP_FRAME_WIDTH, self.width)
        self.cap.set(cv2.CAP_PROP_FRAME_HEIGHT, self.height)
        
        # Set buffer size to reduce latency
        self.cap.set(cv2.CAP_PROP_BUFFERSIZE, 1)
        
        # Disable auto-focus (use manual focus)
        self.cap.set(cv2.CAP_PROP_AUTOFOCUS, 0)  # 0 = disable, 1 = enable
        # Set fixed focus (adjust value 0-255 depending on camera)
        self.cap.set(cv2.CAP_PROP_FOCUS, 0)  # 0 = infinity focus
        
        # Optionally disable auto exposure
        # self.cap.set(cv2.CAP_PROP_AUTO_EXPOSURE, 1)  # 1 = manual, 3 = auto
        
        print("🔧 Auto-focus disabled")
        
        actual_w = int(self.cap.get(cv2.CAP_PROP_FRAME_WIDTH))
        actual_h = int(self.cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
        print(f"📷 Resolution: {actual_w}x{actual_h}")
        
        return True
    
    def close_camera(self):
        """Release camera"""
        if self.cap:
            self.cap.release()
            cv2.destroyAllWindows()
    
    def draw_calibration_overlay(self, frame):
        """Draw grid and guides on frame for calibration"""
        h, w = frame.shape[:2]
        
        # Draw grid lines
        # Horizontal lines (divide into 3 zones: NEAR, CENTER, FAR)
        y1 = h // 3
        y2 = 2 * h // 3
        cv2.line(frame, (0, y1), (w, y1), (0, 255, 255), 1)
        cv2.line(frame, (0, y2), (w, y2), (0, 255, 255), 1)
        
        # Zone labels
        cv2.putText(frame, "FAR", (10, y1 - 10), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 255, 255), 1)
        cv2.putText(frame, "CENTER", (10, y2 - 10), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 255, 0), 1)
        cv2.putText(frame, "NEAR", (10, h - 10), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 165, 255), 1)
        
        # Center crosshair
        cx, cy = w // 2, h // 2
        cv2.line(frame, (cx - 30, cy), (cx + 30, cy), (0, 255, 0), 1)
        cv2.line(frame, (cx, cy - 30), (cx, cy + 30), (0, 255, 0), 1)
        
        # Vertical center line
        cv2.line(frame, (cx, 0), (cx, h), (100, 100, 100), 1)
        
        # Show clicked points
        for i, (px, py) in enumerate(self.click_points):
            cv2.circle(frame, (px, py), 5, (0, 0, 255), -1)
            cv2.putText(frame, f"P{i+1}", (px+10, py), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 0, 255), 1)
        
        # Draw line between 2 points
        if len(self.click_points) == 2:
            p1, p2 = self.click_points
            cv2.line(frame, p1, p2, (255, 0, 255), 2)
            dist = math.sqrt((p2[0]-p1[0])**2 + (p2[1]-p1[1])**2)
            mid = ((p1[0]+p2[0])//2, (p1[1]+p2[1])//2)
            cv2.putText(frame, f"{dist:.1f}px", mid, cv2.FONT_HERSHEY_SIMPLEX, 0.7, (255, 0, 255), 2)
        
        # Instructions
        cv2.putText(frame, "Click 2 points to measure | Q=Quit | C=Clear | S=Screenshot", 
                    (10, 20), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (255, 255, 255), 1)
        
        return frame
    
    def run_preview(self, with_overlay: bool = True) -> Optional[Tuple[int, int]]:
        """
        Run live camera preview with calibration overlay
        Returns last measured pixel distance if any
        """
        if not self.open_camera():
            return None
        
        window_name = "AgriBot Calibration - Camera Preview"
        cv2.namedWindow(window_name)
        cv2.setMouseCallback(window_name, self._mouse_callback)
        
        last_distance = None
        screenshot_count = 0
        
        print("\n🎥 Camera Preview Started")
        print("   Click 2 points to measure distance")
        print("   Q=Quit | C=Clear points | S=Screenshot")
        print("-" * 40)
        
        try:
            while True:
                ret, frame = self.cap.read()
                if not ret:
                    print("⚠️ Cannot read frame")
                    break
                
                if with_overlay:
                    frame = self.draw_calibration_overlay(frame)
                
                cv2.imshow(window_name, frame)
                
                key = cv2.waitKey(1) & 0xFF
                
                if key == ord('q') or key == 27:  # Q or ESC
                    break
                elif key == ord('c'):  # Clear points
                    self.click_points = []
                    print("🗑️ Points cleared")
                elif key == ord('s'):  # Screenshot
                    screenshot_path = Path(__file__).parent / f"calibration_screenshot_{screenshot_count}.jpg"
                    cv2.imwrite(str(screenshot_path), frame)
                    print(f"📸 Screenshot saved: {screenshot_path}")
                    screenshot_count += 1
                
                # Update last measured distance
                if len(self.click_points) == 2:
                    p1, p2 = self.click_points
                    last_distance = math.sqrt((p2[0]-p1[0])**2 + (p2[1]-p1[1])**2)
        
        except KeyboardInterrupt:
            print("\n⚠️ Interrupted")
        finally:
            self.close_camera()
        
        return last_distance
    
    def measure_pixels_live(self) -> float:
        """Open camera, let user measure, return pixel distance"""
        distance = self.run_preview()
        if distance:
            print(f"\n📏 Last measured: {distance:.1f} pixels")
        return distance if distance else 0.0
    
    def guided_calibration(self) -> dict:
        """
        Guided step-by-step calibration with camera
        Returns dictionary with all measured values
        """
        if not self.open_camera():
            return {}
        
        results = {
            'pixel_near': 0.0,
            'pixel_center': 0.0,
            'pixel_far': 0.0,
            'real_cm': 10.0,  # Using 10cm ruler
        }
        
        steps = [
            {
                'name': 'NEAR',
                'axis': 'Z-AXIS (แกนยืดแขน)',
                'instruction': 'วางไม้บรรทัด 10cm ที่ส่วนล่างของภาพ (ใกล้กล้อง)',
                'zone': 'bottom',
                'color': (0, 165, 255),  # Orange
            },
            {
                'name': 'CENTER', 
                'axis': 'Z-AXIS (แกนยืดแขน)',
                'instruction': 'วางไม้บรรทัด 10cm ตรงกลางภาพ',
                'zone': 'middle',
                'color': (0, 255, 0),  # Green
            },
            {
                'name': 'FAR',
                'axis': 'Z-AXIS (แกนยืดแขน)',
                'instruction': 'วางไม้บรรทัด 10cm ที่ส่วนบนของภาพ (ไกลกล้อง)',
                'zone': 'top',
                'color': (0, 255, 255),  # Yellow
            },
        ]
        
        current_step = 0
        window_name = "AgriBot Guided Calibration"
        cv2.namedWindow(window_name)
        cv2.setMouseCallback(window_name, self._mouse_callback)
        
        # Enable guided mode - don't auto-clear points
        self.guided_mode = True
        
        print("\n" + "="*60)
        print("  🎯 GUIDED CALIBRATION - ทำตามคำแนะนำบนหน้าจอ")
        print("="*60)
        print("\nคำสั่ง:")
        print("  • คลิก 2 จุด บนปลายไม้บรรทัดเพื่อวัด")
        print("  • กด SPACE = ยืนยันค่าและไปขั้นตอนถัดไป")
        print("  • กด C = ล้างจุดแล้ววัดใหม่")
        print("  • กด Q = ออก")
        print("-"*60)
        
        last_measured = 0.0
        
        try:
            while current_step < len(steps):
                ret, frame = self.cap.read()
                if not ret:
                    break
                
                step = steps[current_step]
                h, w = frame.shape[:2]
                
                # Draw zone indicator
                if step['zone'] == 'bottom':
                    y1, y2 = 2*h//3, h
                elif step['zone'] == 'middle':
                    y1, y2 = h//3, 2*h//3
                else:  # top
                    y1, y2 = 0, h//3
                
                # Highlight zone
                overlay = frame.copy()
                cv2.rectangle(overlay, (0, y1), (w, y2), step['color'], -1)
                frame = cv2.addWeighted(overlay, 0.2, frame, 0.8, 0)
                
                # Draw zone border
                cv2.rectangle(frame, (0, y1), (w, y2), step['color'], 3)
                
                # Draw instruction box at top
                cv2.rectangle(frame, (0, 0), (w, 100), (50, 50, 50), -1)
                
                # Axis indicator (prominent)
                cv2.putText(frame, step.get('axis', 'Z-AXIS'), 
                           (10, 25), cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 255, 255), 2)
                
                # Step indicator
                cv2.putText(frame, f"Step {current_step+1}/3: {step['name']}", 
                           (10, 50), cv2.FONT_HERSHEY_SIMPLEX, 0.6, (255, 255, 255), 2)
                cv2.putText(frame, step['instruction'], 
                           (10, 75), cv2.FONT_HERSHEY_SIMPLEX, 0.5, step['color'], 1)
                
                # Show clicked points
                for i, (px, py) in enumerate(self.click_points):
                    cv2.circle(frame, (px, py), 8, (0, 0, 255), -1)
                    cv2.circle(frame, (px, py), 10, (255, 255, 255), 2)
                
                # Draw line and distance if 2 points
                if len(self.click_points) >= 2:
                    p1, p2 = self.click_points[0], self.click_points[1]
                    cv2.line(frame, p1, p2, (255, 0, 255), 3)
                    last_measured = math.sqrt((p2[0]-p1[0])**2 + (p2[1]-p1[1])**2)
                    
                    # Show measurement
                    mid = ((p1[0]+p2[0])//2, (p1[1]+p2[1])//2 - 15)
                    cv2.putText(frame, f"{last_measured:.1f} px", mid, 
                               cv2.FONT_HERSHEY_SIMPLEX, 1.0, (255, 0, 255), 2)
                    
                    # Show confirmation hint
                    cv2.putText(frame, "SPACE = Confirm | C = Redo", 
                               (w//2 - 120, h - 20), cv2.FONT_HERSHEY_SIMPLEX, 0.6, (0, 255, 0), 2)
                else:
                    cv2.putText(frame, "Click 2 points on ruler ends", 
                               (w//2 - 130, h - 20), cv2.FONT_HERSHEY_SIMPLEX, 0.6, (255, 255, 255), 1)
                
                cv2.imshow(window_name, frame)
                key = cv2.waitKey(1) & 0xFF
                
                if key == ord('q') or key == 27:
                    break
                elif key == ord('c'):
                    self.click_points = []
                    print(f"🔄 รีเซ็ต - วัดใหม่")
                elif key == ord(' ') and len(self.click_points) >= 2:
                    # Confirm and go to next step
                    key_name = f"pixel_{step['name'].lower()}"
                    results[key_name] = last_measured
                    print(f"✅ {step['name']}: {last_measured:.1f} pixels")
                    
                    self.click_points = []
                    current_step += 1
        
        except KeyboardInterrupt:
            print("\n⚠️ Cancelled")
        finally:
            self.guided_mode = False  # Reset mode
            self.close_camera()
        
        # Calculate pixel_to_cm ratios
        if results['pixel_center'] > 0:
            results['pixel_to_cm_center'] = results['real_cm'] / results['pixel_center']
        if results['pixel_near'] > 0:
            results['pixel_to_cm_near'] = results['real_cm'] / results['pixel_near']
        if results['pixel_far'] > 0:
            results['pixel_to_cm_far'] = results['real_cm'] / results['pixel_far']
        
        # Average
        valid_ratios = [results.get(f'pixel_to_cm_{z}', 0) for z in ['near', 'center', 'far'] if results.get(f'pixel_to_cm_{z}', 0) > 0]
        if valid_ratios:
            results['pixel_to_cm_avg'] = sum(valid_ratios) / len(valid_ratios)
        
        return results



def find_available_cameras() -> List[int]:
    """Find available camera indices on Raspberry Pi"""
    if not CV2_AVAILABLE:
        return []
    
    available = []
    for i in range(5):  # Check first 5 indices
        cap = cv2.VideoCapture(i)
        if cap.isOpened():
            available.append(i)
            cap.release()
    return available


def camera_preview_menu():
    """Menu for camera preview and measurement"""
    print_header("📷 CAMERA PREVIEW (Raspberry Pi 5)")
    
    if not CV2_AVAILABLE:
        print("❌ OpenCV not available!")
        print("   Install with: pip install opencv-python")
        return None
    
    print("""
📹 USB Camera ปกติจะอยู่ที่ /dev/video0
   เช็คด้วย: v4l2-ctl --list-devices
""")
    
    cam_id = get_int("Camera ID (0 = /dev/video0)", 0)
    width = get_int("Width", 640)
    height = get_int("Height", 480)
    
    calibrator = CameraCalibrator(cam_id, width, height)
    distance = calibrator.run_preview()
    
    return distance


def easy_guided_calibration():
    """
    Easy mode: กล้องนำทาง + บันทึกอัตโนมัติ
    ผู้ใช้แค่ทำตามคำแนะนำบนหน้าจอ
    """
    print_header("🎯 EASY GUIDED CALIBRATION")
    
    if not CV2_AVAILABLE:
        print("❌ OpenCV not available!")
        return None
    
    print("""
╔═══════════════════════════════════════════════════════════╗
║  📋 สิ่งที่ต้องเตรียม:                                     ║
║     • ไม้บรรทัด 10 cm                                      ║
║     • กล้องเชื่อมต่อและทำงานปกติ                           ║
║                                                           ║
║  📌 วิธีใช้:                                               ║
║     1. วางไม้บรรทัดตามตำแหน่งที่ไฮไลท์                     ║
║     2. คลิก 2 จุด ที่ปลายทั้งสองของไม้บรรทัด              ║
║     3. กด SPACE เพื่อยืนยันและไปขั้นตอนถัดไป              ║
║                                                           ║
╚═══════════════════════════════════════════════════════════╝
""")
    
    input("กด Enter เพื่อเริ่มต้น...")
    
    # Create calibrator
    calibrator = CameraCalibrator(0, 640, 480)
    
    # Run guided calibration
    results = calibrator.guided_calibration()
    
    if not results or results.get('pixel_to_cm_avg', 0) == 0:
        print("\n❌ Calibration ไม่สำเร็จ หรือถูกยกเลิก")
        return None
    
    # Show results
    print("\n" + "="*60)
    print("  📊 ผลลัพธ์ CALIBRATION")
    print("="*60)
    print(f"""
╔═══════════════════════════════════════════════════════════╗
║  Measurements (using 10cm ruler):                         ║
╠═══════════════════════════════════════════════════════════╣
║  NEAR   : {results.get('pixel_near', 0):>7.1f} pixels  →  {results.get('pixel_to_cm_near', 0):.6f} cm/px  ║
║  CENTER : {results.get('pixel_center', 0):>7.1f} pixels  →  {results.get('pixel_to_cm_center', 0):.6f} cm/px  ║
║  FAR    : {results.get('pixel_far', 0):>7.1f} pixels  →  {results.get('pixel_to_cm_far', 0):.6f} cm/px  ║
╠═══════════════════════════════════════════════════════════╣
║  AVERAGE: {results.get('pixel_to_cm_avg', 0):.6f} cm/px                           ║
╚═══════════════════════════════════════════════════════════╝
""")
    
    # Ask to save
    save = input("💾 บันทึกค่าเหล่านี้? (y/n) [y]: ").lower().strip()
    if save != 'n':
        # Load existing and update
        data = CalibrationData.load()
        
        data.pixel_to_cm_z = results.get('pixel_to_cm_avg', data.pixel_to_cm_z)
        data.pixel_to_cm_z_near = results.get('pixel_to_cm_near', 0)
        data.pixel_to_cm_z_center = results.get('pixel_to_cm_center', 0)
        data.pixel_to_cm_z_far = results.get('pixel_to_cm_far', 0)
        data.pixel_to_cm_x = data.pixel_to_cm_z  # Same as Z
        
        data.calibrated_by = "Easy Guided Calibration"
        data.save()
        
        print("\n✅ บันทึกสำเร็จ! robot_brain.py จะใช้ค่าเหล่านี้อัตโนมัติ")
    else:
        print("\n❌ ไม่บันทึก")
    
    return results


# ==================== UTILITIES ====================

def clear_screen():
    """ล้างหน้าจอ (optional)"""
    import os
    os.system('cls' if os.name == 'nt' else 'clear')


def print_header(title: str):
    """แสดง header สวยๆ"""
    print("\n" + "="*60)
    print(f"  {title}")
    print("="*60)


def print_box(lines: List[str], title: str = ""):
    """แสดงข้อความในกรอบ"""
    max_len = max(len(line) for line in lines) if lines else 20
    if title:
        max_len = max(max_len, len(title) + 4)
    
    print("┌" + "─" * (max_len + 2) + "┐")
    if title:
        print(f"│ {title.center(max_len)} │")
        print("├" + "─" * (max_len + 2) + "┤")
    for line in lines:
        print(f"│ {line.ljust(max_len)} │")
    print("└" + "─" * (max_len + 2) + "┘")


def get_float(prompt: str, default: float, min_val: float = None, max_val: float = None) -> float:
    """รับ input เป็น float พร้อม default และ validation"""
    while True:
        try:
            value = input(f"{prompt} [{default}]: ").strip()
            if value == "":
                return default
            result = float(value)
            
            if min_val is not None and result < min_val:
                print(f"⚠️ ค่าต้องมากกว่า {min_val}")
                continue
            if max_val is not None and result > max_val:
                print(f"⚠️ ค่าต้องน้อยกว่า {max_val}")
                continue
                
            return result
        except ValueError:
            print("⚠️ กรุณาใส่ตัวเลข")


def get_int(prompt: str, default: int) -> int:
    """รับ input เป็น int พร้อม default value"""
    try:
        value = input(f"{prompt} [{default}]: ").strip()
        if value == "":
            return default
        return int(value)
    except ValueError:
        print("⚠️ ค่าไม่ถูกต้อง ใช้ค่า default")
        return default


# ==================== CALIBRATION FUNCTIONS ====================

def calibrate_pixel_to_cm_multipoint(data: CalibrationData) -> float:
    """
    คำนวณ pixel_to_cm จากการวัดหลายจุด (สำหรับกล้องเฉียง)
    """
    print_header("📏 PIXEL TO CM CALIBRATION (Multi-Point)")
    
    print("""
┌─────────────────────────────────────────────────────────┐
│  วิธีวัด (สำหรับกล้องเฉียง)                              │
├─────────────────────────────────────────────────────────┤
│                                                         │
│  1. วางไม้บรรทัด 3 ตำแหน่ง:                             │
│     - NEAR:   ส่วนล่างของภาพ (ใกล้กล้อง)               │
│     - CENTER: กลางภาพ (ตำแหน่งที่ target จะอยู่)        │
│     - FAR:    ส่วนบนของภาพ (ไกลกล้อง)                  │
│                                                         │
│  2. ในแต่ละตำแหน่ง:                                     │
│     - วัดว่าไม้บรรทัด 10 cm กินกี่ pixel                │
│     - (ดูจากภาพกล้องหรือใช้โปรแกรมวัด)                  │
│                                                         │
│  3. ระบบจะคำนวณค่าเฉลี่ยให้                             │
│                                                         │
│  💡 TIP: ใช้ค่า CENTER สำหรับการยืดแขน (Z-axis)         │
│                                                         │
└─────────────────────────────────────────────────────────┘
""")
    
    measurements = []
    
    # วัด 3 จุด
    positions = [
        ("NEAR", "ส่วนล่างของภาพ (ใกล้กล้อง)"),
        ("CENTER", "กลางภาพ (สำคัญที่สุด!)"),
        ("FAR", "ส่วนบนของภาพ (ไกลกล้อง)")
    ]
    
    for pos_name, pos_desc in positions:
        print(f"\n📍 {pos_name}: {pos_desc}")
        print("-" * 40)
        
        # ถามว่าจะวัดไหม
        measure = input("   วัดจุดนี้? (y/n/skip all) [y]: ").lower()
        if measure == 'skip all' or measure == 's':
            break
        if measure == 'n':
            continue
        
        pixel_dist = get_float(f"   📷 จำนวน pixel", 200, min_val=1)
        real_cm = get_float(f"   📐 ระยะจริง (cm)", 10, min_val=0.1)
        
        point = MeasurementPoint(
            position=pos_name.lower(),
            pixel_distance=pixel_dist,
            real_distance_cm=real_cm
        )
        ratio = point.calculate()
        measurements.append(point)
        
        print(f"   ✓ pixel_to_cm = {ratio:.6f}")
        
        # Save individual values
        if pos_name == "NEAR":
            data.pixel_to_cm_z_near = ratio
        elif pos_name == "CENTER":
            data.pixel_to_cm_z_center = ratio
        elif pos_name == "FAR":
            data.pixel_to_cm_z_far = ratio
    
    if not measurements:
        print("\n⚠️ ไม่มีการวัด ใช้ค่าเดิม")
        return data.pixel_to_cm_z
    
    # คำนวณค่าเฉลี่ย
    print("\n" + "="*50)
    print("📊 สรุปผล:")
    print("-"*50)
    
    ratios = [m.pixel_to_cm for m in measurements]
    
    for m in measurements:
        print(f"   {m.position.upper():8} : {m.pixel_to_cm:.6f} cm/px")
    
    avg_ratio = sum(ratios) / len(ratios)
    print("-"*50)
    print(f"   {'AVERAGE':8} : {avg_ratio:.6f} cm/px")
    
    # ถ้ามี CENTER ให้ใช้ CENTER (สำคัญที่สุดสำหรับ Z-axis)
    center_point = next((m for m in measurements if m.position == "center"), None)
    
    if center_point:
        print(f"\n💡 แนะนำ: ใช้ค่า CENTER ({center_point.pixel_to_cm:.6f}) สำหรับ Z-axis")
        use_center = input("   ใช้ค่า CENTER? (y/n) [y]: ").lower()
        if use_center != 'n':
            return center_point.pixel_to_cm
    
    return avg_ratio


def calibrate_camera_setup(data: CalibrationData):
    """ตั้งค่ากล้อง"""
    print_header("📷 CAMERA SETUP")
    
    print("""
องศากล้อง:
  - 0°  = มองลงตรงๆ (Top-down)
  - 45° = เฉียง 45 องศา
  - 90° = มองไปข้างหน้า (ไม่แนะนำ)
""")
    
    data.camera_angle_deg = get_float("📐 องศากล้อง", data.camera_angle_deg, min_val=0, max_val=90)
    data.camera_height_cm = get_float("📏 ความสูงกล้องจากพื้น (cm)", data.camera_height_cm, min_val=10)
    
    print(f"\n✓ Camera: {data.camera_angle_deg}° at {data.camera_height_cm}cm height")


def calibrate_arm_speed(data: CalibrationData):
    """Calibrate ความเร็วแขน (สำหรับ Time-based mode)"""
    print_header("⚙️ ARM SPEED CALIBRATION")
    
    print("""
┌─────────────────────────────────────────────────────────┐
│  วิธีวัด (สำหรับ Time-based mode)                        │
│  ⚠️ ถ้าใช้ Encoder mode ข้ามขั้นตอนนี้ได้               │
├─────────────────────────────────────────────────────────┤
│                                                         │
│  1. ทำเครื่องหมายจุดเริ่มต้นของแขน                      │
│                                                         │
│  2. ใช้ Serial Monitor ส่งคำสั่ง:                        │
│     ACT:Z_OUT:1.00  (ยืด 1 วินาที)                       │
│                                                         │
│  3. วัดระยะที่ยืดได้ (cm)                                │
│                                                         │
│  4. คำนวณ: speed = ระยะ / เวลา                          │
│                                                         │
└─────────────────────────────────────────────────────────┘
""")
    
    skip = input("ข้ามขั้นตอนนี้? (y/n) [n]: ").lower()
    if skip == 'y':
        return
    
    distance = get_float("📏 ระยะที่ยืดได้ (cm)", 10, min_val=0)
    duration = get_float("⏱️ เวลาที่ใช้ (วินาที)", 1.0, min_val=0.1)
    
    if duration > 0:
        speed = distance / duration
        data.arm_speed_cm_per_sec = speed
        print(f"\n✓ arm_speed = {speed:.2f} cm/s")


def calibrate_arm_offset(data: CalibrationData):
    """วัด offset ของแขน"""
    print_header("📍 ARM OFFSET")
    
    print("""
วัดระยะจากจุดกึ่งกลางเลนส์กล้อง ถึงจุดที่แขนเริ่มยืดออก
(ระยะนี้จะถูกลบออกจากการคำนวณ)

  กล้อง
    │
    │←── offset ──→ แขน
    │               ═══════→
    ▼
  พื้น
""")
    
    data.arm_base_offset_cm = get_float("📏 Arm offset (cm)", data.arm_base_offset_cm, min_val=0)


def calibrate_encoder(data: CalibrationData):
    """ตั้งค่า Encoder"""
    print_header("🔩 ENCODER SETTINGS (ESP32)")
    
    print("""
ใส่ค่าจาก spec ของ encoder และมอเตอร์
ค่าเหล่านี้จะบันทึกไว้เป็น reference สำหรับ ESP32
""")
    
    data.encoder_ppr = get_int("⚙️ Encoder PPR (pulses/rev)", data.encoder_ppr)
    data.wheel_diameter_mm = get_float("📏 เส้นผ่านศูนย์กลางเพลา (mm)", data.wheel_diameter_mm, min_val=1)
    
    # คำนวณ mm per pulse
    mm_per_pulse = (3.14159 * data.wheel_diameter_mm) / data.encoder_ppr
    print(f"\n📊 คำนวณได้: {mm_per_pulse:.4f} mm/pulse")


# ==================== MAIN WIZARDS ====================

def full_calibration_wizard():
    """Full Calibration Wizard"""
    print_header("🔧 FULL CALIBRATION WIZARD")
    print("กรอกค่าที่วัดได้ หรือกด Enter เพื่อใช้ค่าเดิม/default\n")
    
    # Load existing
    data = CalibrationData.load()
    
    # Step 1: Camera Setup
    calibrate_camera_setup(data)
    
    # Step 2: Pixel to CM (Multi-point)
    data.pixel_to_cm_z = calibrate_pixel_to_cm_multipoint(data)
    data.pixel_to_cm_x = data.pixel_to_cm_z  # Default same
    
    # Step 3: Arm Speed
    calibrate_arm_speed(data)
    
    # Step 4: Arm Offset
    calibrate_arm_offset(data)
    
    # Step 5: Other settings
    print_header("📐 OTHER SETTINGS")
    data.max_arm_extend_cm = get_float("🔧 ระยะยืดสูงสุด (cm)", data.max_arm_extend_cm, min_val=1)
    data.alignment_tolerance_px = get_int("🎯 Alignment tolerance (px)", data.alignment_tolerance_px)
    data.default_spray_duration = get_float("💨 เวลาพ่นยา (วินาที)", data.default_spray_duration, min_val=0.1)
    
    # Step 6: Encoder
    enc = input("\nตั้งค่า Encoder? (y/n) [n]: ").lower()
    if enc == 'y':
        calibrate_encoder(data)
    
    # Notes
    data.notes = input("\n📝 บันทึกเพิ่มเติม: ").strip()
    data.calibrated_by = input("👤 ผู้ calibrate: ").strip()
    
    # Summary
    show_summary(data)
    
    # Save
    confirm = input("\n💾 บันทึกค่าเหล่านี้? (y/n) [y]: ").lower()
    if confirm != 'n':
        data.save()
        print("\n✅ บันทึกสำเร็จ! robot_brain.py จะใช้ค่าเหล่านี้อัตโนมัติ")
    else:
        print("\n❌ ยกเลิก ไม่บันทึก")
    
    return data


def quick_calibration():
    """Quick calibration - เฉพาะค่าสำคัญ"""
    print_header("⚡ QUICK CALIBRATION")
    
    data = CalibrationData.load()
    
    # Pixel to CM only
    data.pixel_to_cm_z = calibrate_pixel_to_cm_multipoint(data)
    data.pixel_to_cm_x = data.pixel_to_cm_z
    
    # Offset
    calibrate_arm_offset(data)
    
    data.save()
    print("\n✅ Quick calibration สำเร็จ!")
    
    return data


def show_summary(data: CalibrationData):
    """แสดงสรุป"""
    print_header("📊 CALIBRATION SUMMARY")
    
    print(f"""
┌─────────────────────────────────────────────────────────┐
│  Camera                                                  │
├─────────────────────────────────────────────────────────┤
│  Angle:          {data.camera_angle_deg:>6.1f}°                              │
│  Height:         {data.camera_height_cm:>6.1f} cm                            │
│  Image:          {data.img_width} x {data.img_height}                           │
├─────────────────────────────────────────────────────────┤
│  Z-Axis (Arm)                                           │
├─────────────────────────────────────────────────────────┤
│  pixel_to_cm_z:  {data.pixel_to_cm_z:>10.6f}                          │
│    - Near:       {data.pixel_to_cm_z_near:>10.6f}                          │
│    - Center:     {data.pixel_to_cm_z_center:>10.6f}                          │
│    - Far:        {data.pixel_to_cm_z_far:>10.6f}                          │
│  arm_speed:      {data.arm_speed_cm_per_sec:>6.2f} cm/s                          │
│  arm_offset:     {data.arm_base_offset_cm:>6.2f} cm                            │
│  max_extend:     {data.max_arm_extend_cm:>6.2f} cm                            │
├─────────────────────────────────────────────────────────┤
│  Other                                                   │
├─────────────────────────────────────────────────────────┤
│  alignment_tol:  {data.alignment_tolerance_px:>6} px                            │
│  spray_time:     {data.default_spray_duration:>6.2f} s                             │
│  encoder_ppr:    {data.encoder_ppr:>6}                                  │
└─────────────────────────────────────────────────────────┘
""")


def show_current():
    """แสดงค่าปัจจุบัน"""
    print_header("📋 CURRENT CALIBRATION")
    
    if not CONFIG_FILE.exists():
        print("⚠️ ยังไม่มีไฟล์ calibration.json")
        print("   รัน calibration ก่อน")
        return
    
    data = CalibrationData.load()
    show_summary(data)
    print(f"\nCalibrated: {data.calibrated_at}")
    print(f"By: {data.calibrated_by}")
    if data.notes:
        print(f"Notes: {data.notes}")


# ==================== MAIN ====================

def main():
    print("""
╔══════════════════════════════════════════════════════════╗
║                                                          ║
║        🚜 AgriBot Calibration Tool v2.2 🚜               ║
║       Raspberry Pi 5 Compatible                          ║
║                                                          ║
║   + Easy Guided Calibration (ใหม่!)                      ║
║   + Live Camera Preview                                  ║
║                                                          ║
╚══════════════════════════════════════════════════════════╝
""")
    
    print("เลือก mode:")
    print("  1. 🎯 Easy Calibration  ★แนะนำ★ (กล้องนำทาง ง่ายที่สุด!)")
    print("  2. Full Calibration    (ตั้งค่าครบทุกอย่าง)")
    print("  3. Quick Calibration   (เฉพาะ pixel_to_cm)")
    print("  4. 📷 Camera Preview   (ดูภาพกล้อง + วัด pixel)")
    print("  5. แสดงค่าปัจจุบัน")
    print("  6. อ่านคู่มือ")
    print("  q. ออก")
    
    choice = input("\nเลือก (1/2/3/4/5/6/q): ").strip()
    
    if choice == '1':
        easy_guided_calibration()
    elif choice == '2':
        full_calibration_wizard()
    elif choice == '3':
        quick_calibration()
    elif choice == '4':
        camera_preview_menu()
    elif choice == '5':
        show_current()
    elif choice == '6':
        print("\n📖 ดูคู่มือที่: raspberry_pi/CALIBRATION_GUIDE.md")
    elif choice == 'q':
        print("👋 Bye!")
    else:
        print("⚠️ Invalid choice")


if __name__ == "__main__":
    main()
