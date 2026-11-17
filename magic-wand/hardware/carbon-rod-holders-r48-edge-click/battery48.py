"""Micron 72217 single-cell cradle and two-rail rosette lid. Local Y follows the rod."""
from functools import lru_cache
from pathlib import Path
import hashlib
import json
import sys

import manifold3d as mf
import numpy as np
import trimesh

HERE = Path(__file__).resolve().parent
OLD = HERE.parent / 'carbon-rod-holders-r47-bottom-click/exports'
BODY, PANEL = 'Battery_Holder', 'Battery_End_Door'
FLOOR = 6.35
CELL = (11.8, 27., 3.9)  # Micron dimensions transposed from length × width × height.
PULL = (0., -33., 0.)
LOAD = (0., 0., 12.)
SLOT_X = 7.67
DETENT = .20
FRONT = -15.05
REAR = float(np.float32(15.20))  # Exact shared rear plane of the inherited binary STL.


def box(x0, x1, y0, y1, z0, z1):
    return mf.Manifold.cube((x1-x0, y1-y0, z1-z0)).translate((x0, y0, z0))


def block(x0, x1, y0, y1, z0, z1, radius):
    section = mf.CrossSection.square((x1-x0-2*radius, y1-y0-2*radius)).offset(
        radius, mf.JoinType.Round, 2., 40)
    return section.extrude(z1-z0).translate((x0+radius, y0+radius, z0))


def union(items):
    return mf.Manifold.batch_boolean(list(items), mf.OpType.Add)


def read(path):
    mesh = trimesh.load_mesh(path)
    return mf.Manifold(mf.Mesh64(mesh.vertices, np.asarray(mesh.faces, np.uint64)))


@lru_cache(maxsize=1)
def old_body():
    return read(OLD / (BODY + '-assembly.stl'))


def cell():
    return box(-CELL[0]/2, CELL[0]/2, -CELL[1]/2, CELL[1]/2, FLOOR, FLOOR + CELL[2])


def leads():
    # Connector stays entirely outside the slot. Draw 35 mm leads from the
    # wire-end face. The drawing illustrates the exit; it is not a mandate
    # to bend a flexible lead into this exact straight pose.
    return {name: mf.Manifold.cylinder(35., .44, .44, 24).rotate((90,0,0)).translate(
        (x,-13.5,8.26)) for name,x in [('positive',1.),('negative',-1.)]}


@lru_cache(maxsize=1)
def body():
    # Reuse the printed snap-ring bores, jaws, spring roots, and lower keel.
    base = old_body() ^ box(-8.5,8.5,-18.,REAR+.01,-6.,5.95)
    floor = box(-8.45,8.45,FRONT,REAR,5.04,FLOOR)
    # Spring bores and jaw tips are below the floor. Keep the original lower
    # keel as the only contact with the rod between the rings.
    back = box(-8.45,8.45,14.05,REAR,5.70,12.80)
    pieces = [base, floor, back]
    for sign in (-1,1):
        wall = box(6.45,8.45,FRONT,REAR,6.1,12.80)
        # A rigid groove takes the spring load away from the pouch.
        slot = box(6.29,SLOT_X,FRONT-1.,14.05,10.42,11.94)
        # An expanded entry steers a free tip into the groove on insertion.
        entry = mf.Manifold.batch_hull([box(6.25,7.96,FRONT-.2,FRONT+.03,10.30,12.06),
                                       box(6.25,SLOT_X,FRONT+1.55,FRONT+1.65,10.42,11.94)])
        wall = wall - slot - entry
        if sign == 1:
            pocket = block(7.39,7.98,-10.48,-7.95,10.42,11.94,.20)
            wall -= pocket
        pieces.append(wall if sign==1 else wall.mirror((1,0,0)))
    return union(pieces)


def petal_windows():
    # Reuse the R24 eight-petal rosette construction, with a 1.1 mm hub,
    # rounded lens openings and a protected peripheral frame on this narrow lid.
    path = HERE.parent / 'carbon-rod-holders-r24-patterned-spacer'
    if str(path) not in sys.path:
        sys.path.insert(0, str(path))
    import spacer24
    masks = [spacer24.circle(0., .6, .62)]
    for a in range(0,360,45):
        masks.append(spacer24.lens(1.8,4.85,.64,a+22.5))
    for y in (-6.5,7.7):
        for s in (-1,1):
            # Two pairs of leaf openings keep continuous webs along the edges.
            masks.append(spacer24.lens(0.,3.0,.64,35.*s).translate((s*-1.35,y-.6)))
    return mf.CrossSection.batch_boolean(masks,mf.OpType.Add)


