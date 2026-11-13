import bpy,math,json
from pathlib import Path
from mathutils import Vector
P=Path('C:/GrandTour/Art/Export/VehicleTools/porsche-cleanup-v01');OUT=Path('C:/GrandTour/Art/Export/VehicleTools/porsche-working-v01');OUT.mkdir(exist_ok=True)
bpy.ops.wm.open_mainfile(filepath=str(P/'Porsche_Assembly.blend'))
parts=bpy.data.collections['Porsche - separated assembly'];sc=bpy.context.scene
for o in parts.objects:
 if o.name.startswith('Wheel_') and o.name.endswith('_Tread'):
  for v in o.data.vertices:
   r=math.hypot(v.co.y,v.co.z)
   if r>.0835*4.5:
    new=.0835*4.5+(r-.0835*4.5)*.55;v.co.y*=new/r;v.co.z*=new/r
notes='''PORSCHE WORKING CLEANUP — NOT GAME READY

Original source preserved: C:/Users/mille/Downloads/porshceoffroadtripo.glb

Completed: source inspection, UV-preserving separation, overlap-sliver cleanup,
small-loop repair, round replacement tyres, vented steel rims, lugs and tread,
four axle pivots, packed source textures, metre scale and GLB export.

The body retains source topology. Body panels are not individually articulated.
Windscreen, rear and quarter glazing still have the donor's opaque baked appearance.
The source cockpit is separated but not a finished interior. No Unreal setup yet.

Do not promote the porsche-work-v01/v02/v03/v04, cleanup-v02, review-v01,
or prepared-v01 experiments: those body/glass studies failed visual review.
Whole-body voxel processing erased thin features; shrinkwrapping both sides of
thin sheets introduced local folds. A successful QuadriFlow result is not proof
of good panel interfaces or preserved silhouette/detail.

Next body work must isolate deliberate exterior patches, lock their mating
boundaries and compare in clay. Retain the present donor fit and wheel datums.
Do not solve glass with a broad spatial face mask: it catches roof/frame faces
and leaves opaque fragments. Trace actual pane boundaries and rebuild the panes.

Required before game readiness: body/window/arch finishing, fitted clear panes,
cockpit finishing, steering/suspension clearance, collision, LOD and Unreal tests.
'''
(OUT/'READ_ME.txt').write_text(notes,encoding='utf-8');text=bpy.data.texts.new('READ ME - WORKING STATUS');text.write(notes)
sc.render.engine='CYCLES';sc.cycles.samples=32;cam=sc.camera;cam.data.ortho_scale=5.8
for name,pos in [('quarter',(5.4,-7.2,4.5)),('side',(5.4,0,.95)),('rear',(5,7,3.6))]:
 cam.location=pos;cam.rotation_euler=(Vector((0,0,.85))-cam.location).to_track_quat('-Z','Y').to_euler();sc.render.filepath=str(OUT/(name+'.png'));bpy.ops.render.render(write_still=True)
cam.location=(5.4,-7.2,4.5);cam.rotation_euler=(Vector((0,0,.85))-cam.location).to_track_quat('-Z','Y').to_euler()
bpy.ops.wm.save_as_mainfile(filepath=str(OUT/'Porsche_Assembly.blend'))
for o in sc.objects:o.select_set(False)
for o in parts.objects:o.select_set(True)
bpy.ops.export_scene.gltf(filepath=str(OUT/'Porsche_Assembly.glb'),export_format='GLB',use_selection=True,export_apply=True)
