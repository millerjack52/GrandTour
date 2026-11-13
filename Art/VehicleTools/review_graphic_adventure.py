import bpy
from mathutils import Vector
from pathlib import Path
P=Path('C:/GrandTour/Art/Export/VehicleTools/graphic-adventure-assembly-v01')
bpy.ops.wm.open_mainfile(filepath=str(P/'GraphicAdventure_Assembly.blend'))
sc=bpy.context.scene;cam=sc.camera
sc.render.resolution_x=1600;sc.render.resolution_y=1200
def render(name,pos,target,scale):
 cam.location=Vector(pos)*4.6;cam.rotation_euler=(Vector(target)*4.6-cam.location).to_track_quat('-Z','Y').to_euler();cam.data.ortho_scale=scale;sc.render.filepath=str(P/(name+'.png'));bpy.ops.render.render(write_still=True)
render('review-bonnet',(1,-.8,.48),(0,-.27,.29),2.8)
render('review-rear-corner',(.9,.95,.14),(.15,.39,.32),2.2)
render('review-roof-seams',(1,-.2,.48),(0,.15,.43),2.8)
render('review-wheel',(1,-.6,.12),(.19,-.31,.10),1.4)
render('review-rear-low',(.7,1,-.12),(0,.30,.16),3.7)
render('review-bottom',(0,0,-2),(0,0,.15),5.0)
for o in bpy.data.collections['Wheels'].objects:o.hide_render=True
render('review-wheelhouse',(1,-.48,.17),(.17,-.31,.19),1.7)
for o in bpy.data.collections['Wheels'].objects:o.hide_render=False
wiremat=bpy.data.materials.new('Diagnostic topology wire');wiremat.diffuse_color=(.008,.009,.010,1)
wirestate=[]
for o in bpy.context.scene.objects:
 if o.type=='MESH' and o.name.startswith('RET |'):
  saved=[(m,m.show_render) for m in o.modifiers]
  for m,state in saved:m.show_render=False
  o.data.materials.append(wiremat);mod=o.modifiers.new('DIAGNOSTIC wire','WIREFRAME');mod.thickness=.0015;mod.use_replace=False;mod.material_offset=len(o.data.materials)-1
  wirestate.append((o,mod,saved))
sc.display.shading.show_cavity=False
render('review-wire',(1,-1,.60),(0,0,.28),6.4)
# Leave the saved assembly in the normal review view, with helpers hidden.
for o,mod,saved in wirestate:
 o.modifiers.remove(mod);o.data.materials.pop(index=len(o.data.materials)-1)
 for m,state in saved:m.show_render=state
bpy.data.materials.remove(wiremat)
sc.display.shading.show_cavity=True
cam.location=(7,-9,4);cam.rotation_euler=(Vector((0,0,1.25))-cam.location).to_track_quat('-Z','Y').to_euler();cam.data.ortho_scale=6.7
for screen in bpy.data.screens:
 for a in screen.areas:
  if a.type=='VIEW_3D':
   a.spaces.active.region_3d.view_rotation=cam.rotation_euler.to_quaternion();a.spaces.active.region_3d.view_distance=7.0;a.spaces.active.region_3d.view_location=(0,0,1.25)
   a.spaces.active.shading.color_type='MATERIAL';a.spaces.active.overlay.show_extras=False
bpy.ops.wm.save_as_mainfile(filepath=str(P/'GraphicAdventure_Assembly.blend'))
