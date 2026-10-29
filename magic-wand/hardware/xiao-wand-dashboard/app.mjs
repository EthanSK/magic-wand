import {BUTTONS, WandState, LineFramer} from './model.mjs';
import {openSerial, openBluetooth, UART_SERVICE} from './transports.mjs';
const $=id=>document.getElementById(id), state=new WandState();
let owner=null, generation=0, busy=false, demoTimer=null, demoPaused=false, demoSeq=0;
const demoHeld={thumb:false,index:false,middle:false}, demoCounts={thumb:0,index:0,middle:0};
let eventKey='';
const localMode=document.documentElement.dataset.localBridge==='1';
let localCursor=-1,localSession=null,localMeta=null;
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
  const rows=state.history.filter(p=>p.imu&&now-p.now<=10000),max=Math.max(keys[0][0]==='a'?1.25:30,...rows.flatMap(p=>keys.map(k=>Math.abs(p.imu[k]))))*1.15;
  const left=52,right=w-12,top=22,bottom=h-24;
  c.font='17px system-ui';c.fillStyle='#9baeb9';c.strokeStyle='#34434e';c.lineWidth=1;
  for(const n of [-1,0,1]){const y=top+(bottom-top)*(1-n)/2;c.beginPath();c.moveTo(left,y);c.lineTo(right,y);c.stroke();c.fillText((max*n).toFixed(max<10?1:0),3,y+5);}
  ['#ef9296','#9bd7b8','#8bbdf1'].forEach((colour,i)=>{c.strokeStyle=colour;c.lineWidth=3;c.beginPath();let previous=null;for(const row of rows){const x=right-(now-row.now)/10000*(right-left),y=(top+bottom)/2-row.imu[keys[i]]/max*(bottom-top)/2;if(previous===null||row.now-previous>300)c.moveTo(x,y);else c.lineTo(x,y);previous=row.now;}c.stroke();});
  if(!fresh){c.fillStyle='#cad6dc';c.font='19px system-ui';c.textAlign='center';c.fillText(state.latest?'Last readings · no fresh data':'Waiting for motion readings',(left+right)/2,h/2-14);c.textAlign='left';}
}
function render(){
  const now=performance.now(),fresh=state.fresh(now),motion=fresh&&state.latest?.imu;
  document.body.classList.toggle('stale',!fresh);
  $('source').textContent=state.connected?`${state.source}${state.source==='Demo'?' · simulated':fresh?' · live':' · waiting'}`:'Not connected';$('source').className=`pill ${state.connected?(state.source==='Demo'?'demo':fresh?'live':''):''}`;
  $('freshness').textContent=fresh?`${Math.round(now-state.received)} ms since last packet`:state.connected?(state.latest?'No recent readings':'Waiting for a wand packet'):'Waiting for a data source';
  for(const b of BUTTONS){const card=document.querySelector(`[data-key="${b.key}"]`),pressed=fresh?state.latest.buttons[b.key]:null;card.classList.toggle('pressed',pressed===true);card.querySelector('[data-state]').textContent=pressed===null?'Unknown':pressed?'Pressed':'Released';card.querySelector('[data-level]').textContent=pressed===null?'No current reading':pressed?'LOW · joined to GND':'HIGH · pull-up';const count=localMode&&state.latest?.presses?state.latest.presses[b.key]:state.counts[b.key];card.querySelector('[data-count]').textContent=count;card.querySelector('[data-count]').parentElement.lastChild.textContent=count===1?' press':' presses';}
  for(const [id,keys] of [['gyro-values',['gx','gy','gz']],['accel-values',['ax','ay','az']]])document.querySelectorAll(`#${id} b`).forEach((el,i)=>el.textContent=motion?motion[keys[i]].toFixed(id==='gyro-values'?1:3):'—');
  if(fresh){const [x,y,z]=state.orientation;$('wand').style.transform=`rotateX(${x}deg) rotateY(${y}deg) rotateZ(${-z}deg)`;$('angles').textContent=`X ${x.toFixed(0)}° · Y ${y.toFixed(0)}° · Z ${z.toFixed(0)}°`;}else{$('angles').textContent='X —° · Y —° · Z —°';}
  plot('gyro-chart',['gx','gy','gz'],now,!!motion);plot('accel-chart',['ax','ay','az'],now,!!motion);
  $('packets').textContent=`${state.total} packets`;$('rate').textContent=fresh?`${state.rate(now).toFixed(1)} packets/s`:'—';$('rejected').textContent=`${state.invalid} / ${state.duplicates}`;$('export').disabled=!state.frames.length;
  const key=JSON.stringify(state.events);if(key!==eventKey){eventKey=key;const list=$('events');list.replaceChildren();if(!state.events.length){const li=document.createElement('li');li.textContent='No button changes received.';list.append(li);}for(const e of state.events){const li=document.createElement('li'),text=document.createElement('span'),time=document.createElement('time');text.textContent=e.text;time.textContent=`${(e.now/1000).toFixed(1)} s`;li.append(text,time);list.append(li);}}
}
support();render();setInterval(render,100);

// Local bridge mode is enabled only by the opt-in local hardware server.
async function pollLocal(){
  try{
    const response=await fetch(`/api/wand?after=${localCursor}`,{cache:'no-store'});
    if(!response.ok)throw Error('Reader unavailable');
    const meta=await response.json();if(meta.bridge!=='wand-local-v1')throw Error('Unexpected reader');
    localMeta=meta;const now=performance.now();
    // A restarted reader can reuse a session number but resets its cursor.
    if(meta.cursor<localCursor)localSession=null;
    if(meta.transport && (meta.session!==localSession || state.source!==meta.transport)){state.connect(meta.transport);localSession=meta.session;}
    for(const row of meta.packets){if(row.session===meta.session)state.accept(row.packet,now-row.age_ms);}
    localCursor=meta.cursor;
    if(['searching','usb_error','bluetooth_error','bootloader','ambiguous','disabled'].includes(meta.status))state.disconnect();
    else if(meta.transport)state.connected=true;
    notice(meta.message+(meta.status==='live'?' · USB is primary; Bluetooth takes over when USB is unplugged.':''),meta.status.endsWith('error')?'problem':'');
    support();
  }catch{state.disconnect();notice('The local reader is unavailable. Retrying the connection…','problem');}
  setTimeout(pollLocal,150);
}
if(localMode){notice('Looking for the connected Sense through the local reader…');pollLocal();}

window.addEventListener('pagehide',()=>{++generation;closeCurrent();});
