"""Photo-led riverside homestead. Metres, front = -Y, ground datum = 0.
Exterior only; authored box hulls keep the veranda, stairs and open garage usable.
Rebuild: blender --background --python Art/Blender/build_lidar_homestead.py
"""
import bpy, math, json, random, sys
from pathlib import Path
from mathutils import Vector, Matrix
sys.path.insert(0,str(Path(__file__).resolve().parent))
import native_plant_lib as L
OUT=Path(__file__).resolve().parents[1]/'Export/LidarStudy/Homestead'
OUT.mkdir(parents=True,exist_ok=True)
bpy.ops.object.select_all(action='SELECT');bpy.ops.object.delete(use_global=False)
rng=random.Random(201020)
WOOD=(.43,.315,.19,1);TRIM=(.34,.265,.17,1);IRON=(.32,.38,.375,.65)
BLACK=(.032,.044,.041,1);GLASS=(.045,.075,.085,.15);STONE=(.20,.21,.19,1)
# Owner correction: longer perpendicular wing, steps inside the L.
WING_FRONT=-6.5;WING_BACK=3.8
WING_CENTRE=(WING_FRONT+WING_BACK)/2;WING_LENGTH=WING_BACK-WING_FRONT
WING_EAVE_FRONT=WING_FRONT-.35
STAIR_X=1.45
verts=[];faces=[];colours=[];hulls=[];models=[]
def export(ob,hs=()):
 # UE's FBX conversion reflects Blender Y. Counter-reflect render AND hull
 # geometry so the authored -Y front and the surveyed apron stay registered.
 mirror=Matrix.Diagonal((-1,-1,1,1))
 group=[ob]+list(hs)
 for o in group:o.data.transform(mirror);o.data.update()
 try:L.export(ob,hs,OUT)
 finally:
  for o in group:o.data.transform(mirror);o.data.update()
def face(points,c):
 n=len(verts);verts.extend(points);faces.append(tuple(range(n,n+len(points))));colours.append(c)
def box(p,size,c,solid=False):
 x,y,z=p;a,b,d=[v*.5 for v in size]
 vv=[(x+sx*a,y+sy*b,z+sz*d) for sx,sy,sz in [(-1,-1,-1),(1,-1,-1),(1,1,-1),(-1,1,-1),(-1,-1,1),(1,-1,1),(1,1,1),(-1,1,1)]]
 for f in [(3,2,1,0),(0,1,5,4),(1,2,6,5),(2,3,7,6),(3,0,4,7),(4,5,6,7)]:face([vv[i] for i in f],c)
 if solid:hulls.append((p,size))
def beam(a,b,w,c):
 a,b=Vector(a),Vector(b);d=(b-a).normalized();u=d.cross(Vector((0,0,1)))
 if u.length<.01:u=Vector((1,0,0))
 u.normalize();v=d.cross(u);u*=w*.5;v*=w*.5
 q=[a-u-v,a+u-v,a+u+v,a-u+v,b-u-v,b+u-v,b+u+v,b-u+v]
 for f in [(3,2,1,0),(0,1,5,4),(1,2,6,5),(2,3,7,6),(3,0,4,7),(4,5,6,7)]:face([tuple(q[i]) for i in f],c)
def shade(c):
 s=rng.uniform(.98,1.02);return tuple(v*s for v in c[:3])+(c[3],)
def window(x,y,z,w,h,side=False):
 # Dark recess and thin reveals; no transparent sorting or interior draw cost.
 if side:
  box((x,y,z),(.11,w+.16,h+.16),TRIM);box((x-.07,y,z),(.025,w,h),GLASS)
  box((x-.09,y,z),(.04,.045,h),IRON)
 else:
  box((x,y,z),(w+.16,.12,h+.16),TRIM);box((x,y-.075,z),(w,.025,h),GLASS)
  box((x,y-.1,z),(.045,.04,h),IRON)

