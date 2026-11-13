"""Deterministic inputs for the separate rally handling circuit (metres in JSON)."""
from pathlib import Path
import json
import numpy as np
from PIL import Image, ImageDraw
from scipy.interpolate import CubicSpline
from scipy.spatial import cKDTree

ROOT = Path(__file__).resolve().parents[2]
OUT = ROOT / 'Art/Export/RallyHandling'
OUT.mkdir(parents=True, exist_ok=True)
points = [(-100,-180,0),(0,-180,0),(100,-180,0),(160,-170,0),
          (190,-140,0),(195,-95,0),(165,-55,0),(120,-35,0),
          (105,0,0),(145,25,0),(185,60,0),(175,105,0),
          (135,125,0),(80,125,0),(40,155,0),(0,175,0),
          (-55,175,0),(-90,150,0),(-95,120,0),(-75,100,0),
          (-45,100,0),(-25,80,0),(-45,60,0),(-90,60,0),
          (-135,75,0),(-180,50,0),(-195,0,0),(-195,-70,2.5),
          (-190,-140,0),(-160,-175,0),(-130,-180,0),(-100,-180,0)]
p = np.array(points, dtype=float)
knots = np.r_[0, np.cumsum(np.linalg.norm(np.diff(p, axis=0), axis=1))]
curve = CubicSpline(knots, p, bc_type='natural')
stations = np.linspace(0, knots[-1], int(knots[-1])+1)
samples = curve(stations)
checkpoints = [dict(name=name, index=i) for name,i in [
    ('Start / acceleration',0),('Fast right',2),('Linked bends',6),
    ('Sweeper',11),('Hairpin approach',19),('Crest',26),('Service bay',0)]]
data = dict(version=1, span_cm=50400, origin_cm=-25200, width_cm=900,
            points_m=points, checkpoints=checkpoints, samples_m=samples.tolist(),
            length_m=float(np.linalg.norm(np.diff(samples,axis=0),axis=1).sum()))
(OUT/'course.json').write_text(json.dumps(data,indent=2))
# Owned masks, subsequently painted by the same road author as the LiDAR map.
for name, color in [('paint',(0,255,0,0)),('style',(0,220,20,0)),
                    ('macro',(100,130,65,255)),('clay',(0,0,0,0))]:
    Image.new('RGBA',(1024,1024),color).save(OUT/(name+'.png'))
# RD1's alpha is signed lateral position, not clay. RGB stays zero everywhere.
axis=np.linspace(-252,252,1024)
xx,yy=np.meshgrid(axis,axis);xy=np.stack((xx,yy),axis=-1).reshape(-1,2)
_,nearest=cKDTree(samples[:,:2]).query(xy)
directions=curve(stations,1)[:,:2];directions/=np.linalg.norm(directions,axis=1)[:,None]
delta=xy-samples[nearest,:2]
signed=delta[:,0]*directions[nearest,1]-delta[:,1]*directions[nearest,0]
clay=np.zeros((1024,1024,4),dtype=np.uint8)
clay[:,:,3]=np.rint(np.clip(.5+signed.reshape(1024,1024)/12.8,0,1)*255).astype(np.uint8)
Image.fromarray(clay).save(OUT/'clay.png')
im=Image.new('RGB',(1000,1160),'#152525');d=ImageDraw.Draw(im)
def pixel(q):return (int(500+q[0]*2.1),int(510-q[1]*2.1))
d.text((30,25),'GRAND TOUR / RALLY HANDLING',fill='#f5d49a',font_size=30)
d.text((30,68),f'{data["length_m"]/1000:.2f} km | firm gravel | follow numbered sections from START',fill='white',font_size=21)
d.line([pixel(q) for q in samples],fill='#a9a38b',width=18,joint='curve')
for k,cp in enumerate(checkpoints[:-1],1):
    x,y=pixel(p[cp['index']]);d.ellipse((x-14,y-14,x+14,y+14),fill='#cf6a2f')
    d.text((x-6,y-11),str(k),fill='white',font_size=20)
for k,cp in enumerate(checkpoints,1):
    d.text((30+(k>4)*500,985+((k-1)%4)*35),f'{k}  {cp["name"]}',fill='white',font_size=20)
im.save(OUT/'course.png')
print(f'Prepared {data["length_m"]:.1f} m course')
