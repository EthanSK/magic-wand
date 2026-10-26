#pragma once
#ifndef CONTROL_STONES_FINGER_BUS
#include "timed_i2c.h"
#define CONTROL_STONES_FINGER_BUS ExternalBus
#endif

// Ethan's adapter-board wiring starts at SD2/SC2, not channel zero.
// Wire is the external D4/D5 bus; the built-in Sense IMU uses Wire1.
namespace Fingers {
namespace Bus = CONTROL_STONES_FINGER_BUS;
constexpr uint8_t CHANNELS[] = {2, 3, 4, 5, 6};
const char *const NAMES[] = {"thumb", "index", "middle", "ring", "little"};
static uint8_t addresses[5] = {};
static uint32_t lastScan = 0;
static uint8_t scanIndex = 0;
constexpr uint32_t STALE_MS = 1000;
enum Health : uint8_t { Missing, Live, NoData, BusError, ConfigurationError, Ambiguous, Starting };
static uint8_t health[5] = {};
static uint32_t lastGood[5] = {}, lastAttempt[5] = {}, restarts[5] = {};
static bool configuredBefore[5] = {};

// A selected downstream sensor must not remain on the shared bus while idle.
struct ChannelSession {
  ~ChannelSession() {
    const uint8_t mask = 0;
    Bus::write(0x70, &mask, 1);
  }
};

static bool select(uint8_t channel) {
  const uint8_t mask = uint8_t(1u << channel);
  return Bus::write(0x70, &mask, 1);
}
static bool read(uint8_t address, uint8_t reg, uint8_t *data, uint8_t count) {
  return Bus::read(address, reg, data, count);
}
static bool write(uint8_t address, uint8_t reg, uint8_t value) {
  const uint8_t data[] = {reg, value};
  return Bus::write(address, data, 2);
}
static bool configure(uint8_t i) {
  ChannelSession session;
  addresses[i] = 0;
  lastAttempt[i] = millis();
  health[i] = BusError;
  if (!select(CHANNELS[i])) return false;
  uint8_t id = 0, found = 0;
  for (uint8_t address = 0x68; address <= 0x69; ++address) {
    if (read(address, 0x00, &id, 1) && id == 0xD1) {
      if (found) { health[i] = Ambiguous; return false; }
      found = address;
    }
  }
  if (!found) { health[i] = Missing; return false; }
  health[i] = ConfigurationError;
  // Bosch BMI160 datasheet: normal bandwidth, 100 Hz, +/-4 g and +/-1000 dps.
  if (!write(found, 0x7E, 0xB6)) return false;
  delay(100);
  if (!write(found, 0x40, 0x28) || !write(found, 0x41, 0x05) ||
      !write(found, 0x42, 0x28) || !write(found, 0x43, 0x01) ||
      !write(found, 0x7E, 0x11)) return false;
  delay(5);
  if (!write(found, 0x7E, 0x15)) return false;
  delay(80);
  uint8_t pmu = 0;
  if (!read(found, 0x03, &pmu, 1) || (pmu & 0x3C) != 0x14) return false;
  const uint8_t values[] = {0x28, 0x05, 0x28, 0x01};
  for (uint8_t n = 0; n < 4; ++n) {
    uint8_t actual = 0;
    if (!read(found, 0x40 + n, &actual, 1) || actual != values[n]) return false;
  }
  addresses[i] = found;
  lastGood[i] = millis();
  health[i] = Starting;
  if (configuredBefore[i]) ++restarts[i];
  configuredBefore[i] = true;
  return true;
}
static void begin() {
  Bus::begin();
  const uint8_t off = 0;
  Bus::write(0x70, &off, 1);
  for (uint8_t i = 0; i < 5; ++i) configure(i);
  lastScan = millis();
}
static bool sample(uint8_t i, float *axes) {
  if (!addresses[i]) return false;
  ChannelSession session;
  if (!select(CHANNELS[i])) { addresses[i] = 0; health[i] = BusError; return false; }
  uint8_t status = 0, raw[12];
  if (!read(addresses[i], 0x1B, &status, 1)) { addresses[i] = 0; health[i] = BusError; return false; }
  if ((status & 0xC0) != 0xC0) {
    // A power glitch can leave CHIPID/I2C working while sampling stays off.
    // Do not keep a cached address forever without any actual measurements.
    if (uint32_t(millis() - lastGood[i]) >= STALE_MS) {
      addresses[i] = 0;
      health[i] = NoData;
    }
    return false;
  }
  if (!read(addresses[i], 0x0C, raw, 12)) { addresses[i] = 0; health[i] = BusError; return false; }
  for (uint8_t n = 0; n < 6; ++n) {
    int16_t value = int16_t(uint16_t(raw[n * 2]) | (uint16_t(raw[n * 2 + 1]) << 8));
    axes[n] = value / (n < 3 ? 32.8f : 8192.0f); // gx,gy,gz,ax,ay,az
  }
  lastGood[i] = millis();
  health[i] = Live;
  return true;
}
static void rescan() {
  if (uint32_t(millis() - lastScan) < 200) return;
  lastScan = millis();
  for (uint8_t n = 0; n < 5; ++n) {
    const uint8_t i = scanIndex;
    scanIndex = (scanIndex + 1) % 5;
    if (!addresses[i] && uint32_t(millis() - lastAttempt[i]) >= 1000) {
      configure(i);
      break; // At most one sensor reset per pass; healthy sensors keep reading.
    }
  }
}
static bool any() {
  for (uint8_t address : addresses) if (address) return true;
  return false;
}
}
