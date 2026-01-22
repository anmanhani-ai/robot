"""
arm_controller.py
Main Arm Controller ที่รวม Camera Calibration + Inverse Kinematics + Motor Control

รองรับทั้ง:
- Encoder-based closed-loop control (PID)
- Time-based open-loop control (Improved)

Author: AgriBot Team
Created: 2026-01-21
"""

import time
import threading
from dataclasses import dataclass
from typing import Tuple, Optional, Callable
import logging

from kinematics.camera_calibration import CameraCalibration, quick_calibration
from kinematics.inverse_kinematics import InverseKinematics, IKSolution, create_agribot_ik, Joint, JointType
from control.pid_controller import PIDController, ImprovedTimeBasedController, create_agribot_controller

logger = logging.getLogger(__name__)


@dataclass
class ArmState:
    """Current state of the arm"""
    z_position_cm: float = 0.0
    y_angle_deg: float = 0.0
    is_moving: bool = False
    last_target: Tuple[float, float, float] = (0, 0, 0)
    error_message: str = ""


class ArmController:
    """
    Main Arm Controller
    
    รวม Camera Calibration + Inverse Kinematics + Motor Control เข้าด้วยกัน
    
    Usage:
        controller = ArmController(serial_connection)
        controller.move_to_pixel(x_px, y_px)  # Move arm to detected object
        controller.move_to_world(x_cm, y_cm, z_cm)  # Move to world coords
    """
    
    def __init__(
        self,
        serial_connection,
        camera_calibration: Optional[CameraCalibration] = None,
        ik_engine: Optional[InverseKinematics] = None,
        use_encoder: bool = False
    ):
        """
        Args:
            serial_connection: Serial connection to ESP32
            camera_calibration: Camera calibration object (optional)
            ik_engine: Inverse kinematics engine (optional)
            use_encoder: Whether to use encoder feedback for closed-loop control
        """
        self.serial = serial_connection
        self.use_encoder = use_encoder
        
        # Initialize camera calibration
        if camera_calibration:
            self.camera = camera_calibration
        else:
            # Default quick calibration
            self.camera = quick_calibration(
                camera_height_cm=50.0,
                camera_angle_deg=45.0
            )
        
        # Initialize IK engine
        if ik_engine:
            self.ik = ik_engine
        else:
            self.ik = create_agribot_ik()
        
        # Initialize motor controllers
        if use_encoder:
            # PID controllers for closed-loop control
            self.pid_z = PIDController(Kp=2.0, Ki=0.1, Kd=0.05, name="Z_Axis")
            self.pid_y = PIDController(Kp=3.0, Ki=0.2, Kd=0.1, name="Y_Axis")
        else:
            # Time-based controller for open-loop control
            self.time_controller = create_agribot_controller()
        
        # State
        self.state = ArmState()
        self._stop_event = threading.Event()
        
        # Control loop parameters
        self.control_rate = 50  # Hz
        self.position_tolerance = 0.5  # cm for Z, degrees for Y
        self.max_iterations = 500
        
        logger.info(f"ArmController initialized (encoder={use_encoder})")
    
    # ==================== Main Movement Functions ====================
    
    def move_to_pixel(self, x_px: int, y_px: int, z_target: float = 0.0) -> bool:
        """
        เคลื่อนที่แขนไปยังตำแหน่ง pixel ที่กล้องเห็น
        
        Args:
            x_px, y_px: Pixel coordinates from detection
            z_target: Target Z height (cm, 0 = ground)
        
        Returns:
            True if movement successful
        """
        logger.info(f"Moving to pixel ({x_px}, {y_px})")
        
        # Step 1: Convert pixel to world coordinates
        x_world, y_world, z_world = self.camera.pixel_to_world(x_px, y_px, z_target)
        logger.info(f"  → World coords: ({x_world:.2f}, {y_world:.2f}, {z_world:.2f}) cm")
        
        # Step 2: Move to world coordinates
        return self.move_to_world(x_world, y_world, z_world)
    
    def move_to_world(self, x: float, y: float, z: float) -> bool:
        """
        เคลื่อนที่แขนไปยังตำแหน่ง world coordinates
        
        Args:
            x, y, z: World coordinates (cm)
        
        Returns:
            True if movement successful
        """
        self.state.last_target = (x, y, z)
        self.state.is_moving = True
        self._stop_event.clear()
        
        try:
            # Step 1: Solve Inverse Kinematics
            solution = self.ik.solve(x, y, z)
            
            if not solution.reachable:
                self.state.error_message = solution.error_message
                logger.warning(f"Target unreachable: {solution.error_message}")
                return False
            
            logger.info(f"IK Solution: {solution.joint_values}")
            logger.info(f"  Times: {solution.joint_times}")
            
            # Step 2: Execute movement
            if self.use_encoder:
                return self._execute_closed_loop(solution)
            else:
                return self._execute_open_loop(solution)
            
        except Exception as e:
            logger.error(f"Movement failed: {e}")
            self.state.error_message = str(e)
            return False
        finally:
            self.state.is_moving = False
    
    # ==================== Closed-Loop Control (with Encoder) ====================
    
    def _execute_closed_loop(self, solution: IKSolution) -> bool:
        """
        Execute movement with closed-loop PID control
        
        Requires encoder feedback from ESP32
        """
        target_z = solution.joint_values.get('Z', self.state.z_position_cm)
        target_y = solution.joint_values.get('Y', self.state.y_angle_deg)
        
        dt = 1.0 / self.control_rate
        
        # Reset PIDs
        self.pid_z.reset()
        self.pid_y.reset()
        
        for i in range(self.max_iterations):
            if self._stop_event.is_set():
                self._stop_motors()
                logger.info("Movement stopped by user")
                return False
            
            # Read current positions from encoders
            current_z = self._read_encoder('Z')
            current_y = self._read_encoder('Y')
            
            self.state.z_position_cm = current_z
            self.state.y_angle_deg = current_y
            
            # Check if reached target
            z_error = abs(target_z - current_z)
            y_error = abs(target_y - current_y)
            
            if z_error < self.position_tolerance and y_error < self.position_tolerance:
                self._stop_motors()
                logger.info(f"Reached target in {i+1} iterations")
                return True
            
            # Compute PID outputs
            z_pwm = self.pid_z.compute(target_z, current_z, dt)
            y_pwm = self.pid_y.compute(target_y, current_y, dt)
            
            # Send motor commands
            self._send_motor_pwm('Z', z_pwm)
            self._send_motor_pwm('Y', y_pwm)
            
            time.sleep(dt)
        
        self._stop_motors()
        logger.warning("Movement timeout")
        return False
    
    def _read_encoder(self, axis: str) -> float:
        """Read encoder position from ESP32"""
        try:
            self.serial.write(f"GET:ENC_{axis}\n".encode())
            response = self.serial.readline().decode().strip()
            
            if ':' in response:
                return float(response.split(':')[1])
            return 0.0
        except Exception as e:
            logger.error(f"Encoder read failed: {e}")
            return 0.0
    
    def _send_motor_pwm(self, axis: str, pwm: float):
        """Send PWM command to motor"""
        direction = 'FW' if pwm >= 0 else 'BW'
        pwm_value = int(min(abs(pwm), 255))
        
        cmd = f"MOT:{axis}:{direction}:{pwm_value}\n"
        self.serial.write(cmd.encode())
    
    # ==================== Open-Loop Control (Time-Based) ====================
    
    def _execute_open_loop(self, solution: IKSolution) -> bool:
        """
        Execute movement with time-based open-loop control
        
        Uses improved time-based controller with compensation
        """
        # Get joint commands
        commands = self.ik.get_joint_commands(solution)
        
        logger.info(f"Executing commands: {commands}")
        
        for cmd in commands:
            if self._stop_event.is_set():
                self._stop_motors()
                return False
            
            # Parse and execute command
            success = self._execute_command(cmd)
            if not success:
                logger.error(f"Command failed: {cmd}")
                return False
        
        # Update estimated position
        if 'Z' in solution.joint_values:
            self.state.z_position_cm = solution.joint_values['Z']
        if 'Y' in solution.joint_values:
            self.state.y_angle_deg = solution.joint_values['Y']
        
        return True
    
    def _execute_command(self, cmd: str) -> bool:
        """
        Execute a single motor command
        
        Format: ACT:{axis}_{direction}:{time}
        Examples:
            ACT:Z_OUT:1.5
            ACT:Y_DOWN
        """
        try:
            self.serial.write(f"{cmd}\n".encode())
            logger.debug(f"Sent: {cmd}")
            
            # Wait for DONE response
            start = time.time()
            while time.time() - start < 30:  # 30s timeout
                if self.serial.in_waiting > 0:
                    response = self.serial.readline().decode().strip()
                    if response == "DONE":
                        return True
                    elif response.startswith("ERR"):
                        logger.error(f"ESP32 error: {response}")
                        return False
                time.sleep(0.01)
            
            logger.error("Command timeout")
            return False
            
        except Exception as e:
            logger.error(f"Command execution failed: {e}")
            return False
    
    def _stop_motors(self):
        """Stop all motors"""
        try:
            self.serial.write("STOP\n".encode())
        except Exception as e:
            logger.error(f"Stop failed: {e}")
    
    # ==================== Spray Mission ====================
    
    def execute_spray_mission(self, x_px: int, y_px: int, spray_duration: float = 2.0) -> bool:
        """
        Execute complete spray mission:
        1. Move arm to target
        2. Lower spray head
        3. Spray
        4. Raise spray head
        5. Retract arm
        
        Args:
            x_px, y_px: Target pixel coordinates
            spray_duration: Spray time (seconds)
        
        Returns:
            True if mission successful
        """
        logger.info(f"=== Spray Mission Start ===")
        logger.info(f"Target: pixel ({x_px}, {y_px})")
        
        # Convert pixel to world
        x_w, y_w, z_w = self.camera.pixel_to_world(x_px, y_px)
        logger.info(f"World: ({x_w:.1f}, {y_w:.1f}, {z_w:.1f}) cm")
        
        # Solve IK
        solution = self.ik.solve(x_w, y_w, z_w)
        
        if not solution.reachable:
            logger.error(f"Target unreachable: {solution.error_message}")
            return False
        
        z_time = solution.joint_times.get('Z', 0)
        
        # Step 1: Extend arm
        logger.info(f"Step 1: Extending arm ({z_time:.2f}s)")
        if not self._execute_command(f"ACT:Z_OUT:{z_time:.2f}"):
            return False
        
        # Step 2: Lower spray head
        logger.info("Step 2: Lowering spray head")
        if not self._execute_command("ACT:Y_DOWN"):
            return False
        
        # Step 3: Spray
        logger.info(f"Step 3: Spraying ({spray_duration}s)")
        if not self._execute_command(f"ACT:SPRAY:{spray_duration:.1f}"):
            return False
        
        # Step 4: Raise spray head
        logger.info("Step 4: Raising spray head")
        if not self._execute_command("ACT:Y_UP"):
            return False
        
        # Step 5: Retract arm
        logger.info(f"Step 5: Retracting arm ({z_time:.2f}s)")
        if not self._execute_command(f"ACT:Z_IN:{z_time:.2f}"):
            return False
        
        logger.info("=== Spray Mission Complete ===")
        return True
    
    # ==================== Utility ====================
    
    def home(self) -> bool:
        """Return arm to home position"""
        logger.info("Homing arm...")
        
        # Retract fully
        self._execute_command("ACT:Z_IN:10.0")  # Max retract
        
        # Raise head
        self._execute_command("ACT:Y_UP")
        
        # Reset state
        self.state.z_position_cm = 0.0
        self.state.y_angle_deg = 0.0
        
        if not self.use_encoder:
            self.time_controller.reset_position()
        
        return True
    
    def stop(self):
        """Emergency stop"""
        self._stop_event.set()
        self._stop_motors()
        self.state.is_moving = False
        logger.warning("Emergency stop activated")
    
    def get_state(self) -> dict:
        """Get current arm state"""
        return {
            'z_position_cm': self.state.z_position_cm,
            'y_angle_deg': self.state.y_angle_deg,
            'is_moving': self.state.is_moving,
            'last_target': self.state.last_target,
            'error': self.state.error_message
        }
    
    def calibrate_pixel_to_cm(self, known_distance_cm: float, measured_pixels: int) -> float:
        """
        Calibrate pixel-to-cm ratio from known distance
        
        Returns:
            New pixel_to_cm ratio
        """
        ratio = known_distance_cm / measured_pixels
        logger.info(f"New pixel-to-cm ratio: {ratio:.6f}")
        return ratio


