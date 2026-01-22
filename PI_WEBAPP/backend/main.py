"""
AgriBot API Server
FastAPI backend สำหรับ Dashboard ควบคุมหุ่นยนต์

Features:
- Real-time status API
- Camera streaming (MJPEG)
- Report JSON management
- Mock robot simulator for testing

Run: uvicorn main:app --reload --host 0.0.0.0 --port 8000

Author: AgriBot Team
"""

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse, StreamingResponse
from pydantic import BaseModel
from contextlib import asynccontextmanager
from typing import Optional, List
from datetime import datetime
from pathlib import Path
import asyncio
import json
import csv
import io
import random
import time
import threading

# ==================== CONFIGURATION ====================
DATA_DIR = Path(__file__).parent / "data"
REPORT_FILE = DATA_DIR / "report.json"
STATUS_FILE = DATA_DIR / "status.json"
STATIC_DIR = Path(__file__).parent.parent / "frontend" / "dist"

# Ensure data directory exists
DATA_DIR.mkdir(exist_ok=True)

# ==================== MODELS ====================
class RobotStatus(BaseModel):
    weed_count: int = 0
    chili_count: int = 0
    distance_traveled: float = 0.0
    state: str = "Idle"  # Idle, Moving, Spraying, Stopped
    spray_count: int = 0
    battery: int = 100
    timestamp: str = ""
    # Friendly message for UX
    robot_message: str = "สวัสดีครับ! พร้อมทำงานแล้ว 🌱"
    robot_emoji: str = "😊"
    # Current step tracking for debugging
    current_step: int = 0  # 0=Idle, 1=Searching, 2-3=Aligning, 4=Calculate Z, 5=Offset, 6=Spraying, 7=Reset
    step_description: str = ""  # รายละเอียด step ปัจจุบัน

class LogEntry(BaseModel):
    timestamp: str
    event: str
    x: Optional[float] = None
    y: Optional[float] = None
    details: Optional[str] = None

class CommandRequest(BaseModel):
    command: str
    params: Optional[dict] = None

# ==================== JSON HANDLERS ====================
def read_json(filepath: Path, default=None):
    """อ่านไฟล์ JSON อย่างปลอดภัย"""
    try:
        if filepath.exists():
            with open(filepath, 'r', encoding='utf-8') as f:
                return json.load(f)
    except (json.JSONDecodeError, IOError):
        pass
    return default if default is not None else []

def write_json(filepath: Path, data):
    """เขียนไฟล์ JSON อย่างปลอดภัย"""
    with open(filepath, 'w', encoding='utf-8') as f:
        json.dump(data, f, indent=2, ensure_ascii=False)

def append_log(entry: LogEntry):
    """
    เพิ่ม log entry ใหม่เข้าไปในไฟล์ report.json
    Logic: อ่านค่าเก่า -> เติมค่าใหม่ (Append) -> บันทึก
    """
    logs = read_json(REPORT_FILE, [])
    logs.append(entry.model_dump())  # ใช้ model_dump() แทน dict()
    write_json(REPORT_FILE, logs)
    return len(logs)

# ==================== REAL ROBOT CONTROLLER ====================
import sys
sys.path.insert(0, str(Path(__file__).parent.parent.parent / "raspberry_pi"))

# Try to import real robot modules
try:
    from robot_brain import RobotBrain, CalibrationConfig, RobotState
    from weed_detector import WeedDetector
    ROBOT_AVAILABLE = True
except ImportError as e:
    print(f"⚠️ Cannot import robot modules: {e}")
    ROBOT_AVAILABLE = False


