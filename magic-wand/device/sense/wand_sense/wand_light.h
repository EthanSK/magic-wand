#pragma once
#include <stdint.h>
#include "wand_time.h"
// The board's own status light while no host session owns it.
//
// Ethan: "While it's restarting, instead of being orange, it should be blinking
// orange, just so I know it's loading." On the Puck the loading blink keeps
// running on the device while Wand Receiver restarts. On the Sense the canonical
// program runs on the Mac and stops with the receiver, so only this firmware can
// keep blinking. The receiver ends its session with "XU" when an update restart
// is in progress; the board then blinks the same orange, 250 ms on and 250 ms
// off like the Puck's loadingLight(), until the next host session or the
// existing one-minute offline dark. A plain "X", a lost link or a host timeout
// keeps the steady disconnected orange. Older firmware reads "XU" as "X".

static const uint32_t WAND_LOADING_BLINK_MS = 250;

// "XU": end because the receiver is restarting for an update.
static inline bool wandEndRestarting(const char *line, uint8_t length) {
  return length == 2 && line[0] == 'X' && line[1] == 'U';
}

// Whether the loading orange is lit at `now`; it starts lit.
static inline bool wandLoadingLit(uint32_t now, uint32_t since) {
  return (wandElapsed(now, since) / WAND_LOADING_BLINK_MS) % 2 == 0;
}
