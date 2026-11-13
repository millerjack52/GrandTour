import bpy,sys,json,math,random
from pathlib import Path
from mathutils import Vector
ROOT=Path('C:/GrandTour');sys.path[:0]=[str(ROOT/'Art/Blender'),str(ROOT/'Art/Unreal')]
import native_plant_lib as L
import lidar_section_surface as S
import lidar_bank_relief_detail as D
OUT=ROOT/'Art/Export/LidarStudy/FirstSection';OUT.mkdir(parents=True,exist_ok=True)
grid={(int(x),int(y)):z for x,y,z in json.loads((ROOT/'Saved/LidarAuthoringQA/RS7/dense-ground.json').read_text())['grid']}
def height(x,y):
 ix=math.floor(x/50)*50;iy=math.floor(y/50)*50;fx=(x-ix)/50;fy=(y-iy)/50
 return (grid[ix,iy]*(1-fx)+grid[ix+50,iy]*fx)*(1-fy)+(grid[ix,iy+50]*(1-fx)+grid[ix+50,iy+50]*fx)*fy
def point(a,b):
 x,y=S.xy(a,b);return Vector(((x-S.CX)/100,(y-S.CY)/100,(height(x,y)+S.relief(x,y)-4800)/100))
bpy.ops.object.select_all(action='SELECT');bpy.ops.object.delete(use_global=False)
g=L.Geo();nu,nv=220,156
for i in range(nu+1):
 for j in range(nv+1):
  a=-S.HALF_U+i*10;b=-S.HALF_V+j*10;p=point(a,b)
  r=max(S.rock(a,b),min(1.,D.rock_detail(a,b)/22));m=(.5+.5*math.sin(a*.007+math.sin(b*.009)))*(.68+.32*math.cos(b*.019-a*.003))
  earth=Vector((.105,.078,.038));moss=Vector((.115,.165,.042));stone=Vector((.20,.195,.16))
  col=earth.lerp(moss,max(0,min(.9,m*.95)));col=col.lerp(stone,max(0,min(1,(r-.3)*1.5))*(1-m*.45))
  # Small embedded mineral faces belong to the physical surface, not a colour stamp.
  embedded=D.stone_detail(a,b);extra=D.additional(*S.xy(a,b))
  col=col.lerp(stone*.88,min(1.,embedded/10)*min(1.,extra/10)*.78)
  col*=.92+.08*math.sin(a*.057+b*.063)
  g.v.append(p);g.c.append(tuple(col));g.uv.append((a/200,b/200));g.r.append(Vector((0,0,1)))
# Mild baked geometric cavity colour: paired samples cancel the underlying slope.
# It makes recesses between real ledges readable under the gully's diffuse light.
for i in range(4,nu-3):
 for j in range(4,nv-3):
  n=i*(nv+1)+j;z=g.v[n].z
  around=[g.v[(i+di)*(nv+1)+j+dj].z for di,dj in [(4,0),(-4,0),(0,4),(0,-4),(3,3),(-3,-3),(3,-3),(-3,3)]]
  cavity=max(0.,sum(around)/len(around)-z)
  ao=1-min(.26,cavity*1.6)
  g.c[n]=tuple(c*ao for c in g.c[n])
for i in range(nu):
 for j in range(nv):
  n=i*(nv+1)+j
  g.f.extend([(n,n+1,n+nv+2),(n,n+nv+2,n+nv+1)]);g.mi.extend([0,0])
# Close perimeter below existing landform; no floating sheet edges.
edges=[j for j in range(nv+1)]+[i*(nv+1)+nv for i in range(1,nu+1)]+[nu*(nv+1)+j for j in range(nv-1,-1,-1)]+[i*(nv+1) for i in range(nu-1,0,-1)]
for k,n in enumerate(edges):
 m=edges[(k+1)%len(edges)];a=g.v[n];b=g.v[m]
 g.add([a,b,b-Vector((0,0,.8)),a-Vector((0,0,.8))],[(0,1,2,3)],(.09,.065,.03),None,0)
# Irregular exposed root runs follow the support, with short branching ends.
rng=random.Random(7031)
for k in range(28):
 a=rng.uniform(-980,980);b=rng.uniform(-650,450);length=rng.uniform(80,250)
 pts=[]
 for j in range(9):
  q=point(a+math.sin(j*.5+k)*12,b+j*length/8);q.z+=.015;pts.append(q)
 col=(.095,.075,.035) if k%3 else (.17,.21,.06)
 # A few stronger root runs give an actual raised edge and contact shadow.
 radius=.07 if k%6==0 else .035
 if any((a-aa)**2+(b-bb)**2<90**2 for aa,bb in [(-600,0),(600,0),(0,-500),(0,500),(0,0)]):radius=.025
 L.tube(g,pts,[radius*(1-j/11) for j in range(9)],7 if radius>.05 else 5,col,mi=0,caps=(True,True))
# Legacy FBX converts Blender +Y to Unreal -Y. This mesh encodes a surveyed
# world surface, so pre-reflect Y (and winding) to preserve that registration.
for v in g.v:v.y=-v.y
g.f=[tuple(reversed(f)) for f in g.f]
g.a=[]
for v in g.v:
 a,b=S.uv(S.CX+v.x*100,S.CY-v.y*100)
 g.a.append(max(0.,min(1.,(S.HALF_U-abs(a)-25)/150,(S.HALF_V-abs(b)-25)/150)))
mats=L.plant_materials();ob,_=L.to_object(g,'SM_RS7_BankSkin_LOD0',mats,[0])
bpy.context.view_layer.objects.active=ob;ob.select_set(True)
bpy.ops.object.shade_smooth_by_angle(angle=math.radians(38),keep_sharp_edges=True)
L.export(ob,out=OUT)
bpy.ops.wm.save_as_mainfile(filepath=str(OUT/'bank-surface.blend'))
print('RS7_SURFACE_BUILT',len(g.f))
