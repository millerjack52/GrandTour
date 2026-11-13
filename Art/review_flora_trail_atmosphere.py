"""Validate saved atmosphere evidence and assemble unretouched game views."""
from pathlib import Path
import hashlib,json
from PIL import Image,ImageDraw,ImageFont

R=Path('C:/GrandTour');O=R/'Art/Export/FloraTrail/Atmosphere'
stages=['atmosphere','install_atmosphere','verify_atmosphere']
reports={s:json.loads((O/(s+'-report.json')).read_text()) for s in stages}
processes={s:json.loads((O/(s+'-process.json')).read_text()) for s in stages}
assert all(r['ok'] for r in reports.values())
assert all(p['exit_code']==0 for p in processes.values())
assert reports['verify_atmosphere']['saved_settings_match']
build=json.loads((R/'Art/Export/FloraTrail/build-report.json').read_text())
hashes=build['package_hashes']
assert reports['verify_atmosphere']['package_fingerprint']==hashlib.sha256(json.dumps(hashes,sort_keys=True).encode()).hexdigest()
for p,h in hashes.items():assert hashlib.sha256(Path(p).read_bytes()).hexdigest()==h,p
board=Image.new('RGB',(1600,1010),(16,26,25));d=ImageDraw.Draw(board)
font=ImageFont.truetype('C:/Windows/Fonts/segoeui.ttf',24)
small=ImageFont.truetype('C:/Windows/Fonts/segoeui.ttf',19)
d.text((18,12),'ATMOSPHERE / same palette, exposure and surface lighting',font=font,fill='#e2e6dc')
for col,mode in enumerate(['before','saved']):
    x=16+col*792
    d.text((x,54),'Before: dense near-camera haze' if col==0 else 'After: lighter haze, clearer colour',font=font,fill='#d9e0d5')
    for row,view in enumerate(['road','canopy']):
        im=Image.open(O/('game_'+mode+'_'+view+'.png')).convert('RGB')
        im.thumbnail((776,416));board.paste(im,(x,90+row*446))
d.text((18,976),'Actual Unreal game views. Identical cameras; no image colour correction.',font=small,fill='#b9c9c2')
board.save(O/'atmosphere-before-after.jpg',quality=94)
validation={'ok':True,'reports':reports,'processes':processes,'performance_verified':False,
            'scope':'FloraTrail fog and volumetric sunlight only. Textures, materials, exposure, direct/sky lighting, geometry and gameplay unchanged.',
            'images':['atmosphere-before-after.jpg','game_saved_driving.png'],
            'limits':['No new GPU timing claim','This small-scene haze profile is not a validated LiDAR long-distance profile']}
(R/'docs/validation/flora-trail-atmosphere.json').write_text(json.dumps(validation,indent=2)+'\n')
(O/'review-report.json').write_text(json.dumps(validation,indent=2)+'\n')
print(json.dumps({'ok':True,'performance_verified':False,'images':validation['images']}))
