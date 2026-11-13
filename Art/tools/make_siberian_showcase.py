"""Compact authored taiga route. Source map previews inform composition, not a decoded STG copy.
World centimetres; four 63 m terrain tiles preserve the existing 12.5 cm visual grid.
"""
from pathlib import Path
import json, math
try:import numpy as np
except ImportError:
 # Unreal's embedded interpreter needs only scalar terrain queries.
 class Scalar:
  sin=staticmethod(math.sin);cos=staticmethod(math.cos);exp=staticmethod(math.exp);sqrt=staticmethod(math.sqrt);abs=staticmethod(abs)
  minimum=staticmethod(min);maximum=staticmethod(max)
  @staticmethod
  def clip(v,a,b):return max(a,min(b,v))
  @staticmethod
  def zeros_like(v,dtype=None):return 0.
 np=Scalar()

OUT=Path(__file__).resolve().parents[1]/'Export/SiberianShowcase'
SIZE=6300.; N=512
TILES=[('SW',-6300,-6300,True,30.),('SE',0,-6300,True,30.),('NW',-6300,0,False,None),('NE',0,0,False,160.)]
def smooth(a,b,v):
 t=np.clip((v-a)/(b-a),0,1);return t*t*(3-2*t)
def river_y(x):return 1450+560*np.sin(x/1700)+180*np.sin(x/570)+70*np.cos(x/270)
def spline(points,closed=True,sub=5):
 result=[];n=len(points)
 for i in range(n if closed else n-1):
  p0,p1,p2,p3=[points[j%n if closed else min(n-1,max(0,j))] for j in [i-1,i,i+1,i+2]]
  for k in range(sub):
   t=k/sub;result.append(tuple(.5*(2*b+(-a+c)*t+(2*a-5*b+4*c-d)*t*t+(-a+3*b-3*c+d)*t*t*t) for a,b,c,d in zip(p0,p1,p2,p3)))
 result.append(result[0] if closed else points[-1]);return result
ROAD=spline([(-4700,-2800),(-3900,-4050),(-2300,-4600),(-650,-4050),(1200,-4400),(3000,-3400),(4200,-2450),(4700,-450),(3950,1200),(4400,2600),(2800,3350),(1600,4900),(-200,4600),(-2000,3500),(-3800,4200),(-4800,2850),(-4200,1000),(-5000,-800)])
SHORT=spline([(-4750,-1800),(-3100,-1900),(-1300,-1450),(200,-2650),(1800,-2350),(2900,-1300),(4580,-400)],False)
def path_distance(x,y,points):
 best=1.e12
 for (ax,ay),(bx,by) in zip(points,points[1:]):
  dx,dy=bx-ax,by-ay;t=np.clip(((x-ax)*dx+(y-ay)*dy)/(dx*dx+dy*dy),0,1)
  best=np.minimum(best,(x-ax-t*dx)**2+(y-ay-t*dy)**2)
 return np.sqrt(best)
def road_distance(x,y):
 return np.minimum(path_distance(x,y,ROAD),path_distance(x,y,SHORT))
def pond_q(x,y,cx,cy,rx,ry):
 # Domain-warped bowls: unequal lobes, coves and narrow projecting banks.
 dx=(x-cx)+140*np.sin((y-cy)/280)+85*np.cos((x-cx)/190)
 dy=(y-cy)+170*np.sin((x-cx)/380)+65*np.sin((y-cy)/160)
 return (dx/rx)**2+(dy/ry)**2+.13*np.sin(x/175)*np.cos(y/135)
def fords():
 result=[]
 for a,b in zip(ROAD,ROAD[1:]):
  da=a[1]-float(river_y(a[0]));db=b[1]-float(river_y(b[0]))
  if da*db<0:
   t=da/(da-db);x=a[0]+(b[0]-a[0])*t;result.append((x,float(river_y(x)),math.degrees(math.atan2(b[1]-a[1],b[0]-a[0]))))
 return sorted(result)
