"""Deterministic, habitat-grouped level dressing, with explicit clearances."""
from pathlib import Path
import json,math,sys,collections
import numpy as np
from PIL import Image,ImageDraw
from scipy.spatial import cKDTree
from scipy.ndimage import distance_transform_edt
from shapely.geometry import shape,LineString,Polygon,Point
from shapely.ops import unary_union
from rasterio.features import rasterize
from affine import Affine
ROOT=Path('C:/GrandTour');BASE=ROOT/'Art/Export/LidarStudy';PLACE=BASE/'Place';OUT=BASE/'LevelDetail';OUT.mkdir(exist_ok=True)
sys.path.insert(0,str(ROOT/'Art/Unreal'));import lidar_section_surface as protected
rng=np.random.default_rng(11092026);N=2048;STEP=3700/N
forest=np.array(Image.open(BASE/'Reference/forest-mask.png').convert('L'))/255
scrub=np.array(Image.open(BASE/'Reference/scrub-mask.png').convert('L'))/255
style=np.array(Image.open(PLACE/'style.png'))/255
H=np.fromfile(PLACE/'authoring-height.r16','<u2').reshape(2017,2017).astype(np.float32)*32768/65535/100
def sample(a,x,y):return a[min(len(a)-1,max(0,int((y+1850)/3700*len(a)))),min(len(a)-1,max(0,int((x+1850)/3700*len(a))))]
def height(x,y):return float(sample(H,x,y))
roads=json.loads((PLACE/'roads.json').read_text());roadshape=unary_union([LineString(np.array(r['points'])/100) for r in roads])
features=json.loads((BASE/'Reference/aligned-features.json').read_text())['features']
water=unary_union([shape(f['geometry']).buffer(18 if f['properties']['kind']=='river' else 5) for f in features if f['properties']['kind'] in ['river','pond']])
paddocks=unary_union([Polygon(np.array(p['polygon_cm'])/100).buffer(3) for p in json.loads((PLACE/'paddocks.json').read_text())['polygons']])
yards=unary_union([Point(np.array(s['center'])/100).buffer(36 if s['name']=='Riverside house' else 15) for s in json.loads((PLACE/'installed-sites.json').read_text())])
transform=Affine(STEP,0,-1850,0,STEP,-1850)
excluded=rasterize([(g,1) for g in [water,paddocks,yards,roadshape.buffer(7)]],out_shape=(N,N),transform=transform,dtype='uint8')
roadmask=rasterize([(roadshape.buffer(1),1)],out_shape=(N,N),transform=transform,dtype='uint8')
road_distance=distance_transform_edt(roadmask==0)*STEP
wetmask=rasterize([(water,1)],out_shape=(N,N),transform=transform,dtype='uint8')
water_distance=distance_transform_edt(wetmask==0)*STEP
old=json.loads((PLACE/'understory.json').read_text());oldtree=cKDTree(np.array([p['p'][:2] for p in old])/100)
trees=json.loads((BASE/'CanopyDepth/lighting-seeds.json').read_text())['trees'];trunks=cKDTree(np.array(trees)[:,:2])
palette={
 'woodland':(['moss','twig','shrub','grass','fern','root'],[.28,.13,.20,.22,.10,.07]),
 'edge':(['grass','shrub','moss','twig','fern'],[.47,.27,.16,.06,.04]),
 'damp':(['rush','moss','shrub','fern','flax','twig'],[.26,.27,.16,.12,.08,.11]),
 'rock':(['stone','grass','shrub','crevice','moss'],[.35,.22,.16,.10,.17])}
kit='/Game/GrandTour/Environment/NativePlants/v01/';bank='/Game/GrandTour/ArtTests/LidarStudy/FirstSection/'
names={'moss':['MossHummock_A','MossHummock_B'],'twig':['TwigLitter_A','TwigLitter_B'],'shrub':['Coprosma_A','Coprosma_B','Matagouri_A'],
 'grass':['VergeTussock_A','VergeTussock_B'],'root':['RootTangle_A'],'rush':['Rush_A','Rush_B'],'flax':['Harakeke_A'],
 'stone':['Boulder_A','Boulder_B'],'log':['Log_A','Log_B'],'stump':['Stump_A']}
