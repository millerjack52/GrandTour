"""Assemble matched engine frames without retouching the water."""
import json,sys
from pathlib import Path
from PIL import Image,ImageDraw,ImageFont

VARIANT=sys.argv[1] if len(sys.argv)>1 else 'Motion'
assert VARIANT in ('Motion','Rapids')
OUT=Path(__file__).resolve().parents[2]/('Art/Export/BenmoreGaea/Water'+VARIANT+'_20261011')
TITLE='Shallow rapids and whitewater' if VARIANT=='Rapids' else 'Stronger river motion'
report=json.loads((OUT/'install-report.json').read_text())
assert report['ok'],report.get('error')
assert report['before']==report['after']
assert report['camera']['Before']==report['camera']['After']
font=ImageFont.truetype('C:/Windows/Fonts/arial.ttf',22)
small=ImageFont.truetype('C:/Windows/Fonts/arial.ttf',16)
paired=[];after=[];details=[]
for i in range(24):
    left=Image.open(OUT/('Before_%02d.png'%i)).convert('RGB')
    right=Image.open(OUT/('After_%02d.png'%i)).convert('RGB')
    assert left.size==right.size==(960,600)
    frame=Image.new('RGB',(1536,526),(19,24,28))
    draw=ImageDraw.Draw(frame)
    draw.text((18,8),'Previous pass',font=font,fill=(235,239,242))
    draw.text((786,8),TITLE,font=font,fill=(235,239,242))
    draw.text((18,36),'Fixed camera / same water clock / 3-second sequence',font=small,fill=(157,179,187))
    frame.paste(left.resize((768,480),Image.Resampling.LANCZOS),(0,46))
    frame.paste(right.resize((768,480),Image.Resampling.LANCZOS),(768,46))
    paired.append(frame);after.append(right)
    detail=Image.new('RGB',(860,418),(19,24,28))
    draw=ImageDraw.Draw(detail)
    draw.text((12,5),'Previous pass / river detail',font=font,fill=(235,239,242))
    draw.text((12,214),TITLE+' / same water clock',font=font,fill=(235,239,242))
    detail.paste(left.crop((70,170,930,345)),(0,34))
    detail.paste(right.crop((70,170,930,345)),(0,243))
    details.append(detail)
# GIF timing is quantized to 10 ms: alternate 120/130 ms for exact 8 Hz.
durations=[120,130]*12
for frames,name in [(paired,'Comparison.gif'),(after,'Motion.gif'),(details,'Detail.gif')]:
    frames[0].save(OUT/name,save_all=True,append_images=frames[1:],duration=durations,loop=0)
print(json.dumps({'ok':True,'frames':24,'seconds':3,'comparison':str(OUT/'Comparison.gif'),
    'preview':str(OUT/'Motion.gif'),'runtime_clock':report['runtime_clock']},indent=2))
