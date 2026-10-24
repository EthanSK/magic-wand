/* Puck wand: bottom D1 starts follow, then clicks; double tap stops follow.
 * Middle D2 navigates the HUD; top D30 is speech. Mac receiver uses BLE UART.
 * Keep still while the red calibration LED is on.
 */
var mouse = require("ble_hid_mouse");
NRF.setServices(undefined, {hid:mouse.report});
// Official Espruino mouse advertisement: retain UART discovery and advertise HID.
NRF.setAdvertising([{}, [2,1,6,3,3,0x12,0x18,3,0x19,0xc2,0x03]]);

// Adjust only after checking the board's mounting direction.
var HUD_PIN=D2, STT_PIN=D30;
var hudHeld=false, hudX=0, hudY=0, hudTimer;
var MOVE_PIN=D1; // Bottom pointer button.
var calibrationLit=false;
var lightLevels=[0,0,0];
function writeLight(pin, level) {
  if(level>0 && level<1)analogWrite(pin,level,{freq:200});
  else {pinMode(pin,"output");pin.write(level);}
}
function updateLights() {
  if(global.WAND_UPDATING){writeLight(LED1,1);writeLight(LED2,0);writeLight(LED3,0);return;}
  // Button-edge feedback only: no animation or idle polling timer.
  var move=moveLatched||!digitalRead(MOVE_PIN),hud=hudOpen||!digitalRead(HUD_PIN),speech=!digitalRead(STT_PIN);
  // White pointer, orange HUD/disconnected, red speech. Hardware PWM mixes the LEDs.
  lightLevels=calibrationLit?[1,0,0]:!connected?[0.08,0.016,0]:scrollHeld?[0,1,1]:speech?[1,0,0]:hud?[1,0.2,0]:move?[0.45,0.45,0.45]:[0,0,0];
  writeLight(LED1,lightLevels[0]);
  writeLight(LED2,lightLevels[1]);
  writeLight(LED3,lightLevels[2]);
}
var CONFIG = {xAxis:"z", yAxis:"x", xSign:-1, ySign:-1,
              gain:108, yGain:1.4, sampleRate:104,
              fineGain:0.35, fineSpeed:2, fullSpeed:18,
              deadZone:1.2, tapSeconds:0.22, doubleTapSeconds:0.25}; // gain: cursor counts per degree
