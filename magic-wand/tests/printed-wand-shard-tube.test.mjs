import {test} from 'node:test';
import {execFileSync} from 'node:child_process';
import {fileURLToPath} from 'node:url';

test('sharper tube preserves the tip sensor, V20 grip and checked print files', () => {
  const script = fileURLToPath(new URL('../hardware/printed-loop-wand/shard-tube/verify_release.py', import.meta.url));
  execFileSync('python3', [script], {stdio:'pipe'});
});
