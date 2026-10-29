#pragma once
#include <stdint.h>
// A timestamp refreshed during an iteration may be one tick newer than now.
// Treat that as no elapsed time, not ~49 days. Wrap remains valid for these
// short (<2^31 ms) heartbeat, debounce and five-minute sleep intervals.
static inline uint32_t wandElapsed(uint32_t now, uint32_t since) {
  const uint32_t delta = now - since;
  return delta <= 0x7fffffffUL ? delta : 0;
}
