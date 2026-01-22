"""
Custom Exceptions สำหรับ AgriBot
แยก Exception types เพื่อให้ Error Handling ชัดเจน

Author: AgriBot Team
"""


class AgribotError(Exception):
    """Base exception สำหรับ AgriBot"""
    pass


class RobotConnectionError(AgribotError):
    """เกิดข้อผิดพลาดในการเชื่อมต่อกับ ESP32"""
    def __init__(self, message: str = "Cannot connect to ESP32", port: str = None):
        self.port = port
        super().__init__(f"{message} (port: {port})" if port else message)


class CalibrationError(AgribotError):
    """เกิดข้อผิดพลาดในการโหลด/บันทึก Calibration"""
    def __init__(self, message: str = "Calibration error", filepath: str = None):
        self.filepath = filepath
        super().__init__(f"{message}: {filepath}" if filepath else message)


class TargetUnreachableError(AgribotError):
    """ตำแหน่งเป้าหมายอยู่นอกระยะที่แขนกลเข้าถึงได้"""
    def __init__(self, target_cm: float, max_cm: float):
        self.target_cm = target_cm
        self.max_cm = max_cm
        super().__init__(f"Target at {target_cm:.1f}cm is beyond max reach of {max_cm:.1f}cm")


class EmergencyStopError(AgribotError):
    """ถูกกด Emergency Stop"""
    def __init__(self, message: str = "Emergency stop activated"):
        super().__init__(message)


class CommandTimeoutError(AgribotError):
    """คำสั่งไม่ได้รับการตอบกลับในเวลาที่กำหนด"""
    def __init__(self, command: str, timeout: float):
        self.command = command
        self.timeout = timeout
        super().__init__(f"Command '{command}' timed out after {timeout:.1f}s")


class ModelLoadError(AgribotError):
    """ไม่สามารถโหลด YOLO Model ได้"""
    def __init__(self, model_path: str, reason: str = None):
        self.model_path = model_path
        msg = f"Failed to load model: {model_path}"
        if reason:
            msg += f" ({reason})"
        super().__init__(msg)


class CameraError(AgribotError):
    """เกิดข้อผิดพลาดกับกล้อง"""
    def __init__(self, camera_id, message: str = "Camera error"):
        self.camera_id = camera_id
        super().__init__(f"{message} (camera: {camera_id})")
