// Button-wake standby: sensors and Bluetooth off, GPIO watches retained.
// Ethan's custom grip buttons are D1 (Bottom), D2 (Middle), D30 (Top).
// The host requests this only after five minutes of confirmed desk rest.
// Ethan: "Just before the wand goes to sleep ... flash all the colours twice."
// All three LEDs pulse together twice (100 ms on, 100 ms off), then standby.
// A grip press or a Mac connecting cancels the warning; a disconnect does not.
// A repeated request never restarts it. Only actual entry prints ENTERED.
// g is global: the short alias keeps this within the Puck's flash budget.
if(global.WAND_POWER_POLICY_VERSION!==4)(function(g){
  if(g.wandPowerWatches){g.wandPowerWatches.forEach(function(id){try{clearWatch(id);}catch(e){}});g.wandPowerClearTimer();NRF.removeListener('disconnect',g.wandPowerDisconnected);NRF.removeListener('connect',g.wandPowerConnectedEvent);}
  g.wandPowerOfflineTimer=g.wandPowerOfflineDeepTimer=g.wandPowerWarnTimer=g.wandPowerWarnPhase=undefined;
  g.wandPowerStandby=false;
  g.wandPowerConnected=function(){return !!NRF.getSecurityStatus().connected;};
  g.wandPowerHeld=function(){return !digitalRead(D1)||!digitalRead(D2)||!digitalRead(D30);};
  g.wandPowerClearTimer=function(){if(g.wandPowerOfflineTimer!==undefined)clearTimeout(g.wandPowerOfflineTimer);if(g.wandPowerOfflineDeepTimer!==undefined)clearTimeout(g.wandPowerOfflineDeepTimer);g.wandPowerOfflineTimer=g.wandPowerOfflineDeepTimer=undefined;};
  // allLights is the base program's shared three-LED writer; writing also ends
  // any loading blink, so darkness and the sleep warning own the lights.
  g.wandPowerDark=function(){allLights(0);Puck.accelOff();};
  g.wandPowerArmOffline=function(){g.wandPowerClearTimer();if(!g.wandPowerConnected()&&!g.wandPowerStandby){g.wandPowerOfflineTimer=setTimeout(function(){g.wandPowerOfflineTimer=undefined;if(!g.wandPowerConnected()&&!g.wandPowerHeld())g.wandPowerDark();},60000);g.wandPowerOfflineDeepTimer=setTimeout(function(){g.wandPowerOfflineDeepTimer=undefined;if(!g.wandPowerConnected())g.wandEnterDeepStandby();},300000);}};
  g.wandPowerDisconnected=function(){if(g.wandPowerStandby)setTimeout(g.wandPowerDark,0);else g.wandPowerArmOffline();};
  g.wandPowerWarnCancel=function(){if(g.wandPowerWarnTimer!==undefined)clearTimeout(g.wandPowerWarnTimer);g.wandPowerWarnTimer=undefined;if(g.wandPowerWarnPhase===undefined)return;g.wandPowerWarnPhase=undefined;updateLights();print('WAND_POWER_STANDBY_CANCELLED');};
  g.wandPowerConnectedEvent=function(){g.wandPowerClearTimer();if(!g.wandPowerManual){g.wandPowerWarnCancel();g.wandPowerStandby=false;}};
  // Ethan's all-three grip chord toggles power once until every button is up.
  // Any single grip button wakes both manual and automatic sleep, without firing its action.
  g.wandPowerInputGuard=function(){
    var n=7-digitalRead(D1)-2*digitalRead(D2)-4*digitalRead(D30);
    if(g.wandChord){if(!n)g.wandChord=false;return true;}
    if((g.wandPowerStandby||g.wandPowerManual)&&n){g.wandChord=true;g.wandPowerManual=false;g.wandPowerWarnCancel();g.wandPowerStandby=false;NRF.wake();return true;}
    if(n===7){
      g.wandChord=true;
      g.wandPowerWarnCancel();g.wandPowerManual=true;g.wandPowerClearTimer();g.wandPowerWarnPhase=0;g.wandPowerWarn();
      return true;
    }
    return !!g.wandPowerManual;
  };
  g.wandPowerButton=function(e){if(g.wandPowerInputGuard())return;if(!e.state){g.wandPowerWarnCancel();if(g.wandPowerStandby){g.wandPowerStandby=false;NRF.wake();}}if(!g.wandPowerConnected())g.wandPowerArmOffline();};
  g.wandPowerWatches=[D1,D2,D30].map(function(pin){return setWatch(g.wandPowerButton,pin,{edge:'both',repeat:true,debounce:20});});
  NRF.on('disconnect',g.wandPowerDisconnected);
  NRF.on('connect',g.wandPowerConnectedEvent);
  g.wandPowerWarn=function(){var n=g.wandPowerWarnPhase;g.wandPowerWarnTimer=undefined;if(n===undefined)return;if(!g.wandPowerManual&&g.wandPowerHeld())return g.wandPowerWarnCancel();g.wandPowerWarnPhase=n+1;if(n<4){allLights(n&1?0:1);g.wandPowerWarnTimer=setTimeout(g.wandPowerWarn,100);return;}g.wandPowerWarnPhase=undefined;g.wandPowerClearTimer();g.wandPowerStandby=true;g.wandPowerDark();g.wandPowerSleeps=(g.wandPowerSleeps|0)+1;print('WAND_POWER_STANDBY_ENTERED');NRF.sleep();};
  g.wandEnterDeepStandby=function(){if(g.wandPowerHeld())return false;if(g.wandPowerWarnPhase===undefined&&!g.wandPowerStandby){g.wandPowerWarnPhase=0;g.wandPowerWarn();}return true;};
  g.WAND_POWER_POLICY_VERSION=4;
})(global);
if(!global.wandPowerConnected())global.wandPowerArmOffline();
print('WAND_POWER_POLICY_READY');
