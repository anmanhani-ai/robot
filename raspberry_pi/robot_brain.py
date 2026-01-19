"""
Robot Brain - Raspberry Pi 5 Controller
Industrial Grade Logic with Distance-Based Z-Axis Control

ทำหน้าที่เป็น "ผู้จัดการ" คำนวณระยะทางและลำดับขั้นตอนการทำงาน
รองรับการวัดระยะ Z-Axis จากกล้อง

Author: AgriBot Team
"""

import serial
import time
import logging
import json
from pathlib import Path
from typing import Tuple, Optional
from dataclasses import dataclass, field
from enum import Enum

# ==================== LOGGING SETUP ====================
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# ==================== CONFIG FILE ====================
CALIBRATION_FILE = Path(__file__).parent / "calibration.json"


class RobotState(Enum):
    """สถานะของหุ่นยนต์"""
    IDLE = "idle"
    SEARCHING = "searching"         # กำลังหาเป้า
    APPROACHING = "approaching"     # กำลังเข้าหาเป้า
    ALIGNING = "aligning"          # กำลัง align
    EXTENDING = "extending"        # กำลังยืดแขน
    SPRAYING = "spraying"          # กำลังพ่น
    RETRACTING = "retracting"      # กำลังเก็บแขน
    ERROR = "error"


