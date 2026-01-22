/**
 * command_handler.h
 * จัดการคำสั่งจาก Raspberry Pi ผ่าน Serial
 */

#ifndef COMMAND_HANDLER_H
#define COMMAND_HANDLER_H

#include <Arduino.h>
#include "config.h"
#include "motor_z.h"
#include "motor_wheel.h"
#include "servo_y.h"
#include "pump.h"

class CommandHandler {
public:
    void init();
    void processCommand(String command);
    void stopAll();
    
private:
    void sendDone();
    void sendError(String message);
    float parseTime(String command);
};

extern CommandHandler cmdHandler;

#endif // COMMAND_HANDLER_H
