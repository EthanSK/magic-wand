// Render raw wand telemetry and controls; display precision never filters pointer input.
import {BUTTONS, WandState, LineFramer, motionPlotLimit, MOTION_WINDOW_MS, hasSensorAxis, firmwareNumber, buttonPin, labelFirmware, R58_INPUTS, R58_TRACE_ORDER, PinReports, PIN_REPORT_STALE_MS, TIMELINE_MS, clickState, traceSegments, batteryLive, batteryHeader, batteryCard, packLine} from './model.mjs';
import {openSerial, openBluetooth, UART_SERVICE} from './transports.mjs';
const $=id=>document.getElementById(id), state=new WandState(), pins=new PinReports();
let owner=null, generation=0, busy=false, demoTimer=null, demoPaused=false, demoSeq=0;
const demoHeld={thumb:false,index:false,middle:false}, demoCounts={thumb:0,index:0,middle:0};
let eventKey='';
const localMode=document.documentElement.dataset.localBridge==='1';
let localCursor=-1,localSession=null,localMeta=null,inputCursor=-1;
function notice(text,kind=''){if($('notice').textContent!==text)$('notice').textContent=text;$('notice').className=`notice ${kind}`;}
function support() {
  const missing=[];if(!navigator.serial)missing.push('USB');if(!navigator.bluetooth)missing.push('Bluetooth');
  $('capabilities').textContent=missing.length?`${missing.join(' and ')} browser access is unavailable here. For hardware, open this page in Chrome or Edge on this Mac. Demo works here.`:'USB and Bluetooth readers are available. Each connection starts only after you choose a device.';
  $('usb').disabled=busy||!navigator.serial;$('ble').disabled=busy||!navigator.bluetooth;
  $('demo').disabled=busy;$('stop').disabled=!state.connected&&!busy;
  $('pause').hidden=state.source!=='Demo'||!state.connected;
  for(const b of document.querySelectorAll('[data-hold]'))b.hidden=state.source!=='Demo'||!state.connected;
  if(localMode){$('count-note').hidden=false;$('usb').disabled=true;$('ble').disabled=true;$('usb').classList.add('managed');$('ble').classList.add('managed');$('usb').textContent=(localMeta?.usb_present||localMeta?.transport==='USB')?'USB primary':'USB waiting';$('ble').textContent=(localMeta?.usb_present||localMeta?.transport==='USB')?'Bluetooth standby':'Bluetooth fallback';$('demo').hidden=true;$('stop').hidden=true;$('capabilities').textContent='One local reader owns the board. USB takes priority; Bluetooth is used when USB is absent. No device picker is needed.';}
}
async function closeCurrent(){if(demoTimer!==null){clearInterval(demoTimer);demoTimer=null;}for(const b of BUTTONS)demoHeld[b.key]=false;const old=owner;owner=null;await old?.close();}
async function stop(){++generation;state.disconnect();busy=false;support();notice('Disconnected. Button states are unknown until fresh readings arrive.');await closeCurrent();}
function framerFor(ticket){return new LineFramer(p=>{if(ticket===generation)state.accept(p,performance.now());},()=>{if(ticket===generation)++state.invalid;});}
async function connect(kind){
  if(busy)return;
  if(kind==='USB'&&!navigator.serial||kind==='Bluetooth'&&!navigator.bluetooth)return;
  busy=true;support();const before=generation;
  try{
    // Ask inside the click gesture. Keep the current source until a choice is made.
    const choice=kind==='USB'?await navigator.serial.requestPort({filters:[{usbVendorId:0x2886}]}):await navigator.bluetooth.requestDevice({filters:[{namePrefix:'Magic Wand Sense'}],optionalServices:[UART_SERVICE]});
    if(before!==generation)return;
    const ticket=++generation;await closeCurrent();
    if(ticket!==generation)return;
    state.connect(kind);const frame=framerFor(ticket);let ended=false;
    const end=error=>{if(ticket!==generation||ended)return;ended=true;state.disconnect();owner=null;notice(error?`Connection ended: ${error.message}`:'Connection ended. Choose Connect to reconnect.','problem');support();};
    notice(`Opening ${kind}. Waiting for wand telemetry…`);
    const opened=kind==='USB'?await openSerial(choice,t=>frame.push(t),end):await openBluetooth(choice,t=>frame.push(t),end);
    if(ticket!==generation||ended){await opened.close();return;}
    owner=opened;notice(`${kind} connected. Waiting for the matching wand diagnostic sketch; no commands are sent to the board.`);
  }catch(error){if(before===generation||state.source===kind){notice(error.name==='NotFoundError'?'No device selected.':`Could not connect: ${error.message}`,'problem');if(!owner&&demoTimer===null)state.disconnect();}}
  finally{busy=false;support();}
}
function demoPacket(){
  if(demoPaused)return;
  const now=performance.now(),t=now/1000;
  state.accept({schema:1,sensor:'wand',seq:++demoSeq,ms:Math.floor(now)>>>0,
    buttons:{...demoHeld},presses:{...demoCounts},imu:{ax:.28*Math.sin(t*.8),ay:.22*Math.cos(t*.7),az:.98+.05*Math.sin(t),gx:18*Math.sin(t*.6),gy:12*Math.cos(t*.8),gz:9*Math.sin(t*.4)}},now);
}
async function startDemo(){const ticket=++generation;state.disconnect();await closeCurrent();if(ticket!==generation)return;state.connect('Demo');demoSeq=0;demoPaused=false;for(const b of BUTTONS)demoCounts[b.key]=0;$('pause').textContent='Pause demo data';demoPacket();demoTimer=setInterval(demoPacket,20);notice('DEMO · simulated motion. Hold the three demo buttons, or keys 1 / 2 / 3. No hardware is connected.','demo');support();}
function hold(key,pressed){if(state.source!=='Demo'||!state.connected||demoPaused)return;if(pressed&&!demoHeld[key])++demoCounts[key];demoHeld[key]=pressed;demoPacket();}
for(const button of document.querySelectorAll('[data-hold]')){
  button.addEventListener('pointerdown',e=>{button.setPointerCapture(e.pointerId);hold(button.dataset.hold,true);});
  for(const name of ['pointerup','pointercancel','lostpointercapture','blur'])button.addEventListener(name,()=>hold(button.dataset.hold,false));
  button.addEventListener('keydown',e=>{if(['Space','Enter'].includes(e.code)){e.preventDefault();hold(button.dataset.hold,true);}});
  button.addEventListener('keyup',e=>{if(['Space','Enter'].includes(e.code)){e.preventDefault();hold(button.dataset.hold,false);}});
}
const keys=Object.fromEntries(BUTTONS.map((b,i)=>['Digit'+(i+1),b.key]));
window.addEventListener('keydown',e=>{if(keys[e.code]&&!e.metaKey&&!e.ctrlKey&&!e.altKey){e.preventDefault();hold(keys[e.code],true);}});
window.addEventListener('keyup',e=>{if(keys[e.code])hold(keys[e.code],false);});
window.addEventListener('blur',()=>{for(const b of BUTTONS)hold(b.key,false);});
$('usb').addEventListener('click',()=>connect('USB'));$('ble').addEventListener('click',()=>connect('Bluetooth'));$('demo').addEventListener('click',startDemo);$('stop').addEventListener('click',stop);
$('pause').addEventListener('click',()=>{for(const b of BUTTONS)hold(b.key,false);demoPaused=!demoPaused;$('pause').textContent=demoPaused?'Resume demo data':'Pause demo data';notice(demoPaused?'DEMO PAUSED · after 1.5 seconds the inputs become Unknown. Resume to receive simulated readings.':'DEMO · simulated readings resumed.','demo');});
$('zero').addEventListener('click',()=>{state.zero();state.event('View zeroed · sensor calibration unchanged',performance.now());});
$('export').addEventListener('click',()=>{if(!state.frames.length)return;const text=state.frames.map(p=>JSON.stringify(p)).join('\n')+'\n',url=URL.createObjectURL(new Blob([text],{type:'application/x-ndjson'}));const a=document.createElement('a');a.href=url;a.download=`Magic_Wand_Sense_${state.source}_${new Date().toISOString().replace(/[:.]/g,'-')}.jsonl`;a.click();setTimeout(()=>URL.revokeObjectURL(url),1000);});
function plot(id,keys,now,fresh){
  const canvas=$(id),c=canvas.getContext('2d'),w=canvas.width,h=canvas.height;c.clearRect(0,0,w,h);
  const rows=state.history.filter(p=>hasSensorAxis(p,keys[0])&&now-p.now<=MOTION_WINDOW_MS),max=motionPlotLimit(rows,keys);
  const left=52,right=w-12,top=22,bottom=h-24;
  c.font='17px system-ui';c.fillStyle='#9baeb9';c.strokeStyle='#34434e';c.lineWidth=1;
  for(const n of [-1,0,1]){const y=top+(bottom-top)*(1-n)/2;c.beginPath();c.moveTo(left,y);c.lineTo(right,y);c.stroke();c.fillText((max*n).toFixed(max<10?1:0),3,y+5);}
  ['#ef9296','#9bd7b8','#8bbdf1'].forEach((colour,i)=>{c.strokeStyle=colour;c.lineWidth=3;c.beginPath();let previous=null;for(const row of rows){const x=right-(now-row.now)/MOTION_WINDOW_MS*(right-left),y=(top+bottom)/2-row.imu[keys[i]]/max*(bottom-top)/2;if(previous===null||row.now-previous>300)c.moveTo(x,y);else c.lineTo(x,y);previous=row.now;}c.stroke();});
  if(!fresh){c.fillStyle='#cad6dc';c.font='19px system-ui';c.textAlign='center';c.fillText(state.latest?'Last readings · no fresh data':'Waiting for motion readings',(left+right)/2,h/2-14);c.textAlign='left';}
}
// R58 key holder view (firmware 14). Each input is on, off or unknown (null):
// pin reports go unknown after PIN_REPORT_STALE_MS, wire channels after 1.5 s.
// Unknown is never shown as released or open.
const R58_TEXT={click:['Closed','Open'],touch:['Touched','Not touched'],key:['Pressed','Released']};
const WIRING_THREE='Wiring, left to right: 1 \u2192 D10 (10), 2 \u2192 D8 (8), 3 \u2192 D9 (9). Each switch\u2019s other contact \u2192 GND. No 3V3 connection.';
const WIRING_R58='R58 wiring: keys D0, D1, D9, D10 and press contact D6 \u2192 GND. Resting contact D8 is closed at rest. Touch output \u2192 D4; sensor powered from 3V3.';
function r58Active(input,now){
  if(input.source==='wire')return state.fresh(now)?state.latest.buttons[input.key]:null;
  const level=pins.level(input.pin,now);return level===null?null:level===input.active;
}
function drawTimeline(now){
  // Size the canvas to its displayed size so labels aren't stretched.
  const canvas=$('r58-timeline'),box=canvas.getBoundingClientRect(),dpr=window.devicePixelRatio||1;
  if(!box.width||!box.height)return;
  const W=Math.round(box.width*dpr),H=Math.round(box.height*dpr);if(canvas.width!==W||canvas.height!==H){canvas.width=W;canvas.height=H;}
  const c=canvas.getContext('2d'),w=box.width,h=box.height;c.setTransform(dpr,0,0,dpr,0,0);c.clearRect(0,0,w,h);
  const left=86,right=w-8,top=6,bottom=h-22,rowH=(bottom-top)/R58_TRACE_ORDER.length,x=t=>right-(now-t)/TIMELINE_MS*(right-left);
  c.font='12px system-ui';c.textBaseline='middle';c.lineWidth=1;
  for(let s=0;s<=TIMELINE_MS/1000;s++){const gx=right-s*1000/TIMELINE_MS*(right-left);c.strokeStyle=s%5?'#1f2a31':'#2e3c45';c.beginPath();c.moveTo(gx,top);c.lineTo(gx,bottom);c.stroke();if(s%5===0){c.fillStyle='#9baeb9';c.textAlign=s?(s===10?'left':'center'):'right';c.fillText(s?`\u2212${s} s`:'now',gx,h-10);}}
  R58_TRACE_ORDER.forEach((pin,i)=>{
    const input=R58_INPUTS.find(v=>v.pin===pin),y0=top+i*rowH,hi=y0+5,lo=y0+rowH-5,mid=(hi+lo)/2;
    c.textAlign='left';c.fillStyle='#cad6dc';c.fillText(input.trace,4,mid);
    // A dashed line marks unknown time; known levels are drawn over it.
    c.setLineDash([3,4]);c.strokeStyle='#3a4852';c.beginPath();c.moveTo(left,mid);c.lineTo(right,mid);c.stroke();c.setLineDash([]);
    const segments=input.source==='wire'?traceSegments(state.buttonTrace,r=>r.buttons[input.key],now,1500):traceSegments(pins.rows,r=>r.report[pin]?r.report[pin].level===input.active:null,now,PIN_REPORT_STALE_MS);
    c.strokeStyle=input.colour;c.fillStyle=input.colour;c.lineWidth=2;c.beginPath();let previous=null;
    for(const s of segments){
      const x0=x(s.start),x1=x(s.end),y=s.active?hi:lo;c.clearRect(x0,mid-2,x1-x0,4);
      if(s.active){c.globalAlpha=.2;c.fillRect(x0,hi,x1-x0,lo-hi);c.globalAlpha=1;}
      if(previous&&previous.end===s.start)c.lineTo(x0,y);else c.moveTo(x0,y);c.lineTo(x1,y);previous=s;
    }
    c.stroke();
  });
}
function renderR58(now,firmware){
  // Firmware 13 and the three-switch layout keep their original page.
  const show=firmware!==null&&firmware>=14;$('r58').hidden=!show;
  $('wiring-note').textContent=show?WIRING_R58:WIRING_THREE;
  if(!show)return;
  const fresh=pins.fresh(now);
  $('r58-freshness').textContent=fresh?`${Math.round((now-pins.received)/1000)} s since last pin report`:pins.latest?'No pin report for over 12 seconds':'Waiting for firmware 14 pin reports';
  $('r58-freshness').classList.toggle('problem',!fresh&&pins.latest!==null);
  for(const input of R58_INPUTS){
    const row=document.querySelector(`.r58-row[data-input="${input.pin}"]`),on=r58Active(input,now);
    row.style.setProperty('--input-colour',input.colour);row.classList.toggle('on',on===true);row.classList.toggle('unknown',on===null);
    row.querySelector('[data-state]').textContent=on===null?'Unknown':R58_TEXT[input.group][on?0:1];
    const fitted=row.querySelector('[data-fitted]');if(fitted)fitted.textContent=input.fitted===false?'Not fitted':'';
  }
  const click=clickState(pins.level('D6',now),pins.level('D8',now));$('click-state').textContent=click??'Unknown';$('click-state').classList.toggle('unknown',click===null);
  drawTimeline(now);
}
function render(){
  const now=performance.now(),fresh=state.fresh(now),firmware=labelFirmware(state.latest?firmwareNumber(state.latest):null,pins.latest!==null);
  // Firmware 14 moved the mouse button to D6; label pins from the packet's firmware.
  $('pin-summary').textContent=`XIAO nRF52840 Sense \u00b7 left to right: ${BUTTONS.map(b=>`${b.name} ${buttonPin(b,firmware)}`).join(' \u00b7 ')}`;
  for(const b of BUTTONS)document.querySelector(`[data-key="${b.key}"] .pin`).textContent=`${buttonPin(b,firmware)} \u00b7 ${b.role}`;
  renderR58(now,firmware);

  document.body.classList.toggle('stale',!fresh);
  $('source').textContent=state.connected?`${state.source}${state.source==='Demo'?' · simulated':fresh?' · live':' · waiting'}`:'Not connected';$('source').className=`pill ${state.connected?(state.source==='Demo'?'demo':fresh?'live':''):''}`;
  $('freshness').textContent=fresh?`${Math.round(now-state.received)} ms since last packet`:state.connected?(state.latest?'No recent readings':'Waiting for a wand packet'):'Waiting for a data source';
  for(const b of BUTTONS){const card=document.querySelector(`[data-key="${b.key}"]`),pressed=fresh?state.latest.buttons[b.key]:null;card.classList.toggle('pressed',pressed===true);card.querySelector('[data-state]').textContent=pressed===null?'Unknown':pressed?'Pressed':'Released';card.querySelector('[data-level]').textContent=pressed===null?'No current reading':pressed?'LOW · joined to GND':'HIGH · pull-up';const count=localMode&&state.latest?.presses?state.latest.presses[b.key]:state.counts[b.key];card.querySelector('[data-count]').textContent=count;card.querySelector('[data-count]').parentElement.lastChild.textContent=count===1?' press':' presses';}
  for(const [id,keys] of [['gyro-values',['gx','gy','gz']],['accel-values',['ax','ay','az']]])document.querySelectorAll(`#${id} b`).forEach((el,i)=>el.textContent=(id==='gyro-values'?state.latestGyro:state.latestAccel)?.imu[keys[i]]?.toFixed(3)??'—');
  if(fresh){const [x,y,z]=state.orientation;$('wand').style.transform=`rotateX(${x}deg) rotateY(${y}deg) rotateZ(${-z}deg)`;$('angles').textContent=`X ${x.toFixed(2)}° · Y ${y.toFixed(2)}° · Z ${z.toFixed(2)}°`;}else{$('angles').textContent='X —° · Y —° · Z —°';}
  plot('gyro-chart',['gx','gy','gz'],now,fresh);plot('accel-chart',['ax','ay','az'],now,fresh);
  $('gyro-note').textContent=hasSensorAxis(state.latest??{},'gx')?`Raw gyro readings · last ${MOTION_WINDOW_MS/1000} seconds`:'Last readings · no fresh data';
  $('packets').textContent=`${state.total} packets`;$('rate').textContent=fresh?`${state.rate(now).toFixed(1)} packets/s`:'—';$('rejected').textContent=`${state.invalid} / ${state.duplicates}`;$('export').disabled=!state.frames.length;
  const key=JSON.stringify(state.events);if(key!==eventKey){eventKey=key;const list=$('events');list.replaceChildren();if(!state.events.length){const li=document.createElement('li');li.textContent='No button changes received.';list.append(li);}for(const e of state.events){const li=document.createElement('li'),text=document.createElement('span'),time=document.createElement('time');text.textContent=e.text;time.textContent=`${(e.now/1000).toFixed(1)} s`;li.append(text,time);list.append(li);}}
}
support();render();setInterval(render,100);

