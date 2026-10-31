// Magic Wand Sense: the complete saved control firmware for the ORIGINAL Seeed
// XIAO nRF52840 Sense (not MG24, not Sense Plus). Not Puck firmware.
// Board Seeeduino:nrf52:xiaonRF52840Sense, core 1.1.13; Seeed Arduino LSM6DS3 2.0.7.
//
// The board reports buttons and motion and obeys light, sensor and sleep
// commands. Ethan's gestures run in the one canonical Puck program, hosted by
// Wand Receiver on the Mac (receiver/Sources/WandVirtualPuck.swift). Nothing is
// uploaded on connection; this sketch is the whole device program.
//
// Wiring (physical presses checked 2026-10-29): Button 1 left D10 = middle
// finger = Middle (HUD/review); Button 2 centre D8 = thumb = Bottom (mouse);
// Button 3 right D9 = index finger = Top (speech). Each
// switch goes to GND; internal pull-ups, pressed = LOW. Wire channel order is
// D8, D9, D10 (the dashboard's legacy keys thumb, index, middle; not fingers).
//
// Protocol "wand-sense-1" over USB serial and Nordic UART, newline framed:
//   board: I{identity}  S seq,us,buttons,pD8,pD9,pD10,imuFlags,ax,ay,az,gx,gy,gz,count,firstUs
//          V millivolts,charging   E event
//   host:  ? identity  H heartbeat  Lrrggbb light  M0/M1/M2 sensor  Z sleep  X end
//          XU end because the receiver is restarting: cycle the loading colours until the next host
//          UC update challenge  UA<version>,<size>,<crc16>,<hmac> authorized handoff  UV confirm update
//          UR<running>,<target> acknowledge one failed update (explicit host request)
//          K<key hex> / KX provision or remove the update key (USB only)
//   board: U C <nonce> | U GO | U NO <reason> | U V ok | U KEY saved/removed
// Readings are raw LSM6DS3TR-C counts (gyro 500 dps, accel 4 g). Each is sent
// as soon as the link can take a frame; readings that arrive while the radio is
// busy are merged into that next frame (count > 1), never held back or dropped.
// No smoothing is added here.
#include <Adafruit_TinyUSB.h>
#include <bluefruit.h>
#include <LSM6DS3.h>
#include <Wire.h>
#include <FreeRTOS.h>
#include <task.h>
#include <queue.h>
#include "nrf_gpio.h"
#include "nrf_sdm.h"          // SD_FWID_GET / SD_SIZE_GET, as the core's utilities.c
#include "nrf52/nrf_mbr.h"   // MBR_SIZE
#include "wand_time.h"
#include "wand_merge.h"
#include "wand_light.h"
#include "wand_update.h"
#include "wand_usb_output.h"
#include "wand_ble_output.h"
#include <Adafruit_LittleFS.h>
#include <InternalFileSystem.h>
using namespace Adafruit_LittleFS_Namespace;

// Numeric firmware versions from 6 on; earlier images used dated letters
// (the previous one was wand-sense-20261029e). Wireless updates only move up.
static const char FIRMWARE[] = "wand-sense-7";
static const uint32_t FIRMWARE_NUMBER = 7;
// The image's own statement of its board and number. The receiver refuses a
// package without exactly one, or for another board or number. Change the
// number with FIRMWARE_NUMBER.
static const char WAND_IMAGE_MARKER[] = "WANDIMG1;xiao-nrf52840-sense;7";
static const uint32_t DEBOUNCE_MS = 10;            // Same as the checked diagnostic sketch.
static const uint32_t HOST_TIMEOUT_MS = 2000;      // Host heartbeat is every 500 ms.
static const uint32_t HEARTBEAT_FRAME_MS = 250;    // Liveness while the sensor is quiet.
static const uint32_t OFFLINE_DARK_MS = 60000UL;   // Puck power policy: dark after a minute offline,
static const uint32_t OFFLINE_SLEEP_MS = 300000UL; // button-wake sleep after five minutes offline.
static const uint8_t ORANGE[3] = {255, 80, 0};     // Receiver WandSenseLight.orange.

LSM6DS3 imu(I2C_MODE, 0x6A);
BLEUart uart;
static bool imuReady = false, bleReady = false, advReady = false, advDataReady = false;
static uint32_t uartStatus = 0xffffffffUL, lastAdvRetry = 0;
static uint8_t activeXL = 0, activeG = 0;
static uint8_t imuMode = 0xff;                     // 0 off, 1 accelerometer ~1.6 Hz, 2 both at 104 Hz
static uint8_t lowRateCount = 0;
static TaskHandle_t loopTask = nullptr;
static volatile uint32_t readyMicros = 0;
static uint32_t linkConnectedAt = 0;
static uint8_t intervalRequests = 0;

enum Transport : uint8_t { NONE = 0, USB_LINK = 1, BLE_LINK = 2 };
static Transport session = NONE;
static uint32_t hostAt = 0, offlineSince = 0, lastFrameAt = 0, lastBatteryAt = 0, sequence = 0;
static bool stateDirty = false, sleepRequested = false, localDark = false; // sleepRequested: host Z only.
static bool loadingBlink = false;                 // Offline after XU: the receiver is restarting; cycle the loading colours.
static uint32_t loadingSince = 0;
static uint8_t chordPhase = 0;                     // Local all-three warning when no host owns the board.
static uint32_t chordAt = 0;
static bool wokeFromOff = false;
static char usbLine[112], bleLine[112]; // Update authorizations are about 80 characters.
static uint8_t usbLength = 0, bleLength = 0;
static uint8_t light[3] = {0, 0, 0};
static bool lightKnown = false;
static uint32_t batteryMv = 0;
static bool charging = false;
static const uint8_t CHARGE_STATUS = 23;           // Original Sense: active-low charger status, P0.17.

