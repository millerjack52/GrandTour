"""Registered map vectors, aerial-digitized access and LiDAR-derived drainage."""
from pathlib import Path
import json,math,struct,hashlib,os
import numpy as np
import shapely
from PIL import Image,ImageDraw,ImageFilter
from shapely.geometry import shape,LineString,Point
from shapely.ops import linemerge,unary_union
from scipy.ndimage import gaussian_filter, distance_transform_edt
from rasterio.features import rasterize
from affine import Affine
import sys;sys.path.insert(0,str(Path(__file__).resolve().parent));import lidar_farm as LF   # LP4: paddocks and farm hardware
import lidar_authoring as LA
import lidar_river_repair as RR
ROOT=Path(__file__).resolve().parents[2];BASE=ROOT/'Art/Export/LidarStudy';OUT=Path(os.environ.get('GT_LIDAR_OUTPUT',str(BASE/'Place')));OUT.mkdir(parents=True,exist_ok=True)
DESIGN=LA.load(Path(os.environ.get('GT_LIDAR_EDITS',str(LA.DEFAULT))))
_trial=ROOT/'Art/LidarAuthoring/logging_trial.json'
(OUT/'logging_trial.json').write_text(_trial.read_text(encoding='utf-8') if _trial.exists() else '{}',encoding='utf-8')
N=2048;SIZE=370000.;O=-185000.;STEP=SIZE/N
H=np.fromfile(BASE/'height.r16',dtype='<u2').reshape(2017,2017).astype(float)/65535*32768
features=json.loads((BASE/'Reference/aligned-features.json').read_text())['features']
forest=np.array(Image.open(BASE/'Reference/forest-mask.png'))/255.;scrub=np.array(Image.open(BASE/'Reference/scrub-mask.png'))/255.
def sample(a,x,y):
 i=np.clip(((np.asarray(x)-O)/SIZE*a.shape[1]).astype(int),0,a.shape[1]-1);j=np.clip(((np.asarray(y)-O)/SIZE*a.shape[0]).astype(int),0,a.shape[0]-1);return a[j,i]
def height(x,y):
 fx=np.clip((np.asarray(x)-O)/SIZE*2016,0,2015.9999);fy=np.clip((np.asarray(y)-O)/SIZE*2016,0,2015.9999);i=fx.astype(int);j=fy.astype(int);a=fx-i;b=fy-j;q=H[j,i];r=H[j,i+1];v=H[j+1,i];w=H[j+1,i+1];return np.where(a>=b,q+(r-q)*a+(w-r)*b,q+(w-v)*a+(v-q)*b)
def save(n,a):Image.fromarray(np.uint8(np.clip(a,0,1)*255+.5)).save(OUT/(n+'.png'))
def smooth(a,b,x):t=np.clip((x-a)/(b-a),0,1);return t*t*(3-2*t)
def resize(a,n):return np.array(Image.fromarray(a.astype('float32')).resize((n,n),Image.Resampling.BILINEAR))
roads=[]
for name in sorted({f['properties'].get('name') for f in features if f['properties']['kind']=='road'}):
 gg=[shape(f['geometry']) for f in features if f['properties']['kind']=='road' and f['properties']['name']==name];g=linemerge(gg)
 for line in ([g] if g.geom_type=='LineString' else g.geoms):
  # Retain the georeferenced polyline, densifying only long segments.
  pts=[]
  c=list(line.coords)
  for a,b in zip(c,c[1:]):
   for t in np.linspace(0,1,max(1,math.ceil(math.dist(a,b)/15)),endpoint=False):pts.append((np.array(a)*(1-t)+np.array(b)*t)*100)
  pts.append(np.array(c[-1])*100);roads.append(dict(name=name,points=np.asarray(pts).tolist(),length_m=line.length))
# Registered water shapes; also keep the road bench below out of the river and ponds.
water_shapes=[shape(f['geometry']).buffer(9 if f['properties']['kind']=='river' else 2) for f in features if f['properties']['kind'] in ['river','pond']]
A=Affine(STEP/100,0,O/100,0,STEP/100,O/100);wm=rasterize([(g,1) for g in water_shapes],out_shape=(N,N),transform=A,dtype='uint8')
# LP1 road bench. The aerial-digitised private lines sit 2-4m beside the graded
# bench visible in the 1m LiDAR DEM (median offset 2.8m, steep side slope at the
# line where a flat bench lies within 8m). Re-register them onto that bench.
DEM=np.load(BASE/'dem.npy')
def dem_height(x_cm,y_cm):
 rows,cols=DEM.shape;c=np.clip(np.asarray(x_cm,float)/100+cols/2,0,cols-1.001);r=np.clip(np.asarray(y_cm,float)/100+rows/2,0,rows-1.001)
 i=c.astype(int);j=r.astype(int);a=c-i;b=r-j
 return DEM[j,i]*(1-a)*(1-b)+DEM[j,i+1]*a*(1-b)+DEM[j+1,i]*(1-a)*b+DEM[j+1,i+1]*a*b
bench_report={};bench_geom={}   # CL1: per-station geometry of the chosen offsets (stations st, unit normals nrm, offsets off), read by the clay cut-face band below
def register_to_bench(points_cm,name):
 # Continuous-offset path: 49 offsets (-12..+12m, 0.5m) at every 5m station.
 # Cost = car-track cross-slope (deg, +-0.9m from the 1m DEM) + 0.15/m away
 # from the digitised line + 50 in registered water; moving sideways costs 4
 # per metre and more than 1m between stations is forbidden. Ends stay on the
 # digitised line so the junctions with the public roads do not move.
 from scipy.ndimage import uniform_filter1d
 p=np.asarray(points_cm,float)/100;cum=np.concatenate([[0.],np.cumsum(np.hypot(*np.diff(p,axis=0).T))]);L=float(cum[-1])
 s=np.arange(0,L,5.)
 if L-s[-1]>1e-6:s=np.append(s,L)
 at=lambda v:np.stack([np.interp(v,cum,p[:,0]),np.interp(v,cum,p[:,1])],-1)
 st=at(s);t=at(np.minimum(s+10,L))-at(np.maximum(s-10,0));t/=np.maximum(np.linalg.norm(t,axis=1)[:,None],1e-9);nrm=np.stack([-t[:,1],t[:,0]],-1)
 states=np.arange(-12,12.25,.5)
 def hm(k,v):v=np.asarray(v,float);return dem_height((st[k,0]+nrm[k,0]*v)*100,(st[k,1]+nrm[k,1]*v)*100)
 def cross(k,v):v=np.asarray(v,float);return np.degrees(np.arctan(np.abs(hm(k,v+.9)-hm(k,v-.9))/1.8))
 def wet(k,v):v=np.asarray(v,float);return sample(wm,(st[k,0]+nrm[k,0]*v)*100,(st[k,1]+nrm[k,1]*v)*100)>=.5
 em=np.array([cross(k,states)+.15*np.abs(states)+50*wet(k,states) for k in range(len(s))])
 em[[0,-1]]=np.where(states==0,em[[0,-1]],1e9)
 d=np.abs(states[:,None]-states[None,:]);tr=np.where(d>1.,1e9,4.*d)
 cost=em[0];back=[]
 for k in range(1,len(s)):
  tot=cost[None,:]+tr;bp=tot.argmin(1);back.append(bp);cost=tot[np.arange(len(states)),bp]+em[k]
 ch=[int(cost.argmin())]
 for bp in reversed(back):ch.append(int(bp[ch[-1]]))
 raw=states[ch[::-1]]
 off=np.clip(uniform_filter1d(raw,size=3,mode='nearest'),-12,12);off[[0,-1]]=0
 cc=np.array([float(cross(k,off[k])) for k in range(len(s))]);new=st+nrm*off[:,None];bench_geom[name]=dict(s=s,st=st,nrm=nrm,off=off)
 bench_report[name]=dict(stations=int(len(s)),mean_abs_offset_m=float(np.abs(off).mean()),max_abs_offset_m=float(np.abs(off).max()),chosen_track_cross_p95=float(np.percentile(cc,95)),chosen_track_cross_max=float(cc.max()),over_10_dem=int((cc>10).sum()),length_before_m=L,length_after_m=float(np.hypot(*np.diff(new,axis=0).T).sum()))
 return (new*100).tolist()
for rd in roads:
 if rd['name'] in ['Riverside access','Pond field spur']:
  rd['points']=register_to_bench(rd['points'],rd['name']);rp=np.asarray(rd['points'])/100;rd['length_m']=float(np.hypot(*np.diff(rp,axis=0).T).sum())
roads.extend(LA.road_records(DESIGN))
roadimg=Image.new('L',(N,N));draw=ImageDraw.Draw(roadimg)
for r in roads:
 if not r.get('authoring'):draw.line([tuple((np.array(p)-O)/STEP) for p in r['points']],fill=255,width=4)
road=np.array(roadimg.filter(ImageFilter.GaussianBlur(.6)))/255.
# LP4 paddocks (owner 2026-10-18: the three paddocks are just grass): the three big grazed fields along the private roads, from the registered aerial (lidar_farm.find_paddocks);
# polygons in map metres, fence-line straight runs, vertices >= 8 m apart. PAD_COV is their coverage on the 2048 grid.
LF_PRIV={r['name']:np.asarray(r['points'])/100. for r in roads if r['name'] in ('Riverside access','Pond field spur')}
pad=LF.find_paddocks(BASE,[LineString(v) for v in LF_PRIV.values()]);PADS=[c['polygon'] for c in pad['paddocks']];PAD_COV=LF.soft_mask(PADS,N,STEP/100.,O/100.)
print('LP4 paddocks',pad['rule'],[(round(c['area_polygon_m2']),c['vertices'],round(c['dist_to_private_road_m'],1)) for c in pad['paddocks']])
yy,xx=np.mgrid[:N,:N];x=O+(xx+.5)*STEP;y=O+(yy+.5)*STEP;z=height(x,y);gy,gx=np.gradient(z,STEP);slope=np.hypot(gx,gy)
road=LA.track_mask(DESIGN,x/100,y/100,road)
rng=np.random.default_rng(20261016);broad=resize(rng.random((60,60)),N);fine=resize(rng.random((240,240)),N)
concavity=np.clip((gaussian_filter(z,10)-z)/180+.25,0,1);wetland=concavity*(1-smooth(.08,.3,slope))
rock=smooth(.55,1.2,slope)*.5;wet=np.clip(.25+.4*forest+.35*wetland-.3*road,0,1);grass=(1-road*.99)*(1-rock)*(.85-.25*forest+.15*fine)
depth=(3+wetland*36)*(1-road*.92)*(1-rock);firm=np.clip(.22+.65*road-.12*wetland,0,1)
paint=np.stack([depth/50,np.ones_like(depth),firm,.25+.7*wet],-1);paint[[0,-1],:,:]=[0,1,0,0];paint[:,[0,-1],:]=[0,1,0,0]
# LP2b river channel from the 1m DEM. A LiDAR bare-earth DEM already records the water
# surface, so a pit is an artefact or a drop, never a deep pool: no priority-flood fill.
# Channel bottom = lowest DEM point within +-12m across each 1m course station; depth
# comes from how far that bottom dips below its 21-station running mean (riffles 0.30m,
# pools at most 1.20m); walking downstream the surface may climb at most 2cm per metre.
from scipy.spatial import cKDTree
from scipy.ndimage import uniform_filter1d,map_coordinates,binary_dilation
river_feats=[f for f in features if f['properties']['kind']=='river' and f['properties'].get('source')=='LiDAR drainage'];assert len(river_feats)==1
rg=shape(river_feats[0]['geometry']).intersection(__import__('shapely').geometry.box(-1817,-1849,1817,1849))
rl=LineString(np.array(rg.coords));rds=np.arange(0,rl.length+.5,1);rps=np.array([[rl.interpolate(float(v)).x,rl.interpolate(float(v)).y] for v in rds])
rtang=np.gradient(rps,axis=0);rtang/=np.maximum(np.linalg.norm(rtang,axis=1)[:,None],1e-6);rnrm=np.stack([-rtang[:,1],rtang[:,0]],-1)
# Downstream direction: the ends of the DEM-conditioned (filled) drainage profile.
hydro=np.load(BASE/'Reference/drainage-2m.npz');rprofile=map_coordinates(hydro['filled'],np.stack([(rps[:,1]+1849.5)/2,(rps[:,0]+1817.5)/2]),order=1,mode='nearest')
rsign=-1 if rprofile[-1]>rprofile[0] else 1
offs=np.arange(-12,12.25,.5);thal_raw=dem_height((rps[:,:1]+rnrm[:,:1]*offs)*100,(rps[:,1:]+rnrm[:,1:]*offs)*100).min(1);thal_smooth=uniform_filter1d(thal_raw,21,mode='nearest')
# Round 2: every station keeps at least 20cm over its own channel bottom, so a riffle hump is a
# shallow riffle, not dry ground; only the rise cap below can still leave a real DEM hump dry.
rsurf=np.maximum(thal_smooth+np.clip(.45+(thal_smooth-thal_raw),.30,1.20),thal_raw+.20);rsurf_pre=rsurf.copy();down=np.arange(len(rps))[::rsign]
for a,b in zip(down,down[1:]):rsurf[b]=min(rsurf[b],rsurf[a]+.02)
# RR2: preserve the source drainage and its levels, but route the derived local
# channel around the inside-bank footprint instead of excavating through it.
source_rps=rps.copy();rps=RR.channel_guide(source_rps)
rtang=np.gradient(rps,axis=0);rtang/=np.maximum(np.linalg.norm(rtang,axis=1)[:,None],1e-6);rnrm=np.stack([-rtang[:,1],rtang[:,0]],-1)
# Authoring changes the bed only. Freeze the original river surface/course first.
_source_H=H.copy();_river_tree=cKDTree(rps)
def author_water(wx,wy):
 dist,idx=_river_tree.query(np.stack([np.asarray(wx).ravel(),np.asarray(wy).ravel()],-1))
 return np.where(dist.reshape(np.shape(wx))<20,rsurf[idx].reshape(np.shape(wx)),np.nan)
