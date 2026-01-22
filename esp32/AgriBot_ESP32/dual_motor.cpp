/**
 * dual_motor.cpp
 * ควบคุม 2 Motor แบบ Differential Drive
 * 
 * สำหรับ Motor Driver แบบ 4 ขา (IN1-IN4)
 * ใช้ PWM โดยตรงผ่าน IN1-IN4 (ไม่มี ENA/ENB)
 */

#include "dual_motor.h"
#include <EEPROM.h>

// Global instance
DualMotorController dualMotor;

// EEPROM address for trim
#define EEPROM_TRIM_ADDR 100

void DualMotorController::init() {
    // Setup pins - Motor Left (ใช้ PWM โดยตรง)
    pinMode(PIN_MOTOR_L_IN1, OUTPUT);
    pinMode(PIN_MOTOR_L_IN2, OUTPUT);
    
    // Setup pins - Motor Right (ใช้ PWM โดยตรง)
    pinMode(PIN_MOTOR_R_IN3, OUTPUT);
    pinMode(PIN_MOTOR_R_IN4, OUTPUT);
    
    // Stop motors
    stop();
    
    // Load trim from EEPROM
    loadTrim();
    
    Serial.println("✅ Dual Motor initialized (4-pin driver)");
    Serial.println("   Left:  IN1=GPIO" + String(PIN_MOTOR_L_IN1) + 
                   ", IN2=GPIO" + String(PIN_MOTOR_L_IN2));
    Serial.println("   Right: IN3=GPIO" + String(PIN_MOTOR_R_IN3) + 
                   ", IN4=GPIO" + String(PIN_MOTOR_R_IN4));
    Serial.println("   Trim:  " + String(trimOffset));
}

// ==================== MOVEMENT ====================

void DualMotorController::forward() {
    direction = 1;
    targetSpeed = MOTOR_DEFAULT_SPEED;
}

void DualMotorController::backward() {
    direction = -1;
    targetSpeed = MOTOR_DEFAULT_SPEED;
}

void DualMotorController::stop() {
    direction = 0;
    targetSpeed = 0;
    // Smooth stop จะทำใน update()
}

void DualMotorController::emergencyStop() {
    direction = 0;
    targetSpeed = 0;
    currentSpeedL = 0;
    currentSpeedR = 0;
    
    // หยุดทันที - ทุก pin เป็น LOW
    analogWrite(PIN_MOTOR_L_IN1, 0);
    analogWrite(PIN_MOTOR_L_IN2, 0);
    analogWrite(PIN_MOTOR_R_IN3, 0);
    analogWrite(PIN_MOTOR_R_IN4, 0);
    
    Serial.println("🛑 Emergency Stop!");
}

// ==================== TURNING ====================

void DualMotorController::turnLeft() {
    // หมุนในที่: ซ้ายถอย ขวาหน้า
    setMotorL(-MOTOR_DEFAULT_SPEED / 2);
    setMotorR(MOTOR_DEFAULT_SPEED / 2);
}

void DualMotorController::turnRight() {
    // หมุนในที่: ซ้ายหน้า ขวาถอย
    setMotorL(MOTOR_DEFAULT_SPEED / 2);
    setMotorR(-MOTOR_DEFAULT_SPEED / 2);
}

void DualMotorController::curveLeft() {
    // เลี้ยวโค้ง: ซ้ายช้า ขวาเร็ว
    setMotorL(MOTOR_DEFAULT_SPEED / 3);
    setMotorR(MOTOR_DEFAULT_SPEED);
}

void DualMotorController::curveRight() {
    // เลี้ยวโค้ง: ซ้ายเร็ว ขวาช้า
    setMotorL(MOTOR_DEFAULT_SPEED);
    setMotorR(MOTOR_DEFAULT_SPEED / 3);
}

// ==================== SPEED CONTROL ====================

void DualMotorController::setSpeed(int speed) {
    targetSpeed = constrain(speed, 0, 255);
    if (direction == 0 && speed > 0) {
        direction = 1;  // Default forward
    }
}

void DualMotorController::setSpeedSmooth(int speed) {
    targetSpeed = constrain(speed, 0, 255);
}

// ==================== TRIM ====================

void DualMotorController::setTrim(int offset) {
    trimOffset = constrain(offset, -50, 50);
    Serial.println("📐 Trim set to: " + String(trimOffset));
}

