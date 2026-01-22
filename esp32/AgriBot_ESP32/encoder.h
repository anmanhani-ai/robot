/**
 * encoder.h
 * Rotary Encoder สำหรับวัดตำแหน่ง Motor Z
 * 
 * รองรับ:
 * - Incremental Encoder (2 channel: A, B)
 * - ใช้ Interrupt สำหรับความแม่นยำสูง
 */

#ifndef ENCODER_H
#define ENCODER_H

#include <Arduino.h>

// ==================== PIN CONFIGURATION ====================
// Encoder สำหรับ Motor Z (แขนกล)
#define PIN_ENCODER_A     35    // Channel A (CLK) - เปลี่ยนจาก 34 (ใช้กับ Emergency Stop)
#define PIN_ENCODER_B     36    // Channel B (DT)

// ==================== CONSTANTS ====================
// Encoder specifications (ปรับตามรุ่นที่ใช้)
#define ENCODER_PPR       20    // Pulses Per Revolution (ของ encoder)
#define GEAR_RATIO        1.0   // อัตราทด (ถ้าไม่มีก็ใส่ 1.0)
#define WHEEL_DIAMETER_MM 30.0  // เส้นผ่านศูนย์กลางล้อ/เพลา (mm)

// คำนวณล่วงหน้า
#define MM_PER_PULSE      (PI * WHEEL_DIAMETER_MM / (ENCODER_PPR * GEAR_RATIO))

// ==================== CLASS ====================
class MotorEncoder {
public:
    void init();
    
    // Position
    long getPosition();           // ตำแหน่งเป็น pulse count
    float getPositionMM();        // ตำแหน่งเป็น mm
    float getPositionCM();        // ตำแหน่งเป็น cm
    
    // Reset
    void reset();                 // Reset ตำแหน่งเป็น 0
    void setPosition(long pos);   // ตั้งค่าตำแหน่ง
    
    // สำหรับ Interrupt
    static void IRAM_ATTR handleInterrupt();
    
    // ข้อมูล
    void printInfo();             // แสดงข้อมูล encoder
    
private:
    static volatile long pulseCount;
    static volatile int lastStateA;
};

extern MotorEncoder encoderZ;

#endif // ENCODER_H
