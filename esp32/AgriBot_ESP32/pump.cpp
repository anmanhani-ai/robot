/**
 * pump.cpp
 * ควบคุม Relay ปั๊มพ่นยา
 */

#include "pump.h"

// Global instance
Pump pump;

void Pump::init() {
    pinMode(PIN_PUMP_RELAY, OUTPUT);
    isOn = false;
    off();
}

void Pump::spray(float seconds) {
    long duration_ms = (long)(seconds * 1000);
    on();
    delay(duration_ms);
    off();
}

void Pump::on() {
    digitalWrite(PIN_PUMP_RELAY, HIGH);
    isOn = true;
}

void Pump::off() {
    digitalWrite(PIN_PUMP_RELAY, LOW);
    isOn = false;
}
