"""Publish unretouched game-view comparisons and the scoped canopy validation."""
from pathlib import Path
import json,hashlib
from PIL import Image,ImageDraw,ImageFont
R=Path('C:/GrandTour');O=R/'Art/Export/FloraTrail/Canopy'
reports={s:json.loads((O/(s+'-report.json')).read_text()) for s in ['canopy','install','verify']}
process={s:json.loads((O/(s+'-process.json')).read_text()) for s in reports}
assert all(r['ok'] for r in reports.values()) and all(r['exit_code']==0 for r in process.values())
build=json.loads((R/'Art/Export/FloraTrail/build-report.json').read_text());hashes=build['package_hashes']
assert reports['verify']['package_fingerprint']==hashlib.sha256(json.dumps(hashes,sort_keys=True).encode()).hexdigest()
for p,h in hashes.items():assert hashlib.sha256(Path(p).read_bytes()).hexdigest()==h,p
font=ImageFont.truetype('C:/Windows/Fonts/segoeui.ttf',24);small=ImageFont.truetype('C:/Windows/Fonts/segoeui.ttf',20)
board=Image.new('RGB',(1600,1160),(16,26,25));d=ImageDraw.Draw(board)
d.text((20,12),'TREE CANOPIES / same camera, sun, exposure and LODs',font=font,fill='#e2e6dc')
for i,mode in enumerate(['before','after']):
 x=16+i*792;d.text((x,54),'Before' if i==0 else 'After: fuller coverage + reflective leaf lighting',font=small,fill='#d9e0d5')
 im=Image.open(O/('game_'+mode+'_canopy.png')).convert('RGB').crop((550,70,1274,640));im.thumbnail((776,610));board.paste(im,(x+(776-im.width)//2,86))
 d.text((x,710),'Matched game view from the road',font=small,fill='#d9e0d5')
 im=Image.open(O/('game_'+mode+'_road.png')).convert('RGB');im.thumbnail((776,370));board.paste(im,(x+(776-im.width)//2,744))
d.text((20,1124),'Actual Unreal captures. Top row: identical crops. No image colour correction.',font=small,fill='#b9c9c2')
board.save(O/'trees-before-after.jpg',quality=94)
grid=Image.new('RGB',(1240,1185),(16,26,25));d=ImageDraw.Draw(grid)
for i,(name,label) in enumerate([('00_before','Original'),('01_lod0_only','Full geometry only'),('02_coverage_only','Coverage fix only'),('03_lighting_only','Lighting fix only'),('04_combined','Combined fix'),('05_combined_sun_off','Combined fix: sun off')]):
 x=12+(i%2)*620;y=12+(i//2)*390;d.text((x,y),label,font=small,fill='#d9e0d5');im=Image.open(O/(name+'_canopy.png')).convert('RGB');im.thumbnail((604,345));grid.paste(im,(x,y+30))
grid.save(O/'diagnostic-grid.jpg',quality=93)
validation={'ok':True,'scope':'FloraTrail tree leaf materials only','install':reports['install'],'saved_map_verification':reports['verify'],'processes':process,'performance':json.loads((O/'performance-environment.json').read_text()),'images':['trees-before-after.jpg','diagnostic-grid.jpg','game_after_driving.png'],'unchanged_geometry':True,'remaining_limits':['Fine temporal mask edge noise','Full Blender appearance parity and full-pack conversion not claimed','No clean performance result while Skate shares the GPU']}
(R/'docs/validation/flora-trail-canopy.json').write_text(json.dumps(validation,indent=2));(O/'review-report.json').write_text(json.dumps(validation,indent=2))
print(json.dumps({'ok':True,'trees':reports['install']['trees'],'geometry_unchanged':True,'performance_verified':False,'images':validation['images']},indent=2))
