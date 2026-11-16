"""Remove the isolated inter-band saddle tip below its first joined section."""
import manifold3d as mf


def prepare(body):
    # In the keys-up slice the tiny pointed underside of the saddle starts
    # separately and only joins its longitudinal wall at assembly Z3.0.
    # Limit this flat to the isolated tip. Both gripping bands stay intact.
    bounds=(2.44,20.80,2.52,3.27,22.35,2.98)
    x,y,z,X,Y,Z=bounds
    cutter=mf.Manifold.cube((X-x,Y-y,Z-z)).translate((x,y,z))
    result=body-cutter
    removed=body.volume()-result.volume()
    assert result.status()==mf.Error.NoError and 0.<removed<.25,removed
    return result, {'removed_mm3':removed,'added_mm3':0.,'cut_bounds_assembly_mm':bounds,
        'feature':'Isolated lower tip of the inter-band rod saddle at the diagonal cutout.',
        'physical_grip_and_fatigue_verified':False}
