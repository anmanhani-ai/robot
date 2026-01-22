# 📘 คู่มือการติดตั้งฮาร์ดแวร์ AgriBot ESP32

## 📋 สารบัญ

1. [ภาพรวมระบบ](#ภาพรวมระบบ)
2. [อุปกรณ์ที่ต้องใช้](#อุปกรณ์ที่ต้องใช้)
3. [สรุป GPIO ทั้งหมด](#สรุป-gpio-ทั้งหมด)
4. [ขั้นตอนที่ 1: เตรียม ESP32](#ขั้นตอนที่-1-เตรียม-esp32)
5. [ขั้นตอนที่ 2: ติดตั้ง Motor Driver](#ขั้นตอนที่-2-ติดตั้ง-motor-driver)
6. [ขั้นตอนที่ 3: ต่อ Motor ล้อซ้าย-ขวา](#ขั้นตอนที่-3-ต่อ-motor-ล้อซ้าย-ขวา)
7. [ขั้นตอนที่ 4: ต่อ Motor แกน Z](#ขั้นตอนที่-4-ต่อ-motor-แกน-z)
8. [ขั้นตอนที่ 5: ต่อ Motor แกน Y](#ขั้นตอนที่-5-ต่อ-motor-แกน-y)
9. [ขั้นตอนที่ 6: ต่อ Relay และปั๊ม](#ขั้นตอนที่-6-ต่อ-relay-และปั๊ม)
10. [ขั้นตอนที่ 7: ต่อ Ultrasonic Sensors](#ขั้นตอนที่-7-ต่อ-ultrasonic-sensors)
11. [ขั้นตอนที่ 8: ต่อ Buzzer](#ขั้นตอนที่-8-ต่อ-buzzer)
12. [ขั้นตอนที่ 9: ต่อ LCD I2C](#ขั้นตอนที่-9-ต่อ-lcd-i2c)
13. [ขั้นตอนที่ 10: ต่อปุ่มควบคุม](#ขั้นตอนที่-10-ต่อปุ่มควบคุม)
14. [ขั้นตอนที่ 11: ต่อ Encoder (ถ้าใช้)](#ขั้นตอนที่-11-ต่อ-encoder-ถ้าใช้)
15. [แผนผังการเชื่อมต่อทั้งหมด](#แผนผังการเชื่อมต่อทั้งหมด)
16. [การติดตั้งซอฟต์แวร์](#การติดตั้งซอฟต์แวร์)
17. [การทดสอบระบบ](#การทดสอบระบบ)
18. [ปัญหาที่พบบ่อย](#ปัญหาที่พบบ่อย)

---

## ภาพรวมระบบ

### AgriBot คืออะไร?
AgriBot คือหุ่นยนต์กำจัดวัชพืชอัตโนมัติ ควบคุมด้วย ESP32 ที่รับคำสั่งจาก Raspberry Pi

### องค์ประกอบหลัก:

```
┌─────────────────────────────────────────────────────────────┐
│                      AgriBot System                          │
├─────────────────────────────────────────────────────────────┤
│                                                               │
│   ┌─────────────┐      Serial      ┌─────────────────┐       │
│   │ Raspberry Pi│◄────────────────►│     ESP32       │       │
│   │  (สมองกล)   │                  │  (ควบคุม Motor) │       │
│   └─────────────┘                  └────────┬────────┘       │
│         │                                   │                │
│         ▼                                   ▼                │
│   ┌───────────┐            ┌────────────────────────────┐   │
│   │  Camera   │            │         Actuators          │   │
│   │  (กล้อง)  │            │  - Motor ล้อ (ซ้าย/ขวา)    │   │
│   └───────────┘            │  - Motor Z (แขนยืด/หด)     │   │
│                            │  - Motor Y (หัวพ่นขึ้น/ลง) │   │
│                            │  - Pump (ปั๊มพ่นยา)        │   │
│                            └────────────────────────────┘   │
│                                          │                   │
│                                          ▼                   │
│                            ┌────────────────────────────┐   │
│                            │          Sensors           │   │
│                            │  - Ultrasonic x3           │   │
│                            │  - Encoder (optional)      │   │
│                            │  - Emergency Button        │   │
│                            └────────────────────────────┘   │
└─────────────────────────────────────────────────────────────┘
```

### ระบบแขนกล 2 แกน:

```
              ↑ แกน Y (ขึ้น/ลง)
              │   Motor Y
              │
          ┌───┴───┐
          │หัวพ่น │ ← Ultrasonic Y-axis (วัดความสูง)
          └───────┘
              │
      ◄───────┼───────► แกน Z (ยืด/หด)
          Motor Z       
              │
         ┌────┴────┐
         │ ตัวหุ่น │
         └─────────┘
```

---

## อุปกรณ์ที่ต้องใช้

### 📦 รายการอุปกรณ์หลัก

| # | อุปกรณ์ | จำนวน | ราคาประมาณ | หมายเหตุ |
|---|---------|-------|-----------|----------|
| 1 | ESP32 DevKit V1 | 1 | ~150 บาท | 30 pin |
| 2 | Motor Driver L298N หรือ TB6612 | 2 | ~60 บาท/ตัว | แบบ 4 ขา (ไม่มี ENA/ENB) |
| 3 | DC Motor 12V | 4 | ~80 บาท/ตัว | ล้อ 2 + แขน Z 1 + แขน Y 1 |
| 4 | Relay Module 5V | 1 | ~35 บาท | 1 Channel |
| 5 | ปั๊มน้ำ 12V | 1 | ~120 บาท | ปั๊มมินิ |
| 6 | Ultrasonic HC-SR04 | 3 | ~35 บาท/ตัว | Front + Right + Y-axis |
| 7 | Active Buzzer 5V | 1 | ~15 บาท | |
| 8 | LCD 16x2 I2C | 1 | ~80 บาท | Address 0x27 หรือ 0x3F |
| 9 | Push Button | 2 | ~5 บาท/ตัว | Start + Emergency Stop |
| 10 | Resistor 10kΩ | 1-3 | ~1 บาท/ตัว | สำหรับ Pull-up |

### 📦 อุปกรณ์เสริม (Optional)

| # | อุปกรณ์ | จำนวน | หมายเหตุ |
|---|---------|-------|----------|
| 1 | Rotary Encoder | 1 | สำหรับวัดตำแหน่ง Motor Z แม่นยำ |
| 2 | Power Supply 12V 5A | 1 | สำหรับ Motor (ถ้าใช้แบต) |
| 3 | Buck Converter | 1 | 12V → 5V สำหรับ ESP32 |

### 🔧 เครื่องมือที่ต้องใช้

- สาย Jumper (ผู้-ผู้, ผู้-เมีย)
- Breadboard
- ไขควง
- มัลติมิเตอร์ (แนะนำ)
- หัวแร้งบัดกรี (ถ้าต้องการต่อถาวร)

---

## สรุป GPIO ทั้งหมด

### 📍 ตาราง GPIO ที่ใช้

| GPIO | อุปกรณ์ | ประเภท | หมายเหตุ |
|------|---------|--------|----------|
| **2** | Motor Y IN2 | Output | ⚠️ มี LED onboard |
| **4** | Pump Relay | Output | |
| **5** | US Front ECHO | Input | |
| **12** | US Front TRIG | Output | ⚠️ ต้องเป็น LOW ตอน boot |
| **13** | Motor Y IN1 | Output | |
| **14** | Buzzer | Output | |
| **15** | Button Start | Input | ใช้ Internal Pull-up |
| **16** | Motor Right IN2 | Output | |
| **17** | Motor Right IN1 | Output | |
| **18** | US Right TRIG | Output | |
| **19** | US Right ECHO | Input | |
| **21** | LCD SDA | I2C | |
| **22** | LCD SCL | I2C | |
| **23** | US Y-axis ECHO | Input | |
| **25** | US Y-axis TRIG | Output | |
| **26** | Motor Z IN1 | Output | |
| **27** | Motor Z IN2 | Output | |
| **32** | Motor Left IN1 | Output | |
| **33** | Motor Left IN2 | Output | |
| **34** | Button E-Stop | Input Only | ⚠️ ต้องต่อ Pull-up 10kΩ |
| **35** | Encoder A | Input Only | Optional - ต้องต่อ Pull-up |
| **36** | Encoder B | Input Only | Optional - ต้องต่อ Pull-up |

### 📍 GPIO ที่ห้ามใช้

| GPIO | เหตุผล |
|------|--------|
| 0 | Boot button |
| 1 | TX0 (Serial) |
| 3 | RX0 (Serial) |
| 6-11 | ใช้กับ Flash Memory |

---

## ขั้นตอนที่ 1: เตรียม ESP32

### 1.1 ติดตั้ง Arduino IDE

1. ดาวน์โหลด Arduino IDE จาก https://www.arduino.cc/en/software
2. ติดตั้งตามปกติ

### 1.2 เพิ่ม ESP32 Board

1. เปิด Arduino IDE
2. ไปที่ `File` → `Preferences`
3. ใส่ URL นี้ใน "Additional Board Manager URLs":
   ```
   https://raw.githubusercontent.com/espressif/arduino-esp32/gh-pages/package_esp32_index.json
   ```
4. ไปที่ `Tools` → `Board` → `Boards Manager`
5. ค้นหา "ESP32" และติดตั้ง "ESP32 by Espressif Systems"

### 1.3 ติดตั้ง Library

ไปที่ `Tools` → `Manage Libraries` แล้วติดตั้ง:
- **LiquidCrystal_I2C** by Frank de Brabander

### 1.4 เลือก Board และ Port

1. `Tools` → `Board` → `ESP32 Arduino` → `ESP32 Dev Module`
2. `Tools` → `Port` → เลือก COM port ที่ ESP32 ต่ออยู่

---

## ขั้นตอนที่ 2: ติดตั้ง Motor Driver

### ⚠️ สำคัญ: Motor Driver แบบ 4 ขา

โปรเจคนี้ใช้ Motor Driver แบบ **ไม่มี ENA/ENB** (ใช้ PWM โดยตรงผ่าน IN1/IN2)

### หลักการทำงาน:

| การเคลื่อนที่ | IN1 | IN2 | อธิบาย |
|--------------|-----|-----|--------|
| **หน้า** | PWM (0-255) | 0 | ความเร็วขึ้นกับค่า PWM |
| **ถอย** | 0 | PWM (0-255) | ความเร็วขึ้นกับค่า PWM |
| **หยุด** | 0 | 0 | Motor หยุดทันที |

### การต่อไฟเลี้ยง Motor Driver:

```
แหล่งจ่ายไฟ 12V           Motor Driver
═════════════════════════════════════════
    12V+ ──────────────────► 12V / VCC
    GND  ──────────────────► GND
                              │
                              └──────────► ESP32 GND (ต่อร่วม!)
```

> ⚠️ **สำคัญมาก!** GND ของ Motor Driver, ESP32 และแหล่งจ่ายไฟ **ต้องต่อร่วมกัน!**

---

## ขั้นตอนที่ 3: ต่อ Motor ล้อซ้าย-ขวา

### แผนผังการต่อ:

```
                    Motor Driver (Dual)
                    ┌───────────────────┐
                    │                   │
    Motor ซ้าย ◄────┤ OUT1         12V ├────► Power 12V+
    Motor ซ้าย ◄────┤ OUT2         GND ├────► Power GND + ESP32 GND
                    │                   │
    Motor ขวา  ◄────┤ OUT3        IN1  ├────► ESP32 GPIO 32 (PWM ซ้าย-หน้า)
    Motor ขวา  ◄────┤ OUT4        IN2  ├────► ESP32 GPIO 33 (PWM ซ้าย-ถอย)
                    │             IN3  ├────► ESP32 GPIO 17 (PWM ขวา-หน้า)
                    │             IN4  ├────► ESP32 GPIO 16 (PWM ขวา-ถอย)
                    └───────────────────┘
```

### ขั้นตอนการต่อ:

1. **ต่อไฟเลี้ยง Motor Driver:**
   - 12V จากแหล่งจ่ายไฟ → ขา 12V ของ Driver
   - GND จากแหล่งจ่ายไฟ → ขา GND ของ Driver

2. **ต่อ GND ร่วมกับ ESP32:**
   - ใช้สาย Jumper ต่อ GND ของ Driver → GND ของ ESP32

3. **ต่อสัญญาณควบคุม (Motor ซ้าย):**
   - IN1 → GPIO 32
   - IN2 → GPIO 33

4. **ต่อสัญญาณควบคุม (Motor ขวา):**
   - IN3 → GPIO 17
   - IN4 → GPIO 16

5. **ต่อ Motor:**
   - OUT1, OUT2 → Motor ซ้าย
   - OUT3, OUT4 → Motor ขวา

### ทดสอบ:
```
คำสั่ง Serial: DRIVE_FW   → ล้อทั้งสองหมุนไปข้างหน้า
คำสั่ง Serial: DRIVE_BW   → ล้อทั้งสองหมุนถอยหลัง
คำสั่ง Serial: TURN_LEFT  → หมุนซ้าย
คำสั่ง Serial: TURN_RIGHT → หมุนขวา
```

---

## ขั้นตอนที่ 4: ต่อ Motor แกน Z

### หน้าที่: ยืด/หด แขนกล (แนวนอน)

```
              Motor Driver (Z)
              ┌───────────────┐
              │               │
Motor Z  ◄────┤ OUT1     12V ├────► Power 12V+
Motor Z  ◄────┤ OUT2     GND ├────► Power GND + ESP32 GND
              │          IN1 ├────► ESP32 GPIO 26 (PWM ยืด)
              │          IN2 ├────► ESP32 GPIO 27 (PWM หด)
              └───────────────┘
```

### ขั้นตอนการต่อ:

1. ต่อไฟเลี้ยง 12V, GND เหมือนขั้นตอนที่ 3
2. ต่อ GND ร่วมกับ ESP32
3. IN1 → GPIO 26
4. IN2 → GPIO 27
5. OUT1, OUT2 → Motor Z

### ทดสอบ:
```
คำสั่ง Serial: ACT:Z_OUT:2.0  → แขนยืดออก 2 วินาที
คำสั่ง Serial: ACT:Z_IN:2.0   → แขนหดเข้า 2 วินาที
```

---

## ขั้นตอนที่ 5: ต่อ Motor แกน Y

### หน้าที่: ยก/วาง หัวพ่น (แนวตั้ง)

```
              Motor Driver (Y)
              ┌───────────────┐
              │               │
Motor Y  ◄────┤ OUT1     12V ├────► Power 12V+
Motor Y  ◄────┤ OUT2     GND ├────► Power GND + ESP32 GND
              │          IN1 ├────► ESP32 GPIO 13 (PWM ขึ้น)
              │          IN2 ├────► ESP32 GPIO 2  (PWM ลง)
              └───────────────┘
```

> ⚠️ **หมายเหตุ:** GPIO 2 มี LED onboard แต่ใช้งานได้ปกติ (LED จะกะพริบตอน Motor ทำงาน)

### ขั้นตอนการต่อ:

1. ต่อไฟเลี้ยง 12V, GND
2. ต่อ GND ร่วมกับ ESP32
3. IN1 → GPIO 13
4. IN2 → GPIO 2
5. OUT1, OUT2 → Motor Y

### ทดสอบ:
```
คำสั่ง Serial: ACT:Y_UP    → หัวพ่นยกขึ้น
คำสั่ง Serial: ACT:Y_DOWN  → หัวพ่นลง
คำสั่ง Serial: Y_UP:2.0    → ยกขึ้น 2 วินาที
คำสั่ง Serial: Y_DOWN:2.0  → ลง 2 วินาที
```

---

## ขั้นตอนที่ 6: ต่อ Relay และปั๊ม

### แผนผังการต่อ:

```
                    Relay Module 5V
                    ┌───────────────┐
                    │               │
ESP32 5V  ─────────►│ VCC       COM ├───────► ไฟ+ ปั๊ม
ESP32 GND ─────────►│ GND        NO ├───────► Power 12V+
ESP32 GPIO 4 ─────►│ IN         NC │ (ไม่ใช้)
                    └───────────────┘

ไฟ- ปั๊ม ──────────────────────────────────► Power GND
```

### อธิบาย:
- **COM** (Common): ขากลาง ต่อกับ ขา+ ของปั๊ม
- **NO** (Normally Open): ขาปกติเปิด ต่อกับ 12V+
- เมื่อ Relay ทำงาน COM จะเชื่อมกับ NO → ปั๊มทำงาน

### ขั้นตอนการต่อ:

1. **ต่อไฟเลี้ยง Relay:**
   - VCC → ESP32 5V (หรือ VIN)
   - GND → ESP32 GND

2. **ต่อสัญญาณควบคุม:**
   - IN → GPIO 4

3. **ต่อปั๊ม:**
   - COM → ขา+ ของปั๊ม
   - NO → Power 12V+
   - ขา- ของปั๊ม → Power GND

### ทดสอบ:
```
คำสั่ง Serial: PUMP_ON   → ได้ยินเสียง Relay คลิก, ปั๊มทำงาน
คำสั่ง Serial: PUMP_OFF  → Relay คลิก, ปั๊มหยุด
คำสั่ง Serial: ACT:SPRAY:3.0 → พ่น 3 วินาทีแล้วหยุด
```

---

## ขั้นตอนที่ 7: ต่อ Ultrasonic Sensors

### ภาพรวม: มี 3 ตัว

| Sensor | ตำแหน่งติดตั้ง | หน้าที่ |
|--------|--------------|---------|
| **Front** | หน้าหุ่น ชี้ไปข้างหน้า | ตรวจจับสิ่งกีดขวางด้านหน้า |
| **Right** | ข้างขวาหุ่น ชี้ไปด้านขวา | ตรวจจับสิ่งกีดขวางด้านขวา |
| **Y-axis** | ที่หัวพ่น ชี้ลงพื้น | วัดความสูงหัวพ่นจากพื้น |

### 7.1 ต่อ Ultrasonic Front

```
HC-SR04 (Front)                ESP32
═══════════════════════════════════════
VCC  ─────────────────────────► 5V
GND  ─────────────────────────► GND
TRIG ─────────────────────────► GPIO 12
ECHO ─────────────────────────► GPIO 5
```

### 7.2 ต่อ Ultrasonic Right

```
HC-SR04 (Right)                ESP32
═══════════════════════════════════════
VCC  ─────────────────────────► 5V
GND  ─────────────────────────► GND
TRIG ─────────────────────────► GPIO 18
ECHO ─────────────────────────► GPIO 19
```

### 7.3 ต่อ Ultrasonic Y-axis (วัดความสูง)

```
HC-SR04 (Y-axis)               ESP32
═══════════════════════════════════════
VCC  ─────────────────────────► 5V
GND  ─────────────────────────► GND
TRIG ─────────────────────────► GPIO 25
ECHO ─────────────────────────► GPIO 23

📌 ติดตั้งที่หัวพ่น ชี้ลงพื้น
   ใช้วัดระยะห่างจากหัวพ่นถึงพื้น/วัชพืช
```

### ทดสอบ:
```
คำสั่ง Serial: US_GET_DIST
ผลลัพธ์: DIST:25.3,45.2,12.5
         ↑     ↑     ↑
       Front Right Y-axis (cm)
```

---

## ขั้นตอนที่ 8: ต่อ Buzzer

### แผนผังการต่อ:

```
Active Buzzer                  ESP32
═══════════════════════════════════════
+ (ขายาว)  ───────────────────► GPIO 14
- (ขาสั้น) ───────────────────► GND
```

### วิธีดูขั้ว Buzzer:
- **ขายาว** = ขั้วบวก (+)
- **ขาสั้น** = ขั้วลบ (-)
- หรือดูที่บน Buzzer จะมีเครื่องหมาย + กำกับ

### ทดสอบ:
```
คำสั่ง Serial: BEEP           → beep 1 ครั้ง
คำสั่ง Serial: BEEP:3         → beep 3 ครั้ง
คำสั่ง Serial: BUZZER_SUCCESS → เสียงสำเร็จ (สูงขึ้น)
คำสั่ง Serial: BUZZER_ERROR   → เสียง error (ต่ำๆ 3 ครั้ง)
คำสั่ง Serial: BUZZER_WARNING → เสียงเตือน (ยาว)
```

---

## ขั้นตอนที่ 9: ต่อ LCD I2C

### แผนผังการต่อ:

```
LCD I2C 16x2                   ESP32
═══════════════════════════════════════
VCC  ─────────────────────────► 5V
GND  ─────────────────────────► GND
SDA  ─────────────────────────► GPIO 21
SCL  ─────────────────────────► GPIO 22
```

### หา I2C Address:

1. Upload โค้ด I2C Scanner:
```cpp
#include <Wire.h>

void setup() {
  Wire.begin();
  Serial.begin(115200);
  Serial.println("I2C Scanner");
}

void loop() {
  for (byte address = 1; address < 127; address++) {
    Wire.beginTransmission(address);
    if (Wire.endTransmission() == 0) {
      Serial.print("Found: 0x");
      Serial.println(address, HEX);
    }
  }
  delay(5000);
}
```

2. ดูผลใน Serial Monitor
3. ปกติจะเป็น `0x27` หรือ `0x3F`

### ปรับ Address (ถ้าจำเป็น):
ใน `lcd_display.h` บรรทัดที่ 14:
```cpp
#define LCD_ADDR    0x27    // เปลี่ยนเป็น 0x3F ถ้าไม่ขึ้น
```

---

## ขั้นตอนที่ 10: ต่อปุ่มควบคุม

### 10.1 ปุ่ม Start (กดค้าง 3 วินาทีเพื่อเริ่ม)

```
Push Button                    ESP32
═══════════════════════════════════════
ขา 1 ─────────────────────────► GPIO 15
ขา 2 ─────────────────────────► GND

(ใช้ Internal Pull-up ของ ESP32 - ไม่ต้องต่อ Resistor)
```

### 10.2 ปุ่ม Emergency Stop

```
                    3.3V
                      │
                   [10kΩ] ← Pull-up Resistor (ต้องต่อ!)
                      │
Push Button ──────────┼─────► GPIO 34
      │
     GND
```

> ⚠️ **สำคัญ!** GPIO 34 เป็น Input Only ไม่มี Internal Pull-up
> **ต้องต่อ Resistor 10kΩ** จาก GPIO 34 ไป 3.3V

### ขั้นตอนการต่อ Emergency Stop:

1. ต่อ Resistor 10kΩ ระหว่าง 3.3V กับ GPIO 34
2. ต่อปุ่มระหว่าง GPIO 34 กับ GND

### ทดสอบ:
- **กดค้างปุ่ม Start 3 วินาที** → LCD แสดง countdown แล้วเริ่มทำงาน
- **กดปุ่ม Emergency Stop** → หุ่นหยุดทำงานทันที

---

## ขั้นตอนที่ 11: ต่อ Encoder (ถ้าใช้)

### Encoder ใช้ทำอะไร?
ใช้วัดตำแหน่ง Motor Z เพื่อให้แม่นยำ (Optional)

### แผนผังการต่อ:

```
                    3.3V
                      │
                   [10kΩ] ← Pull-up Resistor
                      │
Encoder A ────────────┼─────► GPIO 35

                    3.3V
                      │
                   [10kΩ] ← Pull-up Resistor
                      │
Encoder B ────────────┼─────► GPIO 36

Encoder VCC ─────────────────► 5V (หรือ 3.3V ตามรุ่น)
Encoder GND ─────────────────► GND
```

> ⚠️ GPIO 35, 36 เป็น Input Only ไม่มี Internal Pull-up
> **ต้องต่อ Resistor 10kΩ** ทั้ง 2 ขา

### ถ้าไม่ใช้ Encoder:
ในโค้ดจะใช้การควบคุมแบบ Time-based (ตามเวลา) แทน

---

## แผนผังการเชื่อมต่อทั้งหมด

```
┌──────────────────────────────────────────────────────────────────────┐
│                          ESP32 DevKit V1                              │
│                                                                        │
│  ┌──────────────────────────────────────────────────────────────────┐ │
│  │                      GPIO Connections                             │ │
│  ├──────────────────────────────────────────────────────────────────┤ │
│  │                                                                    │ │
│  │  Motor Left  ─────── GPIO 32 (IN1), 33 (IN2)                      │ │
│  │  Motor Right ─────── GPIO 17 (IN1), 16 (IN2)                      │ │
│  │  Motor Z     ─────── GPIO 26 (IN1), 27 (IN2)                      │ │
│  │  Motor Y     ─────── GPIO 13 (IN1), 2 (IN2)                       │ │
│  │                                                                    │ │
│  │  Pump Relay  ─────── GPIO 4                                       │ │
│  │  Buzzer      ─────── GPIO 14                                      │ │
│  │                                                                    │ │
│  │  US Front    ─────── GPIO 12 (TRIG), 5 (ECHO)                     │ │
│  │  US Right    ─────── GPIO 18 (TRIG), 19 (ECHO)                    │ │
│  │  US Y-axis   ─────── GPIO 25 (TRIG), 23 (ECHO)                    │ │
│  │                                                                    │ │
│  │  LCD I2C     ─────── GPIO 21 (SDA), 22 (SCL)                      │ │
│  │                                                                    │ │
│  │  Btn Start   ─────── GPIO 15                                      │ │
│  │  Btn E-Stop  ─────── GPIO 34 (+ Pull-up 10kΩ)                     │ │
│  │                                                                    │ │
│  │  Encoder     ─────── GPIO 35, 36 (+ Pull-up 10kΩ) [Optional]      │ │
│  │                                                                    │ │
│  └──────────────────────────────────────────────────────────────────┘ │
│                                                                        │
│  Power:                                                                │
│    12V ─► Motor Drivers                                               │
│    5V  ─► Relay, LCD, Ultrasonic                                      │
│    3.3V ─► Pull-up Resistors                                          │
│    GND ─► ต่อร่วมทุกอุปกรณ์                                            │
│                                                                        │
└──────────────────────────────────────────────────────────────────────┘
```

---

## การติดตั้งซอฟต์แวร์

### ขั้นตอนการ Upload โค้ด:

1. **เปิด Arduino IDE**

2. **เปิดไฟล์โปรเจค:**
   - `File` → `Open` → เลือก `AgriBot_ESP32.ino`

3. **ตั้งค่า Board:**
   - `Tools` → `Board` → `ESP32 Dev Module`
   - `Tools` → `Upload Speed` → `115200`
   - `Tools` → `Port` → เลือก COM port ที่ถูกต้อง

4. **Upload:**
   - กดปุ่ม Upload (→) หรือ `Ctrl+U`
   - รอจน "Done uploading"

5. **เปิด Serial Monitor:**
   - `Tools` → `Serial Monitor` หรือ `Ctrl+Shift+M`
   - ตั้ง Baud Rate: `115200`
   - ควรเห็น:
   ```
   =============================
     AgriBot ESP32 v2.6.0
     Motor Y + Full Features
   =============================
   [Motor Z] Initialized
   [Motor Y] Initialized
   [Ultrasonic] 3 sensors initialized
   [Buzzer] Initialized on GPIO 14
   Ready to receive commands...
   ```

---

## การทดสอบระบบ

### 1. ทดสอบการเชื่อมต่อ
```
Send: PING
Expect: PONG

Send: STATUS
Expect: OK
```

### 2. ทดสอบ Motor ล้อ
```
Send: DRIVE_FW      → ล้อหมุนไปข้างหน้า
Send: DRIVE_STOP    → หยุด
Send: DRIVE_BW      → ล้อหมุนถอยหลัง
Send: DRIVE_STOP    → หยุด
Send: TURN_LEFT     → หมุนซ้าย
Send: TURN_RIGHT    → หมุนขวา
Send: DRIVE_ESTOP   → หยุดฉุกเฉิน
```

### 3. ทดสอบแขนกล
```
Send: ACT:Z_OUT:1.5  → แขนยืดออก 1.5 วินาที
Send: ACT:Z_IN:1.5   → แขนหดเข้า 1.5 วินาที
Send: ACT:Y_UP       → หัวพ่นยกขึ้น
Send: ACT:Y_DOWN     → หัวพ่นลง
Send: Y_UP:2.0       → ยก 2 วินาที
Send: Y_DOWN:2.0     → ลง 2 วินาที
```

### 4. ทดสอบปั๊ม
```
Send: PUMP_ON        → เปิดปั๊ม
Send: PUMP_OFF       → ปิดปั๊ม
Send: ACT:SPRAY:3.0  → พ่น 3 วินาที
```

### 5. ทดสอบ Ultrasonic
```
Send: US_GET_DIST
Expect: DIST:25.3,45.2,12.5  (cm: Front, Y-axis, Right)
```

### 6. ทดสอบ Buzzer
```
Send: BEEP           → beep
Send: BEEP:3         → beep 3 ครั้ง
Send: BUZZER_SUCCESS → เสียงสำเร็จ
Send: BUZZER_ERROR   → เสียง error
```

### 7. ทดสอบปุ่ม
- กดค้าง Start 3 วินาที → LCD countdown แล้วแสดง "Running"
- กด Emergency Stop → หุ่นหยุด, LCD แสดง "STOPPED"

---

## ปัญหาที่พบบ่อย

### ❓ Motor ไม่หมุน

| สาเหตุ | วิธีแก้ |
|--------|--------|
| GND ไม่ต่อร่วม | ต่อ GND ของ Motor Driver กับ ESP32 |
| ไฟไม่เข้า Driver | เช็ค Power Supply 12V |
| สายหลุด | ตรวจสอบสาย IN1-IN4 |

### ❓ Motor หมุนทางเดียว

- สลับสาย IN1 กับ IN2
- หรือสลับสาย Motor ที่ OUT

### ❓ Motor หมุนแล้วหยุดเอง

- ไฟไม่พอ → ใช้ Power Supply ที่มีกำลังเพียงพอ (12V 3A ขึ้นไป)

### ❓ Ultrasonic อ่านค่า 999 ตลอด

| สาเหตุ | วิธีแก้ |
|--------|--------|
| สายหลวม | เช็คการต่อสาย |
| ติดตั้งผิดทาง | Sensor ต้องไม่ชี้ไปติดกำแพง |
| TRIG/ECHO สลับ | สลับสายให้ถูก |

### ❓ LCD ไม่แสดงผล

| สาเหตุ | วิธีแก้ |
|--------|--------|
| Address ผิด | ใช้ I2C Scanner หา address ที่ถูกต้อง |
| ความสว่างต่ำ | หมุน potentiometer ด้านหลัง LCD |
| SDA/SCL สลับ | สลับสายให้ถูก (SDA=21, SCL=22) |

### ❓ Buzzer ไม่ดัง

| สาเหตุ | วิธีแก้ |
|--------|--------|
| ต่อผิดขั้ว | ขายาว (สั้น) = + (GPIO), ขาสั้น (ยาว) = GND |
| ใช้ Passive Buzzer | ต้องใช้ Active Buzzer |

### ❓ Emergency Button ไม่ทำงาน

| สาเหตุ | วิธีแก้ |
|--------|--------|
| ไม่มี Pull-up | ต่อ Resistor 10kΩ จาก GPIO 34 ไป 3.3V |

### ❓ Upload ไม่ได้

| สาเหตุ | วิธีแก้ |
|--------|--------|
| Port ผิด | เลือก COM port ที่ถูกต้อง |
| Driver ไม่มี | ติดตั้ง CP210x หรือ CH340 driver |
| กด Boot button | กดค้าง BOOT ขณะ Upload (บาง board) |

---

## 📞 ติดต่อ

หากมีปัญหาในการติดตั้ง:
- GitHub Issues: https://github.com/Na1awut/robot/issues

---

**🎉 เมื่อติดตั้งครบแล้ว AgriBot พร้อมใช้งาน!**