_axis=np.linspace(O,-O,2017)/100;_hx,_hy=np.meshgrid(_axis,_axis)
river_repair=RR.Repair(rps,rsurf,roads)
_river_h,_repair_mask=river_repair.sculpt(_hx,_hy,H/100)
_new_h,_bed_mask=LA.sculpt_beds(DESIGN,_hx,_hy,_river_h,author_water(_hx,_hy),dem_height(_hx*100,_hy*100))
_bed_mask|=_repair_mask
_encoded=np.rint(np.clip(_new_h*100/32768,0,1)*65535).astype('<u2')
_encoded.tofile(OUT/'authoring-height.r16');H=_encoded.astype(float)/65535*32768
_change=H-_source_H
authoring_report=dict(ok=True,version=1,design_digest=LA.digest(DESIGN),mud_tracks=len(LA.enabled(DESIGN,'mud_track')),river_beds=len(LA.enabled(DESIGN,'river_bed')),
 changed_terrain_vertices=int((np.abs(_change)>.01).sum()),maximum_terrain_change_cm=float(np.abs(_change).max()),source_height_sha256=hashlib.sha256((BASE/'height.r16').read_bytes()).hexdigest(),
 derived_height_sha256=hashlib.sha256(_encoded.tobytes()).hexdigest(),water_course_unchanged=False,water_surface_unchanged=True,local_guide_shift_max_m=float(np.linalg.norm(rps-source_rps,axis=1).max()))
