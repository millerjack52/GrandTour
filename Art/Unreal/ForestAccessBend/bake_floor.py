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