class RealRobotController:
    """
    ควบคุมหุ่นยนต์จริงผ่าน Web API
    เชื่อมต่อ ESP32 + Camera ตอน server start
    """
    
    def __init__(self):
        self.status = RobotStatus()
        self.is_running = False
        self.thread: Optional[threading.Thread] = None
        
        # Device status
        self.esp32_connected = False
        self.camera_connected = False
        self.error_message = ""
        
        # Real robot components
        self.brain: Optional[RobotBrain] = None
        self.detector: Optional[WeedDetector] = None
        self.config: Optional[CalibrationConfig] = None
        
        # Initialize status file
        self._save_status()
    
    def initialize_devices(self) -> bool:
        """เชื่อมต่อ ESP32 + Camera ตอน server start (ทั้งสองอุปกรณ์แยกกัน)"""
        if not ROBOT_AVAILABLE:
            self.error_message = "โมดูลหุ่นยนต์ไม่พร้อมใช้งาน กรุณาตรวจสอบการติดตั้ง"
            print(f"❌ {self.error_message}")
            return False
        
        try:
            # Load calibration
            self.config = CalibrationConfig.load_from_file()
            print("✅ Loaded calibration config")
            
            # Connect ESP32 (ไม่บังคับ - กล้องทำงานได้แม้ไม่มี ESP32)
            self.brain = RobotBrain(self.config)
            if self.brain.connect():
                self.esp32_connected = True
                print("✅ ESP32 connected")
            else:
                self.esp32_connected = False
                print("⚠️ ESP32 ไม่พร้อมใช้งาน (กล้องยังทำงานได้)")
            
            # Initialize detector with camera (ทำงานแยกจาก ESP32)
            self.detector = WeedDetector(
                camera_id=0,
                frame_width=self.config.img_width,
                frame_height=self.config.img_height
            )
            
            if self.detector.start_camera():
                self.camera_connected = True
                print("✅ Camera connected")
            else:
                self.camera_connected = False
                print("⚠️ กล้องไม่พร้อมใช้งาน")
            
            # สรุปสถานะ
            if not self.esp32_connected and not self.camera_connected:
                self.error_message = "ESP32 และกล้องไม่พร้อมใช้งาน"
                return False
            elif not self.esp32_connected:
                self.error_message = "ESP32 ไม่พร้อม แต่กล้องพร้อมใช้งาน"
            elif not self.camera_connected:
                self.error_message = "กล้องไม่พร้อม แต่ ESP32 พร้อมใช้งาน"
            else:
                self.error_message = ""
            
            return self.esp32_connected or self.camera_connected
            
        except Exception as e:
            self.error_message = f"เกิดข้อผิดพลาด: {str(e)}"
            print(f"❌ {self.error_message}")
            return False
    
    def _save_status(self):
        """บันทึก status ลงไฟล์"""
        self.status.timestamp = datetime.now().isoformat()
        write_json(STATUS_FILE, self.status.model_dump())
    
    def say(self, message_type: str, custom_msg: str = None):
        """ตั้งค่าข้อความที่หุ่นยนต์พูดแบบ friendly"""
        messages = {
            "ready": ("สวัสดีครับ! พร้อมทำงานแล้ว 🌱", "😊"),
            "waiting": ("รอคำสั่งอยู่นะครับ...", "🤖"),
            "moving": ("กำลังเดินลาดตระเวนครับ 🚶", "🔍"),
            "searching": ("กำลังมองหาวัชพืช... 👀", "🔎"),
            "found_weed": ("เจอวัชพืชแล้ว! 🎯", "😤"),
            "no_weed": ("ไม่เจอวัชพืชครับ ปลอดภัย! ✨", "😌"),
            "preparing_spray": ("กำลังเตรียมพ่นยา...", "💪"),
            "spraying": ("กำลังพ่นยากำจัดวัชพืช 💦", "🔫"),
            "spray_done": ("พ่นยาเสร็จแล้วครับ! ✅", "👍"),
            "arm_extend": ("กำลังยืดแขนออก...", "🦾"),
            "arm_retract": ("กำลังหดแขนกลับ", "🦾"),
            "obstacle": ("เจอสิ่งกีดขวาง! กำลังหลบ... 🚧", "😰"),
            "clear": ("ทางโล่งแล้ว ไปต่อครับ!", "😊"),
            "stopping": ("กำลังหยุด...", "✋"),
            "stopped": ("หยุดแล้วครับ", "🛑"),
            "error": ("อุ๊ย! มีปัญหานิดหน่อย 😅", "❌"),
            "mission_complete": ("เสร็จภารกิจแล้วครับ! 🎉", "🏆"),
            "thinking": ("กำลังคิดอยู่...", "🤔"),
            "analyzing": ("กำลังวิเคราะห์ภาพ...", "🧠"),
        }
        
        if custom_msg:
            self.status.robot_message = custom_msg
            self.status.robot_emoji = "💬"
        elif message_type in messages:
            self.status.robot_message, self.status.robot_emoji = messages[message_type]
        
        self._save_status()
    
    def set_step(self, step: int, description: str):
        """
        อัพเดท step ปัจจุบันสำหรับแสดงบน Web Dashboard
        
        Steps:
        0 = Idle
        1 = Searching (เดินหน้า+ตรวจจับ)
        2 = Target Detected (พบวัชพืช หยุดรถ)
        3 = Aligning (เคลื่อนที่ให้วัตถุอยู่แกน Y)
        4 = Calculate Z (คำนวณระยะยืดแขน)
        5 = Compensate Offset (ชดเชย 8.5cm)
        6 = Spraying (ยืด Z → ลง Y → ฉีด)
        7 = Reset (ขึ้น Y → หด Z)
        8 = Continue (เดินหน้าต่อ)
        """
        self.status.current_step = step
        self.status.step_description = description
        print(f"📍 STEP {step}: {description}")
        self._save_status()
    
    def start_mission(self, single_shot: bool = False) -> dict:
        """เริ่ม Mission"""
        if not self.esp32_connected or not self.camera_connected:
            return {
                "success": False, 
                "error": self.error_message or "อุปกรณ์ไม่พร้อมใช้งาน"
            }
        
        if self.is_running:
            return {"success": False, "error": "Mission กำลังทำงานอยู่"}
        
        # Stop background detection to avoid camera conflict
        global _detection_running
        _detection_running = False
        time.sleep(0.2)  # Wait for detection thread to stop
        
        self.is_running = True
        self.status.state = "Moving"
        self.say("moving")
        
        # Log start
        append_log(LogEntry(
            timestamp=datetime.now().isoformat(),
            event="MISSION_START",
            details=f"Mission started ({'Single Shot' if single_shot else 'Continuous'})"
        ))
        
        # Start auto mode thread with single_shot parameter
        self.thread = threading.Thread(
            target=self._auto_mode_loop, 
            args=(single_shot,),
            daemon=True
        )
        self.thread.start()
        
        return {"success": True}
    
    def stop_mission(self) -> dict:
        """หยุด Mission ฉุกเฉิน"""
        self.is_running = False
        self.status.state = "Stopped"
        
        # Stop robot
        if self.brain:
            self.brain.stop_movement()
        
        self.say("stopped")
        
        append_log(LogEntry(
            timestamp=datetime.now().isoformat(),
            event="EMERGENCY_STOP",
            details="Mission stopped by user"
        ))
        
        # Restart background detection
        _start_detection_thread()
        
        return {"success": True}
    
    def reset(self) -> dict:
        """Reset ทุกอย่าง"""
        self.is_running = False
        self.status = RobotStatus()
        self.say("ready")
        
        # Clear report
        write_json(REPORT_FILE, [])
        
        return {"success": True}
    
    def _auto_mode_loop(self, single_shot: bool = False):
        """
        Auto mode loop - ใช้ Flow ที่ออกแบบใหม่
        
        Flow:
        0. เดินหน้า + ตรวจจับ
        1. พบวัชพืช → หยุด
        2-3. Align ให้วัตถุอยู่บนแกน Y
        4. คำนวณระยะยืดแขน Z
        5. ชดเชย offset กล้อง-แขน (8.5cm)
        6. ยืด Z → ลง Y → ฉีด
        7. ขึ้น Y → หด Z → reset
        8. เดินหน้าต่อ
        """
        if not self.brain or not self.detector:
            print("❌ Brain or Detector not available")
            return
        
        print("🚀 Auto mode started (NEW FLOW)")
        
        # ใช้ค่าจาก config
        IMG_CENTER_X = self.config.img_center_x if self.config else 320
        SPRAY_DURATION = 3.0
        
        # ป้องกันการ re-detect ระหว่าง processing
        is_processing = False
        last_target_x = None
        last_target_y = None
        MIN_TARGET_DISTANCE = 50  # pixels - ระยะห่างขั้นต่ำที่ถือว่าเป็น target ใหม่
        
        self.set_step(0, "เริ่มต้นระบบ")
        
        while self.is_running:
            try:
                # ================================================
                # STEP 1: เดินหน้า + ตรวจจับ (เฉพาะเมื่อไม่ได้ processing)
                # ================================================
                if is_processing:
                    print("⚠️ Still processing, skip detection")
                    time.sleep(0.1)
                    continue
                
                self.set_step(1, "กำลังเดินหน้าและตรวจจับวัชพืช")
                self.brain.move_forward()
                
                target_found = False
                target = None
                
                while self.is_running and not target_found and not is_processing:
                    frame = self.detector.capture_frame()
                    if frame is None:
                        time.sleep(0.05)
                        continue
                    
                    all_detections = self.detector.detect(frame)
                    
                    # กรองเฉพาะ target ที่อยู่หน้ารถ (X >= CENTER)
                    valid_targets = [d for d in all_detections 
                                    if d.is_target and d.x >= IMG_CENTER_X]
                    
                    # กรองออก target ที่เพิ่งทำไปแล้ว (ระยะใกล้กว่า MIN_TARGET_DISTANCE)
                    if last_target_x is not None and last_target_y is not None:
                        valid_targets = [
                            d for d in valid_targets 
                            if abs(d.x - last_target_x) > MIN_TARGET_DISTANCE or 
                               abs(d.y - last_target_y) > MIN_TARGET_DISTANCE
                        ]
                    
                    if valid_targets:
                        target = min(valid_targets, key=lambda d: abs(d.x - IMG_CENTER_X))
                        target_found = True
                        # ตั้ง flag processing ทันที!
                        is_processing = True
                        print(f"🎯 Target found at ({target.x}, {target.y}) - LOCKING")
                    else:
                        time.sleep(0.1)
                
                if not self.is_running:
                    break
                
                if target is None:
                    is_processing = False
                    continue
                
                # บันทึกตำแหน่ง target ปัจจุบัน
                last_target_x = target.x
                last_target_y = target.y
                
                # ================================================
                # STEP 2: พบวัชพืช → หยุดรถ
                # ================================================
                self.set_step(2, f"พบ {target.class_name}! หยุดรถ")
                self.brain.stop_movement()
                self.status.weed_count += 1
                
                # Log detection
                append_log(LogEntry(
                    timestamp=datetime.now().isoformat(),
                    event="TARGET_DETECTED",
                    x=target.x,
                    y=target.y,
                    details=f"Detected: {target.class_name}"
                ))
                
                time.sleep(0.5)  # brief pause
                
                # ================================================
                # STEP 3: Align ให้วัตถุอยู่บนแกน Y
                # ================================================
                try:
                    print(f">>> STEP 3: Calculating align for target.x={target.x}")
                    direction, align_time = self.brain.calculate_align_to_y_axis(target.x)
                    self.set_step(3, f"Align: {direction} {align_time:.2f}s")
                    print(f">>> STEP 3: direction={direction}, align_time={align_time:.2f}s")
                    
                    if align_time > 0.05:
                        if direction == "FW":
                            print(f">>> STEP 3: Moving forward {align_time:.2f}s")
                            self.brain.move_forward_time(align_time)
                        else:
                            print(f">>> STEP 3: Moving backward {align_time:.2f}s")
                            self.brain.move_backward_time(align_time)
                    print(">>> STEP 3: Done")
                except Exception as e:
                    print(f"❌ STEP 3 Error: {e}")
                    import traceback
                    traceback.print_exc()
                
                # ================================================
                # STEP 4: คำนวณระยะยืดแขน Z
                # ================================================
                try:
                    print(f">>> STEP 4: Calculating Z for target.y={target.y}")
                    z_distance_cm, z_time = self.brain.calculate_z_from_image_y(target.y)
                    self.set_step(4, f"คำนวณ Z: {z_distance_cm:.1f}cm = {z_time:.2f}s")
                    print(f">>> STEP 4: z_distance={z_distance_cm:.1f}cm, z_time={z_time:.2f}s")
                except Exception as e:
                    print(f"❌ STEP 4 Error: {e}")
                    z_distance_cm, z_time = 5.0, 2.3  # fallback
                
                # ================================================
                # STEP 5: ชดเชย offset กล้อง → แขน (8.5cm)
                # ================================================
                try:
                    print(">>> STEP 5: Getting camera offset time")
                    offset_time = self.brain.get_camera_offset_time()
                    self.set_step(5, f"ชดเชย offset: เดินหน้า {offset_time:.2f}s")
                    print(f">>> STEP 5: offset_time={offset_time:.2f}s")
                    self.brain.move_forward_time(offset_time)
                    print(">>> STEP 5: Done")
                except Exception as e:
                    print(f"❌ STEP 5 Error: {e}")
                    import traceback
                    traceback.print_exc()
                
                # ================================================
                # STEP 6: ปฏิบัติการฉีดพ่น
                # ================================================
                try:
                    print(f">>> STEP 6: Extending arm for {z_time:.2f}s")
                    self.set_step(6, "ยืดแขน Z...")
                    self.brain.extend_arm(z_time)
                    
                    print(">>> STEP 6: Lowering spray head")
                    self.set_step(6, "ลงแขน Y...")
                    self.brain.lower_spray_head()
                    
                    print(f">>> STEP 6: Spraying for {SPRAY_DURATION}s")
                    self.set_step(6, f"กำลังฉีดพ่น {SPRAY_DURATION}s...")
                    self.brain.spray(SPRAY_DURATION)
                    print(">>> STEP 6: Done")
                except Exception as e:
                    print(f"❌ STEP 6 Error: {e}")
                    import traceback
                    traceback.print_exc()
                
                # ================================================
                # STEP 7: Reset - กลับสู่ตำแหน่งเดิม
                # ================================================
                try:
                    print(">>> STEP 7: Raising spray head")
                    self.set_step(7, "ขึ้นแขน Y...")
                    self.brain.raise_spray_head()
                    
                    print(f">>> STEP 7: Retracting arm for {z_time:.2f}s")
                    self.set_step(7, "หดแขน Z...")
                    self.brain.retract_arm(z_time)
                    print(">>> STEP 7: Done")
                except Exception as e:
                    print(f"❌ STEP 7 Error: {e}")
                    import traceback
                    traceback.print_exc()
                
                # Update spray count
                self.status.spray_count += 1
                print(f">>> Spray count: {self.status.spray_count}")
                
                # Log completion
                append_log(LogEntry(
                    timestamp=datetime.now().isoformat(),
                    event="TARGET_SPRAYED",
                    x=target.x,
                    y=target.y,
                    details=f"Spray #{self.status.spray_count} - {target.class_name}"
                ))
                
                # Single shot mode?
                if single_shot:
                    self.set_step(8, "Single Shot - เสร็จสิ้น")
                    self.is_running = False
                    break
                
                # ================================================
                # STEP 8: เดินหน้าต่อ
                # ================================================
                self.set_step(8, "เสร็จสิ้น! กำลังหาเป้าหมายถัดไป...")
                print(">>> STEP 8: Continuing to next target")
                
                # ปลดล็อค detection สำหรับ target ถัดไป
                is_processing = False
                print(">>> Processing UNLOCKED - ready for next target")
                time.sleep(1.0)
                
            except Exception as e:
                print(f"❌ Auto mode error: {e}")
                import traceback
                traceback.print_exc()
                self.set_step(0, f"Error: {str(e)}")
                is_processing = False  # ปลดล็อคกรณี error
                time.sleep(0.5)
        
        # Stopped
        self.set_step(0, "หยุดทำงาน")
        self.brain.stop_movement()
        print("🛑 Auto mode stopped")
    
    def get_status(self) -> dict:
        """ดึง status ปัจจุบัน"""
        self.status.timestamp = datetime.now().isoformat()
        return {
            **self.status.model_dump(),
            "esp32_connected": self.esp32_connected,
            "camera_connected": self.camera_connected,
            "error_message": self.error_message,
            "devices_ready": self.esp32_connected and self.camera_connected
        }
    
    def get_camera_frame(self):
        """Get current camera frame for streaming"""
        if self.detector:
            return self.detector.capture_frame()
        return None
    
    def shutdown(self):
        """Cleanup on server shutdown"""
        self.is_running = False
        if self.detector:
            self.detector.stop_camera()
        if self.brain:
            self.brain.disconnect()


