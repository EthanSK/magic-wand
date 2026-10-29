// Magic Wand Sense: the complete saved control firmware for the ORIGINAL Seeed
// XIAO nRF52840 Sense (not MG24, not Sense Plus). Not Puck firmware.
// Board Seeeduino:nrf52:xiaonRF52840Sense, core 1.1.13; Seeed Arduino LSM6DS3 2.0.7.
//
// The board reports buttons and motion and obeys light, sensor and sleep
// commands. Ethan's gestures run in the one canonical Puck program, hosted by
// Wand Receiver on the Mac (receiver/Sources/WandVirtualPuck.swift). Nothing is
// uploaded on connection; this sketch is the whole device program.
//
// Wiring (Ethan's assembled wand, user-corrected 2026-10-29): Button 1 left
// D8 = middle finger = Bottom (mouse); Button 2 centre D9 = thumb = Top
// (speech); Button 3 right D10 = index finger = Middle (HUD/review). Each
// switch goes to GND; internal pull-ups, pressed = LOW. Wire channel order is
// D8, D9, D10 (the dashboard's legacy keys thumb, index, middle; not fingers).
//
// Protocol "wand-sense-1" over USB serial and Nordic UART, newline framed:
//   board: I{identity}  S seq,us,buttons,pD8,pD9,pD10,imuFlags,ax,ay,az,gx,gy,gz
//          V millivolts,charging   E event
//   host:  ? identity  H heartbeat  Lrrggbb light  M0/M1/M2 sensor  Z sleep  X end
// Readings are raw LSM6DS3 counts (gyro 245 dps, accel 4 g), each sent as soon
// as it is read: no batching, buffering or smoothing is added here.
#include <Adafruit_TinyUSB.h>
#include <bluefruit.h>
#include <LSM6DS3.h>
#include <Wire.h>
#include <FreeRTOS.h>
#include <task.h>
#include "nrf_gpio.h"
#include "wand_time.h"

static const char FIRMWARE[] = "wand-sense-20261029c";
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

enum Transport : uint8_t { NONE = 0, USB_LINK = 1, BLE_LINK = 2 };
static Transport session = NONE;
static uint32_t hostAt = 0, offlineSince = 0, lastFrameAt = 0, lastBatteryAt = 0, sequence = 0;
static bool stateDirty = false, sleepRequested = false, localDark = false; // sleepRequested: host Z only.
static uint8_t chordPhase = 0;                     // Local all-three warning when no host owns the board.
static uint32_t chordAt = 0;
static bool wokeFromOff = false;
static char usbLine[48], bleLine[48];
static uint8_t usbLength = 0, bleLength = 0;
static uint8_t light[3] = {0, 0, 0};
static bool lightKnown = false;
static uint32_t batteryMv = 0;
static bool charging = false;
static const uint8_t CHARGE_STATUS = 23;           // Original Sense: active-low charger status, P0.17.

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

// ---------- Sensor ----------
static void setIMUMode(uint8_t mode) {
  if (!imuReady || mode == imuMode) return;
  imuMode = mode; lowRateCount = 0;
  // Data-ready on INT1: gyro in mode 2, accelerometer in mode 1.
  imu.writeRegister(0x0D, mode == 2 ? 0x02 : mode == 1 ? 0x01 : 0x00);
  imu.writeRegister(0x11, mode == 2 ? activeG : 0x00);                               // CTRL2_G
  imu.writeRegister(0x10, mode == 2 ? activeXL : mode == 1 ? uint8_t((activeXL & 0x0F) | 0x10) : 0x00); // CTRL1_XL, 12.5 Hz when low
}

// ---------- Output ----------
static bool writeTo(Transport t, const char *text, int n) {
  if (n <= 0) return false;
  if (t == USB_LINK) {
    if (!Serial || Serial.availableForWrite() < n) return false; // Never block motion on a full USB buffer.
    return Serial.write((const uint8_t *)text, n) == size_t(n);
  }
  if (t == BLE_LINK) {
    if (!Bluefruit.connected() || !uart.notifyEnabled()) return false;
    return uart.write((const uint8_t *)text, n) == size_t(n);
  }
  return false;
}
static bool sendFrame(uint32_t us, bool hasAccel, bool hasGyro, const int16_t *v) {
  if (session == NONE) return false;
  char frame[128];
  const int n = snprintf(frame, sizeof(frame), "\nS%lu,%lu,%u,%lu,%lu,%lu,%u,%d,%d,%d,%d,%d,%d\n",
    (unsigned long)(sequence + 1), (unsigned long)us, buttonMask(),
    (unsigned long)buttons[0].presses, (unsigned long)buttons[1].presses, (unsigned long)buttons[2].presses,
    (hasAccel ? 1 : 0) | (hasGyro ? 2 : 0),
    hasAccel ? v[3] : 0, hasAccel ? v[4] : 0, hasAccel ? v[5] : 0, hasGyro ? v[0] : 0, hasGyro ? v[1] : 0, hasGyro ? v[2] : 0);
  if (!writeTo(session, frame, n)) return false;
  ++sequence; lastFrameAt = millis();
  return true;
}
static void sendIdentity(Transport t) {
  char text[512];
  const int n = snprintf(text, sizeof(text),
    "\nI{\"protocol\":\"wand-sense-1\",\"firmware\":\"%s\",\"id\":\"%08lx%08lx\",\"imu\":%s,\"gyroDpsPerLsb\":0.00875,\"accelGPerLsb\":0.000122,\"odr\":104,\"wake\":%s}\n",
    FIRMWARE, (unsigned long)NRF_FICR->DEVICEID[1], (unsigned long)NRF_FICR->DEVICEID[0], imuReady ? "true" : "false", wokeFromOff ? "true" : "false");
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
  Bluefruit.Advertising.stop();
  for (auto &b : buttons) nrf_gpio_cfg_sense_input(g_ADigitalPinMap[b.pin], NRF_GPIO_PIN_PULLUP, NRF_GPIO_PIN_SENSE_LOW);
  delay(5);
  sd_power_system_off();
  NRF_POWER->SYSTEMOFF = 1; // SoftDevice absent fallback.
  while (true) {}
}

