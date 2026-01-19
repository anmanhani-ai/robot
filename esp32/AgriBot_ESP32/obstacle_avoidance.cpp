/**
 * obstacle_avoidance.cpp
 * ระบบหลบหลีกสิ่งกีดขวางอัตโนมัติ
 * 
 * Logic (2 sensors: Front + Right):
 * - ถ้าเจอสิ่งกีดขวางด้านหน้า → ถอยหลัง + เลี้ยวซ้าย
 * - ถ้าเจอด้านขวา → เลี้ยวซ้าย
 * - ถ้าเจอทั้งสอง → ถอยหลัง + เลี้ยวซ้าย
 */

#include "obstacle_avoidance.h"

// Global instance
ObstacleAvoidance obstacleAvoid;

void ObstacleAvoidance::init() {
    enabled = false;
    thresholdCm = OBSTACLE_THRESHOLD_CM;
    lastCheckTime = 0;
    Serial.println("[Obstacle Avoidance] Initialized (disabled by default)");
    Serial.println("   Sensors: Front + Right (2 sensors)");
}

void ObstacleAvoidance::enable() {
    enabled = true;
    Serial.println("[Obstacle Avoidance] ENABLED");
}

void ObstacleAvoidance::disable() {
    enabled = false;
    Serial.println("[Obstacle Avoidance] DISABLED");
}

bool ObstacleAvoidance::isEnabled() {
    return enabled;
}

void ObstacleAvoidance::setThreshold(int cm) {
    thresholdCm = cm;
    Serial.print("[Obstacle Avoidance] Threshold set to ");
    Serial.print(cm);
    Serial.println(" cm");
}

bool ObstacleAvoidance::checkAndAvoid() {
    if (!enabled) return false;
    
    // Rate limiting
    unsigned long now = millis();
    if (now - lastCheckTime < AVOID_CHECK_INTERVAL_MS) {
        return false;
    }
    lastCheckTime = now;
    
    // Check for obstacles (Front + Right only)
    ObstacleDirection obstacle = ultrasonics.checkObstacles();
    
    if (obstacle == NO_OBSTACLE) {
        return false; // No obstacle, continue normal operation
    }
    
    // Log obstacle detection
    Serial.print("[Obstacle] Detected: ");
    
    switch (obstacle) {
        case OBSTACLE_FRONT:
            Serial.println("FRONT - Backing up and turning left");
            avoidFront();
            break;
            
        case OBSTACLE_RIGHT:
            Serial.println("RIGHT - Turning left");
            avoidRight();
            break;
            
        case OBSTACLE_FRONT_RIGHT:
            Serial.println("FRONT+RIGHT - Backing up, turning left");
            avoidFront();
            break;
            
        default:
            return false;
    }
    
    // Send distance info
    ultrasonics.sendDistancesToSerial();
    
    return true; // Avoided something
}

void ObstacleAvoidance::avoidFront() {
    // หยุด
    dualMotor.stop();
    delay(100);
    
    // ถอยหลัง
    dualMotor.backward();
    delay(AVOID_BACKUP_DURATION_MS);
    dualMotor.stop();
    delay(100);
    
    // เลี้ยวซ้าย (เพราะไม่มี sensor ซ้าย จะถือว่าซ้ายว่างกว่า)
    Serial.println("[Avoid] Turning LEFT");
    dualMotor.turnLeft();
    
    delay(AVOID_TURN_DURATION_MS);
    dualMotor.stop();
}

void ObstacleAvoidance::avoidRight() {
    // เลี้ยวซ้ายเล็กน้อย
    dualMotor.stop();
    delay(100);
    Serial.println("[Avoid] Slight left turn");
    dualMotor.curveLeft();
    delay(AVOID_TURN_DURATION_MS / 2);
    dualMotor.forward();
}

void ObstacleAvoidance::emergencyStop() {
    dualMotor.emergencyStop();
    Serial.println("[Avoid] EMERGENCY STOP - Obstacles detected!");
    // ส่งสัญญาณไปยัง Pi
    Serial.println("BLOCKED");
}
