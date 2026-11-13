"""Three small reusable moss/root/litter stamps, fitted at runtime with a shear."""
import bpy,sys,math,random
from pathlib import Path
ROOT=Path('C:/GrandTour');sys.path.insert(0,str(ROOT/'Art/Blender'))
import native_plant_lib as L
OUT=ROOT/'Art/Export/LidarStudy/Place/ForestGround';OUT.mkdir(parents=True,exist_ok=True)
bpy.ops.object.select_all(action='SELECT');bpy.ops.object.delete(use_global=False)
for kind in range(3):
 rng=random.Random(881+kind);g=L.Geo();phase=kind*1.7;vs=[];cols=[]
 for ring,r in enumerate([1.,.80,.46,.08]):
  for j in range(16):
   t=j*math.tau/16;shape=1+.26*math.sin(3*t+phase)+.16*math.cos(5*t-phase)
   # Blender Y is opposite Unreal Y, preserving the authored mask's outline.
   vs.append((math.cos(t)*.5*shape*r,-math.sin(t)*.5*shape*r,.055*max(0,1-r*r)**.62-.006))
   shade=[.80,.95,1.,1.03][ring]*(.95+.10*math.sin(t*3+phase))
   cols.append(tuple(v*shade for v in (.105,.137,.030)))
 faces=[]
 for ring in range(3):
  for j in range(16):
   k=ring*16+j;kn=ring*16+(j+1)%16;faces.append((k,k+16,kn+16,kn))
 faces.append(tuple(48+j for j in reversed(range(16))))
 g.add(vs,faces,cols,None,0)
 for k in range(2):
  angle=rng.random()*math.tau;points=[]
  for j in range(7):
   d=-.6+j*.17;points.append((math.cos(angle)*d+math.sin(j*.8)*.05,math.sin(angle)*d,.005+.009*math.sin(j*.6)))
  L.tube(g,points,[.014*(1-j*.08) for j in range(7)],5,(.115,.077,.038),mi=0,caps=(True,True))
 for k in range(8):
  x,y=rng.uniform(-.55,.55),rng.uniform(-.55,.55);r=rng.uniform(.012,.025)
  g.add([(x-r,y,.002),(x,y-r*.6,.004),(x+r,y,.008),(x,y+r*.6,.004)],[(0,1,2),(0,2,3)],(.15,.095,.044),None,0)
 g.uv=[(v.x,v.y) for v in g.v];g.a=[.8 if v.z<.01 else .95 for v in g.v]
 ob,_=L.to_object(g,f'SM_FG_Stamp_{kind}',L.plant_materials(),[0]);L.export(ob,out=OUT)
 for lod,ratio in [(1,.48),(2,.2)]:
  copy=ob.copy();copy.data=ob.data.copy();bpy.context.collection.objects.link(copy);copy.name=f'SM_FG_Stamp_{kind}_LOD{lod}';bpy.context.view_layer.objects.active=copy
  mod=copy.modifiers.new('Distance','DECIMATE');mod.ratio=ratio;bpy.ops.object.modifier_apply(modifier=mod.name);L.export(copy,out=OUT);bpy.data.objects.remove(copy,do_unlink=True)
bpy.ops.wm.save_as_mainfile(filepath=str(OUT/'forest-ground-stamps.blend'))
