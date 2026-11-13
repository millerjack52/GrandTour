import bpy,bmesh,json,math
from pathlib import Path
from mathutils import Vector
P=Path('C:/GrandTour/Art/Export/VehicleTools/prado-source-v01')
a=json.loads((P/'islands.json').read_text())[0];me=bpy.data.meshes.new('body');me.from_pydata(a['verts'],[],a['polys']);bm=bmesh.new();bm.from_mesh(me);bm.normal_update();bm.faces.ensure_lookup_table();todo=set(bm.faces);groups=[]
while todo:
 seed=todo.pop();group={seed};q=[seed]
 while q:
  f=q.pop()
  for e in f.edges:
   for n in e.link_faces:
    if n in todo and n.normal.dot(seed.normal)>.985 and abs((n.calc_center_median()-seed.calc_center_median()).dot(seed.normal))<.002:
     todo.remove(n);group.add(n);q.append(n)
 area=sum(f.calc_area() for f in group)
 if area<.002:continue
 verts={v for f in group for v in f.verts};cent=sum((f.calc_center_median()*f.calc_area() for f in group),Vector())/area
 groups.append({'area':area,'normal':list(seed.normal),'center':list(cent),'bounds':[[min(v.co[k] for v in verts),max(v.co[k] for v in verts)] for k in range(3)],'faces':[f.index for f in group]})
groups.sort(key=lambda g:-g['area']);(P/'panel-groups.json').write_text(json.dumps(groups,indent=2));print(json.dumps([{k:v for k,v in g.items() if k!='faces'} for g in groups[:45]],indent=2))
