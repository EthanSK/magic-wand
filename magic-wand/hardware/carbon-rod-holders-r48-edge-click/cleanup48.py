"""Animate each independently removable R48 print helper on its native path."""
import math

from native48 import digest, read


def compose(guide, parts, out):
    from guide45 import highest_z, pose
    audit = read(parts / 'candidate-audit.json')
    release = read(parts / 'recess-support-removal.json')
    assert release['passed'] and release['archive_sha256'] == audit['archive_sha256']
    order = [item.split(':', 1)[0].strip() for item in audit['removal_order']]
    pieces = []
    names = {'External_cradle', 'Front_pull_shelf', 'Rear_pull_shelf', 'Release_tabs'}
    assert set(order) == names == set(audit['owners']) - {'Key_Carrier'}
    receipts = {}
    for group in order:
        if group == 'External_cradle':
            file = 'R45-external-cradle.stl'
            pieces.append((group, file, 'Outer cradle', '#e19753', [0.,0.,-math.ceil(highest_z(parts/file)+4.)],
                           'Release the outer cradle',
                           'Hold the solid blue frame. Release the orange cradle from its exposed feet, one foot at a time.'))
        elif group == 'Release_tabs':
            pieces.append((group, 'R45-release-tabs.stl', 'Bed tabs', '#ffdd68', [0., 0., -18.],
                           'Peel off the bed tabs',
                           'Peel the thin yellow tabs from the face that touched the plate. The tabs sit outside the centre pusher’s swing. Clear any loose scraps from the switch openings and wire slot. Once assembled, check that the pusher clicks and springs back freely.'))
        else:
            front = group == 'Front_pull_shelf'
            file = 'shelf-cad.json' if front else 'rear-shelf-cad.json'
            receipt = read(parts/file)
            receipts[group] = digest(parts/file)
            rows = receipt['removable_pieces']
            expected = release['independent_front_pieces'] if front else len(release['independent_rear_pieces'])
            assert receipt['owner'] == group and len(rows) == expected
            assert [v['removal_order'] for v in rows] == list(range(1, len(rows)+1))
            for row in rows:
                name = row['name']
                filename = row['file']
                assert digest(parts/filename) == row['sha256']
                assert row['has_1p2mm_grip_land'] and not row['whole_cad_conflicts_with_remaining_pieces']
                assert row['direction_print'] == [0, -1 if front else 1, 0]
                vector = [v*row['translation_mm'] for v in row['direction_print']]
                if front:
                    title = 'Slide out the '+name.lower()
                    caption = f'Hold the solid frame. Grip the exposed foot of the {name.lower()} and pull it straight out through the finger-rest side.'
                else:
                    title = 'Slide out the '+name.lower()
                    caption = f'From the opposite side, grip the purple foot of the {name.lower()}. Pull it out through its switch opening. Keep the blue switch surround still.'
                pieces.append((group,filename,name,'#8ab77e' if front else '#b59ada',vector,title,caption))
    actors = {'carrier': {'label':'Permanent key holder','file':str((parts/'R45-Key-Carrier.stl').relative_to(out)),
                          'color':'#29a5b7'}}
    sequence = []
    for i,(group,file,label,color,vector,title,caption) in enumerate(pieces):
        actor = f'helper_{i}'
        actors[actor]={'label':label,'color':color,'file':str((parts/file).relative_to(out))}
        sequence.append({'owner':group,'actor':actor,'filename':file})
    poses = {key:pose() for key in actors}
    def frame():
        return {k:list(v) for k,v in poses.items()}
    steps=[{'title':'Find the removable supports','duration':3,'samples':[frame()],
            'caption':'Let the print cool. Hold the blue key holder by its solid frame. The green and purple supports each have separate feet you can pull individually.'}]
    for record,(_group,_file,_label,_color,vector,title,caption) in zip(sequence,pieces,strict=True):
        frames=[]
        for i in range(25):
            poses[record['actor']] = pose(*[v*i/24 for v in (vector[2],vector[1],vector[0])])
            frames.append(frame())
        steps.append({'title':title,'duration':4,'caption':caption,'samples':frames})
    guide['modules']['print_cleanup']={'label':'Remove print support','rotation':[.85,0,.35],
            'note':'Each support follows the path checked against the sliced plate. Work one foot at a time. If the frame bends, stop pulling.',
            'actors':actors,'steps':steps,'native_removal_sequence':order,'physical_piece_removal_sequence':sequence}
    for key in ('key','dfr'):
        guide['modules'][key]['steps'][0].update(title='Remove Print Supports',
            caption='Choose Remove print support for the removal order. Clear the supports on the cool part before fitting the switches or boards.')
    guide['modules']['key']['label']='Fit the Choc switches'
    guide['modules']['xiao']['label']='XIAO holder and keeper'
    guide['modules']['xiao_latch']['label']='XIAO keeper detail'
    return {'print_frame_sha256':digest(parts/'frame.json'),'native_audit_sha256':digest(parts/'candidate-audit.json'),
            'selected_native_archive_sha256':audit['archive_sha256'],'side_helper_receipts_sha256':receipts,
            'support_release_sha256':digest(parts/'recess-support-removal.json')}
