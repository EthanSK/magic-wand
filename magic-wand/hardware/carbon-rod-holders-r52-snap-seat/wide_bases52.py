"""R48-style two-layer outboard plates, with individually exposed cutting necks."""
import manifold3d as mf
import numpy as np


def rectangle(x0,y0,x1,y1):
    return mf.CrossSection.square((x1-x0,y1-y0)).translate((x0,y0))


def plate(x0,y0,x1,y1):
    k=3.
    return mf.CrossSection([[(x0+k,y0),(x1-k,y0),(x1,y0+k),(x1,y1-k),
                             (x1-k,y1),(x0+k,y1),(x0,y1-k),(x0,y0+k)]])


def bond(a,b,width):
    a=np.array(a);b=np.array(b)
    perpendicular=np.array([a[1]-b[1],b[0]-a[0]])
    normal=perpendicular*width/(2*np.linalg.norm(perpendicular))
    return mf.CrossSection([[a-normal,b-normal,b+normal,a+normal]])


def panels(name):
    if name=='Key_Carrier':
        return [plate(16,45,87,69),plate(16,110,87,134),rectangle(16,66,18.8,95)]
    return [plate(92,80,120,134),plate(136,80,164,134)]


def build(name,body,helpers=None):
    plates=panels(name)
    roots=[]
    if name=='Key_Carrier':
        # Forward prop feet, fixture feet and existing tear-away body ears.
        for part in helpers.slice(.1).decompose():
            poly=np.concatenate(part.to_polygons()); lo=poly.min(0);hi=poly.max(0)
            if hi[1]<80:
                v=poly[np.argmin(poly[:,1])];a=(v[0],68);b=v+[0,1]
            elif lo[0]<23 and lo[1]<90:
                v=poly[np.argmin(poly[:,0])];a=(17.5,v[1]);b=v+[1,0]
            elif hi[1]>105:
                v=poly[np.argmax(poly[:,1])];a=(v[0],111);b=v-[0,1]
            else:
                v=poly[np.argmax(poly[:,1])];a=(v[0],111);b=v-[0,1]
            roots.append((a,b))
    else:
        foot=body.slice(.1)
        for y in (87.25,98.,110.):
            sec=foot^rectangle(100,y-.12,150,y+.12)
            if sec.is_empty():continue
            xmin,_,xmax,_=sec.bounds()
            roots.extend([((119.3,y),(xmin+.50,y)),((136.7,y),(xmax-.50,y))])
    sheets=mf.CrossSection.batch_boolean(plates,mf.OpType.Add)
    ties=[bond(a,b,1.4) for a,b in roots]
    total=mf.CrossSection.batch_boolean([sheets,*ties],mf.OpType.Add)
    return total.extrude(.4),sheets,roots
