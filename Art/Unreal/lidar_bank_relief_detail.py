"""Deterministic centimetre-scale geometric relief, with protected plant contacts."""
import json,math
from pathlib import Path
PATH=Path(__file__).resolve().parents[2]/'Art/Export/LidarStudy/FirstSection/physical-relief.json'
DATA=json.loads(PATH.read_text()) if PATH.exists() else None
BUCKETS={}
if DATA:
 for cap in DATA['caps']:
  key=(math.floor(cap[0]/100),math.floor(cap[1]/100));BUCKETS.setdefault(key,[]).append(cap)

def smooth(v):
 v=max(0.,min(1.,v));return v*v*(3-2*v)
def hash2(x,y):return (math.sin(x*127.1+y*311.7)*43758.5453)%1
def noise(x,y):
 i,j=math.floor(x),math.floor(y);a,b=smooth(x-i),smooth(y-j)
 return (hash2(i,j)*(1-a)+hash2(i+1,j)*a)*(1-b)+(hash2(i,j+1)*(1-a)+hash2(i+1,j+1)*a)*b
def shape(a,b,f):
 x,y,w,h,angle,z=f;ca,sa=math.cos(angle),math.sin(angle)
 u=(a-x)*ca+(b-y)*sa;v=-(a-x)*sa+(b-y)*ca
 d=max(abs(u)/w,abs(v)/h)
 if d>=1.08:return 0.
 d+=.035*math.sin(u*.072+v*.059)
 return z*smooth((1-d)/.26)*(.92+.08*u/w)
def rock_detail(a,b):
 if not DATA:return 0.
 return max([0.]+[shape(a,b,f) for f in DATA['rock_ledges']])
def stone_detail(a,b):
 if not DATA:return 0.
 return max([0.]+[shape(a,b,f) for f in DATA['embedded_stones']])
def additional(x,y):
 if not DATA:return 0.
 dx,dy=x+45800,y+31600;a=.6*dx-.8*dy;b=-.8*dx-.6*dy
 edge=smooth(min((1100-abs(a)-70)/140,(780-abs(b)-70)/140))
 if edge<=0:return 0.
 # Broad root-mat hummocks and smaller clods, deliberately distinct from shader grain.
 soil=4+12*noise(a/95,b/95)+7*noise((a+53)/43,(b-77)/43)
 value=max(soil,rock_detail(a,b),stone_detail(a,b))*edge
 # Store maximum allowed extra height, not a change to the approved plant pose.
 i,j=math.floor(x/100),math.floor(y/100)
 for di in (-1,0,1):
  for dj in (-1,0,1):
   for px,py,allow,radius in BUCKETS.get((i+di,j+dj),[]):
    dist=math.hypot(x-px,y-py)
    if dist<radius+70:value=min(value,allow+max(0.,dist-radius)*.50)
 return max(0.,value)
