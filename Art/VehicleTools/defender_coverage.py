"""Vehicle-specific coverage probes. Run against rejected and repaired assemblies."""
import bpy
from mathutils import Vector
from mathutils.bvhtree import BVHTree
S=4.6
FRONT=[(-.465,.152),(-.429,.207),(-.400,.228),(-.300,.228),(-.274,.207),(-.250,.143)]
REAR=[(.184,.145),(.214,.207),(.238,.226),(.311,.226),(.338,.207),(.357,.145)]
def lerp_at(y,p):
 for (a,b),(c,d) in zip(p,p[1:]):
  if a<=y<=c:return b+(d-b)*(y-a)/(c-a)
 return p[0][1] if y<p[0][0] else p[-1][1]
def sx(z):return lerp_at(z,[(.13,.209),(.147,.2146),(.263,.2146),(.274,.209),(.295,.207),(.307,.205),(.32,.201),(.44,.193)])
def probes():
 points=[]
 for sign in [1,-1]:
  side='L' if sign==1 else 'R'
  for label,poly in [('front',FRONT),('rear',REAR)]:
   for i in range(1,32):
    y=poly[0][0]+(poly[-1][0]-poly[0][0])*i/32
    top=lerp_at(y,poly)-.001
    # The compartment begins at the floor. Below this, the wheel/suspension opening is intentional.
    if top<.151:continue
    for j in range(11):
     z=.151+(top-.151)*j/10
     points.append((side+' '+label+' wheelhouse',(sign*.238,y,z),(-sign,0,0),.105))
  for a,b,z,label in [(-.191,.003,.308,'front window base'),(.030,.176,.308,'rear window base'),(.204,.417,.3075,'cargo window base'),(-.13,.42,.441,'roof header')]:
   for i in range(31):
    y=a+(b-a)*i/30
    points.append((side+' '+label,(sign*(sx(z)+.008),y,z),(-sign,0,0),.030))
  for y in [-.1965,.0075,.0255,.1805,.1995,.4215]:
   for j in range(21):
    z=(.24 if y>.17 else .16)+(.438-(.24 if y>.17 else .16))*j/20
    # The A-post above the waist follows the windscreen rake, not a vertical line.
    yy=y+max(0,z-.309)/(.44-.309)*.060 if y<-.19 else y
    points.append((side+' panel perimeter',(sign*(sx(z)+.008),yy,z),(-sign,0,0),.035))
  for i in range(15):
   z=.282+i*(.029/14)
   points.append((side+' scuttle',(sign*(sx(z)+.008),-.201,z),(-sign,0,0),.04))
 return points
def inspect(objects):
 dg=bpy.context.evaluated_depsgraph_get();v=[];f=[]
 for o in objects:
  if o.type!='MESH' or o.name.startswith('Rebuilt'):continue
  ev=o.evaluated_get(dg);me=ev.to_mesh();off=len(v)
  v.extend(o.matrix_world@p.co for p in me.vertices)
  f.extend(tuple(off+i for i in p.vertices) for p in me.polygons);ev.to_mesh_clear()
 tree=BVHTree.FromPolygons(v,f);groups={};misses=[]
 for label,p,d,dist in probes():
  result=tree.ray_cast(Vector(p)*S,Vector(d),dist*S)
  g=groups.setdefault(label,{'samples':0,'uncovered':0});g['samples']+=1
  if result[0] is None:g['uncovered']+=1;misses.append({'region':label,'point_raw':p})
 return {'samples':sum(g['samples'] for g in groups.values()),'uncovered':len(misses),'regions':groups,'misses':misses}
