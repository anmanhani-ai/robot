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
from typing import Optional
from datetime import datetime
from pathlib import Path
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
    
    def start_mission(self) -> dict:
        """เริ่ม Mission"""
        if not self.esp32_connected or not self.camera_connected:
            return {
                "success": False, 
                "error": self.error_message or "อุปกรณ์ไม่พร้อมใช้งาน"
            }
        
        if self.is_running:
            return {"success": False, "error": "Mission กำลังทำงานอยู่"}
        
        self.is_running = True
        self.status.state = "Moving"
        self.say("moving")
        
        # Log start
        append_log(LogEntry(
            timestamp=datetime.now().isoformat(),
            event="MISSION_START",
            details="Mission started via web dashboard"
        ))
        
        # Start auto mode thread
        self.thread = threading.Thread(target=self._auto_mode_loop, daemon=True)
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
        
        return {"success": True}
    
    def reset(self) -> dict:
        """Reset ทุกอย่าง"""
        self.is_running = False
        self.status = RobotStatus()
        self.say("ready")
        
        # Clear report
        write_json(REPORT_FILE, [])
        
        return {"success": True}
    
    def _auto_mode_loop(self):
        """
        Auto mode loop - ทำงานเหมือน main.py 
        """
        if not self.brain or not self.detector:
            return
        
        self.brain.move_forward_speed(self.brain.SPEED_NORMAL)
        
        while self.is_running:
            try:
                # Capture & detect
                frame = self.detector.capture_frame()
                if frame is None:
                    time.sleep(0.05)
                    continue
                
                all_detections = self.detector.detect(frame)
                target = self.detector.get_nearest_target(all_detections)
                
                # Update counters
                for det in all_detections:
                    if det.is_target:
                        self.status.weed_count += 1
                    else:
                        self.status.chili_count += 1
                
                if target is None:
                    # No target - keep moving
                    self.status.state = "Moving"
                    self.status.distance_traveled += 0.05
                else:
                    # Has target - adjust speed
                    distance_x = target.distance_from_center_x
                    new_speed = self.brain.calculate_approach_speed(distance_x)
                    
                    if new_speed == 0:
                        # Aligned - spray
                        self.status.state = "Spraying"
                        self._save_status()
                        
                        self.brain.stop_movement()
                        time.sleep(0.1)
                        
                        distance_y = abs(target.distance_from_center_y)
                        success = self.brain.execute_spray_mission(distance_y)
                        
                        if success:
                            self.status.spray_count += 1
                            append_log(LogEntry(
                                timestamp=datetime.now().isoformat(),
                                event="WEED_SPRAYED",
                                x=target.x,
                                y=target.y,
                                details=f"Spray #{self.status.spray_count}"
                            ))
                        
                        # Resume moving
                        self.brain.move_forward_speed(self.brain.SPEED_NORMAL)
                    else:
                        self.brain.set_speed(new_speed)
                
                self._save_status()
                time.sleep(0.04)  # ~25 FPS
                
            except Exception as e:
                print(f"❌ Auto mode error: {e}")
                time.sleep(0.1)
        
        # Stopped
        self.brain.stop_movement()
    
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
        result = robot.start_mission()
        if result.get("success"):
            return {"success": True, "message": "Mission started"}
        else:
            return {"success": False, "message": result.get("error", "ไม่สามารถเริ่ม Mission ได้")}
    
    elif cmd == "stop":
        result = robot.stop_mission()
        return {"success": True, "message": "Mission stopped"}
    
    elif cmd == "reset":
        result = robot.reset()
        return {"success": True, "message": "System reset"}
    
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
    max_arm_extend_cm: float = 50.0
    arm_base_offset_cm: float = 5.0
    arm_speed_cm_per_sec: float = 10.0
    servo_y_angle_down: int = 90
    servo_y_angle_up: int = 0
    default_spray_duration: float = 1.0


