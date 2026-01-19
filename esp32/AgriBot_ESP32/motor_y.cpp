/**
 * motor_y.cpp
 * ควบคุม Motor DC แกน Y (ขึ้น/ลง หัวฉีด)
 * 
 * ใช้ Motor Driver แบบ 4 ขา (ไม่มี ENA)
 * PWM โดยตรงผ่าน IN1/IN2
 */

#include "motor_y.h"
#include "ultrasonic.h"

// Global instance
MotorY motorY;

void MotorY::init() {
    // 4-pin driver: ใช้ PWM ผ่าน IN1/IN2 โดยตรง
    pinMode(PIN_MOTOR_Y_IN1, OUTPUT);
    pinMode(PIN_MOTOR_Y_IN2, OUTPUT);
    
    motorSpeed = MOTOR_Y_SPEED;
    moving = false;
    
    stop();
    
    Serial.println("[Motor Y] Initialized (4-pin driver)");
    Serial.println("  IN1: GPIO" + String(PIN_MOTOR_Y_IN1) + ", IN2: GPIO" + String(PIN_MOTOR_Y_IN2));
}

// ==================== MOVEMENT ====================

void MotorY::up() {
    Serial.println("[Motor Y] Moving UP");
    runUp();
    delay(MOTOR_Y_UP_TIMEOUT);
    stop();
    Serial.println("[Motor Y] UP complete");
}

void MotorY::down() {
    Serial.println("[Motor Y] Moving DOWN");
    runDown();
    delay(MOTOR_Y_DOWN_TIMEOUT);
    stop();
    Serial.println("[Motor Y] DOWN complete");
}

void MotorY::upFor(float seconds) {
    long duration_ms = (long)(seconds * 1000);
    Serial.print("[Motor Y] Moving UP for ");
    Serial.print(seconds, 2);
    Serial.println(" sec");
    
    runUp();
    delay(duration_ms);
    stop();
}

void MotorY::downFor(float seconds) {
    long duration_ms = (long)(seconds * 1000);
    Serial.print("[Motor Y] Moving DOWN for ");
    Serial.print(seconds, 2);
    Serial.println(" sec");
    
    runDown();
    delay(duration_ms);
    stop();
}

void MotorY::stop() {
    // หยุด: ทั้งคู่ = 0
    analogWrite(PIN_MOTOR_Y_IN1, 0);
    analogWrite(PIN_MOTOR_Y_IN2, 0);
    moving = false;
}

// ==================== HEIGHT CONTROL (US Y-axis) ====================

void MotorY::moveToHeight(float targetCm) {
    Serial.print("[Motor Y] Moving to height: ");
    Serial.print(targetCm, 1);
    Serial.println(" cm");
    
    float tolerance = 2.0;  // +/- 2cm
    int maxAttempts = 50;   // Timeout protection
    int attempts = 0;
    
    while (attempts < maxAttempts) {
        float currentHeight = ultrasonics.getYDistance();
        float diff = currentHeight - targetCm;
        
        Serial.print("  Current: ");
        Serial.print(currentHeight, 1);
        Serial.print(" cm, Diff: ");
        Serial.println(diff, 1);
        
        // ถึงเป้าหมายแล้ว
        if (abs(diff) <= tolerance) {
            stop();
            Serial.println("[Motor Y] Target height reached!");
            return;
        }
        
        // ต่ำกว่าเป้าหมาย → ขึ้น
        if (diff < 0) {
            runUp();
        } else {
            // สูงกว่าเป้าหมาย → ลง
            runDown();
        }
        
        delay(100);  // ให้เวลา motor ทำงาน
        attempts++;
    }
    
    stop();
    Serial.println("[Motor Y] Timeout - target not reached");
}

// ==================== LOW-LEVEL CONTROL ====================

void MotorY::runUp() {
    // ขึ้น: IN1 = PWM, IN2 = 0
    analogWrite(PIN_MOTOR_Y_IN1, motorSpeed);
    analogWrite(PIN_MOTOR_Y_IN2, 0);
    moving = true;
}

void MotorY::runDown() {
    // ลง: IN1 = 0, IN2 = PWM
    analogWrite(PIN_MOTOR_Y_IN1, 0);
    analogWrite(PIN_MOTOR_Y_IN2, motorSpeed);
    moving = true;
}

// ==================== SPEED CONTROL ====================

void MotorY::setSpeed(int speed) {
    motorSpeed = constrain(speed, 0, 255);
    Serial.print("[Motor Y] Speed set to ");
    Serial.println(motorSpeed);
}

