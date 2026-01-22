"""
camera_calibration.py
Camera Calibration Module สำหรับแปลง pixel coordinates → world coordinates

Author: AgriBot Team
Created: 2026-01-21
"""

import numpy as np
import cv2
import json
from pathlib import Path
from dataclasses import dataclass
from typing import Tuple, Optional
import logging

logger = logging.getLogger(__name__)


@dataclass
class CameraConfig:
    """Camera intrinsic and extrinsic parameters"""
    # Image size
    width: int = 640
    height: int = 480
    
    # Intrinsic parameters (focal length and principal point)
    fx: float = 600.0  # Focal length x (pixels)
    fy: float = 600.0  # Focal length y (pixels)
    cx: float = 320.0  # Principal point x (pixels)
    cy: float = 240.0  # Principal point y (pixels)
    
    # Distortion coefficients (k1, k2, p1, p2, k3)
    distortion: tuple = (0.0, 0.0, 0.0, 0.0, 0.0)
    
    # Extrinsic parameters
    camera_height_cm: float = 50.0   # Height from workspace
    camera_angle_deg: float = 45.0   # Tilt angle from vertical
    
    # Workspace offset (camera position relative to arm base)
    offset_x_cm: float = 0.0
    offset_y_cm: float = 0.0
    offset_z_cm: float = 0.0
    
    @property
    def intrinsic_matrix(self) -> np.ndarray:
        """Get camera intrinsic matrix K (3x3)"""
        return np.array([
            [self.fx, 0, self.cx],
            [0, self.fy, self.cy],
            [0, 0, 1]
        ], dtype=np.float64)
    
    @property
    def distortion_coeffs(self) -> np.ndarray:
        """Get distortion coefficients"""
        return np.array(self.distortion, dtype=np.float64)
    
    @classmethod
    def load_from_file(cls, filepath: str) -> 'CameraConfig':
        """Load config from JSON file"""
        with open(filepath, 'r') as f:
            data = json.load(f)
        
        return cls(
            width=data.get('img_width', 640),
            height=data.get('img_height', 480),
            fx=data.get('fx', 600.0),
            fy=data.get('fy', 600.0),
            cx=data.get('cx', 320.0),
            cy=data.get('cy', 240.0),
            distortion=tuple(data.get('distortion', [0, 0, 0, 0, 0])),
            camera_height_cm=data.get('camera_height_cm', 50.0),
            camera_angle_deg=data.get('camera_angle_deg', 45.0),
            offset_x_cm=data.get('offset_x_cm', 0.0),
            offset_y_cm=data.get('offset_y_cm', 0.0),
            offset_z_cm=data.get('offset_z_cm', 0.0),
        )
    
    def save_to_file(self, filepath: str):
        """Save config to JSON file"""
        data = {
            'img_width': self.width,
            'img_height': self.height,
            'fx': self.fx,
            'fy': self.fy,
            'cx': self.cx,
            'cy': self.cy,
            'distortion': list(self.distortion),
            'camera_height_cm': self.camera_height_cm,
            'camera_angle_deg': self.camera_angle_deg,
            'offset_x_cm': self.offset_x_cm,
            'offset_y_cm': self.offset_y_cm,
            'offset_z_cm': self.offset_z_cm,
        }
        with open(filepath, 'w') as f:
            json.dump(data, f, indent=2)


