"""Actual-vehicle wake preview; image durations follow recorded simulation time."""
import json,re
from pathlib import Path
from PIL import Image,ImageDraw,ImageFont
root=Path(__file__).resolve().parents[2]
out=root/'Art/Export/BenmoreGaea/VehicleWaves_20261011'
r=json.loads((out/'vehicle-review.json').read_text());assert r['ok'],r.get('error')
assert r['fixed_dt']['ok'] and r['paired_wakes']['same_physics_state']
font=ImageFont.truetype('C:/Windows/Fonts/arial.ttf',20)
frames=[];rows=[x for x in r['samples'] if x['case']=='AlongRiver']
for i,row in enumerate(rows):
    raw=Image.open(out/('AlongRiver_%02d.png'%(i+1))).convert('RGB')
    frame=Image.new('RGB',(960,630),(21,27,30));frame.paste(raw,(0,30))
    ImageDraw.Draw(frame).text((12,4),'Actual car / bow wave and spreading wake',font=font,fill='white')
    frames.append(frame)
durations=[max(30,round((b['t']-a['t'])*100)*10) for a,b in zip(rows,rows[1:])]
durations.append(durations[-1])
frames[0].save(out/'VehicleWake.gif',save_all=True,append_images=frames[1:],duration=durations,loop=0)
pair=Image.new('RGB',(1280,430),(21,27,30));draw=ImageDraw.Draw(pair)
for i,(name,title) in enumerate([('Driver_WakesOff','Surface relief off'),('Driver_WakesOn','Surface relief on / same physics state')]):
    pair.paste(Image.open(out/(name+'.png')).convert('RGB').resize((640,400),Image.Resampling.LANCZOS),(i*640,30))
    draw.text((i*640+12,4),title,font=font,fill='white')
pair.save(out/'WaveComparison.png')
stats={}
for name in dict.fromkeys(x['case'] for x in r['samples']):
    samples=[x for x in r['samples'] if x['case']==name]
    stats[name]={'samples':len(samples),'max_speed_mps':max(x['speed_mps'] for x in samples),
        'max_wheel_splash_rate':max(x['splash_rate'] for x in samples),'max_bow_spray_rate':max(x['bow_rate'] for x in samples)}
peaks=[tuple(map(float,m)) for m in re.findall(r'modelPeak=([\d.]+)cm upload=\[([-\d.]+),([-\d.]+)\]cm',(out/'Review.log').read_text(errors='replace'))]
result={'car':r['car'],'cases':stats,'paired_same_physics':True,'animation_frames':len(frames),'animation_seconds':sum(durations)/1000,
    'max_uploaded_positive_relief_cm':max(p[2] for p in peaks)}
(out/'preview-report.json').write_text(json.dumps(result,indent=2));print(json.dumps(result,indent=2))