def facade(x0,x1,y,z0,z1,openings=(),reverse=False):
 """Weatherboard wall with actual openings; no boards running behind glazing.

 Openings are (centre, centre-height, width, height). Thin framed reveals
 sit on a wall shell. The opaque backing inside each window supplies depth
 without another transparent material or sorting cost.
 """
 sign=1 if reverse else -1
 cuts=sorted(set([x0,x1]+[max(x0,min(x1,v)) for x,z,w,h in openings for v in (x-w/2,x+w/2)]))
 for a,b in zip(cuts,cuts[1:]):
  spans=[(z0,z1)]
  for x,z,w,h in openings:
   if x-w/2<(a+b)/2<x+w/2:
    spans=[(lo,hi) for u,v in spans for lo,hi in [(u,min(v,z-h/2)),(max(u,z+h/2),v)] if hi>lo+.001]
  for lo,hi in spans:
   box(((a+b)/2,y,(lo+hi)/2),(b-a,.12,hi-lo),WOOD)
   for k in range(math.ceil((z1-z0)/.18)):
    bot=max(lo,z0+k*.18);top=min(hi,z0+(k+1)*.18)
    if top<=bot:continue
    # A wedge profile gives each lap a clean, continuous shadow line.
    ya=y+sign*.065;yb=y+sign*.09
    q=[(a,ya,top),(b,ya,top),(b,yb,bot+.008),(a,yb,bot+.008)]
    face(q[::-1] if sign<0 else q,shade(WOOD))
    face([(a,yb,bot+.008),(b,yb,bot+.008),(b,ya,bot+.008),(a,ya,bot+.008)],TRIM)
 for x,z,w,h in openings:
  yy=y+sign*.075
  box((x,y-sign*.035,z),(w,.025,h),GLASS)
  for xx in (x-w/2,x+w/2):box((xx,yy,z),(.065,.16,h+.13),TRIM)
  for zz in (z-h/2,z+h/2):box((x,yy,zz),(w+.13,.16,.065),TRIM)
  box((x,yy,z),(.045,.10,h),IRON)
  box((x,y+sign*.15,z-h/2-.025),(w+.18,.20,.055),TRIM)

def joined_roofs():
 """Trim both gables to the visible roof envelope, including their valleys.

 Subtract the portions covered by the other roof planes before making faces.
 This avoids intersecting roof slabs, double gables and Z-fighting at the join.
 """
 planes=[]
 for side in (-1,1):
  q=[(-6.9,1,4.76),(4.8,1,4.76),(4.8,1+side*3.35,3.60),(-6.9,1+side*3.35,3.60)]
  planes.append((q if side>0 else q[::-1],IRON))
 for side in (-1,1):
  q=[(4.8,WING_EAVE_FRONT,4.95),(4.8,4.15,4.95),(4.8+side*2.325,4.15,3.65),(4.8+side*2.325,WING_EAVE_FRONT,3.65)]
  planes.append((q if side<0 else q[::-1],(.19,.26,.21,.7)))
 def split(poly,fn):
  inside=[];outside=[]
  for a,b in zip(poly,poly[1:]+poly[:1]):
   fa,fb=fn(a),fn(b)
   (inside if fa>=0 else outside).append(a)
   if (fa>=0)!=(fb>=0):
    t=fa/(fa-fb);p=tuple(a[i]+t*(b[i]-a[i]) for i in range(3));inside.append(p);outside.append(p)
  return inside,outside
 def blockers(q):
  a,b,c=map(Vector,q[:3]);n=(b-a).cross(c-a);assert n.z>0
  out=[]
  for a,b in zip(q,q[1:]+q[:1]):out.append(lambda p,a=a,b=b:(b[0]-a[0])*(p[1]-a[1])-(b[1]-a[1])*(p[0]-a[0]))
  out.append(lambda p,n=n,a=q[0]:sum(n[i]*(a[i]-p[i]) for i in range(3))-.00001)
  return out
 for i,(q,col) in enumerate(planes):
  visible=[q]
  for j,(cover,_) in enumerate(planes):
   if i==j:continue
   result=[]
   for poly in visible:
    rem=poly
    for fn in blockers(cover):
     rem,outer=split(rem,fn)
     if len(outer)>=3:result.append(outer)
     if len(rem)<3:break
   visible=result
  for poly in visible:face(poly,col)
 # Main exposed end and both wing ends; no interior gable at the junction.
 face([(-6.5,-2,3.55),(-6.5,1,4.68),(-6.5,4,3.55)],WOOD)
 for y in (WING_FRONT,WING_BACK):
  p=[(2.8,y,3.6),(6.8,y,3.6),(4.8,y,4.86)]
  face(p if y<0 else p[::-1],WOOD)
 # Thin seams stop at the roof intersection, instead of protruding through it.
 def main_z(y):return 3.6+1.16*(1-abs(y-1)/3.35)
 def wing_z(x):return 3.65+1.3*(1-abs(x-4.8)/2.325)
 def visible_main(x,y):return not (2.475<x<7.125 and WING_EAVE_FRONT<y<4.15 and wing_z(x)>main_z(y))
 def visible_wing(x,y):return not (-6.9<x<4.8 and -2.35<y<4.35 and main_z(y)>wing_z(x))
 def rib(a,b,check,zfn,col,width=.014):
  start=None
  for k in range(81):
   t=k/80;x=a[0]*(1-t)+b[0]*t;y=a[1]*(1-t)+b[1]*t;p=(x,y,zfn(x,y)+.012)
   ok=check(x,y)
   if ok and start is None:start=p
   if start is not None and (not ok or k==80):
    end=prev if not ok else p
    if (Vector(end)-Vector(start)).length>.025:beam(start,end,width,col)
    start=None
   prev=p
 for x in [-6.9+i*.24 for i in range(49)]:
  for side in (-1,1):rib((x,1),(x,1+side*3.35),visible_main,lambda x,y:main_z(y),IRON)
 for y in [WING_EAVE_FRONT+i*(4.15-WING_EAVE_FRONT)/46 for i in range(47)]:
  for side in (-1,1):rib((4.8,y),(4.8+side*2.325,y),visible_wing,lambda x,y:wing_z(x),(.19,.26,.21,.7))
 rib((-6.9,1),(4.8,1),visible_main,lambda x,y:main_z(y),IRON,.08)
 rib((4.8,WING_EAVE_FRONT),(4.8,4.15),visible_wing,lambda x,y:wing_z(x),IRON,.08)
 for side in (-1,1):
  beam((-6.92,1,4.77),(-6.92,1+side*3.35,3.60),.12,TRIM)
  for y in (WING_EAVE_FRONT-.01,4.16):beam((4.8,y,4.96),(4.8+side*2.325,y,3.65),.12,TRIM)
