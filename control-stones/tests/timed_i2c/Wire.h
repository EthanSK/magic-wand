#pragma once
#include <cstdint>
#include <cstring>
#include <cassert>
constexpr int PIN_WIRE_SDA=4,PIN_WIRE_SCL=5,INPUT_PULLUP=1,OUTPUT=2,LOW=0;
struct Dma {uint32_t PTR=0,MAXCNT=0,AMOUNT=0;};
struct Registers {volatile uint32_t EVENTS_ERROR=0,EVENTS_STOPPED=0,EVENTS_SUSPENDED=0,EVENTS_LASTTX=0,EVENTS_TXSTARTED=0,EVENTS_LASTRX=0,EVENTS_RXSTARTED=0; uint32_t SHORTS=0,INTENCLR=0,ERRORSRC=0,ENABLE=0,ADDRESS=0,TASKS_STOP=0,TASKS_SUSPEND=0,TASKS_RESUME=0,TASKS_STARTTX=0,TASKS_STARTRX=0; Dma TXD,RXD;};
inline Registers peripheral;
#define NRF_TWIM0 (&peripheral)
inline unsigned begins=0,ticks=0;inline int mode=0;inline bool stuck=false,autoStopped=false;
inline uint32_t micros(){return ticks++*1000;}
inline void pinMode(int,int){}
inline void digitalWrite(int,int value){assert(value==LOW);}
inline int digitalRead(int){return stuck?0:1;}
inline void delayMicroseconds(int){}
inline void __DMB(){}
struct WireType {void begin(){++begins;peripheral=Registers{};autoStopped=false;} void setClock(int){};};
inline WireType Wire;
inline void taskYIELD(){
 if(mode==1)return;
 if(peripheral.TASKS_STARTTX){peripheral.TASKS_STARTTX=0;autoStopped=false;if(mode==2){peripheral.EVENTS_ERROR=1;peripheral.EVENTS_STOPPED=1;autoStopped=true;}else{peripheral.TXD.AMOUNT=peripheral.TXD.MAXCNT;peripheral.EVENTS_LASTTX=1;}}
 if(peripheral.TASKS_STARTRX&&mode!=3){peripheral.TASKS_STARTRX=0;peripheral.RXD.AMOUNT=peripheral.RXD.MAXCNT;peripheral.EVENTS_LASTRX=1;}
 if(peripheral.TASKS_STOP&&!autoStopped){peripheral.TASKS_STOP=0;peripheral.EVENTS_STOPPED=1;}
 if(peripheral.TASKS_SUSPEND){peripheral.TASKS_SUSPEND=0;peripheral.EVENTS_SUSPENDED=1;}
}
