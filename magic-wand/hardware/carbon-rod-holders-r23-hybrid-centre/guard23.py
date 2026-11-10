#!/usr/bin/env python3
"""R23 reinforced guard runners: R22's six runner paths regrown with a larger rounded section by R22's own
layer-by-layer supported-growth code (each 0.2 mm print layer grows only from the layer below), one runner at a
time so each member is its own solid for slice-coverage audits. R22 files are not modified; its parameter dict is
overridden in memory only while growing."""
import sys
sys.dont_write_bytecode = True
from functools import lru_cache
import copy
import numpy as np
import holder23 as h

h22 = h.h22
GR = h.L['guard_reinforcement']


def _grow(beams):
    saved = copy.deepcopy(h22.G); s = GR['r23_section_mm']
    try:
        h22.G.update(width_mm=s['width'], thickness_mm=s['thickness'], section_round_mm=s['corner_round'], blend_half_length_mm=s['blend_half_length'], beams=beams)
        h22.guard_layers.cache_clear()
        layers, stats = h22.guard_layers()
        pieces = [h22.xz(sec, y0 - .001, y1 + .001) for y0, y1, sec in layers if sec.area() > 0]
        areas = [(round((y0 + y1) / 2, 2), round(sec.area(), 3)) for y0, y1, sec in layers if sec.area() > 0]
        return h.union(pieces), stats, areas
    finally:
        h22.G.clear(); h22.G.update(saved); h22.guard_layers.cache_clear()


@lru_cache(maxsize=1)
def members():
    """{runner name: (solid, growth stats, [(y, section area per print layer)])} in the assembly frame."""
    return {b['name']: _grow([b]) for b in h22.G['beams']}


def member(name): return members()[name][0]


def runners(): return h.union([m[0] for m in members().values()])


def r22_runner_sections():
    """R22 section areas along each runner for comparison (original parameters)."""
    out = {}
    for b in h22.G['beams']:
        sec = [h22.beam_section(b, y) for y in np.arange(-8.0, b['root_y_mm'], 1.0)]
        out[b['name']] = round(min(s.area() for s in sec if s is not None), 3)
    return out
