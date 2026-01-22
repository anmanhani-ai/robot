/**
 * AgriBot ESP32 Main
 * 
 * ระบบควบคุมหุ่นยนต์กำจัดวัชพืช
 * รับคำสั่งจาก Raspberry Pi ผ่าน Serial
 * 
 * Features:
 * - Motor Z: ยืด/หด แขนกล (รองรับ Encoder)
 * - Motor Y: ขึ้น/ลง หัวฉีด (DC Motor)
 * - Motor Wheel: เดินหน้า/ถอยหลัง
 * - Pump: พ่นยา
 * - Ultrasonic: ตรวจจับสิ่งกีดขวาง (หน้า/ซ้าย/ขวา)
 * - Obstacle Avoidance: หลบหลีกอัตโนมัติ
 * - Encoder: วัดตำแหน่งแขนกลแม่นยำ
 * - Button: Start (hold 3s) + Emergency Stop
 * - LCD: แสดงสถานะ
 * 
 * สำหรับ Arduino IDE:
 * 1. ติดตั้ง Board: ESP32 by Espressif
 * 2. ติดตั้ง Library: LiquidCrystal_I2C
 * 3. เลือก Board: ESP32 Dev Module
 * 4. Upload
 * 
 * @author AgriBot Team
 * @version 2.6.0 (Motor Y instead of Servo)
 */

#include "config.h"
#include "gpio_config.h"
#include "encoder.h"
#include "motor_z.h"
#include "motor_y.h"
#include "dual_motor.h"
#include "pump.h"
#include "ultrasonic.h"
#include "obstacle_avoidance.h"
#include "command_handler.h"
#include "button.h"
#include "lcd_display.h"
#include "buzzer.h"

// State tracking
bool isRunning = false;

// ==================== SETUP ====================
void setup() {
    // Initialize GPIO config first (loads from EEPROM)
    gpioConfig.init();
    
    // Initialize all modules
    cmdHandler.init();
    encoderZ.init();        // Encoder ก่อน Motor Z
    motorZ.init();
    dualMotor.init();       // Dual motor (2 wheels)
    motorY.init();          // Motor Y (ขึ้น/ลง)
    pump.init();
    ultrasonics.init();
    obstacleAvoid.init();
    buttons.init();
    buzzer.init();
    lcdDisplay.init();
    
    Serial.println("=============================");
    Serial.println("  AgriBot ESP32 v2.6.0");
    Serial.println("  Motor Y + Full Features");
    Serial.println("=============================");
    Serial.println("Features:");
    Serial.println("  - Dual Motor (L+R)");
    Serial.println("  - Motor Y (Up/Down)");
    Serial.println("  - 3x Ultrasonic (F/L/R)");
    Serial.println("Ready to receive commands...");
    
    // Play startup sound
    buzzer.playStartup();
}

// ==================== MAIN LOOP ====================
void loop() {
    // Check buttons
    buttons.check();
    
    // Handle button events
    if (buttons.isEmergencyTriggered()) {
        // Emergency Stop!
        cmdHandler.stopAll();
        isRunning = false;
        lcdDisplay.showStopped();
        buttons.resetFlags();
    }
    
    if (buttons.isStartTriggered() && !isRunning) {
        // Start triggered - show countdown
        for (int i = 3; i > 0; i--) {
            lcdDisplay.showCountdown(i);
            delay(1000);
        }
        isRunning = true;
        lcdDisplay.showRunning();
        buttons.resetFlags();
    }
    
    // Show hold progress on LCD
    int progress = buttons.getHoldProgress();
    if (progress > 0 && progress < 100) {
        lcdDisplay.showHoldProgress(progress);
    }
    
    // Check for incoming serial commands
    if (Serial.available() > 0) {
        String command = Serial.readStringUntil('\n');
        cmdHandler.processCommand(command);
    }
    
    // Update dual motor (smooth acceleration)
    dualMotor.update();
    
    // Check for obstacles (if enabled)
    obstacleAvoid.checkAndAvoid();
    
    // Small delay to prevent CPU overload
    delay(10);
}
