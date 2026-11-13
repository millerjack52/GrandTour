"""RR1: derived-bed continuity, with photo-led widening only by the crossings.

Metres throughout. Source DEM, river surface elevations and course are inputs,
never rewritten. All dressing is deterministic and baked, with no runtime scan.
"""
import json
from pathlib import Path
import numpy as np
from scipy.spatial import cKDTree
from scipy.ndimage import minimum_filter1d

VERSION='RR2-1'
REACH=(3160.,3540.)
BANK_FILE=Path(__file__).resolve().parents[1]/'LidarAuthoring/river_banks.json'

def bank_definitions():
 data=json.loads(BANK_FILE.read_text());assert data['version']==1
 return data['banks']

def channel_guide(points):
 """Correct the derived drainage guide around explicitly preserved inside banks.

 Original surveyed vectors and water levels remain immutable. Only configured
 station windows move, with smooth ends and a bounded lateral displacement.
 """
 from scipy.ndimage import gaussian_filter1d
 tangent=np.gradient(points,axis=0)
 tangent=gaussian_filter1d(tangent,2,axis=0)
 tangent/=np.maximum(np.linalg.norm(tangent,axis=1)[:,None],1e-8)
 normal=np.stack([-tangent[:,1],tangent[:,0]],-1)
 k=np.arange(len(points));result=points.copy()
 for bank in bank_definitions():
  lo,hi=bank['guide_station_range_m'];blend=bank['guide_end_blend_m']
  weight=smooth(lo,lo+blend,k)*(1-smooth(hi-blend,hi,k))
  result+=normal*(bank['guide_offset_m']*weight)[:,None]
 return result

def smooth(a,b,v):
 t=np.clip((v-a)/(b-a),0,1);return t*t*(3-2*t)

