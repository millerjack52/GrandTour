"""Native editor reference -> isolated Unreal comparison inputs.

Geometry/placement comes from an actual editor build, not a new procedural map.
The engine adapters (asset substitutions, physical thickness, shoreline mesh and
Unreal height quantisation) are recorded explicitly in authoring.json.
"""
from pathlib import Path
import json, struct, hashlib, math
import numpy as np
from PIL import Image
from decode_mudrunner_editor_stg import decode,blocks,grass_instances

ROOT=Path(__file__).resolve().parents[2];OUT=ROOT/'Art/Export/NativeRoad';OUT.mkdir(exist_ok=True)
REF=ROOT/'Art/Export/MudRunnerEditorResearch/NativeBaseline'
STG=REF/'ref_codex_road_baseline.stg';meta,_=decode(STG);native=blocks(STG)
SIZE=12800.;ORIGIN=-6400.;SPAN=4096.;N=1024

def sample(a,u,v):
    x=np.clip(u,0,1)*(a.shape[1]-1);y=np.clip(v,0,1)*(a.shape[0]-1)
    i=np.minimum(x.astype(int),a.shape[1]-2);j=np.minimum(y.astype(int),a.shape[0]-2);fx=x-i;fy=y-j
    if a.ndim==3:fx=fx[...,None];fy=fy[...,None]
    return (a[j,i]*(1-fx)+a[j,i+1]*fx)*(1-fy)+(a[j+1,i]*(1-fx)+a[j+1,i+1]*fx)*fy

def fields(x,y):
    x,y=np.broadcast_arrays(np.asarray(x,dtype=float),np.asarray(y,dtype=float))
    nx=np.clip(x/100,-48,48-1e-6);nz=np.clip(y/100,-64,64-1e-6)
    ix=np.floor((nx+48)/16).astype(int);iz=np.floor((nz+64)/16).astype(int)
    h=np.zeros(x.shape);dep=h.copy();grass=h.copy();track=h.copy();wl=h.copy();coverage=h.copy();rel=h.copy()
    for k,b in enumerate(native):
        hit=(iz*6+ix)==k
        if not hit.any():continue
        u=(nx[hit]-b['xz'][0])/16;v=(nz[hit]-b['xz'][1])/16
        h[hit]=sample(b['height'],u,v)
        grass[hit]=1-sample(b['blockmap'][:25,:25,1].astype(float)/255,u,v)
        if b['mud'] is not None:
            # Native serialized channels are A then R. Base grid already includes
            # road texture offset; authored mud adds (R-155)*0.008 metres.
            rel[hit]=sample((b['mud'][:,:,1].astype(float)-155)*.008,u,v)
            track[hit]=sample(b['mud'][:,:,0].astype(float)/255,u,v)
            dep[hit]=sample(b['control'].astype(float)/255,u,v)*124
        if b['waterdata'] is not None:
            wd=b['waterdata'].reshape(5,5,2)
            wl[hit]=sample(wd[:,:,0],u,v)
            # The interleaved DWORD is packed colour, not a second float.
            alpha=(wd[:,:,1].copy().view('u4')>>24).astype(float)/255
            coverage[hit]=sample(alpha,u,v)
    return dict(height=(h+rel)*100,base=h*100,relief=rel*100,depth=dep,grass=grass,track=track,water=wl*100,coverage=coverage)

def grid(n,centres=True):
    a=ORIGIN+(np.arange(n)+.5)*SIZE/n if centres else np.linspace(ORIGIN,-ORIGIN,n)
    return np.meshgrid(a,a)
def save(name,a):Image.fromarray(np.uint8(np.clip(a,0,1)*255+.5)).save(OUT/(name+'.png'))
def pack(name,a):
    q=np.uint16(np.clip(a,0,1)*65535+.5)
    Image.fromarray(np.stack([q>>8,q&255,np.zeros_like(q),np.full_like(q,255)],-1).astype('uint8')).save(OUT/(name+'.png'))
    return q

