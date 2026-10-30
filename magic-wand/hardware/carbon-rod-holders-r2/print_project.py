#!/usr/bin/env python3
"""Compose the preserved accessory-pair Bambu recipe for this revision."""
import argparse
from pathlib import Path
import cad
if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--scratch',type=Path,required=True);p.add_argument('--slice',action='store_true');a=p.parse_args()
    m=cad.load('print_project');m.HERE=cad.HERE;m.build(cad.HERE/'exports',a.scratch.resolve(),a.slice)
