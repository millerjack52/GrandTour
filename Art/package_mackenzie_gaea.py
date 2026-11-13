"""Create aligned Gaea height inputs, route masks and a readable terrain brief.

Requires numpy and Pillow. Run export_mackenzie_gaea.py in Unreal first.
All height resampling uses endpoint-aligned bilinear interpolation.
"""
from pathlib import Path
import hashlib, json, math, shutil
import numpy as np
from PIL import Image, ImageDraw, ImageFont

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / 'Art/Export/MackenzieGaea/first-pass'
SRC = ROOT / 'Art/Export/MackenzieBlockout'
export = json.loads((OUT / 'landscape-export.json').read_text())
assert export['ok'], export
layout = json.loads((SRC / 'setup-report.json').read_text())
original = np.fromfile(OUT / 'H_Mackenzie_UE_original.r16', dtype='<u2').reshape(1009, 1009)
height = (original.astype(np.float64) - 32768) / 128
Image.fromarray(original).save(OUT / 'H_Mackenzie_UE_original_1009.png')

def resample(a, n):
    p = np.linspace(0, a.shape[0]-1, n)
    lo = p.astype(int); hi = np.minimum(lo+1, a.shape[0]-1); f = p-lo
    rows = a[lo] * (1-f[:,None]) + a[hi] * f[:,None]
    return rows[:,lo] * (1-f[None,:]) + rows[:,hi] * f[None,:]

N = 1024
h = resample(height, N)
# Black=-16 m UE, white=112 m UE. Gaea gets a 128 m positive range.
encoded = np.rint((h+16) / 128 * 65535).astype(np.uint16)
Image.fromarray(encoded).save(OUT / 'H_Mackenzie_Start_1024.png')
xy = np.linspace(-500, 500, N)
X,Y = np.meshgrid(xy,xy)

def distance(rows):
    result = np.full((N,N), np.inf)
    points = np.array([[r['x_m'],r['y_m']] for r in rows])
    for a,b in zip(points[:-1],points[1:]):
        delta = b-a
        den = np.dot(delta,delta)
        if den < 1e-10: continue
        t = np.clip(((X-a[0])*delta[0]+(Y-a[1])*delta[1])/den,0,1)
        d2 = (X-a[0]-t*delta[0])**2+(Y-a[1]-t*delta[1])**2
        np.minimum(result,d2,out=result)
    return np.sqrt(result)

def capsule(a,b):
    return distance([dict(x_m=a[0],y_m=a[1]),dict(x_m=b[0],y_m=b[1])])

def feather(d, core, outer):
    t=np.clip((d-core)/(outer-core),0,1)
    return 1-t*t*(3-2*t)

loop = layout['route']
track = layout['shortcut']
if math.hypot(loop[-1]['x_m']-loop[0]['x_m'],loop[-1]['y_m']-loop[0]['y_m']) > .01:
    loop=loop+[loop[0]]
dl = distance(loop); ds = distance(track)
ford = min(loop,key=lambda r:abs(r['arc_m']-layout['ford_arc_m']))
df = np.hypot(X-ford['x_m'],Y-ford['y_m'])
# Conservatively retain the broad graded shortcut embankment, not only the track.
ramp = [r for r in track if r['arc_m'] >= layout['shortcut_length_m']-355]
dr = distance(ramp)
protect = np.maximum.reduce([feather(dl,8,35),feather(ds,5,28),
    feather(dr,40,65),feather(df,40,65),
    feather(np.hypot(X+45,Y+388),22,45)])
masks = {
    'M_ProtectGameplay':protect,
    'M_EditTerrain':1-protect,
    'M_MainRoad':feather(dl,3.2,4.2),
    'M_Shortcut':feather(ds,2,3),
    'M_StreamGuide':feather(capsule((110,-80),(500,-80)),17,40),
    'M_FordKeep':feather(df,40,65),
}
for name,a in masks.items():
    Image.fromarray(np.rint(a*255).astype(np.uint8)).save(OUT/(name+'_1024.png'))

# Aligned, transparent route guide, useful over a terrain render.
overlay=Image.new('RGBA',(N,N)); od=ImageDraw.Draw(overlay)
def coords(rows): return [((r['x_m']+500)/1000*(N-1),(r['y_m']+500)/1000*(N-1)) for r in rows]
od.line(coords(loop),fill=(244,205,117,255),width=4,joint='curve')
od.line(coords(track),fill=(239,138,92,255),width=3,joint='curve')
fx,fy=coords([ford])[0]
od.ellipse((fx-9,fy-9,fx+9,fy+9),outline=(105,225,233,255),width=3)
overlay.save(OUT/'Route_Overlay_1024.png')

# Human preview: +Y is up. This flip applies ONLY to the review image.
gy,gx=np.gradient(h,1000/(N-1))
shade=np.clip((1-.65*gx+.85*gy)/np.sqrt(1+gx*gx+gy*gy),.15,1.4)
rgb=np.clip(np.array([153,158,124])[None,None,:]*(.5+.45*shade[:,:,None]),0,255).astype(np.uint8)
terrain=Image.fromarray(rgb).convert('RGBA')
pd=ImageDraw.Draw(terrain)
for i in range(1,10):
    q=round(i*(N-1)/10)
    pd.line((q,0,q,N-1),fill=(210,219,204,70))
    pd.line((0,q,N-1,q),fill=(210,219,204,70))
