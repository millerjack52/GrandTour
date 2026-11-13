import bpy,sys
from pathlib import Path
from mathutils import Vector
P=Path('C:/GrandTour/Art/Export/VehicleTools/panda-interior-v01');S=3.6
bpy.ops.wm.open_mainfile(filepath=str(P/'Panda_Assembly.blend'));sc=bpy.context.scene
sc.render.engine='CYCLES';sc.cycles.samples=16;sc.cycles.use_denoising=True;sc.render.threads_mode='FIXED';sc.render.threads=10
sc.render.resolution_x=1200;sc.render.resolution_y=860;sc.render.resolution_percentage=100
sc.world.use_nodes=True;sc.world.node_tree.nodes['Background'].inputs[0].default_value=(.55,.6,.68,1);sc.world.node_tree.nodes['Background'].inputs[1].default_value=.4
for name,p,e,size in [('Key',(3,-4,6),1300,4),('Fill',(-3,0,4),850,3),('Back',(1,4,5),1200,3),('Cabin',(0,.35,1.54),18,1.0)]:
 d=bpy.data.lights.new('Review '+name,'AREA');d.energy=e;d.shape='DISK';d.size=size;o=bpy.data.objects.new(d.name,d);sc.collection.objects.link(o);o.location=p;o.rotation_euler=(Vector((0,0,.7))-o.location).to_track_quat('-Z','Y').to_euler()
cam=sc.camera;cam.data.clip_start=.008
def render(name,p,target,ortho=None,lens=23):
 cam.location=Vector(p)*S;cam.rotation_euler=(Vector(target)*S-cam.location).to_track_quat('-Z','Y').to_euler();cam.data.type='ORTHO' if ortho else 'PERSP';cam.data.lens=lens
 if ortho:cam.data.ortho_scale=ortho*S
 sc.render.filepath=str(P/(name+'.png'));bpy.ops.render.render(write_still=True)
render('driver',(.096,.054,.410),(.061,-.130,.310),lens=22)
render('dashboard',(-.018,.11,.406),(.012,-.134,.312),lens=24)
render('rear-cabin',(0,.107,.417),(0,.295,.29),lens=22)
if '--quick' in sys.argv:raise SystemExit(0)
render('exterior',(1.7,-2.7,1.30),(0,0,.26),ortho=1.3)
for c in ['Body','Doors','Bonnet','Tailgate','Glazing','Roof and snorkel','Front equipment']:bpy.data.collections[c].hide_render=True
for o in sc.objects:
 if o.get('panda_cabin') and any(k in o.name for k in ['Headlining','Sun visor','Visor hinge','Visor roof mount','Dome light','Grab handle','Rearview mirror','pillar lining','upper belt guide','parked front belt','belt tongue','rear belt upper bracket']):o.hide_render=True
render('interior-cutaway',(1.0,-1.0,1.1),(0,.12,.26),ortho=.9)
render('seating',(.60,-.26,.69),(0,.16,.28),ortho=.68)
render('door-card',(-.08,.08,.34),(.20,-.025,.235),lens=24)
print('REVIEW_COMPLETE',flush=True)
