"""Slice the R37 plate using the verified R36 A1 mini PETG profile."""

import argparse
from pathlib import Path

import holder37 as design
import plate36

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("output", type=Path)
    plate36.design = design
    plate36.build(parser.parse_args().output, source=Path(__file__).resolve().parent)
