"""NP3 (docs/NATIVE_PLANT_KIT_PLAN.md): the native plant lineup level /Game/GrandTour/ArtTests/NativePlants/L_NativePlants.

A flat 300 x 300 m dark peat ground (the map-owned MI_NZ_Peat, built from MI_Env_Bog's parent) with the project's daylight (tussock_style_lighting)
overridden by the NP4c values below, and the drivable GTRunGameMode.
Layout in metres, x east (UE +X), y north (UE +Y), origin at the ground centre:
  Row 1 (y 0): the 20 meshes at true scale, 8 m apart from x -76.
  Row 2 (y -30): each mesh three times at scales .85/1/1.15, yaws 0/120/240, 3 m apart.
  Bush assembly (x 0..40, y 50..90): build_native_bush.py's assembly rebuilt as instances (same seed, track and draws).
  Edge assembly (front y 56, x 60..100): the bush wall from the paddock (build_native_open.py's assembly_edge as briefed).
S1 (docs/SOUTHLAND_ASSET_PLAN.md), the 15 bush-floor and river meshes:
  Row 3 (y 6): the 15 S1 meshes at true scale, centred on x 0, 1 m between bounds.
  Bush stand additions: Log_A x2, Log_B x3, Stump_A x2 (crown ferns cleared .5 m around them) and MossHummock A/B x12 among the ferns, by a seeded search that
    keeps clear of trunks, the track and the cameras; the first Log_B is the NZ_FloorLogs subject (camera 1.6 m, 4 m from its side, south of it).
  Riverbed strip (x -7..-1, y 53..77, 24 x 6 m, on the peat ground at the stand's open west side): CobbleBar x3 end to end, Cobble clusters x8, Boulder A x2,
    Boulder B x3, Driftwood x2, LogJam at the north end, Kiokio A x6 / B x4 along the east edge, TreeFern_A x2 behind them; NZ_Riverbed looks up it from 8 m back at 1.2 m.
S2b (docs/SOUTHLAND_ASSET_PLAN.md), the 15 verge meshes (manifest set 'verge'):
  Row 4 (y 12, 6 m behind row 3): the 15 verge meshes at true scale, centred on x 0, 1 m between bounds.
  Bush stand litter: into NZ_BushFerns TwigLitter A/B x120, RootTangle x25 (trunk bases) and LeafLitter x60, placed on a 0.25 m coverage grid of what the stand's trunks,
    logs, stumps, hummocks and crown ferns already hide; holes go first (largest bare square first) until no 1 m square of peat is bare anywhere in x 0..40, y 50..90.
  Paddock edge band (x 60..100, y 44..50, 6 m in front of the coprosma band): Gorse_A x6, Gorse_B x4, Broom x4 in four thickets, VergeTussock_A x40 / _B x30 in drifts,
    Rush_A/B x12 in one 4 x 4 m dip (x 77..81, y 44.4..48.4; the ground is a flat slab, so the dip is a planting area), Thistle x5.
  Shelterbelt (the bush stand's open west side, row on x -40 running north from y 35, 40 m from the stand): Radiata_Mature x6 at 7 m, Macrocarpa x2, Radiata_Young x3 at the
    north end, VergeTussock x20 at its foot. Collision on the trees only (BlockAll); everything else NoCollision.
  Cameras NZ_DenseFloor (on foot 1.6 m, in the stand, aimed at the ground 3 m ahead), NZ_EdgeBand (1.2 m, 10 m out from the band), NZ_Shelterbelt (1.6 m, 25 m along the row).
Meshes with manifest hulls > 0 block (BlockAll); every other mesh has no collision.
Run through Art/native_plants.ps1 -Mode Lineup after -Mode Import.
"""
import unreal as u, json, math, random, traceback, sys
from pathlib import Path
ROOT=Path(u.Paths.project_dir()).resolve(); OUT=ROOT/'Art/Export/NativePlants/v01'
sys.path.insert(0,str(ROOT/'Art/Unreal'))
SRC='/Game/GrandTour/Environment/NativePlants/v01'; DEST='/Game/GrandTour/ArtTests/NativePlants'; LEVEL=DEST+'/L_NativePlants'
ORDER=['Beech_Mature','Beech_Pole','Beech_Edge','DeadSpar','CrownFern_A','CrownFern_B','CrownFern_C','TreeFern_A','TreeFern_B','TreeFern_Young',
       'Harakeke_A','Harakeke_B','Coprosma_A','Coprosma_B','Matagouri_A','Matagouri_B','TiKouka_A','TiKouka_B','Kanuka_A','Kanuka_B']
# S1: the 15 floor and river meshes (manifest set 'floor'), imported by import_native_plants.py
FLOOR=['Kiokio_A','Kiokio_B','Log_A','Log_B','Stump_A','MossHummock_A','MossHummock_B','Cobble_Cluster_S','Cobble_Cluster_M','Cobble_Cluster_L','CobbleBar',
       'Driftwood_A','LogJam','Boulder_A','Boulder_B']
# S2b: the 15 verge meshes (manifest set 'verge'), imported by import_native_plants.py
VERGE=['Gorse_A','Gorse_B','Broom_A','Rush_A','Rush_B','Thistle_A','VergeTussock_A','VergeTussock_B','Radiata_Young','Radiata_Mature','Macrocarpa',
       'TwigLitter_A','TwigLitter_B','RootTangle_A','LeafLitter_A']
ALL=ORDER+FLOOR+VERGE
TAG='NativePlants'
eal=u.EditorAssetLibrary; les=u.get_editor_subsystem(u.LevelEditorSubsystem); act=u.get_editor_subsystem(u.EditorActorSubsystem)
report={'ok':False,'level':LEVEL}

def spawn(cls,label,pos_m,rot=None):
    a=act.spawn_actor_from_class(cls,u.Vector(pos_m[0]*100,pos_m[1]*100,pos_m[2]*100),rot or u.Rotator())
    a.set_actor_label(label); return a

def look(frm,to):
    dx,dy,dz=to[0]-frm[0],to[1]-frm[1],to[2]-frm[2]
    return u.Rotator(pitch=math.degrees(math.atan2(dz,math.hypot(dx,dy))),yaw=math.degrees(math.atan2(dy,dx)))

def xt(y):   # build_native_bush.py's meandering track, x offset in metres at track distance y
    return 2.8*(math.sin(y/8.5+.7)-math.sin(.7))+.5*(math.sin(y/3.1+2.1)-math.sin(2.1))

def at_centre(mesh,cx,cy,yaw_deg,sc):
    """The actor origin (x, y metres) that puts the mesh bounds' centre at (cx, cy) for a yaw and scale."""
    b=mesh.get_bounds(); ox,oy=b.origin.x/100*sc,b.origin.y/100*sc; c,s=math.cos(math.radians(yaw_deg)),math.sin(math.radians(yaw_deg))
    return cx-(ox*c-oy*s),cy-(ox*s+oy*c)

def long_axis_offset(mesh):
    """Degrees from the mesh's local +X to its long horizontal axis (0 when it is longer along X, else 90)."""
    e=mesh.get_bounds().box_extent; return 0. if e.x>=e.y else 90.

class Fp:
    """A mesh's bounds as an oriented rectangle on the ground (metres) for an actor origin, yaw and scale."""
    def __init__(self,mesh,x,y,yaw_deg,sc):
        b=mesh.get_bounds(); ox,oy=b.origin.x/100*sc,b.origin.y/100*sc
        self.c,self.s=math.cos(math.radians(yaw_deg)),math.sin(math.radians(yaw_deg))
        self.cx=x+ox*self.c-oy*self.s; self.cy=y+ox*self.s+oy*self.c; self.hx=b.box_extent.x/100*sc; self.hy=b.box_extent.y/100*sc
    def dist(self,px,py):
        dx,dy=px-self.cx,py-self.cy; lx=dx*self.c+dy*self.s; ly=-dx*self.s+dy*self.c
        return math.hypot(max(abs(lx)-self.hx,0.),max(abs(ly)-self.hy,0.))
    def points(self):
        n=int(2*self.hx/.5)+2; m=int(2*self.hy/.5)+2; out=[]
        for i in range(n):
            for j in range(m):
                lx=self.hx*(2*i/(n-1)-1); ly=self.hy*(2*j/(m-1)-1)
                out.append((self.cx+lx*self.c-ly*self.s,self.cy+lx*self.s+ly*self.c))
        return out
    def gap(self,o):
        return min(min(o.dist(*p) for p in self.points()),min(self.dist(*p) for p in o.points()))

