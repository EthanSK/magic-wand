if(global.wandNativeMotion){Puck.removeListener('accel',global.wandNativeMotion);Puck.removeListener('accel',onMotion);Puck.on('accel',onMotion);delete global.wandNativeMotion;}
// Locate the actual callback registered on the bottom pin, not a stale global
// function with the same name. Espruino exposes these in its documented root.
var wr=(E.internal||global['\xFF']).watches,wc=[];
for(var wk in wr){var wv=wr[wk];if(wv&&wv.pin==MOVE_PIN&&typeof wv.cb==='function'&&wv.cb.toString().indexOf('clearHoldClick')>=0)wc.push(wv.cb);}
if(wc.length!==1)throw Error('WAND_LIVE_CALLBACK_NOT_UNIQUE '+wc.length);
global.wandLiveMoveCallback=wc[0];
print('WAND_CALLBACK_MATCH '+(global.wandLiveMoveCallback===onMoveButton));
delete global.wr;delete global.wc;delete global.wk;delete global.wv;
// Puck boot code has its own saved scope. Replace callbacks in place, preserving
// that scope and the registered watch references (Espruino Function.replaceWith).
// Assigning a new global function instead leaves old callbacks reading old state.

  if(global.wandPointerModeWatch!==undefined){
    var id=global.wandPointerModeWatch;try{clearWatch(id);}catch(e){}
    watches=watches.filter(function(w){return w!==id;});delete global.wandPointerModeWatch;
  }
  if(global.wandLightWatches){
    global.wandLightWatches.forEach(function(id){try{clearWatch(id);}catch(e){}watches=watches.filter(function(w){return w!==id;});});
    delete global.wandLightWatches;
  }
  if(global.wandRecordingBlinkTimer!==undefined)clearInterval(global.wandRecordingBlinkTimer);
  global.wandRecordingBlinkTimer=undefined;global.wandRecordingBlinkRed=false;
  global.wandMomentaryStarted=undefined;global.wandLastLightState=undefined;
  // A brief receiver update must not discard a good sensor zero. Without this,
  // holding a button during reconnect can time out calibration and disable only
  // motion while the other buttons and the Bluetooth connection still work.
  var connects=NRF['#onconnect'];
  if(!connects)connects=[onConnect];else if(typeof connects==='function')connects=[connects];
  connects.forEach(function(callback){if(callback.toString().indexOf('stopScroll')>=0)callback.replaceWith(function(){
    global.wandCircleScrolling=false;global.wandReviewTracking=false;global.wandDeskSleeping=false;global.wandAppMode=undefined;global.wandReviewFiles=false;stopScroll();scrollSuppress=false;chordFollowBefore=false;
    clearHoldClick();moveLatched=false;hudOpen=false;moveGestureMode=undefined;lastMoveTap=-100;
    stopHUD();cancelTapGesture();epoch++;connected=true;busy=false;sentButtons=0;
    if(sendTimer!==undefined){clearTimeout(sendTimer);sendTimer=undefined;}
    buttons=readButtons();states=[0,buttons];
    if(bias){calibrationLit=false;sleepGyro();updateLights();}else calibrate();
    resetMoveGesture();
  });});
  global.wandCircleScrolling=false;
  global.wandDoubleClickSeconds=0.3;
  // Ethan's independent lanes: Bottom = mouse, Middle = HUD/review, Top = speech.
  global.wandReviewTracking=false;global.wandDeskSleeping=false;
  // Keep legacy simultaneous-button scrolling out of the independent controls.
  checkScrollChord.replaceWith(function(){return false;});
  middlePress.replaceWith(function(){
    if(!connected)return;hudReportStarted=true;Bluetooth.println('@MIDDLE 1');
  });
  hudReport.replaceWith(function(){
    if(connected&&(hudOpen||global.wandReviewTracking))Bluetooth.println('@NAV '+Math.round(hudX*1000)+','+Math.round(hudY*1000));
  });
  setMouseFollow.replaceWith(function(on){
    // Release the device's native drag before forgetting its gesture state.
    // Otherwise a recording/mode change leaves sentButtons latched at one.
    if(dragging){dragging=false;states.push(0);pump();}
    cancelTapGesture();clearHoldClick();moveGestureMode=undefined;moveLatched=!!on;
    if(on&&global.wandDeskSleeping)global.setWandDeskSleeping(false);
    if(connected&&!global.wandDeskSleeping&&(moveLatched||hudOpen||global.wandReviewTracking))wakeGyro();else if(bias)sleepGyro();
    updateLights();
  });
  setHUDOpen.replaceWith(function(open){
    if(hudOpen===open){updateLights();return;}hudOpen=open;
    if(open||global.wandReviewTracking){
      if(hudTimer===undefined){hudX=0;hudY=0;hudTimer=setInterval(function(){hudReport();},30);}
    }else stopHUD();
    if(connected&&!global.wandDeskSleeping&&(moveLatched||hudOpen||global.wandReviewTracking))wakeGyro();else if(bias)sleepGyro();
    updateLights();
  });
  global.setWandReviewTracking=function(active){
    if(global.wandReviewTracking===!!active)return;
    global.wandReviewTracking=!!active;
    if(active){hudX=0;hudY=0;if(hudTimer===undefined)hudTimer=setInterval(function(){hudReport();},30);if(!global.wandDeskSleeping)wakeGyro();}
    else if(!hudOpen){stopHUD();if(!moveLatched)sleepGyro();}
  };
  // Keep the actual registered sensor callback, including its saved scope.
  var mh=Puck['#onaccel'];if(typeof mh==='function')mh=[mh];
  var mc=(mh||[]).filter(function(f){return typeof f==='function'&&f.toString().indexOf('var g=a.gyro')>=0;});
  if(mc.length!==1)throw Error('WAND_MOTION_CALLBACK_NOT_UNIQUE '+mc.length);
  global.wandLiveMotionCallback=mc[0];delete global.mh;delete global.mc;
  global.wandMotionReady=false;
  // Free the old function body before parsing its larger replacement. This
  // preserves the callback object and scope, including the calibrated zero.
  // Keep the discovery marker so an interrupted update can safely reapply.
  global.wandLiveMotionCallback.replaceWith(function(a){var g=a.gyro;});
  // HID is still byte-bounded. UART text carries wider counts so fast travel
  // is not thrown away before the Mac can clamp it to actual screens.
  pump.replaceWith(function(){});
  pump.replaceWith(function(){
  if (!connected || busy) return;
  var hasState=states.length>0;
  var b=hasState?states[0]:sentButtons;
  var limit=global.wandBridgeOriginalSend?4095:127;
  var x=hasState?0:Math.max(-limit,Math.min(limit,moveX));
  var y=hasState?0:Math.max(-limit,Math.min(limit,moveY));
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
});
  // Latency first: retain the accepted sensor rate and filter, reduce both
  // pointer axes by 20%, and keep a one-second sensor grace between gestures.
  // Pointer output still stops immediately; only sensor power-down is deferred.
  CONFIG.gain=86.4;
  // The 208 Hz trial stuttered on this workload; keep the smoother 104 Hz rate.
  CONFIG.sampleRate=104;
  // Holding Bottom is the precision gesture: use one-third of normal pointer
  // gain for temporary movement and real dragging. Released-button follow
  // keeps normal gain; HUD selection and the two-button scroll return earlier.
  CONFIG.heldPointerGain=1/3;
  // Ethan calls released-button follow HIGH sensitivity and a plain held
  // pointer gesture LOW sensitivity. LOW repositions; it does not hold a
  // mouse button. Release clicks, then HIGH pauses for 300 ms if it was
  // active before the hold. A real drag also resumes prior HIGH after dropping.
  CONFIG.releaseClickPause=0.3;
  // A radial angular tolerance absorbs hand tremor without filtering fast
  // travel. Re-centre quiet movement too, so residual bias cannot keep pushing
  // an anchor already at the edge after a sweep. These are starting values,
  // not measured hand-noise limits. Keep HUD and wheel angular input separate.
  CONFIG.slackDegrees=0.2;CONFIG.slackRecentre=0.35;CONFIG.slackQuietSpeed=1;
  global.wandSlackX=global.wandSlackY=0;
  // Pure motion calculation lives separately to keep each tokenised upload
  // statement small enough for the Puck's memory. No arrays per gyro sample.
  global.wandPointerSlack=(function(){
    // Private scalar state avoids repeated searches through the device's global
    // object. Reset on the same zero-slack boundary as the original algorithm.
    var ix=0,iy=0,is=0,it=0;
    return function(x,y,dt,speed,radius,recentre,quietSpeed){
      var g=global,m=Math,ox=g.wandSlackX,oy=g.wandSlackY;
      if(!ox&&!oy)ix=iy=is=it=0;
      var a=1-m.exp(-dt/0.15);
      ix+=a*(x-ix);iy+=a*(y-iy);is+=a*(speed-is);
      var mean=m.sqrt(ix*ix+iy*iy);
      it=mean>0.45&&mean>is*0.8?m.min(0.3,it+dt):m.max(0,it-dt*3);
      var active=speed>0.45&&it>=0.25;
      ox+=x*dt;oy+=y*dt;
      var om=m.sqrt(ox*ox+oy*oy),qx=0,qy=0;
      if(!active&&(om<=radius||speed<=quietSpeed)){var decay=m.exp(-dt/recentre);ox*=decay;oy*=decay;om*=decay;}
      if(om>radius){var excess=(om-radius)/om;qx=ox*excess;qy=oy*excess;ox-=qx;oy-=qy;}
      g.wandIntentActive=active;g.wandSlackX=ox;g.wandSlackY=oy;g.wandStepX=qx;g.wandStepY=qy;
    };
  })();
  global.wandPowerDownGyro=function(){
    if(connected&&bias)Puck.accelOn(1.6);else Puck.accelOff();gyroAwake=false;motionWarmup=0;lastTime=0;
    fractionX=fractionY=moveX=moveY=filteredX=filteredY=0;
    global.wandSlackX=global.wandSlackY=0;
  };
  wakeGyro.replaceWith(function(){
    if(global.wandSleepTimer!==undefined){clearTimeout(global.wandSleepTimer);global.wandSleepTimer=undefined;}
    if(gyroAwake)return;
    gyroAwake=true;motionWarmup=0;lastTime=getTime();global.wandMotionReadyAt=lastTime+0.096;
    filteredX=0;filteredY=0;motionStats={count:0,elapsed:0,maxGap:0};
    global.wandSlackX=global.wandSlackY=0;
    Puck.accelOn(CONFIG.sampleRate);
  });
  sleepGyro.replaceWith(function(){
    if(global.wandSleepTimer!==undefined){clearTimeout(global.wandSleepTimer);global.wandSleepTimer=undefined;}
    if(!connected||!bias){global.wandPowerDownGyro();return;}
    if(!gyroAwake){global.wandPowerDownGyro();return;}
    global.wandSleepTimer=setTimeout(function(){
      global.wandSleepTimer=undefined;
      if(!moveLatched&&!hudOpen&&!scrollHeld&&!global.wandReviewTracking)global.wandPowerDownGyro();
    },1000);
  });
  // A minute of confirmed desk rest is timed by the existing Mac detector.
  // Preserve the logical modes, recording and calibration. The accelerometer
  // stays at 1.6 Hz so pickup can wake it; this is not a Bluetooth disconnect.
  global.setWandDeskSleeping=function(on){
    if(on&&(!digitalRead(MOVE_PIN)||!digitalRead(HUD_PIN)||!digitalRead(STT_PIN)))return;
    if(global.wandDeskSleeping===!!on)return;
    global.wandDeskSleeping=!!on;
    if(on){
      if(global.wandSleepTimer!==undefined){clearTimeout(global.wandSleepTimer);global.wandSleepTimer=undefined;}
      if(hudTimer!==undefined){clearInterval(hudTimer);hudTimer=undefined;}
      global.wandPowerDownGyro();
    }else{
      if((hudOpen||global.wandReviewTracking)&&hudTimer===undefined)hudTimer=setInterval(function(){hudReport();},30);
      if(connected&&(moveLatched||hudOpen||global.wandReviewTracking))wakeGyro();
    }
    updateLights();
  };
  // Only accelerometer readings run on the desk (1.6 Hz, gyro off). The Mac
  // classifies pickup and set-down from this stream, never from pointer silence.
  // Active telemetry is capped at 10 Hz; accepted pointer processing stays 104 Hz.
  global.wandIMUNext=0;
  global.wandReportIMU=function(a,now){
    if(!connected||!bias||!a.acc||now<global.wandIMUNext)return;
    global.wandIMUNext=now+0.1;
    var q=a.acc,g=a.gyro,r=gyroAwake&&g?Math.sqrt(Math.pow((g.x-bias.x)/134,2)+Math.pow((g.y-bias.y)/134,2)+Math.pow((g.z-bias.z)/134,2)):0;
    Bluetooth.println('@IMU '+q.x+','+q.y+','+q.z+','+Math.round(r*100)+','+((!digitalRead(MOVE_PIN)||!digitalRead(HUD_PIN)||!digitalRead(STT_PIN))?1:0)+','+((moveLatched&&(global.wandSlackX!==0||global.wandSlackY!==0)&&global.wandIntentActive)?1:0)+','+((digitalRead(MOVE_PIN)?0:1)+(digitalRead(HUD_PIN)?0:2)+(digitalRead(STT_PIN)?0:4)));
  };
  // Pressing or releasing any grip switch can twist the wand. Only these
  // brief edges are guarded; steady aiming keeps the existing fast filter.
  if(global.wandNoiseGuardWatches)global.wandNoiseGuardWatches.forEach(function(id){try{clearWatch(id);}catch(e){}watches=watches.filter(function(w){return w!==id;});});
  global.wandNoiseGuardWatches=[MOVE_PIN,HUD_PIN,STT_PIN].map(function(pin){
    var id=setWatch(function(e){if(!e.state&&global.wandDeskSleeping)global.setWandDeskSleeping(false);global.wandSlackX=global.wandSlackY=0;global.wandSettleUntil=getTime()+(e.state?0.07:0.05);},pin,{edge:'both',repeat:true,debounce:20});
    watches.push(id);return id;
  });
  if(!global.wandRawPointer)global.wandLiveMotionCallback.replaceWith(function(a) {
  var g=a.gyro;
  var G=global,C=CONFIG,M=Math;
  var now=getTime();
  if(now>=G.wandIMUNext)G.wandReportIMU(a,now);
  if (!g || (!gyroAwake&&bias)) return;
  if (!bias) {
    if (now>calibrationDeadline) {calibrationLit=false;updateLights();sleepGyro();return;}
    if (warmup>0) {warmup--; return;}
    // Never learn a held/moving wand as its stationary zero.
    var stable=digitalRead(MOVE_PIN) && digitalRead(D2) && digitalRead(D30);
    ['x','y','z'].forEach(function(k) {
      restMin[k]=M.min(restMin[k],g[k]);
      restMax[k]=M.max(restMax[k],g[k]);
      if (M.abs(g[k])>8*134 || restMax[k]-restMin[k]>3*134) stable=false;
    });
    if (!stable) {
      sum={x:0,y:0,z:0}; sumSquares={x:0,y:0,z:0}; samples=0;
      restMin={x:g.x,y:g.y,z:g.z}; restMax={x:g.x,y:g.y,z:g.z};
      return;
    }
    sum.x+=g.x; sum.y+=g.y; sum.z+=g.z;
    sumSquares.x+=g.x*g.x;sumSquares.y+=g.y*g.y;sumSquares.z+=g.z*g.z;samples++;
    if (samples>=C.sampleRate*2) {
      bias={x:sum.x/samples,y:sum.y/samples,z:sum.z/samples};
      ["x","y","z"].forEach(function(k){
        noise[k]=M.max(0.25,M.min(C.deadZone,4*M.sqrt(M.max(0,sumSquares[k]/samples-bias[k]*bias[k]))/134));
      });
      calibrationLit=false;updateLights(); lastTime=now; motionWarmup=0;
      if(global.wandSaveCalibration)global.wandSaveCalibration(bias);print('WAND_CALIBRATED',JSON.stringify(bias));
      if (!connected || (!moveLatched && !hudOpen && digitalRead(MOVE_PIN))) sleepGyro();
    }
    return;
  }
  // Ignore the physical switch impulse; discard it instead of replaying it.
  // Cold sensor settling is time-based so dropped readings cannot stretch it.
  motionWarmup=0;
  if(now<(G.wandMotionReadyAt||0)||now<(G.wandSettleUntil||0)){
    G.wandSlackX=G.wandSlackY=0;
    lastTime=now;fractionX=fractionY=moveX=moveY=filteredX=filteredY=0;return;
  }
  var gap=M.max(0,now-lastTime),dt=M.min(0.05,gap);lastTime=now;
  motionStats.count++;motionStats.elapsed+=gap;if(gap>motionStats.maxGap)motionStats.maxGap=gap;
  if(scrollHeld){
    G.wandSlackX=G.wandSlackY=0;
    var sx=(g[C.xAxis]-bias[C.xAxis])/134,sy=(g[C.yAxis]-bias[C.yAxis])/134,sk=radialKeep(sx,sy);
    scrollX+=sx*sk*dt*C.xSign;scrollY+=sy*sk*dt*C.ySign;return;
  }
  if(scrollSuppress){G.wandSlackX=G.wandSlackY=0;return;}
  if((hudOpen||G.wandReviewTracking)&&connected){
    var hx=(g[C.xAxis]-bias[C.xAxis])/134,hy=(g[C.yAxis]-bias[C.yAxis])/134,keep=radialKeep(hx,hy);
    hudX+=hx*keep*dt*C.xSign;hudY+=hy*keep*dt*C.ySign;
  }
  if (!connected || !moveLatched || tapPending || now<(G.wandPointerPauseUntil||0) || (moveGestureMode==="pointer" && !dragging)) {
    G.wandSlackX=G.wandSlackY=0;
    fractionX=fractionY=moveX=moveY=filteredX=filteredY=0;return;
  }
  // Espruino documents raw gyro values / 134 as degrees per second.
  var px=(g[C.xAxis]-bias[C.xAxis])/134,py=(g[C.yAxis]-bias[C.yAxis])/134;
  // Time-based light smoothing: 8 ms for fine aim, 2 ms during fast sweeps.
  var speed=M.sqrt(px*px+py*py),blend=M.max(0,M.min(1,(speed-C.fineSpeed)/(C.fullSpeed-C.fineSpeed)));
  var alpha=1-M.exp(-dt/(0.008-0.006*blend));
  filteredX+=alpha*(px-filteredX);filteredY+=alpha*(py-filteredY);
  G.wandPointerSlack(filteredX,filteredY,dt,speed,C.slackDegrees,C.slackRecentre,C.slackQuietSpeed);
  var scale=C.fineGain+(1-C.fineGain)*blend*blend*(3-2*blend);
  if(!digitalRead(MOVE_PIN))scale*=C.heldPointerGain;
  fractionX+=G.wandStepX*C.gain*scale*C.xSign;
  fractionY+=G.wandStepY*C.gain*C.yGain*scale*C.ySign;
  var x=fractionX<0?M.ceil(fractionX):M.floor(fractionX);
  var y=fractionY<0?M.ceil(fractionY):M.floor(fractionY);
  fractionX-=x; fractionY-=y;
  var limit=G.wandBridgeOriginalSend?4095:127;
  moveX=M.max(-limit,M.min(limit,moveX+x));
  moveY=M.max(-limit,M.min(limit,moveY+y));
  pump();

  });
  // Keep the shared host wheel gain unchanged. Ethan asked for stronger
  // sideways scrolling to match vertical feel; compensate only that axis.
  global.wandHorizontalScrollBoost=1.4;
  scrollReport.replaceWith(function(phase){
    if(connected)Bluetooth.println('@SCROLL '+phase+','+Math.round(scrollX*1000*global.wandHorizontalScrollBoost)+','+Math.round(scrollY*1000));
  });
  // These are mode indicators, not just button-down lights. Recording remains
  // red after release only if neither pointer, HUD nor scroll has priority.
  // Remove the prior animation when updating a running bridge.
  if(global.wandRecordingBlinkTimer!==undefined){clearInterval(global.wandRecordingBlinkTimer);delete global.wandRecordingBlinkTimer;}
  delete global.wandRecordingBlinkRed;
  global.wandLastFollow=undefined;
  updateLights.replaceWith(function(){
    if(connected&&global.wandLastFollow!==moveLatched){global.wandLastFollow=moveLatched;Bluetooth.println('@FOLLOW '+(moveLatched?1:0));}
    var move=moveLatched||!digitalRead(MOVE_PIN),hud=hudOpen||!digitalRead(HUD_PIN);
    var mode=(global.WAND_UPDATING||global.wandMotionReady===false)?'update':!connected?'disconnected':(!bias||calibrationLit)?'calibration':global.wandDeskSleeping?'sleep':(scrollHeld||global.wandCircleScrolling)?'scroll':global.wandAppMode?'app':move?'mouse':hud?'hud':(global.wandRecording||!digitalRead(STT_PIN))?'recording':'idle';
    lightLevels=mode==='update'||mode==='calibration'||mode==='disconnected'?[0.45,0.45,0.45]:mode==='recording'?[1,0,0]:mode==='scroll'?[0,1,1]:mode==='app'?(global.wandReviewFiles?[1,0,1]:[0,1,0]):mode==='mouse'?[0,0,1]:mode==='hud'?[1,0.2,0]:[0,0,0];
    writeLight(LED1,lightLevels[0]);writeLight(LED2,lightLevels[1]);writeLight(LED3,lightLevels[2]);
    if(connected&&mode!==global.wandLastLightState){global.wandLastLightState=mode;print('WAND_LIGHT_STATE '+mode+' '+JSON.stringify(lightLevels));}
  });
  // From mouse-off: a short tap enters latched follow without clicking. A hold
  // moves temporarily, then release clicks once at the endpoint and stops.
  // If HIGH was already active, LOW release clicks and holds that point for
  // 300 ms before HIGH resumes. Starting LOW from off returns to off.
  // Click then hold is the explicit real drag; release drops, then resumes prior HIGH.
  // A single short press exits HIGH; stopping after travel clicks on the Mac.
  // Keep the preceding short tap available for explicit tap-then-hold dragging.
  // Free the prior button body too: repeated live updates can exhaust Puck RAM.
  global.wandLiveMoveCallback.replaceWith(function(){if(false)clearHoldClick();});
  // Small helpers inherit the registered callback's saved boot scope.
  // This keeps peak parser memory below the monolithic button handler.
  global.wandLiveMoveCallback.replaceWith(function(){
    global.wandBottomPress=function(){
      if(!bias)calibrate();
      global.wandPressStarted=getTime();
      global.wandFollowBeforeHold=moveLatched||!!(global.wandExitFollow&&getTime()-lastMoveTap<=global.wandDoubleClickSeconds);global.wandExitFollow=false;
      global.wandPointerPauseUntil=0;
      moveGestureMode=moveLatched?'pointer':'enable';
      global.wandMomentaryStarted=moveGestureMode==='enable'?getTime():undefined;
      if(moveGestureMode==='enable'){
        moveLatched=true;
        if(connected)wakeGyro();
      }
      // Remember the previous tap for the Mac's full double-click window, even
      // if its ordinary click has already been posted after the short delay.
      global.wandDragCandidate=tapPending||(getTime()-lastMoveTap<=global.wandDoubleClickSeconds);
      print('WAND_BUTTON_STATE '+JSON.stringify({edge:'down',mode:moveGestureMode,follow:moveLatched,dragCandidate:global.wandDragCandidate}));
      lastMoveTap=-100;
      secondTap=tapPending;
      if(tapTimer!==undefined)clearTimeout(tapTimer);
      tapTimer=undefined;tapPending=false;moveClickFired=false;
      clearHoldClick();holdClickTimer=setTimeout(function(){
        holdClickTimer=undefined;
        if(digitalRead(MOVE_PIN)||!connected||!bias||(moveGestureMode!=='pointer'&&!(moveGestureMode==='enable'&&global.wandDragCandidate)))return;
        moveClickFired=true;
        if(global.wandDragCandidate){moveGestureMode='pointer';dragging=true;states.push(1);pump();}
        else moveGestureMode='clutch';
        wakeGyro();
      },CONFIG.tapSeconds*1000);
      // No redundant terminal return: the saved flash-backed handler must
      // finish normally at the end of its source on the Puck interpreter.
      updateLights();

    };
  });
  global.wandLiveMoveCallback();
  global.wandLiveMoveCallback.replaceWith(function(){
    global.wandBottomRelease=function(){
    clearHoldClick();
    if(moveGestureMode==='operation'){pointerReport('E');stopPointerTrack();}
    else if(moveGestureMode==='clutch'){
      moveLatched=!!global.wandFollowBeforeHold;cancelTapGesture();lastMoveTap=-100;
      global.wandPointerPauseUntil=getTime()+CONFIG.releaseClickPause;
      clickTimes(1);
    }
    else if(moveGestureMode==='enable'){
      moveLatched=global.wandMomentaryStarted===undefined||getTime()-global.wandMomentaryStarted<CONFIG.tapSeconds;
      if(moveLatched)lastMoveTap=getTime();else clickTimes(1);
    }else if(moveGestureMode==='pointer'){
      if(dragging){dragging=false;states.push(0);pump();moveLatched=!!global.wandFollowBeforeHold;global.wandPointerPauseUntil=getTime()+CONFIG.releaseClickPause;cancelTapGesture();}
      else {moveLatched=false;global.wandExitFollow=true;cancelTapGesture();lastMoveTap=getTime();}
    }
    print('WAND_BUTTON_STATE '+JSON.stringify({mode:moveGestureMode,ms:Math.round((getTime()-global.wandPressStarted)*1000),follow:moveLatched}));
    global.wandMomentaryStarted=undefined;global.wandDragCandidate=false;global.wandFollowBeforeHold=false;moveGestureMode=undefined;secondTap=false;
    // A short exit tap may be followed by the held second press of a real drag.
    if((moveLatched||hudOpen||global.wandReviewTracking)&&connected)wakeGyro();else if(bias)sleepGyro();
    updateLights();

    };
  });
  global.wandLiveMoveCallback();
  global.wandLiveMoveCallback.replaceWith(function(){
    if(connected)Bluetooth.println('@BOTTOM '+(digitalRead(MOVE_PIN)?0:1));
    if(!digitalRead(MOVE_PIN)&&digitalRead(HUD_PIN)&&!scrollSuppress)chordFollowBefore=moveLatched;
    if(checkScrollChord()){global.wandMomentaryStarted=undefined;return;}
    moveX=moveY=fractionX=fractionY=filteredX=filteredY=0;
    global.wandSlackX=global.wandSlackY=0;
    // Discovery marker for the registered watch.
    if(false)clearHoldClick();
    if(!digitalRead(MOVE_PIN))global.wandBottomPress();else global.wandBottomRelease();
  });
  // Expose the same scoped functions to receiver commands; never a second copy
  // of mode state. Recording changes do not wake the motion sensor.
  global.setHUDOpen=setHUDOpen;global.updateLights=updateLights;global.setMouseFollow=setMouseFollow;
  global.restoreWandCalibration=function(value){
    if(!value||!isFinite(value.x)||!isFinite(value.y)||!isFinite(value.z))return;
    bias={x:value.x,y:value.y,z:value.z};calibrationLit=false;
    global.wandSlackX=global.wandSlackY=0;
    fractionX=fractionY=moveX=moveY=filteredX=filteredY=0;
    if(moveLatched||hudOpen)wakeGyro();else sleepGyro();updateLights();
    if(global.wandSaveCalibration)global.wandSaveCalibration(bias);print('WAND_CALIBRATED',JSON.stringify(bias));
  };
  global.wandState=function(){return {calibrated:!!bias,move:moveLatched,hud:hudOpen,gyro:gyroAwake,bias:bias,light:lightLevels};};
  global.setWandRecording=function(active){global.wandRecording=!!active;updateLights();print('WAND_RECORDING_LIGHT '+(active?'1':'0'));};
  if(connected&&bias&&!gyroAwake)global.wandPowerDownGyro();
  // Do not advertise a working mouse after an interrupted or partial upload.
  global.wandMotionReady=global.wandLiveMotionCallback.toString().indexOf('wandPointerSlack')>=0;
  if(gyroAwake)Puck.accelOn(CONFIG.sampleRate);
  updateLights();
  if(global.wandMotionReady)print('WAND_MODE_ROUTING_READY');else print('WAND_UPDATE_FAILED');

