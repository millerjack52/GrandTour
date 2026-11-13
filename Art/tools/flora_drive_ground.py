"""Deterministic, shallow forest-floor forms; centimetres, clear of the driving lane."""
import math,random
from make_mud_road import centre
from make_mud_proving_ground import smooth
def pond_delta(x,y):
    r2=((x-900)/700)**2+((y-1050)/500)**2
    return -32*max(0.,1-r2)**1.5*smooth(340,520,abs(y-centre(x)))
def surround_height(x,y):
    return smooth(3150,5800,max(abs(x),abs(y)))*(280+155*math.sin(x/1800+y/2300)+90*math.sin(x/700-y/1200))
rng=random.Random(4117)
MOUNDS=[]
for x in range(-2600,2700,650):
    for side in (-1,1):
        for offset in (800,1900):
            xx=x+rng.uniform(-160,160);yy=centre(xx)+side*(offset+rng.uniform(-100,100))
            if abs(yy)>2550:continue
            if ((xx-900)/900)**2+((yy-1050)/700)**2<1:continue
            MOUNDS.append((xx,yy,rng.uniform(220,350),rng.uniform(160,260),rng.uniform(18,42)))
def ground_height(x,y):
    return max([0.]+[h*max(0.,1-((x-a)/rx)**2-((y-b)/ry)**2)**2 for a,b,rx,ry,h in MOUNDS])
def floor_z(x,y):
    return pond_delta(x,y)+ground_height(x,y)-3 if max(abs(x),abs(y))<3150 else surround_height(x,y)-35