manifest=json.loads((ROOT/'Art/Export/NativePlants/v01/manifest.json').read_text())['models'];sizes={r['asset']:r['size_m'] for r in manifest if r['lod']==0}
items=[];patches=[];reject=collections.Counter();counts=collections.Counter();occupied={}
def eligible(x,y,radius=0):
 if max(abs(x),abs(y))>1815 or sample(excluded,x,y) or protected.inside(x*100,y*100,margin=-600):return False
 if sample(forest,x,y)<.28 and sample(scrub,x,y)<.35:return False
 if radius>1 and (roadshape.distance(Point(x,y))<7+radius or water.distance(Point(x,y))<radius or paddocks.distance(Point(x,y))<radius):return False
 return True
def add(role,x,y,biome,pid,anchor=False):
 if role in ['fern','crevice']:
  kind='Crevice' if role=='crevice' else rng.choice(['Fine','Crown','Cascade'],p=[.45,.30,.25]);name=f'SM_RS7_{kind}_{rng.integers(3)}';mesh=bank+name;scale=float(rng.uniform(.55,.93));radius=.85*scale
 else:
  suffix=rng.choice(names[role]);name='SM_NZ_'+suffix;mesh=kit+name
  ranges={'stone':(1.6,3.0) if anchor else (.45,1.35),'log':(.38,.70),'stump':(.45,.80),'shrub':(.48,.90),'moss':(.65,1.30),'grass':(.68,1.25),'flax':(.55,.90)}
  scale=float(rng.uniform(*ranges.get(role,(.65,1.05))));radius=max(sizes[name][:2])*scale*.5
 if not eligible(x,y,radius):reject['exclusion']+=1;return
 if trunks.query([x,y])[0]<(.7 if role in ['moss','twig','root'] else 1.1):reject['trunk']+=1;return
 if role not in ['moss','twig','root','stone'] and oldtree.query([x,y])[0]<.9:reject['existing_plant']+=1;return
 key=(int(math.floor(x/3)),int(math.floor(y/3)));spacing=max(.35,min(radius,.85))
 for dx in range(-2,3):
  for dy in range(-2,3):
   if any(math.hypot(x-px,y-py)<spacing+rr for px,py,rr in occupied.get((key[0]+dx,key[1]+dy),[])):reject['spacing']+=1;return
 gx=(height(x+2,y)-height(x-2,y))/4;gy=(height(x,y+2)-height(x,y-2))/4;slope=math.degrees(math.atan(math.hypot(gx,gy)))
 limits={'log':20,'stump':28,'twig':25,'root':28,'shrub':40,'grass':42,'rush':28,'flax':28,'fern':34,'crevice':48,'moss':45,'stone':54}
 if slope>limits[role]:reject['slope']+=1;return
 yaw=float(rng.uniform(-180,180))
 if role in ['fern','crevice']:yaw=math.degrees(math.atan2(-gy,-gx))+float(rng.uniform(-20,20))
 occupied.setdefault(key,[]).append((x,y,spacing if not anchor else radius*.85))
 items.append(dict(mesh=mesh,role=role,xy_cm=[round(x*100,2),round(y*100,2)],scale=round(scale,4),yaw=round(yaw,3),biome=biome,patch=pid,radius_cm=round(radius*100,2),anchor=anchor))
 counts[role]+=1

