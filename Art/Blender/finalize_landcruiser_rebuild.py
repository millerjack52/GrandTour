"""Save the checked replacement and a clean portable handoff archive. Plain Python."""
from pathlib import Path
import shutil,json,hashlib,zipfile,argparse
parser=argparse.ArgumentParser();parser.add_argument('--package',default='Package_v03');args=parser.parse_args()
ROOT=Path(__file__).resolve().parents[2];OUT=ROOT/'Art/Export/LandCruiser'/args.package;DST=ROOT/'Art/Vehicles/LandCruiser80'
audit=json.loads((OUT/'validation_report.json').read_text());asset=json.loads((OUT/'asset_report.json').read_text())
for lod in [0,1,2]:
    file=OUT/('SK_LandCruiser80'+('_LOD'+str(lod) if lod else '')+'.fbx')
    checked=audit['roundtrip_LOD'+str(lod)]
    assert checked['status']=='PASS' and hashlib.sha256(file.read_bytes()).hexdigest()==checked['fbx_sha256']
for wheel,b in asset['wheel_bounds_metres'].items():
    dims=[b['max'][i]-b['min'][i] for i in range(3)]
    assert .30<dims[0]<.33 and .82<dims[1]<.84 and .82<dims[2]<.84,(wheel,dims)
shutil.copy2(ROOT/'Art/Export/LandCruiser'/asset.get('source_revision','R5')/'LandCruiser80.blend',DST/'LandCruiser80.blend')
shutil.copy2(OUT/'LandCruiser80_Rigged.blend',DST/'LandCruiser80_Game.blend')
engine_report=OUT/'unreal_import_report.json'
engine=json.loads(engine_report.read_text()) if engine_report.exists() else None
status='UNREAL_ART_IMPORTED_DRIVING_PENDING' if engine and engine.get('status')=='IMPORTED' else 'OFFLINE_PASS_UNREAL_PENDING'
(DST/'model_check.json').write_text(json.dumps({'status':status,'asset':asset,'validation':audit,'unreal_import':engine},indent=2))
shutil.copy2(ROOT/'docs/LANDCRUISER_MODEL_STUDY.md',OUT/'README.md')
files=['LandCruiser80_Rigged.blend','LandCruiser80_LOD1.blend','LandCruiser80_LOD2.blend','LandCruiser80_ArticulationReview.blend','SK_LandCruiser80.fbx','SK_LandCruiser80_LOD1.fbx','SK_LandCruiser80_LOD2.fbx','asset_report.json','validation_report.json','README.md','front.png','rear.png','cockpit.png','lod2.png','articulation.png']
files += [p.name for p in OUT.glob('T_LC80_*.png')]
if (OUT/'side.png').exists():files.append('side.png')
if (OUT/'unreal_import_report.json').exists():files.append('unreal_import_report.json')
files += [str(p.relative_to(OUT)) for d in OUT.glob('*.fbm') for p in d.rglob('*') if p.is_file()]
archive=DST/'LandCruiser80_BlenderPackage.zip'
with zipfile.ZipFile(archive,'w',zipfile.ZIP_DEFLATED,compresslevel=6) as z:
    z.write(DST/'LandCruiser80.blend','Authoring/LandCruiser80.blend')
    for file in files:z.write(OUT/file,'GameAsset/'+file)
with zipfile.ZipFile(archive) as z:assert z.testzip() is None
print('LC_FINALIZED '+str(archive))
