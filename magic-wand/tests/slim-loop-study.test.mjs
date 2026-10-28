import { test } from 'node:test';
import { execFileSync } from 'node:child_process';
import { fileURLToPath } from 'node:url';

test('slim loop studies retain their checked meshes and Bambu projects', () => {
  const script = fileURLToPath(new URL('../hardware/printed-loop-wand/slim-loop-study/verify_release.py', import.meta.url));
  execFileSync('python3', [script], { stdio: 'pipe' });
});
