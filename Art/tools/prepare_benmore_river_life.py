"""Build review-owned creek geometry, ecology masks, crossings and placements."""
from pathlib import Path
import json,heapq,math
import numpy as np
from scipy.ndimage import map_coordinates,distance_transform_edt,gaussian_filter,gaussian_filter1d
from scipy.spatial import cKDTree
from PIL import Image
from bake_benmore_river_life import OUT,BASE,ROOT,BOUNDS,DX

N=2017;STEP=2500/2016
H=np.fromfile(OUT/'height_local_south_up.f32',dtype='<f4').reshape(N,N)
bake=np.load(OUT/'flow-bake.npz');x=bake['x'];y=bake['y'];bx,by=np.meshgrid(x,y)

def native(a,px,py):
    xx=(np.asarray(px)+1250)/STEP;yy=(np.asarray(py)+1250)/STEP
    return map_coordinates(a,[yy,xx],order=1,mode='nearest')

def field(a,px,py):
    return map_coordinates(a,[(np.asarray(py)-y[0])/DX,(np.asarray(px)-x[0])/DX],order=1,mode='constant')

def ground(px,py):
    xx=np.clip((np.asarray(px)+1250)/STEP,0,2015.99999);yy=np.clip((np.asarray(py)+1250)/STEP,0,2015.99999)
    i=xx.astype(int);j=yy.astype(int);s=xx-i;t=yy-j;q=H[j,i];r=H[j,i+1];v=H[j+1,i];w=H[j+1,i+1]
    return np.where(s>=t,q+(r-q)*s+(w-r)*t,q+(w-v)*s+(v-q)*t)

def exportmesh(name,xx,yy,z,mask,threshold):
    vertices=[];faces=[];lookup={}
    def vert(p):
        key=tuple(np.round(p,5))
        if key not in lookup:lookup[key]=len(vertices);vertices.append(p.tolist())
        return lookup[key]
    cells=np.argwhere(np.maximum.reduce([mask[:-1,:-1],mask[1:,:-1],mask[:-1,1:],mask[1:,1:]])>threshold)
    for j,i in cells:
        for tri in [[(j,i),(j,i+1),(j+1,i+1)],[(j,i),(j+1,i+1),(j+1,i)]]:
            polygon=[(np.array([xx[a,b],yy[a,b],z[a,b]]),mask[a,b]-threshold) for a,b in tri];clipped=[]
            for k,(p,d) in enumerate(polygon):
                q,e=polygon[(k+1)%3]
                if d>=0:clipped.append(p)
                if (d>=0)!=(e>=0):clipped.append(p+(q-p)*d/(d-e))
            if len(clipped)>2:
                ids=[vert(p) for p in clipped]
                for k in range(1,len(ids)-1):
                    t=[ids[0],ids[k],ids[k+1]]
                    if len(set(t))==3:faces.append(t)
    p=OUT/(name+'.json');p.write_text(json.dumps({'vertices':vertices,'faces':faces},separators=(',',':')))
    return {'name':name,'vertices':len(vertices),'triangles':len(faces)}

def crossing(target,bridge=False):
    dep=bake['depth'];speed=np.hypot(bake['vx'],bake['vy'])
    candidates=np.argwhere(bake['wet']&(dep>(.065 if bridge else .10))&(dep<(.8 if bridge else .34))&(bx>-1100)&(np.hypot(bx-target[0],by-target[1])<140)&(speed>.10))
    best=None
    for j,i in candidates[::3]:
        p=np.array([x[i],y[j]]);flow=np.array([bake['vx'][j,i],bake['vy'][j,i]]);flow/=np.linalg.norm(flow)
        n=np.array([-flow[1],flow[0]])
        if n[1]<0:n=-n
        d=np.linspace(-14,14,113);pts=p+n*d[:,None];wet=field(bake['wet'].astype(float),pts[:,0],pts[:,1])>.4
        if wet.sum()<3 or wet[0] or wet[-1]:continue
        lo=d[wet][0]-1.2;hi=d[wet][-1]+1.2;span=hi-lo
        if span>(9.0 if bridge else 14.0) or span<2.5:continue
        ends=p+n*np.array([lo,hi])[:,None];heights=ground(ends[:,0],ends[:,1]);crossheight=ground(pts[:,0],pts[:,1])
        grade=np.percentile(abs(np.diff(crossheight)/.25),95)
        if not bridge and (grade>.27 or abs(heights[1]-heights[0])>1.6):continue
        if bridge and abs(heights[1]-heights[0])>1.2:continue
        score=np.linalg.norm(p-target)+grade*160+span*(1.5 if bridge else 3)
        if best is None or score<best[0]:best=(score,dict(name='Footbridge' if bridge else 'Ford',center_m=[*p,float(ground(p[0:1],p[1:2])[0])],flow_direction=flow.tolist(),cross_direction=n.tolist(),ends_m=np.c_[ends,heights].tolist(),span_m=float(span),sampled_bank_grade_p95=float(grade),water_depth_m=float(dep[j,i]),flow_speed_mps=float(speed[j,i]),surface_z_m=float(bake['surface'][j,i])))
    assert best,'No suitable crossing near '+str(target)
    return best[1]

