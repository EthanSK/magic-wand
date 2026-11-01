// Pure rate-command parsing for the reversible Sense refresh-rate experiment.
// Firmware uses the register nibble without changing range or gain; inert tests
// exercise this same table. These are configured sensor rates, not BLE rates.
#pragma once
#include <stdint.h>
#include <stddef.h>

struct WandSampleRate {
  uint16_t hz;
  uint8_t odrBits;
};

static bool wandSampleRate(uint32_t hz, WandSampleRate &rate) {
  switch (hz) {
    case 104: rate = {104, 0x40}; return true;
    case 208: rate = {208, 0x50}; return true;
    case 416: rate = {416, 0x60}; return true;
    case 833: rate = {833, 0x70}; return true;
    case 1660: rate = {1660, 0x80}; return true;
    case 3330: rate = {3330, 0x90}; return true;
    case 6660: rate = {6660, 0xa0}; return true;
    default: return false;
  }
}

static bool wandSampleRateCommand(const char *line, size_t length, WandSampleRate &rate) {
  if (!line || length < 4 || length > 5 || line[0] != 'R' || line[1] == '0') return false;
  uint32_t hz = 0;
  for (size_t i = 1; i < length; ++i) {
    if (line[i] < '0' || line[i] > '9') return false;
    hz = hz * 10 + uint32_t(line[i] - '0');
  }
  return wandSampleRate(hz, rate);
}
