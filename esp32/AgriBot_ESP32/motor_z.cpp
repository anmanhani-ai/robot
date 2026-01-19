/**
 * motor_z.cpp
 * ควบคุม Motor DC แกน Z (ยืด/หด แขนกล)
 * 
 * รองรับ 2 โหมด:
 * 1. Time-based: ควบคุมด้วยเวลา (ไม่ต้องใช้ encoder)
 * 2. Encoder-based: ควบคุมด้วยตำแหน่งจริง (แม่นยำกว่า)
 */

#include "motor_z.h"

// Global instance
MotorZ motorZ;

void MotorZ::init() {
    // 4-pin driver: ใช้ PWM ผ่าน IN1/IN2 โดยตรง
    pinMode(PIN_MOTOR_Z_IN1, OUTPUT);
    pinMode(PIN_MOTOR_Z_IN2, OUTPUT);
    // ไม่มี PWM pin แยก
    
    motorSpeed = MOTOR_Z_SPEED;
    encoderEnabled = true;  // เปิดใช้ encoder by default
    
    stop();
    
    Serial.println("[Motor Z] Initialized (4-pin driver)");
    Serial.println("  IN1: GPIO" + String(PIN_MOTOR_Z_IN1) + ", IN2: GPIO" + String(PIN_MOTOR_Z_IN2));
    Serial.print("  Encoder mode: ");
    Serial.println(encoderEnabled ? "ENABLED" : "DISABLED");
}

// ==================== TIME-BASED CONTROL ====================

void MotorZ::extend(float seconds) {
    long duration_ms = (long)(seconds * 1000);
    run(true, duration_ms);
}

void MotorZ::retract(float seconds) {
    long duration_ms = (long)(seconds * 1000);
    run(false, duration_ms);
}

void MotorZ::run(bool forward, long duration_ms) {
    if (forward) {
        runForward();
    } else {
        runBackward();
    }
    delay(duration_ms);
    stop();
}

// ==================== ENCODER-BASED CONTROL ====================

bool MotorZ::extendToCM(float targetCM) {
    if (!encoderEnabled) {
        Serial.println("[Motor Z] Encoder not enabled, using time-based");
        float currentCM = getPositionCM();
        float diffCM = targetCM - currentCM;
        if (diffCM > 0) {
            extend(diffCM / 10.0); // Rough estimate
        }
        return true;
    }
    
    return moveToCM(targetCM);
}

bool MotorZ::retractToCM(float targetCM) {
    if (!encoderEnabled) {
        Serial.println("[Motor Z] Encoder not enabled, using time-based");
        float currentCM = getPositionCM();
        float diffCM = currentCM - targetCM;
        if (diffCM > 0) {
            retract(diffCM / 10.0);
        }
        return true;
    }
    
    return moveToCM(targetCM);
}

bool MotorZ::moveToCM(float targetCM) {
    if (!encoderEnabled) {
        Serial.println("[Motor Z] ERROR: Encoder not enabled for moveToCM");
        return false;
    }
    
    float targetMM = targetCM * 10.0;
    unsigned long startTime = millis();
    
    Serial.print("[Motor Z] Moving to ");
    Serial.print(targetCM, 1);
    Serial.println(" cm");
    
    while (true) {
        float currentMM = encoderZ.getPositionMM();
        float errorMM = targetMM - currentMM;
        
        // Check if reached target
        if (abs(errorMM) <= MOTOR_Z_POSITION_TOLERANCE) {
            stop();
            Serial.print("[Motor Z] Reached target. Actual: ");
            Serial.print(currentMM / 10.0, 2);
            Serial.println(" cm");
            return true;
        }
        
        // Check timeout
        if (millis() - startTime > MOTOR_Z_TIMEOUT_MS) {
            stop();
            Serial.println("[Motor Z] TIMEOUT!");
            return false;
        }
        
        // Move towards target
        if (errorMM > 0) {
            runForward();   // ต้องยืดออก
        } else {
            runBackward();  // ต้องหดเข้า
        }
        
        delay(10);  // Small delay for encoder to update
    }
}

// ==================== POSITION ====================

float MotorZ::getPositionCM() {
    if (encoderEnabled) {
        return encoderZ.getPositionCM();
    }
    return 0;  // ไม่มี encoder ไม่รู้ตำแหน่ง
}

void MotorZ::resetPosition() {
    encoderZ.reset();
    Serial.println("[Motor Z] Position reset to 0 (HOME)");
}

// ==================== LOW-LEVEL CONTROL ====================
// 4-pin driver: ใช้ PWM โดยตรงผ่าน IN1/IN2

void MotorZ::runForward() {
    // ยืดออก: IN1 = PWM, IN2 = 0
    analogWrite(PIN_MOTOR_Z_IN1, motorSpeed);
    analogWrite(PIN_MOTOR_Z_IN2, 0);
}

void MotorZ::runBackward() {
    // หดเข้า: IN1 = 0, IN2 = PWM
    analogWrite(PIN_MOTOR_Z_IN1, 0);
    analogWrite(PIN_MOTOR_Z_IN2, motorSpeed);
}

void MotorZ::stop() {
    // หยุด: ทั้งคู่ = 0
    analogWrite(PIN_MOTOR_Z_IN1, 0);
    analogWrite(PIN_MOTOR_Z_IN2, 0);
}

void MotorZ::setSpeed(int speed) {
    motorSpeed = constrain(speed, 0, 255);
    Serial.print("[Motor Z] Speed set to ");
    Serial.println(motorSpeed);
}

// ==================== MODE ====================

void MotorZ::enableEncoderMode() {
    encoderEnabled = true;
    Serial.println("[Motor Z] Encoder mode ENABLED");
}

void MotorZ::disableEncoderMode() {
    encoderEnabled = false;
    Serial.println("[Motor Z] Encoder mode DISABLED (time-based)");
}

bool MotorZ::isEncoderEnabled() {
    return encoderEnabled;
}