FORDS=fords()
PUDDLES=[(-3900,-4050),(-650,-4050),(-4700,-2800)]
def pond_shelf(x,y,h,cx,cy,rx,ry,level,pocket_x,pocket_y):
 # Authored shallows, not decoded source STG geometry. An off-centre pocket
 # breaks the concentric bowl; a broad wet shelf meets a gently rising bank.
 q=np.maximum(0,pond_q(x,y,cx,cy,rx,ry))
 pocket=np.exp(-((x-cx-pocket_x)/(rx*.38))**2-((y-cy-pocket_y)/(ry*.45))**2)
 bed=level-9-21*(1-smooth(.05,.8,q))-13*pocket
 bed+=14*smooth(.2,1.1,q)+30*smooth(1,1.8,q)
 bed+=1.5*np.sin((x-cx)/210)*np.cos((y-cy)/170)
 w=1-smooth(.95,2.5,q)
 return h*(1-w)+bed*w

def ground(x,y):
 h=145+110*np.sin(x/2900)*np.sin(y/2300)+120*np.exp(-((x+4500)/2200)**2-((y-4100)/1900)**2)
 h+=190*np.exp(-((x-4800)/1800)**2-((y+4300)/1800)**2)
 # The northern pond is perched above the river, separated by an intact berm.
 h+=110*np.exp(-((x-3900)/2400)**2-((y-4500)/1700)**2)
 h=pond_shelf(x,y,h,-2500,-900,1050,730,30,-240,100)
 h=pond_shelf(x,y,h,3900,4500,1000,760,160,190,-160)
 # Broad muddy bog: variable shallows with intact raised hummocks.
 q=pond_q(x,y,2300,-2070,1400,900);w=1-smooth(.25,1.5,q)
 bog=28+7*np.sin(x/190)*np.cos(y/240)+8*np.sin(y/380)
 h=h*(1-w)+bog*w
 # Broken puddles on the firm western/southern track.
 for cx,cy in PUDDLES:
  q=((x-cx)/800)**2+((y-cy)/760)**2;w=1-smooth(.15,2.8,q);h=h*(1-w)+42*w
 d=np.abs(y-river_y(x));width=370+100*np.sin(x/1050)+170*np.exp(-((x+1200)/950)**2)
 ford=np.maximum(np.exp(-((x-FORDS[0][0])/620)**4),np.exp(-((x-FORDS[-1][0])/620)**4))
 # A wandering deeper thread through broad shallow margins, with shallower fords.
 channel_depth=30+7*np.sin(x/1100)+9*np.exp(-((x+1800)/850)**2)
 channel_depth=channel_depth*(1-ford)+(17+3*np.sin(x/700))*ford
 offset=100*np.sin(x/850)+70*np.cos(x/1450)
 core=np.exp(-((y-river_y(x)-offset)/(width*.55))**2)
 bed=-10-(channel_depth-10)*core+22*smooth(width*.65,width+280,d)
 bank=width+140*np.sin(x/300)+70*np.cos(x/125)
 w=1-smooth(width+40,bank+650+500*ford,d);h=h*(1-w)+bed*w
 # Low gravel/mud bar splits the broad middle reach into uneven channels.
 q=((x+1100)/630)**2+((y-river_y(x)-50)/160)**2;island=(1-smooth(.15,1.5,q));h=h*(1-island)+(18+9*np.sin(x/170))*island
 # Gentle closed outer rim, hiding the finite study's edge behind forest.
 h+=240*smooth(4900,6300,np.maximum(np.abs(x),np.abs(y)))*smooth(900,1350,d)
 return h
