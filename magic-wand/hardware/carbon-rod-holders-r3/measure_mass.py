#!/usr/bin/env python3
"""Measure model/brim filament from the actual sliced two-part project."""
import json
import cad
if __name__ == '__main__':
    m = cad.load_previous('measure_mass', cad.HERE.parent / 'carbon-rod-holders').m
    result = m.inspect(cad.HERE / 'exports/Holder-pair-sliced.3mf')
    assert result['build_instances'] == 2
    result['scope'] = 'One five-key carrier and one R2 sensor holder; purchased hardware, rod and tape excluded. Slicer estimate, not weighed.'
    (cad.HERE / 'exports/mass.json').write_text(json.dumps(result, indent=2) + '\n')
    print({k: result[k] for k in ['object_printed_parts_g', 'printed_parts_g', 'supports_and_brim_g', 'total_slicer_g']})
