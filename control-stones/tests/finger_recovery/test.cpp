#include <cstdint>
#include <cstring>
#include <cassert>
#include <iostream>
static uint32_t now=0;
uint32_t millis(){return now;}
void delay(uint32_t ms){now+=ms;}
namespace FakeBus {
struct Sensor {bool present=true,ready=true;uint8_t regs[256]={};unsigned resets=0;};
Sensor sensors[8];uint8_t selected=0;unsigned selections=0;
void begin(){}
bool write(uint8_t address,const uint8_t* data,uint8_t count){
 if(address==0x70&&count==1){selected=data[0];++selections;return true;}
 if(address!=0x69||count!=2||!selected)return false;
 unsigned channel=0;while(!(selected&(1u<<channel)))++channel;
 auto& s=sensors[channel];if(!s.present)return false;
 const auto reg=data[0],value=data[1];
 if(reg==0x7e&&value==0xb6){std::memset(s.regs,0,256);s.ready=true;++s.resets;}
 else if(reg==0x7e&&value==0x11)s.regs[3]=(s.regs[3]&~0x30)|0x10;
 else if(reg==0x7e&&value==0x15)s.regs[3]=(s.regs[3]&~0x0c)|0x04;
 else s.regs[reg]=value;
 return true;
}
bool read(uint8_t address,uint8_t reg,uint8_t* data,uint8_t count){
 if(address!=0x69||!selected)return false;
 unsigned channel=0;while(!(selected&(1u<<channel)))++channel;
 auto& s=sensors[channel];if(!s.present)return false;
 if(reg==0&&count==1){*data=0xd1;return true;}
 if(reg==0x1b&&count==1){*data=s.ready?0xc0:0;return true;}
 if(reg==0x0c&&count==12){std::memset(data,0,12);data[9]=0x20;return true;}
 std::memcpy(data,s.regs+reg,count);return true;
}
}
#define CONTROL_STONES_FINGER_BUS FakeBus
#include "finger_sensors.h"
int main(){
 Fingers::begin();float axes[6];
 assert(Fingers::sample(4,axes));assert(Fingers::sample(0,axes));
 const auto thumbResets=FakeBus::sensors[2].resets;
 const auto littleResets=FakeBus::sensors[6].resets;
 // The sensor still acknowledges I2C but lost its sampling configuration.
 FakeBus::sensors[6].ready=false;
 unsigned thumbSamples=0,littleSamples=0;
 for(unsigned i=0;i<250;++i){
  now+=20;Fingers::rescan();
  if(Fingers::sample(0,axes))++thumbSamples;
  if(Fingers::sample(4,axes))++littleSamples;
 }
 assert(littleSamples>0&&"sensor with no ready data never recovered");
 assert(FakeBus::sensors[6].resets>littleResets);
 assert(thumbSamples==250&&"one stale finger interrupted the healthy thumb");
 assert(FakeBus::sensors[2].resets==thumbResets);
 assert(FakeBus::selected==0&&"sensor channel left connected between reads");
 // An absent sensor can return without rebooting the board.
 FakeBus::sensors[6].present=false;assert(!Fingers::sample(4,axes));
 FakeBus::sensors[6].present=true;littleSamples=0;
 for(unsigned i=0;i<150;++i){now+=20;Fingers::rescan();if(Fingers::sample(4,axes))++littleSamples;}
 assert(littleSamples>0);
 std::cout<<"Stale sensor reinitialises, healthy sensor continues, mux isolates channels, and reconnect recovers\n";
}
