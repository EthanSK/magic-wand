import {test} from 'node:test';
import {execFileSync} from 'node:child_process';
import {fileURLToPath} from 'node:url';

test('continuous V19 wand preserves Sunny’s grip and checked print files', () => {
  const script = fileURLToPath(new URL('../hardware/printed-loop-wand/continuous-two-wide-v19/verify_release.py', import.meta.url));
  execFileSync('python3', [script], {stdio:'pipe'});
});