class Group:
    """Per-mesh instance transforms for one actor; flushed through GTVegetationSubsystem.add_tagged_instances."""
    def __init__(self):self.items={}; self.log=[]
    def put(self,short,x,y,yaw_deg,scale,roll=0.,pitch=0.):
        self.items.setdefault(short,[]).append(u.Transform(u.Vector(x*100,y*100,0),u.Rotator(roll=roll,pitch=pitch,yaw=yaw_deg),u.Vector(scale,scale,scale)))
        self.log.append((short,x,y,yaw_deg,scale))   # S2b: the actor origin (metres), kept so the litter pass can see what the stand's floor already hides

def flush(label,group,profile,meshes):
    a=spawn(u.Actor,label,(0,0,0)); counts={}
    for short in ALL:
        tr=group.items.get(short)
        if not tr:continue
        c=u.GTVegetationSubsystem.add_tagged_instances(a,meshes[short],tr,TAG,profile,True)
        assert c,(label,short)
        c.set_cull_distances(0,0); c.set_editor_property('affect_distance_field_lighting',False); c.set_editor_property('receives_decals',False)
        assert c.get_instance_count()==len(tr),(label,short,c.get_instance_count(),len(tr))
        counts[short]=len(tr)
    return dict(actor=label,collision=profile,instances=sum(counts.values()),per_mesh=counts)

TRUNK_R={'Beech_Pole':.14,'Beech_Mature':.4,'Beech_Edge':.34,'DeadSpar':.3,'TreeFern_A':.25,'TreeFern_B':.25,'TreeFern_Young':.45}

def bush_floor(meshes,blocking,placed,stand,ferns,keep_clear):
    """S1: Log_A x2, Log_B x3, Stump_A x2 and MossHummock A/B x12 into the bush stand (world metres; placed = [(name, x, y)] of the stand's trunks).
    A seeded random search keeps each footprint inside the stand, 1.5 m off the track, clear of every trunk and of the camera and start points,
    and .4 m off the other items. Returns (info, clear): clear(x, y) says a crown fern there is cleared (.5 m around logs and stumps, .3 m around hummocks)."""
    rng=random.Random(52710+4999); trunks=[(x,y,TRUNK_R[n]) for n,x,y in placed]; fps=[]; clearing=[]; info=dict(placed={},missed=[])
    def track_x(y):return 20+xt(y-50)
    def fits(fp):
        for px,py in fp.points():
            if not (1.5<px<38.5 and 51.5<py<88.5) or abs(px-track_x(py))<1.5:return False
        if any(fp.dist(tx,ty)<tr+.15 for tx,ty,tr in trunks) or any(fp.dist(kx,ky)<3. for kx,ky in keep_clear):return False
        return all(fp.gap(o)>.4 for o in fps)
    def candidates(short,axis=None,tries=800):
        mesh=meshes[short]
        for _ in range(tries):
            sc=rng.uniform(.92,1.08); ang=rng.uniform(0,360) if axis is None else axis()-long_axis_offset(mesh)
            ax,ay=at_centre(mesh,rng.uniform(3,37),rng.uniform(53,87),ang,sc); fp=Fp(mesh,ax,ay,ang,sc)
            if fits(fp):yield fp,ax,ay,ang,sc
    def commit(short,fp,ax,ay,ang,sc):
        (stand if short in blocking else ferns).put(short,ax,ay,ang,sc); fps.append(fp)
        m=.3 if short.startswith('MossHummock') else .5; clearing.append(lambda x,y,fp=fp,m=m:fp.dist(x,y)<m); info['placed'].setdefault(short,[]).append([round(fp.cx,2),round(fp.cy,2),round(ang,1),round(sc,3)])
        return fp
    def put(short,axis=None):
        for fp,ax,ay,ang,sc in candidates(short,axis):return commit(short,fp,ax,ay,ang,sc)
        info['missed'].append(short); return None
    def camera_for(hero):
        """4 m from the log's surface, south of it first and then swinging round it, on a spot that is off every trunk and has a clear line of sight."""
        d0=(-hero.s,hero.c) if hero.hx>=hero.hy else (hero.c,hero.s)
        if d0[1]>0:d0=(-d0[0],-d0[1])
        for delta in (0,15,-15,30,-30,45,-45,60,-60):
            a=math.radians(delta); dx=d0[0]*math.cos(a)-d0[1]*math.sin(a); dy=d0[0]*math.sin(a)+d0[1]*math.cos(a)
            r=.5
            while hero.dist(hero.cx+r*dx,hero.cy+r*dy)<4. and r<20:r+=.05
            px,py=hero.cx+r*dx,hero.cy+r*dy
            if not (2<px<38 and 52<py<88) or abs(px-track_x(py))<1.:continue
            if any(math.hypot(px-tx,py-ty)<tr+.7 for tx,ty,tr in trunks) or any(math.hypot(px-kx,py-ky)<2. for kx,ky in keep_clear):continue
            line=[(px+(hero.cx-px)*t/20,py+(hero.cy-py)*t/20) for t in range(0,18)]
            if any(math.hypot(qx-tx,qy-ty)<tr+.3 for qx,qy in line for tx,ty,tr in trunks):continue
            return dict(pos=[round(px,2),round(py,2)],target=[round(hero.cx,2),round(hero.cy,2)],swing_deg=delta,surface_distance_m=round(hero.dist(px,py),2))
        return None
    def view_cost(cam,hero):
        """Trunks in a 72 degree wedge from the camera toward the log (up to 14 m): big and near ones cost most, so the view keeps its gaps and its sky."""
        ax=math.atan2(hero.cy-cam['pos'][1],hero.cx-cam['pos'][0]); cost=0.
        for tx,ty,tr in trunks:
            dx,dy=tx-cam['pos'][0],ty-cam['pos'][1]; d=math.hypot(dx,dy)
            if .1<d<14. and abs((math.atan2(dy,dx)-ax+math.pi)%(2*math.pi)-math.pi)<math.radians(36):cost+=tr/max(d,1.)
        return cost
    # the NZ_FloorLogs subject first: a Log_B lying roughly east-west, the cheapest view of 40 candidate spots that each have an open camera spot 4 m from the log
    best=None
    for fp,ax,ay,ang,sc in candidates('Log_B',axis=lambda:rng.uniform(-30,30),tries=3000):
        cam=camera_for(fp)
        if not cam:continue
        cost=view_cost(cam,fp)
        if best is None or cost<best[0]:best=(cost,fp,ax,ay,ang,sc,cam)
        info.setdefault('hero_candidates',0); info['hero_candidates']+=1
        if info['hero_candidates']>=40:break
    hero=None; cam=None
    if best:
        cost,fp,ax,ay,ang,sc,cam=best; hero=commit('Log_B',fp,ax,ay,ang,sc); keep_clear.append(tuple(cam['pos'])); info['hero_view_cost']=round(cost,3)
        # a sight lane: crown ferns are cleared 0.5 m either side of the line from the camera to the log, and 0.6 m round the camera, so the log is seen and not just its stubs
        (x0,y0),(x1,y1)=cam['pos'],(hero.cx,hero.cy); L2=(x1-x0)**2+(y1-y0)**2
        def lane(x,y):
            t=max(0.,min(1.,((x-x0)*(x1-x0)+(y-y0)*(y1-y0))/L2)); return math.hypot(x-(x0+t*(x1-x0)),y-(y0+t*(y1-y0)))<.5 or math.hypot(x-x0,y-y0)<.6
        clearing.append(lane)
    else:info['missed'].append('Log_B (hero)')
    for short in ['Log_A','Log_A','Log_B','Log_B','Stump_A','Stump_A']:put(short)
    for k in range(12):put('MossHummock_A' if k%2==0 else 'MossHummock_B')
    info['hero_camera']=cam; info['hero']=dict(centre=[round(hero.cx,2),round(hero.cy,2)],half=[round(hero.hx,2),round(hero.hy,2)]) if hero else None
    def clear(x,y):return any(f(x,y) for f in clearing)
    return info,clear