@app.get("/api/settings")
async def get_settings():
    """
    GET /api/settings
    ดึงค่าตั้งค่าแขนกลจาก calibration.json
    """
    try:
        if CALIBRATION_FILE.exists():
            with open(CALIBRATION_FILE, 'r') as f:
                data = json.load(f)
            
            # Extract relevant settings
            return {
                "max_arm_extend_cm": data.get("max_arm_extend_cm", 50.0),
                "arm_base_offset_cm": data.get("arm_base_offset_cm", 5.0),
                "arm_speed_cm_per_sec": data.get("arm_speed_cm_per_sec", 10.0),
                "servo_y_angle_down": data.get("servo_y_angle_down", 90),
                "servo_y_angle_up": data.get("servo_y_angle_up", 0),
                "default_spray_duration": data.get("default_spray_duration", 1.0),
            }
    except Exception as e:
        print(f"Error reading settings: {e}")
    
    # Return defaults
    return ArmSettings().model_dump()


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
        
        # Update with new settings
        data["max_arm_extend_cm"] = settings.max_arm_extend_cm
        data["arm_base_offset_cm"] = settings.arm_base_offset_cm
        data["arm_speed_cm_per_sec"] = settings.arm_speed_cm_per_sec
        data["servo_y_angle_down"] = settings.servo_y_angle_down
        data["servo_y_angle_up"] = settings.servo_y_angle_up
        data["default_spray_duration"] = settings.default_spray_duration
        data["settings_updated_at"] = datetime.now().isoformat()
        
        # Save
        with open(CALIBRATION_FILE, 'w') as f:
            json.dump(data, f, indent=2)
        
        print(f"✅ Settings saved: max_arm={settings.max_arm_extend_cm}cm")
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
            robot.brain.send_command("DRIVE_FW")
            robot.say("moving")
            return {"success": True, "message": "กำลังเดินหน้า"}
        
        elif cmd == "MOVE_BACKWARD":
            robot.brain.send_command("DRIVE_BW")
            return {"success": True, "message": "กำลังถอยหลัง"}
        
        elif cmd == "MOVE_LEFT":
            robot.brain.send_command("TURN_LEFT")
            return {"success": True, "message": "กำลังเลี้ยวซ้าย"}
        
        elif cmd == "MOVE_RIGHT":
            robot.brain.send_command("TURN_RIGHT")
            return {"success": True, "message": "กำลังเลี้ยวขวา"}
        
        elif cmd == "MOVE_STOP":
            robot.brain.send_command("DRIVE_STOP")
            return {"success": True, "message": "หยุดแล้ว"}
        
        # Arm Z commands
        elif cmd.startswith("ACT:Z_OUT:"):
            duration = cmd.split(":")[2]
            robot.brain.send_command(f"ACT:Z_OUT:{duration}")
            robot.say("arm_extend")
            return {"success": True, "message": f"ยืดแขน {duration} วินาที"}
        
        elif cmd.startswith("ACT:Z_IN:"):
            duration = cmd.split(":")[2]
            robot.brain.send_command(f"ACT:Z_IN:{duration}")
            robot.say("arm_retract")
            return {"success": True, "message": f"หดแขน {duration} วินาที"}
        
        # Arm Y commands
        elif cmd == "ACT:Y_UP":
            robot.brain.send_command("ACT:Y_UP")
            return {"success": True, "message": "ยกหัวพ่นขึ้น"}
        
        elif cmd == "ACT:Y_DOWN":
            robot.brain.send_command("ACT:Y_DOWN")
            return {"success": True, "message": "วางหัวพ่นลง"}
        
        # Spray command
        elif cmd.startswith("ACT:SPRAY:"):
            duration = cmd.split(":")[2]
            robot.brain.send_command(f"ACT:SPRAY:{duration}")
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
            robot.brain.send_command("PUMP_ON")
            return {"success": True, "message": "เปิดปั๊ม"}
        
        elif cmd == "PUMP_OFF":
            robot.brain.send_command("PUMP_OFF")
            return {"success": True, "message": "ปิดปั๊ม"}
        
        # Emergency stop
        elif cmd == "STOP_ALL":
            robot.brain.send_command("STOP_ALL")
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
            robot.brain.send_command("US_GET_DIST")
            return {"success": True, "message": "อ่านค่า Ultrasonic"}
        
        else:
            return {"success": False, "error": f"Unknown command: {cmd}"}
    
    except Exception as e:
        print(f"❌ Manual control error: {e}")
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
