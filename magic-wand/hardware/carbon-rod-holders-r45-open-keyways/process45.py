"""Apply a native bridge direction to the editable carrier project only."""
import json
from xml.etree import ElementTree as E
from zipfile import ZipFile,ZIP_DEFLATED
def bridge_angle(source,target,angle,infill_first=False):
    with ZipFile(source) as z:files={n:z.read(n) for n in z.namelist()}
    config='Metadata/project_settings.config';settings='Metadata/model_settings.config'
    values=json.loads(files[config]);values['bridge_angle']=str(angle);values['is_infill_first']=str(int(infill_first))
    xml=E.fromstring(files[settings])
    for obj in xml.findall('object'):
        name=obj.find("metadata[@key='name']").get('value')
        m=obj.find("metadata[@key='bridge_angle']")
        if m is None:m=E.SubElement(obj,'metadata',key='bridge_angle')
        m.set('value',str(angle) if name=='Key_Carrier' else '0')
        seq=obj.find("metadata[@key='is_infill_first']")
        if seq is None:seq=E.SubElement(obj,'metadata',key='is_infill_first')
        seq.set('value',str(int(infill_first and name=='Key_Carrier')))
    files[config]=json.dumps(values,indent=2).encode();files[settings]=E.tostring(xml,encoding='utf-8',xml_declaration=True)
    with ZipFile(target,'w',ZIP_DEFLATED) as z:
        for n,d in files.items():z.writestr(n,d)
