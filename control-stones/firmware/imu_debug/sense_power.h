#pragma once
#include <LSM6DS3.h>
#include <FreeRTOS.h>
#include <task.h>

// Register owner for the internal Sense IMU; motion_idle.h decides when the
// whole assembly rests. The Puck and other sensor drivers are unaffected.
namespace SensePower {
static TaskHandle_t readerTask = nullptr;
static bool enabled = false;
static bool idle = false;
static uint8_t activeAccel = 0, activeControl4 = 0, activeControl6 = 0;

static void onMotionInterrupt() {
  BaseType_t wake = pdFALSE;
  if (readerTask) vTaskNotifyGiveFromISR(readerTask, &wake);
  portYIELD_FROM_ISR(wake);
}

static bool begin(LSM6DS3 &imu) {
  readerTask = xTaskGetCurrentTaskHandle();
  // Keep the hardware wake interrupt, but disable autonomous inactivity:
  // finger motion must keep the internal gyro awake too. AN5130 §§3.4/3.5/5.2.
  const uint8_t registers[] = {0x5C, 0x5B, 0x58, 0x5E};
  const uint8_t values[] = {0x00, 0x01, 0x80, 0x20};
  enabled = imu.readRegister(&activeAccel, 0x10) == IMU_SUCCESS &&
    imu.readRegister(&activeControl4, 0x13) == IMU_SUCCESS &&
    imu.readRegister(&activeControl6, 0x15) == IMU_SUCCESS;
  for (unsigned i = 0; enabled && i < sizeof(registers); ++i) {
    uint8_t actual = 0;
    if (imu.writeRegister(registers[i], values[i]) != IMU_SUCCESS ||
        imu.readRegister(&actual, registers[i]) != IMU_SUCCESS || actual != values[i]) {
      enabled = false;
      break;
    }
  }
  if (!enabled) {
    imu.writeRegister(0x58, 0); // Fall back to continuous sensing.
    imu.writeRegister(0x5E, 0);
    return false;
  }
  pinMode(PIN_LSM6DS3TR_C_INT1, INPUT);
  attachInterrupt(digitalPinToInterrupt(PIN_LSM6DS3TR_C_INT1), onMotionInterrupt, RISING);
  return true;
}

static bool setIdle(LSM6DS3 &imu, bool sleeping) {
  if (!enabled || idle == sleeping) return enabled;
  const uint8_t registers[] = {0x13, 0x15, 0x10};
  const uint8_t values[] = {
    uint8_t(sleeping ? activeControl4 | 0x40 : activeControl4),
    uint8_t(sleeping ? activeControl6 | 0x10 : activeControl6),
    uint8_t(sleeping ? (activeAccel & 0x0F) | 0x10 : activeAccel)
  };
  for (uint8_t i = 0; i < 3; ++i) {
    uint8_t actual = 0;
    if (imu.writeRegister(registers[i], values[i]) != IMU_SUCCESS ||
        imu.readRegister(&actual, registers[i]) != IMU_SUCCESS || actual != values[i]) {
      // Restore the known active setup rather than calling a partial change sleep.
      imu.writeRegister(0x10, activeAccel);
      imu.writeRegister(0x15, activeControl6);
      imu.writeRegister(0x13, activeControl4);
      idle = false;
      enabled = false;
      return false;
    }
  }
  idle = sleeping;
  return true;
}
static bool waitAndUpdate(LSM6DS3 &imu, uint32_t waitMs) {
  ulTaskNotifyTake(pdTRUE, pdMS_TO_TICKS(waitMs));
  uint8_t source = 0;
  return enabled && imu.readRegister(&source, 0x1B) == IMU_SUCCESS && (source & 0x08);
}
}
