// Exercise the real temporary update lease and desk-sleep policy without
// connecting to hardware or sending any operating-system input.
import test from 'node:test';
import assert from 'node:assert/strict';
import {readFileSync,writeFileSync,mkdtempSync,rmSync} from 'node:fs';
import {tmpdir} from 'node:os';
import {join} from 'node:path';
import {spawnSync} from 'node:child_process';

test('temporary update work prevents automatic standby, expires safely and preserves dark idle', {skip:process.platform!=='darwin'},()=>{
 const source=readFileSync(new URL('../receiver/Sources/WandPointerControl.swift',import.meta.url),'utf8');
 const start=source.indexOf('struct WandDeskSleep {');
 const end=source.indexOf('\n}\n',start)+2;
 assert(start>=0 && end>start);
 const main=`import Foundation
import Darwin
${source.slice(start,end)}
let root=URL(fileURLWithPath:CommandLine.arguments[1]), file=root.appendingPathComponent(WandUpdateWork.fileName)
func lease(_ text:String,mode:Int=0o600) throws {
 try Data(text.utf8).write(to:file,options:.atomic)
 try FileManager.default.setAttributes([.posixPermissions:mode],ofItemAtPath:file.path)
}
var work=WandUpdateWork()
precondition(!work.refresh(from:file,now:1000))
try lease("{\\"version\\":1,\\"expiresAt\\":1900}")
precondition(work.refresh(from:file,now:1000) && work.active(at:1000))
precondition(!work.refresh(from:file,now:1001),"same lease does not restart the policy")
var rest=WandDeskSleep(); rest.keepAwakeForUpdate(until:900,now:0)
for t in stride(from:0.0,through:899.0,by:1) { _=rest.sample(parked:true,buttons:false,now:t) }
precondition(rest.sleeping && !rest.deepSleeping,"idle stays dark, radio remains reachable")
rest.reset()
for t in stride(from:600.0,through:899.0,by:1) { _=rest.sample(parked:true,buttons:false,now:t) }
precondition(!rest.deepSleeping,"a reconnect/reset does not discard active work")
for t in stride(from:900.0,through:1200.0,by:1) { _=rest.sample(parked:true,buttons:false,now:t) }
precondition(rest.deepSleeping,"expiry gives normal five minutes before standby")
rest.keepAwakeForUpdate(until:nil,now:1200)
_=rest.sample(parked:true,buttons:false,now:1201)
precondition(rest.sleeping && !rest.deepSleeping,"clearing work preserves dark idle")
precondition(work.refresh(from:file,now:1900) && !work.active(at:1900))
try lease("{\\"version\\":1,\\"expiresAt\\":1900}")
precondition(work.refresh(from:file,now:1000))
try lease("{\\"version\\":1,\\"expiresAt\\":0}")
precondition(work.refresh(from:file,now:1000) && !work.active(at:1000),"explicit end clears work")
for value in ["{\\"version\\":true,\\"expiresAt\\":1900}","{\\"version\\":1,\\"expiresAt\\":true}","{\\"version\\":1,\\"expiresAt\\":9000}","{\\"version\\":1,\\"expiresAt\\":1900,\\"extra\\":1}","bad"] {
 try lease(value);precondition(WandUpdateWork.read(from:file,now:1000)==0)
}
try lease("{\\"version\\":1,\\"expiresAt\\":1900}",mode:0o644)
precondition(WandUpdateWork.read(from:file,now:1000)==0,"shared lease rejected")
try FileManager.default.removeItem(at:file)
try FileManager.default.createSymbolicLink(at:file,withDestinationURL:root.appendingPathComponent("target"))
precondition(WandUpdateWork.read(from:file,now:1000)==0,"symlink rejected")
print("PASS bounded update work, receiver restart, expiry, cancellation and unsafe files")
`;
 const dir=mkdtempSync(join(tmpdir(),'wand-update-work.noindex-'));
 try {
  writeFileSync(join(dir,'main.swift'),main);
  const native=new URL('../receiver/Sources/WandUpdateWork.swift',import.meta.url).pathname;
  const build=spawnSync('swiftc',[native,join(dir,'main.swift'),'-o',join(dir,'test')],{encoding:'utf8'});
  assert.equal(build.status,0,build.stderr);
  const run=spawnSync(join(dir,'test'),[dir],{encoding:'utf8'});
  assert.equal(run.status,0,run.stdout+run.stderr);
 }finally{rmSync(dir,{recursive:true,force:true});}
});
