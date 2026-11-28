"""Bind the repair plate, both native slices and the assembly to the reviewed geometry."""
from pathlib import Path
from shutil import copyfile
import sys
from zipfile import ZipFile

from plate80 import OUT, previous, parts
from audit80 import v, b
import release61
import review78


def release(primary, reopened):
    dest = OUT / 'print-mechanisms'
    dest.mkdir(exist_ok=True)
    inventory = {row['name'] for row in parts()}
    layout = v.digest(primary / 'layout.3mf')
    references = {n: previous.OUT / 'print-mechanisms' for n in inventory if n != 'Touch_Paddle'}
    old = v.read(dest / 'r79-post-sections.json')
    receipts = []
    studies = {}
    for label, folder, prefix in [('primary', primary, ''), ('reopened', reopened, 'reopened-')]:
        frame = v.read(folder / 'layout.frame.json')
        native = v.read(folder / 'OP1-hinge.gcode.native.json')
        assert frame['layout_sha256'] == v.digest(folder / 'layout.3mf') == layout
        assert native['archive_sha256'] == v.digest(folder / v.ARCHIVE) and not native['plates'][0]['warning_message']
        expected_input = layout if label == 'primary' else studies['primary']['archive_sha256']
        assert native['slice_input_sha256'] == expected_input and native['reopened_sliced_archive'] == (label=='reopened')
        routes = v.read(folder / 'routes.json')
        assert set(routes) == inventory and all(not r['obstructed_poses'] for checks in routes.values() for r in checks.values())
        for row in parts():
            assert frame['parts'][row['name']]['source_sha256'] == v.digest(row['source'])
        profiles = v.read(folder / 'post-sections.json')
        for side, sections in profiles.items():
            bearing = [r for r in sections if r['above_board_seat_mm'] < b.BOARD_TOP-b.SEAT_Z]
            assert len(bearing) >= 7 and len(bearing) < len(sections)
            for row, before in zip(bearing, old[side]):
                assert row['above_board_seat_mm'] == before['above_board_seat_mm']
                if row['above_board_seat_mm'] <= 1.0:
                    assert row['width_x_mm'] > before['width_x_mm']+.08, (side, row, before)
            assert sections[-1]['minimum_width_mm'] < min(r['minimum_width_mm'] for r in bearing if r['above_board_seat_mm'] < 1.1)-.20
        studies[label] = dict(archive_sha256=native['archive_sha256'], groups=sum(map(len,routes.values())),
                              new_anchored_spans=review78.inspect(folder, baseline=previous.old.OUT / 'print-mechanisms',
                                                                  part_baselines=references))
        for name in ('OP1-hinge.gcode.native.json','layers.json','separation-and-machine.json','bases.json','routes.json','post-sections.json','spring-gaps.json','before-pad-removal.json','paddle-passage.json','load-sections.json'):
            destination = dest/(prefix+name)
            copyfile(folder/name, destination)
            receipts.append(destination)
    for name in ('layout.3mf', 'layout.frame.json', v.ARCHIVE):
        copyfile(primary / name, dest / name)
    with ZipFile(primary / v.ARCHIVE) as archive:
        (dest/'tray.png').write_bytes(archive.read('Metadata/top_1.png'))
    review = dest/'review.json'
    v.write(review, dict(revision='R80', inventory=sorted(inventory), layout_sha256=layout,
                         fitted_guide_sha256=v.digest(OUT/'assembly-guide.json'), slices=studies,
                         physical_fit_verified=False))
    release61.package(primary/v.ARCHIVE,dest/'R80-Touchpad-Repair-A1-mini-PETG-print-only.3mf',
                      inventory,[*receipts,review,dest/'r79-post-sections.json'])


if __name__ == '__main__':
    release(*map(Path,sys.argv[1:]))
