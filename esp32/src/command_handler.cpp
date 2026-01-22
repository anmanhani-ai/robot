/**
 * command_handler.cpp
 * จัดการคำสั่งจาก Raspberry Pi ผ่าน Serial
 * 
 * Protocol Format: ACT:<ACTION>:<TIME>
 * Example: ACT:Z_OUT:1.50
 */

#include "command_handler.h"

// Global instance
CommandHandler cmdHandler;

void CommandHandler::init() {
    Serial.begin(SERIAL_BAUD_RATE);
    Serial.println("ESP32 AgriBot Ready");
}

void CommandHandler::processCommand(String command) {
    command.trim();
    
    // ==================== MOVEMENT COMMANDS ====================
    if (command == "MOVE_FORWARD") {
        motorWheel.forward();
        sendDone();
    }
    else if (command == "MOVE_BACKWARD") {
        motorWheel.backward();
        sendDone();
    }
    else if (command == "MOVE_STOP") {
        motorWheel.stop();
        sendDone();
    }
    
    // ==================== ARM Z COMMANDS ====================
    else if (command.startsWith("ACT:Z_OUT:")) {
        float seconds = parseTime(command);
        motorZ.extend(seconds);
        sendDone();
    }
    else if (command.startsWith("ACT:Z_IN:")) {
        float seconds = parseTime(command);
        motorZ.retract(seconds);
        sendDone();
    }
    
    // ==================== SERVO Y COMMANDS ====================
    else if (command == "ACT:Y_DOWN") {
        servoY.down();
        sendDone();
    }
    else if (command == "ACT:Y_UP") {
        servoY.up();
        sendDone();
    }
    
    // ==================== PUMP COMMANDS ====================
    else if (command.startsWith("ACT:SPRAY:")) {
        float seconds = parseTime(command);
        pump.spray(seconds);
        sendDone();
    }
    else if (command == "PUMP_ON") {
        pump.on();
        sendDone();
    }
    else if (command == "PUMP_OFF") {
        pump.off();
        sendDone();
    }
    
    // ==================== SYSTEM COMMANDS ====================
    else if (command == "STOP_ALL") {
        stopAll();
        sendDone();
    }
    else if (command == "STATUS") {
        Serial.println("OK");
    }
    else if (command == "PING") {
        Serial.println("PONG");
    }
    else {
        sendError("Unknown command: " + command);
    }
}

void CommandHandler::stopAll() {
    motorZ.stop();
    motorWheel.stop();
    servoY.up();
    pump.off();
}

void CommandHandler::sendDone() {
    Serial.println("DONE");
}

void CommandHandler::sendError(String message) {
    Serial.print("ERROR:");
    Serial.println(message);
}

float CommandHandler::parseTime(String command) {
    // Format: ACT:ACTION:TIME
    int lastColon = command.lastIndexOf(':');
    if (lastColon == -1) return 0;
    
    String timeStr = command.substring(lastColon + 1);
    return timeStr.toFloat();
}
