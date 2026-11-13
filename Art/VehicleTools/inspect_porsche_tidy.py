import bpy,bmesh,json,math
from pathlib import Path
from mathutils import Vector
O=Path('C:/GrandTour/Art/Export/VehicleTools/porsche-tidy-v03');O.mkdir(exist_ok=True)
bpy.ops.wm.open_mainfile(filepath='C:/GrandTour/Art/Export/VehicleTools/porsche-preserved-repair-v02/Porsche_Preserved_Repair.blend');s=bpy.context.scene
b=bpy.data.objects['Porsche original body - locally repaired'];bm=bmesh.new();bm.from_mesh(b.data)
edges={e for e in bm.edges if e.is_boundary};groups=[]
while edges:
 e=edges.pop();ee={e};vv=set(e.verts);stack=list(e.verts)
 while stack:
  v=stack.pop()
  for x in v.link_edges:
   if x in edges:edges.remove(x);ee.add(x);vv.update(x.verts);stack.extend(x.verts)
 groups.append({'edges':len(ee),'bounds':[[min(v.co[k] for v in vv) for k in range(3)],[max(v.co[k] for v in vv) for k in range(3)]],'simple':all(sum(v in e.verts for e in ee)==2 for v in vv)})
(O/'boundary-baseline.json').write_text(json.dumps(groups,indent=2))
for o in bpy.data.collections['Porsche - repaired original components'].objects:
 if o.name.startswith('Wheel_'):o.hide_render=True
s.render.resolution_x=1500;s.render.resolution_y=1100
for name,pos,target,scale in [('windows-before',(5,-2,2.5),(.65,.15,1.23),2.8),('arch-before',(5,-2,1.1),(.75,-1.25,.65),1.6),('underside-before',(4,-5,-3),(0,0,.5),5.5)]:
 c=s.camera;c.location=pos;c.rotation_euler=(Vector(target)-c.location).to_track_quat('-Z','Y').to_euler();c.data.ortho_scale=scale;s.render.filepath=str(O/(name+'.png'));bpy.ops.render.render(write_still=True)
for name in ['Windscreen','Door glass L','Quarter glass L']:
 o=bpy.data.objects[name];N=len(o.data.vertices)//2;ec={}
 for f in o.data.polygons:
  if all(k<N for k in f.vertices):
   ids=list(f.vertices)
   for a,b in zip(ids,ids[1:]+ids[:1]):key=tuple(sorted((a,b)));ec[key]=ec.get(key,0)+1
 print('GLASS',name,len(o.data.vertices),sum(v==1 for v in ec.values()))
