"""Measure native positive-extrusion bridge G1 lines in the four key banks."""
import re,json,math
from zipfile import ZipFile
def moves(archive):
    with ZipFile(archive) as z:g=z.read('Metadata/plate_1.gcode').decode()
    top=0.;feature='';owner=None;x=y=0.;rows=[]
    for line in g.splitlines():
        if line.startswith('; Z_HEIGHT:'):top=float(line.split(':')[1])
        elif line.startswith('; FEATURE:'):feature=line.split(':',1)[1].strip()
        elif line.startswith('; start printing object, unique label id:'):owner=int(line.rsplit(':',1)[1])
        elif line.startswith('; stop printing object,'):owner=None
        elif line.startswith(('G1 ','G0 ','G2 ','G3 ')):
            d={k:float(v) for k,v in re.findall(r'\b([XYE])(-?[\d.]+)',line)}
            nx=d.get('X',x);ny=d.get('Y',y)
            if feature=='Bridge' and owner==2 and line.startswith('G1 ') and d.get('E',0)>0:
                length=math.hypot(nx-x,ny-y)
                if length>1:
                    rows.append(dict(top=top,length_mm=round(length,3),xy_delta=[round(nx-x,3),round(ny-y,3)],start_xy=[x,y],end_xy=[nx,ny]))
            x,y=nx,ny
    slots=[r for r in rows if 10.5<r['top']<12.3 and (r['start_xy'][0]<68 or r['start_xy'][0]>92)]
    tall=[r for r in slots if abs(r['xy_delta'][0])>12]
    return dict(key_pocket_lines_longer_than_12mm_across_x=len(tall),max_key_line_mm=max((r['length_mm'] for r in slots),default=0),
        example_longest_key_lines=sorted(slots,key=lambda r:-r['length_mm'])[:4],all_bridge_lines_longer_than_12mm=sum(r['length_mm']>12 for r in rows))
if __name__=='__main__':
    import sys
    for path in sys.argv[1:]:print(path,json.dumps(moves(path)))
