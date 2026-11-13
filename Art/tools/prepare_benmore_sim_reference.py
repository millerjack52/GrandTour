"""Prepare bounded river reference windows; no runtime simulation is claimed.

The native bed and offline mean surface/current share coordinates. These files
are inputs for adapting GTWaterField, not a replacement water solver.
"""
from pathlib import Path
import json
import numpy as np
from scipy.ndimage import map_coordinates

ROOT=Path(__file__).resolve().parents[2]
SOURCE=ROOT/'Art/Export/BenmoreGaea/RiverLife'
OUT=ROOT/'Art/Export/BenmoreGaea/RiverScale'

def main():
    OUT.mkdir(parents=True,exist_ok=True)
    d=np.load(SOURCE/'flow-bake.npz');dx=float(d['x'][1]-d['x'][0])
    def sample(key,xy):
        a=d[key]
        if a.dtype==np.bool_:a=a.astype('f4')
        return map_coordinates(a,[(xy[...,1]-d['y'][0])/dx,(xy[...,0]-d['x'][0])/dx],order=1,mode='nearest')
    height=np.fromfile(SOURCE/'height_local_south_up.f32',dtype='<f4').reshape(2017,2017)
    def bed(xy):
        uv=(xy+1250)/2500*2016
        assert np.all((uv>=0)&(uv<2016)), 'Window extends outside native Landscape'
        i=uv[...,0].astype(int);j=uv[...,1].astype(int);s=uv[...,0]-i;t=uv[...,1]-j
        q=height[j,i];r=height[j,i+1];v=height[j+1,i];w=height[j+1,i+1]
        return np.where(s>=t,q+(r-q)*s+(w-r)*t,q+(w-v)*s+(v-q)*t)
    report={'ok':False,'runtime_installed':False,'source_spacing_m':dx,'cell_budget':16384,'windows':[]}
    for crossing in json.loads((SOURCE/'assets.json').read_text())['crossings']:
        cell=.375;nx,ny=128,64
        ax=np.array(crossing['flow_direction']);ay=np.array([-ax[1],ax[0]]);centre=np.array(crossing['center_m'][:2])
        origin=centre-ax*nx*cell/2-ay*ny*cell/2
        xx,yy=np.meshgrid((np.arange(nx)+.5)*cell,(np.arange(ny)+.5)*cell)
        xy=origin+xx[...,None]*ax+yy[...,None]*ay
        native=bed(xy);wet_weight=sample('wet',xy);coverage=wet_weight>.5
        coords=[(xy[...,1]-d['y'][0])/dx,(xy[...,0]-d['x'][0])/dx]
        # Interpolate only wet reference elevations, not the exposed dry-bank bed.
        surface=map_coordinates(d['surface']*d['wet'],coords,order=1,mode='nearest')/np.maximum(wet_weight,1.e-6)
        depth=np.where(coverage,np.maximum(surface-native,0),0)
        # Dry shoreline cells carry their native bed, never a low sentinel height.
        surface=native+depth
        vx=np.where(depth>.01,sample('vx',xy),0);vy=np.where(depth>.01,sample('vy',xy),0)
        vel_x=vx*ax[0]+vy*ax[1];vel_y=vx*ay[0]+vy*ay[1]
        assert np.all(np.isfinite(surface)) and np.all(depth>=0)
        np.savez_compressed(OUT/('reference_'+crossing['name']+'.npz'),origin_m=origin,axis_x=ax,axis_y=ay,cell_m=cell,bed_m=native.astype('f4'),surface_m=surface.astype('f4'),depth_m=depth.astype('f4'),velocity_x_mps=vel_x.astype('f4'),velocity_y_mps=vel_y.astype('f4'))
        s=np.linspace(-18,18,145);line=centre+s[:,None]*ax
        mean_surface=sample('surface',line)
        level=float(crossing['surface_z_m']);flat_error=level-mean_surface
        report['windows'].append({'name':crossing['name'],'cells':[nx,ny],'cell_m':cell,'span_m':[nx*cell,ny*cell],'wet_cells':int((depth>.01).sum()),'drop_over_36m_m':float(mean_surface[0]-mean_surface[-1]),'single_level_surface_error_m':{'min':float(flat_error.min()),'max':float(flat_error.max())},'array_units':'metres and metres/second; rotated axes','resampling_warning':'The 1.25 m mean-flow bake is resampled onto the 0.375 m interaction grid. This does not add hydraulic detail. Bed uses native Landscape triangles.'})
    report['ok']=True
    (OUT/'reference-report.json').write_text(json.dumps(report,indent=2))
    print(json.dumps(report,indent=2))

if __name__=='__main__':main()
