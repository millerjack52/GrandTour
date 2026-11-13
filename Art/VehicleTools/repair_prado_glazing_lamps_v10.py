import bpy,sys,json,hashlib
from pathlib import Path
from mathutils import Vector
sys.path.insert(0,'C:/GrandTour/Art/VehicleTools')
from prado_glazing_repair import repair_rear,repair_front
from prado_lamp_repair_module import repair_rear_lamps
SRC=Path('C:/GrandTour/Art/Export/VehicleTools/prado-cabin-v08/Prado_Interior.blend')
OUT=SRC.parent.parent/'prado-glazing-v10';OUT.mkdir(exist_ok=True)
assert not (OUT/'Prado_Corrected.blend').exists(),'Saved revision protected'
bpy.ops.wm.open_mainfile(filepath=str(SRC));sc=bpy.context.scene
source=json.loads(Path('C:/GrandTour/Art/Export/VehicleTools/prado-source-v01/islands.json').read_text())[0]
audit=Path('C:/GrandTour/Art/Export/VehicleTools/prado-glazing-audit')
objects=[o for o in sc.objects if o.type=='MESH' and (o.name.startswith('Door |') or o.name=='Prado | fixed shell and underbody')]
before={o.name:hashlib.sha256(repr([tuple(v.co) for v in o.data.vertices]).encode()).hexdigest() for o in sc.objects if o.type=='MESH'}
report={'input_file':str(SRC),'input_sha256':hashlib.sha256(SRC.read_bytes()).hexdigest()}
report['rear_window']=repair_rear(source,json.loads((audit/'repair-contract.json').read_text()),objects)
report['windscreen']=repair_front(source,json.loads((audit/'windscreen-repair-contract.json').read_text()),objects)
report['rear_lamps']=repair_rear_lamps()
report['unchanged_meshes']=[o.name for o in sc.objects if o.type=='MESH' and o.name in before and hashlib.sha256(repr([tuple(v.co) for v in o.data.vertices]).encode()).hexdigest()==before[o.name]]
(OUT/'repair-report.json').write_text(json.dumps(report,indent=2))
sc.render.engine='BLENDER_WORKBENCH';sc.display.shading.color_type='MATERIAL';sc.render.resolution_x=1500;sc.render.resolution_y=1100;sc.render.resolution_percentage=100
for screen in bpy.data.screens:
 for area in screen.areas:
  if area.type=='VIEW_3D':area.spaces.active.shading.color_type='MATERIAL';area.spaces.active.shading.type='SOLID'
cam=sc.camera
def render(n,c,d,size):
 target=Vector(c)*5;cam.data.type='ORTHO';cam.location=target+Vector(d)*5;cam.rotation_euler=(target-cam.location).to_track_quat('-Z','Y').to_euler();cam.data.ortho_scale=size*5;sc.render.filepath=str(OUT/(n+'.png'));bpy.ops.render.render(write_still=True)
for n,c,d,size in [('front-close',(0,-.13,.36),(0,-3,.1),.44),('front-oblique',(0,-.13,.36),(-2,-3,.5),.48),('rear-installed',(0,.35,.29),(-2,3,.5),.70),('quarter',(0,0,.27),(2,-3,1.1),1.2),('rear-quarter',(0,0,.27),(-2,3,1.0),1.2)]:render(n,c,d,size)
hidden=[]
for o in sc.objects:
 if o.type=='MESH' and any(c.name in ['04 Spare wheel','06 Roof rack and cargo','07 Side equipment'] for c in o.users_collection) and not o.hide_render:hidden.append(o);o.hide_render=True
render('rear-isolated',(0,.37,.37),(0,3,0),.44);render('rear-oblique',(0,.37,.37),(-2,3,.3),.49)
for o in hidden:o.hide_render=False
render('quarter',(0,0,.27),(2,-3,1.1),1.2)
sc['asset_status']='Glazing seating/contours and rear-lamp corrective review. Remaining source body cleanup and engine prep outstanding.'
bpy.ops.wm.save_as_mainfile(filepath=str(OUT/'Prado_Corrected.blend'))

