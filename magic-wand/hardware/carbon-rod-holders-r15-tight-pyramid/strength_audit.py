#!/usr/bin/env python3
"""Measure exported clip sections and surviving actual radial extrusion tracks.

This is a geometric/process audit, not a force, fatigue or material simulation.
"""
import argparse,json,math,zipfile,xml.etree.ElementTree as E
from pathlib import Path
import numpy as np,trimesh
import cad
import deliverables
import start_audit
from verify_slice import q,N
OUT=cad.HERE/'exports'

def read_solid(name):
    m=trimesh.load_mesh(OUT/(name+'-assembly.stl'))
    return q.solid(m.vertices,m.faces)

def radial_section(solid,y,angle):
    a=math.radians(angle);hits=solid.ray_cast((0,y,0),(8*math.cos(a),y,8*math.sin(a)))
    assert len(hits)>=2,(y,angle,'missing exported clip section')
    return float(np.linalg.norm(np.array(hits[1].position)-hits[0].position))

def section(solid,centre,direction):
    """The solid interval containing the probe, with both endpoints outside."""
    c=np.array(centre,dtype=float);d=np.array(direction,dtype=float);d/=np.linalg.norm(d)
    hits=sorted(solid.ray_cast(c-d*100,c+d*100),key=lambda h:h.distance)
    for a,b in zip(hits[::2],hits[1::2]):
        if a.distance<.5<b.distance:
            return float(np.linalg.norm(np.array(b.position)-a.position)),np.array(a.position),np.array(b.position)
    raise AssertionError(('Probe is not in material',centre,direction))

def feature(solid,points,label,probes,direction,minimum,load,decision,physical_test):
    """Actual sections and centre-line extrusion tracks in the same XZ plane.

    A track count is a distinct bead-centre cluster, never the number of
    samples. The Y axis is the layer axis for these four print transforms.
    """
    records=[]
    for centre in probes:
        d=np.array(direction(centre)if callable(direction)else direction,dtype=float)
        assert abs(d[1])<.001;d/=np.linalg.norm(d)
        transverse=np.array([-d[2],0,d[0]])
        c=np.array(centre,dtype=float);thickness,a,b=section(solid,c,d)
        assert thickness>=minimum-.02,(label,thickness,minimum)
        nearest=float(points[np.argmin(abs(points[:,1]-c[1])),1]);assert abs(nearest-c[1])<.12
        c[1]=nearest;actual_thickness,a,b=section(solid,c,d)
        pp=points[abs(points[:,1]-nearest)<.01];relative=pp-c
        along=relative@d;low=float((a-c)@d);high=float((b-c)@d)
        values=np.sort(along[(abs(relative@transverse)<.09)&(along>=low)&(along<=high)])
        clusters=[]
        for value in values:
            if not clusters or value-clusters[-1][-1]>.17:clusters.append([float(value)])
            else:clusters[-1].append(float(value))
        assert len(clusters)>=2,(label,centre,'Fewer than two surviving tracks',clusters)
        records.append({'probe_assembly_mm':list(centre),'section_direction_assembly':d.tolist(),'STL_section_mm':round(thickness,4),
                        'sampled_layer_assembly_y_mm':nearest,'sampled_layer_section_mm':round(actual_thickness,4),
                        'extrusion_track_centres_relative_mm':[round(float(np.median(v)),3)for v in clusters]})
    return {'feature':label,'probes':records,'minimum_sampled_section_mm':round(min(r['STL_section_mm']for r in records),4),
            'minimum_sampled_track_count':min(len(r['extrusion_track_centres_relative_mm'])for r in records),
            'load_case':load,'layer_direction':'Assembly Y is the layer axis; XZ is the layer plane.',
            'decision':decision,'required_physical_test':physical_test,'physical_strength_verified':False}

def track_clusters(values):
    clusters=[]
    for value in np.sort(values):
        if not clusters or value-clusters[-1][-1]>.17:clusters.append([float(value)])
        else:clusters[-1].append(float(value))
    return clusters

