/**
 * button.h
 * ปุ่ม Start และ Emergency Stop สำหรับ AgriBot
 */

#ifndef BUTTON_H
#define BUTTON_H

#include <Arduino.h>

// Pin Configuration
#define PIN_BTN_START       15    // ปุ่ม Start (กดค้าง 3 วินาที)
#define PIN_BTN_EMERGENCY   34    // ปุ่ม Emergency Stop

// Timing
#define BTN_START_HOLD_TIME 3000  // เวลากดค้าง (ms)
#define BTN_DEBOUNCE_TIME   50    // Debounce time (ms)

class ButtonController {
public:
    void init();
    void check();
    
    bool isStartTriggered();      // true เมื่อกด Start สำเร็จ
    bool isEmergencyTriggered();  // true เมื่อกด Emergency
    
    int getHoldProgress();        // 0-100% สำหรับแสดงบน LCD
    
    void resetFlags();
    
private:
    unsigned long startPressedTime = 0;
    bool startTriggered = false;
    bool emergencyTriggered = false;
    bool lastStartState = HIGH;
    bool lastEmergencyState = HIGH;
    unsigned long lastDebounceTime = 0;
};

extern ButtonController buttons;

#endif // BUTTON_H
