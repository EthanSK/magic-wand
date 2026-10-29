#!/usr/bin/env python3
"""Reproducible shaded drawings from the delivered CAD triangles."""
from pathlib import Path
import argparse,importlib.util,json
from PIL import Image,ImageDraw
HERE=Path(__file__).resolve().parent
s=importlib.util.spec_from_file_location('rod_draw',HERE.parent/'thin-rod-study/render_models.py');r=importlib.util.module_from_spec(s);s.loader.exec_module(r)
def build(exports,out):
 m=json.loads((exports/'manifest.json').read_text());im=Image.new('RGB',(1300,1100),(242,246,248));d=ImageDraw.Draw(im)
 d.text((48,30),'Long solid wand',font=r.font(40),fill=(27,45,56));d.text((48,85),'500 mm long · 8 to 5.8 mm tapered body · Wires outside',font=r.font(24),fill=(55,75,86))
 r.draw_model(im,m['parts'],(300,600),1.65,250.,(38,158,185));d.text((110,140),'Full assembly',font=r.font(28),fill=(27,45,56))
 r.draw_model(im,m['parts'][-1:],(920,610),9.,470.,(38,158,185),clip=(434.,501.));d.text((695,140),'Integral gyro frame',font=r.font(28),fill=(27,45,56))
 d.rectangle((0,1030,1300,1100),fill=(242,246,248));d.text((48,1040),'Unprinted prototype. Physical fit and strength remain untested.',font=r.font(23),fill=(124,78,39));im.save(out)
if __name__=='__main__':
 a=argparse.ArgumentParser();a.add_argument('--exports',type=Path,default=HERE/'exports');a.add_argument('--out',type=Path,default=HERE/'preview/model.png');v=a.parse_args();build(v.exports,v.out)
