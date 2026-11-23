// Hardware-independent wire protocol and display state. No device access.
export const BUTTONS = [
  // Ethan: "They no longer have specific fingers, just have them like one,
  // two, and three going left to right." Visible names are numbers only.
  // wand-v1 keys are legacy wire channels (thumb=D8, index=D9, middle=D10),
  // not fingers; keep them for compatibility. Previously named by finger.
  // control was Middle, Bottom and Top before Ethan's 2026-10-30 rename.
  {key:'middle', name:'1', position:'left', control:'HUD button', role:'HUD', pin:'D10', printed:'10', colour:'#edc96d'},
  {key:'thumb', name:'2', position:'centre', control:'Mouse button', role:'Mouse', pin:'D8', printed:'8', colour:'#78b9fa'},
  {key:'index', name:'3', position:'right', control:'Speech button', role:'Recording', pin:'D9', printed:'9', colour:'#f27c88'},
];
// `firmware` arrives as the board's name with punctuation removed by Wand Receiver
// (wand-sense-14 -> wandsense14). null when the packet doesn't say.
export function firmwareNumber(packet) {
  const m=/^wandsense(\d{1,6})$/.exec(packet?.firmware ?? '');
  return m ? Number(m[1]) : null;
}
// Firmware 14 (R58 key holder) moved the mouse button from D8 to D6. D8 is now the
// OP1 resting contact, which is closed at rest; on firmware 13 that read as a held
// mouse button and blocked wireless updates. The wire channel (thumb) is unchanged,
// so only the visible pin label depends on the firmware. BUTTONS keeps the original
// three-switch pins because pin-plan.json and firmware 13 still use them.
export const buttonPin = (button, firmware) => button.key==='thumb' && firmware!==null && firmware>=14 ? 'D6' : button.pin;

