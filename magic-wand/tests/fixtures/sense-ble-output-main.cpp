#include "wand_ble_output.h"
#include <cassert>
#include <algorithm>
#include <iostream>
#include <string>
#include <vector>
struct Link {
  uint16_t att=247;
  uint32_t time=0,advance=0;
  int calls=0,disconnectAt=0,failAt=0,shortAt=0,shrinkAt=0,generationAt=0;
  uint32_t generation=1,expectedGeneration=1;
  bool connected=true;
  std::string bytes;
  std::vector<size_t> requested;
  uint32_t now() const {return time;}
  bool valid() const {return connected && generation==expectedGeneration;}
  uint16_t mtu() const {return att;}
  size_t write(const uint8_t *data,size_t n) {
    ++calls;requested.push_back(n);time+=advance;
    if(calls==failAt)return 0;
    size_t accepted=std::min(n,size_t(247)); // Bluefruit's silent characteristic clamp.
    if(calls==shortAt)accepted=n-1;
    bytes.append(reinterpret_cast<const char*>(data),accepted);
    if(calls==disconnectAt)connected=false;
    if(calls==generationAt)++generation;
    if(calls==shrinkAt)att=23;
    return calls==shortAt?accepted:n; // Original BLEUart reports requested n even when clamped.
  }
};
static bool send(Link &l,const std::string &s){return WandBleOutput::write(l,reinterpret_cast<const uint8_t*>(s.data()),s.size());}
int main(){
  const std::string identity="\nI{\"protocol\":\"wand-sense-1\",\"firmware\":\"wand-sense-7\",\"padding\":\""+std::string(320,'x')+"\"}\n";
  assert(identity.size()>247 && identity.size()<512);
  Link old;assert(old.write(reinterpret_cast<const uint8_t*>(identity.data()),identity.size())==identity.size());assert(old.bytes.size()==247 && old.bytes.back()!='\n');
  for(uint16_t mtu:{23,64,247,512}) {
    Link l;l.att=mtu;assert(send(l,identity));assert(l.bytes==identity && l.bytes.back()=='\n');
    for(auto n:l.requested)assert(n<=size_t(std::min<uint16_t>(mtu,247)-3));
    const std::string sensor="\nS1,100,0,0,0,0,3,1,2,3,4,5,6,1,100\n";
    assert(send(l,sensor));assert(l.bytes==identity+sensor); // Complete ordered lines; no sensor interleaving.
  }
  Link shrinking;shrinking.shrinkAt=1;assert(send(shrinking,identity));assert(shrinking.bytes==identity);
  for(size_t i=1;i<shrinking.requested.size();++i)assert(shrinking.requested[i]<=20);
  Link failed;failed.failAt=2;assert(!send(failed,identity) && failed.calls==2);
  Link partial;partial.shortAt=1;assert(!send(partial,identity) && partial.calls==1);
  Link gone;gone.disconnectAt=1;assert(!send(gone,identity) && gone.calls==1); // Generation change uses this same validity gate.
  Link replaced;replaced.generationAt=1;assert(!send(replaced,identity) && replaced.calls==1);
  Link stalled;stalled.att=23;stalled.advance=100;assert(!send(stalled,identity) && stalled.calls==10 && stalled.time==1000);
  Link wrap;wrap.time=0xfffffff0;wrap.advance=10;assert(send(wrap,identity));assert(wrap.bytes==identity);
  Link absent;absent.connected=false;assert(!send(absent,identity) && absent.calls==0);
  Link invalid;invalid.att=22;assert(!send(invalid,identity) && invalid.calls==0);
  Link large;assert(!send(large,std::string(513,'x')) && large.calls==0);
  Link empty;assert(!send(empty,"") && empty.calls==0);
  std::cout<<"PASS actual header: silent-clamp reproduction, MTU23/64/247/512, identity newline, ordered sensor/control bytes, MTU shrink, disconnect, same-handle generation change, short write, failure, deadline, clock wrap, bounds\n";
}
