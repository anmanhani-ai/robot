"""
inverse_kinematics.py
Inverse Kinematics Engine สำหรับคำนวณมุมข้อต่อจากตำแหน่งเป้าหมาย

รองรับ:
- 2-DOF Linear-Rotary (ระบบปัจจุบัน: Z ยืด/หด + Y ขึ้น/ลง)
- 2-DOF Planar Arm (แบบ 2 ข้อหมุน)
- 3-DOF Articulated Arm (อนาคต)

Author: AgriBot Team
Created: 2026-01-21
"""

import numpy as np
from dataclasses import dataclass, field
from typing import Tuple, List, Optional, Dict
from enum import Enum
import logging

logger = logging.getLogger(__name__)


class JointType(Enum):
    """ประเภทของข้อต่อ"""
    LINEAR = "linear"      # เคลื่อนที่เป็นเส้นตรง (cm)
    ROTARY = "rotary"      # หมุน (degrees)
    PRISMATIC = "prismatic"  # Linear on rail


@dataclass
class Joint:
    """Configuration ของข้อต่อแต่ละตัว"""
    name: str
    type: JointType
    min_value: float       # ค่าต่ำสุด (cm หรือ degrees)
    max_value: float       # ค่าสูงสุด
    speed: float           # ความเร็ว (cm/s หรือ deg/s)
    home_value: float = 0.0  # ตำแหน่ง home
    current_value: float = 0.0  # ตำแหน่งปัจจุบัน
    
    def clamp(self, value: float) -> float:
        """จำกัดค่าให้อยู่ในช่วงที่กำหนด"""
        return np.clip(value, self.min_value, self.max_value)
    
    def time_to_move(self, target: float) -> float:
        """คำนวณเวลาที่ใช้เคลื่อนที่ไปยังเป้าหมาย"""
        distance = abs(target - self.current_value)
        return distance / self.speed if self.speed > 0 else 0
    
    def is_reachable(self, value: float) -> bool:
        """ตรวจสอบว่าค่าอยู่ในช่วงที่เข้าถึงได้"""
        return self.min_value <= value <= self.max_value


@dataclass
class IKSolution:
    """ผลลัพธ์จากการคำนวณ Inverse Kinematics"""
    joint_values: Dict[str, float]  # {joint_name: target_value}
    joint_times: Dict[str, float]   # {joint_name: time_seconds}
    reachable: bool = True
    total_time: float = 0.0
    error_message: str = ""
    
    # Debug info
    target_position: Tuple[float, float, float] = (0, 0, 0)
    calculated_position: Tuple[float, float, float] = (0, 0, 0)
    position_error: float = 0.0