// R58 key holder inputs on firmware 14 (prototypes/sense-r58.json is the wiring record).
// source 'report': the board's `Ein` pin reports, read from Wand Receiver's log by
//   bridge.py. `active` is the level that means closed, pressed or touched: switches
//   use pull-ups (closed reads 0); the DFRobot touch output drives the pin high (1).
// source 'wire': a wand-v1 button channel, because D9 and D10 are not in pin reports.
// Order is the card layout: centre click, touch, then keys as they sit physically.
export const R58_INPUTS = [
  {pin:'D6', group:'click', name:'Press contact', trace:'Press D6', source:'report', active:0, colour:'#78b9fa'},
  {pin:'D8', group:'click', name:'Resting contact', trace:'Resting D8', source:'report', active:0, colour:'#9bd7b8'},
  {pin:'D4', group:'touch', name:'Touch sensor', trace:'Touch D4', source:'report', active:1, colour:'#c9a7f5'},
  {pin:'D0', group:'key', name:'Upper left', trace:'Key D0', source:'report', active:0, fitted:false, colour:'#edc96d'},
  {pin:'D9', group:'key', name:'Upper right', role:'Speech', trace:'Key D9', source:'wire', key:'index', fitted:false, colour:'#f27c88'},
  {pin:'D10', group:'key', name:'Lower left', role:'HUD', trace:'Key D10', source:'wire', key:'middle', fitted:false, colour:'#edc96d'},
  {pin:'D1', group:'key', name:'Lower right', trace:'Key D1', source:'report', active:0, fitted:true, colour:'#edc96d'},
];
export const R58_TRACE_ORDER = ['D6','D8','D4','D0','D1','D9','D10'];
// The board sends a pin report on every change and every 10 s even when idle, so
// no report for 12.5 s means the levels are unknown, never released.
export const PIN_REPORT_STALE_MS = 12500;
export const TIMELINE_MS = 10000;
const REPORT_PINS = new Set(R58_INPUTS.filter(i => i.source==='report').map(i => i.pin));
export function validatePinReport(levels) {
  if (!levels || typeof levels!=='object' || Array.isArray(levels)) throw Error('Expected a pin report.');
  const report={};
  for (const [pin,value] of Object.entries(levels)) {
    if (!value || (value.level!==0 && value.level!==1) || !uint32(value.changes)) throw Error('Invalid pin level.');
    // Later firmware may report more pins; show only the ones this page knows.
    if (REPORT_PINS.has(pin)) report[pin]={level:value.level, changes:value.changes};
  }
  return report;
}
// The two OP1 contacts together. Break-before-make means a press opens D8 before
// D6 closes, so "Between contacts" is a normal brief state, and both closed is not.
export function clickState(press, rest) {
  if (press===null || press===undefined || rest===null || rest===undefined) return null;
  const pressed=press===0, resting=rest===0;
  return pressed && !resting ? 'Pressed' : !pressed && resting ? 'Released' : !pressed ? 'Between contacts' : 'Both closed · check wiring';
}
function pinEventText(input, level) {
  if (input.group==='click') return `${input.name} ${level===input.active?'closed':'opened'} · ${input.pin}`;
  if (input.group==='touch') return `${level===input.active?'Touched':'Not touched'} · ${input.pin}`;
  return `Key ${level===input.active?'pressed':'released'} · ${input.pin}`;
}
// Firmware 14 pin reports, timed by when this page received them (the bridge's
// age_ms), not when the input changed on the board.
export class PinReports {
  constructor() { this.reset(); }
  reset() { this.rows=[]; this.latest=null; this.received=null; }
  fresh(now) { return this.received!==null && now-this.received<PIN_REPORT_STALE_MS; }
  level(pin, now) { return this.fresh(now) ? this.latest?.[pin]?.level ?? null : null; }
  // Returns activity texts for changes since the previous report. Change counters
  // show changes merged into one report (reports are at least 25 ms apart). No
  // changes are invented across a stale gap or a board restart (counter went down).
  accept(levels, now) {
    const report=validatePinReport(levels), texts=[];
    // The bridge's first answer can repeat a report already shown (placed at its log
    // time after a bridge restart); keep the timeline in order and skip it.
    if (this.received!==null && now<=this.received) return texts;
    const previous=this.fresh(now) ? this.latest : null;
    if (previous) for (const input of R58_INPUTS) {
      const a=previous[input.pin], b=report[input.pin];
      if (input.source!=='report' || !a || !b || b.changes<a.changes) continue;
      const seen=a.level!==b.level ? 1 : 0, count=b.changes-a.changes;
      if (seen) texts.push(pinEventText(input,b.level));
      if (count>seen) texts.push(`${input.pin}: ${count} level changes reported by board`);
    }
    this.latest=report; this.received=now; this.rows.push({now,report});
    while (this.rows.length && now-this.rows[0].now>PIN_REPORT_STALE_MS+TIMELINE_MS) this.rows.shift();
    return texts;
  }
}
// Step trace for one input over the timeline window: [{start,end,active}] segments.
// A level holds from one sample until the next, but no longer than `holdMs` (when
// the source counts as stale); gaps are unknown and drawn as nothing.
export function traceSegments(samples, activeOf, now, holdMs, windowMs=TIMELINE_MS) {
  const out=[];
  for (let i=0;i<samples.length;i++) {
    const active=activeOf(samples[i]);
    const start=Math.max(samples[i].now, now-windowMs), end=Math.min(samples[i+1]?.now ?? now, samples[i].now+holdMs, now);
    if (active===null || end<=start) continue;
    const last=out.at(-1);
    if (last && last.active===active && last.end===start) last.end=end; else out.push({start,end,active});
  }
  return out;
}
export const AXES = ['ax','ay','az','gx','gy','gz'];
export const MOTION_WINDOW_MS = 2000;
export const hasSensorAxis = (packet,key) => !!packet.imu && (((packet.imuFlags ?? 3) & (key[0]==='g'?2:1)) !== 0);
const uint32 = v => Number.isInteger(v) && v >= 0 && v <= 0xffffffff;
export function validatePacket(value) {
  if (!value || value.schema !== 1 || value.sensor !== 'wand' || !uint32(value.ms) || !uint32(value.seq)) throw Error('Expected a wand-v1 telemetry packet.');
  if (!value.buttons || BUTTONS.some(b => typeof value.buttons[b.key] !== 'boolean')) throw Error('Three explicit button states are required.');
  if (value.imu !== null && (!value.imu || AXES.some(k => typeof value.imu[k] !== 'number' || !Number.isFinite(value.imu[k]) || Math.abs(value.imu[k]) > 10000))) throw Error('Invalid motion reading.');
  if (value.imuFlags !== undefined && (!Number.isInteger(value.imuFlags) || value.imuFlags<0 || value.imuFlags>3)) throw Error('Invalid motion flags.');
  if (value.presses !== undefined && (!value.presses || BUTTONS.some(b => !uint32(value.presses[b.key])))) throw Error('Invalid press counter.');
  // Keep the firmware label (bridge.py already limits it to short letters and
  // digits); the pin labels for the mouse button depend on it.
  const firmware=typeof value.firmware==='string' && /^[A-Za-z0-9]{1,64}$/.test(value.firmware) ? value.firmware : undefined;
  return {schema:1, sensor:'wand', seq:value.seq, ms:value.ms, ...(firmware ? {firmware} : {}),
    buttons:Object.fromEntries(BUTTONS.map(b => [b.key,value.buttons[b.key]])),
    imu:value.imu === null ? null : Object.fromEntries(AXES.map(k => [k,value.imu[k]])),
    ...(value.imuFlags !== undefined ? {imuFlags:value.imuFlags} : {}),
    ...(value.presses ? {presses:Object.fromEntries(BUTTONS.map(b => [b.key,value.presses[b.key]]))} : {})};
}
// Keep small raw readings visible: the old 30 deg/s minimum flattened normal
// slow aiming. The scale still expands to include every sample, without clipping
// or changing the data sent to the receiver. This is display scaling only.
export function motionPlotLimit(rows, keys) {
  let limit=keys[0][0]==='a'?1.25:0.5;
  for (const row of rows) for (const key of keys) limit=Math.max(limit,Math.abs(row.imu[key]));
  return limit*1.15;
}
export class LineFramer {
  constructor(receive, invalid = () => {}) { this.receive=receive; this.invalid=invalid; this.buffer=''; this.dropping=false; }
  push(text) {
    for (const part of text.split(/(?<=\n)/)) {
      const end=part.endsWith('\n');
      if (!this.dropping) this.buffer+=part;
      if (this.buffer.length>2048) { this.buffer=''; this.dropping=true; this.invalid(); }
      if (end) {
        if (!this.dropping && this.buffer.trim()) {
          try { this.receive(validatePacket(JSON.parse(this.buffer))); } catch { this.invalid(); }
        }
        this.buffer=''; this.dropping=false;
      }
    }
  }
}
export class WandState {
  constructor() { this.reset('None'); }
  reset(source) {
    this.source=source; this.connected=false; this.latest=null; this.received=null; this.latestMotion=null; this.motionReceived=null; this.latestGyro=null; this.gyroReceived=null; this.latestAccel=null; this.frames=[]; this.history=[]; this.events=[]; this.buttonTrace=[];
    this.total=0; this.invalid=0; this.duplicates=0; this.previous=null; this.counterLast=null;
    this.counts={thumb:0,index:0,middle:0}; this.orientation=[0,0,0]; this.arrivals=[];
  }
  connect(source) { this.reset(source); this.connected=true; }
  disconnect() { this.connected=false; this.previous=null; }
  fresh(now) { return this.connected && this.received!==null && now-this.received<1500; }
  motionFresh(now) { return this.fresh(now) && this.motionReceived!==null && now-this.motionReceived<1500; }
  zero() { this.orientation=[0,0,0]; }
  event(text,now) { this.events.unshift({text,now}); this.events.length=Math.min(this.events.length,40); }
  accept(value,now) {
    const p=validatePacket(value);
    if (this.latest) {
      const seqDelta=(p.seq-this.latest.seq)>>>0;
      if (!seqDelta || seqDelta>0x7fffffff) { ++this.duplicates; return false; }
    }
    const wasFresh=this.fresh(now);
    if (!wasFresh) this.previous=null;
    if (this.previous) for (const b of BUTTONS) if (p.buttons[b.key]!==this.previous.buttons[b.key]) {
      if (!p.presses && p.buttons[b.key]) ++this.counts[b.key];
      this.event(`${b.name} ${p.buttons[b.key]?'pressed':'released'} · ${buttonPin(b,firmwareNumber(p))}`,now);
    }
    if (p.presses) {
      if (this.counterLast) for (const b of BUTTONS) {
        const d=(p.presses[b.key]-this.counterLast[b.key])>>>0;
        if (d && d<100000) { this.counts[b.key]+=d; if (d>1 || !wasFresh || !this.previous || this.previous.buttons[b.key] || !p.buttons[b.key]) this.event(`${b.name}: ${d} press${d===1?'':'es'} reported by board`,now); }
      }
      this.counterLast=p.presses;
    } else this.counterLast=null;
    // Button-only heartbeats do not erase the last motion reading. Keep motion
    // freshness separate so the idle sensor cannot flash numbers on and off.
    if (this.latestGyro && this.gyroReceived!==null && now-this.gyroReceived<1500 && hasSensorAxis(p,'gx')) {
      const dt=((p.ms-this.latestGyro.ms)>>>0)/1000;
      if (dt>0 && dt<=0.2) ['gx','gy','gz'].forEach((k,i)=>{this.orientation[i]=(this.orientation[i]+p.imu[k]*dt)%360;});
    }
    if (p.imu) { this.latestMotion=p; this.motionReceived=now; }
    if (hasSensorAxis(p,'gx')) { this.latestGyro=p; this.gyroReceived=now; }
    if (hasSensorAxis(p,'ax')) this.latestAccel=p;
    this.previous=p; this.latest=p; this.received=now; ++this.total;
    this.frames.push(p); if(this.frames.length>3000)this.frames.shift();
    this.history.push({now,imu:p.imu,imuFlags:p.imuFlags}); if(this.history.length>500)this.history.shift();
    // Button channels for the R58 timeline. Wand Receiver forwards several hundred
    // packets a second, so keep every change plus one sample per 250 ms; that is
    // enough to end a trace within 250 ms of the 1.5 s staleness limit.
    const traced=this.buttonTrace.at(-1);
    if (!traced || now-traced.now>=250 || BUTTONS.some(b=>traced.buttons[b.key]!==p.buttons[b.key])) this.buttonTrace.push({now,buttons:p.buttons});
    while(this.buttonTrace.length && now-this.buttonTrace[0].now>TIMELINE_MS+1500) this.buttonTrace.shift();
    this.arrivals.push(now); this.arrivals=this.arrivals.filter(t=>now-t<=2000);
    return true;
  }
  rate(now) { const t=this.arrivals.filter(t=>now-t<=2000); return t.length>1?(t.length-1)*1000/(t.at(-1)-t[0]||1):0; }
}
