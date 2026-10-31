#pragma once
#include <stdint.h>
#include <stddef.h>
#include <string.h>
#include <stdio.h>
#include "wand_time.h"
// Authorized wireless application updates. Pure, host-testable logic only;
// wand_sense.ino owns storage, the radio and the bootloader handoff.
//
// Ethan, 2026-10-30: "Is this firmware also gonna add wireless updates? And is
// fully reviewed so it'll work, so I never have to plug it in again?"
//
// Why authorization lives here: the Adafruit nRF52 bootloader (0.6.1 and 0.6.2 sources
// reviewed) accepts any unsigned application package once it is in BLE DFU
// mode; its init packet carries only a device type, SoftDevice list and CRC16.
// This firmware therefore does NOT expose Adafruit's BLEDfu service, whose
// control point lets any nearby central reboot the board into that mode. The
// handoff happens only after the receiver proves it holds this board's update
// key: HMAC-SHA256 over a fresh one-time board nonce and the exact image it
// will send. The key is written only over USB (never Bluetooth), kept in the
// internal file system, and survives application updates (the bootloader
// preserves its reserved application-data pages).
//
// Residual risk, documented rather than hidden: once authorized, the
// bootloader advertises openly until the transfer ends or the board resets;
// the receiver connects at once and holds the only connection.

static const uint8_t WAND_UPDATE_PROTOCOL = 1;
static const uint8_t WAND_UPDATE_KEY_BYTES = 32;
static const uint8_t WAND_UPDATE_NONCE_BYTES = 16;
static const uint32_t WAND_UPDATE_NONCE_MS = 30000;  // A challenge expires after 30 s and is single-use.
static const uint16_t WAND_UPDATE_MIN_MILLIVOLTS = 3600; // Below this, only while charging.
static const char WAND_UPDATE_DOMAIN[] = "wand-sense-update-1";

// ---------- SHA-256 / HMAC-SHA256 (FIPS 180-4, RFC 2104) ----------
struct WandSha256 { uint32_t h[8]; uint8_t block[64]; uint64_t bytes; uint8_t used; };
static const uint32_t WAND_SHA256_K[64] = {
  0x428a2f98,0x71374491,0xb5c0fbcf,0xe9b5dba5,0x3956c25b,0x59f111f1,0x923f82a4,0xab1c5ed5,
  0xd807aa98,0x12835b01,0x243185be,0x550c7dc3,0x72be5d74,0x80deb1fe,0x9bdc06a7,0xc19bf174,
  0xe49b69c1,0xefbe4786,0x0fc19dc6,0x240ca1cc,0x2de92c6f,0x4a7484aa,0x5cb0a9dc,0x76f988da,
  0x983e5152,0xa831c66d,0xb00327c8,0xbf597fc7,0xc6e00bf3,0xd5a79147,0x06ca6351,0x14292967,
  0x27b70a85,0x2e1b2138,0x4d2c6dfc,0x53380d13,0x650a7354,0x766a0abb,0x81c2c92e,0x92722c85,
  0xa2bfe8a1,0xa81a664b,0xc24b8b70,0xc76c51a3,0xd192e819,0xd6990624,0xf40e3585,0x106aa070,
  0x19a4c116,0x1e376c08,0x2748774c,0x34b0bcb5,0x391c0cb3,0x4ed8aa4a,0x5b9cca4f,0x682e6ff3,
  0x748f82ee,0x78a5636f,0x84c87814,0x8cc70208,0x90befffa,0xa4506ceb,0xbef9a3f7,0xc67178f2};
