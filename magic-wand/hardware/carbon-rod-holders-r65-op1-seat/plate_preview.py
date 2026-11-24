"""Embed plate and object-picking images from the editable 3MF's own triangles.

Bambu Studio's headless macOS export can reuse these images without starting
a graphical session. The native slicer still generates the G-code and metadata.
"""
from hashlib import sha256
from io import BytesIO
import json
from xml.etree import ElementTree as ET
from zipfile import ZIP_DEFLATED, ZipFile

import numpy as np
from PIL import Image, ImageDraw


def previews(files):
    scene = ET.fromstring(files['3D/3dmodel.model'])
    objects = {o.get('id'): o for o in scene.findall('.//{*}resources/{*}object')}
    cfg = ET.fromstring(files['Metadata/model_settings.config'])
    printable = {(o.get('id'),p.get('id')) for o in cfg.findall('object')
                 for p in o.findall('part') if p.get('subtype') == 'normal_part'}
    triangles, ids = [], []
    for item in scene.findall('.//{*}build/{*}item'):
        owner = item.get('objectid')
        transform = np.asarray([float(n) for n in item.get('transform').split()]).reshape(4,3)
        for part in objects[owner].findall('{*}components/{*}component'):
            if (owner,part.get('objectid')) not in printable:
                continue
            mesh = objects[part.get('objectid')].find('{*}mesh')
            vertices = np.asarray([[float(v.get(n)) for n in 'xyz'] for v in mesh.find('{*}vertices')])
            faces = np.asarray([[int(f.get(n)) for n in ('v1','v2','v3')] for f in mesh.find('{*}triangles')])
            triangles.append((vertices @ transform[:3] + transform[3])[faces])
            ids.extend([int(owner)]*len(faces))
    vertices = np.concatenate(triangles)
    ids = np.asarray(ids)
    settings = json.loads(files['Metadata/project_settings.config'])
    color = bytes.fromhex(settings['filament_colour'][0].lstrip('#')[:6])
    rgb = np.asarray(list(color))
    normal = np.cross(vertices[:,1]-vertices[:,0],vertices[:,2]-vertices[:,0])
    normal /= np.maximum(np.linalg.norm(normal,axis=1,keepdims=True),1e-12)
    light = np.maximum(0, normal @ np.array([-.36,-.48,.80]))
    shades = (.53+.44*light[:,None])*rgb
    iso = Image.new('RGBA',(512,512))
    plain, top, pick = (Image.new('RGBA',iso.size) for _ in range(3))

    def paint(images, x, y, depth, top_view=False):
        polygons = np.rint(np.stack((x,y),axis=-1)).astype(int).reshape(-1,6).tolist()
        artists = [ImageDraw.Draw(image) for image in images]
        for i in np.argsort(depth.mean(axis=1),kind='stable'):
            shape = polygons[i]
            shade = tuple(shades[i].astype(int))+(255,)
            owner = int(ids[i])
            flat = (owner & 255, (owner>>8)&255, (owner>>16)&255, 255) if top_view else (*color,255)
            artists[0].polygon(shape, fill=shade)
            artists[1].polygon(shape, fill=flat)

    x,y,z = vertices.transpose(2,0,1)
    paint((top,pick), x*512/180, (180-y)*512/180,z,True)
    # Orthographic view from the front right. Fit the actual bounds.
    horizontal = .82*x+.57*y
    vertical = -.37*x+.53*y+.76*z
    scale = min(452/np.ptp(horizontal),452/np.ptp(vertical))
    project = lambda a: (a-(a.max()+a.min())/2)*scale
    paint((iso,plain), 256+project(horizontal), 256-project(vertical),.43*x-.62*y+.65*z)
    return {'thumbnail_file': ('plate_1',iso), 'thumbnail_no_light_file': ('plate_no_light_1',plain),
            'top_file': ('top_1',top), 'pick_file': ('pick_1',pick)}


def embed(layout):
    with ZipFile(layout) as source:
        files = {key:source.read(key) for key in source.namelist()}
    settings = 'Metadata/model_settings.config'
    cfg = ET.fromstring(files[settings])
    plate = cfg.find('plate')
    for key,(name,image) in previews(files).items():
        path = 'Metadata/'+name+'.png'
        buf = BytesIO()
        image.save(buf,format='PNG')
        files[path] = buf.getvalue()
        ET.SubElement(plate,'metadata',key=key,value=path)
    files[settings] = ET.tostring(cfg,encoding='utf-8',xml_declaration=True)
    staged = layout.with_suffix('.new.3mf')
    with ZipFile(staged,'w',ZIP_DEFLATED) as dest:
        for key,value in files.items():
            dest.writestr(key,value)
    staged.replace(layout)
    frame = layout.with_suffix('.frame.json')
    data = json.loads(frame.read_text())
    data['layout_sha256'] = sha256(layout.read_bytes()).hexdigest()
    frame.write_text(json.dumps(data,indent=2)+'\n')
