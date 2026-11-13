import bpy
from pathlib import Path
from mathutils import Vector
O=Path('C:/GrandTour/Art/Export/VehicleTools/porsche-window-repair-v05');bpy.ops.wm.open_mainfile(filepath=str(O/'Porsche_Window_Repair.blend'));s=bpy.context.scene;c=s.camera
def render(n,p,t,z,ortho=True):
 c.data.type='ORTHO' if ortho else 'PERSP';c.data.lens=24;c.location=p;c.rotation_euler=(Vector(t)-c.location).to_track_quat('-Z','Y').to_euler();c.data.ortho_scale=z;s.render.filepath=str(O/(n+'.png'));bpy.ops.render.render(write_still=True)
s.render.engine='BLENDER_WORKBENCH';s.render.resolution_x=1600;s.render.resolution_y=1100;s.render.resolution_percentage=100
render('front-header',(0,-5,2),(0,-.3,1.4),1.85)
render('cowl-low',(3,-4,1.1),(.55,-.55,1.12),1.15)
render('rear-header',(0,5,2),(0,1.25,1.35),1.85)
render('front',(0,-8,1),(0,0,1),3.0)
render('top',(0,0,8),(0,0,0),5.3)
s.render.engine='CYCLES';s.cycles.samples=32;s.cycles.use_denoising=True;s.cycles.max_bounces=10;s.cycles.transmission_bounces=8;s.render.resolution_x=1400;s.render.resolution_y=1000
render('beauty',(4.7,-7,3.4),(0,0,.9),5.5)
render('cabin-closeup',(4,-3,2.4),(.68,.05,1.25),2.0)
for o in bpy.data.collections['08 Studio'].objects:
 if o.type=='LIGHT':o.data.energy*=.3
d=bpy.data.lights.new('Cabin review fill','AREA');d.energy=22;d.size=.65;o=bpy.data.objects.new('Cabin review fill',d);s.collection.objects.link(o);o.location=(0,.22,1.38);o.rotation_euler=(Vector((0,-.25,.7))-o.location).to_track_quat('-Z','Y').to_euler()
render('driver-view',(.395,.15,1.25),(.18,-.50,.985),1.5,False)
