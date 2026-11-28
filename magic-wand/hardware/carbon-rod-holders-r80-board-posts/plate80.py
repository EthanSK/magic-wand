"""Build the small touchpad repair plate from the fitted carrier's existing kit."""
from functools import lru_cache
from os.path import relpath
from pathlib import Path
import sys

HERE = Path(__file__).resolve().parent
OUT = HERE / 'exports'
sys.path.insert(0, str(HERE.parent / 'carbon-rod-holders-r79-hinge-release'))
import plate79 as previous

kit = previous.old.previous.kit.base_plate


@lru_cache(maxsize=1)
def parts():
    # The rods, key carrier and hinge pin already fitted are reusable. Include
    # fresh copies of both easy clips each time the board posts are replaced.
    import design80
    replacements = {'DFR_Post_Bar': OUT / design80.POST_BAR, 'OP1_Lid_Stop': OUT / design80.LID}
    clips = set(previous.CLIPS)
    rows = []
    for original in previous.parts():
        name = original['name']
        if name not in replacements and name not in clips:
            continue
        row = dict(original)
        if name in replacements:
            row['source'] = replacements[name]
            pose = row['assembly_to_print'].copy()
            pose[2, 3] -= previous.b.load(row['source']).transform(pose[:3]).bounding_box()[2]
            row['assembly_to_print'] = pose
        if name == 'DFR_Post_Bar':
            # Lay down the spring ends on the first layer. Otherwise the
            # slicer draws a narrow return out into free air on layer two.
            row['wall_settings'] = {**row.get('wall_settings', {}), 'wall_generator': 'arachne'}
        row['mesh_reference'] = relpath(row['source'], OUT)
        rows.append(row)
    assert {r['name'] for r in rows} == replacements.keys() | clips
    return rows


def layout(folder):
    from plate_preview import embed
    folder.mkdir(parents=True, exist_ok=True)
    target = folder / 'layout.3mf'
    kit.printer.write_layout(parts(), target, kit.kit64.kit63.plate.plate60.prior.p58.TOWER,
                             'R80 touchpad repair', panel_builder=previous.old.previous.panel_builder)
    embed(target)


if __name__ == '__main__':
    layout(Path(sys.argv[1]))
