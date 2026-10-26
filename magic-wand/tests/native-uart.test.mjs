import test from 'node:test';
import assert from 'node:assert/strict';
import {copyFileSync, mkdirSync, mkdtempSync, rmSync} from 'node:fs';
import {fileURLToPath} from 'node:url';
import {join} from 'node:path';
import {tmpdir} from 'node:os';
import {spawnSync} from 'node:child_process';

test('UART packets respect negotiated limits and preserve the full command', {skip:process.platform!=='darwin'}, () => {
    const root=mkdtempSync(join(tmpdir(),'wand-uart-'));
    const dir=join(root,'build.noindex');
    mkdirSync(dir);
    try {
        copyFileSync(new URL('./fixtures/uart-main.swift',import.meta.url),join(dir,'main.swift'));
        const source=fileURLToPath(new URL('../receiver/Sources/WandUART.swift',import.meta.url));
        const build=spawnSync('swiftc',['-O',source,join(dir,'main.swift'),'-o',join(dir,'check')],{encoding:'utf8'});
        assert.equal(build.status,0,build.stderr);
        const run=spawnSync(join(dir,'check'),[],{encoding:'utf8'});
        assert.equal(run.status,0,run.stdout+run.stderr);
        assert.match(run.stdout,/PASS negotiated UART/);
    } finally { rmSync(root,{recursive:true,force:true}); }
});
