"""Give disposable cradle ribs their own actual G-code object ID.

Bambu's object ownership comments let us distinguish helper from printed
carrier even when both use normal PETG walls. Both remain on the same plate.
"""
from copy import deepcopy
from pathlib import Path
from xml.etree import ElementTree as E
from zipfile import ZipFile, ZIP_DEFLATED
import hashlib,json
NS='http://schemas.microsoft.com/3dmanufacturing/core/2015/02'
E.register_namespace('',NS)
def layout_owners(directory):
    """Use the selected editable layout as the independent owner list."""
    with ZipFile(directory/'R45-Key-Carrier-layout.3mf') as archive:
        settings=E.fromstring(archive.read('Metadata/model_settings.config'))
    names={obj.find("metadata[@key='name']").get('value') for obj in settings.findall('object')}
    basic={'Key_Carrier','External_cradle','Release_tabs'}
    assert names in (basic,basic|{'Front_pull_shelf'},basic|{'Front_pull_shelf','Rear_pull_shelf'})
    return names

def split_owner(path):
    with ZipFile(path) as z:files={n:z.read(n) for n in z.namelist()}
    model=E.fromstring(files['3D/3dmodel.model']);settings=E.fromstring(files['Metadata/model_settings.config'])
    resources=model.find('./{*}resources');parent=resources.find('./{*}object[@id="2"]/{*}components')
    ref=parent.find('./{*}component[@objectid="400"]')
    if ref is None:return
    build=model.find('./{*}build');carrier=settings.find("object[@id='2']")
    plate=settings.find('plate')
    for number,identifier,name in [('400','401','External_cradle'),('402','403','Release_tabs'),('410','411','Front_pull_shelf'),('412','413','Rear_pull_shelf')]:
        ref=parent.find(f'./{{*}}component[@objectid="{number}"]')
        if ref is None:continue
        parent.remove(ref)
        group=E.SubElement(resources,'{'+NS+'}object',id=identifier,type='model',name=name)
        E.SubElement(group,'{'+NS+'}components').append(ref)
        item=deepcopy(build[0]);item.set('objectid',identifier);build.append(item)
        pm=carrier.find(f"part[@id='{number}']");carrier.remove(pm)
        helper=E.SubElement(settings,'object',id=identifier)
        for key,val in {'name':name,'extruder':'1','enable_support':'0','brim_type':'no_brim','wall_loops':'1','sparse_infill_density':'12%','top_shell_layers':'2','bottom_shell_layers':'2','top_shell_thickness':'0','bottom_shell_thickness':'0'}.items():
            E.SubElement(helper,'metadata',key=key,value=val)
        pm.find("metadata[@key='name']").set('value',name);helper.append(pm)
        instance=deepcopy(plate.find('model_instance'))
        for key in ('object_id','identify_id'):instance.find(f"metadata[@key='{key}']").set('value',identifier)
        plate.append(instance)
    for name,root in [('3D/3dmodel.model',model),('Metadata/model_settings.config',settings)]:
        files[name]=E.tostring(root,encoding='utf-8',xml_declaration=True)
    with ZipFile(path,'w',ZIP_DEFLATED) as z:
        for name,data in files.items():z.writestr(name,data)
    frame=path.parent/'frame.json';f=json.loads(frame.read_text())
    f['layout_sha256']=hashlib.sha256(path.read_bytes()).hexdigest();frame.write_text(json.dumps(f,indent=2)+'\n')
if __name__=='__main__':
    import sys
    split_owner(Path(sys.argv[1]))