static inline uint32_t wandRotr(uint32_t x, uint8_t n) { return (x >> n) | (x << (32 - n)); }
static inline void wandShaBlock(WandSha256 &s, const uint8_t *p) {
  uint32_t w[64];
  for (int i = 0; i < 16; ++i) w[i] = uint32_t(p[i * 4]) << 24 | uint32_t(p[i * 4 + 1]) << 16 | uint32_t(p[i * 4 + 2]) << 8 | p[i * 4 + 3];
  for (int i = 16; i < 64; ++i) {
    const uint32_t s0 = wandRotr(w[i - 15], 7) ^ wandRotr(w[i - 15], 18) ^ (w[i - 15] >> 3);
    const uint32_t s1 = wandRotr(w[i - 2], 17) ^ wandRotr(w[i - 2], 19) ^ (w[i - 2] >> 10);
    w[i] = w[i - 16] + s0 + w[i - 7] + s1;
  }
  uint32_t a = s.h[0], b = s.h[1], c = s.h[2], d = s.h[3], e = s.h[4], f = s.h[5], g = s.h[6], h = s.h[7];
  for (int i = 0; i < 64; ++i) {
    const uint32_t t1 = h + (wandRotr(e, 6) ^ wandRotr(e, 11) ^ wandRotr(e, 25)) + ((e & f) ^ (~e & g)) + WAND_SHA256_K[i] + w[i];
    const uint32_t t2 = (wandRotr(a, 2) ^ wandRotr(a, 13) ^ wandRotr(a, 22)) + ((a & b) ^ (a & c) ^ (b & c));
    h = g; g = f; f = e; e = d + t1; d = c; c = b; b = a; a = t1 + t2;
  }
  s.h[0] += a; s.h[1] += b; s.h[2] += c; s.h[3] += d; s.h[4] += e; s.h[5] += f; s.h[6] += g; s.h[7] += h;
}
static inline void wandShaInit(WandSha256 &s) {
  static const uint32_t iv[8] = {0x6a09e667,0xbb67ae85,0x3c6ef372,0xa54ff53a,0x510e527f,0x9b05688c,0x1f83d9ab,0x5be0cd19};
  memcpy(s.h, iv, sizeof(iv)); s.bytes = 0; s.used = 0;
}
static inline void wandShaUpdate(WandSha256 &s, const uint8_t *data, size_t n) {
  for (size_t i = 0; i < n; ++i) {
    s.block[s.used++] = data[i]; ++s.bytes;
    if (s.used == 64) { wandShaBlock(s, s.block); s.used = 0; }
  }
}
static inline void wandShaFinal(WandSha256 &s, uint8_t out[32]) {
  const uint64_t bits = s.bytes * 8;
  const uint8_t one = 0x80, zero = 0;
  wandShaUpdate(s, &one, 1);
  while (s.used != 56) wandShaUpdate(s, &zero, 1);
  uint8_t length[8];
  for (int i = 0; i < 8; ++i) length[i] = uint8_t(bits >> (56 - 8 * i));
  wandShaUpdate(s, length, 8);
  for (int i = 0; i < 8; ++i) { out[i * 4] = s.h[i] >> 24; out[i * 4 + 1] = s.h[i] >> 16; out[i * 4 + 2] = s.h[i] >> 8; out[i * 4 + 3] = s.h[i]; }
}
static inline void wandHmacSha256(const uint8_t *key, size_t keyLength, const uint8_t *message, size_t length, uint8_t out[32]) {
  uint8_t k[64] = {0};
  if (keyLength > 64) { WandSha256 s; wandShaInit(s); wandShaUpdate(s, key, keyLength); wandShaFinal(s, k); }
  else memcpy(k, key, keyLength);
  uint8_t pad[64];
  WandSha256 inner; wandShaInit(inner);
  for (int i = 0; i < 64; ++i) pad[i] = k[i] ^ 0x36;
  wandShaUpdate(inner, pad, 64); wandShaUpdate(inner, message, length);
  uint8_t innerHash[32]; wandShaFinal(inner, innerHash);
  WandSha256 outer; wandShaInit(outer);
  for (int i = 0; i < 64; ++i) pad[i] = k[i] ^ 0x5c;
  wandShaUpdate(outer, pad, 64); wandShaUpdate(outer, innerHash, 32);
  wandShaFinal(outer, out);
}
// No early exit: comparison time does not reveal how much of a tag matched.
static inline bool wandEqualConstantTime(const uint8_t *a, const uint8_t *b, size_t n) {
  uint8_t diff = 0;
  for (size_t i = 0; i < n; ++i) diff |= a[i] ^ b[i];
  return diff == 0;
}

// ---------- Hex ----------
static inline int wandHexNibble(char c) { return c >= '0' && c <= '9' ? c - '0' : c >= 'a' && c <= 'f' ? c - 'a' + 10 : c >= 'A' && c <= 'F' ? c - 'A' + 10 : -1; }
// Exactly 2*n hex characters into n bytes.
static inline bool wandHexDecode(const char *text, size_t textLength, uint8_t *out, size_t n) {
  if (textLength != n * 2) return false;
  for (size_t i = 0; i < n; ++i) {
    const int hi = wandHexNibble(text[i * 2]), lo = wandHexNibble(text[i * 2 + 1]);
    if (hi < 0 || lo < 0) return false;
    out[i] = uint8_t(hi << 4 | lo);
  }
  return true;
}
static inline void wandHexEncode(const uint8_t *data, size_t n, char *out) {
  static const char digits[] = "0123456789abcdef";
  for (size_t i = 0; i < n; ++i) { out[i * 2] = digits[data[i] >> 4]; out[i * 2 + 1] = digits[data[i] & 15]; }
  out[n * 2] = 0;
}