_changed=np.argwhere(np.abs(_change)>.01)
authoring_report['height_probes_cm']=[[float(_hx[j,i]*100),float(_hy[j,i]*100),float(H[j,i])] for j,i in _changed[::max(1,len(_changed)//32)][:32]]
(OUT/'authoring-reference.json').write_text(json.dumps(dict(river_points_cm=np.column_stack([rps*100,rsurf*100]).tolist(),source_river_points_cm=np.column_stack([source_rps*100,rsurf*100]).tolist())))
(OUT/'authoring-report.json').write_text(json.dumps(authoring_report,indent=2))
river_repair.export(OUT,height)
z=height(x,y);gy,gx=np.gradient(z,STEP);slope=np.hypot(gx,gy)
# Riffles run fast, pools slow: speed from the surface slope over +-5m, positive downstream.
k=np.arange(len(rps));ka=np.clip(k-5,0,len(rps)-1);kb=np.clip(k+5,0,len(rps)-1);rslope=rsign*(rsurf[ka]-rsurf[kb])/np.maximum(kb-ka,1)
rspeed=np.clip(.3+3*np.sqrt(np.maximum(rslope,0)),.3,1.5);rkd=cKDTree(rps)
def river_cells(wx,wy):
 dist,idx=rkd.query(np.stack([wx.ravel(),wy.ravel()],-1));idx=idx.reshape(wx.shape)
 # One bed for render, water queries and collision, including unedited cells.
 bed=height(wx*100,wy*100)/100
 return dist.reshape(wx.shape),idx,rsurf[idx],bed
# The rendered river's own wet vertices (the 1m OBJ grid and clip rule below).
rshape=rg.buffer(20.,cap_style=2);rlo=np.floor(np.array(rshape.bounds[:2])-3);rhi=np.ceil(np.array(rshape.bounds[2:])+3)
rwx,rwy=np.meshgrid(np.arange(rlo[0]+.5,rhi[0],1.),np.arange(rlo[1]+.5,rhi[1],1.));rdist,ridx,rmean,rbed=river_cells(rwx,rwy);rdepth=rmean-rbed
rwet1=np.minimum(rdepth-.015,(20-rdist)*.2)>0
# Wet vertices + 1m (every quad holding water) on the 2048 grid: any such 1m point marks its cell,
# so every cell containing water is marked. The bed there reads as cobbles: rock, wet, no grass.
rfoot=binary_dilation(rwet1,np.ones((3,3),bool));river_bed=np.zeros((N,N),bool)
river_bed[np.clip(((rwy[rfoot]*100-O)/STEP).astype(int),0,N-1),np.clip(((rwx[rfoot]*100-O)/STEP).astype(int),0,N-1)]=True
grass[river_bed]=0;wet[river_bed]=1;rock[river_bed]=1
bed_paint=river_bed.copy();bed_paint[[0,-1],:]=False;bed_paint[:,[0,-1]]=False;paint[bed_paint,0]=0;paint[bed_paint,2]=.9
# Trees and shrubs: the river footprint dilated one full 1.8m cell including diagonals (>=1.8m clear of
# any water triangle) replaces the 9m line buffer; ponds keep their 2m buffer.
pond_wm=rasterize([(shape(f['geometry']).buffer(2),1) for f in features if f['properties']['kind']=='pond'],out_shape=(N,N),transform=A,dtype='uint8')
tree_water=(binary_dilation(river_bed,np.ones((3,3),bool))|(pond_wm>0)).astype('uint8')
rdem_at=height(rps[:,0]*100,rps[:,1]*100)/100;smd=rsurf-rdem_at
sv=np.arange(-25,25.5,1.);d_,i_,m_,b_=river_cells(rps[::10,:1]+rnrm[::10,:1]*sv,rps[::10,1:]+rnrm[::10,1:]*sv);rwidth=(np.minimum(m_-b_-.015,(20-d_)*.2)>0).sum(1)
river_stats=dict(downstream_sign=rsign,stations=int(len(rps)),surface_minus_dem_p50=float(np.percentile(smd,50)),surface_minus_dem_p95=float(np.percentile(smd,95)),surface_minus_dem_max=float(smd.max()),
 wet_width_p50_m=float(np.percentile(rwidth,50)),wet_width_p10_p90_m=[float(np.percentile(rwidth,10)),float(np.percentile(rwidth,90))],dry_stations_pct=float(100*(rsurf<rdem_at).mean()),
 rise_capped_stations_pct=float(100*(rsurf<rsurf_pre-1e-9).mean()),flow_speed_p50=float(np.percentile(rspeed,50)),flow_speed_p95=float(np.percentile(rspeed,95)))
# Dry stretches left: runs of stations whose surface is below the channel bottom (real DEM humps the
# 2cm/m rise cap cannot climb). [start_x_cm, start_y_cm, length_m, hump_height_m, distance_to_house_m (nearest station of the run)]
rdry=np.diff(np.concatenate([[0],(rsurf<rdem_at).astype(int),[0]]));rd0=np.flatnonzero(rdry==1);rd1=np.flatnonzero(rdry==-1);HOUSE=np.array([-522.6444549,-262.5674983])
dry_stretches=sorted([[float(rps[a,0]*100),float(rps[a,1]*100),int(b-a),float((rdem_at[a:b]-rsurf[a:b]).max()),float(np.linalg.norm(rps[a:b]-HOUSE,axis=1).min())] for a,b in zip(rd0,rd1) if b-a>=10],key=lambda r:-r[2])
river_stats.update(dry_stretches_over_5m=int(((rd1-rd0)>=5).sum()),dry_stretches=dry_stretches)
print('LP2b dry: %.2f%% of stations, %d stretches >=5m, %d >=10m'%(river_stats['dry_stations_pct'],river_stats['dry_stretches_over_5m'],len(dry_stretches)))
for r in dry_stretches:print('  dry stretch start (%.0f, %.0f) cm, %d m, hump %.2f m, %.0f m from house'%tuple(r))
# LP3b floor under the canopy: inside the forest mask (blended over 6m at its edge) the painted ground is dark wet peat and litter,
# not bright grass: grass x .15 and wet +.2 (cap 1). Roads (1-road) and the river bed are left alone, and the paint channels
# (depth, firm, wet) were stacked above and are not touched.
fbin=forest>.5;inside_m=distance_transform_edt(fbin)*STEP/100;outside_m=distance_transform_edt(~fbin)*STEP/100
floor_w=smooth(0.,6.,inside_m)*(1-road)*(~river_bed)
grass_before,wet_before=grass.copy(),wet.copy();grass=grass*(1-.85*floor_w);wet=np.minimum(1.,wet+.2*floor_w)
floor_stats=dict(forest_cells=int(fbin.sum()),cells_changed=int((floor_w>.01).sum()),forest_grass_mean_before=float(grass_before[fbin].mean()),forest_grass_mean_after=float(grass[fbin].mean()),forest_wet_mean_before=float(wet_before[fbin].mean()),forest_wet_mean_after=float(wet[fbin].mean()),
 outside_grass_max_abs_change=float(np.abs(grass-grass_before)[~fbin].max()),outside_wet_max_abs_change=float(np.abs(wet-wet_before)[~fbin].max()))
# CL1 clay masks (owner 2026-10-17, photos 10/11/12). The clay weight is NOT written to style R: GTLandscapeSurface reads style R as sand (granular response,
# native mud off, mud rest height x.1) and AGTProceduralGround::Rebuild zeroes it across every road corridor, so style R would change the soil physics (CL2's job)
# and would lose the track anyway. It travels in its own atlas clay.png, same window and size as paint/style: R clay weight, G orange cut face (cut band x DEM
# steepness), B bush slurry (forest mask), A 255. Paint and style R/B/A are untouched; style G (visual grass cover only) is cleared on the yard and the orange faces.
from shapely.geometry import Polygon
from scipy.ndimage import zoom,median_filter
PRIV=('Riverside access','Pond field spur');SS=4;hS=STEP/100./SS;Om=O/100.;Sm=STEP/100.
priv_pts={r['name']:np.asarray(r['points'])/100. for r in roads if r['name'] in PRIV}
_box=np.concatenate(list(priv_pts.values())+[HOUSE[None]+np.array([[-32.,-32.],[32.,32.]])])
ci0,cj0=np.floor((_box.min(0)-16.-Om)/Sm).astype(int);ci1,cj1=np.ceil((_box.max(0)+16.-Om)/Sm).astype(int)
assert ci0>=0 and cj0>=0 and ci1<=N and cj1<=N,(ci0,cj0,ci1,cj1)
cW,cH=int(ci1-ci0)*SS,int(cj1-cj0)*SS;ci0,cj0,ci1,cj1=int(ci0),int(cj0),int(ci1),int(cj1);A_ss=Affine(hS,0,Om+ci0*Sm,0,hS,Om+cj0*Sm)
CX,CY=np.meshgrid((Om+ci0*Sm+(np.arange(cW)+.5)*hS).astype('float32'),(Om+cj0*Sm+(np.arange(cH)+.5)*hS).astype('float32'))
def dem_at(arr,x_m,y_m):
 rows,cols=arr.shape;c=np.clip(np.asarray(x_m,float)+cols/2,0,cols-1.001);r=np.clip(np.asarray(y_m,float)+rows/2,0,rows-1.001);i=c.astype(int);j=r.astype(int);a=c-i;b=r-j
 return arr[j,i]*(1-a)*(1-b)+arr[j,i+1]*a*(1-b)+arr[j+1,i]*(1-a)*b+arr[j+1,i+1]*a*b
# track: the two private roads' centrelines, road width 3.8 m (install width_cm 380) + 1.5 m shoulders each side, 1 m blend centred on the edge
lines_ss=rasterize([(LineString(p),1) for p in priv_pts.values()],out_shape=(cH,cW),transform=A_ss,all_touched=True,dtype='uint8')
dline=(distance_transform_edt(lines_ss==0)*hS).astype('float32');TRACK_R=1.9+1.5;track=1-smooth(TRACK_R-.5,TRACK_R+.5,dline)
# river bed and pond footprint (tree_water: bed cells + one cell + 2 m pond buffer) stays unclayed, softened over ~1.5 m
keep=1-np.clip(gaussian_filter(np.repeat(np.repeat(tree_water[cj0:cj1,ci0:ci1],SS,0),SS,1).astype('float32'),1.5/hS),0,1)
# yard: 25 m disc around the house anchor, a 12 x 8 m axis-aligned rectangle at the anchor left at 0 for the house massing, forest interior (3 m ramp) and water excluded
ra=np.hypot(CX-HOUSE[0],CY-HOUSE[1]);disc=1-smooth(24.5,25.5,ra)
qx=np.abs(CX-HOUSE[0])-6.;qy=np.abs(CY-HOUSE[1])-4.;sdr=np.hypot(np.maximum(qx,0),np.maximum(qy,0))+np.minimum(np.maximum(qx,qy),0);hole=smooth(-.5,.5,sdr)
in_ss=zoom(inside_m[cj0:cj1,ci0:ci1].astype('float32'),SS,order=1,grid_mode=True,mode='nearest');forest_ex=smooth(0.,3.,in_ss);yard_pre=disc*hole;yard=yard_pre*(1-forest_ex)
# cut faces: at each private-road station where register_to_bench chose an offset (>=.5 m) and the DEM rises by >=.8 m across the road (mean of 3.5..6.5 m on each side),
# a 2.5 m band from the road edge (1.9 m) on the uphill side; 1 m blend. Orange only where the DEM is steep (tan 24..40 deg), 1 m DEM smoothed 1.5 m.
_tan=np.hypot(*np.gradient(gaussian_filter(DEM,1.5)));band_polys=[];cut_stats={};E0=1.9;E1=E0+2.5
for name in PRIV:
 g=bench_geom[name];st,nrm,off=g['st'],g['nrm'],g['off'];pos=st+nrm*off[:,None];ds=(3.5,4.5,5.5,6.5)
 hp=np.mean([dem_height((pos+nrm*d)[:,0]*100,(pos+nrm*d)[:,1]*100) for d in ds],0);hm=np.mean([dem_height((pos-nrm*d)[:,0]*100,(pos-nrm*d)[:,1]*100) for d in ds],0)
 rise=hp-hm;side=np.where(np.abs(rise)>=.8,np.sign(rise),0.);moved=np.abs(off)>=.5;cutst=moved&(side!=0);tg=np.stack([nrm[:,1],-nrm[:,0]],-1)
 for k in range(len(st)):
  if not cutst[k]:continue
  sd=side[k]
  if k+1<len(st) and cutst[k+1] and side[k+1]==sd:q=[pos[k]+nrm[k]*sd*E0,pos[k]+nrm[k]*sd*E1,pos[k+1]+nrm[k+1]*sd*E1,pos[k+1]+nrm[k+1]*sd*E0]
  elif k>0 and cutst[k-1] and side[k-1]==sd:continue
  else:a_,b_=pos[k]-tg[k]*2.5,pos[k]+tg[k]*2.5;q=[a_+nrm[k]*sd*E0,a_+nrm[k]*sd*E1,b_+nrm[k]*sd*E1,b_+nrm[k]*sd*E0]
  pg=Polygon(q);pg=pg if pg.is_valid else pg.buffer(0)
  if pg.area>0:band_polys.append(pg)
 cut_stats[name]=dict(stations=int(len(st)),offset_ge_half_m=int(moved.sum()),cut_stations=int(cutst.sum()),uphill_left=int((side[cutst]>0).sum()),uphill_right=int((side[cutst]<0).sum()),rise_across_p50_m=float(np.percentile(np.abs(rise[cutst]),50)) if cutst.any() else 0.)
 # RD1 probe for Check: the middle of the cut band (E0 + 1.25 m from the road line) at a station inside a run of three cut stations on one side (15 m of continuous band), outside every paddock and the water, so the atlas clay value there is the band's .8 (not an edge cell)
 for k in range(1,len(st)-1):
  if cutst[k-1] and cutst[k] and cutst[k+1] and side[k-1]==side[k]==side[k+1]:
   pp=pos[k]+nrm[k]*side[k]*(E0+1.25)
   if not any(pg.contains(Point(*pp)) for pg in PADS) and float(sample(tree_water,pp[0]*100,pp[1]*100))<.5:cut_stats[name]['probe_cm']=[float(pp[0]*100),float(pp[1]*100)];cut_stats[name]['probe_station_m']=float(g['s'][k]);break
_b=rasterize([(p,1) for p in band_polys],out_shape=(cH,cW),transform=A_ss,dtype='uint8').astype('float32') if band_polys else np.zeros((cH,cW),'float32')
band=np.clip(gaussian_filter(_b,.35/hS),0,1);bi=np.nonzero(band>.02);tanv=dem_at(_tan,CX[bi],CY[bi]);gate=np.zeros_like(band);gate[bi]=smooth(.45,.85,tanv)
bw=band[bi];rockv=sample(rock,CX[bi]*100,CY[bi]*100)
cut_gate_stats=dict(dem_tan_p10_p50_p90_in_band=[float(np.percentile(tanv[bw>.5],q)) for q in (10,50,90)] if (bw>.5).any() else [],orange_gate_mean_in_band=float(np.average(gate[bi],weights=bw)),
 band_area_share_with_style_rock_over_005=float(bw[rockv>.05].sum()/max(bw.sum(),1e-9)),band_area_share_with_style_rock_over_025=float(bw[rockv>.25].sum()/max(bw.sum(),1e-9)))
_padss=np.zeros((cH,cW),'float32')   # LP4: clay only where the track crosses: no cut-face clay or orange inside the paddocks (the track corridor and the yard stay)
for _p in PADS:_padss=np.maximum(_padss,rasterize([(_p,1)],out_shape=(cH,cW),transform=A_ss,dtype='uint8').astype('float32'))
# RD1 (owner 2026-10-19: "the roads are super slow and boggy ... they should be gravel roads"): every road is gravel, so the clay PHYSICS leaves the carriageway. The old track corridor (3.4 m radius, carriageway plus shoulders) is zero,
# and the carriageway strip (CORE_R 1.9 m = the 3.8 m road, 1 m blend) is carved out of the yard disc too; the cut band (.8) and the rest of the yard (1.0) stay clay.
CORE_R=1.9;core=1-smooth(CORE_R-.5,CORE_R+.5,dline)
clay_track_old=track*keep;clay_track=np.zeros_like(track);clay_yard_full=yard*keep;clay_yard=clay_yard_full*(1-core);clay_cut_all=.8*band*keep;clay_cut=clay_cut_all*(1-_padss);orange_all=band*gate*keep;orange=orange_all*(1-_padss);clay_ss=np.maximum(np.maximum(clay_track,clay_yard),clay_cut)
def down(a):return a.reshape(cH//SS,SS,cW//SS,SS).mean((1,3))
clay=np.zeros((N,N),'float32');clay[cj0:cj1,ci0:ci1]=down(clay_ss);orange_n=np.zeros((N,N),'float32');orange_n[cj0:cj1,ci0:ci1]=down(orange);yard_n=np.zeros((N,N),'float32');yard_n[cj0:cj1,ci0:ci1]=down(clay_yard)
bush=smooth(.3,.7,gaussian_filter(forest.astype('float32'),1.0))
# RD1 road lateral-distance atlas (carried in the clay atlas ALPHA, which was a constant 255 and is read by nothing in C++): for every road (all four, public and private) the signed perpendicular distance in cm from the cell centre to the tangent line at the
# nearest 25 cm centreline vertex (left normal positive), clamped to +-3.2 m and encoded A = d / 6.4 m + .5 (2.5 cm steps; A = 1 is "far", which is also the old constant). Bilinear sampling of a linear field is exact between the 1.8 m texel centres, so the shader reads the
# road corridor (gravel look, |d| < 2.0 m full, 2.6 m none) and the two wheel lines (|d| about .82 m) from it without a high-resolution texture. Near a road END the lateral value becomes the radial distance (|d| = hypot(d, along beyond the end)).
LAT_RANGE_CM=320.;lat_pts=[];lat_tan=[];lat_end=[]
for r_ in roads:
 if r_.get('surface')=='mud':continue  # Owner's new track uses the native mud material, never RD1 gravel.
 p_=np.asarray(r_['points'],float);cum_=np.concatenate([[0.],np.cumsum(np.hypot(*np.diff(p_,axis=0).T))]);s_=np.append(np.arange(0,cum_[-1],25.),cum_[-1])
 q_=np.stack([np.interp(s_,cum_,p_[:,0]),np.interp(s_,cum_,p_[:,1])],-1);t_=np.gradient(q_,axis=0);t_/=np.maximum(np.linalg.norm(t_,axis=1)[:,None],1e-9)
 e_=np.zeros(len(q_),int);e_[0]=-1;e_[-1]=1;lat_pts.append(q_);lat_tan.append(t_);lat_end.append(e_)
lat_P=np.concatenate(lat_pts);lat_T=np.concatenate(lat_tan);lat_E=np.concatenate(lat_end);lat_N=np.stack([-lat_T[:,1],lat_T[:,0]],-1)
lat_cx=(O+(np.arange(N)+.5)*STEP);lat_gx,lat_gy=np.meshgrid(lat_cx,lat_cx);lat_cells=np.stack([lat_gx.ravel(),lat_gy.ravel()],-1)
lat_dist,lat_idx=cKDTree(lat_P).query(lat_cells,k=1,distance_upper_bound=LAT_RANGE_CM*1.6,workers=-1);lat_ok=np.isfinite(lat_dist);lat_i=np.where(lat_ok,lat_idx,0)
lat_rel=lat_cells-lat_P[lat_i];lat_d=(lat_rel*lat_N[lat_i]).sum(1);lat_a=(lat_rel*lat_T[lat_i]).sum(1);lat_out=np.maximum(lat_a*lat_E[lat_i],0)   # along-track distance beyond a road end (0 inside the road)
lat_d=np.where(lat_E[lat_i]!=0,np.sign(lat_d+1e-9)*np.hypot(lat_d,lat_out),lat_d);lat_d=np.where(lat_ok,np.clip(lat_d,-LAT_RANGE_CM,LAT_RANGE_CM),LAT_RANGE_CM)
road_lat=(lat_d/(2*LAT_RANGE_CM)+.5).reshape(N,N).astype('float32')
lat_stats=dict(range_cm=LAT_RANGE_CM,step_cm=2*LAT_RANGE_CM/255.,vertices=int(len(lat_P)),cells_within_range=int((np.abs(lat_d)<LAT_RANGE_CM-1e-3).sum()),cells_in_carriageway_2m=int((np.abs(lat_d)<200).sum()),cells_with_wheel_line_band=int(((np.abs(lat_d)>60)&(np.abs(lat_d)<105)).sum()))
print('RD1 road lateral atlas',json.dumps(lat_stats))
cell=hS*hS;yard_cells=yard_n>.5
clay_stats=dict(window_native_px=[ci0,cj0,ci1,cj1],supersample=SS,cell_m=hS,
 area_m2=dict(track=float(clay_track.sum()*cell),yard=float(clay_yard.sum()*cell),cut=float((band*keep).sum()*cell),cut_net_of_track_and_yard=float(np.maximum(clay_cut-np.maximum(clay_track,clay_yard),0).sum()*cell),
  cut_orange_steep=float(orange.sum()*cell),union_all=float(clay_ss.sum()*cell),union_native_atlas=float(clay.sum()*Sm*Sm),track_removed_by_rd1=float(clay_track_old.sum()*cell),yard_carriageway_carved_by_rd1=float((clay_yard_full-clay_yard).sum()*cell)),
 excluded_m2=dict(yard_disc_less_rectangle=float(yard_pre.sum()*cell),yard_removed_by_forest=float((yard_pre*forest_ex).sum()*cell),yard_removed_by_water=float((yard*(1-keep)).sum()*cell),track_removed_by_water=float((track*(1-keep)).sum()*cell),house_rectangle_m2=96.),
 cut=dict(stats=cut_stats,gate=cut_gate_stats,band_polygons=len(band_polys)),
 grass=dict(yard_mean_before=float(grass[yard_cells].mean()) if yard_cells.any() else 0.,orange_cells=int((orange_n>.5).sum())),style_r_written=0.,mask_max=float(clay.max()),mask_cells_over_half=int((clay>.5).sum()))
grass=grass*(1-np.clip(yard_n,0,1))*(1-.9*np.clip(orange_n,0,1));clay_stats['grass']['yard_mean_after']=float(grass[yard_cells].mean()) if yard_cells.any() else 0.
# LP4 paddock ground: plain grazed grass. Style grass .95 (blended by coverage at the fence line), wet back to its pre-floor value, no rock; style R untouched; the paint (depth, firmness) change is the GP2c block below.
_pc=PAD_COV>.5;pad_ground=dict(cells_over_half=int(_pc.sum()),grass_mean_before=float(grass[_pc].mean()),wet_mean_before=float(wet[_pc].mean()),rock_mean_before=float(rock[_pc].mean()),rock_max_before=float(rock[_pc].max()),forest_cells_inside=int((forest[_pc]>.5).sum()),floor_peat_cells_restored=int((floor_w[_pc]>.01).sum()))
grass=grass*(1-PAD_COV)+.95*PAD_COV;wet=wet*(1-PAD_COV)+wet_before*PAD_COV;rock=rock*(1-PAD_COV)
pad_ground.update(grass_mean_after=float(grass[_pc].mean()),wet_mean_after=float(wet[_pc].mean()),rock_mean_after=float(rock[_pc].mean()),wet_changed_vs_pre_floor_max=float(np.abs(wet-wet_before)[_pc].max()))
# GP2c firm paddocks (owner 2026-10-18: HUD "sink 14.6 cm" on grazed pasture): inside the paddocks the paint depth (channel 0, /50 cm) becomes PAD_DEPTH_CM and the firmness (channel 2) .90, blended by the same coverage as the grass,
# and only where the road raster is below .003 so the clay track that crosses the paddocks keeps its authored depth and firmness. SampleSurface reads sinkage_cap_cm from paint channel 0 (x50 cm) TIMES the surface's LayerDepthScale (2.48 on this level, copied from the
# woodland level), so the 2 cm of the brief gave 4.86 cm at the trough (first Check, which asserts <= 4); 1.5 cm is 8/255 of 50 cm = 1.57 cm in the atlas, x2.48 = 3.89 cm (GP2c); GP2d: 1.0 cm, 2.43 cm.
PAD_DEPTH_CM=1.0   # GP2d second pass: 1.5 gave a worst-wheel sink of 7.5 cm at the chase spot (target under 3); 1.0 is 5/255 of 50 cm = .98 cm in the atlas, x LayerDepthScale 2.48 = 2.43 cm
# GP2d turf softness (owner 2026-10-18, GP2c chase spot: worst wheel 6.4 cm on grazed turf with softness .53): paint channel 3 (wet/softness: SampleSurface Softness, which sets the wheel's settle, rolling and spin terms and the friction) becomes PAD_SOFT inside the paddocks off the track, blended by the same coverage as depth and firmness.
PAD_SOFT=.22
_pe=_pc&(road<.003);_pw=PAD_COV*(road<.003)
pad_ground.update(paint_depth_cm_mean_before=float(paint[...,0][_pc].mean()*50),paint_firm_mean_before=float(paint[...,2][_pc].mean()),paint_depth_cm_mean_before_off_track=float(paint[...,0][_pe].mean()*50),paint_firm_mean_before_off_track=float(paint[...,2][_pe].mean()),
 paint_depth_cm_max_before_off_track=float(paint[...,0][_pe].max()*50),cells_over_half_off_track=int(_pe.sum()),cells_over_half_on_track=int((_pc&~_pe).sum()))
pad_ground.update(paint_soft_mean_before_off_track=float(paint[...,3][_pe].mean()));_soft_trk_before=paint[...,3][_pc&~_pe].copy()
paint[...,0]=paint[...,0]*(1-_pw)+(PAD_DEPTH_CM/50)*_pw;paint[...,2]=paint[...,2]*(1-_pw)+.90*_pw;paint[...,3]=paint[...,3]*(1-_pw)+PAD_SOFT*_pw
pad_ground.update(paint_depth_cm_mean_after=float(paint[...,0][_pc].mean()*50),paint_firm_mean_after=float(paint[...,2][_pc].mean()),paint_depth_cm_mean_after_off_track=float(paint[...,0][_pe].mean()*50),paint_firm_mean_after_off_track=float(paint[...,2][_pe].mean()),
 paint_depth_cm_max_after_off_track=float(paint[...,0][_pe].max()*50),paint_depth_cm_on_track_unchanged_max_abs=float(np.abs(paint[...,0][_pc&~_pe]*50).max()) if (_pc&~_pe).any() else 0.)
pad_ground.update(paint_soft_mean_after_off_track=float(paint[...,3][_pe].mean()),paint_soft_on_track_unchanged_max_abs=float(np.abs(paint[...,3][_pc&~_pe]-_soft_trk_before).max()) if (_pc&~_pe).any() else 0.)
print('GP2d paddock paint softness %.3f -> %.3f'%(pad_ground['paint_soft_mean_before_off_track'],pad_ground['paint_soft_mean_after_off_track']))
print('GP2c paddock paint depth cm %.2f -> %.2f, firm %.3f -> %.3f (off-track cells %d, track cells %d)'%(pad_ground['paint_depth_cm_mean_before_off_track'],pad_ground['paint_depth_cm_mean_after_off_track'],pad_ground['paint_firm_mean_before_off_track'],pad_ground['paint_firm_mean_after_off_track'],pad_ground['cells_over_half_off_track'],pad_ground['cells_over_half_on_track']))
# bush versus open along each private road: forest mask > .5 at five points across the 6.8 m corridor, station fraction >= .5 is bush, 15 m median, runs under 30 m merged into the longer neighbour
def bush_runs(rd,step=5.,min_run=30.):
 p=np.asarray(rd['points'])/100.;cum=np.concatenate([[0.],np.cumsum(np.hypot(*np.diff(p,axis=0).T))]);Lp=float(cum[-1]);s=np.arange(step/2,Lp,step)
 at=lambda v:np.stack([np.interp(v,cum,p[:,0]),np.interp(v,cum,p[:,1])],-1);c=at(s);t=at(np.minimum(s+5,Lp))-at(np.maximum(s-5,0));t/=np.maximum(np.linalg.norm(t,axis=1)[:,None],1e-9);nr=np.stack([-t[:,1],t[:,0]],-1)
 frac=np.mean([sample(forest,(c+nr*o)[:,0]*100,(c+nr*o)[:,1]*100)>.5 for o in (-3.4,-1.7,0.,1.7,3.4)],0);flag=median_filter((frac>=.5).astype(int),size=3,mode='nearest')
 e=[0]+[k for k in range(1,len(flag)) if flag[k]!=flag[k-1]]+[len(flag)];runs=[[e[i],e[i+1],int(flag[e[i]])] for i in range(len(e)-1)]
 while len(runs)>1:
  short=[i for i,r in enumerate(runs) if (r[1]-r[0])*step<min_run]
  if not short:break
  i=short[0];j=max([x for x in (i-1,i+1) if 0<=x<len(runs)],key=lambda x:runs[x][1]-runs[x][0]);lo,hi=min(i,j),max(i,j);runs[lo]=[runs[lo][0],runs[hi][1],runs[j][2]];del runs[hi]
  k=0
  while k<len(runs)-1:
   if runs[k][2]==runs[k+1][2]:runs[k]=[runs[k][0],runs[k+1][1],runs[k][2]];del runs[k+1]
   else:k+=1
 segs=[[round(a*step,1),round(b*step,1),f] for a,b,f in runs];segs[0][0]=0.;segs[-1][1]=round(float(rd['length_m']),1);return segs,frac
road_surface={}
for rd in roads:
 if rd['name'] in PRIV:
  segs,frac=bush_runs(rd);rd['surface']='gravel';rd['segments']=segs;   # RD1: every road is gravel; the segments (bush flag) stay for the farm hardware, the captures and the Check
  L_=float(rd['length_m']);bl=sum((b-a) for a,b,f in segs if f)
  road_surface[rd['name']]=dict(length_m=L_,bush_m=bl,open_m=L_-bl,bush_fraction=bl/L_,open_fraction=1-bl/L_,stations=int(len(frac)),stations_bush_raw=int((frac>=.5).sum()),segments=segs)
 elif rd.get('surface')!='mud':rd['surface']='gravel'
clay_stats['road_lateral']=lat_stats;clay_stats['paddock_cut_clay_removed_m2']=float((clay_cut_all-clay_cut).sum()*cell);clay_stats['paddock_orange_removed_m2']=float((orange_all-orange).sum()*cell);clay_stats['roads']=road_surface;print('CL1 clay',json.dumps({k:v for k,v in clay_stats.items() if k!='roads'}));print('CL1 roads',json.dumps(road_surface))
# LP4 farm hardware (lidar_farm.build): fences, strainers, gates, cattle stop, culverts, poles, troughs, bales, entrance signs. Needs the road segments (bush flag), the river/pond footprint and the drainage grids.
water_near_m=distance_transform_edt(~(river_bed|(pond_wm>0)))*STEP/100.;_bush_segs=road_surface['Riverside access']['segments']
HW=LF.build(dict(polys=PADS,priv=LF_PRIV,bush_flag=lambda s:any(a<=s<b and f for a,b,f in _bush_segs),forest=lambda x,y:float(sample(forest,x*100.,y*100.)),water_dist=lambda x,y:float(sample(water_near_m,x*100.,y*100.)),
 acc=hydro['acc'],filled=hydro['filled'],height_cm=lambda x,y:float(height(x,y)),rng=np.random.default_rng(20261018+4)))
_circles=unary_union([Point(x,y).buffer(r) for x,y,r in HW['clear']]);_pad_u=unary_union(PADS);_wing_u=unary_union([w.buffer(1.) for w in HW['wings']])
TREE_CLEAR=unary_union([_pad_u.buffer(1.2),_wing_u.buffer(.4),_circles.buffer(.5)]);UNDER_FENCE=unary_union([_pad_u.buffer(.8),_wing_u]);UNDER_HW=_circles
save('clay',np.stack([clay,orange_n,bush,road_lat],-1))   # RD1: A is the road lateral distance (see above); it was a constant 255
# RR1: the dry point has a shallow yielding gravel layer, not peat or clay.
_rrd,_rrk,_rrside,_rrreach,_rrbar=river_repair.sample(x/100,y/100)
_rrbar*=smooth(-.05,.20,z/100-rsurf[_rrk])
paint[...,0]=paint[...,0]*(1-_rrbar)+(5/2.48/50)*_rrbar
paint[...,2]=paint[...,2]*(1-_rrbar)+.84*_rrbar
paint[...,3]=paint[...,3]*(1-_rrbar)+.24*_rrbar
grass*=1-_rrbar
save('paint',paint);save('style',np.stack([np.zeros_like(grass),grass,wet,rock],-1))
def pack(n,v):
 q=np.uint16(np.clip(v,0,1)*65535+.5);Image.fromarray(np.stack([q>>8,q&255,np.zeros_like(q),np.full_like(q,255)],-1).astype('uint8')).save(OUT/(n+'.png'))
pack('macro',z/65536);pack('rest',(resize(-wetland*2-road*.5,1024)+50)/65)
# 8m irregular spacing in mapped woodland. Smaller coherent gaps occur within it.
tx,ty=np.meshgrid(np.arange(O+3500,-O-3500,800),np.arange(O+1500,-O-1500,800));tx=tx.ravel()+rng.uniform(-310,310,tx.size);ty=ty.ravel()+rng.uniform(-310,310,ty.size)
f=sample(forest,tx,ty);keep=(sample(road,tx,ty)<.003)&(sample(slope,tx,ty)<1.3)&(rng.random(tx.size)<f*(.8+.18*sample(broad,tx,ty)))
sites=[]
priority=[('Access entrance',(695,1230),-100),('Pond bend',(648,966),-90),('Riverside house',(579,393),-90),('Field spur',(601,795),-30)]
# Digitized review points sit 3-6m beside the registered road lines (2-5m
# aerial accuracy), and one road vertex crosses a 26 degree side slope. Each
# site is snapped onto its road and slid along it to the flattest bench within
# 40m, so the stationary review car rests on the road bed, heading along it.
road_lines=[LineString(r['points']) for r in roads]
def site_on_road(cx,cy,yaw):
 line=min(road_lines,key=lambda l:l.distance(Point(cx,cy)));s0=line.project(Point(cx,cy));best=None
 for s in np.arange(max(0,s0-4000),min(line.length,s0+4000)+1,100):
  p=line.interpolate(float(s));q=line.interpolate(float(min(line.length,s+200)));r=line.interpolate(float(max(0,s-200)));t=np.array([q.x-r.x,q.y-r.y]);t/=max(1e-6,np.linalg.norm(t));n=np.array([-t[1],t[0]])
  cross=float(height(p.x+n[0]*200,p.y+n[1]*200)-height(p.x-n[0]*200,p.y-n[1]*200))/400;along=float(height(p.x+t[0]*200,p.y+t[1]*200)-height(p.x-t[0]*200,p.y-t[1]*200))/400
  score=abs(cross)+.5*abs(along)+abs(s-s0)/40000
  if best is None or score<best[0]:best=(score,p.x,p.y,t,cross,along)
 score,x,y,t,cross,along=best;heading=math.degrees(math.atan2(t[1],t[0]))
 if math.cos(math.radians(heading-yaw))<0:heading+=180
 return float(x),float(y),(heading+180)%360-180,math.degrees(math.atan(cross)),math.degrees(math.atan(along))
for name,(px,py),yaw in priority:
 cx=(1196250+px*750/1182-1197144.5)*100;cy=(4865011.5-4865500+py*1300/2048)*100
 cx,cy,yaw,cross_deg,along_deg=site_on_road(cx,cy,yaw)
 sites.append(dict(name=name,center=[cx,cy],center_height_cm=float(height(cx,cy)),yaw=yaw,cross_slope_deg=cross_deg,along_slope_deg=along_deg))
inmap=lambda x,y:(x>O+3500)&(x<-O-3500)&(y>O+1500)&(y<-O-1500)
# LP3b canopy points: the 8m grid above stays everywhere except a near band (within 60m of any road line or site centre),
# which takes a 5m jittered grid (+-2m) with the same forest gate (road, slope, forest-mask probability).
canopy_near=unary_union([l.buffer(6000) for l in road_lines]+[Point(*s['center']).buffer(6000) for s in sites])
far8=~shapely.contains_xy(canopy_near,tx,ty);cb=canopy_near.bounds;nrng=np.random.default_rng(20261018)
gx,gy=np.meshgrid(np.arange(cb[0],cb[2],500),np.arange(cb[1],cb[3],500));gx=gx.ravel()+nrng.uniform(-200,200,gx.size);gy=gy.ravel()+nrng.uniform(-200,200,gy.size)
m=inmap(gx,gy)&shapely.contains_xy(canopy_near,gx,gy);nx5,ny5=gx[m],gy[m]
nkeep=(sample(road,nx5,ny5)<.003)&(sample(slope,nx5,ny5)<1.3)&(nrng.random(nx5.size)<sample(forest,nx5,ny5)*(.8+.18*sample(broad,nx5,ny5)))
tnear=np.concatenate([np.zeros(int(far8.sum()),bool),np.ones(nx5.size,bool)])
tx=np.concatenate([tx[far8],nx5]);ty=np.concatenate([ty[far8],ny5]);keep=np.concatenate([keep[far8],nkeep])
# Keep water clear of tree trunks and shrub geometry: the river's final wet footprint (LP2b,
# tree_water) replaces the 9m line buffer; wm (9m) still steers the road bench step above.
keep_old=keep&(sample(wm,tx,ty)<.5);keep&=sample(tree_water,tx,ty)<.5
for s in sites:
 cx,cy=s['center'];keep&=np.hypot(tx-cx,ty-cy)>800;keep_old&=np.hypot(tx-cx,ty-cy)>800
count=int(keep.sum());assert not (keep&(sample(river_bed,tx,ty)>0)).any(),'tree in river'
river_stats.update(trees_removed_from_water=int(keep_old.sum())-count,old_rule_trees_in_river_footprint=int((keep_old&(sample(river_bed,tx,ty)>0)).sum()))
# LP3b canopy kinds (kind -> SM_Canopy_k): 0 Beech_Mature, 1 Beech_Pole, 2 Beech_Edge (within 12m of the forest-mask edge), 3 DeadSpar
# (1.5% of interior points, replacing their tree). Inside the forest the pole probability is .8 where a low-frequency noise
# (about 30m cells) is above .5 and .2 elsewhere, so pole stands and mature stands alternate at 20-40m scale (about 49% each).
CANOPY=['SM_NZ_Beech_Mature','SM_NZ_Beech_Pole','SM_NZ_Beech_Edge','SM_NZ_DeadSpar']
manifest=json.loads((ROOT/'Art/Export/NativePlants/v01/manifest.json').read_text());KIT_SIZE={r['asset']:r['size_m'] for r in manifest['models'] if r['lod']==0}
krng=np.random.default_rng(20261017);pole_noise=resize(krng.random((120,120)),N)
txk,tyk,nearT=tx[keep],ty[keep],tnear[keep];edge=sample(inside_m,txk,tyk)<12.
pole_p=np.where(sample(pole_noise,txk,tyk)>.5,.8,.2)
kind=np.where(edge,2,np.where(krng.random(count)<pole_p,1,0));kind=np.where((~edge)&(krng.random(count)<.015),3,kind)
hlo=np.array([1900.,1100.,1400.,1100.]);hhi=np.array([2400.,1500.,1800.,1500.])
trees=np.stack([txk,tyk,height(txk,tyk),kind,krng.uniform(hlo[kind],hhi[kind]),krng.uniform(0,360,count)],-1)
# LP4: no trees inside the paddocks or within 1.2 m of their fence lines, or in the way of the hardware (filtered AFTER every random draw so the rest of the forest is identical)
_tin=shapely.contains_xy(TREE_CLEAR,trees[:,0]/100.,trees[:,1]/100.);trees_removed=dict(total=int(_tin.sum()),inside_paddocks=int(shapely.contains_xy(_pad_u,trees[:,0]/100.,trees[:,1]/100.).sum()),before=int(count))
trees=trees[~_tin];kind=kind[~_tin];nearT=nearT[~_tin];count=int((~_tin).sum())
(OUT/'trees.json').write_text(json.dumps(np.round(trees,2).tolist(),separators=(',',':')))
tree_kinds={CANOPY[k]:int((kind==k).sum()) for k in range(4)}
tree_kinds_by_regime={reg:{CANOPY[k]:int(((kind==k)&(nearT==(reg=='near_5m'))).sum()) for k in range(4)} for reg in ['near_5m','far_8m']}
# Crown cover estimate as before: sum of crown ellipse areas (kit footprint x scale^2) over the forest-mask area, capped at 1.
ksz=np.array([KIT_SIZE[n] for n in CANOPY]);kscale=trees[:,4]/100/ksz[kind,2];crown_m2=np.pi/4*ksz[kind,0]*ksz[kind,1]*kscale**2;forest_m2=float(forest.sum())*(STEP/100)**2
crown_cover=dict(estimate=float(min(1.,crown_m2.sum()/forest_m2)),uncapped_sum_over_forest=float(crown_m2.sum()/forest_m2),forest_km2=forest_m2/1e6,crown_km2=float(crown_m2.sum()/1e6),
 crown_km2_by_kind={CANOPY[k]:float(crown_m2[kind==k].sum()/1e6) for k in range(4)},crown_km2_by_regime=dict(near_5m=float(crown_m2[nearT].sum()/1e6),far_8m=float(crown_m2[~nearT].sum()/1e6)),
 near_band_km2=float(canopy_near.area/1e10),near_band_forest_km2=float((sample(forest,nx5,ny5)>.5).sum()*25/1e6),near_grid_points=int(nx5.size),far_grid_points=int(far8.sum()))
print('LP3b canopy',tree_kinds,tree_kinds_by_regime);print('LP3b crown cover',json.dumps(crown_cover));print('LP3b floor',json.dumps(floor_stats))
# LP3 understory. Kit meshes by habitat, two density regimes: a near band (35m of any road line, 60m of a site,
# 40m of the house anchor) at 1.0m mean spacing (LP3b, was 1.8m) and the old 12m grid elsewhere inside the forest. Entries carry the
# kit asset name; height_cm is the instance height (install scales the mesh to it).
import shapely
from shapely.geometry import MultiLineString
KIT_H={r['asset']:r['size_m'][2]*100 for r in manifest['models'] if r['lod']==0}
HOUSE_CM=np.array([-52264.44549,-26256.74983]);site_xy=np.array([s['center'] for s in sites])
PRIVATE=tuple(['Riverside access','Pond field spur']+[r['name'] for r in roads if r.get('surface')=='mud'])
priv=MultiLineString([l for l,r in zip(road_lines,roads) if r['name'] in PRIVATE]);pub=MultiLineString([l for l,r in zip(road_lines,roads) if r['name'] not in PRIVATE])
def road_edge_cm(x,y):
 p=shapely.points(x,y)
 edges=[]
 for l,r in zip(road_lines,roads):
  half=(3.8 if r['name'] in PRIVATE else 5.5)*50
  if r.get('authoring'):
   knots=np.r_[0,np.cumsum(np.linalg.norm(np.diff(np.array(r['points']),axis=0),axis=1))]
   half=np.interp(shapely.line_locate_point(l,p),knots,r['widths_cm'])/2
  edges.append(shapely.distance(p,l)-half)
 return np.minimum.reduce(edges)
near_geom=unary_union([l.buffer(3500) for l in road_lines]+[Point(*s['center']).buffer(6000) for s in sites]+[Point(*HOUSE_CM).buffer(4000)])
nb=near_geom.bounds
def jgrid(step,jit,x0,x1,y0,y1,test=None):
 # row blocks keep the 1m near grid (up to ~14M points before the masks) out of memory; test(x,y) -> bool mask is applied per block
 xs=np.arange(x0,x1,step);ys=np.arange(y0,y1,step);ox=[];oy=[]
 for r in range(0,len(ys),256):
  gx,gy=np.meshgrid(xs,ys[r:r+256]);gx=gx.ravel()+krng.uniform(-jit,jit,gx.size);gy=gy.ravel()+krng.uniform(-jit,jit,gy.size)
  if test is not None:m=test(gx,gy);gx,gy=gx[m],gy[m]
  ox.append(gx);oy.append(gy)
 return np.concatenate(ox),np.concatenate(oy)
def near_forest_test(x,y):
 m=inmap(x,y)&(sample(forest,x,y)>.5);out=np.zeros(x.size,bool);out[m]=shapely.contains_xy(near_geom,x[m],y[m]);return out
cellij=lambda x,y:(np.clip(((np.asarray(y)-O)/STEP).astype(int),0,N-1),np.clip(((np.asarray(x)-O)/STEP).astype(int),0,N-1))
# candidate points: near forest 1.0m (+-.5m, LP3b; was 1.8m), near margin 2.5m (open ground within 15m of the forest edge), far forest 12m
nx,ny=jgrid(100,50,nb[0],nb[2],nb[1],nb[3],near_forest_test)
gx,gy=jgrid(250,125,nb[0],nb[2],nb[1],nb[3]);m=inmap(gx,gy)&shapely.contains_xy(near_geom,gx,gy)&(sample(forest,gx,gy)<.5)&(sample(outside_m,gx,gy)<=15.);mx,my=gx[m],gy[m]
gx,gy=jgrid(1200,400,O+3500,-O-3500,O+1500,-O-1500);m=inmap(gx,gy)&(sample(forest,gx,gy)>.5)&~shapely.contains_xy(near_geom,gx,gy);fx,fy=gx[m],gy[m]
river_near=distance_transform_edt(~river_bed)*STEP/100<25.;wet_high=wetland>.5
tree_kd=cKDTree(np.stack([txk,tyk],-1))
def pick(n,weights):
 w=np.asarray(weights,float);return np.searchsorted(np.cumsum(w)/w.sum(),krng.random(n),side='right').clip(0,len(w)-1)
def variants(n,names,weights):return np.array(names,object)[pick(n,weights)]
CROWN_NEAR_W=[1,2,2]   # LP3b near band: crown fern A 20%, B 40%, C 40% (far regime keeps 1:1:1)
def crown_names(n,near):return variants(n,VAR['crown'][0],CROWN_NEAR_W if near else VAR['crown'][1])
CAT=['crown','tfern','hummock','twig','leaf','root','log','stump','kiokio'];CATP=[.70,.07,.06,.06,.04,.02,.01,.01,.03]
VAR=dict(crown=(['CrownFern_A','CrownFern_B','CrownFern_C'],[1,1,1]),tfern=(['TreeFern_A','TreeFern_B','TreeFern_Young'],[3,3,4]),hummock=(['MossHummock_A','MossHummock_B'],[1,1]),twig=(['TwigLitter_A','TwigLitter_B'],[1,1]),
 leaf=(['LeafLitter_A'],[1]),root=(['RootTangle_A'],[1]),log=(['Log_A','Log_B'],[1,1]),stump=(['Stump_A'],[1]),kiokio=(['Kiokio_A','Kiokio_B'],[1,1]))
MARGIN=dict(coprosma=(['Coprosma_A','Coprosma_B'],[1,1],.40),gorse=(['Gorse_A','Gorse_B'],[1,1],.20),tussock=(['VergeTussock_A','VergeTussock_B'],[1,1],.30),broom=(['Broom_A'],[1],.10))
SCALE=dict(MossHummock=(.8,1.5),TwigLitter=(.8,1.3),LeafLitter=(.8,1.3),RootTangle=(.8,1.2),Log=(.6,1.1),Stump=(.8,1.2),Kiokio=(.8,1.3),Coprosma=(.8,1.3),Gorse=(.6,1.1),VergeTussock=(.8,1.5),Broom=(.8,1.2),Harakeke=(.8,1.2))
def heights(names,reg):
 out=np.zeros(len(names))
 for i,n in enumerate(names):
  stem=n.rsplit('_',1)[0]
  if stem=='CrownFern':out[i]=krng.uniform(85,140) if reg[i]==0 else krng.uniform(55,100)   # LP3b near band 85-140cm, far regime unchanged
  elif n=='TreeFern_Young':out[i]=krng.uniform(135,165)
  elif stem=='TreeFern':out[i]=krng.uniform(350,500)
  else:lo,hi=SCALE[stem];out[i]=krng.uniform(lo,hi)*KIT_H['SM_NZ_'+n]
 return out
# forest floor kinds by habitat (weights above); regime 0 near, 1 far
px_=np.concatenate([nx,fx]);py_=np.concatenate([ny,fy]);regime=np.concatenate([np.zeros(nx.size,int),np.ones(fx.size,int)])
cat=np.array(CAT,object)[pick(px_.size,CATP)];names=np.empty(px_.size,object);ok=np.ones(px_.size,bool)
for c,(vn,vw) in VAR.items():
 sel=cat==c
 if c=='crown':
  for near in (True,False):
   s2=sel&(regime==(0 if near else 1));names[s2]=crown_names(int(s2.sum()),near)
 else:names[sel]=variants(int(sel.sum()),vn,vw)
# kiokio only on wet ground (wetland mask high, or within 25m of the river's wet cells); elsewhere the draw becomes crown fern
ci=cellij(px_,py_);wetish=wet_high[ci]|river_near[ci]
swap=(cat=='kiokio')&~wetish
for near in (True,False):
 s2=swap&(regime==(0 if near else 1));names[s2]=crown_names(int(s2.sum()),near)
cat[swap]='crown'
# root tangle sits at a trunk base: snap to the nearest tree within 3m, else skip
rt=np.flatnonzero(cat=='root')
if rt.size:
 dd,ii=tree_kd.query(np.stack([px_[rt],py_[rt]],-1),distance_upper_bound=300.);hit=np.isfinite(dd);ok[rt[~hit]]=False
 px_[rt[hit]]=txk[ii[hit]]+krng.uniform(-40,40,int(hit.sum()));py_[rt[hit]]=tyk[ii[hit]]+krng.uniform(-40,40,int(hit.sum()))
# forest margin scrub on the open side, near band only
mc=np.array(list(MARGIN),object)[pick(mx.size,[v[2] for v in MARGIN.values()])];mnames=np.empty(mx.size,object)
for c,(vn,vw,_) in MARGIN.items():
 sel=mc==c;mnames[sel]=variants(int(sel.sum()),vn,vw)
# open ground by the house: 8 flax in 3 clumps and 30 verge tussock in 6, scattered 8-32m from the anchor, clear of the road, water and the forest
hx=[];hy=[];hn=[];tries=0
for ncl,pool,total,spread in [(3,['Harakeke_A','Harakeke_B'],8,250.),(6,['VergeTussock_A','VergeTussock_B'],30,300.)]:
 centres=[]
 while len(centres)<ncl and tries<20000:
  tries+=1;a=krng.uniform(0,2*math.pi);r=krng.uniform(800,3200);cx,cy=HOUSE_CM+r*np.array([math.cos(a),math.sin(a)])
  if sample(forest,cx,cy)>.5 or sample(outside_m,cx,cy)<6 or float(road_edge_cm(cx,cy))<350 or sample(wm,cx,cy)>=.5 or sample(tree_water,cx,cy)>=.5 or np.hypot(*(site_xy-[cx,cy]).T).min()<800:continue
  centres.append((cx,cy))
 assert len(centres)==ncl,('house clearing too small for the scatter',pool)
 made=0;guard=0;bigp=pool[0].startswith('Harakeke')
 while made<total:   # every member passes the same filters as the rest of the understory, so the totals (8 flax, 30 tussock) hold
  guard+=1;assert guard<5000,('house scatter',pool)
  cx,cy=centres[made%ncl];x=cx+krng.normal(0,spread/2);y=cy+krng.normal(0,spread/2)
  if sample(forest,x,y)>.5 or sample(slope,x,y)>=1.2 or sample(wm,x,y)>=.5 or sample(tree_water,x,y)>=.5 or float(road_edge_cm(x,y))<=(200. if bigp else 60.) or np.hypot(*(site_xy-[x,y]).T).min()<=800:continue
  hx.append(x);hy.append(y);hn.append(str(krng.choice(pool)));made+=1
hx=np.array(hx);hy=np.array(hy);hn=np.array(hn,object)
# assemble and filter: slope, water (wm and the river footprint), the 8m site circles, road clearance by size, logs off the road mask
ax=np.concatenate([px_[ok],mx,hx]);ay=np.concatenate([py_[ok],my,hy]);an=np.concatenate([names[ok],mnames,hn]);areg=np.concatenate([regime[ok],np.full(mx.size,2),np.full(hx.size,3)])
big=np.array([any(t in n for t in ('TreeFern','Stump','Log','Coprosma','Gorse','Broom','Harakeke')) for n in an])
edge_cm=road_edge_cm(ax,ay)
good=inmap(ax,ay)&(sample(slope,ax,ay)<1.2)&(sample(wm,ax,ay)<.5)&(sample(tree_water,ax,ay)<.5)&(edge_cm>np.where(big,200.,60.))
for s in sites:good&=np.hypot(ax-s['center'][0],ay-s['center'][1])>800
good&=~(np.array([n.startswith('Log_') for n in an])&(sample(road,ax,ay)>.003))
ax,ay,an,areg=ax[good],ay[good],an[good],areg[good]
# cap at 260k: thin the far regime first, then the near band
CAP=260000;thinned={'before_cap':int(ax.size)}
if ax.size>CAP:
 far=np.flatnonzero(areg==1);dropn=min(ax.size-CAP,far.size);thinned['far_dropped']=int(dropn);keepm=np.ones(ax.size,bool);keepm[krng.choice(far,dropn,replace=False)]=False
 if ax.size-dropn>CAP:
  rest=np.flatnonzero(keepm&(areg==0));d2=ax.size-dropn-CAP;thinned['near_dropped']=int(d2);keepm[krng.choice(rest,d2,replace=False)]=False
 ax,ay,an,areg=ax[keepm],ay[keepm],an[keepm],areg[keepm]
ah=heights(an,areg);ayaw=krng.uniform(0,360,ax.size);az=height(ax,ay)
# LP4: nothing of the understory inside the three paddocks, within .8 m of their fence lines or entrance wings, or under the hardware (after every random draw, so the rest is identical)
_in=shapely.contains_xy(_pad_u,ax/100.,ay/100.);_fn=shapely.contains_xy(UNDER_FENCE,ax/100.,ay/100.)&~_in;_hw=shapely.contains_xy(UNDER_HW,ax/100.,ay/100.)&~_in&~_fn;_drop=_in|_fn|_hw
under_removed=dict(total=int(_drop.sum()),inside_paddocks=int(_in.sum()),fence_margin=int(_fn.sum()),hardware_clearance=int(_hw.sum()),before=int(ax.size),by_mesh={},by_regime={})
for _n,_r,_a,_b,_c in zip(an[_drop],areg[_drop],_in[_drop],_fn[_drop],_hw[_drop]):
 _d=under_removed['by_mesh'].setdefault('SM_NZ_'+_n,dict(inside_paddocks=0,fence_margin=0,hardware_clearance=0));_d['inside_paddocks' if _a else 'fence_margin' if _b else 'hardware_clearance']+=1
 _k=['near_forest','far_forest','margin','house'][int(_r)];under_removed['by_regime'][_k]=under_removed['by_regime'].get(_k,0)+1
under_removed['by_mesh']=dict(sorted(under_removed['by_mesh'].items()))
ax,ay,an,areg,ah,ayaw,az=[v[~_drop] for v in (ax,ay,an,areg,ah,ayaw,az)]
under=[dict(kind='SM_NZ_'+n,p=[round(float(x),1),round(float(y),1),round(float(z),1)],height_cm=round(float(h),1),yaw=round(float(w),1)) for n,x,y,z,h,w in zip(an,ax,ay,az,ah,ayaw)]
(OUT/'understory.json').write_text(json.dumps(under,separators=(',',':')))
under_by_mesh={}
for n in an:under_by_mesh['SM_NZ_'+n]=under_by_mesh.get('SM_NZ_'+n,0)+1
under_by_mesh=dict(sorted(under_by_mesh.items()))
under_regimes={k:int((areg==i).sum()) for i,k in enumerate(['near_forest','far_forest','margin','house'])}
REG_NAMES=['near_forest','far_forest','margin','house'];under_by_regime_mesh={REG_NAMES[i]:{} for i in range(4)}
for n_,r_ in zip(an,areg):
 d_=under_by_regime_mesh[REG_NAMES[int(r_)]];d_['SM_NZ_'+n_]=d_.get('SM_NZ_'+n_,0)+1
under_by_regime_mesh={k:dict(sorted(v.items())) for k,v in under_by_regime_mesh.items()}
print('LP3b understory by regime and mesh',json.dumps(under_by_regime_mesh));print('LP3 canopy kinds',tree_kinds);print('LP3 understory',len(under),under_regimes,thinned);print(json.dumps(under_by_mesh))
# LP3 captures: the bush climb 400m (along the road) before the house end of Riverside access, and 15m from the house anchor
def lp3_captures():
 cands=[(l,r) for l,r in zip(road_lines,roads) if r['name']=='Riverside access'];line,_=min(cands,key=lambda lr:min(Point(lr[0].coords[0]).distance(Point(*HOUSE_CM)),Point(lr[0].coords[-1]).distance(Point(*HOUSE_CM))))
 if Point(line.coords[0]).distance(Point(*HOUSE_CM))<Point(line.coords[-1]).distance(Point(*HOUSE_CM)):line=LineString(list(line.coords)[::-1])
 L=line.length;best=None
 for back in np.arange(250,801,10):  # metres before the house end; the spot nearest 400m with 30m of forest around it
  s=L-back*100;q=line.interpolate(s);tgt=line.interpolate(min(L,s+3000))
  if float(sample(inside_m,q.x,q.y))<30:continue
  if best is None or abs(back-400)<abs(best[0]-400):best=(float(back),[q.x,q.y],[tgt.x,tgt.y])
 assert best,'no forest stretch of the climb found'
 yard=None
 for deg in range(0,360,15):  # camera 15m from the anchor on open ground, bush wall 10-45m behind the anchor
  u_=np.array([math.cos(math.radians(deg)),math.sin(math.radians(deg))]);cam=HOUSE_CM+u_*1500
  if sample(forest,*cam)>.5 or sample(outside_m,*cam)<4 or sample(wm,*cam)>=.5 or sample(tree_water,*cam)>=.5:continue
  wall=None
  for dcm in range(300,5001,100):
   b=HOUSE_CM-u_*dcm
   if sample(forest,*b)>.5:wall=dcm;break
  if wall is None or not 1000<=wall<=4500:continue
  sc_=abs(wall-2500)
  if yard is None or sc_<yard[0]:yard=(sc_,cam.tolist(),wall,deg)
 assert yard,'no open camera position 15m from the house anchor'
 return dict(Bush_track=dict(road='Riverside access',metres_before_house_end=best[0],pos_cm=best[1],target_cm=best[2],eye_height_cm=160),House_yard=dict(anchor_cm=HOUSE_CM.tolist(),pos_cm=yard[1],bush_wall_behind_anchor_cm=yard[2],bearing_deg=yard[3],eye_height_cm=160))
captures=lp3_captures()
# CL1 capture Clay_track_open: Riverside access 300 m from the gate (the end of the line farthest from the house), looking along the track toward the house end, on open ground:
# the spot nearest 300 m (150..700 m searched) whose 60 m ahead has no forest mask > .3 within 8 m of the centreline and none behind the camera within 10 m.
def clay_capture():
 rd=next(r for r in roads if r['name']=='Riverside access');line=LineString(rd['points'])
 if Point(line.coords[0]).distance(Point(*HOUSE_CM))<Point(line.coords[-1]).distance(Point(*HOUSE_CM)):line=LineString(list(line.coords)[::-1])
 best=None
 for back in np.arange(150,701,10):
  s=back*100.;q=line.interpolate(s);ahead=[line.interpolate(s+d) for d in range(0,6001,500)];behind=line.interpolate(max(0,s-1000))
  if any(float(sample(forest,a.x,a.y))>.3 for a in ahead) or float(sample(forest,behind.x,behind.y))>.3:continue
  tg=np.array([ahead[1].x-q.x,ahead[1].y-q.y]);tg/=np.linalg.norm(tg);nr=np.array([-tg[1],tg[0]])
  if any(float(sample(forest,a.x+nr[0]*800*sgn,a.y+nr[1]*800*sgn))>.3 for a in ahead[:7] for sgn in (-1,1)):continue
  if best is None or abs(back-300)<abs(best[0]-300):best=(float(back),[q.x,q.y],[line.interpolate(s+3000).x,line.interpolate(s+3000).y])
 assert best,'no open stretch of Riverside access 150..700 m from the gate'
 return dict(road='Riverside access',metres_from_gate=best[0],pos_cm=best[1],target_cm=best[2],eye_height_cm=160)
captures['Clay_track_open']=clay_capture()
# LP4 captures (eye 1.6 m): Paddock_gate = 12 m outside the fence before the first gate on Riverside access, looking through the gate at the far fence and the bush wall beyond;
# Entrance = 15 m of track before the cattle stop at the Waimeamea Road junction, looking along the track at the stop, the fence wings, the sign and the letterbox.
def lp4_captures():
 ra_m=LF_PRIV['Riverside access'];ral=LineString(ra_m);gs=[g for g in HW['info']['gates'] if g['road']=='Riverside access'];assert gs,'no gate on Riverside access'
 g=min(gs,key=lambda g:ral.project(Point(*g['centre_m'])));sg=float(ral.project(Point(*g['centre_m'])));c=np.array(g['centre_m']);a=np.array(g['approach']);back=next((dd for dd in (12.,10.,8.,6.) if float(sample(forest,*((c-a*dd)*100.)))<.5 and float(sample(tree_water,*((c-a*dd)*100.)))<.5),6.);cam=c-a*back   # 12 m back along the approach (outside the fence), nearer only if that spot is bush or water
 hit=LineString([c+a*.5,c+a*400.]).intersection(PADS[g['paddock']]);far=float(max((x.length for x in (hit.geoms if hasattr(hit,'geoms') else [hit])),default=60.)) if not hit.is_empty else 60.
 tgt=c+a*(far+10.);e=HW['info']['entrance'];ec=np.array(e['stop_m']);tt=np.array(e['track_tangent']);ep=LF.along(ra_m,e['stop_station_m']-15.)[0]
 return dict(Paddock_gate=dict(road='Riverside access',gate_paddock=int(g['paddock']),gate_centre_cm=[float(c[0]*100),float(c[1]*100)],metres_before_gate=back,gate_station_m=sg,far_fence_m=far,pos_cm=[float(cam[0]*100),float(cam[1]*100)],target_cm=[float(tgt[0]*100),float(tgt[1]*100)],target_up_cm=300,eye_height_cm=160),
  Entrance=dict(road='Riverside access',metres_before_stop=15.,pos_cm=[float(ep[0]*100),float(ep[1]*100)],target_cm=[float((ec+tt*6)[0]*100),float((ec+tt*6)[1]*100)],target_up_cm=100,eye_height_cm=160))
captures.update(lp4_captures());print('LP3 captures',json.dumps(captures))
hw_by_mesh={};[hw_by_mesh.__setitem__(i['mesh'],hw_by_mesh.get(i['mesh'],0)+1) for i in HW['items']];hw_by_mesh=dict(sorted(hw_by_mesh.items()))
(OUT/'hardware.json').write_text(json.dumps(HW['items'],separators=(',',':')))
(OUT/'roads.json').write_text(json.dumps(roads,indent=2));(OUT/'sites.json').write_text(json.dumps(sites,indent=2))
# Local patches retain 1m sampling rather than allocating a full-map wet grid.
water=[]
for i,f in enumerate([f for f in features if f['properties']['kind'] in ['river','pond'] and (f['properties']['kind']!='river' or f['properties'].get('source')=='LiDAR drainage')]):
 g=shape(f['geometry']).intersection(__import__('shapely').geometry.box(-1817,-1849,1817,1849));river=f['properties']['kind']=='river';shape_water=g.buffer(20.,cap_style=2) if river else g
 lo=np.floor(np.array(shape_water.bounds[:2])-3);hi=np.ceil(np.array(shape_water.bounds[2:])+3)
 step=2. if river else 1.;xs=np.arange(lo[0]+step*.5,hi[0],step);ys=np.arange(lo[1]+step*.5,hi[1],step);wx,wy=np.meshgrid(xs,ys);bed=height(wx*100,wy*100)/100
 if river:
  # LP2b channel model (above): surface at the nearest 1m course station, bed and depth
  # from the repaired landscape. Depth remains inferred: no bathymetric survey.
  assert g.equals(rg);dist,idx,mean,bed=river_cells(wx,wy);vx=rtang[idx,0]*rspeed[idx]*rsign;vy=rtang[idx,1]*rspeed[idx]*rsign
 else:
  mask0=rasterize([(g,1)],out_shape=wx.shape,transform=Affine(step,0,lo[0],0,step,lo[1]),dtype='uint8')>0
  mean=np.full_like(bed,np.percentile(bed[mask0],75)+.12);vx=np.zeros_like(bed);vy=np.zeros_like(bed)
 mask=rasterize([(shape_water,1)],out_shape=wx.shape,transform=Affine(step,0,lo[0],0,step,lo[1]),dtype='uint8')>0
 depth=mean-bed;wet=mask&(depth>.015);dcap=1.5 if river else np.inf
 assert not wet.any() or depth[wet].max()<6, (name if 'name' in locals() else 'water',float(depth[wet].max()))
 records=np.stack([mean*100,np.where(wet,np.minimum(depth,dcap),-1),vx,vy],-1).astype('<f4')
 if river:
  near_house=(wx+522.6444549)**2+(wy+262.5674983)**2
  hj,hk=np.unravel_index(np.where(wet&(depth>.15),near_house,np.inf).argmin(),wet.shape);river_house_probe=[float(wx[hj,hk]*100),float(wy[hj,hk]*100),float(mean[hj,hk]*100)]
 name='River' if river else ('AccessPond' if f['properties'].get('source')=='priority aerial' else 'MappedPond');path=OUT/(name+'-domain.bin');path.write_bytes(struct.pack('<5i3f',0x47545744,len(xs),len(ys),1,1,lo[0]*100,lo[1]*100,step*100)+records.tobytes()+bytes([0]))
 signed=(distance_transform_edt(wet)-distance_transform_edt(~wet))*step
 save(name+'-flow',np.stack([.5+vx/4,.5+vy/4,np.clip(depth,0,dcap)/2,np.zeros_like(bed)],-1));save(name+'-shore',np.stack([.5+signed/4,.5+signed/4,wet,np.ones_like(wet)],-1))
 domain_wet_cells=int(wet.sum());domain_max_depth=float(min(depth[wet].max(),dcap));best=np.unravel_index(np.where(wet,depth,0).argmax(),depth.shape);probe=[float(wx[best]*100),float(wy[best]*100),float(mean[best]*100)]
 if river:
  # What the material's white-water gate (rapidShallow*rapidCurrent, before its 0.3-1 patch noise) sees on the 2m domain.
  wsp=np.hypot(vx,vy);wd=np.clip(depth,0,dcap);gate=smooth(.025,.10,wd)*(1-smooth(.28,.72,wd))*smooth(.35,1.05,wsp)
  river_stats.update(max_depth_unclamped_cm=float(depth[wet].max()*100),cells_over_cap=int((depth[wet]>dcap).sum()),whitewater_gate_over_03_pct=float(100*(gate[wet]>.3).mean()),pool_cells_over_072m_pct=float(100*(depth[wet]>.72).mean()),
   whitewater_gate_in_pools_pct=float(100*(gate[wet&(depth>.72)]>.3).mean()) if (wet&(depth>.72)).any() else 0.)
 # Water geometry follows the imported bed at 1m; interaction storage remains
 # the bounded 2m river domain. A geometric signed boundary avoids raster steps.
 if river:
  # The 1m grid computed with the channel model above (same bounds, same clip rule).
  assert (lo==rlo).all() and (hi==rhi).all();wx,wy,distance_to_course,mean,depth=rwx,rwy,rdist,rmean,rdepth
 from shapely import points as shp_points,distance as shp_distance,contains_xy
 geom_distance=(20-distance_to_course.reshape(wx.shape)) if river else shp_distance(shp_points(wx,wy),shape_water.boundary)*np.where(contains_xy(shape_water,wx,wy),1,-1)
 clip_depth=np.minimum(depth-.015,geom_distance*.2);wet=clip_depth>0
 # Clipped triangles interpolate wet/dry depth, removing grid-shaped banks.
 verts=[];faces=[]
 active=wet[:-1,:-1]|wet[1:,:-1]|wet[:-1,1:]|wet[1:,1:]
 for row,col in zip(*np.nonzero(active)):
  if True:
   for corners in [[(row,col),(row+1,col),(row,col+1)],[(row,col+1),(row+1,col),(row+1,col+1)]]:
    poly=[(np.array([wx[j,k],wy[j,k],mean[j,k]])*100,clip_depth[j,k]) for j,k in corners];clipped=[]
    for a,b in zip(poly,poly[1:]+poly[:1]):
     if a[1]>0:clipped.append(a[0])
     if (a[1]>0)!=(b[1]>0):clipped.append(a[0]+(b[0]-a[0])*a[1]/(a[1]-b[1]))
    if len(clipped)<3:continue
    first=len(verts)+1;verts+=clipped
    for j in range(1,len(clipped)-1):faces.append((first,first+j,first+j+1))
 obj=['v %.5f %.5f %.5f'%(v[0],-v[1],v[2]) for v in verts]+['f %d %d %d'%t for t in faces]
 (OUT/(name+'.obj')).write_text('\n'.join(obj))
 water.append(dict(name=name,label=f['properties'].get('name','Mapped pond'),origin_cm=(lo*100).tolist(),span_cm=[len(xs)*step*100,len(ys)*step*100],wet_cells=domain_wet_cells,triangles=len(faces),max_depth_cm=domain_max_depth*100,probe=probe,bathymetry='Not surveyed; surface inferred from DEM elevations',first_vertex=verts[0].tolist()))
 if river:water[-1].update(river_stats);print('LP2b River',json.dumps(river_stats))
report=dict(ok=True,trees=count,tree_kinds=tree_kinds,tree_kinds_by_regime=tree_kinds_by_regime,crown_cover=crown_cover,floor_style=floor_stats,understory=len(under),understory_by_mesh=under_by_mesh,understory_by_regime_mesh=under_by_regime_mesh,understory_regimes=under_regimes,understory_thinned=thinned,captures=captures,forest_fraction=float(forest.mean()),road_length_m=sum(r['length_m'] for r in roads),roads=len(roads),sites=sites,water=water,terrain_source_unchanged=True,attribution='OpenStreetMap contributors (ODbL), including LINZ-origin landcover; original LINZ LiDAR tiles',land_use='Registered mapped forest/clearings and road lines; tree species and individual placements are approximations')
report['river_house_probe']=river_house_probe;report['clay']=clay_stats
report['authoring']=authoring_report
report['bench_report']=bench_report
report['paddocks']=dict(rule=pad['rule'],aerial_px_m=pad['aerial_px_m'],split_u=pad['split_u'],candidates=[{k:v for k,v in c.items() if k!='polygon'} for c in pad['candidates']],ground=pad_ground,trees_removed=trees_removed,understory_removed=under_removed,
 polygons=[dict(index=i,area_m2=c['area_polygon_m2'],area_ha=c['area_polygon_m2']/1e4,aerial_area_m2=c['area_m2'],vertices=c['vertices'],perimeter_m=c['perimeter_m'],min_edge_m=c['min_edge_m'],dist_to_private_road_m=c['dist_to_private_road_m'],
  polygon_cm=[[round(x*100,1),round(y*100,1)] for x,y in c['polygon'].exterior.coords]) for i,c in enumerate(pad['paddocks'])])
report['hardware']=dict(by_mesh=hw_by_mesh,total=len(HW['items']),info={k:v for k,v in HW['info'].items()})
report['hardware_by_mesh']=hw_by_mesh
# A local bank edit must not reroll the entire forest merely because two more
# candidates survived a water mask, advancing the shared RNG by two draws.
# Retain the prior authored placement records when terrain changes are confined
# to this correction and road/source inputs are identical; reseat/remove locally.
prior=Path(os.environ.get('GT_LIDAR_VEGETATION_BASELINE',str(BASE/'Place')))
if (prior/'prepare.json').exists() and (prior/'authoring-height.r16').exists():
 old_report=json.loads((prior/'prepare.json').read_text());old_h=np.fromfile(prior/'authoring-height.r16','<u2').reshape(2017,2017)
 stations=np.concatenate([np.arange(*b['guide_station_range_m']) for b in RR.bank_definitions()])
 bounds=np.vstack([source_rps[stations],rps[stations]]);lo=bounds.min(0)-30;hi=bounds.max(0)+30
 local=(_hx>=lo[0])&(_hx<=hi[0])&(_hy>=lo[1])&(_hy<=hi[1])
 same_inputs=all(old_report.get('authoring',{}).get(k)==authoring_report[k] for k in ['design_digest','source_height_sha256'])
 if not same_inputs and old_report.get('authoring',{}).get('source_height_sha256')==authoring_report['source_height_sha256']:
  # A bank-only vertical correction of the saved track cannot affect distant
  # vegetation. Require identical route metadata/XY and bound every Z change.
  import copy
  old_paths=[v['authoring'] for v in json.loads((prior/'roads.json').read_text()) if 'authoring' in v]
  new_paths=[v['authoring'] for v in roads if 'authoring' in v]
  normalized=copy.deepcopy(new_paths);safe=len(old_paths)==len(new_paths) and len(old_paths)>0
  for before,after in zip(old_paths,normalized):
   bp=before['points_cm'];ap=after['points_cm']
   if len(bp)!=len(ap):safe=False;break
   length=sum(math.dist(a,b) for a,b in zip(ap,ap[1:]))/100
   for a,b in zip(after.get('conditions',[]),before.get('conditions',[])):
    if b['end_metres']>length and a['end_metres']==length:a['end_metres']=b['end_metres']
   for a,b in zip(ap,bp):
    if a==b:continue
    if a[:2]!=b[:2] or abs(a[2]-b[2])>100 or float(river_repair.bank_mask(np.array([a[:2]])/100)[0])<.999:safe=False
    a[2]=b[2]
  same_inputs=safe and normalized==old_paths
 if same_inputs and np.array_equal(old_h[~local],_encoded[~local]):
  from collections import Counter
  persistence={}
  for filename in ['trees.json','understory.json']:
   old=json.loads((prior/filename).read_text());xy=np.array([v[:2] if filename=='trees.json' else v['p'][:2] for v in old])
   localp=np.all((xy/100>=lo)&(xy/100<=hi),axis=1)
   remove=localp&((sample(tree_water,xy[:,0],xy[:,1])>.5)|(river_repair.bank_mask(xy/100)>.1))
   revised=[]
   for index,value in enumerate(old):
    if remove[index]:continue
    if localp[index]:
     xyz=value if filename=='trees.json' else value['p'];xyz[2]=round(float(height(*xy[index])),2 if filename=='trees.json' else 1)
    revised.append(value)
   (OUT/filename).write_text(json.dumps(revised,separators=(',',':')))
   persistence[filename]=dict(before=len(old),after=len(revised),removed_local=int(remove.sum()),retained_outside=int((~localp).sum()))
   if filename=='trees.json':report['trees']=len(revised);report['tree_kinds']={CANOPY[k]:sum(int(v[3])==k for v in revised) for k in range(4)}
   else:report['understory']=len(revised);report['understory_by_mesh']=dict(Counter(v['kind'] for v in revised))
  report['vegetation_persistence']=dict(bounds_m=[lo.tolist(),hi.tolist()],records=persistence,note='Unchanged records outside bank correction preserved exactly; candidate regime/crown statistics above precede this local retention.')
(OUT/'paddocks.json').write_text(json.dumps(report['paddocks'],indent=1))
(OUT/'prepare.json').write_text(json.dumps(report,indent=2));print(json.dumps(report,indent=2))
