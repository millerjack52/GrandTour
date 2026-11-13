import bpy,bmesh,json
from pathlib import Path
from mathutils import Vector
P=Path('C:/GrandTour/Art/Export/VehicleTools/porsche-source-v01')
bpy.ops.wm.open_mainfile(filepath=str(P/'Porsche_Analysed.blend'))
o=next(o for o in bpy.context.scene.objects if o.type=='MESH');bm=bmesh.new();bm.from_mesh(o.data);il=bm.faces.layers.int.get('source_island')
report=[]
for i in range(112):
 fs=[f for f in bm.faces if f[il]==i];es={e for f in fs for e in f.edges};bound=[e for e in es if e.is_boundary];over=[e for e in es if len(e.link_faces)>2]
 if not bound and not over:continue
 report.append({'part':i,'boundary':len(bound),'overconnected':len(over)})
print('TOPOLOGY',json.dumps(report))
fs=[f for f in bm.faces if f[il]==0];edges={e for f in fs for e in f.edges if e.is_boundary};components=[]
while edges:
 seed=edges.pop();seen={seed};vs=set(seed.verts);q=list(seed.verts)
 while q:
  v=q.pop()
  for e in v.link_edges:
   if e in edges:edges.remove(e);seen.add(e);vs.update(e.verts);q.extend(e.verts)
 components.append({'n':len(seen),'min':[min(v.co[k] for v in vs) for k in range(3)],'max':[max(v.co[k] for v in vs) for k in range(3)],'verts':[list(v.co) for v in vs]})
(P/'body-boundaries.json').write_text(json.dumps(components,indent=2))
print('BODY_BOUNDARIES',json.dumps([{k:v for k,v in x.items() if k!='verts'} for x in components]))
for label,pred in [('wind',lambda x,y,z: abs(x)<.14 and -.19<y<-.035 and .246<z<.325),('rear',lambda x,y,z: abs(x)<.12 and .20<y<.38 and .24<z<.32)]:
 data=[]
 for f in fs:
  p=f.calc_center_median()
  if pred(*p):data.append({'p':list(p),'n':list(f.normal),'verts':[list(v.co) for v in f.verts]})
 (P/(label+'-faces.json')).write_text(json.dumps(data))
 print(label,len(data))