// ---------- Wireless update state (see wand_update.h) ----------
static const char UPDATE_KEY_FILE[] = "/wand-update.key";       // 32 bytes, written over USB only.
static const char UPDATE_PENDING_FILE[] = "/wand-update.pending"; // 4 bytes: the version handed over.
// Reviewed: Adafruit nRF52 bootloader 0.6.1/0.6.2 single-bank source reserves 40 KB of
// application data on the nRF52840 and enters BLE DFU from GPREGRET 0xB1.
static const uint32_t REVIEWED_BOOTLOADER_RESERVED = 10 * 4096;
static bool updateKeyPresent = false, updateFsReady = false;
static uint8_t updateKey[WAND_UPDATE_KEY_BYTES];
static bool nonceValid = false;
static char nonceHex[WAND_UPDATE_NONCE_BYTES * 2 + 1];
static uint32_t nonceAt = 0;
static uint32_t updateTarget = 0;
static WandUpdateResult updateResult = WAND_UPDATE_RESULT_NONE;
static bool verifyBlink = false;                   // Offline after an installed update, until a host confirms.
static uint32_t verifySince = 0;

struct Button {
  uint8_t pin; bool raw, pressed, masked; uint32_t changedAt, presses;
  void begin(uint32_t now) {
    pinMode(pin, INPUT_PULLUP);
    raw = digitalRead(pin) == LOW; pressed = raw; changedAt = now; presses = 0;
    masked = raw; // Held at power-on or wake: reported released until let go.
  }
  bool update(uint32_t now) {
    const bool v = digitalRead(pin) == LOW;
    if (v != raw) { raw = v; changedAt = now; }
    if (raw == pressed || wandElapsed(now, changedAt) < DEBOUNCE_MS) return false;
    pressed = raw;
    if (!pressed) { const bool wasMasked = masked; masked = false; return !wasMasked; }
    if (!masked) ++presses;
    return !masked;
  }
  bool down() const { return pressed && !masked; }
};
static Button buttons[3] = {{D8}, {D9}, {D10}};

static uint8_t buttonMask() { uint8_t m = 0; for (int i = 0; i < 3; ++i) if (buttons[i].down()) m |= 1 << i; return m; }
static bool anyPhysical() { for (auto &b : buttons) if (b.pressed || b.raw) return true; return false; }

static void wakeLoop() { BaseType_t woken = pdFALSE; if (loopTask) vTaskNotifyGiveFromISR(loopTask, &woken); portYIELD_FROM_ISR(woken); }
static void onIMUReady() { readyMicros = micros(); wakeLoop(); }

// ---------- Status light (active-low RGB) ----------
static void ledChannel(uint8_t pin, uint8_t value) {
  if (value == 0) {
    // Fully off releases the PWM channel so a dark wand runs no PWM clock.
    for (int i = 0; i < HWPWM_MODULE_NUM; ++i) if (HwPWMx[i]->checkPin(pin)) HwPWMx[i]->removePin(pin);
    pinMode(pin, OUTPUT); digitalWrite(pin, HIGH);
  } else analogWrite(pin, 255 - value);
}
static void setLight(uint8_t r, uint8_t g, uint8_t b) {
  if (lightKnown && light[0] == r && light[1] == g && light[2] == b) return;
  light[0] = r; light[1] = g; light[2] = b; lightKnown = true;
  ledChannel(LED_RED, r); ledChannel(LED_GREEN, g); ledChannel(LED_BLUE, b);
}

static void clearMerged();
// ---------- Sensor ----------
static void setIMUMode(uint8_t mode) {
  if (!imuReady || mode == imuMode) return;
  imuMode = mode; lowRateCount = 0; clearMerged(); // Never mix two sensor modes in one run.
  // Data-ready on INT1: gyro in mode 2, accelerometer in mode 1.
  imu.writeRegister(0x0D, mode == 2 ? 0x02 : mode == 1 ? 0x01 : 0x00);
  imu.writeRegister(0x11, mode == 2 ? activeG : 0x00);                               // CTRL2_G
  imu.writeRegister(0x10, mode == 2 ? activeXL : mode == 1 ? uint8_t((activeXL & 0x0F) | 0x10) : 0x00); // CTRL1_XL, 12.5 Hz when low
}

