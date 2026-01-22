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

# Import custom exceptions
try:
    from exceptions import (
        RobotConnectionError, 
        CommandTimeoutError, 
        EmergencyStopError,
        CalibrationError
    )
except ImportError:
    # Fallback if exceptions.py not found
    RobotConnectionError = ConnectionError
    CommandTimeoutError = TimeoutError
    EmergencyStopError = RuntimeError
    CalibrationError = ValueError

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
    arm_speed_cm_per_sec: float = 10.0      # ความเร็วแขน Z (cm/s)
    pixel_to_cm_z: float = 0.05             # 1 pixel = กี่ cm (แกน Z)
    arm_base_offset_cm: float = 5.0         # ระยะจากแกนกลางถึงจุดเริ่มยืดแขน
    z_base_offset_cm: float = 7.0           # ระยะขอบล่างภาพถึงขอบซ้ายรถ (cm)
    max_arm_extend_time: float = 5.0        # เวลาสูงสุดที่ยืดได้ (วินาที)
    arm_retract_buffer: float = 0.5         # เวลาเพิ่มเติมตอนหด (วินาที)
    arm_z_default_cm: float = 0.0           # ตำแหน่ง default Z (cm)
    
    # === Y-Axis Calibration (Motor DC ขึ้น/ลง) ===
    motor_y_speed_cm_per_sec: float = 5.0   # ความเร็วแขน Y (cm/s)
    motor_y_default_cm: float = 0.0         # ตำแหน่ง default Y (cm จากบนสุด)
    motor_y_max_cm: float = 20.0            # ระยะเคลื่อนที่ Y สูงสุด (cm)
    
    # === X-Axis Calibration (ล้อ) ===
    wheel_speed_cm_per_sec: float = 2.17    # ความเร็วล้อ (cm/s) - จาก calibration  
    pixel_to_cm_x: float = 0.05             # 1 pixel = กี่ cm (แกน X)
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
                if 'arm_z_default_cm' in data:
                    config.arm_z_default_cm = data['arm_z_default_cm']
                    
                # Motor Y settings
                if 'motor_y_speed_cm_per_sec' in data:
                    config.motor_y_speed_cm_per_sec = data['motor_y_speed_cm_per_sec']
                if 'motor_y_default_cm' in data:
                    config.motor_y_default_cm = data['motor_y_default_cm']
                if 'motor_y_max_cm' in data:
                    config.motor_y_max_cm = data['motor_y_max_cm']
                    
                if 'alignment_tolerance_px' in data:
                    config.alignment_tolerance_px = data['alignment_tolerance_px']
                if 'default_spray_duration' in data:
                    config.spray_duration = data['default_spray_duration']
                if 'img_width' in data:
                    config.img_width = data['img_width']
                if 'img_height' in data:
                    config.img_height = data['img_height']
                
                # Serial configuration
                if 'serial_port' in data:
                    config.serial_port = data['serial_port']
                if 'baud_rate' in data:
                    config.baud_rate = data['baud_rate']
                if 'timeout' in data:
                    config.timeout = data['timeout']
                
                logger.info(f"✅ Loaded calibration from {filepath}")
                logger.info(f"   Z speed: {config.arm_speed_cm_per_sec:.2f} cm/s, default: {config.arm_z_default_cm:.1f} cm")
                logger.info(f"   Y speed: {config.motor_y_speed_cm_per_sec:.2f} cm/s, default: {config.motor_y_default_cm:.1f} cm")
                
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
        except serial.SerialException as e:
            logger.error(f"Serial error in connection check: {e}")
            return False
        except UnicodeDecodeError as e:
            logger.warning(f"Decode error in connection check: {e}")
            return False
        except Exception as e:
            logger.error(f"Unexpected error in connection check: {e}")
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
    
    # ==================== CAMERA COORDINATE SYSTEM ====================
    # กล้องหันไปทางซ้ายของรถ
    # X ในภาพ = หน้า-หลังของรถ (X+ = หน้ารถ)
    # Y ในภาพ = ระยะไกล-ใกล้จากรถ (ใช้คำนวณ Z-axis)
    # ================================================================
    
    def calculate_coord_x_movement(self, coord_x: int) -> Tuple[str, float]:
        """
        คำนวณการเคลื่อนที่ตาม X ในระบบพิกัดใหม่
        
        Args:
            coord_x: พิกัด X (X+ = ขวา = Forward, X- = ซ้าย = Backward)
            
        Returns:
            Tuple[str, float]: (ทิศทาง 'FW'/'BW', เวลา_วินาที)
        """
        direction = "FW" if coord_x > 0 else "BW"
        distance_cm = abs(coord_x) * self.config.pixel_to_cm_x
        time_seconds = distance_cm / self.config.wheel_speed_cm_per_sec
        
        logger.debug(f"Coord X: {coord_x}px → {direction} {distance_cm:.1f}cm → {time_seconds:.2f}s")
        
        return direction, time_seconds
    
    def calculate_y_from_bottom(self, bottom_y_px: int) -> Tuple[float, float]:
        """
        คำนวณระยะ Y จากขอบล่างของภาพถึงขอบล่างของวัตถุ
        
        Args:
            bottom_y_px: ระยะ pixel จากขอบล่างภาพถึงขอบล่างวัตถุ
            
        Returns:
            Tuple[float, float]: (ระยะ_cm, เวลา_วินาที at 2.17 cm/s)
        """
        distance_cm = bottom_y_px * self.config.pixel_to_cm_z
        time_seconds = distance_cm / self.config.arm_speed_cm_per_sec
        
        logger.debug(f"Y from bottom: {bottom_y_px}px → {distance_cm:.1f}cm → {time_seconds:.2f}s")
        
        return distance_cm, time_seconds
    
    def calculate_x_movement(self, distance_from_center_px: int) -> Tuple[str, float]:
        """
        คำนวณการเคลื่อนที่ X-Axis (legacy - ยังใช้ได้)
        
        Args:
            distance_from_center_px: ระยะห่างจากจุดกลาง (pixel)
            
        Returns:
            Tuple[str, float]: (ทิศทาง 'FW'/'BW', เวลา_วินาที)
        """
        direction = "FW" if distance_from_center_px > 0 else "BW"
        distance_cm = abs(distance_from_center_px) * self.config.pixel_to_cm_x
        time_seconds = distance_cm / self.config.wheel_speed_cm_per_sec
        
        logger.debug(f"X-Calc: {distance_from_center_px}px → {direction} {distance_cm:.1f}cm → {time_seconds:.2f}s")
        
        return direction, time_seconds
    
    def is_aligned(self, distance_from_center_px: int) -> bool:
        """ตรวจสอบว่า target อยู่ตรงกลางแล้วหรือยัง"""
        return abs(distance_from_center_px) <= self.config.alignment_tolerance_px
    
    # ==================== FLOW METHODS (ตาม Flow ที่ออกแบบ) ====================
    
    def calculate_align_to_y_axis(self, target_x: int) -> Tuple[str, float]:
        """
        STEP 2-3: คำนวณการเคลื่อนที่ให้วัตถุอยู่บนแกน Y ของภาพ
        
        Args:
            target_x: ตำแหน่ง X ของวัตถุในภาพ (0-640)
            
        Returns:
            Tuple[str, float]: (direction 'FW'/'BW', time_seconds)
            
        Note:
            - X ในภาพ = หน้า-หลังของรถ (เพราะกล้องหันซ้าย)
            - X > center (320) = วัตถุอยู่หน้ารถ = ต้องเดินหน้า
            - X < center (320) = วัตถุอยู่หลังรถ = ต้องถอยหลัง
        """
        center_x = self.config.img_center_x  # 320
        offset_px = target_x - center_x
        
        direction = "FW" if offset_px > 0 else "BW"
        distance_cm = abs(offset_px) * self.config.pixel_to_cm_x
        time_seconds = distance_cm / self.config.wheel_speed_cm_per_sec
        
        logger.info(f"📏 Align to Y-axis: {target_x}px - {center_x}px = {offset_px}px")
        logger.info(f"   → {direction} {distance_cm:.1f}cm = {time_seconds:.2f}s")
        
        return direction, time_seconds
    
    def calculate_z_from_image_y(self, target_y: int) -> Tuple[float, float]:
        """
        STEP 4: คำนวณระยะยืดแขน Z จากตำแหน่ง Y ในภาพ
        
        Args:
            target_y: ตำแหน่ง Y ของวัตถุในภาพ (0-480)
            
        Returns:
            Tuple[float, float]: (z_distance_cm, z_time_seconds)
            
        Note:
            - Y ในภาพ = ระยะไกล-ใกล้จากรถ (กล้องหันซ้าย)
            - Y = 0 (บนภาพ) = ไกลจากรถ = ยืดแขนมาก
            - Y = 480 (ล่างภาพ) = ใกล้รถ = ยืดแขนน้อย
            - ขอบล่างภาพห่างจากขอบซ้ายรถ 7cm (z_base_offset_cm)
        """
        # ระยะจากขอบล่างภาพ (pixel)
        distance_from_bottom_px = self.config.img_height - target_y
        
        # แปลงเป็น cm + เพิ่ม offset ขอบล่างภาพถึงขอบรถ
        z_from_image_cm = distance_from_bottom_px * self.config.pixel_to_cm_z
        z_base_offset = getattr(self.config, 'z_base_offset_cm', 7.0)
        z_distance_cm = z_from_image_cm + z_base_offset
        
        z_time = z_distance_cm / self.config.arm_speed_cm_per_sec
        
        # Safety limit
        z_time = min(z_time, self.config.max_arm_extend_time)
        
        logger.info(f"📏 Z extension: Y={target_y}px → {distance_from_bottom_px}px from bottom")
        logger.info(f"   → image={z_from_image_cm:.1f}cm + offset={z_base_offset:.1f}cm = {z_distance_cm:.1f}cm")
        logger.info(f"   → time={z_time:.2f}s")
        
        return z_distance_cm, z_time
    
    def get_camera_offset_time(self) -> float:
        """
        STEP 5: คำนวณเวลาที่ต้องเดินหน้าเพื่อชดเชยระยะ กล้อง → แขน
        
        Returns:
            float: เวลาที่ต้องเดินหน้า (วินาที)
        """
        offset_cm = self.config.arm_base_offset_cm  # 8.5 cm
        offset_time = offset_cm / self.config.wheel_speed_cm_per_sec
        
        logger.info(f"📏 Camera offset: {offset_cm}cm = {offset_time:.2f}s")
        
        return offset_time
    
    def move_forward_time(self, time_seconds: float) -> bool:
        """เดินหน้าตามเวลาที่กำหนด แล้วหยุด"""
        if time_seconds <= 0:
            return True
        self.move_forward()
        time.sleep(time_seconds)
        return self.stop_movement()
    
    def move_backward_time(self, time_seconds: float) -> bool:
        """ถอยหลังตามเวลาที่กำหนด แล้วหยุด"""
        if time_seconds <= 0:
            return True
        self.move_backward()
        time.sleep(time_seconds)
        return self.stop_movement()
    
    def is_target_behind_robot(self, target_x: int) -> bool:
        """
        ตรวจสอบว่าวัตถุอยู่หลังรถแล้วหรือยัง (ไม่ต้องทำซ้ำ)
        
        Args:
            target_x: ตำแหน่ง X ของวัตถุในภาพ
            
        Returns:
            bool: True ถ้าอยู่หลังรถแล้ว
        """
        # X < center = อยู่ซ้ายภาพ = อยู่หลังรถ (เพราะกล้องหันซ้าย)
        return target_x < self.config.img_center_x
    
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
    
    # Speed constants (PWM 0-255) - ตรงกับ ESP32 dual_motor.h
    SPEED_MAX = 60        # ความเร็วสูงสุด (สำหรับ auto mode)
    SPEED_NORMAL = 40     # ความเร็วปกติ (ตรงกับ MOTOR_DEFAULT_SPEED)
    SPEED_SLOW = 30       # ความเร็วต่ำ (เมื่อใกล้ target)
    SPEED_CREEP = 25      # ความเร็วคืบ (ใกล้มาก)
    
    def move_forward(self) -> bool:
        """รถเดินหน้า (ความเร็วปกติ)"""
        self.state = RobotState.SEARCHING
        return self.send_cmd("MOVE_FORWARD", wait_for_done=False)
    
    def move_forward_speed(self, speed: int) -> bool:
        """รถเดินหน้าด้วยความเร็วที่กำหนด (0-255)"""
        self.state = RobotState.SEARCHING
        return self.send_cmd(f"MOVE_FW:{speed}", wait_for_done=False)
    
    def move_backward(self) -> bool:
        """รถถอยหลัง (ความเร็วปกติ)"""
        return self.send_cmd("MOVE_BACKWARD", wait_for_done=False)
    
    def move_backward_speed(self, speed: int) -> bool:
        """รถถอยหลังด้วยความเร็วที่กำหนด (0-255)"""
        return self.send_cmd(f"MOVE_BW:{speed}", wait_for_done=False)
    
    def set_speed(self, speed: int) -> bool:
        """ปรับความเร็วขณะวิ่ง (0-255)"""
        return self.send_cmd(f"MOVE_SET_SPEED:{speed}", wait_for_done=False)
    
    def stop_movement(self) -> bool:
        """หยุดรถ"""
        return self.send_cmd("MOVE_STOP")
    
    def emergency_stop(self) -> bool:
        """หยุดฉุกเฉินทุกระบบ"""
        self.state = RobotState.IDLE
        logger.warning("⚠️ EMERGENCY STOP!")
        return self.send_cmd("STOP_ALL")
    
    def calculate_approach_speed(self, distance_from_center_px: int) -> int:
        """
        คำนวณความเร็วตามระยะห่างจาก target
        ยิ่งใกล้ → ยิ่งช้า (Smooth approach)
        """
        dist = abs(distance_from_center_px)
        
        FAR_ZONE = 200
        MID_ZONE = 100
        NEAR_ZONE = 50
        ALIGN_ZONE = self.config.alignment_tolerance_px
        
        if dist > FAR_ZONE:
            return self.SPEED_MAX
        elif dist > MID_ZONE:
            ratio = (dist - MID_ZONE) / (FAR_ZONE - MID_ZONE)
            return int(self.SPEED_NORMAL + ratio * (self.SPEED_MAX - self.SPEED_NORMAL))
        elif dist > NEAR_ZONE:
            ratio = (dist - NEAR_ZONE) / (MID_ZONE - NEAR_ZONE)
            return int(self.SPEED_SLOW + ratio * (self.SPEED_NORMAL - self.SPEED_SLOW))
        elif dist > ALIGN_ZONE:
            ratio = (dist - ALIGN_ZONE) / (NEAR_ZONE - ALIGN_ZONE)
            return int(self.SPEED_CREEP + ratio * (self.SPEED_SLOW - self.SPEED_CREEP))
        else:
            return 0
    
    # ==================== MISSION EXECUTION ====================
    
    def execute_spray_mission(
        self, 
        distance_from_center_px: int,
        spray_duration: Optional[float] = None
    ) -> bool:
        """
        ปฏิบัติการพ่นยาแบบ Distance-Based
        
        Flow:
        1. คำนวณเวลายืดจากระยะ pixel
        2. ยืดแขน Z
        3. หัวฉีดลง Y
        4. พ่นยา
        5. หัวฉีดขึ้น Y
        6. หดแขน Z
        """
        # คำนวณฟิสิกส์
        t_move, distance_cm = self.calculate_z_distance(distance_from_center_px)
        logger.info(f"🎯 Target: {distance_cm:.1f}cm | Move Time: {t_move:.2f}s")
        
        if t_move <= 0:
            logger.warning("⚠️ Target too close, skipping extension")
            t_move = 0.1
        
        # Step 1: ยืดแขน Z
        self.state = RobotState.EXTENDING
        if not self.extend_arm(t_move):
            logger.error("❌ Failed: Extend Arm")
            return False
        
        # Step 2: หัวฉีดลง Y
        if not self.lower_spray_head():
            logger.error("❌ Failed: Lower Head")
            return False
        
        # Step 3: พ่นยา
        self.state = RobotState.SPRAYING
        if not self.spray(spray_duration):
            logger.error("❌ Failed: Spray")
            return False
        
        # Step 4: หัวฉีดขึ้น Y
        if not self.raise_spray_head():
            logger.error("❌ Failed: Raise Head")
            return False
        
        # Step 5: หดแขน Z
        self.state = RobotState.RETRACTING
        if not self.retract_arm(t_move):
            logger.error("❌ Failed: Retract Arm")
            return False
        
        self.state = RobotState.IDLE
        logger.info("✨ Spray Mission Complete!")
        return True

