#!/usr/bin/env python3
"""Compare actual exported carrier meshes and illustrative moving cap bounds."""
import json
from pathlib import Path
import numpy as np
import trimesh
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from matplotlib.collections import PolyCollection
import cad

def render():
    old=cad.load('cad',cad.HERE.parent/'carbon-rod-holders-r13-printability')
    fig,axes=plt.subplots(1,2,figsize=(12,6))
    for ax,module,title in zip(axes,[old,cad],['R13: outboard pair','R14: centred pyramid']):
        m=trimesh.load_mesh(module.HERE/'exports/Key_Carrier-assembly.stl')
        ax.add_collection(PolyCollection(m.triangles[:,:,:2],facecolor='#8ba5b5',edgecolor='none',alpha=.25))
        for i,(x,y) in enumerate(module.key_positions()):
            cap=module.references()[f'key_{i}_cap'];bb=cap.bounding_box()
            rect=plt.Rectangle((bb[0],bb[1]),bb[3]-bb[0],bb[4]-bb[1],facecolor='#dfedec',edgecolor='#174e59',lw=1.5)
            ax.add_patch(rect);ax.text(x,y,str(i+1),ha='center',va='center',color='#174e59')
        ax.set(xlim=(-36,36),ylim=(-20,36),title=title,xlabel='Across rod, mm',ylabel='Toward tip (+Y), mm')
        ax.set_aspect('equal');ax.grid(alpha=.2)
    fig.suptitle('Actual carrier exports; 16.6 × 17.5 mm cap references')
    fig.text(.5,.02,'Cap dimensions/play are illustrative. Physical comfort, cap fit and printed strength remain unverified.',ha='center')
    fig.tight_layout(rect=[0,.05,1,.95]);target=cad.HERE/'exports/layout-comparison.png';fig.savefig(target,dpi=145);plt.close(fig)
    receipt={'generator_sha256':cad.sha(Path(__file__)),'image_sha256':cad.sha(target),
             'r14_manifest_sha256':cad.sha(cad.HERE/'exports/manifest.json'),
             'r13_manifest_sha256':cad.sha(old.HERE/'exports/manifest.json')}
    (target.with_suffix('.json')).write_text(json.dumps(receipt,indent=2)+'\n')

if __name__=='__main__':render()
