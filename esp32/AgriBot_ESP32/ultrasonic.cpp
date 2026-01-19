/**
 * ultrasonic.cpp
 * ควบคุม Ultrasonic Sensors
 * 
 * 3 Sensors: Front (หลบหลีก), Right (หลบหลีก), Y-axis (วัดความสูง)
 */

#include "ultrasonic.h"

// Global instance
UltrasonicSensors ultrasonics;

void UltrasonicSensors::init() {
    // Front sensor
    pinMode(PIN_US_FRONT_TRIG, OUTPUT);
    pinMode(PIN_US_FRONT_ECHO, INPUT);
    
    // Right sensor
    pinMode(PIN_US_RIGHT_TRIG, OUTPUT);
    pinMode(PIN_US_RIGHT_ECHO, INPUT);
    
    // Y-axis sensor (วัดความสูงหัวพ่น)
    pinMode(PIN_US_Y_TRIG, OUTPUT);
    pinMode(PIN_US_Y_ECHO, INPUT);
    
    // Initialize cache
    lastFront = 999;
    lastRight = 999;
    lastY = 999;
    lastMeasureTime = 0;
    
    Serial.println("[Ultrasonic] 3 sensors initialized (Front/Right/Y-axis)");
    Serial.println("   Front:  TRIG=" + String(PIN_US_FRONT_TRIG) + ", ECHO=" + String(PIN_US_FRONT_ECHO));
    Serial.println("   Right:  TRIG=" + String(PIN_US_RIGHT_TRIG) + ", ECHO=" + String(PIN_US_RIGHT_ECHO));
    Serial.println("   Y-axis: TRIG=" + String(PIN_US_Y_TRIG) + ", ECHO=" + String(PIN_US_Y_ECHO));
}

float UltrasonicSensors::measureDistance(int trigPin, int echoPin) {
    // Send trigger pulse
    digitalWrite(trigPin, LOW);
    delayMicroseconds(2);
    digitalWrite(trigPin, HIGH);
    delayMicroseconds(10);
    digitalWrite(trigPin, LOW);
    
    // Measure echo duration
    long duration = pulseIn(echoPin, HIGH, US_TIMEOUT_US);
    
    // Calculate distance
    if (duration == 0) {
        return 999; // No echo received (out of range)
    }
    
    float distance = (duration * SOUND_SPEED_CM_US) / 2;
    return distance;
}

float UltrasonicSensors::getDistance(SensorPosition sensor) {
    switch (sensor) {
        case SENSOR_FRONT:  return getFrontDistance();
        case SENSOR_RIGHT:  return getRightDistance();
        case SENSOR_Y_AXIS: return getYDistance();
        default: return 999;
    }
}

float UltrasonicSensors::getFrontDistance() {
    lastFront = measureDistance(PIN_US_FRONT_TRIG, PIN_US_FRONT_ECHO);
    return lastFront;
}

float UltrasonicSensors::getRightDistance() {
    lastRight = measureDistance(PIN_US_RIGHT_TRIG, PIN_US_RIGHT_ECHO);
    return lastRight;
}

float UltrasonicSensors::getYDistance() {
    lastY = measureDistance(PIN_US_Y_TRIG, PIN_US_Y_ECHO);
    return lastY;
}

bool UltrasonicSensors::hasObstacleFront() {
    return getFrontDistance() < OBSTACLE_THRESHOLD_CM;
}

bool UltrasonicSensors::hasObstacleRight() {
    return getRightDistance() < OBSTACLE_THRESHOLD_CM;
}

ObstacleDirection UltrasonicSensors::checkObstacles() {
    bool front = hasObstacleFront();
    bool right = hasObstacleRight();
    
    // 2-sensor logic
    if (front && right) return OBSTACLE_FRONT_RIGHT;
    if (front) return OBSTACLE_FRONT;
    if (right) return OBSTACLE_RIGHT;
    
    return NO_OBSTACLE;
}

// ==================== Y-AXIS HEIGHT FUNCTIONS ====================

bool UltrasonicSensors::isYTooClose() {
    return getYDistance() < Y_MIN_HEIGHT_CM;
}

bool UltrasonicSensors::isYTooFar() {
    return getYDistance() > Y_MAX_HEIGHT_CM;
}

bool UltrasonicSensors::isYAtTarget() {
    float dist = getYDistance();
    float tolerance = 3.0;  // +/- 3cm
    return (dist >= Y_TARGET_HEIGHT_CM - tolerance) && 
           (dist <= Y_TARGET_HEIGHT_CM + tolerance);
}

void UltrasonicSensors::sendDistancesToSerial() {
    // Format: DIST:front,right,y
    Serial.print("DIST:");
    Serial.print(lastFront, 1);
    Serial.print(",");
    Serial.print(lastRight, 1);
    Serial.print(",");
    Serial.println(lastY, 1);
}