x,y=grid(N);f=fields(x,y);z=f['height'];deep=f['depth'];grass=f['grass'];tracks=f['track']
# Physical layer remains the existing host solver. Preserve normalized native
# extrude controls; 1.24m is the native maximum extrusion constant. Exact CPU
# tire material/strength conversion remains an explicit parity gap.
deep=np.maximum(deep,2.5);deep[np.abs(x)>4800]=2.5
wet=np.clip(.45+deep/160,0,1)
paint=np.stack([deep/124,np.ones_like(z),np.zeros_like(z),wet],-1)
paint[[0,-1],:,:]=[0,1,0,0];paint[:,[0,-1],:]=[0,1,0,0]
save('paint',paint)
save('style',np.stack([np.zeros_like(z),grass*(1-tracks*.7),wet,np.zeros_like(z)],-1))
pack('rest',np.full_like(z,50/65));pack('macro',z/32768)
pack('relief',np.full((4,4),50/65));pack('ReliefLighting',np.full((4,4),50/65))
save('authoredTracks',np.stack([tracks,tracks,tracks,np.ones_like(z)],-1))
hx,hy=grid(1009,False);hf=fields(hx,hy);q=pack('HeightRG',hf['height']/SPAN);q.astype('<u2').tofile(OUT/'height.r16')

# Mean water heights are decoded from the native 5x5 corner records per block.
# Host surface triangulation clips at the imported physical bed.
D=512;wx,wy=grid(D);wf=fields(wx,wy);wd=(wf['water']-wf['height'])/100
wetmask=(wf['coverage']>.1)&(wd>.005)
domain=np.stack([wf['water'],np.where(wetmask,wd,-1),np.zeros_like(wd),np.zeros_like(wd)],-1).astype('<f4')
(OUT/'water-domain.bin').write_bytes(struct.pack('<5i3f',0x47545744,D,D,1,1,ORIGIN,ORIGIN,SIZE/D)+domain.tobytes()+bytes([0]))
save('waterflow',np.stack([np.full_like(wd,.5),np.full_like(wd,.5),np.clip(wd/2,0,1),wetmask],-1))
dy,dx=np.gradient(wf['height']/100,SIZE/D/100);shore=wd/np.maximum(np.hypot(dx,dy),.02)
save('waterShore',np.stack([wetmask,.5+np.clip(shore,-2,2)/4,np.zeros_like(wd),np.ones_like(wd)],-1))
M=513;mx,my=grid(M,False);mf=fields(mx,my);distance=np.minimum(mf['water']-mf['height'],(mf['coverage']-.1)*100)
verts=faces=0
with (OUT/'Water.obj').open('w') as out:
    for j in range(M-1):
        for i in range(M-1):
            ids=[(j,i),(j,i+1),(j+1,i+1),(j+1,i)]
            if max(distance[t] for t in ids)<=0:continue
            for tri in [(0,1,2),(0,2,3)]:
                poly=[np.array([mx[ids[k]],my[ids[k]],mf['water'][ids[k]],distance[ids[k]]]) for k in tri];cut=[]
                for a,b in zip(poly,poly[1:]+poly[:1]):
                    if a[3]>=0:cut.append(a)
                    if (a[3]>=0)!=(b[3]>=0):cut.append(a+(b-a)*(a[3]/(a[3]-b[3])))
                if len(cut)<3:continue
                for a in cut:out.write('v %.4f %.4f %.4f\n'%(a[0],-a[1],a[2]))
                for k in range(1,len(cut)-1):out.write(f'f {verts+1} {verts+k+2} {verts+k+1}\n');faces+=1
                verts+=len(cut)

trees=[];under=[];debris=[]
for i,p in enumerate(meta['plants']):
    a,b,c=p['native_xyz'];raw=bytes.fromhex(p['packed']);scale=.25+raw[7]/255*3.75
    quat=np.array([raw[2],raw[1],raw[0],raw[3]],dtype=float)/127.5-1;quat/=np.linalg.norm(quat)
    # Native Y-up -> UE Z-up, with handedness change; yaw is sufficient for
    # upright replacement assets. Full native quaternion retained in provenance.
    qx,qy,qz,qw=quat;yaw=-math.degrees(math.atan2(2*(qw*qy+qx*qz),1-2*(qy*qy+qz*qz)))
    px,py=a*100,c*100;hz=float(fields(px,py)['height']);brand=p['brand']
    if brand in ['birch_a','birch_b','birch_c','birch_big_a','pine_dry_a','fir_small_a','spruce_a','spruce_b']:
        trees.append([px,py,hz,i%3,1200*scale,yaw])
    elif brand.startswith(('bush','birch_bush','small_tree')):
        under.append(dict(kind=0,p=[px,py,hz],height_cm=(230 if brand.startswith('small_tree') else 110)*scale,yaw=yaw))
    elif brand.startswith('small_twig'):
        under.append(dict(kind=2,p=[px,py,hz],height_cm=24*scale,yaw=yaw))
    else:debris.append(dict(brand=brand,native_p=[a*100,c*100,b*100],p=[px,py,hz],scale=scale,yaw=yaw,native_quat=quat.tolist()))
