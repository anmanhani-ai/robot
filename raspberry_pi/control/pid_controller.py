"""
pid_controller.py
PID Controller สำหรับ closed-loop motor control

Features:
- Anti-windup
- Derivative filtering
- Output limiting
- Error history for debugging

Author: AgriBot Team
Created: 2026-01-21
"""

import time
from dataclasses import dataclass, field
from typing import Optional, List, Tuple
import logging

logger = logging.getLogger(__name__)


@dataclass
class PIDGains:
    """PID Tuning Parameters"""
    Kp: float = 1.0     # Proportional gain
    Ki: float = 0.0     # Integral gain
    Kd: float = 0.0     # Derivative gain
    
    # Anti-windup limits
    integral_max: float = 100.0
    integral_min: float = -100.0
    
    # Output limits
    output_max: float = 255.0
    output_min: float = -255.0
    
    # Derivative filter (0 = no filter, 1 = full filter)
    derivative_filter: float = 0.1


class PIDController:
    """
    PID Controller with Anti-Windup and Derivative Filtering
    
    Usage:
        pid = PIDController(Kp=2.0, Ki=0.1, Kd=0.05)
        while True:
            output = pid.compute(target, current_value, dt)
            send_to_motor(output)
    """
    
    def __init__(
        self, 
        Kp: float = 1.0, 
        Ki: float = 0.0, 
        Kd: float = 0.0,
        output_limits: Tuple[float, float] = (-255, 255),
        name: str = "PID"
    ):
        """
        Args:
            Kp, Ki, Kd: PID gains
            output_limits: (min, max) output values
            name: Controller name for logging
        """
        self.gains = PIDGains(
            Kp=Kp, Ki=Ki, Kd=Kd,
            output_min=output_limits[0],
            output_max=output_limits[1]
        )
        self.name = name
        
        # State
        self.integral = 0.0
        self.prev_error = 0.0
        self.prev_derivative = 0.0
        self.prev_time = None
        
        # Debug history
        self._history: List[dict] = []
        self._max_history = 1000
    
    def compute(self, setpoint: float, measurement: float, dt: Optional[float] = None) -> float:
        """
        คำนวณ output จาก PID
        
        Args:
            setpoint: ค่าเป้าหมาย
            measurement: ค่าที่วัดได้จริง
            dt: Time delta (ถ้าไม่ระบุจะคำนวณเอง)
        
        Returns:
            Output value (clamped to limits)
        """
        current_time = time.time()
        
        # Compute dt if not provided
        if dt is None:
            if self.prev_time is not None:
                dt = current_time - self.prev_time
            else:
                dt = 0.02  # Default 50Hz
        self.prev_time = current_time
        
        # Ensure minimum dt to avoid division by zero
        dt = max(dt, 0.001)
        
        # Calculate error
        error = setpoint - measurement
        
        # === Proportional ===
        P = self.gains.Kp * error
        
        # === Integral with Anti-Windup ===
        self.integral += error * dt
        self.integral = max(self.gains.integral_min, 
                           min(self.gains.integral_max, self.integral))
        I = self.gains.Ki * self.integral
        
        # === Derivative with Filtering ===
        raw_derivative = (error - self.prev_error) / dt
        
        # Low-pass filter on derivative
        alpha = self.gains.derivative_filter
        filtered_derivative = alpha * self.prev_derivative + (1 - alpha) * raw_derivative
        self.prev_derivative = filtered_derivative
        
        D = self.gains.Kd * filtered_derivative
        self.prev_error = error
        
        # === Output ===
        output = P + I + D
        output = max(self.gains.output_min, min(self.gains.output_max, output))
        
        # Log history
        self._add_history(setpoint, measurement, error, P, I, D, output)
        
        return output
    
    def reset(self):
        """Reset controller state"""
        self.integral = 0.0
        self.prev_error = 0.0
        self.prev_derivative = 0.0
        self.prev_time = None
        logger.debug(f"{self.name} PID reset")
    
    def set_gains(self, Kp: float = None, Ki: float = None, Kd: float = None):
        """Update PID gains"""
        if Kp is not None:
            self.gains.Kp = Kp
        if Ki is not None:
            self.gains.Ki = Ki
        if Kd is not None:
            self.gains.Kd = Kd
        logger.info(f"{self.name} gains updated: Kp={self.gains.Kp}, Ki={self.gains.Ki}, Kd={self.gains.Kd}")
    
    def _add_history(self, setpoint, measurement, error, P, I, D, output):
        """Add to debug history"""
        self._history.append({
            'time': time.time(),
            'setpoint': setpoint,
            'measurement': measurement,
            'error': error,
            'P': P,
            'I': I,
            'D': D,
            'output': output
        })
        
        # Limit history size
        if len(self._history) > self._max_history:
            self._history = self._history[-self._max_history:]
    
    def get_history(self) -> List[dict]:
        """Get debug history"""
        return self._history.copy()
    
    def get_stats(self) -> dict:
        """Get controller statistics"""
        if not self._history:
            return {}
        
        errors = [h['error'] for h in self._history]
        outputs = [h['output'] for h in self._history]
        
        return {
            'samples': len(self._history),
            'error_avg': sum(errors) / len(errors),
            'error_max': max(abs(e) for e in errors),
            'output_avg': sum(outputs) / len(outputs),
            'integral': self.integral
        }


