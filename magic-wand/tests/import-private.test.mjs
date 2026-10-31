import test from 'node:test';
import assert from 'node:assert/strict';
import {spawnSync} from 'node:child_process';

test('receiver import accepts a complete public source, rejects partial migration and private identity', () => {
  const result=spawnSync('python3',['-c',String.raw`
import importlib.util
from pathlib import Path
spec=importlib.util.spec_from_file_location("wand_import", "scripts/import_private.py")
m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m)
source=Path("receiver/Sources/main.swift").read_text()
assert m.sanitize_receiver(source)==source
partial=source.replace("    var target: UUID? { deviceSettings.identifier }", "    var target: UUID?")
try:
    m.sanitize_receiver(partial)
except SystemExit:
    pass
else:
    raise AssertionError("partial public migration was accepted")
assert m.leaks(source)==[]
# Both wireless updater modules and the changed transport adapters are canonical imports.
for public in ["WandSenseUpdate.swift", "WandReceiverSenseUpdate.swift", "WandSenseLink.swift", "WandSenseProtocol.swift", "WandReceiverSense.swift", "WandReceiverActions.swift"]:
    path="receiver/Sources/"+public
    assert any(target==path for target,transform in m.FILES.values()), path
    assert m.leaks(Path(path).read_text())==[], path
for name in ["wand_sense.ino", "wand_time.h", "wand_merge.h", "wand_light.h", "wand_update.h", "wand_usb_output.h", "wand_ble_output.h"]:
    assert m.FILES["sense/"+name] == ("device/sense/wand_sense/"+name, "verbatim")
assert m.leaks(source+'\nlet privateID="'+"-".join("0"*n for n in (8,4,4,4,12))+'"')
print("PASS: public source stays byte-identical; partial source and private identity fail")
`],{cwd:new URL('..',import.meta.url),encoding:'utf8'});
  assert.equal(result.status,0,result.stdout+result.stderr);
});