def finish(name):
 global verts,faces,colours,hulls
 mesh=bpy.data.meshes.new(name);mesh.from_pydata(verts,[],faces);mesh.update()
 ob=bpy.data.objects.new(name,mesh);bpy.context.collection.objects.link(ob)
 mat=bpy.data.materials.get('M_Homestead') or bpy.data.materials.new('M_Homestead');mat.diffuse_color=WOOD
 mat.use_nodes=True
 if not mat.node_tree.nodes.get('HomesteadColour'):
  colour=mat.node_tree.nodes.new('ShaderNodeVertexColor');colour.name='HomesteadColour';colour.layer_name='Color'
  bs=mat.node_tree.nodes.get('Principled BSDF');mat.node_tree.links.new(colour.outputs['Color'],bs.inputs['Base Color']);bs.inputs['Roughness'].default_value=.78
 mesh.materials.append(mat);attr=mesh.color_attributes.new(name='Color',type='FLOAT_COLOR',domain='CORNER')
 for poly,c in zip(mesh.polygons,colours):
  for i in poly.loop_indices:attr.data[i].color=c
 hs=[]
 for i,(p,size) in enumerate(hulls):
  bpy.ops.mesh.primitive_cube_add(size=1,location=p);h=bpy.context.object;h.name=f'UCX_{name}_{i:03}';h.dimensions=size
  bpy.ops.object.transform_apply(location=False,rotation=False,scale=True)
  # Export helper scales vertices, not object translations: bake the hull offset.
  for v in h.data.vertices:v.co+=h.location
  h.location=(0,0,0);h.hide_render=True;hs.append(h)
 export(ob,hs)
 models.append(dict(name=name,triangles=sum(len(f)-2 for f in faces),hulls=len(hulls),expected_first_vertex_cm=[-verts[0][0]*100,verts[0][1]*100,verts[0][2]*100]))
 verts=[];faces=[];colours=[];hulls=[]
 return ob

