/**
 * button.cpp
 * ควบคุมปุ่ม Start และ Emergency Stop
 */

#include "button.h"

ButtonController buttons;

void ButtonController::init() {
    pinMode(PIN_BTN_START, INPUT_PULLUP);
    pinMode(PIN_BTN_EMERGENCY, INPUT_PULLUP);
    
    startTriggered = false;
    emergencyTriggered = false;
    startPressedTime = 0;
    
    Serial.println("✅ Buttons initialized");
    Serial.println("   Start: GPIO " + String(PIN_BTN_START) + " (hold 3s)");
    Serial.println("   Emergency: GPIO " + String(PIN_BTN_EMERGENCY));
}

void ButtonController::check() {
    unsigned long now = millis();
    
    // === Emergency Stop (กดทันที) ===
    // ⚠️ ปิดชั่วคราว - ถ้าไม่มี Pull-up Resistor จะ trigger เอง
    // ต้องต่อ Resistor 10kΩ จาก GPIO 34 ไป 3.3V ก่อนใช้งาน
    /*
    bool emergencyState = digitalRead(PIN_BTN_EMERGENCY);
    if (emergencyState == LOW && lastEmergencyState == HIGH) {
        // ปุ่มถูกกด
        emergencyTriggered = true;
        Serial.println("STOP_CMD");  // ส่งไป Pi
    }
    lastEmergencyState = emergencyState;
    */
    
    // === Start Button (กดค้าง 3 วินาที) ===
    bool startState = digitalRead(PIN_BTN_START);
    
    if (startState == LOW) {
        // กำลังกดอยู่
        if (lastStartState == HIGH) {
            // เริ่มกด
            startPressedTime = now;
        } else {
            // กดค้างอยู่ - ตรวจสอบเวลา
            if (startPressedTime > 0 && (now - startPressedTime >= BTN_START_HOLD_TIME)) {
                // กดครบ 3 วินาที!
                startTriggered = true;
                Serial.println("START_CMD");  // ส่งไป Pi
                startPressedTime = 0;  // Reset
            }
        }
    } else {
        // ปล่อยปุ่ม
        startPressedTime = 0;
    }
    
    lastStartState = startState;
}

bool ButtonController::isStartTriggered() {
    return startTriggered;
}

bool ButtonController::isEmergencyTriggered() {
    return emergencyTriggered;
}

int ButtonController::getHoldProgress() {
    if (startPressedTime == 0) return 0;
    
    unsigned long held = millis() - startPressedTime;
    int progress = (held * 100) / BTN_START_HOLD_TIME;
    return min(progress, 100);
}

void ButtonController::resetFlags() {
    startTriggered = false;
    emergencyTriggered = false;
}
