#pragma once
#include <stdint.h>
#include <stddef.h>

// Bluefruit can report the requested length after silently clamping notify()
// to the characteristic maximum. Give it one negotiated ATT payload at a time.
// Only the existing sender task calls this; sensor sampling never waits here.
struct WandBleOutput {
  static const uint16_t maxMtu = 247;
  static const size_t maxMessage = 512;
  static const uint32_t budgetMs = 1000;
  template<class Link> static bool write(Link &link, const uint8_t *data, size_t length) {
    if (!data || !length || length > maxMessage) return false;
    const uint32_t started = link.now();
    size_t offset = 0;
    while (offset < length) {
      // A connection handle can be reused. The adapter checks its generation
      // before every packet, so a reconnect never receives an old line's tail.
      if (!link.valid() || uint32_t(link.now() - started) >= budgetMs) return false;
      const uint16_t mtu = link.mtu();
      if (mtu < 23) return false;
      const size_t payload = (mtu < maxMtu ? mtu : maxMtu) - 3;
      const size_t left = length - offset;
      const size_t count = left < payload ? left : payload;
      if (link.write(data + offset, count) != count) return false;
      offset += count;
      if (!link.valid() || uint32_t(link.now() - started) >= budgetMs) return false;
    }
    return true;
  }
};
