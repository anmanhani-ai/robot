/**
 * dual_motor.h
 * ควบคุม 2 Motor แบบ Differential Drive
 * 
 * สำหรับ Motor Driver แบบ 4 ขา (IN1-IN4)
 * ใช้ PWM โดยตรงผ่าน IN1-IN4 (ไม่มี ENA/ENB)
 * 
 * Features:
 * - Motor ซ้าย + ขวา แยกกัน
 * - Smooth Acceleration (ไม่กระตุก)
 * - Trim Offset (ปรับให้วิ่งตรง)
 * - เลี้ยวซ้าย/ขวา
 */

#ifndef DUAL_MOTOR_H
#define DUAL_MOTOR_H

#include <Arduino.h>

// ==================== PIN CONFIGURATION ====================
// Motor Driver แบบ 4 ขา (ไม่มี ENA/ENB)
// ใช้ PWM โดยตรงผ่าน IN1-IN4

// Motor Left (ล้อซ้าย)
#define PIN_MOTOR_L_IN1   32    // PWM Forward
#define PIN_MOTOR_L_IN2   33    // PWM Backward

// Motor Right (ล้อขวา)
#define PIN_MOTOR_R_IN1   17    // PWM Forward
#define PIN_MOTOR_R_IN2   16    // PWM Backward

// ==================== SETTINGS ====================
#define MOTOR_DEFAULT_SPEED   200     // ความเร็วปกติ (0-255)
#define MOTOR_MIN_SPEED       50      // ความเร็วต่ำสุดที่ motor หมุนได้
#define MOTOR_ACCEL_STEP      5       // เพิ่ม/ลดความเร็วทีละกี่
#define MOTOR_ACCEL_DELAY     20      // หน่วง ms ระหว่าง step

class DualMotorController {
public:
    void init();
    
    // === Movement ===
    void forward();
    void backward();
    void stop();
    void emergencyStop();  // หยุดทันทีไม่ ramp down
    
    // === Turning ===
    void turnLeft();       // หมุนตัวในที่
    void turnRight();
    void curveLeft();      // เลี้ยวโค้ง (ล้อในช้า ล้อนอกเร็ว)
    void curveRight();
    
    // === Speed Control ===
    void setSpeed(int speed);
    void setSpeedSmooth(int targetSpeed);  // เปลี่ยนความเร็วแบบ smooth
    int getSpeed() { return targetSpeed; }
    
    // === Trim (ปรับตรง) ===
    void setTrim(int offset);  // -50 ถึง +50 (บวก=ขวาเร็วกว่า)
    int getTrim() { return trimOffset; }
    void saveTrim();           // บันทึกลง EEPROM
    void loadTrim();           // โหลดจาก EEPROM
    
    // === Update (เรียกใน loop) ===
    void update();  // สำหรับ smooth acceleration
    
    // === Status ===
    bool isMoving() { return currentSpeedL != 0 || currentSpeedR != 0; }
    
private:
    void setMotorL(int speed);  // -255 ถึง +255 (ลบ=ถอย)
    void setMotorR(int speed);
    void applySpeed();
    
    int targetSpeed = 0;        // ความเร็วเป้าหมาย
    int currentSpeedL = 0;      // ความเร็วปัจจุบัน motor ซ้าย
    int currentSpeedR = 0;      // ความเร็วปัจจุบัน motor ขวา
    int trimOffset = 0;         // offset สำหรับวิ่งตรง
    int direction = 0;          // 0=หยุด, 1=หน้า, -1=หลัง
    
    unsigned long lastAccelTime = 0;
};

extern DualMotorController dualMotor;

#endif // DUAL_MOTOR_H