// ---------- Bootloader facts ----------
// The bootloader stores MK_BOOTLOADER_VERSION (major<<16 | minor<<8 | patch)
// in NRF_TIMER2->CC[0]; the core copies it to `bootloaderVersion` at start.
static inline void wandBootloaderText(uint32_t raw, char out[16]) {
  snprintf(out, 16, "%u.%u.%u", unsigned((raw >> 16) & 0xff), unsigned((raw >> 8) & 0xff), unsigned(raw & 0xff));
}
// Historical name: this is our conservative half-size application cap,
// NOT a bootloader bank or rollback guarantee. Reviewed 0.6.1/0.6.2 compile
// dfu_single_bank.c: Start DFU erases the current application before transfer.
// Interrupted/invalid transfers can require USB application recovery.
static inline uint32_t wandBankedLimit(uint32_t codeStart, uint32_t bootloaderStart, uint32_t reserved) {
  if (bootloaderStart <= codeStart || bootloaderStart - codeStart <= reserved) return 0;
  const uint32_t full = bootloaderStart - codeStart - reserved;
  return (full - full % (2 * 4096)) / 2;
}

// ---------- Commands ----------
// The exact message both sides authenticate. Binding the image size and CRC16
// stops a captured authorization from being reused for a different image.
static inline int wandUpdateMessage(char *out, size_t capacity, const char *boardId, const char *nonceHex,
                                    uint32_t version, uint32_t size, uint16_t crc) {
  return snprintf(out, capacity, "%s|%s|%s|%lu|%lu|%04x", WAND_UPDATE_DOMAIN, boardId, nonceHex,
                  (unsigned long)version, (unsigned long)size, unsigned(crc));
}

// "UA<version>,<size>,<crc16 hex4>,<tag hex64>": authorize one handoff.
struct WandUpdateRequest { uint32_t version, size; uint16_t crc; uint8_t tag[32]; };
static inline bool wandParseDecimal(const char *&p, const char *end, uint32_t &value) {
  if (p >= end || *p < '0' || *p > '9') return false;
  uint64_t v = 0;
  while (p < end && *p >= '0' && *p <= '9') { v = v * 10 + uint32_t(*p++ - '0'); if (v > 0xffffffffULL) return false; }
  value = uint32_t(v); return true;
}
static inline bool wandParseUpdateRequest(const char *line, size_t length, WandUpdateRequest &r) {
  if (length < 2 || line[0] != 'U' || line[1] != 'A') return false;
  const char *p = line + 2, *end = line + length;
  uint8_t crc[2];
  if (!wandParseDecimal(p, end, r.version) || p >= end || *p++ != ',') return false;
  if (!wandParseDecimal(p, end, r.size) || p >= end || *p++ != ',') return false;
  if (end - p < 5 || !wandHexDecode(p, 4, crc, 2) || p[4] != ',') return false;
  r.crc = uint16_t(crc[0] << 8 | crc[1]); p += 5;
  return wandHexDecode(p, size_t(end - p), r.tag, 32);
}