def path_between(start,end,water,spacing=2.5):
    # Route over the existing landform, favouring gentler grades; no road grading.
    lo=np.minimum(start,end)-80;hi=np.maximum(start,end)+80
    xx=np.arange(lo[0],hi[0]+spacing,spacing);yy=np.arange(lo[1],hi[1]+spacing,spacing);gx,gy=np.meshgrid(xx,yy)
    z=ground(gx,gy);wet=native(water,gx,gy)>.45
    directions=[(-1,0),(1,0),(0,-1),(0,1),(-1,-1),(-1,1),(1,-1),(1,1)]
    grades={}
    for dj,di in directions:
        heights=np.stack([ground(gx+di*spacing*t,gy+dj*spacing*t) for t in np.linspace(0,1,6)])
        grades[dj,di]=np.max(abs(np.diff(heights,axis=0)),axis=0)/(spacing*np.hypot(dj,di)/5)
    a=(int(np.argmin(abs(yy-start[1]))),int(np.argmin(abs(xx-start[0]))));b=(int(np.argmin(abs(yy-end[1]))),int(np.argmin(abs(xx-end[0]))))
    costs={a:0.};prev={};queue=[(0,a)];ny,nx=z.shape
    while queue:
        cost,k=heapq.heappop(queue)
        if k==b:break
        if cost>costs[k]:continue
        for dj,di in directions:
            q=(k[0]+dj,k[1]+di)
            if not(0<=q[0]<ny and 0<=q[1]<nx):continue
            if wet[q] and np.hypot(gx[q]-end[0],gy[q]-end[1])>12:continue
            length=spacing*np.hypot(dj,di);grade=grades[dj,di][k]
            if grade>.25:continue
            nc=cost+length*(1+80*grade**2)+max(grade-.20,0)*length*60
            if nc<costs.get(q,1e20):costs[q]=nc;prev[q]=k;heapq.heappush(queue,(nc,q))
    assert b in costs,'Approach route failed'
    k=b;points=[]
    while k!=a:points.append([xx[k[1]],yy[k[0]]]);k=prev[k]
    points.append(start);points=np.array(points[::-1]);points[-1]=end
    # Remove the routing grid's stair steps. A shortcut must be traversable at
    # sub-metre terrain samples, not just at the coarse route endpoints.
    simplified=[points[0]];index=0
    while index<len(points)-1:
        chosen=index+1
        for candidate in range(len(points)-1,index+1,-1):
            length=np.linalg.norm(points[candidate]-points[index]);line=np.linspace(points[index],points[candidate],max(3,int(length/.5)+1))
            heights=ground(line[:,0],line[:,1]);grade=np.max(abs(np.diff(heights)))/(length/(len(line)-1))
            onwater=native(water,line[:,0],line[:,1])>.45
            if grade<=.22 and not np.any(onwater&(np.linalg.norm(line-end,axis=1)>12)):
                chosen=candidate;break
        simplified.append(points[chosen]);index=chosen
    points=np.array(simplified)
    # Sample the simplified line densely before gently rounding its corners.
    arc=np.r_[0,np.cumsum(np.linalg.norm(np.diff(points,axis=0),axis=1))];s=np.linspace(0,arc[-1],int(arc[-1])+1)
    points=np.stack([np.interp(s,arc,points[:,0]),np.interp(s,arc,points[:,1])],axis=-1)
    points=gaussian_filter1d(points,.35,axis=0,mode='nearest');points[0]=start;points[-1]=end
    arc=np.r_[0,np.cumsum(np.linalg.norm(np.diff(points,axis=0),axis=1))];s=np.arange(0,arc[-1]+.01,1.)
    p=np.stack([np.interp(s,arc,points[:,0]),np.interp(s,arc,points[:,1])],axis=-1)
    return p

