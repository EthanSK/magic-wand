#pragma once
#include <stdint.h>
#include <math.h>

// Ethan's "put it down / pick it up": gravity is a resting reference, not
// movement. Keep that reference until a real change so slow tilts accumulate.
class MotionIdle {
  struct Reference { bool valid = false; float accel[3] = {}; } refs[6];
  uint32_t lastMotion = 0, lastReading = 0;
  bool seen = false;
public:
  static constexpr uint32_t STILL_MS = 5000;
  static constexpr uint32_t IDLE_POLL_MS = 80; // 12.5 Hz movement watch
  static constexpr float ACCEL_CHANGE_G = 0.0625f;
  static constexpr float GYRO_DPS = 3.0f;
  void restart(uint32_t now) { lastMotion = now; }
  bool observe(uint8_t sensor, const float *axes, bool gyroActive, uint32_t now) {
    if (sensor >= 6) return false;
    for (uint8_t n = 0; n < 6; ++n) if (!isfinite(axes[n])) return false;
    Reference &ref = refs[sensor];
    bool moved = !ref.valid;
    for (uint8_t n = 0; n < 3; ++n) {
      if (gyroActive && fabsf(axes[n]) >= GYRO_DPS) moved = true;
      if (ref.valid && fabsf(axes[n + 3] - ref.accel[n]) >= ACCEL_CHANGE_G) moved = true;
    }
    if (moved) {
      for (uint8_t n = 0; n < 3; ++n) ref.accel[n] = axes[n + 3];
      ref.valid = true;
      lastMotion = now;
    }
    seen = true;
    lastReading = now;
    return moved;
  }
  bool shouldSleep(uint32_t now) const {
    // Loss of all telemetry is a fault, never evidence of stillness.
    return seen && uint32_t(now - lastReading) < 250 && uint32_t(now - lastMotion) >= STILL_MS;
  }
};
