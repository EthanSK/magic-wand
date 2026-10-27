#!/usr/bin/env python3
"""Sample real straight/arc extrusions through functional clearances.

Uses the established V18 check's 0.5 mm centreline sampling and measured P1S
extruder offset. Open lattice gaps may contain removable external supports;
this gate checks the wire/battery/button/cam/loop airflow routes, not strength.
"""
from pathlib import Path
import argparse, collections, importlib.util, json, math, zipfile
import numpy as np
HERE=Path(__file__).resolve().parent;ROOT=HERE.parents[3]
sp=importlib.util.spec_from_file_location('study',HERE/'wand_cad.py');s=importlib.util.module_from_spec(sp);sp.loader.exec_module(s)

def samples(project):
    with zipfile.ZipFile(project) as z:code=z.read('Metadata/plate_1.gcode').decode()
    points=[];kinds=[];position=np.zeros(3);relative=True;last_e=0.;feature=''
    for line in code.splitlines():
        if line.startswith('; FEATURE:'):feature=line[11:].strip();continue
        t=line.split(';')[0].split()
        if not t:continue
        if t[0]=='M83':relative=True
        if t[0]=='M82':relative=False
        if t[0]=='G92':
            for v in t[1:]:
                if v.startswith('E'):last_e=float(v[1:])
            continue
        if t[0] not in ('G0','G1','G2','G3'):continue
        v={p[0]:float(p[1:]) for p in t[1:] if len(p)>1 and p[0] in 'XYZEIJ'}
        nxt=np.array([v.get(k,position[i]) for i,k in enumerate('XYZ')]);de=v.get('E',0.) if relative else v.get('E',last_e)-last_e
        if not relative:last_e=v.get('E',last_e)
        if de>0 and feature not in ('','Custom'):
            if t[0] in ('G2','G3') and ('I' in v or 'J' in v):
                center=position[:2]+[v.get('I',0.),v.get('J',0.)];r=np.linalg.norm(position[:2]-center)
                a=math.atan2(position[1]-center[1],position[0]-center[0]);b=math.atan2(nxt[1]-center[1],nxt[0]-center[0]);da=(b-a)%(2*math.pi)
                if t[0]=='G2':da=-((a-b)%(2*math.pi))
                f=np.linspace(0,1,max(2,int(math.ceil(abs(da)*r/.5))));aa=a+da*f
                p=np.c_[center[0]+r*np.cos(aa),center[1]+r*np.sin(aa),position[2]+(nxt[2]-position[2])*f]
            elif np.linalg.norm(nxt-position)>.001:
                p=position+(nxt-position)*np.linspace(0,1,max(2,int(math.ceil(np.linalg.norm(nxt-position)/.5))))[:,None]
            else:p=np.empty((0,3))
            points.append(p);kinds.extend([feature]*len(p))
        position=nxt
    return np.concatenate(points),np.asarray(kinds)