// ---------- Output ----------
// Only wandtx calls BLEUart.write. It explicitly splits complete lines into ATT
// packets: notify() otherwise silently truncates at the characteristic limit.
// Status producers never interleave bytes or block IMU sampling.
static TaskHandle_t senderTask = nullptr;
struct Outbound { uint16_t length, connection; uint32_t generation; char text[512]; };
static QueueHandle_t outbound = nullptr;
static volatile uint32_t bleGeneration = 0;
static WandUsbOutput usbOutput;
struct BleOutputLink {
  uint16_t connection;
  uint32_t generation;
  bool valid() const {
    return generation == bleGeneration && Bluefruit.connected() &&
      connection == Bluefruit.connHandle() && uart.notifyEnabled(connection);
  }
  uint16_t mtu() const {
    BLEConnection *link = Bluefruit.Connection(connection);
    return link ? link->getMtu() : 0;
  }
  uint32_t now() const { return millis(); }
  size_t write(const uint8_t *data, size_t length) { return uart.write(connection, data, length); }
};
static bool writeBle(const char *text, size_t length, uint16_t connection, uint32_t generation) {
  if (xTaskGetCurrentTaskHandle() != senderTask) return false;
  BleOutputLink link{connection, generation};
  return WandBleOutput::write(link, (const uint8_t *)text, length);
}
static bool writeTo(Transport t, const char *text, int n) {
  if (n <= 0) return false;
  if (t == USB_LINK) {
    return usbOutput.write(Serial, text, size_t(n));
  }
  if (t == BLE_LINK) {
    if (!Bluefruit.connected() || !uart.notifyEnabled()) return false;
    if (xTaskGetCurrentTaskHandle() != senderTask) {
      if (!outbound || n > 512) return false;
      Outbound message{}; message.length = uint16_t(n);
      message.connection = Bluefruit.connHandle(); message.generation = bleGeneration;
      memcpy(message.text, text, size_t(n));
      if (xQueueSend(outbound, &message, 0) != pdTRUE) return false;
      if (senderTask) xTaskNotifyGive(senderTask);
      return true;
    }
    return writeBle(text, size_t(n), Bluefruit.connHandle(), bleGeneration);
  }
  return false;
}
// ---------- Readings waiting for the link ----------
// Measured 2026-10-29 over Bluetooth: macOS ran a 30 ms connection interval and
// the core's three-notification queue (BANDWIDTH_MAX) filled; notify() then
// blocked for up to 100 ms while the IMU overwrote its newest readings, so
// active-stream device-time gaps reached 112 ms (loss is estimated, not measured). Now the Bluetooth
// sender runs in its own task. Readings join one merged slot; a free link sends
// a single reading at once, a busy one sends the whole run (mean rate, count,
// first time) the moment it frees. The newest reading is always included, so
// no intentional waiting is added. Button/session boundaries discard old motion.
typedef WandMerged Merged;
static Merged merged = {};
static uint32_t inputEpoch = 0;
static uint8_t frameButtons = 0;
static uint32_t framePresses[3] = {};
static volatile bool frameWanted = false;          // Button change or heartbeat due.
static uint32_t mergedFrames = 0, mergedReadings = 0;
static void clearMerged() {
  taskENTER_CRITICAL();
  merged = Merged{}; merged.epoch = ++inputEpoch;
  frameButtons = buttonMask();
  for (int i = 0; i < 3; ++i) framePresses[i] = buttons[i].presses;
  taskEXIT_CRITICAL();
}
static void addReading(uint32_t us, const int16_t *v, bool hasGyro) {
  taskENTER_CRITICAL(); wandMergeAdd(merged, us, v, v + 3, hasGyro); taskEXIT_CRITICAL();
}
// A frame that could not be sent goes back in front of anything newer.
static void restoreMerged(const WandMerged &old) {
  taskENTER_CRITICAL(); wandMergeRestore(merged, old); taskEXIT_CRITICAL();
}
static bool sendPending(Transport t) {
  if (session != t || t == NONE) return false;
  taskENTER_CRITICAL();
  const Merged run = merged; merged = Merged{}; merged.epoch = inputEpoch;
  const uint8_t mask = frameButtons;
  const uint32_t presses[3] = {framePresses[0], framePresses[1], framePresses[2]};
  const bool wanted = frameWanted; frameWanted = false;
  taskEXIT_CRITICAL();
  if (!run.count && !wanted) return true;
  const int16_t mean[3] = {wandMergeMean(run, 0), wandMergeMean(run, 1), wandMergeMean(run, 2)};
  const uint32_t us = run.count ? run.last : micros();
  char frame[160];
  const int n = snprintf(frame, sizeof(frame), "\nS%lu,%lu,%u,%lu,%lu,%lu,%u,%d,%d,%d,%d,%d,%d,%u,%lu\n",
    (unsigned long)(sequence + 1), (unsigned long)us, mask,
    (unsigned long)presses[0], (unsigned long)presses[1], (unsigned long)presses[2],
    (run.count && run.hasAccel ? 1 : 0) | (run.count && run.hasGyro ? 2 : 0),
    run.count ? run.accel[0] : 0, run.count ? run.accel[1] : 0, run.count ? run.accel[2] : 0, mean[0], mean[1], mean[2],
    run.count ? run.count : 1, (unsigned long)(run.count ? run.first : us));
  if (!writeTo(t, frame, n)) {
    restoreMerged(run);
    if (wanted) frameWanted = true;
    return false;
  }
  taskENTER_CRITICAL(); ++sequence; taskEXIT_CRITICAL();
  lastFrameAt = millis();
  if (run.count > 1) { ++mergedFrames; mergedReadings += run.count; }
  return true;
}
// Bluetooth only: notify() may wait for the radio here, never in the sampling loop.
static void senderLoop(void *) {
  for (;;) {
    ulTaskNotifyTake(pdTRUE, pdMS_TO_TICKS(20));
    for (;;) {
      Outbound message;
      while (outbound && xQueueReceive(outbound, &message, 0) == pdTRUE) {
        writeBle(message.text, message.length, message.connection, message.generation);
      }
      if (session != BLE_LINK || (!merged.count && !frameWanted)) break;
      if (!sendPending(BLE_LINK)) { vTaskDelay(pdMS_TO_TICKS(2)); break; }
    }
  }
}
static void wakeSender() { if (senderTask) xTaskNotifyGive(senderTask); }

