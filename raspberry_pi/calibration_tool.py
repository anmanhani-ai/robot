"""
AgriBot Calibration Tool
เครื่องมือช่วย Calibrate ค่าต่างๆ หน้างาน

Features:
1. วัด pixel-to-cm จากภาพจริง
2. วัดความเร็วมอเตอร์
3. Export ค่า config พร้อมใช้

Author: AgriBot Team
"""

import cv2
import numpy as np
import json
import time
from dataclasses import dataclass, asdict
from typing import List, Tuple, Optional
from pathlib import Path


@dataclass
class CalibrationResult:
    """ผลลัพธ์การ Calibrate"""
    pixel_to_cm_z: float = 0.0
    arm_speed_cm_per_sec: float = 0.0
    arm_base_offset_cm: float = 0.0
    img_width: int = 640
    img_height: int = 480
    
    def to_dict(self):
        return asdict(self)
    
    def save(self, filepath: str):
        with open(filepath, 'w', encoding='utf-8') as f:
            json.dump(self.to_dict(), f, indent=2, ensure_ascii=False)
        print(f"✅ Saved to {filepath}")
    
    @classmethod
    def load(cls, filepath: str):
        with open(filepath, 'r', encoding='utf-8') as f:
            data = json.load(f)
        return cls(**data)


