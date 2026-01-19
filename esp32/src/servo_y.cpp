/**
 * servo_y.cpp
 * ควบคุม Servo แกน Y (ยก/วาง หัวฉีด)
 */

#include "servo_y.h"

// Global instance
ServoY servoY;

void ServoY::init() {
    servo.attach(PIN_SERVO_Y);
    currentAngle = SERVO_Y_UP;
    servo.write(currentAngle);
    delay(SERVO_MOVE_DELAY);
}

void ServoY::down() {
    setAngle(SERVO_Y_DOWN);
}

void ServoY::up() {
    setAngle(SERVO_Y_UP);
}

void ServoY::setAngle(int angle) {
    servo.write(angle);
    currentAngle = angle;
    delay(SERVO_MOVE_DELAY);
}
