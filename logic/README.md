# 🧠 AgriBot System Logic Documentation

เอกสารอธิบายการทำงานทั้งหมดของระบบหุ่นยนต์กำจัดวัชพืช AgriBot อย่างละเอียด

---

## 📋 สารบัญ

1. [ภาพรวมระบบ](#1-ภาพรวมระบบ)
2. [Flow การทำงานหลัก](#2-flow-การทำงานหลัก)
3. [YOLO11 Detection Logic](#3-yolo11-detection-logic)
4. [Physics Calculation](#4-physics-calculation)
5. [ESP32 Command Protocol](#5-esp32-command-protocol)
6. [Obstacle Avoidance Logic](#6-obstacle-avoidance-logic)
7. [Encoder Position Control](#7-encoder-position-control)
8. [Weed Tracking System](#8-weed-tracking-system)
9. [Physical Buttons + LCD](#9-physical-buttons--lcd)
10. [Calibration System](#10-calibration-system)
11. [Web Dashboard Architecture](#11-web-dashboard-architecture)
12. [Error Handling](#12-error-handling)

---

## 1. ภาพรวมระบบ

### 1.1 Architecture Overview

```
┌──────────────────────────────────────────────────────────────────────────┐
│                           AgriBot Architecture                           │
├──────────────────────────────────────────────────────────────────────────┤
│                                                                          │
│  ┌────────────────────────────────────────────────────────────────────┐  │
│  │                        BRAIN (Raspberry Pi 5)                      │  │
│  │                                                                    │  │
│  │  ┌──────────────┐    ┌──────────────┐    ┌──────────────┐         │  │
│  │  │   Camera     │───►│  YOLO11 AI   │───►│  Detection   │         │  │
│  │  │   Input      │    │  Inference   │    │  Results     │         │  │
│  │  └──────────────┘    └──────────────┘    └──────┬───────┘         │  │
│  │                                                 │                  │  │
│  │                                                 ▼                  │  │
│  │  ┌──────────────┐    ┌──────────────┐    ┌──────────────┐         │  │
│  │  │ Calibration  │───►│  Robot Brain │◄───│  Physics     │         │  │
│  │  │   Config     │    │  Controller  │    │  Calculator  │         │  │
│  │  └──────────────┘    └──────┬───────┘    └──────────────┘         │  │
│  │                             │                                      │  │
│  └─────────────────────────────┼──────────────────────────────────────┘  │
│                                │ Serial (USB)                            │
│                                ▼                                         │
│  ┌────────────────────────────────────────────────────────────────────┐  │
│  │                        BODY (ESP32)                                │  │
│  │                                                                    │  │
│  │  ┌──────────────┐    ┌──────────────┐    ┌──────────────┐         │  │
│  │  │   Motor      │    │   Servo      │    │    Pump      │         │  │
│  │  │   Control    │    │   Control    │    │   Control    │         │  │
│  │  └──────────────┘    └──────────────┘    └──────────────┘         │  │
│  │                                                                    │  │
│  │  ┌──────────────┐    ┌──────────────┐    ┌──────────────┐         │  │
│  │  │  Ultrasonic  │    │   Encoder    │    │   Obstacle   │         │  │
│  │  │   Sensors    │    │   Feedback   │    │   Avoidance  │         │  │
│  │  └──────────────┘    └──────────────┘    └──────────────┘         │  │
│  │                                                                    │  │
│  └────────────────────────────────────────────────────────────────────┘  │
│                                                                          │
└──────────────────────────────────────────────────────────────────────────┘
```

### 1.2 หน้าที่แต่ละส่วน

| Component        | Hardware          | หน้าที่หลัก                            |
| ---------------- | ----------------- | ------------------------------------------------- |
| **Brain**  | Raspberry Pi 5    | ประมวลผล AI, ตัดสินใจ, คำนวณ |
| **Body**   | ESP32             | ควบคุม Hardware, รับคำสั่ง         |
| **Eyes**   | Camera            | มองเห็น, ส่งภาพให้ AI             |
| **Arms**   | Motor Z + Servo Y | ยืด/หด แขน, ยก/วาง หัวฉีด      |
| **Legs**   | Motor Wheel       | เคลื่อนที่                              |
| **Spray**  | Pump + Relay      | พ่นยา                                        |
| **Senses** | Ultrasonic × 3   | ตรวจจับสิ่งกีดขวาง              |

---

## 2. Flow การทำงานหลัก

### 2.1 Main Mission Flow

```
START
  │
  ▼
┌─────────────────┐
│ 1. SEARCH MODE  │
│ รถเดินหน้า       │
│ กล้องสแกนหาหญ้า  │
└────────┬────────┘
         │
         ▼
    ┌──────────┐
    │ พบหญ้า?  │
    └────┬─────┘
    No   │  Yes
    │    ▼
    │ ┌─────────────────┐
    │ │ 2. STOP         │
    │ │ หยุดรถ           │
    │ └────────┬────────┘
    │          │
    │          ▼
    │ ┌─────────────────┐
    │ │ 3. ALIGN        │
    │ │ จัดตำแหน่งให้     │
    │ │ หญ้าอยู่กลางภาพ   │
    │ └────────┬────────┘
    │          │
    │          ▼
    │ ┌─────────────────┐
    │ │ 4. CALCULATE    │
    │ │ คำนวณระยะยืดแขน  │
    │ │ (pixel → cm)    │
    │ └────────┬────────┘
    │          │
    │          ▼
    │ ┌─────────────────┐
    │ │ 5. EXTEND ARM   │
    │ │ ยืดแขน Z ไปหาหญ้า │
    │ └────────┬────────┘
    │          │
    │          ▼
    │ ┌─────────────────┐
    │ │ 6. LOWER HEAD   │
    │ │ หัวฉีดลง Y      │
    │ └────────┬────────┘
    │          │
    │          ▼
    │ ┌─────────────────┐
    │ │ 7. SPRAY        │
    │ │ พ่นยา           │
    │ └────────┬────────┘
    │          │
    │          ▼
    │ ┌─────────────────┐
    │ │ 8. RAISE HEAD   │
    │ │ หัวฉีดขึ้น Y     │
    │ └────────┬────────┘
    │          │
    │          ▼
    │ ┌─────────────────┐
    │ │ 9. RETRACT ARM  │
    │ │ หดแขน Z กลับ     │
    │ └────────┬────────┘
    │          │
    └──────────┘
         │
         ▼
    CONTINUE SEARCH
```

### 2.2 Sequence Diagram

```
Camera     YOLO11      RobotBrain       ESP32        Hardware
  │           │            │              │             │
  │──frame───►│            │              │             │
  │           │──detect───►│              │             │
  │           │   (weed    │              │             │
  │           │   at x,y)  │              │             │
  │           │            │              │             │
  │           │            │──MOVE_STOP──►│             │
  │           │            │              │──stop───────►│
  │           │            │◄────DONE─────│             │
  │           │            │              │             │
  │           │            │──calculate   │             │
  │           │            │  distance    │             │
  │           │            │              │             │
  │           │            │──ACT:Z_OUT:──►│             │
  │           │            │    2.5       │──extend────►│
  │           │            │◄────DONE─────│             │
  │           │            │              │             │
  │           │            │──ACT:Y_DOWN─►│             │
  │           │            │              │──lower─────►│
  │           │            │◄────DONE─────│             │
  │           │            │              │             │
  │           │            │──ACT:SPRAY:─►│             │
  │           │            │    1.0       │──spray─────►│
  │           │            │◄────DONE─────│             │
  │           │            │              │             │
  │           │            │──ACT:Y_UP───►│             │
  │           │            │              │──raise─────►│
  │           │            │◄────DONE─────│             │
  │           │            │              │             │
  │           │            │──ACT:Z_IN:──►│             │
  │           │            │    3.0       │──retract───►│
  │           │            │◄────DONE─────│             │
  │           │            │              │             │
```

---

## 3. YOLO11 Detection Logic

### 3.1 Class Definition

```python
# weed_detector.py

TARGET_CLASSES = {
    0: ("weed", True),      # Class 0 = หญ้า → ต้องพ่นยา
    1: ("chili", False),    # Class 1 = พริก → ข้าม ไม่พ่น
}
```

### 3.2 Detection Output

```python
@dataclass
class Detection:
    x: int                  # พิกัด X ของจุดกลาง (pixel)
    y: int                  # พิกัด Y ของจุดกลาง (pixel)
    width: int              # ความกว้าง bounding box
    height: int             # ความสูง bounding box
    confidence: float       # ความมั่นใจ (0-1)
    class_name: str         # "weed" หรือ "chili"
    class_id: int           # 0 หรือ 1
    is_target: bool         # True ถ้าเป็นหญ้า
  
    # สำคัญ: ระยะจากแกนกลาง
    distance_from_center_x: int  # pixel (บวก=ขวา, ลบ=ซ้าย)
    distance_from_center_y: int  # pixel (บวก=ล่าง, ลบ=บน)
```

### 3.3 Detection Flow

```
┌─────────────────────────────────────────────────────────────┐
│              YOLO11 Detection Pipeline                      │
├─────────────────────────────────────────────────────────────┤
│                                                             │
│  Frame (640×480)     YOLO11 Model        Detections        │
│  ┌─────────────┐     ┌───────────┐      ┌───────────┐      │
│  │  📷         │────►│  best.pt  │─────►│ [         │      │
│  │  BGR Image  │     │           │      │  weed @   │      │
│  │             │     │ Inference │      │  (400,200)│      │
│  └─────────────┘     └───────────┘      │  conf=0.9 │      │
│                                         │           │      │
│                                         │  chili @  │      │
│                                         │  (100,300)│      │
│                                         │  conf=0.85│      │
│                                         │ ]         │      │
│                                         └───────────┘      │
│                                               │            │
│                                               ▼            │
│                                         Filter:           │
│                                         is_target==True   │
│                                               │            │
│                                               ▼            │
│                                         Targets:          │
│                                         [weed @ (400,200)]│
│                                                             │
└─────────────────────────────────────────────────────────────┘
```

### 3.4 Model Auto-Loading

```python
# ค้นหาโมเดลจาก models/ folder อัตโนมัติ

MODELS_DIR = Path(__file__).parent / "models"
DEFAULT_MODEL_NAME = "best.pt"

def _auto_load_model(self):
    # 1. หา best.pt ก่อน
    default_model = MODELS_DIR / DEFAULT_MODEL_NAME
    if default_model.exists():
        return self.load_yolo_model(str(default_model))
  
    # 2. หาไฟล์ .pt ตัวแรก
    pt_files = list(MODELS_DIR.glob("*.pt"))
    if pt_files:
        return self.load_yolo_model(str(pt_files[0]))
  
    return False
```

---

## 4. Physics Calculation

### 4.1 Pixel to CM Conversion

```
Problem: กล้องเห็นหญ้าที่ตำแหน่ง pixel → แขนต้องยืดไปกี่ cm?

Solution:
1. Calibrate หา pixel_to_cm ratio
2. แปลง pixel → cm
3. ลบ offset ของฐานแขน
4. แปลง cm → เวลา (หรือส่งตรงถ้าใช้ encoder)
```

### 4.2 Z-Axis Calculation (แขนยืด)

```python
# robot_brain.py

def calculate_z_distance(self, distance_from_center_px: int):
    """
    สมการ:
    1. distance_cm = |distance_px| × pixel_to_cm_z
    2. actual_distance = distance_cm - arm_base_offset
    3. time = actual_distance / arm_speed (ถ้า Time-based)
    """
  
    # Step 1: แปลง pixel → cm
    distance_cm = abs(distance_from_center_px) * self.config.pixel_to_cm_z
  
    # Step 2: ลบ offset
    actual_distance = max(0, distance_cm - self.config.arm_base_offset_cm)
  
    # Step 3: แปลง cm → เวลา (t = d / v)
    time_seconds = actual_distance / self.config.arm_speed_cm_per_sec
  
    # Step 4: Safety limit
    time_seconds = min(time_seconds, self.config.max_arm_extend_time)
  
    return time_seconds, actual_distance
```

### 4.3 ตัวอย่างการคำนวณ

```
Input:
  - หญ้าอยู่ที่ y = 350 pixel (ห่างจากกลาง = 350 - 240 = 110 pixel)
  - pixel_to_cm_z = 0.05 cm/pixel
  - arm_offset = 5 cm
  - arm_speed = 10 cm/s

Calculation:
  1. distance_cm = 110 × 0.05 = 5.5 cm
  2. actual = 5.5 - 5 = 0.5 cm
  3. time = 0.5 / 10 = 0.05 วินาที

Output:
  - สั่ง ESP32: ACT:Z_OUT:0.05
  - หรือถ้าใช้ Encoder: Z_MOVE:0.5
```

### 4.4 Camera Angle Compensation (กล้องเฉียง)

```
ถ้ากล้องติดเฉียง (ไม่ใช่ 90°):
- pixel_to_cm ไม่เท่ากันทั้งภาพ
- ส่วนบน (ไกล) → pixel เล็ก → pixel_to_cm มาก
- ส่วนล่าง (ใกล้) → pixel ใหญ่ → pixel_to_cm น้อย

Solution:
- Calibrate 3 จุด: NEAR, CENTER, FAR
- ใช้ค่า CENTER (ตำแหน่งที่ target อยู่เมื่อ aligned)
```

---

## 5. ESP32 Command Protocol

### 5.1 Communication Format

```
Protocol: Serial (USB)
Baud Rate: 115200
Format: Plain text + newline (\n)
Handshake: Synchronous (รอ DONE ก่อนส่งคำสั่งถัดไป)
```

### 5.2 Command Categories

#### 5.2.1 Movement Commands

| Command           | Description          | Response |
| ----------------- | -------------------- | -------- |
| `MOVE_FORWARD`  | รถเดินหน้า | DONE     |
| `MOVE_BACKWARD` | รถถอยหลัง   | DONE     |
| `MOVE_STOP`     | รถหยุด         | DONE     |

#### 5.2.2 Arm Z Commands (Time-based)

| Command             | Description                 | Response |
| ------------------- | --------------------------- | -------- |
| `ACT:Z_OUT:<sec>` | ยืดแขน X วินาที | DONE     |
| `ACT:Z_IN:<sec>`  | หดแขน X วินาที   | DONE     |

#### 5.2.3 Arm Z Commands (Encoder-based)

| Command         | Description                            | Response        |
| --------------- | -------------------------------------- | --------------- |
| `Z_MOVE:<cm>` | ยืดแขนไปตำแหน่ง X cm    | POS:X.XX + DONE |
| `Z_HOME`      | หดกลับตำแหน่ง 0           | DONE            |
| `Z_POS`       | อ่านตำแหน่งปัจจุบัน | POS:X.XX        |
| `Z_RESET`     | Reset encoder เป็น 0               | DONE            |
| `Z_ENC_ON`    | เปิด encoder mode                  | DONE            |
| `Z_ENC_OFF`   | ปิด encoder mode                    | DONE            |

#### 5.2.4 Servo Y Commands

| Command        | Description                | Response |
| -------------- | -------------------------- | -------- |
| `ACT:Y_DOWN` | หัวฉีดลง (90°)    | DONE     |
| `ACT:Y_UP`   | หัวฉีดขึ้น (0°) | DONE     |

#### 5.2.5 Pump Commands

| Command             | Description               | Response |
| ------------------- | ------------------------- | -------- |
| `ACT:SPRAY:<sec>` | พ่นยา X วินาที | DONE     |
| `PUMP_ON`         | เปิด pump ค้าง    | DONE     |
| `PUMP_OFF`        | ปิด pump               | DONE     |

#### 5.2.6 Ultrasonic Commands

| Command         | Description                          | Response   |
| --------------- | ------------------------------------ | ---------- |
| `US_GET_DIST` | อ่านระยะ 3 เซนเซอร์  | DIST:f,l,r |
| `US_CHECK`    | ตรวจสอบสิ่งกีดขวาง | OBSTACLE:X |

#### 5.2.7 Obstacle Avoidance Commands

| Command            | Description         | Response |
| ------------------ | ------------------- | -------- |
| `AVOID_ON`       | เปิด auto-avoid | DONE     |
| `AVOID_OFF`      | ปิด auto-avoid   | DONE     |
| `AVOID_SET:<cm>` | ตั้ง threshold  | DONE     |

#### 5.2.8 System Commands

| Command      | Description                          | Response |
| ------------ | ------------------------------------ | -------- |
| `STOP_ALL` | หยุดฉุกเฉินทุกระบบ | DONE     |
| `STATUS`   | ตรวจสอบสถานะ             | OK       |
| `PING`     | ทดสอบการเชื่อมต่อ   | PONG     |

### 5.3 Response Format

```
Success: DONE
Error:   ERROR:<message>
Data:    <TYPE>:<value>

Examples:
  DONE
  ERROR:Unknown command
  DIST:25.5,30.2,28.1
  POS:15.50
  OBSTACLE:1
```

### 5.4 Obstacle Direction Codes

```python
NO_OBSTACLE     = 0  # ไม่มีสิ่งกีดขวาง
OBSTACLE_FRONT  = 1  # ด้านหน้า
OBSTACLE_LEFT   = 2  # ด้านซ้าย
OBSTACLE_RIGHT  = 3  # ด้านขวา
OBSTACLE_FRONT_LEFT  = 4  # หน้า+ซ้าย
OBSTACLE_FRONT_RIGHT = 5  # หน้า+ขวา
OBSTACLE_ALL    = 6  # ทุกทิศ (ติด!)
```

---

## 6. Obstacle Avoidance Logic

### 6.1 Sensor Positions

```
         ┌─────────────────┐
         │    FRONT (F)    │
         │    ┌─────┐      │
         │    │sensor│      │
         │    └──┬──┘      │
    ┌────┴──────┴──────────┴────┐
    │                           │
   ┌┴┐                         ┌┴┐
   │L│         ROBOT           │R│
   │ │                         │ │
   └┬┘                         └┬┘
    │      ═══════════════      │
    │         (arm Z)           │
    └───────────────────────────┘
```

### 6.2 Detection Logic

```cpp
// obstacle_avoidance.cpp

bool checkAndAvoid() {
    // อ่านระยะ
    float front = ultrasonics.getFrontDistance();
    float left = ultrasonics.getLeftDistance();
    float right = ultrasonics.getRightDistance();
  
    // ตรวจสอบ threshold (default 30 cm)
    bool obstacleFront = front < THRESHOLD;
    bool obstacleLeft = left < THRESHOLD;
    bool obstacleRight = right < THRESHOLD;
  
    // ตัดสินใจ
    if (obstacleFront && obstacleLeft && obstacleRight) {
        // ติดทุกทิศ → Emergency Stop
        emergencyStop();
    }
    else if (obstacleFront) {
        // มีข้างหน้า → ถอย + เลี้ยว
        avoidFront();
    }
    else if (obstacleLeft) {
        // มีซ้าย → เลี้ยวขวา
        avoidLeft();
    }
    else if (obstacleRight) {
        // มีขวา → เลี้ยวซ้าย
        avoidRight();
    }
}
```

### 6.3 Avoidance Actions

```
เจอหน้า: STOP → ถอยหลัง → เลี้ยวหาทางว่าง
เจอซ้าย: หยุด → เลี้ยวขวานิดหน่อย → ไปต่อ
เจอขวา: หยุด → เลี้ยวซ้ายนิดหน่อย → ไปต่อ
เจอหมด: EMERGENCY STOP + ส่ง BLOCKED ไป Pi
```

---

## 7. Encoder Position Control

### 7.1 Hardware Setup

```
Encoder (Incremental, 2-channel)
├── Channel A → GPIO 34
└── Channel B → GPIO 35

Specifications:
- PPR (Pulses Per Revolution): 20 (ปรับตามรุ่น)
- Wheel Diameter: 30 mm (ปรับตามเพลา)
```

### 7.2 Position Calculation

```cpp
// encoder.cpp

// mm per pulse = (π × diameter) / PPR
#define MM_PER_PULSE  (3.14159 * WHEEL_DIAMETER_MM / ENCODER_PPR)

// ตัวอย่าง:
// diameter = 30 mm, PPR = 20
// mm_per_pulse = (3.14159 × 30) / 20 = 4.71 mm/pulse

float getPositionMM() {
    return pulseCount * MM_PER_PULSE;
}

float getPositionCM() {
    return getPositionMM() / 10.0;
}
```

### 7.3 Interrupt-based Counting

```cpp
// ใช้ Hardware Interrupt
void IRAM_ATTR handleInterrupt() {
    int stateA = digitalRead(PIN_ENCODER_A);
    int stateB = digitalRead(PIN_ENCODER_B);
  
    if (stateA != lastStateA) {
        if (stateB != stateA) {
            pulseCount++;  // หมุนไปข้างหน้า
        } else {
            pulseCount--;  // หมุนถอยหลัง
        }
    }
  
    lastStateA = stateA;
}
```

### 7.4 Position Control Loop

```cpp
// motor_z.cpp

bool moveToCM(float targetCM) {
    float targetMM = targetCM * 10.0;
  
    while (true) {
        float currentMM = encoderZ.getPositionMM();
        float errorMM = targetMM - currentMM;
      
        // ถึงเป้าหมายแล้ว?
        if (abs(errorMM) <= TOLERANCE) {
            stop();
            return true;
        }
      
        // Timeout?
        if (millis() - startTime > TIMEOUT) {
            stop();
            return false;
        }
      
        // เคลื่อนที่
        if (errorMM > 0) {
            runForward();   // ต้องยืด
        } else {
            runBackward();  // ต้องหด
        }
      
        delay(10);
    }
}
```

---

## 8. Weed Tracking System

### 8.1 ปัญหา

```
ก่อนหน้า: หุ่นยนต์อาจพ่นซ้ำต้นเดิมหลายครั้ง
- ไม่มีระบบจำว่าพ่นไปแล้ว
- พึ่งพาการเคลื่อนที่เพื่อให้ต้นเก่าหลุดจากเฟรม
```

### 8.2 Solution: IoU Tracking + Position Filter

```python
# weed_tracker.py

class SimpleTracker:
    """
    2-Layer Protection:
    1. ID Tracking - เก็บประวัติ ID ที่พ่นแล้ว
    2. Position Filter - ข้าม targets ที่ X < 0 (ผ่านไปแล้ว)
    """
    
    def update(self, detections) -> List[TrackedObject]:
        # จับคู่ detections ใหม่กับ track เดิมด้วย IoU
        matched = self._match_detections(detections)
        # สร้าง track ใหม่สำหรับ detections ที่ไม่ match
        new_tracks = self._create_tracks(unmatched)
        return all_tracks
    
    def mark_sprayed(self, track_id: int):
        # เก็บ ID ใน sprayed_ids set
        self.sprayed_ids.add(track_id)
    
    def get_unsprayed_targets(self, min_x: int = 0):
        # หา targets ที่:
        # 1. is_target == True (เป็นหญ้า)
        # 2. sprayed == False (ยังไม่พ่น)
        # 3. X >= min_x (อยู่ด้านหน้า)
        return [t for t in tracks if t.is_target 
                and not t.sprayed 
                and t.x >= min_x]
```

### 8.3 IoU Matching

```
IoU = Intersection / Union

  Detection (New)     Track (Existing)
  ┌─────────┐        ┌─────────┐
  │    ┌────┼────────┼────┐    │
  │    │    │ Inter- │    │    │
  │    │    │ section│    │    │
  └────┼────┴────────┴────┼────┘
       │                  │
       └──────────────────┘
               Union

IoU >= 0.3 → Same object (match)
IoU <  0.3 → New object (create new track)
```

### 8.4 Flow Integration

```
1. YOLO detect() → detections
                      ↓
2. tracker.update(detections) → tracked objects with IDs
                      ↓
3. tracker.get_unsprayed_targets(min_x=-20)
                      ↓
   Only targets that:
   - Have is_target=True
   - Not in sprayed_ids
   - X position >= -20 (in front of robot)
                      ↓
4. Execute spray → tracker.mark_sprayed(id)
                      ↓
5. Loop continues, skips this ID next time
```

---

## 9. Physical Buttons + LCD

### 9.1 Pin Configuration

```
┌─────────────────────────────────────┐
│           ESP32 GPIO Layout         │
├─────────────────────────────────────┤
│                                     │
│   Start Button ──── GPIO 15         │
│   (กดค้าง 3s)       (INPUT_PULLUP)  │
│                                     │
│   Emergency Stop ── GPIO 34         │
│   (กดทันที)         (INPUT_PULLUP)  │
│                                     │
│   LCD I2C ───────── SDA: GPIO 21    │
│   (16x2)            SCL: GPIO 22    │
│                     Address: 0x27   │
└─────────────────────────────────────┘
```

### 9.2 Start Button Logic

```cpp
// button.cpp

void ButtonController::check() {
    bool startState = digitalRead(PIN_BTN_START);
    
    if (startState == LOW) {
        // กำลังกดอยู่
        if (now - startPressedTime >= 3000) {
            // กดครบ 3 วินาที!
            startTriggered = true;
            Serial.println("START_CMD");  // ส่งไป Pi
        }
    }
}
```

### 9.3 LCD Display States

```
┌──────────────────┐
│   AgriBot v2     │  ← Ready (รอกด Start)
│  Press START     │
└──────────────────┘
         ↓ กด Start ค้าง
┌──────────────────┐
│  Hold 3 sec..    │  ← Progress bar
│ ████████░░░░░░░░ │
└──────────────────┘
         ↓ กดครบ 3s
┌──────────────────┐
│   Starting..     │  ← นับถอยหลัง
│       3          │
└──────────────────┘
         ↓
┌──────────────────┐
│    RUNNING       │  ← กำลังทำงาน
│   Auto Mode      │
└──────────────────┘

❌ กด Emergency Stop
┌──────────────────┐
│    STOPPED!      │  ← หยุดฉุกเฉิน
│ Emergency Stop   │
└──────────────────┘
```

### 9.4 Serial Commands from Buttons

```
Start Button (3s hold) → "START_CMD\n" → Pi starts mission
Emergency Stop (instant) → "STOP_CMD\n" → Pi stops everything
```

---

## 10. Calibration System

### 8.1 Calibration Values

```python
# calibration.json

{
    "img_width": 640,
    "img_height": 480,
  
    "camera_angle_deg": 45.0,       # องศากล้อง
    "camera_height_cm": 50.0,       # ความสูงกล้อง
  
    "pixel_to_cm_z": 0.052631,      # สำคัญที่สุด!
    "pixel_to_cm_z_near": 0.045,    # (reference)
    "pixel_to_cm_z_center": 0.052631,
    "pixel_to_cm_z_far": 0.065,
  
    "arm_speed_cm_per_sec": 10.0,   # สำหรับ Time-based
    "arm_base_offset_cm": 5.0,      # ระยะกล้อง→แขน
    "max_arm_extend_cm": 50.0,
  
    "alignment_tolerance_px": 30,
    "default_spray_duration": 1.0,
  
    "encoder_ppr": 20,              # สำหรับ ESP32
    "wheel_diameter_mm": 30.0
}
```

### 8.2 Multi-Point Calibration (กล้องเฉียง)

```
┌───────────────────────────────┐
│ FAR   (ส่วนบน)  pixel_to_cm ↑│
│       pixel เล็ก              │
│                               │
│ CENTER (กลาง) ← ใช้ค่านี้!    │
│       ตำแหน่งที่ target อยู่   │
│                               │
│ NEAR  (ส่วนล่าง) pixel_to_cm ↓│
│       pixel ใหญ่              │
└───────────────────────────────┘

วิธีวัด:
1. วางไม้บรรทัดที่แต่ละตำแหน่ง
2. วัดว่า 10 cm = กี่ pixel
3. คำนวณ: pixel_to_cm = 10 / pixel_count
```

### 8.3 Auto-Loading

```python
# robot_brain.py

class RobotBrain:
    def __init__(self):
        # โหลดจาก calibration.json อัตโนมัติ
        self.config = CalibrationConfig.load_from_file()
```

---

## 11. Web Dashboard Architecture

### 11.1 Stack

```
Frontend: React + Vite + Tailwind CSS
Backend:  FastAPI (Python)
Communication: REST API + MJPEG Stream
```

### 11.2 Web Control (New!)

```
ก่อนหน้า: รัน main.py โดยตรง
ตอนนี้:   ควบคุมผ่าน Web Dashboard

┌─────────────────────────────────────────┐
│              Web Dashboard              │
├─────────────────────────────────────────┤
│                                         │
│   [Start Mission]   [Stop Mission]      │
│                                         │
│   ┌─────────────────────────────────┐   │
│   │                                 │   │
│   │      Camera Live Stream         │   │
│   │      with YOLO Detection        │   │
│   │                                 │   │
│   └─────────────────────────────────┘   │
│                                         │
│   Status: Running                       │
│   ESP32: ✅ Connected                   │
│   Camera: ✅ Connected                  │
│   Weeds: 15 | Sprayed: 12               │
│                                         │
└─────────────────────────────────────────┘
```

### 11.3 Device Initialization on Startup

```python
# PI_WEBAPP/backend/main.py

@asynccontextmanager
async def lifespan(app: FastAPI):
    # เมื่อ server start
    robot.initialize_devices()  # ESP32 + Camera
    
    yield
    
    # เมื่อ server stop
    robot.shutdown()
```

### 11.4 API Endpoints

| Endpoint                 | Method | Description                      |
| ------------------------ | ------ | -------------------------------- |
| `/api/status`          | GET    | ดึงสถานะหุ่นยนต์ |
| `/api/command`         | POST   | ส่งคำสั่ง               |
| `/api/logs`            | GET    | ดึง Log                       |
| `/api/download/report` | GET    | ดาวน์โหลด Report        |
| `/api/camera/stream`   | GET    | Stream กล้อง (MJPEG)        |

### 9.3 Component Structure

```
frontend/src/
├── App.jsx              # Main layout
├── components/
│   ├── Header.jsx       # Header + logo
│   ├── StatusCard.jsx   # แสดงสถานะ
│   ├── ControlPanel.jsx # ปุ่มควบคุม
│   ├── CameraFeed.jsx   # ภาพกล้อง
│   └── LogViewer.jsx    # แสดง Log
└── services/
    └── api.js           # API calls
```

---

## 12. Error Handling

### 10.1 ESP32 Errors

```cpp
// command_handler.cpp

void sendError(String message) {
    Serial.print("ERROR:");
    Serial.println(message);
}

// Examples:
// ERROR:Unknown command: xyz
// ERROR:Move failed or timeout
```

### 10.2 Pi Errors

```python
# robot_brain.py

def send_cmd(self, command: str):
    try:
        self.ser.write(f"{command}\n".encode())
      
        # รอ response
        while True:
            line = self.ser.readline().decode().strip()
          
            if line == "DONE":
                return True
            elif line.startswith("ERR"):
                logger.error(f"ESP32 Error: {line}")
                return False
            elif line == "EMERGENCY_STOPPED":
                self.state = RobotState.IDLE
                return True
              
            # Timeout
            if time.time() - start > self.config.timeout:
                logger.error("Response Timeout")
                return False
              
    except Exception as e:
        logger.error(f"Send Error: {e}")
        return False
```

### 10.3 Fallback Detection

```python
# weed_detector.py

def detect(self, frame):
    if self.model is None:
        # ไม่มี YOLO → ใช้ Color Detection
        return self._detect_by_color(frame)
  
    return self._detect_by_yolo(frame)
```

---

## 📝 Summary

AgriBot ทำงานโดย:

1. **กล้องจับภาพ** → ส่งให้ YOLO11
2. **YOLO11 ตรวจจับ** → หาหญ้า + พริก
3. **Tracker ติดตาม** → กำหนด ID, เก็บประวัติ
4. **Brain คำนวณ** → แปลง pixel → cm
5. **ส่งคำสั่ง** → ESP32 ทำงานตามลำดับ
6. **ESP32 ควบคุม** → Motor, Servo, Pump
7. **Mark Sprayed** → บันทึก ID ที่พ่นแล้ว
8. **Loop** → กลับไปค้นหา, ข้าม ID ที่พ่นแล้ว

**Key Features:**
- ✅ Weed Tracking ป้องกันพ่นซ้ำ
- ✅ Physical Buttons (Start + Emergency Stop)
- ✅ LCD Status Display
- ✅ Web Dashboard Control

---

**เขียนโดย:** AgriBot Team
**Version:** 2.3.0
**อัพเดท:** 2026-01-15
