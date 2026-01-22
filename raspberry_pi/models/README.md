# AgriBot Models Directory

โฟลเดอร์สำหรับเก็บ YOLO11 Models

## วิธีใช้

1. วางไฟล์โมเดล `.pt` ในโฟลเดอร์นี้
2. ระบบจะโหลดโมเดลชื่อ `best.pt` อัตโนมัติ
3. หรือระบุชื่อไฟล์เองใน calibration.json

## ไฟล์ที่รองรับ

- `best.pt` - โมเดลหลัก (auto-load)
- `weed_chili.pt` - โมเดลสำรอง
- `*.pt` - YOLO11 format

## โครงสร้าง

```
models/
├── README.md
├── best.pt          ← โมเดลหลัก
├── weed_chili.pt    ← โมเดลสำรอง
└── old/             ← เก็บโมเดลเก่า
```

## อัพเดทโมเดล

1. Train โมเดลใหม่
2. Copy ไฟล์ `best.pt` มาวางทับ
3. Restart ระบบ
