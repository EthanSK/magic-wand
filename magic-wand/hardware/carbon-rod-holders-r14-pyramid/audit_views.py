#!/usr/bin/env python3
"""Render final exported meshes, including the removable exterior print walls."""
import json
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from mpl_toolkits.mplot3d.art3d import Poly3DCollection
import numpy as np,trimesh
import cad
import deliverables
OUT=cad.HERE/'exports'

def render():
    manifest=json.loads((OUT/'manifest.json').read_text())
    receipt={'generator_sha256':cad.sha(cad.HERE/'audit_views.py'),
             'manifest_sha256':cad.sha(OUT/'manifest.json'),
             'project_sha256':cad.sha(OUT/deliverables.project_name(OUT)),
             'source_meshes_sha256':{},'images_sha256':{}}
    for name in manifest['parts']:
        normal=OUT/(name+'-assembly.stl');model=trimesh.load_mesh(normal)
        receipt['source_meshes_sha256'][normal.name]=cad.sha(normal)
        helper=OUT/(name+'-PRINT-HELPER-assembly.stl')
        if helper.exists():receipt['source_meshes_sha256'][helper.name]=cad.sha(helper)
        fig=plt.figure(figsize=(11,5))
        for i,(elev,azim,title)in enumerate([(28,-65,'Top / front'),(-25,-105,'Underside')],1):
            ax=fig.add_subplot(1,2,i,projection='3d')
            ax.add_collection3d(Poly3DCollection(model.triangles,facecolor='#29a5b7',edgecolor='none',alpha=.93))
            if helper.exists():
                hm=trimesh.load_mesh(helper)
                ax.add_collection3d(Poly3DCollection(hm.triangles,facecolor='#f28b25',edgecolor='none',alpha=.40))
            lo,hi=model.bounds;centre=(lo+hi)/2;half=max(hi-lo)*.55
            ax.set(xlim=(centre[0]-half,centre[0]+half),ylim=(centre[1]-half,centre[1]+half),zlim=(centre[2]-half,centre[2]+half))
            ax.set_box_aspect((1,1,1));ax.view_init(elev,azim);ax.set_title(title)
            ax.set_xlabel('X mm');ax.set_ylabel('rod Y mm');ax.set_zlabel('Z mm')
        fig.suptitle(name+' | final STL in blue; removable CAD printing walls in orange')
        target=OUT/(name+'-overview.png')
        fig.tight_layout();fig.savefig(target,dpi=130);plt.close(fig)
        receipt['images_sha256'][target.name]=cad.sha(target)
    (OUT/'overview-checks.json').write_text(json.dumps(receipt,indent=2)+'\n')
if __name__=='__main__':render()