// ---------- Wireless updates ----------
static void boardIdText(char out[17]) {
  snprintf(out, 17, "%08lx%08lx", (unsigned long)NRF_FICR->DEVICEID[1], (unsigned long)NRF_FICR->DEVICEID[0]);
}
static uint32_t codeStart() { return SD_SIZE_GET(MBR_SIZE); }
static uint32_t bootloaderStart() { return NRF_UICR->NRFFW[0]; }
// Legacy function name: conservative application cap, not a second bank.
// Only the reviewed versions and the original Sense s140 7.3.0 layout qualify.
static uint32_t bankedLimit() {
  if (!wandReviewedBootloader(bootloaderVersion) || codeStart() != 0x27000 ||
      bootloaderStart() != 0xF4000 || SD_FWID_GET(MBR_SIZE) != 0x0123) return 0;
  return wandBankedLimit(codeStart(), bootloaderStart(), REVIEWED_BOOTLOADER_RESERVED);
}
static bool readFile(const char *path, uint8_t *out, size_t n) {
  if (!updateFsReady) return false;
  File f(InternalFS);
  if (!f.open(path, FILE_O_READ)) return false;
  const bool ok = f.size() == n && f.read(out, n) == int(n);
  f.close(); return ok;
}
static bool writeFile(const char *path, const uint8_t *data, size_t n) {
  if (!updateFsReady) return false;
  InternalFS.remove(path);
  File f(InternalFS);
  if (!f.open(path, FILE_O_WRITE)) return false;
  const bool ok = f.write(data, n) == n;
  f.close(); return ok;
}
static void loadUpdateState() {
  updateFsReady = InternalFS.begin();
  updateKeyPresent = readFile(UPDATE_KEY_FILE, updateKey, sizeof(updateKey));
  uint8_t pending[4] = {};
  const bool hasPending = readFile(UPDATE_PENDING_FILE, pending, sizeof(pending));
  const uint32_t expected = uint32_t(pending[0]) << 24 | uint32_t(pending[1]) << 16 | uint32_t(pending[2]) << 8 | pending[3];
  updateTarget = hasPending ? expected : 0;
  updateResult = wandUpdateResult(hasPending, expected, FIRMWARE_NUMBER);
  verifyBlink = updateResult == WAND_UPDATE_RESULT_INSTALLED; verifySince = millis();
}
static void sendUpdate(Transport t, const char *text) {
  char line[96];
  writeTo(t, line, snprintf(line, sizeof(line), "\nU %s\n", text));
}

static void sendIdentity(Transport t) {
  char text[512], loader[16];
  wandBootloaderText(bootloaderVersion, loader);
  const int n = snprintf(text, sizeof(text),
    "\nI{\"protocol\":\"wand-sense-1\",\"firmware\":\"%s\",\"id\":\"%08lx%08lx\",\"imu\":%s,\"gyroDpsPerLsb\":0.0175,\"accelGPerLsb\":0.000122,\"odr\":104,\"merge\":true,\"wake\":%s,"
    "\"firmwareNumber\":%lu,\"bootloader\":\"%s\",\"softDevice\":%lu,\"codeStart\":%lu,\"bootloaderStart\":%lu,\"updater\":%u,\"updateKey\":%s,\"update\":\"%s\",\"updateTarget\":%lu}\n",
    FIRMWARE, (unsigned long)NRF_FICR->DEVICEID[1], (unsigned long)NRF_FICR->DEVICEID[0], imuReady ? "true" : "false", wokeFromOff ? "true" : "false",
    (unsigned long)FIRMWARE_NUMBER, loader, (unsigned long)SD_FWID_GET(MBR_SIZE), (unsigned long)codeStart(), (unsigned long)bootloaderStart(),
    unsigned(WAND_UPDATE_PROTOCOL), updateKeyPresent ? "true" : "false", wandUpdateResultName(updateResult), (unsigned long)updateTarget);
  writeTo(t, text, n);
  char radio[120];
  const int count = snprintf(radio, sizeof(radio), "\nEradio init=%u uart=%lu data=%u advertising=%u connected=%u\n", bleReady, (unsigned long)uartStatus, advDataReady, bleReady && Bluefruit.Advertising.isRunning(), bleReady && Bluefruit.connected());
  writeTo(t, radio, count);
}
static void readBattery() {
  uint32_t total = 0;
  for (int i = 0; i < 8; ++i) total += analogRead(PIN_VBAT);
  // Original Sense's 1 MOhm / 510 kOhm divider and the 3.0 V reference.
  batteryMv = uint32_t((total / 8.0f) * (3000.0f / 4096.0f) * (1510.0f / 510.0f));
  charging = digitalRead(CHARGE_STATUS) == LOW;
}
static void sendBattery() {
  char text[32];
  writeTo(session, text, snprintf(text, sizeof(text), "\nV%lu,%u\n", (unsigned long)batteryMv, charging ? 1 : 0));
}
// What macOS actually negotiated, for the receiver log (interval in 1.25 ms units).
static void sendLink() {
  BLEConnection *c = Bluefruit.connected() ? Bluefruit.Connection(Bluefruit.connHandle()) : nullptr;
  if (!c) return;
  char text[120];
  writeTo(session, text, snprintf(text, sizeof(text), "\nElink interval=%u latency=%u mtu=%u phy=%u merged=%lu/%lu\n",
    c->getConnectionInterval(), c->getSlaveLatency(), c->getMtu(), c->getPHY(), (unsigned long)mergedFrames, (unsigned long)mergedReadings));
}

