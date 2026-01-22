/**
 * gpio_config.cpp
 * Implementation ของ GPIO Configuration Manager
 */

#include "gpio_config.h"

// Global instance
GpioConfigManager gpioConfig;

// Preferences namespace
#define PREFS_NAMESPACE "gpio_config"
#define CONFIG_VERSION  1

void GpioConfigManager::init() {
    Serial.println("[GPIO Config] Initializing...");
    
    // โหลดจาก EEPROM
    if (!loadFromEEPROM()) {
        Serial.println("[GPIO Config] No saved config, using defaults");
        resetToDefault();
        saveToEEPROM();
    }
    
    initialized = true;
    Serial.println("[GPIO Config] Ready");
    Serial.println("[GPIO Config] Current config:");
    Serial.println(toJson());
}

void GpioConfigManager::setDefaultValues() {
    config.motorY_pin1 = DEFAULT_MOTOR_Y_PIN1;
    config.motorY_pin2 = DEFAULT_MOTOR_Y_PIN2;
    
    config.motorZ_pin1 = DEFAULT_MOTOR_Z_PIN1;
    config.motorZ_pin2 = DEFAULT_MOTOR_Z_PIN2;
    
    config.wheelL_pin1 = DEFAULT_WHEEL_L_PIN1;
    config.wheelL_pin2 = DEFAULT_WHEEL_L_PIN2;
    
    config.wheelR_pin1 = DEFAULT_WHEEL_R_PIN1;
    config.wheelR_pin2 = DEFAULT_WHEEL_R_PIN2;
    
    config.usFront_trig = DEFAULT_US_FRONT_TRIG;
    config.usFront_echo = DEFAULT_US_FRONT_ECHO;
    
    config.usY_trig = DEFAULT_US_Y_TRIG;
    config.usY_echo = DEFAULT_US_Y_ECHO;
    
    config.usRight_trig = DEFAULT_US_RIGHT_TRIG;
    config.usRight_echo = DEFAULT_US_RIGHT_ECHO;
    
    config.pumpRelay = DEFAULT_PUMP_RELAY;
    config.buzzer = DEFAULT_BUZZER;
    
    config.version = CONFIG_VERSION;
}

bool GpioConfigManager::loadFromEEPROM() {
    preferences.begin(PREFS_NAMESPACE, true); // read-only
    
    // Check if config exists
    if (!preferences.isKey("version")) {
        preferences.end();
        return false;
    }
    
    uint8_t savedVersion = preferences.getUChar("version", 0);
    if (savedVersion != CONFIG_VERSION) {
        Serial.println("[GPIO Config] Version mismatch, resetting");
        preferences.end();
        return false;
    }
    
    // Load all values
    config.motorY_pin1 = preferences.getUChar("my_p1", DEFAULT_MOTOR_Y_PIN1);
    config.motorY_pin2 = preferences.getUChar("my_p2", DEFAULT_MOTOR_Y_PIN2);
    
    config.motorZ_pin1 = preferences.getUChar("mz_p1", DEFAULT_MOTOR_Z_PIN1);
    config.motorZ_pin2 = preferences.getUChar("mz_p2", DEFAULT_MOTOR_Z_PIN2);
    
    config.wheelL_pin1 = preferences.getUChar("wl_p1", DEFAULT_WHEEL_L_PIN1);
    config.wheelL_pin2 = preferences.getUChar("wl_p2", DEFAULT_WHEEL_L_PIN2);
    
    config.wheelR_pin1 = preferences.getUChar("wr_p1", DEFAULT_WHEEL_R_PIN1);
    config.wheelR_pin2 = preferences.getUChar("wr_p2", DEFAULT_WHEEL_R_PIN2);
    
    config.usFront_trig = preferences.getUChar("usf_t", DEFAULT_US_FRONT_TRIG);
    config.usFront_echo = preferences.getUChar("usf_e", DEFAULT_US_FRONT_ECHO);
    
    config.usY_trig = preferences.getUChar("usy_t", DEFAULT_US_Y_TRIG);
    config.usY_echo = preferences.getUChar("usy_e", DEFAULT_US_Y_ECHO);
    
    config.usRight_trig = preferences.getUChar("usr_t", DEFAULT_US_RIGHT_TRIG);
    config.usRight_echo = preferences.getUChar("usr_e", DEFAULT_US_RIGHT_ECHO);
    
    config.pumpRelay = preferences.getUChar("pump", DEFAULT_PUMP_RELAY);
    config.buzzer = preferences.getUChar("buzz", DEFAULT_BUZZER);
    
    config.version = savedVersion;
    
    preferences.end();
    Serial.println("[GPIO Config] Loaded from EEPROM");
    return true;
}

