import bpy,bmesh,json,math
from pathlib import Path
from mathutils import Vector
P=Path('C:/GrandTour/Art/Export/VehicleTools/ferrari288-source-v01')
A=json.loads((P/'islands.json').read_text())[0];G=json.loads((P/'panel-groups.json').read_text())
bpy.ops.wm.read_factory_settings(use_empty=True)
me=bpy.data.meshes.new('body');me.from_pydata(A['verts'],[],A['polys']);me.update()
bm=bmesh.new();bm.from_mesh(me);bm.normal_update();bm.faces.ensure_lookup_table()
out={}
for name,seed,normal in [('Windscreen',21,(0,-.5,.866)),('Door left',98,(.84,0,.54)),('Door right',79,(-.84,0,.54)),('Quarter left',198,(.84,.08,.54)),('Quarter right',229,(-.84,.08,.54))]:
 fs={bm.faces[i] for i in G[seed]['faces']};q=list(fs);n=Vector(normal).normalized()
 while q:
  f=q.pop()
  for e in f.edges:
   for other in e.link_faces:
    if other in fs:continue
    c=other.calc_center_median()
    if name=='Windscreen':ok=-.19<c.y<-.018 and .232<c.z<.334 and abs(c.x)<.185 and other.normal.dot(n)>.952
    else:ok=.240<c.z<.320 and -.15<c.y<.215 and abs(other.normal.dot(n))>.50 and abs(c.x)>.14 and other.calc_area()>.000065
    if ok and (name!='Windscreen' or other.normal.dot(f.normal)>.93):fs.add(other);q.append(other)
 es={e for f in fs for e in f.edges if sum(g in fs for g in e.link_faces)==1}
 edges=[[e.verts[0].index,e.verts[1].index] for e in es]
 out[name]={'faces':sorted(f.index for f in fs),'edges':edges}
 print(name,len(fs),'edges',len(es),'bounds',[[min(v.co[k] for e in es for v in e.verts),max(v.co[k] for e in es for v in e.verts)] for k in range(3)])
(P/'glass-selections.json').write_text(json.dumps(out,indent=2))
body=bpy.data.objects.new('body',me);bpy.context.scene.collection.objects.link(body)
for i,col in enumerate([(.68,.64,.51,1),(.07,.24,.32,1),(.06,.32,.26,1),(.06,.32,.26,1),(.07,.24,.32,1),(.07,.24,.32,1)]):
 m=bpy.data.materials.new(str(i));m.diffuse_color=col;me.materials.append(m)
for idx,g in enumerate(out.values()):
 for i in g['faces']:me.polygons[i].material_index=idx+1
for p in me.polygons:p.use_smooth=True
sc=bpy.context.scene;sc.render.engine='BLENDER_WORKBENCH';sc.render.resolution_x=1500;sc.render.resolution_y=1000
sc.world=bpy.data.worlds.new('world');sc.world.color=(.10,.12,.14)
sh=sc.display.shading;sh.color_type='MATERIAL';sh.light='STUDIO';sh.show_cavity=True;sh.background_type='WORLD'
bpy.ops.object.camera_add();cam=bpy.context.object;sc.camera=cam;cam.data.type='ORTHO'
for name,d in [('glass-quarter',(2,-3,1.2)),('glass-side',(3,0,0)),('glass-opposite',(-3,0,0))]:
 c=Vector((0,0,.23));cam.location=c+Vector(d);cam.rotation_euler=(c-cam.location).to_track_quat('-Z','Y').to_euler();cam.data.ortho_scale=1.05;sc.render.filepath=str(P/(name+'.png'));bpy.ops.render.render(write_still=True)