// Local bridge mode is enabled only by the opt-in local hardware server.
async function pollLocal(){
  try{
    const response=await fetch(`/api/wand?after=${localCursor}&inputs_after=${inputCursor}`,{cache:'no-store'});
    if(!response.ok)throw Error('Reader unavailable');
    const meta=await response.json();if(meta.bridge!=='wand-local-v1')throw Error('Unexpected reader');
    localMeta=meta;const now=performance.now();
    // A restarted reader can reuse a session number but resets its cursor.
    if(meta.cursor<localCursor)localSession=null;
    if(meta.transport && (meta.session!==localSession || state.source!==meta.transport)){state.connect(meta.transport);localSession=meta.session;}
    for(const row of meta.packets){if(row.session===meta.session)state.accept(row.packet,now-row.age_ms);}
    localCursor=meta.cursor;
    // Firmware 14 pin reports have their own cursor. A restarted bridge starts
    // again from 0; ask for its latest report instead of waiting for new ids.
    const inputs=meta.inputs;
    if(inputs&&Number.isInteger(inputs.cursor)){
      if(inputs.cursor<inputCursor)inputCursor=-1;
      else{
        for(const row of inputs.rows??[]){if(!(row.id>inputCursor))continue;try{for(const text of pins.accept(row.levels,now-row.age_ms))state.event(text,now-row.age_ms);}catch{++state.invalid;}inputCursor=row.id;}
        if(inputCursor<0)inputCursor=inputs.cursor;
      }
    }
    if(['searching','usb_error','bluetooth_error','bootloader','ambiguous','disabled'].includes(meta.status))state.disconnect();
    else if(meta.transport)state.connected=true;
    notice(meta.message+(meta.status==='live'?' · USB is primary; Bluetooth takes over when USB is unplugged.':''),meta.status.endsWith('error')?'problem':'');
    support();
  }catch{state.disconnect();notice('The local reader is unavailable. Retrying the connection…','problem');}
  setTimeout(pollLocal,150);
}
if(localMode){notice('Looking for the connected Sense through the local reader…');pollLocal();}