var bias, sum, samples, warmup, lastTime, fractionX, fractionY;
var restMin, restMax, sumSquares, noise={x:1.2,y:1.2,z:1.2};
var filteredX=0, filteredY=0;
var motionStats={count:0,elapsed:0,maxGap:0};
var calibrationDeadline;
var debugUntil=0, debugNext=0;
function gyroDebug(seconds) { debugUntil=getTime()+seconds; debugNext=0; }
var connected=false, busy=false, epoch=0, buttons=0, sentButtons=0;
var states=[], moveX=0, moveY=0, watches=[], sendTimer;
var moveDownAt, moveHeld=false, gyroAwake=false, motionWarmup=0;
var tapTimer, tapPending=false, secondTap=false, dragging=false;
var pointerTrackX=0,pointerTrackY=0,pointerTrackTimer;
var moveLatched=false,hudOpen=false,moveGestureMode,holdClickTimer;
var moveClickFired=false,lastMoveTap=-100;
var scrollHeld=false,scrollSuppress=false,scrollX=0,scrollY=0,scrollTimer;
var chordFollowBefore=false,hudDelayTimer,hudReportStarted=false;
function stopScroll(){if(scrollTimer!==undefined)clearInterval(scrollTimer);scrollTimer=undefined;scrollHeld=false;}
function scrollReport(phase){if(connected)Bluetooth.println('@SCROLL '+phase+','+Math.round(scrollX*1000)+','+Math.round(scrollY*1000));}
function checkScrollChord(){
  var both=!digitalRead(MOVE_PIN)&&!digitalRead(HUD_PIN);
  if(scrollHeld){
    if(!both){
      scrollReport('E');stopScroll();scrollSuppress=!digitalRead(MOVE_PIN)||!digitalRead(HUD_PIN);
      moveLatched=chordFollowBefore;moveGestureMode=undefined;
      if(!scrollSuppress&&(moveLatched||hudOpen))wakeGyro();else if(bias)sleepGyro();
    }
    updateLights();return true;
  }
  if(scrollSuppress&&!both){
    if(digitalRead(MOVE_PIN)&&digitalRead(HUD_PIN)){
      scrollSuppress=false;
      if((moveLatched||hudOpen))wakeGyro();else if(bias)sleepGyro();
    }
    updateLights();return true;
  }
  if(!both)return false;
  scrollSuppress=false;
  scrollHeld=true;scrollX=0;scrollY=0;scrollReport('B');
  if(hudDelayTimer!==undefined)clearTimeout(hudDelayTimer);hudDelayTimer=undefined;hudHeld=false;hudReportStarted=false;
  if(moveGestureMode==='operation')pointerReport('E');stopPointerTrack();
  if(dragging){states.push(0);pump();}cancelTapGesture();clearHoldClick();
  moveGestureMode=undefined;moveLatched=false;moveX=0;moveY=0;
  scrollTimer=setInterval(function(){scrollReport('U');},30);
  if(connected)wakeGyro();updateLights();return true;
}
function clearHoldClick(){if(holdClickTimer!==undefined)clearTimeout(holdClickTimer);holdClickTimer=undefined;}
function setHUDOpen(open){
  if(hudOpen===open)return;
  hudOpen=open;
  if(open){hudX=0;hudY=0;if(hudTimer!==undefined)clearInterval(hudTimer);hudTimer=setInterval(function(){hudReport();},30);}
  else stopHUD();
  if(connected&&(scrollHeld||moveLatched||hudOpen))wakeGyro();else if(bias)sleepGyro();
  updateLights();
}
function setMouseFollow(on){
  if(dragging){states.push(0);pump();}
  cancelTapGesture();clearHoldClick();moveGestureMode=undefined;
  moveLatched=!!on;
  if(moveLatched && connected && !hudOpen)wakeGyro();else if(bias)sleepGyro();
  updateLights();
}
function pointerReport(phase){if(connected)Bluetooth.println("@MOVE "+phase+","+Math.round(pointerTrackX*1000)+","+Math.round(pointerTrackY*1000));}
function stopPointerTrack(){if(pointerTrackTimer!==undefined)clearInterval(pointerTrackTimer);pointerTrackTimer=undefined;}

function wakeGyro() {
  if (gyroAwake) return;
  gyroAwake=true; motionWarmup=Math.ceil(CONFIG.sampleRate*0.096); lastTime=getTime();
  filteredX=0;filteredY=0;motionStats={count:0,elapsed:0,maxGap:0};
  Puck.accelOn(CONFIG.sampleRate);
}
function sleepGyro() {
  Puck.accelOff(); gyroAwake=false; motionWarmup=0;
  lastTime=0; fractionX=0; fractionY=0; moveX=0; moveY=0;
  filteredX=0;filteredY=0;
}

