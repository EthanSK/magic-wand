"""Prepare the complete R40 plate with R39's checked PETG recipe.

Run after assembly40.py. This only creates a slicer project; the final slice,
openings, supports and deposited joints require their own audit.
"""
import argparse
import json
from pathlib import Path
from unittest.mock import patch
from zipfile import ZipFile


import holder40 as design
import plate39 as previous

HERE = Path(__file__).resolve().parent
command_audit = previous.command_audit
# Coordinates are the actual R40 down-facing roofs in assembly X/Z, followed
# by their height in the rear-face-down print. R38's over-rod connector roofs
# disappeared when that slot was restored; its old boxes are not evidence of
# support for the new crosswise opening.
LEDGES = (
    ('crosswise OP1 slot', (-15.65, 8.78, 15.65, 11.35), 23.3),
    ('white connector ledge', (-15.75, 7.27, -8.5, 11.12), 21.77),
    ('upper left key lip', (-31.18, 9.93, -17.22, 11.12), 18.35),
    ('outer finger guard', (-30.1, 4.3, -26.3, 5.8), 19.7),
)


def support_boxes(record):
    with patch.object(previous.previous, 'LEDGES', LEDGES):
        return previous.support_boxes(record)


def configure_layout(path, title):
    with patch.object(previous.previous, 'LEDGES', LEDGES), patch.object(previous.previous, 'design', design):
        previous.previous.configure_layout(path, title)


def make(output: Path) -> Path:
    output.mkdir(parents=True, exist_ok=True)
    assert not any(output.iterdir()), 'Use a fresh preparation directory'
    plate = previous.previous.plate
    selected = {n for g in plate.read_json(HERE/plate.BOM)['groups'].values() for n in g['parts']}
    plate.BRACKET = design.BRACKET
    plate.CLIPS = ()
    plate.LOCAL_PADS = (plate.KEY, plate.BRACKET)
    plate.ORIGINS = {n:v for n,v in previous.previous.pads.ORIGINS.items() if n in selected}
    plate.BRIM_WIDTH = 6
    plate.stage_parts = previous.previous.stage_parts
    plate.configure_layout = configure_layout
    plate.build(HERE, output, plate.FLASHFORGE_PROFILE, False, True)
    target = output/'R40-Complete-A1-mini-PETG-layout.3mf'
    previous.configure_motion(target)
    report_path = output/'print-checks.json'
    report = plate.read_json(report_path)
    with ZipFile(target) as archive:
        config = json.loads(archive.read('Metadata/project_settings.config'))
    report.update(layout_sha256=plate.digest(target), driver_sha256=plate.digest(Path(__file__)),
        recipe_source_sha256=plate.digest(previous.previous.BASE),
        small_part_recipe='40 mm/s outer, 65 mm/s inner, 1000/1500 mm/s2; bracket 4 walls and solid infill',
        effective_filament_settings={k:config[k] for k in report['effective_filament_settings']},
        physical_success_verified=False)
    report_path.write_text(json.dumps(report, indent=2)+'\n')
    return target


if __name__ == '__main__':
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('output',type=Path)
    print(make(parser.parse_args().output.resolve()))