@lru_cache(maxsize=1)
def panel():
    # Flat top is the print bed face. Deeper edge strips slide on the ledges;
    # the smooth 0.80 mm patterned centre stands 0.65 mm over the resting pouch.
    sheet = block(-7.43,7.43,-15.85,13.88,10.90,11.70,.52)
    sheet -= petal_windows().extrude(1.3).translate((0.,0.,10.67))
    edges = box(5.78,7.43,-15.27,13.28,10.60,11.70)
    for sign in (-1,1):
        sheet += edges if sign==1 else edges.mirror((1,0,0))
        # Small lips on the lid retain the front corners. The middle is open
        # to lay the already-terminated leads in place without threading plugs.
        shoulder = block(3.38,6.12,-15.71,-14.21,7.08,11.70,.33)
        sheet += shoulder if sign==1 else shoulder.mirror((1,0,0))
    # The inner slit and cross slit free a long PETG leaf at the right edge.
    cuts = block(5.53,6.32,-11.35,-.85,10.35,11.91,.29)
    cuts += box(6.05,8.1,-11.35,-10.69,10.35,11.91)
    sheet -= cuts
    # Rounded side detent. The right rail has its receiving pocket while the
    # tall endwall stops the slider's forward travel.
    bump = mf.Manifold.cylinder(1.10,.60,.60,48).scale((1.,1.55,1.)).translate(
        (SLOT_X+DETENT-.60,-9.24,10.60))
    return sheet+bump


def deflect(points, amount=1.):
    """Inward displacement of the isolated side spring for the digital fit check."""
    x,y,z = np.asarray(points).T
    t = np.clip((-.85-y)/8.39,0.,1.)
    active = (x>=6.30) & (y<=-.85) & (y>=-10.7)
    dx = -(DETENT+.10)*amount*t*t*(3.-t)/2*active
    return np.column_stack((dx,np.zeros_like(x),np.zeros_like(x)))


def pinched():
    return panel().warp_batch(lambda p:p+deflect(p))


@lru_cache(maxsize=1)
def inherited_rod_spaces():
    source = HERE.parent / 'carbon-rod-holders-r20-finger-guard'
    if str(source) not in sys.path:
        sys.path.insert(0, str(source))
    import holder20
    prior = holder20.part_regions(BODY)
    return {name: prior[name] for name in ('unloaded_clip_bore','clip_gap_near','clip_gap_far',
                                          'external_wire_bus','reverse_wire_bus')}


def routes():
    cable = union(leads().values())
    # The interior of each rosette and leaf opening must survive actual layer
    # deposition. Exclude the pointed tips where the nozzle rounds the edge.
    pattern = petal_windows().offset(-.24,mf.JoinType.Round).extrude(.60).translate((0.,0.,11.00))
    # Clearance checks exclude the fitted contact face on the floor.
    core = box(-5.86,5.86,-13.46,13.46,FLOOR+.08,FLOOR+3.90)
    empty = {BODY:{**inherited_rod_spaces(),'Micron cell and vertical loading':core + mf.Manifold.batch_hull(
        [core,core.translate(LOAD)]), 'open two-wire exit':cable},
        PANEL:{'Micron pouch below lid':core,'free lead exit between lips':cable,
               'side spring isolation slit':box(5.75,6.07,-10.40,-1.45,10.60,11.70),
               'open rosette hub, petals and leaves':pattern}}
    material = {BODY:{'positive guide root':box(7.79,8.31,-8.,2.,10.20,12.39),
                      'negative guide root':box(-8.31,-7.79,-8.,2.,10.20,12.39)},
                PANEL:{'spring root to sliding rim':box(6.52,7.22,-1.1,.48,10.73,11.57),
                       'continuous patterned border':box(-5.71,-4.98,-4.2,3.4,11.04,11.56)}}
    return empty,material


def print_frame(name, shape):
    x0,_,z0,_,y1,z1=shape.bounding_box()
    if name==BODY:
        return np.array([[1.,0.,0.,x0],[0.,0.,-1.,y1],[0.,1.,0.,z0],[0.,0.,0.,1.]])
    return np.array([[1.,0.,0.,x0],[0.,-1.,0.,y1],[0.,0.,-1.,z1],[0.,0.,0.,1.]])


