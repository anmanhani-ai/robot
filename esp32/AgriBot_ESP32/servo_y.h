/**
 * servo_y.h
 * ควบคุม Servo แกน Y (ยก/วาง หัวฉีด)
 */

#ifndef SERVO_Y_H
#define SERVO_Y_H

#include <Arduino.h>
#include <ESP32Servo.h>
#include "config.h"

class ServoY {
public:
    void init();
    void down();
    void up();
    void setAngle(int angle);
    
private:
    Servo servo;
    int currentAngle;
};

extern ServoY servoY;

#endif // SERVO_Y_H