# Two house volumes, with a separate, lower lean-to veranda roof. The main
# gable must remain visible above it, as in the owner's oblique ground photos.
box((-1.85,1,.84),(9.3,6,.22),TRIM,True)
box((4.8,WING_CENTRE,.84),(4,WING_LENGTH,.22),TRIM,True)
facade(-6.5,2.8,-2,.95,3.55,[(-4.75,2.23,2.25,1.65),(-1.8,2.23,2.15,1.65),(1.55,1.99,1.5,2.08)])
facade(-6.5,2.8,4,.95,3.55,[(-3,2.25,1.5,1.1)],True)
facade(2.8,6.8,WING_FRONT,.95,3.6,[(4.8,2.25,1.65,1.05)])
facade(2.8,6.8,3.8,.95,3.6,[],True)
start=len(verts)
facade(-2,4,6.5,.95,3.55,[(1,2.3,1.7,1.35)],True)
facade(WING_FRONT,WING_BACK,-6.8,.95,3.6,[(-4.5,2.3,1.3,1.15),(1.4,2.3,1.3,1.15)])
# Exposed inside face of the L; it must not be an open shell behind the deck.
facade(WING_FRONT,-2,-2.8,.95,3.6,[],True)
verts[start:]=[(-y,x,z) for x,y,z in verts[start:]]
# Simple interior exclusion hulls remain inside the weatherboard shell.
hulls.extend([((-1.85,1,2.25),(9.1,5.8,2.6)),((4.8,WING_CENTRE,2.275),(3.8,WING_LENGTH-.2,2.65))])
for x,y in [(-6.55,-2),(-6.55,4),(2.8,WING_FRONT),(6.85,WING_FRONT),(6.85,3.8)]:box((x,y,2.25),(.10,.12,2.6),TRIM)
joined_roofs()
def lean_roof(x0,x1,y0,y1,z0,z1):
 face([(x0,y0,z0),(x1,y0,z0),(x1,y1,z1),(x0,y1,z1)],IRON)
 face([(x0,y1,z1-.08),(x1,y1,z1-.08),(x1,y0,z0-.08),(x0,y0,z0-.08)],TRIM)
 for a,b in [((x0,y0,z0),(x1,y0,z0)),((x0,y0,z0),(x0,y1,z1)),((x1,y0,z0),(x1,y1,z1))]:beam(a,b,.12,TRIM)
 for i in range(math.ceil((x1-x0)/.17)+1):
  x=x0+i*(x1-x0)/math.ceil((x1-x0)/.17);beam((x,y0,z0+.012),(x,y1,z1+.012),.018,IRON)
lean_roof(-7.0,2.85,-4.95,-1.90,3.10,3.47)
# Side veranda / light lean-to extension, visible to the left of the gable.
lean_roof(-8.9,-6.6,-4.95,-1.90,2.95,3.35)
box((-2,-3.35,.82),(9.4,2.95,.26),TRIM,True)
box((-7.55,-3.35,.82),(2,2.95,.26),TRIM,True)
for i in range(61):box((-6.6+i*.153,-3.35,.965),(.145,2.92,.03),shade(WOOD))
for x in (-8.7,-6.6,-3.5,-.35,2.7):
 box((x,-4.78,1.53),(.13,.13,3.06),TRIM,True)
box((-8.7,-1.9,1.53),(.13,.13,3.06),TRIM)
# Timber foundation skirt and a solid boarded section of the deck balustrade.
# These hide the undercroft rather than leaving the house on bare stilts.
for i in range(9):box((-1.95,-4.84,-.48+i*.16),(9.3,.075,.15),shade(WOOD))
# Close the side extension's exposed undercroft as well.
box((-7.65,-4.80,.22),(2.15,.10,1.20),WOOD)
box((-8.72,-3.35,.22),(.10,2.95,1.20),WOOD)
for i in range(13):
 box((6.84,WING_CENTRE,-1.12+i*.16),(.075,WING_LENGTH,.15),shade(WOOD))
 box((4.8,WING_FRONT-.04,-1.12+i*.16),(4,.075,.15),shade(WOOD))
