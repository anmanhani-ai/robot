/**
 * buzzer.h
 * ควบคุม Buzzer สำหรับส่งสัญญาณเสียง
 */

#ifndef BUZZER_H
#define BUZZER_H

#include <Arduino.h>

// ==================== PIN CONFIGURATION ====================
#define PIN_BUZZER    14    // GPIO 14 (เดิมใช้กับ Motor Z PWM)

// ==================== CONSTANTS ====================
#define BUZZER_DEFAULT_FREQ   1000    // ความถี่ default (Hz)
#define BUZZER_DEFAULT_DUR    100     // ระยะเวลา default (ms)

class BuzzerController {
public:
    void init();
    
    // === Basic Control ===
    void on();
    void off();
    void beep(int duration_ms = BUZZER_DEFAULT_DUR);
    void beepTimes(int times, int duration_ms = 100, int pause_ms = 100);
    
    // === Tones ===
    void tone(int frequency, int duration_ms);
    void playSuccess();     // เสียงสำเร็จ
    void playError();       // เสียง error
    void playWarning();     // เสียงเตือน
    void playStartup();     // เสียงเปิดเครื่อง
    
private:
    bool isOn;
};

extern BuzzerController buzzer;

#endif // BUZZER_H
