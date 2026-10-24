#pragma once
#include <Wire.h>

// Ethan's adapter-board wiring starts at SD2/SC2, not channel zero.
// Wire is the external D4/D5 bus; the built-in Sense IMU uses Wire1.
namespace Fingers {
constexpr uint8_t CHANNELS[] = {2, 3, 4, 5, 6};
const char *const NAMES[] = {"thumb", "index", "middle", "ring", "little"};
static uint8_t addresses[5] = {};
static uint32_t lastScan = 0;
static uint8_t scanIndex = 0;

static bool select(uint8_t channel) {
  Wire.beginTransmission(0x70);
  Wire.write(uint8_t(1u << channel));
  return Wire.endTransmission() == 0;
}
static bool read(uint8_t address, uint8_t reg, uint8_t *data, uint8_t count) {
  Wire.beginTransmission(address);
  Wire.write(reg);
  if (Wire.endTransmission(false) != 0) return false;
  if (Wire.requestFrom(address, count) != count) return false;
  for (uint8_t i = 0; i < count; ++i) data[i] = Wire.read();
  return true;
}
static bool write(uint8_t address, uint8_t reg, uint8_t value) {
  Wire.beginTransmission(address);
  Wire.write(reg);
  Wire.write(value);
  return Wire.endTransmission() == 0;
}
static bool configure(uint8_t i) {
  addresses[i] = 0;
  if (!select(CHANNELS[i])) return false;
  uint8_t id = 0, found = 0;
  for (uint8_t address = 0x68; address <= 0x69; ++address) {
    if (read(address, 0x00, &id, 1) && id == 0xD1) {
      if (found) return false; // Do not guess between two sensors on one channel.
      found = address;
    }
  }
  if (!found) return false;
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
  return true;
}
static void begin() {
  Wire.begin();
  Wire.setClock(100000);
  for (uint8_t i = 0; i < 5; ++i) configure(i);
  lastScan = millis();
}
static bool sample(uint8_t i, float *axes) {
  if (!addresses[i]) return false;
  if (!select(CHANNELS[i])) { addresses[i] = 0; return false; }
  uint8_t status = 0, raw[12];
  if (!read(addresses[i], 0x1B, &status, 1)) { addresses[i] = 0; return false; }
  if ((status & 0xC0) != 0xC0) return false;
  if (!read(addresses[i], 0x0C, raw, 12)) { addresses[i] = 0; return false; }
  for (uint8_t n = 0; n < 6; ++n) {
    int16_t value = int16_t(uint16_t(raw[n * 2]) | (uint16_t(raw[n * 2 + 1]) << 8));
    axes[n] = value / (n < 3 ? 32.8f : 8192.0f); // gx,gy,gz,ax,ay,az
  }
  return true;
}
static void rescan() {
  if (millis() - lastScan < 2000) return;
  lastScan = millis();
  if (!addresses[scanIndex]) configure(scanIndex);
  scanIndex = (scanIndex + 1) % 5;
}
static bool any() {
  for (uint8_t address : addresses) if (address) return true;
  return false;
}
}
