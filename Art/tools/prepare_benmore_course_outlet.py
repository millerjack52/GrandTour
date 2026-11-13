"""Match the existing outside-Landscape scenery apron to the revised solve.

No native terrain is replaced. Pixel masks describe geographic coverage, not art.
"""
import json
import numpy as np
from PIL import Image
from scipy.ndimage import map_coordinates,distance_transform_edt
from scipy.interpolate import LinearNDInterpolator
import prepare_benmore_river_life as geometry

def prepare(out):
    bounds=(-1580,-330,-1250,800);step=1.25
    b=np.load(out/'flow-bake.npz')
    x=np.arange(bounds[0],bounds[2]+step/2,step);y=np.arange(bounds[1],bounds[3]+step/2,step)
    xx,yy=np.meshgrid(x,y);uv=[(yy-b['y'][0])/step,(xx-b['x'][0])/step]
    wet=map_coordinates(b['wet'].astype(float),uv,order=1,mode='constant')>.4
    bed=map_coordinates(b['bed'],uv,order=1,mode='nearest')
    old=np.asarray(Image.open(geometry.ROOT/'Art/Export/BenmoreGaea/RiverLife/T_RL_Mouth.png'))[:,:,0]>127
    footprint=(distance_transform_edt(~wet)*step<32)|old
    v=np.fromfile(geometry.ROOT/'Art/Export/BenmoreHills/SM_Benmore_Hills_West.f32','<f4').reshape(-1,3)
    coarse=LinearNDInterpolator(v[:,:2],v[:,2])(xx,yy);coarse=np.where(np.isfinite(coarse),coarse,bed)
    edge=distance_transform_edt(np.pad(footprint,1))[1:-1,1:-1]*step
    blend=np.clip((edge-step)/12,0,1);blend=blend*blend*(3-2*blend)
    blend=np.maximum(blend,(xx>-1253.75).astype(float));blend=np.maximum(blend,wet.astype(float))
    z=coarse*(1-blend)+(bed-.012)*blend
    geometry.OUT=out
    mesh=geometry.exportmesh('SM_GC_MouthBed',xx,yy,z,footprint.astype(float),.5)
    assert abs(z[wet]-bed[wet]+.012).max()<1e-8
    assert xx.max()<=-1250
    rgba=np.stack([footprint,bed<.60,wet,np.ones_like(wet)],-1)
    Image.fromarray(np.uint8(np.rint(rgba*255))).save(out/'T_RL_Mouth.png')
    paths=np.load(out/'network-paths.npz')['0'];p=paths[(paths[:,0]<-1252)&(paths[:,0]>-1340)][::12,:2]
    samples=map_coordinates(z,[(p[:,1]+330)/step,(p[:,0]+1580)/step],order=1,mode='nearest')
    report=dict(ok=True,**mesh,bounds_m=bounds,spacing_m=step,scenery_only=True,native_landscape_replaced=False,
        bed_source='Revised hydraulic bed, continuously joined to native Landscape edge',max_wet_bed_error_m=float(abs(z[wet]-bed[wet]+.012).max()),
        support_points_m=np.c_[p,samples].tolist())
    (out/'outlet-assets.json').write_text(json.dumps(report,indent=2))
    return report
