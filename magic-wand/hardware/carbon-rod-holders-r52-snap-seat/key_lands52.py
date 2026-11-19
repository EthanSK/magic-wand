"""Compare the carrier's bearing surfaces for all four Choc switch flanges."""
import json
from pathlib import Path
import sys

import build52 as cad
from sockets52 import key_spaces
from orient51 import load_solid, digest


def check(directory):
    reference=cad.PREV/'exports/Key_Carrier-assembly.stl'
    source=directory/'Key_Carrier-assembly.stl'
    prior=load_solid(reference)
    revised=load_solid(source)
    spaces=key_spaces()
    rows={}
    for key in (0,2,3,4):
        mount=spaces[f'key_{key}_mount_opening'][0]
        switch=spaces[f'key_{key}_switch'][0]
        x0,y0,_,x1,y1,top=mount.bounding_box()
        # R16's opening extends 0.2 mm above the physical plate. Section
        # just below its true top; compare only the immediate land at this key.
        z=top-.2-.025
        x,y=(x0+x1)/2,(y0+y1)/2
        land=cad.box(x-8.15,x+8.15,y-8.15,y+8.15,z-.1,z+.1).slice(z)-mount.slice(z)
        original=prior.slice(z)
        current=revised.slice(z)
        old_land=original^land
        new_land=current^land
        # Project the bought switch flange just above that real bearing plane.
        flange=switch.slice(z+.12)+switch.slice(z+.28)+switch.slice(z+.50)
        was=original^flange
        now=current^flange
        rows[str(key)]=dict(upper_land_plane_z_mm=z,
            reference_top_land_area_mm2=old_land.area(),new_top_land_area_mm2=new_land.area(),
            retained_top_land_percent=(old_land^new_land).area()*100/old_land.area(),
            reference_flange_bearing_mm2=was.area(),new_flange_bearing_mm2=now.area(),
            flange_bearing_retained_percent=(was^now).area()*100/was.area())
    report=dict(reference_carrier_sha256=digest(reference),new_carrier_sha256=digest(source),key_lands=rows)
    (directory/'key-bearing.json').write_text(json.dumps(report,indent=2)+'\n')


if __name__=='__main__':
    check(Path(sys.argv[1]))
