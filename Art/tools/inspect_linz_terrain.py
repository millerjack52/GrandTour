"""Inspect a LINZ DEM download and produce a georeferenced regional mosaic."""
from pathlib import Path
import json, shutil, sys
import numpy as np
import rasterio as rio
from rasterio.merge import merge
from rasterio.enums import Resampling
from pyproj import Transformer
from PIL import Image, ImageDraw, ImageFont

SOURCE=Path(r'C:\Users\mille\Downloads\lds-new-zealand-lidar-1m-dem-GTiff')
ROOT=Path(__file__).resolve().parents[2]
OUT=ROOT/'Art/Export/MackenzieRealTerrain/region-01'
OUT.mkdir(parents=True,exist_ok=True)
paths=sorted(SOURCE.glob('*.tif'))
sources=[rio.open(p) for p in paths]
report={'ok':False,'source_folder':str(SOURCE),'tiles':[]}
for src in sources:
    assert src.crs.to_epsg()==2193 and src.count==1 and src.res==(1.,1.)
    valid=0; missing=0; low=float('inf'); high=-float('inf')
    for _,win in src.block_windows(1):
        a=src.read(1,window=win,masked=True)
        good=a.compressed(); good=good[np.isfinite(good)]
        valid+=len(good);missing+=a.size-len(good)
        if len(good): low=min(low,float(good.min()));high=max(high,float(good.max()))
    report['tiles'].append({'name':Path(src.name).name,'width':src.width,'height':src.height,
        'bounds_nztm':list(src.bounds),'valid_pixels':valid,'missing_pixels':missing,'elevation_m':[low,high]})
    print('Inspected',Path(src.name).name,flush=True)

left=min(s.bounds.left for s in sources);right=max(s.bounds.right for s in sources)
bottom=min(s.bounds.bottom for s in sources);top=max(s.bounds.top for s in sources)
report.update(bounds_nztm=[left,bottom,right,top],size_m=[right-left,top-bottom],crs='EPSG:2193',vertical_datum='NZVD2016',pixel_size_m=1)
convert=Transformer.from_crs(2193,4326,always_xy=True)
report['centre_lon_lat']=list(convert.transform((left+right)/2,(bottom+top)/2))
report['corners_lon_lat']=[list(convert.transform(x,y)) for x,y in [(left,bottom),(right,top)]]
report['valid_pixels']=sum(t['valid_pixels'] for t in report['tiles'])
report['missing_pixels']=sum(t['missing_pixels'] for t in report['tiles'])
report['elevation_m']=[min(t['elevation_m'][0] for t in report['tiles']),max(t['elevation_m'][1] for t in report['tiles'])]
if '--preview-only' not in sys.argv:
    merge(sources,res=1,nodata=-9999,dtype='float32',dst_path=OUT/'Region_DEM_1m_NZTM.tif',
          mem_limit=128,dst_kwds={'compress':'deflate','predictor':3,'tiled':True,'BIGTIFF':'IF_SAFER'})
