/**
 * motor_wheel.cpp
 * ควบคุม Motor ล้อ (เดินหน้า/ถอยหลัง)
 */

#include "motor_wheel.h"

// Global instance
MotorWheel motorWheel;

void MotorWheel::init() {
    pinMode(PIN_MOTOR_WHEEL_IN1, OUTPUT);
    pinMode(PIN_MOTOR_WHEEL_IN2, OUTPUT);
    pinMode(PIN_MOTOR_WHEEL_PWM, OUTPUT);
    isRunning = false;
    stop();
}

void MotorWheel::forward() {
    digitalWrite(PIN_MOTOR_WHEEL_IN1, HIGH);
    digitalWrite(PIN_MOTOR_WHEEL_IN2, LOW);
    analogWrite(PIN_MOTOR_WHEEL_PWM, MOTOR_WHEEL_SPEED);
    isRunning = true;
}

void MotorWheel::backward() {
    digitalWrite(PIN_MOTOR_WHEEL_IN1, LOW);
    digitalWrite(PIN_MOTOR_WHEEL_IN2, HIGH);
    analogWrite(PIN_MOTOR_WHEEL_PWM, MOTOR_WHEEL_SPEED);
    isRunning = true;
}

void MotorWheel::stop() {
    digitalWrite(PIN_MOTOR_WHEEL_IN1, LOW);
    digitalWrite(PIN_MOTOR_WHEEL_IN2, LOW);
    analogWrite(PIN_MOTOR_WHEEL_PWM, 0);
    isRunning = false;
}