def spine_neck_scan(solid,points,widths,name,minimum,layer=.2,step=.1,fractions=(-.8,-.4,0.,.4,.8)):
    """Bounded native section scan over one fixed spine's whole joining span.

    Reviewer N16: point probes far along each spine missed the neck where it
    leaves its clip ring. Cast vertical (Z) Manifold rays every 0.1 mm of Y,
    0.05 mm off every layer boundary and modelled face, at five X positions
    inside the local spine width, from the crown seed to the floor root. Then
    count actual bead-centre clusters on each ray at every printed layer of
    the span, sectioning the mesh at that layer's slicing middle. Under a
    thousand ray casts for both spines on small point subsets; no point-grid
    containment or proximity query. A probe outside material fails loudly.
    """
    s=cad.spine_layouts()[name];hw=cad.P['finger_recess']['spine_crown_half_width_mm']
    (x0,x1),(r0,_),crown=s['root_x_mm'],s['root_y_mm'],s['crown_y_mm']
    start,stop=crown-.1,r0;near=crown+.1;bed=cad.front_plane();probe_z=4.9
    def xs(y):
        t=min(1.,max(0.,(y-near)/(r0-near)))
        left,right=hw+(-x0-hw)*t,hw+(x1-hw)*t
        return [f*(right if f>0 else left)for f in fractions]
    first=math.ceil((start-bed-step/2)/step-1e-9);last=math.floor((stop-bed-step/2)/step+1e-9)
    mesh=[]
    for k in range(first,last+1):
        y=bed+step/2+k*step
        for x in xs(y):
            thickness,_,_=section(solid,(x,y,probe_z),(0,0,1))
            assert thickness>=minimum-.02,(name,'Spine neck below the strength screen',x,y,thickness,minimum)
            mesh.append((round(thickness,4),round(x,4),round(y,4)))
    # Actual layers whose middle lies in the span. Pre-select the spine's own
    # small bead subset once; each layer/ray then filters only that subset.
    box=(points[:,1]>=start-.01)&(points[:,1]<=stop+layer+.01)&(points[:,0]>=x0-.5)&(points[:,0]<=x1+.5)&(points[:,2]>=3.)&(points[:,2]<=6.5)
    local,local_widths=points[box],widths[box];layers=[]
    # Keep layer middles strictly inside the span, off the end faces.
    tops=np.unique(np.round(local[:,1],3));tops=tops[(tops-layer/2>start+.01)&(tops-layer/2<stop-.01)]
    assert len(tops)>=int((stop-start)/layer)-1,(name,'Missing printed layers in the spine span',len(tops))
    for top in tops:
        middle=float(top)-layer/2;row=local[abs(local[:,1]-top)<.01];row_widths=local_widths[abs(local[:,1]-top)<.01];rays=[]
        for x in xs(middle):
            thickness,a,b=section(solid,(x,middle,probe_z),(0,0,1))
            assert thickness>=minimum-.02,(name,'Spine section below the strength screen at a slicing middle',x,middle,thickness,minimum)
            on=(abs(row[:,0]-x)<.09)&(row[:,2]>=a[2])&(row[:,2]<=b[2])
            clusters=track_clusters(row[on,2])
            assert len(clusters)>=2,(name,'Fewer than two surviving spine tracks',float(top),x,clusters)
            centres=[float(np.median(c))for c in clusters]
            envelope=centres[-1]-centres[0]+float(np.median(row_widths[on]))
            rays.append({'x_mm':round(x,4),'STL_section_mm':round(thickness,4),'track_count':len(clusters),
                         'printed_bead_envelope_mm':round(envelope,4)})
        layers.append({'layer_top_assembly_y_mm':round(float(top),4),'mesh_section_assembly_y_mm':round(middle,4),
                       'minimum_STL_section_mm':min(r['STL_section_mm']for r in rays),
                       'minimum_track_count':min(r['track_count']for r in rays),
                       'minimum_printed_bead_envelope_mm':min(r['printed_bead_envelope_mm']for r in rays),'rays':rays})
    # The reported minimum covers both the offset grid and the slicing middles.
    worst=min(mesh+[(r['STL_section_mm'],r['x_mm'],l['mesh_section_assembly_y_mm'])for l in layers for r in l['rays']])
    return {'span_assembly_y_mm':[round(start,4),round(stop,4)],'clip_ring_back_face_y_mm':round(s['ring_y_mm']+cad.P['rod']['ring_width']/2,4),
            'mesh_ray_step_mm':step,'mesh_rays':len(mesh),'probe_z_mm':probe_z,'x_fractions_of_local_half_width':list(fractions),
            'minimum_STL_section_mm':worst[0],'minimum_at_assembly_xy_mm':[worst[1],worst[2]],
            'offset_grid_per_y_minimum_STL_section_mm':[[y,min(m[0]for m in mesh if m[2]==y)]for y in sorted({m[2]for m in mesh})],
            'printed_layers':layers,'minimum_track_count':min(l['minimum_track_count']for l in layers),
            'minimum_printed_bead_envelope_mm':min(l['minimum_printed_bead_envelope_mm']for l in layers),
            'screen_mm':minimum,'screen_allowance_mm':.02,
            'method':'Native Manifold vertical ray sections through the exported assembly STL over the complete crown-to-root span, plus actual G-code bead-centre clusters on the same rays at every printed layer. The bead envelope is recorded, not screened.'}

