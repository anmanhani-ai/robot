/**
 * lcd_display.cpp
 * แสดงสถานะบน LCD I2C
 */

#include "lcd_display.h"

LCDDisplay lcdDisplay;

void LCDDisplay::init() {
    // ปิดการใช้งาน LCD เพราะเอาออกแล้ว และต้องการใช้ GPIO 21/22 สำหรับ Motor
    // ถ้าต้องการใช้ LCD อีกครั้ง ให้ uncomment ด้านล่าง และเปลี่ยน Motor R pins
    
    /*
    lcd = new LiquidCrystal_I2C(LCD_ADDR, LCD_COLS, LCD_ROWS);
    lcd->init();
    lcd->backlight();
    
    initialized = true;
    showReady();
    
    Serial.println("✅ LCD initialized");
    Serial.println("   Address: 0x" + String(LCD_ADDR, HEX));
    */
    
    initialized = false;
    Serial.println("ℹ️ LCD disabled (GPIO 21/22 used for Motor R)");
}

void LCDDisplay::showReady() {
    if (!initialized) return;
    lcd->clear();
    lcd->setCursor(0, 0);
    lcd->print("   AgriBot v2   ");
    lcd->setCursor(0, 1);
    lcd->print("  Press START   ");
}

void LCDDisplay::showHoldProgress(int percent) {
    if (!initialized) return;
    lcd->setCursor(0, 0);
    lcd->print("  Hold 3 sec..  ");
    lcd->setCursor(0, 1);
    
    // แสดง progress bar
    int bars = (percent * 16) / 100;
    for (int i = 0; i < 16; i++) {
        if (i < bars) {
            lcd->print((char)255);  // Block character
        } else {
            lcd->print(" ");
        }
    }
}

void LCDDisplay::showCountdown(int seconds) {
    if (!initialized) return;
    lcd->clear();
    lcd->setCursor(0, 0);
    lcd->print("   Starting..   ");
    lcd->setCursor(7, 1);
    lcd->print(seconds);
}

void LCDDisplay::showRunning() {
    if (!initialized) return;
    lcd->clear();
    lcd->setCursor(0, 0);
    lcd->print("    RUNNING     ");
    lcd->setCursor(0, 1);
    lcd->print("   Auto Mode    ");
}

void LCDDisplay::showStopped() {
    if (!initialized) return;
    lcd->clear();
    lcd->setCursor(0, 0);
    lcd->print("    STOPPED!    ");
    lcd->setCursor(0, 1);
    lcd->print(" Emergency Stop ");
}

void LCDDisplay::showStatus(const char* line1, const char* line2) {
    if (!initialized) return;
    lcd->clear();
    lcd->setCursor(0, 0);
    lcd->print(line1);
    if (line2[0] != '\0') {
        lcd->setCursor(0, 1);
        lcd->print(line2);
    }
}

void LCDDisplay::clear() {
    if (!initialized) return;
    lcd->clear();
}
