"""Make a colour/coverage stamp for LiDAR's forest shoulders. The terrain supplies fine normals."""
import math
import argparse
from pathlib import Path
import numpy as np
from PIL import Image, ImageDraw, ImageFilter

size = 512
rng = np.random.default_rng(231126)
Y, X = np.mgrid[-1:1:complex(size), -1:1:complex(size)]
def noise(cells):
    cells = rng.integers(0,256,(cells,cells),dtype=np.uint8)
    return np.asarray(Image.fromarray(cells).resize((size,size),Image.Resampling.BICUBIC))/255.
broad,medium,fine=noise(5),noise(17),noise(111)
mask=np.clip((.96 - np.hypot(X+.085*np.sin(Y*5),Y*1.02)+(broad-.5)*.43+(medium-.5)*.18)*4.4,0,1)
mask*=np.clip((1-np.maximum(abs(X),abs(Y)))*16.,0,1)
moss=np.clip((broad*.65+medium*.35-.37)*3.1,0,1)[...,None]
soil=np.array([76,59,44]); green=np.array([96,103,56])
pigment=(soil*(1-moss)+green*moss)*(0.75+.25*medium[...,None]+.16*fine[...,None])
im=Image.fromarray(np.uint8(pigment.clip(0,255))).convert('RGB')
pen=ImageDraw.Draw(im,'RGBA')
for _ in range(950):
    x,y=rng.uniform(0,size,2); ix,iy=min(size-1,int(x)),min(size-1,int(y))
    if moss[iy,ix,0]>.65 or mask[iy,ix]<.1:continue
    a=rng.uniform(0,math.tau); reach=rng.uniform(2.8,6.5); w=reach*rng.uniform(.25,.42)
    dx,dy=np.cos(a),np.sin(a)
    pts=[(x+dx*reach,y+dy*reach),(x-dy*w,y+dx*w),(x-dx*reach,y-dy*reach),(x+dy*w,y-dx*w)]
    colour=[(111,87,55,145),(139,105,62,135),(82,67,45,120)][int(rng.integers(3))]
    pen.polygon(pts,fill=colour)
im.putalpha(Image.fromarray(np.uint8(175*mask)))
parser=argparse.ArgumentParser(description=__doc__)
parser.add_argument('--output-dir',type=Path,default=Path(__file__).resolve().parents[3]/'Saved/ForestAccessBend')
out=parser.parse_args().output_dir/'T_ForestAccessFloor.tga'
out.parent.mkdir(parents=True, exist_ok=True)
im.save(out)

# Periodic moss cushions and leaf pockets at a physical scale of four metres.
# RGB channels encode broad cover, cushion shading and dry litter separately.
def periodic(cells):
    g=rng.random((cells,cells))
    uv=np.arange(size)*cells/size
    i=uv.astype(int);w=uv-i
    w=w*w*(3-2*w)
    a=g[i[:,None],i[None,:]]*(1-w)+g[i[:,None],(i[None,:]+1)%cells]*w
    b=g[(i[:,None]+1)%cells,i[None,:]]*(1-w)+g[(i[:,None]+1)%cells,(i[None,:]+1)%cells]*w
    return a*(1-w[:,None])+b*w[:,None]

cover=.63*periodic(5)+.26*periodic(11)+.11*periodic(22)
cushion=.53*periodic(17)+.32*periodic(39)+.15*periodic(81)
litter=Image.new('L',(size,size))
brush=ImageDraw.Draw(litter)
for _ in range(1300):
    x,y=rng.uniform(0,size,2)
    if cover[int(y),int(x)]>.58:continue
    a=rng.uniform(0,math.tau)
    dx,dy=math.cos(a),math.sin(a)
    length=rng.uniform(2,6);width=length*rng.uniform(.24,.44)
    shape=[(dx*length,dy*length),(-dy*width,dx*width),(-dx*length,-dy*length),(dy*width,-dx*width)]
    shade=int(rng.integers(100,245))
    for xx in (-size,0,size):
        for yy in (-size,0,size):
            brush.polygon([(x+xx+a,y+yy+b) for a,b in shape],fill=shade)
field=np.dstack((cover,cushion,np.asarray(litter)/255))
Image.fromarray(np.uint8(field*255)).save(out.with_name('T_BendMossLitterFields.tga'))

# A repeatable 72 cm swatch. Paint overlapping fronds in rosettes; the three
# channels carry colony shape, tip pigment and relief in a single masked texture.
def moss_swatch():
    cover = .64 * periodic(6) + .25 * periodic(13) + .11 * periodic(31)
    relief = np.array(cover * .48)
    tips = np.zeros_like(cover)
    for _ in range(420):
        x, y = rng.uniform(0, size, 2)
        phase = rng.uniform(0, math.tau)
        radius = rng.uniform(5, 18)
        for n in range(7):
            angle = phase + n * 2.4 + rng.uniform(-.27, .27)
            c, s = math.cos(angle), math.sin(angle)
            length = radius * rng.uniform(.6, 1.15)
            width = length * rng.uniform(.14, .25)
            r = math.ceil(length + width + 1)
            iy, ix = np.mgrid[int(y)-r:int(y)+r+1, int(x)-r:int(x)+r+1]
            along = ((ix-x)*c + (iy-y)*s) / length
            across = (-(ix-x)*s + (iy-y)*c) / width
            profile = np.maximum(0., 1.-abs(across-.36*along**2)
                                 / np.maximum(.10, np.sin(np.pi*np.clip(along, 0, 1))**.67))
            profile *= (along>0) & (along<1)
            idx = (iy % size, ix % size)
            base = cover[int(y), int(x)] * .42
            relief[idx] = np.maximum(relief[idx], (base + profile*.46)*(profile>0))
            tips[idx] = np.maximum(tips[idx], profile*np.clip(.20 + .85*along, 0, 1))
    packed = np.dstack([cover, tips, relief]).clip(0, 1)
    Image.fromarray(np.uint8(packed*255)).save(out.with_name('T_BendMossShoots.tga'))

moss_swatch()
