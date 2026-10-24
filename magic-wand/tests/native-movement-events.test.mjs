import test from 'node:test';
import assert from 'node:assert/strict';
import {readFileSync,writeFileSync,mkdtempSync,mkdirSync,rmSync} from 'node:fs';
import {tmpdir} from 'node:os';
import {join} from 'node:path';
import {fileURLToPath} from 'node:url';
import {spawnSync} from 'node:child_process';
test('native pointer and drag events carry movement distance and final position',{skip:process.platform!=='darwin'},()=>{
 const source=readFileSync(new URL('../receiver/Sources/main.swift',import.meta.url),'utf8');
 const a=source.indexOf('    static func mouseMovementEvent(');assert(a>=0);
 let b=source.indexOf('{',a)+1,depth=1;while(depth){if(source[b]==='{')depth++;if(source[b]==='}')depth--;b++;}
 const code=`import CoreGraphics
final class Events {
${source.slice(a,b)}
}
for (buttons,kind) in [(0,CGEventType.mouseMoved),(1,.leftMouseDragged),(2,.rightMouseDragged)] {
 let from=CGPoint(x:100,y:100),to=CGPoint(x:135,y:88)
 let event=Events.mouseMovementEvent(buttons:buttons,from:from,to:to)!
 precondition(event.type==kind && event.location==to)
 precondition(event.getIntegerValueField(.mouseEventDeltaX)==35)
 precondition(event.getIntegerValueField(.mouseEventDeltaY) == -12)
}
let edge=Events.mouseMovementEvent(buttons:1,from:CGPoint(x:995,y:100),to:CGPoint(x:999,y:100))!
precondition(edge.getIntegerValueField(.mouseEventDeltaX)==4,"delta is actual clamped movement")
let still=Events.mouseMovementEvent(buttons:1,from:.zero,to:.zero)!
precondition(still.getIntegerValueField(.mouseEventDeltaX)==0 && still.getIntegerValueField(.mouseEventDeltaY)==0)
`;
 const root=mkdtempSync(join(tmpdir(),'wand-event-')),dir=join(root,'build.noindex');mkdirSync(dir);
 try {writeFileSync(join(dir,'main.swift'),code);const c=spawnSync('swiftc',[join(dir,'main.swift'),'-o',join(dir,'check')],{encoding:'utf8'});assert.equal(c.status,0,c.stderr);const r=spawnSync(join(dir,'check'),[],{encoding:'utf8'});assert.equal(r.status,0,r.stdout+r.stderr);} finally {rmSync(root,{recursive:true,force:true});}
});
