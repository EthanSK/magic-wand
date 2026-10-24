#include "timed_i2c.h"
#include <iostream>
int main(){
 uint8_t byte=4,data[12]={};
 ExternalBus::begin();
 assert(ExternalBus::write(0x70,&byte,1));
 assert(ExternalBus::read(0x69,0x0c,data,12));
 // An error may already have stopped the peripheral; retain that event.
 mode=2;assert(!ExternalBus::write(0x70,&byte,1));assert(ExternalBus::timeouts==0);
 mode=1;stuck=true;auto start=ticks;auto before=begins;
 assert(!ExternalBus::write(0x70,&byte,1));
 assert(ExternalBus::timeouts==1);assert(begins==before+1);assert(ticks-start<100);
 mode=0;stuck=false;assert(ExternalBus::write(0x70,&byte,1));
 assert(ExternalBus::read(0x69,0x0c,data,12));
 mode=3;start=ticks;
 assert(!ExternalBus::read(0x69,0x0c,data,12));
 assert(ExternalBus::timeouts==2);assert(ticks-start<100);
 mode=0;assert(ExternalBus::read(0x69,0x0c,data,12));
 std::cout<<"Success, repeated-start read, NACK, stuck bus deadlines and recovery passed\n";
}
