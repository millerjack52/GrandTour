"""Unique physical height/paint data for a loose and compacted sand crossing."""
import json,math,random
from pathlib import Path
from make_mud_proving_ground import noise,smooth,png
OUT=Path(__file__).resolve().parents[2]/'Art/Export/SandTerrain'
N=512;SIZE=3150.;ORIGIN=-1575.
def build():
    OUT.mkdir(parents=True,exist_ok=True);rest=bytearray();paint=bytearray();lo=99;hi=-99
    rng=random.Random(82014)
    piles=[(rng.uniform(-1300,1300),rng.uniform(-560,60),rng.uniform(38,92),rng.uniform(45,105),rng.uniform(12,25)) for _ in range(65)]
    for j in range(N):
        y=ORIGIN+(j+.5)*SIZE/N
        for i in range(N):
            x=ORIGIN+(i+.5)*SIZE/N
            bend=(noise(x/420,2,731)-.5)*110
            cover=(1-smooth(1280,1470,abs(x)))*(1-smooth(630,840,abs(y-bend)))
            compact=smooth(70,250,y-bend)
            soft=(.88+.09*noise(x/220,y/300,712))*(1-compact)+(.22+.07*noise(x/240,y/260,741))*compact
            depth=(38*(1-compact)+12*compact)*cover
            # Broad rounded piles with a low, wandering centre, never the mud's torn clods.
            h=-12+12*(noise(x/310,y/220,811)-.5)+5*(noise(x/85,y/105,812)-.5)
            h+=2.0*(noise(x/22,y/31,813)-.5)
            for px,py,sx,sy,height in piles:
                if abs(x-px)<sx*2 and abs(y-py)<sy*2:
                    h+=height*math.exp(-((x-px)/sx)**2-((y-py)/sy)**2)*(1-compact)
            outer=abs(y-bend)
            h+=12*math.exp(-((outer-600)/115)**2)*(.55+.45*noise(x/180,3,815))
            # Faint old paths in the firmer lane, fading independently along the route.
            for side in (-1,1):
                centre=335+side*83+24*(noise(x/300,side,816)-.5)
                h-=2.5*math.exp(-((y-centre)/32)**2)*smooth(.15,.7,noise(x/260,side,817))*compact
            h*=1-.58*compact;h=max(-19,min(14,h))*cover
            lo=min(lo,h);hi=max(hi,h)
            q=round((h+50)/65*65535);rest.extend((q>>8,q&255,0,255))
            paint.extend((round(depth/50*255),255,0,round(soft*cover*255)))
    png(OUT/'sand-rest.png',rest);png(OUT/'sand-paint.png',paint)
    (OUT/'authoring-report.json').write_text(json.dumps(dict(resolution=N,size_cm=SIZE,height_range_cm=[lo,hi],loose_lane_y=-280,packed_lane_y=350,loose_depth_cm=38,packed_depth_cm=12),indent=2))
if __name__=='__main__':build()
