"""Separate positive native prop extrusion from the carrier subpart in the same Bambu object."""
import json
from pathlib import Path
from xml.etree import ElementTree as ET
from zipfile import ZipFile

import numpy as np


def geometry(archive,q):
    with ZipFile(archive) as z:
        project=ET.fromstring(z.read('3D/3dmodel.model')); settings=ET.fromstring(z.read('Metadata/model_settings.config'))
        obj=next(o for o in settings.findall('object') if q.metadata(o)['name']=='Key_Carrier')
        sub=next((p for p in obj.findall('part') if q.metadata(p).get('name')=='External_peel_support'),None)
        if sub is None:return None
        item=project.find("{*}build/{*}item[@objectid='"+obj.get('id')+"']")
        base=project.find("{*}resources/{*}object[@id='"+obj.get('id')+"']")
        comp=base.find("{*}components/{*}component[@objectid='"+sub.get('id')+"']")
        path=next((v.lstrip('/') for k,v in comp.attrib.items() if k.endswith('}path')),None)
        ref=ET.fromstring(z.read(path)) if path else project
        mesh=ref.find("{*}resources/{*}object[@id='"+sub.get('id')+"']/{*}mesh")
        verts=np.array([[float(v.get(k)) for k in 'xyz'] for v in mesh.findall('{*}vertices/{*}vertex')])
        faces=np.array([[int(v.get(k)) for k in ('v1','v2','v3')] for v in mesh.findall('{*}triangles/{*}triangle')])
        verts=q.points(q.points(verts,q.transform(comp.get('transform'))),q.transform(item.get('transform')))
    return q.solid(verts,faces)


def native_mask(archive,q,data,owner,features,sequences=None):
    shape=geometry(archive,q); select=np.zeros(len(data),bool)
    if shape is None:return select,{}
    cand=(data[:,6]==owner)&np.isin(data[:,5],features)
    lo=np.array(shape.bounding_box()[:3])-.3;hi=np.array(shape.bounding_box()[3:])+.3
    cand&=np.all((data[:,:3]>=lo)&(data[:,:3]<=hi),axis=1)
    for top in np.unique(data[cand,7]):
        chosen=np.flatnonzero(cand&(abs(data[:,7]-top)<.001))
        section=shape.slice(float(top)-.101)
        select[chosen]=q._inside(section.offset(.18),data[chosen,:2])
    groups=np.unique(sequences[select]) if sequences is not None else []
    crosses=int(len(np.intersect1d(groups,np.unique(sequences[cand&~select])))) if sequences is not None else None
    return select,dict(CAD_mm3=round(shape.volume(),3),nominal_solid_mass_g=round(shape.volume()*.00127,4),
        native_bead_samples=int(select.sum()),native_continuous_sequences=len(groups),mixed_model_prop_sequences=crosses)
