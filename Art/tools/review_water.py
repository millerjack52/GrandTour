"""Package unretouched runtime frames for the water inspection."""
from pathlib import Path
from PIL import Image, ImageDraw, ImageFont
import json, shutil, html

ROOT=Path('C:/GrandTour')
src=ROOT/'Saved/LidarAuthoringQA/WaterReview/Capture'
out=ROOT/'Art/Export/LidarStudy/WaterReview'
result=json.loads((src/'process.json').read_text(encoding='utf-8-sig'))
assert result['ok'], 'Capture validation failed'
out.mkdir(parents=True,exist_ok=True)
labels={
 'river-bank':'River / bank view',
 'river-above':'River / surface and shallows',
 'access-pond-above':'Access-road pond / woodland edge',
 'mapped-pond-above':'Northern pond / shoreline',
 'access-pond-bank':'Access-road pond / low view',
 'mapped-pond-low':'Northern pond / low view',
}
for name in labels:
    shutil.copy2(src/(name+'.png'),out/(name+'.png'))
font=ImageFont.truetype('C:/Windows/Fonts/segoeui.ttf',24)
small=ImageFont.truetype('C:/Windows/Fonts/segoeui.ttf',19)
board=Image.new('RGB',(1824,1196),'#132020')
draw=ImageDraw.Draw(board)
draw.text((16,12),'LIDAR WATER / CURRENT GAME VIEWS',font=font,fill='#edf0e7')
draw.text((16,48),'Current palette preserved. Unretouched 888 x 500 runtime frames. GPU timings unverified.',font=small,fill='#b8c6c2')
for i,name in enumerate(list(labels)[:4]):
    x=16+(i%2)*904; y=90+(i//2)*550
    draw.text((x,y),labels[name],font=font,fill='#edf0e7')
    im=Image.open(src/(name+'.png')).convert('RGB')
    assert im.size==(888,500),im.size
    board.paste(im,(x,y+34))
board.save(out/'water-review.jpg',quality=94)
parts=['<!doctype html><meta charset="utf-8"><title>LiDAR water review</title><style>body{margin:32px auto;max-width:1100px;background:#132020;color:#edf0e7;font:18px system-ui}img{max-width:100%}figure{margin:32px 0}a{color:#b5d5d1}</style><h1>Current water review</h1><p>Six actual game views, current palette. Materials and level unchanged. Native frames: 888 × 500. GPU timings unverified.</p>']
for name,label in labels.items():
    parts.append(f'<figure><h2>{html.escape(label)}</h2><a href="{name}.png"><img src="{name}.png"></a></figure>')
(out/'index.html').write_text('\n'.join(parts),encoding='utf-8')
print(out/'water-review.jpg')
