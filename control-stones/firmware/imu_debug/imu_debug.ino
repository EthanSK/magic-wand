#include <Adafruit_TinyUSB.h>
#include <LSM6DS3.h>
#include <Wire.h>
#include <bluefruit.h>
#include "sense_power.h"
#include "finger_sensors.h"

// Control Stones: the Sense's built-in hand sensor, not the external finger gyros.
LSM6DS3 handIMU(I2C_MODE, 0x6A);
bool ready = false;
uint32_t lastSample = 0;
uint32_t lastBattery = 0;
float batteryVoltage = 0;
uint32_t lastHealth = 0, lastBluetooth = 0, bluetoothDrops = 0;
constexpr int FRAME_SIZE = 512;
BLEUart sensorUart;
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
    "{\"sensor\":\"health\",\"firmware\":\"cs-recovery-20261026\",\"ms\":%lu,\"finger_state\":[%u,%u,%u,%u,%u],\"finger_restarts\":[%lu,%lu,%lu,%lu,%lu],\"i2c_timeouts\":%lu,\"ble_drops\":%lu}\n",
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
}

void loop() {
  SensePower::waitAndUpdate(handIMU, Fingers::any());
  lastSample = millis();
  static char frame[FRAME_SIZE];
  // Sample and stream USB at the original rate; bound the five-finger radio load.
  const bool publishBluetooth = uint32_t(lastSample - lastBluetooth) >= 50;
  if (publishBluetooth) lastBluetooth = lastSample;
  Fingers::rescan();
  for (uint8_t i = 0; i < 5; ++i) {
    float axes[6];
    if (!Fingers::sample(i, axes)) continue;
    int n = snprintf(frame, sizeof(frame),
      "{\"sensor\":\"finger\",\"channel\":%u,\"finger\":\"%s\",\"address\":%u,\"ms\":%lu,\"gx\":%.3f,\"gy\":%.3f,\"gz\":%.3f,\"ax\":%.4f,\"ay\":%.4f,\"az\":%.4f}\n",
      Fingers::CHANNELS[i], Fingers::NAMES[i], Fingers::addresses[i], (unsigned long)millis(),
      axes[0], axes[1], axes[2], axes[3], axes[4], axes[5]);
    emit(frame, n, publishBluetooth);
  }
  reportHealth(frame);
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
  uint8_t available = 0;
  if (!SensePower::idle && (handIMU.readRegister(&available, 0x1E) != IMU_SUCCESS || !(available & 0x02))) return;
  int length = snprintf(frame, sizeof(frame),
    "{\"sensor\":\"hand\",\"ms\":%lu,\"ax\":%.4f,\"ay\":%.4f,\"az\":%.4f,\"gx\":%.3f,\"gy\":%.3f,\"gz\":%.3f,\"battery_v\":%.3f,\"charging\":%s,\"idle\":%s,\"sleep_ready\":%s,\"i2c_timeouts\":%lu}\n",
    (unsigned long)lastSample, handIMU.readFloatAccelX(), handIMU.readFloatAccelY(),
    handIMU.readFloatAccelZ(), SensePower::idle ? 0 : handIMU.readFloatGyroX(), SensePower::idle ? 0 : handIMU.readFloatGyroY(),
    SensePower::idle ? 0 : handIMU.readFloatGyroZ(), batteryVoltage, digitalRead(CHARGE_STATUS) == LOW ? "true" : "false",
    SensePower::idle ? "true" : "false", SensePower::enabled ? "true" : "false", (unsigned long)ExternalBus::timeouts);
  emit(frame, length, publishBluetooth);
}