def audit(exports=None):
    global OUT
    OUT=exports or OUT
    manifest=json.loads((OUT/'manifest.json').read_text());project=OUT/deliverables.project_name(OUT)
    with zipfile.ZipFile(project)as archive:
        cfg=E.fromstring(archive.read('Metadata/model_settings.config'))
        model=E.fromstring(archive.read('3D/3dmodel.model'));cache={'3D/3dmodel.model':model}
        roots={o.get('id'):o for o in model.findall('m:resources/m:object',N)}
        builds={i.get('objectid'):q.transform(i.get('transform'))for i in model.findall('m:build/m:item',N)}
        settings=json.loads(archive.read('Metadata/project_settings.config'))
        data,features,_=q.extrusion_points(archive.read('Metadata/plate_1.gcode').decode(),.15)
        off=np.array([float(x)for x in settings['extruder_offset'][0].split('x')]+[0])
        rows={};row_widths={}
        for obj in cfg.findall('object'):
            name=q.metadata(obj)['name'];normal=next(p for p in obj.findall('part')if q.metadata(p).get('name')==name)
            comp=next(c for c in roots[obj.get('id')].findall('m:components/m:component',N)if c.get('objectid')==normal.get('id'))
            path=next((v.lstrip('/')for k,v in comp.attrib.items()if k.endswith('}path')),'3D/3dmodel.model')
            if path not in cache:cache[path]=E.fromstring(archive.read(path))
            child=next(o for o in cache[path].findall('m:resources/m:object',N)if o.get('id')==normal.get('id'))
            vv=np.array([[float(v.get(k))for k in 'xyz']for v in child.findall('m:mesh/m:vertices/m:vertex',N)])
            vv=q.points(q.points(vv,q.transform(comp.get('transform'))),builds[obj.get('id')])
            expected=trimesh.load_mesh(OUT/deliverables.normal_name(name));place=(vv.min(0)+vv.max(0)-expected.bounds.sum(0))/2
            local=data[:,:3]+off-place;mask=np.all(local>=expected.bounds[0]-.4,1)&np.all(local<=expected.bounds[1]+.4,1)
            rows[name]=q.points(local[mask],np.array(manifest['parts'][name]['print_to_assembly']))
            row_widths[name]=data[mask,3]
    report={'project_sha256':cad.sha(project),'manifest_sha256':cad.sha(OUT/'manifest.json'),
            'checker_sha256':cad.sha(cad.HERE/'strength_audit.py'),'physical_strength_verified':False,
            'method':'Ray intersections through final exported assembly STLs; actual G-code radial track clusters at clip midplanes. Both fixed floor spines also get a bounded native ray scan over their complete crown-to-root span with actual per-layer track clusters. No force/fatigue simulation.', 'clips':{}}
    for name,centres in [('Key_Carrier',cad.carrier_clip_centres()),('Battery_Holder',cad.battery_clip_centres()),('XIAO_Rod_Holder',[-3.8,22.2])]:
        if name not in rows:continue
        solid=read_solid(name);points=rows[name];records=[]
        for y in centres:
            sections={str(a):round(radial_section(solid,y,a),4)for a in [-70,-55,0,90,180,235,250]}
            assert min(sections.values())>.95,(name,y,sections)
            nearest=float(points[np.argmin(abs(points[:,1]-y)),1]);p=points[abs(points[:,1]-nearest)<.01]
            theta=np.degrees(np.arctan2(p[:,2],p[:,0]));radius=np.linalg.norm(p[:,[0,2]],axis=1)
            tracks={}
            for angle in [-55,90,235]:
                delta=abs((theta-angle+180)%360-180);r=np.sort(radius[(delta<3)&(radius>3.95)&(radius<5.6)])
                clusters=[]
                for value in r:
                    if not clusters or value-clusters[-1][-1]>.17:clusters.append([float(value)])
                    else:clusters[-1].append(float(value))
                tracks[str(angle)]=[round(float(np.median(c)),3)for c in clusters]
                assert len(clusters)>=2,(name,y,angle,tracks)
            records.append({'axial_centre_mm':y,'radial_STL_sections_mm':sections,'sampled_actual_layer_assembly_y_mm':nearest,'radial_extrusion_track_centres_mm':tracks})
        report['clips'][name]=records
    if 'Key_Carrier'in rows:
        key=read_solid('Key_Carrier');floors={}
        # Scan the entire front-to-rear connection, not only convenient
        # point probes. In the upright print this is an interlayer load path.
        upright=key.rotate((90,0,0));load_paths={}
        for i in manifest.get('key_indices',range(5)):
            x,y=cad.key_positions()[i];zone=q.CrossSection([[[x-9.11,-20],[x+9.11,-20],[x+9.11,20],[x-9.11,20]]])
            measurements=[];points=rows['Key_Carrier'];widths=row_widths['Key_Carrier']
            rail_windows=[q.CrossSection([[[x+sign*7.69,-(cad.P['keys']['pcb_z']+1.41)],
                [x+sign*9.11,-(cad.P['keys']['pcb_z']+1.41)],
                [x+sign*9.11,-(cad.P['keys']['pcb_z']-1.81)],
                [x+sign*7.69,-(cad.P['keys']['pcb_z']-1.81)]]])for sign in [1,-1]]
            # Correct the mirrored contour winding before combining it.
            rail_windows[1]=rail_windows[0].mirror((1,0)).translate((2*x,0))
            # Lower keys now begin at the recessed front plane (the bed); scan
            # from their first printed layer. Upper keys keep R12's start.
            start=y-9.4 if y else cad.front_plane()+.2
            for probe in np.arange(start,y+5.21,.2):
                actual_y=float(points[np.argmin(abs(points[:,1]-probe)),1]);assert abs(actual_y-probe)<.12
                sec=upright.slice(actual_y)^zone
                ids=np.flatnonzero(abs(points[:,1]-actual_y)<.01)
                xy=points[ids][:,[0,2]]*np.array([1,-1])
                beads=start_audit.bead_footprints(q,xy,widths[ids])^sec
                rail_areas=[(sec^window).area()for window in rail_windows]
                printed_rails=[(beads^window).area()for window in rail_windows]
                # Include the complete front anchor/ramp in the whole-path
                # scan. Full-depth individual rails start after that ramp.
                full_rails=actual_y>=y-6.8-.12
                if full_rails:
                    assert min(rail_areas)>=2.5 and min(printed_rails)>=1.6,('Individual key rail',i,actual_y,rail_areas,printed_rails)
                measurements.append({'assembly_y_mm':round(actual_y,4),'mesh_area_mm2':round(sec.area(),4),'printed_area_mm2':round(beads.area(),4),
                    'individual_full_depth_rail_screen_applies':full_rails,
                    'individual_rail_mesh_area_mm2':[round(v,4)for v in rail_areas],
                    'individual_rail_printed_area_mm2':[round(v,4)for v in printed_rails]})
            mesh_min=min(v['mesh_area_mm2']for v in measurements);printed_min=min(v['printed_area_mm2']for v in measurements)
            assert mesh_min>=8 and printed_min>=5,('Key load-path bottleneck',i,mesh_min,printed_min)
            load_paths[str(i)]={'sections':measurements,'minimum_mesh_area_mm2':mesh_min,'minimum_printed_area_mm2':printed_min,
                'previous_upper_key_mesh_bottleneck_mm2':2.76,'screen_threshold_mesh_mm2':8.,'screen_threshold_printed_mm2':5.,
                'decision':'Outboard fixed rails bypass the thin switch rims; screen against a narrow interlayer bottleneck, not a rated breaking force.',
                'physical_test':'Press each upper key while mounted and inspect the complete key-to-clip path for whitening, layer splits or excess bending.'}
        report['key_to_clip_load_paths']=load_paths
        for i in manifest.get('key_indices',range(5)):
            x,y=cad.key_positions()[i];local={}
            for dx,dy in [(0,5),(3,5),(3,7),(5,-.2)]:
                thickness,_,_=section(key,(x+dx,y+dy,4.8),(0,0,1))
                local[f'{dx},{dy}']=round(thickness,4)
            assert min(local.values())>1.15 and local['3,5']>1.35,(i,local)
            floors[str(i)]=local
        report['key_socket_floor_sampled_sections_mm']=floors
        report['key_floor_note']='Every key has rear and leading floor sections. The leading probe is 0.3 mm inside the nominal -0.5 mm face, avoiding an unprinted boundary sliver; all actual first layers and their backing are audited separately. The central rod cut is retained, not replaced with a uniform floor-thickness claim.'
    report['fixed_reinforcement']={'battery_crossbars_diameter_mm':2.,'battery_previous_crossbars_diameter_mm':1.4,
        'key_fixed_load_rail_width_mm':1.4,'key_fixed_load_rail_depth_mm':3.2,
        'key_load_path_scanned_local_y_mm':{'upper':[-9.4,5.2],'lower':[round(cad.front_plane()+.2,4),5.2]},
        'removed_lower_front_web':'The deep front web, round front rail and front legs ahead of the recessed plane were removed; the bumper, front ties and spine replace them. Their bending capacity is not a measured equivalent.',
        'battery_bridge_half_span_mm':12.8,'sensor_outer_rail_width_mm':2.,'sensor_previous_rail_width_mm':1.2,
        'sensor_fixed_root_diameter_mm':2.1,'sensor_previous_fixed_root_diameter_mm':1.6,
        'gate_central_grab_bar_depth_mm':2.7,'gate_previous_grab_bar_depth_mm':1.6,
        'gate_sliding_wedge_neck_width_mm':1.2,'gate_sliding_wedge_depth_mm':1.6,
        'note':'These are source dimensions with exported one-body/interface checks, not breaking-force predictions. Sliding wedge dimensions and spring profiles remain unchanged.'}
    z=cad.P['keys']['pcb_z'];floor=cad.P['battery']['floor_z']+cad.P['assembly']['battery_floor_raise_mm']
    roof=floor+cad.P['battery']['reserve_thickness']+cad.P['battery_cage']['roof_clearance']
    table={n:[]for n in manifest['parts']}
    positions=[cad.key_positions()[i]for i in manifest.get('key_indices',range(5))]
    def add(name,*args):
        if name not in rows or (manifest.get('coupon')and args[0]=='Four fixed joints between key rows'):return
        table[name].append(feature(read_solid(name),rows[name],*args))
    neck_screen=cad.P['finger_recess']['spine_neck_minimum_section_mm']
    def add_spine(spine,label,probes,*args):
        # Reviewer N16: keep the convenient probes, and also scan the complete
        # crown-to-root span, whose true neck is where the spine leaves its ring.
        if 'Key_Carrier' not in rows:return
        solid=read_solid('Key_Carrier');points=rows['Key_Carrier']
        row=feature(solid,points,label,probes,(0,0,1),neck_screen,*args)
        scan=spine_neck_scan(solid,points,row_widths['Key_Carrier'],spine,neck_screen)
        row['minimum_probe_section_mm']=row['minimum_sampled_section_mm'];row['minimum_probe_track_count']=row['minimum_sampled_track_count']
        row['minimum_sampled_section_mm']=min(row['minimum_sampled_section_mm'],scan['minimum_STL_section_mm'])
        row['minimum_sampled_track_count']=min(row['minimum_sampled_track_count'],scan['minimum_track_count'])
        row['neck_scan']=scan;table['Key_Carrier'].append(row)
    add('Key_Carrier','Switch-opening side rims',[(x+sign*7.625,y,z+cad.P['keys']['plate_bottom']+.6)for x,y in positions for sign in [-1,1]],(1,0,0),1.1,
        'Switch insertion loads the rim; fixed outboard rails bypass its thin section for the key-to-clip pressing load.',
        'Preserve the bought switch opening and scan the complete reinforced load path separately; the rim still needs a real insertion trial.',
        'Insert the actual switch, press normally and inspect whitening or layer separation on every tested seat.')
    add('Key_Carrier','All five socket floors including leading edges',[(x+dx,y+dy,4.8)for x,y in positions for dx,dy in [(0,5),(3,5),(3,7),(5,-.2)]],(0,0,1),1.15,
        'Socket insertion, removal and pressing load a locally thin floor.',
        'Keep the socket and rod clearance. Direct backing and a real socket trial are required.',
        'Remove helpers without levering the floor; insert and remove a real socket and press the key.')
    add('Key_Carrier','Outboard fixed key load rails',[(x+sign*8.4,y-4,z-.2)for x,y in positions for sign in [-1,1]],(0,0,1),3.,
        'Upper-key pressing and insertion transfer through the front-to-rear connection, across layer lines in this orientation.',
        'Add outboard fixed rails while preserving mounting lands and complete switch/socket routes; scan every intervening layer as well as these probes.',
        'Try the repaired coupon first, then repeatedly press both upper keys while mounted; stop on whitening, separation or excess bending.')
    lower=[(x,y)for x,y in positions if not y];fr=cad.P['finger_recess'];front=cad.front_plane()
    add('Key_Carrier','Recessed lower front bumper',[(x+dx,front+.5,9.6)for x,y in lower for dx in [-4,0,4]],(0,0,1),2.4,
        'An index finger rests against the lower edge; key pressing and handling bend the front strip ahead of each switch opening.',
        'Replace the protruding rail, deep webs and leg ends with one continuous bar behind the cap fronts; keep the flange lands and bought openings. Its 45-degree finger-relief chin recedes '+f"{fr['chin_back_y_mm']-front:.1f}"+' mm, with a lip below the switch housing behind it.',
        'Hold the wand normally with the index finger on the lower edge, press every lower key repeatedly and inspect the bumper for bending, whitening or layer splits.')
    if len(positions)==5:
        add_spine('rear','Rear clip to upper floor spine',[(-3.,15.,4.9),(2.5,15.,4.9),(-4.5,17.,4.85),(5.,16.6,4.85)],
            'Upper socket insertion and pressing load the floor fronts; the upper-left floor formerly began as a free tongue.',
            'Grow a tapered fixed spine from inside the rear clip crown to both upper floor fronts, above the rod and below every switch/socket route. Its crown seed rises to an arc just inside the fixed ring crown so the neck leaving the ring is not thinner than the screen; the whole span is scanned.',
            'Inspect the upper-left floor start during printing, then insert and remove both upper sockets and press both upper keys; inspect the spine/floor junction.')
    if any(x==0 for x,y in lower):
        # Probe both the chin-notched front of each tie and its full join behind the chin.
        add('Key_Carrier','Front clip ties to fixed rails',[(sign*6.2,yy,6.15)for sign in [-1,1]for yy in [front+.5,fr['chin_back_y_mm']+.6]],lambda c:(-4.1*np.sign(c[0]),0,4.8),2.4,
            'Rod loads from the front clip pass through two flat-fronted diagonals into the fixed rails and bumper.',
            'Start both diagonals on the bed with a 3.2 mm nominal section; keep the lower spring arms free.',
            'Slide the carrier on the rod, twist it gently by the outer keys and inspect both diagonal roots.')
        add_spine('front','Front clip to central floor spine',[(-3,-3,4.8),(3,-3,4.8),(0,-1.2,4.9)],
            'The central socket floor is joined directly to the front clip crown instead of only cantilevering from the rear.',
            f"Grow a tapered spine from inside the clip crown to the floor (half-width {fr['spine_half_width_mm']} mm) below the socket and switch routes. Its crown seed rises to an arc just inside the fixed ring crown so the neck leaving the ring is not thinner than the screen; the whole span is scanned.",
            'Insert and remove the centre socket, press the centre key and inspect the spine/floor junction.')
    add('Key_Carrier','Four fixed joints between key rows',[(sign*((cad.P['keys']['pitch']+cad.P['keys']['upper_half_spacing'])/2+dx),cad.P['keys']['row_spacing']/2,10.12)for sign in [-1,1]for dx in [-7.5,7.5]],(0,0,1),1.95,
        'Upper-key pressing bends the connectors and can peel layers across Y.',
        'Locally thicken the fixed joint from 1.2 to 2 mm below the new staggered seats; full-height trial required.',
        'Support the carrier as mounted and repeatedly press both upper keys; inspect the four joint roots.')
    add('Key_Carrier','Fixed rear socket posts',[(x+sign*7.9,y+9.6,7.)for x,y in positions for sign in [-1,1]],(1,0,0),1.85,
        'Socket insertion and key pressing load the rear columns.',
        'Retain the 1.9 mm rounded fixed columns; trim an obsolete 0.27 mm detached leading strip that the slicer omitted.',
        'Inspect the rear columns after cleanup and under repeated key pressing; bought-part routes must remain clear.')
    add('Key_Carrier','Fixed socket-side stops',[(x+8.525,y+6.,7.)for x,y in positions],(1,0,0),1.3,
        'Socket insertion and sideways handling load a narrow stop between the floor and mounting lip.',
        'Retain the 1.35 mm bought-interface stop. Its 4.47 mm clear printed bridge must be tested in the key coupon.',
        'Inspect the stop bridge and push the seated socket gently sideways; stop on cracking, whitening or looseness.')
    add('Battery_Holder','Reinforced roof crossbars',[(6,y,roof+1)for y in [-8,0,8]],(0,0,1),1.95,
        'Battery retention and accidental snags bend the cage hoops.',
        'Grow crossbars from 1.4 to 2 mm and connect longitudinal stringers; sag and retention remain unverified.',
        'Inspect all hoop/stringer joints and bridge sag, then gently load the real cell without pouch pressure.')
    add('Battery_Holder','Reinforced floor crossbars',[(6,y,floor-1)for y in [-15.8/3,15.8/3]],(0,0,1),1.95,
        'Cell weight and sliding insertion load the floor.',
        'Reinforce outside the battery reserve; the full cell-loading route remains clear.',
        'Slide the real cell in and out and inspect floor joints for cracking or whitening.')
    add('Battery_Holder','Outside gate-guide walls',[(sign*15,-16.3,floor+3)for sign in [-1,1]],(1,0,0),1.55,
        'Gate wedging can split thin outside walls across their printed layers.',
        'Grow the outside wall from 0.8 to 1.6 mm and add an outside diagonal; preserve the slot.',
        'Try the real gate gently; stop if it binds or whitens either guide. Never force it against the cell.')
    add('Battery_Holder','Outside guide diagonal braces',[(sign*14.5,-11.25,12.65)for sign in [-1,1]],lambda c:(-1.6*np.sign(c[0]),0,-1.4),1.5,
        'Guide bending transfers through a diagonal into the roof post.',
        'Add a 1.6 mm outside brace without entering the gate route; check the actual root and diagonal print.',
        'Inspect both diagonals for gaps or layer splits before trying the gate.')
    add('Battery_Holder','Centre roof stringer',[(0,4,roof+1)],(1,0,0),1.95,
        'Roof bars transmit retention loads through the longitudinal centre support.',
        'Join successive crossbars with a 2 mm stringer, reducing the unsupported crossbar span.',
        'Inspect every crossbar/stringer junction and the free end after helper removal.')
    add('Battery_End_Gate','Both sliding-wedge narrow ends',[(sign*13.4,-16.3,floor+6.9)for sign in [-1,1]],(1,0,0),1.15,
        'Gate insertion and removal flex its narrow sliding wedges.',
        'Preserve the wedge fit, print its broad face on the bed and use the reinforced centre as the handle.',
        'Cycle the gate without a cell first; inspect narrow ends and verify removal by the central bar.')
    add('Battery_End_Gate','Central grab bar',[(0,-16.3,floor+3)],(0,0,1),1.75,
        'Pulling at the centre distributes removal load instead of using a wedge as a handle.',
        'Increase the print depth from 1.6 to 2.7 mm outside the cell and sliding paths.',
        'Pull at the central bar, checking that both wedges release together without bowing or cracks.')
    add('XIAO_Rod_Holder','Fixed outside PCB rails',[(sign*10.2,10,8.4)for sign in [-1,1]],(1,0,0),1.95,
        'PCB insertion and USB lead snags load the rails and their roots.',
        'Grow the fixed rails outward from 1.2 to 2 mm and fixed roots from 1.6 to 2.1 mm; keep bearing faces.',
        'Check the actual populated PCB underside and insert without forcing; gently check lead strain.')
    add('XIAO_Rod_Holder','Fixed front diagonal root sections',[(sign*6.95,-1,5.735)for sign in [-1,1]],lambda c:(-4.47*np.sign(c[0]),0,6.5),2.,
        'PCB and USB loads pass through the intersecting diagonals into the clip crown.',
        'Thicken fixed ribs to 2.1 mm nominal diameter; intersecting roots are wider than the individual rib.',
        'Inspect root bonding and check the complete holder under gentle board/lead handling.')
    add('XIAO_Rod_Holder','Axial rails beside the rod',[(sign*4.8,10,0)for sign in [-1,1]],(1,0,0),1.95,
        'Rod sliding and lateral handling bend the thin rails between the clips.',
        'Thicken the fixed middle rail from 1.25 to 2 mm, stopping before the free clip arms; retain the bore and spring profile.',
        'Print the full-height sensor holder and slide onto the rod from its end; inspect rails and clip roots.')
    report['per_part_weak_point_decisions']=table
    report['full_set_physically_ready']=False
    report['qualification']='Geometric and extrusion-section screening only. Physical trial is required for every listed load case; no guaranteed breaking force or fatigue life.'
    report['passed']=True
    (OUT/'strength-checks.json').write_text(json.dumps(report,indent=2)+'\n');print('Exported clip sections, two-or-more actual radial tracks and key socket floor passed.')
if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--exports',type=Path,default=OUT);a=p.parse_args();audit(a.exports.resolve())
