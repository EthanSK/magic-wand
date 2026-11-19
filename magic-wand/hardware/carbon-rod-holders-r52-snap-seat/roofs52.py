"""Audit native mechanism paths and identify the R52 CAD journal in the report."""
import json
from pathlib import Path
import sys
from build52 import RUNNING_RADIUS
from support51 import inspect


def describe_journal(output):
    report=json.loads(output.read_text())
    report['parts']['DFRobot_Hole_Bracket']['bearing_space']['nominal_CAD_radius_mm']=RUNNING_RADIUS
    output.write_text(json.dumps(report,indent=2)+'\n')


if __name__=='__main__':
    archive,frame,output=map(Path,sys.argv[1:4])
    inspect(archive,frame,output,trace_roofs=True,other_objects=json.loads(frame.read_text())['extra_objects'])
    describe_journal(output)
