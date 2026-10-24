#pragma once
#include <LSM6DS3.h>
#include <FreeRTOS.h>
#include <task.h>

// Sense-only policy. Does not change the Puck or future external sensor drivers.
// ST AN5130 §5.6: accelerometer automatically drops to 12.5 Hz while idle.
namespace SensePower {
static TaskHandle_t readerTask = nullptr;
static bool enabled = false;
static bool idle = false;

static void onMotionInterrupt() {
  BaseType_t wake = pdFALSE;
  if (readerTask) vTaskNotifyGiveFromISR(readerTask, &wake);
  portYIELD_FROM_ISR(wake);
}

static bool begin(LSM6DS3 &imu) {
  readerTask = xTaskGetCurrentTaskHandle();
  // 4 * 512 / 416 Hz = 4.92 seconds still before sleep.
  // ±4 g range gives a 62.5 mg wake threshold with one threshold unit.
  const uint8_t registers[] = {0x5C, 0x5B, 0x58, 0x5E};
  const uint8_t values[] = {0x04, 0x01, 0xC0, 0xA0};
  enabled = true;
  for (unsigned i = 0; i < sizeof(registers); ++i) {
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

static void waitAndUpdate(LSM6DS3 &imu) {
  // FreeRTOS may idle the CPU; BLE's own tasks remain running. Motion interrupts
  // wake this task without waiting for the one-second idle status transmission.
  ulTaskNotifyTake(pdTRUE, pdMS_TO_TICKS(idle ? 1000 : 20));
  if (enabled) {
    uint8_t source = 0;
    if (imu.readRegister(&source, 0x1B) == IMU_SUCCESS) idle = (source & 0x10) != 0;
  }
}
}
