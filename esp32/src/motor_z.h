/**
 * motor_z.h
 * ควบคุม Motor DC แกน Z (ยืด/หด แขนกล)
 */

#ifndef MOTOR_Z_H
#define MOTOR_Z_H

#include <Arduino.h>
#include "config.h"

class MotorZ {
public:
    void init();
    void extend(float seconds);
    void retract(float seconds);
    void stop();
    
private:
    void run(bool forward, long duration_ms);
};

extern MotorZ motorZ;

#endif // MOTOR_Z_H
