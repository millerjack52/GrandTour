import json,hashlib,zipfile
from pathlib import Path
P=Path('C:/GrandTour/Art/Export/VehicleTools/ferrari288-good-game-v01')
def read(name):return json.loads((P/name).read_text())
export=read('export-report.json');runtime=read('runtime-check.json');health=read('mesh-health.json');preserve=read('preservation-report.json');clearance=read('clearance-report.json')
assert runtime['ok'] and runtime['status']=='PASS' and runtime['exit_reenter']=='PASS'
fbx_hash=hashlib.sha256((P/'SK_Ferrari288.fbx').read_bytes()).hexdigest();assert runtime['fbx_sha256']==export['fbx_sha256']==fbx_hash
assert hashlib.sha256(Path(export['source']).read_bytes()).hexdigest()==export['source_sha256']
assert all(not x['zero_area_faces'] and x['zero_normals']==0 and x['zero_area_uv']==0 for x in health.values())
assert all(p['contacts']==0 for p in clearance['poses']);assert all(v==0 for v in clearance['seat_body_intersections'].values())
assert preserve['body_position_error_m']<1e-6 and preserve['body_uv_error']==0
report={'status':'VALIDATED_IN_GRANDTOUR_EDITOR','fbx_sha256':fbx_hash,'lod_triangles':[x['triangles'] for x in export['lods']],'materials':len(export['materials']),'source_body_preserved':True,'removed_interior_placeholder_faces':len(read('build-report.json')['removed_interior_placeholder_faces']),'runtime':{k:runtime[k] for k in ['forward_distance_cm','peak_speed_cm_s','brake_start_cm_s','brake_end_cm_s','steer_yaw_change_deg','exit_reenter','ground_contacts','renderer_enabled']},'limits':export['limits']+['No packaged shipping build or target-hardware performance certification.']}
(P/'delivery-report.json').write_text(json.dumps(report,indent=2))
names=['Ferrari288_GameReady.blend','Ferrari288_GameRig.blend','SK_Ferrari288.fbx','SK_Ferrari288_LOD1.fbx','SK_Ferrari288_LOD2.fbx','T_F288_Source.png','T_F288_Palette.png','README.txt','Open_Ferrari_Test.ps1','delivery-report.json','export-report.json','build-report.json','preservation-report.json','clearance-report.json','mesh-health.json','runtime-check.json','process-lessons.json','UE_Front.png','UE_Rear.png','UE_Cockpit.png','UE_LOD1.png','UE_LOD2.png']
with zipfile.ZipFile(P/'Ferrari288_GamePackage.zip','w',zipfile.ZIP_DEFLATED) as z:
 for name in names:z.write(P/name,name)
print(json.dumps(report,indent=2))