// ---------- Power ----------
static void powerOff() {
  // Button-wake standby: radio, sensor and lights off; any grip button wakes.
  setLight(0, 0, 0);
  if (imuReady) { imu.writeRegister(0x0D, 0); imu.writeRegister(0x11, 0); imu.writeRegister(0x10, 0); }
  detachInterrupt(digitalPinToInterrupt(PIN_LSM6DS3TR_C_INT1));
#ifdef PIN_LSM6DS3TR_C_POWER
  digitalWrite(PIN_LSM6DS3TR_C_POWER, LOW);
#endif
  if (session != NONE) { const char bye[] = "\nE off\n"; writeTo(session, bye, sizeof(bye) - 1); delay(20); }
  if (senderTask) vTaskSuspend(senderTask);
  Bluefruit.Advertising.stop();
  for (auto &b : buttons) nrf_gpio_cfg_sense_input(g_ADigitalPinMap[b.pin], NRF_GPIO_PIN_PULLUP, NRF_GPIO_PIN_SENSE_LOW);
  delay(5);
  sd_power_system_off();
  NRF_POWER->SYSTEMOFF = 1; // SoftDevice absent fallback.
  while (true) {}
}

// restarting: the host sent XU (receiver update restart), so the loading colours cycle.
static void endSession(bool restarting) {
  if (session == NONE) return;
  nonceValid = false; // A challenge belongs to the session that asked for it.
  session = NONE; offlineSince = millis(); localDark = false; chordPhase = 0;
  loadingBlink = restarting; loadingSince = offlineSince;
  setIMUMode(0); clearMerged(); frameWanted = false;
  setLight(ORANGE[0], ORANGE[1], ORANGE[2]); // Disconnected orange, as on the Puck; also the first loading colour.
}

extern "C" void bootloader_util_app_start(uint32_t start_addr);
// Extraction of existing library code: Bluefruit52Lib BLEDfu.cpp's START_DFU
// handoff (core 1.1.13), reached here only after wandAuthorizeUpdate() passes
// instead of from an open GATT control point. Unchanged: it leaves the peer
// address and CCCD state at the bootloader's agreed RAM address so the
// bootloader keeps this board's address (no +1) for the reconnect, sets
// GPREGRET 0xB1, disables the SoftDevice and jumps to the bootloader.
static uint16_t peerCrc16(const uint8_t *data, uint8_t length) {
  uint16_t crc = 0xFFFF;
  while (length--) { uint8_t x = crc >> 8 ^ *data++; x ^= x >> 4; crc = (crc << 8) ^ uint16_t(x << 12) ^ uint16_t(x << 5) ^ uint16_t(x); }
  return crc;
}
static const char *enterUpdater(uint32_t version) {
  const uint16_t handle = Bluefruit.connHandle();
  BLEConnection *conn = Bluefruit.Connection(handle);
  if (!conn) return "handoff";
  if (!wandSaveUpdateRecord(version,
      [](const uint8_t *data, size_t n) { return writeFile(UPDATE_PENDING_FILE, data, n); },
      [](uint8_t *data, size_t n) { return readFile(UPDATE_PENDING_FILE, data, n); })) {
    return "storage";
  }
  updateTarget = version;
  sendUpdate(session, "GO");
  delay(30); // Let GO leave only after durable pending-version readback.

  // Firmware family: three fast magenta flashes. This deliberate 600 ms wait
  // happens only on this authorized exit, never during ordinary input.
  for (uint8_t step = 0; step < WAND_HANDOFF_STEPS; ++step) {
    const WandRgb c = wandHandoffColour(step); setLight(c.r, c.g, c.b); delay(WAND_HANDOFF_STEP_MS);
  }
  setLight(WAND_FIRMWARE_MAGENTA.r, WAND_FIRMWARE_MAGENTA.g, WAND_FIRMWARE_MAGENTA.b);
  typedef struct { ble_gap_addr_t addr; ble_gap_irk_t irk; ble_gap_enc_key_t enc_key; uint8_t sys_attr[8]; uint16_t crc16; } peer_data_t;
  static_assert(offsetof(peer_data_t, crc16) == 60, "bootloader peer data layout");
  peer_data_t *peer = (peer_data_t *)(0x20007F80UL);
  memset(peer, 0, sizeof(*peer));
  uint16_t sysattrLength = sizeof(peer->sys_attr);
  sd_ble_gatts_sys_attr_get(handle, peer->sys_attr, &sysattrLength, BLE_GATTS_SYS_ATTR_FLAG_SYS_SRVCS);
  peer->addr = conn->getPeerAddr();
  if (conn->secured()) {
    bond_keys_t keys;
    if (conn->loadBondKey(&keys)) { peer->addr = keys.peer_id.id_addr_info; peer->irk = keys.peer_id.id_info; peer->enc_key = keys.own_enc; }
  }
  peer->crc16 = peerCrc16((uint8_t *)peer, offsetof(peer_data_t, crc16));
  Bluefruit.Advertising.restartOnDisconnect(false);
  conn->disconnect();
  sd_power_gpregret_clr(0, 0xFF);
  if (sd_power_gpregret_set(0, 0xB1) != NRF_SUCCESS) return "handoff";
  if (sd_softdevice_disable() != NRF_SUCCESS) return "handoff";
  NVIC->ICER[0] = 0xFFFFFFFF; NVIC->ICPR[0] = 0xFFFFFFFF;
#if defined(__NRF_NVIC_ISER_COUNT) && __NRF_NVIC_ISER_COUNT == 2
  NVIC->ICER[1] = 0xFFFFFFFF; NVIC->ICPR[1] = 0xFFFFFFFF;
#endif
  if (sd_softdevice_vector_table_base_set(NRF_UICR->NRFFW[0]) != NRF_SUCCESS) return "handoff";
  __set_CONTROL(0); // Switch to MSP, required with FreeRTOS.
  bootloader_util_app_start(NRF_UICR->NRFFW[0]);
  return "handoff";
}

