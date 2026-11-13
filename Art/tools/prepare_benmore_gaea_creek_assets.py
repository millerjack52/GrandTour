"""Package matching native bed, hydraulic domain, shoreline mesh and data masks."""
import json,hashlib,sys
import numpy as np
from PIL import Image
from scipy.ndimage import map_coordinates,distance_transform_edt
import reshape_benmore_channel as shape
import build_benmore_gaea_creek as creek
import prepare_benmore_water_domain as domain
import prepare_benmore_river_life as geometry

ROOT,BASE,OUT=creek.ROOT,creek.BASE,creek.OUT
MORPHOLOGY='--morphology' in sys.argv
COURSE_REVISION='--course-revision' in sys.argv or MORPHOLOGY
if COURSE_REVISION:OUT=BASE/'CourseRevision'
if MORPHOLOGY:OUT=BASE/'Morphology'

def main():
    flow_report=json.loads((OUT/'flow-report.json').read_text())
    assert flow_report['ok'] and flow_report['converged']
    if MORPHOLOGY:
        cold=json.loads((OUT/'cold-start.json').read_text())
        assert cold['native_creek_initial_water_m3']==0
        assert cold['terrain_height_sha256']==hashlib.sha256((OUT/'H_GaeaCreek_2017.r16').read_bytes()).hexdigest()
    h=np.fromfile(OUT/'height_local_south_up.f32',dtype='<f4').reshape(2017,2017)
    oldh=np.fromfile(BASE/('CourseRevision' if MORPHOLOGY else 'GaeaCreek' if COURSE_REVISION else 'ChannelShape')/'height_local_south_up.f32',dtype='<f4').reshape(2017,2017)
    changed=abs(h-oldh)>.008
    prefix=np.zeros((2018,2018),dtype='<u4');prefix[1:,1:]=changed.cumsum(0).cumsum(1)
    prefix.tofile(OUT/'changed-prefix.u32')
    support=np.argwhere(abs(h-oldh)>.08);support=support[np.linspace(0,len(support)-1,24).astype(int)]
    (OUT/'support-checks.json').write_text(json.dumps([[-1250+i*2500/2016,-1250+j*2500/2016] for j,i in support],indent=2))
    domain.SRC=OUT;domain.OUT=OUT;geometry.H=h;geometry.OUT=OUT
    if COURSE_REVISION:
        from prepare_benmore_course_outlet import prepare as prepare_outlet
        outlet=prepare_outlet(OUT)
    else:
        (OUT/'T_RL_Mouth.png').write_bytes((BASE/'RiverLife/T_RL_Mouth.png').read_bytes())
    domain.main()
    with np.load(OUT/'water-domain.npz') as z:d={k:z[k] for k in z.files}
    valid=d['depth']>.005
    river=d['wet'];speed=np.hypot(d['vx'],d['vy'])
    mask=np.stack([np.clip(distance_transform_edt(~river)*1.25/16,0,1),river,np.clip(distance_transform_edt(river)*1.25/6,0,1),np.clip(speed/2,0,1)],-1)
    Image.fromarray(np.uint8(np.rint(mask*255))).save(OUT/'T_RL_WaterMask.png')
    def sample(a,p):return map_coordinates(a,[(p[...,1]-d['y'][0])/1.25,(p[...,0]-d['x'][0])/1.25],order=1,mode='constant')
    def mean(p):
        weight=sample(valid.astype(float),p)
        return sample(d['mean']*valid,p)/np.maximum(weight,1e-8),weight
    # Surface detail is independent of the hydraulic grid. Extract its continuous
    # native-bed intersection, rather than subdividing the old circular footprint.
    meshes=[]
    for name,lo,hi in [('SM_GC_RiverSurface',(-1250,-300),(-220,775)),('SM_GC_OutletSurface',(-1480,-300),(-1250,775))]:
        cell=.625 if name=='SM_GC_RiverSurface' else 1.25
        x=np.arange(lo[0],hi[0]+cell/2,cell);y=np.arange(lo[1],hi[1]+cell/2,cell)
        xx,yy=np.meshgrid(x,y);p=np.stack([xx,yy],-1);surface,weight=mean(p)
        bed=shape.native(h,xx,yy) if lo[0]>=-1250 else sample(np.load(OUT/'flow-bake.npz')['bed'],p)
        # Lake-only coverage belongs to the lake mesh, not an overlapping outlet.
        riverweight=sample(d['wet'].astype(float),p)
        signed=np.minimum(riverweight-.5,(surface-bed-.005)*4)
        info=geometry.exportmesh(name,xx,yy,surface,signed,0)
        data=json.loads((OUT/(name+'.json')).read_text());v=np.array(data['vertices']);f=np.array(data['faces'])
        m,w=mean(v[:,:2]);v[:,2]=m
        area=np.cross(v[f[:,1]]-v[f[:,0]],v[f[:,2]]-v[f[:,0]])[:,2];f=f[area>1e-10]
        assert np.isfinite(v).all() and len(f)>100
        data=dict(vertices=v.tolist(),faces=f.tolist());(OUT/(name+'.json')).write_text(json.dumps(data,separators=(',',':')))
        info.update(triangles=len(f),spacing_m=cell,surface_query_max_error_m=float(abs(v[:,2]-m).max()),all_finite=True,positive_triangle_area=True);meshes.append(info)
    # Reconcile crossings and approach paint with the actual new wet course.
    geometry.bake=np.load(OUT/'flow-bake.npz');geometry.x=d['x'];geometry.y=d['y'];geometry.bx,geometry.by=np.meshgrid(d['x'],d['y'])
    crossings=[geometry.crossing(np.array([-661.25,177.5])),geometry.crossing(np.array([-406.25,438.75]),True)]
    for c in crossings:
        p=np.array(c['center_m'][:2]);n=np.array(c['cross_direction']);ends=np.array(c['ends_m']);anchors=ends[:,:2]+np.array([-1,1])[:,None]*n*4.5
        c['approach_anchors_m']=np.c_[anchors,geometry.ground(anchors[:,0],anchors[:,1])].tolist()
    (OUT/'crossings.json').write_text(json.dumps(crossings,indent=2))
    # Existing material zones, updated from the new continuous shoreline.
    yy,xx=np.meshgrid(np.linspace(-1250,1250,2017),np.linspace(-1250,1250,2017),indexing='ij');p=np.stack([xx,yy],-1)
    surface,weight=mean(p);wet=(weight>=.5)&(surface-h>.005)
    shore=distance_transform_edt(~wet)*(2500/2016)
    shore.astype('<f4').tofile(OUT/'shore_distance.f32')
    path=np.zeros_like(h)
    from scipy.spatial import cKDTree
    roads=json.loads((ROOT/'Art/Export/BenmoreRoads/road-manifest.json').read_text())['routes']
    road=np.concatenate([[[q['x_m'],q['y_m']] for q in r['points']] for r in roads]);paths=[]
    for c in crossings:
        center=np.array(c['center_m'][:2]);n=np.array(c['cross_direction']);end=center-n*(c['span_m']/2+6);start=road[cKDTree(road).query(end)[1]]
        points=geometry.path_between(start,end,wet.astype(float));points=np.vstack([points,np.linspace(end,center+n*(c['span_m']/2+12),45)[1:]])
        width=4.5 if c['name']=='Ford' else 1.7
        distance=cKDTree(points).query(np.c_[xx.ravel(),yy.ravel()])[0].reshape(h.shape)
        path=np.maximum(path,1-shape.smooth((distance-width/2)/1.1));paths.append(dict(name=c['name'],width_m=width,points_m=points.tolist()))
    path.astype('<f4').tofile(OUT/'path_mask.f32');(OUT/'paths.json').write_text(json.dumps(paths,indent=2))
    patch=.5+.5*np.sin(xx*.043+np.sin(yy*.017)*2)*np.cos(yy*.033-xx*.012)
    cluster=np.zeros_like(h)
    for cx,cy,r in [(-1140,-60,36),(-1030,-70,38),(-920,25,32),(-750,140,48),(-620,240,40),(-495,327,42),(-390,460,35),(-336,560,38)]:cluster=np.maximum(cluster,np.exp(-((xx-cx)**2+(yy-cy)**2)/(r*r)))
    mud=(1-np.clip(shore/7,0,1))*(.2+.8*cluster)*np.clip((patch-.3)*1.9,0,1)
    gravel=np.maximum((1-np.clip(shore/10,0,1))*(.45+.55*(1-patch)),path*.88)
    ford=crossings[0]
    for sign in [-1,1]:
        q=np.array(ford['center_m'][:2])+sign*np.array(ford['cross_direction'])*(ford['span_m']/2+3)
        mud=np.maximum(mud,np.exp(-(((xx-q[0])/6)**2+((yy-q[1])/5)**2))*.8)
    bankfull=np.fromfile(OUT/'bankfull_mask.f32','<f4').reshape(h.shape)
    gravel=np.maximum(gravel,bankfull*.88)
    keep=np.minimum(np.clip((shore-1.1)/3.4,0,1),1-bankfull*.96)*(1-path)
    # Reuse the existing meshes and instance budget; distribute their bank
    # positions against the final wet domain, rather than the retired trench.
    rng=np.random.default_rng(81026);positions={}
    for kind,count,lo,hi in [('tree',31,5,16),('rock',100,2.5,9),('gravel',1400,.5,7),('shrub',240,3,13),('tussock',2400,3,13),('aggregate',550,.35,4)]:
        allowed=(shore>lo)&(shore<hi)&(xx>-1230)&(xx<-270)&(yy>-130)&(yy<670)&(path<.05)&(h<90)
        if MORPHOLOGY and kind in ['tree','shrub','tussock']:allowed&=bankfull<.35
        candidate=np.argwhere(allowed)
        assert len(candidate)>count/10
        picked=candidate[rng.integers(len(candidate),size=count)]
        positions[kind]=[[float(xx[j,i]),float(yy[j,i])] for j,i in picked]
    (OUT/'dressing-positions.json').write_text(json.dumps(positions,separators=(',',':')))
    Image.fromarray(np.uint8(np.rint(np.stack([gravel,mud,keep,path],-1)*255))).save(OUT/'T_RL_Ecology.png')
    original=np.asarray(Image.open(BASE.parent/'BenmoreVegetation/T_Benmore_VegetationMask.png'))
    Image.fromarray(np.uint8(np.rint(original*keep[...,None]))).save(OUT/'T_RL_Vegetation.png')
    # Apply the sourced-gravel wrapper across the full native creek domain.
    bounds=(-1250,-1250,1250,1250);cell=2500/2016;x=np.arange(bounds[0],bounds[2]+cell/2,cell);y=np.arange(bounds[1],bounds[3]+cell/2,cell)
    xx,yy=np.meshgrid(x,y);p=np.stack([xx,yy],-1);surface,weight=mean(p);bed=shape.native(h,xx,yy)
    depth=surface-bed;wet=(weight>=.5)&(depth>.005);shore=distance_transform_edt(~wet)*cell;inset=distance_transform_edt(wet)*cell
    edge=np.minimum(p-np.array(bounds[:2]),np.array(bounds[2:])-p).min(-1);core=shape.smooth(edge/12)
    speed=np.hypot(sample(d['vx'],p),sample(d['vy'],p));influence=np.maximum(core*(1-shape.smooth((shore-1.2)/3.8)),bankfull*.96)
    coarse=np.clip(.22+speed*.70+shape.smooth(inset/1.5)*.18,0,1)
    if MORPHOLOGY:
        bars=np.fromfile(OUT/'inside_bar.f32','<f4').reshape(2017,2017)
        rocky=np.fromfile(OUT/'rocky_reach.f32','<f4').reshape(2017,2017)
        # Geographic substrate masks reuse the sourced mineral material. Dry
        # sediment bars and steep reaches retain coarse aggregate independently
        # of today's wetness, rather than turning into smooth uniform silt.
        coarse=np.maximum(coarse,np.maximum(np.clip(bars/.30,0,1)*.86,rocky*.90))
    silt=(1-shape.smooth((speed-.12)/.65))*(1-shape.smooth(shore/1.8))*.62
    bedzones=np.uint8(np.rint(np.stack([coarse,silt,1-shape.smooth(shore/.8),influence],-1)*255))
    Image.fromarray(bedzones).save(OUT/'T_CP_BedZones.png')
    if COURSE_REVISION:extended_bed_zones(bedzones,d)
    coverage=np.minimum(weight-.5,(depth-.005)*4)
    Image.fromarray(np.uint8(np.rint(np.stack([np.clip(.5+coverage,0,1),wet,wet,core],-1)*255))).save(OUT/'T_CP_Shore.png')
    def query(x,y):
        p=np.array([[x,y]]);m,w=mean(p);return dict(covers=bool(w[0]>=.5),surface_m=float(m[0]),ground_m=float(shape.native(h,x,y)),depth_m=float(m[0]-shape.native(h,x,y)))
    queries={c['name'].replace('Footbridge','Bridge'):query(*c['center_m'][:2]) for c in crossings}
    reach=np.load(OUT/'network-paths.npz')['0'];point=reach[np.argmin(np.linalg.norm(reach[:,:2]-np.array([-605,230]),axis=1))]
    queries['Bed']=query(*point[:2]);(OUT/'bed-point.json').write_text(json.dumps(point[:2].tolist()))
    assert all(q['covers'] for q in queries.values()),queries
    report=dict(ok=True,meshes=meshes,hydraulic_spacing_m=1.25,surface_spacing_m=.625,queries=queries,crossings=crossings,
                terrain_height_sha256=hashlib.sha256((OUT/'H_GaeaCreek_2017.r16').read_bytes()).hexdigest(),
                source_original_drive_sha256=hashlib.sha256((ROOT/'Content/GrandTour/Demo/BenmoreRoads/L_Benmore_Drive.umap').read_bytes()).hexdigest())
    if COURSE_REVISION:report['outlet']=outlet
    (OUT/'prepare-report.json').write_text(json.dumps(report,indent=2));print(json.dumps(report,indent=2))

