"""Create three reversible 1 km Gaea terrain studies from the verified LINZ mosaic."""
from pathlib import Path
import json, math, sys
import numpy as np
import rasterio as rio
from rasterio.warp import reproject, Resampling
from rasterio.transform import from_origin
from PIL import Image,ImageDraw,ImageFont

ROOT=Path(__file__).resolve().parents[2]
OUT=ROOT/'Art/Export/MackenzieRealTerrain/region-01'
info=json.loads((OUT/'inspection.json').read_text());assert info['ok']
font=lambda n,b=False:ImageFont.truetype('C:/Windows/Fonts/'+('segoeuib.ttf' if b else 'segoeui.ttf'),n)
titles=['A / Western foothills','B / Northern terrace','C / Eastern rolling ground']
notes=['Best starting point: broad gentle slopes.','Similar relief, farther north along the basin.','More undulation and steeper local slopes.']
palette=['#f3ce7b','#d4e3b9','#e5a381']
shoreline='--shoreline' in sys.argv
plans=info['terrain_candidates'][:3]
if shoreline:
    from pyproj import Transformer
    plans=[{'centre_nztm':[1382600,5081000],
            'centre_lon_lat':list(Transformer.from_crs(2193,4326,always_xy=True).transform(1382600,5081000)),
            'selection':'1 km lower-terrace study within the user-indicated area south of C'}]
    titles=['D / Eastern shoreline terrace']
    notes=['Lower terrace, with gullies and steep hill backdrop.']
    palette=['#e7b9ea']
sheet=Image.new('RGB',(544 if shoreline else 1584,775),'#172123');draw=ImageDraw.Draw(sheet)
draw.text((32,20),'SHORELINE / 1 KM STUDY' if shoreline else 'THREE POSSIBLE 1 KM DEMO SITES',font=font(30,True),fill='#f2f0df')
draw.text((32,65),'Real terrain / north up / no roads authored' if shoreline else 'Real terrain / equal map scale / north up / routes not yet designed',font=font(19),fill='#bbc8c3')
rows=[]
with rio.open(OUT/'Region_DEM_1m_NZTM.tif') as src:
    for index,c in enumerate(plans):
        letter='D' if shoreline else 'ABC'[index];target=OUT/('Candidate_'+letter);target.mkdir(exist_ok=True)
        cx,cy=[round(v) for v in c['centre_nztm']]
        bounds=[cx-500,cy-500,cx+500,cy+500]
        n=1024;step=1000/(n-1)
        # The first and last pixel centres represent the exact 1 km endpoints.
        transform=from_origin(bounds[0]-step/2,bounds[3]+step/2,step,step)
        h=np.full((n,n),-9999,dtype='float32')
        reproject(rio.band(src,1),h,src_transform=src.transform,src_crs=src.crs,
                  dst_transform=transform,dst_crs=src.crs,src_nodata=-9999,dst_nodata=-9999,
                  resampling=Resampling.bilinear,num_threads=2)
        assert np.isfinite(h).all() and (h!=-9999).all()
        low,high=float(h.min()),float(h.max());base=math.floor(low/16)*16-16
        span=2**math.ceil(math.log2(high-base+16))
        encoded=np.rint((h-base)/span*65535).astype('uint16')
        path=target/f'H_Candidate_{letter}_1024.png';Image.fromarray(encoded).save(path)
        assert path.read_bytes()[24:26]==bytes([16,0])
        decoded=np.asarray(Image.open(path)).astype('float64')/65535*span+base
        error=float(np.max(np.abs(decoded-h)))
        assert error<=span/65535/2+1e-4
        with rio.open(target/f'Candidate_{letter}_Elevations_NZTM.tif','w',driver='GTiff',
                      count=1,height=n,width=n,dtype='float32',crs=src.crs,transform=transform,
                      nodata=-9999,compress='deflate',predictor=3) as dst:dst.write(h,1)
        gy,gx=np.gradient(h,step);shade=np.clip((1-.7*gx+.7*gy)/np.sqrt(gx*gx+gy*gy+1),.1,1.45)
        t=(h-low)/max(high-low,1)
        colour=np.array([128,145,113])[None,None,:]*(1-t[:,:,None])+np.array([185,166,126])[None,None,:]*t[:,:,None]
        rgb=np.clip(colour*(.45+.5*shade[:,:,None]),0,255).astype('uint8')
        rgb[h<361]=[57,99,113]
        preview=Image.fromarray(rgb);preview.save(target/f'Candidate_{letter}_Preview.png')
        x=32+index*520
        draw.text((x,112),titles[index],font=font(23,True),fill=palette[index])
        sheet.paste(preview.resize((496,496),Image.Resampling.LANCZOS),(x,152))
        draw.line((x+18,626,x+117,626),fill='white',width=3)
        draw.text((x+18,600),'200 m',font=font(16),fill='white')
        draw.text((x,665),f'{low:.0f}–{high:.0f} m elevation  |  {high-low:.0f} m total relief',font=font(19),fill='#ecede1')
        draw.text((x,697),notes[index],font=font(17),fill='#bbc8c3')
        row=dict(c,id=letter,title=titles[index],centre_nztm=[cx,cy],bounds_nztm=bounds,
                 elevation_m=[low,high],gaea_width_m=1000,gaea_height_m=span,
                 elevation_offset_m=base,encoding='NZVD2016 metres = PNG/65535 * gaea_height_m + elevation_offset_m',
                 max_png_quantization_error_m=error,
                 orientation='North-up: row 0 is maximum NZTM northing. Columns increase east. Pixel centres span exactly 1000 m.',
                 caution='Terrain-shape candidate only; road gradients, drainage, crossing locations and land cover not yet verified.')
        land=h>=361
        # Statistics use a 5 m view to avoid confusing tiny LiDAR features with
        # broad terrain slope. They do not represent a surveyed road gradient.
        coarse=h[::5,::5];sy,sx=np.gradient(coarse,step*5)
        land5=coarse>=361;slopes=np.degrees(np.arctan(np.hypot(sx,sy)))
        row['land_fraction_above_361m']=float(land.mean())
        row['land_under_10_degrees_fraction_5m']=float(np.mean(slopes[land5]<10))
        (target/'heightmap.json').write_text(json.dumps(row,indent=2));rows.append(row)
