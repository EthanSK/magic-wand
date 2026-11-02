#!/usr/bin/env python3
"""Render scientific diagrams from results.json; no CAD or hardware is touched.

Run after mechanics-study.mjs. Pillow draws the explanatory layout;
Matplotlib draws the scientific Pareto plot with the Agg backend.
"""
from pathlib import Path
import hashlib
import json
import PIL
from PIL import Image, ImageDraw, ImageFont

HERE = Path(__file__).resolve().parent
data = json.loads((HERE / 'results.json').read_text())
font_root = Path('/System/Library/Fonts/Supplemental')
def font(size, bold=False):
    return ImageFont.truetype(str(font_root / ('Arial Bold.ttf' if bold else 'Arial.ttf')), size)

W, H = 1700, 1040
img = Image.new('RGB', (W,H), '#f8fafc')
d = ImageDraw.Draw(img)
ink, muted, blue, orange = '#0f172a', '#475569', '#0369a1', '#c2410c'
def text(x,y,s,size=27,color=ink,bold=False):
    d.text((x,y),s,font=font(size,bold),fill=color)
def arrow(a,b,color=ink,width=4):
    import math
    d.line([a,b],fill=color,width=width)
    theta=math.atan2(b[1]-a[1],b[0]-a[0]); length=14
    d.polygon([b,(b[0]-length*math.cos(theta-.5),b[1]-length*math.sin(theta-.5)),
               (b[0]-length*math.cos(theta+.5),b[1]-length*math.sin(theta+.5))],fill=color)

text(70,40,'Legacy illustrative model: not the chosen prototype',43,bold=True)
text(70,104,'Masses and rotation axis are hypotheses. The actual hand pivot is unmeasured.',27,muted)
s=data['inputs']['scenario']; baseline=data['baseline']
x0,x1,y=100,1570,300
scale=(x1-x0)/baseline['length_mm']
xp=x0+baseline['pivot_mm']*scale
xc=x0+baseline['centre_from_butt_mm']*scale
d.line([(x0,y),(x1,y)],fill='#334155',width=15)
d.ellipse((x0-8,y-8,x0+8,y+8),fill=ink)
d.rounded_rectangle((xp-68,y-42,xp+68,y+42),radius=18,fill='#e2e8f0',outline=ink,width=3)
d.rounded_rectangle((x1-35,y-36,x1+35,y+36),radius=8,fill='#bae6fd',outline=blue,width=3)
d.line([(xc,y-70),(xc,y+72)],fill=orange,width=3)
text(xc-75,y-112,'Whole-model COM',23,orange,bold=True)
text(xc-36,y+80,f"{baseline['centre_from_butt_mm']/10:.1f} cm",23,orange)
text(x0-5,y+42,'Butt: y = 0',23)
text(xp-105,y+42,f"Assumed axis: {baseline['pivot_mm']/10:g} cm",24,bold=True)
text(x1-166,y+42,f"Tip: L = {baseline['length_mm']/10:g} cm",25,blue,bold=True)
arrow((x0,190),(x1,190)); arrow((x1,190),(x0,190))
text(700,151,'Tube length L',25,bold=True)
text(xp-90,y-104,f"{s['near_grip_package_g']:g} g at grip",24)
text(x1-124,y-94,f"{s['tip_package_g']:g} g tip package",24,blue)
arrow((x0+baseline['length_mm']/2*scale,y+10),(x0+baseline['length_mm']/2*scale,y+115),muted)
arrow((x1,y+10),(x1,y+115),blue)
text(690,432,'Gravity acts downward here: horizontal wand, torque about the grip.',25,muted)
text(70,487,'Wrist position and hand dynamics are not known. Grip torque is not measured wrist strain.',26,orange,bold=True)
d.line([(70,546),(1630,546)],fill='#cbd5e1',width=2)
text(70,565,'Same packages, shorter tube',32,bold=True)
text(70,660,'Total mass',24,muted)
text(70,725,'Moment at assumed axis',24,muted)
text(70,790,'Wand inertia',24,muted)
colors=['#0f172a','#0369a1','#047857','#a16207','#9f1239']
rows=data['same_packages']
for i,(r,color) in enumerate(zip(rows,colors)):
    xx=445+i*236
    text(xx,615,f"{r['length_mm']/10:g} cm",29,color,bold=True)
    text(xx,660,f"{r['total_g']:.2f} g",27,color)
    text(xx,725,f"{r['torque_N_m']:.5f} Nm",25,color)
    text(xx,790,f"{100*r['inertia_fraction']:.1f}%",28,color,bold=True)
comparison=next(r for r in rows if r['length_mm']==350)
saved_mass=baseline['total_g']-comparison['total_g']
moment_percent=100*comparison['torque_N_m']/baseline['torque_N_m']
lost_inertia=100*(1-comparison['inertia_fraction'])
text(70,842,f"Shortening {baseline['length_mm']/10:g} -> 35 cm saves {saved_mass:.2f} g; grip moment becomes {moment_percent:.1f}% of baseline,",29,bold=True)
text(70,884,f"and wand inertia falls by {lost_inertia:.1f}%. That does not measure a change in wobble.",29,bold=True)
text(70,961,f"Inputs: {data['inputs']['outer_mm']:g}/{data['inputs']['inner_mm']:g} mm tube; density {s['density_g_cm3']:g} g/cm3; p = {s['grip_from_butt_mm']/10:g} cm; tip = {s['tip_package_g']:g} g; near-grip = {s['near_grip_package_g']:g} g.",24,muted)
img.save(HERE/'geometry-and-comparison.png')