for cy in np.arange(-1800,1801,28):
 for cx in np.arange(-1800,1801,28):
  x,y=np.array([cx,cy])+rng.uniform(-11,11,2)
  if not eligible(x,y):continue
  rd=float(sample(road_distance,x,y));chance=.84 if rd<85 else .30
  # Broad variations leave readable gaps between richer communities.
  chance*=.60+.40*(.5+.5*math.sin(x*.017+math.sin(y*.011)))
  if rng.random()>chance:continue
  gx=(height(x+2,y)-height(x-2,y))/4;gy=(height(x,y+2)-height(x,y-2))/4;slope=math.degrees(math.atan(math.hypot(gx,gy)))
  if slope>51:continue
  st=sample(style,x,y);wd=float(sample(water_distance,x,y))
  hollow=sum(height(x+dx,y+dy) for dx,dy in [(18,0),(-18,0),(0,18),(0,-18)])/4-height(x,y)
  biome='rock' if slope>24 or st[3]>.45 else 'damp' if wd<30 or (hollow>2.4 and slope<16) else 'edge' if rd<24 or sample(forest,x,y)<.70 or sample(scrub,x,y)>.6 else 'woodland'
  pid=len(patches);begin=len(items);radius=float(rng.uniform(5.0,9.5));angle=float(rng.uniform(0,math.tau))
  if biome=='rock' or (biome=='edge' and rng.random()<.25):add('stone',x,y,biome,pid,True)
  elif biome=='woodland' and rng.random()<.22:add('log',x,y,biome,pid,True)
  elif biome=='woodland' and rng.random()<.12:add('stump',x,y,biome,pid,True)
  for i in range(32 if rd<85 else 23):
   role=str(rng.choice(palette[biome][0],p=palette[biome][1]));a=rng.uniform(0,math.tau);r=radius*math.sqrt(rng.random());px=math.cos(a)*r;py=math.sin(a)*r*.65
   add(role,x+px*math.cos(angle)-py*math.sin(angle),y+px*math.sin(angle)+py*math.cos(angle),biome,pid)
  if len(items)>begin:patches.append(dict(id=pid,biome=biome,xy_m=[float(x),float(y)],radius_m=radius,items=len(items)-begin,road_distance_m=rd,slope=slope))
review=[]
print('PLANNED',len(items),dict(counts),dict(collections.Counter(p['biome'] for p in patches)),flush=True)
targets={'woodland':[-620,69],'edge':[-645,68],'rock':[-1200,800],'damp':[-520,-300]}
log_patches={i['patch'] for i in items if i['role']=='log'}
for k,(biome,target) in enumerate(targets.items()):
 candidates=[p for p in patches if p['biome']==biome and p['items']>=6 and p['slope']<42 and (biome!='woodland' or p['id'] in log_patches)]
 assert candidates,('No review patch',biome)
 best=min(candidates,key=lambda p:math.dist(p['xy_m'],target)+max(0,16-p['items'])*10)
 x,y=best['xy_m'];gx=(height(x+2,y)-height(x-2,y))/4;gy=(height(x,y+2)-height(x,y-2))/4;a=math.atan2(gy,gx)
 choices=[]
 for angle in [a,a+.5,a-.5,a+1,a-1,a+math.pi]:
  px=x+math.cos(angle)*11;py=y+math.sin(angle)*11
  if trunks.query([px,py])[0]>1.4 and oldtree.query([px,py])[0]>.8:choices.append([px,py])
 px,py=choices[0] if choices else [x+10,y+8]
 review.append(dict(view=f'D0{k+1}',biome=biome,patch=best['id'],position_xy_cm=[px*100,py*100],target_xy_cm=[x*100,y*100],eye_cm=190,target_height_cm=70,fov=68))
recipe=dict(version=1,seed=11092026,enabled=True,items=items,patches=patches,review=review)
(OUT/'layout.json').write_text(json.dumps(recipe,separators=(',',':')))
summary=dict(items=len(items),patches=len(patches),roles=dict(counts),biomes=dict(collections.Counter(i['biome'] for i in items)),rejected=dict(reject),review=review,rule='Grouped habitats across woodland/scrub; denser near routes; keep roads, water, paddocks, yards and approved bank clear')
(OUT/'plan.json').write_text(json.dumps(summary,indent=2))
im=Image.fromarray(np.uint8(np.stack([forest*.22+.12,forest*.30+.12,forest*.17+.12],-1)*255)).resize((1000,1000));draw=ImageDraw.Draw(im)
colours={'woodland':'#7cb65a','edge':'#d7b45f','rock':'#b5a49a','damp':'#60b7bb'}
for p in patches:
 x,y=[(v+1850)/3700*1000 for v in p['xy_m']];draw.ellipse((x-1.2,y-1.2,x+1.2,y+1.2),fill=colours[p['biome']])
for v in review:
 x,y=[(q/100+1850)/3700*1000 for q in v['target_xy_cm']];draw.ellipse((x-6,y-6,x+6,y+6),outline='white',width=2);draw.text((x+9,y-8),v['view'],fill='white')
im.save(OUT/'distribution.png');print(json.dumps({k:v for k,v in summary.items() if k!='review'},indent=2))