draw.text((32,745),'LINZ / CC BY 4.0   |   Terrain preview colours' if shoreline else 'LINZ Data Service / CC BY 4.0   |   Colours show terrain shape, not satellite imagery or vegetation.',font=font(15),fill='#aabbb7')
sheet.save(OUT/('Candidate_D_Study.png' if shoreline else 'Candidate_Comparison.png'))
overview=Image.open(OUT/'Region_Overview.png');d=ImageDraw.Draw(overview)
left,bottom,right,top=info['bounds_nztm'];scale=(overview.width-80)/(right-left)
for i,row in enumerate(rows):
    l,b,r,t=row['bounds_nztm'];x1=40+(l-left)*scale;x2=40+(r-left)*scale;y1=100+(top-t)*scale;y2=100+(top-b)*scale
    d.rectangle((x1,y1,x2,y2),outline=palette[i],width=4)
    d.rounded_rectangle((x1,y1-33,x1+35,y1),4,fill=palette[i])
    d.text((x1+8,y1-32),row['id'],font=font(23,True),fill='#172123')
overview.save(OUT/('Region_With_D.png' if shoreline else 'Region_With_Candidates.png'))
if shoreline:
    row=rows[0]
    # Location inset has the same map orientation as the user's selected area.
    box=(1060,345,1430,780)
    overview.crop(box).resize((740,870),Image.Resampling.LANCZOS).save(OUT/'Candidate_D_Location.png')
    note=f'''# Candidate D: eastern shoreline terrace

Prepared from the area the user indicated below candidate C. The supplied screenshot matches approximately a 2.2 x 2.4 km area; D marks a proposed 1 km square within its lower terrace rather than treating the whole screenshot as a 1 km tile.

- Centre NZTM: 1382600 E, 5081000 N.
- Study bounds: 1382100–1383100 E, 5080500–5081500 N.
- Terrain elevations: {row['elevation_m'][0]:.2f}–{row['elevation_m'][1]:.2f} m NZVD2016.
- Land above the approximate 361 m lake threshold: {row['land_fraction_above_361m']*100:.1f}%.
- Of that land, {row['land_under_10_degrees_fraction_5m']*100:.1f}% has slope below 10 degrees at about 5 m sampling. This is a landform statistic, not a road grade or driveability test.

Design recommendation: use the low terrace for the main route, with the hills and lake as the backdrop. A contour-following climb could provide a more demanding branch. Review the gullies for a possible crossing, but the DEM alone does not establish water flow or ford suitability. The steeper upper slopes are better kept outside the main driving loop.

Gaea: load `Candidate_D/H_Candidate_D_1024.png` through a File node using Raw scale, width 1000 m and height {row['gaea_height_m']} m. Add {row['elevation_offset_m']} m to its Gaea elevation to recover NZVD2016 elevation. North is at the top; first and last pixel centres span exactly 1000 m. Full transform and encoding are in `Candidate_D/heightmap.json`. These settings replace the earlier synthetic-blockout settings for this input only.

`Candidate_D_Study.png` shows the close-up. `Candidate_D_Location.png` shows the selected square within the indicated area; `Region_With_D.png` shows it in the full download. The GeoTIFF preserves metre elevations. No roads, erosion or changes to the playable Unreal level have been applied.

Source and attribution: LINZ Data Service, Toitū Te Whenua Land Information New Zealand, CC BY 4.0. See `LINZ_source_and_license.txt`.
'''
    (OUT/'Candidate_D_README.md').write_text(note,encoding='utf-8')
    print(json.dumps(row,indent=2))
    sys.exit(0)
