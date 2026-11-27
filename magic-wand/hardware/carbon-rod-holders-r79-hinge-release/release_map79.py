"""Measure transfer paths from the breakaway base to the carrier and mark the cut points."""
import json
from pathlib import Path
import sys

import numpy as np
from matplotlib import pyplot as plt
from matplotlib.path import Path as PlotPath
from matplotlib.patches import PathPatch
import plate79 as plate

v = plate.old.previous.base.v


def measure(folder, exports):
    frame = v.read(folder / 'layout.frame.json')
    carrier = frame['parts']['Key_Carrier']
    body = v.load_solid(exports / carrier['source'])
    tr = np.asarray(carrier['assembly_to_machine'])
    native_pose = tr[:3].copy()
    native_pose[:2,3] = 0
    solid = body.transform(native_pose)
    params = carrier['adhesion_panel']
    complete = plate.old.previous.panel_builder(solid, params)
    actual_base = complete - solid
    stations = v.read(folder / 'fin-design.json')['fins']
    regions = {'hinge_bay':v.BAY}
    for row in stations:
        x,y = row['cut_at_xy']
        regions[f"{row['face']} at {x:g}"] = [x-2.5, y-1.1, x+2.5, y+1.1]
    report = v.seam(folder / v.ARCHIVE, frame, body, regions=regions,
                    regional_base=actual_base.translate((*tr[:2,3],0)),max_layers=25)
    areas = report['regional_joint_area_mm2']
    # The 0.1 mm raster plus proximity filter can include a sliver from an
    # adjoining wall (0.02 mm² on the R78 control); use the native seam gate.
    assert areas['hinge_bay'] < .25 and all(a > .05 for k,a in areas.items() if k != 'hinge_bay'), areas
    return areas, solid, actual_base, stations


def fill(ax, section, color):
    loops = [np.vstack((p,p[0])) for p in section.to_polygons() if len(p)>2]
    if loops:
        path = PlotPath.make_compound_path(*[PlotPath(loop, closed=True) for loop in loops])
        ax.add_patch(PathPatch(path,facecolor=color,edgecolor='none'))


def figure(solid, base, stations, filename):
    fig, ax = plt.subplots(figsize=(9,4.9))
    fill(ax,base.slice(.1),'#d8d1c7')
    fill(ax,solid.slice(.1),'#4f6773')
    for row in stations:
        x,y = row['cut_at_xy']
        direction = 1 if row['face']=='+y' else -1
        ax.plot(x,y+direction*.24,'o',mfc='none',mec='#b13214',ms=8,mew=1.7)
    ax.set_aspect('equal')
    ax.set_axis_off()
    ax.autoscale()
    ax.set_title('Where to cut the six tabs',loc='left',fontsize=17)
    fig.text(.12,.11,'Orange rings mark the tabs. Blue is the holder. Beige is the disposable base.',fontsize=10)
    fig.text(.12,.06,'Let the plate cool. Support the holder and snip each tab before peeling away the base.',fontsize=10)
    fig.savefig(filename,dpi=150,bbox_inches='tight')
    plt.close(fig)


def report(folder, render=False):
    previous = plate.old.OUT / 'print-mechanisms'
    before, *_ = measure(previous, plate.old.OUT)
    current, solid, base, stations = measure(folder, plate.OUT)
    right, left = '+y at 17', '+y at -17'
    # The right shoulder had over four times the left contact in R78.
    # Require a material reduction there and keep both sides comparable.
    if not (0 < current[right] < before[right]/2 and abs(current[right]-current[left]) < .4):
        raise ValueError(f'Uneven or excessive hinge-end contact on the replacement: {current}')
    proof = dict(r78_contacts_mm2=before, replacement_contacts_mm2=current,
                 archive_sha256=v.digest(folder / v.ARCHIVE), break_force_measured=False)
    (folder/'release-contacts.json').write_text(json.dumps(proof,indent=2)+'\n')
    if render:
        figure(solid,base,stations,plate.OUT/'removing-the-base.png')
    return proof


if __name__ == '__main__':
    print(report(Path(sys.argv[1]), '--render' in sys.argv))
