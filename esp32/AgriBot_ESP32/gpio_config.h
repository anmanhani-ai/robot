/**
 * gpio_config.h
 * ระบบจัดการ GPIO Configuration แบบ Dynamic
 * 
 * บันทึกค่าลง Preferences (EEPROM) และโหลดใช้งานเมื่อ boot
 * สามารถสลับ pin ผ่าน Serial command หรือ Web API
 */

#ifndef GPIO_CONFIG_H
#define GPIO_CONFIG_H

#include <Arduino.h>
#include <Preferences.h>

// ==================== DEFAULT PIN VALUES ====================
// ค่าเริ่มต้น (ใช้เมื่อ EEPROM ว่าง)

// Motor Y (แกน Y - ขึ้น/ลง)
#define DEFAULT_MOTOR_Y_PIN1   13
#define DEFAULT_MOTOR_Y_PIN2   2

// Motor Z (แกน Z - ยืด/หด)
#define DEFAULT_MOTOR_Z_PIN1   26
#define DEFAULT_MOTOR_Z_PIN2   27

// Wheel Left (ล้อซ้าย)
#define DEFAULT_WHEEL_L_PIN1   32
#define DEFAULT_WHEEL_L_PIN2   33

// Wheel Right (ล้อขวา)
#define DEFAULT_WHEEL_R_PIN1   17
#define DEFAULT_WHEEL_R_PIN2   16

// Ultrasonic Front
#define DEFAULT_US_FRONT_TRIG  12
#define DEFAULT_US_FRONT_ECHO  5

// Ultrasonic Y-axis
#define DEFAULT_US_Y_TRIG      25
#define DEFAULT_US_Y_ECHO      23

// Ultrasonic Right
#define DEFAULT_US_RIGHT_TRIG  18
#define DEFAULT_US_RIGHT_ECHO  19

// Pump Relay
#define DEFAULT_PUMP_RELAY     4

// Buzzer
#define DEFAULT_BUZZER         14

// ==================== CONFIG STRUCTURE ====================

struct GpioPinConfig {
    // Motor Y
    uint8_t motorY_pin1;
    uint8_t motorY_pin2;
    
    // Motor Z
    uint8_t motorZ_pin1;
    uint8_t motorZ_pin2;
    
    // Wheel Left
    uint8_t wheelL_pin1;
    uint8_t wheelL_pin2;
    
    // Wheel Right
    uint8_t wheelR_pin1;
    uint8_t wheelR_pin2;
    
    // Ultrasonic Front
    uint8_t usFront_trig;
    uint8_t usFront_echo;
    
    // Ultrasonic Y-axis
    uint8_t usY_trig;
    uint8_t usY_echo;
    
    // Ultrasonic Right
    uint8_t usRight_trig;
    uint8_t usRight_echo;
    
    // Pump & Buzzer
    uint8_t pumpRelay;
    uint8_t buzzer;
    
    // Version marker
    uint8_t version;
};

// ==================== CONFIG MANAGER ====================

class GpioConfigManager {
public:
    void init();
    
    // Load/Save
    bool loadFromEEPROM();
    bool saveToEEPROM();
    void resetToDefault();
    
    // Get current config
    GpioPinConfig& getConfig() { return config; }
    
    // Swap functions (สลับ pin ภายในกลุ่ม)
    void swapMotorY();      // สลับ Motor Y กับ Motor Z
    void swapMotorZ();      // สลับ Motor Z กับ Motor Y
    void swapWheels();      // สลับ Wheel Left กับ Right
    
    // Get config as JSON string
    String toJson();
    
    // Apply config to hardware (ต้องเรียกหลัง load)
    void applyConfig();
    
private:
    GpioPinConfig config;
    Preferences preferences;
    bool initialized = false;
    
    void setDefaultValues();
};

// Global instance
extern GpioConfigManager gpioConfig;

#endif // GPIO_CONFIG_H
