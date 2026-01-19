/**
 * lcd_display.h
 * แสดงสถานะบน LCD I2C 16x2
 */

#ifndef LCD_DISPLAY_H
#define LCD_DISPLAY_H

#include <Arduino.h>
#include <Wire.h>
#include <LiquidCrystal_I2C.h>

// LCD Configuration
#define LCD_ADDR    0x27  // ลอง 0x27 ถ้าไม่ขึ้น
#define LCD_COLS    16
#define LCD_ROWS    2

class LCDDisplay {
public:
    void init();
    void showReady();
    void showHoldProgress(int percent);
    void showCountdown(int seconds);
    void showRunning();
    void showStopped();
    void showStatus(const char* line1, const char* line2 = "");
    void clear();
    
private:
    LiquidCrystal_I2C* lcd = nullptr;
    bool initialized = false;
};

extern LCDDisplay lcdDisplay;

#endif // LCD_DISPLAY_H
