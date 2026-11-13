"""Plain Python handoff: verify evidence, copy canonical sources, archive and review sheet."""
from pathlib import Path
import json,hashlib,shutil,zipfile,argparse
from PIL import Image,ImageDraw,ImageFont
ROOT=Path(__file__).resolve().parents[2]
ap=argparse.ArgumentParser();ap.add_argument('--reviewed',action='store_true');args=ap.parse_args()
assert args.reviewed,'Inspect final baked, LOD and articulated renders before finalizing'
BASE=ROOT/'Art/Vehicles/SpecialsTrio';BASE.mkdir(parents=True,exist_ok=True);rows=[]
cars=['KadettA','E39Touring','SJ413']
names=['Opel Kadett A','BMW E39 Touring','Suzuki SJ413']
sheet=Image.new('RGB',(1800,910),(23,29,34));draw=ImageDraw.Draw(sheet)
font=ImageFont.truetype('C:/Windows/Fonts/segoeui.ttf',25);small=ImageFont.truetype('C:/Windows/Fonts/segoeui.ttf',18)
for i,car in enumerate(cars):
 out=ROOT/'Art/Export/SpecialsTrio'/car/'Package_v01';asset=json.loads((out/'asset_report.json').read_text());validation=json.loads((out/'validation_report.json').read_text())
 source=out.parent/asset['source_revision'];intersection=json.loads((source/'intersection_report.json').read_text());assert intersection['status']=='PASS'
 assert asset['validation']['rigid_weights_uv_finite_nonzero_faces']=='PASS'
 for lod in range(3):
  fbx=out/('SK_'+car+('_LOD'+str(lod) if lod else '')+'.fbx');check=validation['roundtrip_LOD'+str(lod)]
  assert check['status']=='PASS' and hashlib.sha256(fbx.read_bytes()).hexdigest()==check['fbx_sha256']
 for view in ['front','rear','side','cockpit','lod2','articulation','rear_open']:assert (out/(view+'.png')).is_file(),(car,view)
 dest=BASE/car;dest.mkdir(exist_ok=True)
 shutil.copy2(source/(car+'.blend'),dest/(car+'.blend'));shutil.copy2(out/(car+'_Rigged.blend'),dest/(car+'_Game.blend'))
 shutil.copy2(source/'intersection_report.json',out/'intersection_report.json')
 shutil.copy2(ROOT/'docs/SPECIALS_VEHICLE_TRIO.md',out/'README.md')
 row={'car':car,'source_revision':asset['source_revision'],'status':'BLENDER_VALIDATED_UNREAL_PENDING','triangles':[validation['roundtrip_LOD'+str(l)]['triangles'] for l in range(3)],'bones':len(asset['bones']),'intersection_pairs':len(intersection['checks']),'visual_review':['front','rear','side','cockpit','lod2','articulation','rear_open'],'fbx_validation':validation,'limitations':'Engine import, Chaos driving, instrument bindings, steering/suspension clearance and performance remain untested.'}
 (dest/'model_check.json').write_text(json.dumps(row,indent=2));rows.append(row)
 with zipfile.ZipFile(dest/(car+'_BlenderPackage.zip'),'w',zipfile.ZIP_DEFLATED,compresslevel=6) as z:
  z.write(dest/(car+'.blend'),'Authoring/'+car+'.blend');z.write(dest/'model_check.json','model_check.json')
  for f in out.rglob('*'):
   if f.is_file() and f.suffix in {'.blend','.fbx','.png','.json','.md'}:z.write(f,'GameAsset/'+str(f.relative_to(out)))
  z.write(ROOT/'Art/References/Vehicles/SpecialsTrio'/(car+'_reference.png'),'Reference/'+car+'_reference.png')
  z.write(ROOT/'Art/References/Vehicles/SpecialsTrio/prompts.json','Reference/prompts.json')
 with zipfile.ZipFile(dest/(car+'_BlenderPackage.zip')) as z:assert z.testzip() is None
 draw.text((i*600+16,10),names[i],font=font,fill=(228,220,203))
 for j,view in enumerate(['front','cockpit']):
  im=Image.open(out/(view+'.png')).convert('RGB').resize((600,400),Image.Resampling.LANCZOS);sheet.paste(im,(i*600,50+j*425))
  draw.text((i*600+16,454+j*425),'Actual Blender render | '+view,font=small,fill=(203,213,218))
sheet.save(BASE/'SpecialsTrio_review.png')
(BASE/'summary.json').write_text(json.dumps(rows,indent=2))
print(json.dumps([{k:v for k,v in r.items() if k!='fbx_validation'} for r in rows],indent=2))
