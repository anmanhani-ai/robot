/**
 * encoder.cpp
 * Rotary Encoder สำหรับวัดตำแหน่ง Motor Z
 * 
 * ใช้ Hardware Interrupt เพื่อนับ pulse แม่นยำ
 * รองรับทั้งหมุนไปข้างหน้า (+) และถอยหลัง (-)
 */

#include "encoder.h"

// Global instance
MotorEncoder encoderZ;

// Static variables for interrupt
volatile long MotorEncoder::pulseCount = 0;
volatile int MotorEncoder::lastStateA = LOW;

void MotorEncoder::init() {
    // Setup pins
    pinMode(PIN_ENCODER_A, INPUT_PULLUP);
    pinMode(PIN_ENCODER_B, INPUT_PULLUP);
    
    // Read initial state
    lastStateA = digitalRead(PIN_ENCODER_A);
    
    // Attach interrupt (CHANGE = ทั้งขาขึ้นและขาลง)
    attachInterrupt(digitalPinToInterrupt(PIN_ENCODER_A), handleInterrupt, CHANGE);
    
    // Reset position
    pulseCount = 0;
    
    Serial.println("[Encoder] Initialized");
    Serial.print("  PPR: ");
    Serial.println(ENCODER_PPR);
    Serial.print("  mm/pulse: ");
    Serial.println(MM_PER_PULSE, 3);
}

void IRAM_ATTR MotorEncoder::handleInterrupt() {
    // อ่านสถานะปัจจุบัน
    int stateA = digitalRead(PIN_ENCODER_A);
    int stateB = digitalRead(PIN_ENCODER_B);
    
    // ตรวจสอบทิศทาง
    // ถ้า A เปลี่ยนและ B ต่างจาก A = หมุนไปข้างหน้า
    // ถ้า A เปลี่ยนและ B เหมือน A = หมุนถอยหลัง
    if (stateA != lastStateA) {
        if (stateB != stateA) {
            pulseCount++;  // หมุนข้างหน้า (ยืดออก)
        } else {
            pulseCount--;  // หมุนถอยหลัง (หดเข้า)
        }
    }
    
    lastStateA = stateA;
}

long MotorEncoder::getPosition() {
    // ต้อง disable interrupt ชั่วคราวเพื่ออ่านค่า
    noInterrupts();
    long pos = pulseCount;
    interrupts();
    return pos;
}

float MotorEncoder::getPositionMM() {
    return getPosition() * MM_PER_PULSE;
}

float MotorEncoder::getPositionCM() {
    return getPositionMM() / 10.0;
}

void MotorEncoder::reset() {
    noInterrupts();
    pulseCount = 0;
    interrupts();
    Serial.println("[Encoder] Position reset to 0");
}

void MotorEncoder::setPosition(long pos) {
    noInterrupts();
    pulseCount = pos;
    interrupts();
}

void MotorEncoder::printInfo() {
    Serial.print("[Encoder] Position: ");
    Serial.print(getPosition());
    Serial.print(" pulses = ");
    Serial.print(getPositionMM(), 1);
    Serial.print(" mm = ");
    Serial.print(getPositionCM(), 2);
    Serial.println(" cm");
}
