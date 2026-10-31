#pragma once
#include <stdint.h>
#include <stddef.h>
#include <string.h>

// The core's USB TX FIFO is 256 bytes; identity is longer. Continue only
// oversized control lines between loop iterations. Ordinary sensor frames
// keep their all-or-nothing write and existing merged-reading backpressure.
// This object has one owner (the main loop); the radio task never writes USB.
struct WandUsbOutput {
  static const size_t fifoSize = 256;
  char text[512]{};
  size_t length = 0, offset = 0;
  void reset() { length = offset = 0; }
  template<class SerialPort> void drain(SerialPort &port) {
    if (!port) { reset(); return; }
    if (offset == length) return;
    const int available = port.availableForWrite();
    if (available <= 0) return;
    const size_t left = length - offset;
    const size_t n = left < size_t(available) ? left : size_t(available);
    offset += port.write((const uint8_t *)text + offset, n);
    if (offset == length) reset();
  }
  template<class SerialPort> bool write(SerialPort &port, const char *data, size_t n) {
    if (!port) { reset(); return false; }
    drain(port);
    if (length || !n || n > sizeof(text)) return false;
    if (n <= fifoSize) {
      if (port.availableForWrite() < int(n)) return false;
      return port.write((const uint8_t *)data, n) == n;
    }
    memcpy(text, data, n); length = n; offset = 0;
    drain(port);
    return true; // Accepted whole: no other line can interleave until drained.
  }
};
