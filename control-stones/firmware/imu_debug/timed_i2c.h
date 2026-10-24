#pragma once
#include <Wire.h>
#include <FreeRTOS.h>
#include <task.h>

// The Seeed 1.1.13 Wire driver polls TWIM events without a deadline. Use the
// same external TWIM0 peripheral with bounded waits; Wire1 still owns the IMU.
namespace ExternalBus {
constexpr uint32_t TIMEOUT_US = 20000;
static uint32_t timeouts = 0;

static bool wait(volatile uint32_t &event, bool breakOnError = true) {
  const uint32_t start = micros();
  while (!event) {
    if (breakOnError && NRF_TWIM0->EVENTS_ERROR) return false;
    if (uint32_t(micros() - start) >= TIMEOUT_US) {
      ++timeouts;
      return false;
    }
    taskYIELD();
  }
  return true;
}

static void begin() {
  Wire.begin();
  Wire.setClock(100000);
  NRF_TWIM0->SHORTS = 0;
  NRF_TWIM0->INTENCLR = 0xFFFFFFFF;
  NRF_TWIM0->EVENTS_ERROR = 0;
  NRF_TWIM0->EVENTS_STOPPED = 0;
  NRF_TWIM0->EVENTS_SUSPENDED = 0;
  NRF_TWIM0->ERRORSRC = NRF_TWIM0->ERRORSRC;
}

static void recover() {
  // Disable DMA before its stack-backed buffers leave scope. Release both
  // wires, then clock out a partial transaction without ever driving high.
  NRF_TWIM0->ENABLE = 0;
  pinMode(PIN_WIRE_SDA, INPUT_PULLUP);
  pinMode(PIN_WIRE_SCL, INPUT_PULLUP);
  for (uint8_t i = 0; i < 9 && !digitalRead(PIN_WIRE_SDA); ++i) {
    digitalWrite(PIN_WIRE_SCL, LOW);
    pinMode(PIN_WIRE_SCL, OUTPUT);
    delayMicroseconds(5);
    pinMode(PIN_WIRE_SCL, INPUT_PULLUP);
    const uint32_t start = micros();
    while (!digitalRead(PIN_WIRE_SCL) && uint32_t(micros() - start) < 1000) taskYIELD();
    if (!digitalRead(PIN_WIRE_SCL)) break;
    delayMicroseconds(5);
  }
  // Only generate STOP when SCL can actually rise.
  if (digitalRead(PIN_WIRE_SCL)) {
    digitalWrite(PIN_WIRE_SDA, LOW);
    pinMode(PIN_WIRE_SDA, OUTPUT);
    delayMicroseconds(5);
    pinMode(PIN_WIRE_SDA, INPUT_PULLUP);
    delayMicroseconds(5);
  }
  begin();
}

static bool finish(bool stop) {
  const bool failed = NRF_TWIM0->EVENTS_ERROR != 0;
  bool completed;
  if (stop || failed) {
    NRF_TWIM0->TASKS_STOP = 1;
    completed = wait(NRF_TWIM0->EVENTS_STOPPED, false);
  } else {
    NRF_TWIM0->TASKS_SUSPEND = 1;
    completed = wait(NRF_TWIM0->EVENTS_SUSPENDED, false);
  }
  NRF_TWIM0->EVENTS_ERROR = 0;
  NRF_TWIM0->ERRORSRC = NRF_TWIM0->ERRORSRC;
  if (!completed) recover();
  return completed && !failed;
}

static bool write(uint8_t address, const uint8_t *data, uint8_t count, bool stop = true) {
  if (!data || !count || count > 2) return false;
  // EasyDMA requires RAM, including for a constant mux-selection byte.
  static uint8_t tx[2];
  for (uint8_t i = 0; i < count; ++i) tx[i] = data[i];
  NRF_TWIM0->EVENTS_ERROR = 0;
  NRF_TWIM0->EVENTS_LASTTX = 0;
  NRF_TWIM0->EVENTS_TXSTARTED = 0;
  NRF_TWIM0->EVENTS_STOPPED = 0;
  NRF_TWIM0->EVENTS_SUSPENDED = 0;
  NRF_TWIM0->ADDRESS = address;
  NRF_TWIM0->TXD.PTR = (uint32_t)(uintptr_t)tx;
  NRF_TWIM0->TXD.MAXCNT = count;
  __DMB();
  NRF_TWIM0->TASKS_RESUME = 1;
  NRF_TWIM0->TASKS_STARTTX = 1;
  if (!wait(NRF_TWIM0->EVENTS_LASTTX)) {
    if (NRF_TWIM0->EVENTS_ERROR) finish(true); else recover();
    return false;
  }
  return finish(stop) && NRF_TWIM0->TXD.AMOUNT == count;
}

static bool read(uint8_t address, uint8_t reg, uint8_t *data, uint8_t count) {
  if (!write(address, &reg, 1, false)) return false;
  NRF_TWIM0->EVENTS_ERROR = 0;
  NRF_TWIM0->EVENTS_LASTRX = 0;
  NRF_TWIM0->EVENTS_RXSTARTED = 0;
  NRF_TWIM0->EVENTS_STOPPED = 0;
  NRF_TWIM0->EVENTS_SUSPENDED = 0;
  NRF_TWIM0->ADDRESS = address;
  NRF_TWIM0->RXD.PTR = (uint32_t)(uintptr_t)data;
  NRF_TWIM0->RXD.MAXCNT = count;
  __DMB();
  NRF_TWIM0->TASKS_RESUME = 1;
  NRF_TWIM0->TASKS_STARTRX = 1;
  if (!wait(NRF_TWIM0->EVENTS_LASTRX)) {
    if (NRF_TWIM0->EVENTS_ERROR) finish(true); else recover();
    return false;
  }
  const bool ok = finish(true) && NRF_TWIM0->RXD.AMOUNT == count;
  __DMB();
  return ok;
}
}
