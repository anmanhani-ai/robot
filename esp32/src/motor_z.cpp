/**
 * motor_z.cpp
 * ควบคุม Motor DC แกน Z (ยืด/หด แขนกล)
 */

#include "motor_z.h"

// Global instance
MotorZ motorZ;

void MotorZ::init() {
    pinMode(PIN_MOTOR_Z_IN3, OUTPUT);
    pinMode(PIN_MOTOR_Z_IN4, OUTPUT);
    pinMode(PIN_MOTOR_Z_PWM, OUTPUT);
    stop();
}

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
        digitalWrite(PIN_MOTOR_Z_IN3, HIGH);
        digitalWrite(PIN_MOTOR_Z_IN4, LOW);
    } else {
        digitalWrite(PIN_MOTOR_Z_IN3, LOW);
        digitalWrite(PIN_MOTOR_Z_IN4, HIGH);
    }
    
    analogWrite(PIN_MOTOR_Z_PWM, MOTOR_Z_SPEED);
    delay(duration_ms);
    stop();
}

void MotorZ::stop() {
    digitalWrite(PIN_MOTOR_Z_IN3, LOW);
    digitalWrite(PIN_MOTOR_Z_IN4, LOW);
    analogWrite(PIN_MOTOR_Z_PWM, 0);
}
