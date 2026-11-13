import bpy,bmesh,json,math
from pathlib import Path
from mathutils import Vector
P=Path('C:/GrandTour/Art/Export/VehicleTools/prado-source-v01');O=P.parent/'prado-glazing-audit'
A=json.loads((P/'islands.json').read_text())[0];d=json.loads((O/'adjacent-loops.json').read_text())['Windscreen']
bpy.ops.wm.read_factory_settings(use_empty=True);sc=bpy.context.scene
me=bpy.data.meshes.new('Source wind bands');me.from_pydata([Vector(p)*5 for p in A['verts']],[],A['polys']);me.update();ob=bpy.data.objects.new('Source wind bands',me);sc.collection.objects.link(ob)
for n,c in [('body',(.5,.5,.5)),('pane',(.03,.3,.65)),('depth1',(1,.42,.03)),('depth2',(.8,.04,.035)),('depth3',(.8,.75,.01))]:
 m=bpy.data.materials.new(n);m.diffuse_color=(*c,1);me.materials.append(m)
sets=[set(row['faces']) for row in d]
for f in me.polygons:f.material_index=next((i+1 for i,s in enumerate(sets) if f.index in s),0)
sc.render.engine='BLENDER_WORKBENCH';sc.display.shading.light='STUDIO';sc.display.shading.color_type='MATERIAL';sc.display.shading.show_shadows=False;sc.display.shading.show_cavity=True;sc.display.shading.cavity_type='BOTH';sc.display.shading.show_object_outline=True
sc.render.resolution_x=1600;sc.render.resolution_y=1000;sc.render.resolution_percentage=100
cam=bpy.data.objects.new('Cam',bpy.data.cameras.new('Cam'));sc.collection.objects.link(cam);sc.camera=cam;cam.data.type='ORTHO'
for name,c,d,sz in [('wind-bands-front',(0,-.13,.36),(0,-3,0),.43),('wind-bands-quarter',(0,-.13,.36),(-2,-3,.5),.48),('wind-bands-top',(0,-.13,.36),(0,-2,3),.43)]:
 center=Vector(c)*5;cam.location=center+Vector(d)*5;cam.rotation_euler=(center-cam.location).to_track_quat('-Z','Y').to_euler();cam.data.ortho_scale=sz*5;sc.render.filepath=str(O/(name+'.png'));bpy.ops.render.render(write_still=True)
print('DONE')
