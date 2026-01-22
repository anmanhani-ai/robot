/**
 * motor_wheel.h
 * ควบคุม Motor ล้อ (เดินหน้า/ถอยหลัง)
 */

#ifndef MOTOR_WHEEL_H
#define MOTOR_WHEEL_H

#include <Arduino.h>
#include "config.h"

class MotorWheel {
public:
    void init();
    void forward();
    void backward();
    void stop();
    
private:
    bool isRunning;
};

extern MotorWheel motorWheel;

#endif // MOTOR_WHEEL_H