def river_strip(meshes,blocking,placed):
    """S1: the dry riverbed strip, 24 x 6 m: u along +Y from the south end (world y 53 + u), v across (world x -4 + v), the stand's open west side.
    LogJam at the north end, CobbleBar x3 end to end up the middle, Kiokio A x6 / B x4 along the east edge, TreeFern_A x2 behind them,
    Driftwood x2, Boulder A x2 / B x3, Cobble clusters x8 (L x2, M x3, S x3). Returns (solid group, scatter group, info)."""
    rng=random.Random(52710+5999); X0,Y0,LEN=-4.,53.,24.; solid=Group(); scatter=Group(); fps=[]; info=dict(placed={},missed=[],strip=dict(x=[X0-3,X0+3],y=[Y0,Y0+LEN]))
    trunks=[(x,y,TRUNK_R[n]) for n,x,y in placed]
    def commit(short,ax,ay,ang,sc):
        (solid if short in blocking else scatter).put(short,ax,ay,ang,sc)
        info['placed'].setdefault(short,[]).append([round(ax,2),round(ay,2),round(ang,1),round(sc,3)])
    def put_at(short,u,v,axis,sc=1.):
        mesh=meshes[short]; ang=axis-long_axis_offset(mesh); ax,ay=at_centre(mesh,X0+v,Y0+u,ang,sc); commit(short,ax,ay,ang,sc); return Fp(mesh,ax,ay,ang,sc)
    def inside(fp):return all(-3.<=px-X0<=3. and 0.<=py-Y0<=LEN for px,py in fp.points())
    def free(short,urange,vrange,axis,margin=.3,scale=(.95,1.05),tries=600):
        mesh=meshes[short]
        for _ in range(tries):
            sc=rng.uniform(*scale); u,v=rng.uniform(*urange),rng.uniform(*vrange); ang=axis()-long_axis_offset(mesh)
            ax,ay=at_centre(mesh,X0+v,Y0+u,ang,sc); fp=Fp(mesh,ax,ay,ang,sc)
            if inside(fp) and all(fp.gap(o)>margin for o in fps):
                commit(short,ax,ay,ang,sc); fps.append(fp); return fp
        info['missed'].append(short); return None
    # the jam spans the strip's north end, long axis across (east-west)
    fps.append(put_at('LogJam',21.8,0.,0.))
    # three bars end to end up the middle, long axis north, each a hair into the last
    u=.8
    for v in (0.,-.25,.1):
        e=meshes['CobbleBar'].get_bounds().box_extent; length=2*max(e.x,e.y)/100
        fps.append(put_at('CobbleBar',u+length/2,v,90.+rng.uniform(-5,5))); u+=length-.12
    info['bars_end_u']=round(u,2)
    # kiokio along the east edge, 2 m apart with jitter, six A and four B shuffled
    kinds=['Kiokio_A']*6+['Kiokio_B']*4; rng.shuffle(kinds)
    for k,short in enumerate(kinds):
        fps.append(put_at(short,1.6+2.15*k+rng.uniform(-.4,.4),rng.uniform(2.1,2.9),rng.uniform(0,360),rng.uniform(.92,1.08)))
    # tree ferns behind the kiokio, between the stand's first trunks, at least 5 m apart
    tf=[]
    for _ in range(400):
        if len(tf)==2:break
        u,v=rng.uniform(5,19),rng.uniform(3.2,4.4); x,y=X0+v,Y0+u
        if any(math.hypot(x-tx,y-ty)<tr+.9 for tx,ty,tr in trunks) or any(abs(u-q)<5. for q,_ in tf):continue
        tf.append((u,v))
    if len(tf)<2:info['missed'].append('TreeFern_A behind the kiokio')
    for u,v in tf:put_at('TreeFern_A',u,v,rng.uniform(0,360),rng.uniform(.95,1.05))
    info['tree_ferns_behind']=[[round(X0+v,2),round(Y0+u,2)] for u,v in tf]
    for _ in range(2):free('Driftwood_A',(8.,19.),(-2.2,1.),lambda:90.+rng.uniform(-25,25),margin=.4)
    for short in ['Cobble_Cluster_L']*2:free(short,(.5,20.),(-2.7,1.8),lambda:rng.uniform(0,360),margin=.25,scale=(.9,1.1))
    for _ in range(2):free('Boulder_A',(1.,20.),(-2.6,1.6),lambda:rng.uniform(0,360),margin=.3,scale=(.9,1.1),tries=1500)
    for _ in range(3):free('Boulder_B',(1.,20.),(-2.6,1.6),lambda:rng.uniform(0,360),margin=.3,scale=(.9,1.1),tries=1500)
    for short in ['Cobble_Cluster_M']*3+['Cobble_Cluster_S']*3:free(short,(.5,20.),(-2.7,1.8),lambda:rng.uniform(0,360),margin=.25,scale=(.9,1.1))
    return solid,scatter,info

def bush_assembly(blocking,cam,meshes):
    """build_native_bush.py::assembly, Blender (bx, by) -> (bx + 20, by + 50); the 70 m ring is not part of NP3."""
    rng=random.Random(52710+999); stand=Group(); ferns=Group(); placed=[]   # placed: (mesh, world x, world y) of each trunk, for the S1 floor items
    def put(short,bx,by,yaw,sc,tilt=(0.,0.)):
        g=stand if short in blocking else ferns
        g.put(short,bx+20,by+50,math.degrees(yaw),sc,math.degrees(tilt[0]),math.degrees(tilt[1]))
    trunks=[]; cell=2.4; nc=int(40/cell); skipped=0
    for i in range(nc+1):
        for j in range(nc+1):
            x=-20+cell*(i+.5)+rng.uniform(-.45,.45); y=cell*(j+.5)+rng.uniform(-.45,.45)
            r=rng.random(); yaw=rng.uniform(0,math.tau); sc=rng.uniform(.9,1.1)
            if abs(x)>20 or y>40 or abs(x-xt(y))<1.25:continue
            if (x+20-cam[0])**2+(y+50-cam[1])**2<1.0:skipped+=1; continue   # keep the TowardSun camera out of a trunk
            name='Beech_Pole' if r<.70 else 'Beech_Mature' if r<.90 else 'Beech_Edge' if r<.97 else 'DeadSpar'
            put(name,x,y,yaw,sc); trunks.append((x,y)); placed.append((name,x+20,y+50))
    tfs=['TreeFern_A','TreeFern_B','TreeFern_Young']; tf=0; tries=0
    while tf<12 and tries<5000:
        tries+=1
        if tf<3:y=rng.uniform(7,10); x=xt(y)+rng.choice((-1,1))*rng.uniform(1.3,2.4)
        else:x=rng.uniform(-19,19); y=rng.uniform(1,39)
        if abs(x-xt(y))<1.25 or any((x-a)**2+(y-b)**2<1.0 for a,b in trunks):continue
        put(tfs[tf%3],x,y,rng.uniform(0,math.tau),rng.uniform(.9,1.1)); trunks.append((x,y)); placed.append((tfs[tf%3],x+20,y+50)); tf+=1
    # S1 floor items go in before the crown ferns, which are then cleared around them (every fern draw below happens before its skip tests, so the stream is unchanged)
    floor_info,cleared=bush_floor(meshes,blocking,placed,stand,ferns,[(20,60),(cam[0],cam[1]),(20,44)])
    fern_cleared=0
    crowns=['CrownFern_A','CrownFern_B','CrownFern_C']; step=math.sqrt(.6); m=int(40/step)
    for i in range(m):
        for j in range(m):
            x=-20+step*(i+.5)+rng.uniform(-.35,.35)*step; y=step*(j+.5)+rng.uniform(-.35,.35)*step
            pick=rng.random(); yaw=rng.uniform(0,math.tau); sc=rng.uniform(.8,1.2)
            tl=math.radians(rng.uniform(0,10)); ta=rng.uniform(0,math.tau)
            if abs(x-xt(y))<.85 or any((x-a)**2+(y-b)**2<.35**2 for a,b in trunks):continue
            if cleared(x+20,y+50):fern_cleared+=1; continue
            put(crowns[0 if pick<.30 else 1 if pick<.75 else 2],x,y,yaw,sc,(tl*math.cos(ta),tl*math.sin(ta)))
    floor_info['crown_ferns_cleared']=fern_cleared
    return stand,ferns,dict(tree_ferns=tf,trunks_skipped_for_camera=skipped),floor_info,placed

