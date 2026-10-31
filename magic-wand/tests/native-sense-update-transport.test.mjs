import test from 'node:test';
import assert from 'node:assert/strict';
import {mkdtempSync, readFileSync, writeFileSync, rmSync} from 'node:fs';
import {tmpdir} from 'node:os';
import {join} from 'node:path';
import {fileURLToPath} from 'node:url';
import {spawnSync} from 'node:child_process';

// Replace only the OS boundary in a disposable test copy. The production link
// and transfer methods themselves run against fake CoreBluetooth objects.
test('Sense update transport runs on fake Bluetooth without accessing hardware', {skip:process.platform!=='darwin'},()=>{
 const dir=mkdtempSync(join(tmpdir(),'wand-update-transport-'));
 try {
  const source=(name)=>fileURLToPath(new URL(`../receiver/Sources/${name}`,import.meta.url));
  let link=readFileSync(source('WandSenseLink.swift'),'utf8').replace('import CoreBluetooth\n','');
  const start=link.indexOf('    private func openUSBIfPresent() {');
  assert(start>=0);let end=start+link.slice(start).indexOf('{')+1,depth=1;
  for(;end<link.length&&depth;end++){if(link[end]==='{')depth++;if(link[end]==='}')depth--;}
  assert.equal(depth,0);
  link=link.slice(0,start)+'    private func openUSBIfPresent() { TestHardware.usbPolls += 1 }'+link.slice(end);
  writeFileSync(join(dir,'WandSenseLink.swift'),link);
  writeFileSync(join(dir,'WandSenseUpdate.swift'),readFileSync(source('WandSenseUpdate.swift'),'utf8').replace('import CoreBluetooth\n',''));
  writeFileSync(join(dir,'main.swift'),readFileSync(new URL('native-sense-update-transport-main.swift',import.meta.url)));
  const built=spawnSync('swiftc',['-O',source('WandSenseProtocol.swift'),source('WandCalibration.swift'),join(dir,'WandSenseUpdate.swift'),join(dir,'WandSenseLink.swift'),join(dir,'main.swift'),'-o',join(dir,'check')],{encoding:'utf8'});
  assert.equal(built.status,0,built.stderr);
  const ran=spawnSync(join(dir,'check'),[],{encoding:'utf8',timeout:30000});
  assert.equal(ran.status,0,ran.stderr+ran.stdout);
  assert.match(ran.stdout,/PASS: real updater\/link orchestration/);
 } finally {rmSync(dir,{recursive:true,force:true});}
});
