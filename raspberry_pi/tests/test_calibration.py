"""
Test Calibration Config Loading
"""
import pytest
import json
import tempfile
from pathlib import Path
import sys

# Add parent to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from robot_brain import CalibrationConfig


class TestCalibrationConfig:
    """ทดสอบการโหลด Calibration Config"""
    
    def test_default_values(self):
        """ทดสอบค่า default เมื่อไม่มีไฟล์ config"""
        config = CalibrationConfig()
        
        assert config.img_width == 640
        assert config.img_height == 480
        assert config.pixel_to_cm_z == 0.05
        assert config.arm_speed_cm_per_sec == 10.0
        assert config.baud_rate == 115200
    
    def test_load_from_file(self, tmp_path):
        """ทดสอบการโหลดจากไฟล์ JSON"""
        # สร้างไฟล์ config ชั่วคราว
        config_data = {
            "pixel_to_cm_z": 0.08,
            "arm_speed_cm_per_sec": 3.5,
            "img_width": 1280,
            "img_height": 720
        }
        
        config_file = tmp_path / "test_calibration.json"
        with open(config_file, 'w') as f:
            json.dump(config_data, f)
        
        # โหลด config
        config = CalibrationConfig.load_from_file(config_file)
        
        assert config.pixel_to_cm_z == 0.08
        assert config.arm_speed_cm_per_sec == 3.5
        assert config.img_width == 1280
        assert config.img_height == 720
    
    def test_load_missing_file_uses_defaults(self):
        """เมื่อไฟล์ไม่มี ใช้ค่า default"""
        config = CalibrationConfig.load_from_file(Path("/nonexistent/path.json"))
        
        assert config.pixel_to_cm_z == 0.05
        assert config.img_width == 640
    
    def test_img_center_properties(self):
        """ทดสอบ computed properties"""
        config = CalibrationConfig()
        config.img_width = 640
        config.img_height = 480
        
        assert config.img_center_x == 320
        assert config.img_center_y == 240
    
    def test_partial_config_file(self, tmp_path):
        """ทดสอบไฟล์ config ที่มีแค่บางค่า"""
        config_data = {
            "pixel_to_cm_z": 0.1
            # ไม่มีค่าอื่นๆ
        }
        
        config_file = tmp_path / "partial_config.json"
        with open(config_file, 'w') as f:
            json.dump(config_data, f)
        
        config = CalibrationConfig.load_from_file(config_file)
        
        # ค่าที่มีในไฟล์
        assert config.pixel_to_cm_z == 0.1
        
        # ค่าที่ไม่มีในไฟล์ ใช้ default
        assert config.arm_speed_cm_per_sec == 10.0


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