// The native receiver opts in before loading. Free the interpreted pointer
// calculation before allocating this shorter callback; other hosts keep it.
if(global.wandRawPointer){global.wandLiveMotionCallback.replaceWith(function(a){var g=a.gyro;});delete global.wandPointerSlack;global.wandRawBias=undefined;global.wandRawActive=false;};
if(global.wandRawPointer){
  global.wandLiveMotionCallback.replaceWith(function(){
    global.wandCalibrateSample=function(g,now){var C=CONFIG,M=Math;
    if (now>calibrationDeadline) {calibrationLit=false;updateLights();sleepGyro();return;}
    if (warmup>0) {warmup--; return;}
    // Never learn a held/moving wand as its stationary zero.
    var stable=digitalRead(MOVE_PIN) && digitalRead(D2) && digitalRead(D30);
    ['x','y','z'].forEach(function(k) {
      restMin[k]=M.min(restMin[k],g[k]);
      restMax[k]=M.max(restMax[k],g[k]);
      if (M.abs(g[k])>8*134 || restMax[k]-restMin[k]>3*134) stable=false;
    });
    if (!stable) {
      sum={x:0,y:0,z:0}; sumSquares={x:0,y:0,z:0}; samples=0;
      restMin={x:g.x,y:g.y,z:g.z}; restMax={x:g.x,y:g.y,z:g.z};
      return;
    }
    sum.x+=g.x; sum.y+=g.y; sum.z+=g.z;
    sumSquares.x+=g.x*g.x;sumSquares.y+=g.y*g.y;sumSquares.z+=g.z*g.z;samples++;
    if (samples>=C.sampleRate*2) {
      bias={x:sum.x/samples,y:sum.y/samples,z:sum.z/samples};
      ["x","y","z"].forEach(function(k){
        noise[k]=M.max(0.25,M.min(C.deadZone,4*M.sqrt(M.max(0,sumSquares[k]/samples-bias[k]*bias[k]))/134));
      });
      calibrationLit=false;updateLights(); lastTime=now; motionWarmup=0;
      if(global.wandSaveCalibration)global.wandSaveCalibration(bias);print('WAND_CALIBRATED',JSON.stringify(bias));
      if (!connected || (!moveLatched && !hudOpen && digitalRead(MOVE_PIN))) sleepGyro();
    }
    return;
  };
  });
  global.wandLiveMotionCallback();
}
if(global.wandRawPointer)global.wandLiveMotionCallback.replaceWith(function(a) {
  var g=a.gyro,rawReset=!global.wandRawActive;global.wandRawActive=false;
  var G=global,C=CONFIG,M=Math;
  var now=getTime();
  if(now>=G.wandIMUNext)G.wandReportIMU(a,now);
  if (!g || (!gyroAwake&&bias)) return;
  if (!bias) {G.wandCalibrateSample(g,now);return;}
  // Ignore the physical switch impulse; discard it instead of replaying it.
  // Cold sensor settling is time-based so dropped readings cannot stretch it.
  motionWarmup=0;
  if(now<(G.wandMotionReadyAt||0)||now<(G.wandSettleUntil||0)){
    G.wandSlackX=G.wandSlackY=0;
    lastTime=now;fractionX=fractionY=moveX=moveY=filteredX=filteredY=0;return;
  }
  var gap=M.max(0,now-lastTime),dt=M.min(0.05,gap);lastTime=now;
  motionStats.count++;motionStats.elapsed+=gap;if(gap>motionStats.maxGap)motionStats.maxGap=gap;
  if(scrollHeld){
    G.wandSlackX=G.wandSlackY=0;
    var sx=(g[C.xAxis]-bias[C.xAxis])/134,sy=(g[C.yAxis]-bias[C.yAxis])/134,sk=radialKeep(sx,sy);
    scrollX+=sx*sk*dt*C.xSign;scrollY+=sy*sk*dt*C.ySign;return;
  }
  if(scrollSuppress){G.wandSlackX=G.wandSlackY=0;return;}
  if((hudOpen||G.wandReviewTracking)&&connected){
    var hx=(g[C.xAxis]-bias[C.xAxis])/134,hy=(g[C.yAxis]-bias[C.yAxis])/134,keep=radialKeep(hx,hy);
    hudX+=hx*keep*dt*C.xSign;hudY+=hy*keep*dt*C.ySign;
  }
  if (!connected || (!moveLatched && !hudOpen) || tapPending || now<(G.wandPointerPauseUntil||0) || (moveGestureMode==="pointer" && !dragging)) {
    G.wandSlackX=G.wandSlackY=0;
    fractionX=fractionY=moveX=moveY=filteredX=filteredY=0;return;
  }
  if(G.wandRawBias!==bias){Bluetooth.println('@ZERO '+JSON.stringify([bias[C.xAxis],bias[C.yAxis],C.gain,C.yGain,C.fineGain,C.fineSpeed,C.fullSpeed,C.heldPointerGain,C.slackDegrees,C.slackRecentre,C.slackQuietSpeed,C.xSign,C.ySign]));G.wandRawBias=bias;}
  // Bit 4 supplies HIGH sensitivity to the HUD without moving an inactive pointer.
  var flags=(digitalRead(MOVE_PIN)?0:1)+(rawReset?2:0)+(moveLatched?0:4);G.wandRawActive=true;
  Bluetooth.println('@RAW '+M.max(1,M.round(dt*1000000))+','+g[C.xAxis]+','+g[C.yAxis]+','+flags);
});
if(global.wandRawPointer)global.wandMotionReady=global.wandLiveMotionCallback.toString().indexOf('@RAW ')>=0;