# Matplotlib owns the scientific Pareto plot; Pillow above only draws the
# explanatory layout. No data or dominance decisions are recomputed here.
import matplotlib
matplotlib.use('Agg')
from matplotlib import pyplot as plt
from matplotlib import font_manager
from matplotlib.lines import Line2D
for filename in ['Arial.ttf', 'Arial Bold.ttf']:
    font_manager.fontManager.addfont(str(font_root/filename))
plt.rcParams.update({'font.family': 'Arial', 'font.size': 15,
                     'axes.edgecolor': ink, 'axes.labelcolor': ink,
                     'xtick.color': muted, 'ytick.color': muted,
                     'text.color': ink})
fig=plt.figure(figsize=(17,11.1),dpi=100,facecolor='#f8fafc')
ax=fig.add_axes([.105,.19,.60,.61],facecolor='#f8fafc')
fig.text(.045,.947,'Legacy mechanical trade-offs, not an optimal length',fontsize=27,weight='bold')
fig.text(.045,.902,f"Normalised to the assumed {baseline['length_mm']/10:g} cm model; axes and package masses are hypotheses.",fontsize=16,color=muted)
def percentages(records):
    return ([100*r['inertia_kg_m2']/baseline['inertia_kg_m2'] for r in records],
            [100*abs(r['torque_N_m'])/baseline['torque_N_m'] for r in records])
ax.scatter(*percentages(data['illustrative_candidates']),s=38,c='#cbd5e1',zorder=2)
ax.scatter(*percentages(data['finite_candidate_frontier']),s=38,c='#248b94',zorder=3)
line=list(reversed(rows))
ax.plot(*percentages(line),color=blue,linewidth=2.6,marker='o',markersize=10,
        markeredgecolor='white',markeredgewidth=1.2,zorder=4)
for r in rows:
    xx,yy=percentages([r])
    offset=(-60,12) if r['length_mm']==350 else (10,-3)
    ax.annotate(f"{r['length_mm']/10:g} cm",(xx[0],yy[0]),xytext=offset,
                textcoords='offset points',fontsize=16,color=blue,weight='bold')
ax.set(xlim=(0,135),ylim=(0,108),xticks=[0,25,50,75,100,125],yticks=[0,25,50,75,100],
       xlabel='Wand inertia retained (%)',ylabel='Absolute gravity moment retained (%)')
ax.xaxis.labelpad=15
ax.yaxis.labelpad=15
ax.spines[['top','right']].set_visible(False)
ax.spines[['bottom','left']].set_linewidth(1.5)
ax.tick_params(length=5,pad=8)
ax.grid(color='#dbe3ee',linewidth=1)
ax.set_axisbelow(True)
handles=[Line2D([],[],color=blue,marker='o',linewidth=2.6,label='Same packages;\nshorter tube'),
         Line2D([],[],color='#248b94',marker='o',linestyle='none',label='Non-dominated layouts\nin this sampled model'),
         Line2D([],[],color='#cbd5e1',marker='o',linestyle='none',label='Other sampled layouts')]
ax.legend(handles=handles,loc='upper left',bbox_to_anchor=(1.035,1),frameon=False,
          fontsize=14,labelspacing=1.7,handlelength=2)
fig.text(.755,.44,'Dominance also includes\nmass and length.\n\nInertia is a declared\nmechanical proxy,\nnot measured steadiness.',fontsize=15,linespacing=1.45)
fig.text(.07,.082,'Lower gravity moment means less static torque. Higher inertia can resist torque disturbances,',fontsize=15,color=muted)
fig.text(.07,.047,'but also takes more effort to turn. Inertia is not damping or a measured steadiness score.',fontsize=15,color=muted)
fig.savefig(HERE/'mechanical-pareto.png',dpi=100,facecolor=fig.get_facecolor())
plt.close(fig)

# The read-only report check rejects figures made from older data or code.
# Font and Pillow metadata explain any cross-platform pixel differences.
def sha(name):
    return hashlib.sha256((HERE/name).read_bytes()).hexdigest()
receipt = {
    'inputs': {name: sha(name) for name in ['results.json', 'render-study.py', 'renderer-requirements.txt']},
    'outputs': {name: sha(name) for name in ['geometry-and-comparison.png', 'mechanical-pareto.png']},
    'renderer': {'pillow': PIL.__version__, 'matplotlib': matplotlib.__version__,
                 'plot_backend': matplotlib.get_backend(), 'font': 'Arial',
                 'font_sha256': {name: hashlib.sha256((font_root/name).read_bytes()).hexdigest()
                                 for name in ['Arial.ttf', 'Arial Bold.ttf']}}
}
(HERE/'figures-provenance.json').write_text(json.dumps(receipt, indent=2)+'\n')
