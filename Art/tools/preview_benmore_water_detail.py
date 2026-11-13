"""Present unretouched engine captures and measure the controlled optical toggle."""
import json
from pathlib import Path
import numpy as np
from PIL import Image,ImageDraw,ImageFont
out=Path(__file__).resolve().parents[2]/'Art/Export/BenmoreGaea/WaterDetail_20261011'
report=json.loads((out/'install-report.json').read_text());assert report['ok'],report.get('error')
assert report['before']==report['after']
assert report['camera']['Before']==report['camera']['After']
font=ImageFont.truetype('C:/Windows/Fonts/arial.ttf',20)
frames=[];after=[]
for i in range(24):
    a=Image.open(out/('Before_%02d.png'%i)).convert('RGB');b=Image.open(out/('After_%02d.png'%i)).convert('RGB')
    canvas=Image.new('RGB',(1280,430),(21,27,30));draw=ImageDraw.Draw(canvas)
    draw.text((12,4),'Before',font=font,fill='white');draw.text((652,4),'Broken foam, spray and refraction',font=font,fill='white')
    canvas.paste(a.resize((640,400),Image.Resampling.LANCZOS),(0,30));canvas.paste(b.resize((640,400),Image.Resampling.LANCZOS),(640,30))
    frames.append(canvas);after.append(b)
for sequence,name in [(frames,'Comparison.gif'),(after,'Motion.gif')]:
    sequence[0].save(out/name,save_all=True,append_images=sequence[1:],duration=[120,130]*12,loop=0)
a=np.array(Image.open(out/'Refraction_Off.png').convert('RGB'),dtype=float)
b=np.array(Image.open(out/'Refraction_On.png').convert('RGB'),dtype=float)
delta=np.mean(np.abs(a-b),axis=2)
# Central water crop excludes sky, most bank vegetation and the sun hotspot.
water=delta[300:570,280:750]
metrics={'water_toggle_mean_rgb_difference':float(water.mean()),'water_pixels_changed_over_3_levels':float((water>3).mean()),'seconds':3,'frames':24}
hidden=np.array(Image.open(out/'Spray_Off.png').convert('RGB'),dtype=float)
spray_delta=np.mean(b-hidden,axis=2)[240:590,220:950]
metrics['spray_bright_pixels']=int((spray_delta>35).sum())
metrics['spray_dark_pixels']=int((spray_delta< -35).sum())
assert metrics['spray_bright_pixels']>3,metrics
assert metrics['spray_bright_pixels']>metrics['spray_dark_pixels'],metrics
(out/'preview-report.json').write_text(json.dumps(metrics,indent=2));print(json.dumps(metrics,indent=2))