class InverseKinematics:
    """
    Inverse Kinematics Engine
    
    คำนวณค่าข้อต่อจากตำแหน่งเป้าหมาย (x, y, z) ในหน่วย cm
    """
    
    def __init__(self, joints: List[Joint], base_position: Tuple[float, float, float] = (0, 0, 0)):
        """
        Args:
            joints: รายการข้อต่อ
            base_position: ตำแหน่งฐานแขนกล (x, y, z) cm
        """
        self.joints = {j.name: j for j in joints}
        self.joint_order = [j.name for j in joints]
        self.base = np.array(base_position)
        
        logger.info(f"IK Engine initialized with {len(joints)} joints")
        for j in joints:
            logger.info(f"  - {j.name}: {j.type.value}, range [{j.min_value}, {j.max_value}]")
    
    def solve(self, x: float, y: float, z: float) -> IKSolution:
        """
        คำนวณ Inverse Kinematics (เลือก solver ตามจำนวน DOF)
        
        Args:
            x, y, z: ตำแหน่งเป้าหมาย (cm)
        
        Returns:
            IKSolution object
        """
        # Adjust for base position
        target = np.array([x, y, z]) - self.base
        
        num_joints = len(self.joints)
        
        if num_joints == 2:
            # Check joint types
            joint_types = [self.joints[n].type for n in self.joint_order]
            
            if joint_types == [JointType.LINEAR, JointType.ROTARY]:
                return self._solve_linear_rotary(target[0], target[1], target[2])
            elif all(t == JointType.ROTARY for t in joint_types):
                return self._solve_2dof_planar(target[0], target[1])
        
        elif num_joints == 3:
            return self._solve_3dof_articulated(target[0], target[1], target[2])
        
        # Fallback: simple solution
        return self._solve_simple(target[0], target[1], target[2])
    
    def _solve_linear_rotary(self, x: float, y: float, z: float) -> IKSolution:
        """
        2-DOF: Linear (Z-axis) + Rotary (Y-axis)
        
        ระบบปัจจุบัน:
        - Joint 0 (Z): ยืด/หดแนวราบ
        - Joint 1 (Y): ขึ้น/ลง (หมุน)
        
        Geometry:
        - Z extension = horizontal distance to target
        - Y angle = angle from horizontal to reach target height
        """
        j_z = self.joints[self.joint_order[0]]
        j_y = self.joints[self.joint_order[1]]
        
        # Calculate horizontal distance
        horizontal_dist = np.sqrt(x**2 + y**2)
        
        # Z extension needed
        z_value = j_z.clamp(horizontal_dist)
        
        # Y angle to reach target height
        if z_value > 0:
            # arctan(height / distance)
            y_angle = np.degrees(np.arctan2(-z, z_value))  # Negative z because down is positive angle
        else:
            y_angle = 0
        y_value = j_y.clamp(y_angle)
        
        # Calculate times
        z_time = j_z.time_to_move(z_value)
        y_time = j_y.time_to_move(y_value)
        
        # Check reachability
        reachable = (
            j_z.is_reachable(horizontal_dist) and 
            abs(y_angle) <= max(abs(j_y.min_value), abs(j_y.max_value))
        )
        
        # Create solution
        solution = IKSolution(
            joint_values={j_z.name: z_value, j_y.name: y_value},
            joint_times={j_z.name: z_time, j_y.name: y_time},
            reachable=reachable,
            total_time=max(z_time, y_time),  # Parallel movement
            target_position=(x, y, z)
        )
        
        if not reachable:
            solution.error_message = f"Target out of reach: need {horizontal_dist:.1f}cm, max {j_z.max_value}cm"
        
        logger.debug(f"IK Solution: Z={z_value:.2f}cm ({z_time:.2f}s), Y={y_value:.1f}° ({y_time:.2f}s)")
        
        return solution
    
    def _solve_2dof_planar(self, x: float, y: float, L1: float = None, L2: float = None) -> IKSolution:
        """
        2-DOF Planar Arm (2 rotary joints)
        
        Standard 2-link inverse kinematics using geometric approach
        
        Args:
            x, y: Target position in plane
            L1, L2: Link lengths (if None, estimated from joint limits)
        """
        j1 = self.joints[self.joint_order[0]]
        j2 = self.joints[self.joint_order[1]]
        
        # Estimate link lengths from joint limits if not provided
        if L1 is None:
            L1 = 10.0  # Default 10cm
        if L2 is None:
            L2 = 10.0
        
        d = np.sqrt(x**2 + y**2)
        
        # Check reachability
        if d > (L1 + L2) or d < abs(L1 - L2):
            return IKSolution(
                joint_values={j1.name: j1.current_value, j2.name: j2.current_value},
                joint_times={j1.name: 0, j2.name: 0},
                reachable=False,
                error_message=f"Target ({x:.1f}, {y:.1f}) unreachable with L1={L1}, L2={L2}"
            )
        
        # Elbow angle (θ2)
        cos_theta2 = (d**2 - L1**2 - L2**2) / (2 * L1 * L2)
        cos_theta2 = np.clip(cos_theta2, -1, 1)
        theta2 = np.arccos(cos_theta2)  # Elbow down solution
        
        # Shoulder angle (θ1)
        beta = np.arctan2(y, x)
        alpha = np.arctan2(L2 * np.sin(theta2), L1 + L2 * np.cos(theta2))
        theta1 = beta - alpha
        
        # Convert to degrees
        theta1_deg = np.degrees(theta1)
        theta2_deg = np.degrees(theta2)
        
        # Clamp to joint limits
        theta1_deg = j1.clamp(theta1_deg)
        theta2_deg = j2.clamp(theta2_deg)
        
        # Calculate times
        t1 = j1.time_to_move(theta1_deg)
        t2 = j2.time_to_move(theta2_deg)
        
        return IKSolution(
            joint_values={j1.name: theta1_deg, j2.name: theta2_deg},
            joint_times={j1.name: t1, j2.name: t2},
            reachable=True,
            total_time=max(t1, t2),
            target_position=(x, y, 0)
        )
    
    def _solve_3dof_articulated(self, x: float, y: float, z: float) -> IKSolution:
        """
        3-DOF Articulated Arm
        
        Joint 0: Base rotation (around Z-axis)
        Joint 1: Shoulder (around Y-axis)
        Joint 2: Elbow (around Y-axis)
        """
        j_base = self.joints[self.joint_order[0]]
        j_shoulder = self.joints[self.joint_order[1]]
        j_elbow = self.joints[self.joint_order[2]]
        
        # Link lengths (assumed from joint config or defaults)
        L1 = 10.0  # Shoulder to elbow
        L2 = 10.0  # Elbow to end effector
        
        # Base rotation
        theta_base = np.degrees(np.arctan2(y, x))
        theta_base = j_base.clamp(theta_base)
        
        # Project onto vertical plane through target
        r = np.sqrt(x**2 + y**2)  # Horizontal distance
        
        # Solve 2-DOF planar IK in the vertical plane
        d = np.sqrt(r**2 + z**2)
        
        if d > (L1 + L2) or d < abs(L1 - L2):
            return IKSolution(
                joint_values={j.name: j.current_value for j in [j_base, j_shoulder, j_elbow]},
                joint_times={j.name: 0 for j in [j_base, j_shoulder, j_elbow]},
                reachable=False,
                error_message=f"Target unreachable at distance {d:.1f}cm"
            )
        
        # Elbow angle
        cos_theta_elbow = (d**2 - L1**2 - L2**2) / (2 * L1 * L2)
        theta_elbow = np.degrees(np.arccos(np.clip(cos_theta_elbow, -1, 1)))
        
        # Shoulder angle
        beta = np.arctan2(z, r)
        alpha = np.arctan2(L2 * np.sin(np.radians(theta_elbow)), 
                          L1 + L2 * np.cos(np.radians(theta_elbow)))
        theta_shoulder = np.degrees(beta + alpha)
        
        # Clamp to limits
        theta_shoulder = j_shoulder.clamp(theta_shoulder)
        theta_elbow = j_elbow.clamp(theta_elbow)
        
        # Times
        t_base = j_base.time_to_move(theta_base)
        t_shoulder = j_shoulder.time_to_move(theta_shoulder)
        t_elbow = j_elbow.time_to_move(theta_elbow)
        
        return IKSolution(
            joint_values={
                j_base.name: theta_base,
                j_shoulder.name: theta_shoulder,
                j_elbow.name: theta_elbow
            },
            joint_times={
                j_base.name: t_base,
                j_shoulder.name: t_shoulder,
                j_elbow.name: t_elbow
            },
            reachable=True,
            total_time=max(t_base, t_shoulder, t_elbow),
            target_position=(x, y, z)
        )
    
    def _solve_simple(self, x: float, y: float, z: float) -> IKSolution:
        """
        Simple fallback solver
        Maps x, y, z directly to joints in order
        """
        solution = IKSolution(
            joint_values={},
            joint_times={},
            reachable=True,
            target_position=(x, y, z)
        )
        
        targets = [x, y, z]
        for i, name in enumerate(self.joint_order):
            if i < len(targets):
                j = self.joints[name]
                value = j.clamp(targets[i])
                solution.joint_values[name] = value
                solution.joint_times[name] = j.time_to_move(value)
        
        solution.total_time = max(solution.joint_times.values()) if solution.joint_times else 0
        
        return solution
    
    def forward_kinematics(self, joint_values: Dict[str, float]) -> Tuple[float, float, float]:
        """
        Forward Kinematics: คำนวณตำแหน่งจากมุมข้อต่อ
        
        Args:
            joint_values: {joint_name: value}
        
        Returns:
            (x, y, z) position in cm
        """
        # For linear-rotary system
        if len(self.joints) == 2:
            z_name, y_name = self.joint_order
            z_ext = joint_values.get(z_name, 0)
            y_ang = joint_values.get(y_name, 0)
            
            # Convert Y angle to radians
            y_rad = np.radians(y_ang)
            
            # Calculate position
            x = z_ext * np.cos(y_rad)
            y = 0  # Assuming arm moves in XZ plane
            z = -z_ext * np.sin(y_rad)  # Negative because down is positive angle
            
            return (x + self.base[0], y + self.base[1], z + self.base[2])
        
        # Default: return base position
        return tuple(self.base)
    
    def get_joint_commands(self, solution: IKSolution) -> List[str]:
        """
        สร้างคำสั่งสำหรับส่งไป ESP32
        
        Returns:
            List of command strings
        """
        commands = []
        
        for name in self.joint_order:
            if name not in solution.joint_values:
                continue
            
            j = self.joints[name]
            target = solution.joint_values[name]
            time_sec = solution.joint_times[name]
            
            if j.type == JointType.LINEAR:
                # Linear movement: ACT:{axis}:{direction}:{time}
                direction = "OUT" if target > j.current_value else "IN"
                commands.append(f"ACT:Z_{direction}:{time_sec:.2f}")
            
            elif j.type == JointType.ROTARY:
                # Rotary movement: ACT:{axis}:{direction}
                if "Y" in name.upper():
                    direction = "DOWN" if target > j.current_value else "UP"
                    commands.append(f"ACT:Y_{direction}")
        
        return commands


