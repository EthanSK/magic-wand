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

def corrected_caps(module):
    # Draw both revisions with R15's corrected, inferred cap orientation:
    # 17.5 mm along X (the stem-post axis) and 16.6 mm along Y. R14 used the
    # rotated reference, so its own cap bounds would understate its X gaps.
    c=cad.P['cap_clearance_screen'];w,l=c['reference_width_mm'],c['reference_length_mm'];z=cad.P['keys']['pcb_z']
    return [(x-w/2,y-l/2,z+6.1,x+w/2,y+l/2,z+9.1)for x,y in module.key_positions()]

def render():
    old=cad.load('cad',cad.HERE.parent/'carbon-rod-holders-r14-pyramid')
    fig,axes=plt.subplots(3,2,figsize=(12,15),gridspec_kw={'height_ratios':[1.6,1,1]})
    for column,(module,title) in enumerate(zip([old,cad],['R14: earlier pyramid','R15: corrected cap pitch, recessed lower edge'])):
        m=trimesh.load_mesh(module.HERE/'exports/Key_Carrier-assembly.stl')
        caps=corrected_caps(module)
        ax=axes[0][column]
        ax.add_collection(PolyCollection(m.triangles[:,:,:2],facecolor='#8ba5b5',edgecolor='none',alpha=.25))
        for i,((x,y),bb) in enumerate(zip(module.key_positions(),caps)):
            rect=plt.Rectangle((bb[0],bb[1]),bb[3]-bb[0],bb[4]-bb[1],facecolor='#dfedec',edgecolor='#174e59',lw=1.5)
            ax.add_patch(rect);ax.text(x,y,str(i+1),ha='center',va='center',color='#174e59')
        ax.set(xlim=(-36,36),ylim=(-20,36),title=title,xlabel='Across rod, mm',ylabel='Toward tip (+Y), mm')
        ax.set_aspect('equal');ax.grid(alpha=.2)
        # Front view from the handle end: the frame edge below the bottom row.
        ax=axes[1][column];depth=m.triangles[:,:,1].mean(1);order=np.argsort(-depth)
        colours=plt.cm.viridis(np.clip((depth[order]+14)/20,0,1))
        ax.add_collection(PolyCollection(m.triangles[order][:,:,[0,2]],facecolors=colours,edgecolors='none'))
        for (x,y),bb in zip(module.key_positions(),caps):
            if not y:ax.add_patch(plt.Rectangle((bb[0],bb[2]),bb[3]-bb[0],bb[5]-bb[2],fill=False,edgecolor='#c0392b',ls='--'))
        ax.axhspan(-4,4,color='#2c3e91',alpha=.08)
        ax.set(xlim=(-32,32),ylim=(-8,19),title='Front view from the handle end (dark = nearer)',xlabel='X, mm',ylabel='Toward keycaps (+Z), mm')
        ax.set_aspect('equal');ax.grid(alpha=.2)
        # Side silhouette: lower cap front edge against the frame front.
        ax=axes[2][column]
        ax.add_collection(PolyCollection(m.triangles[:,:,[1,2]],facecolor='#8ba5b5',edgecolor='none',alpha=.18))
        front=min(bb[1]for (x,y),bb in zip(module.key_positions(),caps)if not y)
        ax.add_patch(plt.Rectangle((front,caps[1][2]),caps[1][4]-caps[1][1],caps[1][5]-caps[1][2],fill=False,edgecolor='#c0392b',ls='--'))
        ax.axvline(front,color='#c0392b',lw=.8);ax.axvline(m.bounds[0][1],color='k',lw=.8)
        ax.text(m.bounds[0][1],-6.5,f' frame front {m.bounds[0][1]:.1f}',fontsize=8)
        ax.axhspan(-4,4,color='#2c3e91',alpha=.08)
        ax.set(xlim=(-16,32),ylim=(-8,19),title=f'Side silhouette; cap front at Y {front:.2f}',xlabel='Toward tip (+Y), mm',ylabel='Z, mm')
        ax.set_aspect('equal');ax.grid(alpha=.2)
    c=cad.P['cap_clearance_screen']
    fig.suptitle(f"Actual carrier exports; inferred {c['reference_width_mm']} (X, stem-post axis) × {c['reference_length_mm']} mm (Y) caps on both; blue band = rod")
    fig.text(.5,.01,'Cap size is inferred from a same-family listing, not measured. Physical comfort, cap fit and printed strength remain unverified.',ha='center')
    fig.tight_layout(rect=[0,.03,1,.97]);target=cad.HERE/'exports/layout-comparison.png';fig.savefig(target,dpi=120);plt.close(fig)
    receipt={'generator_sha256':cad.sha(Path(__file__)),'image_sha256':cad.sha(target),
             'r15_manifest_sha256':cad.sha(cad.HERE/'exports/manifest.json'),
             'r14_manifest_sha256':cad.sha(old.HERE/'exports/manifest.json')}
    (target.with_suffix('.json')).write_text(json.dumps(receipt,indent=2)+'\n')

if __name__=='__main__':render()