bool GpioConfigManager::saveToEEPROM() {
    preferences.begin(PREFS_NAMESPACE, false); // read-write
    
    preferences.putUChar("version", CONFIG_VERSION);
    
    preferences.putUChar("my_p1", config.motorY_pin1);
    preferences.putUChar("my_p2", config.motorY_pin2);
    
    preferences.putUChar("mz_p1", config.motorZ_pin1);
    preferences.putUChar("mz_p2", config.motorZ_pin2);
    
    preferences.putUChar("wl_p1", config.wheelL_pin1);
    preferences.putUChar("wl_p2", config.wheelL_pin2);
    
    preferences.putUChar("wr_p1", config.wheelR_pin1);
    preferences.putUChar("wr_p2", config.wheelR_pin2);
    
    preferences.putUChar("usf_t", config.usFront_trig);
    preferences.putUChar("usf_e", config.usFront_echo);
    
    preferences.putUChar("usy_t", config.usY_trig);
    preferences.putUChar("usy_e", config.usY_echo);
    
    preferences.putUChar("usr_t", config.usRight_trig);
    preferences.putUChar("usr_e", config.usRight_echo);
    
    preferences.putUChar("pump", config.pumpRelay);
    preferences.putUChar("buzz", config.buzzer);
    
    preferences.end();
    Serial.println("[GPIO Config] Saved to EEPROM");
    return true;
}

void GpioConfigManager::resetToDefault() {
    setDefaultValues();
    Serial.println("[GPIO Config] Reset to defaults");
}

void GpioConfigManager::swapMotorY() {
    // สลับ Motor Y pins กับ Motor Z pins
    uint8_t tmp1 = config.motorY_pin1;
    uint8_t tmp2 = config.motorY_pin2;
    
    config.motorY_pin1 = config.motorZ_pin1;
    config.motorY_pin2 = config.motorZ_pin2;
    
    config.motorZ_pin1 = tmp1;
    config.motorZ_pin2 = tmp2;
    
    Serial.println("[GPIO Config] Swapped Motor Y <-> Motor Z");
}

void GpioConfigManager::swapMotorZ() {
    // Same as swapMotorY (just alias)
    swapMotorY();
}

void GpioConfigManager::swapWheels() {
    // สลับ Wheel Left กับ Wheel Right
    uint8_t tmp1 = config.wheelL_pin1;
    uint8_t tmp2 = config.wheelL_pin2;
    
    config.wheelL_pin1 = config.wheelR_pin1;
    config.wheelL_pin2 = config.wheelR_pin2;
    
    config.wheelR_pin1 = tmp1;
    config.wheelR_pin2 = tmp2;
    
    Serial.println("[GPIO Config] Swapped Wheel Left <-> Wheel Right");
}

String GpioConfigManager::toJson() {
    String json = "{";
    json += "\"motor_y\":{\"pin1\":" + String(config.motorY_pin1) + ",\"pin2\":" + String(config.motorY_pin2) + "},";
    json += "\"motor_z\":{\"pin1\":" + String(config.motorZ_pin1) + ",\"pin2\":" + String(config.motorZ_pin2) + "},";
    json += "\"wheel_l\":{\"pin1\":" + String(config.wheelL_pin1) + ",\"pin2\":" + String(config.wheelL_pin2) + "},";
    json += "\"wheel_r\":{\"pin1\":" + String(config.wheelR_pin1) + ",\"pin2\":" + String(config.wheelR_pin2) + "},";
    json += "\"us_front\":{\"trig\":" + String(config.usFront_trig) + ",\"echo\":" + String(config.usFront_echo) + "},";
    json += "\"us_y\":{\"trig\":" + String(config.usY_trig) + ",\"echo\":" + String(config.usY_echo) + "},";
    json += "\"us_right\":{\"trig\":" + String(config.usRight_trig) + ",\"echo\":" + String(config.usRight_echo) + "},";
    json += "\"pump\":" + String(config.pumpRelay) + ",";
    json += "\"buzzer\":" + String(config.buzzer);
    json += "}";
    return json;
}

void GpioConfigManager::applyConfig() {
    // Note: This requires restarting the motors/sensors with new pins
    // Call this after loading config and before initializing hardware
    Serial.println("[GPIO Config] Config applied (restart hardware modules to take effect)");
}