// U: update challenge, authorization and post-update acknowledgement.
// K: provision or remove the update key, accepted only over USB.
static void updateCommand(const char *line, uint8_t length, Transport from) {
  if (line[0] == 'K') {
    if (from != USB_LINK) { sendUpdate(from, "NO transport"); return; }
    if (length == 2 && line[1] == 'X') {
      if (updateFsReady) InternalFS.remove(UPDATE_KEY_FILE);
      updateKeyPresent = false; memset(updateKey, 0, sizeof(updateKey)); nonceValid = false;
      sendUpdate(from, "KEY removed"); return;
    }
    uint8_t key[WAND_UPDATE_KEY_BYTES];
    if (!wandHexDecode(line + 1, length - 1, key, sizeof(key))) { sendUpdate(from, "NO format"); return; }
    uint8_t saved[WAND_UPDATE_KEY_BYTES] = {};
    if (!writeFile(UPDATE_KEY_FILE, key, sizeof(key)) || !readFile(UPDATE_KEY_FILE, saved, sizeof(saved)) ||
        !wandEqualConstantTime(key, saved, sizeof(key))) {
      updateKeyPresent = false; memset(updateKey, 0, sizeof(updateKey)); nonceValid = false;
      sendUpdate(from, "NO storage"); return;
    }
    memcpy(updateKey, key, sizeof(key)); updateKeyPresent = true; nonceValid = false;
    sendUpdate(from, "KEY saved"); return;
  }
  if (length == 2 && line[1] == 'C') {
    if (!updateKeyPresent) { sendUpdate(from, "NO no-key"); return; }
    uint8_t nonce[WAND_UPDATE_NONCE_BYTES], available = 0;
    for (int i = 0; i < 20 && available < sizeof(nonce); ++i) { sd_rand_application_bytes_available_get(&available); if (available < sizeof(nonce)) delay(1); }
    if (available < sizeof(nonce) || sd_rand_application_vector_get(nonce, sizeof(nonce)) != NRF_SUCCESS) { sendUpdate(from, "NO busy"); return; }
    wandHexEncode(nonce, sizeof(nonce), nonceHex); nonceValid = true; nonceAt = millis();
    char reply[48]; snprintf(reply, sizeof(reply), "C %s", nonceHex); sendUpdate(from, reply); return;
  }
  if ((length == 2 && line[1] == 'V') || (length > 2 && line[1] == 'R')) {
    // UV confirms a successful boot. UR<running>,<target> explicitly
    // acknowledges a failed attempt; a stale request cannot clear a new one.
    if (line[1] == 'V') {
      if (updateResult != WAND_UPDATE_RESULT_INSTALLED) { sendUpdate(from, "NO result"); return; }
    } else {
      if (!wandAcknowledgeFailedResult(line, length, FIRMWARE_NUMBER, updateTarget, updateResult)) {
        sendUpdate(from, "NO result"); return;
      }
    }
    if (!updateFsReady) { sendUpdate(from, "NO storage"); return; }
    if (!wandClearUpdateRecord([] { InternalFS.remove(UPDATE_PENDING_FILE); },
                               [] { return InternalFS.exists(UPDATE_PENDING_FILE); })) {
      sendUpdate(from, "NO storage"); return;
    }
    updateResult = WAND_UPDATE_RESULT_NONE; updateTarget = 0; verifyBlink = false;
    sendUpdate(from, "V ok"); return;
  }
  WandUpdateRequest request;
  if (!wandParseUpdateRequest(line, length, request)) { sendUpdate(from, "NO format"); return; }
  char board[17]; boardIdText(board);
  const WandUpdateContext context = {updateKeyPresent, updateKey, from == BLE_LINK, nonceValid, nonceHex, nonceAt, millis(), board,
                                     FIRMWARE_NUMBER, bankedLimit(), uint16_t(batteryMv > 0xffff ? 0xffff : batteryMv), charging, anyPhysical()};
  const WandUpdateRefusal result = wandAuthorizeUpdate(request, context);
  nonceValid = false; // Single use, success or not.
  if (result != WAND_UPDATE_OK) { char reply[32]; snprintf(reply, sizeof(reply), "NO %s", wandUpdateRefusalName(result)); sendUpdate(from, reply); return; }
  // Normally this never returns; a failed save must leave the current app running.
  const char *failure = enterUpdater(request.version);
  char reply[32]; snprintf(reply, sizeof(reply), "NO %s", failure); sendUpdate(from, reply);
}

static int hexValue(char c) { return c >= '0' && c <= '9' ? c - '0' : c >= 'a' && c <= 'f' ? c - 'a' + 10 : c >= 'A' && c <= 'F' ? c - 'A' + 10 : -1; }
static void command(const char *line, uint8_t length, Transport from) {
  if (!length) return;
  const char c = line[0];
  if (c == '?') { sendIdentity(from); if (session == from) sendBattery(); return; }
  if (c == 'X') { if (session == from) endSession(wandEndRestarting(line, length)); return; }
  if (c == 'U' || c == 'K') { if (session == from) updateCommand(line, length, from); return; }
  if (c != 'H' && c != 'L' && c != 'M' && c != 'Z') return;
  if (session != from) {
    // A new host session: current state only, never queued edges or old motion.
    session = from; clearMerged(); stateDirty = true; chordPhase = 0; localDark = false; loadingBlink = false; verifyBlink = false;
    lastBatteryAt = millis() - 10000; // Report the battery at once.
  }
  hostAt = millis();
  if (c == 'L' && length == 7) {
    int v[6]; for (int i = 0; i < 6; ++i) { v[i] = hexValue(line[i + 1]); if (v[i] < 0) return; }
    setLight(v[0] * 16 + v[1], v[2] * 16 + v[3], v[4] * 16 + v[5]);
  } else if (c == 'M' && length == 2 && line[1] >= '0' && line[1] <= '2') setIMUMode(line[1] - '0');
  else if (c == 'Z') sleepRequested = true;
}
static void readCommands() {
  while (Serial.available()) {
    const int c = Serial.read();
    if (c == '\n' || c == '\r') { command(usbLine, usbLength, USB_LINK); usbLength = 0; }
    else if (usbLength < sizeof(usbLine) - 1) usbLine[usbLength++] = char(c);
    else usbLength = 0;
  }
  while (uart.available()) {
    const int c = uart.read();
    if (c == '\n' || c == '\r') { command(bleLine, bleLength, BLE_LINK); bleLength = 0; }
    else if (bleLength < sizeof(bleLine) - 1) bleLine[bleLength++] = char(c);
    else bleLength = 0;
  }
}