def extended_bed_zones(native,d):
    """One geographic atlas across the native/scenery boundary, exact native pixels."""
    cell=2500/2016;columns=267;origin=-1250-columns*cell
    xx,yy=np.meshgrid(origin+np.arange(columns)*cell,np.linspace(-1250,1250,2017))
    uv=[(yy-d['y'][0])/1.25,(xx-d['x'][0])/1.25]
    sample=lambda a,cval=0:map_coordinates(a,uv,order=1,mode='constant',cval=cval)
    shore=sample(distance_transform_edt(~d['wet'])*1.25,1000)
    wet=sample(d['wet'].astype(float));speed=np.hypot(sample(d['vx']),sample(d['vy']))
    zones=np.stack([np.clip(.22+speed*.70+wet*.18,0,1),
        (1-shape.smooth((speed-.12)/.65))*(1-shape.smooth(shore/1.8))*.62,
        1-shape.smooth(shore/.8),1-shape.smooth((shore-1.2)/8)],-1)
    join=shape.smooth((-xx-1250)/15)[...,None]
    zones=native[:,0:1,:]/255*(1-join)+zones*join
    packed=np.concatenate([np.uint8(np.rint(zones*255)),native],axis=1)
    assert np.array_equal(packed[:,columns:],native)
    Image.fromarray(packed).save(OUT/'T_GC_ExtendedBedZones.png')
    (OUT/'bed-atlas.json').write_text(json.dumps(dict(origin_m=[origin,-1250],span_m=[packed.shape[1]*cell,2017*cell],half_cell_m=cell/2,native_pixels_equal=True,scenery_only_added_columns=columns),indent=2))

if __name__=='__main__':
    if '--bed-atlas-only' in sys.argv:
        with np.load(OUT/'water-domain.npz') as z:d={k:z[k] for k in z.files}
        extended_bed_zones(np.asarray(Image.open(OUT/'T_CP_BedZones.png')),d)
    else:main()
