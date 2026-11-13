"""Transfer sampled LiDAR logging-road soil character, retaining FloraDrive's relief."""
from pathlib import Path
import json,math,numpy as np
from PIL import Image
from make_mud_road import centre
O=Path('C:/GrandTour/Art/Export/FloraDrive');L=O/'LidarMud';ref=json.loads((L/'reference.json').read_text());assert ref['ok']
n=512;y,x=np.mgrid[:n,:n];x=-3150+(x+.5)*6300/n;y=-3150+(y+.5)*6300/n
d=(y-(530*np.sin((x+2200)/1050)-150))/np.sqrt(1+(530/1050*np.cos((x+2200)/1050))**2)
station=np.clip(170+(x+2450)/4900*90,170,260);across=np.abs(d)/100
smooth=lambda a,b,t:np.clip((t-a)/(b-a),0,1)**2*(3-2*np.clip((t-a)/(b-a),0,1))
cover=(1-smooth(240,330,np.abs(d)))*smooth(-2850,-2450,x)*(1-smooth(2450,2850,x));scale=ref['settings']['layer_depth_scale']
stations=sorted(set(r['station'] for r in ref['samples']));offsets=sorted(set(r['across'] for r in ref['samples']))
def sample(key):
    cols=[np.interp(station,stations,[next(r[key] for r in ref['samples'] if r['station']==s and r['across']==a) for s in stations]) for a in offsets]
    result=cols[-1].copy()
    for k in reversed(range(len(offsets)-1)):
        t=np.clip((across-offsets[k])/(offsets[k+1]-offsets[k]),0,1)
        result=np.where(across<=offsets[k+1],cols[k]*(1-t)+cols[k+1]*t,result)
    return result
old=np.array(Image.open(O/'BeforeLidarMudRocks/soil-paint.png').convert('RGBA'),dtype=float)/255
height=np.load(O/'road-rest-heights.npy');old_depth=old[:,:,0]*50
desired=sample('sinkage_cap_cm');minimum=np.maximum(0,-height+4)
depth=np.maximum(desired,minimum)*cover+old_depth*(1-cover)
paint=old.copy();paint[:,:,0]=depth/(50*scale);paint[:,:,3]=sample('softness')*cover+old[:,:,3]*(1-cover)
style=np.zeros_like(paint);style[:,:,1]=sample('grass_cover')*cover+.7*(1-cover);style[:,:,2]=sample('wetness')*cover+.5*(1-cover)
clay=np.zeros_like(paint);clay[:,:,0]=sample('clay_weight')*cover;clay[:,:,3]=1 # exclude gravel-only colour branch
def save(name,a):Image.fromarray(np.uint8(np.round(np.clip(a,0,1)*255))).save(L/(name+'.png'))
save('paint',paint);save('style',style);save('clay',clay)
# Sample the actual LiDAR corridor composition (litter/churn/road overlay mix).
src=Path('C:/GrandTour/Art/Export/LidarStudy/Place/TrackDetail');spec=json.loads((src/'manifest.json').read_text())
roads=json.loads(Path('C:/GrandTour/Art/Export/LidarStudy/Place/roads.json').read_text());path=next(r['authoring'] for r in roads if r.get('authoring',{}).get('id')==spec['design_id'])
pts=np.array(path['points_cm'])[:,:2];dist=np.r_[0,np.cumsum(np.linalg.norm(np.diff(pts,axis=0),axis=1))/100]
idx=np.clip(np.searchsorted(dist,station,side='right')-1,0,len(pts)-2);t=np.clip((station-dist[idx])/(dist[idx+1]-dist[idx]),0,1)
v=pts[idx+1]-pts[idx];v=v/np.linalg.norm(v,axis=2)[:,:,None];p=pts[idx]*(1-t[:,:,None])+pts[idx+1]*t[:,:,None];p[:,:,0]-=v[:,:,1]*d;p[:,:,1]+=v[:,:,0]*d
im=np.array(Image.open(src/'T_Composition.png').convert('RGBA'),dtype=float)/255
uv=(p-np.array(spec['origin_cm']))/spec['span_cm']*im.shape[0]-.5;uv=np.clip(uv,0,im.shape[0]-1);lo=uv.astype(int);hi=np.minimum(lo+1,im.shape[0]-1);f=uv-lo
comp=(im[lo[:,:,1],lo[:,:,0]]*(1-f[:,:,0,None])+im[lo[:,:,1],hi[:,:,0]]*f[:,:,0,None])*(1-f[:,:,1,None])+(im[hi[:,:,1],lo[:,:,0]]*(1-f[:,:,0,None])+im[hi[:,:,1],hi[:,:,0]]*f[:,:,0,None])*f[:,:,1,None]
comp[:,:,0]=cover;save('composition',comp)
q=np.uint32(np.round(np.clip(station/1024,0,1)*65535));a=np.uint32(np.round(np.clip((d/100+32)/64,0,1)*65535));route=np.stack([q>>8,q&255,a>>8,a&255],axis=2).astype('uint8');Image.fromarray(route).save(L/'route.png')
zero=round(50/65*65535);Image.new('RGBA',(4,4),(zero>>8,zero&255,0,255)).save(L/'neutral-rest.png')
report={'ok':True,'source':'LiDAR logging track, stations 170–260 m; sampled dry-to-wet-to-dry character','settings':ref['settings'],'kept_authored_rest':True,'depth_floor_adjusted_road_cells':int(np.sum((minimum>desired+.1)&(cover>.01))),'depth_floor_reason':'Retained road geometry requires enough layer thickness beneath the authored troughs','road_softness_range':[float(sample('softness')[cover>.9].min()),float(sample('softness')[cover>.9].max())],'road_wetness_range':[float(sample('wetness')[cover>.9].min()),float(sample('wetness')[cover>.9].max())]}
(L/'transfer.json').write_text(json.dumps(report,indent=2));print(report)