@dataclass
class CalibrationConfig:
    """
    ค่า Calibration สำหรับคำนวณฟิสิกส์
    
    ⚠️ ค่าเหล่านี้จะโหลดจาก calibration.json อัตโนมัติ!
    ใช้ calibration_simple.py เพื่อสร้างไฟล์ calibration
    """
    # === Serial Configuration ===
    serial_port: str = '/dev/ttyUSB0'
    baud_rate: int = 115200
    timeout: int = 10
    
    # === Image Configuration ===
    img_width: int = 640
    img_height: int = 480
    
    # === Z-Axis Calibration (แขนยืด) ===
    arm_speed_cm_per_sec: float = 10.0      # ความเร็วแขน (cm/s)
    pixel_to_cm_z: float = 0.05             # 1 pixel = กี่ cm (แกน Z)
    arm_base_offset_cm: float = 5.0         # ระยะจากแกนกลางถึงจุดเริ่มยืดแขน
    max_arm_extend_time: float = 5.0        # เวลาสูงสุดที่ยืดได้ (วินาที)
    arm_retract_buffer: float = 0.5         # เวลาเพิ่มเติมตอนหด (วินาที)
    
    # === X-Axis Calibration (ล้อ) ===
    wheel_speed_cm_per_sec: float = 20.0    # ความเร็วล้อ (cm/s)  
    pixel_to_cm_x: float = 0.1              # 1 pixel = กี่ cm (แกน X)
    alignment_tolerance_px: int = 30        # ค่าคลาดเคลื่อน align (pixel)
    
    # === Spray Configuration ===
    spray_duration: float = 2.0             # เวลาพ่นเริ่มต้น (วินาที)
    
    @property
    def img_center_x(self) -> int:
        return self.img_width // 2
    
    @property
    def img_center_y(self) -> int:
        return self.img_height // 2
    
    @classmethod
    def load_from_file(cls, filepath: Path = CALIBRATION_FILE) -> 'CalibrationConfig':
        """
        โหลดค่า calibration จากไฟล์ JSON
        ถ้าไม่มีไฟล์จะใช้ค่า default
        """
        config = cls()
        
        if filepath.exists():
            try:
                with open(filepath, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                
                # Map fields from JSON to config
                if 'pixel_to_cm_z' in data:
                    config.pixel_to_cm_z = data['pixel_to_cm_z']
                if 'pixel_to_cm_x' in data:
                    config.pixel_to_cm_x = data['pixel_to_cm_x']
                if 'arm_speed_cm_per_sec' in data:
                    config.arm_speed_cm_per_sec = data['arm_speed_cm_per_sec']
                if 'arm_base_offset_cm' in data:
                    config.arm_base_offset_cm = data['arm_base_offset_cm']
                if 'max_arm_extend_cm' in data:
                    # แปลง max_arm_extend_cm เป็น max_arm_extend_time
                    max_cm = data['max_arm_extend_cm']
                    config.max_arm_extend_time = max_cm / config.arm_speed_cm_per_sec
                if 'alignment_tolerance_px' in data:
                    config.alignment_tolerance_px = data['alignment_tolerance_px']
                if 'default_spray_duration' in data:
                    config.spray_duration = data['default_spray_duration']
                if 'img_width' in data:
                    config.img_width = data['img_width']
                if 'img_height' in data:
                    config.img_height = data['img_height']
                
                logger.info(f"✅ Loaded calibration from {filepath}")
                logger.info(f"   pixel_to_cm_z = {config.pixel_to_cm_z:.6f}")
                logger.info(f"   arm_speed = {config.arm_speed_cm_per_sec:.2f} cm/s")
                logger.info(f"   arm_offset = {config.arm_base_offset_cm:.2f} cm")
                
            except Exception as e:
                logger.warning(f"⚠️ Failed to load calibration: {e}")
                logger.info("   Using default values")
        else:
            logger.warning(f"⚠️ Calibration file not found: {filepath}")
            logger.info("   Run: python calibration_simple.py")
            logger.info("   Using default values")
        
        return config


class RobotBrain:
    """
    Main Controller Class with Distance-Based Z-Axis
    
    คำนวณระยะทางจากพิกัด pixel และควบคุม ESP32
    """
    
    def __init__(self, config: Optional[CalibrationConfig] = None):
        # ถ้าไม่มี config ให้โหลดจากไฟล์ calibration.json อัตโนมัติ
        self.config = config or CalibrationConfig.load_from_file()
        self.ser: Optional[serial.Serial] = None
        self.is_connected = False
        self.state = RobotState.IDLE
        
    # ==================== CONNECTION ====================
    
    def connect(self) -> bool:
        """เชื่อมต่อกับ ESP32"""
        try:
            self.ser = serial.Serial(
                port=self.config.serial_port,
                baudrate=self.config.baud_rate,
                timeout=self.config.timeout
            )
            time.sleep(2)  # รอ ESP32 reset
            
            if self._check_connection():
                self.is_connected = True
                self.state = RobotState.IDLE
                logger.info("✅ Connected to ESP32")
                return True
            else:
                logger.error("❌ ESP32 not responding")
                return False
                
        except serial.SerialException as e:
            logger.error(f"❌ Connection Failed: {e}")
            return False
    
    def disconnect(self):
        """ปิดการเชื่อมต่อ"""
        if self.ser and self.ser.is_open:
            self.ser.close()
            self.is_connected = False
            self.state = RobotState.IDLE
            logger.info("🔌 Disconnected from ESP32")
    
    def _check_connection(self) -> bool:
        """ตรวจสอบการเชื่อมต่อด้วย PING/PONG"""
        try:
            self.ser.reset_input_buffer()
            self.ser.write(b"PING\n")
            response = self.ser.readline().decode().strip()
            return response == "PONG"
        except:
            return False
    
    # ==================== SERIAL COMMUNICATION ====================
    
    def send_cmd(self, command: str, wait_for_done: bool = True) -> bool:
        """
        ส่งคำสั่งไปยัง ESP32 (Synchronous Handshake)
        
        Args:
            command: คำสั่งที่จะส่ง
            wait_for_done: รอ DONE หรือไม่
            
        Returns:
            bool: True ถ้าสำเร็จ
        """
        if not self.is_connected:
            logger.error("❌ Not connected to ESP32")
            return False
        
        try:
            self.ser.reset_input_buffer()
            self.ser.write(f"{command}\n".encode())
            logger.info(f"📤 Sent: {command}")
            
            if wait_for_done:
                start_time = time.time()
                while True:
                    if self.ser.in_waiting > 0:
                        line = self.ser.readline().decode().strip()
                        if line == "DONE":
                            logger.info("📥 ESP32 Task Completed")
                            return True
                        elif line.startswith("ERR"):
                            logger.error(f"❌ ESP32 Error: {line}")
                            return False
                        elif line == "EMERGENCY_STOPPED":
                            logger.warning("⚠️ Emergency Stop Activated")
                            self.state = RobotState.IDLE
                            return True
                    
                    # Timeout
                    if time.time() - start_time > self.config.timeout:
                        logger.error("❌ Response Timeout")
                        return False
                    
                    time.sleep(0.01)
                        
            return True
            
        except Exception as e:
            logger.error(f"❌ Send Error: {e}")
            return False
    
    # ==================== PHYSICS CALCULATIONS ====================
    
    def calculate_z_distance(self, distance_from_center_px: int) -> Tuple[float, float]:
        """
        คำนวณระยะทาง Z-Axis จาก pixel distance
        
        สมการ:
        1. distance_cm = |distance_px| * pixel_to_cm
        2. actual_distance = distance_cm - arm_base_offset (ถ้า > 0)
        3. time = actual_distance / arm_speed
        
        Args:
            distance_from_center_px: ระยะห่างจากแกนกลาง (pixel)
            
        Returns:
            Tuple[float, float]: (เวลา_วินาที, ระยะทาง_cm)
        """
        # 1. แปลง pixel เป็น cm
        distance_cm = abs(distance_from_center_px) * self.config.pixel_to_cm_z
        
        # 2. ลบ offset ของฐานแขน
        actual_distance = max(0, distance_cm - self.config.arm_base_offset_cm)
        
        # 3. แปลงเป็นเวลา (t = d / v)
        time_seconds = actual_distance / self.config.arm_speed_cm_per_sec
        
        # 4. Safety limit
        time_seconds = min(time_seconds, self.config.max_arm_extend_time)
        
        logger.debug(f"Z-Calc: {distance_from_center_px}px → {distance_cm:.1f}cm → {time_seconds:.2f}s")
        
        return time_seconds, actual_distance
    
    def calculate_x_movement(self, distance_from_center_px: int) -> Tuple[str, float]:
        """
        คำนวณทิศทางและเวลาเคลื่อนที่แกน X (ล้อ)
        
        Args:
            distance_from_center_px: ระยะห่างจากแกนกลาง (pixel, บวก=ขวา, ลบ=ซ้าย)
            
        Returns:
            Tuple[str, float]: (ทิศทาง "FW"/"BW", เวลา_วินาที)
        """
        # แปลง pixel เป็น cm
        distance_cm = abs(distance_from_center_px) * self.config.pixel_to_cm_x
        
        # คำนวณเวลา
        time_seconds = distance_cm / self.config.wheel_speed_cm_per_sec
        
        # กำหนดทิศทาง (ปรับตามการติดตั้งกล้อง)
        direction = "FW" if distance_from_center_px > 0 else "BW"
        
        return direction, time_seconds
    
    def is_aligned(self, distance_from_center_px: int) -> bool:
        """ตรวจสอบว่า target อยู่ตรงกลางแล้วหรือยัง"""
        return abs(distance_from_center_px) <= self.config.alignment_tolerance_px
    
    # ==================== ARM OPERATIONS ====================
    
    def extend_arm(self, time_seconds: float) -> bool:
        """ยืดแขน Z-Axis"""
        self.state = RobotState.EXTENDING
        return self.send_cmd(f"ACT:Z_OUT:{time_seconds:.2f}")
    
    def retract_arm(self, time_seconds: float) -> bool:
        """หดแขน Z-Axis (บวก buffer เพิ่ม)"""
        self.state = RobotState.RETRACTING
        retract_time = time_seconds + self.config.arm_retract_buffer
        return self.send_cmd(f"ACT:Z_IN:{retract_time:.2f}")
    
    def lower_spray_head(self) -> bool:
        """หัวฉีดลง Y-Axis"""
        return self.send_cmd("ACT:Y_DOWN")
    
    def raise_spray_head(self) -> bool:
        """หัวฉีดขึ้น Y-Axis"""
        return self.send_cmd("ACT:Y_UP")
    
    def spray(self, duration: Optional[float] = None) -> bool:
        """พ่นยา"""
        self.state = RobotState.SPRAYING
        spray_time = duration or self.config.spray_duration
        return self.send_cmd(f"ACT:SPRAY:{spray_time:.2f}")
    
    # ==================== MOVEMENT OPERATIONS ====================
    
    # Speed constants (PWM 0-255)
    SPEED_MAX = 200       # ความเร็วสูงสุด (ไม่ใช้ 255 เพื่อไม่ให้แรงเกิน)
    SPEED_NORMAL = 150    # ความเร็วปกติ
    SPEED_SLOW = 80       # ความเร็วต่ำ (เมื่อใกล้ target)
    SPEED_CREEP = 50      # ความเร็วคืบ (ใกล้มาก)
    
    def move_forward(self) -> bool:
        """รถเดินหน้า (ความเร็วปกติ)"""
        self.state = RobotState.SEARCHING
        return self.send_cmd("MOVE_FORWARD")
    
    def move_forward_speed(self, speed: int) -> bool:
        """รถเดินหน้าด้วยความเร็วที่กำหนด (0-255)"""
        self.state = RobotState.SEARCHING
        return self.send_cmd(f"MOVE_FW:{speed}")
    
    def move_backward(self) -> bool:
        """รถถอยหลัง (ความเร็วปกติ)"""
        return self.send_cmd("MOVE_BACKWARD")
    
    def move_backward_speed(self, speed: int) -> bool:
        """รถถอยหลังด้วยความเร็วที่กำหนด (0-255)"""
        return self.send_cmd(f"MOVE_BW:{speed}")
    
    def set_speed(self, speed: int) -> bool:
        """ปรับความเร็วขณะวิ่ง (0-255)"""
        return self.send_cmd(f"MOVE_SET_SPEED:{speed}")
    
    def stop_movement(self) -> bool:
        """หยุดรถ"""
        return self.send_cmd("MOVE_STOP")
    
    def calculate_approach_speed(self, distance_from_center_px: int) -> int:
        """
        คำนวณความเร็วตามระยะห่างจาก target
        ยิ่งใกล้ → ยิ่งช้า (Smooth approach)
        
        Args:
            distance_from_center_px: ระยะห่างจากแกนกลาง (pixel)
            
        Returns:
            int: ความเร็ว PWM (0-255)
        """
        dist = abs(distance_from_center_px)
        
        # Zone definitions (ปรับได้ตามต้องการ)
        FAR_ZONE = 200     # ไกลมาก → เร็วเต็มที่
        MID_ZONE = 100     # กลาง → ความเร็วปกติ
        NEAR_ZONE = 50     # ใกล้ → ช้าลง
        ALIGN_ZONE = self.config.alignment_tolerance_px  # ใกล้มาก → หยุด
        
        if dist > FAR_ZONE:
            return self.SPEED_MAX
        elif dist > MID_ZONE:
            # Linear interpolation: MAX → NORMAL
            ratio = (dist - MID_ZONE) / (FAR_ZONE - MID_ZONE)
            return int(self.SPEED_NORMAL + ratio * (self.SPEED_MAX - self.SPEED_NORMAL))
        elif dist > NEAR_ZONE:
            # Linear interpolation: NORMAL → SLOW
            ratio = (dist - NEAR_ZONE) / (MID_ZONE - NEAR_ZONE)
            return int(self.SPEED_SLOW + ratio * (self.SPEED_NORMAL - self.SPEED_SLOW))
        elif dist > ALIGN_ZONE:
            # SLOW → CREEP
            ratio = (dist - ALIGN_ZONE) / (NEAR_ZONE - ALIGN_ZONE)
            return int(self.SPEED_CREEP + ratio * (self.SPEED_SLOW - self.SPEED_CREEP))
        else:
            return 0  # หยุด
    
    def emergency_stop(self) -> bool:
        """หยุดฉุกเฉินทุกระบบ"""
        self.state = RobotState.IDLE
        logger.warning("⚠️ EMERGENCY STOP!")
        return self.send_cmd("STOP_ALL")
    
    # ==================== MISSION EXECUTION ====================
    
    def execute_spray_mission(
        self, 
        distance_from_center_px: int,
        spray_duration: Optional[float] = None
    ) -> bool:
        """
        ปฏิบัติการพ่นยาแบบ Distance-Based
        
        Flow ตาม Step-by-Step:
        1. คำนวณเวลายืดจากระยะ pixel
        2. ยืดแขน Z
        3. หัวฉีดลง Y
        4. พ่นยา
        5. หัวฉีดขึ้น Y
        6. หดแขน Z
        
        Args:
            distance_from_center_px: ระยะห่างจากแกนกลาง (pixel)
            spray_duration: เวลาพ่น (วินาที)
            
        Returns:
            bool: True ถ้าสำเร็จทุกขั้นตอน
        """
        # === คำนวณฟิสิกส์ ===
        t_move, distance_cm = self.calculate_z_distance(distance_from_center_px)
        logger.info(f"🎯 Target: {distance_cm:.1f}cm | Move Time: {t_move:.2f}s")
        
        if t_move <= 0:
            logger.warning("⚠️ Target too close, skipping extension")
            t_move = 0.1  # minimum extend
        
        # === Step 3.1: ยืดแขน Z ===
        self.state = RobotState.EXTENDING
        if not self.extend_arm(t_move):
            logger.error("❌ Failed at Step 3.1: Extend Arm")
            return False
        
        # === Step 3.2: หัวฉีดลง Y ===
        if not self.lower_spray_head():
            logger.error("❌ Failed at Step 3.2: Lower Head")
            return False
        
        # === Step 3.3: พ่นยา ===
        self.state = RobotState.SPRAYING
        if not self.spray(spray_duration):
            logger.error("❌ Failed at Step 3.3: Spray")
            return False
        
        # === Step 4.1: หัวฉีดขึ้น Y (ก่อนหดแขน!) ===
        if not self.raise_spray_head():
            logger.error("❌ Failed at Step 4.1: Raise Head")
            return False
        
        # === Step 4.2: หดแขน Z ===
        self.state = RobotState.RETRACTING
        if not self.retract_arm(t_move):
            logger.error("❌ Failed at Step 4.2: Retract Arm")
            return False
        
        self.state = RobotState.IDLE
        logger.info("✨ Spray Mission Complete!")
        return True
    
    def align_to_target(self, distance_from_center_px: int) -> bool:
        """
        จัดตำแหน่งรถให้ target อยู่ตรงกลาง (X-Axis)
        
        Args:
            distance_from_center_px: ระยะห่างจากแกนกลาง (pixel)
            
        Returns:
            bool: True ถ้า aligned สำเร็จ
        """
        if self.is_aligned(distance_from_center_px):
            logger.info("✓ Already aligned")
            return True
        
        self.state = RobotState.ALIGNING
        direction, move_time = self.calculate_x_movement(distance_from_center_px)
        
        logger.info(f"↔️ Aligning: {direction} for {move_time:.2f}s")
        
        # เคลื่อนที่
        cmd = f"MOVE_X:{direction}"
        if not self.send_cmd(cmd):
            return False
        
        time.sleep(move_time)
        
        # หยุด
        return self.stop_movement()


# ==================== MAIN EXECUTION ====================
if __name__ == "__main__":
    # ทดสอบ
    config = CalibrationConfig()
    bot = RobotBrain(config)
    
    if bot.connect():
        # สมมติ AI ตรวจพบหญ้าห่างจากแกนกลาง 100 pixel
        distance_px = 100
        
        # คำนวณ
        t, d = bot.calculate_z_distance(distance_px)
        print(f"Distance: {distance_px}px → {d:.1f}cm → {t:.2f}s")
        
        # ปฏิบัติการ
        bot.execute_spray_mission(distance_px)
        
        bot.disconnect()
