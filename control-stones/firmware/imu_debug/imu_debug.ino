#include <Adafruit_TinyUSB.h>
#include <LSM6DS3.h>
#include <Wire.h>
#include <bluefruit.h>
#include "sense_power.h"

// Control Stones: the Sense's built-in hand sensor, not the external finger gyros.
LSM6DS3 handIMU(I2C_MODE, 0x6A);
bool ready = false;
uint32_t lastSample = 0;
uint32_t lastBattery = 0;
float batteryVoltage = 0;
BLEUart sensorUart;
// Original Sense variant: D23 is the active-low charger status on P0.17.
constexpr uint8_t CHARGE_STATUS = 23;

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
}

void loop() {
  SensePower::waitAndUpdate(handIMU);
  lastSample = millis();
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
  char frame[256];
  int length = snprintf(frame, sizeof(frame),
    "{\"ms\":%lu,\"ax\":%.4f,\"ay\":%.4f,\"az\":%.4f,\"gx\":%.3f,\"gy\":%.3f,\"gz\":%.3f,\"battery_v\":%.3f,\"charging\":%s,\"idle\":%s,\"sleep_ready\":%s}\n",
    (unsigned long)lastSample, handIMU.readFloatAccelX(), handIMU.readFloatAccelY(),
    handIMU.readFloatAccelZ(), SensePower::idle ? 0 : handIMU.readFloatGyroX(), SensePower::idle ? 0 : handIMU.readFloatGyroY(),
    SensePower::idle ? 0 : handIMU.readFloatGyroZ(), batteryVoltage, digitalRead(CHARGE_STATUS) == LOW ? "true" : "false",
    SensePower::idle ? "true" : "false", SensePower::enabled ? "true" : "false");
  if (length <= 0 || length >= (int)sizeof(frame)) return;
  if (Serial) Serial.write((uint8_t*)frame, length);
  if (Bluefruit.connected() && sensorUart.notifyEnabled()) sensorUart.write((uint8_t*)frame, length);
}