(OUT/'trees.json').write_text(json.dumps(trees));(OUT/'understory.json').write_text(json.dumps(under));(OUT/'debris.json').write_text(json.dumps(debris))
grass_rows=[]
for g in grass_instances(STG):
    if not g['brand'].startswith('grass_'):continue
    x,_,y=g['native_xyz'];px,py=x*100,y*100
    grass_rows.append(dict(p=[px,py,float(fields(px,py)['height'])-2],height_cm=(52 if g['brand']=='grass_long' else 24)*g['scale'],yaw=math.degrees((x*17.371+y*115.913)%(2*math.pi)),brand=g['brand']))
(OUT/'grass.json').write_text(json.dumps(grass_rows,separators=(',',':')))
sites=[]
for name,px,py,yaw in [('Road_entry',-550,5700,-88),('Muddy_bend',-1550,-1100,-70),('Pool_edge',550,4000,-95)]:
    sites.append(dict(name=name,center=[px,py],center_height_cm=float(fields(px,py)['height']),yaw=yaw))
cost=np.where(wetmask&(wd>.15)&(wd<.65),wx**2+(wy-3000)**2,1e20);j,i=np.unravel_index(cost.argmin(),cost.shape);assert cost[j,i]<1e20
(OUT/'water-probe.json').write_text(json.dumps(dict(point=[float(wx[j,i]),float(wy[j,i])],surface_cm=float(wf['water'][j,i]),depth_m=float(wd[j,i]))))
preview=np.stack([.25+.10*(1-grass),.20+.15*grass,.10+.06*grass],-1);preview[f['coverage']>.1]=np.where(((f['water']-z)>0)[f['coverage']>.1,None],[.08,.28,.34],preview[f['coverage']>.1]);save('reference-plan',preview)
other=blocks(REF/'ref_codex_road_nooffset.stg');diff=np.concatenate([(b['height']-a['height']).ravel() for a,b in zip(other,native)])
comparison=dict(changed_input='Both road ApplyOffset true -> false',base_height_delta_min_m=float(diff.min()),base_height_delta_max_m=float(diff.max()),changed_height_samples=int(np.count_nonzero(diff)),compared_samples=len(diff),baseline_plants=len(meta['plants']),variant_plants=len(decode(REF/'ref_codex_road_nooffset.stg')[0]['plants']),note='Compiled quantisation can affect neighbouring samples; seed scheduling parity is not claimed.')
(REF/'offset-comparison.json').write_text(json.dumps(comparison,indent=2))
report=dict(ok=True,native_source=str(STG),native_source_sha256=meta['sha256'],native_extent_m=meta['size'],origin=[ORIGIN,ORIGIN],size=SIZE,height_resolution=1009,height_span_cm=SPAN,z_scale=SPAN*128/65535,landscape_z_cm=SPAN*32768/65535,terrain_sha256=hashlib.sha256((OUT/'height.r16').read_bytes()).hexdigest(),sites=sites,trees=len(trees),understory=len(under),debris=len(debris),water_triangles=faces,wet_domain_cells=int(wetmask.sum()),maximum_water_depth_m=float(wd[wetmask].max()),native_relief_cm=[float(f['relief'].min()),float(f['relief'].max())],driving_tested=False,adapters=['Existing Unreal tree/bush/wood meshes substitute native brands; original imported mud clods use native XYZ, orientation and scale.', 'Native base height and signed mud relief baked into 12.7cm Unreal landscape; existing solver adds live deformation.', 'Physical thickness uses native extrude mask scaled by 124cm; exact native CPU strength conversion remains unverified.', 'Existing host grass generator uses native cover; native packed grass placement is retained but not decoded.', 'Shore mesh clipped against imported bed; native water levels retained.'],offset_experiment=comparison)
report['native_grass_instances']=len(grass_rows)
report['adapters'][3]='Native grass positions and scale decoded and mapped to existing Unreal blade mesh; existing contact component retains bending/removal.'
(OUT/'authoring.json').write_text(json.dumps(report,indent=2));print(json.dumps(report,indent=2))
