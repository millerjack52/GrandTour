"""Assemble unretouched saved-map tree-colour comparisons and validation."""
from pathlib import Path
import hashlib,json
from PIL import Image,ImageDraw,ImageFont

R=Path('C:/GrandTour');O=R/'Art/Export/FloraTrail/TreeColour'
stages=['colour','install_colour','verify_colour']
reports={s:json.loads((O/(s+'-report.json')).read_text()) for s in stages}
processes={s:json.loads((O/(s+'-process.json')).read_text()) for s in stages}
assert all(r['ok'] for r in reports.values()) and all(p['exit_code']==0 for p in processes.values())
assert reports['verify_colour']['saved_settings_match']
hashes=json.loads((R/'Art/Export/FloraTrail/build-report.json').read_text())['package_hashes']
assert reports['verify_colour']['package_fingerprint']==hashlib.sha256(json.dumps(hashes,sort_keys=True).encode()).hexdigest()
for p,h in hashes.items():assert hashlib.sha256(Path(p).read_bytes()).hexdigest()==h,p
font=ImageFont.truetype('C:/Windows/Fonts/segoeui.ttf',24)
small=ImageFont.truetype('C:/Windows/Fonts/segoeui.ttf',20)
board=Image.new('RGB',(1600,1160),(16,26,25));d=ImageDraw.Draw(board)
d.text((20,12),'TREE COLOUR / brighter lit foliage, shaded crown interiors',font=font,fill='#e2e6dc')
for col,mode in enumerate(['current','saved']):
    x=16+col*792
    d.text((x,54),'Before: subdued foliage' if col==0 else 'After: stronger native leaf-light response',font=small,fill='#d9e0d5')
    im=Image.open(O/('game_'+mode+'_canopy.png')).convert('RGB').crop((550,70,1274,640))
    board.paste(im,(x+26,86))
    d.text((x,710),'Matched view of the sunlit crowns',font=small,fill='#d9e0d5')
    im=Image.open(O/('game_'+mode+'_sunlit.png')).convert('RGB');im.thumbnail((776,370))
    board.paste(im,(x+(776-im.width)//2,744))
d.text((20,1124),'Actual Unreal. Same lighting, exposure, fog and leaf coverage. No image colour correction.',font=small,fill='#b9c9c2')
board.save(O/'tree-colour-before-after.jpg',quality=94)
grid=Image.new('RGB',(1500,970),(16,26,25));d=ImageDraw.Draw(grid)
d.text((16,10),'CONTROLLED COLOUR TRIALS / same trees and lighting',font=font,fill='#e2e6dc')
for col,(mode,label) in enumerate([('current','Original'),('colour_medium','Medium response'),('colour_strong','Stronger response: selected')]):
    x=12+col*500;d.text((x,55),label,font=small,fill='#d9e0d5')
    for row,view in enumerate(['canopy','sunlit']):
        im=Image.open(O/('game_'+mode+'_'+view+'.png')).convert('RGB')
        im=im.crop((550,70,1274,640)) if view=='canopy' else im.crop((0,100,900,682))
        im.thumbnail((476,410));grid.paste(im,(x,90+row*440))
grid.save(O/'colour-trials.jpg',quality=94)
validation={'ok':True,'reports':reports,'processes':processes,'performance_verified':False,
            'scope':'Two local tree materials, 340 instances; reflectance and transmission scalar values only.',
            'unchanged':['Source textures and hue','Leaf coverage and authored normals','Geometry and LODs','Scene lights, fog and exposure','Bark, shrubs, ground, mud and water'],
            'images':['tree-colour-before-after.jpg','colour-trials.jpg','game_saved_sunlit.png'],
            'limits':['No exact Blender parity claim','No new GPU benchmark; capture runner disables the RHI thread to avoid a tooling shutdown fault','Existing fine mask noise remains']}
(R/'docs/validation/flora-tree-colour.json').write_text(json.dumps(validation,indent=2)+'\n')
(O/'review-report.json').write_text(json.dumps(validation,indent=2)+'\n')
print(json.dumps({'ok':True,'trees':reports['install_colour']['trees'],'images':validation['images']}))
