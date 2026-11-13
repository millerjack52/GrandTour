import bpy,sys,json,math
from pathlib import Path
from mathutils import Vector
out=Path(sys.argv[sys.argv.index('--')+1]);bpy.ops.wm.open_mainfile(filepath=str(out/'Impreza_Gravel.blend'));sc=bpy.context.scene;r=bpy.data.objects['GT | Impreza controls'];props=['L_front_door','R_front_door','L_rear_door','R_rear_door','steer','roll'];sc.cycles.samples=32
def pose(**values):
 for p in props:r[p]=float(values.get(p,0))
 r.update_tag();sc.frame_set(1);bpy.context.view_layer.update()
def render(key,cam):
 sc.camera=bpy.data.objects[cam];sc.render.resolution_x,sc.render.resolution_y=sc.camera['resolution'];sc.render.filepath=str(out/(key+'.png'));bpy.ops.render.render(write_still=True)
if '--only-cockpit' not in sys.argv:
 for key,cam in [('quarter','Review | front quarter'),('rear-quarter','Review | rear quarter'),('front','Review | front'),('side','Review | side'),('rear','Review | rear'),('top','Review | top')]:pose();render(key,cam)
 pose(L_front_door=50,R_front_door=50,L_rear_door=50,R_rear_door=50);sc.camera=bpy.data.objects['Review | front quarter'];sc.camera.data.ortho_scale=5.85;render('doors-open','Review | front quarter')
 render('doors-open-rear','Review | rear quarter')
 pose(steer=25);render('steering','Review | front quarter')
 pose();bpy.data.objects['Studio ground'].hide_render=True;render('underside','Review | underside');bpy.data.objects['Studio ground'].hide_render=False
# Diagnostic cabin cutaway: only roof/upper glazing removed, fixed body remains.
hidden=[]
for o in sc.objects:
 if o.name.startswith(('Roof |','Windscreen |','Rear screen |','Cabin | sunvisor')) or any(term in o.name for term in ['| window pane','| window frame','| window gasket','| inner glass reveal','lower window corner seal','B pillar seam backing']):
  if not o.hide_render:hidden.append(o);o.hide_render=True
pose(L_front_door=45,R_front_door=45,L_rear_door=45,R_rear_door=45)
d=bpy.data.cameras.new('Review | cockpit');cam=bpy.data.objects.new('Review | cockpit',d);sc.collection.objects.link(cam);cam.location=(2.7,3.8,4.5);cam.rotation_euler=(Vector((0,.13,.81))-cam.location).to_track_quat('-Z','Y').to_euler();d.type='ORTHO';d.ortho_scale=3.65;cam['resolution']=(1200,1050);render('cockpit-cutaway',cam.name)
for o in hidden:o.hide_render=False
pose()
# Source manual scene remains unchanged on disk.
print('REVIEW_RENDERED',flush=True)
