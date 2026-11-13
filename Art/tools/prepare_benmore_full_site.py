"""Prepare the whole screenshot-selected Benmore site, at its real-world scale."""
from pathlib import Path
import json, math, shutil
import numpy as np
import rasterio as rio
from rasterio.warp import reproject,Resampling
from rasterio.transform import from_origin
from rasterio.windows import from_bounds
from pyproj import Transformer
from PIL import Image,ImageDraw,ImageFont

ROOT=Path(__file__).resolve().parents[2]
REGION=ROOT/'Art/Export/MackenzieRealTerrain/region-01'
OUT=ROOT/'Art/Export/MackenzieRealTerrain/BenmoreFullSite';OUT.mkdir(exist_ok=True)
# Screenshot matched to Region_Overview.png: x1132.69..1369.23,
# y425..678.85. These metre-rounded bounds encompass that entire selection.
SITE=[1382180,5079947,1384420,5082351]
CX,CY=1383300,5081149
BOUNDS=[CX-1250,CY-1250,CX+1250,CY+1250]
LAKE=360.531005859375
FONT=lambda n,b=False:ImageFont.truetype('C:/Windows/Fonts/'+('segoeuib.ttf' if b else 'segoeui.ttf'),n)
def sample(src,n,bounds):
    l,b,r,t=bounds;dx=(r-l)/(n-1);dy=(t-b)/(n-1)
    tr=from_origin(l-dx/2,t+dy/2,dx,dy)
    a=np.full((n,n),-9999,dtype='float32')
    reproject(rio.band(src,1),a,src_transform=src.transform,src_crs=src.crs,
        dst_transform=tr,dst_crs=src.crs,src_nodata=-9999,dst_nodata=-9999,
        resampling=Resampling.bilinear,num_threads=2)
    assert np.isfinite(a).all() and (a!=-9999).all()
    return a,tr
def save_tif(name,a,tr):
    with rio.open(OUT/name,'w',driver='GTiff',width=a.shape[1],height=a.shape[0],count=1,
        dtype='float32',crs='EPSG:2193',transform=tr,nodata=-9999,compress='deflate',predictor=3) as dst:dst.write(a,1)
with rio.open(REGION/'Region_DEM_1m_NZTM.tif') as src:
    for name,bounds in [('Selected_Area_1m_NZTM.tif',SITE),('Gaea_Border_1m_NZTM.tif',BOUNDS),
                        ('Surroundings_4km_1m_NZTM.tif',[CX-2000,CY-2000,CX+2000,CY+2000])]:
        win=from_bounds(*bounds,src.transform).round_offsets().round_lengths()
        a=src.read(1,window=win);assert np.isfinite(a).all() and (a!=-9999).all()
        save_tif(name,a,src.window_transform(win))
    h,tr=sample(src,2048,BOUNDS)
    ue,_=sample(src,2017,BOUNDS)
    small,_=sample(src,513,BOUNDS)
    small.astype('<f4').tofile(OUT/'preview_height_513.f32')
    save_tif('Gaea_Grid_2048_NZTM.tif',h,tr)
base=math.floor(float(h.min())/128)*128
span=2**math.ceil(math.log2(float(h.max())-base+32))
q=np.rint((h-base)/span*65535).astype('uint16')
Image.fromarray(q).save(OUT/'H_Benmore_FullSite_2048.png')
assert (OUT/'H_Benmore_FullSite_2048.png').read_bytes()[24:26]==bytes([16,0])
recovered=np.asarray(Image.open(OUT/'H_Benmore_FullSite_2048.png')).astype(float)/65535*span+base
assert np.abs(recovered-h).max()<span/65535/2+.0001
# UE keeps X=east and Y=north, so rows must be flipped from GIS north-up.
# Local lake elevation is zero. ZScale=200 => one encoded unit is 1/64 metre.
encoded=np.rint((ue[::-1]-LAKE)*64+32768)
assert encoded.min()>0 and encoded.max()<65535
encoded=encoded.astype('uint16')
Image.fromarray(encoded).save(OUT/'H_Benmore_UE_2017.png')
encoded.astype('<u2').tofile(OUT/'H_Benmore_UE_2017.r16')
rg=np.zeros((2017,2017,4),dtype='uint8');rg[:,:,0]=encoded>>8;rg[:,:,1]=encoded&255;rg[:,:,3]=255
Image.fromarray(rg).save(OUT/'T_Benmore_HeightRG_2017.png')
# Masks share the Gaea input grid, never the flipped UE grid.
xx=np.linspace(BOUNDS[0],BOUNDS[2],2048);yy=np.linspace(BOUNDS[3],BOUNDS[1],2048)
X,Y=np.meshgrid(xx,yy)
area=(X>=SITE[0])&(X<=SITE[2])&(Y>=SITE[1])&(Y<=SITE[3])
gy,gx=np.gradient(h,2500/2047);slope=np.degrees(np.arctan(np.hypot(gx,gy)))
water=h<361
for name,m in [('M_Selected_Footprint',area),('M_Lake_Approx',water),('M_Land_Approx',~water)]:
    Image.fromarray((m*255).astype('uint8')).save(OUT/(name+'_2048.png'))
