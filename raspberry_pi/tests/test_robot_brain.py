"""
Test Robot Brain Physics Calculations
"""
import pytest
import sys
from pathlib import Path

# Add parent to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from robot_brain import RobotBrain, CalibrationConfig


class TestPhysicsCalculations:
    """ทดสอบการคำนวณฟิสิกส์"""
    
    @pytest.fixture
    def brain(self):
        """สร้าง RobotBrain สำหรับทดสอบ"""
        config = CalibrationConfig()
        config.pixel_to_cm_z = 0.05      # 1px = 0.05cm
        config.pixel_to_cm_x = 0.05
        config.arm_speed_cm_per_sec = 10.0
        config.arm_base_offset_cm = 5.0
        config.wheel_speed_cm_per_sec = 20.0
        config.alignment_tolerance_px = 30
        config.max_arm_extend_time = 5.0
        return RobotBrain(config)
    
    def test_calculate_z_distance_basic(self, brain):
        """ทดสอบการคำนวณระยะ Z แบบพื้นฐาน"""
        # 200 pixels = 10cm, ลบ offset 5cm = 5cm
        # เวลา = 5cm / 10cm/s = 0.5s
        time_sec, distance_cm = brain.calculate_z_distance(200)
        
        assert distance_cm == pytest.approx(5.0, rel=0.01)
        assert time_sec == pytest.approx(0.5, rel=0.01)
    
    def test_calculate_z_distance_negative(self, brain):
        """ระยะลบก็คำนวณได้ (ใช้ abs)"""
        time_sec, distance_cm = brain.calculate_z_distance(-200)
        
        assert distance_cm == pytest.approx(5.0, rel=0.01)
        assert time_sec == pytest.approx(0.5, rel=0.01)
    
    def test_calculate_z_distance_too_close(self, brain):
        """เมื่อระยะน้อยกว่า offset"""
        # 50 pixels = 2.5cm, ลบ offset 5cm = 0cm (ใกล้เกิน)
        time_sec, distance_cm = brain.calculate_z_distance(50)
        
        assert distance_cm == 0.0
        assert time_sec == 0.0
    
    def test_calculate_z_distance_max_limit(self, brain):
        """เวลาต้องไม่เกิน max limit"""
        # 5000 pixels = 250cm → จะใช้เวลานานมาก แต่ต้อง clamp
        time_sec, _ = brain.calculate_z_distance(5000)
        
        assert time_sec <= brain.config.max_arm_extend_time
    
    def test_calculate_x_movement_forward(self, brain):
        """ทดสอบการเคลื่อนที่ X ไปข้างหน้า"""
        direction, time_sec = brain.calculate_x_movement(100)
        
        assert direction == "FW"
        # 100px * 0.05 = 5cm / 20cm/s = 0.25s
        assert time_sec == pytest.approx(0.25, rel=0.01)
    
    def test_calculate_x_movement_backward(self, brain):
        """ทดสอบการเคลื่อนที่ X ถอยหลัง"""
        direction, time_sec = brain.calculate_x_movement(-100)
        
        assert direction == "BW"
        assert time_sec == pytest.approx(0.25, rel=0.01)
    
    def test_is_aligned_within_tolerance(self, brain):
        """อยู่ในระยะ tolerance = aligned"""
        assert brain.is_aligned(0) == True
        assert brain.is_aligned(30) == True
        assert brain.is_aligned(-30) == True
    
    def test_is_aligned_outside_tolerance(self, brain):
        """อยู่นอกระยะ tolerance = not aligned"""
        assert brain.is_aligned(31) == False
        assert brain.is_aligned(-31) == False
        assert brain.is_aligned(100) == False
    
    def test_calculate_approach_speed_zones(self, brain):
        """ทดสอบการคำนวณความเร็วตาม zone"""
        # FAR_ZONE (>200) = SPEED_MAX
        speed_far = brain.calculate_approach_speed(250)
        assert speed_far == brain.SPEED_MAX
        
        # ใกล้มาก (<tolerance) = 0
        speed_aligned = brain.calculate_approach_speed(10)
        assert speed_aligned == 0
        
        # กลางๆ ต้องอยู่ระหว่าง
        speed_mid = brain.calculate_approach_speed(75)
        assert brain.SPEED_CREEP < speed_mid < brain.SPEED_MAX


class TestCoordinateSystem:
    """ทดสอบระบบพิกัดใหม่"""
    
    @pytest.fixture
    def brain(self):
        config = CalibrationConfig()
        config.pixel_to_cm_x = 0.05
        config.pixel_to_cm_z = 0.05
        config.arm_speed_cm_per_sec = 2.17
        config.wheel_speed_cm_per_sec = 20.0
        return RobotBrain(config)
    
    def test_coord_x_positive_is_forward(self, brain):
        """X+ = Forward"""
        direction, _ = brain.calculate_coord_x_movement(100)
        assert direction == "FW"
    
    def test_coord_x_negative_is_backward(self, brain):
        """X- = Backward"""
        direction, _ = brain.calculate_coord_x_movement(-100)
        assert direction == "BW"
    
    def test_calculate_y_from_bottom(self, brain):
        """ทดสอบการคำนวณ Y จากขอบล่าง"""
        # 100 pixels from bottom
        distance_cm, time_sec = brain.calculate_y_from_bottom(100)
        
        # 100 * 0.05 = 5cm
        assert distance_cm == pytest.approx(5.0, rel=0.01)
        
        # 5cm / 2.17cm/s ≈ 2.3s
        assert time_sec == pytest.approx(2.3, rel=0.1)


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
