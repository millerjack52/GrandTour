"""Shared moss outlines for fitted geometry and the bank's unique coverage mask."""
import math, random, json
from pathlib import Path
import bpy
import numpy as np
from mathutils import Vector

def build(g,L,S,ground,clear,out):
    rng=random.Random(818043);islands=[]
    for attempt in range(2400):
        a=rng.uniform(-960,960);b=rng.uniform(-630,630)
        if S.rock(a,b)>.28:continue
        wx,wy=S.xy(a,b);x=(wx-S.CX)/100;y=-(wy-S.CY)/100
        q=ground(x,y)
        if q is None or not clear(q,.14):continue
        tier=rng.random()
        rx=rng.uniform(.08,.22) if tier<.48 else rng.uniform(.23,.49) if tier<.88 else rng.uniform(.50,.78)
        ry=rx*rng.uniform(.35,1.5);angle=rng.uniform(0,math.tau);phase=rng.uniform(0,math.tau)
        if islands and rng.random()<.42:
            parent=rng.choice(islands);t=rng.random()*math.tau
            x=parent['x']+math.cos(t)*(parent['rx']+rx)*.82;y=parent['y']+math.sin(t)*(parent['ry']+ry)*.82
            wx=S.CX+x*100;wy=S.CY-y*100;a,b=S.uv(wx,wy);q=ground(x,y)
            if q is None or not S.inside(wx,wy,100) or S.rock(a,b)>.28 or not clear(q,.12):continue
        if any((x-i['x'])**2+(y-i['y'])**2 < (.30*(rx+i['rx']))**2 for i in islands):continue
        height=rng.uniform(.012,.050)*min(1,rx/.25);vs=[];cols=[];valid=True
        # Rings share the irregular outline used by the material coverage bake.
        for ring,r in enumerate([1.,.80,.46,.08]):
            for j in range(16):
                t=j*math.tau/16;shape=1+.26*math.sin(3*t+phase)+.16*math.cos(5*t-phase)
                px=math.cos(t)*rx*shape*r;py=math.sin(t)*ry*shape*r
                xx=x+px*math.cos(angle)-py*math.sin(angle);yy=y+px*math.sin(angle)+py*math.cos(angle)
                hit=ground(xx,yy)
                if hit is None:valid=False;break
                z=height*max(0,1-r*r)**.62-.006
                if z>0 and not clear(hit,z+.015):valid=False;break
                hit.z+=z;vs.append(hit)
                tint=.82+.18*math.sin(t*3+phase)+.11*math.cos(t*5-phase)
                shade=[.80,.95,1.,1.03][ring]
                cols.append(tuple(v*tint*shade for v in (.105,.137,.030)))
            if not valid:break
        if not valid:continue
        faces=[]
        for ring in range(3):
            for j in range(16):
                k=ring*16+j;kn=ring*16+(j+1)%16
                faces.append((k,kn,kn+16,k+16))
        faces.append(tuple(48+j for j in range(16)))
        g.add(vs,faces,cols,None,0)
        islands.append(dict(x=x,y=y,rx=rx,ry=ry,angle=angle,phase=phase,height=height))
        if len(islands)>=350:break
    # Blender images use bottom-to-top pixel rows. Match FernFloor contact UV.
    W=1024;aa=(np.arange(W)+.5)/W*2200-1100;bb=(np.arange(W)+.5)/W*1560-780
    a,b=np.meshgrid(aa,bb);xx=(.6*a-.8*b)/100;yy=(.8*a+.6*b)/100
    mask=np.zeros((W,W),np.float32)
    for item in islands:
        dx=xx-item['x'];dy=yy-item['y'];co=math.cos(item['angle']);si=math.sin(item['angle'])
        px=(dx*co+dy*si)/item['rx'];py=(-dx*si+dy*co)/item['ry'];t=np.arctan2(py,px)
        shape=1+.26*np.sin(3*t+item['phase'])+.16*np.cos(5*t-item['phase'])
        distance=np.sqrt(px*px+py*py)/shape
        # Texture extends 2-4 cm under the buried fringe, never a large green halo.
        coverage=np.clip((1.08-distance)/.20,0,1);coverage=coverage*coverage*(3-2*coverage)
        mask=np.maximum(mask,coverage)
    # Dampness is local ground concavity, not an arbitrary worldwide elevation band.
    wet=np.zeros((W,W),np.float32)
    for j in range(0,W,4):
        for k in range(0,W,4):
            x=float(xx[j,k]);y=float(yy[j,k]);p=ground(x,y)
            if p is None:continue
            neighbours=[ground(x+dx,y+dy) for dx,dy in [(.12,0),(-.12,0),(0,.12),(0,-.12)]]
            if any(v is None for v in neighbours):continue
            concave=sum(v.z for v in neighbours)/4-p.z
            value=max(0,min(1,(concave-.007)/.035))*(1-float(mask[j,k]))
            wet[j:j+4,k:k+4]=value
    pixels=np.stack([mask,wet,np.zeros_like(mask),np.ones_like(mask)],axis=-1).astype('float32')
    im=bpy.data.images.new('T_PM_Coverage',width=W,height=W,alpha=True)
    im.colorspace_settings.name='Non-Color';im.pixels.foreach_set(pixels.ravel());im.filepath_raw=str(out/'T_PM_Coverage.png');im.file_format='PNG';im.save()
    record=dict(islands=islands,coverage_fraction=float(np.mean(mask>.5)),resolution=W,space='bank a [-1100,1100], b [-780,780]; UV y reversed',seed=818043)
    (out/'islands.json').write_text(json.dumps(record,indent=2))
    print('PEAT_MOSS_ISLANDS',len(islands),'coverage',record['coverage_fraction'],flush=True)
    return len(islands)