# ==================== Factory Functions ====================

def create_arm_controller_from_config(serial_connection, config_path: str) -> ArmController:
    """
    Create ArmController from config file
    """
    from kinematics.camera_calibration import CameraCalibration, CameraConfig
    
    # Load camera config
    camera_config = CameraConfig.load_from_file(config_path)
    camera = CameraCalibration(config=camera_config)
    
    # Create IK engine
    ik = create_agribot_ik()
    
    return ArmController(
        serial_connection=serial_connection,
        camera_calibration=camera,
        ik_engine=ik,
        use_encoder=False
    )


if __name__ == "__main__":
    # Test arm controller (mock serial)
    logging.basicConfig(level=logging.DEBUG)
    
    class MockSerial:
        def write(self, data):
            print(f"Serial: {data.decode().strip()}")
        def readline(self):
            return b"DONE\n"
        @property
        def in_waiting(self):
            return 1
    
    print("\n=== Testing Arm Controller ===")
    
    controller = ArmController(
        serial_connection=MockSerial(),
        use_encoder=False
    )
    
    # Test pixel to world to IK
    test_pixels = [
        (320, 240),  # Center
        (400, 300),  # Offset right-down
        (200, 180),  # Offset left-up
    ]
    
    for x_px, y_px in test_pixels:
        print(f"\n--- Testing pixel ({x_px}, {y_px}) ---")
        
        # Get world coords
        x_w, y_w, z_w = controller.camera.pixel_to_world(x_px, y_px)
        print(f"World: ({x_w:.2f}, {y_w:.2f}, {z_w:.2f}) cm")
        
        # Get IK solution
        solution = controller.ik.solve(x_w, y_w, z_w)
        print(f"IK: {solution.joint_values}")
        print(f"Times: {solution.joint_times}")
        print(f"Reachable: {solution.reachable}")