class Repair:
 def __init__(self,points,levels,roads):
  self.points=points;self.levels=levels;self.tree=cKDTree(points)
  # Lower envelope over one landscape cell prevents interpolated collision
  # bridging a sharp water-surface drop between neighbouring course samples.
  self.cut_levels=minimum_filter1d(levels,size=5,mode='nearest')
  self.tangent=np.gradient(points,axis=0)
  self.tangent/=np.maximum(np.linalg.norm(self.tangent,axis=1)[:,None],1e-8)
  self.normal=np.stack([-self.tangent[:,1],self.tangent[:,0]],-1)
  self.bank_spec=bank_definitions()[0]
  route=next(r for r in roads if r.get('authoring',{}).get('id')==self.bank_spec['route_id'])
  p=np.array(route['authoring']['points_cm'])[:,:2]/100
  s=np.r_[0,np.cumsum(np.linalg.norm(np.diff(p,axis=0),axis=1))]
  self.bar=np.stack([np.interp(np.arange(*self.bank_spec['route_station_range_m'],.5),s,p[:,i]) for i in range(2)],-1)
  self.bar_tree=cKDTree(self.bar)

 def bank_mask(self,xy):
  import shapely
  polygon=shapely.Polygon(self.bank_spec['attachment_polygon_m'])
  lo=np.min(self.bank_spec['attachment_polygon_m'],axis=0)-3
  hi=np.max(self.bank_spec['attachment_polygon_m'],axis=0)+3
  use=np.all((xy>=lo)&(xy<=hi),axis=1);result=np.zeros(len(xy))
  if use.any():
   pts=shapely.points(xy[use]);distance=shapely.distance(pts,polygon)
   result[use]=1-smooth(0,self.bank_spec['edge_blend_m'],distance)
  return result

 def sample(self,x,y):
  shape=np.shape(x);xy=np.stack([np.asarray(x).ravel(),np.asarray(y).ravel()],-1)
  distance,k=self.tree.query(xy)
  side=np.sum((xy-self.points[k])*self.normal[k],axis=1)
  reach=smooth(REACH[0],REACH[0]+35,k)*(1-smooth(REACH[1]-35,REACH[1],k))
  bar_distance,_=self.bar_tree.query(xy)
  bar=self.bank_mask(xy)*reach
  return tuple(a.reshape(shape) for a in (distance,k,side,reach,bar))

 def sculpt(self,x,y,base):
  d,k,side,reach,bar=self.sample(x,y)
  # Continuity floor is narrow outside the photographed reach. Inside it,
  # 11-14m variable wet width, asymmetric shoals and deeper pockets.
  half=2.2+reach*(4.0+.8*np.sin(k/31)+.45*np.sin(k/73))
  cross=np.clip(d/half,0,1)
  depth=.42+reach*(.13+.10*np.sin(k/21)+.09*np.sin(k/47))
  depth=depth*(1-.58*cross**2)+.05
  target=self.cut_levels[k]-depth
  weight=1-smooth(half,half+4.,d)
  # Protect the whole attached bank, not just a ribbon under the route.
  weight*=1-bar
  # LiDAR banks can rise sharply only 4m from the centre. Bound lateral cuts;
  # the centreline itself needs <3.5m in the source, so this keeps its repair
  # while retaining the high banks instead of excavating a uniform trench.
  cut=np.maximum(np.minimum(target-base,0),-(4.5+reach))*weight
  worst=np.unravel_index(np.argmin(cut),cut.shape)
  assert np.max(-cut)<650/100,('River cut exceeds 6.5m review guard',float(np.max(-cut)),int(k[worst]),float(d[worst]),float(reach[worst]),float(base[worst]),float(target[worst]))
  result=base+cut
  xy=np.stack([np.asarray(x).ravel(),np.asarray(y).ravel()],-1)
  bd,_=self.bar_tree.query(xy);bd=bd.reshape(np.shape(x))
  cap=self.levels[k]+self.bank_spec['bank_height_m']+self.bank_spec['rear_rise_m']*smooth(3,14,bd)
  # Low yielding front, rising gently into the original mainland. Still cut-only
  # relative to source LiDAR; restoring an erroneous excavation is not a fill.
  bank_surface=np.minimum(base,cap)
  result=result*(1-bar)+bank_surface*bar
  return result,np.abs(result-base)>.0001

 def export(self,out,height):
  from PIL import Image
  s=np.arange(REACH[0],REACH[1]+1,2).astype(int)
  rows=[]
  for k in s:
   offsets=np.arange(-20,20.1,.5);xy=self.points[k]+self.normal[k]*offsets[:,None]
   z=height(xy[:,0]*100,xy[:,1]*100)/100
   rows.append(dict(station=int(k),xy_m=self.points[k].tolist(),normal=self.normal[k].tolist(),water_m=float(self.levels[k]),offset_m=offsets.tolist(),bed_m=z.tolist()))
  lo=np.floor(self.points[s].min(0)-28);hi=np.ceil(self.points[s].max(0)+28)
  span=float(max(hi-lo));axis=np.arange(1024)+.5
  xx,yy=np.meshgrid(lo[0]+axis*span/1024,lo[1]+axis*span/1024)
  d,k,side,reach,bar=self.sample(xx,yy);z=height(xx*100,yy*100)/100;above=z-self.levels[k]
  bed=reach*(1-smooth(15,20,d))*(1-smooth(.20,.85,above))
  bar*=smooth(-.05,.20,above)
  moss=reach*(1-smooth(16,22,d))*smooth(.25,.65,above)*(1-smooth(1.8,3.5,above))*(1-bar)
  Image.fromarray(np.uint8(np.stack([bed,bar,moss,np.ones_like(bed)],-1)*255+.5)).save(out/'river-detail.png')
  rng=np.random.default_rng(20261020);items=[]
  # Coherent patches with gaps, not a repeating row of identical rocks.
  for k in range(int(REACH[0]+20),int(REACH[1]-20),2):
   for side in [-1,1]:
    for lateral in [rng.uniform(1.5,4),rng.uniform(4,7),rng.uniform(7,11),rng.uniform(11,15)]:
     xy=self.points[k]+self.normal[k]*side*lateral+self.tangent[k]*rng.uniform(-1,1)
     z=float(height(*(xy*100)))/100;above=z-self.levels[k]
     if above < -.9 or above>4:continue
     if above<.25:
      if rng.random()<.18:continue
      name=rng.choice(['Cobble_Cluster_S','Cobble_Cluster_M','Cobble_Cluster_L'],p=[.15,.35,.5]);size=rng.uniform(.6,1.5);solid=False
      if rng.random()<.08:name=rng.choice(['Boulder_A','Boulder_B']);size=rng.uniform(.6,1.4);solid=True
     else:
      if rng.random()<.10:continue
      name=rng.choice(['CrownFern_B','CrownFern_C','Kiokio_A','Kiokio_B','MossHummock_A','MossHummock_B','RootTangle_A'],p=[.18,.18,.20,.14,.10,.10,.10]);size=rng.uniform(.65,1.15);solid=False
      if above>.5 and rng.random()<.035:name='TreeFern_Young';size=rng.uniform(.75,1.2)
     items.append(dict(mesh='SM_NZ_'+name,xy_cm=(xy*100).tolist(),scale=float(size),yaw=float(rng.uniform(0,360)),solid=solid))
  # A few bank-held driftwood pieces and a jam, clear of the driving crossings.
  for k in [3200,3245,3378,3440,3490]:
   for side in [-1,1]:
    xy=self.points[k]+self.normal[k]*side*8
    items.append(dict(mesh='SM_NZ_LogJam' if k==3378 and side==1 else 'SM_NZ_Driftwood_A',xy_cm=(xy*100).tolist(),scale=.75,yaw=float(np.degrees(np.arctan2(*self.tangent[k][::-1]))+rng.uniform(-25,25)),solid=True))
  (out/'river-repair.json').write_text(json.dumps(dict(version=VERSION,reach_m=list(REACH),profiles=rows,bar_points_m=self.bar.tolist(),bank_preservation=self.bank_spec,mask_origin_cm=(lo*100).tolist(),mask_span_cm=span*100,items=items),separators=(',',':')))
