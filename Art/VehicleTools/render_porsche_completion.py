import bpy,sys
from pathlib import Path
from mathutils import Vector
O=Path('C:/GrandTour/Art/Export/VehicleTools/porsche-completion-v04');bpy.ops.wm.open_mainfile(filepath=str(O/'Porsche_Safari_Review.blend'));s=bpy.context.scene;c=s.camera;s.render.engine='CYCLES';s.cycles.samples=40;s.cycles.use_denoising=True;s.cycles.max_bounces=10;s.cycles.transmission_bounces=8;s.render.resolution_x=1500;s.render.resolution_y=1050;s.render.resolution_percentage=100
def render(n,p,target,scale,ortho=True):
 c.data.type='ORTHO' if ortho else 'PERSP';c.data.lens=24;c.location=p;c.rotation_euler=(Vector(target)-c.location).to_track_quat('-Z','Y').to_euler();c.data.ortho_scale=scale;s.render.filepath=str(O/(n+'.png'));bpy.ops.render.render(write_still=True)
render('beauty',(4.7,-7,3.4),(0,0,.9),5.5)
render('rear-beauty',(4.7,7,3.4),(0,0,.9),5.5)
for o in bpy.data.collections['08 Studio'].objects:
 if o.type=='LIGHT':o.data.energy*=.30
d=bpy.data.lights.new('Cabin review fill','AREA');d.energy=22;d.size=.65;o=bpy.data.objects.new('Cabin review fill',d);s.collection.objects.link(o);o.location=(0,.22,1.38);o.rotation_euler=(Vector((0,-.25,.7))-o.location).to_track_quat('-Z','Y').to_euler()
render('driver-view',(.395,.15,1.25),(.18,-.50,.985),1.5,False)