def anchors(frame, printed):
    # Six 2.0 × 0.4 mm snip ties on the rigid rear frame, sized like the
    # proven pad necks. Nothing touches the clip jaws below the tray.
    sites=[]; pads=[]
    ox,oz=-frame[0,3],-frame[2,3]
    for sign in (-1,1):
        for z in (7.0,11.0):
            x=sign*8.45
            xlim=sorted((x-sign*.52,x+sign*3.0))
            neck=box(*xlim, z-1.,z+1.,0.,.4)
            lo,hi=sorted((x+sign*2.2,x+sign*12.2))
            pad=block(lo,hi,z-1.88,z+1.88,0.,.4,.9)
            pads.append((neck+pad).translate((ox,oz,0.)))
            sites.append([x+ox,z+oz,sign,0])
        x=sign*4.15;z=12.80
        neck=box(x-1.,x+1.,z-.52,z+3.,0.,.4)
        pad=block(x-3.92,x+3.92,z+2.2,z+12.2,0.,.4,1.0)
        pads.append((neck+pad).translate((ox,oz,0.)))
        sites.append([x+ox,z+oz,0,1])
    bonds=[round((p^printed).volume(),5) for p in pads]
    assert min(bonds)>.33 and max(bonds)<.45,bonds
    combined=union(pads)
    assert len(combined.decompose())==6
    return combined,{'pad_count':6,'sites_print_xy_outward':sites,'tie_width_mm':2.,
                     'pad_thickness_mm':.4,'root_overlap_mm3':bonds,
                     'combined_first_layer_area_mm2':round((combined+printed).slice(.10).area(),3)}


def rod():
    return mf.Manifold.cylinder(45.,4.,4.,128).rotate((-90,0,0)).translate((0.,-20.,0.))


def checks():
    tray,lid,pouch=body(),panel(),cell()
    relaxed=pinched()
    envelope=mf.Manifold.batch_hull([pouch,pouch.translate(LOAD)])
    wire=union(leads().values())
    travel=np.linspace(PULL[1],0.,133)
    released_hit=max((tray^relaxed.translate((0.,float(d),0.))).volume() for d in travel)
    neutral_catch=max((tray^lid.translate((0.,float(d),0.))).volume() for d in travel)
    pouch_hit=max((pouch^lid.translate((0.,float(d),0.))).volume() for d in travel)
    lead_hit=max((wire^lid.translate((0.,float(d),0.))).volume() for d in travel)
    # The complete baseline rod intersections are expected at the two working
    # rings only. Extra collar contact elsewhere would change their snap feel.
    seated=tray+lid
    capture={name:round((pouch.translate(delta)^seated).volume(),5)
             for name,delta in [('left',(-.85,0.,0.)),('right',(.85,0.,0.)),
                                ('wire_end',(0.,-1.,0.)),('far_end',(0.,1.,0.)),
                                ('up',(0.,0.,.9)),('down',(0.,0.,-.3))]}
    cover_capture={name:round((lid.translate(delta)^tray).volume(),5)
                   for name,delta in [('left',(-.48,0.,0.)),('right',(.48,0.,0.)),
                                      ('up',(0.,0.,.43)),('down',(0.,0.,-.38))]}
    retained_routes={name:round((tray^space).volume(),6) for name,space in inherited_rod_spaces().items()}
    change=(tray-old_body())^rod()
    removed=(old_body()-tray)^rod()
    right_root=routes()[1][PANEL]['spring root to sliding rim']
    stop=lid.translate((0.,.40,0.))^tray
    layout={'cell_dimensions_LWH_mm':[27.,11.8,3.9],'cell_mass_g':2.05,'wire_length_mm':35.,
            'wire_diameter_assumption_mm':.88,'open_wire_exit_width_mm':6.76,
            'connector':'Molex 2 mm, pin 1 negative; remains outside the cradle',
            'cell_center_xyz_mm':[0.,0.,FLOOR+CELL[2]/2],
            'side_free_mm':round(6.45-CELL[0]/2,3),'end_free_mm':round(14.05-CELL[1]/2,3),
            'cell_to_panel_underside_mm':round(10.90-(FLOOR+CELL[2]),3),
            'pouch_to_front_panel_lips_y_mm':round(14.21-CELL[1]/2,3),
            'center_panel_thickness_mm':.80,'sliding_edge_thickness_mm':1.10,
            'groove_height_mm':1.52,'straight_edge_clearance_mm':SLOT_X-7.43,
            'detent_interference_mm':DETENT,'modelled_spring_displacement_mm':DETENT+.1,
            'cantilever_strain_proxy_percent':round(100*1.5*(7.43-6.32)*(DETENT+.10)/8.39**2,4),
            'load_displacement_mm':list(LOAD),'open_panel_displacement_mm':list(PULL)}
    measurements={'single_piece_holder':len(tray.decompose())==1,'single_piece_lid':len(lid.decompose())==1,
        'fitted_slide_overlap_mm3':(tray^lid).volume(),'cell_loading_overlap_mm3':(tray^envelope).volume(),
        'cell_at_resting_lid_overlap_mm3':(pouch^lid).volume(),'cell_throughout_lid_slide_overlap_mm3':pouch_hit,
        'released_lid_through_grooves_overlap_mm3':released_hit,'free_detent_resists_opening_overlap_mm3':neutral_catch,
        'overtravel_stop_overlap_at_0.4_mm3':stop.volume(),
        'lead_to_body_mm3':(wire^tray).volume(),'lead_throughout_lid_slide_overlap_mm3':lead_hit,
        'new_rod_interference_mm3':change.volume(),'lost_original_rod_grip_mm3':removed.volume(),
        'spring_root_core_fraction':(lid^right_root).volume()/right_root.volume(),
        'original_rod_and_wire_routes_overlap_mm3':retained_routes,
        'separate_pattern_openings':len(petal_windows().decompose()),
        'cell_stop_contacts_after_free_play_mm3':capture,'lid_guide_capture_after_free_play_mm3':cover_capture}
    zeros=['fitted_slide_overlap_mm3','cell_loading_overlap_mm3','cell_at_resting_lid_overlap_mm3',
           'cell_throughout_lid_slide_overlap_mm3','released_lid_through_grooves_overlap_mm3','lead_to_body_mm3',
           'lead_throughout_lid_slide_overlap_mm3','new_rod_interference_mm3','lost_original_rod_grip_mm3']
    ok=(all(measurements[k]<.001 for k in zeros) and measurements['single_piece_holder'] and
        measurements['single_piece_lid'] and neutral_catch>.09 and stop.volume()>.3 and
        measurements['spring_root_core_fraction']>.98 and min(capture.values())>.1 and
        min(cover_capture.values())>.1 and max(retained_routes.values())<.002 and measurements['separate_pattern_openings']==13 and layout['cantilever_strain_proxy_percent']<1.0)
    return {'passed':bool(ok),'layout':layout,'measurements':measurements,'sample_count':len(travel),
            'physical_fit_friction_fatigue_verified':False,'clearance_basis':'Nominal manufacturer cell dimensions.'}


