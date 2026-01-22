#!/usr/bin/env python3
"""
AgriBot Main Runner - ฉบับสมบูรณ์
Entry point หลักที่มี Flow การทำงานถูกต้องตามที่ออกแบบ

Flow:
1. รถเดินหน้า + ตรวจจับ
2. พบวัชพืช → หยุด
3. คำนวณ + เคลื่อนที่ให้วัตถุอยู่บนแกน Y ของภาพ
4. คำนวณระยะยืดแขน Z
5. ชดเชยระยะ กล้อง→แขน (8.5cm)
6. ยืด Z → ลง Y → ฉีด 3 วิ
7. ขึ้น Y → หด Z → reset
8. เดินหน้าต่อ

Author: AgriBot Team
"""

import argparse
import logging
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

from robot_brain import RobotBrain, CalibrationConfig, RobotState
from weed_detector import WeedDetector, Detection
from exceptions import RobotConnectionError, CameraError, EmergencyStopError

# Logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(),
        logging.FileHandler('agribot.log', encoding='utf-8')
    ]
)
logger = logging.getLogger(__name__)


class AgribotController:
    """
    Main Controller รวม RobotBrain + WeedDetector
    จัดการ Flow การทำงานทั้งหมด
    """
    
    # Constants
    IMAGE_CENTER_X = 320  # กลางภาพ 640px (แกน Y ของภาพ)
    IMAGE_CENTER_Y = 240  # กลางภาพ 480px (แกน X ของภาพ)
    SPRAY_DURATION = 3.0  # เวลาฉีดพ่น (วินาที)
    
    def __init__(self, config: CalibrationConfig = None):
        self.config = config or CalibrationConfig.load_from_file()
        self.brain = RobotBrain(self.config)
        self.detector = WeedDetector(
            frame_width=self.config.img_width,
            frame_height=self.config.img_height,
            confidence_threshold=0.25
        )
        self.running = False
    
    def connect(self) -> bool:
        """เชื่อมต่อ ESP32 และ กล้อง"""
        if not self.detector.start_camera():
            raise CameraError(self.detector.camera_id, "Failed to start camera")
        
        if not self.brain.connect():
            self.detector.stop_camera()
            raise RobotConnectionError(port=self.config.serial_port)
        
        logger.info("✅ All systems connected")
        return True
    
    def disconnect(self):
        """ปิดการเชื่อมต่อ"""
        self.brain.stop_movement()
        self.brain.disconnect()
        self.detector.stop_camera()
        logger.info("🔌 Disconnected")
    
    def is_valid_target(self, detection: Detection) -> bool:
        """
        ตรวจสอบว่า target ยังไม่ถูกประมวลผล
        ใช้ method จาก RobotBrain
        """
        # วัตถุที่อยู่หลังรถแล้ว = ไม่ทำซ้ำ
        return not self.brain.is_target_behind_robot(detection.x)
    
    def execute_spray_sequence(self, z_time: float):
        """
        ปฏิบัติการฉีดพ่น
        
        1. ยืดแขน Z
        2. ลงแขน Y
        3. ฉีด 3 วินาที
        4. ขึ้นแขน Y
        5. หดแขน Z
        """
        logger.info("🎯 Starting spray sequence...")
        
        # Step 1: ยืดแขน Z
        logger.info(f"   Z OUT: {z_time:.2f}s")
        self.brain.extend_arm(z_time)
        
        # Step 2: ลงแขน Y
        logger.info("   Y DOWN")
        self.brain.lower_spray_head()
        
        # Step 3: ฉีดพ่น
        logger.info(f"   SPRAY: {self.SPRAY_DURATION}s")
        self.brain.spray(self.SPRAY_DURATION)
        
        # Step 4: ขึ้นแขน Y
        logger.info("   Y UP")
        self.brain.raise_spray_head()
        
        # Step 5: หดแขน Z (บวก buffer)
        retract_time = z_time + self.config.arm_retract_buffer
        logger.info(f"   Z IN: {retract_time:.2f}s")
        self.brain.retract_arm(z_time)
        
        logger.info("✅ Spray sequence complete")
    
    def process_target(self, detection: Detection):
        """
        ประมวลผล target ที่ตรวจพบ (Flow เต็ม)
        ใช้ methods จาก RobotBrain
        """
        logger.info(f"🌿 Processing target: {detection.class_name} at ({detection.x}, {detection.y})")
        
        # STEP 2-3: คำนวณและเคลื่อนที่ให้วัตถุอยู่บนแกน Y
        direction, align_time = self.brain.calculate_align_to_y_axis(detection.x)
        
        if align_time > 0.05:  # มากกว่า 50ms ถึงจะเคลื่อนที่
            if direction == "FW":
                self.brain.move_forward_time(align_time)
            else:
                self.brain.move_backward_time(align_time)
        
        # STEP 4: คำนวณระยะยืดแขน Z จาก Y ในภาพ
        z_distance_cm, z_time = self.brain.calculate_z_from_image_y(detection.y)
        
        # STEP 5: ชดเชยระยะ กล้อง → แขน (8.5 cm)
        offset_time = self.brain.get_camera_offset_time()
        self.brain.move_forward_time(offset_time)
        
        # STEP 6-7: ปฏิบัติการฉีดพ่น + reset
        self.execute_spray_sequence(z_time)
    
    def run_auto_mode(self):
        """
        โหมดอัตโนมัติ - Loop หลัก
        """
        logger.info("🚀 Starting AUTO mode")
        self.running = True
        
        try:
            while self.running:
                # STEP 0: เดินหน้า
                self.brain.move_forward()
                
                while self.running:
                    # จับภาพ
                    frame = self.detector.capture_frame()
                    if frame is None:
                        continue
                    
                    # ตรวจจับ
                    detections = self.detector.detect(frame)
                    
                    # กรองเฉพาะ target ที่ valid (อยู่หน้ารถ)
                    valid_targets = [d for d in detections 
                                    if d.is_target and self.is_valid_target(d)]
                    
                    if valid_targets:
                        # STEP 1: หยุดรถ
                        self.brain.stop_movement()
                        
                        # เลือก target ที่ใกล้กลางที่สุด
                        target = min(valid_targets, 
                                    key=lambda d: abs(d.x - self.IMAGE_CENTER_X))
                        
                        # ประมวลผล
                        self.process_target(target)
                        
                        # STEP 8: เดินหน้าต่อ (break inner loop)
                        break
                    
                    time.sleep(0.05)  # 20 FPS
                    
        except KeyboardInterrupt:
            logger.info("🛑 Stopped by user (Ctrl+C)")
        except EmergencyStopError:
            logger.warning("⚠️ Emergency stop activated!")
        finally:
            self.running = False
            self.brain.stop_movement()
    
    def run_test_mode(self):
        """ทดสอบการเชื่อมต่อ"""
        print("\n" + "="*50)
        print("  Connection Test")
        print("="*50)
        
        # Test ESP32
        print("\n🔌 Testing ESP32...")
        if self.brain.connect():
            print("   ✅ ESP32 OK")
            self.brain.disconnect()
        else:
            print("   ❌ ESP32 FAILED")
            return False
        
        # Test Camera
        print("\n📷 Testing Camera...")
        if self.detector.start_camera():
            frame = self.detector.capture_frame()
            if frame is not None:
                print(f"   ✅ Camera OK ({frame.shape[1]}x{frame.shape[0]})")
                self.detector.stop_camera()
            else:
                print("   ❌ Camera read FAILED")
                self.detector.stop_camera()
                return False
        else:
            print("   ❌ Camera open FAILED")
            return False
        
        print("\n" + "="*50)
        print("  ✅ All systems ready!")
        print("="*50)
        return True


def main():
    parser = argparse.ArgumentParser(description='AgriBot Controller')
    parser.add_argument('--test', action='store_true', help='Test connections')
    parser.add_argument('--debug', action='store_true', help='Debug mode')
    args = parser.parse_args()
    
    if args.debug:
        logging.getLogger().setLevel(logging.DEBUG)
    
    print("="*50)
    print("  🚜 AgriBot - Weed Spraying Robot")
    print("  Version 3.0.0")
    print("="*50)
    
    controller = AgribotController()
    
    if args.test:
        success = controller.run_test_mode()
        sys.exit(0 if success else 1)
    
    try:
        controller.connect()
        controller.run_auto_mode()
    except Exception as e:
        logger.error(f"Error: {e}")
        sys.exit(1)
    finally:
        controller.disconnect()


if __name__ == "__main__":
    main()
