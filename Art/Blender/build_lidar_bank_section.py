"""RS7 map-owned bank plants. +X faces out of bank; Z follows gravity.

The same seeded frond skeleton survives all LODs. No horizontal floor clamp.
The live site sampler selects placement and tests representative frond clearance.
"""
import bpy, sys, math, random, json
from pathlib import Path
from mathutils import Vector
sys.path.insert(0,str(Path(__file__).resolve().parent))
import native_plant_lib as L
OUT=Path('C:/GrandTour/Art/Export/LidarStudy/FirstSection');OUT.mkdir(parents=True,exist_ok=True)
bpy.ops.object.select_all(action='SELECT');bpy.ops.object.delete(use_global=False)
mats=L.plant_materials();manifest=[]

def design(kind,variant):
 r=random.Random(7100+variant*173+kind*941);fs=[]
 # Mature outward sprays, shorter upright central fronds, a few senescent fronds.
 for i in range((13,17,10,12)[kind]):
  role='outer' if i< (8,10,6,7)[kind] else 'young'
  az=r.uniform(-1.40,1.40) if role=='outer' else r.uniform(-2.3,2.3)
  length=r.uniform(1.35,2.15) if role=='outer' else r.uniform(.65,1.18)
  if kind==2:length*=.55
  if kind==3:length*=.83
  el=r.uniform(.64,1.0) if role=='outer' else r.uniform(1.15,1.46)
  droop=r.uniform(2.35,2.75) if role=='outer' else r.uniform(.55,1.05)
  if kind==1:
   length*=1.15;el+=.13;droop-=.12
  if kind==3:
   az=r.uniform(-2.0,2.0);el=r.uniform(1.0,1.25) if role=='outer' else r.uniform(1.3,1.5)
   droop=r.uniform(1.45,1.85) if role=='outer' else r.uniform(.35,.65)
  col=((.16,.30,.055),(.10,.225,.105),(.23,.30,.075),(.13,.25,.065))[(variant+kind)%4]
  if role=='young':col=(.20,.31,.075) if i%3 else (.27,.35,.09)
  if i in (1,6) and variant%2:col=(.22,.12,.045)
  col=tuple(c*r.uniform(.9,1.08) for c in col)
  fs.append(dict(az=az,length=length,el=el,droop=droop,col=col,width=r.uniform(.16,.25)*( .65 if kind==2 else 1),roll=r.uniform(-.36,.36),curl=r.uniform(-.07,.07),role=role))
 return fs

def build(fs,kind,lod):
 g=L.Geo();probes=[]
 L.tube(g,[(0,0,-.16),(.015,0,-.02),(.035,0,.07)],[.08,.065,.03],7,(.085,.065,.028),mi=0,caps=(True,True))
 for f in fs:
  az=f['az'];d=Vector((math.cos(az)*math.cos(f['el']),math.sin(az)*math.cos(f['el']),math.sin(f['el'])))
  pts,tans,sides,ups=L.frond_path(Vector((.025,0,.065)),d,f['length'],f['droop'],16,1.15,f['curl'],f['roll'],None)
  probes.extend([list(p) for p in pts[2::3]])
  L.tube(g,pts,[.007*(1-j/20) for j in range(17)],3,tuple(c*.65 for c in f['col']),mi=1)
  # Longitudinal folds and a raised midrib give each pinna actual volume.
  pairs=(30,20,12)[lod] if kind!=1 else (38,24,14)[lod]
  for j in range(pairs):
   t=.12+.86*(j+.5)/pairs;seg=min(15,int(t*16));v=t*16-seg
   p=pts[seg].lerp(pts[seg+1],v);T=tans[seg].lerp(tans[seg+1],v).normalized();S=sides[seg];U=ups[seg]
   width=f['width']*math.sin(math.pi*(t-.04))**.68
   thick=f['length']*.84/pairs*.40
   for sign in [-1,1]:
    a=p+T*(.012 if sign<0 else 0);tip=a+S*sign*width+T*width*.35-U*width*.14
    mid=a.lerp(tip,.48)+U*width*.13
    vs=[a-T*thick,mid-T*thick*.77,tip,mid+T*thick*.77,a+T*thick,mid+U*width*.075]
    g.add(vs,[(0,1,5),(1,2,5),(2,3,5),(3,4,5),(4,0,5)],f['col'],[(0,0)]*6,1)
    if kind==1 and lod==0:
     # Fine secondary divisions distinguish the delicate form from broad kiokio.
     for k in range(1,4):
      q=a.lerp(tip,k/4)
      L.leaf(g,q,T+S*sign*.35,width*.32,f['col'],broad=.23,roll=sign*.2,mi=1)
 g.a=[max(0.,min(1.,(math.hypot(v.x,v.y)-.12)/1.2)) for v in g.v]
 return g,probes

for kind,label in enumerate(['Cascade','Fine','Crevice','Crown']):
 for variant in range(3):
  fs=design(kind,variant);name='SM_RS7_'+label+'_'+str(variant)
  row={'asset':name,'kind':label,'variant':variant,'lods':[]}
  for lod in range(3):
   g,probes=build(fs,kind,lod)
   ob,_=L.to_object(g,name+'_LOD'+str(lod),mats,[0,1]);L.export(ob,out=OUT)
   ob.data.calc_loop_triangles()
   row['lods'].append({'triangles':len(ob.data.loop_triangles),'min_z':min(v.z for v in g.v),'max_z':max(v.z for v in g.v)})
   if lod==0:row['probes']=probes
   ob.hide_render=True;ob.hide_set(True)
  manifest.append(row)
bpy.ops.wm.save_as_mainfile(filepath=str(OUT/'bank-plants.blend'))
(OUT/'plants.json').write_text(json.dumps(manifest,indent=2))
print('RS7_PLANTS_BUILT',len(manifest))
