"""Recreate the exact two-object layout, or check the resulting native machine commands."""
import argparse
from pathlib import Path
from parts52 import audit
from plate52 import HERE, compose


def main(out, check):
    out.mkdir(parents=True,exist_ok=True)
    layout=out/'layout.3mf'
    if check:
        audit(out/'Mechanisms.gcode.3mf',layout,out/'separation-and-machine.json',
              {'Key_Carrier','DFRobot_Hole_Bracket'})
    else:
        compose(layout,HERE/'exports')


if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('output',type=Path)
    parser.add_argument('--check',action='store_true')
    args=parser.parse_args()
    main(args.output,args.check)
