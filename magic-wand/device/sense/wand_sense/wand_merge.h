#pragma once
#include <stdint.h>
// Readings the radio could not take yet, merged into the next frame (wand_sense.ino).
// Pure arithmetic only, so a host test can check it; callers hold the lock.
struct WandMerged {
  uint32_t epoch; uint16_t count; int32_t gyro[3]; int16_t accel[3]; uint32_t first, last; bool hasAccel, hasGyro;
};
static const uint16_t WAND_MERGE_MAX = 255;

static inline void wandMergeAdd(WandMerged &m, uint32_t us, const int16_t *gyro, const int16_t *accel, bool hasGyro) {
  if (m.count == 0) { m.first = us; m.gyro[0] = m.gyro[1] = m.gyro[2] = 0; }
  if (m.count < WAND_MERGE_MAX) { ++m.count; for (int i = 0; i < 3; ++i) m.gyro[i] += hasGyro ? gyro[i] : 0; }
  for (int i = 0; i < 3; ++i) m.accel[i] = accel[i];
  m.last = us; m.hasAccel = true; m.hasGyro = hasGyro;
}

// An unsent run goes back in front of anything newer; its rate is kept.
static inline void wandMergeRestore(WandMerged &m, const WandMerged &old) {
  // A button, sensor or connection boundary invalidates an in-flight retry.
  if (!old.count || m.epoch != old.epoch) return;
  if (!m.count) { m = old; return; }
  m.first = old.first;
  const uint16_t room = uint16_t(WAND_MERGE_MAX - m.count), add = old.count < room ? old.count : room;
  if (!add) return;
  for (int i = 0; i < 3; ++i) m.gyro[i] += int32_t((int64_t)old.gyro[i] * add / old.count);
  m.count = uint16_t(m.count + add);
}

static inline int16_t wandMergeMean(const WandMerged &m, int axis) {
  if (!m.count || !m.hasGyro) return 0;
  const int32_t sum = m.gyro[axis], n = m.count;
  return int16_t(sum >= 0 ? (sum + n / 2) / n : -((-sum + n / 2) / n));
}
