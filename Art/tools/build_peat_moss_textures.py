"""Deterministic authored peat/root/leaf relief; colour and packed data share shapes.

No photographic lighting is baked into the albedo. One 1.5m periodic tile; the
unique bank moss coverage is baked separately from the fitted geometry recipe.
"""
from pathlib import Path
import json, math
import numpy as np
from PIL import Image, ImageDraw, ImageFilter

ROOT=Path('C:/GrandTour');OUT=ROOT/'Art/Export/LidarStudy/FirstSection/PeatMoss'
OUT.mkdir(parents=True,exist_ok=True)
N=2048;SPAN=150.;rng=np.random.default_rng(818041)
def noise(size):
    a=rng.uniform(0,1,(size,size)).astype('float32')
    # Wrap a border before interpolation, then crop a complete periodic tile.
    im=Image.fromarray(np.pad(a,1,mode='wrap'),mode='F')
    big=im.resize((N*(size+2)//size,)*2,Image.Resampling.BICUBIC)
    offset=(big.width-N)//2
    return np.asarray(big.crop((offset,offset,offset+N,offset+N))).copy()
coarse=noise(22);fine=noise(160);grain=noise(500)
h=np.clip(.27+.17*coarse+.09*fine+.035*grain,0,1)
colour=np.zeros((N,N,3),np.float32)
colour[:]=[.068,.043,.025]
colour*= (.72+.40*coarse+.16*fine)[...,None]

# Individually shaped peat clods, partially buried, not uniform Voronoi pebbles.
clods=Image.new('L',(N,N));dc=ImageDraw.Draw(clods)
for k in range(1250):
    x,y=rng.uniform(0,N,2);rx=rng.uniform(1.2,5.0)*N/SPAN;ry=rx*rng.uniform(.35,.9)
    angle=rng.uniform(0,math.tau)
    pts=[]
    for j in range(7):
        a=j*math.tau/7;rr=rng.uniform(.72,1.1)
        px=math.cos(a)*rx*rr;py=math.sin(a)*ry*rr
        pts.append((x+px*math.cos(angle)-py*math.sin(angle),y+px*math.sin(angle)+py*math.cos(angle)))
    val=int(rng.integers(75,200))
    for ox in [-N,0,N]:
        for oy in [-N,0,N]:dc.polygon([(a+ox,b+oy) for a,b in pts],fill=val)
cl=np.asarray(clods.filter(ImageFilter.GaussianBlur(1.0)),dtype=np.float32)/255
h+=cl*.19
colour*= (1+cl*.20)[...,None]

# Embedded fibrous root network: centimetre width, coherent colour + height.
roots=Image.new('L',(N,N));dr=ImageDraw.Draw(roots)
for k in range(150):
    x,y=rng.uniform(0,N,2);angle=rng.uniform(0,math.tau);length=rng.uniform(9,48)*N/SPAN
    points=[(x+math.cos(angle)*length*t+math.sin(t*7+k)*length*.055,
             y+math.sin(angle)*length*t+math.cos(t*5+k)*length*.045) for t in np.linspace(0,1,18)]
    width=max(2,int(rng.uniform(.18,.95)*N/SPAN))
    for ox in [-N,0,N]:
        for oy in [-N,0,N]:dr.line([(a+ox,b+oy) for a,b in points],fill=int(rng.integers(150,245)),width=width)
root=np.asarray(roots.filter(ImageFilter.GaussianBlur(.8)),dtype=np.float32)/255
colour=colour*(1-root[...,None]*.75)+np.array([.12,.080,.044])*root[...,None]*.75
h+=root*.24

# Small beech fragments, 1.2-4 cm. Sparse, oval, with a crease on the SAME map.
leaves=Image.new('RGBA',(N,N));dl=ImageDraw.Draw(leaves)
leafheight=Image.new('L',(N,N));dh=ImageDraw.Draw(leafheight)
for k in range(185):
    x,y=rng.uniform(0,N,2);length=rng.uniform(1.2,4)*N/SPAN;angle=rng.uniform(0,math.tau)
    pts=[]
    for j in range(8):
        a=j*math.tau/8;px=math.cos(a)*length*.5;py=math.sin(a)*length*.29
        pts.append((x+px*math.cos(angle)-py*math.sin(angle),y+px*math.sin(angle)+py*math.cos(angle)))
    col=rng.choice([[95,64,32,255],[110,77,39,255],[75,55,32,255]])
    for ox in [-N,0,N]:
        for oy in [-N,0,N]:
            pp=[(a+ox,b+oy) for a,b in pts];dl.polygon(pp,fill=tuple(int(c) for c in col));dh.polygon(pp,fill=110)
            dh.line([pp[0],pp[4]],fill=185,width=2)
la=np.asarray(leaves,dtype=np.float32)/255;lm=la[:,:,3]
# Source literal colours are sRGB; store linear before final encoding.
lc=np.where(la[:,:,:3]<=.04045,la[:,:,:3]/12.92,((la[:,:,:3]+.055)/1.055)**2.4)
colour=colour*(1-lm[...,None])+lc*lm[...,None]
h+=np.asarray(leafheight,dtype=np.float32)/255*.18

# Moss micro-cushions use the colour alpha and packed alpha; no extra sampler.
moss=np.clip(.55*noise(110)+.30*noise(250)+.15*grain,0,1)
moss=np.clip((moss-.23)*1.75,0,1)
height=np.clip(h,0,1)
smooth=np.asarray(Image.fromarray(height,mode='F').resize((192,192),Image.Resampling.BOX).resize((N,N),Image.Resampling.BILINEAR))
cavity=np.clip(.92+(height-smooth)*1.6,.48,1)
rough=np.clip(.83+(1-cavity)*.15-root*.07,.68,.98)
encoded=np.where(colour<=.0031308,colour*12.92,1.055*np.maximum(colour,0)**(1/2.4)-.055)
Image.fromarray(np.uint8(np.clip(np.dstack([encoded,moss]),0,1)*255)).save(OUT/'T_PM_PeatColour.png')
Image.fromarray(np.uint8(np.clip(np.dstack([height,rough,cavity,.65+.35*moss]),0,1)*255)).save(OUT/'T_PM_PeatData.png')
(OUT/'textures.json').write_text(json.dumps(dict(tile_metres=SPAN/100,resolution=N,colour='sRGB RGB peat albedo; linear alpha moss microheight',data='linear RGBA: peat height, roughness, cavity, moss cavity',height_cm=2.2,seed=818041),indent=2))
print('PEAT_TEXTURES_BUILT',OUT)
