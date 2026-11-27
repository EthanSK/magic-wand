"""Write the complete nine-piece R72 plate with the battery-mouth relief at its new position."""
from os.path import relpath
from pathlib import Path
import sys
import design72 as model
import kit71 as previous


def parts():
    rows = previous.parts()
    for row in rows:
        if row['name'] == 'Key_Carrier':
            row['source'] = model.OUT / model.HOLDER
            row['assembly_to_print'] = previous.printer.pose_for(row['source'], *previous.kit64.PRINT_POSES['Key_Carrier'])
            panel = dict(row['panel'])
            mouth = previous.pouch_mouth()
            panel['keep_clear'] = [
                [box[0]+model.INBOARD, box[1], box[2]+model.INBOARD, box[3]] if list(box)==mouth else list(box)
                for box in panel['keep_clear']]
            if len(panel['keep_clear']) != sum(list(box) != mouth for box in panel['keep_clear']):
                raise ValueError('Outdated battery entrance in base layout')
            ties = [dict(tie) for tie in previous.CARRIER_TIES]
            ties[0].update(at=-26.45)            # top of the backed outer roof
            ties[1]['at'] += model.INBOARD       # reinforced heel under the outer wall
            ties[2].update(face='-y', at=-26.5, neck=previous.SLIM)
            ties[3]['at'] = -8.0                 # inner rail's supported rear lip
            panel['ties'] = ties
            row['panel'] = panel
        row['mesh_reference'] = relpath(row['source'], model.OUT)
    return rows


def layout(path):
    from plate_preview import embed
    previous.printer.write_layout(parts(), Path(path), previous.kit64.kit63.plate.plate60.prior.p58.TOWER,
                                  'R72 complete key holder', panel_builder=previous.panel_builder)
    embed(Path(path))


if __name__ == '__main__':
    layout(sys.argv[1])
