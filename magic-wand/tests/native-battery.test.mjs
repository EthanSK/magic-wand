import test from 'node:test';
import assert from 'node:assert/strict';
import {readFileSync,writeFileSync,mkdtempSync,rmSync} from 'node:fs';
import {fileURLToPath} from 'node:url';
import {join} from 'node:path';
import {tmpdir} from 'node:os';
import {spawnSync} from 'node:child_process';
test('battery queries use existing transport and reject malformed readings',{skip:process.platform!=='darwin'},()=>{
 const source=readFileSync(new URL('../receiver/Sources/main.swift',import.meta.url),'utf8');
 function method(name){const a=source.indexOf('    func '+name+'(');assert(a>=0,name);let b=source.indexOf('{',a)+1,depth=1;while(depth){if(source[b]==='{')depth++;if(source[b]==='}')depth--;b++;}return source.slice(a,b);}
 const code=`import Foundation
import CoreFoundation
func log(_ values:Any...) {}
final class Harness {
 var batteryPercent:Int?,batteryVolts:Double?,batterySampleAt:Date?,batteryRequested=Date.distantPast
 var ready=true,restoring=false,deskSleep=WandDeskSleep(),commands:[String]=[],updates=0
 func queue(_ s:String){commands.append(s)}
 func status(){updates+=1}
 ${['requestBattery','handleBattery'].map(method).join('\n')}
}
let h=Harness();h.requestBattery();h.requestBattery()
precondition(h.commands.count==1 && h.commands[0].contains("NRF.getBattery()"))
h.handleBattery(#"{"percent":72,"volts":2.91}"#)
precondition(h.batteryPercent==72 && h.batteryVolts==2.91 && h.batterySampleAt != nil && h.updates==1)
for bad in [#"{"percent":true,"volts":2.91}"#,#"{"percent":999,"volts":2.91}"#,#"{"percent":72,"volts":999}"#,"bad"]{h.handleBattery(bad)}
precondition(h.batteryPercent==72 && h.updates==1,"bad packets cannot replace the last valid reading")
h.ready=false;h.batteryRequested = .distantPast;h.requestBattery();precondition(h.commands.count==1)
print("PASS bounded battery polling and readings")
`;
 const dir=mkdtempSync(join(tmpdir(),'wand-battery-'));
 try{writeFileSync(join(dir,'main.swift'),code);const build=spawnSync('swiftc',['-O',fileURLToPath(new URL('../receiver/Sources/WandPointerControl.swift',import.meta.url)),join(dir,'main.swift'),'-o',join(dir,'check')],{encoding:'utf8'});assert.equal(build.status,0,build.stderr);const r=spawnSync(join(dir,'check'),[],{encoding:'utf8'});assert.equal(r.status,0,r.stdout+r.stderr);}finally{rmSync(dir,{recursive:true,force:true});}
});
