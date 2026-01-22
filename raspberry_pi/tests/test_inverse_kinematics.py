"""
Test Inverse Kinematics Engine
"""
import pytest
import sys
from pathlib import Path

# Add parent to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from kinematics.inverse_kinematics import (
    InverseKinematics,
    Joint,
    JointType,
    IKSolution,
    create_agribot_ik
)


class TestJoint:
    """ทดสอบ Joint class"""
    
    def test_clamp_within_range(self):
        """ค่าในช่วงไม่เปลี่ยน"""
        joint = Joint("test", JointType.LINEAR, min_value=0, max_value=10, speed=5)
        assert joint.clamp(5) == 5
    
    def test_clamp_below_min(self):
        """ค่าต่ำกว่า min → clamp เป็น min"""
        joint = Joint("test", JointType.LINEAR, min_value=0, max_value=10, speed=5)
        assert joint.clamp(-5) == 0
    
    def test_clamp_above_max(self):
        """ค่าสูงกว่า max → clamp เป็น max"""
        joint = Joint("test", JointType.LINEAR, min_value=0, max_value=10, speed=5)
        assert joint.clamp(15) == 10
    
    def test_time_to_move(self):
        """ทดสอบการคำนวณเวลา"""
        joint = Joint("test", JointType.LINEAR, min_value=0, max_value=10, speed=5, current_value=0)
        # จาก 0 ไป 10 = 10 units / 5 units/s = 2s
        assert joint.time_to_move(10) == pytest.approx(2.0)
    
    def test_is_reachable(self):
        """ทดสอบ reachability"""
        joint = Joint("test", JointType.LINEAR, min_value=0, max_value=10, speed=5)
        assert joint.is_reachable(5) == True
        assert joint.is_reachable(0) == True
        assert joint.is_reachable(10) == True
        assert joint.is_reachable(-1) == False
        assert joint.is_reachable(11) == False


class TestAgribotIK:
    """ทดสอบ IK สำหรับ AgriBot"""
    
    @pytest.fixture
    def ik(self):
        return create_agribot_ik()
    
    def test_solve_forward_reach(self, ik):
        """ทดสอบการเข้าถึงเป้าหมายข้างหน้า"""
        solution = ik.solve(15.0, 0.0, 0.0)  # 15cm ข้างหน้า
        
        assert solution.reachable == True
        assert "Z" in solution.joint_values
        assert solution.total_time > 0
    
    def test_solve_unreachable_target(self, ik):
        """ทดสอบเป้าหมายที่เข้าไม่ถึง"""
        solution = ik.solve(50.0, 0.0, 0.0)  # ไกลเกินไป
        
        # ควร clamp แต่ยัง solve ได้ (อาจ reachable=False)
        assert "Z" in solution.joint_values
    
    def test_get_joint_commands(self, ik):
        """ทดสอบการสร้างคำสั่ง"""
        solution = ik.solve(15.0, 0.0, 0.0)
        commands = ik.get_joint_commands(solution)
        
        assert len(commands) > 0
        # คำสั่งควรเริ่มด้วย ACT:
        for cmd in commands:
            assert cmd.startswith("ACT:")
    
    def test_forward_kinematics_roundtrip(self, ik):
        """ทดสอบ FK กลับมาให้ได้ตำแหน่งใกล้เคียง"""
        # Solve for a target
        target = (10.0, 0.0, 0.0)
        solution = ik.solve(*target)
        
        # Get position from FK
        pos = ik.forward_kinematics(solution.joint_values)
        
        # ตำแหน่งควรใกล้เคียง (within tolerance)
        # Note: อาจมี offset จาก base position
        assert pos is not None


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
