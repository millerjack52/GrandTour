import bpy,bmesh,json,math
from pathlib import Path
from mathutils import Vector
P=Path('C:/GrandTour/Art/Export/VehicleTools/prado-source-v01')
bpy.ops.wm.open_mainfile(filepath=str(P/'Prado_Normal_Diagnostic.blend'))
o=bpy.data.objects['Prado Tripo source'];o.hide_render=True
a=json.loads((P/'islands.json').read_text())[0]
me=bpy.data.meshes.new('body');me.from_pydata(a['verts'],[],a['polys']);bm=bmesh.new();bm.from_mesh(me);bm.normal_update();bm.faces.ensure_lookup_table()
specs=[('Windscreen',Vector((0,-.81,.59)),(-.155,.155),(-.211,-.074),(.306,.418))]
for s in [-1,1]:
 for name,ya,yb in [('FrontDoor',-.184,.039),('RearDoor',.045,.207),('Cargo',.213,.377)]:
  specs.append((name+('_L' if s>0 else '_R'),Vector((s*.978,0,.208)),(.137,.171) if s>0 else (-.171,-.137),(ya,yb),(.308,.418)))
specs.append(('RearWindow',Vector((0,.998,.064)),(-.14,.14),(.347,.372),(.319,.415)))
out={}
for name,n,xr,yr,zr in specs:
 faces=[]
 for f in bm.faces:
  c=f.calc_center_median()
  if xr[0]<c.x<xr[1] and yr[0]<c.y<yr[1] and (zr[0]-.012 if name=='Windscreen' else zr[0])<c.z<zr[1] and f.normal.dot(n.normalized())>(.94 if name=='Windscreen' else .968):
   faces.append(f)
 todo=set(faces);parts=[]
 while todo:
  seed=todo.pop();part={seed};q=[seed]
  while q:
   f=q.pop()
   for e in f.edges:
    for g in e.link_faces:
     if g in todo:todo.remove(g);part.add(g);q.append(g)
  parts.append(part)
 parts.sort(key=lambda p:sum(f.calc_area() for f in p),reverse=True)
 print(name,[(len(p),sum(f.calc_area() for f in p)) for p in parts])
 faces=list(parts[0]) if parts else []
 if name.startswith('Cargo') and len(parts)>1:faces+=list(parts[1])
 fs=set(faces);edges={e for f in faces for e in f.edges if sum(g in fs for g in e.link_faces)==1}
 verts=sorted({v for f in faces for v in f.verts},key=lambda v:v.index);idx={v:i for i,v in enumerate(verts)}
 m=bpy.data.meshes.new(name);m.from_pydata([v.co for v in verts],[],[[idx[v] for v in f.verts] for f in faces]);obj=bpy.data.objects.new(name,m);bpy.context.scene.collection.objects.link(obj);obj.color=(.04,.25,.48,1)
 out[name]={'faces':[f.index for f in faces],'verts':[list(v.co) for v in verts],'boundary':[[list(v.co) for v in e.verts] for e in edges],'area':sum(f.calc_area() for f in faces)}
sel={i for d in out.values() for i in d['faces']}
m=bpy.data.meshes.new('Rest');m.from_pydata(a['verts'],[],[p for i,p in enumerate(a['polys']) if i not in sel]);rest=bpy.data.objects.new('Rest',m);bpy.context.scene.collection.objects.link(rest);rest.color=(.55,.55,.5,1)
for p in m.polygons:p.use_smooth=True
mod=rest.modifiers.new('Weighted','WEIGHTED_NORMAL');mod.keep_sharp=True
(P/'glass-selections.json').write_text(json.dumps(out,indent=2))
sc=bpy.context.scene
for name,c,d,size in [('glass-side',(0,.05,.34),(3,0,0),.85),('glass-quarter',(0,.01,.29),(2,-3,1.6),1.15),('glass-rear',(0,.32,.34),(1,3,1),.55)]:
 center=Vector(c);sc.camera.location=center+Vector(d);sc.camera.rotation_euler=(center-sc.camera.location).to_track_quat('-Z','Y').to_euler();sc.camera.data.ortho_scale=size;sc.render.filepath=str(P/(name+'.png'));bpy.ops.render.render(write_still=True)
print([(n,len(d['faces']),d['area'],len(d['boundary'])) for n,d in out.items()])