def masks(x,y):
 d=road_distance(x,y);width=185+35*np.sin(x/260)+25*np.sin(y/180);road=1-smooth(width,width+115,d+15*np.sin(x/43)*np.cos(y/57))
 rd=np.abs(y-river_y(x));sand=(1-smooth(570+90*np.sin(x/300),930+100*np.sin(x/500),rd))*(y>0)
 pq=pond_q(x,y,3900,4500,1000,760);sand=np.maximum(sand,(1-smooth(1.1,2.1,pq))*(y>0))
 bog=1-smooth(.5,1.5,pond_q(x,y,2300,-2070,1400,900))
 pond=1-smooth(.8,1.9,pond_q(x,y,-2500,-900,1050,730))
 grass=(1-road)*(1-sand)*(1-bog)*(1-pond)
 # Keep the recovered sand overlay on exposed bank; blend the same source mud
 # colour into saturated margins instead of a uniform pale ring around water.
 sand*=.50+.50*smooth(30,150,ground(x,y))
 patches=np.zeros_like(x+y,dtype=float)
 for cx,cy in PUDDLES+[(2800,-3150)]:
  patches=np.maximum(patches,np.exp(-(((x-cx)/450)**2+((y-cy)/500)**2)))
 depth=6*grass+2*(1-grass)
 depth=np.maximum(depth,24*sand);depth=np.maximum(depth,(85+25*np.sin(x/420)**2*np.cos(y/360)**2)*bog);depth=np.maximum(depth,60*pond);depth=np.maximum(depth,30*patches)
 soft=.24+.2*grass+.4*sand+.67*bog+.35*pond+.48*patches
 soft=np.clip(soft,.18,.96)
 # Initial track hollows are centimetres relative to the landscape collision bed.
 rest=-(2+12*patches+5*bog)*road*np.exp(-((d-83)/32)**2)
 rest+=.8*np.sin(x/32)*np.sin(y/43)*np.minimum(1,depth/8)
 return sand,grass,depth,soft,rest
