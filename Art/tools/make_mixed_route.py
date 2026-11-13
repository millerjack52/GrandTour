"""63m eastern extension of the existing road. All geometry is centimetres."""
import json,math
from pathlib import Path
from make_mud_proving_ground import png,N,noise,smooth
from make_mud_road import centre as old_centre
OUT=Path(__file__).resolve().parents[1]/'Export/MudRoad/MixedSurfaces'
ORIGIN=(3150.,-3150.);SIZE=6300.
def route_y(x):return old_centre(3150)+440*math.sin((x-3150)/1300)
def ground(x,y):
 edge=smooth(3150,3550,x)
 hill=210*math.exp(-((x-4550)/950)**2-((y+400)/1600)**2)
 hill+=260*math.exp(-((x-8600)/1100)**2-((y-600)/1800)**2)
 h=(18+hill+9*math.sin(y/550)*math.sin(x/650))*edge
 # Closed pond with an accessible sandy shore.
 q=((x-5550)/950)**2+((y-1550)/720)**2
 h=h*(smooth(.70,1.35,q)) - 90*(1-smooth(0,1.35,q))
 # Meandering river with a shallower crossing at the main route.
 rx=7300+95*math.sin(y/850);d=abs(x-rx)
 bed=-78+48*math.exp(-((y-route_y(x))/420)**2)
 h=h*smooth(220,580,d)+bed*(1-smooth(220,580,d))
 return h*edge
def kind(x,y):
 return 1 if ((x-4250)/1000)**2+((y+450)/1450)**2<1 or (6750<x<7900) or ((x-5550)/1150)**2+((y-1550)/880)**2<1 else 2

def sand_blend(x,y):
 a=(math.sqrt(((x-4250)/1000)**2+((y+450)/1450)**2)-1)*1000
 b=abs(x-7325)-575
 c=(math.sqrt(((x-5550)/1150)**2+((y-1550)/880)**2)-1)*880
 edge=min(a,b,c)+(noise(x/170,y/170,121)-.5)*110
 return 1-smooth(-60,100,edge)
def build():
 OUT.mkdir(parents=True,exist_ok=True);paint=bytearray();rest=bytearray();style=bytearray();macro=bytearray()
 for j in range(N):
  for i in range(N):
   x=ORIGIN[0]+(i+.5)*SIZE/N;y=ORIGIN[1]+(j+.5)*SIZE/N;k=kind(x,y)
   thickness=27 if k==1 else 9
   soft=.78 if k==1 else .44
   border=min(i,j,N-1-i,N-1-j);fade=smooth(0,3,border)
   paint.extend((round(thickness/50*255*fade),255,0,round(soft*255)))
   h=(noise(x/35,y/35,89)-.5)*(1.5 if k==1 else .5)*fade
   v=round((h+50)/65*65535);rest.extend((v>>8,v&255,0,255))
   blend=sand_blend(x,y);style.extend((round(255*blend),round(255*(1-blend)),0,255))
   q=round((ground(x,y)+200)/800*65535);macro.extend((q>>8,q&255,0,255))
 for name,data in [('paint',paint),('rest',rest),('style',style),('macro',macro)]:png(OUT/(name+'.png'),data)
 heights=[ground(ORIGIN[0]+x*50,ORIGIN[1]+y*50) for y in range(127) for x in range(127)]
 points=[dict(x=x,y=route_y(x),z=ground(x,route_y(x)),yaw=math.degrees(math.atan(440/1300*math.cos((x-3150)/1300)))) for x in range(3150,9201,100)]
 r=dict(origin=ORIGIN,size=SIZE,heights_cm=heights,points=points,height_range_cm=[min(heights),max(heights)],
  pond=dict(x=5550,y=1550,level=-5),river=dict(x=7300,y=0,level=.1),
  probes=dict(sand=[4350,route_y(4350)],grass=[5900,route_y(5900)],river=[7300,route_y(7300)],pond=[5550,1550]))
 (OUT/'authoring.json').write_text(json.dumps(r));print({k:v for k,v in r.items() if k not in ['heights_cm','points']})
if __name__=='__main__':build()
