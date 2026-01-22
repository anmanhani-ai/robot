/**
 * motor_y.h
 * ควบคุม Motor DC แกน Y (ขึ้น/ลง หัวฉีด)
 * 
 * ใช้ Motor Driver แบบ 4 ขา (ไม่มี ENA)
 * PWM โดยตรงผ่าน IN1/IN2
 */

#ifndef MOTOR_Y_H
#define MOTOR_Y_H

#include <Arduino.h>

// ==================== PIN CONFIGURATION ====================
// Motor Y (แกน Y - ขึ้น/ลง)
#define PIN_MOTOR_Y_IN1   13    // PWM Up
#define PIN_MOTOR_Y_IN2   2     // PWM Down

// ==================== CONSTANTS ====================
#define MOTOR_Y_SPEED         200   // ความเร็ว (0-255)
#define MOTOR_Y_UP_TIMEOUT    3000  // Timeout ขึ้น (ms)
#define MOTOR_Y_DOWN_TIMEOUT  3000  // Timeout ลง (ms)

class MotorY {
public:
    void init();
    
    // === Movement ===
    void up();                      // ขึ้นจนสุด
    void down();                    // ลงจนสุด
    void upFor(float seconds);      // ขึ้นตามเวลา
    void downFor(float seconds);    // ลงตามเวลา
    void stop();
    
    // === Height Control (ใช้ US Y-axis) ===
    void moveToHeight(float targetCm);  // เลื่อนให้สูง targetCm จากพื้น
    
    // === Speed Control ===
    void setSpeed(int speed);       // 0-255
    int getSpeed() { return motorSpeed; }
    
    // === Status ===
    bool isMoving() { return moving; }
    
private:
    void runUp();
    void runDown();
    
    int motorSpeed;
    bool moving;
};

extern MotorY motorY;

#endif // MOTOR_Y_H
