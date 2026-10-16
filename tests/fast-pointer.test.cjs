const test = require('node:test');
const assert = require('node:assert/strict');
const {createWand, read} = require('./harness.cjs');

function make(reference, uart) {
  const wand = createWand({bridge:false});
  wand.calibrate();
  wand.loadBridge('readable');
  if(reference) wand.device.evaluate(read('tests/fixtures/pointer-reference.js'));
  // The live receiver owns a synchronous UART wrapper. Without its marker,
  // the device must keep the ordinary HID/button pump.
  if(uart) wand.ctx.wandBridgeOriginalSend = wand.ctx.mouse.send;
  return wand;
}

for(const uart of [false,true]) for(const hz of [20,35,104,208]) {
  test(`optimized pointer preserves accepted output at ${hz} Hz, UART ${uart}`, () => {
    const previous=make(true,uart),current=make(false,uart);
    const both=fn=>{fn(previous);fn(current);};
    both(w=>w.tap());both(w=>w.advance(.8));
    let seed=331;
    for(let i=0;i<1500;i++) {
      if(i===300||i===700) both(w=>w.edge('D1',0));
      if(i===550||i===900) both(w=>w.edge('D1',1));
      if(i===1100) both(w=>w.tap('D2'));
      seed=(Math.imul(seed,1664525)+1013904223)>>>0;
      const angle=i/14,mag=i%200<50?.3:i%200<100?.5:(seed%32767)/134;
      const gyro={x:Math.round(Math.sin(angle)*mag*134),y:0,z:Math.round(Math.cos(angle)*mag*134)};
      both(w=>w.paced(1/hz,gyro));
    }
    assert.equal(JSON.stringify(current.frames),JSON.stringify(previous.frames));
    for(const field of ['fractionX','fractionY','wandSlackX','wandSlackY','wandIntentActive']) {
      assert.equal(current.ctx[field],previous.ctx[field],field);
    }
    assert.deepEqual(current.colors(),previous.colors());
  });
}

test('Pointer pump drops failed movement without leaving the sender busy', () => {
  const wand=make(false,true);
  wand.tap();wand.advance(.8);
  wand.ctx.mouse.send=()=>{throw new Error('UART unavailable');};
  for(let i=0;i<40;i++) wand.paced(1/35,{x:1340,y:0,z:1340});
  assert.equal(wand.ctx.busy,false);
  assert.equal(wand.ctx.moveX,0);
  assert.equal(wand.ctx.moveY,0);
});


test('orange persists through a stalled update and overrides a stale mouse mode', () => {
  const w=make(false,true);
  w.ctx.moveLatched=true;
  w.ctx.WAND_UPDATING=true;
  w.ctx.updateLights();
  assert.deepEqual(w.colors(),[1,.2,0]);
  w.advance(12);
  assert.deepEqual(w.colors(),[1,.2,0]);
  w.ctx.WAND_UPDATING=false;w.ctx.wandMotionReady=false;w.ctx.updateLights();
  assert.deepEqual(w.colors(),[1,.2,0], 'partial motion installation must not claim blue-ready');
  w.ctx.wandMotionReady=true;w.ctx.updateLights();
  assert.deepEqual(w.colors(),[0,0,1]);
  w.device.disconnect();
  assert.deepEqual(w.colors(),[.08,.016,0]);
});
