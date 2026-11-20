"""Check each compact pad in the native slice and package the reviewed plate."""
import argparse
from pathlib import Path

from plate56 import HERE, SMALL_PADS
from check55 import check
from release55 import release

PRINT_NAME = 'R56-Small-Pads-Complete-Hinge-print-only.3mf'


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('plate', type=Path)
    parser.add_argument('--release', action='store_true')
    parser.add_argument('--output', type=Path, default=HERE / 'exports')
    args = parser.parse_args()
    if args.release:
        release(args.plate, args.output, print_name=PRINT_NAME)
    else:
        check(args.plate, compact_pads=SMALL_PADS)
