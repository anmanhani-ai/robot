/**
 * config.h
 * ค่า Configuration และ Pin definitions
 */

#ifndef CONFIG_H
#define CONFIG_H

// ==================== PIN CONFIGURATION ====================

// Motor DC สำหรับแกน Z (ยืด/หด แขนกล)
// Driver แบบ 4 ขา - ใช้ PWM ผ่าน IN3/IN4
#define PIN_MOTOR_Z_IN3   26    // PWM Forward
#define PIN_MOTOR_Z_IN4   27    // PWM Backward

// Motor DC สำหรับแกน Y (ขึ้น/ลง หัวฉีด)
// ใช้แทน Servo
#define PIN_MOTOR_Y_IN1   13    // PWM Up
#define PIN_MOTOR_Y_IN2   2     // PWM Down

// Relay สำหรับปั๊มพ่นยา
#define PIN_PUMP_RELAY    4     // Relay Control Pin

// Motor ล้อ - ดู dual_motor.h
// Motor Left:  GPIO 32, 33
// Motor Right: GPIO 17, 16

// ==================== CONSTANTS ====================

// Motor Speeds (0-255)
#define MOTOR_Z_SPEED     200   // ความเร็วแขน Z
#define MOTOR_Y_SPEED     200   // ความเร็วแขน Y
#define MOTOR_WHEEL_SPEED 180   // (deprecated - ใช้ dual_motor)

// Serial
#define SERIAL_BAUD_RATE  115200

#endif // CONFIG_H
