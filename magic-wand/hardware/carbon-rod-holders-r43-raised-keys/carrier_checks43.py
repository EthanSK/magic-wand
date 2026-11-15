"""Fresh R43 paths: raised key routes and complete surviving seat bonds.

All unchanged OP1/hinge/rod routes and guard sections compose R42. The
changed key spaces come from R43 solids, and four additional whole bonds
must meet the existing deposited-material threshold without shrinking.
"""
from functools import lru_cache
from pathlib import Path
from unittest.mock import patch
import holder43 as d
import plate43
import carrier_checks42 as previous

full=previous.full
common=previous.c
BASE_ROUTES=full.routes


@lru_cache(maxsize=1)
def routes():
    gaps,material=BASE_ROUTES()
    gaps={n:dict(v) for n,v in gaps.items()}
    material={n:dict(v) for n,v in material.items()}
    gaps[d.CARRIER].update({n:s for n,s in d.geometry()[1].items() if n.startswith('key_')})
    material[d.CARRIER].update(d.seat_bonds())
    material[d.CARRIER].update(d.guard_web_interfaces())
    return gaps,material


def base_routes():
    gaps,material=routes()
    return {**gaps,d.CARRIER:{n:s for n,s in gaps[d.CARRIER].items() if n!=full.PLUG_ROUTE}},material


def audit(archive,scratch,owner):
    # Construct inherited route regions before changing their dispatcher.
    routes()
    with patch.object(previous,'d',d),patch.object(full,'routes',side_effect=routes), \
         patch.object(full,'base_routes',side_effect=base_routes),patch.object(full,'plate42',plate43):
        result=previous.audit(archive,scratch,owner)
    result.update(checker_sha256=common.digest(Path(__file__)),
        upstream_carrier_checker_sha256=common.digest(Path(previous.__file__)),
        geometry_source_sha256=common.digest(Path(d.__file__)),
        raised_key_bonds_checked=list(d.seat_bonds()),physical_success_verified=False)
    return result
