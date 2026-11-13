"""Static, local coverage probes for this measured Graphic Adventure assembly."""
import bpy, json
from pathlib import Path
from mathutils import Vector
from mathutils.bvhtree import BVHTree
S=4.6
P=Path('C:/GrandTour/Art/Export/VehicleTools/graphic-adventure-assembly-v04')
SPEC=json.loads((P/'vehicle-spec.json').read_text())
def ip(x,points):
 if x<=points[0][0]:return points[0][1]
 for (a,b),(c,d) in zip(points,points[1:]):
  if x<=c:return b+(d-b)*(x-a)/(c-a)
 return points[-1][1]
def sx(z):return ip(z,SPEC['side_stations'])
def tail(z):return ip(z,SPEC['rear_stations'])
def seq(a,b,n):return [a+(b-a)*i/(n-1) for i in range(n)]
def probes():
 p=[]
 def add(label,pos,d,reach=.035):p.append((label,pos,d,reach))
 for sign in [-1,1]:
  side='L' if sign>0 else 'R'
  for kind,a in SPEC['arches'].items():
   for y in seq(a['inner'][0][0]+.003,a['inner'][-1][0]-.003,45):
    top=ip(y,a['inner'])-.001
    if top<=.143:continue
    for z in seq(.143,top,12):add(side+' '+kind+' inner wheelhouse',(sign*.244,y,z),(-sign,0,0),.110)
   for y in seq(a['outer'][0][0]+.001,a['outer'][-1][0]-.001,75):
    z=ip(y,a['outer'])+.001
    add(side+' '+kind+' arch seating',(sign*(sx(z)+.010),y,z),(-sign,0,0),.025)
  for label,a,b,z in [('front window base',-.17,.032,.301),('rear window base',.036,.252,.301),('cargo window base',.260,.414,.301),('roof rebate',-.087,.385,.425)]:
   for y in seq(a,b,45):add(side+' '+label,(sign*(sx(z)+.01),y,z),(-sign,0,0),.04)
  for label,y,lo,hi in [('front door',-.1785,.152,.301),('B pillar',.034,.152,.424),('rear door',.255,.244,.301),('scuttle',-.182,.27,.299)]:
   for z in seq(lo,hi,45):add(side+' '+label,(sign*(sx(z)+.01),y,z),(-sign,0,0),.04)
  for z in seq(.303,.422,45):
   y=ip(z,[(.301,.2565),(.424,.211)])
   add(side+' C pillar',(sign*(sx(z)+.01),y,z),(-sign,0,0),.04)
   y=tail(z)-.0005
   add(side+' rear corner',(sign*(sx(z)+.01),y,z),(-sign,0,0),.04)
  for y in seq(-.085,.395,45):
   # Between the upper window rail and the underside of the crowned roof.
   for z in [.4245,.4265,.4280]:add(side+' crown to cantrail',(sign*.174,y,z),(-sign,0,0),.023)
  for y in seq(-.43,-.186,45):
   for z in [.2575,.2585,.2600]:add(side+' bonnet to wing',(sign*.233,y,z),(-sign,0,0),.045)
  for y in seq(-.17,.435,65):
   if .138<y<.392:continue
   for x in seq(.201,sx(.14)-.001,7):add(side+' floor perimeter',(sign*x,y,.120),(0,0,1),.033)
 for z in seq(.322,.410,15):
  for x in seq(-.15,.15,25):add('Windscreen',(x,ip(z,[(.301,-.185),(.424,-.107)])-.012,z),(0,1,0),.04)
 for x in seq(-.166,.166,41):
  f=ip(abs(x)/.176,[(0,1),(.4545,.91),(.7386,.77),(.8523,.67),(.9375,.49),(.9773,.24),(1,0)])
  top=.4245+.0055*f
  for z in seq(.4242,top-.0001,7):add('Curved roof front header',(x,-.140,z),(0,1,0),.060)
 for z in seq(.190,.300,30):
  for x in [-.1675,.1675]:add('Tailgate jamb',(x,tail(z)+.010,z),(0,-1,0),.04)
 for x in seq(-.165,.165,35):
  for z in [.187,.301,.423]:add('Rear horizontal seams',(x,tail(z)+.010,z),(0,-1,0),.04)
 for y in seq(-.175,.434,45):
  for x in seq(-.2,.2,29):
   if .15<y<.376 and abs(x)>.137:continue
   add('Cabin floor',(x,y,.134),(0,0,1),.009)
 return p
def tree(objects):
 dg=bpy.context.evaluated_depsgraph_get();v=[];f=[]
 for o in objects:
  if o.type!='MESH':continue
  ev=o.evaluated_get(dg);me=ev.to_mesh();off=len(v)
  v.extend(o.matrix_world@p.co for p in me.vertices)
  f.extend(tuple(off+i for i in p.vertices) for p in me.polygons);ev.to_mesh_clear()
 return BVHTree.FromPolygons(v,f)
def inspect(objects):
 objects=[o for o in objects if not any(k in o.name for k in ['tyre','tread','rim','spoke','bolt','hub'])]
 t=tree(objects);groups={};miss=[]
 for label,pos,d,reach in probes():
  g=groups.setdefault(label,{'samples':0,'uncovered':0});g['samples']+=1
  if t.ray_cast(Vector(pos)*S,Vector(d),reach*S)[0] is None:g['uncovered']+=1;miss.append({'region':label,'raw_position':pos})
 return {'samples':sum(g['samples'] for g in groups.values()),'uncovered':len(miss),'regions':groups,'misses':miss}
