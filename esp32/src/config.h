/**
 * config.h
 * ค่า Configuration และ Pin definitions
 */

#ifndef CONFIG_H
#define CONFIG_H

// ==================== PIN CONFIGURATION ====================

// Motor DC สำหรับแกน Z (ยืด/หด แขนกล)
#define PIN_MOTOR_Z_IN3   26    // Motor Driver IN3
#define PIN_MOTOR_Z_IN4   27    // Motor Driver IN4
#define PIN_MOTOR_Z_PWM   14    // PWM Speed Control (0-255)

// Servo สำหรับแกน Y (ยก/วาง หัวฉีด)
#define PIN_SERVO_Y       13    // Servo Signal Pin

// Relay สำหรับปั๊มพ่นยา
#define PIN_PUMP_RELAY    4     // Relay Control Pin

// Motor ล้อ (เดินหน้า/ถอยหลัง)
#define PIN_MOTOR_WHEEL_IN1  32
#define PIN_MOTOR_WHEEL_IN2  33
#define PIN_MOTOR_WHEEL_PWM  25

// ==================== CONSTANTS ====================

// Motor Speeds (0-255)
#define MOTOR_Z_SPEED     200   // ความเร็วแขน Z (ห้ามเปลี่ยน - ส่งผลต่อสมการเวลา)
#define MOTOR_WHEEL_SPEED 180   // ความเร็วล้อ

// Servo Angles
#define SERVO_Y_DOWN      90    // องศาหัวฉีดลง
#define SERVO_Y_UP        0     // องศาหัวฉีดขึ้น
#define SERVO_MOVE_DELAY  500   // เวลารอ Servo หมุน (ms)

// Serial
#define SERIAL_BAUD_RATE  115200

#endif // CONFIG_H