# Global robot controller
robot = RealRobotController()


# ==================== LIFESPAN ====================
@asynccontextmanager
async def lifespan(app: FastAPI):
    """Lifespan event handler (แทน on_event deprecated)"""
    # Startup
    print("🚀 AgriBot API Server Started")
    print(f"📁 Data directory: {DATA_DIR}")
    print(f"📁 Static directory: {STATIC_DIR}")
    
    # Initialize files if not exist
    if not REPORT_FILE.exists():
        write_json(REPORT_FILE, [])
    if not STATUS_FILE.exists():
        write_json(STATUS_FILE, RobotStatus().model_dump())
    
    # Initialize robot devices (ESP32 + Camera)
    print("🔌 Initializing robot devices...")
    if robot.initialize_devices():
        print("✅ Robot devices ready")
    else:
        print(f"⚠️ Robot devices not ready: {robot.error_message}")
    
    yield
    
    # Shutdown
    print("👋 Server shutting down...")
    robot.shutdown()


# ==================== FASTAPI APP ====================
app = FastAPI(
    title="AgriBot API", 
    version="1.0.0",
    lifespan=lifespan
)

# CORS for development
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# ==================== API ENDPOINTS ====================

@app.get("/api/status")
async def get_status():
    """
    GET /api/status
    ดึงสถานะปัจจุบันของหุ่นยนต์
    Frontend เรียกทุก 1 วินาที (polling)
    """
    return robot.get_status()


@app.post("/api/command")
async def send_command(request: CommandRequest):
    """
    POST /api/command
    ส่งคำสั่งควบคุมหุ่นยนต์
    
    Commands:
    - start: เริ่ม mission
    - stop: หยุดฉุกเฉิน
    - reset: reset ทุกอย่าง
    """
    cmd = request.command.lower()
    
    if cmd == "start":
        result = robot.start_mission(single_shot=False)
        if result.get("success"):
            return {"success": True, "message": "Mission started (Continuous)"}
        else:
            return {"success": False, "message": result.get("error", "ไม่สามารถเริ่ม Mission ได้")}
            
    elif cmd == "start_single":
        result = robot.start_mission(single_shot=True)
        if result.get("success"):
            return {"success": True, "message": "Mission started (Single Shot)"}
        else:
            return {"success": False, "message": result.get("error", "ไม่สามารถเริ่ม Mission ได้")}
    
    elif cmd == "stop":
        result = robot.stop_mission()
        return {"success": True, "message": "Mission stopped"}
    
    elif cmd == "reset":
        result = robot.reset()
        return {"success": True, "message": "System reset"}
    
    elif cmd == "arm_test":
        # ทดสอบแขนกล: ใช้ตำแหน่งจริงจาก detection
        if not robot.brain:
            return {"success": False, "message": "Brain not initialized"}
        if not robot.detector:
            return {"success": False, "message": "Detector not initialized"}
        
        try:
            # 1. Capture และ detect
            frame = robot.detector.capture_frame()
            if frame is None:
                return {"success": False, "message": "❌ Cannot capture frame"}
            
            all_detections = robot.detector.detect(frame)
            target = robot.detector.get_nearest_target(all_detections)
            
            if target is None:
                return {"success": False, "message": "❌ No target detected! วางวัตถุหน้ากล้องก่อน"}
            
            # 2. คำนวณระยะ X (ระยะยืดแขน)
            dist_x = abs(target.distance_from_center_x)
            dist_y = target.distance_from_center_y
            
            # 3. คำนวณเวลายืดแขน
            t_move, distance_cm = robot.brain.calculate_z_distance(dist_x)
            
            # 4. Log ข้อมูล
            info_msg = f"🎯 Target: {target.class_name}\n"
            info_msg += f"📍 Position: X={target.x}, Y={target.y}\n"
            info_msg += f"📏 Distance: X={dist_x}px, Y={dist_y}px\n"
            info_msg += f"⏱️ Arm extend: {distance_cm:.1f}cm = {t_move:.2f}s"
            print(info_msg)
            
            # 5. Execute spray mission
            success = robot.brain.execute_spray_mission(dist_x)
            
            if success:
                return {
                    "success": True, 
                    "message": f"✅ Arm test completed!\n{info_msg}",
                    "target": target.class_name,
                    "dist_x": dist_x,
                    "dist_y": dist_y,
                    "arm_distance_cm": round(distance_cm, 1),
                    "arm_time_sec": round(t_move, 2)
                }
            else:
                return {"success": False, "message": f"❌ Arm test failed\n{info_msg}"}
        except Exception as e:
            import traceback
            traceback.print_exc()
            return {"success": False, "message": f"Error: {str(e)}"}
    
    elif cmd == "arm_extend":
        # ยืดแขน - ใช้ duration จาก params (default 1.0 วินาที)
        duration = 1.0
        if request.params and "duration" in request.params:
            duration = float(request.params["duration"])
        if robot.brain:
            robot.brain.extend_arm(duration)
            return {"success": True, "message": f"Arm extended for {duration}s"}
        return {"success": False, "message": "Brain not ready"}
    
    elif cmd == "arm_retract":
        # หดแขน - ใช้ duration จาก params (default 1.0 วินาที)
        duration = 1.0
        if request.params and "duration" in request.params:
            duration = float(request.params["duration"])
        if robot.brain:
            robot.brain.retract_arm(duration)
            return {"success": True, "message": f"Arm retracted for {duration}s"}
        return {"success": False, "message": "Brain not ready"}
    
    elif cmd == "head_down":
        # หัวฉีดลง
        if robot.brain:
            robot.brain.lower_spray_head()
            return {"success": True, "message": "Head lowered"}
        return {"success": False, "message": "Brain not ready"}
    
    elif cmd == "head_up":
        # หัวฉีดขึ้น
        if robot.brain:
            robot.brain.raise_spray_head()
            return {"success": True, "message": "Head raised"}
        return {"success": False, "message": "Brain not ready"}
    
    elif cmd == "spray":
        # พ่นน้ำ 1 วินาที
        if robot.brain:
            robot.brain.spray(1.0)
            return {"success": True, "message": "Spray done"}
        return {"success": False, "message": "Brain not ready"}
    
    else:
        raise HTTPException(status_code=400, detail=f"Unknown command: {cmd}")


