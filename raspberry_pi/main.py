"""
AgriBot Main Application
โปรแกรมหลักสำหรับรถพ่นยากำจัดวัชพืชอัตโนมัติ

YOLO11 Multi-Class Detection:
- weed (หญ้า): พ่นยา ✓
- chili (ต้นพริก): ห้ามพ่น ✗

v2.0 - Smooth Movement with Speed Control:
- High FPS detection (~20-30 FPS)
- Speed control based on distance to target
- Continuous detection while moving

Author: AgriBot Team
"""

import time
import logging
import argparse
import cv2
from typing import Optional

from robot_brain import RobotBrain, CalibrationConfig, RobotState
from weed_detector import WeedDetector, Detection
from weed_tracker import SimpleTracker, TrackedObject

# ==================== LOGGING SETUP ====================
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


class AgriBot:
    """
    Main Application Class
    
    รวม YOLO11 Vision + Robot Control + Smooth Movement
    """
    
    # Detection settings
    TARGET_FPS = 25                  # Target frame rate
    FRAME_DELAY = 1.0 / TARGET_FPS   # ~40ms per frame
    
    def __init__(
        self,
        serial_port: str = '/dev/ttyUSB0',
        camera_id: int = 0,
        yolo_model: str = None
    ):
        # สร้าง Config (โหลดจาก calibration.json อัตโนมัติ)
        self.config = CalibrationConfig.load_from_file()
        self.config.serial_port = serial_port
        
        # สร้าง Components
        self.brain = RobotBrain(self.config)
        self.detector = WeedDetector(
            model_path=yolo_model,
            camera_id=camera_id,
            frame_width=self.config.img_width,
            frame_height=self.config.img_height
        )
        
        # Weed Tracker
        self.tracker = SimpleTracker(
            max_frames_missing=15,
            iou_threshold=0.3
        )
        
        # Statistics
        self.spray_count = 0
        self.weed_detected = 0
        self.chili_avoided = 0
        self.is_running = False
        
        # Speed control state
        self.current_speed = 0
        self.last_speed_update = 0
    
    def initialize(self) -> bool:
        """เริ่มต้นระบบ"""
        logger.info("🚀 Initializing AgriBot v2.0 (Smooth Movement)...")
        
        if not self.brain.connect():
            logger.error("❌ Failed to connect ESP32")
            return False
        
        if not self.detector.start_camera():
            logger.error("❌ Failed to start camera")
            self.brain.disconnect()
            return False
        
        logger.info("✅ AgriBot initialized")
        logger.info(f"   Target FPS: {self.TARGET_FPS}")
        logger.info(f"   Model: {self.detector.get_model_info()['model_name']}")
        return True
    
    def shutdown(self):
        """ปิดระบบ"""
        logger.info("🛑 Shutting down AgriBot...")
        self.is_running = False
        self.brain.stop_movement()
        self.detector.stop_camera()
        self.brain.disconnect()
        
        # แสดงสถิติ
        logger.info("📊 Session Statistics:")
        logger.info(f"   Weeds detected: {self.weed_detected}")
        logger.info(f"   Weeds sprayed: {self.spray_count}")
        logger.info(f"   Chilies avoided: {self.chili_avoided}")
    
    # ==================== AUTO MODE (SMOOTH) ====================
    
    def run_auto_mode(
        self,
        confidence_threshold: float = 0.5
    ):
        """
        โหมดอัตโนมัติ: Smooth Movement with Continuous Detection
        
        Features:
        - High FPS detection (~20-30 FPS)
        - Speed control based on distance
        - Smooth deceleration when approaching target
        """
        logger.info("🤖 AUTO MODE v2.0 Started (Smooth Movement)")
        logger.info("   Press Ctrl+C to stop")
        logger.info("   RED = Weed (target), GREEN = Chili (safe)")
        
        self.is_running = True
        self.detector.confidence_threshold = confidence_threshold
        
        try:
            while self.is_running:
                self._smooth_search_cycle()
                
        except KeyboardInterrupt:
            logger.info("⏹️ Stopped by user")
        finally:
            self.shutdown()
    
    def _smooth_search_cycle(self):
        """
        Smooth Search Cycle:
        1. เริ่มวิ่งช้าๆ พร้อมสแกน
        2. เจอ target → ปรับความเร็วตามระยะ
        3. ใกล้พอ → หยุด + พ่น
        4. พ่นเสร็จ → ไปต่อ
        """
        # เริ่มวิ่งด้วยความเร็วปกติ
        self.brain.move_forward_speed(self.brain.SPEED_NORMAL)
        self.current_speed = self.brain.SPEED_NORMAL
        
        frame_count = 0
        last_frame_time = time.time()
        
        while self.is_running:
            loop_start = time.time()
            
            # === จับภาพ ===
            frame = self.detector.capture_frame()
            if frame is None:
                continue
            
            frame_count += 1
            
            # === ตรวจจับ ===
            all_detections = self.detector.detect(frame)
            
            # === Track objects ===
            tracked = self.tracker.update(all_detections)
            
            # นับ class (ทุก 10 frames เพื่อไม่ให้นับซ้ำ)
            if frame_count % 10 == 0:
                for det in all_detections:
                    if det.is_target:
                        self.weed_detected += 1
                    else:
                        self.chili_avoided += 1
            
            # === หา nearest unsprayed target (หญ้า) ===
            # เฉพาะ target ที่อยู่ด้านหน้า (X >= 0) และยังไม่ได้พ่น
            unsprayed_targets = self.tracker.get_unsprayed_targets(min_x=-20)
            
            if not unsprayed_targets:
                # ไม่มี target → วิ่งเต็มความเร็ว
                if self.current_speed != self.brain.SPEED_NORMAL:
                    self.brain.set_speed(self.brain.SPEED_NORMAL)
                    self.current_speed = self.brain.SPEED_NORMAL
            else:
                # มี target → ใช้ตัวที่ใกล้ center ที่สุด
                target = unsprayed_targets[0]
                distance_x = target.x - (self.config.img_width // 2)
                new_speed = self.brain.calculate_approach_speed(distance_x)
                
                # อัพเดทความเร็ว (ไม่ถี่เกินไป)
                if abs(new_speed - self.current_speed) > 10:
                    self.brain.set_speed(new_speed)
                    self.current_speed = new_speed
                
                # === ถึงตำแหน่งแล้ว? ===
                if new_speed == 0:
                    logger.info(f"🎯 Target #{target.id} ALIGNED at X:{target.x}")
                    self.brain.stop_movement()
                    time.sleep(0.1)  # รอนิ่ง
                    
                    # จับภาพใหม่ยืนยัน
                    frame = self.detector.capture_frame()
                    if frame:
                        all_detections = self.detector.detect(frame)
                        self.tracker.update(all_detections)
                        unsprayed_targets = self.tracker.get_unsprayed_targets(min_x=-30)
                    
                    if unsprayed_targets:
                        target = unsprayed_targets[0]
                        # === พ่นยา ===
                        distance_y = target.y - (self.config.img_height // 2)
                        logger.info(f"🔄 Spraying target #{target.id} at Y-distance: {distance_y}px")
                        
                        success = self.brain.execute_spray_mission(
                            distance_from_center_px=abs(distance_y)
                        )
                        
                        if success:
                            # ทำเครื่องหมายว่าพ่นแล้ว
                            self.tracker.mark_sprayed(target.id)
                            self.spray_count += 1
                            logger.info(f"💧 Spray #{self.spray_count} completed (ID:{target.id})")
                        else:
                            logger.error("❌ Spray mission failed")
                    
                    # ไปหาเป้าถัดไป
                    logger.info("➡️ Moving to next target...")
                    break
            
            # === FPS Control ===
            elapsed = time.time() - loop_start
            sleep_time = self.FRAME_DELAY - elapsed
            if sleep_time > 0:
                time.sleep(sleep_time)
            
            # แสดง FPS ทุก 50 frames
            if frame_count % 50 == 0:
                actual_fps = 50 / (time.time() - last_frame_time)
                logger.debug(f"📊 FPS: {actual_fps:.1f}")
                last_frame_time = time.time()
    
    # ==================== MANUAL MODE ====================
    
    def run_manual_mode(self):
        """
        โหมด Manual พร้อมแสดง YOLO11 Detection
        
        Controls:
            W/S - Forward/Backward
            X   - Stop
            Z/C - Extend/Retract arm
            Y   - Toggle spray head
            P   - Spray
            Q   - Quit
        """
        logger.info("🎮 MANUAL MODE Started")
        logger.info("   W=Forward, S=Backward, X=Stop")
        logger.info("   Z=Extend, C=Retract, Y=Toggle Head, P=Spray")
        logger.info("   Q=Quit")
        
        self.is_running = True
        head_down = False
        
        try:
            while self.is_running:
                frame = self.detector.capture_frame()
                if frame is not None:
                    # ตรวจจับและแสดง
                    all_detections = self.detector.detect(frame)
                    targets = self.detector.get_targets_only(all_detections)
                    
                    output = self.detector.draw_detections(frame, all_detections)
                    
                    # แสดงสถานะ
                    status_lines = [
                        f"State: {self.brain.state.value}",
                        f"Speed: {self.current_speed}",
                        f"Head: {'DOWN' if head_down else 'UP'}",
                        f"Targets: {len(targets)} | Total: {len(all_detections)}",
                        f"Sprayed: {self.spray_count}"
                    ]
                    
                    for i, line in enumerate(status_lines):
                        cv2.putText(output, line, (10, 25 + i*25),
                                    cv2.FONT_HERSHEY_SIMPLEX, 0.6, (0, 255, 255), 2)
                    
                    # แสดง nearest target info + recommended speed
                    nearest = self.detector.get_nearest_target(all_detections)
                    if nearest:
                        t, d = self.brain.calculate_z_distance(nearest.distance_from_center_y)
                        speed = self.brain.calculate_approach_speed(nearest.distance_from_center_x)
                        info = f"Nearest: {d:.1f}cm | Speed: {speed}"
                        cv2.putText(output, info, (10, 150),
                                    cv2.FONT_HERSHEY_SIMPLEX, 0.6, (0, 255, 0), 2)
                    
                    cv2.imshow("AgriBot Manual Control", output)
                
                # รับคำสั่ง
                key = cv2.waitKey(50) & 0xFF
                
                if key == ord('q'):
                    break
                elif key == ord('w'):
                    self.brain.move_forward()
                    self.current_speed = self.brain.SPEED_NORMAL
                elif key == ord('s'):
                    self.brain.move_backward()
                elif key == ord('x'):
                    self.brain.stop_movement()
                    self.current_speed = 0
                elif key == ord('z'):
                    self.brain.send_cmd("ACT:Z_OUT:1.0")
                elif key == ord('c'):
                    self.brain.send_cmd("ACT:Z_IN:1.5")
                elif key == ord('y'):
                    if head_down:
                        self.brain.raise_spray_head()
                    else:
                        self.brain.lower_spray_head()
                    head_down = not head_down
                elif key == ord('p'):
                    self.brain.spray()
                    self.spray_count += 1
                elif key == ord('e'):
                    # Auto-spray nearest target
                    if nearest:
                        self.brain.execute_spray_mission(
                            abs(nearest.distance_from_center_y)
                        )
                        self.spray_count += 1
                    
        except KeyboardInterrupt:
            pass
        finally:
            cv2.destroyAllWindows()
            self.shutdown()
    
    # ==================== CALIBRATION MODE ====================
    
    def run_calibration_mode(self):
        """
        โหมด Calibration สำหรับวัดค่าต่างๆ
        """
        logger.info("📐 CALIBRATION MODE Started")
        logger.info("   Place ruler in view and measure pixel-to-cm ratio")
        logger.info("   Press Q to quit")
        
        self.is_running = True
        
        try:
            while self.is_running:
                frame = self.detector.capture_frame()
                if frame is None:
                    continue
                
                # ตรวจจับ
                all_detections = self.detector.detect(frame)
                output = self.detector.draw_detections(frame, all_detections)
                
                # แสดง Calibration info
                cv2.putText(output, "CALIBRATION MODE", (10, 25),
                            cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 0, 255), 2)
                
                cv2.putText(output, f"Center: ({self.detector.center_x}, {self.detector.center_y})", 
                            (10, 50), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (255, 255, 255), 1)
                
                # แสดงข้อมูลแต่ละ detection
                for i, det in enumerate(all_detections[:5]):
                    t, d = self.brain.calculate_z_distance(det.distance_from_center_y)
                    speed = self.brain.calculate_approach_speed(det.distance_from_center_x)
                    info = f"[{i}] {det.class_name}: X={det.distance_from_center_x}px (spd:{speed}) Y={det.distance_from_center_y}px -> {d:.1f}cm"
                    cv2.putText(output, info, (10, 80 + i*20),
                                cv2.FONT_HERSHEY_SIMPLEX, 0.4, (0, 255, 255), 1)
                
                # แสดง current config
                y_pos = output.shape[0] - 100
                configs = [
                    f"pixel_to_cm_z: {self.config.pixel_to_cm_z}",
                    f"arm_speed: {self.config.arm_speed_cm_per_sec} cm/s",
                    f"arm_offset: {self.config.arm_base_offset_cm} cm",
                    f"Speed zones: FAR>200 MID>100 NEAR>50 ALIGN>{self.config.alignment_tolerance_px}"
                ]
                for i, conf in enumerate(configs):
                    cv2.putText(output, conf, (10, y_pos + i*20),
                                cv2.FONT_HERSHEY_SIMPLEX, 0.4, (200, 200, 200), 1)
                
                cv2.imshow("AgriBot Calibration", output)
                
                if cv2.waitKey(50) & 0xFF == ord('q'):
                    break
                    
        except KeyboardInterrupt:
            pass
        finally:
            cv2.destroyAllWindows()
            self.detector.stop_camera()


# ==================== MAIN EXECUTION ====================
def main():
    parser = argparse.ArgumentParser(description="AgriBot - YOLO11 Weed Spraying Robot v2.0")
    parser.add_argument('--mode', '-m', 
                        choices=['auto', 'manual', 'calibrate'],
                        default='auto',
                        help='Operating mode')
    parser.add_argument('--port', '-p', 
                        default='/dev/ttyUSB0',
                        help='Serial port for ESP32')
    parser.add_argument('--camera', '-c', 
                        type=int, default=1,
                        help='Camera ID (default: 1 for USB camera on RPi5)')
    parser.add_argument('--model', 
                        type=str, default=None,
                        help='Path to YOLO11 model (.pt)')
    parser.add_argument('--threshold', '-t', 
                        type=float, default=0.5,
                        help='Detection confidence threshold')
    
    args = parser.parse_args()
    
    # สร้าง AgriBot
    bot = AgriBot(
        serial_port=args.port,
        camera_id=args.camera,
        yolo_model=args.model
    )
    
    # เริ่มระบบ
    if args.mode == 'calibrate':
        # Calibrate mode ไม่ต้องเชื่อม ESP32
        if bot.detector.start_camera():
            bot.run_calibration_mode()
        return
    
    if not bot.initialize():
        logger.error("❌ Failed to initialize AgriBot")
        return
    
    # เลือกโหมด
    if args.mode == 'auto':
        bot.run_auto_mode(confidence_threshold=args.threshold)
    elif args.mode == 'manual':
        bot.run_manual_mode()


if __name__ == "__main__":
    main()
