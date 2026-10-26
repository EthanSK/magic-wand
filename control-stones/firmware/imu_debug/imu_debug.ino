#include <Adafruit_TinyUSB.h>
#include <LSM6DS3.h>
#include <Wire.h>
#include <bluefruit.h>
#include "sense_power.h"
#include "finger_sensors.h"
#include "motion_idle.h"

// Control Stones: the Sense's built-in hand sensor, not the external finger gyros.
LSM6DS3 handIMU(I2C_MODE, 0x6A);
bool ready = false;
uint32_t lastSample = 0;
uint32_t lastBattery = 0;
float batteryVoltage = 0;
uint32_t lastHealth = 0, lastBluetooth = 0, bluetoothDrops = 0;
constexpr int FRAME_SIZE = 512;
BLEUart sensorUart;
MotionIdle motionIdle;
// Original Sense variant: D23 is the active-low charger status on P0.17.
constexpr uint8_t CHARGE_STATUS = 23;
void emit(const char *frame, int length, bool wireless = true) {
  if (length <= 0 || length >= FRAME_SIZE) return;
  if (Serial) Serial.write((const uint8_t*)frame, length);
  if (wireless && Bluefruit.connected() && sensorUart.notifyEnabled()) {
    // Recover framing if an earlier multi-notification write sent only a prefix.
    static char radio[FRAME_SIZE + 1];
    radio[0] = '\n';
    memcpy(radio + 1, frame, length);
    if (sensorUart.write((const uint8_t*)radio, length + 1) != size_t(length + 1)) ++bluetoothDrops;
  }
}

void reportHealth(char *frame) {
  if (uint32_t(millis() - lastHealth) < 1000) return;
  lastHealth = millis();
  int n = snprintf(frame, FRAME_SIZE,
    "{\"sensor\":\"health\",\"firmware\":\"cs-assembly-sleep-20261026\",\"ms\":%lu,\"finger_state\":[%u,%u,%u,%u,%u],\"finger_restarts\":[%lu,%lu,%lu,%lu,%lu],\"i2c_timeouts\":%lu,\"ble_drops\":%lu}\n",
    (unsigned long)lastHealth,
    Fingers::health[0], Fingers::health[1], Fingers::health[2], Fingers::health[3], Fingers::health[4],
    (unsigned long)Fingers::restarts[0], (unsigned long)Fingers::restarts[1], (unsigned long)Fingers::restarts[2],
    (unsigned long)Fingers::restarts[3], (unsigned long)Fingers::restarts[4],
    (unsigned long)ExternalBus::timeouts, (unsigned long)bluetoothDrops);
  emit(frame, n);
}

void setup() {
  Serial.begin(115200);
  pinMode(VBAT_ENABLE, OUTPUT);
  digitalWrite(VBAT_ENABLE, LOW);
  pinMode(CHARGE_STATUS, INPUT_PULLUP);
  analogReference(AR_INTERNAL_3_0);
  analogReadResolution(12);
  handIMU.settings.accelRange = 4;
  ready = handIMU.begin() == 0;
  if (ready) SensePower::begin(handIMU);
  Bluefruit.autoConnLed(false);
  Bluefruit.configPrphBandwidth(BANDWIDTH_MAX);
  Bluefruit.begin();
  Bluefruit.setName("Control Stones");
  sensorUart.begin();
  Bluefruit.Advertising.addFlags(BLE_GAP_ADV_FLAGS_LE_ONLY_GENERAL_DISC_MODE);
  Bluefruit.Advertising.addService(sensorUart);
  Bluefruit.ScanResponse.addName();
  Bluefruit.Advertising.restartOnDisconnect(true);
  Bluefruit.Advertising.setInterval(32, 244);
  Bluefruit.Advertising.start(0);
  Fingers::begin();
  motionIdle.restart(millis());
}

