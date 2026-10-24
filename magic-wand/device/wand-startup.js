NRF.sleep();
var mouse=require("ble_hid_mouse");
NRF.setServices(undefined,{hid:mouse.report});
NRF.setAdvertising([{},[2,1,6,3,3,0x12,0x18,3,0x19,0xc2,0x03]]);
var watches=[],sendTimer,onMotion=function(){},onConnect=function(){},onDisconnect=function(){};
var s=require('Storage');
eval(s.read('wand.boot.v4'));
onInit();
global.wandRawPointer=true;
global.wandSaveCalibration=function(v){if(!v||!isFinite(v.x)||!isFinite(v.y)||!isFinite(v.z)||Math.abs(v.x)>1072||Math.abs(v.y)>1072||Math.abs(v.z)>1072)return;var j=JSON.stringify({x:v.x,y:v.y,z:v.z});if(s.read('wand.zero')!==j)s.write('wand.zero',j);};
eval(s.read('wand.bridge.p1'));
eval(s.read('wand.power.p1'));
try{var z=s.readJSON('wand.zero',1);if(z)global.restoreWandCalibration(z);delete global.z;}catch(e){print('WAND_SAVED_ZERO_INVALID');}
global.WAND_RUNTIME_VERSION='__WAND_RUNTIME__';
global.WAND_BRIDGE_REVISION="__WAND_BRIDGE__";global.WAND_PERSISTENT_IMAGE='__WAND_PERSISTENT__';global.onInit=undefined;global.WAND_UPDATING=false;NRF.wake();updateLights();
