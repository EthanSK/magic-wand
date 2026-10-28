// Separate original XIAO nRF52840 Sense diagnostic sketch. Not Puck firmware.
// Seeeduino:nrf52:xiaonRF52840Sense, core 1.1.13; Seeed Arduino LSM6DS3 2.0.7.
#include <Adafruit_TinyUSB.h>
#include <LSM6DS3.h>
#include <Wire.h>
#include <bluefruit.h>
LSM6DS3 imu(I2C_MODE, 0x6A);
BLEUart uart;
bool imuReady = false;
uint32_t sequence = 0, lastUSB = 0, lastBLE = 0;
struct Button {
  uint8_t pin; bool raw, pressed; uint32_t changedAt, presses;
  void begin(uint32_t now) { pinMode(pin, INPUT_PULLUP); raw = digitalRead(pin)==LOW; pressed=raw; changedAt=now; presses=0; }
  void update(uint32_t now) {
    bool v=digitalRead(pin)==LOW;
    if(v!=raw){raw=v;changedAt=now;}
    if(raw!=pressed && uint32_t(now-changedAt)>=10){pressed=raw;if(pressed)++presses;}
  }
};
Button buttons[]={{D8,false,false,0,0},{D9,false,false,0,0},{D10,false,false,0,0}};
void setup(){
  Serial.begin(115200);
  for(auto &b:buttons)b.begin(millis());
  imu.settings.accelRange=4;
  imu.settings.gyroRange=1000;
  imuReady=imu.begin()==0;
  Bluefruit.autoConnLed(false);
  Bluefruit.configPrphBandwidth(BANDWIDTH_MAX);
  Bluefruit.begin();
  Bluefruit.setName("Magic Wand Sense");
  uart.begin();
  Bluefruit.Advertising.addFlags(BLE_GAP_ADV_FLAGS_LE_ONLY_GENERAL_DISC_MODE);
  Bluefruit.Advertising.addService(uart);
  Bluefruit.ScanResponse.addName();
  Bluefruit.Advertising.restartOnDisconnect(true);
  Bluefruit.Advertising.start(0);
}
void loop(){
  const uint32_t now=millis();
  for(auto &b:buttons)b.update(now);
  if(uint32_t(now-lastUSB)<20){delay(2);return;}
  lastUSB=now;
  char axes[200]="null";
  uint8_t available=0;
  if(imuReady && imu.readRegister(&available,0x1E)==IMU_SUCCESS && (available&3)==3){
    snprintf(axes,sizeof(axes),"{\"ax\":%.4f,\"ay\":%.4f,\"az\":%.4f,\"gx\":%.3f,\"gy\":%.3f,\"gz\":%.3f}",
      imu.readFloatAccelX(),imu.readFloatAccelY(),imu.readFloatAccelZ(),imu.readFloatGyroX(),imu.readFloatGyroY(),imu.readFloatGyroZ());
  }
  char frame[512];
  int n=snprintf(frame,sizeof(frame),"\n{\"schema\":1,\"sensor\":\"wand\",\"seq\":%lu,\"ms\":%lu,\"buttons\":{\"thumb\":%s,\"index\":%s,\"middle\":%s},\"presses\":{\"thumb\":%lu,\"index\":%lu,\"middle\":%lu},\"imu\":%s}\n",
    (unsigned long)++sequence,(unsigned long)now,
    buttons[0].pressed?"true":"false",buttons[1].pressed?"true":"false",buttons[2].pressed?"true":"false",
    (unsigned long)buttons[0].presses,(unsigned long)buttons[1].presses,(unsigned long)buttons[2].presses,axes);
  if(n>0 && n<int(sizeof(frame))){
    if(Serial)Serial.write((uint8_t*)frame,n);
    if(uint32_t(now-lastBLE)>=50 && Bluefruit.connected() && uart.notifyEnabled()){
      lastBLE=now;uart.write((uint8_t*)frame,n);
    }
  }
}