static void connectCallback(uint16_t handle) {
  ++bleGeneration; // A previous link's queued status never enters the next link.
  BLEConnection *connection = Bluefruit.Connection(handle);
  if (!connection) return;
  connection->requestPHY();
  connection->requestDataLengthUpdate();
  connection->requestMtuExchange(WandBleOutput::maxMtu);
  // The 15 ms interval itself is requested from the loop once these finish.
  linkConnectedAt = millis(); intervalRequests = 0;
}

void setup() {
  // The core saves and clears RESETREAS during start-up; informational only.
  wokeFromOff = (readResetReason() & POWER_RESETREAS_OFF_Msk) != 0;
  loopTask = xTaskGetCurrentTaskHandle();
  Serial.begin(115200);
  const uint32_t now = millis();
  for (auto &b : buttons) b.begin(now);
  pinMode(VBAT_ENABLE, OUTPUT);
  digitalWrite(VBAT_ENABLE, LOW); // Keep P0.14 low whenever a battery may be fitted.
  pinMode(CHARGE_STATUS, INPUT_PULLUP);
  analogReference(AR_INTERNAL_3_0);
  analogReadResolution(12);
  setLight(ORANGE[0], ORANGE[1], ORANGE[2]);

  // 500 deg/s: measured fast sweeps clipped at the Puck's 245 deg/s setting
  // (286.7 deg/s full scale). The host still converts to Puck counts.
  imu.settings.gyroRange = 500;
  imu.settings.accelRange = 4;      // The Puck's own 4 g scale.
  imu.settings.accelBandWidth = 50; // The Puck's 50 Hz accelerometer anti-alias filter (Espruino jswrap_puck.c).
  imu.settings.gyroSampleRate = 104;
  imu.settings.accelSampleRate = 104;
  imuReady = imu.begin() == 0;
  if (imuReady) {
    Wire1.setClock(400000); // The built-in IMU is on Wire1; shorter reads, no added wait.
    imu.readRegister(&activeXL, 0x10);
    imu.readRegister(&activeG, 0x11);
    uint8_t control3 = 0;
    if (imu.readRegister(&control3, 0x12) == IMU_SUCCESS) imu.writeRegister(0x12, control3 | 0x40); // Block data update.
    pinMode(PIN_LSM6DS3TR_C_INT1, INPUT);
    attachInterrupt(digitalPinToInterrupt(PIN_LSM6DS3TR_C_INT1), onIMUReady, RISING);
    setIMUMode(0);
  }

  outbound = xQueueCreate(4, sizeof(Outbound));
  Bluefruit.autoConnLed(false);
  // One UART service, one peripheral: reserve only the vendor UUID and GATT
  // table it uses, leaving room for the 247-byte MTU in the core's fixed RAM.
  Bluefruit.configUuid128Count(1);
  Bluefruit.configAttrTableSize(2048);
  Bluefruit.configPrphBandwidth(BANDWIDTH_MAX);
  bleReady = Bluefruit.begin(1, 0);
  Bluefruit.setName("Magic Wand Sense");
  Bluefruit.Periph.setConnInterval(12, 12); // 15 ms, as the Puck requested.
  Bluefruit.Periph.setConnectCallback(connectCallback);
  uartStatus = uart.begin();
  Bluefruit.Advertising.clearData(); Bluefruit.ScanResponse.clearData();
  advDataReady = Bluefruit.Advertising.addFlags(BLE_GAP_ADV_FLAGS_LE_ONLY_GENERAL_DISC_MODE);
  advDataReady = Bluefruit.Advertising.addService(uart) && advDataReady;
  advDataReady = Bluefruit.ScanResponse.addName() && advDataReady;
  // Board identity for the receiver's selected-board check: test company 0xFFFF + 8-byte ID.
  uint8_t identity[10] = {0xFF, 0xFF};
  const uint32_t id[2] = {NRF_FICR->DEVICEID[1], NRF_FICR->DEVICEID[0]};
  for (int i = 0; i < 8; ++i) identity[2 + i] = uint8_t(id[i / 4] >> (24 - 8 * (i % 4)));
  advDataReady = Bluefruit.ScanResponse.addManufacturerData(identity, sizeof(identity)) && advDataReady;
  Bluefruit.Advertising.restartOnDisconnect(true);
  Bluefruit.Advertising.setInterval(32, 244);
  advReady = bleReady && uartStatus == 0 && advDataReady && Bluefruit.Advertising.start(0);
  xTaskCreate(senderLoop, "wandtx", 1024, nullptr, TASK_PRIO_LOW, &senderTask);
  offlineSince = millis();
  readBattery(); lastBatteryAt = millis();
  loadUpdateState(); // After Bluefruit.begin(), which also uses the internal file system.
  (void)*(volatile const char *)WAND_IMAGE_MARKER; // Keep the marker in the linked image.
}

