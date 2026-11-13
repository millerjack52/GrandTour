"""Fitted litter/root geometry and short-range occlusion from the actual bank/ferns."""
import bpy,sys,math,random,json,time,hashlib
from pathlib import Path
from mathutils import Vector,Matrix
from mathutils.bvhtree import BVHTree
ROOT=Path('C:/GrandTour');sys.path[:0]=[str(ROOT/'Art/Blender'),str(ROOT/'Art/Unreal')]
import native_plant_lib as L
import lidar_section_surface as S
OUT=ROOT/'Art/Export/LidarStudy/FirstSection/FernFloor';OUT.mkdir(parents=True,exist_ok=True)
started=time.time();bpy.ops.wm.open_mainfile(filepath=str(OUT.parent/'bank-surface.blend'))
bank=next(o for o in bpy.data.objects if o.type=='MESH' and o.name.startswith('SM_RS7_BankSkin'))
bank_tree=BVHTree.FromPolygons([v.co.copy() for v in bank.data.vertices],[tuple(p.vertices) for p in bank.data.polygons])
with bpy.data.libraries.load(str(OUT.parent/'bank-plants.blend'),link=False) as (src,dst):dst.objects=[n for n in src.objects if n.endswith('_LOD1')]
plant_mesh={o.name.replace('_LOD1',''):o.data for o in dst.objects if o}
plants=json.loads((ROOT/'Saved/LidarAuthoringQA/RS7/placement.json').read_text())['placement']
verts=[];faces=[]
for p in plants:
 mesh=plant_mesh[p['mesh']];t=Matrix.Translation(Vector(((p['x']-S.CX)/100,-(p['y']-S.CY)/100,(p['z']-4800)/100)))@Matrix.Rotation(-math.radians(p['yaw']),4,'Z')@Matrix.Scale(p['scale'],4)
 base=len(verts);verts.extend(t@v.co for v in mesh.vertices);faces.extend(tuple(base+i for i in f.vertices) for f in mesh.polygons)
plant_tree=BVHTree.FromPolygons(verts,faces);print('FERN_FLOOR_PLANT_BVH',len(verts),len(faces),flush=True)
def ground(x,y):
 hit=bank_tree.ray_cast(Vector((x,y,100)),Vector((0,0,-1)),200)
 return hit[0]
def clear(p,height=.06):
 hit=plant_tree.ray_cast(p+Vector((0,0,.01)),Vector((0,0,1)),height)
 return hit[0] is None
rng=random.Random(711680);g=L.Geo();counts=dict(leaves=0,twigs=0,roots=0,moss_clods=0)
for p in plants:
 cx=(p['x']-S.CX)/100;cy=-(p['y']-S.CY)/100
 # Connected root runs emerge from existing crowns, partly embedded in the bank.
 for k in range(2):
  angle=rng.random()*math.tau;length=rng.uniform(.32,.95);radius=rng.uniform(.009,.022);points=[]
  for j in range(6):
   d=.05+length*j/5;x=cx+math.cos(angle)*d+math.sin(j*.8)*.035;y=cy+math.sin(angle)*d
   q=ground(x,y)
   if q is None:break
   q.z+=radius*.25*(1-j/7);points.append(q)
  if len(points)==6:
   L.tube(g,points,[radius*(1-j/7) for j in range(6)],5,(.105,.078,.038),mi=0,caps=(True,True));counts['roots']+=1
 # Small islands of fallen leaves, with open moss and exposed rock left between.
 for k in range(rng.randint(8,13)):
  angle=rng.random()*math.tau;rad=rng.uniform(.25,1.15)*p['scale'];x=cx+math.cos(angle)*rad;y=cy+math.sin(angle)*rad;q=ground(x,y)
  if q is None or not clear(q):continue
  a,b=S.uv(S.CX+x*100,S.CY-y*100)
  if not S.inside(S.CX+x*100,S.CY-y*100,100) or S.rock(a,b)>.65:continue
  length=rng.uniform(.075,.19);width=length*rng.uniform(.37,.62);rot=rng.random()*math.tau;cs,sn=math.cos(rot),math.sin(rot)
  leaf=[]
  for u,v,curl in [(-.5,0,.003),(-.22,-.48,.002),(.28,-.35,.006),(.5,0,.023),(.28,.35,.009),(-.22,.48,.002),(.02,0,.014)]:
   xx=x+cs*u*length-sn*v*width;yy=y+sn*u*length+cs*v*width;hit=ground(xx,yy)
   if hit is None:break
   hit.z+=curl;leaf.append(hit)
  if len(leaf)==7:
   col=rng.choice([(.17,.12,.055),(.115,.095,.045),(.105,.125,.045),(.20,.155,.075)]);col=tuple(c*rng.uniform(.85,1.1) for c in col)
   g.add(leaf,[(6,j,(j+1)%6) for j in range(6)],col,None,1);counts['leaves']+=1
 # Broken woody fragments bridge hollows but retain several ground contacts.
 if rng.random()<.75:
  angle=rng.random()*math.tau;length=rng.uniform(.18,.55);points=[];x=cx+math.cos(angle)*.7;y=cy+math.sin(angle)*.7
  for j in range(4):
   q=ground(x+math.cos(angle)*length*j/3,y+math.sin(angle)*length*j/3)
   if q is None:break
   q.z+=.008;points.append(q)
  if len(points)==4:
   L.tube(g,points,[.012,.010,.008,.005],5,(.14,.10,.045),mi=0,caps=(True,True));counts['twigs']+=1
 for k in range(2):
  angle=rng.random()*math.tau;rad=rng.uniform(.25,.9);x=cx+math.cos(angle)*rad;y=cy+math.sin(angle)*rad;q=ground(x,y)
  if q is None or not clear(q,.10):continue
  a,b=S.uv(S.CX+x*100,S.CY-y*100)
  if S.rock(a,b)>.55:continue
  radius=rng.uniform(.045,.11);height=rng.uniform(.02,.055);vs=[]
  for j in range(6):
   hit=ground(x+math.cos(j*math.tau/6)*radius,y+math.sin(j*math.tau/6)*radius)
   if hit is None:break
   hit.z-=.004;vs.append(hit)
  if len(vs)==6:
   vs.append(q+Vector((0,0,height)));g.add(vs,[(6,j,(j+1)%6) for j in range(6)],(.095,.135,.036),None,0);counts['moss_clods']+=1