@app.get("/api/download")
async def download_report():
    """
    GET /api/download
    แปลง report.json เป็น CSV และส่งให้ download
    
    Logic:
    1. อ่าน report.json
    2. แปลงเป็น CSV
    3. ส่งเป็นไฟล์ download
    """
    logs = read_json(REPORT_FILE, [])
    
    if not logs:
        raise HTTPException(status_code=404, detail="No data to download")
    
    # สร้าง CSV ใน memory
    output = io.StringIO()
    writer = csv.DictWriter(output, fieldnames=['timestamp', 'event', 'x', 'y', 'details'])
    writer.writeheader()
    
    for log in logs:
        writer.writerow({
            'timestamp': log.get('timestamp', ''),
            'event': log.get('event', ''),
            'x': log.get('x', ''),
            'y': log.get('y', ''),
            'details': log.get('details', '')
        })
    
    # ส่งเป็นไฟล์
    output.seek(0)
    filename = f"agribot_report_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv"
    
    return StreamingResponse(
        iter([output.getvalue()]),
        media_type="text/csv",
        headers={"Content-Disposition": f"attachment; filename={filename}"}
    )


@app.post("/api/reset")
async def reset_report():
    """
    POST /api/reset
    ลบข้อมูลใน report.json เพื่อเตรียมสำหรับ mission ใหม่
    
    Logic:
    1. Truncate ไฟล์ report.json เป็น []
    2. Reset status
    """
    write_json(REPORT_FILE, [])
    robot.reset()
    
    return {"success": True, "message": "Report cleared, ready for new mission"}


@app.get("/api/logs")
async def get_logs(limit: int = 50):
    """
    GET /api/logs
    ดึง log entries ล่าสุด
    """
    logs = read_json(REPORT_FILE, [])
    return logs[-limit:]  # ส่ง log ล่าสุด


# ==================== SETTINGS API ====================
CALIBRATION_FILE = Path(__file__).parent.parent.parent / "raspberry_pi" / "calibration.json"

class ArmSettings(BaseModel):
    # === ARM CONFIGURATION ===
    arm_links: list = [15.5, 0, 0]
    joint_z_min: float = 0
    joint_z_max: float = 15.5
    joint_y_min: float = -90
    joint_y_max: float = 90
    
    # === SPEED & MOTION CONTROL ===
    max_speed_percent: int = 60
    acceleration: int = 30
    deceleration: int = 30
    position_tolerance_cm: float = 0.5
    angle_tolerance_deg: float = 2
    retry_attempts: int = 3
    
    # Legacy arm Z settings
    max_arm_extend_cm: float = 15.5
    arm_base_offset_cm: float = 9.0
    arm_speed_cm_per_sec: float = 2.21
    arm_z_default_cm: float = 0.0
    
    # Legacy arm Y settings
    motor_y_speed_cm_per_sec: float = 5.0
    motor_y_default_cm: float = 0.0
    motor_y_max_cm: float = 20.0
    
    # === CAMERA CALIBRATION ===
    camera_height_cm: float = 50.0
    camera_angle_deg: float = 45.0
    camera_fov_deg: float = 60.0
    pixel_to_cm_ratio: float = 0.034
    workspace_x_min: float = -30
    workspace_x_max: float = 30
    workspace_y_min: float = -30
    workspace_y_max: float = 30
    workspace_z_min: float = 0
    workspace_z_max: float = 20
    
    # === MOTION PLANNING ===
    motion_type: str = "direct"
    approach_height_cm: float = 5.0
    approach_speed_percent: int = 50
    retreat_height_cm: float = 5.0
    
    # === CONTROL MODES ===
    operation_mode: str = "auto"
    control_method: str = "inverse_kinematics"
    
    # === SAFETY SETTINGS ===
    emergency_stop_enabled: bool = True
    collision_detection_enabled: bool = False
    timeout_seconds: int = 30
    on_target_lost: str = "stop"
    on_unreachable: str = "alert"
    
    # === PID TUNING ===
    pid_kp: float = 2.0
    pid_ki: float = 0.1
    pid_kd: float = 0.05
    moving_average_window: int = 5
    kalman_filter_enabled: bool = False
    
    # === SPRAY SETTINGS ===
    default_spray_duration: float = 1.0


@app.get("/api/settings")
async def get_settings():
    """
    GET /api/settings
    ดึงค่าตั้งค่าแขนกลจาก calibration.json
    """
    defaults = ArmSettings()
    try:
        if CALIBRATION_FILE.exists():
            with open(CALIBRATION_FILE, 'r') as f:
                data = json.load(f)
            
            # Return all settings with defaults
            return {
                # ARM CONFIGURATION
                "arm_links": data.get("arm_links", defaults.arm_links),
                "joint_z_min": data.get("joint_z_min", defaults.joint_z_min),
                "joint_z_max": data.get("joint_z_max", defaults.joint_z_max),
                "joint_y_min": data.get("joint_y_min", defaults.joint_y_min),
                "joint_y_max": data.get("joint_y_max", defaults.joint_y_max),
                
                # SPEED & MOTION CONTROL
                "max_speed_percent": data.get("max_speed_percent", defaults.max_speed_percent),
                "acceleration": data.get("acceleration", defaults.acceleration),
                "deceleration": data.get("deceleration", defaults.deceleration),
                "position_tolerance_cm": data.get("position_tolerance_cm", defaults.position_tolerance_cm),
                "angle_tolerance_deg": data.get("angle_tolerance_deg", defaults.angle_tolerance_deg),
                "retry_attempts": data.get("retry_attempts", defaults.retry_attempts),
                
                # Legacy arm Z
                "max_arm_extend_cm": data.get("max_arm_extend_cm", defaults.max_arm_extend_cm),
                "arm_base_offset_cm": data.get("arm_base_offset_cm", defaults.arm_base_offset_cm),
                "arm_speed_cm_per_sec": data.get("arm_speed_cm_per_sec", defaults.arm_speed_cm_per_sec),
                "arm_z_default_cm": data.get("arm_z_default_cm", defaults.arm_z_default_cm),
                
                # Legacy arm Y
                "motor_y_speed_cm_per_sec": data.get("motor_y_speed_cm_per_sec", defaults.motor_y_speed_cm_per_sec),
                "motor_y_default_cm": data.get("motor_y_default_cm", defaults.motor_y_default_cm),
                "motor_y_max_cm": data.get("motor_y_max_cm", defaults.motor_y_max_cm),
                
                # CAMERA CALIBRATION
                "camera_height_cm": data.get("camera_height_cm", defaults.camera_height_cm),
                "camera_angle_deg": data.get("camera_angle_deg", defaults.camera_angle_deg),
                "camera_fov_deg": data.get("camera_fov_deg", defaults.camera_fov_deg),
                "pixel_to_cm_ratio": data.get("pixel_to_cm_ratio", defaults.pixel_to_cm_ratio),
                "workspace_x_min": data.get("workspace_x_min", defaults.workspace_x_min),
                "workspace_x_max": data.get("workspace_x_max", defaults.workspace_x_max),
                "workspace_y_min": data.get("workspace_y_min", defaults.workspace_y_min),
                "workspace_y_max": data.get("workspace_y_max", defaults.workspace_y_max),
                "workspace_z_min": data.get("workspace_z_min", defaults.workspace_z_min),
                "workspace_z_max": data.get("workspace_z_max", defaults.workspace_z_max),
                
                # MOTION PLANNING
                "motion_type": data.get("motion_type", defaults.motion_type),
                "approach_height_cm": data.get("approach_height_cm", defaults.approach_height_cm),
                "approach_speed_percent": data.get("approach_speed_percent", defaults.approach_speed_percent),
                "retreat_height_cm": data.get("retreat_height_cm", defaults.retreat_height_cm),
                
                # CONTROL MODES
                "operation_mode": data.get("operation_mode", defaults.operation_mode),
                "control_method": data.get("control_method", defaults.control_method),
                
                # SAFETY SETTINGS
                "emergency_stop_enabled": data.get("emergency_stop_enabled", defaults.emergency_stop_enabled),
                "collision_detection_enabled": data.get("collision_detection_enabled", defaults.collision_detection_enabled),
                "timeout_seconds": data.get("timeout_seconds", defaults.timeout_seconds),
                "on_target_lost": data.get("on_target_lost", defaults.on_target_lost),
                "on_unreachable": data.get("on_unreachable", defaults.on_unreachable),
                
                # PID TUNING
                "pid_kp": data.get("pid_kp", defaults.pid_kp),
                "pid_ki": data.get("pid_ki", defaults.pid_ki),
                "pid_kd": data.get("pid_kd", defaults.pid_kd),
                "moving_average_window": data.get("moving_average_window", defaults.moving_average_window),
                "kalman_filter_enabled": data.get("kalman_filter_enabled", defaults.kalman_filter_enabled),
                
                # SPRAY SETTINGS
                "default_spray_duration": data.get("default_spray_duration", defaults.default_spray_duration),
            }
    except Exception as e:
        print(f"Error reading settings: {e}")
    
    # Return defaults
    return defaults.model_dump()


