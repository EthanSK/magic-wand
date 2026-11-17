"""Measure the consequence of completely losing a sub-bead disposable stroke."""
from pathlib import Path
from xml.etree import ElementTree
from zipfile import ZipFile
import json
import numpy as np


def omission(archive, row):
    from grounded45 import trace
    from native_order45 import map_moves
    from holder45 import inherited
    if (row['before'] or row['after'] or row['mm'] > row['minimum_bead_width_mm']
            or row['mm'] < .30 or row['features'] != ['Outer wall']):
        return None
    checker = inherited.common.load_checker().audit
    q = checker.q
    z = row['z']
    with ZipFile(archive) as project:
        gcode = project.read('Metadata/plate_1.gcode').decode()
        xml = ElementTree.fromstring(project.read('Metadata/slice_info.config'))
        offsets = json.loads(project.read('Metadata/project_settings.config'))['extruder_offset'][0]
    owners = {o.get('name'):int(o.get('identify_id')) for o in xml.findall('./plate/object')}
    frame = json.loads((Path(archive).parent/'frame.json').read_text())
    heights = {round(z+i*.2,3) for i in range(-2,6)}
    blocks = {}
    current = None
    for number, line in enumerate(gcode.splitlines(),1):
        if line.startswith('; Z_HEIGHT:'):
            height = round(float(line.split(':')[1]),3)
            current = (number,[]) if height in heights else None
            if current is not None:
                blocks[height] = current
        if current is not None:
            current[1].append(line)
    samples = {}
    for height,(first,lines) in blocks.items():
        source = '; FEATURE: Custom\n' + '\n'.join(lines)
        paths, features, _ = q.extrusion_points(source,.15)
        line_id, sequence, _, _ = map_moves(q,source,len(paths))
        regular = inherited.common.model_mask(np.asarray(features)[paths[:,5].astype(int)])
        xy = paths[:,:2] + np.array(offsets.split('x'),dtype=float) - frame['bed_translation'][:2]
        samples[height] = (xy[regular], paths[regular,3],paths[regular,6],line_id[regular]+first-2,sequence[regular])
    shelf = owners['Front_pull_shelf']
    xy,widths,ids,lines,seq = samples[z]
    omit = (ids==shelf) & (lines>=row['first_gcode_line']) & (lines<=row['last_gcode_line'])
    if not omit.any() or len(set(seq[omit]))!=1 or np.any((ids==shelf) & np.isin(seq,seq[omit]) & ~omit):
        return None

    omitted = {z:omit}

    def footprint(height, take, remove=False):
        pts,width,owner,_,_ = samples[round(height,3)]
        mask = np.isin(owner,take)
        if remove and round(height,3) in omitted:
            mask &= ~omitted[round(height,3)]
        return checker.start_audit.bead_footprints(q,pts[mask],width[mask]) if mask.any() else q.CrossSection()

    tip = checker.start_audit.bead_footprints(q,xy[omit],widths[omit])
    # A functional bead can use a helper even across one empty layer.
    receiver = {}

    def anchored(height,remove):
        pts,width,owner,indexes,sequences = samples[height]
        select = owner==shelf
        if remove and height==z:
            select &= ~omit
        indices = np.flatnonzero(select)
        points = pts[indices]
        backing = footprint(height-.2,[shelf],remove).offset(.25)
        backing += footprint(height-.4,[owners['Key_Carrier'],owners['External_cradle']])
        start = q._inside(backing,points)
        moves = np.r_[0,np.flatnonzero(np.diff(indexes[indices]))+1,len(indices)]
        groups = np.r_[0,np.flatnonzero(np.diff(sequences[indices]))+1,len(indices)]
        distances = np.linalg.norm(np.diff(points,axis=0),axis=1)
        return indices,np.isfinite(trace(points,width[indices],start,moves,groups,distances))

    checks = {}
    recovered = False
    for i in range(4):
        height = round(z + i*.2,3)
        if height not in samples:
            break
        control_ids,control = anchored(height,False)
        kept_ids,reduced = anchored(height,True)
        expected = control[np.searchsorted(control_ids,kept_ids)]
        lost = kept_ids[expected & ~reduced]
        pts,width,_,_,_ = samples[height]
        discard = omitted.setdefault(height,np.zeros(len(pts),dtype=bool))
        discard[lost] = True
        if discard.any():
            unavailable = checker.start_audit.bead_footprints(q,pts[discard],width[discard])
            carrier_area = {}
            for step in (0, 1, 2):
                neighbour = round(height + step*.2,3)
                if neighbour in samples:
                    carrier = footprint(neighbour,[owners['Key_Carrier']])
                    carrier_area[str(neighbour)] = {'direct_mm2':(unavailable ^ carrier).area(),
                        'within_lateral_0p25_band_mm2':(unavailable.offset(.25) ^ carrier).area()}
            receiver[str(height)] = carrier_area
        checks[str(height)] = {'retained_samples':len(kept_ids), 'newly_unanchored_samples':len(lost),
                               'omitted_area_mm2':unavailable.area() if discard.any() else 0.,
                               'previously_unanchored_retained_samples':int(np.sum(~expected))}
        if i and not len(lost):
            recovered = True
            break
    localized = i <= 3 and all(row['omitted_area_mm2'] <= .4 for row in checks.values())
    return {'native_stroke':row, 'removed_shelf_footprint_mm2':tip.area(),
            'actual_carrier_overlap_by_layer_mm2':receiver, 'other_shelf_paths_without_stroke':checks,
            'omission_stops_propagating':recovered,
            'passed':bool(recovered and localized and all(r['direct_mm2']<.00001 for c in receiver.values() for r in c.values())),
            'scope':'Entire travel-separated stroke omitted in the test. Subsequent shelf paths traced in actual print order; physical sag and adhesion untested.'}