function calibrate() {
  bias=undefined; sum={x:0,y:0,z:0}; sumSquares={x:0,y:0,z:0}; samples=0; warmup=Math.ceil(CONFIG.sampleRate*0.096);
  restMin={x:Infinity,y:Infinity,z:Infinity};
  restMax={x:-Infinity,y:-Infinity,z:-Infinity};
  lastTime=0; fractionX=0; fractionY=0; moveX=0; moveY=0;
  calibrationLit=true;updateLights();
  calibrationDeadline=getTime()+10;
  wakeGyro();
}
function readButtons() {
  return 0; // The other two buttons deliberately have no mouse action.
}
function cancelTapGesture() {
  if(tapTimer!==undefined){clearTimeout(tapTimer);tapTimer=undefined;}
  tapPending=false;secondTap=false;dragging=false;
}
function clickTimes(count) {
  if(!connected || !bias)return;
  for(var i=0;i<count;i++)states.push(1,0);
  pump();
}
function deferSingleClick() {
  tapPending=true;
  tapTimer=setTimeout(function(){
    tapTimer=undefined;
    if(tapPending){tapPending=false;clickTimes(1);}
  },CONFIG.doubleTapSeconds*1000);
}
function resetMoveGesture() {
  // A button already held at startup/reconnect must not become a tap.
  moveHeld=!digitalRead(MOVE_PIN);
  moveDownAt=moveHeld?getTime()-CONFIG.tapSeconds:undefined;
}
function queueButtons() {
  var next=readButtons();
  if (next===buttons) return;
  buttons=next;
  if (!connected) return;
  // Preserve press AND release during asynchronous Bluetooth sends.
  states.push(next);
  pump();
}
function pump() {
  if (!connected || busy) return;
  var hasState=states.length>0;
  var b=hasState?states[0]:sentButtons;
  var x=hasState?0:Math.max(-127,Math.min(127,moveX));
  var y=hasState?0:Math.max(-127,Math.min(127,moveY));
  if (!hasState && !x && !y) return;
  var token=epoch;
  busy=true;
  try {
    mouse.send(x,y,b,function() {
      if (token!==epoch) return;
      busy=false; sentButtons=b;
      if (hasState) states.shift();
      if (states.length) pump();
      // New motion is deliberately not replayed after a delayed report.
    });
    if (!hasState) {moveX-=x; moveY-=y;}
  } catch(e) {
    // Editor connections and a host not yet subscribed to HID can reject.
    busy=false; moveX=0; moveY=0;
    if (states.length && sendTimer===undefined) sendTimer=setTimeout(function(){sendTimer=undefined;pump();},20);
  }
}
function deadZone(v) {
  if (Math.abs(v)<=CONFIG.deadZone) return 0;
  return v-(v>0?CONFIG.deadZone:-CONFIG.deadZone);
}
function precisionZone(v,threshold) {
  return Math.abs(v)<=threshold?0:v-(v>0?threshold:-threshold);
}
function radialKeep(x,y) {
  // HUD only: the same threshold on the rotation vector keeps its direction,
  // so a shallow diagonal is neither flattened nor dropped. Cursor stays per-axis.
  var m=Math.sqrt(x*x+y*y);
  return m<=CONFIG.deadZone?0:(m-CONFIG.deadZone)/m;
}
function onMotion(a) {
  var g=a.gyro;
  if (!g) return;
  var now=getTime();
  if (!digitalRead(MOVE_PIN) && now<debugUntil && now>=debugNext) {
    debugNext=now+0.25;
    print("GYRO degrees/sec", {x:g.x/134,y:g.y/134,z:g.z/134},
          "HOLD", !digitalRead(MOVE_PIN));
  }
  if (!bias) {
    if (now>calibrationDeadline) {calibrationLit=false;updateLights();sleepGyro();return;}
    if (warmup>0) {warmup--; return;}
    // Never learn a held/moving wand as its stationary zero.
    var stable=digitalRead(MOVE_PIN) && digitalRead(D2) && digitalRead(D30);
    ['x','y','z'].forEach(function(k) {
      restMin[k]=Math.min(restMin[k],g[k]);
      restMax[k]=Math.max(restMax[k],g[k]);
      if (Math.abs(g[k])>8*134 || restMax[k]-restMin[k]>3*134) stable=false;
    });
    if (!stable) {
      sum={x:0,y:0,z:0}; sumSquares={x:0,y:0,z:0}; samples=0;
      restMin={x:g.x,y:g.y,z:g.z}; restMax={x:g.x,y:g.y,z:g.z};
      return;
    }
    sum.x+=g.x; sum.y+=g.y; sum.z+=g.z;
    sumSquares.x+=g.x*g.x;sumSquares.y+=g.y*g.y;sumSquares.z+=g.z*g.z;samples++;
    if (samples>=CONFIG.sampleRate*2) {
      bias={x:sum.x/samples,y:sum.y/samples,z:sum.z/samples};
      ["x","y","z"].forEach(function(k){
        noise[k]=Math.max(0.25,Math.min(CONFIG.deadZone,4*Math.sqrt(Math.max(0,sumSquares[k]/samples-bias[k]*bias[k]))/134));
      });
      calibrationLit=false;updateLights(); lastTime=now; motionWarmup=0;
      print('WAND_CALIBRATED',JSON.stringify(bias));
      if (!connected || (!moveLatched && !hudOpen && digitalRead(MOVE_PIN))) sleepGyro();
    }
    return;
  }
  if (motionWarmup>0) {motionWarmup--; lastTime=now; return;}
  var gap=Math.max(0,now-lastTime),dt=Math.min(0.05,gap);lastTime=now;
  motionStats.count++;motionStats.elapsed+=gap;motionStats.maxGap=Math.max(motionStats.maxGap,gap);
  if(scrollHeld){
    var sx=(g[CONFIG.xAxis]-bias[CONFIG.xAxis])/134,sy=(g[CONFIG.yAxis]-bias[CONFIG.yAxis])/134,sk=radialKeep(sx,sy);
    scrollX+=sx*sk*dt*CONFIG.xSign;scrollY+=sy*sk*dt*CONFIG.ySign;return;
  }
  if(scrollSuppress)return;
  if(hudOpen&&connected){
    var hx=(g[CONFIG.xAxis]-bias[CONFIG.xAxis])/134,hy=(g[CONFIG.yAxis]-bias[CONFIG.yAxis])/134,keep=radialKeep(hx,hy);
    hudX+=hx*keep*dt*CONFIG.xSign;hudY+=hy*keep*dt*CONFIG.ySign;
  }
  if (!connected || !moveLatched || (moveGestureMode==="pointer" && !dragging)) {
    fractionX=0;fractionY=0;moveX=0;moveY=0;return;
  }
  // Espruino documents raw gyro values / 134 as degrees per second.
  var px=(g[CONFIG.xAxis]-bias[CONFIG.xAxis])/134,py=(g[CONFIG.yAxis]-bias[CONFIG.yAxis])/134;
  // Time-based light smoothing: 8 ms for fine aim, 2 ms during fast sweeps.
  var speed=Math.sqrt(px*px+py*py),blend=Math.max(0,Math.min(1,(speed-CONFIG.fineSpeed)/(CONFIG.fullSpeed-CONFIG.fineSpeed)));
  var alpha=1-Math.exp(-dt/(0.008-0.006*blend));
  filteredX+=alpha*(px-filteredX);filteredY+=alpha*(py-filteredY);
  var sx=precisionZone(filteredX,noise[CONFIG.xAxis]),sy=precisionZone(filteredY,noise[CONFIG.yAxis]);
  var scale=CONFIG.fineGain+(1-CONFIG.fineGain)*blend*blend*(3-2*blend);
  fractionX+=sx*dt*CONFIG.gain*scale*CONFIG.xSign;
  fractionY+=sy*dt*CONFIG.gain*CONFIG.yGain*scale*CONFIG.ySign;
  var x=fractionX<0?Math.ceil(fractionX):Math.floor(fractionX);
  var y=fractionY<0?Math.ceil(fractionY):Math.floor(fractionY);
  fractionX-=x; fractionY-=y;
  moveX=Math.max(-127,Math.min(127,moveX+x));
  moveY=Math.max(-127,Math.min(127,moveY+y));
  pump();
}
function hudReport(){if(connected&&hudOpen)Bluetooth.println('@NAV '+Math.round(hudX*1000)+','+Math.round(hudY*1000));}
function stopHUD(){
  if(hudDelayTimer!==undefined)clearTimeout(hudDelayTimer);hudDelayTimer=undefined;hudReportStarted=false;
  if(hudTimer!==undefined)clearInterval(hudTimer);hudTimer=undefined;hudHeld=false;hudX=0;hudY=0;
}
function middlePress(){
  if(!connected||scrollHeld)return;
  if(!hudOpen)setHUDOpen(true);
  hudReportStarted=true;Bluetooth.println('@MIDDLE 1');
}
function onHUDButton(){
  if(!digitalRead(HUD_PIN)&&digitalRead(MOVE_PIN)&&!scrollSuppress)chordFollowBefore=moveLatched;
  if(checkScrollChord())return;
  if(!digitalRead(HUD_PIN)){
    hudHeld=true;
    hudDelayTimer=setTimeout(function(){hudDelayTimer=undefined;if(hudHeld)middlePress();},80);
  }else{
    if(!hudHeld){updateLights();return;}
    if(hudDelayTimer!==undefined)clearTimeout(hudDelayTimer);hudDelayTimer=undefined;
    if(!hudReportStarted)middlePress();
    if(connected)Bluetooth.println('@MIDDLE 0');
    hudHeld=false;hudReportStarted=false;
  }
  updateLights();
}
function onSpeechButton() {
  updateLights();
  if(connected)Bluetooth.println('@STT '+(digitalRead(STT_PIN)?0:1));
}
function onConnect() {
  stopScroll();scrollSuppress=false;chordFollowBefore=false;
  clearHoldClick();moveLatched=false;hudOpen=false;moveGestureMode=undefined;lastMoveTap=-100;
  stopHUD();cancelTapGesture();
  epoch++; connected=true; busy=false; sentButtons=0;
  if (sendTimer!==undefined) {clearTimeout(sendTimer);sendTimer=undefined;}
  buttons=readButtons(); states=[0,buttons]; calibrate();
  resetMoveGesture();
}
function onDisconnect() {
  stopScroll();scrollSuppress=false;chordFollowBefore=false;
  clearHoldClick();moveLatched=false;hudOpen=false;moveGestureMode=undefined;lastMoveTap=-100;
  stopPointerTrack();stopHUD();cancelTapGesture();
  epoch++; connected=false; busy=false; states=[];
  if (sendTimer!==undefined) {clearTimeout(sendTimer);sendTimer=undefined;}
  sentButtons=0; moveX=0; moveY=0;
  moveDownAt=undefined; moveHeld=false;
  sleepGyro();calibrationLit=false;updateLights();
}
function onMoveButton() {
  if(!digitalRead(MOVE_PIN)&&digitalRead(HUD_PIN)&&!scrollSuppress)chordFollowBefore=moveLatched;
  if(checkScrollChord())return;
  moveX=0;moveY=0;fractionX=0;fractionY=0;filteredX=0;filteredY=0;
  if(!digitalRead(MOVE_PIN)) {
      moveGestureMode=moveLatched?"pointer":"enable";
      if(moveGestureMode==="enable"){moveLatched=true;if(connected)wakeGyro();}
      secondTap=tapPending;
      if(tapTimer!==undefined)clearTimeout(tapTimer);
      tapTimer=undefined;tapPending=false;moveClickFired=false;
      clearHoldClick();holdClickTimer=setTimeout(function(){
        holdClickTimer=undefined;
        if(digitalRead(MOVE_PIN)||moveGestureMode!=="pointer"||!connected||!bias)return;
        moveClickFired=true;dragging=true;states.push(1);pump();wakeGyro();
      },CONFIG.tapSeconds*1000);
    updateLights();return;
  }
  clearHoldClick();
  if(moveGestureMode==="operation") {pointerReport("E");stopPointerTrack();}
  else if(moveGestureMode==="enable") {moveLatched=true;}
  else if(moveGestureMode==="pointer") {
    if(dragging){dragging=false;states.push(0);pump();}
    else if(secondTap){moveLatched=false;cancelTapGesture();}
    else deferSingleClick();
  }
  moveGestureMode=undefined;secondTap=false;
  if((moveLatched||hudOpen)&&connected)wakeGyro();else if(bias)sleepGyro();
  updateLights();
}