def edge_assembly(blocking):
    """The bush wall seen from the paddock: 40 m front at y 56, coprosma band y 50..56, stand behind y 58..102."""
    rng=random.Random(52710+1999); stand=Group(); scrub=Group(); trunks=[]
    def put(short,x,y,yaw_deg,sc=1.):
        (stand if short in blocking else scrub).put(short,x,y,yaw_deg,sc)
        if short in blocking:trunks.append((x,y))
    # the front: build_native_open.py's ten trees (2 edge, 6 pole, 1 mature, 1 dead spar) at x 80 + bx; edge trees lean toward the paddock (-y)
    front=[('Beech_Edge',-13.),('Beech_Pole',-17.5),('Beech_Pole',-8.5),('DeadSpar',-4.5),('Beech_Pole',-1.),('Beech_Mature',3.5),
           ('Beech_Pole',8.),('Beech_Edge',12.),('Beech_Pole',15.5),('Beech_Pole',18.5)]
    for name,bx in front:
        yaw=-90+rng.uniform(-23,23) if name=='Beech_Edge' else rng.uniform(0,360)
        put(name,80+bx+rng.uniform(-.8,.8),rng.uniform(55,57),yaw,rng.uniform(.92,1.06))
    put('TreeFern_B',73.5,54.6,rng.uniform(0,360))
    # the stand behind: Beech_Pole/Mature 72/28 at 2.5 m, jittered .6 m, wider than the front so the wall closes the frame
    step=2.5; n=0
    for i in range(int(65/step)+1):
        for j in range(int(44/step)+1):
            x=47.5+step*i+rng.uniform(-.6,.6); y=58+step*j+rng.uniform(-.6,.6)
            pick=rng.random(); yaw=rng.uniform(0,360); sc=rng.uniform(.9,1.1)
            put('Beech_Pole' if pick<.72 else 'Beech_Mature',x,y,yaw,sc); n+=1
    # crown ferns in the margin rows (B/C 60/40 at 1.1 m)
    fs=1.1; ferns=0
    for i in range(int(50/fs)+1):
        for j in range(int(7/fs)+1):
            x=55+fs*i+rng.uniform(-.35,.35); y=56+fs*j+rng.uniform(-.35,.35)
            pick=rng.random(); yaw=rng.uniform(0,360); sc=rng.uniform(.85,1.15)
            if any((x-a)**2+(y-b)**2<.35**2 for a,b in trunks):continue
            put('CrownFern_B' if pick<.6 else 'CrownFern_C',x,y,yaw,sc); ferns+=1
    # coprosma band y 50..56 at about 1 per 2 m2 (A/B 55/45)
    cs=math.sqrt(2.); cop=0
    for i in range(int(40/cs)+1):
        for j in range(int(6/cs)+1):
            x=60+cs*(i+.5)+rng.uniform(-.45,.45); y=50+cs*(j+.5)+rng.uniform(-.45,.45)
            pick=rng.random(); yaw=rng.uniform(0,360); sc=rng.uniform(.85,1.15)
            if x>100 or y>56:continue
            put('Coprosma_A' if pick<.55 else 'Coprosma_B',x,y,yaw,sc); cop+=1
    put('Harakeke_B',75.,48.8,rng.uniform(0,360)); put('Harakeke_B',87.5,49.4,rng.uniform(0,360))
    put('Kanuka_B',60.,53.,rng.uniform(0,360))
    put('Matagouri_B',105.,45.,rng.uniform(0,360)); put('TiKouka_A',110.,52.,rng.uniform(0,360))
    return stand,scrub,dict(stand_trees=n,margin_crown_ferns=ferns,coprosma=cop)

# ---- S2b (docs/SOUTHLAND_ASSET_PLAN.md): bush-stand litter, paddock edge band, shelterbelt, owner cameras ------------------------------------------------------

class Cover:
    """A 0.25 m coverage grid over [x0, x1] x [y0, y1] (metres): the ground that items hide, and the largest all-bare square that is left."""
    def __init__(self,x0,y0,x1,y1,cell=.25):
        self.x0,self.y0,self.cell=x0,y0,cell; self.nx=int(round((x1-x0)/cell)); self.ny=int(round((y1-y0)/cell))
        self.g=[bytearray(self.nx) for _ in range(self.ny)]
    def cells(self,cx,cy,yaw_deg,hx,hy,rect=False):
        """The (row, column) of every cell whose centre is inside the oriented rectangle (rect) or its inscribed ellipse."""
        c,s=math.cos(math.radians(yaw_deg)),math.sin(math.radians(yaw_deg)); r=math.hypot(hx,hy); q=self.cell
        i0=max(0,int((cx-r-self.x0)/q)); i1=min(self.nx-1,int((cx+r-self.x0)/q)); j0=max(0,int((cy-r-self.y0)/q)); j1=min(self.ny-1,int((cy+r-self.y0)/q))
        for j in range(j0,j1+1):
            py=self.y0+(j+.5)*q-cy
            for i in range(i0,i1+1):
                px=self.x0+(i+.5)*q-cx; lx=px*c+py*s; ly=-px*s+py*c
                if (abs(lx)<=hx and abs(ly)<=hy) if rect else (lx/hx)**2+(ly/hy)**2<=1.:yield j,i
    def mark(self,cx,cy,yaw_deg,hx,hy,rect=False):
        for j,i in self.cells(cx,cy,yaw_deg,hx,hy,rect):self.g[j][i]=1
    def bare_in(self,cx,cy,yaw_deg,hx,hy,rect=False):
        return sum(1 for j,i in self.cells(cx,cy,yaw_deg,hx,hy,rect) if not self.g[j][i])
    def bare_cells(self):return sum(self.nx-sum(row) for row in self.g)
    def bare_square(self):
        """(side in cells, centre x, centre y metres) of the largest square of bare cells."""
        prev=[0]*(self.nx+1); best=(0,0,0)
        for j in range(self.ny):
            cur=[0]*(self.nx+1); row=self.g[j]
            for i in range(self.nx):
                if not row[i]:
                    k=min(prev[i],prev[i+1],cur[i])+1; cur[i+1]=k
                    if k>best[0]:best=(k,i,j)
            prev=cur
        k,i,j=best
        return k,self.x0+(i+1-k/2)*self.cell,self.y0+(j+1-k/2)*self.cell

