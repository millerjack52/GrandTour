import bpy,bmesh,json
from pathlib import Path
from mathutils import Vector
O=Path('C:/GrandTour/Art/Export/VehicleTools/porsche-completion-v04');O.mkdir(exist_ok=True)
bpy.ops.wm.open_mainfile(filepath='C:/GrandTour/Art/Export/VehicleTools/porsche-tidy-v03/Porsche_Tidy.blend')
s=bpy.context.scene;parts=bpy.data.collections['Porsche - repaired original components'];body=bpy.data.objects['Porsche original body - locally repaired']
def bounds(o):
 p=[o.matrix_world@v.co for v in o.data.vertices];return [[min(v[k] for v in p) for k in range(3)],[max(v[k] for v in p) for k in range(3)]]
out={'objects':[{'name':o.name,'island':o.get('source_island'),'bounds':bounds(o)} for o in parts.objects if o.type=='MESH'],'boundary_components':[]}
bm=bmesh.new();bm.from_mesh(body.data);es={e for e in bm.edges if e.is_boundary}
while es:
 e=es.pop();group={e};todo=[e]
 while todo:
  e=todo.pop()
  for v in e.verts:
   for ee in v.link_edges:
    if ee in es:es.remove(ee);group.add(ee);todo.append(ee)
 vs=list({v for e in group for v in e.verts});out['boundary_components'].append({'edges':len(group),'length':sum(e.calc_length() for e in group),'lo':[min(v.co[k] for v in vs) for k in range(3)],'hi':[max(v.co[k] for v in vs) for k in range(3)]})
bm.free();(O/'before-inspection.json').write_text(json.dumps(out,indent=2))
def render(name,pos,target,scale):
 c=s.camera;c.location=pos;c.rotation_euler=(Vector(target)-c.location).to_track_quat('-Z','Y').to_euler();c.data.ortho_scale=scale;s.render.filepath=str(O/(name+'.png'));bpy.ops.render.render(write_still=True)
s.render.resolution_x=1400;s.render.resolution_y=1000
render('front-detail-before',(3,-4,1.65),(.45,-1.78,.72),1.9)
render('rear-detail-before',(3,4,1.7),(0,1.68,.8),2.8)
for o in parts.objects:
 if o.type=='MESH':
  lo,hi=bounds(o)
  if o==body or lo[2]>1.5 or 'glass' in o.name.lower() or 'surround' in o.name.lower() or o.name=='Windscreen':o.hide_render=True
render('interior-before',(3,2,3),(0,.1,.8),2.6)