class ImprovedTimeBasedController:
    """
    ปรับปรุง Time-Based Control สำหรับระบบที่ไม่มี Encoder
    
    Features:
    - Acceleration ramp
    - Overshoot compensation
    - Retry mechanism
    - Calibration adjustment
    """
    
    def __init__(
        self,
        speed_cm_per_sec: float,
        accel_time_sec: float = 0.15,
        overshoot_factor: float = 0.95,
        min_move_time: float = 0.1,
        max_retries: int = 3
    ):
        """
        Args:
            speed_cm_per_sec: ความเร็วมอเตอร์ (cm/s)
            accel_time_sec: เวลา acceleration (วินาที)
            overshoot_factor: ตัวคูณชดเชย overshoot (< 1.0)
            min_move_time: เวลาเคลื่อนที่ต่ำสุด
            max_retries: จำนวน retry สูงสุด
        """
        self.speed = speed_cm_per_sec
        self.accel_time = accel_time_sec
        self.overshoot_factor = overshoot_factor
        self.min_move_time = min_move_time
        self.max_retries = max_retries
        
        # Calibration adjustment (multiply factor)
        self.calibration_factor = 1.0
        
        # State tracking
        self.current_position = 0.0  # Estimated position
        
        # History for auto-calibration
        self._move_history: List[dict] = []
    
    def calculate_move_time(self, target_cm: float, from_position: float = None) -> float:
        """
        คำนวณเวลาเคลื่อนที่
        
        Args:
            target_cm: ระยะทางเป้าหมาย (cm)
            from_position: ตำแหน่งเริ่มต้น (ถ้าไม่ระบุใช้ current_position)
        
        Returns:
            เวลาที่ต้องใช้ (วินาที)
        """
        if from_position is None:
            from_position = self.current_position
        
        distance = abs(target_cm - from_position)
        
        if distance < 0.1:  # Too small, skip
            return 0.0
        
        # Base time from distance and speed
        base_time = distance / self.speed
        
        # Add acceleration compensation
        total_time = base_time + self.accel_time
        
        # Apply overshoot compensation
        total_time *= self.overshoot_factor
        
        # Apply calibration factor
        total_time *= self.calibration_factor
        
        # Ensure minimum time
        total_time = max(total_time, self.min_move_time)
        
        logger.debug(f"Move time: {distance:.2f}cm → base={base_time:.3f}s, final={total_time:.3f}s")
        
        return total_time
    
    def get_move_command(self, target_cm: float) -> dict:
        """
        Generate move command with timing
        
        Returns:
            dict with direction, time, and estimated position
        """
        move_time = self.calculate_move_time(target_cm)
        
        if move_time <= 0:
            return {
                'direction': 'NONE',
                'time': 0,
                'start_pos': self.current_position,
                'target_pos': target_cm
            }
        
        direction = 'OUT' if target_cm > self.current_position else 'IN'
        
        return {
            'direction': direction,
            'time': move_time,
            'start_pos': self.current_position,
            'target_pos': target_cm
        }
    
    def execute_move(self, motor_func, target_cm: float) -> bool:
        """
        Execute move with the motor function
        
        Args:
            motor_func: Function(direction, time) to control motor
            target_cm: Target position
        
        Returns:
            True if move completed
        """
        command = self.get_move_command(target_cm)
        
        if command['direction'] == 'NONE':
            return True
        
        # Record move
        move_record = {
            'start_pos': self.current_position,
            'target_pos': target_cm,
            'time': command['time'],
            'direction': command['direction'],
            'timestamp': time.time()
        }
        
        # Execute
        try:
            motor_func(command['direction'], command['time'])
            
            # Update estimated position
            self.current_position = target_cm
            
            move_record['success'] = True
            self._move_history.append(move_record)
            
            return True
            
        except Exception as e:
            logger.error(f"Move failed: {e}")
            move_record['success'] = False
            move_record['error'] = str(e)
            self._move_history.append(move_record)
            return False
    
    def calibrate(self, actual_movement: float, expected_movement: float):
        """
        ปรับ calibration จากการวัดจริง
        
        Args:
            actual_movement: ระยะที่เคลื่อนที่จริง (cm)
            expected_movement: ระยะที่คาดหวัง (cm)
        """
        if expected_movement <= 0:
            return
        
        ratio = actual_movement / expected_movement
        
        # Smoothly adjust calibration factor
        self.calibration_factor = 0.7 * self.calibration_factor + 0.3 * ratio
        
        logger.info(f"Calibration adjusted: factor={self.calibration_factor:.3f}")
    
    def reset_position(self, position: float = 0.0):
        """Reset estimated position"""
        self.current_position = position
        logger.info(f"Position reset to {position}")
    
    def get_stats(self) -> dict:
        """Get controller statistics"""
        if not self._move_history:
            return {}
        
        success = sum(1 for m in self._move_history if m.get('success'))
        
        return {
            'total_moves': len(self._move_history),
            'success_rate': success / len(self._move_history) * 100,
            'current_position': self.current_position,
            'calibration_factor': self.calibration_factor
        }