def bush_litter(meshes,stand,ferns,placed):
    """S2b: TwigLitter A/B x120, RootTangle x25 and LeafLitter x60 into the bush stand's NZ_BushFerns group, on top of every existing instance.
    A 0.25 m grid over x 0..40, y 50..90 first records what is hidden already: trunks as circles of their base radius, logs and stumps as their oriented bounds, hummocks
    as an ellipse .9 of their bounds, crown ferns as an ellipse .6 of their bounds (the first capture at .85 left visible flat peat), twig litter .5, leaf litter and roots .6. RootTangle goes to trunk bases (Beech_Mature,
    Beech_Edge and DeadSpar first, then poles). Twig and leaf pieces then go to the centre of the largest bare square, again and again, until no square of 1 m is bare;
    what is left of the quota lands where it hides the most bare ground (best of 8 random spots), leaf litter favouring trunk bases. Own seed: the rest of the stand is unchanged."""
    rng=random.Random(52710+7001); X0,Y0,X1,Y1=0.,50.,40.,90.; cov=Cover(X0,Y0,X1,Y1)
    trunks=[(x,y,TRUNK_R[n]) for n,x,y in placed]; info=dict(placed={},quota=dict(twig=120,leaf=60,root=25))
    def shape(short):
        if short.startswith(('Log_','Stump_')):return True,1.
        if short.startswith('MossHummock'):return False,.9
        if short.startswith('CrownFern'):return False,.6   # a rosette hides about its middle 60 percent; its outer fronds are thin and the peat shows through
        if short in ('TwigLitter_A','TwigLitter_B'):return False,.5   # sticks: the visible mass is a core half the size of the bounds
        if short in ('LeafLitter_A','RootTangle_A'):return False,.6
        return None
    def mark(short,x,y,yaw,sc):
        sh=shape(short)
        if sh:fp=Fp(meshes[short],x,y,yaw,sc); cov.mark(fp.cx,fp.cy,yaw,fp.hx*sh[1],fp.hy*sh[1],sh[0])
    for short,x,y,yaw,sc in stand.log+ferns.log:mark(short,x,y,yaw,sc)
    for tx,ty,tr in trunks:cov.mark(tx,ty,0.,tr,tr)
    total=cov.nx*cov.ny; info['bare_fraction_before']=round(cov.bare_cells()/total,4); info['largest_bare_square_before_m']=round(cov.bare_square()[0]*cov.cell,2)
    quota=dict(twig=120,leaf=60,root=25)
    def put(short,x,y,yaw,sc):
        ferns.put(short,x,y,yaw,sc); mark(short,x,y,yaw,sc); info['placed'][short]=info['placed'].get(short,0)+1
    def drop(kind,cx,cy):   # a twig or leaf piece with its bounds centre at (cx, cy)
        if kind=='twig':short='TwigLitter_A' if quota['twig']%2==0 else 'TwigLitter_B'; sc=rng.uniform(.9,1.2)
        else:short='LeafLitter_A'; sc=rng.uniform(.95,1.3)
        yaw=rng.uniform(0,360); ax,ay=at_centre(meshes[short],cx,cy,yaw,sc); put(short,ax,ay,yaw,sc); quota[kind]-=1
    def kind():
        t,l=quota['twig'],quota['leaf']
        return None if t+l==0 else 'twig' if rng.random()*(t+l)<t else 'leaf'
    # root tangles at trunk bases: the big trunks first, then poles
    big=[(n,x,y) for n,x,y in placed if n in ('Beech_Mature','Beech_Edge','DeadSpar')]; poles=[(n,x,y) for n,x,y in placed if n=='Beech_Pole']
    rng.shuffle(big); rng.shuffle(poles)
    for n,x,y in (big+poles)[:25]:
        put('RootTangle_A',x+rng.uniform(-.12,.12),y+rng.uniform(-.12,.12),rng.uniform(0,360),rng.uniform(.9,1.2)); quota['root']-=1
    # holes first: the centre of the largest bare square, until no 1 m square is bare
    info['holes_filled']=0; info['quota_ran_out_with_holes_left']=False
    for _ in range(600):
        k,cx,cy=cov.bare_square()
        if k*cov.cell<1.:break
        t=kind()
        if not t:info['quota_ran_out_with_holes_left']=True; break
        drop(t,cx+rng.uniform(-.1,.1),cy+rng.uniform(-.1,.1)); info['holes_filled']+=1
    # the rest of the quota: best of 8 random spots by bare cells hidden; leaf litter favours trunk bases (a mound against the trunk, .35 to 1.3 m off its surface)
    info['scattered']=0
    while True:
        t=kind()
        if not t:break
        best=None
        for _ in range(8):
            if t=='leaf' and rng.random()<.5:
                tx,ty,tr=rng.choice(trunks); a=rng.uniform(0,math.tau); d=tr+rng.uniform(.35,1.3); cx,cy=tx+d*math.cos(a),ty+d*math.sin(a)
            else:cx,cy=rng.uniform(.4,39.6),rng.uniform(50.4,89.6)
            if not (.3<cx<39.7 and 50.3<cy<89.7) or any(math.hypot(cx-tx,cy-ty)<tr+.25 for tx,ty,tr in trunks):continue
            n=cov.bare_in(cx,cy,0.,.45,.45)
            if best is None or n>best[0]:best=(n,cx,cy)
        if best:drop(t,best[1],best[2]); info['scattered']+=1
    k,cx,cy=cov.bare_square()
    info['largest_bare_square_m']=round(k*cov.cell,2); info['largest_bare_square_at']=[round(cx,2),round(cy,2)]; info['bare_fraction']=round(cov.bare_cells()/total,4)
    info['quota_left']=dict(quota); info['totals']=dict(twig=info['placed'].get('TwigLitter_A',0)+info['placed'].get('TwigLitter_B',0),leaf=info['placed'].get('LeafLitter_A',0),root=info['placed'].get('RootTangle_A',0))
    return info

def dense_floor_camera(placed,avoid):
    """NZ_DenseFloor: on foot (1.6 m) inside the stand, off the track and 4 m from the other cameras, 1 m clear of every trunk, aimed along a compass direction at the ground 3 m ahead.
    The direction with the clearest 7 m (fewest trunks in a 64 degree wedge) wins; the first of 600 seeded spots with a clear 3.5 m sightline."""
    rng=random.Random(52710+7501); trunks=[(x,y,TRUNK_R[n]) for n,x,y in placed]; best=None
    for _ in range(600):
        px,py=rng.uniform(5,35),rng.uniform(56,86)
        if abs(px-(20+xt(py-50)))<2.5 or any(math.hypot(px-ax,py-ay)<4. for ax,ay in avoid) or any(math.hypot(px-tx,py-ty)<tr+1. for tx,ty,tr in trunks):continue
        for yaw in (90,0,180,-90,45,135,-45,-135):
            c,s=math.cos(math.radians(yaw)),math.sin(math.radians(yaw)); tx,ty=px+3*c,py+3*s
            if any(math.hypot(tx-a,ty-b)<tr+.9 for a,b,tr in trunks):continue
            seg=[(px+c*d,py+s*d) for d in (0,.5,1,1.5,2,2.5,3,3.5)]
            if any(math.hypot(qx-a,qy-b)<tr+.45 for qx,qy in seg for a,b,tr in trunks):continue
            cost=sum(tr/max(math.hypot(a-px,b-py),1.) for a,b,tr in trunks if 0.<math.hypot(a-px,b-py)<7. and abs((math.degrees(math.atan2(b-py,a-px))-yaw+180)%360-180)<32)
            if best is None or cost<best[0]-1e-9:best=(cost,px,py,yaw,tx,ty)
        if best and best[0]<.05:break
    return dict(pos=[round(best[1],2),round(best[2],2)],yaw=best[3],aim_ground=[round(best[4],2),round(best[5],2)],trunk_cost=round(best[0],3)) if best else None