base=len(verts);verts.extend(v.co.copy() for v in bank.data.vertices);faces.extend(tuple(base+i for i in p.vertices) for p in bank.data.polygons)
base=len(verts);verts.extend(g.v);faces.extend(tuple(base+i for i in f) for f in g.f)
scene_tree=BVHTree.FromPolygons(verts,faces);del verts,faces

def ao(p,n,samples=24):
 n=n.normalized();t=n.cross(Vector((.23,.71,.37))).normalized();b=n.cross(t);blocked=0.
 for k in range(samples):
  z=math.sqrt((k+.5)/samples);r=math.sqrt(1-z*z);ang=k*2.39996323;direction=n*z+(t*math.cos(ang)+b*math.sin(ang))*r
  hit=scene_tree.ray_cast(p+n*.008,direction,1.35)
  if hit[0] is not None:blocked+=(1-hit[3]/1.35)**.5
 return max(.30,1-.88*blocked/samples)
W,H=512,512;pixels=[];values=[]
for j in range(H):
 b=-780+(j+.5)/H*1560
 for i in range(W):
  a=-1100+(i+.5)/W*2200;x,y=S.xy(a,b);hit=bank_tree.ray_cast(Vector(((x-S.CX)/100,-(y-S.CY)/100,100)),Vector((0,0,-1)),200)
  value=ao(hit[0],hit[1]) if hit[0] is not None else 1.
  edge=max(0,min(1,(1100-abs(a)-35)/140,(780-abs(b)-35)/140));value=1-(1-value)*edge
  pixels.extend([value,value,value,1]);values.append(value)
 if j%48==0:print('FERN_FLOOR_AO_ROW',j,'seconds',round(time.time()-started,1),flush=True)
image=bpy.data.images.new('T_FernFloor_Contact',width=W,height=H,alpha=True);image.colorspace_settings.name='Non-Color';image.pixels.foreach_set(pixels);image.filepath_raw=str(OUT/'T_FernFloor_Contact.png');image.file_format='PNG';image.save()
# Vertex occlusion gives the small fitted pieces readable depth in diffuse shade.
g.a=[ao(v,Vector((0,0,1)),12) for v in g.v]
ob,_=L.to_object(g,'SM_FernFloor_Litter',L.plant_materials(),[0,1]);L.export(ob,out=OUT)
# Save a compact reproducible asset scene, without duplicating the whole fern stand.
for item in list(bpy.data.objects):
 if item!=ob:bpy.data.objects.remove(item,do_unlink=True)
bpy.ops.wm.save_as_mainfile(filepath=str(OUT/'fern-floor.blend'))
ob.data.calc_loop_triangles();report=dict(counts=counts,triangles=len(ob.data.loop_triangles),vertices=len(ob.data.vertices),ao_resolution=[W,H],ao_min=min(values),ao_mean=sum(values)/len(values),ray_distance_m=1.35,rays_per_texel=24,source_plant_count=len(plants),source_placement_sha256=hashlib.sha256(json.dumps(plants,sort_keys=True).encode()).hexdigest(),ground_mesh_unchanged=True,collision='None on decorative floor layer',world_origin=[S.CX,S.CY,4800],seconds=time.time()-started)
(OUT/'bake.json').write_text(json.dumps(report,indent=2));print('FERN_FLOOR_BAKED',report,flush=True)