for lo,hi,closed in [(-8.7,-6.6,False),(-6.6,-2.1,False),(-2.1,.55,True),(2.35,2.70,False)]:
 for z in (1.04,1.96):box(((lo+hi)/2,-4.79,z),(hi-lo,.12,.12),TRIM)
 pitch=.14 if closed else .18
 for i in range(math.ceil((hi-lo)/pitch)):
  x=lo+(i+.5)*(hi-lo)/math.ceil((hi-lo)/pitch);box((x,-4.80,1.50),(.132 if closed else .06,.07,.86),shade(WOOD))
for i in range(6):
 h=(6-i)*.158;box((STAIR_X,-4.95-i*.30,h*.5),(1.55,.34,h),shade(WOOD),True)
for x in (STAIR_X-.83,STAIR_X+.83):
 beam((x,-4.7,1.96),(x,-6.6,1.01),.09,TRIM)
 for i in range(6):box((x,-4.95-i*.30,1.38-i*.158),(.065,.065,.95),WOOD)
# Larger glazed living openings behind the veranda, and modest wing windows.

# Thin gutter, downpipe and flue; long roof details stay geometry, not actors.
beam((-7,-4.97,3.08),(2.85,-4.97,3.08),.075,IRON)
beam((-6.75,-4.99,3.08),(-6.75,-4.99,.10),.06,IRON)
box((-.35,.6,4.85),(.13,.13,2.35),IRON);box((-.35,.6,6.05),(.26,.26,.07),BLACK)
for y in (-1.9,-.55,.8):
 for x in (5.6,6.25):
  z=3.65+1.30*(1-abs(x-4.8)/2.325)+.055
  face([(x-.29,y-.62,z+.162),(x+.29,y-.62,z-.162),(x+.29,y+.62,z-.162),(x-.29,y+.62,z+.162)],(.025,.055,.073,.28))
  for t in (-.62,0,.62):beam((x-.29,y+t,z+.165),(x+.29,y+t,z-.16),.018,IRON)
house=finish('SM_RiversideHouse')

# Low charcoal corrugated garage: two bays, left open, right roller, side access.
box((0,0,-.15),(8.2,7.2,.3),STONE,True)
for x in (-4,4):box((x,0,1.5),(.16,7,3),BLACK,True)
box((0,3.5,1.5),(8,.16,3),BLACK,True)
box((0,-3.5,2.82),(8,.18,.36),BLACK,True)
for x in (-3.75,0,3.75):box((x,-3.5,1.32),(.5,.18,2.64),BLACK,True)
box((1.87,-3.5,1.3),(3.2,.10,2.6),(.055,.066,.062,1),True)
for z in [i*.14+.05 for i in range(19)]:box((1.87,-3.57,z),(3.2,.035,.035),(.075,.085,.08,1))
box((-1.87,-3.5,2.65),(3.2,.32,.32),BLACK)
# Roof falls gently to rear; shallow parapet and closely spaced ribs.
face([(-4.25,-3.8,3.15),(4.25,-3.8,3.15),(4.25,3.8,2.92),(-4.25,3.8,2.92)],BLACK)
for x in [i*.17-4.25 for i in range(51)]:beam((x,-3.8,3.16),(x,3.8,2.93),.027,BLACK)
for x in (-4,4):
 for i in range(42):box((x+(-.09 if x<0 else .09),-3.5+i*.17,1.5),(.035,.028,3),(.05,.062,.057,1))
for i in range(48):box((-4+i*.17,3.60,1.45),(.028,.035,2.9),(.05,.062,.057,1))
window(-4.11,1.5,1.75,1.45,.85,True)
box((-4.13,-1,1.05),(.10,.95,2.1),(.06,.073,.064,1));box((-4.2,-1.33,1.1),(.07,.07,.035),IRON)
for x in (-3.48,-.28,.28,3.48):box((x,-3.65,1.4),(.1,.13,2.8),(.09,.10,.09,1))
box((1.87,-3.67,.95),(.32,.06,.04),IRON)
# Low workbench inside open bay and rear shelving supply depth without interior clutter actors.
box((-2.1,2.7,.85),(2.8,.65,.12),WOOD)
for x in (-3.2,-1):box((x,2.7,.4),(.1,.1,.8),BLACK)
# Photo proportions: compact two-car shed, lower than the timber veranda.
# Scale render and collision together; layout below uses the same door centre.
garage_scale=(.8,.9,.9)
verts=[tuple(v[i]*garage_scale[i] for i in range(3)) for v in verts]
hulls=[(tuple(p[i]*garage_scale[i] for i in range(3)),tuple(s[i]*garage_scale[i] for i in range(3))) for p,s in hulls]
garage=finish('SM_RiversideGarage')

