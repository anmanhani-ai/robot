# 🚜 AgriBot - ระบบหุ่นยนต์กำจัดวัชพืชอัจฉริยะ

**Intelligent Weed Spraying Robot with YOLO11 Detection**

---

## 📋 สารบัญ

1. [ภาพรวมระบบ](#ภาพรวมระบบ)
2. [อุปกรณ์ที่ต้องใช้](#อุปกรณ์ที่ต้องใช้)
3. [ติดตั้ง ESP32](#ติดตั้ง-esp32)
4. [ติดตั้ง Raspberry Pi](#ติดตั้ง-raspberry-pi)
5. [ติดตั้ง Web Dashboard](#ติดตั้ง-web-dashboard)
6. [การ Calibrate](#การ-calibrate)
7. [การใช้งาน](#การใช้งาน)
8. [Troubleshooting](#troubleshooting)

---

## ภาพรวมระบบ

```
┌─────────────────────────────────────────────────────────────────┐
│                        AgriBot System                           │
├─────────────────────────────────────────────────────────────────┤
│                                                                 │
│  ┌─────────────┐    Serial    ┌─────────────┐    WiFi          │
│  │   ESP32     │◄────────────►│ Raspberry   │◄──────►  📱      │
│  │  (Control)  │              │  Pi 5       │         Web      │
│  └──────┬──────┘              │  (Brain)    │         Dashboard│
│         │                     └──────┬──────┘                   │
│         │                            │                          │
│    ┌────┴────┐                  ┌────┴────┐                     │
│    │ Motors  │                  │ Camera  │                     │
│    │ Servo   │                  │ YOLO11  │                     │
│    │ Pump    │                  │ AI      │                     │
│    │ Sensors │                  └─────────┘                     │
│    └─────────┘                                                  │
│                                                                 │
└─────────────────────────────────────────────────────────────────┘
```

### หน้าที่แต่ละส่วน

| อุปกรณ์          | หน้าที่                                                               |
| ----------------------- | ---------------------------------------------------------------------------- |
| **ESP32**         | ควบคุม Motor, Servo, Pump, อ่าน Sensor                             |
| **Raspberry Pi**  | ประมวลผล AI (YOLO11), คำนวณตำแหน่ง, สั่งงาน ESP32 |
| **Web Dashboard** | แสดงผล, ควบคุมระยะไกล, ดู Log                           |

---

## อุปกรณ์ที่ต้องใช้

### Hardware

| รายการ        | จำนวน | หมายเหตุ                                  |
| ------------------- | ---------- | ------------------------------------------------- |
| ESP32 DevKit        | 1          | แนะนำ ESP32-WROOM-32                         |
| Raspberry Pi 5      | 1          | 4GB RAM ขึ้นไป                              |
| Camera              | 1          | USB Camera หรือ Pi Camera                     |
| DC Motor (ล้อ)   | 2-4        | พร้อม Motor Driver (L298N)                   |
| DC Motor (แขน Z) | 1          | พร้อม Motor Driver                           |
| Servo (แกน Y)    | 1          | SG90 หรือ MG996R                              |
| Relay Module        | 1          | สำหรับ Pump                                 |
| Pump                | 1          | 12V DC Pump                                       |
| Ultrasonic Sensor   | 3          | HC-SR04 (หน้า/ซ้าย/ขวา)                |
| Rotary Encoder      | 1          | (Optional) สำหรับวัดตำแหน่งแขน |
| Power Supply        | 1          | 12V สำหรับ Motor, 5V สำหรับ ESP32/Pi  |

### Pin Connection (ESP32)

```
ESP32 Pin Configuration (v2.4)
═══════════════════════════════════════════════════════

Motor Z (แขนยืด/หด):
  IN1  → GPIO 26
  IN2  → GPIO 27
  PWM  → GPIO 14

Dual Motor / L298N (ล้อซ้าย + ขวา):
┌───────────────────────────────────────────┐
│ L298N Driver                              │
│ =========================================│
│ ล้อซ้าย (Motor A):                        │
│   IN1 → GPIO 32                           │
│   IN2 → GPIO 33                           │
│   ENA → GPIO 25 (PWM)                     │
│                                           │
│ ล้อขวา (Motor B):                         │
│   IN3 → GPIO 17                           │
│   IN4 → GPIO 16                           │
│   ENB → GPIO 23 (PWM)                     │
└───────────────────────────────────────────┘

Servo Y (หัวฉีด):
  Signal → GPIO 13

Pump Relay:
  Signal → GPIO 4

Ultrasonic (2 ตัว - Front + Right เท่านั้น):
  Front: TRIG → GPIO 12, ECHO → GPIO 5
  Right: TRIG → GPIO 18, ECHO → GPIO 19
  Left:  ❌ ปิดใช้งาน (GPIO 16 ใช้กับ Motor Right)

Encoder (Optional):
  Channel A → GPIO 35
  Channel B → GPIO 36

Buttons:
  Start (กดค้าง 3s) → GPIO 15
  Emergency Stop    → GPIO 34

LCD I2C (16x2):
  SDA → GPIO 21
  SCL → GPIO 22
  Address: 0x27 (หรือ 0x3F)
```

---

## ติดตั้ง ESP32

### วิธีที่ 1: Arduino IDE (แนะนำ)

**Step 1: ติดตั้ง Arduino IDE**

- ดาวน์โหลดจาก [arduino.cc](https://www.arduino.cc/en/software)

**Step 2: ติดตั้ง ESP32 Board**

```
1. File → Preferences
2. Additional Boards Manager URLs เพิ่ม:
   https://dl.espressif.com/dl/package_esp32_index.json
3. Tools → Board → Boards Manager
4. ค้นหา "ESP32" → Install
```

**Step 3: ติดตั้ง Library**

```
Sketch → Include Library → Manage Libraries
ค้นหา "ESP32Servo" → Install
```

**Step 4: เปิด Project**

```
File → Open → เลือก:
esp32/AgriBot_ESP32/AgriBot_ESP32.ino
```

**Step 5: ตั้งค่า Board**

```
Tools → Board → ESP32 Dev Module
Tools → Port → COM? (เลือก port ที่ ESP32 ต่ออยู่)
```

**Step 6: Upload**

```
กด Upload (→) รอจนเสร็จ
```

### วิธีที่ 2: PlatformIO

```bash
# เปิดโฟลเดอร์ esp32/ ใน VSCode + PlatformIO
# กด Upload ที่ Status Bar
```

### ทดสอบ ESP32

เปิด Serial Monitor (115200 baud):

```
PING      → ตอบ PONG
STATUS    → ตอบ OK
```

---

## ติดตั้ง Raspberry Pi

### Step 1: ติดตั้ง OS

```bash
# ใช้ Raspberry Pi Imager
# เลือก Raspberry Pi OS (64-bit)
# Flash ลง SD Card
```

### Step 2: Update System

```bash
sudo apt update && sudo apt upgrade -y
```

### Step 3: ติดตั้ง Python

```bash
sudo apt install python3-pip python3-venv -y

cd /home/pi
mkdir agribot && cd agribot
python3 -m venv venv
source venv/bin/activate
```

### Step 4: Copy ไฟล์ Project

```bash
# จาก PC
scp -r raspberry_pi/* pi@<PI_IP>:/home/pi/agribot/
```

### Step 5: ติดตั้ง Dependencies

```bash
pip install -r requirements.txt
```

**requirements.txt:**

```
pyserial
opencv-python-headless
numpy
ultralytics
```

### Step 6: ติดตั้ง YOLO Model

```bash
mkdir -p models
# Copy best.pt มาวางใน models/
```

### Step 7: ตั้งค่า Serial Permission

```bash
sudo usermod -a -G dialout pi
sudo reboot
```

### Step 8: ทดสอบ

```bash
python calibration_simple.py  # ทดสอบ Calibration
python main.py                # รันระบบหลัก

```

---

## ติดตั้ง Web Dashboard

### บน Raspberry Pi

```bash
# ติดตั้ง Node.js
curl -fsSL https://deb.nodesource.com/setup_20.x | sudo -E bash -
sudo apt install nodejs -y

# Build Frontend
cd PI_WEBAPP/frontend
npm install && npm run build

# Run Backend
cd ../backend
pip install -r requirements.txt
# กด Ctrl+C หยุด server เก่า
# แล้วรันใหม่
/home/nww/Downloads/pro/project-robot/.venv/bin/uvicorn main:app --host 0.0.0.0 --port 8000 
```

**เข้าใช้งาน:** `http://<PI_IP>:8000`

### บน PC (Development)

```bash
# Backend
cd PI_WEBAPP/backend
/home/nww/Downloads/pro/project-robot/.venv/bin/uvicorn main:app --host 0.0.0.0 --port 8000 

# Frontend
cd PI_WEBAPP/frontend
npm install && npm run dev
```

**เข้าใช้งาน:** `http://localhost:5173`

---

## การ Calibrate

```bash
cd raspberry_pi
python calibration_simple.py
```

1. เลือก "1. Full Calibration"
2. กรอกค่า pixel_to_cm (วางไม้บรรทัดหน้ากล้อง วัด pixel)
3. กรอก arm_offset (ระยะกล้อง → แขน)
4. บันทึก

**ดูคู่มือละเอียด:** `CALIBRATION_GUIDE.md`

---

## การใช้งาน

### คำสั่ง ESP32

| คำสั่ง      | ผลลัพธ์                          |
| ----------------- | --------------------------------------- |
| `MOVE_FORWARD`  | รถเดินหน้า                    |
| `MOVE_STOP`     | รถหยุด                            |
| `ACT:Z_OUT:2.5` | แขนยืด 2.5 วินาที           |
| `ACT:Z_IN:2.5`  | แขนหด                              |
| `ACT:Y_DOWN`    | หัวฉีดลง                        |
| `ACT:Y_UP`      | หัวฉีดขึ้น                    |
| `ACT:SPRAY:1.0` | พ่นยา 1 วินาที               |
| `STOP_ALL`      | หยุดทุกระบบ                  |
| `US_GET_DIST`   | อ่านระยะ Ultrasonic             |
| `Z_MOVE:15.0`   | แขนไปตำแหน่ง 15cm (Encoder) |

---

## Troubleshooting

| ปัญหา              | วิธีแก้                     |
| ----------------------- | ---------------------------------- |
| ESP32 ไม่ตอบ      | ตรวจสอบ Port, กด Reset    |
| YOLO ไม่โหลด     | ตรวจสอบไฟล์ใน models/ |
| Camera ไม่ทำงาน | `ls /dev/video*`                 |
| Permission denied       | `sudo usermod -a -G dialout pi`  |

---

## 📁 โครงสร้างโปรเจค

```
project-robot/
├── esp32/AgriBot_ESP32/     ← ESP32 Code
├── raspberry_pi/            ← Pi Code + AI
│   ├── models/best.pt       ← YOLO Model
│   └── calibration.json     ← Calibration
└── PI_WEBAPP/               ← Web Dashboard
```

---

**Version:** 2.2.0 | **อัพเดท:** 2026-01-13
