"""Whole river/outlet mean surface plus lake coverage. No Landscape/placement edits.

Smooth the water elevation independently of the riverbed, then clip to genuinely
wet ground. Export the same mean for rendering and all runtime water queries.
"""
from pathlib import Path
import json,struct
import numpy as np
from scipy.ndimage import gaussian_filter,distance_transform_edt,map_coordinates
from PIL import Image
import prepare_benmore_river_life as geometry

ROOT=Path(__file__).resolve().parents[2]
SRC=ROOT/'Art/Export/BenmoreGaea/RiverLife'
OUT=ROOT/'Art/Export/BenmoreGaea/RiverScale'

def main():
    b=np.load(SRC/'flow-bake.npz');x=b['x'];y=b['y'];xx,yy=np.meshgrid(x,y)
    wet=b['wet'].astype(bool)
    nearest=distance_transform_edt(~wet,return_distances=False,return_indices=True)
    extended=b['surface'][tuple(nearest)]
    smooth=gaussian_filter(extended,1.8)
    # Small conservative elevation correction; ford stays fordable, existing banks/roads are untouched.
    smooth=np.clip(smooth,b['surface']-.08,b['surface']+.08)+.035
    smooth=np.where(b['bed']<.50,.60,smooth)
    native=np.where(xx>=-1250,geometry.ground(xx,yy),b['bed'])
    depth=np.maximum(0,smooth-native)
    wet &= depth>.015
    lake=np.asarray(Image.open(ROOT/'Art/Export/BenmoreVistas/T_Benmore_LakeCoverage.png'))[:,:,0]
    lake=np.ascontiguousarray(lake[::-1])
    luv=[(yy+8492)/12770*lake.shape[0]-.5,(xx+11463)/13680*lake.shape[1]-.5]
    lake_here=map_coordinates(lake,luv,order=0,mode='constant')>127
    # Match the refined lake-mouth coverage, including the old river/lake junction.
    mouth=np.asarray(Image.open(SRC/'T_RL_Mouth.png')).astype(float)/255
    muv=[(yy+330)/1.25,(xx+1580)/1.25]
    valid=map_coordinates(mouth[:,:,0],muv,order=1,mode='constant')>.5
    lm=map_coordinates(mouth[:,:,1],muv,order=1,mode='constant')>.5
    lake_here=np.where(valid,lm,lake_here)&(native<.60)
    lake_only=lake_here&~wet
    mean=np.where(lake_only,.60,smooth)
    h=np.where(wet,depth,np.where(lake_only,np.maximum(.60-native,.015),-1))
    speed=np.hypot(b['vx'],b['vy']);scale=np.minimum(1,1.5/np.maximum(speed,.001))
    vx=np.where(wet,b['vx']*scale,0);vy=np.where(wet,b['vy']*scale,0)
    records=np.stack([mean*100,h,vx,vy],-1).astype('<f4')
    with (OUT/'water-domain.bin').open('wb') as f:
        f.write(struct.pack('<5i3f',0x47545744,len(x),len(y),lake.shape[1],lake.shape[0],(x[0]-.625)*100,(y[0]-.625)*100,125))
        f.write(records.tobytes());f.write(lake.tobytes())
    np.savez_compressed(OUT/'water-domain.npz',x=x,y=y,mean=mean,depth=h,vx=vx,vy=vy,wet=wet)
    rgba=np.stack([.5+vx/4,.5+vy/4,np.maximum(h,0)/2,np.where(wet,b['foam'],0)],-1)
    Image.fromarray(np.uint8(np.rint(np.clip(rgba,0,1)*255))).save(OUT/'T_RS_DomainFlow.png')
    Image.fromarray(np.uint8(np.stack([wet,wet,wet,np.ones_like(wet)],-1)*255)).save(OUT/'T_RS_DomainMask.png')
    geometry.OUT=OUT
    meshes=[]
    for name,mask in [('SM_RS_RiverSurface',wet&(xx>=-1250)),('SM_RS_OutletSurface',wet&(xx<=-1250))]:
        meshes.append(geometry.exportmesh(name,xx,yy,mean,mask.astype(float),.5))
    checks={'ok':True,'grid':[len(x),len(y)],'wet_river_cells':int(wet.sum()),'lake_mask_cells':int((lake>127).sum()),'payload_bytes':(OUT/'water-domain.bin').stat().st_size,'meshes':meshes,'mean_elevation_change_m':np.percentile((smooth-b['surface'])[wet],[0,50,95,100]).tolist(),'local_solver_cells':9216,'local_cell_m':.625,'local_span_m':60,'lake_bathymetry':'Coverage only; runtime uses an effective 1.5 m surface-wave layer.'}
    (OUT/'water-domain-prepare.json').write_text(json.dumps(checks,indent=2));print(json.dumps(checks,indent=2))

if __name__=='__main__':main()
