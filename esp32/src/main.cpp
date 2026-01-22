/**
 * AgriBot ESP32 Main
 * 
 * ระบบควบคุมหุ่นยนต์กำจัดวัชพืช
 * รับคำสั่งจาก Raspberry Pi ผ่าน Serial
 * 
 * File Structure:
 * - config.h         : Pin definitions & constants
 * - motor_z.h/cpp    : Z-axis arm motor control
 * - motor_wheel.h/cpp: Wheel motor control
 * - servo_y.h/cpp    : Y-axis spray head servo
 * - pump.h/cpp       : Pump relay control
 * - command_handler.h/cpp: Serial command processing
 * 
 * @author AgriBot Team
 * @version 2.0.0 (Modular)
 */

#include <Arduino.h>
#include "config.h"
#include "motor_z.h"
#include "motor_wheel.h"
#include "servo_y.h"
#include "pump.h"
#include "command_handler.h"

// ==================== SETUP ====================
void setup() {
    // Initialize all modules
    cmdHandler.init();
    motorZ.init();
    motorWheel.init();
    servoY.init();
    pump.init();
    
    Serial.println("=============================");
    Serial.println("  AgriBot ESP32 v2.0.0");
    Serial.println("  Modular Architecture");
    Serial.println("=============================");
    Serial.println("Ready to receive commands...");
}

// ==================== MAIN LOOP ====================
void loop() {
    // Check for incoming serial commands
    if (Serial.available() > 0) {
        String command = Serial.readStringUntil('\n');
        cmdHandler.processCommand(command);
    }
    
    // Small delay to prevent CPU overload
    delay(10);
}
