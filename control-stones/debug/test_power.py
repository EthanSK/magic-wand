"""Check the real internal-IMU mode writes, restoration and failure handling."""
import shutil
import subprocess
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


class PowerTests(unittest.TestCase):
    @unittest.skipUnless(shutil.which("c++"), "Host C++ compiler is unavailable")
    def test_internal_mode_transition_and_failed_readback(self):
        source = r'''
#include <cstdint>
#include <cassert>
using TaskHandle_t = void*;
using BaseType_t = int;
#define pdFALSE 0
#define pdTRUE 1
#define portYIELD_FROM_ISR(x) ((void)x)
#define pdMS_TO_TICKS(x) (x)
#define INPUT 0
#define RISING 1
#define PIN_LSM6DS3TR_C_INT1 11
#define IMU_SUCCESS 0
void* xTaskGetCurrentTaskHandle(){return nullptr;}
void vTaskNotifyGiveFromISR(void*,int*){}
unsigned waited=0;
void ulTaskNotifyTake(int,unsigned ms){waited=ms;}
void pinMode(int,int){}
int digitalPinToInterrupt(int x){return x;}
void attachInterrupt(int,void(*)(),int){}
class LSM6DS3 {
public:
  uint8_t regs[256]={}; bool rejectSleep=false;
  int writeRegister(uint8_t r,uint8_t v){if(rejectSleep&&r==0x13&&(v&0x40))return 1;regs[r]=v;return 0;}
  int readRegister(uint8_t* v,uint8_t r){*v=regs[r];return 0;}
};
#include "sense_power.h"
int main(){
  LSM6DS3 imu;imu.regs[0x10]=0x68;imu.regs[0x13]=0x04;imu.regs[0x15]=0x01;
  assert(SensePower::begin(imu));
  assert(imu.regs[0x58]==0x80); // No independent hand-only inactivity.
  assert(imu.regs[0x5e]==0x20); // Hardware wake interrupt still enabled.
  assert(SensePower::setIdle(imu,true));
  assert(SensePower::idle&&imu.regs[0x10]==0x18&&imu.regs[0x13]==0x44&&imu.regs[0x15]==0x11);
  imu.regs[0x1b]=0x08;assert(SensePower::waitAndUpdate(imu,80));assert(waited==80);
  assert(SensePower::setIdle(imu,false));
  assert(!SensePower::idle&&imu.regs[0x10]==0x68&&imu.regs[0x13]==0x04&&imu.regs[0x15]==0x01);
  imu.rejectSleep=true;
  assert(!SensePower::setIdle(imu,true));
  assert(!SensePower::idle&&!SensePower::enabled);
  assert(imu.regs[0x10]==0x68&&imu.regs[0x13]==0x04&&imu.regs[0x15]==0x01);
}
'''
        with tempfile.TemporaryDirectory(prefix="stones-power-") as directory:
            folder = Path(directory)
            for name in ("LSM6DS3.h", "FreeRTOS.h", "task.h"):
                (folder / name).write_text("")
            (folder / "test.cpp").write_text(source)
            built = subprocess.run(
                ["c++", "-std=c++11", "-I" + directory, "-I" + str(ROOT / "firmware/imu_debug"),
                 str(folder / "test.cpp"), "-o", str(folder / "test")],
                capture_output=True, text=True)
            self.assertEqual(built.returncode, 0, built.stderr)
            result = subprocess.run([str(folder / "test")], capture_output=True, text=True, timeout=5)
            self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