class CameraCalibration:
    """
    Camera Calibration Class
    
    แปลง pixel coordinates → world coordinates (cm)
    รองรับทั้ง simple projection และ full camera calibration
    """
    
    def __init__(self, config: Optional[CameraConfig] = None, config_file: Optional[str] = None):
        if config:
            self.config = config
        elif config_file:
            self.config = CameraConfig.load_from_file(config_file)
        else:
            self.config = CameraConfig()
        
        # Cache matrices
        self._K = self.config.intrinsic_matrix
        self._dist = self.config.distortion_coeffs
        
        # Precompute values
        self._angle_rad = np.radians(self.config.camera_angle_deg)
        
        logger.info(f"Camera Calibration initialized: {self.config.width}x{self.config.height}")
    
    def pixel_to_world_simple(self, x_px: int, y_px: int, z_world: float = 0.0) -> Tuple[float, float, float]:
        """
        แปลง pixel → world coordinates (Simple Projection)
        
        สมมติ:
        - กล้องมองลงมาที่พื้นราบ (z = z_world)
        - ไม่มี lens distortion
        
        Args:
            x_px: X pixel position
            y_px: Y pixel position
            z_world: Target Z height (default 0 = ground plane)
        
        Returns:
            (x_world, y_world, z_world) in cm
        """
        # Normalize to image center
        x_norm = (x_px - self.config.cx) / self.config.fx
        y_norm = (y_px - self.config.cy) / self.config.fy
        
        # Calculate scale based on camera geometry
        # For camera looking down at angle θ from vertical:
        # - vertical distance = H * cos(θ)
        # - horizontal offset = H * sin(θ)
        
        effective_height = self.config.camera_height_cm - z_world
        
        if self.config.camera_angle_deg < 5:
            # Nearly vertical camera (looking straight down)
            scale = effective_height
        else:
            # Angled camera
            # Adjust for perspective (objects further appear smaller)
            y_angle_offset = y_norm * self._angle_rad * 0.5  # Approximate
            scale = effective_height / np.cos(self._angle_rad + y_angle_offset)
        
        x_world = x_norm * scale + self.config.offset_x_cm
        y_world = y_norm * scale + self.config.offset_y_cm
        
        return (x_world, y_world, z_world)
    
    def pixel_to_world(self, x_px: int, y_px: int, z_world: float = 0.0) -> Tuple[float, float, float]:
        """
        แปลง pixel → world coordinates (Full Calibration)
        
        ใช้ OpenCV undistortion สำหรับ lens distortion correction
        
        Args:
            x_px: X pixel position
            y_px: Y pixel position
            z_world: Target Z height (default 0 = ground plane)
        
        Returns:
            (x_world, y_world, z_world) in cm
        """
        # 1. Undistort point
        pts = np.array([[[x_px, y_px]]], dtype=np.float32)
        
        if np.any(self._dist != 0):
            undistorted = cv2.undistortPoints(pts, self._K, self._dist, P=self._K)
            x_ud, y_ud = undistorted[0][0]
        else:
            x_ud, y_ud = x_px, y_px
        
        # 2. Use simple projection with undistorted point
        return self.pixel_to_world_simple(x_ud, y_ud, z_world)
    
    def world_to_pixel(self, x_world: float, y_world: float, z_world: float = 0.0) -> Tuple[int, int]:
        """
        แปลง world → pixel coordinates (Forward Projection)
        
        Args:
            x_world, y_world, z_world: World coordinates in cm
        
        Returns:
            (x_px, y_px)
        """
        # Adjust for offsets
        x_adj = x_world - self.config.offset_x_cm
        y_adj = y_world - self.config.offset_y_cm
        
        effective_height = self.config.camera_height_cm - z_world
        
        if self.config.camera_angle_deg < 5:
            scale = effective_height
        else:
            scale = effective_height / np.cos(self._angle_rad)
        
        x_norm = x_adj / scale
        y_norm = y_adj / scale
        
        x_px = int(x_norm * self.config.fx + self.config.cx)
        y_px = int(y_norm * self.config.fy + self.config.cy)
        
        return (x_px, y_px)
    
    def calibrate_from_checkerboard(
        self, 
        image_paths: list, 
        pattern_size: Tuple[int, int] = (9, 6),
        square_size_cm: float = 2.5
    ) -> bool:
        """
        Calibrate camera using checkerboard images
        
        Args:
            image_paths: List of paths to calibration images
            pattern_size: (cols, rows) of inner corners
            square_size_cm: Size of each square in cm
        
        Returns:
            True if calibration successful
        """
        # Prepare object points
        objp = np.zeros((pattern_size[0] * pattern_size[1], 3), np.float32)
        objp[:, :2] = np.mgrid[0:pattern_size[0], 0:pattern_size[1]].T.reshape(-1, 2)
        objp *= square_size_cm
        
        obj_points = []  # 3D points in real world
        img_points = []  # 2D points in image plane
        
        for path in image_paths:
            img = cv2.imread(path)
            if img is None:
                logger.warning(f"Could not read image: {path}")
                continue
            
            gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
            
            # Find checkerboard corners
            ret, corners = cv2.findChessboardCorners(gray, pattern_size, None)
            
            if ret:
                # Refine corner positions
                criteria = (cv2.TERM_CRITERIA_EPS + cv2.TERM_CRITERIA_MAX_ITER, 30, 0.001)
                corners2 = cv2.cornerSubPix(gray, corners, (11, 11), (-1, -1), criteria)
                
                obj_points.append(objp)
                img_points.append(corners2)
                logger.info(f"Found corners in: {path}")
            else:
                logger.warning(f"No corners found in: {path}")
        
        if len(obj_points) < 3:
            logger.error("Not enough valid images for calibration (need at least 3)")
            return False
        
        # Calibrate camera
        ret, mtx, dist, rvecs, tvecs = cv2.calibrateCamera(
            obj_points, img_points, gray.shape[::-1], None, None
        )
        
        if ret:
            # Update config
            self.config.fx = mtx[0, 0]
            self.config.fy = mtx[1, 1]
            self.config.cx = mtx[0, 2]
            self.config.cy = mtx[1, 2]
            self.config.distortion = tuple(dist.flatten()[:5])
            
            # Update cached values
            self._K = self.config.intrinsic_matrix
            self._dist = self.config.distortion_coeffs
            
            logger.info(f"Calibration successful! RMS error: {ret:.4f}")
            logger.info(f"fx={self.config.fx:.1f}, fy={self.config.fy:.1f}")
            logger.info(f"cx={self.config.cx:.1f}, cy={self.config.cy:.1f}")
            
            return True
        
        return False
    
    def get_pixel_to_cm_ratio(self, at_distance_cm: Optional[float] = None) -> float:
        """
        คำนวณ ratio: 1 pixel = กี่ cm
        
        Args:
            at_distance_cm: Distance from camera (None = use camera height)
        
        Returns:
            cm per pixel
        """
        distance = at_distance_cm or self.config.camera_height_cm
        
        # Average of fx and fy
        f_avg = (self.config.fx + self.config.fy) / 2
        
        return distance / f_avg
    
    def visualize_calibration(self, image: np.ndarray, target_x: int, target_y: int) -> np.ndarray:
        """
        แสดง visualization ของ calibration บนภาพ
        
        Args:
            image: Input image (BGR)
            target_x, target_y: Target pixel position
        
        Returns:
            Annotated image
        """
        img = image.copy()
        
        # Draw crosshair at center
        cv2.line(img, (self.config.cx - 50, self.config.cy), 
                 (self.config.cx + 50, self.config.cy), (0, 255, 0), 1)
        cv2.line(img, (self.config.cx, self.config.cy - 50), 
                 (self.config.cx, self.config.cy + 50), (0, 255, 0), 1)
        
        # Draw target point
        cv2.circle(img, (target_x, target_y), 8, (0, 0, 255), 2)
        
        # Calculate world position
        x_w, y_w, z_w = self.pixel_to_world(target_x, target_y)
        
        # Draw info text
        info = f"Pixel: ({target_x}, {target_y})"
        cv2.putText(img, info, (10, 30), cv2.FONT_HERSHEY_SIMPLEX, 0.6, (255, 255, 255), 2)
        
        info = f"World: ({x_w:.1f}, {y_w:.1f}, {z_w:.1f}) cm"
        cv2.putText(img, info, (10, 60), cv2.FONT_HERSHEY_SIMPLEX, 0.6, (255, 255, 255), 2)
        
        ratio = self.get_pixel_to_cm_ratio()
        info = f"Scale: {ratio:.4f} cm/px"
        cv2.putText(img, info, (10, 90), cv2.FONT_HERSHEY_SIMPLEX, 0.6, (255, 255, 255), 2)
        
        return img