def edge_band(meshes):
    """S2b: the paddock edge band, x 60..100, y 44..50: the 6 m in front of the edge assembly's coprosma band (y 50..56), facing the paddock (-y).
    Four thickets (x 64.5, 71.5, 86, 95.5) hold Gorse_A x6, Gorse_B x4 and Broom x4; VergeTussock_A x40 / _B x30 in drifts (skirts of the shrubs, beside other tussocks, a few
    on their own); Rush_A/B x6 each in one 4 x 4 m dip at x 77..81, y 44.4..48.4 (the ground is a flat slab: a planting area, not a depression); Thistle x5 at the front, 4 m apart.
    The two Harakeke_B of the edge assembly (75, 48.8) and (87.5, 49.4) stay and are kept 1.3 to 1.6 m clear. Everything NoCollision."""
    rng=random.Random(52710+8001); band=Group(); info=dict(placed={},missed=[],band=dict(x=[60.,100.],y=[44.,50.],dip=[77.,81.,44.4,48.4]))
    BX0,BX1,BY0,BY1=60.,100.,44.,50.; DIP=(77.,81.,44.4,48.4); HARAKEKE=[(75.,48.8),(87.5,49.4)]; shrubs=[]; small=[]
    def rad(short,sc):
        e=meshes[short].get_bounds().box_extent; return (e.x+e.y)/2/100*sc*.8
    def in_dip(x,y,m=0.):return DIP[0]-m<=x<=DIP[1]+m and DIP[2]-m<=y<=DIP[3]+m
    def near_hara(x,y,m):return any(math.hypot(x-a,y-b)<m for a,b in HARAKEKE)
    def put(short,x,y,yaw,sc):
        band.put(short,x,y,yaw,sc); info['placed'].setdefault(short,[]).append([round(x,2),round(y,2),round(yaw,1),round(sc,3)])
    thickets=[((64.5,46.5),['Gorse_B','Gorse_A','Gorse_A','Broom_A']),((71.5,45.8),['Gorse_A','Broom_A']),
              ((86.0,46.0),['Gorse_B','Gorse_A','Gorse_B','Broom_A']),((95.5,46.8),['Gorse_A','Gorse_B','Gorse_A','Broom_A'])]
    for (cx,cy),members in thickets:
        for k,short in enumerate(members):
            for _ in range(300):
                sc=rng.uniform(.88,1.18); r=rad(short,sc)
                if k==0:x,y=cx+rng.uniform(-.4,.4),cy+rng.uniform(-.4,.4)
                else:a=rng.uniform(0,math.tau); d=rng.uniform(1.0,2.3); x,y=cx+d*math.cos(a),cy+d*math.sin(a)*.7
                if not (BX0+.8<=x<=BX1-.8 and BY0+1.<=y<=BY1-.8) or in_dip(x,y,1.2) or near_hara(x,y,1.6):continue
                if any(math.hypot(x-sx,y-sy)<.55*(r+sr) for sx,sy,sr in shrubs):continue
                put(short,x,y,rng.uniform(0,360),sc); shrubs.append((x,y,r)); break
            else:info['missed'].append(short)
    for short in rng.sample(['Rush_A']*6+['Rush_B']*6,12):   # the dip
        for _ in range(400):
            sc=rng.uniform(.9,1.2); r=rad(short,sc); x=rng.uniform(DIP[0]+.4,DIP[1]-.4); y=rng.uniform(DIP[2]+.4,DIP[3]-.4)
            if any(math.hypot(x-a,y-b)<.8*(r+rr) for a,b,rr in small):continue
            put(short,x,y,rng.uniform(0,360),sc); small.append((x,y,r)); break
        else:info['missed'].append(short)
    thistles=[]
    for _ in range(5):
        for _ in range(500):
            x,y=rng.uniform(BX0+1.,BX1-1.),rng.uniform(BY0-.3,BY0+3.2); r=rad('Thistle_A',1.)
            if in_dip(x,y,.9) or near_hara(x,y,1.6) or any(math.hypot(x-sx,y-sy)<sr+.4 for sx,sy,sr in shrubs) or any(math.hypot(x-a,y-b)<4. for a,b in thistles):continue
            put('Thistle_A',x,y,rng.uniform(0,360),rng.uniform(.9,1.15)); thistles.append((x,y)); small.append((x,y,r)); break
        else:info['missed'].append('Thistle_A')
    tuss=[]
    for short in rng.sample(['VergeTussock_A']*40+['VergeTussock_B']*30,70):
        for _ in range(400):
            sc=rng.uniform(.85,1.2); r=rad(short,sc); roll=rng.random()
            if roll<.4 and shrubs:
                sx,sy,sr=rng.choice(shrubs); a=rng.uniform(0,math.tau); d=.8*sr+rng.uniform(.2,1.8); x,y=sx+d*math.cos(a),sy+d*math.sin(a)
            elif roll<.75 and tuss:
                a_,b_,rr=rng.choice(tuss); a=rng.uniform(0,math.tau); d=rr+r+rng.uniform(0,.9); x,y=a_+d*math.cos(a),b_+d*math.sin(a)
            else:x,y=rng.uniform(BX0,BX1),rng.uniform(BY0-.2,BY1)
            if not (BX0-.3<=x<=BX1+.3 and BY0-.4<=y<=BY1+.1) or in_dip(x,y,.2) or near_hara(x,y,1.3):continue
            if any(math.hypot(x-sx,y-sy)<.8*sr+.2 for sx,sy,sr in shrubs) or any(math.hypot(x-a,y-b)<.75*(r+rr) for a,b,rr in tuss+small):continue
            put(short,x,y,rng.uniform(0,360),sc); tuss.append((x,y,r)); break
        else:info['missed'].append(short)
    info['counts']={k:len(v) for k,v in info['placed'].items()}
    return band,info

def shelter_row(meshes):
    """S2b: the shelterbelt on the bush stand's open west side, 40 m from the stand (the stand's west edge is x 0): a row on x -40 running north from y 35.
    Macrocarpa x2 at the south end (s 0, 13), Radiata_Mature x6 at 7 m (+-.3 jitter, s 26..61), Radiata_Young x3 at the north end (s 72.5, 78, 83.5), VergeTussock x20 at the foot (within 3.2 m
    of the line, 1 m from every trunk). Trees BlockAll (stand group), tussock NoCollision (foot group). Returns (stand, foot, info) with info['camera'] for NZ_Shelterbelt."""
    rng=random.Random(52710+9001); stand=Group(); foot=Group(); X,Y0=-40.,35.; info=dict(placed={},missed=[],row=dict(x=X,y0=Y0))
    seq=[('Macrocarpa',0.),('Macrocarpa',13.)]+[('Radiata_Mature',float(s)) for s in (26,33,40,47,54,61)]+[('Radiata_Young',72.5),('Radiata_Young',78.),('Radiata_Young',83.5)]
    TR={'Radiata_Mature':.45,'Macrocarpa':.7,'Radiata_Young':.3}; trees=[]
    for short,s in seq:
        sc=rng.uniform(.93,1.07) if short=='Radiata_Mature' else rng.uniform(.95,1.05) if short=='Macrocarpa' else rng.uniform(.9,1.1)
        x=X+rng.uniform(-.6,.6); y=Y0+s+rng.uniform(-.3,.3); yaw=rng.uniform(0,360)
        stand.put(short,x,y,yaw,sc); trees.append((short,x,y,TR[short])); info['placed'].setdefault(short,[]).append([round(x,2),round(y,2),round(yaw,1),round(sc,3)])
    mature=[t for t in trees if t[0]=='Radiata_Mature']; info['radiata_mature_spacing_m']=[round(mature[i+1][2]-mature[i][2],2) for i in range(5)]
    foots=[]
    for short in rng.sample(['VergeTussock_A']*10+['VergeTussock_B']*10,20):
        for _ in range(400):
            sc=rng.uniform(.9,1.2); e=meshes[short].get_bounds().box_extent; r=(e.x+e.y)/2/100*sc*.8
            x=X+rng.uniform(-3.2,3.2); y=Y0+rng.uniform(-1.5,88.)
            if any(math.hypot(x-tx,y-ty)<tr+1. for _n,tx,ty,tr in trees) or any(math.hypot(x-a,y-b)<.75*(r+rr) for a,b,rr in foots):continue
            foot.put(short,x,y,rng.uniform(0,360),sc); foots.append((x,y,r)); info['placed'].setdefault(short,[]).append([round(x,2),round(y,2)]); break
        else:info['missed'].append(short)
    info['camera']=dict(pos=[X+16.,Y0+25.],aim=[X,Y0+70.,8.],along_row_m=25.,offset_m=16.)
    return stand,foot,info

