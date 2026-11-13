import bpy,bmesh,json,math,colorsys
from pathlib import Path
from mathutils import Vector
P=Path('C:/GrandTour/Art/Export/VehicleTools/ferrari288-source-v01')
A=json.loads((P/'islands.json').read_text())
src=Path('C:/GrandTour/Art/VehicleTools/analyse_prado_panels.py').read_text().replace('prado-source-v01','ferrari288-source-v01')
exec(compile(src,'panel-analysis','exec'))
rows=[]
for i,a in enumerate(A):
 lo,hi=Vector(a['min']),Vector(a['max']);rows.append({'id':i,'faces':a['faces'],'center':list((lo+hi)/2),'size':list(hi-lo)})
(P/'component-summary.json').write_text(json.dumps(rows,indent=2))
print('COMPONENTS')
for r in rows:print(r['id'],r['faces'],' C',*[round(x,4) for x in r['center']],' D',*[round(x,4) for x in r['size']])
bpy.ops.wm.read_factory_settings(use_empty=True)
sc=bpy.context.scene;sc.render.engine='BLENDER_WORKBENCH';sc.render.resolution_x=1800;sc.render.resolution_y=1100;sc.render.resolution_percentage=100
sc.world=bpy.data.worlds.new('Survey');sc.world.color=(.11,.12,.14)
sh=sc.display.shading;sh.light='STUDIO';sh.color_type='MATERIAL';sh.show_cavity=True;sh.cavity_type='BOTH';sh.background_type='WORLD'
me=bpy.data.meshes.new('body');me.from_pydata(A[0]['verts'],[],A[0]['polys']);me.update()
body=bpy.data.objects.new('body',me);sc.collection.objects.link(body)
mat=bpy.data.materials.new('base');mat.diffuse_color=(.26,.29,.3,1);me.materials.append(mat)
groups=json.loads((P/'panel-groups.json').read_text())
for i,g in enumerate(groups):
 m=bpy.data.materials.new('Chart '+str(i));m.diffuse_color=(*colorsys.hsv_to_rgb((i*.618)%1,.7,.8),1);me.materials.append(m)
 for f in g['faces']:me.polygons[f].material_index=i+1
bpy.ops.object.camera_add();cam=bpy.context.object;cam.data.type='ORTHO';sc.camera=cam
labels=[]
for i,g in enumerate(groups):
 curve=bpy.data.curves.new(str(i),'FONT');curve.body=str(i);curve.size=.013;curve.align_x='CENTER';curve.align_y='CENTER';curve.extrude=.00015
 obj=bpy.data.objects.new('label '+str(i),curve);sc.collection.objects.link(obj);obj.location=Vector(g['center'])+Vector(g['normal'])*.005
 labels.append(obj)
for name,d in [('charts-side',(3,0,.05)),('charts-opposite',(-3,0,.05)),('charts-front',(0,-3,.3)),('charts-rear',(0,3,.3)),('charts-top',(0,0,3))]:
 c=Vector((0,0,.21));cam.location=c+Vector(d);cam.rotation_euler=(c-cam.location).to_track_quat('-Z','Y').to_euler();cam.data.ortho_scale=1.15
 for ob in labels:ob.rotation_euler=cam.rotation_euler
 sc.render.filepath=str(P/(name+'.png'));bpy.ops.render.render(write_still=True)