# Positive fill only, sampled from the final map relief by the installer survey.
# A broad graded terrace gives the deck steps and garage a grounded landing.
survey=OUT/'ground-survey.json'
if survey.exists():
 data=json.loads(survey.read_text());H=data['heights_cm'];ox,oy=data['grid_origin'];step=data['step_cm']
 def height(x,y):
  i=max(0,min(len(H[0])-2,int((x-ox)/step)));j=max(0,min(len(H)-2,int((y-oy)/step)))
  a=(x-ox)/step-i;b=(y-oy)/step-j
  return (1-b)*((1-a)*H[j][i]+a*H[j][i+1])+b*((1-a)*H[j+1][i]+a*H[j+1][i+1])
 def samples(bounds):
  x0,y0,x1,y1=bounds;return [height(x,y) for x in range(x0,x1+1,100) for y in range(y0,y1+1,100)]
 # Set the FLOOR just above the ground under the actual house, not the datum
 # above the highest point of a much larger yard. The latter created a shelf.
 house_z=max(samples((-650,-200,280,400))+samples((280,int(WING_FRONT*100),680,400))+samples((-870,-470,-670,-190)))+18-95
 gx,gy=data['garage_local_cm']
 garage_bounds=(int(gx-330),int(gy-315),int(gx+330),int(gy+315))
 parking_bounds=(int(gx-420),int(gy-1350),int(gx+420),int(gy+315))
 garage_z=max(samples(garage_bounds))+5
 def smooth(t):t=max(0,min(1,t));return t*t*(3-2*t)
 def weight(x,y,bounds,feather):
  x0,y0,x1,y1=bounds;dist=math.hypot(max(x0-x,0,x-x1),max(y0-y,0,y-y1))
  return 1-smooth(dist/feather)
 def court(x,y):
  radius=math.hypot((x-150)/2050,(y+2000)/1700)
  return 1-smooth((radius-.85)/.15)
 def grade(x,y):
  h=height(x,y);wh=weight(x,y,(-880,-660,700,400),950);wg=weight(x,y,parking_bounds,650)
  if wh>=.999:return max(h+2,house_z)
  if wg>=.999:return max(h+2,garage_z)
  a=wh/max(.001,1-wh)**2;b=wg/max(.001,1-wg)**2
  target=(a*house_z+b*garage_z)/max(.0001,a+b)
  cover=max(wh,wg)
  # Bury the outer seam to absorb sub-grid terrain curvature; keep pads intact.
  return max(h+2,h+(target-h)*cover)-28*(1-smooth(max(cover,court(x,y))/.35))
 gv=[];gf=[];mats=[]
 for y in range(-3900,1501,100):
  for x in range(-2000,2301,100):gv.append((x*.01,y*.01,grade(x,y)*.01))
 nx=44
 for j in range(54):
  for i in range(43):
   x=-2000+(i+.5)*100;y=-3900+(j+.5)*100
   # Omit the unmodified outer landscape, retaining only positive graded fill.
   if max(weight(x,y,(-880,-660,700,400),950),weight(x,y,parking_bounds,650),court(x,y))<.001:continue
   a=j*nx+i;gf.extend([(a,a+1,a+nx+1),(a,a+nx+1,a+nx)])
   mats.extend([1 if x<650 and y>-1000 else 0]*2)
 mesh=bpy.data.meshes.new('SM_HomesteadGrade');mesh.from_pydata(gv,[],gf);mesh.update()
 ob=bpy.data.objects.new('SM_HomesteadGrade',mesh);bpy.context.collection.objects.link(ob)
 for name in ('M_Gravel','M_Lawn'):
  m=bpy.data.materials.new(name);m.diffuse_color=(.25,.27,.25,1) if name=='M_Gravel' else (.11,.15,.055,1);mesh.materials.append(m)
 for p,m in zip(mesh.polygons,mats):p.material_index=m;p.use_smooth=True
 attr=mesh.color_attributes.new(name='Color',type='FLOAT_COLOR',domain='CORNER')
 for p in mesh.polygons:
  for li in p.loop_indices:
   x,y,_=gv[mesh.loops[li].vertex_index];x*=100;y*=100
   lawn=weight(x+45*math.sin(y/130),y+65*math.sin(x/170),(-930,-830,560,430),650)
   attr.data[li].color=(lawn,lawn,lawn,1)
 export(ob)
 models.append(dict(name=ob.name,triangles=len(gf),hulls=0,collision='complex static',expected_first_vertex_cm=[-gv[0][0]*100,gv[0][1]*100,gv[0][2]*100]))
 bay=(gx+187*.8,gy-950)
 (OUT/'layout.json').write_text(json.dumps(dict(version='HS4',placement_yaw=data['yaw'],anchor_cm=data['anchor_cm'],house_datum_cm=house_z,garage_floor_cm=garage_z,garage_local_cm=[gx,gy],door_local_cm=[gx+187*.8,gy-345],stand_local_cm=[gx+187*.8,gy-515],bay_local_cm=bay,bay_height_cm=grade(*bay),front_camera_cm=[-950,-3200,height(-950,-3200)+140],veranda_path_local_cm=[[145,-700],[145,-430],[145,-270],[-150,-270]],wing_front_cm=WING_FRONT*100,ground_digest=data['ground_digest'],notes='HS4 extended L wing and connected inside-corner veranda stairs. Existing terrain unchanged.'),indent=2))
 # Rebuild benchmark poses with the same transform as the buildings.
 angle=math.radians(data['yaw'])
 def world_xy(x,y):return (data['anchor_cm'][0]-x*math.cos(angle)-y*math.sin(angle),data['anchor_cm'][1]-x*math.sin(angle)+y*math.cos(angle))
 ax,ay=world_xy(-950,-3200);tx,ty=world_xy(350,-100)
 dx,dy=world_xy(gx+187*.8,gy-515)
 poses=[dict(name='house_arrival',x=ax,y=ay,z=height(-950,-3200)+140,yaw=math.degrees(math.atan2(ty-ay,tx-ax))),dict(name='garage_door',x=dx,y=dy,z=garage_z+100,yaw=data['yaw']+90)]
 (OUT/'perf-poses.json').write_text(json.dumps(poses,indent=2))