(OUT/'candidates.json').write_text(json.dumps({'recommended':'A','candidates':rows},indent=2))
doc='''# Real terrain: Lake Benmore region

Prepared from the supplied LINZ download. This is a separate source-data and site-selection package; the accepted Unreal blockout and other environment asset work are untouched.

## Download inspection

- Four 1 m GeoTIFF tiles, NZTM2000 / EPSG:2193; metre elevations in NZVD2016.
- Combined footprint: 13.688 x 12.779 km; 174,918,952 valid source pixels, no missing cells.
- Elevation range: 360.488–1571.505 m. The large central flat area is Lake Benmore; it must not be treated as driveable ground or surveyed lake-bed bathymetry.
- `Region_DEM_1m_NZTM.tif` joins the tiles without resampling. Complete missing-value scan passed; 36 checks at tile corners, centres and edges matched source elevations exactly.
- `Region_Overview_5m_NZTM.tif` is for browsing. Use the full-resolution mosaic for production crops.
- `LINZ_source_and_license.txt` preserves the supplied attribution and metadata.

## Candidate sites

See `Region_With_Candidates.png` for positions and `Candidate_Comparison.png` for equally scaled close-ups. A is the suggested starting point: gentle western foothill terrain with sufficient elevation change for a route. B is a northern alternative. C has more local undulation. Ranking uses slope and relief, excluding lake-level areas; it is a design suggestion, not proof of driveability. Roads, land cover and possible stream crossings still need review. The blue lake preview mask is inferred from elevations below 361 m, not an authoritative shoreline dataset.

Each candidate spans exactly 1000 x 1000 m between the outer pixel centres, with a 1024 x 1024 16-bit PNG for Gaea and a matching float GeoTIFF for geographic reference. Native one-metre elevations were sampled bilinearly. The GeoTIFF footprint extends half a sample beyond the study bounds because GIS pixels have area; its first/last pixel centres coincide with the study edges.

## Open a candidate in Gaea

Create a new graph, add a File node, choose that candidate's `H_Candidate_*_1024.png`, and use Raw scale with no Autolevel. Set Width 1000 m and Height from this table. Start at 1024 resolution.

| Candidate | Terrain Height | Add to Gaea elevation to recover NZVD2016 | Observed elevations |
| --- | --- | --- | --- |
'''
for row in rows:
    doc+=f"| {row['id']} | {row['gaea_height_m']} m | {row['elevation_offset_m']} m | {row['elevation_m'][0]:.2f}–{row['elevation_m'][1]:.2f} m |\n"
doc+='''
These files are north-up; row zero is the northern edge. The earlier synthetic blockout package used a different row orientation and encoding. Use each candidate's `heightmap.json`, not the earlier blockout settings, for integration. No height exaggeration or erosion has been applied.

Choose a site before adapting the route. The synthetic road-protection masks do not align to these geographic locations. Keep the accepted road rhythm as a design reference, then fit roads to the selected landforms. An Unreal import must also reconcile deterministic gameplay height queries and recheck collision and driving.

Rebuild tools: `Art/tools/inspect_linz_terrain.py` and `Art/tools/package_linz_candidates.py`. Python runtime: `Saved/Tools/TerrainPython/Scripts/python.exe` (rasterio, pyproj, numpy, Pillow). The `--preview-only` inspector option reuses the native mosaic and verifies it before rebuilding previews.

Attribution: Sourced from the LINZ Data Service and licensed by Toitū Te Whenua Land Information New Zealand for re-use under CC BY 4.0. Source: https://data.linz.govt.nz/layer/121859-new-zealand-lidar-1m-dem/
'''
(OUT/'START_HERE.md').write_text(doc,encoding='utf-8')
(ROOT/'docs/MACKENZIE_REAL_TERRAIN.md').write_text(doc,encoding='utf-8')
print(json.dumps([{k:r[k] for k in ['id','elevation_m','gaea_height_m','elevation_offset_m','max_png_quantization_error_m']} for r in rows],indent=2))
