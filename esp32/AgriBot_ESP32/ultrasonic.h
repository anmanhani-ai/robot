/**
 * ultrasonic.h
 * ควบคุม Ultrasonic Sensors
 * 
 * Sensors:
 * - FRONT: ตรวจจับสิ่งกีดขวางด้านหน้า
 * - RIGHT: ตรวจจับสิ่งกีดขวางด้านขวา
 * - Y_AXIS: วัดความสูงหัวพ่นจากพื้น
 */

#ifndef ULTRASONIC_H
#define ULTRASONIC_H

#include <Arduino.h>

// ==================== PIN CONFIGURATION ====================
// Front Sensor (สิ่งกีดขวางด้านหน้า)
#define PIN_US_FRONT_TRIG   12
#define PIN_US_FRONT_ECHO   5

// Right Sensor (สิ่งกีดขวางด้านขวา)
#define PIN_US_RIGHT_TRIG   18
#define PIN_US_RIGHT_ECHO   19

// Y-Axis Sensor (วัดความสูงหัวพ่น - เดิมเป็น US Left)
#define PIN_US_Y_TRIG       25
#define PIN_US_Y_ECHO       23

// ==================== CONSTANTS ====================
#define OBSTACLE_THRESHOLD_CM   30    // ระยะที่ถือว่ามีสิ่งกีดขวาง (cm)
#define US_TIMEOUT_US           30000 // Timeout สำหรับ echo (microseconds)
#define SOUND_SPEED_CM_US       0.034 // ความเร็วเสียง (cm/microsecond)

// Y-axis height thresholds
#define Y_MIN_HEIGHT_CM         5     // ต่ำสุด - ใกล้พื้นเกินไป
#define Y_MAX_HEIGHT_CM         30    // สูงสุด - ไกลพื้นเกินไป
#define Y_TARGET_HEIGHT_CM      15    // ความสูงเป้าหมาย

// ==================== ENUMS ====================
enum SensorPosition {
    SENSOR_FRONT = 0,
    SENSOR_RIGHT = 1,
    SENSOR_Y_AXIS = 2
};

enum ObstacleDirection {
    NO_OBSTACLE     = 0,
    OBSTACLE_FRONT  = 1,
    OBSTACLE_RIGHT  = 2,
    OBSTACLE_FRONT_RIGHT = 3
};

// ==================== CLASS ====================
class UltrasonicSensors {
public:
    void init();
    
    // วัดระยะทาง
    float getDistance(SensorPosition sensor);
    float getFrontDistance();
    float getRightDistance();
    float getYDistance();
    
    // ตรวจสอบสิ่งกีดขวาง (Front + Right)
    bool hasObstacleFront();
    bool hasObstacleRight();
    ObstacleDirection checkObstacles();
    
    // ตรวจสอบความสูงแกน Y
    bool isYTooClose();   // ใกล้พื้นเกินไป
    bool isYTooFar();     // ไกลพื้นเกินไป
    bool isYAtTarget();   // อยู่ที่ความสูงเป้าหมาย
    
    // ส่งข้อมูลระยะทางทั้งหมด
    void sendDistancesToSerial();
    
private:
    float measureDistance(int trigPin, int echoPin);
    
    // Cache distances
    float lastFront;
    float lastRight;
    float lastY;
    unsigned long lastMeasureTime;
};

extern UltrasonicSensors ultrasonics;

#endif // ULTRASONIC_H
