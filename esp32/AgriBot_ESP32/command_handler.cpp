/**
 * command_handler.cpp
 * จัดการคำสั่งจาก Raspberry Pi ผ่าน Serial
 * 
 * Protocol Format: ACT:<ACTION>:<VALUE>
 * Example: ACT:Z_OUT:1.50 (time-based)
 * Example: Z_MOVE:15.5 (encoder-based, cm)
 */

#include "command_handler.h"
#include "encoder.h"
#include "buzzer.h"

// Global instance
CommandHandler cmdHandler;

void CommandHandler::init() {
    Serial.begin(SERIAL_BAUD_RATE);
    Serial.println("ESP32 AgriBot Ready");
}

void CommandHandler::processCommand(String command) {
    command.trim();
    
    // ==================== MOVEMENT COMMANDS (use dualMotor) ====================
    if (command == "MOVE_FORWARD") {
        dualMotor.forward();
        sendDone();
    }
    else if (command == "MOVE_BACKWARD") {
        dualMotor.backward();
        sendDone();
    }
    else if (command == "MOVE_STOP") {
        dualMotor.stop();
        sendDone();
    }
    // Speed-controlled movement: MOVE_FW:<speed> (0-255)
    else if (command.startsWith("MOVE_FW:")) {
        int speed = parseInt(command);
        dualMotor.setSpeed(speed);
        dualMotor.forward();
        sendDone();
    }
    else if (command.startsWith("MOVE_BW:")) {
        int speed = parseInt(command);
        dualMotor.setSpeed(speed);
        dualMotor.backward();
        sendDone();
    }
    else if (command.startsWith("MOVE_SET_SPEED:")) {
        int speed = parseInt(command);
        dualMotor.setSpeed(speed);
        sendDone();
    }
    else if (command == "MOVE_GET_SPEED") {
        Serial.print("SPEED:");
        Serial.println(dualMotor.getSpeed());
    }
    // X-Axis alignment commands (ใช้สำหรับ align_to_target)
    else if (command == "MOVE_X:FW") {
        // เลื่อนไปทางขวา (forward ในแกน X ของกล้อง)
        dualMotor.curveRight();
        sendDone();
    }
    else if (command == "MOVE_X:BW") {
        // เลื่อนไปทางซ้าย (backward ในแกน X ของกล้อง)
        dualMotor.curveLeft();
        sendDone();
    }
    
    // ==================== ARM Z COMMANDS (Time-based) ====================
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
    
    // ==================== ARM Z COMMANDS (Encoder-based) ====================
    else if (command.startsWith("Z_MOVE:")) {
        // เคลื่อนที่ไปตำแหน่ง (cm) ตาม encoder
        float targetCM = parseTime(command);
        bool success = motorZ.moveToCM(targetCM);
        if (success) {
            Serial.print("POS:");
            Serial.println(motorZ.getPositionCM(), 2);
        } else {
            sendError("Move failed or timeout");
        }
        sendDone();
    }
    else if (command == "Z_HOME") {
        // หดกลับตำแหน่ง 0
        bool success = motorZ.moveToCM(0);
        if (success) {
            motorZ.resetPosition(); // Reset encoder เพื่อความแม่นยำ
        }
        sendDone();
    }
    else if (command == "Z_POS") {
        // อ่านตำแหน่งปัจจุบัน
        Serial.print("POS:");
        Serial.println(motorZ.getPositionCM(), 2);
    }
    else if (command == "Z_RESET") {
        // Reset encoder ให้ตำแหน่งปัจจุบันเป็น 0
        motorZ.resetPosition();
        sendDone();
    }
    else if (command == "Z_ENC_ON") {
        motorZ.enableEncoderMode();
        sendDone();
    }
    else if (command == "Z_ENC_OFF") {
        motorZ.disableEncoderMode();
        sendDone();
    }
    
    // ==================== MOTOR Y COMMANDS ====================
    else if (command == "ACT:Y_DOWN") {
        motorY.down();
        sendDone();
    }
    else if (command == "ACT:Y_UP") {
        motorY.up();
        sendDone();
    }
    else if (command.startsWith("Y_DOWN:")) {
        float seconds = parseTime(command);
        motorY.downFor(seconds);
        sendDone();
    }
    else if (command.startsWith("Y_UP:")) {
        float seconds = parseTime(command);
        motorY.upFor(seconds);
        sendDone();
    }
    else if (command == "Y_STOP") {
        motorY.stop();
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
    
    // ==================== ULTRASONIC COMMANDS ====================
    else if (command == "US_GET_DIST") {
        float front = ultrasonics.getFrontDistance();
        float yAxis = ultrasonics.getYDistance();
        float right = ultrasonics.getRightDistance();
        Serial.print("DIST:");
        Serial.print(front, 1);
        Serial.print(",");
        Serial.print(yAxis, 1);
        Serial.print(",");
        Serial.println(right, 1);
    }
    else if (command == "US_CHECK") {
        ObstacleDirection obstacle = ultrasonics.checkObstacles();
        Serial.print("OBSTACLE:");
        Serial.println((int)obstacle);
    }
    
    // ==================== OBSTACLE AVOIDANCE COMMANDS ====================
    else if (command == "AVOID_ON") {
        obstacleAvoid.enable();
        sendDone();
    }
    else if (command == "AVOID_OFF") {
        obstacleAvoid.disable();
        sendDone();
    }
    else if (command.startsWith("AVOID_SET:")) {
        int threshold = parseInt(command);
        obstacleAvoid.setThreshold(threshold);
        sendDone();
    }
    
    // ==================== DUAL MOTOR COMMANDS ====================
    else if (command == "DRIVE_FW") {
        dualMotor.forward();
        sendDone();
    }
    else if (command == "DRIVE_BW") {
        dualMotor.backward();
        sendDone();
    }
    else if (command == "DRIVE_STOP") {
        dualMotor.stop();
        sendDone();
    }
    else if (command == "DRIVE_ESTOP") {
        dualMotor.emergencyStop();
        sendDone();
    }
    else if (command == "TURN_LEFT") {
        dualMotor.turnLeft();
        sendDone();
    }
    else if (command == "TURN_RIGHT") {
        dualMotor.turnRight();
        sendDone();
    }
    else if (command == "CURVE_LEFT") {
        dualMotor.curveLeft();
        sendDone();
    }
    else if (command == "CURVE_RIGHT") {
        dualMotor.curveRight();
        sendDone();
    }
    else if (command.startsWith("DRIVE_SPEED:")) {
        int speed = parseInt(command);
        dualMotor.setSpeed(speed);
        sendDone();
    }
    else if (command.startsWith("TRIM_SET:")) {
        int offset = parseInt(command);
        dualMotor.setTrim(offset);
        sendDone();
    }
    else if (command == "TRIM_SAVE") {
        dualMotor.saveTrim();
        sendDone();
    }
    else if (command == "TRIM_GET") {
        Serial.print("TRIM:");
        Serial.println(dualMotor.getTrim());
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
    
    // ==================== BUZZER COMMANDS ====================
    else if (command == "BEEP") {
        buzzer.beep();
        sendDone();
    }
    else if (command.startsWith("BEEP:")) {
        int times = parseInt(command);
        buzzer.beepTimes(times);
        sendDone();
    }
    else if (command == "BUZZER_ON") {
        buzzer.on();
        sendDone();
    }
    else if (command == "BUZZER_OFF") {
        buzzer.off();
        sendDone();
    }
    else if (command == "BUZZER_SUCCESS") {
        buzzer.playSuccess();
        sendDone();
    }
    else if (command == "BUZZER_ERROR") {
        buzzer.playError();
        sendDone();
    }
    else if (command == "BUZZER_WARNING") {
        buzzer.playWarning();
        sendDone();
    }
    else {
        sendError("Unknown command: " + command);
    }
}

void CommandHandler::stopAll() {
    motorZ.stop();
    motorY.stop();
    dualMotor.emergencyStop();
    pump.off();
    obstacleAvoid.disable();
}

void CommandHandler::sendDone() {
    Serial.println("DONE");
}

void CommandHandler::sendError(String message) {
    Serial.print("ERROR:");
    Serial.println(message);
}

float CommandHandler::parseTime(String command) {
    int lastColon = command.lastIndexOf(':');
    if (lastColon == -1) return 0;
    String timeStr = command.substring(lastColon + 1);
    return timeStr.toFloat();
}

int CommandHandler::parseInt(String command) {
    int lastColon = command.lastIndexOf(':');
    if (lastColon == -1) return 0;
    String valStr = command.substring(lastColon + 1);
    return valStr.toInt();
}
