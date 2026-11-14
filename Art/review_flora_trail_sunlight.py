"""Validate and assemble the actual sunlight correction views, without recolouring."""
import json,sys
from pathlib import Path
from PIL import Image,ImageDraw,ImageFont,ImageStat
R=Path('C:/GrandTour');O=R/'Art/Export/FloraTrail/Sunlight'
sys.path.insert(0,str(R/'Art/Unreal'))
from flora_trail_evidence import audited_fingerprint
reports={k:json.loads((O/(k+'-report.json')).read_text()) for k in ['probe','install','verify']}
processes={k:json.loads((O/(k+'-process.json')).read_text()) for k in reports}
assert all(r['ok'] for r in reports.values()) and all(p['exit_code']==0 for p in processes.values())
assert reports['probe']['package_fingerprint']==reports['install']['before_fingerprint']
fingerprint=audited_fingerprint()
assert reports['install']['after_fingerprint']==reports['verify']['package_fingerprint']==fingerprint
grey=Image.open(O/'game_verify_display_check.png').convert('RGB');x,y=grey.width//2,grey.height//2
rgb=ImageStat.Stat(grey.crop((x-8,y-8,x+8,y+8))).mean
assert max(abs(v-117.6458) for v in rgb)<3,rgb
font=ImageFont.truetype('C:/Windows/Fonts/segoeui.ttf',24)
small=ImageFont.truetype('C:/Windows/Fonts/segoeui.ttf',20)
w,h=900,482;canvas=Image.new('RGB',(1836,1147),(15,25,27));draw=ImageDraw.Draw(canvas)
draw.text((12,12),'FLORA TRAIL / restoring direct sunlight',font=font,fill='#E3E9E5')
draw.text((12,48),'Same tree materials, camera, exposure and skylight. Actual game captures.',font=small,fill='#B9C6C2')
for row,view in enumerate(['road','mixed']):
 for column,(mode,label) in enumerate([('before','Previous / comparison light rig'),('saved','Corrected / scene sunlight')]):
  x=12+912*column;y=82+521*row
  draw.text((x,y),label,font=small,fill='#DCE5E0')
  im=Image.open(O/f'game_{mode}_{view}.png').convert('RGB');im.thumbnail((w,h),Image.Resampling.LANCZOS);canvas.paste(im,(x,y+29))
canvas.save(O/'sunlight-comparison.jpg',quality=95)
validation={'ok':True,'scope':'FloraTrail sun direction/intensity and matching undergrowth light vector only; calibrated tree shaders unchanged.','fingerprint':fingerprint,'processes':processes,'lighting':reports['verify']['lighting'],'settings':reports['install']['settings'],'retained_scene_packages':reports['install']['retained_scene_packages'],'protected_other_assets':reports['install']['protected_other_assets'],'display_rgb':rgb,'performance_verified':False,'driving_regression':'Prior Source34 driving result remains historical; no gameplay, geometry or material assets changed in this lighting-only correction.','comparison':'Art/Export/FloraTrail/Sunlight/sunlight-comparison.jpg'}
(R/'Docs/validation/flora-trail-sunlight.json').write_text(json.dumps(validation,indent=2)+'\n')
(O/'review-report.json').write_text(json.dumps(validation,indent=2)+'\n')
print(json.dumps(validation,indent=2))