# ==================== Utility Functions ====================

def quick_calibration(camera_height_cm: float, camera_angle_deg: float = 0.0,
                      image_width: int = 640, image_height: int = 480) -> CameraCalibration:
    """
    สร้าง CameraCalibration แบบเร็วโดยไม่ต้อง calibrate ด้วย checkerboard
    
    Args:
        camera_height_cm: ความสูงกล้องจากพื้นที่ทำงาน
        camera_angle_deg: มุมกล้อง (0 = มองตรงลง)
        image_width, image_height: ขนาดภาพ
    
    Returns:
        CameraCalibration object
    """
    # Estimate focal length from typical webcam FOV (~60 degrees)
    fov_rad = np.radians(60)
    fx = image_width / (2 * np.tan(fov_rad / 2))
    fy = fx  # Assume square pixels
    
    config = CameraConfig(
        width=image_width,
        height=image_height,
        fx=fx,
        fy=fy,
        cx=image_width / 2,
        cy=image_height / 2,
        camera_height_cm=camera_height_cm,
        camera_angle_deg=camera_angle_deg
    )
    
    return CameraCalibration(config=config)


if __name__ == "__main__":
    # Test camera calibration
    logging.basicConfig(level=logging.INFO)
    
    # Quick calibration test
    calib = quick_calibration(camera_height_cm=50.0, camera_angle_deg=0.0)
    
    # Test pixel to world conversion
    test_points = [
        (320, 240),  # Center
        (0, 0),      # Top-left
        (640, 480),  # Bottom-right
        (400, 300),  # Offset
    ]
    
    print("\n=== Pixel to World Conversion Test ===")
    for x_px, y_px in test_points:
        x_w, y_w, z_w = calib.pixel_to_world(x_px, y_px)
        print(f"Pixel ({x_px}, {y_px}) → World ({x_w:.2f}, {y_w:.2f}, {z_w:.2f}) cm")
    
    print(f"\nPixel to cm ratio: {calib.get_pixel_to_cm_ratio():.4f} cm/px")
