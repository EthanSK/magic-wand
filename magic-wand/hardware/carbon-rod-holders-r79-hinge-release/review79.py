"""Use each part's last matching native reference and inspect new local bridge paths."""
import kit70
import plate78
import review78
from plate79 import CLIPS


def inspect(folder):
    return review78.inspect(folder, baseline=plate78.OUT / 'print-mechanisms',
                            part_baselines={name: kit70.OUT / 'print-mechanisms' for name in CLIPS})
