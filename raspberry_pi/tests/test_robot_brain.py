"""
Test Robot Brain Physics Calculations - Updated for new flow
"""
import pytest
import sys
from pathlib import Path

# Add parent to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from robot_brain import RobotBrain, CalibrationConfig


class TestFlowMethods:
    """ทดสอบ Flow Methods ที่ออกแบบใหม่"""
    
    @pytest.fixture
    def brain(self):
        """สร้าง RobotBrain สำหรับทดสอบ"""
        config = CalibrationConfig()
        config.img_width = 640
        config.img_height = 480
        config.pixel_to_cm_z = 0.05
        config.pixel_to_cm_x = 0.05
        config.arm_speed_cm_per_sec = 2.17
        config.wheel_speed_cm_per_sec = 2.17
        config.arm_base_offset_cm = 8.5
        config.max_arm_extend_time = 7.5
        return RobotBrain(config)
    
    def test_calculate_align_to_y_axis_forward(self, brain):
        """วัตถุอยู่ขวาภาพ (X > 320) = ต้องเดินหน้า"""
        target_x = 420  # 100px ขวาของกลาง
        direction, time_sec = brain.calculate_align_to_y_axis(target_x)
        
        assert direction == "FW"
        # 100px * 0.05 = 5cm / 2.17 cm/s ≈ 2.3s
        assert time_sec == pytest.approx(2.3, rel=0.1)
    
    def test_calculate_align_to_y_axis_backward(self, brain):
        """วัตถุอยู่ซ้ายภาพ (X < 320) = ต้องถอยหลัง"""
        target_x = 220  # 100px ซ้ายของกลาง
        direction, time_sec = brain.calculate_align_to_y_axis(target_x)
        
        assert direction == "BW"
        assert time_sec == pytest.approx(2.3, rel=0.1)
    
    def test_calculate_align_to_y_axis_centered(self, brain):
        """วัตถุอยู่กลางพอดี = เวลา ≈ 0"""
        target_x = 320
        direction, time_sec = brain.calculate_align_to_y_axis(target_x)
        
        assert time_sec == pytest.approx(0.0, abs=0.01)
    
    def test_calculate_z_from_image_y_top(self, brain):
        """วัตถุอยู่บนภาพ (Y=0) = ไกลจากรถ = ยืดมาก"""
        target_y = 0
        z_cm, z_time = brain.calculate_z_from_image_y(target_y)
        
        # distance_from_bottom = 480 - 0 = 480px
        # 480 * 0.05 = 24cm / 2.17 ≈ 11s → แต่ max = 7.5s
        assert z_time == brain.config.max_arm_extend_time
    
    def test_calculate_z_from_image_y_bottom(self, brain):
        """วัตถุอยู่ล่างภาพ (Y=480) = ใกล้รถ = ยืดน้อย"""
        target_y = 480
        z_cm, z_time = brain.calculate_z_from_image_y(target_y)
        
        # distance_from_bottom = 480 - 480 = 0px
        assert z_cm == 0.0
        assert z_time == 0.0
    
    def test_calculate_z_from_image_y_middle(self, brain):
        """วัตถุอยู่กลางภาพ (Y=240)"""
        target_y = 240
        z_cm, z_time = brain.calculate_z_from_image_y(target_y)
        
        # distance_from_bottom = 480 - 240 = 240px
        # 240 * 0.05 = 12cm / 2.17 ≈ 5.5s
        assert z_cm == pytest.approx(12.0, rel=0.01)
        assert z_time == pytest.approx(5.5, rel=0.1)
    
    def test_get_camera_offset_time(self, brain):
        """ทดสอบการคำนวณ camera offset"""
        offset_time = brain.get_camera_offset_time()
        
        # 8.5cm / 2.17 cm/s ≈ 3.9s
        assert offset_time == pytest.approx(3.9, rel=0.1)
    
    def test_is_target_behind_robot_true(self, brain):
        """วัตถุ X < 320 = อยู่หลังรถ"""
        assert brain.is_target_behind_robot(100) == True
        assert brain.is_target_behind_robot(319) == True
    
    def test_is_target_behind_robot_false(self, brain):
        """วัตถุ X >= 320 = อยู่หน้ารถ"""
        assert brain.is_target_behind_robot(320) == False
        assert brain.is_target_behind_robot(500) == False


class TestLegacyMethods:
    """ทดสอบ Methods เดิมที่ยังใช้งานได้"""
    
    @pytest.fixture
    def brain(self):
        config = CalibrationConfig()
        config.pixel_to_cm_z = 0.05
        config.arm_speed_cm_per_sec = 2.17
        config.wheel_speed_cm_per_sec = 2.17
        config.alignment_tolerance_px = 30
        return RobotBrain(config)
    
    def test_is_aligned_within_tolerance(self, brain):
        """อยู่ในระยะ tolerance = aligned"""
        assert brain.is_aligned(0) == True
        assert brain.is_aligned(30) == True
        assert brain.is_aligned(-30) == True
    
    def test_is_aligned_outside_tolerance(self, brain):
        """อยู่นอกระยะ tolerance = not aligned"""
        assert brain.is_aligned(31) == False
        assert brain.is_aligned(-31) == False


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