void DualMotorController::saveTrim() {
    EEPROM.begin(512);
    EEPROM.write(EEPROM_TRIM_ADDR, trimOffset + 50);  // offset 50 เพราะ signed
    EEPROM.commit();
    EEPROM.end();
    Serial.println("💾 Trim saved: " + String(trimOffset));
}

void DualMotorController::loadTrim() {
    EEPROM.begin(512);
    int stored = EEPROM.read(EEPROM_TRIM_ADDR);
    EEPROM.end();
    
    if (stored >= 0 && stored <= 100) {
        trimOffset = stored - 50;
    } else {
        trimOffset = 0;
    }
}

// ==================== MOTOR CONTROL (Internal) ====================
// สำหรับ 4-pin driver: ใช้ PWM โดยตรงผ่าน IN1/IN2
// IN1 = PWM สำหรับหน้า, IN2 = PWM สำหรับถอย

void DualMotorController::setMotorL(int speed) {
    int absSpeed = abs(speed);
    absSpeed = constrain(absSpeed, 0, 255);
    
    if (speed > 0) {
        // หน้า: IN1 = PWM, IN2 = 0
        analogWrite(PIN_MOTOR_L_IN1, absSpeed);
        analogWrite(PIN_MOTOR_L_IN2, 0);
    } else if (speed < 0) {
        // ถอย: IN1 = 0, IN2 = PWM
        analogWrite(PIN_MOTOR_L_IN1, 0);
        analogWrite(PIN_MOTOR_L_IN2, absSpeed);
    } else {
        // หยุด: ทั้งคู่ = 0
        analogWrite(PIN_MOTOR_L_IN1, 0);
        analogWrite(PIN_MOTOR_L_IN2, 0);
    }
}

void DualMotorController::setMotorR(int speed) {
    int absSpeed = abs(speed);
    absSpeed = constrain(absSpeed, 0, 255);
    
    if (speed > 0) {
        // หน้า: IN3 = PWM, IN4 = 0
        analogWrite(PIN_MOTOR_R_IN3, absSpeed);
        analogWrite(PIN_MOTOR_R_IN4, 0);
    } else if (speed < 0) {
        // ถอย: IN3 = 0, IN4 = PWM
        analogWrite(PIN_MOTOR_R_IN3, 0);
        analogWrite(PIN_MOTOR_R_IN4, absSpeed);
    } else {
        // หยุด: ทั้งคู่ = 0
        analogWrite(PIN_MOTOR_R_IN3, 0);
        analogWrite(PIN_MOTOR_R_IN4, 0);
    }
}

void DualMotorController::applySpeed() {
    // คำนวณความเร็วพร้อม trim
    int speedL = currentSpeedL;
    int speedR = currentSpeedR;
    
    // Apply trim
    if (trimOffset > 0) {
        // ขวาเร็วกว่า → ลดขวา
        speedR = speedR - trimOffset;
    } else if (trimOffset < 0) {
        // ซ้ายเร็วกว่า → ลดซ้าย
        speedL = speedL + trimOffset;  // trimOffset เป็นลบ
    }
    
    // Apply direction
    speedL *= direction;
    speedR *= direction;
    
    setMotorL(speedL);
    setMotorR(speedR);
}

// ==================== UPDATE (SMOOTH ACCELERATION) ====================

void DualMotorController::update() {
    unsigned long now = millis();
    
    // Rate limit acceleration
    if (now - lastAccelTime < MOTOR_ACCEL_DELAY) {
        return;
    }
    lastAccelTime = now;
    
    // Calculate target for each motor
    int targetL = targetSpeed;
    int targetR = targetSpeed;
    
    // Smoothly ramp left motor
    if (currentSpeedL < targetL) {
        currentSpeedL = min(currentSpeedL + MOTOR_ACCEL_STEP, targetL);
    } else if (currentSpeedL > targetL) {
        currentSpeedL = max(currentSpeedL - MOTOR_ACCEL_STEP, targetL);
    }
    
    // Smoothly ramp right motor
    if (currentSpeedR < targetR) {
        currentSpeedR = min(currentSpeedR + MOTOR_ACCEL_STEP, targetR);
    } else if (currentSpeedR > targetR) {
        currentSpeedR = max(currentSpeedR - MOTOR_ACCEL_STEP, targetR);
    }
    
    // Apply speeds
    applySpeed();
}
