"""Local underside bevels derived from the actual float32 export, standing.

The procedural R45 relief leaves two small unsupported socket-lip starts after
export. Reapplying its existing protected relief to the exported body removes
them. The moved OP1 pocket also needs a gradual underside at print X36.0–42.5,
Y11.7–14.0, Z20.4–27.4. Neither repair adds disposable material into a hole.
Actual native starts, load paths and routes must still be checked after slicing.
"""
import numpy as np
import manifold3d as mf
from standing_relief45 import make as socket_relief


def prepare(carrier, frame, routes, structural, platforms, stage, load, save, inside_existing_steps):
    inverse = np.linalg.inv(frame)[:3]
    stage.mkdir(parents=True, exist_ok=True)
    reference = stage / 'R47-before-local-relief-assembly.stl'
    save(reference, carrier)
    body = load(reference).transform(inverse)
    first, sockets = socket_relief(body, body, [], frame, routes, structural)
    relieved = body - first
    mask = mf.CrossSection.square((6.5, 2.3)).translate((36., 11.7))
    allowed = mask.extrude(7.).translate((0., 0., 20.4))
    targets = [target.transform(inverse) ^ allowed for target in structural.values()]
    targets.append(platforms.transform(inverse) ^ allowed)
    keep = mf.Manifold.batch_boolean(targets, mf.OpType.Add)
    previous = None
    cuts = []
    for k in range(1, round(relieved.bounding_box()[5] / .2) + 1):
        top = k * .2
        middle = top - .1
        current = relieved.slice(middle)
        if previous is not None and 20.4 < middle < 27.4:
            unsupported = ((current ^ mask) - previous.offset(.10)) - keep.slice(middle).offset(.05)
            if not unsupported.is_empty():
                cuts.append(unsupported.extrude(.20002).translate((0., 0., top - .20001)))
                current -= unsupported
        previous = current
    cut = mf.Manifold.batch_boolean(cuts, mf.OpType.Add) - keep
    removed = body ^ (first + cut)
    losses = {name: max(0., (target.transform(inverse) ^ removed).volume())
              for name, target in structural.items()}
    assert max(losses.values(), default=0.) < 1e-5, losses
    result = (relieved - cut).transform(frame[:3])
    assert result.status() == mf.Error.NoError
    # The overlapping layer cuts can leave very small, disconnected floor
    # fins after float32 export. Remove only those bounded local remnants;
    # then prove the exact export has one substantial body. Do not simplify
    # here: simplifying the already quantized floor creates another remnant.
    raw_export = stage / 'R47-after-relief-before-cleanup.stl'
    save(raw_export, result)
    exported = load(raw_export)
    pieces = sorted(exported.decompose(), key=lambda item: -item.volume())
    discarded = [item for item in pieces[1:] if abs(item.volume()) > 1e-8]
    central = allowed.transform(frame[:3])
    central_bounds = central.bounding_box()
    def inside_central(item):
        bounds = item.bounding_box()
        return all(bounds[i] >= central_bounds[i] - .001
                   and bounds[i + 3] <= central_bounds[i + 3] + .001 for i in range(3))
    assert all(inside_existing_steps(item) or inside_central(item)
               for item in discarded), 'Cleanup extends beyond the measured floor repairs'
    positive = sum(max(0., item.volume()) for item in discarded)
    negative = sum(max(0., -item.volume()) for item in discarded)
    assert positive < .25 and negative < .25, (positive, negative)
    result = pieces[0]
    final_export = stage / 'R47-cleanup-validation.stl'
    save(final_export, result)
    verified = load(final_export)
    assert sum(item.volume() > .001 for item in verified.decompose()) == 1
    cleanup_losses = {name: max(0., (target ^ exported).volume() - (target ^ result).volume())
                      for name, target in structural.items()}
    assert max(cleanup_losses.values(), default=0.) < 1e-5, cleanup_losses
    return result, {
        'socket_relief': sockets,
        'central_pocket_removed_mm3': max(0., (relieved ^ cut).volume()),
        'complete_removed_mm3': max(0., removed.volume()),
        'structural_witness_losses_mm3': losses,
        'central_lateral_growth_per_0p2mm_layer_mm': .10,
        'central_print_bounds_mm': [36., 11.7, 20.4, 42.5, 14., 27.4],
        'export_cleanup': {
            'dropped_floor_fragments_mm3': positive,
            'filled_floor_void_shells_mm3': negative,
            'substantial_final_export_bodies': 1,
            'structural_witness_losses_mm3': cleanup_losses,
            'discarded': [{'volume_mm3': item.volume(), 'assembly_bounds_mm': list(item.bounding_box())}
                          for item in discarded],
        },
        'native_validation_required': True,
    }