function onInit() {
  stopScroll();scrollSuppress=false;chordFollowBefore=false;
  clearHoldClick();moveLatched=false;hudOpen=false;moveGestureMode=undefined;lastMoveTap=-100;
  global.WAND_UPDATING=false;
  // save() restores JS state; remove this program's restored handlers first.
  stopPointerTrack();stopHUD();cancelTapGesture();
  watches.forEach(function(id){clearWatch(id);}); watches=[];
  if (sendTimer!==undefined) clearTimeout(sendTimer);
  sendTimer=undefined;
  Puck.removeListener("accel",onMotion);
  NRF.removeListener("connect",onConnect);
  NRF.removeListener("disconnect",onDisconnect);
  pinMode(D1,"input_pullup"); pinMode(D2,"input_pullup");
  pinMode(D30,"input_pullup");
  buttons=readButtons(); sentButtons=0; states=[];
  busy=false; connected=false; epoch++;
  resetMoveGesture();
  sleepGyro();
  NRF.setConnectionInterval(15);
  Puck.on("accel",onMotion); calibrate();
  watches.push(setWatch(onMoveButton,MOVE_PIN,{edge:"both",repeat:true,debounce:20}));
  watches.push(setWatch(onHUDButton,HUD_PIN,{edge:"both",repeat:true,debounce:20}));
  watches.push(setWatch(onSpeechButton,STT_PIN,{edge:"both",repeat:true,debounce:20}));
  NRF.on("connect",onConnect);
  NRF.on("disconnect",onDisconnect);
  // No periodic JS polling while idle; button/sensor events drive reports.
}
onInit();