@app.post("/api/settings")
async def save_settings(settings: ArmSettings):
    """
    POST /api/settings
    บันทึกค่าตั้งค่าแขนกลลง calibration.json
    """
    try:
        # Read existing calibration
        data = {}
        if CALIBRATION_FILE.exists():
            with open(CALIBRATION_FILE, 'r') as f:
                data = json.load(f)
        
        # === Update all settings ===
        
        # ARM CONFIGURATION
        data["arm_links"] = settings.arm_links
        data["joint_z_min"] = settings.joint_z_min
        data["joint_z_max"] = settings.joint_z_max
        data["joint_y_min"] = settings.joint_y_min
        data["joint_y_max"] = settings.joint_y_max
        
        # SPEED & MOTION CONTROL
        data["max_speed_percent"] = settings.max_speed_percent
        data["acceleration"] = settings.acceleration
        data["deceleration"] = settings.deceleration
        data["position_tolerance_cm"] = settings.position_tolerance_cm
        data["angle_tolerance_deg"] = settings.angle_tolerance_deg
        data["retry_attempts"] = settings.retry_attempts
        
        # Legacy arm Z
        data["max_arm_extend_cm"] = settings.max_arm_extend_cm
        data["arm_base_offset_cm"] = settings.arm_base_offset_cm
        data["arm_speed_cm_per_sec"] = settings.arm_speed_cm_per_sec
        data["arm_z_default_cm"] = settings.arm_z_default_cm
        
        # Legacy arm Y
        data["motor_y_speed_cm_per_sec"] = settings.motor_y_speed_cm_per_sec
        data["motor_y_default_cm"] = settings.motor_y_default_cm
        data["motor_y_max_cm"] = settings.motor_y_max_cm
        
        # CAMERA CALIBRATION
        data["camera_height_cm"] = settings.camera_height_cm
        data["camera_angle_deg"] = settings.camera_angle_deg
        data["camera_fov_deg"] = settings.camera_fov_deg
        data["pixel_to_cm_ratio"] = settings.pixel_to_cm_ratio
        data["workspace_x_min"] = settings.workspace_x_min
        data["workspace_x_max"] = settings.workspace_x_max
        data["workspace_y_min"] = settings.workspace_y_min
        data["workspace_y_max"] = settings.workspace_y_max
        data["workspace_z_min"] = settings.workspace_z_min
        data["workspace_z_max"] = settings.workspace_z_max
        
        # MOTION PLANNING
        data["motion_type"] = settings.motion_type
        data["approach_height_cm"] = settings.approach_height_cm
        data["approach_speed_percent"] = settings.approach_speed_percent
        data["retreat_height_cm"] = settings.retreat_height_cm
        
        # CONTROL MODES
        data["operation_mode"] = settings.operation_mode
        data["control_method"] = settings.control_method
        
        # SAFETY SETTINGS
        data["emergency_stop_enabled"] = settings.emergency_stop_enabled
        data["collision_detection_enabled"] = settings.collision_detection_enabled
        data["timeout_seconds"] = settings.timeout_seconds
        data["on_target_lost"] = settings.on_target_lost
        data["on_unreachable"] = settings.on_unreachable
        
        # PID TUNING
        data["pid_kp"] = settings.pid_kp
        data["pid_ki"] = settings.pid_ki
        data["pid_kd"] = settings.pid_kd
        data["moving_average_window"] = settings.moving_average_window
        data["kalman_filter_enabled"] = settings.kalman_filter_enabled
        
        # SPRAY SETTINGS
        data["default_spray_duration"] = settings.default_spray_duration
        
        # Timestamp
        data["settings_updated_at"] = datetime.now().isoformat()
        
        # Save
        with open(CALIBRATION_FILE, 'w') as f:
            json.dump(data, f, indent=2)
        
        print(f"✅ Settings saved: Z speed={settings.arm_speed_cm_per_sec}cm/s, PID={settings.pid_kp}/{settings.pid_ki}/{settings.pid_kd}")
        return {"success": True, "message": "Settings saved"}
        
    except Exception as e:
        print(f"Error saving settings: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/reboot")
async def reboot_backend():
    """
    POST /api/reboot
    รีบูต Backend Server
    """
    import os
    import subprocess
    
    print("🔄 Reboot requested via API...")
    
    # Send response before restarting
    def delayed_restart():
        time.sleep(1)
        print("🔄 Restarting server...")
        
        # Use systemctl restart if running as service
        try:
            subprocess.run(["systemctl", "restart", "agribot.service"], timeout=5)
        except:
            # Fallback: restart using python
            os.execv(sys.executable, [sys.executable] + sys.argv)
    
    # Start restart in background thread
    restart_thread = threading.Thread(target=delayed_restart)
    restart_thread.start()
    
    return {"success": True, "message": "Rebooting..."}

# ==================== CAMERA STREAM (With Background YOLO) ====================
import cv2

# Background detection cache
_detection_boxes = []
_detection_lock = threading.Lock()
_detection_thread = None
_detection_running = False
_camera_retry_count = 0
_last_camera_retry = 0

def _try_reconnect_camera():
    """Try to reconnect camera using V4L2 detection (คล้าย Cheese)"""
    global _camera_retry_count, _last_camera_retry
    
    # Rate limit retries (every 5 seconds)
    if time.time() - _last_camera_retry < 5:
        return False
    
    _last_camera_retry = time.time()
    _camera_retry_count += 1
    
    print(f"🔄 Camera reconnect attempt #{_camera_retry_count}")
    
    # ใช้ V4L2 หา USB cameras (วิธีเดียวกับ Cheese)
    try:
        from weed_detector import find_usb_cameras
        usb_cameras = find_usb_cameras()
        devices = usb_cameras + [0, 1, 2]
    except ImportError:
        devices = ['/dev/video0', '/dev/video1', '/dev/video2', 0, 1, 2]
    
    for device in devices:
        try:
            if robot.detector and hasattr(robot.detector, 'cap'):
                if robot.detector.cap is not None:
                    robot.detector.cap.release()
                
                robot.detector.cap = cv2.VideoCapture(device)
                if robot.detector.cap.isOpened():
                    # ทดสอบอ่านภาพ
                    ret, test_frame = robot.detector.cap.read()
                    if ret and test_frame is not None:
                        robot.detector.cap.set(cv2.CAP_PROP_FRAME_WIDTH, 640)
                        robot.detector.cap.set(cv2.CAP_PROP_FRAME_HEIGHT, 480)
                        robot.camera_connected = True
                        print(f"✅ Camera reconnected on {device}")
                        _camera_retry_count = 0
                        return True
                    else:
                        robot.detector.cap.release()
        except Exception as e:
            print(f"   Failed on {device}: {e}")
            continue
    
    print("❌ Camera reconnect failed")
    robot.camera_connected = False
    return False

def _background_detection_loop():
    """Run YOLO detection in background thread, cache results"""
    global _detection_boxes, _detection_running
    
    while _detection_running:
        try:
            if robot.camera_connected and robot.detector:
                frame = robot.detector.capture_frame()
                if frame is not None:
                    # Run YOLO detection
                    detections = robot.detector.detect(frame)
                    
                    # Cache boxes for stream to use
                    boxes = []
                    for det in detections:
                        color = (0, 0, 255) if det.is_target else (0, 255, 0)
                        boxes.append({
                            'x1': det.x - det.width // 2,
                            'y1': det.y - det.height // 2,
                            'x2': det.x + det.width // 2,
                            'y2': det.y + det.height // 2,
                            'label': det.class_name,
                            'conf': det.confidence,
                            'color': color
                        })
                    
                    with _detection_lock:
                        _detection_boxes = boxes
                else:
                    # Frame is None - camera might be disconnected
                    _try_reconnect_camera()
            else:
                # Camera not connected - try to reconnect
                _try_reconnect_camera()
            
            time.sleep(0.1)  # Run detection every 100ms
        except Exception as e:
            print(f"Detection error: {e}")
            time.sleep(0.5)

def _start_detection_thread():
    """Start background detection if not running"""
    global _detection_thread, _detection_running
    if not _detection_running:
        _detection_running = True
        _detection_thread = threading.Thread(target=_background_detection_loop, daemon=True)
        _detection_thread.start()


@app.post("/api/camera/reconnect")
async def reconnect_camera():
    """
    POST /api/camera/reconnect
    พยายามเชื่อมต่อกล้องใหม่
    """
    global _camera_retry_count, _last_camera_retry
    _last_camera_retry = 0  # Reset rate limit
    
    success = _try_reconnect_camera()
    
    return {
        "success": success,
        "message": "Camera reconnected" if success else "Camera reconnect failed",
        "retry_count": _camera_retry_count
    }


@app.get("/api/camera/status")
async def camera_status():
    """
    GET /api/camera/status
    สถานะกล้อง
    """
    return {
        "connected": robot.camera_connected,
        "retry_count": _camera_retry_count
    }

