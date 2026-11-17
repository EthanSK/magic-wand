"""Scope complete-plate evidence to the key/helper group without changing paths.

Neighbour separation and all eight other parts are checked by audit_parts47.
Keep the complete archive hash and the actual tower; never substitute the old
key-only G-code. Reads of reference archives retain their original data.
"""
from contextlib import contextmanager
from pathlib import Path
from unittest.mock import patch
import numpy as np
import holder47
import audit45
import single44
import native_order45
import roof_context46
from owner45 import layout_owners


@contextmanager
def key_group(archive):
    archive=Path(archive).resolve()
    engine=audit45.common.load_checker()
    original_read=engine.audit.read_project
    original_owners=single44.previous.owners
    raw=list(original_read(archive));owner=original_owners(archive)
    full_count=len(raw[0]);full_gcode=raw[6]
    original_map=native_order45.map_moves
    wanted=layout_owners(archive.parent)
    selected={name:owner[name] for name in wanted}
    labels=np.asarray(raw[1])[raw[0][:,5].astype(int)]
    mask=np.isin(raw[0][:,6],list(selected.values()))|(labels=='Prime tower')
    raw[0]=raw[0][mask];raw[5]={name:raw[5][name] for name in wanted}
    mapped=None
    def map_moves(q,gcode,total):
        nonlocal mapped
        if gcode is full_gcode:
            assert total==len(raw[0])
            if mapped is None:
                mapped=tuple(array[mask] for array in original_map(q,gcode,full_count))
            return mapped
        return original_map(q,gcode,total)
    def read(path):
        return tuple(raw) if Path(path).resolve()==archive else original_read(path)
    def owners(path):
        return selected if Path(path).resolve()==archive else original_owners(path)
    with patch.object(audit45.common,'load_checker',return_value=engine), \
         patch.object(engine.audit,'read_project',side_effect=read), \
         patch.object(single44.previous,'owners',side_effect=owners), \
         patch.object(native_order45,'map_moves',side_effect=map_moves), \
         patch.object(roof_context46,'map_moves',side_effect=map_moves):
        yield engine