def inspect(key,manifest,project):
    c=s.configure(key);A,F=samples(project);records={p['name']:p for p in manifest['variants'][key]['parts']+manifest['shared_parts']};checks={}
    layout=json.loads((HERE/'exports/projects.json').read_text())[key]['complete'];external_support_bases={}
    for name,center in zip(layout['part_names'],layout['positions']):
        if name not in ('Handle_Left','Handle_Right','Lower_Shaft','Upper_Shaft','Removable_Finger_Loop','Sense_Open_Cradle'):continue
        transform=np.asarray(records[name]['print_to_assembly']);p=A+[0.,2.,0.]-[*center,0.];xyz=p@transform[:3,:3].T+transform[:3,3];x,y,z=xyz.T
        z0,z1=(61.,173.5) if name.startswith('Handle_') else (160.5,259.5) if name=='Lower_Shaft' else (246.5,365.5) if name=='Upper_Shaft' else (0.,0.)
        areas={'wire_bore_9mm':(x*x+y*y<4.5**2)&(z>z0)&(z<z1)}
        if name.startswith('Handle_'):
            areas['battery']=(abs(x)<9.3)&(abs(y)<3.5)&(z>15)&(z<58)
            for i,zz in enumerate(c.LOOP_MOUNTS):
                r=c.loop_mount_radius(zz)
                for angle in [0.,3.,6.,9.,12.]:
                    a=math.radians(angle);xl=x*math.cos(a)-y*math.sin(a);yl=x*math.sin(a)+y*math.cos(a);dz=-c.LOOP_CAM_RISE*angle/c.LOOP_TWIST
                    areas[f'cam_{i}_{angle}']=(xl*xl+(z-zz-dz)**2<2.3**2)&(yl>-r+2.85)&(yl<-r+4.15)
                    areas[f'shoulder_{i}_{angle}']=(abs(xl)<3.5)&(abs(z-zz-dz)<3.)&(yl>-r+.25)&(yl<-r+1.)
            for button,angle,zz in c.HAND_BUTTONS:
                if name.endswith('Right'):angle=-angle
                a=math.radians(angle);t=x*math.cos(a)-y*math.sin(a);r=x*math.sin(a)+y*math.cos(a)
                areas[button+'_wire']=(t*t+(z-zz)**2<3**2)&(r>0)&(r<18)
                areas[button+'_socket']=(t>-8.1)&(t<-1.5)&(zz-z>-7.6)&(zz-z<2.2)&(r>c.BUTTON_ORIGIN-4.2)&(r<c.BUTTON_ORIGIN-2.8)
                areas[button+'_clip']=(abs(t)>7.5)&(abs(t)<8.1)&(zz-z>4.5)&(zz-z<7.5)&(r>c.BUTTON_ORIGIN-1.5)&(r<c.BUTTON_ORIGIN-.9)
        if name=='Sense_Open_Cradle':
            areas={'head_wire_9mm':(x*x+y*y<4.5**2)&(z>352.5)&(z<374.8),'forward_wire':(x*x+(y-2.)**2<2.7**2)&(z>375)&(z<387.5),'board':(abs(x)<8.6)&(y>c.BOARD_Y+.3)&(y<c.BOARD_Y+c.BOARD_T-.3)&(z>c.BOARD0+.3)&(z<c.BOARD0+20.7),'solder':(abs(x)<5.1)&(y>c.BOARD_Y-5.5)&(y<c.BOARD_Y-.4)&(z>c.BOARD0+3.5)&(z<c.BOARD0+17.5),'usb':(abs(x)<5.7)&(y>c.BOARD_Y-.8)&(y<c.BOARD_Y+4.8)&(z>c.BOARD0+21.3)&(z<411.)}
        if name=='Sense_Open_Cradle':
            # The exposed back permits removable support feet on the build
            # plate below the soldered-board space. These are not supports
            # trapped inside a hole: require support-only first-layer paths,
            # at least 0.5 mm outside the actual local back of the holder.
            candidate=areas['solder']&np.isin(F,['Support','Support transition','Support interface'])&(p[:,2]<=.4)
            external=np.zeros(len(A),bool);head=s.open_head(c)
            for zz in np.unique(np.round(z[candidate],5)):
                section=head.slice(float(zz))
                if not section.is_empty():
                    back=section.bounds()[1]
                    external|=candidate&(abs(z-zz)<.00001)&(y<back-.5)
            external_support_bases[name]=dict(collections.Counter(F[external]))
            areas['solder']&=~external
        if name=='Removable_Finger_Loop':
            for i,port in enumerate(c.loop_air_ports()):
                delta=xyz-np.asarray(port['center']);n=np.asarray(port['inward']);axial=delta@n;cross=delta-axial[:,None]*n;t=delta@np.asarray(port['tangent'])
                areas[f'contact_airflow_{i}']=(np.sum(cross*cross,axis=1)<.8**2)&(abs(axial)<8.)
                areas[f'broad_face_{i}']=((t/6.5)**2+(axial/1.5)**2<1)&(abs(x)<c.LOOP_WIDTH/2+.3)
        checks[name]={label:dict(collections.Counter(F[mask])) for label,mask in areas.items()}
    assert all(not hits for part in checks.values() for hits in part.values()),(key,checks)
    return {'project_sha256':s.sha(project),'sample_step_mm':.5,'extruder_offset_mm':[0,2],'path_samples':len(A),'clearance_extrusion_samples':checks,'removable_support_bases_outside_open_back':external_support_bases}

def main(out):
    manifest=json.loads((HERE/'exports/manifest.json').read_text());report={}
    for key in manifest['variants']:
        report[key]=inspect(key,manifest,ROOT/'magic-wand-3d-models'/f'Print-Lattice-{key}-complete.3mf');print(key+' sliced functional clearances passed',flush=True)
    out.write_text(json.dumps(report,indent=2)+'\n')
if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--out',type=Path,required=True);main(p.parse_args().out)
