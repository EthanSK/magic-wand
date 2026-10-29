import test from 'node:test';
import assert from 'node:assert/strict';
import fs from 'node:fs';
import {WandState,validatePacket,LineFramer,BUTTONS} from '../hardware/xiao-wand-dashboard/model.mjs';
import {openSerial,openBluetooth,UART_SERVICE,UART_TX} from '../hardware/xiao-wand-dashboard/transports.mjs';
const packet=(seq=1,ms=20)=>({schema:1,sensor:'wand',seq,ms,buttons:{thumb:false,index:false,middle:false},imu:{ax:0,ay:0,az:1,gx:2,gy:3,gz:4}});
const setup=()=>{const s=new WandState();s.connect('USB');return s;};
test('Sense dashboard pin mapping matches the wiring plan and stays separate from Puck',()=>{
 const plan=JSON.parse(fs.readFileSync(new URL('../hardware/xiao-wand-dashboard/pin-plan.json',import.meta.url)));
 assert.deepEqual(BUTTONS.map(b=>b.pin),plan.buttons.map(b=>b.board_pin));
 assert.deepEqual(BUTTONS.map(b=>[b.name,b.position,b.control,b.role,b.pin]),[['1','left','Middle','HUD','D10'],['2','centre','Bottom','Mouse','D8'],['3','right','Top','Recording','D9']]);
 assert.deepEqual(BUTTONS.map(b=>b.key),plan.buttons.map(b=>b.wire_key),'already-flashed v1 wire channels stay compatible');
 assert.equal(JSON.parse(fs.readFileSync(new URL('../wand.json',import.meta.url))).buttons[0].pin,'D30');
});
test('rejects hand/Puck packets, missing buttons, non-finite axes and malformed counters',()=>{
 for(const modify of [p=>p.sensor='hand',p=>delete p.buttons.thumb,p=>p.buttons.thumb=0,p=>p.imu.ax=NaN,p=>p.seq=-1,p=>p.imu.gx=Infinity,p=>p.presses={thumb:0,index:false,middle:0}]){const p=packet();modify(p);assert.throws(()=>validatePacket(p));}
 assert.equal(validatePacket({...packet(),imu:null}).imu,null,'button-only readings are allowed when the IMU fails');
});
test('frames split across notifications and oversized frames resynchronise at a newline',()=>{
 const out=[];let bad=0;const f=new LineFramer(p=>out.push(p),()=>++bad),line=JSON.stringify(packet())+'\n';
 f.push(line.slice(0,19));f.push(line.slice(19));assert.equal(out.length,1);
 f.push('x'.repeat(2100));f.push('garbage\n'+line);assert.equal(bad,1);assert.equal(out.length,2);
 f.push('{bad}\n');assert.equal(bad,2);
});
test('a held input becomes unknown on staleness and disconnect; stale gaps do not integrate rotation',()=>{
 const s=setup(),p=packet();p.buttons.thumb=true;s.accept(p,0);assert(s.fresh(1499));assert(!s.fresh(1500));
 s.accept({...packet(2,10020),buttons:{thumb:false,index:false,middle:false}},10000);
 assert.deepEqual(s.orientation,[0,0,0]);assert.equal(s.events.length,0,'do not invent a release across an unseen gap');
 s.disconnect();assert(!s.fresh(10001));assert(s.latest,'last data may be retained only as history');
});
test('counts independent simultaneous buttons and rejects duplicates/out-of-order packets',()=>{
 const s=setup();s.accept(packet(),0);const p=packet(2,40);p.buttons={thumb:true,index:true,middle:true};s.accept(p,20);
 assert.deepEqual(s.counts,{thumb:1,index:1,middle:1});assert.equal(s.events.length,3);
 assert(!s.accept(p,21));assert(!s.accept(packet(),22));assert.equal(s.total,2);assert.equal(s.duplicates,2);
});
test('authoritative counters include a short press between received frames and handle counter wrap',()=>{
 const s=setup();s.accept({...packet(),presses:{thumb:0xffffffff,index:3,middle:0}},0);
 s.accept({...packet(2,40),presses:{thumb:0,index:5,middle:0}},20);
 assert.deepEqual(s.counts,{thumb:1,index:2,middle:0});assert(s.events.some(e=>e.text.includes('2 presses')));
});
test('sequence and milliseconds wrap naturally; view zero and reconnection have independent state',()=>{
 const s=setup();s.accept(packet(0xffffffff,0xfffffff0),0);s.accept(packet(0,4),20);
 assert.equal(s.total,2);assert(s.orientation[0]>0);s.zero();assert.deepEqual(s.orientation,[0,0,0]);s.connect('Bluetooth');assert.equal(s.total,0);assert.equal(s.latest,null);
});
test('USB reader rejects the bootloader without opening it',async()=>{
 let opened=false;await assert.rejects(openSerial({getInfo:()=>({usbProductId:0x0045}),open:()=>{opened=true;}},()=>{},()=>{}),/bootloader/);assert(!opened);
});
test('USB reader cancellation releases its lock and closes the port without a late end event',async()=>{
 let resolveRead,closed=0,released=0,ended=0;const reader={read:()=>new Promise(r=>resolveRead=r),cancel:async()=>resolveRead({done:true}),releaseLock:()=>++released};
 const port={getInfo:()=>({usbProductId:0x8045}),open:async()=>{},readable:{getReader:()=>reader},close:async()=>++closed};
 const handle=await openSerial(port,()=>{},()=>++ended);await handle.close();assert.equal(closed,1);assert.equal(released,1);assert.equal(ended,0);
});
test('Bluetooth receives only UART notifications and removes handlers before disconnecting',async()=>{
 const listeners=new Map(),deviceListeners=new Map();let stopped=0,disconnected=0,output='';
 const characteristic={addEventListener:(k,v)=>listeners.set(k,v),removeEventListener:k=>listeners.delete(k),startNotifications:async()=>{},stopNotifications:async()=>++stopped};
 const device={addEventListener:(k,v)=>deviceListeners.set(k,v),removeEventListener:k=>deviceListeners.delete(k),gatt:{connect:async()=>({getPrimaryService:async id=>{assert.equal(id,UART_SERVICE);return {getCharacteristic:async id=>{assert.equal(id,UART_TX);return characteristic;}};}}),disconnect:()=>++disconnected}};
 const h=await openBluetooth(device,text=>output+=text,()=>assert.fail('intentional close must not report a disconnection'));
 const bytes=new TextEncoder().encode('prefix\nhello\n'),view=new DataView(bytes.buffer,7,6);listeners.get('characteristicvaluechanged')({target:{value:view}});assert.equal(output,'hello\n');await h.close();assert.equal(stopped,1);assert.equal(disconnected,1);assert.equal(listeners.size,0);assert.equal(deviceListeners.size,0);
});

test('a short press between packets is logged even when both received states are released',()=>{
 const s=setup();s.accept({...packet(),presses:{thumb:0,index:0,middle:0}},0);s.accept({...packet(2,40),presses:{thumb:1,index:0,middle:0}},20);assert.equal(s.counts.thumb,1);assert(s.events.some(e=>e.text.includes('1 press')));
});
test('an unexpected Bluetooth disconnect clears handlers and reports the end without an exception',async()=>{
 const listeners=new Map(),deviceListeners=new Map();let ended=0;
 const characteristic={addEventListener:(k,v)=>listeners.set(k,v),removeEventListener:k=>listeners.delete(k),startNotifications:async()=>{},stopNotifications:async()=>{}};
 const device={addEventListener:(k,v)=>deviceListeners.set(k,v),removeEventListener:k=>deviceListeners.delete(k),gatt:{connect:async()=>({getPrimaryService:async()=>({getCharacteristic:async()=>characteristic})}),disconnect:()=>{}}};
 await openBluetooth(device,()=>{},()=>++ended);deviceListeners.get('gattserverdisconnected')();assert.equal(ended,1);assert.equal(listeners.size,0);assert.equal(deviceListeners.size,0);
});
