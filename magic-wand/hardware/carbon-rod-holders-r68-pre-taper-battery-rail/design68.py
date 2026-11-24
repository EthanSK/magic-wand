"""R68 key carrier: the R67 carrier with the battery's outboard rail restored to its pre-taper shape.

Assembly frame as in R53-R67: the rod runs along Y through X = Z = 0, +Z is up,
+Y is the top (two-key) end and the rear face Y = BED lies on the print bed.

R66 tapered the outboard (finger-side) battery rail: from Y 32 its wall and lip rose to the
deck, the spring-root post was exposed and rounded, and R67 then cut the remaining bed-face
corner diagonally. R68 puts back the full-length rail exactly as R63, R64 and R65 built it:
the outboard wall and its lip run at full depth to the bed face, with the square corner
round the spring-root post and the battery roof plate.

Build: the restore region is design66's battery zone (the only box R66 rebuilt), raised to
1 mm above the battery roof plate so it also holds everything R67's corner cut removed.
Its faces lie where R64 and R67 agree, never on the cut faces themselves. Inside that box
the R68 carrier is the exact R64 export, which is identical there to R63 and R65.
Outside it, the R68 carrier is the exact R67 export: the three-hole OP1 deck, the plug
lead-in and open route, the cleaned front saddle, the compact hinge, the rear socket
backing, the guards and the rod grip are all unchanged.
"""
from functools import lru_cache
from hashlib import sha256
from pathlib import Path
import sys

HERE = Path(__file__).resolve().parent
HARDWARE = HERE.parent
for folder in ('carbon-rod-holders-r67-diagonal-battery-corner', 'carbon-rod-holders-r66-three-hole-op1',
               'carbon-rod-holders-r64-under-entry', 'carbon-rod-holders-r63-open-hinge',
               'carbon-rod-holders-r62-compact-guard'):
    if str(HARDWARE / folder) not in sys.path:
        sys.path.insert(0, str(HARDWARE / folder))

import design67 as r67  # noqa: E402

r66, old, b = r67.r66, r67.old, r67.b
OUT = HERE / 'exports'
HOLDER = r67.HOLDER
R67_CARRIER = r67.OUT / HOLDER
R64_CARRIER = r66.R64_OUT / HOLDER
R67_SHA256 = 'a83ac4df043a069a42a432b8852d35d8d75d680009db710aa09efd06a580e9ea'
R64_SHA256 = '6aa0c8652b248957621869b3d1e9164456f412a281ea0eaed4051a533cd71a92'


def _sha(path):
    return sha256(Path(path).read_bytes()).hexdigest()


# R66's battery zone, its top raised from the deck (7.27) to 1 mm above the roof plate (8.47).
RESTORE_BOX = (*r66.OUTBOARD_ZONE[:5], r67.ROOF_TOP + 1.0)


@lru_cache(maxsize=1)
def restore_region():
    return b.box(*RESTORE_BOX)


def r67_carrier():
    assert _sha(R67_CARRIER) == R67_SHA256, 'R67 carrier changed'
    return b.load(R67_CARRIER)


def pre_taper_carrier():
    """R64's carrier, the last export built before the battery taper (R65 is identical here)."""
    assert _sha(R64_CARRIER) == R64_SHA256, 'R64 carrier changed'
    return b.load(R64_CARRIER)


def pre_taper_rail():
    return pre_taper_carrier() ^ restore_region()


def carrier():
    region = restore_region()
    body = (r67_carrier() - region) + (pre_taper_carrier() ^ region)
    return old.one_piece(body, 'R68 carrier', limit=.02)


def export(path):
    """Save as design66.exported does: if the saved mesh carries a zero-volume sliver where
    the restore box meets the deck, drop it and save again."""
    r66.exported(carrier(), path)
    assert len(b.load(path).decompose()) == 1


def main():
    OUT.mkdir(exist_ok=True)
    export(OUT / HOLDER)
    print('saved', OUT / HOLDER, _sha(OUT / HOLDER), flush=True)


if __name__ == '__main__':
    main()
