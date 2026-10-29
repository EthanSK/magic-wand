// Hardware-independent wire protocol and display state. No device access.
export const BUTTONS = [
  // Ethan: "They no longer have specific fingers, just have them like one,
  // two, and three going left to right." Visible names are numbers only.
  // wand-v1 keys are legacy wire channels (thumb=D8, index=D9, middle=D10),
  // not fingers; keep them for compatibility. Previously named by finger.
  {key:'middle', name:'1', position:'left', control:'Middle', role:'HUD', pin:'D10', printed:'10', colour:'#edc96d'},
  {key:'thumb', name:'2', position:'centre', control:'Bottom', role:'Mouse', pin:'D8', printed:'8', colour:'#78b9fa'},
  {key:'index', name:'3', position:'right', control:'Top', role:'Recording', pin:'D9', printed:'9', colour:'#f27c88'},
];
export const AXES = ['ax','ay','az','gx','gy','gz'];
const uint32 = v => Number.isInteger(v) && v >= 0 && v <= 0xffffffff;
export function validatePacket(value) {
  if (!value || value.schema !== 1 || value.sensor !== 'wand' || !uint32(value.ms) || !uint32(value.seq)) throw Error('Expected a wand-v1 telemetry packet.');
  if (!value.buttons || BUTTONS.some(b => typeof value.buttons[b.key] !== 'boolean')) throw Error('Three explicit button states are required.');
  if (value.imu !== null && (!value.imu || AXES.some(k => typeof value.imu[k] !== 'number' || !Number.isFinite(value.imu[k]) || Math.abs(value.imu[k]) > 10000))) throw Error('Invalid motion reading.');
  if (value.presses !== undefined && (!value.presses || BUTTONS.some(b => !uint32(value.presses[b.key])))) throw Error('Invalid press counter.');
  return {schema:1, sensor:'wand', seq:value.seq, ms:value.ms,
    buttons:Object.fromEntries(BUTTONS.map(b => [b.key,value.buttons[b.key]])),
    imu:value.imu === null ? null : Object.fromEntries(AXES.map(k => [k,value.imu[k]])),
    ...(value.presses ? {presses:Object.fromEntries(BUTTONS.map(b => [b.key,value.presses[b.key]]))} : {})};
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
    this.source=source; this.connected=false; this.latest=null; this.received=null; this.frames=[]; this.history=[]; this.events=[];
    this.total=0; this.invalid=0; this.duplicates=0; this.previous=null; this.counterLast=null;
    this.counts={thumb:0,index:0,middle:0}; this.orientation=[0,0,0]; this.arrivals=[];
  }
  connect(source) { this.reset(source); this.connected=true; }
  disconnect() { this.connected=false; this.previous=null; }
  fresh(now) { return this.connected && this.received!==null && now-this.received<1500; }
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
      this.event(`${b.name} ${p.buttons[b.key]?'pressed':'released'} · ${b.pin}`,now);
    }
    if (p.presses) {
      if (this.counterLast) for (const b of BUTTONS) {
        const d=(p.presses[b.key]-this.counterLast[b.key])>>>0;
        if (d && d<100000) { this.counts[b.key]+=d; if (d>1 || !wasFresh || !this.previous || this.previous.buttons[b.key] || !p.buttons[b.key]) this.event(`${b.name}: ${d} press${d===1?'':'es'} reported by board`,now); }
      }
      this.counterLast=p.presses;
    } else this.counterLast=null;
    if (this.latest && wasFresh && p.imu && this.latest.imu) {
      const dt=((p.ms-this.latest.ms)>>>0)/1000;
      if (dt>0 && dt<=0.2) ['gx','gy','gz'].forEach((k,i)=>{this.orientation[i]=(this.orientation[i]+p.imu[k]*dt)%360;});
    }
    this.previous=p; this.latest=p; this.received=now; ++this.total;
    this.frames.push(p); if(this.frames.length>3000)this.frames.shift();
    this.history.push({now,imu:p.imu}); if(this.history.length>500)this.history.shift();
    this.arrivals.push(now); this.arrivals=this.arrivals.filter(t=>now-t<=2000);
    return true;
  }
  rate(now) { const t=this.arrivals.filter(t=>now-t<=2000); return t.length>1?(t.length-1)*1000/(t.at(-1)-t[0]||1):0; }
}
