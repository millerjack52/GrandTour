import bpy,math
from mathutils import Vector
from pathlib import Path
P=Path('C:/GrandTour/Art/Export/VehicleTools/ferrari288-prepared-v02')
bpy.ops.wm.open_mainfile(filepath=str(P/'Ferrari288_Safari.blend'))
sc=bpy.context.scene;sc.render.engine='CYCLES';sc.cycles.samples=32;sc.cycles.use_denoising=True;sc.render.resolution_x=1400;sc.render.resolution_y=1000;sc.view_settings.view_transform='AgX'
def area(name,pos,power,size):
 data=bpy.data.lights.new(name,'AREA');data.energy=power;data.shape='DISK';data.size=size;o=bpy.data.objects.new(name,data);sc.collection.objects.link(o);o.location=pos;o.rotation_euler=(Vector((0,0,.8))-o.location).to_track_quat('-Z','Y').to_euler()
area('Key',(3,-4,6),1500,5);area('Fill',(-4,-1,3),1100,4);area('Rim',(1,4,5),1400,3)
cam=sc.camera
def render(n,c,pos,ortho=None):
 cam.location=pos;cam.rotation_euler=(Vector(c)-cam.location).to_track_quat('-Z','Y').to_euler();cam.data.type='ORTHO' if ortho else 'PERSP';cam.data.lens=20
 if ortho:cam.data.ortho_scale=ortho
 sc.render.filepath=str(P/(n+'.png'));bpy.ops.render.render(write_still=True)
render('lit-quarter',(0,0,.90),(6,-9,4.8),5.5)
render('lit-glazing',(.0,-.15,1.18),(4,-6,3.4),2.7)
render('driver-view',(.38,-2,1.14),(.40,.21,1.28))
