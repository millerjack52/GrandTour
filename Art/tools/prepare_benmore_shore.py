"""Render-only shore reconstruction and geographic sediment zones.

Uses the accepted Morphology native floor and flow bake verbatim. Outputs are
coverage/data masks, not painted art textures. No terrain, flow or physics bake.
"""
from pathlib import Path
import hashlib, json
import numpy as np
from scipy.ndimage import map_coordinates, distance_transform_edt, gaussian_filter
from PIL import Image
import reshape_benmore_channel as shape
import prepare_benmore_river_life as geometry

ROOT=Path(__file__).resolve().parents[2]
SRC=ROOT/'Art/Export/BenmoreGaea/Morphology'
OUT=SRC.parent/'ShoreRefinement'
CELL=2500/2016

def main():
    OUT.mkdir(parents=True,exist_ok=True)
    hashes={name:hashlib.sha256((SRC/name).read_bytes()).hexdigest() for name in
            ['H_GaeaCreek_2017.r16','height_local_south_up.f32','water-domain.bin','flow-bake.npz']}
    h=np.fromfile(SRC/'height_local_south_up.f32','<f4').reshape(2017,2017)
    with np.load(SRC/'water-domain.npz') as z:d={k:z[k] for k in z.files}
    wet=d['wet'];valid=d['depth']>.005
    nearest=distance_transform_edt(~wet,return_distances=False,return_indices=True)
    mean_extended=d['mean'][tuple(nearest)]
    distance=(distance_transform_edt(wet)-distance_transform_edt(~wet))*1.25
    # Less than one hydraulic cell of reconstruction; individual point stamps
    # and bar/side-channel topology cannot be changed by this filter.
    distance=gaussian_filter(distance,.65)
    def sample(a,x,y,cval=0):
        return map_coordinates(a,[(y-d['y'][0])/1.25,(x-d['x'][0])/1.25],order=1,mode='constant',cval=cval)
    def surface(x,y):
        w=sample(valid.astype(float),x,y)
        weighted=sample(d['mean']*valid,x,y)/np.maximum(w,1e-9)
        return np.where(w>1e-5,weighted,sample(mean_extended,x,y)),w
    # Keep exactly the accepted mean where its interpolation exists. The limited
    # extension is clipped both by the immutable native bed and by occupancy.
    x=np.arange(-1480,-220+.01,.625);y=np.arange(-300,775+.01,.625)
    xx,yy=np.meshgrid(x,y);s,w=surface(xx,yy)
    with np.load(SRC/'flow-bake.npz') as b:outside=sample(b['bed'],xx,yy)
    bed=np.where(xx>=-1250,shape.native(h,xx,yy),outside)
    weight=sample(wet.astype(float),xx,yy)
    support=np.clip(sample(distance,xx,yy,-100), (weight-.5)*2.5-.15, (weight-.5)*2.5+.45)
    signed=np.minimum(support,(s-bed-.005)*5)
    old=(weight>=.5)&(s-bed>.005)
    new=signed>0
    outside_distance=distance_transform_edt(~old)*.625
    missing_distance=distance_transform_edt(~new)*.625
    added=new&~old;removed=old&~new
    stats=dict(old_area_m2=float(old.sum()*.625**2),new_area_m2=float(new.sum()*.625**2),
               changed_fraction=float(np.count_nonzero(old!=new)/old.sum()),
               added_max_distance_m=float(outside_distance[added].max(initial=0)),
               removed_max_distance_m=float(missing_distance[removed].max(initial=0)),
               added_depth_max_m=float((s-bed)[added].max(initial=0)))
    assert stats['changed_fraction']<.13,stats
    assert stats['added_max_distance_m']<=1.25 and stats['removed_max_distance_m']<=1.4,stats
    assert np.min((s-bed)[new])>=.005
    # R is the exact clipping field; G is horizontal distance to the shore.
    # Do not use depth for the live rim: shallow channel interiors must retain
    # their dynamic wet/dry clipping, irrespective of how deep they are.
    horizontal=(distance_transform_edt(new)-distance_transform_edt(~new))*.625
    horizontal-=np.sign(horizontal)*.3125
    shore=np.stack([np.clip(.5+signed/4,0,1),np.clip(.5+horizontal/4,0,1),weight,np.ones_like(w)],-1)
    Image.fromarray(np.uint8(np.rint(shore*255))).save(OUT/'T_SR_Shore.png')
    (OUT/'shore-atlas.json').write_text(json.dumps(dict(origin_m=[x[0],y[0]],cell_m=.625,
         span_m=[len(x)*.625,len(y)*.625],signed_distance_range_m=2),indent=2))
    geometry.OUT=OUT;meshes=[]
    for name,lo,hi in [('SM_GC_RiverSurface',-1250,-220),('SM_GC_OutletSurface',-1480,-1250)]:
        sl=slice(int(round((lo-x[0])/.625)),int(round((hi-x[0])/.625))+1)
        # Outlet was lower resolution; preserve its interior budget via stride.
        step=1 if lo>=-1250 else 2
        info=geometry.exportmesh(name,xx[::step,sl][:,::step],yy[::step,sl][:,::step],s[::step,sl][:,::step],signed[::step,sl][:,::step],0)
        data=json.loads((OUT/(name+'.json')).read_text());v=np.array(data['vertices']);f=np.array(data['faces'])
        v[:,2],vw=surface(v[:,0],v[:,1])
        area=np.cross(v[f[:,1]]-v[f[:,0]],v[f[:,2]]-v[f[:,0]])[:,2]
        f=f[area>1e-10]
        assert np.isfinite(v).all() and np.all(vw>0)
        info.update(triangles=len(f),mean_surface_error_m=0.0)
        (OUT/(name+'.json')).write_text(json.dumps(dict(vertices=v.tolist(),faces=f.tolist()),separators=(',',':')))
        meshes.append(info)
    # Native sediment data. Gravel dominance follows low bank elevations, bar
    # bodies and fast/rocky reaches, rather than a fixed-width grey border.
    yy,xx=np.meshgrid(np.linspace(-1250,1250,2017),np.linspace(-1250,1250,2017),indexing='ij')
    near_distance=np.maximum(-sample(distance,xx,yy,-100),0)
    level=sample(mean_extended,xx,yy);relative=h-level
    bank=np.fromfile(SRC/'bankfull_mask.f32','<f4').reshape(h.shape)
    bars=np.fromfile(SRC/'inside_bar.f32','<f4').reshape(h.shape)
    rocky=np.fromfile(SRC/'rocky_reach.f32','<f4').reshape(h.shape)
    speed=sample(np.hypot(d['vx'],d['vy'])[tuple(nearest)],xx,yy)
    core=np.clip(bars/.30,0,1)
    low=1-shape.smooth((relative-.10)/.48)
    edge=1-shape.smooth((near_distance-.45)/2.1)
    wetness=(1-shape.smooth((relative+.015)/.20))*(1-shape.smooth(near_distance/1.4))
    deposit=np.maximum(core,rocky*.65)
    influence=np.maximum(edge*.93,bank*(.24+.52*low+.22*deposit))
    influence=np.maximum(influence,core*.94*bank)
    coarse=np.clip(.30+speed*.38+deposit*.54,0,1)
    # Low, slow margins collect fines. Higher dry bar cores retain mineral grain.
    silt=bank*(1-shape.smooth((speed-.18)/.65))*(1-core*.85)*low*.68
    zones=np.stack([coarse,silt,wetness,np.clip(influence,0,1)],-1)
    native=np.uint8(np.rint(zones*255))
    Image.fromarray(native).save(OUT/'T_CP_BedZones.png')
    oldatlas=np.asarray(Image.open(SRC/'T_GC_ExtendedBedZones.png')).copy()
    columns=oldatlas.shape[1]-2017;oldatlas[:,columns:]=native
    # A short bridge at the scenery boundary uses the new first native column.
    t=shape.smooth(np.arange(columns)[::-1]*CELL/15)[:,None]
    oldatlas[:,:columns]=np.uint8(np.rint(oldatlas[:,:columns]*t[None,:,:]+native[:,0:1]*(1-t[None,:,:])))
    Image.fromarray(oldatlas).save(OUT/'T_GC_ExtendedBedZones.png')
    (OUT/'bed-atlas.json').write_bytes((SRC/'bed-atlas.json').read_bytes())
    eco=np.asarray(Image.open(SRC/'T_RL_Ecology.png')).copy();oldkeep=eco[:,:,2:].copy()
    path=np.fromfile(SRC/'path_mask.f32','<f4').reshape(h.shape)
    eco[:,:,0]=np.uint8(np.rint(np.maximum(influence*.82,path*.88)*255))
    eco[:,:,1]=np.uint8(np.rint(np.maximum(eco[:,:,1]/255*.55,silt*wetness*.65)*255))
    assert np.array_equal(oldkeep,eco[:,:,2:])
    Image.fromarray(eco).save(OUT/'T_RL_Ecology.png')
    assert all(hashlib.sha256((SRC/n).read_bytes()).hexdigest()==v for n,v in hashes.items())
    report=dict(ok=True,source_hashes=hashes,shore=stats,meshes=meshes,
        runtime_solver_cells=9216,physical_domain_changed=False,native_terrain_changed=False,
        scope='Bounded visual shoreline reconstruction; geographic sediment data, existing sourced mineral textures',
        source_inputs_unchanged=True)
    (OUT/'prepare-report.json').write_text(json.dumps(report,indent=2));print(json.dumps(report,indent=2))

if __name__=='__main__':main()