def file_sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def save(shape,path):
    mesh=shape.to_mesh64()
    stl=trimesh.Trimesh(mesh.vert_properties[:,:3],mesh.tri_verts,process=False)
    stl.export(path)
    actual=trimesh.load_mesh(path)
    assert actual.is_watertight and actual.is_winding_consistent and actual.volume>0,path
    return file_sha(path)


def generate(scratch):
    output=scratch/'battery48'
    output.mkdir(parents=True,exist_ok=True)
    review=checks()
    checks_path=output/'battery-checks.json'
    checks_path.write_text(json.dumps(review,indent=2)+'\n')
    if not review['passed']:
        raise ValueError(review)
    parts={}
    for name,shape in ((BODY,body()),(PANEL,panel())):
        frame=print_frame(name,shape)
        printed=shape.transform(np.linalg.inv(frame)[:3])
        assembly=output/(name+'-assembly.stl')
        mesh=output/(name+'-SOURCE-REQUIRES-PREPARATION.stl')
        item={'assembly_stl':assembly.name,'assembly_sha256':save(shape,assembly),
              'print_stl':mesh.name,'print_sha256':save(printed,mesh),
              'print_to_assembly':frame.tolist(),'bounds_mm':list(shape.bounding_box()),
              'volume_mm3':round(shape.volume(),4)}
        if name==BODY:
            pads,info=anchors(frame,printed)
            pad_file=output/(name+'-ANCHOR-REMOVE-AFTER-PRINT.stl')
            item.update(pad_stl=pad_file.name,pad_sha256=save(pads,pad_file),anchors=info)
        parts[name]=item
    review_assets={}
    deformed=output/'battery-panel-released.stl'
    mesh=trimesh.load_mesh(output/parts[PANEL]['assembly_stl'],process=False)
    # Preserve the source triangle/vertex order for the guide's spring morph.
    mesh.vertices+=deflect(mesh.vertices)
    mesh.export(deformed)
    for name,solid in {'battery-cell':cell(),**{'battery-'+k:v for k,v in leads().items()}}.items():
        file=output/(name+'.stl')
        review_assets[name]={'file':file.name,'sha256':save(solid,file)}
    review_assets['released_panel']={'file':deformed.name,'sha256':file_sha(deformed)}
    manifest={'revision':'r48','parts':parts,'review_assets':review_assets,'checks':checks_path.name,
              'checks_sha256':file_sha(checks_path),'source_sha256':file_sha(Path(__file__)),
              'supplier':'https://www.micronradiocontrol.co.uk/lipo_1s.html',
              'assembly':review['layout'],'physical_fit_verified':False}
    (output/'manifest.json').write_text(json.dumps(manifest,indent=2)+'\n')
    print(json.dumps(manifest,indent=1))


if __name__=='__main__':
    generate(Path(sys.argv[1]))