def routepoint(t):return ROAD[int((t%math.tau)/math.tau*(len(ROAD)-1))]
def build():
 from PIL import Image, ImageDraw
 OUT.mkdir(parents=True,exist_ok=True);report={'tiles':[],'source_scope':'Original installed map DDS previews and existing recovered terrain/particle programs. Authored compact layout; STG topology not decoded.'}
 for name,ox,oy,native,water in TILES:
  p=OUT/name;p.mkdir(exist_ok=True);x,y=np.meshgrid(ox+(np.arange(N)+.5)*SIZE/N,oy+(np.arange(N)+.5)*SIZE/N)
  sand,grass,depth,soft,rest=masks(x,y);edge=np.minimum.reduce([x-ox,y-oy,ox+SIZE-x,oy+SIZE-y]);fade=smooth(0,30,edge)
  depth*=fade;rest*=fade;rgba=np.zeros((N,N,4),np.uint8);rgba[:,:,0]=np.rint(np.clip(depth/124,0,1)*255);rgba[:,:,1]=255;rgba[:,:,3]=np.rint(soft*255)
  rgba[[0,-1],:,0]=0;rgba[:,[0,-1],0]=0;Image.fromarray(rgba).save(p/'paint.png')
  def packed(name,value):
   v=np.rint(value*65535).clip(0,65535).astype(np.uint16);a=np.zeros((N,N,4),np.uint8);a[:,:,0]=v>>8;a[:,:,1]=v&255;a[:,:,3]=255;Image.fromarray(a).save(p/(name+'.png'))
  packed('rest',(rest+50)/65);packed('macro',(ground(x,y)+200)/800)
  a=np.zeros((N,N,4),np.uint8);a[:,:,0]=np.rint(sand*255);a[:,:,1]=np.rint(grass*255);a[:,:,3]=255;Image.fromarray(a).save(p/'style.png')
  xx,yy=np.meshgrid(ox+np.arange(127)*50,oy+np.arange(127)*50);heights=ground(xx,yy)
  tile=dict(name=name,origin=[ox,oy],native=native,water_level=water,heights_cm=heights.ravel().tolist(),height_range_cm=[float(heights.min()),float(heights.max())]);report['tiles'].append(tile)
 probes=[('Start',1200,-4400),('Puddles',*PUDDLES[0]),('Bog',2300,-2070),('West ford',*FORDS[0][:2]),('Grass',-500,3900),('East ford',*FORDS[-1][:2])]
 report['checkpoints']=[]
 for label,x,y in probes:
  i=min(range(len(ROAD)-1),key=lambda i:(ROAD[i][0]-x)**2+(ROAD[i][1]-y)**2);a,b=ROAD[i],ROAD[i+1];yaw=math.degrees(math.atan2(b[1]-a[1],b[0]-a[0]))
  if label=='Bog':yaw=0
  if 'ford' in label:yaw=FORDS[-1 if x>0 else 0][2]
  report['checkpoints'].append(dict(name=label,x=x,y=y,z=float(ground(x,y))+110,yaw=yaw))
 report['ponds']=[dict(name='Forest pond',x=-2500,y=-900,level=30),dict(name='Upper pond',x=3900,y=4500,level=160)]
 report['river']=dict(length_m=126,width_m=[8,14],main_channel_depth_cm=[20,45],ford_depth_cm=[14,25],level=.1)
 report['water_design']=dict(pond_max_initial_depth_cm=50,river_max_initial_depth_cm=60,scope='Authored bed/shelf geometry; recovered water and mud equations unchanged.')
 points=np.array(ROAD);report['loop_length_m']=float(np.linalg.norm(np.diff(points,axis=0),axis=1).sum()/100)
 (OUT/'authoring.json').write_text(json.dumps(report))
 # A readable route guide built from the same numeric terrain, not a game screenshot.
 xx,yy=np.meshgrid(np.linspace(-6300,6300,800),np.linspace(6300,-6300,800));ss,gg,dd,_,_=masks(xx,yy);hh=ground(xx,yy)
 rgb=np.zeros((800,800,3));rgb[:]=[82,103,57];rgb=rgb*(.8+.2*np.clip(hh/450,0,1))[:,:,None]
 road=(1-smooth(225,340,road_distance(xx,yy)));rgb=rgb*(1-road[:,:,None])+np.array([142,121,84])*road[:,:,None]
 water=(np.abs(yy-river_y(xx))<850)&(hh<.1)
 water|=(pond_q(xx,yy,-2500,-900,1050,730)<1.5)&(hh<30)
 water|=(pond_q(xx,yy,3900,4500,1000,760)<1.5)&(hh<160)
 water|=(pond_q(xx,yy,2300,-2070,1400,900)<1)&(hh<30)
 rgb[water]=[52,107,117];im=Image.fromarray(rgb.astype(np.uint8));dr=ImageDraw.Draw(im)
 def px(x,y):return ((x+6300)/12600*800,(6300-y)/12600*800)
 for i,p in enumerate(report['checkpoints'],1):
  a,b=px(p['x'],p['y']);dr.ellipse((a-11,b-11,a+11,b+11),fill='#ead5a4');dr.text((a-3,b-6),str(i),fill='black');dr.text((a+15,b-6),p['name'],fill='white',stroke_width=1,stroke_fill='black')
 im.save(OUT/'route-guide.png');print('Built 126 m square, %.1f m loop, four terrain tiles'%report['loop_length_m'])
 # Distant forest floor wraps the study. The central four landscape tiles retain collision/deformation.
 lines=['o TaigaSurroundings'];axis=list(range(-49500,-10500,1500))+list(range(-10500,10501,150))+list(range(12000,49501,1500));n=len(axis)
 for y in axis:
  for x in axis:
   far=float(smooth(10500,30000,max(abs(x),abs(y))));h=float(ground(x,y))*(1-far)+(1400+850*math.sin(x/7300)*math.cos(y/5400)+500*math.sin(y/3100))*far
   # OBJ's right-handed Y is reflected by Unreal's importer. Export the inverse
   # and reverse winding so the surrounding heights align with the landscape.
   lines.append('v %.3f %.3f %.3f'%(x,-y,h))
 for j in range(n-1):
  for i in range(n-1):
   if -6300<=axis[i]<6300 and -6300<=axis[j]<6300:continue
   a=j*n+i+1;lines.extend(['f %d %d %d'%(a,a+n,a+1),'f %d %d %d'%(a+1,a+n,a+n+1)])
 (OUT/'surroundings.obj').write_text('\n'.join(lines))
if __name__=='__main__':build()
