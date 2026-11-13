"""Compose unretouched Unreal evidence and publish a portable validation summary."""
import json,hashlib
from pathlib import Path
from PIL import Image,ImageDraw,ImageFont
R=Path('C:/GrandTour');O=R/'Art/Export/FloraTrail'
build=json.loads((O/'build-report.json').read_text());check=json.loads((O/'check-report.json').read_text());capture=json.loads((O/'capture-report.json').read_text())
assert build['ok'] and check['ok'] and capture['ok']
fingerprint=hashlib.sha256(json.dumps(build['package_hashes'],sort_keys=True).encode()).hexdigest()
assert check['trial_packages_sha256']==capture['trial_packages_sha256']==fingerprint
for p,h in build['package_hashes'].items():assert hashlib.sha256(Path(p).read_bytes()).hexdigest()==h,p
for p,h in json.loads((O/'protected-before.json').read_text()).items():assert hashlib.sha256(Path(p).read_bytes()).hexdigest()==h,p
process={stage:json.loads((O/(stage+'-process.json')).read_text()) for stage in ['build','check','capture']}
assert all(v['exit_code']==0 for v in process.values())
font=ImageFont.truetype('C:/Windows/Fonts/segoeui.ttf',22);small=ImageFont.truetype('C:/Windows/Fonts/segoeui.ttf',18)
def board(name,title,tiles):
 w=1600;tilew=776;tileh=416;out=Image.new('RGB',(w,1034),(16,26,25));d=ImageDraw.Draw(out);d.text((20,16),title,font=font,fill='#d9e0d5')
 for i,(file,label) in enumerate(tiles):
  x=16+(i%2)*792;y=62+(i//2)*466
  d.text((x,y),label,font=small,fill='#d9e0d5');im=Image.open(O/file).convert('RGB');im.thumbnail((tilew,tileh));out.paste(im,(x+(tilew-im.width)//2,y+30))
 d.text((20,1000),'Actual Unreal PIE captures. No repainting or colour adjustments to the images.',font=small,fill='#b9c9c2');out.save(O/name,quality=94)
board('playable-section.jpg','FLORA TRAIL / source foliage, deformable mud and water',[
 ('02_broken_puddles.png','Driving through the muddy section'),('03_flooded_dip.png','Shallow water crossing'),('06_forest_path.png','Layered forest edge and corrected source materials'),('15_pond.png','Cooler pond water beside the trail')])
board('deformation-proof.jpg','FLORA TRAIL / actual rendered terrain deformation',[
 ('21_ruts_before_drive.png','Fixed camera: before driving'),('22_ruts_after_drive.png','Same camera: after driving'),('09_ground_detail.png','Close ground relief'),('07_wet_clearing.png','Wet clearing')])
validation={
 'ok':True,'level':build['level'],'source_maps_and_assets_unchanged':True,'route_length_m':build['route_length_m'],
 'foliage_instances':build['instances'],'foliage_components':len(build['components']),
 'asset_audit':capture['asset_audit'],'package_fingerprint_sha256':fingerprint,
 'drive':{k:check['route'][k] for k in ['travel_cm','max_sink_cm','max_water_cm','max_compression_cm']},
 'rendered_deformation':check['rendered_deformation'],'reset_error_cm':check['max_reset_height_error_cm'],
 'shader_oracles':{k:v for k,v in check.items() if 'shader_max_error' in k},
 'pond_bed_cm':capture['pond_bed_cm'],'road_crown_to_trough_cm':capture['minimum_runtime_crown_to_trough_cm'],
 'render_spot_checks':capture['render_spot_checks'],'processes':process,
 'performance_verified':False,'performance_scope':'300-frame stationary PIE spot checks per view; not a 1080p or packaged 60 fps acceptance run. Editor frame pacing may remain active even with t.MaxFPS=0.',
 'limits':['Source foliage sun/uniform-sky model still has weak local-light parity','Temporal foliage edge noise remains','Six converted source foliage meshes, not the full pack'],
 'images':['playable-section.jpg','deformation-proof.jpg']}
(R/'docs/validation/flora-trail.json').write_text(json.dumps(validation,indent=2));(O/'review-report.json').write_text(json.dumps(validation,indent=2))
print(json.dumps({'ok':True,'drive':validation['drive'],'rendered_deformation':validation['rendered_deformation'],'images':validation['images']},indent=2))
