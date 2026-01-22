/**
 * motor_z.h
 * ควบคุม Motor DC แกน Z (ยืด/หด แขนกล)
 * รองรับทั้งโหมด Time-based และ Encoder-based
 */

#ifndef MOTOR_Z_H
#define MOTOR_Z_H

#include <Arduino.h>
#include "config.h"
#include "encoder.h"

// ==================== CONSTANTS ====================
#define MOTOR_Z_POSITION_TOLERANCE  2   // ยอมรับความคลาดเคลื่อน (mm)
#define MOTOR_Z_TIMEOUT_MS          10000 // Timeout สำหรับ moveToCM

class MotorZ {
public:
    void init();
    
    // Time-based control (แบบเดิม)
    void extend(float seconds);
    void retract(float seconds);
    
    // Encoder-based control (แม่นยำกว่า)
    bool extendToCM(float targetCM);    // ยืดไปที่ตำแหน่ง (cm)
    bool retractToCM(float targetCM);   // หดไปที่ตำแหน่ง (cm)
    bool moveToCM(float targetCM);      // เคลื่อนที่ไปตำแหน่งใดก็ได้
    
    // Position
    float getPositionCM();              // ตำแหน่งปัจจุบัน (cm)
    void resetPosition();               // Reset ตำแหน่งเป็น 0 (home)
    
    // Control
    void stop();
    void setSpeed(int speed);           // 0-255
    
    // Mode
    void enableEncoderMode();
    void disableEncoderMode();
    bool isEncoderEnabled();
    
private:
    void runForward();
    void runBackward();
    void run(bool forward, long duration_ms);
    
    int motorSpeed;
    bool encoderEnabled;
};

extern MotorZ motorZ;

#endif // MOTOR_Z_H
