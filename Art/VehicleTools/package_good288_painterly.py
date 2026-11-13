import json,hashlib,zipfile,shutil
from pathlib import Path
P=Path('C:/GrandTour/Art/Export/VehicleTools/ferrari288-painterly-v01');BASE=P.parent/'ferrari288-good-game-v01'
read=lambda name:json.loads((P/name).read_text())
paint=read('painterly-report.json');engine=read('unreal-painterly-report.json');render=read('render-check.json')
assert paint['ok'] and engine['ok'] and render['ok']
assert render['lod_count']==3 and render['renderer_enabled']
assert paint['authoring_geometry_uv_unchanged'] and paint['game_rig_geometry_uv_unchanged']
assert paint['fbx_sha256']==hashlib.sha256((P/'SK_Ferrari288.fbx').read_bytes()).hexdigest()==render['fbx_sha256']
for name in ['runtime-check.json','mesh-health.json','clearance-report.json','preservation-report.json']:
 shutil.copy2(BASE/name,P/('original-'+name))
report={'status':'PAINTERLY_MATERIAL_VALIDATED_IN_EDITOR','geometry_unchanged':True,'stroke_base_cm':100,'stroke_nominal_range_cm':[100,240],'fine_pass':False,'normal_strength':.5,'normal_texture_size':2048,'unreal_material':engine['material'],'render_check':render['status'],'previous_drive_checks':'original-runtime-check.json','new_driving_test_required':False,'reason':'Only material assignment and textures changed; FBX hash identical.'}
(P/'delivery-report.json').write_text(json.dumps(report,indent=2))
with zipfile.ZipFile(P/'Ferrari288_Painterly_Package.zip','w',zipfile.ZIP_DEFLATED) as z:
 for f in sorted(P.iterdir()):
  if f.suffix in ['.blend','.fbx','.png','.json','.txt']:z.write(f,f.name)
print(json.dumps(report,indent=2))
