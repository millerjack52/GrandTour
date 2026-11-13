"""Numeric authoring for an isolated 53 m winding mud road; centimetres throughout."""
import json, math
from pathlib import Path
from make_mud_proving_ground import N, png, noise, smooth
ROOT=Path(__file__).resolve().parents[2];OUT=ROOT/'Art/Export/MudRoad'
SIZE=6300.;ORIGIN=-3150.;WATER=-26*50/255

def centre(x):return 530*math.sin((x+2200)/1050)-150

def heading(x):return math.degrees(math.atan(530/1050*math.cos((x+2200)/1050)))

def build():
    OUT.mkdir(parents=True,exist_ok=True)
    rest=bytearray();paint=bytearray();wet=0;road=0;low=100;high=-100
    for j in range(N):
        y=ORIGIN+(j+.5)*SIZE/N
        for i in range(N):
            x=ORIGIN+(i+.5)*SIZE/N;dy=y-centre(x)
            d=dy/math.sqrt(1+(530/1050*math.cos((x+2200)/1050))**2)
            width=245+30*math.sin(x/340)+20*noise(x/80,2,4)
            cover=(1-smooth(width,width+125,abs(d)))*(1-smooth(2530,2870,abs(x)))
            # Raised crown, irregular old wheel ruts, and a soft broken shoulder.
            rough=2.8*(noise(x/70,y/90,91)-.5)+1.4*(noise(x/20,y/24,93)-.5)
            h=3+rough+2.5*math.sin(x/340)
            for side in [-1,1]:
                wander=10*math.sin(x/180+side)+7*(noise(x/100,side,7)-.5)
                rut=math.exp(-((d-side*83-wander)/32)**2)
                h-=(5+4*noise(x/175,side,8))*rut*smooth(-2250,-1900,x)
            # Asymmetric pools: small broken puddles, a soft corner, then a flooded dip.
            basin=0
            for cx,off,rx,ry,depth in [(-1330,-65,210,110,12),(-940,100,150,92,15),(-350,-100,200,110,17),(650,5,340,240,23),(1530,80,180,115,13)]:
                xx=x+(noise(x/130,y/170,40)-.5)*75
                dd=d+(noise(x/150,y/110,41)-.5)*45
                basin=max(basin,depth*math.exp(-1.25*(((xx-cx)/rx)**2+((dd-off)/ry)**2)))
            h=(h-basin)*cover
            # Keep the entry/exit stable and broad enough to turn around.
            soft=(.57+.28*noise(x/370,y/260,18)+.12*smooth(4,20,basin))*cover
            soft*=.48+.52*smooth(-2250,-1800,x)
            depth=(22+20*smooth(.2,.85,soft))*cover
            h=max(-depth,min(12,h));q=round((h+50)/65*65535)
            rest.extend((q>>8,q&255,0,255));paint.extend((round(depth/50*255),26,0,round(soft*255)))
            if cover>.5:
                road+=1;wet+=h<WATER;low=min(low,h);high=max(high,h)
    png(OUT/'world-rest.png',rest);png(OUT/'soil-paint.png',paint)
    points=[dict(x=x,y=centre(x),yaw=heading(x)) for x in range(-2450,2451,100)]
    recover=[dict(x=x,y=centre(x),yaw=heading(x),z=100) for x in [-2450,-1600,100]]
    length=sum(math.hypot(b['x']-a['x'],b['y']-a['y']) for a,b in zip(points,points[1:]))/100
    r=dict(size_cm=SIZE,origin_cm=[ORIGIN,ORIGIN],water_level_cm=WATER,resolution=N,route_length_m=length,points=points,recovery=recover,
        height_range_cm=[low,high],wet_area_m2=wet*(SIZE/N)**2/10000,road_area_m2=road*(SIZE/N)**2/10000)
    assert 15<r['wet_area_m2']<110 and -40<low<-15 and length>50,r
    (OUT/'authoring.json').write_text(json.dumps(r,indent=2));print({k:v for k,v in r.items() if k not in ('points','recovery')})
if __name__=='__main__':build()