// Ethan's debug pause: Wand Receiver owns the state. The page shows only what
// the receiver reports and never assumes a request worked. Every tab polls the
// same state; closing a tab never resumes actions.
let actions=null,actionsBusy=false,actionsProblem='',actionsProblemUntil=0,r58Profile=null;
const PAUSED_TEXT='WAND ACTIONS PAUSED · Readings continue, but the wand doesn\u2019t move the pointer, click, scroll, or send HUD, review, screenshot or dictation commands. A recording already in progress keeps going.';
function renderActions(){
  const button=$('actions'),banner=$('actions-notice'),available=actions?.available===true,paused=available&&actions.paused===true;
  button.hidden=!localMode;button.disabled=actionsBusy||!available;
  button.textContent=paused?'Resume wand actions':'Pause wand actions';
  button.classList.toggle('primary',paused);
  button.title=available?'':'Wand Receiver is unavailable';
  if(actionsProblem&&Date.now()>actionsProblemUntil)actionsProblem='';
  const text=actionsProblem||(paused?PAUSED_TEXT:'');
  banner.hidden=!text;banner.className=`notice ${actionsProblem?'problem':'demo'}`;
  if(banner.textContent!==text)banner.textContent=text;
  // The receiver's actual pointer conversion, so readings are compared knowingly.
  $('pointer-row').hidden=!localMode;
  // Ethan's battery readout: the receiver's voltage estimate, its age and the
  // charger flag only (model.mjs batteryHeader/batteryCard).
  const battery=available?actions.battery:null,connected=available&&actions.connected===true;
  $('battery').hidden=!localMode;$('battery').classList.toggle('stale',!batteryLive(battery,connected));
  $('battery').textContent=batteryHeader(battery,connected);
  // R58 battery card: the bought pack from the published record, then the same estimate.
  const card=batteryCard(battery,connected);
  for(const [key,text] of Object.entries(card)){const cell=document.querySelector(`[data-battery="${key}"]`);if(cell.textContent!==text)cell.textContent=text;cell.classList.toggle('unknown',text==='Unknown');}
  const pack=packLine(r58Profile?.battery);$('battery-pack').hidden=!pack;$('battery-pack').textContent=pack;
  $('pointer-path').textContent=!available?'Unknown':actions.pointerPath==='direct'?'Sense':actions.pointerPath==='tuned'?'Puck tuning':'Unknown';
}
async function pollActions(){
  try{const response=await fetch('/api/actions',{cache:'no-store'});actions=response.ok?await response.json():null;}
  catch{actions=null;}
  renderActions();setTimeout(pollActions,1000);
}
$('actions').addEventListener('click',async()=>{
  if(actionsBusy||actions?.available!==true)return;
  actionsBusy=true;actionsProblem='';renderActions();
  try{
    const response=await fetch('/api/actions',{method:'POST',cache:'no-store',headers:{'Content-Type':'application/json'},body:JSON.stringify({paused:actions.paused!==true})});
    const value=await response.json().catch(()=>null);
    if(value&&typeof value.available==='boolean')actions=value;
    if(!value?.confirmed)throw Error('unconfirmed');
  }catch{actionsProblem='Wand Receiver didn\u2019t confirm the change. Showing its current state.';actionsProblemUntil=Date.now()+4000;}
  finally{actionsBusy=false;renderActions();}
});
// The R58 record (pack ratings) changes only when the repository does; fetch it once.
async function loadR58Profile(){try{const response=await fetch('/api/r58',{cache:'no-store'});r58Profile=response.ok?await response.json():null;}catch{r58Profile=null;}renderActions();}
if(localMode){pollActions();loadR58Profile();}

window.addEventListener('pagehide',()=>{++generation;closeCurrent();});
