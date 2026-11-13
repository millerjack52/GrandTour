"""Validate staged RR1 inputs before they can replace the saved map's inputs."""
import json,struct,sys,hashlib
from pathlib import Path
import numpy as np
from scipy.ndimage import label,binary_erosion
from scipy.spatial import cKDTree

def bank_check(folder,reference,spec,terrain):
 bank=spec['bank_preservation'];polygon=np.array(bank['attachment_polygon_m'])
 origin=np.floor(polygon.min(0)-14);hi=np.ceil(polygon.max(0)+14);step=.5
 xx,yy=np.meshgrid(np.arange(origin[0],hi[0]+.1,step),np.arange(origin[1],hi[1]+.1,step))
 _,k=cKDTree(reference[:,:2]/100).query(np.c_[xx.ravel(),yy.ravel()]);water=reference[k,2].reshape(xx.shape)/100
 fx=(xx+1850)/3700*2016;fy=(yy+1850)/3700*2016;i=fx.astype(int);j=fy.astype(int);a=fx-i;b=fy-j
 h=terrain.astype(float)*327.68/65535
 z=np.where(a>=b,h[j,i]+(h[j,i+1]-h[j,i])*a+(h[j+1,i+1]-h[j,i+1])*b,h[j,i]+(h[j+1,i+1]-h[j+1,i])*a+(h[j+1,i]-h[j,i])*b)
 dry=z-water>.12
 # A single dry diagonal or one raster pixel is not a usable bank connection.
 safe=binary_erosion(dry,np.ones((7,7)));labels,_=label(safe,np.ones((3,3)))
 ids=[];heights=[]
 for p in [bank['bank_probe_m'],bank['mainland_probe_m']]:
  ix,iy=np.rint((np.array(p)-origin)/step).astype(int);ids.append(int(labels[iy,ix]));heights.append(float(z[iy,ix]-water[iy,ix]))
 result=dict(name=bank['name'],connected_with_3m_clearance=ids[0]>0 and ids[0]==ids[1],probe_above_water_m=heights,origin_m=origin.tolist(),step_m=step,shape=list(xx.shape),water_m=water.ravel().tolist(),probes_m=[bank['bank_probe_m'],bank['mainland_probe_m']])
 (folder/'river-bank-validation.json').write_text(json.dumps(result,separators=(',',':')))
 assert result['connected_with_3m_clearance'],('Gravel point detached from mainland',ids,heights)
 assert .12<heights[0]<.75,('Gravel bank is not low and dry',heights[0])
 return {k:v for k,v in result.items() if k not in ['water_m','shape','origin_m']}

def check(folder):
 folder=Path(folder);base=Path(__file__).resolve().parents[2]/'Art/Export/LidarStudy'
 raw=(folder/'River-domain.bin').read_bytes();_,nx,ny,_,_,ox,oy,step=struct.unpack('<5i3f',raw[:32])
 grid=np.frombuffer(raw[32:-1],'<f4').reshape(ny,nx,4);wet=grid[:,:,1]>.015
 labels,n=label(wet,np.ones((3,3)));ys,xs=np.nonzero(wet)
 ref=np.array(json.loads((folder/'authoring-reference.json').read_text())['river_points_cm'])
 distance,nearest=cKDTree(np.c_[ox+(xs+.5)*step,oy+(ys+.5)*step]).query(ref[:,:2])
 station_labels=labels[ys[nearest],xs[nearest]];components=np.unique(station_labels)
 spec=json.loads((folder/'river-repair.json').read_text());widths=[]
 for p in spec['profiles']:
  if 3200<p['station']<3500:widths.append(float(np.sum(np.array(p['bed_m'])<p['water_m']-.015)*.5))
 src=np.fromfile(base/'height.r16','<u2').reshape(2017,2017);dst=np.fromfile(folder/'authoring-height.r16','<u2').reshape(2017,2017)
 changes=(dst.astype(float)-src)*32768/65535
 report=dict(ok=False,version=spec['version'],course_stations=len(ref),course_connected_components=len(components),wet_components=n,
  station_distance_to_wet_cell_max_m=float(distance.max()/100),reach_width_m_p10_p50_p90=np.percentile(widths,[10,50,90]).tolist(),
  cut_max_cm=float(-changes.min()),fill_max_cm=float(changes.max()),changed_vertices=int(np.count_nonzero(changes)),source_sha256=hashlib.sha256((base/'height.r16').read_bytes()).hexdigest(),
  dressing_candidates=len(spec['items']),note='2m domain connectivity; isolated off-course pools allowed. Dry centreline at preserved corner bar is allowed when the water connects around it.')
 (folder/'river-validation.json').write_text(json.dumps(report,indent=2))
 assert len(components)==1,('Disconnected course',components.tolist())
 assert distance.max()<600,('Course too far from water',distance.max())
 assert changes.max()<.01,'Repair unexpectedly raised terrain'
 assert -changes.min()<650,'Excessive excavation'
 report['bank']=bank_check(folder,ref,spec,dst)
 source=np.array(json.loads((folder/'authoring-reference.json').read_text())['source_river_points_cm'])
 assert np.array_equal(source[:,2],ref[:,2]),'Source water elevations changed'
 from lidar_river_repair import bank_definitions
 active=np.zeros(len(ref),bool)
 for bank in bank_definitions():
  lo,hi=bank['guide_station_range_m'];active[lo:hi+1]=True
 assert np.array_equal(source[~active],ref[~active]),'River guide moved outside the bank correction'
 report['local_guide_shift_max_m']=float(np.linalg.norm(source[:,:2]-ref[:,:2],axis=1).max()/100)
 assert report['local_guide_shift_max_m']<=8.001
 probes=[]
 for station in range(0,len(ref),40):
  j,i=int(ys[nearest[station]]),int(xs[nearest[station]])
  probes.append(dict(station_m=station,x_cm=float(ox+(i+.5)*step),y_cm=float(oy+(j+.5)*step),water_cm=float(grid[j,i,0]),depth_cm=float(grid[j,i,1]*100)))
 report['ok']=True;(folder/'river-validation.json').write_text(json.dumps(dict(report,probes=probes),indent=2));print(json.dumps(report,indent=2));return report

if __name__=='__main__':check(sys.argv[1])