static void endSession() {
  if (session == NONE) return;
  session = NONE; offlineSince = millis(); localDark = false; chordPhase = 0;
  setIMUMode(0);
  setLight(ORANGE[0], ORANGE[1], ORANGE[2]); // Disconnected orange, as on the Puck.
}

static int hexValue(char c) { return c >= '0' && c <= '9' ? c - '0' : c >= 'a' && c <= 'f' ? c - 'a' + 10 : c >= 'A' && c <= 'F' ? c - 'A' + 10 : -1; }
static void command(const char *line, uint8_t length, Transport from) {
  if (!length) return;
  const char c = line[0];
  if (c == '?') { sendIdentity(from); if (session == from) sendBattery(); return; }
  if (c == 'X') { if (session == from) endSession(); return; }
  if (c != 'H' && c != 'L' && c != 'M' && c != 'Z') return;
  if (session != from) {
    // A new host session: current state only, never queued edges or old motion.
    session = from; stateDirty = true; chordPhase = 0; localDark = false;
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
  BLEConnection *connection = Bluefruit.Connection(handle);
  if (!connection) return;
  connection->requestPHY();
  connection->requestDataLengthUpdate();
  connection->requestMtuExchange(247);
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

  imu.settings.gyroRange = 245;     // The Puck's own 245 deg/s scale.
  imu.settings.accelRange = 4;      // The Puck's own 4 g scale.
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
  offlineSince = millis();
  readBattery(); lastBatteryAt = millis();
}

void loop() {
  // Wake on sensor data-ready or within 5 ms for buttons and commands.
  ulTaskNotifyTake(pdTRUE, pdMS_TO_TICKS(5));
  uint32_t now = millis();
  for (auto &b : buttons) if (b.update(now)) stateDirty = true;
  readCommands();
  if (bleReady && uartStatus == 0 && advDataReady && !Bluefruit.connected() && !Bluefruit.Advertising.isRunning() && wandElapsed(millis(), lastAdvRetry) >= 1000) {
    lastAdvRetry = millis(); advReady = Bluefruit.Advertising.start(0);
  }
  // Commands refresh hostAt using millis(). Compare only against a later
  // reading; unsigned subtraction from an earlier tick looks five weeks old.
  now = millis();

  if (session != NONE) {
    const bool linkUp = session == USB_LINK ? bool(Serial) : (Bluefruit.connected() && uart.notifyEnabled());
    if (!linkUp || wandElapsed(now, hostAt) > HOST_TIMEOUT_MS) endSession();
  }

  // endSession() above can also advance offlineSince by a tick.
  now = millis();
  bool sent = false;
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
        if (publish && sendFrame(us, true, imuMode == 2, v)) { sent = true; stateDirty = false; }
      }
    }
  }
  if (session != NONE && !sent && (stateDirty || wandElapsed(now, lastFrameAt) >= HEARTBEAT_FRAME_MS)) {
    if (sendFrame(micros(), false, false, nullptr)) stateDirty = false;
  }
  if (wandElapsed(now, lastBatteryAt) >= 10000) { lastBatteryAt = now; readBattery(); if (session != NONE) sendBattery(); }

  if (session == NONE) {
    // The Puck power policy's offline behaviour, kept on the board itself.
    // Any grip edge re-arms the offline timers and shows the disconnected light again.
    if (stateDirty) { stateDirty = false; offlineSince = now; if (localDark && !chordPhase) { localDark = false; setLight(ORANGE[0], ORANGE[1], ORANGE[2]); } }
    if (!chordPhase && buttonMask() == 7) { chordPhase = 1; chordAt = now; }
    if (chordPhase) {
      // All three: flash every colour twice (100 ms steps), then sleep once released.
      const uint8_t step = uint8_t((now - chordAt) / 100);
      if (step < 4) { const uint8_t v = step & 1 ? 0 : 255; setLight(v, v, v); }
    } else if (!localDark && wandElapsed(now, offlineSince) >= OFFLINE_DARK_MS && !anyPhysical()) { localDark = true; setLight(0, 0, 0); }
  }
  const bool localSleep = session == NONE && ((chordPhase && wandElapsed(now, chordAt) >= 400) || wandElapsed(now, offlineSince) >= OFFLINE_SLEEP_MS);
  // Sleep waits for every grip button to be released so a held chord cannot wake it at once.
  if ((sleepRequested || localSleep) && !anyPhysical()) powerOff();
}
