"""Fast CAD start screen to localise releases that need changes before slicing.

This never qualifies a working opening or bridge as printable. Only real
extrusion confirms the result.
"""
import numpy as np
def scan(body,cradle,frame):
    previous=None; unsupported=[]
    for k in range(1,int(np.ceil(body.bounding_box()[5]/.2))+1):
        z=round(k*.2,4);middle=z-.1; now=body.slice(middle)
        if previous is not None:
            natural=previous.offset(.25)
            under=cradle.slice(z-.5)
            for c in now.decompose():
                if c.area()<=.15 or (c^natural).area()>.01:continue
                if (c^under).area()>.01:continue
                x0,y0,x1,y1=c.bounds()
                centre=np.array([(x0+x1)*.5,(y0+y1)*.5,middle,1])
                bounds=c.bounds()
                # Follow this initially isolated patch until its first union
                # with a different lower island. The next CAD change needs
                # to know how long the unsupported protrusion lasts.
                probe=c;join=None
                for n in range(k+1,min(k+50,int(np.ceil(body.bounding_box()[5]/.2)))+1):
                    up=body.slice(n*.2-.1)
                    linked=[t for t in up.decompose() if (t^probe.offset(.25)).area()>.01]
                    if not linked:break
                    best=max(linked,key=lambda t:(t^probe.offset(.25)).area())
                    if any((best^other).area()>.02 for other in previous_candidates(body,n,probe)):
                        join=round(n*.2,3);break
                    probe=best
                unsupported.append(dict(layer_top=z,part_area=c.area(),print_bounds=bounds,assembly_center=(frame@centre)[:3].tolist(),first_union_with_other_island_top=join))
        previous=now
    return unsupported

def previous_candidates(body,n,probe):
    return [c for c in body.slice((n-1)*.2-.1).decompose() if (c^probe).area()<.01]