Image.fromarray(np.rint(np.clip(slope/45,0,1)*255).astype('uint8')).save(OUT/'M_Slope_0to45deg_2048.png')
shade=np.clip((1-.7*gx+.7*gy)/np.sqrt(gx*gx+gy*gy+1),.1,1.45)
t=np.clip((h-360)/400,0,1)
rgb=(np.array([133,153,117])[None,None,:]*(1-t[:,:,None])+np.array([177,155,121])[None,None,:]*t[:,:,None])*(.45+.5*shade[:,:,None])
rgb=np.clip(rgb,0,255).astype('uint8');rgb[water]=[52,100,116]
Image.fromarray(rgb).save(OUT/'Terrain_Colour_Preview_2048.png')
im=Image.fromarray(rgb).resize((1200,1200),Image.Resampling.LANCZOS)
sheet=Image.new('RGB',(1640,1370),'#172123');sheet.paste(im,(40,110));d=ImageDraw.Draw(sheet)
d.text((40,24),'BENMORE / THE FULL SELECTED AREA',font=FONT(32,True),fill='#f2efdf')
d.text((40,70),'2.24 x 2.40 km selected footprint / real elevations / north up',font=FONT(21),fill='#becac4')
def pixel(e,n):return (40+(e-BOUNDS[0])/2500*1200,110+(BOUNDS[3]-n)/2500*1200)
d.rectangle((*pixel(SITE[0],SITE[3]),*pixel(SITE[2],SITE[1])),outline='#f2ce7b',width=4)
def label(e,n,text):
    p=pixel(e,n);box=d.textbbox(p,text,font=FONT(21,True))
    d.rounded_rectangle((box[0]-7,box[1]-5,box[2]+7,box[3]+5),4,fill='#172123')
    d.text(p,text,font=FONT(21,True),fill='#f0edde')
label(1382700,5082180,'Northern ridge')
label(1382480,5081060,'Open terrace')
label(1382620,5080180,'Southern hills')
label(1382100,5080700,'Lake edge')
x=1280
for y,title,lines in [(135,'FULL FOOTPRINT',['The whole area you selected.','Yellow = selected boundary.','A small border completes the','2.5 km square Gaea input.']),
                     (345,'TERRAIN STRUCTURE',['Northern ridge and gullies','Open ground through the middle','Southern hills and spurs','Shoreline along the west']),
                     (555,'ROAD PLANNING',['Start with the open terrace.','Follow contours into the hills.','Keep steep faces as scenery.','Crossing locations need review.']),
                     (765,'GAEA INPUT',[f'Width: 2500 m',f'Height: {span} m','Resolution: 2048','File node / Raw scale']),
                     (975,'DATA',['No vertical exaggeration.','Lake mask is approximate.','DEM is not lake-bed depth.','Source: LINZ / CC BY 4.0'])]:
    d.text((x,y),title,font=FONT(23,True),fill='#f2ce7b')
    for k,line in enumerate(lines):d.text((x,y+43+k*32),line,font=FONT(18),fill='#c8d2cb')
d.line((72,1278,312,1278),fill='white',width=4);d.text((72,1245),'500 m',font=FONT(19),fill='white')
d.text((40,1330),'Terrain preparation and review / roads and gameplay integration are separate from the imported elevations.',font=FONT(19),fill='#afc0b9')
sheet.save(OUT/'Full_Site_Plan.png')
region=Image.open(REGION/'Region_Overview.png');rd=ImageDraw.Draw(region)
info=json.loads((REGION/'inspection.json').read_text());l,b,r,t=info['bounds_nztm'];scale=(region.width-80)/(r-l)
p=(40+(SITE[0]-l)*scale,100+(t-SITE[3])*scale,40+(SITE[2]-l)*scale,100+(t-SITE[1])*scale)
rd.rectangle(p,outline='#f2ce7b',width=5);rd.text((p[0]-20,p[1]-36),'FULL SITE',font=FONT(24,True),fill='#f2ce7b')
region.save(OUT/'Region_Location.png')
anchors=[]
for iy in [0,128,504,1008,1512,1888,2016]:
    for ix in [0,128,504,1008,1512,1888,2016]:
        anchors.append({'pixel':[ix,iy],'local_xyz_cm':[-125000+ix*250000/2016,-125000+iy*250000/2016,(int(encoded[iy,ix])-32768)/64*100]})
geo=Transformer.from_crs(2193,4326,always_xy=True)
manifest={'ok':True,'selection':'Whole screenshot-selected eastern shore area below C; supersedes the proposed 1 km D square',
    'selected_bounds_nztm':SITE,'selected_size_m':[SITE[2]-SITE[0],SITE[3]-SITE[1]],'selected_area_km2':(SITE[2]-SITE[0])*(SITE[3]-SITE[1])/1e6,
    'square_bounds_nztm':BOUNDS,'centre_nztm':[CX,CY],'centre_lon_lat':list(geo.transform(CX,CY)),
    'gaea':{'width_m':2500,'height_m':span,'resolution':2048,'elevation_offset_nzvd2016_m':base,'orientation':'North-up; row zero is northern edge','decode':'NZVD2016 elevation = pixel / 65535 * height_m + elevation_offset_nzvd2016_m'},
    'unreal':{'resolution':2017,'xy_scale_cm':250000/2016,'z_scale':200,'location_cm':[-125000,-125000,0],
        'height_zero_nzvd2016_m':LAKE,'orientation':'South-up image: row zero is minimum northing, UE Y=-1250m. X east and Y north.',
        'decode_local_m':'(pixel-32768)/64','purpose':'Terrain review; deterministic gameplay height queries still require integration'},
    'square_elevation_m':[float(h.min()),float(h.max())], 'selected_elevation_m':[float(h[area].min()),float(h[area].max())],
    'selected_land_fraction_approx':float(np.mean(~water[area])),
    'gaea_max_encoding_error_m':float(np.abs(recovered-h).max()),'missing_pixels':0,
    'unreal_validation_anchors':anchors}
(OUT/'terrain-manifest.json').write_text(json.dumps(manifest,indent=2))
shutil.copy2(REGION/'LINZ_source_and_license.txt',OUT/'LINZ_source_and_license.txt')
print(json.dumps({k:v for k,v in manifest.items() if k not in ['unreal_validation_anchors']},indent=2))
