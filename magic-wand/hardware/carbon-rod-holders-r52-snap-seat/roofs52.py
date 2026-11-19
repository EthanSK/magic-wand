"""Audit native mechanism paths and identify the R52 CAD journal in the report."""
import json
from pathlib import Path
import sys
from build52 import RUNNING_RADIUS
import numpy as np
import support51


def inspect(*args, **kwargs):
    # R51 evaluates a window around the permanent model. Pads now extend
    # beyond its borders. Rasterize a padded edge and retain the same window.
    original = support51.footprint
    def bounded(points, origin, shape):
        margin = 12
        high = origin + np.array(shape[::-1]) * support51.GRID
        overlap = np.all((points[:, :2] >= origin-.5) & (points[:, :2] <= high+.5),axis=1)
        padded = original(points[overlap], origin-margin*support51.GRID, np.asarray(shape)+2*margin)
        return padded[margin:-margin,margin:-margin]
    support51.footprint=bounded
    try:
        return support51.inspect(*args, **kwargs)
    finally:
        support51.footprint=original


def describe_journal(output):
    report=json.loads(output.read_text())
    report['parts']['DFRobot_Hole_Bracket']['bearing_space']['nominal_CAD_radius_mm']=RUNNING_RADIUS
    output.write_text(json.dumps(report,indent=2)+'\n')


if __name__=='__main__':
    archive,frame,output=map(Path,sys.argv[1:4])
    inspect(archive,frame,output,trace_roofs=True,other_objects=json.loads(frame.read_text())['extra_objects'])
    describe_journal(output)