def run():
    report=json.loads((OUT/'flow-report.json').read_text());assert report['ok'],'Flow bake must pass first'
    yy,xx=np.meshgrid(np.linspace(-1250,1250,N),np.linspace(-1250,1250,N),indexing='ij')
    dep=field(bake['depth'],xx,yy);cover=field(bake['wet'].astype(float),xx,yy)
    raweta=field(bake['surface'],xx,yy);eta=np.maximum(raweta,H+.018)
    wet=(cover>.4)&(dep>.028);shore=distance_transform_edt(~wet)*STEP;inside=distance_transform_edt(wet)*STEP
    surface_mask=np.minimum(cover,np.clip(dep/.055,0,1))
    meshes=[exportmesh('SM_RL_Stream',xx,yy,eta,surface_mask,.40)]
    # Continue the same bake over the existing high-resolution mouth apron.
    outside=np.minimum(bake['wet'].astype(float),.5+(-1250-bx)/DX);z=bake['surface']+.018
    # The .5 contour lands exactly at X=-1250, avoiding a half-cell seam.
    meshes.append(exportmesh('SM_RL_Outlet',bx,by,z,outside,.5))
    flow=np.stack([np.clip(bake['vx']/4+.5,0,1),np.clip(bake['vy']/4+.5,0,1),np.clip(bake['depth']/2,0,1),bake['foam']],axis=-1)
    Image.fromarray(np.uint8(np.rint(flow*255))).save(OUT/'T_RL_Flow.png')
    cov=np.stack([np.clip(distance_transform_edt(~bake['wet'])*DX/16,0,1),bake['wet'],np.clip(distance_transform_edt(bake['wet'])*DX/6,0,1),np.clip(np.hypot(bake['vx'],bake['vy'])/2,0,1)],axis=-1)
    Image.fromarray(np.uint8(np.rint(cov*255))).save(OUT/'T_RL_WaterMask.png')
    ford=crossing(np.array([-680,190]));bridge=crossing(np.array([-450,395]),True)
    n=np.array(bridge['cross_direction']);ends=np.array(bridge['ends_m']);anchors=ends[:,:2]+np.array([-1,1])[:,None]*n*4.5
    bridge['approach_anchors_m']=np.c_[anchors,ground(anchors[:,0],anchors[:,1])].tolist()
    crossings=[ford,bridge]
    routes=json.loads((ROOT/'Art/Export/BenmoreRoads/road-manifest.json').read_text())['routes']
    road=np.concatenate([np.array([[p['x_m'],p['y_m']] for p in r['points']]) for r in routes]);roadtree=cKDTree(road)
    paths=[]
    for c,width in [(ford,4.5),(bridge,1.7)]:
        p=np.array(c['center_m'][:2]);n=np.array(c['cross_direction']);end=p-n*(c['span_m']/2+6)
        start=road[roadtree.query(end)[1]]
        approach=path_between(start,end,wet.astype(float));cross=np.linspace(end,p+n*(c['span_m']/2+12),45)
        pts=np.vstack([approach,cross[1:]]);height=ground(pts[:,0],pts[:,1]);length=np.linalg.norm(np.diff(pts,axis=0),axis=1)
        grade=abs(np.diff(height)/np.maximum(length,.001))
        paths.append({'name':c['name']+'_Approach','width_m':width,'points_m':np.c_[pts,height].tolist(),'grade_p95':float(np.percentile(grade,95)),'grade_max':float(grade.max())})
    pathmask=np.zeros_like(H)
    for path in paths:
        pts=np.array(path['points_m'])[:,:2];d=cKDTree(pts).query(np.c_[xx.ravel(),yy.ravel()])[0].reshape(H.shape)
        t=np.clip((d-path['width_m']/2)/1.1,0,1);pathmask=np.maximum(pathmask,1-t*t*(3-2*t))
    patch=.5+.5*np.sin(xx*.043+np.sin(yy*.017)*2)*np.cos(yy*.033-xx*.012)
    cluster=np.zeros_like(H)
    centers=[(-750,140,48),(-620,240,40),(-495,327,42),(-390,460,35),(-336,560,38)]
    for cx,cy,r in centers:cluster=np.maximum(cluster,np.exp(-((xx-cx)**2+(yy-cy)**2)/(r*r)))
    mud=(1-np.clip(shore/7,0,1))*(.2+.8*cluster)*np.clip((patch-.3)*1.9,0,1)
    gravel=(1-np.clip(shore/10,0,1))*(.45+.55*(1-patch))
    gravel=np.maximum(gravel,pathmask*.88)
    # Damp wheel approaches: irregular local pockets, not a whole muddy river.
    for sign in [-1,1]:
        p=np.array(ford['center_m'][:2])+sign*np.array(ford['cross_direction'])*(ford['span_m']/2+3)
        mudd=np.exp(-(((xx-p[0])/6)**2+((yy-p[1])/5)**2))*.8
        mud=np.maximum(mud,mudd)
    keep=np.clip((shore-1.1)/3.4,0,1)*(1-pathmask)
    eco=np.stack([gravel,mud,keep,pathmask],axis=-1)
    Image.fromarray(np.uint8(np.rint(np.clip(eco,0,1)*255))).save(OUT/'T_RL_Ecology.png')
    original=np.asarray(Image.open(BASE.parent/'BenmoreVegetation/T_Benmore_VegetationMask.png'))
    Image.fromarray(np.uint8(np.rint(original*keep[...,None]))).save(OUT/'T_RL_Vegetation.png')
    shore.astype('<f4').tofile(OUT/'shore_distance.f32');pathmask.astype('<f4').tofile(OUT/'path_mask.f32')
    rng=np.random.default_rng(81026);placements=[];used=[]
    # Trees grow in a few groups with long open views between them.
    young='/Game/GrandTour/Demo/BenmoreRoads/Scenery/SM_Willow_Young'
    variants=[young,'/Game/GrandTour/Demo/BenmoreRoads/Scenery/SM_Willow_Broad','/Game/GrandTour/Demo/BenmoreRoads/Scenery/SM_Willow_Weathered','/Game/GrandTour/Demo/BenmoreRoads/Scenery/SM_Willow_Windswept']
    candidates=np.argwhere((shore>4)&(shore<16)&(cluster>.20)&(pathmask<.02)&(H<65))
    for k in range(31):
        for attempt in range(2500):
            j,i=candidates[rng.integers(len(candidates))];p=np.array([xx[j,i],yy[j,i]])
            if used and min(np.linalg.norm(p-q) for q in used)<rng.uniform(5,9):continue
            used.append(p);s=float(rng.uniform(.7,1.10))
            placements.append(dict(kind='tree',mesh=variants[k%4],xy_m=p.tolist(),scale=[s,s,s*rng.uniform(.9,1.1)],yaw_deg=float(rng.uniform(0,360)),sink_cm=8));break
        else:raise RuntimeError('Tree placement exhausted')
    old=json.loads((BASE/'integration/bank-placements.json').read_text())
    for key,count,min_d,max_d,kind in [('Benmore_River_Art_rocks',100,3.5,9,'rock'),('Benmore_River_GravelBars',1400,.7,7,'gravel'),('Benmore_River_Art_shrubs',240,3,15,'shrub'),('Benmore_River_Art_tussocks',2400,2,13,'tussock')]:
        rows=old[key];pool=[r for r in rows if r['transforms']]
        candidates=np.argwhere((shore>min_d)&(shore<max_d)&(cluster>.08)&(pathmask<.02)&(H<90)&(xx>-1180))
        for k in range(count):
            j,i=candidates[rng.integers(len(candidates))];row=pool[k%len(pool)];tr=row['transforms'][k%len(row['transforms'])]
            s=np.array(tr['scale'])*rng.uniform(.75,1.15)
            placements.append(dict(kind=kind,mesh=row['mesh'],materials=row['materials'],xy_m=[float(xx[j,i]+rng.uniform(-.35,.35)),float(yy[j,i]+rng.uniform(-.35,.35))],scale=s.tolist(),yaw_deg=float(rng.uniform(0,360)),sink_cm=7))
    (OUT/'placements.json').write_text(json.dumps(placements,separators=(',',':')))
    cameras=[]
    for c,offset in [(ford,(12,-15,3)),(bridge,(12,-15,4))]:
        p=np.array(c['center_m']);pos=p+offset;pos[2]=float(ground(pos[0:1],pos[1:2])[0])+offset[2]
        cameras.append(dict(name=c['name'],position_m=pos.tolist(),target_m=(p+[0,0,.5]).tolist(),fov=70))
    p=np.array(ford['center_m']);pos=p+[105,-65,48];pos[2]=max(pos[2],float(ground(pos[0:1],pos[1:2])[0])+35)
    cameras.append(dict(name='River_Reach',position_m=pos.tolist(),target_m=(p+[80,80,8]).tolist(),fov=74))
    cameras+=json.loads((BASE/'integration/assets.json').read_text())['cameras'][-1:]
    meta=dict(ok=True,flow_report='flow-report.json',height_sha256=report['height_sha256'],meshes=meshes,crossings=crossings,paths=paths,cameras=cameras,counts={kind:sum(p['kind']==kind for p in placements) for kind in ['tree','rock','gravel','shrub','tussock']},flow_bounds_m=BOUNDS,flow_grid_m=DX,flow_shape=list(bake['bed'].shape))
    (OUT/'assets.json').write_text(json.dumps(meta,indent=2));print(json.dumps({k:meta[k] for k in ['ok','counts','crossings']},indent=2))

if __name__=='__main__':run()