class CalibrationTool:
    """
    Interactive Calibration Tool
    
    วิธีใช้:
    1. รัน program
    2. คลิก 2 จุดบนภาพ
    3. ใส่ระยะจริง (cm)
    4. โปรแกรมคำนวณ pixel_to_cm ให้
    """
    
    def __init__(self, camera_id: int = 0):
        self.camera_id = camera_id
        self.cap = None
        self.result = CalibrationResult()
        
        # State for point clicking
        self.points: List[Tuple[int, int]] = []
        self.current_frame = None
        self.frozen_frame = None
        self.is_frozen = False
        
    def start_camera(self) -> bool:
        """เปิดกล้อง"""
        self.cap = cv2.VideoCapture(self.camera_id)
        if not self.cap.isOpened():
            print("❌ Cannot open camera")
            return False
        
        self.result.img_width = int(self.cap.get(cv2.CAP_PROP_FRAME_WIDTH))
        self.result.img_height = int(self.cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
        print(f"📷 Camera opened ({self.result.img_width}x{self.result.img_height})")
        return True
    
    def stop_camera(self):
        """ปิดกล้อง"""
        if self.cap:
            self.cap.release()
    
    def _mouse_callback(self, event, x, y, flags, param):
        """Callback สำหรับคลิกเมาส์"""
        if event == cv2.EVENT_LBUTTONDOWN:
            if len(self.points) < 2:
                self.points.append((x, y))
                print(f"📍 Point {len(self.points)}: ({x}, {y})")
    
    def _calculate_pixel_distance(self) -> float:
        """คำนวณระยะ pixel ระหว่าง 2 จุด"""
        if len(self.points) != 2:
            return 0
        
        p1, p2 = self.points
        dist = np.sqrt((p2[0] - p1[0])**2 + (p2[1] - p1[1])**2)
        return dist
    
    def run_pixel_to_cm_calibration(self):
        """
        Mode 1: วัด Pixel-to-CM Ratio
        
        Steps:
        1. วางไม้บรรทัดหน้ากล้อง
        2. กด SPACE เพื่อ freeze ภาพ
        3. คลิก 2 จุดบนไม้บรรทัด
        4. ใส่ระยะจริง (cm)
        """
        if not self.start_camera():
            return None
        
        window_name = "Pixel-to-CM Calibration"
        cv2.namedWindow(window_name)
        cv2.setMouseCallback(window_name, self._mouse_callback)
        
        print("\n" + "="*50)
        print("📐 PIXEL-to-CM CALIBRATION")
        print("="*50)
        print("1. วางไม้บรรทัดหน้ากล้อง")
        print("2. กด SPACE เพื่อ freeze ภาพ")
        print("3. คลิก 2 จุดที่รู้ระยะจริง")
        print("4. ใส่ระยะจริง (cm) ในช่อง input")
        print("5. กด R เพื่อ reset, Q เพื่อจบ")
        print("="*50 + "\n")
        
        while True:
            if not self.is_frozen:
                ret, frame = self.cap.read()
                if not ret:
                    continue
                self.current_frame = frame.copy()
            else:
                frame = self.frozen_frame.copy()
            
            # วาดเส้นแกนกลาง
            h, w = frame.shape[:2]
            cv2.line(frame, (w//2, 0), (w//2, h), (255, 255, 0), 1)
            cv2.line(frame, (0, h//2), (w, h//2), (255, 255, 0), 1)
            
            # วาดจุดที่คลิก
            for i, pt in enumerate(self.points):
                color = (0, 255, 0) if i == 0 else (0, 0, 255)
                cv2.circle(frame, pt, 8, color, -1)
                cv2.putText(frame, f"P{i+1}", (pt[0]+10, pt[1]),
                            cv2.FONT_HERSHEY_SIMPLEX, 0.6, color, 2)
            
            # วาดเส้นเชื่อม
            if len(self.points) == 2:
                cv2.line(frame, self.points[0], self.points[1], (255, 0, 255), 2)
                pixel_dist = self._calculate_pixel_distance()
                mid_x = (self.points[0][0] + self.points[1][0]) // 2
                mid_y = (self.points[0][1] + self.points[1][1]) // 2
                cv2.putText(frame, f"{pixel_dist:.1f} px", (mid_x, mid_y - 10),
                            cv2.FONT_HERSHEY_SIMPLEX, 0.7, (255, 0, 255), 2)
            
            # แสดงสถานะ
            status = "FROZEN - Click 2 points" if self.is_frozen else "LIVE - Press SPACE to freeze"
            cv2.putText(frame, status, (10, 30),
                        cv2.FONT_HERSHEY_SIMPLEX, 0.7, 
                        (0, 0, 255) if self.is_frozen else (0, 255, 0), 2)
            
            cv2.imshow(window_name, frame)
            
            key = cv2.waitKey(1) & 0xFF
            
            if key == ord('q'):
                break
            elif key == ord(' '):  # SPACE - freeze/unfreeze
                self.is_frozen = not self.is_frozen
                if self.is_frozen:
                    self.frozen_frame = self.current_frame.copy()
                    self.points = []
                    print("🔒 Frame frozen - click 2 points")
                else:
                    print("🔓 Frame unfrozen")
            elif key == ord('r'):  # Reset
                self.points = []
                self.is_frozen = False
                print("🔄 Reset")
            elif key == 13:  # ENTER - calculate
                if len(self.points) == 2:
                    pixel_dist = self._calculate_pixel_distance()
                    print(f"\n📏 Pixel distance: {pixel_dist:.2f} px")
                    
                    try:
                        real_dist = float(input("📐 Enter real distance (cm): "))
                        if real_dist > 0:
                            self.result.pixel_to_cm_z = real_dist / pixel_dist
                            print(f"✅ pixel_to_cm_z = {self.result.pixel_to_cm_z:.6f}")
                            print(f"   (1 pixel = {self.result.pixel_to_cm_z:.4f} cm)")
                    except ValueError:
                        print("❌ Invalid input")
        
        cv2.destroyAllWindows()
        self.stop_camera()
        return self.result.pixel_to_cm_z
    
    def run_motor_speed_calibration(self, serial_port: str = None):
        """
        Mode 2: วัดความเร็วมอเตอร์
        
        Steps:
        1. ทำเครื่องหมายจุดเริ่มต้นแขน
        2. กด SPACE เพื่อยืดแขน 1 วินาที
        3. วัดระยะที่ยืดได้ (cm)
        """
        print("\n" + "="*50)
        print("⚙️ MOTOR SPEED CALIBRATION")
        print("="*50)
        print("1. ทำเครื่องหมายจุดเริ่มต้นของแขน")
        print("2. กด ENTER เพื่อยืดแขน (1 วินาที)")
        print("3. วัดระยะที่ยืดได้ (cm)")
        print("="*50 + "\n")
        
        if serial_port:
            try:
                import serial
                ser = serial.Serial(serial_port, 115200, timeout=2)
                time.sleep(2)
                print("✅ Connected to ESP32")
                
                input("กด ENTER เมื่อพร้อมยืดแขน...")
                
                # ยืดแขน 1 วินาที
                print("🔄 Extending arm for 1 second...")
                ser.write(b"ACT:Z_OUT:1.00\n")
                
                # รอ DONE
                response = ser.readline().decode().strip()
                if response == "DONE":
                    print("✅ Done extending")
                
                ser.close()
                
            except Exception as e:
                print(f"❌ Serial error: {e}")
                print("   Manual mode: run motor manually for 1 second")
        else:
            print("⚠️ No serial port - run motor manually for 1 second")
            input("กด ENTER เมื่อยืดแขนเสร็จ...")
        
        try:
            distance = float(input("📏 วัดระยะที่ยืดได้ (cm): "))
            duration = float(input("⏱️ เวลาที่ใช้ (วินาที) [default=1]: ") or "1")
            
            self.result.arm_speed_cm_per_sec = distance / duration
            print(f"✅ arm_speed_cm_per_sec = {self.result.arm_speed_cm_per_sec:.2f}")
            
        except ValueError:
            print("❌ Invalid input")
        
        return self.result.arm_speed_cm_per_sec
    
    def run_offset_calibration(self):
        """
        Mode 3: วัด Arm Base Offset
        
        ระยะจากแกนกลางกล้องถึงจุดที่แขนเริ่มยืด
        """
        print("\n" + "="*50)
        print("📍 ARM BASE OFFSET CALIBRATION")
        print("="*50)
        print("วัดระยะจากจุดกึ่งกลางเลนส์กล้อง")
        print("ถึงจุดที่แขนเริ่มยืดออก (เป็น cm)")
        print("="*50 + "\n")
        
        try:
            offset = float(input("📏 ระยะ offset (cm): "))
            self.result.arm_base_offset_cm = offset
            print(f"✅ arm_base_offset_cm = {self.result.arm_base_offset_cm:.2f}")
            
        except ValueError:
            print("❌ Invalid input")
        
        return self.result.arm_base_offset_cm
    
    def run_full_calibration(self, serial_port: str = None):
        """
        Full Calibration Wizard
        """
        print("\n" + "="*60)
        print("🔧 AGRIBOT FULL CALIBRATION WIZARD")
        print("="*60)
        
        # Step 1: Pixel-to-CM
        print("\n[Step 1/3] Pixel-to-CM Calibration")
        self.run_pixel_to_cm_calibration()
        
        # Step 2: Motor Speed
        print("\n[Step 2/3] Motor Speed Calibration")
        self.run_motor_speed_calibration(serial_port)
        
        # Step 3: Offset
        print("\n[Step 3/3] Arm Base Offset")
        self.run_offset_calibration()
        
        # Summary
        self._print_summary()
        
        # Save
        save = input("\n💾 Save to calibration.json? (y/n): ").lower()
        if save == 'y':
            self.result.save("calibration.json")
        
        return self.result
    
    def _print_summary(self):
        """แสดงสรุปค่า Calibration"""
        print("\n" + "="*60)
        print("📊 CALIBRATION SUMMARY")
        print("="*60)
        print(f"""
# Copy these values to robot_brain.py:

pixel_to_cm_z = {self.result.pixel_to_cm_z:.6f}
arm_speed_cm_per_sec = {self.result.arm_speed_cm_per_sec:.2f}
arm_base_offset_cm = {self.result.arm_base_offset_cm:.2f}
img_width = {self.result.img_width}
img_height = {self.result.img_height}
""")
        print("="*60)
    
    def load_from_image(self, image_path: str):
        """
        Calibrate จากไฟล์ภาพ (ไม่ต้องใช้กล้อง)
        """
        frame = cv2.imread(image_path)
        if frame is None:
            print(f"❌ Cannot load image: {image_path}")
            return None
        
        self.result.img_height, self.result.img_width = frame.shape[:2]
        self.frozen_frame = frame.copy()
        self.is_frozen = True
        
        window_name = "Image Calibration"
        cv2.namedWindow(window_name)
        cv2.setMouseCallback(window_name, self._mouse_callback)
        
        print("\n" + "="*50)
        print(f"📷 Loaded: {image_path}")
        print(f"   Size: {self.result.img_width}x{self.result.img_height}")
        print("="*50)
        print("1. คลิก 2 จุดที่รู้ระยะจริง")
        print("2. กด ENTER เพื่อคำนวณ")
        print("3. กด R เพื่อ reset, Q เพื่อจบ")
        print("="*50 + "\n")
        
        while True:
            display = frame.copy()
            
            # วาดเส้นแกนกลาง
            h, w = display.shape[:2]
            cv2.line(display, (w//2, 0), (w//2, h), (255, 255, 0), 1)
            
            # วาดจุด
            for i, pt in enumerate(self.points):
                color = (0, 255, 0) if i == 0 else (0, 0, 255)
                cv2.circle(display, pt, 8, color, -1)
                cv2.putText(display, f"P{i+1}", (pt[0]+10, pt[1]),
                            cv2.FONT_HERSHEY_SIMPLEX, 0.6, color, 2)
            
            # วาดเส้นเชื่อม
            if len(self.points) == 2:
                cv2.line(display, self.points[0], self.points[1], (255, 0, 255), 2)
                pixel_dist = self._calculate_pixel_distance()
                mid_x = (self.points[0][0] + self.points[1][0]) // 2
                mid_y = (self.points[0][1] + self.points[1][1]) // 2
                cv2.putText(display, f"{pixel_dist:.1f} px", (mid_x, mid_y - 10),
                            cv2.FONT_HERSHEY_SIMPLEX, 0.7, (255, 0, 255), 2)
            
            cv2.imshow(window_name, display)
            
            key = cv2.waitKey(1) & 0xFF
            
            if key == ord('q'):
                break
            elif key == ord('r'):
                self.points = []
                print("🔄 Reset")
            elif key == 13:  # ENTER
                if len(self.points) == 2:
                    pixel_dist = self._calculate_pixel_distance()
                    print(f"\n📏 Pixel distance: {pixel_dist:.2f} px")
                    
                    try:
                        real_dist = float(input("📐 Enter real distance (cm): "))
                        if real_dist > 0:
                            self.result.pixel_to_cm_z = real_dist / pixel_dist
                            print(f"✅ pixel_to_cm_z = {self.result.pixel_to_cm_z:.6f}")
                    except ValueError:
                        print("❌ Invalid input")
        
        cv2.destroyAllWindows()
        return self.result


# ==================== MAIN ====================
def main():
    import argparse
    
    parser = argparse.ArgumentParser(description="AgriBot Calibration Tool")
    parser.add_argument('--mode', '-m', 
                        choices=['pixel', 'motor', 'offset', 'full', 'image'],
                        default='full',
                        help='Calibration mode')
    parser.add_argument('--camera', '-c', type=int, default=0,
                        help='Camera ID')
    parser.add_argument('--port', '-p', type=str, default=None,
                        help='Serial port for ESP32')
    parser.add_argument('--image', '-i', type=str, default=None,
                        help='Image file for calibration (image mode)')
    parser.add_argument('--load', type=str, default=None,
                        help='Load existing calibration.json')
    
    args = parser.parse_args()
    
    tool = CalibrationTool(camera_id=args.camera)
    
    # Load existing
    if args.load:
        try:
            tool.result = CalibrationResult.load(args.load)
            print(f"✅ Loaded calibration from {args.load}")
            tool._print_summary()
        except Exception as e:
            print(f"❌ Failed to load: {e}")
    
    # Run calibration
    if args.mode == 'pixel':
        tool.run_pixel_to_cm_calibration()
    elif args.mode == 'motor':
        tool.run_motor_speed_calibration(args.port)
    elif args.mode == 'offset':
        tool.run_offset_calibration()
    elif args.mode == 'full':
        tool.run_full_calibration(args.port)
    elif args.mode == 'image':
        if args.image:
            tool.load_from_image(args.image)
            tool._print_summary()
        else:
            print("❌ Please specify --image path")
    
    tool._print_summary()


if __name__ == "__main__":
    main()
