import test from 'node:test';
import {execFileSync} from 'node:child_process';
import {fileURLToPath} from 'node:url';
test('local Sense bridge validates frames, expires live state and gives USB priority',()=>{
 execFileSync('python3',['-B','test_bridge.py'],{cwd:fileURLToPath(new URL('../hardware/xiao-wand-dashboard/',import.meta.url)),stdio:'pipe'});
});
