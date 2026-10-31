#pragma once
#include <stdint.h>
#include "wand_time.h"
// The board's own status light while no host session owns it.
//
// ---------- Colour code (read before adding a light or pattern) ----------
// Ethan, 2026-10-30: "Maybe different ones to color code them and add comments
// for that, document that for the future to color code it intelligently when
// adding lights and patterns for me."
//
// Families. Reuse a family's meaning; never borrow another family's colour.
//   Host modes (sent by the receiver as L commands, always steady):
//     green = HUD, red = recording, blue = mouse follow, cyan = scrolling.
//     The board never shows these on its own, so a steady one always means
//     the Mac is connected and in that mode.
//   Link (board-owned, orange family):
//     steady orange          = no receiver (disconnected), dark after a minute.
//     changing colours,      = the receiver is restarting or loading
//       one every 250 ms       (XU); it starts orange, like disconnected.
//                              The only pattern that shows every colour;
//                              it reads by its change, not by one colour.
//   Firmware (board-owned, magenta family; nothing else uses magenta alone):
//     fast magenta strobe    = authorized update: handing over to the updater.
//     transfer/write         = drawn by the bootloader, not this program. Its
//                              0.6.2 source blinks the red and blue LEDs
//                              together for wireless DFU; not yet seen on
//                              this board.
//     slow magenta blink     = new firmware's first start after an update,
//                              until the receiver confirms its version.
//   Power (white = every channel):
//     white flashes x2       = the all-button chord: going to standby.
//     dark                   = standby, sleep or a minute offline.
// Rules for new patterns: steady means a state, animation means a process in
// progress; faster means more urgent or shorter. Every board-owned pattern
// ends at the next host session, the all-button chord or the offline dark, and
// none may delay input, sampling or sleep. Colours are this LED's active-low
// RGB channels at full strength; their appearance is not yet verified by eye.
//
// Ethan: "While it's restarting, instead of being orange, it should be blinking
// orange, just so I know it's loading." Then (2026-10-30): "we should have like
// a flashing animation when it's like installing a new version kind of thing
// between all the colors". On the Puck the loading light keeps running on the
// device while Wand Receiver restarts. On the Sense the canonical program runs
// on the Mac and stops with the receiver, so only this firmware can keep
// animating. The receiver ends its session with "XU" when an update restart is
// in progress; the board then steps through the loading colours, one every
// 250 ms (the cadence of the Puck's loadingLight()), until the next host
// session, the all-button chord or the existing one-minute offline dark. A
// plain "X", a lost link or a host timeout keeps the steady disconnected
// orange. Older firmware reads "XU" as "X". This application cannot light the
// LED while the bootloader is being flashed.

static const uint32_t WAND_LOADING_BLINK_MS = 250;

struct WandRgb { uint8_t r, g, b; };

// Distinct full-strength colours, ordered so neighbours contrast. It starts
// with the established update orange (ORANGE in wand_sense.ino), so the first
// frame matches the disconnected light endSession() shows. Previously the
// loading light alternated that orange with dark.
static const WandRgb WAND_LOADING_COLOURS[] = {
  {255, 80, 0},   // orange
  {0, 255, 0},    // green
  {0, 0, 255},    // blue
  {255, 0, 0},    // red
  {0, 255, 255},  // cyan
  {255, 0, 255},  // magenta
};
static const uint8_t WAND_LOADING_COLOUR_COUNT = sizeof(WAND_LOADING_COLOURS) / sizeof(WAND_LOADING_COLOURS[0]);

// "XU": end because the receiver is restarting for an update.
static inline bool wandEndRestarting(const char *line, uint8_t length) {
  return length == 2 && line[0] == 'X' && line[1] == 'U';
}

// The loading colour at `now`, looping from the first colour at `since`.
// Replaces wandLoadingLit(), the earlier orange on/off phase.
static inline WandRgb wandLoadingColour(uint32_t now, uint32_t since) {
  return WAND_LOADING_COLOURS[(wandElapsed(now, since) / WAND_LOADING_BLINK_MS) % WAND_LOADING_COLOUR_COUNT];
}

// ---------- Firmware family (magenta) ----------
static const WandRgb WAND_FIRMWARE_MAGENTA = {255, 0, 255};
static const WandRgb WAND_LIGHT_DARK = {0, 0, 0};
// Authorized handoff: 100 ms on/off, three flashes, then the board hands over.
static const uint32_t WAND_HANDOFF_STEP_MS = 100;
static const uint8_t WAND_HANDOFF_STEPS = 6;
static inline WandRgb wandHandoffColour(uint8_t step) { return step % 2 == 0 ? WAND_FIRMWARE_MAGENTA : WAND_LIGHT_DARK; }
// First start after an update: 500 ms on/off until a host session begins.
static const uint32_t WAND_VERIFY_BLINK_MS = 500;
static inline WandRgb wandVerifyColour(uint32_t now, uint32_t since) {
  return (wandElapsed(now, since) / WAND_VERIFY_BLINK_MS) % 2 == 0 ? WAND_FIRMWARE_MAGENTA : WAND_LIGHT_DARK;
}
