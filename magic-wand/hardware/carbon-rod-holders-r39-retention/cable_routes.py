"""Regenerate the twelve separate entry routes; run in the CAD runtime."""
import heapq, math, json
from pathlib import Path
import holder39 as d
import numpy as np
from shapely.geometry import Point, Polygon
from shapely.ops import unary_union
# Erode the exact flat clip section by the wire radius. Route each wire around
# already seated wires; use a deterministic fine grid only inside this small loop.
C=d.BATTERY.C
solid=d.BATTERY.cable_clip()
# Reconstruct signed slice loops, then test every sampled 3-D wire position against CAD.
wire=d.BATTERY.cyl(.75,-14,16)
centres=d.BATTERY.wire_centres(); start=(C['centres_mm']+C['cable_bore_mm']/2+C['cable_wall_mm']+2,0.)
step=.075
bounds=(5.9,16.5,-3.5,3.5)
x0,x1,y0,y1=bounds
nx,ny=round((x1-x0)/step)+1,round((y1-y0)/step)+1
clip=solid.slice(C['axial_width_mm']/2)
# Robust geometry: use the union with winding holes via signed area.
outer=[];holes=[]
for arr in clip.to_polygons():
 area=sum(arr[i][0]*arr[(i+1)%len(arr)][1]-arr[(i+1)%len(arr)][0]*arr[i][1] for i in range(len(arr)))/2
 (outer if area>0 else holes).append(Polygon(arr))
shape=unary_union(outer).difference(unary_union(holes))
obstacles=shape.buffer(.755,resolution=24)
def pos(n):return (x0+n[0]*step,y0+n[1]*step)
def node(p):return (round((p[0]-x0)/step),round((p[1]-y0)/step))
valid={}
for x in range(nx):
 for y in range(ny):
  p=pos((x,y));valid[(x,y)]=not obstacles.covers(Point(p))
# Insert the farthest targets first to leave the entry clear.
order=sorted(range(12),key=lambda i:centres[i][0])
placed=[];routes={}
for i in order:
 first=node(start)
 def allowed(n):
  if not valid.get(n,False):return False
  p=pos(n)
  return all(math.dist(p,q)>=1.505 for q in placed)
 queue=[(0,first)];cost={first:0};prev={}
 found=None
 while queue:
  _,n=heapq.heappop(queue)
  if math.dist(pos(n),centres[i])<.085:
   found=n;break
  for dx,dy in ((1,0),(-1,0),(0,1),(0,-1),(1,1),(1,-1),(-1,1),(-1,-1)):
   k=(n[0]+dx,n[1]+dy)
   if not allowed(k):continue
   nc=cost[n]+math.hypot(dx,dy)
   if nc<cost.get(k,1e9):cost[k]=nc;prev[k]=n;heapq.heappush(queue,(nc+math.dist(pos(k),centres[i])/step,k))
 if found is None:raise RuntimeError(('route not found',i,placed))
 path=[centres[i],pos(found)]
 while found!=first:found=prev[found];path.append(pos(found))
 path.append(start);path=path[::-1]
 worst=max((solid ^ wire.translate((x,y,0))).volume() for x,y in path)
 if worst>.0001:raise RuntimeError(('clip overlap',i,worst))
 routes[str(i)]=path;placed.append(centres[i]);
json.dump({'order':order,'routes':routes,'wire_diameter_mm':1.5,'grid_mm':step,'exact_clip_overlap_max_mm3':0},open(Path(__file__).with_name('cable-routes.json'),'w'))