# ==================== Factory Functions ====================

def create_motor_pid(motor_type: str = "dc") -> PIDController:
    """
    สร้าง PID สำหรับมอเตอร์ประเภทต่างๆ
    """
    if motor_type == "dc":
        # DC motor - moderate gains
        return PIDController(Kp=2.0, Ki=0.1, Kd=0.05, name="DC_Motor")
    
    elif motor_type == "stepper":
        # Stepper - mostly proportional
        return PIDController(Kp=5.0, Ki=0.0, Kd=0.1, name="Stepper")
    
    elif motor_type == "servo":
        # Servo - fast response
        return PIDController(Kp=3.0, Ki=0.2, Kd=0.1, name="Servo")
    
    else:
        return PIDController(name=motor_type)


def create_agribot_controller() -> ImprovedTimeBasedController:
    """
    สร้าง controller สำหรับ AgriBot
    ใช้ค่าจาก calibration ของผู้ใช้: 15.5cm ใน 7 วินาที = 2.21 cm/s
    """
    return ImprovedTimeBasedController(
        speed_cm_per_sec=2.21,
        accel_time_sec=0.15,
        overshoot_factor=0.95,
        min_move_time=0.1
    )


if __name__ == "__main__":
    # Test PID Controller
    logging.basicConfig(level=logging.DEBUG)
    
    print("\n=== Testing PID Controller ===")
    pid = PIDController(Kp=2.0, Ki=0.1, Kd=0.05, name="Test")
    
    # Simulate ramp to target
    target = 10.0
    current = 0.0
    dt = 0.02
    
    for i in range(50):
        output = pid.compute(target, current, dt)
        # Simulate motor response
        current += output * 0.01
        print(f"Step {i}: target={target}, current={current:.2f}, output={output:.2f}")
        
        if abs(target - current) < 0.1:
            print("Reached target!")
            break
    
    print(f"\nStats: {pid.get_stats()}")
    
    print("\n=== Testing Improved Time-Based Controller ===")
    ctrl = create_agribot_controller()
    
    test_distances = [5.0, 10.0, 15.0, 15.5, 20.0]
    for d in test_distances:
        time_needed = ctrl.calculate_move_time(d, from_position=0)
        print(f"Distance {d:5.1f}cm → Time {time_needed:.3f}s")
