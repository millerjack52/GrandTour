"""Assemble ungraded game captures and verify the saved-scene promotion evidence."""
import hashlib,json,sys
from pathlib import Path
from PIL import Image,ImageDraw,ImageFont,ImageStat
R=Path('C:/GrandTour');O=R/'Art/Export/FloraTrail/Source34'
sys.path.insert(0,str(R/'Art/Unreal'))
from flora_trail_evidence import audited_fingerprint
reports={k:json.loads((O/(k+'-report.json')).read_text()) for k in ['install','verify','check']}
processes={k:json.loads((O/(k+'-process.json')).read_text()) for k in reports}
assert all(r['ok'] for r in reports.values())
assert all(r['exit_code']==0 for r in processes.values())
fingerprint=audited_fingerprint()
assert reports['install']['after_fingerprint']==reports['verify']['package_fingerprint']==reports['check']['trial_packages_sha256']==fingerprint
grey=Image.open(O/'game_verify_display_check.png').convert('RGB');x,y=grey.width//2,grey.height//2
rgb=ImageStat.Stat(grey.crop((x-8,y-8,x+8,y+8))).mean
expected=255*(1.055*.18**(1/2.4)-.055)
assert max(abs(v-expected) for v in rgb)<3,(rgb,expected)
font=ImageFont.truetype('C:/Windows/Fonts/segoeui.ttf',24)
small=ImageFont.truetype('C:/Windows/Fonts/segoeui.ttf',19)
def board(name,rows,subtitle):
 w,h=900,482;canvas=Image.new('RGB',(w*2+36,(h+39)*len(rows)+105),(15,25,27));draw=ImageDraw.Draw(canvas)
 draw.text((12,10),'FLORA TRAIL / Blender-calibrated tree response',font=font,fill='#E3E9E5')
 draw.text((12,45),subtitle,font=small,fill='#B9C6C2')
 for j,row in enumerate(rows):
  for i,(label,path) in enumerate(row):
   x=12+i*(w+12);y=82+j*(h+39)
   draw.text((x,y),label,font=small,fill='#DCE5E0')
   im=Image.open(path).convert('RGB');im.thumbnail((w,h),Image.Resampling.LANCZOS);canvas.paste(im,(x,y+29))
 canvas.save(O/name,quality=95)
board('before-after.jpg',[[('Previous scene',O/'game_before_road.png'),('Saved scene / calibrated trees and lighting',O/'game_saved_road.png')],[('Previous canopy',O/'game_before_canopy.png'),('Saved canopy',O/'game_saved_canopy.png')]],'Same camera and exposure. Lighting and tree response changed together; no image recolouring.')
board('scene-views.jpg',[[('Road / trees, ferns and shrubs',O/'game_saved_road.png'),('Mixed foliage / pond edge',O/'game_saved_mixed.png')],[('Canopy / upward view',O/'game_saved_pond.png'),('Actual driving camera',O/'game_verify_driving.png')]],'Actual saved-map game views. Warm sun + cool sky from the approved comparison.')
validation={'ok':True,'scope':'FloraTrail only; approved tree/pine Leaf_0 source-version response, comparison warm light rig. Other foliage keeps original conversion.','package_fingerprint':fingerprint,'processes':processes,'lighting':reports['verify']['lighting'],'assets':reports['verify']['assets_before'],'protected_other_assets':reports['install']['protected_other_assets'],'display_check':{'linear_input':.18,'expected_srgb_255':expected,'observed_rgb_255':rgb},'driving':{k:v for k,v in reports['check'].items() if k in ['route','rendered_deformation','max_worked_height_change_cm','max_reset_height_error_cm','performance_verified']},'performance_verified':False,'limitations':['Fine temporal coverage noise remains.','Other foliage shader families and arbitrary local lighting have not received source-version parity validation.','No sustained 60 fps claim; verification launches disable RHI threading.'],'images':['before-after.jpg','scene-views.jpg']}
if 'route' in validation['driving']:validation['driving']['route']={k:v for k,v in validation['driving']['route'].items() if k!='samples'}
(R/'Docs/validation/flora-trail-source34.json').write_text(json.dumps(validation,indent=2)+'\n')
(O/'review-report.json').write_text(json.dumps(validation,indent=2)+'\n')
print(json.dumps({'ok':True,'display_rgb':rgb,'fingerprint':fingerprint}))
