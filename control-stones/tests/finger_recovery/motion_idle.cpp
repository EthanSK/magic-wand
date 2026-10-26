#include <cassert>
#include "motion_idle.h"
int main() {
  MotionIdle state;
  float axes[6] = {0.7f, -1.0f, 0.3f, 0, 0, 1};
  assert(!state.shouldSleep(9000)); // Missing readings are not stillness.
  assert(state.observe(0, axes, true, 100));
  for (unsigned t = 120; t < 5100; t += 20) {
    assert(!state.observe(0, axes, true, t)); // Gravity and bias do not wake.
    assert(!state.shouldSleep(t));
  }
  state.observe(0, axes, true, 5100);
  assert(state.shouldSleep(5100));
  assert(!state.shouldSleep(6000)); // No stale sample can trigger sleep.
  // Finger-only motion wakes even if the hand sensor never changes.
  assert(state.observe(5, axes, false, 6000));
  axes[3] = 0.08f;
  assert(state.observe(5, axes, false, 6100));
  assert(!state.shouldSleep(6100));
  // Anchored comparison catches a slow tilt rather than chasing every sample.
  axes[3] = 0.10f;assert(!state.observe(5, axes, false, 6180));
  axes[3] = 0.12f;assert(!state.observe(5, axes, false, 6260));
  axes[3] = 0.15f;assert(state.observe(5, axes, false, 6340));
  axes[0] = 4;assert(state.observe(0, axes, true, 6500));
  // A fresh stationary sample still works over millis() wrap.
  MotionIdle wrapped;
  axes[0] = 0;
  wrapped.observe(0, axes, false, UINT32_MAX - 3000);
  wrapped.observe(0, axes, false, 1999);
  assert(wrapped.shouldSleep(1999));
}