@app.get("/api/camera/stream")
@app.get("/api/camera")
async def camera_stream():
    """
    GET /api/camera
    MJPEG stream with cached YOLO boxes (smooth 30 FPS)
    """
    _start_detection_thread()
    
    def generate_frames():
        while True:
            if not robot.camera_connected or not robot.detector:
                error_frame = create_error_frame("Camera Not Available")
                yield (b'--frame\r\n'
                       b'Content-Type: image/jpeg\r\n\r\n' + error_frame + b'\r\n')
                time.sleep(1)
                continue
            
            # Get raw frame
            frame = robot.detector.capture_frame()
            if frame is None:
                time.sleep(0.01)
                continue
            
            # Draw cached detection boxes on frame
            with _detection_lock:
                boxes = _detection_boxes.copy()
            
            for box in boxes:
                cv2.rectangle(frame, 
                    (box['x1'], box['y1']), 
                    (box['x2'], box['y2']), 
                    box['color'], 2)
                cv2.putText(frame, f"{box['label']} {box['conf']:.0%}",
                    (box['x1'], box['y1'] - 5),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.4, box['color'], 1)
            
            # Resize and encode
            frame_small = cv2.resize(frame, (480, 360))
            _, buffer = cv2.imencode('.jpg', frame_small, [cv2.IMWRITE_JPEG_QUALITY, 50])
            
            yield (b'--frame\r\n'
                   b'Content-Type: image/jpeg\r\n\r\n' + buffer.tobytes() + b'\r\n')
            
            time.sleep(0.033)  # ~30 FPS
    
    return StreamingResponse(
        generate_frames(),
        media_type='multipart/x-mixed-replace; boundary=frame'
    )


def create_error_frame(message: str) -> bytes:
    """Create an error image with Thai message"""
    import numpy as np
    # Create black frame
    frame = np.zeros((360, 480, 3), dtype=np.uint8)
    
    # Add text (Thai may not render properly without font, use English fallback)
    cv2.putText(frame, "Camera Not Available", (100, 170),
                cv2.FONT_HERSHEY_SIMPLEX, 0.8, (100, 100, 100), 2)
    cv2.putText(frame, "Check USB Connection", (110, 200),
                cv2.FONT_HERSHEY_SIMPLEX, 0.6, (80, 80, 80), 1)
    
    _, buffer = cv2.imencode('.jpg', frame)
    return buffer.tobytes()


# ==================== Model API ====================

@app.get("/api/models")
async def list_models():
    """
    GET /api/models
    ดึงรายการโมเดลที่มีใน models/ folder
    """
    try:
        from pathlib import Path
        models_dir = Path(__file__).parent.parent.parent / "raspberry_pi" / "models"
        
        if not models_dir.exists():
            return {"models": [], "current": None}
        
        models = [f.name for f in models_dir.glob("*.pt")]
        
        # Get current model
        current = None
        if robot.detector and hasattr(robot.detector, 'model_path'):
            current = Path(robot.detector.model_path).name if robot.detector.model_path else None
        
        return {
            "models": sorted(models),
            "current": current,
            "models_dir": str(models_dir)
        }
    except Exception as e:
        print(f"Error listing models: {e}")
        return {"models": [], "current": None, "error": str(e)}


@app.post("/api/models/{model_name}")
async def select_model(model_name: str):
    """
    POST /api/models/{model_name}
    เลือกและโหลดโมเดลใหม่
    """
    try:
        from pathlib import Path
        models_dir = Path(__file__).parent.parent.parent / "raspberry_pi" / "models"
        model_path = models_dir / model_name
        
        if not model_path.exists():
            raise HTTPException(status_code=404, detail=f"Model not found: {model_name}")
        
        if not robot.detector:
            raise HTTPException(status_code=400, detail="Detector not initialized")
        
        # Load new model
        success = robot.detector.load_yolo_model(str(model_path))
        
        if success:
            print(f"✅ Model changed to: {model_name}")
            return {"success": True, "message": f"โหลดโมเดล {model_name} สำเร็จ", "model": model_name}
        else:
            raise HTTPException(status_code=500, detail="Failed to load model")
            
    except HTTPException:
        raise
    except Exception as e:
        print(f"Error loading model: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/models/info")
async def get_model_info():
    """
    GET /api/models/info
    ดึงข้อมูลโมเดลที่ใช้งานอยู่
    """
    if not robot.detector:
        return {"loaded": False, "error": "Detector not initialized"}
    
    info = robot.detector.get_model_info()
    return info


@app.get("/api/detection/debug")
async def detection_debug():
    """
    GET /api/detection/debug
    Debug info สำหรับตรวจสอบ detection
    """
    return {
        "camera_connected": robot.camera_connected,
        "detector_exists": robot.detector is not None,
        "model_loaded": robot.detector.model is not None if robot.detector else False,
        "model_path": robot.detector.model_path if robot.detector else None,
        "target_classes": robot.detector.get_target_classes() if robot.detector else [],
        "confidence_threshold": robot.detector.get_confidence_threshold() if robot.detector else 0,
        "detection_thread_running": _detection_running,
        "cached_boxes_count": len(_detection_boxes),
        "cached_boxes": _detection_boxes[:5]  # แสดง 5 อันแรก
    }


# ==================== Confidence API ====================

@app.get("/api/confidence")
async def get_confidence():
    """GET /api/confidence - ดึงค่า confidence threshold"""
    if not robot.detector:
        return {"confidence": 0.25, "error": "Detector not initialized"}
    return {"confidence": robot.detector.get_confidence_threshold()}


@app.post("/api/confidence/{value}")
async def set_confidence(value: float):
    """POST /api/confidence/{value} - ตั้งค่า confidence threshold (0.1-1.0)"""
    if not robot.detector:
        raise HTTPException(status_code=400, detail="Detector not initialized")
    
    robot.detector.set_confidence_threshold(value)
    return {
        "success": True,
        "confidence": robot.detector.get_confidence_threshold()
    }


# ==================== Target Classes API ====================

@app.get("/api/targets")
async def get_target_classes():
    """
    GET /api/targets
    ดึงรายชื่อ classes ที่เป็น target (จะถูกพ่นยา)
    """
    if not robot.detector:
        return {"error": "Detector not initialized", "targets": [], "available_classes": []}
    
    # Get available classes from model
    available = []
    if robot.detector.model and hasattr(robot.detector.model, 'names'):
        available = list(robot.detector.model.names.values())
    
    return {
        "targets": robot.detector.get_target_classes(),
        "available_classes": available
    }


class TargetClassesRequest(BaseModel):
    targets: List[str]


@app.post("/api/targets")
async def set_target_classes(request: TargetClassesRequest):
    """
    POST /api/targets
    ตั้งค่า classes ที่เป็น target
    
    Body: {"targets": ["weed", "chili"]}
    """
    if not robot.detector:
        raise HTTPException(status_code=400, detail="Detector not initialized")
    
    robot.detector.set_target_classes(request.targets)
    
    return {
        "success": True,
        "message": f"Target classes updated: {request.targets}",
        "targets": robot.detector.get_target_classes()
    }


@app.post("/api/targets/add/{class_name}")
async def add_target_class(class_name: str):
    """
    POST /api/targets/add/{class_name}
    เพิ่ม class เป็น target
    """
    if not robot.detector:
        raise HTTPException(status_code=400, detail="Detector not initialized")
    
    robot.detector.add_target_class(class_name)
    
    return {
        "success": True,
        "message": f"Added target: {class_name}",
        "targets": robot.detector.get_target_classes()
    }


@app.post("/api/targets/remove/{class_name}")
async def remove_target_class(class_name: str):
    """
    POST /api/targets/remove/{class_name}
    ลบ class ออกจาก target
    """
    if not robot.detector:
        raise HTTPException(status_code=400, detail="Detector not initialized")
    
    robot.detector.remove_target_class(class_name)
    
    return {
        "success": True,
        "message": f"Removed target: {class_name}",
        "targets": robot.detector.get_target_classes()
    }


# ==================== MANUAL CONTROL API ====================

class ManualCommandRequest(BaseModel):
    command: str
    params: Optional[dict] = None


