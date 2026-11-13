"""Terrain-wide ecological density masks, with road and lake exclusions."""
from pathlib import Path
import numpy as np,json
from PIL import Image
ROOT=Path(__file__).resolve().parents[2];ROAD=ROOT/'Art/Export/BenmoreRoads';OUT=ROOT/'Art/Export/BenmoreVegetation';OUT.mkdir(exist_ok=True)
n=2017;step=2500/(n-1)
h=np.fromfile(ROAD/'height_local_south_up.f32',dtype='<f4').reshape(n,n)
road=np.asarray(Image.open(ROAD/'T_Benmore_RoadMask.png')).astype(float)/255
y,x=np.mgrid[0:n,0:n]*step-1250
dy,dx=np.gradient(h,step);slope=np.degrees(np.arctan(np.hypot(dx,dy)))
rng=np.random.default_rng(611)
def noise(size):
    a=Image.fromarray((rng.random((size,size))*255).astype('uint8'))
    return np.asarray(a.resize((n,n),Image.Resampling.BICUBIC)).astype(float)/255
patch=.65*noise(37)+.35*noise(111)
moist= .65*noise(22)+.35*np.clip(1-h/160,0,1)
land=np.clip((h-.65)/1.5,0,1)
clear=(1-np.clip(road[:,:,1]*1.5,0,1))*land
gentle=np.clip((42-slope)/28,0,1)
low=clear*gentle*(.68+.32*patch)
tussock=clear*np.clip((48-slope)/28,0,1)*(.25+.75*patch)
tall=clear*gentle*np.clip((moist-.3)*1.8,0,1)*(.3+.7*patch)
m=np.stack([low,tussock,tall,moist],axis=-1)
Image.fromarray(np.uint8(np.clip(m,0,1)*255)).save(OUT/'T_Benmore_VegetationMask.png')
Image.fromarray(np.uint8(np.clip(m[::-1,:,:3],0,1)*255)).resize((1100,1100)).save(OUT/'Coverage_Masks.png')
eligible=(h>2)&(road[:,:,1]<.01)&(slope<40)
assert ((m[:,:,:3].max(axis=2)>0)[eligible]).all()
assert m[:,:,:3][road[:,:,0]>.1].max()==0
assert m[:,:,:3][h<.65].max()==0
report={'ok':True,'terrain_area_km2':6.25,'selected_area_km2':5.38496,'orientation':'South-up, matching UE road masks','road_and_water_exclusion_verified':True,'eligible_land_coverage_percent':float((m[:,:,:3].max(axis=2)>0)[eligible].mean()*100),'mean_weights':[float(m[:,:,i].mean()) for i in range(3)],'sparse_or_bare':'Rock faces, steep banks, road corridors and lake-height ground','seed':611}
(OUT/'coverage-report.json').write_text(json.dumps(report,indent=2));print(json.dumps(report,indent=2))
