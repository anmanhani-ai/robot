/**
 * buzzer.cpp
 * ควบคุม Buzzer สำหรับส่งสัญญาณเสียง
 */

#include "buzzer.h"

// Global instance
BuzzerController buzzer;

void BuzzerController::init() {
    pinMode(PIN_BUZZER, OUTPUT);
    digitalWrite(PIN_BUZZER, LOW);
    isOn = false;
    
    Serial.println("[Buzzer] Initialized on GPIO " + String(PIN_BUZZER));
}

void BuzzerController::on() {
    digitalWrite(PIN_BUZZER, HIGH);
    isOn = true;
}

void BuzzerController::off() {
    digitalWrite(PIN_BUZZER, LOW);
    noTone(PIN_BUZZER);
    isOn = false;
}

void BuzzerController::beep(int duration_ms) {
    on();
    delay(duration_ms);
    off();
}

void BuzzerController::beepTimes(int times, int duration_ms, int pause_ms) {
    for (int i = 0; i < times; i++) {
        beep(duration_ms);
        if (i < times - 1) {
            delay(pause_ms);
        }
    }
}

void BuzzerController::tone(int frequency, int duration_ms) {
    ::tone(PIN_BUZZER, frequency, duration_ms);
    delay(duration_ms);
}

void BuzzerController::playSuccess() {
    // เสียงสำเร็จ: 2 beep สูง
    tone(1000, 100);
    delay(50);
    tone(1500, 150);
}

void BuzzerController::playError() {
    // เสียง error: 3 beep ต่ำ
    for (int i = 0; i < 3; i++) {
        tone(400, 100);
        delay(100);
    }
}

void BuzzerController::playWarning() {
    // เสียงเตือน: beep ยาว
    tone(800, 500);
}

void BuzzerController::playStartup() {
    // เสียงเปิดเครื่อง: ไล่เสียงขึ้น
    tone(500, 100);
    tone(700, 100);
    tone(900, 100);
    tone(1100, 200);
}
