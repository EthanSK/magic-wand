"""Map each sampled bead to its actual G-code line, travel-separated sequence and feed."""
import math
import numpy as np

def map_moves(q,gcode,total,step=.15):
    pos=np.zeros(3);last_e=0.;relative_e=True;relative_xyz=False;feature=''
    feed=0.;fan=0.;boundary=True;sequence=-1;cursor=0;lines=[];seq=[];feeds=[];fans=[];counts=[]
    for number,text in enumerate(gcode.splitlines(),1):
        if text.startswith('; FEATURE:'):feature=text[11:].strip();continue
        if text.startswith(('; start printing object,','; stop printing object,')):boundary=True;continue
        fields=text.split(';',1)[0].split()
        if not fields:continue
        cmd=fields[0]
        if cmd in ('M82','M83'):relative_e=cmd=='M83';continue
        if cmd in ('G90','G91'):relative_xyz=cmd=='G91';continue
        if cmd=='M107':fan=0.;continue
        if cmd=='M106':
            vals={s[0]:float(s[1:]) for s in fields[1:] if s[0] in 'PS' and len(s)>1}
            if vals.get('P',1)==1:fan=vals.get('S',255)
            continue
        if cmd not in ('G0','G1','G2','G3','G92'):continue
        d={s[0]:float(s[1:]) for s in fields[1:] if len(s)>1 and s[0] in 'XYZEIJRF'}
        feed=d.get('F',feed)
        if cmd=='G92':
            last_e=d.get('E',last_e)
            for i,c in enumerate('XYZ'):
                if c in d:pos[i]=d[c]
            continue
        end=pos+np.array([d.get(c,0.) for c in 'XYZ']) if relative_xyz else np.array([d.get(c,pos[i]) for i,c in enumerate('XYZ')])
        extruded=d.get('E',0.) if relative_e else d.get('E',last_e)-last_e
        if not relative_e:last_e=d.get('E',last_e)
        distance=float(np.linalg.norm(end-pos))
        if extruded>0 and feature not in ('','Custom','Flush') and (distance>=1e-7 or cmd in ('G2','G3')):
            if cmd in ('G2','G3'):
                _,r,_,sweep=q._arc(pos,end,d,cmd=='G2');distance=math.hypot(abs(sweep)*r,end[2]-pos[2])
            n=max(2,int(math.ceil(distance/step))+1)
            if boundary:sequence+=1
            boundary=False;lines.append(number);seq.append(sequence);feeds.append(feed/60.);fans.append(fan/255.);counts.append(n);cursor+=n
        elif distance>=1.e-7 or extruded<0:boundary=True
        pos=end
    assert cursor==total,('raw native line/sample mismatch',cursor,total)
    return tuple(np.repeat(np.asarray(rows,dtype=kind),counts) for rows,kind in
                 ((lines,np.int32),(seq,np.int32),(feeds,np.float32),(fans,np.float32)))
