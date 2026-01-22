/**
 * obstacle_avoidance.h
 * ระบบหลบหลีกสิ่งกีดขวางอัตโนมัติ
 */

#ifndef OBSTACLE_AVOIDANCE_H
#define OBSTACLE_AVOIDANCE_H

#include <Arduino.h>
#include "ultrasonic.h"
#include "dual_motor.h"

// ==================== CONSTANTS ====================
#define AVOID_TURN_DURATION_MS  500   // เวลาเลี้ยว (ms)
#define AVOID_BACKUP_DURATION_MS 300  // เวลาถอยหลัง (ms)
#define AVOID_CHECK_INTERVAL_MS  100  // ความถี่ตรวจสอบ (ms)

// ==================== CLASS ====================
class ObstacleAvoidance {
public:
    void init();
    void enable();
    void disable();
    bool isEnabled();
    
    // ตรวจสอบและหลบหลีก (เรียกใน loop)
    bool checkAndAvoid();
    
    // ตั้งค่า threshold
    void setThreshold(int cm);
    
private:
    bool enabled;
    int thresholdCm;
    unsigned long lastCheckTime;
    
    void avoidFront();
    void avoidRight();
    void emergencyStop();
};

extern ObstacleAvoidance obstacleAvoid;

#endif // OBSTACLE_AVOIDANCE_H