@app.post("/api/manual")
async def manual_control(request: ManualCommandRequest):
    """
    POST /api/manual
    ส่งคำสั่งควบคุมหุ่นยนต์แบบ Manual
    
    Commands:
    - Movement: MOVE_FORWARD, MOVE_BACKWARD, MOVE_LEFT, MOVE_RIGHT, MOVE_STOP
    - Arm Z: ACT:Z_OUT:<sec>, ACT:Z_IN:<sec>
    - Arm Y: ACT:Y_UP, ACT:Y_DOWN
    - Spray: ACT:SPRAY:<sec>
    - Emergency: STOP_ALL
    """
    cmd = request.command.upper()
    
    # Check ESP32 connection
    if not robot.esp32_connected:
        return {"success": False, "error": "ESP32 ไม่ได้เชื่อมต่อ"}
    
    if not robot.brain:
        return {"success": False, "error": "Robot brain ไม่พร้อมใช้งาน"}
    
    try:
        # Movement commands
        if cmd == "MOVE_FORWARD":
            robot.brain.send_cmd("DRIVE_FW")
            robot.say("moving")
            return {"success": True, "message": "กำลังเดินหน้า"}
        
        elif cmd == "MOVE_BACKWARD":
            robot.brain.send_cmd("DRIVE_BW")
            return {"success": True, "message": "กำลังถอยหลัง"}
        
        elif cmd == "MOVE_LEFT":
            robot.brain.send_cmd("TURN_LEFT")
            return {"success": True, "message": "กำลังเลี้ยวซ้าย"}
        
        elif cmd == "MOVE_RIGHT":
            robot.brain.send_cmd("TURN_RIGHT")
            return {"success": True, "message": "กำลังเลี้ยวขวา"}
        
        elif cmd == "MOVE_STOP":
            robot.brain.send_cmd("DRIVE_STOP")
            return {"success": True, "message": "หยุดแล้ว"}
        
        # Timed Movement commands (MOVE_FW:duration, MOVE_BW:duration)
        elif cmd.startswith("MOVE_FW:"):
            duration = float(cmd.split(":")[1])
            robot.brain.send_cmd("DRIVE_FW")
            robot.say("moving")
            await asyncio.sleep(duration)
            robot.brain.send_cmd("DRIVE_STOP")
            return {"success": True, "message": f"เดินหน้า {duration} วินาที เสร็จแล้ว"}
        
        elif cmd.startswith("MOVE_BW:"):
            duration = float(cmd.split(":")[1])
            robot.brain.send_cmd("DRIVE_BW")
            await asyncio.sleep(duration)
            robot.brain.send_cmd("DRIVE_STOP")
            return {"success": True, "message": f"ถอยหลัง {duration} วินาที เสร็จแล้ว"}
        
        # Arm Z commands
        elif cmd.startswith("ACT:Z_OUT:"):
            duration = cmd.split(":")[2]
            robot.brain.send_cmd(f"ACT:Z_OUT:{duration}")
            robot.say("arm_extend")
            return {"success": True, "message": f"ยืดแขน {duration} วินาที"}
        
        elif cmd.startswith("ACT:Z_IN:"):
            duration = cmd.split(":")[2]
            robot.brain.send_cmd(f"ACT:Z_IN:{duration}")
            robot.say("arm_retract")
            return {"success": True, "message": f"หดแขน {duration} วินาที"}
        
        # Arm Y commands
        elif cmd == "ACT:Y_UP":
            robot.brain.send_cmd("ACT:Y_UP")
            return {"success": True, "message": "ยกหัวพ่นขึ้น"}
        
        elif cmd == "ACT:Y_DOWN":
            robot.brain.send_cmd("ACT:Y_DOWN")
            return {"success": True, "message": "วางหัวพ่นลง"}
        
        # Arm Y with duration (Y_UP:<seconds>, Y_DOWN:<seconds>)
        elif cmd.startswith("Y_UP:"):
            duration = cmd.split(":")[1]
            robot.brain.send_cmd(f"Y_UP:{duration}")
            return {"success": True, "message": f"ยกหัวพ่นขึ้น {duration} วินาที"}
        
        elif cmd.startswith("Y_DOWN:"):
            duration = cmd.split(":")[1]
            robot.brain.send_cmd(f"Y_DOWN:{duration}")
            return {"success": True, "message": f"วางหัวพ่นลง {duration} วินาที"}
        
        # Spray command
        elif cmd.startswith("ACT:SPRAY:"):
            duration = cmd.split(":")[2]
            robot.brain.send_cmd(f"ACT:SPRAY:{duration}")
            robot.say("spraying")
            robot.status.spray_count += 1
            robot._save_status()
            
            # Log spray event
            append_log(LogEntry(
                timestamp=datetime.now().isoformat(),
                event="MANUAL_SPRAY",
                details=f"Manual spray for {duration}s"
            ))
            
            return {"success": True, "message": f"พ่นยา {duration} วินาที"}
        
        # Pump direct control
        elif cmd == "PUMP_ON":
            robot.brain.send_cmd("PUMP_ON")
            return {"success": True, "message": "เปิดปั๊ม"}
        
        elif cmd == "PUMP_OFF":
            robot.brain.send_cmd("PUMP_OFF")
            return {"success": True, "message": "ปิดปั๊ม"}
        
        # Emergency stop
        elif cmd == "STOP_ALL":
            robot.brain.send_cmd("STOP_ALL")
            robot.is_running = False
            robot.status.state = "Stopped"
            robot.say("stopped")
            
            append_log(LogEntry(
                timestamp=datetime.now().isoformat(),
                event="MANUAL_STOP",
                details="Emergency stop via manual control"
            ))
            
            return {"success": True, "message": "หยุดฉุกเฉินทุกระบบ"}
        
        # Ultrasonic read
        elif cmd == "US_GET_DIST":
            robot.brain.send_cmd("US_GET_DIST")
            return {"success": True, "message": "อ่านค่า Ultrasonic"}
        
        else:
            return {"success": False, "error": f"Unknown command: {cmd}"}
    
    except Exception as e:
        print(f"❌ Manual control error: {e}")
        return {"success": False, "error": str(e)}


# ==================== HEALTH CHECK API ====================

class DeviceStatus:
    """สถานะของอุปกรณ์"""
    OK = "ok"
    WARNING = "warning"
    ERROR = "error"

def create_device_result(status: str, message: str, details: dict = None) -> dict:
    """สร้างผลลัพธ์สำหรับอุปกรณ์"""
    result = {"status": status, "message": message}
    if details:
        result["details"] = details
    return result


@app.get("/api/health")
async def get_health_status():
    """
    GET /api/health
    ตรวจสอบสถานะอุปกรณ์ทั้งหมด
    """
    results = {}
    
    # 1. ESP32 Connection
    if robot.esp32_connected and robot.brain:
        try:
            # Send PING to check connection
            start_time = time.time()
            robot.brain.ser.reset_input_buffer()
            robot.brain.ser.write(b"PING\n")
            
            # Wait for PONG
            response = ""
            timeout = time.time() + 2
            while time.time() < timeout:
                if robot.brain.ser.in_waiting > 0:
                    response = robot.brain.ser.readline().decode().strip()
                    if response == "PONG":
                        break
                time.sleep(0.01)
            
            latency = int((time.time() - start_time) * 1000)
            
            if response == "PONG":
                results["esp32"] = create_device_result(
                    DeviceStatus.OK, 
                    f"เชื่อมต่อแล้ว ({latency}ms)",
                    {"latency_ms": latency, "port": robot.brain.config.serial_port}
                )
            else:
                results["esp32"] = create_device_result(
                    DeviceStatus.WARNING, 
                    "เชื่อมต่อแต่ไม่ตอบสนอง"
                )
        except Exception as e:
            results["esp32"] = create_device_result(DeviceStatus.ERROR, f"ข้อผิดพลาด: {str(e)}")
    else:
        results["esp32"] = create_device_result(
            DeviceStatus.ERROR,
            "ไม่ได้เชื่อมต่อ",
            {"suggestion": "ตรวจสอบสาย USB และ port /dev/ttyUSB0"}
        )
    
    # 2. Camera
    if robot.camera_connected and robot.detector:
        try:
            frame = robot.detector.capture_frame()
            if frame is not None:
                h, w = frame.shape[:2]
                results["camera"] = create_device_result(
                    DeviceStatus.OK,
                    f"พร้อมใช้งาน ({w}x{h})"
                )
            else:
                results["camera"] = create_device_result(
                    DeviceStatus.WARNING,
                    "เชื่อมต่อแต่ไม่สามารถ capture ได้"
                )
        except Exception as e:
            results["camera"] = create_device_result(DeviceStatus.ERROR, f"ข้อผิดพลาด: {str(e)}")
    else:
        results["camera"] = create_device_result(
            DeviceStatus.ERROR,
            "ไม่พบกล้อง",
            {"suggestion": "ตรวจสอบการเชื่อมต่อ USB กล้อง"}
        )
    
    # 3. Motors (ถ้า ESP32 เชื่อมต่อ)
    if robot.esp32_connected:
        # Motor Left/Right assumed ready if ESP32 is connected
        results["motor_left"] = create_device_result(DeviceStatus.OK, "พร้อมใช้งาน")
        results["motor_right"] = create_device_result(DeviceStatus.OK, "พร้อมใช้งาน")
        results["motor_z"] = create_device_result(DeviceStatus.OK, "พร้อมใช้งาน (แกน Z)")
        results["motor_y"] = create_device_result(DeviceStatus.OK, "พร้อมใช้งาน (แกน Y)")
        results["pump"] = create_device_result(DeviceStatus.OK, "พร้อมใช้งาน")
        
        # 4. Ultrasonic Sensors - read actual values
        try:
            robot.brain.ser.reset_input_buffer()
            robot.brain.ser.write(b"US_GET_DIST\n")
            
            response = ""
            timeout = time.time() + 2
            while time.time() < timeout:
                if robot.brain.ser.in_waiting > 0:
                    response = robot.brain.ser.readline().decode().strip()
                    if response.startswith("DIST:"):
                        break
                time.sleep(0.01)
            
            if response.startswith("DIST:"):
                # Parse: DIST:front,yaxis,right
                values = response[5:].split(",")
                if len(values) >= 3:
                    front, yaxis, right = float(values[0]), float(values[1]), float(values[2])
                    
                    def us_status(val, name):
                        if val > 0 and val < 400:
                            return create_device_result(DeviceStatus.OK, f"{val:.1f} cm")
                        elif val == 0:
                            return create_device_result(DeviceStatus.WARNING, "อ่านค่า 0 - อาจต่อผิด")
                        else:
                            return create_device_result(DeviceStatus.ERROR, "ค่าผิดปกติ")
                    
                    results["ultrasonic_front"] = us_status(front, "หน้า")
                    results["ultrasonic_y"] = us_status(yaxis, "แกน Y")
                    results["ultrasonic_right"] = us_status(right, "ขวา")
                else:
                    results["ultrasonic_front"] = create_device_result(DeviceStatus.WARNING, "รูปแบบข้อมูลผิด")
                    results["ultrasonic_y"] = create_device_result(DeviceStatus.WARNING, "รูปแบบข้อมูลผิด")
                    results["ultrasonic_right"] = create_device_result(DeviceStatus.WARNING, "รูปแบบข้อมูลผิด")
            else:
                results["ultrasonic_front"] = create_device_result(DeviceStatus.WARNING, "ไม่ได้รับข้อมูล")
                results["ultrasonic_y"] = create_device_result(DeviceStatus.WARNING, "ไม่ได้รับข้อมูล")
                results["ultrasonic_right"] = create_device_result(DeviceStatus.WARNING, "ไม่ได้รับข้อมูล")
        except Exception as e:
            results["ultrasonic_front"] = create_device_result(DeviceStatus.ERROR, str(e))
            results["ultrasonic_y"] = create_device_result(DeviceStatus.ERROR, str(e))
            results["ultrasonic_right"] = create_device_result(DeviceStatus.ERROR, str(e))
    else:
        # ESP32 not connected - all hardware unavailable
        results["motor_left"] = create_device_result(DeviceStatus.ERROR, "ต้องเชื่อมต่อ ESP32")
        results["motor_right"] = create_device_result(DeviceStatus.ERROR, "ต้องเชื่อมต่อ ESP32")
        results["motor_z"] = create_device_result(DeviceStatus.ERROR, "ต้องเชื่อมต่อ ESP32")
        results["motor_y"] = create_device_result(DeviceStatus.ERROR, "ต้องเชื่อมต่อ ESP32")
        results["pump"] = create_device_result(DeviceStatus.ERROR, "ต้องเชื่อมต่อ ESP32")
        results["ultrasonic_front"] = create_device_result(DeviceStatus.ERROR, "ต้องเชื่อมต่อ ESP32")
        results["ultrasonic_y"] = create_device_result(DeviceStatus.ERROR, "ต้องเชื่อมต่อ ESP32")
        results["ultrasonic_right"] = create_device_result(DeviceStatus.ERROR, "ต้องเชื่อมต่อ ESP32")
    
    # Summary
    ok_count = sum(1 for r in results.values() if r["status"] == DeviceStatus.OK)
    warning_count = sum(1 for r in results.values() if r["status"] == DeviceStatus.WARNING)
    error_count = sum(1 for r in results.values() if r["status"] == DeviceStatus.ERROR)
    
    return {
        "devices": results,
        "summary": {
            "ok": ok_count,
            "warning": warning_count, 
            "error": error_count,
            "total": len(results)
        },
        "all_ok": error_count == 0 and warning_count == 0,
        "timestamp": datetime.now().isoformat()
    }