# Shared vertex colour preview material.
garage.location=(gx*.01,gy*.01,(garage_z-house_z)*.01) if survey.exists() else (12,-2,-.7)
if survey.exists():ob.location.z=-house_z*.01
mat=bpy.data.materials['M_Homestead'];mat.use_nodes=True
n=mat.node_tree.nodes.new('ShaderNodeVertexColor');n.layer_name='Color'
bs=mat.node_tree.nodes.get('Principled BSDF');mat.node_tree.links.new(n.outputs['Color'],bs.inputs['Base Color']);bs.inputs['Roughness'].default_value=.72
bpy.ops.wm.save_as_mainfile(filepath=str(OUT/'RiversideHomestead.blend'))
if '--preview' in sys.argv:
 scene=bpy.context.scene;scene.render.engine='CYCLES';scene.cycles.samples=24
 scene.render.resolution_x=1440;scene.render.resolution_y=900;scene.render.resolution_percentage=100
 bpy.ops.object.camera_add(location=(23,-32,13));cam=bpy.context.object;cam.rotation_euler=(Vector((4,-1,1.7))-cam.location).to_track_quat('-Z','Y').to_euler();cam.data.type='PERSP';cam.data.lens=42;scene.camera=cam
 bpy.ops.object.light_add(type='SUN',location=(3,-12,16));sun=bpy.context.object;sun.rotation_euler=(.4,-.5,-.6);sun.data.energy=3
 scene.world.color=(.35,.35,.35)
 scene.render.filepath=str(OUT/'model-preview.png');bpy.ops.render.render(write_still=True)
(OUT/'manifest.json').write_text(json.dumps(dict(version='HS4',models=models),indent=2))
print('HS1_BUILD',json.dumps(models))
