/**
 * pump.h
 * ควบคุม Relay ปั๊มพ่นยา
 */

#ifndef PUMP_H
#define PUMP_H

#include <Arduino.h>
#include "config.h"

class Pump {
public:
    void init();
    void spray(float seconds);
    void on();
    void off();
    
private:
    bool isOn;
};

extern Pump pump;

#endif // PUMP_H
