# 📡 Communication Protocol Specification

## Overview

ระบบใช้ Serial Communication ผ่าน USB ระหว่าง Raspberry Pi 5 และ ESP32

```
┌─────────────────┐         ┌─────────────────┐
│  Raspberry Pi   │◄──USB──►│     ESP32       │
│     (Brain)     │ 115200  │    (Worker)     │
├─────────────────┤         ├─────────────────┤
│ • AI Inference  │         │ • Motor Control │
│ • Physics Calc  │         │ • Servo Control │
│ • Task Queue    │         │ • Relay Control │
└─────────────────┘         └─────────────────┘
```

## Serial Configuration

| Parameter | Value |
|-----------|-------|
| Baud Rate | 115200 |
| Data Bits | 8 |
| Stop Bits | 1 |
| Parity | None |
| Timeout | 5 seconds |

## Message Format

### Request (Pi → ESP32)
```
<COMMAND>[:<PARAM1>[:<PARAM2>]]\n
```

### Response (ESP32 → Pi)
```
<STATUS>\n
```

## Command Reference

### 1. System Commands

#### CHECK
ตรวจสอบการเชื่อมต่อ

```
Request:  CHECK\n
Response: READY\n
```

#### STOP_ALL
หยุดฉุกเฉินทุกระบบ

```
Request:  STOP_ALL\n
Response: EMERGENCY_STOPPED\n
```

---

### 2. Arm Control (Z-Axis)

#### ACT:Z_OUT
ยืดแขนออก (DC Motor)

```
Request:  ACT:Z_OUT:1.50\n   # ยืด 1.5 วินาที
Response: DONE\n
```

| Parameter | Type | Range | Description |
|-----------|------|-------|-------------|
| seconds | float | 0.0 - 5.0 | เวลาที่ยืด |

#### ACT:Z_IN
หดแขนกลับ (DC Motor)

```
Request:  ACT:Z_IN:2.00\n    # หด 2.0 วินาที
Response: DONE\n
```

---

### 3. Head Control (Y-Axis)

#### ACT:Y_DOWN
หัวฉีดลง (Servo → 90°)

```
Request:  ACT:Y_DOWN\n
Response: DONE\n
```

#### ACT:Y_UP
หัวฉีดขึ้น (Servo → 0°)

```
Request:  ACT:Y_UP\n
Response: DONE\n
```

---

### 4. Spray Control

#### SPRAY
เปิดปั๊มพ่นยา

```
Request:  SPRAY:2.00\n       # พ่น 2 วินาที
Response: DONE\n
```

| Parameter | Type | Range | Description |
|-----------|------|-------|-------------|
| seconds | float | 0.5 - 10.0 | เวลาพ่น |

---

### 5. Movement Control

#### MOVE_X:FW
รถเดินหน้า

```
Request:  MOVE_X:FW\n
Response: DONE\n
```

#### MOVE_X:BW
รถถอยหลัง

```
Request:  MOVE_X:BW\n
Response: DONE\n
```

#### STOP_X
หยุดรถ

```
Request:  STOP_X\n
Response: DONE\n
```

---

## Response Codes

| Code | Description |
|------|-------------|
| `READY` | ระบบพร้อม |
| `DONE` | คำสั่งเสร็จสิ้น |
| `EMERGENCY_STOPPED` | หยุดฉุกเฉินแล้ว |
| `ERR:UNKNOWN_CMD` | ไม่รู้จักคำสั่ง |

---

## Handshake Protocol

เพื่อป้องกันการส่งคำสั่งซ้อนกัน ระบบใช้ Synchronous Handshake:

```
┌──────────┐                    ┌──────────┐
│    Pi    │                    │  ESP32   │
└────┬─────┘                    └────┬─────┘
     │                               │
     │  ACT:Z_OUT:1.50\n             │
     │──────────────────────────────►│
     │                               │ ← Motor running
     │                               │ ← delay(1500ms)
     │                               │ ← Motor stop
     │              DONE\n           │
     │◄──────────────────────────────│
     │                               │
     │  ACT:Y_DOWN\n                 │
     │──────────────────────────────►│
     │                               │
```

**กฎ**: Pi ต้องรอ `DONE` ก่อนส่งคำสั่งถัดไปเสมอ

---

## Mission Sequence Example

ลำดับคำสั่งสำหรับพ่นยา 1 จุด:

```
1. ACT:Z_OUT:1.50   → รอ DONE
2. ACT:Y_DOWN       → รอ DONE
3. SPRAY:2.00       → รอ DONE
4. ACT:Y_UP         → รอ DONE
5. ACT:Z_IN:2.00    → รอ DONE
```

---

## Error Handling

### Timeout
ถ้าไม่ได้รับ Response ภายใน 5 วินาที → ส่ง `STOP_ALL`

### Unknown Command
ESP32 ตอบ `ERR:UNKNOWN_CMD` → Log error และ skip

### Connection Lost
ตรวจจับด้วย `CHECK` command ทุก 10 วินาที
