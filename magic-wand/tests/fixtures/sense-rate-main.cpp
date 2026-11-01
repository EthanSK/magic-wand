#include <cassert>
#include <cstdint>
#include <cstring>
#include "WandSampleRate.h"
const int IMU_SUCCESS=0;
struct FakeIMU {uint8_t r[256]{}; bool refuse=false; int readRegister(uint8_t*p,int a){*p=r[a];return 0;} int writeRegister(int a,uint8_t v){if(!(refuse && a==0x11))r[a]=v;return 0;}} imu;
bool imuReady=true;uint8_t imuMode=0xff,activeXL=0x48,activeG=0x44,lowRateCount=0;uint16_t activeRateHz=104;int clears=0;void clearMerged(){++clears;}
/*LIVE_RATE_FUNCTIONS*/
int main(){
 WandSampleRate r{}; const uint32_t hz[]={104,208,416,833,1660,3330,6660};
 for(int i=0;i<7;i++){assert(wandSampleRate(hz[i],r));assert(r.hz==hz[i]);assert(r.odrBits==uint8_t((i+4)<<4));}
 const char*bad[]={"R0","R0104","R999","R66600","R104x","r104","R-104","R104\n","R",""};
 for(auto p:bad)assert(!wandSampleRateCommand(p,strlen(p),r));
 assert(wandSampleRateCommand("R6660",5,r));
 for(uint8_t mode=0;mode<3;mode++){activeG=0x44;activeXL=0x48;imuMode=0xff;setIMUMode(mode);assert(configureSampleRate(r));assert(activeRateHz==6660);assert(activeG==0xa4 && activeXL==0xa8);assert(imuMode==mode);assert(imu.r[0x11]==(mode==2?0xa4:0));assert(imu.r[0x10]==(mode==2?0xa8:mode==1?0x18:0));}
 assert(wandSampleRate(104,r));assert(configureSampleRate(r));assert(activeG==0x44 && activeXL==0x48);
 imu.r[0x16]=0x80;assert(wandSampleRate(6660,r));assert(!configureSampleRate(r));assert(activeRateHz==104);imu.r[0x16]=0;
 imuMode=0xff;setIMUMode(2);imu.refuse=true;assert(!configureSampleRate(r));assert(activeG==0x44 && activeXL==0x48 && activeRateHz==104);
}