terrain=Image.alpha_composite(terrain,overlay).transpose(Image.Transpose.FLIP_TOP_BOTTOM)
canvas=Image.new('RGB',(1512,1170),(23,31,33)); canvas.paste(terrain,(36,104))
d=ImageDraw.Draw(canvas)
def font(n,bold=False): return ImageFont.truetype('C:/Windows/Fonts/'+('segoeuib.ttf' if bold else 'segoeui.ttf'),n)
d.text((36,25),'MACKENZIE / GAEA STARTING TERRAIN',font=font(30,True),fill='#edf0e4')
d.text((38,68),'Accepted route  /  1,000 x 1,000 metres  /  terrain handoff 01',font=font(18),fill='#b4c0bd')
tx=1090
d.text((tx,112),'KEEP THE DRIVE',font=font(23,True),fill='#f4cd75')
notes=[('Main loop','2.35 km / 6.4 m wide'),('Centre shortcut','699 m / 4 m wide'),('Ford','Retain bed and approach heights'),('White protection mask','Preserve original terrain'),('Black protection mask','Terrain available for shaping')]
for k,(title,body) in enumerate(notes):
    y=165+k*78
    d.text((tx,y),title,font=font(20,True),fill='#e4e9df')
    d.text((tx,y+30),body,font=font(16),fill='#b4c0bd')
d.text((tx,590),'SHAPE THE LAND',font=font(23,True),fill='#bcd0b4')
for k,line in enumerate(['Broaden the basin floor.','Soften cuts beyond road margins.','Shape the western ridge shoulders.','Use restrained erosion.','Keep the ford open and readable.','','Distant mountains come later,','outside this playable square.']):
    d.text((tx,640+k*31),line,font=font(18),fill='#ced7cf')
d.text((tx,960),'+Y / north is up in this preview.',font=font(16),fill='#a6b6b5')
d.text((tx,990),'Import files keep native row order.',font=font(16),fill='#a6b6b5')
def mark(row,label,delta=(12,-30)):
    x=36+(row['x_m']+500)/1000*(N-1)
    y=104+(500-row['y_m'])/1000*(N-1)
    d.ellipse((x-5,y-5,x+5,y+5),fill='#ffffff',outline='#182025',width=2)
    p=(x+delta[0],y+delta[1]); box=d.textbbox(p,label,font=font(18,True))
    d.rounded_rectangle((box[0]-6,box[1]-4,box[2]+6,box[3]+4),4,fill='#182025')
    d.text(p,label,font=font(18,True),fill='#ffffff')
mark(loop[4],'Start')
mark(ford,'Ford',(-60,18))
mark(track[0],'Shortcut junction',(-170,-35))
mark(track[-1],'Rejoin',(-65,-36))
mark(min(loop,key=lambda r:abs(r['arc_m']-1338)),'Western ridge')
d.line((66,1090,168,1090),fill='#ffffff',width=4)
d.text((66,1056),'100 m',font=font(18),fill='#ffffff')
d.text((36,1135),'REFERENCE VIEW ONLY  |  heightmaps and masks contain no labels or grid',font=font(16),fill='#a6b6b5')
canvas.save(OUT/'Gaea_Terrain_Guide.png')

shutil.copy2(SRC/'setup-report.json',OUT/'accepted-layout.json')
# Verify file format and encoding, and quantify rather than hide resampling loss.
disk=np.asarray(Image.open(OUT/'H_Mackenzie_Start_1024.png')).astype(np.float64)/65535*128-16
rt=resample(disk,1009)
err=np.abs(rt-height)
route_errors=[]
for r in loop+track:
    px=(r['x_m']+500)/1000*1008; py=(r['y_m']+500)/1000*1008
    ix=min(int(px),1007); iy=min(int(py),1007); fx=px-ix; fy=py-iy
    route_errors.append(float(err[iy,ix]*(1-fx)*(1-fy)+err[iy,ix+1]*fx*(1-fy)+err[iy+1,ix]*(1-fx)*fy+err[iy+1,ix+1]*fx*fy))
assert (OUT/'H_Mackenzie_Start_1024.png').read_bytes()[24:26] == bytes([16,0])
assert np.array_equal(np.asarray(Image.open(OUT/'H_Mackenzie_UE_original_1009.png')),original)
assert max(route_errors)<.25
manifest={
    'ok':True,'revision':'first-pass','width_m':1000,'input_resolution':1024,
    'gaea_terrain_definition':{'width_m':1000,'height_m':128},
    'gaea_to_unreal_z_offset_m':-16,
    'input_height_decode':'UE height metres = pixel/65535 * 128 - 16',
    'original_ue_height_decode':'UE height metres = (pixel-32768)/128',
    'orientation':'Row 0 is UE Y=-500m. Column 0 is UE X=-500m. All import files have identical orientation. Preview guide alone is flipped for north-up reading.',
    'original_unreal_transform':{'location_cm':[-50000,-50000,0],'scale':[100000/1008,100000/1008,100]},
    'protection':'White keeps accepted heights; black permits shaping. Final = original*protect + edited*(1-protect).',
    'export_validation':{'sample_count':len(export['anchors']),'max_error_m':export['max_error_m']},
    'input_quantization_error_m':float(np.max(np.abs(disk-h))),
    'bilinear_1009_1024_1009_roundtrip':{'max_m':float(err.max()),'rms_m':float(np.sqrt(np.mean(err**2))),'max_sampled_route_error_bound_m':max(route_errors)},
    'note':'This is an input package, not a saved Gaea graph or a reimported terrain. Preserve the original 1009 data for restoring road geometry at integration.',
    'files':{}
}
for p in sorted(OUT.iterdir()):
    if p.is_file() and p.suffix in ['.png','.r16']:
        manifest['files'][p.name]={'bytes':p.stat().st_size,'sha256':hashlib.sha256(p.read_bytes()).hexdigest()}
(OUT/'package-manifest.json').write_text(json.dumps(manifest,indent=2))
print(json.dumps({k:v for k,v in manifest.items() if k in ['ok','export_validation','input_quantization_error_m','bilinear_1009_1024_1009_roundtrip']},indent=2))