enum WandUpdateRefusal : uint8_t {
  WAND_UPDATE_OK = 0, WAND_UPDATE_NO_KEY, WAND_UPDATE_TRANSPORT, WAND_UPDATE_NONCE, WAND_UPDATE_AUTH,
  WAND_UPDATE_VERSION, WAND_UPDATE_SIZE, WAND_UPDATE_BATTERY, WAND_UPDATE_BUSY, WAND_UPDATE_BOOTLOADER
};
static inline const char *wandUpdateRefusalName(WandUpdateRefusal r) {
  static const char *names[] = {"ok", "no-key", "transport", "nonce", "auth", "version", "size", "battery", "busy", "bootloader"};
  return r <= WAND_UPDATE_BOOTLOADER ? names[r] : "unknown";
}
struct WandUpdateContext {
  bool keyPresent; const uint8_t *key;  // WAND_UPDATE_KEY_BYTES
  bool overBluetooth;                   // The handoff needs the live Bluetooth connection.
  bool nonceValid; const char *nonceHex; uint32_t nonceAt, now;
  const char *boardId;
  uint32_t currentVersion;
  uint32_t bankedLimit;                 // Legacy name: conservative size cap, not rollback; 0 for unreviewed layout.
  uint16_t millivolts; bool charging;
  bool buttonsHeld;
};
// Checks run in this order; authentication precedes every image check so an
// unauthenticated caller learns nothing about the board's state.
static inline WandUpdateRefusal wandAuthorizeUpdate(const WandUpdateRequest &r, const WandUpdateContext &c) {
  if (!c.keyPresent) return WAND_UPDATE_NO_KEY;
  if (!c.overBluetooth) return WAND_UPDATE_TRANSPORT;
  if (!c.nonceValid || wandElapsed(c.now, c.nonceAt) >= WAND_UPDATE_NONCE_MS) return WAND_UPDATE_NONCE;
  char message[160];
  const int n = wandUpdateMessage(message, sizeof(message), c.boardId, c.nonceHex, r.version, r.size, r.crc);
  if (n <= 0 || size_t(n) >= sizeof(message)) return WAND_UPDATE_AUTH;
  uint8_t expected[32];
  wandHmacSha256(c.key, WAND_UPDATE_KEY_BYTES, (const uint8_t *)message, size_t(n), expected);
  if (!wandEqualConstantTime(expected, r.tag, 32)) return WAND_UPDATE_AUTH;
  if (r.version <= c.currentVersion) return WAND_UPDATE_VERSION;  // Numeric versions only move forward.
  if (c.bankedLimit == 0) return WAND_UPDATE_BOOTLOADER;
  if (r.size == 0 || r.size > c.bankedLimit) return WAND_UPDATE_SIZE;
  if (c.millivolts < WAND_UPDATE_MIN_MILLIVOLTS && !c.charging) return WAND_UPDATE_BATTERY;
  if (c.buttonsHeld) return WAND_UPDATE_BUSY;
  return WAND_UPDATE_OK;
}

// After a handoff the board records the version it expected. On the next start
// the running firmware compares it with its own number.
enum WandUpdateResult : uint8_t { WAND_UPDATE_RESULT_NONE = 0, WAND_UPDATE_RESULT_INSTALLED, WAND_UPDATE_RESULT_NOT_INSTALLED };
static inline WandUpdateResult wandUpdateResult(bool pending, uint32_t expected, uint32_t running) {
  if (!pending) return WAND_UPDATE_RESULT_NONE;
  return expected == running ? WAND_UPDATE_RESULT_INSTALLED : WAND_UPDATE_RESULT_NOT_INSTALLED;
}
static inline const char *wandUpdateResultName(WandUpdateResult r) {
  return r == WAND_UPDATE_RESULT_INSTALLED ? "installed" : r == WAND_UPDATE_RESULT_NOT_INSTALLED ? "not-installed" : "none";
}

// A successful write alone is insufficient: close and read the exact bytes
// back before announcing GO or leaving the current application.
template<class Write, class Read>
static inline bool wandSaveUpdateRecord(uint32_t version, Write write, Read read) {
  const uint8_t wanted[4] = {uint8_t(version >> 24), uint8_t(version >> 16), uint8_t(version >> 8), uint8_t(version)};
  uint8_t actual[4] = {};
  return write(wanted, sizeof(wanted)) && read(actual, sizeof(actual)) && memcmp(wanted, actual, sizeof(wanted)) == 0;
}
static inline bool wandReviewedBootloader(uint32_t version) { return version == 0x000601 || version == 0x000602; }

// UR targets one observed failed attempt, never a successful installation.
static inline bool wandAcknowledgeFailedResult(const char *line, size_t length, uint32_t running,
                                               uint32_t pending, WandUpdateResult result) {
  if (length <= 2 || line[0] != 'U' || line[1] != 'R' || result != WAND_UPDATE_RESULT_NOT_INSTALLED) return false;
  const char *p = line + 2, *end = line + length;
  uint32_t wantedRunning = 0, wantedTarget = 0;
  return wandParseDecimal(p, end, wantedRunning) && p != end && *p++ == ',' &&
         wandParseDecimal(p, end, wantedTarget) && p == end && wantedRunning == running && wantedTarget == pending;
}
template<class Remove, class Exists>
static inline bool wandClearUpdateRecord(Remove remove, Exists exists) {
  remove();
  return !exists(); // A refused/failed erase must not be acknowledged as cleared.
}
