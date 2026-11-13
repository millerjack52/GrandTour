"""Deterministic seamless rock data maps, in centimetres; no baked lighting."""
from pathlib import Path
import json
import numpy as np
from PIL import Image
ROOT=Path(__file__).resolve().parents[2]
OUT=ROOT/'Art/Export/LidarStudy/FirstSection/ForestFloorRevision/Textures'
OUT.mkdir(parents=True,exist_ok=True)
rng=np.random.default_rng(20261108)
N=1024;SPAN=200.


def noise(cells):
    grid=rng.random((cells,cells)).astype(np.float32)
    v=np.arange(N,dtype=np.float32)*cells/N;i=v.astype(int);f=v-i;f=f*f*(3-2*f)
    a=grid[i[:,None]%cells,i[None,:]%cells]*(1-f[None,:])+grid[i[:,None]%cells,(i[None,:]+1)%cells]*f[None,:]
    b=grid[(i[:,None]+1)%cells,i[None,:]%cells]*(1-f[None,:])+grid[(i[:,None]+1)%cells,(i[None,:]+1)%cells]*f[None,:]
    return a*(1-f[:,None])+b*f[:,None]


h=1.1*noise(10)+.38*noise(34)+.12*noise(128)+.03*noise(256)
y,x=np.mgrid[:N,:N].astype(np.float32)*SPAN/N
pits=np.zeros_like(h)
for _ in range(450):
    cx,cy=rng.uniform(0,SPAN,2);radius=rng.uniform(.28,1.05)
    dx=(x-cx+SPAN/2)%SPAN-SPAN/2;dy=(y-cy+SPAN/2)%SPAN-SPAN/2
    depression=rng.uniform(.05,.18)*np.exp(-((dx/radius)**2+(dy/(radius*.8))**2)*2)
    pits=np.maximum(pits,depression)
h-=pits
for _ in range(65):
    cx,cy=rng.uniform(0,SPAN,2);radius=rng.uniform(2.5,7.)
    dx=(x-cx+SPAN/2)%SPAN-SPAN/2;dy=(y-cy+SPAN/2)%SPAN-SPAN/2
    h-=rng.uniform(.25,.8)*np.exp(-((dx/radius)**2+(dy/(radius*.7))**2)*2)
pixel=SPAN/N
gx=(np.roll(h,-1,1)-np.roll(h,1,1))/(2*pixel)
gy=(np.roll(h,-1,0)-np.roll(h,1,0))/(2*pixel)
normal=np.stack([-gx,gy,np.ones_like(h)],-1);normal/=np.linalg.norm(normal,axis=-1)[...,None]
assert np.isfinite(normal).all()
assert np.max(np.abs(np.linalg.norm(normal,axis=-1)-1))<1e-5
Image.fromarray(np.uint8(np.clip(normal*.5+.5,0,1)*255)).save(OUT/'T_RockWeather_Normal.png')
rough=np.clip(.73+.12*noise(23)+pits*.35,.70,.92)
ao=np.clip(1-pits*1.1,.78,1)
height=(h-h.min())/(h.max()-h.min())
packed=np.stack([rough,ao,height],-1)
Image.fromarray(np.uint8(np.clip(packed,0,1)*255)).save(OUT/'T_RockWeather_RAH.png')
(OUT/'bake.json').write_text(json.dumps(dict(resolution=N,tile_span_cm=SPAN,
    height_range_cm=[float(h.min()),float(h.max())],normal='Tangent space; RGB; non-colour; +Y/OpenGL convention',
    packed='R roughness, G cavity occlusion, B normalized height',
    tiling='Periodic interpolation and wrapped pits; central differences wrap',
    source='Art/tools/bake_rock_weathering.py',validated_finite_unit_normals=True),indent=2))
print('ROCK_WEATHER_MAPS_BAKED',OUT)