try:
    manifest=json.loads((OUT/'manifest.json').read_text())
    lod0={r['asset'].replace('SM_NZ_',''):r for r in manifest['models'] if r['lod']==0}
    meshes={}
    for short in ALL:
        meshes[short]=eal.load_asset(SRC+'/SM_NZ_'+short); assert meshes[short],('Run -Mode Import first; missing',short)
    blocking={s for s in ALL if lod0[s]['hulls']>0}
    report['blocking_meshes']=sorted(blocking)
    eal.make_directory(DEST)
    assert les.load_level(LEVEL) if eal.does_asset_exist(LEVEL) else les.new_level(LEVEL),'Could not open '+LEVEL
    for a in act.get_all_level_actors():
        if not isinstance(a,(u.WorldSettings,u.Brush)):act.destroy_actor(a)
    world=u.get_editor_subsystem(u.UnrealEditorSubsystem).get_editor_world()
    assert world.get_path_name().startswith(LEVEL+'.'),world.get_path_name()
    # ground: a 300 x 300 m cube slab, top at z 0
    ground=spawn(u.StaticMeshActor,'NZ_Ground',(0,0,-.5)); gc=ground.static_mesh_component
    gc.set_mobility(u.ComponentMobility.STATIC); gc.set_static_mesh(u.load_asset('/Engine/BasicShapes/Cube'))
    # NP4b: a map-owned peat instance, MI_NZ_Peat. Parent = MI_Env_Bog's parent; MI_Env_Bog's parameter values copied; then the base colour
    # parameter set to linear (.06,.04,.025) and, when the parent exposes a Roughness scalar, roughness .95. MI_Env_Bog itself is untouched.
    mel=u.MaterialEditingLibrary; PEAT_NAME='MI_NZ_Peat'; PEAT=DEST+'/'+PEAT_NAME
    bog=eal.load_asset('/Game/GrandTour/Materials/MI_Env_Bog'); assert bog,'MI_Env_Bog missing'
    parent=bog.get_editor_property('parent'); assert parent,'MI_Env_Bog has no parent'
    peat=eal.load_asset(PEAT) if eal.does_asset_exist(PEAT) else u.AssetToolsHelpers.get_asset_tools().create_asset(PEAT_NAME,DEST,u.MaterialInstanceConstant,u.MaterialInstanceConstantFactoryNew())
    assert peat,'could not create '+PEAT
    mel.set_material_instance_parent(peat,parent)
    base=parent
    while isinstance(base,u.MaterialInstance):base=base.get_editor_property('parent')   # the root Material, which owns the parameter names
    names={k:[str(n) for n in f(base)] for k,f in (('scalar',mel.get_scalar_parameter_names),('vector',mel.get_vector_parameter_names),('texture',mel.get_texture_parameter_names))}
    copied={'scalar':[],'vector':[],'texture':[]}
    for n in names['scalar']:
        try:mel.set_material_instance_scalar_parameter_value(peat,n,mel.get_material_instance_scalar_parameter_value(bog,n)); copied['scalar'].append(n)
        except Exception:pass
    for n in names['vector']:
        try:mel.set_material_instance_vector_parameter_value(peat,n,mel.get_material_instance_vector_parameter_value(bog,n)); copied['vector'].append(n)
        except Exception:pass
    for n in names['texture']:
        try:
            t=mel.get_material_instance_texture_parameter_value(bog,n)
            if t:mel.set_material_instance_texture_parameter_value(peat,n,t); copied['texture'].append(n)
        except Exception:pass
    colour_name='BaseColor' if 'BaseColor' in names['vector'] else next((n for n in names['vector'] if 'color' in n.lower() or 'colour' in n.lower()),None)
    assert colour_name,('no base colour vector parameter on the parent',names)
    mel.set_material_instance_vector_parameter_value(peat,colour_name,u.LinearColor(.06,.04,.025,1.))
    set_names=[colour_name]; rough_name=next((n for n in names['scalar'] if n.lower()=='roughness'),None)
    if rough_name:mel.set_material_instance_scalar_parameter_value(peat,rough_name,.95); set_names.append(rough_name)
    mel.update_material_instance(peat); assert eal.save_loaded_asset(peat),'could not save '+PEAT
    back=mel.get_material_instance_vector_parameter_value(peat,colour_name)
    report['ground']=dict(material=PEAT,parent=parent.get_path_name(),root_material=base.get_path_name(),copied_from='MI_Env_Bog',copied=copied,
                          parameter_names=names,set=set_names,base_colour=[round(back.r,4),round(back.g,4),round(back.b,4)],
                          roughness=mel.get_material_instance_scalar_parameter_value(peat,rough_name) if rough_name else 'no Roughness scalar on the parent')
    gc.set_material(0,peat); gc.set_collision_profile_name('BlockAll'); ground.set_actor_scale3d(u.Vector(300,300,1))
    # sky and light (setup_live_mud_drive.py), then the accepted tussock daylight
    spawn(u.DirectionalLight,'Sun',(0,0,10)); sky=spawn(u.SkyLight,'SkyLight',(0,0,10))
    sky.light_component.set_editor_property('real_time_capture',True)
    spawn(u.SkyAtmosphere,'SkyAtmosphere',(0,0,0)); spawn(u.ExponentialHeightFog,'HeightFog',(0,0,0))
    from tussock_style_lighting import configure
    report['lighting']=configure(world)
    # NP4c override, after configure(): the sun (pitch -55, 5.0) travels north (yaw 90) so it lights the south-facing edge-wall front and the rows
    # from the camera side; the skylight (8.0) and an unbound post volume with local-exposure shadow contrast .65 (balance_woodland_shadows.py's
    # fix for the Benmore woodland's black interior) lift the bush interior; the fog is a thin veil starting at 20 m.
    for actor in u.GameplayStatics.get_all_actors_of_class(world,u.DirectionalLight):
        actor.set_actor_rotation(u.Rotator(pitch=-55,yaw=90),False)
        lc=actor.get_component_by_class(u.DirectionalLightComponent)
        lc.set_intensity(5.0); lc.set_editor_property('use_temperature',True); lc.set_temperature(6200)
    for actor in u.GameplayStatics.get_all_actors_of_class(world,u.SkyLight):
        lc=actor.get_component_by_class(u.SkyLightComponent); lc.set_intensity(8.0); lc.set_editor_property('real_time_capture',True)
    for actor in u.GameplayStatics.get_all_actors_of_class(world,u.ExponentialHeightFog):
        fc=actor.get_component_by_class(u.ExponentialHeightFogComponent)
        fc.set_editor_property('fog_density',.01); fc.set_editor_property('start_distance',2000.)
    def props(o,**kw):
        for k,v in kw.items():o.set_editor_property(k,v)
        return o
    pp=spawn(u.PostProcessVolume,'NZ_ShadowBalance',(0,0,0))
    props(pp,unbound=True,priority=10.,blend_weight=1.,enabled=True)
    ppset=pp.get_editor_property('settings')
    props(ppset,override_local_exposure_shadow_contrast_scale=True,local_exposure_shadow_contrast_scale=.65)
    pp.set_editor_property('settings',ppset)
    sun=next(iter(u.GameplayStatics.get_all_actors_of_class(world,u.DirectionalLight))); sc=sun.get_component_by_class(u.DirectionalLightComponent)
    sk=next(iter(u.GameplayStatics.get_all_actors_of_class(world,u.SkyLight))).get_component_by_class(u.SkyLightComponent)
    fg=next(iter(u.GameplayStatics.get_all_actors_of_class(world,u.ExponentialHeightFog))).get_component_by_class(u.ExponentialHeightFogComponent)
    rot=sun.get_actor_rotation()
    report['lighting_np4']=dict(sun=dict(pitch=round(rot.pitch,2),yaw=round(rot.yaw,2),intensity=sc.get_editor_property('intensity'),
                                         temperature=sc.get_editor_property('temperature'),use_temperature=sc.get_editor_property('use_temperature'),
                                         source_angle=sc.get_editor_property('light_source_angle')),
                                sky=dict(intensity=sk.get_editor_property('intensity'),real_time_capture=sk.get_editor_property('real_time_capture')),
                                fog=dict(density=fg.get_editor_property('fog_density'),start_distance=fg.get_editor_property('start_distance')))
    ppb=pp.get_editor_property('settings')
    report['shadow_balance']=dict(label=pp.get_actor_label(),unbound=pp.get_editor_property('unbound'),priority=pp.get_editor_property('priority'),
                                  blend_weight=pp.get_editor_property('blend_weight'),enabled=pp.get_editor_property('enabled'),
                                  override_local_exposure_shadow_contrast_scale=ppb.get_editor_property('override_local_exposure_shadow_contrast_scale'),
                                  local_exposure_shadow_contrast_scale=ppb.get_editor_property('local_exposure_shadow_contrast_scale'))
    world.get_world_settings().set_editor_property('default_game_mode',u.GTRunGameMode)
    spawn(u.PlayerStart,'PlayerStart',(20,44,1.5),u.Rotator(yaw=90))
    # rows
    rows={'row1':0,'row2':0,'row3':0,'row4':0}
    def place(label,short,x,y,yaw,sc):
        a=spawn(u.StaticMeshActor,label,(x,y,0),u.Rotator(yaw=yaw)); c=a.static_mesh_component
        c.set_mobility(u.ComponentMobility.STATIC); c.set_static_mesh(meshes[short])
        c.set_collision_profile_name('BlockAll' if short in blocking else 'NoCollision')
        if sc!=1.:a.set_actor_scale3d(u.Vector(sc,sc,sc))
    for i,short in enumerate(ORDER):
        x=-76+8*i
        place('NZ_Row1_'+short,short,x,0,0,1.); rows['row1']+=1
        for k,(sc,yaw,dx) in enumerate([(.85,0,-3),(1.,120,0),(1.15,240,3)]):
            place('NZ_Row2_%s_%d'%(short,k),short,x+dx,-30,yaw,sc); rows['row2']+=1
    # S1 row 3 (y 6, behind row 1): the 15 floor and river meshes at true scale, 1 m between bounds, centred on x 0, each yawed 0
    widths=[2*meshes[s].get_bounds().box_extent.x/100 for s in FLOOR]; cursor=-(sum(widths)+len(FLOOR)-1)/2; row3={}
    for short,w in zip(FLOOR,widths):
        ax,ay=at_centre(meshes[short],cursor+w/2,6.,0.,1.); place('NZ_Row3_'+short,short,ax,ay,0,1.); rows['row3']+=1; row3[short]=round(cursor+w/2,2); cursor+=w+1.
    rows['row3_x_centres']=row3
    # S2b row 4 (y 12, 6 m behind row 3): the 15 verge meshes at true scale, 1 m between bounds, centred on x 0, each yawed 0
    widths=[2*meshes[s].get_bounds().box_extent.x/100 for s in VERGE]; cursor=-(sum(widths)+len(VERGE)-1)/2; row4={}
    for short,w in zip(VERGE,widths):
        ax,ay=at_centre(meshes[short],cursor+w/2,12.,0.,1.); place('NZ_Row4_'+short,short,ax,ay,0,1.); rows['row4']+=1; row4[short]=round(cursor+w/2,2); cursor+=w+1.
    rows['row4_x_centres']=row4
    report['rows']=rows
    # assemblies
    cams=[('NZ_Lineup',(0,-40,1.6),look((0,-40,1.6),(0,0,4))),
          ('NZ_LineupFar',(0,-140,1.6),look((0,-140,1.6),(0,0,4))),
          ('NZ_Driver',(-20,-8,1.2),look((-20,-8,1.2),(30,0,2))),
          ('NZ_FernMass',(20,60,1.6),u.Rotator(pitch=-4,yaw=90)),
          ('NZ_TowardSun',(30,70,1.6),u.Rotator(pitch=10,yaw=-90)),   # NP4: south, into the new sun
          ('NZ_EdgeWall',(80,30,1.6),u.Rotator(pitch=8,yaw=90)),
          ('NZ_Top',(50,50,60),u.Rotator(pitch=-90,yaw=90))]
    stand,ferns,bush_info,floor_info,placed=bush_assembly(blocking,(30,70),meshes)
    rstand,rscatter,river_info=river_strip(meshes,blocking,placed)
    estand,escrub,edge_info=edge_assembly(blocking)
    report['floor_bush']=floor_info; report['river']=river_info
    litter_info=bush_litter(meshes,stand,ferns,placed); report['litter']=litter_info
    band,band_info=edge_band(meshes); report['edge_band']=band_info
    sstand,sfoot,shelter_info=shelter_row(meshes); report['shelterbelt']=shelter_info
    assert not litter_info['quota_ran_out_with_holes_left'] and litter_info['largest_bare_square_m']<1.,('S2b: a 1 m square of the stand floor is still bare',litter_info)
    assert litter_info['totals']==dict(twig=120,leaf=60,root=25),('S2b litter counts',litter_info['totals'])
    assert not band_info['missed'] and not shelter_info['missed'],('S2b items without a free spot',band_info['missed'],shelter_info['missed'])
    assert not floor_info['missed'] and not river_info['missed'],('S1 items without a free spot',floor_info['missed'],river_info['missed'])
    assert floor_info['hero_camera'],'no open spot 4 m from the NZ_FloorLogs log'
    hc=floor_info['hero_camera']; px,py=hc['pos']; tx,ty=hc['target']
    cams.append(('NZ_FloorLogs',(px,py,1.6),look((px,py,1.6),(tx,ty,.9))))
    cams.append(('NZ_Riverbed',(-4.,45.,1.2),look((-4.,45.,1.2),(-3.7,67.,.7))))
    # S2b cameras. DenseFloor: on foot in the stand, aimed at the ground 3 m ahead. EdgeBand: driver height, 10 m out from the band's front (y 44). Shelterbelt: 25 m along the row,
    # 16 m off it on the stand side, aimed up the row at its north end.
    dc=dense_floor_camera(placed,[(20,60),(30,70),(px,py),(20,44)]); assert dc,'no open spot for NZ_DenseFloor'; report['dense_floor_camera']=dc
    cams.append(('NZ_DenseFloor',(dc['pos'][0],dc['pos'][1],1.6),look((dc['pos'][0],dc['pos'][1],1.6),(dc['aim_ground'][0],dc['aim_ground'][1],0.))))
    cams.append(('NZ_EdgeBand',(80.,34.,1.2),look((80.,34.,1.2),(80.,50.,2.))))
    sc_=shelter_info['camera']; cams.append(('NZ_Shelterbelt',(sc_['pos'][0],sc_['pos'][1],1.6),look((sc_['pos'][0],sc_['pos'][1],1.6),tuple(sc_['aim']))))
    report['instances']=[flush('NZ_BushStand',stand,'BlockAll',meshes),flush('NZ_BushFerns',ferns,'NoCollision',meshes),
                         flush('NZ_EdgeStand',estand,'BlockAll',meshes),flush('NZ_EdgeScrub',escrub,'NoCollision',meshes),
                         flush('NZ_RiverStand',rstand,'BlockAll',meshes),flush('NZ_RiverScatter',rscatter,'NoCollision',meshes),
                         flush('NZ_EdgeBandScrub',band,'NoCollision',meshes),flush('NZ_ShelterStand',sstand,'BlockAll',meshes),flush('NZ_ShelterFoot',sfoot,'NoCollision',meshes)]
    report['bush']=bush_info; report['edge']=edge_info
    for label,pos,rot in cams:
        c=spawn(u.CameraActor,label,pos,rot); c.camera_component.set_field_of_view(65)
    report['cameras']=[c[0] for c in cams]
    assert les.save_current_level(),'save failed'
    report['ok']=True
except Exception:
    report['error']=traceback.format_exc(); u.log_error(report['error'])
finally:
    (OUT/'lineup-report.json').write_text(json.dumps(report,indent=2))
    u.log('NATIVE_PLANTS_LINEUP_RESULT ok=%s'%report['ok']); u.SystemLibrary.quit_editor()