void loop() {
  // Wake on sensor data-ready or within 5 ms for buttons and commands.
  ulTaskNotifyTake(pdTRUE, pdMS_TO_TICKS(5));
  uint32_t now = millis();
  bool buttonChanged = false;
  for (auto &b : buttons) if (b.update(now)) buttonChanged = true;
  if (buttonChanged) {
    // Ethan: dragging/scrolling only while held. Never replay a previous
    // control's queued motion with the new button state, including failed sends.
    clearMerged(); stateDirty = true;
  }
  usbOutput.drain(Serial); // Also finish initial identity before any host session exists.
  readCommands();
  if (bleReady && uartStatus == 0 && advDataReady && !Bluefruit.connected() && !Bluefruit.Advertising.isRunning() && wandElapsed(millis(), lastAdvRetry) >= 1000) {
    lastAdvRetry = millis(); advReady = Bluefruit.Advertising.start(0);
  }
  // Commands refresh hostAt using millis(). Compare only against a later
  // reading; unsigned subtraction from an earlier tick looks five weeks old.
  now = millis();

  if (session != NONE) {
    const bool linkUp = session == USB_LINK ? bool(Serial) : (Bluefruit.connected() && uart.notifyEnabled());
    if (!linkUp || wandElapsed(now, hostAt) > HOST_TIMEOUT_MS) endSession(false);
  }

  // endSession() above can also advance offlineSince by a tick.
  now = millis();
  bool sent = false; // A new reading joined the merged slot this pass.
  if (imuReady && imuMode && session != NONE) {
    uint8_t status = 0;
    if (imu.readRegister(&status, 0x1E) == IMU_SUCCESS && (status & (imuMode == 2 ? 0x02 : 0x01))) {
      uint8_t raw[12];
      uint32_t us = readyMicros;
      if (uint32_t(micros() - us) > 20000) us = micros();
      if (imu.readRegisterRegion(raw, 0x22, 12) == IMU_SUCCESS) {
        int16_t v[6];
        for (int i = 0; i < 6; ++i) v[i] = int16_t(raw[2 * i] | (raw[2 * i + 1] << 8));
        // Desk sensing reports every eighth 12.5 Hz reading (~1.6 Hz), like Puck.accelOn(1.6).
        const bool publish = imuMode == 2 || (lowRateCount++ % 8) == 0;
        if (publish) { addReading(us, v, imuMode == 2); sent = true; }
      }
    }
  }
  if (session != NONE && (stateDirty || (!sent && wandElapsed(now, lastFrameAt) >= HEARTBEAT_FRAME_MS))) { stateDirty = false; frameWanted = true; }
  if (session == USB_LINK) sendPending(USB_LINK);      // USB writes never block (availableForWrite).
  else if (session == BLE_LINK && (sent || frameWanted)) wakeSender();
  // Ask macOS for the Puck's 15 ms interval after connection set-up settles.
  if (Bluefruit.connected() && intervalRequests < 3 && wandElapsed(now, linkConnectedAt) >= 1500u + 5000u * intervalRequests) {
    BLEConnection *c = Bluefruit.Connection(Bluefruit.connHandle());
    if (c && c->getConnectionInterval() > 12) c->requestConnectionParameter(12);
    ++intervalRequests;
  }
  if (wandElapsed(now, lastBatteryAt) >= 10000) { lastBatteryAt = now; readBattery(); if (session != NONE) { sendBattery(); sendLink(); } }

  if (session == NONE) {
    // The Puck power policy's offline behaviour, kept on the board itself.
    // Any grip edge re-arms the offline timers and shows the disconnected light again.
    if (stateDirty) { stateDirty = false; offlineSince = now; if (localDark && !chordPhase) { localDark = false; setLight(ORANGE[0], ORANGE[1], ORANGE[2]); } }
    if (!chordPhase && buttonMask() == 7) { chordPhase = 1; chordAt = now; loadingBlink = false; verifyBlink = false; }
    if (chordPhase) {
      // All three: flash every colour twice (100 ms steps), then sleep once released.
      const uint8_t step = uint8_t((now - chordAt) / 100);
      if (step < 4) { const uint8_t v = step & 1 ? 0 : 255; setLight(v, v, v); }
    } else if (!localDark && wandElapsed(now, offlineSince) >= OFFLINE_DARK_MS && !anyPhysical()) { localDark = true; loadingBlink = false; verifyBlink = false; setLight(0, 0, 0); }
    else if (verifyBlink) {
      // Firmware family: slow magenta until the receiver confirms the new version.
      const WandRgb colour = wandVerifyColour(now, verifySince);
      setLight(colour.r, colour.g, colour.b);
    } else if (loadingBlink) {
      // Loop-paced (it wakes at least every 5 ms): no timer, no wait, no session.
      // setLight() writes the LED only when the colour changes (every 250 ms).
      const WandRgb colour = wandLoadingColour(now, loadingSince);
      setLight(colour.r, colour.g, colour.b);
    }
  }
  const bool localSleep = session == NONE && ((chordPhase && wandElapsed(now, chordAt) >= 400) || wandElapsed(now, offlineSince) >= OFFLINE_SLEEP_MS);
  // Sleep waits for every grip button to be released so a held chord cannot wake it at once.
  if ((sleepRequested || localSleep) && !anyPhysical()) powerOff();
}
