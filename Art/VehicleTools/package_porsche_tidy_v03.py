import bpy,json,hashlib
from pathlib import Path
from mathutils import Vector
O=Path('C:/GrandTour/Art/Export/VehicleTools/porsche-tidy-v03');DEST=O/'Porsche_Tidy.blend'
bpy.ops.wm.open_mainfile(filepath=str(DEST));s=bpy.context.scene;parts=[o for o in bpy.data.collections['Porsche - repaired original components'].objects if o.type=='MESH']
def bounds(obs):
 ps=[o.matrix_world@Vector(p) for o in obs for p in o.bound_box]
 return [[min(p[k] for p in ps) for k in range(3)],[max(p[k] for p in ps) for k in range(3)]]
before=bounds(parts);count=len(parts);triangles=0
for o in parts:o.data.calc_loop_triangles();triangles+=len(o.data.loop_triangles)
bpy.ops.object.select_all(action='DESELECT')
for o in parts:o.hide_set(False);o.select_set(True)
glb=O/'Porsche_Tidy.glb';bpy.ops.export_scene.gltf(filepath=str(glb),export_format='GLB',use_selection=True,export_apply=True,export_cameras=False,export_lights=False)
bpy.ops.wm.read_factory_settings(use_empty=True);bpy.ops.import_scene.gltf(filepath=str(glb));afterparts=[o for o in bpy.context.scene.objects if o.type=='MESH'];after=bounds(afterparts);diff=max(abs(before[i][k]-after[i][k]) for i in range(2) for k in range(3))
assert count==len(afterparts),(count,len(afterparts));assert diff<.0001,diff
baseline=Path('C:/GrandTour/Art/Export/VehicleTools/porsche-preserved-repair-v02/Porsche_Preserved_Repair.blend');assert hashlib.sha256(baseline.read_bytes()).hexdigest()=='a8aa8bb82dcdc0c7f87db345197900c12ffa2299e5b0d43153c0ab6014b126af'
record={'status':'Local construction cleanup revision; visual review pending. Not game-ready.','blend':str(DEST),'glb':str(glb),'mesh_count':count,'triangles':triangles,'export_reimport_bounds_difference_m':diff,'accepted_baseline_unchanged':True,'completed':['Rebuilt glass and fitted seals with reformed mounting flanges','Rebuilt rack rails, crossmembers and body-contact mounts','Rebuilt parked wipers and fitted door handles','Rebuilt roof spare cover and toolcase at source envelopes','Added closed headlamp lenses on retained reflectors','Retained connected wheelhouse surfaces; removed intersecting liner trial','Checked floor coverage under both seats','Checked tyre/body intersections','Checked actual saved model and GLB reimport'],'limits':['Retained body still contains mixed source topology and open sheet boundaries','Fine original panel and pillar surfaces retain some source irregularity','No rig, steering/suspension sweep, collision assets, LODs or Unreal validation in this pass','UV/material finishing remains separate'],'blend_sha256':hashlib.sha256(DEST.read_bytes()).hexdigest(),'glb_sha256':hashlib.sha256(glb.read_bytes()).hexdigest()}
(O/'delivery-status.json').write_text(json.dumps(record,indent=2));print(json.dumps(record,indent=2))
