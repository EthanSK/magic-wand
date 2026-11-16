"""Downward-removable lands beneath the four underside levels of the key deck."""
import manifold3d as mf
from holder45 import combine
from shelf45 import box

def below(shape,z):
    return shape.trim_by_plane((0,0,-1),-z).project()

def make(carrier,tabs,front):
    # The steep switch recess prevents a horizontal pull. A bed-side finger
    # reaches it only where its entire straight withdrawal clears the carrier,
    # the fitted bed tabs and the front comb as those parts were printed.
    ribs=combine([box(-2,y,66,2.5) for y in range(-2,46,4)])
    perpendicular=combine([box(x,-2,1.9,48) for x in range(-2,66,6)])
    tips=combine([box(-2,y+.58,66,1.34) for y in range(-2,46,4)])
    tips+=combine([box(x+.38,-2,1.14,48) for x in range(-2,66,6)])
    pieces=[];rows=[]
    for layer in (61,62,63,64):
        top=round((layer-2)*.2,2)
        first_face=carrier.slice(top+.30)-below(carrier,top+.101)
        shadows=(below(carrier,top+.001).offset(.65)
                 +below(front,top+.201).offset(.68)+tabs.project().offset(.65))
        area=first_face-shadows
        lands=(area^(ribs+perpendicular)).offset(-.49).offset(.49)
        contact=(lands^tips).offset(-.40).offset(.40)
        # Only give a tall strip a bed anchor if the actual CAD roof has
        # enough width for the slicer to put a usable line on its top.
        feet=combine([land for land in lands.decompose() if (land^contact).area()>1.2 and land.area()>4.])
        contact^=feet
        if not contact.is_empty():
            pieces.extend([feet.extrude(top-.60),contact.extrude(.601).translate((0,0,top-.601))])
        rows.append(dict(roof_layer=layer*.2,helper_top=top,bed_land_mm2=feet.area(),tip_mm2=contact.area()))
    return mf.Manifold.batch_boolean(pieces,mf.OpType.Add),rows