@app.post("/api/health/test/{device}")
async def test_device(device: str):
    """
    POST /api/health/test/{device}
    ทดสอบอุปกรณ์เฉพาะตัว
    
    Devices: motor_left, motor_right, motor_z, motor_y, pump
    """
    if not robot.esp32_connected or not robot.brain:
        return {"success": False, "error": "ESP32 ไม่ได้เชื่อมต่อ"}
    
    test_commands = {
        "motor_left": ("DRIVE_FW", 0.3),   # ทดสอบล้อซ้าย
        "motor_right": ("DRIVE_FW", 0.3),  # ทดสอบล้อขวา
        "motor_z": ("ACT:Z_OUT:0.3", 0),   # ยืดแขน 0.3 วินาที
        "motor_y": ("ACT:Y_UP", 0),        # ยกหัวพ่น
        "pump": ("ACT:SPRAY:0.2", 0),      # พ่น 0.2 วินาที
    }
    
    if device not in test_commands:
        return {"success": False, "error": f"ไม่รู้จักอุปกรณ์: {device}"}
    
    cmd, after_delay = test_commands[device]
    
    try:
        robot.brain.send_cmd(cmd)
        if after_delay > 0:
            time.sleep(after_delay)
            robot.brain.send_cmd("DRIVE_STOP")
        
        return {"success": True, "message": f"ทดสอบ {device} เสร็จสิ้น", "command": cmd}
    except Exception as e:
        return {"success": False, "error": str(e)}


# ==================== GPIO CONFIGURATION API ====================

@app.get("/api/gpio")
async def get_gpio_config():
    """
    GET /api/gpio
    อ่านค่า GPIO configuration ปัจจุบันจาก ESP32
    """
    if not robot.esp32_connected or not robot.brain:
        return {"success": False, "error": "ESP32 ไม่ได้เชื่อมต่อ"}
    
    try:
        robot.brain.ser.reset_input_buffer()
        robot.brain.ser.write(b"GPIO_GET\n")
        
        response = ""
        timeout = time.time() + 2
        while time.time() < timeout:
            if robot.brain.ser.in_waiting > 0:
                line = robot.brain.ser.readline().decode().strip()
                if line.startswith("GPIO:"):
                    response = line[5:]  # Remove "GPIO:" prefix
                    break
            time.sleep(0.01)
        
        if response:
            import json
            config = json.loads(response)
            return {"success": True, "config": config}
        else:
            return {"success": False, "error": "ไม่ได้รับข้อมูลจาก ESP32"}
            
    except Exception as e:
        return {"success": False, "error": str(e)}


@app.post("/api/gpio/swap/{group}")
async def swap_gpio_group(group: str):
    """
    POST /api/gpio/swap/{group}
    สลับ GPIO pins ในกลุ่มที่ระบุ
    
    Groups: motor_yz, wheels
    """
    if not robot.esp32_connected or not robot.brain:
        return {"success": False, "error": "ESP32 ไม่ได้เชื่อมต่อ"}
    
    swap_commands = {
        "motor_yz": "GPIO_SWAP_MOTOR_YZ",  # สลับ Motor Y <-> Motor Z
        "wheels": "GPIO_SWAP_WHEELS",       # สลับ Wheel Left <-> Right
    }
    
    if group not in swap_commands:
        return {"success": False, "error": f"ไม่รู้จักกลุ่ม: {group}. ใช้ได้: motor_yz, wheels"}
    
    cmd = swap_commands[group]
    
    try:
        robot.brain.ser.reset_input_buffer()
        robot.brain.ser.write(f"{cmd}\n".encode())
        
        # Wait for response
        response = ""
        timeout = time.time() + 3
        while time.time() < timeout:
            if robot.brain.ser.in_waiting > 0:
                line = robot.brain.ser.readline().decode().strip()
                if line.startswith("GPIO:"):
                    response = line
                    break
                elif line == "DONE":
                    break
            time.sleep(0.01)
        
        return {
            "success": True, 
            "message": f"สลับ {group} สำเร็จ",
            "note": "ต้อง restart ESP32 เพื่อให้มีผล"
        }
        
    except Exception as e:
        return {"success": False, "error": str(e)}


@app.post("/api/gpio/reset")
async def reset_gpio_config():
    """
    POST /api/gpio/reset
    Reset GPIO configuration เป็นค่าเริ่มต้น
    """
    if not robot.esp32_connected or not robot.brain:
        return {"success": False, "error": "ESP32 ไม่ได้เชื่อมต่อ"}
    
    try:
        robot.brain.ser.reset_input_buffer()
        robot.brain.ser.write(b"GPIO_RESET\n")
        
        # Wait for DONE
        timeout = time.time() + 3
        while time.time() < timeout:
            if robot.brain.ser.in_waiting > 0:
                line = robot.brain.ser.readline().decode().strip()
                if line == "DONE":
                    break
            time.sleep(0.01)
        
        return {
            "success": True,
            "message": "Reset GPIO config เป็นค่าเริ่มต้นสำเร็จ",
            "note": "ต้อง restart ESP32 เพื่อให้มีผล"
        }
        
    except Exception as e:
        return {"success": False, "error": str(e)}


# ==================== STATIC FILES ====================
# Serve React build (production)
if STATIC_DIR.exists():
    app.mount("/assets", StaticFiles(directory=str(STATIC_DIR / "assets")), name="assets")
    
    @app.get("/{full_path:path}")
    async def serve_spa(full_path: str):
        """Serve React SPA"""
        file_path = STATIC_DIR / full_path
        if file_path.exists() and file_path.is_file():
            return FileResponse(file_path)
        return FileResponse(STATIC_DIR / "index.html")
