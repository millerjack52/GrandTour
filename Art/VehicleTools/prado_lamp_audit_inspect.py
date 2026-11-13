import bpy,json,math
from pathlib import Path
from mathutils import Vector
OUT=Path('C:/GrandTour/Art/Export/VehicleTools/prado-lamp-audit');OUT.mkdir(exist_ok=True,parents=True)
bpy.ops.wm.open_mainfile(filepath='C:/GrandTour/Art/Export/VehicleTools/prado-cabin-v08/Prado_Interior.blend')
sc=bpy.context.scene;sc.render.engine='BLENDER_WORKBENCH';sc.render.resolution_x=1600;sc.render.resolution_y=1300;sc.render.resolution_percentage=100
sh=sc.display.shading;sh.light='STUDIO';sh.color_type='OBJECT';sh.show_shadows=True;sh.show_cavity=True;sh.cavity_type='BOTH';sh.background_type='WORLD'
sc.world.color=(.14,.14,.14);cam=sc.camera;cam.data.type='ORTHO'
def render(n,c,d,size):
 c=Vector(c)*5;cam.location=c+Vector(d)*5;cam.rotation_euler=(c-cam.location).to_track_quat('-Z','Y').to_euler();cam.data.ortho_scale=size*5;sc.render.filepath=str(OUT/(n+'.png'));bpy.ops.render.render(write_still=True)
render('rear-v08',(0,.43,.29),(0,3,.1),.70)
hidden=[]
for o in sc.objects:
 if o.type=='MESH' and any(c.name in ['04 Spare wheel','06 Roof rack and cargo','07 Side equipment','09 Small fittings'] for c in o.users_collection):
  hidden.append((o,o.hide_render));o.hide_render=True
render('rear-body-only',(0,.43,.27),(0,3,0),.49)
render('rear-corner',(.16,.425,.265),(1.7,3,.4),.25)
A=json.loads(Path('C:/GrandTour/Art/Export/VehicleTools/prado-source-v01/islands.json').read_text())
small=[]
for i,a in enumerate(A):
 lo,hi=Vector(a['min']),Vector(a['max']);c=(lo+hi)/2
 if c.y>.37 and c.z>.16:
  small.append({'id':i,'v':a['vertices'],'f':a['faces'],'lo':list(lo),'hi':list(hi),'center':list(c)})
(OUT/'rear-components.json').write_text(json.dumps(small,indent=2))
body=bpy.data.objects['Prado | fixed shell and underbody']
info=[]
for p in body.data.polygons:
 c=sum((body.matrix_world@body.data.vertices[i].co for i in p.vertices),Vector())/len(p.vertices)/5
 if c.y>.405 and c.z>.165 and c.z<.30 and abs(c.x)>.14:
  info.append({'id':p.index,'c':list(c),'n':list(p.normal),'v':[list((body.matrix_world@body.data.vertices[i].co)/5) for i in p.vertices]})
(OUT/'rear-body-faces.json').write_text(json.dumps(info,indent=2))
print('COMPONENTS',json.dumps(small));print('BODY FACES',len(info))
