"""Actual paired renders, shared display, no individual plant colour fitting."""
import json,hashlib
from pathlib import Path
import numpy as np
from PIL import Image,ImageDraw,ImageFont
R=Path('C:/GrandTour');O=R/'Art/Export/LidarStudy/FloraParity/AssetMatch'
def raw(engine,name):return np.fromfile(O/engine/(name+'.f32'),np.float32).reshape(512,512,4)[...,:3]
def rgb(x,exposure=1):
 x=np.maximum(x*exposure,0);return np.uint8(np.clip(np.where(x<=.0031308,x*12.92,1.055*x**(1/2.4)-.055),0,1)*255)
def blur(x):return sum(np.roll(np.roll(x,y,0),z,1) for y in range(-2,3) for z in range(-2,3))/25
report={'source_pigment_and_mask_only':{},'neutral_receivers':{},'opacity':{},'display':'Beauty boards use native Blender and Unreal PNGs, neutral tone settings and exposure 0 in both, no per-asset colour fit. Pigment diagnostic uses shared Standard sRGB at +1 stop. Metrics use scene-linear HDR.','performance_verified':False}
for key in ['fern','shrub','tree']:
 path=O/'unreal'/(key+'_pigment_face.f32')
 if not path.exists():continue
 b=raw('blender',key+'_pigment_face');u=raw('unreal',key+'_pigment_face');mask=(b.max(2)>.003)|(u.max(2)>.003)
 report['source_pigment_and_mask_only'][key]={'integrated_rgb_ratio':(u.sum((0,1))/np.maximum(b.sum((0,1)),1e-9)).tolist(),'relative_rgb_l1_blurred':float(abs(blur(u)-blur(b))[mask].sum()/max(blur(b)[mask].sum(),1e-9))}
 if (O/'unreal'/(key+'_opacity_face.f32')).exists():
  a=raw('blender',key+'_opacity_face')[:,:,0];v=raw('unreal',key+'_opacity_face')[:,:,0]
  report['opacity'][key]={'integrated_ratio':float(v.sum()/a.sum()),'relative_l1':float(abs(a-v).sum()/a.sum()),'source_solid_fraction':float((a>.95).sum()/(a>.01).sum()),'unreal_solid_fraction':float((v>.95).sum()/(v>.01).sum())}
for light in ['front','side','back','shade']:
 b=raw('blender','chart_'+light);u=raw('unreal','chart_'+light)
 ref=float(np.quantile(b[410:480,20:492],.9));actual=float(np.quantile(u[410:480,20:492],.9))
 report['neutral_receivers'][light]={'blender':ref,'unreal':actual,'relative_error':abs(actual-ref)/ref}
protected=json.loads((R/'Art/Export/LidarStudy/FloraParity/protected-baseline.json').read_text())
report['protected_unchanged']={p:hashlib.sha256((R/p).read_bytes()).hexdigest()==h for p,h in protected.items()}
contract=json.loads((R/'Art/Export/LidarStudy/FloraParity/source-contract.json').read_text())
report['purchased_source_unchanged']=hashlib.sha256(Path(contract['source']).read_bytes()).hexdigest()==contract['source_sha256']
source=json.loads((O/'reference-report.json').read_text());built=json.loads((O/'build-report.json').read_text())
report['paired_cases']=sorted(set(source['images'])&set(built['images']))
font='C:/Windows/Fonts/segoeui.ttf';big=ImageFont.truetype(font,25);small=ImageFont.truetype(font,17)
for light in ['front','shade','pigment']:
 board=Image.new('RGB',(1140,1220),'#192326');d=ImageDraw.Draw(board)
 d.text((22,15),'FLORA PAINT / SAME PURCHASED ASSETS',font=big,fill='#edf1e3')
 title='Source pigment + opacity, lighting removed' if light=='pigment' else ('Shared front sunlight + neutral sky' if light=='front' else 'Shared neutral sky / no direct sun')
 d.text((22,53),title+' | identical crop; matched neutral display',font=small,fill='#b4c5c9')
 d.text((22,87),'BLENDER / source materials',font=big,fill='#edf1e3');d.text((587,87),'UNREAL / rebuilt source materials',font=big,fill='#edf1e3')
 for i,(key,crop) in enumerate([('fern',(70,230,460,455)),('shrub',(70,110,460,470)),('tree',(100,30,410,460))]):
  y=130+i*350
  for j,engine in enumerate(['blender','unreal']):
   im=(Image.fromarray(rgb(raw(engine,key+'_'+light+'_face'),2)) if light=='pigment' else Image.open(O/engine/(key+'_'+light+'_face.png')).convert('RGB')).crop(crop)
   im.thumbnail((530,310),Image.Resampling.LANCZOS);x=22+j*565
   d.text((x,y),key.title(),font=small,fill='#d9ddca');board.paste(im,(x+(530-im.width)//2,y+28))
 d.text((22,1190),'Real renderer captures. Source procedural pigment/opacity retained; LiDAR unchanged.',font=small,fill='#d9ddca')
 board.save(O/('same-assets-'+light+'.jpg'),quality=95)
# Show changes of illumination on the same source shrub, with no colour fitting.
board=Image.new('RGB',(1040,1660),'#192326');d=ImageDraw.Draw(board)
d.text((22,15),'FLORA PAINT / LIGHTING CHECKS',font=big,fill='#edf1e3')
d.text((22,53),'Blender source                         Unreal candidate',font=big,fill='#edf1e3')
for i,(light,label) in enumerate([('front','Front sun'),('side','Side sun'),('back','Backlight'),('shade','Neutral sky only'),('warm','Warm sun + cool sky'),('coolshade','Cool sky only')]):
 y=100+i*250;d.text((22,y),label,font=small,fill='#d9ddca')
 for j,engine in enumerate(['blender','unreal']):
  im=Image.open(O/engine/('shrub_'+light+'_face.png')).convert('RGB').crop((50,90,480,490));im.thumbnail((470,215),Image.Resampling.LANCZOS);board.paste(im,(22+j*515+(470-im.width)//2,y+24))
d.text((22,1620),'Actual captures | same source mesh, camera, display and light recipe',font=small,fill='#b4c5c9')
board.save(O/'lighting-comparison.jpg',quality=95)
(O/'comparison.json').write_text(json.dumps(report,indent=2));print(json.dumps(report,indent=2))
assert all(report['protected_unchanged'].values())
assert report['purchased_source_unchanged']
