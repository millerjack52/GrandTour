"""Coherent periodic rock and moss texture bake; centimetres, no geometry."""
from pathlib import Path
import json
import numpy as np
from PIL import Image
ROOT=Path(__file__).resolve().parents[2]
OUT=ROOT/'Art/Export/LidarStudy/FirstSection/ForestFloorRevision/Textures'
rng=np.random.default_rng(20261109)
N=1024;SPAN=200.
y,x=np.mgrid[:N,:N].astype(np.float32)*SPAN/N


def noise(cells):
    grid=rng.random((cells,cells)).astype(np.float32)
    v=np.arange(N,dtype=np.float32)*cells/N;i=v.astype(int);f=v-i;f=f*f*(3-2*f)
    a=grid[i[:,None]%cells,i[None,:]%cells]*(1-f[None,:])+grid[i[:,None]%cells,(i[None,:]+1)%cells]*f[None,:]
    b=grid[(i[:,None]+1)%cells,i[None,:]%cells]*(1-f[None,:])+grid[(i[:,None]+1)%cells,(i[None,:]+1)%cells]*f[None,:]
    return a*(1-f[:,None])+b*f[:,None]


def smooth(a,b,value):
    t=np.clip((value-a)/(b-a),0,1);return t*t*(3-2*t)


def save(name,values,colour=False):
    values=np.clip(values,0,1);assert np.isfinite(values).all()
    if colour:values=np.where(values<=.0031308,12.92*values,1.055*values**(1/2.4)-.055)
    Image.fromarray(np.uint8(np.rint(values*255))).save(OUT/name)


def normal_from_height(height):
    pixel=SPAN/N
    gx=(np.roll(height,-1,1)-np.roll(height,1,1))/(2*pixel)
    gy=(np.roll(height,-1,0)-np.roll(height,1,0))/(2*pixel)
    normal=np.stack([-gx,gy,np.ones_like(height)],-1)
    normal/=np.linalg.norm(normal,axis=-1)[...,None]
    assert np.isfinite(normal).all()
    assert np.max(np.abs(np.linalg.norm(normal,axis=-1)-1))<1e-5
    return normal*.5+.5


macro,medium,fine=noise(5),noise(24),noise(192)
warp_x=(noise(12)-.5)*5+(noise(42)-.5)*1.7;warp_y=(noise(14)-.5)*5+(noise(46)-.5)*1.7
# Overlapping eroded fracture faces, not a closed cellular crack grid.
erosion=np.zeros_like(x);edges=np.zeros_like(x)
for _ in range(110):
    cx,cy=rng.uniform(0,SPAN,2);angle=rng.uniform(0,np.pi)
    rx,ry=rng.uniform(3,13),rng.uniform(2,8)
    dx=(x-cx+warp_x+SPAN/2)%SPAN-SPAN/2;dy=(y-cy+warp_y+SPAN/2)%SPAN-SPAN/2
    u=(dx*np.cos(angle)+dy*np.sin(angle))/rx;v=(-dx*np.sin(angle)+dy*np.cos(angle))/ry
    theta=np.arctan2(v,u);phase0=rng.uniform(0,6.28)
    outline=1+.19*np.sin(theta*3+phase0)+.13*np.sin(theta*5-phase0)+.06*np.sin(theta*9)
    radius=(np.abs(u)**2.4+np.abs(v)**2.4)**(1/2.4)/outline
    # A sloping, chipped face with a torn shoulder, rather than a flat-bottom pit.
    face=(1-smooth(.15,1.,radius))*np.clip(.7+.35*u+.18*v,.2,1.2)
    erosion=np.maximum(erosion,face*rng.uniform(.45,1.25))
    edges=np.maximum(edges,np.exp(-((radius-.77)/.18)**2)*.45)
# Interrupted mineral bedding follows the same physical weathering field.
phase=2*np.pi*(x*3+y*5)/SPAN+1.8*(noise(7)-.5)
mineral=smooth(.1,.82,.5+.5*np.sin(phase))
seam=(1-smooth(.02,.11,np.abs(np.sin(phase))))*smooth(.45,.78,noise(11))
pits=smooth(.52,.86,noise(110))*.13
h=1.4*macro+.85*(noise(18)-.5)+.40*(noise(45)-.5)+.12*(noise(100)-.5)-erosion-.07*seam-pits+.045*(fine-.5)
save('T_RockWeather_Normal.png',normal_from_height(h))
cavity=np.clip(erosion/1.25,0,1)
pigment=.76+.40*macro+.18*mineral-.22*cavity+.16*edges+.16*(fine-.5)
colour=np.array([.095,.112,.118])*pigment[...,None]
stain=seam*.12+cavity*smooth(.58,.82,macro)*.12
colour=colour*(1-stain[...,None])+np.array([.115,.075,.045])*stain[...,None]
inclusions=smooth(.69,.86,fine)*.10
colour=colour*(1-inclusions[...,None])+np.array([.23,.24,.22])*inclusions[...,None]
save('T_RockWeather_Colour.png',colour,colour=True)
rough=np.clip(.68+.16*cavity+.09*medium-.07*mineral,.57,.92)
ao=np.clip(1-.20*cavity-.12*seam,.72,1)
height=(h-h.min())/(h.max()-h.min())
save('T_RockWeather_RAH.png',np.stack([rough,ao,height],-1))

# Small tuft rosettes: radial leaf ridges within irregular cushions. All baked.
cells=85;ux,uy=x/SPAN*cells,y/SPAN*cells
ix,iy=np.floor(ux).astype(int),np.floor(uy).astype(int)
jitter=rng.uniform(.2,.8,(cells,cells,2));leaf=np.zeros_like(x)
for oy in (-1,0,1):
    for ox in (-1,0,1):
        j=jitter[(iy+oy)%cells,(ix+ox)%cells]
        dx,dy=ux-(ix+ox+j[...,0]),uy-(iy+oy+j[...,1])
        radius=np.sqrt(dx*dx+dy*dy);angle=np.arctan2(dy,dx)
        ridges=(.5+.5*np.cos(angle*7+radius*4))**7
        leaf=np.maximum(leaf,np.exp(-radius*radius*4)*(.28+.72*ridges))
coverage=.6*noise(13)+.25*noise(41)+.15*noise(120)
mh=.30*leaf+.07*noise(180)
save('T_RockMoss_Normal.png',normal_from_height(mh))
mcolour=np.array([.025,.052,.009])+leaf[...,None]*np.array([.065,.092,.018])
mcolour*=(.72+.5*noise(22))[...,None]
save('T_RockMoss_Colour.png',mcolour,colour=True)
save('T_RockMoss_Data.png',np.stack([coverage,.9+.08*(1-leaf),leaf],-1))
(OUT/'bake.json').write_text(json.dumps(dict(resolution=N,tile_span_cm=SPAN,
    height_range_cm=[float(h.min()),float(h.max())],normal='Tangent +Y/OpenGL, non-colour',
    packed='Rock: R roughness G cavity B height. Moss: R coverage G roughness B tuft height',
    colour='sRGB encoded from linear pigment, no directional lighting',
    source='Art/tools/bake_rock_surface_detail.py',validated_finite_unit_normals=True,
    tiling='Periodic source noise, wrapped erosion features and tuft cells',
    runtime_displacement=False),indent=2))
print('ROCK_SURFACE_DETAIL_BAKED',OUT)
