// Check raw telemetry, display precision and connection state without opening hardware.
import test from 'node:test';
import assert from 'node:assert/strict';
import fs from 'node:fs';
import {WandState,validatePacket,LineFramer,BUTTONS,motionPlotLimit,MOTION_WINDOW_MS,hasSensorAxis,firmwareNumber,buttonPin,R58_INPUTS,R58_TRACE_ORDER,PinReports,PIN_REPORT_STALE_MS,TIMELINE_MS,clickState,traceSegments,validatePinReport} from '../hardware/xiao-wand-dashboard/model.mjs';
import {openSerial,openBluetooth,UART_SERVICE,UART_TX} from '../hardware/xiao-wand-dashboard/transports.mjs';
const packet=(seq=1,ms=20)=>({schema:1,sensor:'wand',seq,ms,buttons:{thumb:false,index:false,middle:false},imu:{ax:0,ay:0,az:1,gx:2,gy:3,gz:4}});
const setup=()=>{const s=new WandState();s.connect('USB');return s;};
test('Sense dashboard pin mapping matches the wiring plan and stays separate from Puck',()=>{
 const plan=JSON.parse(fs.readFileSync(new URL('../hardware/xiao-wand-dashboard/pin-plan.json',import.meta.url)));
 assert.deepEqual(BUTTONS.map(b=>b.pin),plan.buttons.map(b=>b.board_pin));
 assert.deepEqual(BUTTONS.map(b=>[b.name,b.position,b.control,b.role,b.pin]),[['1','left','HUD button','HUD','D10'],['2','centre','Mouse button','Mouse','D8'],['3','right','Speech button','Recording','D9']]);
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

test('debug pause control starts hidden and shows only the receiver-reported state',()=>{
 const html=fs.readFileSync(new URL('../hardware/xiao-wand-dashboard/index.html',import.meta.url),'utf8');
 const app=fs.readFileSync(new URL('../hardware/xiao-wand-dashboard/app.mjs',import.meta.url),'utf8');
 assert.match(html,/<button id="actions" hidden disabled>Pause wand actions<\/button>/);
 assert.match(html,/<p id="actions-notice" class="notice demo" role="status" hidden><\/p>/);
 assert.match(app,/Resume wand actions/);
 const posts=[...app.matchAll(/fetch\(([^,]+),\{method:'POST'/g)].map(m=>m[1]);
 assert.deepEqual(posts,["'/api/actions'"],'the only write is the pause request');
 assert.match(app,/body:JSON\.stringify\(\{paused:actions\.paused!==true\}\)/);
 assert(!/sendBeacon|beforeunload|pagehide[^\n]*actions/.test(app),'closing a tab never resumes actions');
 assert(!/whether/i.test(html+app));
});

test('debug page names the receiver-reported pointer path only',()=>{
 const html=fs.readFileSync(new URL('../hardware/xiao-wand-dashboard/index.html',import.meta.url),'utf8');
 const app=fs.readFileSync(new URL('../hardware/xiao-wand-dashboard/app.mjs',import.meta.url),'utf8');
 assert.match(html,/<div id="pointer-row" hidden><dt>Pointer mode<\/dt><dd id="pointer-path">Unknown<\/dd><\/div>/);
 assert.match(app,/actions\.pointerPath==='direct'\?'Sense':actions\.pointerPath==='tuned'\?'Puck tuning':'Unknown'/);
});

test('battery at the top shows only the receiver estimate, its age or unknown',()=>{
 const html=fs.readFileSync(new URL('../hardware/xiao-wand-dashboard/index.html',import.meta.url),'utf8');
 const app=fs.readFileSync(new URL('../hardware/xiao-wand-dashboard/app.mjs',import.meta.url),'utf8');
 assert.match(html,/<header>.*<p id="battery" class="battery" title="Estimated from battery voltage\. Runtime isn\u2019t measured\." hidden>Battery unknown<\/p>/s);
 assert.match(app,/!battery\?'Battery unknown'/);
 assert.match(app,/battery\.ageSeconds<=300/,'older or disconnected readings are shown as their age, not live');
 assert(!/hours|remaining/i.test(app),'no runtime is invented');
});

// Raw sub-degree motion must survive the display path even below pointer thresholds.
test('slow raw movement remains measurable and gets a readable chart scale',()=>{
 const s=setup();const a=packet(1,20),b=packet(2,40);a.imu.gx=.0525;b.imu.gx=.0875;
 s.accept(a,0);s.accept(b,20);
 assert.equal(s.latest.imu.gx,.0875);assert(Math.abs(s.orientation[0]-.00175)<1e-12);
 const keys=['gx','gy','gz'];
 assert(motionPlotLimit([{imu:{gx:.0525,gy:.0175,gz:-.035}}],keys)<1);
 assert(motionPlotLimit([{imu:{gx:83,gy:0,gz:0}}],keys)>83,'large readings stay in view');
 assert(motionPlotLimit([],keys)>0,'empty chart has a finite scale');
});

test('button-only heartbeats keep the last motion display steady without faking freshness',()=>{
 const s=setup();s.accept(packet(1,20),0);
 s.accept({...packet(2,40),imu:null},20);
 assert.equal(s.latest.imu,null);assert.equal(s.latestMotion.imu.gx,2);assert(s.motionFresh(20));
 s.accept(packet(3,60),40);assert(Math.abs(s.orientation[0]-.08)<1e-12,'integrate between motion frames');
 s.accept({...packet(4,1620),imu:null},1600);
 assert(s.fresh(1600));assert(!s.motionFresh(1600));assert.equal(s.latestMotion.imu.gx,2);
 s.accept({...packet(5,1640),imu:null},1620);assert(!s.motionFresh(1620));
 s.connect('Bluetooth');assert.equal(s.latestMotion,null);assert.equal(s.motionReceived,null);
});

test('idle accelerometer packets never invent a gyro measurement or rotation',()=>{
 const s=setup();s.accept({...packet(1,20),imuFlags:3},0);const before=[...s.orientation];
 const idle=packet(2,40);idle.imuFlags=1;idle.imu.gx=idle.imu.gy=idle.imu.gz=0;s.accept(idle,20);
 assert.equal(s.latestGyro.seq,1);assert.equal(s.latestAccel.seq,2);assert.deepEqual(s.orientation,before);
 assert.equal(s.history.filter(p=>hasSensorAxis(p,'gx')).length,1);
 assert.equal(s.history.filter(p=>hasSensorAxis(p,'ax')).length,2);
 assert.equal(MOTION_WINDOW_MS,2000,'a large stroke no longer flattens ten seconds of fine motion');
 assert.throws(()=>validatePacket({...packet(),imuFlags:4}));
});

// Firmware 14 (R58 key holder). The fixture is the receiver's own pin report sequence
// for one centre-click press and release: D8 opens before D6 closes, and on release
// D6 opens first. Levels are the board's debounced pin levels; 0 is LOW.
const report=(d6,d8,c6,c8,extra={})=>({D0:{level:1,changes:0},D1:{level:1,changes:52},D4:{level:0,changes:80},D6:{level:d6,changes:c6},D8:{level:d8,changes:c8},...extra});
test('R58 inputs match the published wiring record, including which keys are fitted',()=>{
 const r58=JSON.parse(fs.readFileSync(new URL('../prototypes/sense-r58.json',import.meta.url))).r58;
 assert.deepEqual(R58_INPUTS.map(i=>i.pin).sort(),Object.keys(r58.pins).sort());
 assert.deepEqual([...R58_TRACE_ORDER].sort(),Object.keys(r58.pins).sort(),'every input has a trace');
 for(const i of R58_INPUTS.filter(i=>i.group==='key')){assert.equal(r58.pins[i.pin].part,`${i.name.toLowerCase().replace(' ','-')} key`);assert.equal(i.fitted,!/not fitted/.test(r58.fittedKeys[i.pin]),i.pin);}
 assert.match(r58.pins.D6.part,/press contact/);assert.match(r58.pins.D8.part,/resting contact/);assert.match(r58.pins.D4.part,/touch/);
 assert.deepEqual(R58_INPUTS.filter(i=>i.source==='wire').map(i=>[i.pin,i.key]),[['D9','index'],['D10','middle']],'D9 and D10 are not in pin reports');
 assert.equal(R58_INPUTS.find(i=>i.pin==='D4').active,1,'touch output is high while touched');
 for(const pin of ['D6','D8','D0','D1'])assert.equal(R58_INPUTS.find(i=>i.pin===pin).active,0,'switches close to GND');
});
test('firmware 14 labels the mouse button D6; firmware 13 and unknown keep D8',()=>{
 const p=validatePacket({...packet(),firmware:'wandsense14'});assert.equal(p.firmware,'wandsense14');assert.equal(firmwareNumber(p),14);
 assert.equal(firmwareNumber(validatePacket({...packet(),firmware:'wand-sense-14'})),null,'only the receiver\'s cleaned label is accepted');
 assert.equal(firmwareNumber(validatePacket(packet())),null);
 const mouse=BUTTONS.find(b=>b.key==='thumb');assert.deepEqual([14,15,13,null].map(f=>buttonPin(mouse,f)),['D6','D6','D8','D8']);
 for(const b of BUTTONS.filter(b=>b.key!=='thumb'))assert.equal(buttonPin(b,14),b.pin);
 const s=setup();s.accept({...packet(1,20),firmware:'wandsense14'},0);s.accept({...packet(2,40),firmware:'wandsense14',buttons:{thumb:true,index:false,middle:false}},20);
 assert.equal(s.events[0].text,'2 pressed · D6');
});
test('centre click state follows both contacts; unknown is never released',()=>{
 assert.deepEqual([[1,0],[1,1],[0,1],[0,0]].map(([p,r])=>clickState(p,r)),['Released','Between contacts','Pressed','Both closed · check wiring']);
 assert.equal(clickState(null,0),null);assert.equal(clickState(1,undefined),null);
 const r=new PinReports();assert.equal(r.level('D6',0),null,'no report yet');
 r.accept(report(1,0,178,178),1000);assert.equal(clickState(r.level('D6',1000),r.level('D8',1000)),'Released');
 assert.equal(r.level('D8',1000+PIN_REPORT_STALE_MS-1),0);assert.equal(r.level('D8',1000+PIN_REPORT_STALE_MS),null,'a missing 10 s report makes it unknown');
});
test('pin report fixture gives contact order, merged changes and no invented changes',()=>{
 const r=new PinReports(),events=[];const add=(levels,now)=>events.push(...r.accept(levels,now));
 add(report(1,0,178,178),0);assert.deepEqual(events,[],'the first report is a baseline');
 add(report(1,1,178,179),5000);add(report(0,1,179,179),5030);add(report(1,1,180,179),5200);add(report(1,0,180,180),5230);
 assert.deepEqual(events,['Resting contact opened · D8','Press contact closed · D6','Press contact opened · D6','Resting contact closed · D8']);
 events.length=0;add(report(1,0,182,182),5400);assert.deepEqual(events,['D6: 2 level changes reported by board','D8: 2 level changes reported by board'],'a press merged into one report still counts');
 events.length=0;add(report(1,0,182,182,{D4:{level:1,changes:81},D1:{level:0,changes:53}}),5500);assert.deepEqual(events,['Touched · D4','Key pressed · D1']);
 events.length=0;add(report(0,1,5,5),40000);assert.deepEqual(events,[],'no changes across a stale gap');
 add(report(0,1,0,0),41000);assert.deepEqual(events,[],'a board restart resets counters without events');
 assert.deepEqual(r.accept(report(1,0,9,9),41000),[],'a repeated or older report is skipped');assert.equal(r.latest.D6.level,0);
 assert.throws(()=>validatePinReport({D6:{level:2,changes:0}}));assert.throws(()=>validatePinReport({D6:{level:1,changes:-1}}));assert.throws(()=>validatePinReport(null));
 assert.deepEqual(validatePinReport({D7:{level:1,changes:3},D6:{level:0,changes:1}}),{D6:{level:0,changes:1}},'unknown pins from later firmware are ignored');
});
test('step traces hold a level until the next report and leave stale time unknown',()=>{
 const rows=[{now:0,v:true},{now:100,v:false},{now:200,v:null},{now:300,v:false}];
 assert.deepEqual(traceSegments(rows,r=>r.v,1000,PIN_REPORT_STALE_MS),[{start:0,end:100,active:true},{start:100,end:200,active:false},{start:300,end:1000,active:false}]);
 assert.deepEqual(traceSegments([{now:0,v:true},{now:0,v:false}],r=>r.v,50,1500),[{start:0,end:50,active:false}],'reports received together show only the result');
 assert.deepEqual(traceSegments([{now:0,v:true}],r=>r.v,5000,1500),[{start:0,end:1500,active:true}],'a stale wire channel stops after 1.5 s');
 assert.deepEqual(traceSegments([{now:0,v:true},{now:20000,v:true}],r=>r.v,25000,PIN_REPORT_STALE_MS),[{start:20000,end:25000,active:true}],'only the last 10 seconds');
 const s=setup();for(let i=1;i<=6000;i++)s.accept({...packet(i,i*2),buttons:{thumb:i===3000,index:false,middle:false}},i*2);
 assert(s.buttonTrace.length<=Math.ceil((TIMELINE_MS+1500)/250)+3,'bounded at several hundred packets a second');assert(s.buttonTrace.some(r=>r.buttons.thumb),'a 2 ms press is kept');
});
test('R58 page text matches the reviewed wording and keeps the three-switch page for firmware 13',()=>{
 const html=fs.readFileSync(new URL('../hardware/xiao-wand-dashboard/index.html',import.meta.url),'utf8');
 const app=fs.readFileSync(new URL('../hardware/xiao-wand-dashboard/app.mjs',import.meta.url),'utf8');
 assert.match(html,/<section id="r58" class="panel r58" aria-label="R58 key holder" hidden>/);
 for(const text of ['Press contact · D6','Resting contact · D8','Touch sensor · D4','DFRobot output, high while touched','Upper left · D0','Upper right · D9 · Speech','Lower left · D10 · HUD','Lower right · D1','Last 10 seconds','Times are when the Mac received each report, not when the input changed.'])assert(html.includes(text),text);
 for(const text of ['No pin report for over 12 seconds','Waiting for firmware 14 pin reports',"click:['Closed','Open']","touch:['Touched','Not touched']","key:['Pressed','Released']"])assert(app.includes(text),text);
 assert.match(app,/const show=firmware!==null\?firmware>=14:pins\.latest!==null/);
 assert(!/Resting[^.·]*D9|D9[^.·,]*resting/i.test(html+app),'D9 is never the resting contact');
 assert(!/whether/i.test(html+app));
});