print('Saved native-resolution mosaic',flush=True)
with rio.open(OUT/'Region_DEM_1m_NZTM.tif') as mosaic:
    # Resample the merged raster in one grid; independent tile resampling can
    # create artificial missing border pixels where tile dimensions are odd.
    assert mosaic.width==round(right-left) and mosaic.height==round(top-bottom)
    shape=(round(mosaic.height/5),round(mosaic.width/5))
    z=mosaic.read(1,out_shape=shape,resampling=Resampling.average)
    tr=mosaic.transform*mosaic.transform.scale(mosaic.width/shape[1],mosaic.height/shape[0])
    missing=0; worst=0
    for src in sources:
        for row in [0,src.height//2,src.height-1]:
            for col in [0,src.width//2,src.width-1]:
                x,y=src.xy(row,col)
                original=float(next(src.sample([(x,y)]))[0])
                copied=float(next(mosaic.sample([(x,y)]))[0])
                worst=max(worst,abs(original-copied))
    for _,win in mosaic.block_windows(1):
        block=mosaic.read(1,window=win)
        missing+=int(np.sum((block==-9999)|~np.isfinite(block)))
    assert worst==0 and missing==0
    report['mosaic_validation']={'exact_sample_checks':36,'max_error_m':worst,'missing_pixels':missing}
valid=(z!=-9999)&np.isfinite(z)
with rio.open(OUT/'Region_Overview_5m_NZTM.tif','w',driver='GTiff',width=z.shape[1],height=z.shape[0],count=1,dtype='float32',crs='EPSG:2193',transform=tr,nodata=-9999,compress='deflate',predictor=3) as dst: dst.write(z,1)
# Hillshade is strictly a preview; the GeoTIFF stores unmodified metre elevations.
safe=np.where(valid,z,np.nanmedian(z[valid]))
gy,gx=np.gradient(safe,5)
normal=np.sqrt(gx*gx+gy*gy+1)
shade=np.clip((1-.7*gx+.7*gy)/normal,.1,1.45)
stops=np.array([report['elevation_m'][0],500,700,1000,1400,1800,2400])
colors=np.array([[95,123,113],[160,163,123],[177,159,117],[155,134,112],[143,137,128],[173,177,173],[226,234,232]])
rgb=np.stack([np.interp(safe,stops,colors[:,c]) for c in range(3)],axis=2)*(.45+.5*shade[:,:,None])
rgb=np.clip(rgb,0,255).astype('uint8');rgb[~valid]=[55,74,86]
water=valid&(z<361)
rgb[water]=[57,99,113]
im=Image.fromarray(rgb);im.thumbnail((1500,1350))
canvas=Image.new('RGB',(im.width+80,im.height+145),'#172123');canvas.paste(im,(40,100))
d=ImageDraw.Draw(canvas)
font=lambda n:ImageFont.truetype('C:/Windows/Fonts/segoeui.ttf',n)
d.text((40,20),'LINZ / DOWNLOADED TERRAIN',font=font(30),fill='#f2f0df')
d.text((40,62),f'{(right-left)/1000:.2f} x {(top-bottom)/1000:.2f} km  |  1 m source data  |  north up',font=font(20),fill='#bac8c3')
scale=im.width/(right-left)
for e in range(int(np.ceil(left/2000)*2000),int(right),2000):
    px=40+(e-left)*scale
    d.line((px,100,px,100+im.height),fill='#5d6961',width=1)
    d.text((px+5,105),str(e),font=font(13),fill='white')
for n in range(int(np.ceil(bottom/2000)*2000),int(top),2000):
    py=100+(top-n)*scale
    d.line((40,py,40+im.width,py),fill='#5d6961',width=1)
    d.text((45,py+4),str(n),font=font(13),fill='white')
d.text((40,im.height+110),'LINZ Data Service / CC BY 4.0   |   NZTM grid   |   blue: approximate lake area below 361 m',font=font(16),fill='#bac8c3')
canvas.save(OUT/'Region_Overview.png')
# List viable 1 km terrain windows. These are geometry candidates, not verified routes.
slope=np.degrees(np.arctan(np.hypot(gx,gy)))
candidates=[]
for iy in range(0,z.shape[0]-200,50):
    for ix in range(0,z.shape[1]-200,50):
        v=valid[iy:iy+200,ix:ix+200]
        if not v.all():continue
        p=z[iy:iy+200,ix:ix+200];s=slope[iy:iy+200,ix:ix+200]
        dry=float(np.mean(p>=361))
        if dry<.98:continue
        relief=float(np.percentile(p,95)-np.percentile(p,5));gentle=float(np.mean(s<10));moderate=float(np.mean((s>=10)&(s<25)))
        if not (20<relief<125 and gentle>.6):continue
        score=gentle+.4*moderate-abs(relief-65)/200
        x,y=tr*(ix+100,iy+100)
        candidates.append({'centre_nztm':[x,y],'centre_lon_lat':list(convert.transform(x,y)),
            'relief_p05_p95_m':relief,'gentle_fraction':gentle,'moderate_fraction':moderate,'dry_fraction_approx':dry,'score':score})
candidates.sort(key=lambda r:r['score'],reverse=True)
chosen=[]
for row in candidates:
    if all(np.linalg.norm(np.array(row['centre_nztm'])-r['centre_nztm'])>1800 for r in chosen):chosen.append(row)
    if len(chosen)==8:break
report['terrain_candidates']=chosen
shutil.copy2(SOURCE/'new-zealand-lidar-1m-dem.txt',OUT/'LINZ_source_and_license.txt')
report['ok']=True
(OUT/'inspection.json').write_text(json.dumps(report,indent=2))
for src in sources:src.close()
print(json.dumps({k:v for k,v in report.items() if k!='tiles'},indent=2))