void loop() {
  const bool wakeInterrupt = SensePower::waitAndUpdate(handIMU,
    SensePower::idle ? MotionIdle::IDLE_POLL_MS : 20);
  lastSample = millis();
  static char frame[FRAME_SIZE];
  static float fingerAxes[5][6] = {}, handAxes[6] = {};
  static uint32_t fingerTime[5] = {}, handTime = 0;
  bool fingerReady[5] = {}, handReady = false, moved = wakeInterrupt && SensePower::idle;
  Fingers::rescan();
  for (uint8_t i = 0; i < 5; ++i) {
    fingerReady[i] = Fingers::sample(i, fingerAxes[i]);
    if (fingerReady[i]) {
      fingerTime[i] = millis();
      moved |= motionIdle.observe(i + 1, fingerAxes[i], !Fingers::idle, fingerTime[i]);
    }
  }
  uint8_t available = 0;
  const uint8_t handMask = SensePower::idle ? 0x01 : 0x03;
  if (ready && handIMU.readRegister(&available, 0x1E) == IMU_SUCCESS && (available & handMask) == handMask) {
    handAxes[0] = SensePower::idle ? 0 : handIMU.readFloatGyroX();
    handAxes[1] = SensePower::idle ? 0 : handIMU.readFloatGyroY();
    handAxes[2] = SensePower::idle ? 0 : handIMU.readFloatGyroZ();
    handAxes[3] = handIMU.readFloatAccelX();
    handAxes[4] = handIMU.readFloatAccelY();
    handAxes[5] = handIMU.readFloatAccelZ();
    handReady = true;
    handTime = millis();
    moved |= motionIdle.observe(0, handAxes, !SensePower::idle, handTime);
  }
  if (moved) motionIdle.restart(millis());
  const bool wantIdle = SensePower::enabled && motionIdle.shouldSleep(millis());
  if (wantIdle != SensePower::idle) {
    const bool changed = SensePower::setIdle(handIMU, wantIdle);
    Fingers::setIdle(changed && wantIdle);
    if (!wantIdle) motionIdle.restart(millis());
    // The batch mode switch waits for BMI160 gyro startup. Drop pre-switch
    // readings, including stale gyro output, and collect fresh values next loop.
    memset(fingerTime, 0, sizeof(fingerTime));
    handTime = 0;
    lastBluetooth = millis() - 1000;
    return;
  }
  // Keep the connection alive, but send only one snapshot/second while resting.
  // The accelerometers still watch at 12.5 Hz independently of this radio rate.
  const bool publishBluetooth = uint32_t(lastSample - lastBluetooth) >= (SensePower::idle ? 1000 : 50);
  if (publishBluetooth) lastBluetooth = lastSample;
  reportHealth(frame);
  if (SensePower::idle && !publishBluetooth) return;
  for (uint8_t i = 0; i < 5; ++i) {
    if (!Fingers::addresses[i] || (!fingerReady[i] &&
        !(SensePower::idle && fingerTime[i] && uint32_t(millis() - fingerTime[i]) < 250))) continue;
    const float *axes = fingerAxes[i];
    int n = snprintf(frame, sizeof(frame),
      "{\"sensor\":\"finger\",\"channel\":%u,\"finger\":\"%s\",\"address\":%u,\"ms\":%lu,\"gx\":%.3f,\"gy\":%.3f,\"gz\":%.3f,\"ax\":%.4f,\"ay\":%.4f,\"az\":%.4f,\"idle\":%s,\"sleep_ready\":true}\n",
      Fingers::CHANNELS[i], Fingers::NAMES[i], Fingers::addresses[i], (unsigned long)fingerTime[i],
      axes[0], axes[1], axes[2], axes[3], axes[4], axes[5], Fingers::idle ? "true" : "false");
    emit(frame, n, publishBluetooth);
  }
  if (!ready) {
    Serial.println("{\"error\":\"Built-in sensor not found\"}");
    delay(1000);
    return;
  }
  if (!batteryVoltage || millis() - lastBattery >= 1000) {
    lastBattery = millis();
    uint32_t total = 0;
    for (int i = 0; i < 8; ++i) total += analogRead(PIN_VBAT);
    // Original Sense's 1 MΩ / 510 kΩ divider and the selected 3.0 V reference.
    batteryVoltage = (total / 8.0f) * (3.0f / 4096.0f) * (1510.0f / 510.0f);
  }
  if (!handReady && !(SensePower::idle && handTime && uint32_t(millis() - handTime) < 250)) return;
  int length = snprintf(frame, sizeof(frame),
    "{\"sensor\":\"hand\",\"ms\":%lu,\"ax\":%.4f,\"ay\":%.4f,\"az\":%.4f,\"gx\":%.3f,\"gy\":%.3f,\"gz\":%.3f,\"battery_v\":%.3f,\"charging\":%s,\"idle\":%s,\"sleep_ready\":%s,\"i2c_timeouts\":%lu}\n",
    (unsigned long)handTime, handAxes[3], handAxes[4], handAxes[5], handAxes[0], handAxes[1],
    handAxes[2], batteryVoltage, digitalRead(CHARGE_STATUS) == LOW ? "true" : "false",
    SensePower::idle ? "true" : "false", SensePower::enabled ? "true" : "false", (unsigned long)ExternalBus::timeouts);
  emit(frame, length, publishBluetooth);
}