# ==================== Factory Functions ====================

def create_agribot_ik() -> InverseKinematics:
    """
    สร้าง IK Engine สำหรับ AgriBot (2-DOF: Z linear + Y rotary)
    
    ใช้ค่าจาก calibration.json
    """
    joints = [
        Joint(
            name="Z",
            type=JointType.LINEAR,
            min_value=0.0,
            max_value=15.5,  # cm (from user: แขนยืดได้ 15.5cm)
            speed=2.21,      # cm/s (15.5cm / 7s)
            home_value=0.0
        ),
        Joint(
            name="Y",
            type=JointType.ROTARY,
            min_value=-90.0,  # degrees (up)
            max_value=90.0,   # degrees (down)
            speed=45.0,       # deg/s (estimate)
            home_value=0.0
        )
    ]
    
    # Base offset: camera distance from arm base
    base_offset = (9.0, 0.0, 0.0)  # camera_offset_cm from calibration
    
    return InverseKinematics(joints, base_position=base_offset)


def create_3dof_arm_ik(L1: float = 10.0, L2: float = 10.0) -> InverseKinematics:
    """
    สร้าง IK Engine สำหรับแขน 3-DOF
    """
    joints = [
        Joint(
            name="Base",
            type=JointType.ROTARY,
            min_value=-180.0,
            max_value=180.0,
            speed=60.0
        ),
        Joint(
            name="Shoulder",
            type=JointType.ROTARY,
            min_value=-45.0,
            max_value=135.0,
            speed=45.0
        ),
        Joint(
            name="Elbow",
            type=JointType.ROTARY,
            min_value=0.0,
            max_value=150.0,
            speed=60.0
        )
    ]
    
    return InverseKinematics(joints)


if __name__ == "__main__":
    # Test IK engine
    logging.basicConfig(level=logging.DEBUG)
    
    print("\n=== Testing AgriBot IK (2-DOF Linear-Rotary) ===")
    ik = create_agribot_ik()
    
    # Test cases
    test_targets = [
        (10.0, 0.0, 0.0),   # Forward 10cm
        (15.0, 0.0, 0.0),   # Forward 15cm (near max)
        (10.0, 0.0, -5.0),  # Forward 10cm, down 5cm
        (20.0, 0.0, 0.0),   # Beyond reach
    ]
    
    for x, y, z in test_targets:
        solution = ik.solve(x, y, z)
        print(f"\nTarget: ({x}, {y}, {z}) cm")
        print(f"  Reachable: {solution.reachable}")
        print(f"  Joint values: {solution.joint_values}")
        print(f"  Times: {solution.joint_times}")
        print(f"  Total time: {solution.total_time:.2f}s")
        if solution.error_message:
            print(f"  Error: {solution.error_message}")
        
        # Get commands
        commands = ik.get_joint_commands(solution)
        print(f"  Commands: {commands}")
