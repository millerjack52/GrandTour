"""Drive the real car through the strip; record field uploads and wheel water contact.

LM1 (docs/LIVING_MUD_PLAN.md): Play In Editor in a new 1440x900 window when the editor helper is there (the level
viewport's size is the editor layout's, which changes; a first window that comes up another size is closed and asked
for once more). In that one session and viewport: a dry crossing with gt.Mud.Settle 0, profiled, as the frame-time
baseline; the fields reset to untouched ground; the same dry crossing with gt.Mud.Settle 1 (profiled, with the settle
cost readout; both crossings take the same three cockpit pictures, so their hitches match); the settle pair on a fresh
rut (Mud_Settle_0s/5s.png and settle_profile.csv); the pictures; the wet replay over the retained field; and last, the
fields reset again, a third dry crossing with gt.Mud.Settle 0 (no pictures), so the frame-time pair reads as A/B/A and
a drift over the session (the laptop GPU's) shows apart from the switch.

LM1b: the settle pair also writes D = RMS(S - the 3x3 mean of S) / RMS(S) over the rut's cells at 0.3 s and 5 s (the
cells round the spot that were off the ground at 0.3 s; the same cells at 5 s) into settle_profile.csv and the report,
and after the third crossing (gt.Mud.Settle 0) the same pair is driven again on its fresh lane and shot from the very
same camera (Mud_Settle_0s_Off.png, Mud_Settle_5s_Off.png). For the thin dark line along the left of LM1's settle
pictures, the report's dark_line gives where the patch's box edge, the landscape hole's inset edge (HoleInsetCm) and
the edge lip's inner ring project in that camera's 1440x900 shot.

LM2a/LM2b (docs/LIVING_MUD_PLAN.md): the cost gate is per feature mean <= 0.3 ms and p99 <= 0.7 ms (the max reported,
not gated), for Settle and the clods (whose own gate also asks a game-thread mean <= 0.1 ms); every run's summary has
both. The settle pair's start is the standstill crawl: per wheel, at 10 Hz for its first 15 s, with gt.Mud.Settle 1
(the main stage) and 0 (the third crossing), RutDepth, RutClimb, RutCrossSlope, the hold's push and drag, Sinkage, the
field's surface under the tyre and 30 cm ahead and their set timers (report crawl / crawl_off, crawl.csv). After the dry
pictures, the spin test: a dead stop on a fresh lane (y +4.5 m) where the Bog layer is deepest, full throttle 3 s, then
per wheel the hole's depth and the mound's height and distance behind it from the field, the throw's volumes (the
traction's, the spray's emitted / landed / lost, the patches') and the clods by source and fate; then Mud_Clods_Dry.png
from the settle pair's camera (LM3a housekeeping 2: and Mud_Clods_Dry_NoShadow.png, the same with the patch meshes' shadow
casting off) and Mud_Spin_Dry.png from the same framing on the spin spot, and (LM2c) Mud_OnFoot_Dry.png,
the owner's eye-level view along the settle pair's rut (1.7 m up, 3 m behind its start). Last, the clods at the cap:
every patch filled to 1200 (UGTMudSubsystem::FillClodsForTest), 6 s profiled with gt.Mud.Clods 1 and 6 s with 0 from the
settle camera, the GPU time and its base pass and shadow depth columns.
"""
import unreal as u,json,time,math,traceback,csv,statistics,os,sys
from pathlib import Path
ROOT=Path(u.Paths.project_dir()).resolve()
OUT=ROOT/'Art/Export/LiveMudDrive'
CSV_DIR=ROOT/'Saved/Profiling/CSV'
u.EditorPythonScripting.set_keep_python_script_alive(True)
VIEW=(1440,900)
# The settle pair: a fresh lane 4.5 m to the -Y side of the crossing's line (the winch posts stand at +6.5 m), the spot
# inside the mud section (32-60 m). A stamp reaches 2.3 m round its stroke (tyre, shoulder and ridge band), so the
# spot's last wheel has left it when every contact is that far past.
PAIR_Y=-450.;PAIR_START_X=3300.;PAIR_SPOT_X=4400.;STAMP_REACH_CM=230.
# LM2a's spin test: a fresh lane on the other side, the deepest Bog along it inside the mud section, full throttle 3 s.
SPIN_Y=450.;SPIN_X0=3400.;SPIN_X1=5600.;SPIN_S=3.
# The cost gate per feature (LM2a housekeeping 2) and the clods' own game-thread mean (LM2b).
GATE_MEAN_MS=.3;GATE_P99_MS=.7;CLOD_GT_MEAN_MS=.1
spin={};crawl_rows=[]
phase='load';last=time.monotonic();start=last;run=0;sample_at=0;shots=set();records=[];pending_shot=None
# Checks under a running game (docs/CHECKS_UNDER_GAME_PLAN.md, Art/Unreal/check_render.py): a fixed 1/60 s step (the wrapper's
# -UseFixedTimeStep -FPS=60, verified over 300 frames of the first drive), the scene rendered only from a picture's request
# (30 frames of warm-up; the cockpit pictures are taken that much further on) until its file lands, and through the settle pair's
# watch (its camera set to its 5 s picture); the phases wait while a picture is pending, the drives do not.
sys.path.insert(0,str(Path(u.Paths.project_dir()).resolve()/'Art/Unreal'))
from check_render import Gate
GATE=Gate()
# Checks: game-time limits (2026-10-10, the owner: a running game holds the editor to a fraction of real time): the drives' 110 s cap,
# the sampling, the settle pair's 60 s cap, the crawl window and the spin-up count SIMULATED seconds (gt(), the physics clock, see
# advance_sim), and every reported drive time is in them; the settle pair's 0.3 / 5 s field timers count the world's seconds (gw(): the
# field settles on the world's clock); WALL_CAP_S (40 min) is the only wall-clock limit.
world=None;pc=None;WALL_CAP_S=2400.;DRIVE_CAP_S=110.
def gw():
    try:return u.GameplayStatics.get_time_seconds(world) if world is not None else 0.
    except Exception:return 0.   # a world being torn down (a Play In Editor restart)
# The simulated (physics) seconds: the world's time advances up to its frame clamp each frame, the physics at most MaxPhysicsDeltaTime
# (1/30 s, no substepping here), so under 30 frames a second the world's seconds outrun the car's (at 1.9 frames a second about 5x);
# the drive limits and the reported drive times count this clock, advanced once a tick by min(the world's step, the physics cap).
def _phys_cap():
    try:
        ps=u.PhysicsSettings.get_default_object()
        if ps.get_editor_property('b_substepping'):return ps.get_editor_property('max_substep_delta_time')*ps.get_editor_property('max_substeps')
        return ps.get_editor_property('max_physics_delta_time')
    except Exception:return 1./30.
PHYS_CAP=_phys_cap();SIM=0.;SIM_LASTG=None
def advance_sim():
    global SIM,SIM_LASTG
    g=gw()
    if world is None or SIM_LASTG is None or g<SIM_LASTG:SIM_LASTG=g;return
    SIM+=min(max(0.,g-SIM_LASTG),PHYS_CAP);SIM_LASTG=g
def gt():
    return SIM
def clock():
    # The phases' clock (Checks under a running game): game seconds in play, the wall clock while loading.
    return gt() if (world is not None and phase not in ('load','loaded','warm','restart','finished')) else time.monotonic()
report={'ok':False,'runs':[],'images':[],'profiles':[],'viewports':[]}
stage='base'   # 'base': the gt.Mud.Settle 0 dry crossing; 'main': gt.Mud.Settle 1 on reset fields, everything else; 'after': gt.Mud.Settle 0 again
def run_label():
    return 'dry_settle0' if stage=='base' else ('dry_settle0_after' if stage=='after' else ('wet_settle1' if run else 'dry_settle1'))
def restart_dry(settle):
    # Untouched ground again, the car back at the start, held.
    mud.reset_fields_for_test()
    spec=u.load_asset('/Game/GrandTour/ArtTests/LiveMudDrive/DA_MudDrive').spec;z=u.GTVehicleSetupLibrary.sample_terrain_height_cm(spec,500,0)
    car.set_actor_location_and_rotation(u.Vector(500,0,z+150),u.Rotator(),False,True);body=car.get_component_by_class(u.SkeletalMeshComponent);body.set_physics_linear_velocity(u.Vector());body.set_physics_angular_velocity_in_degrees(u.Vector());car.reset_driving_inputs();move.set_handbrake_input(True)
    console('gt.Mud.Settle %d'%settle)
csv_marks=[]   # (label, the CSV files there were when its profile started)
pair={};pair_camera={};profile_rows=[]
def csv_files():
    return set(p.name for p in CSV_DIR.glob('*.csv')) if CSV_DIR.exists() else set()
# GR1 (docs/GROUND_RELIEF_PLAN.md section 0, no timing): GT_CHECK_NO_PROFILE=1 drives and shoots as before with no CSV profile and
# no clod-cap timing phases (the owner's runs keep the default, profiled).
NO_PROFILE=os.environ.get('GT_CHECK_NO_PROFILE','0').strip()=='1'
def console(cmd):
    if NO_PROFILE and cmd.startswith('csvprofile'):return
    u.SystemLibrary.execute_console_command(world,cmd,pc)
def begin_play():
    lib=getattr(u,'GTPlayWindowLibrary',None)
    if lib and lib.request_play_in_new_window(VIEW[0],VIEW[1]):return 'new window %dx%d'%VIEW
    u.get_editor_subsystem(u.LevelEditorSubsystem).editor_request_begin_play();return 'level viewport'
def column_stats(rows,header,name):
    if name not in header:return None
    i=header.index(name);vals=[]
    for r in rows:
        try:vals.append(float(r[i]))
        except (ValueError,IndexError):pass
    if not vals:return None
    vals.sort()
    return dict(mean=round(statistics.fmean(vals),3),median=round(statistics.median(vals),3),p95=round(vals[min(len(vals)-1,int(.95*len(vals)))],3),p99=round(vals[min(len(vals)-1,max(0,math.ceil(.99*len(vals))-1))],3),max=round(vals[-1],3))
def parse_profiles():
    # Each profile's CSV is the one that appeared after its start (the file is written when the capture stops).
    seen=[m[1] for m in csv_marks]+[csv_files()]
    for k,(label,before) in enumerate(csv_marks):
        new=sorted(seen[k+1]-before)
        entry=dict(run=label,csv=None)
        if new:
            path=CSV_DIR/new[0];entry['csv']=str(path)
            with open(path,newline='') as f:rows=list(csv.reader(f))
            header=rows[0];body=[]
            for r in rows[1:]:
                if not r or r[0].startswith('[') or r[0]=='EVENTS':break
                body.append(r)
            entry['frames']=len(body)
            names=['FrameTime','GameThreadTime','RenderThreadTime','GPUTime','GTMud/GameThread/Settle','GTMud/GameThread/Upload','GTMud/GameThread/Clods']
            # LM2b: the GPU's base pass and shadow depths (-csvGpuStats), whatever the columns are called in this build.
            names+=[h for h in header if h not in names and ('basepass' in h.lower() or 'shadowdepth' in h.lower())]
            for name in names:
                stats=column_stats(body,header,name)
                if stats:entry[name]=stats
        report['profiles'].append(entry)
def finish(error=None):
    global phase
    phase='finished'
    if error:report['error']=error
    try:parse_profiles()
    except Exception:report['profile_error']=traceback.format_exc()
    report['samples']=records
    if crawl_rows:
        try:
            with open(OUT/'crawl.csv','w',newline='') as f:
                wr=csv.DictWriter(f,fieldnames=list(crawl_rows[0].keys()));wr.writeheader();wr.writerows(crawl_rows)
        except Exception:report['crawl_csv_error']=traceback.format_exc()
    try:report['check_run']=GATE.report()
    except Exception:report['check_run_error']=traceback.format_exc().splitlines()[-1]
    (OUT/'drive-report.json').write_text(json.dumps(report,indent=2));u.unregister_slate_post_tick_callback(handle);u.EditorLevelLibrary.editor_end_play();u.SystemLibrary.quit_editor()
def snap(name,detail=False):
    global pending_shot
    if detail:
        pos=u.Vector(4700,450,220);target=u.Vector(4700,0,-35);camera.set_actor_location(pos,False,False);camera.set_actor_rotation(u.MathLibrary.find_look_at_rotation(pos,target),False);camera.camera_component.set_field_of_view(58)
        if name.startswith('Boundary'):
            spec=u.load_asset('/Game/GrandTour/ArtTests/LiveMudDrive/DA_MudDrive').spec
            z=u.GTVehicleSetupLibrary.sample_terrain_height_cm(spec,2520,0)
            pos=u.Vector(2180,-400,z+230);target=u.Vector(2580,60,z)
            camera.set_actor_location(pos,False,False);camera.set_actor_rotation(u.MathLibrary.find_look_at_rotation(pos,target),False)
        elif name.startswith('Mud_Long'):
            pos=u.Vector(3450,140,190);target=u.Vector(4850,0,0)
            camera.set_actor_location(pos,False,False);camera.set_actor_rotation(u.MathLibrary.find_look_at_rotation(pos,target),False);camera.camera_component.set_field_of_view(65)
        pc.set_view_target_with_blend(camera,0.)
    else:
        eye=car.get_driver_camera();camera.set_actor_location(eye.get_world_location(),False,False);camera.set_actor_rotation(eye.get_world_rotation(),False);camera.camera_component.set_field_of_view(eye.field_of_view)
    path=OUT/(name+'.png');report['images'].append(str(path))
    # Capture the PIE viewport directly; the editor automation helper recompiles unrelated preview shaders.
    pending_shot=(clock()+(1.0 if detail else .1),path)
def shoot_now(name):
    path=OUT/(name+'.png');report['images'].append(str(path))
    console('HighResShot %dx%d filename="%s"'%(VIEW[0],VIEW[1],path.as_posix()));GATE.expect(path)
def detail_d(t_label):
    # LM1b's detail measure on the strip: the cells whose centres lie within 1 m along and 1.5 m across of the spot on
    # the rut (the profile's span); the cells measured are the ones off the ground (|S| > 0.01 cm) at 0.3 s, away from the
    # box's edge so every one has its 3x3, and the same cells at 5 s.
    spot=pair['spot_x'];yr=pair['rut_y'];lo=u.Vector2D(spot-100.,yr-150.);hi=u.Vector2D(spot+100.,yr+150.)
    h=list(mud.mud_cell_heights_cm(lo,hi));nx=mud.mud_cells_across(lo,hi)
    if not h or nx<3:return None
    ny=len(h)//nx
    if 'mask' not in pair:pair['mask']=[y*nx+x for y in range(1,ny-1) for x in range(1,nx-1) if abs(h[y*nx+x])>.01]
    num=den=0.
    for i in pair['mask']:
        x,y=i%nx,i//nx;m=sum(h[(y+dy)*nx+x+dx] for dy in (-1,0,1) for dx in (-1,0,1))/9.
        num+=(h[i]-m)**2;den+=h[i]**2
    pair['detail_cells']=len(pair['mask']);pair['detail_grid']=[nx,ny]
    return round(math.sqrt(num/den),4) if den>0 else None
def pair_profile(t_label):
    rows=[];spot=pair['spot_x'];yr=pair['rut_y'];d=detail_d(t_label)
    for k in range(-24,25):
        y=yr+k*6.25;xy=u.Vector2D(spot,y)
        rows.append(dict(t_s=t_label,y_offset_cm=k*6.25,height_cm=round(mud.mud_height_cm_at(xy),3),fresh=round(mud.mud_fresh_at(xy),3),detail_d=d))
    core=min(r['height_cm'] for r in rows if abs(r['y_offset_cm'])<=25.);crest=max(r['height_cm'] for r in rows)
    profile_rows.extend(rows);pair['core_cm_%s'%t_label]=core;pair['crest_cm_%s'%t_label]=crest;pair['detail_d_%s'%t_label]=d
    pair['fresh_core_%s'%t_label]=next(r['fresh'] for r in rows if r['y_offset_cm']==0.)
def dark_line_candidates():
    # Where the patch's box edge (the mesh's lifted outer ring), the landscape hole's inset edge and the lip's inner ring
    # project in the pair camera's 1440x900 shot: a pinhole from the camera's pose and horizontal FOV, letterboxed to the
    # camera's aspect when it constrains it (the shot's black bands). Each line is sampled every 25 cm on the ground and
    # kept where it is in front of the camera and inside the picture.
    cc=camera.camera_component;fov=cc.field_of_view;constrained=bool(cc.get_editor_property('constrain_aspect_ratio'));ar=cc.aspect_ratio
    W,H=VIEW;rh=W/ar if constrained else H;top=(H-rh)/2.;fpx=(W/2.)/math.tan(math.radians(fov)/2.)
    c=camera.get_actor_location();f=camera.get_actor_forward_vector();r=camera.get_actor_right_vector();up=camera.get_actor_up_vector()
    spec=u.load_asset('/Game/GrandTour/ArtTests/LiveMudDrive/DA_MudDrive').spec
    def proj(x,y,z):
        d=(x-c.x,y-c.y,z-c.z);zc=d[0]*f.x+d[1]*f.y+d[2]*f.z
        if zc<10.:return None
        xc=d[0]*r.x+d[1]*r.y+d[2]*r.z;yc=d[0]*up.x+d[1]*up.y+d[2]*up.z
        px=W/2.+fpx*xc/zc;py=top+rh/2.-fpx*yc/zc
        return (round(px,1),round(py,1),round(x,1),round(y,1),round(z,1)) if 0<=px<W and top<=py<top+rh else None
    inset=None
    try:
        for ls in u.GameplayStatics.get_all_actors_of_class(world,u.Landscape):
            m=ls.get_editor_property('landscape_material')
            if isinstance(m,u.MaterialInstance):inset=u.MaterialEditingLibrary.get_material_instance_scalar_parameter_value(m,'HoleInsetCm')
            elif m:inset=u.MaterialEditingLibrary.get_material_default_scalar_parameter_value(m,'HoleInsetCm')
            if inset:break
    except Exception:report['dark_line_inset_error']=traceback.format_exc()
    inset_src='landscape material' if inset else 'assumed (setup_m6_hide.py HOLE_INSET_CM)'
    inset=inset or 12.5
    out=dict(camera=dict(location=[c.x,c.y,c.z],forward=[f.x,f.y,f.z],fov=fov,constrain_aspect=constrained,aspect=ar,shot=list(VIEW),picture_rows=[top,top+rh]),hole_inset_cm=inset,hole_inset_source=inset_src,lines=[])
    for p in u.GameplayStatics.get_all_actors_of_class(world,u.GTMudPatch):
        b0=p.bounds_min;b1=p.bounds_max
        if not (b0.x<=pair['spot_x']<=b1.x and b0.y<=pair['rut_y']<=b1.y):continue   # the patch the pair is on
        for name,shrink in (('box edge (mesh outer ring, lifted EdgeLipCm %.2f)'%p.edge_lip_cm,0.),('hole inset edge (box - %.1f cm)'%inset,inset),('lip inner ring (box - MeshCellCm %.1f, lift 0)'%p.mesh_cell_cm,p.mesh_cell_cm)):
            x0,y0,x1,y1=b0.x+shrink,b0.y+shrink,b1.x-shrink,b1.y-shrink
            for side,pts in (('-Y',[(x,y0) for x in frange(x0,x1)]),('+Y',[(x,y1) for x in frange(x0,x1)]),('-X',[(x0,y) for y in frange(y0,y1)]),('+X',[(x1,y) for y in frange(y0,y1)])):
                # A cheap first look at the camera's ground height, then the terrain sampled only where that is near the picture.
                near=[(x,y) for x,y in pts if proj(x,y,c.z-150.) or proj(x,y,c.z-250.) or proj(x,y,c.z-50.)]
                on=[q for q in (proj(x,y,u.GTVehicleSetupLibrary.sample_terrain_height_cm(spec,x,y)+(p.edge_lip_cm if shrink==0. else 0.)) for x,y in near) if q]
                if on:out['lines'].append(dict(patch=p.section_index,line=name,side=side,world=[x0,y0,x1,y1],points=on))
    # The engine's own projection of a few of the same points (viewport pixels, the PIE window's client size, its own
    # letterbox), as a check on the pinhole's direction and scale.
    try:
        chk=[]
        for line in out['lines'][:3]:
            q=line['points'][len(line['points'])//2]
            res=u.GameplayStatics.project_world_to_screen(pc,u.Vector(q[2],q[3],q[4]),False)
            if isinstance(res,tuple):res=res[-1] if res[0] else None
            chk.append(dict(world=q[2:],pinhole_shot=q[:2],engine_viewport=[round(res.x,1),round(res.y,1)] if res is not None else None))
        out['engine_check']=chk;out['viewport']=list(pc.get_viewport_size())
    except Exception:out['engine_check_error']=traceback.format_exc()
    return out
def frange(a,b,step=25.):
    n=int((b-a)//step);return [a+i*step for i in range(n+1)]+[b]
def gate(mean,p99,mx,gt_mean=None):
    # LM2a housekeeping 2: mean <= 0.3 ms and p99 <= 0.7 ms per feature, the max reported only.
    out=dict(mean_ms=round(mean,4),p99_ms=round(p99,4),max_ms=round(mx,4),ok=bool(mean<=GATE_MEAN_MS and p99<=GATE_P99_MS))
    if gt_mean is not None:out.update(gt_mean_gate_ms=gt_mean,ok_gt_mean=bool(mean<=gt_mean))
    return out
def clod_counts():
    # LM2b: per patch, the clods by source and by fate (and what was dropped: no mesh, or switched off).
    rows=[]
    for p in u.GameplayStatics.get_all_actors_of_class(world,u.GTMudPatch):
        rows.append(dict(section=p.section_index,meshes=p.clod_mesh_count,live=p.clods_live,bank=p.clods_from_bank,throw=p.clods_from_throw,test=p.clods_from_test,
            squashed=p.clods_squashed,sunk=p.clods_sunk,recycled=p.clods_recycled,dropped=p.clods_dropped))
    total={k:sum(r[k] for r in rows) for k in ('live','bank','throw','test','squashed','sunk','recycled','dropped')}
    return dict(total=total,patches=rows)
def throw_counts():
    # LM2a: the throw's volumes - the traction's per wheel, the spray's blobs, the patches' books.
    sp=car.get_spray();wheels=car.get_traction().wheels;patches=u.GameplayStatics.get_all_actors_of_class(world,u.GTMudPatch)
    emitted=sp.get_throw_emitted_cm3();landed=sp.get_throw_landed_cm3();lost=sp.get_throw_lost_cm3()
    return dict(wheels_thrown_cm3=[round(w.thrown_cm3,1) for w in wheels],spray_emitted_cm3=round(emitted,1),spray_landed_cm3=round(landed,1),spray_lost_cm3=round(lost,1),
        spray_pending_cm3=round(sp.get_throw_pending_cm3(),1),lost_share=round(lost/(landed+lost),4) if landed+lost>0 else None,
        blobs=dict(emitted=sp.get_throw_blobs_emitted(),landed=sp.get_throw_blobs_landed(),lost=sp.get_throw_blobs_lost()),
        patches_returned_cm3=round(sum(p.throw_returned_cm3 for p in patches),1),patches_deposited_cm3=round(sum(p.throw_deposited_cm3 for p in patches),1),
        lumps_flattened_cm3=round(sum(p.lump_flattened_cm3 for p in patches),1))
def place_car(x,y):
    spec=u.load_asset('/Game/GrandTour/ArtTests/LiveMudDrive/DA_MudDrive').spec;z=u.GTVehicleSetupLibrary.sample_terrain_height_cm(spec,x,y)
    car.set_actor_location_and_rotation(u.Vector(x,y,z+150),u.Rotator(),False,True);body=car.get_component_by_class(u.SkeletalMeshComponent);body.set_physics_linear_velocity(u.Vector());body.set_physics_angular_velocity_in_degrees(u.Vector());car.reset_driving_inputs();move.set_handbrake_input(True)
def spin_spot():
    # The deepest mud on the spin lane: the most Bog (the patch's baked layer), the section's middle on a tie.
    best=None
    for x in range(int(SPIN_X0),int(SPIN_X1)+1,50):
        b=mud.mud_bog_at(u.Vector2D(x,SPIN_Y))
        if best is None or b>best[0]+1e-6 or (abs(b-best[0])<=1e-6 and abs(x-4600)<abs(best[1]-4600)):best=(b,x)
    return best
def spin_measure():
    # Per wheel from the field: the hole (the lowest surface within 40 cm of the contact) and the mound behind it (the
    # highest surface 0.3-4 m behind along the car's axis, +-40 cm across), with the lumps there.
    fwd=car.get_actor_forward_vector();rx,ry=-fwd.y,fwd.x;out=[]
    for k,w in enumerate(car.get_traction().wheels):
        c=w.contact_point
        hole=min(mud.mud_height_cm_at(u.Vector2D(c.x+dx,c.y+dy)) for dx in range(-40,41,10) for dy in range(-40,41,10))
        best=(-1.e9,0.,0.)
        for i in range(3,41):
            d=i*10.
            for off in range(-40,41,10):
                xy=u.Vector2D(c.x-fwd.x*d+rx*off,c.y-fwd.y*d+ry*off);h=mud.mud_height_cm_at(xy)
                if h>best[0]:best=(h,d,mud.mud_lump_cm_at(xy))
        out.append(dict(wheel=k,contact=[round(c.x,1),round(c.y,1)],hole_cm=round(hole,2),mound_cm=round(best[0],2),mound_behind_m=round(best[1]/100.,2),mound_lump_cm=round(best[2],2),
            sinkage_m=round(w.sinkage,3),thrown_cm3=round(w.thrown_cm3,1),lowered_cm3=round(w.mud_lowered_cm3,1)))
    return out
def aim_camera(cpos,ctarget,fov=55):
    camera.set_actor_location(cpos,False,False);camera.set_actor_rotation(u.MathLibrary.find_look_at_rotation(cpos,ctarget),False);camera.camera_component.set_field_of_view(fov);pc.set_view_target_with_blend(camera,0.)
def crawl_sample(now,sfx):
    # LM2a housekeeping 4 (diagnose only): the standstill crawl, per wheel at 10 Hz for the first 15 s of the pair's start.
    rel=now-pair['release']
    if rel>15. or now-pair.get('crawl_at',-1.)<.1:return
    pair['crawl_at']=now;pos=car.get_actor_location()
    for k,w in enumerate(car.get_traction().wheels):
        c=w.contact_point;hd=w.tyre_heading;here=u.Vector2D(c.x,c.y);ahead=u.Vector2D(c.x+hd.x*30.,c.y+hd.y*30.)
        crawl_rows.append(dict(settle=0 if sfx else 1,t_s=round(rel,2),car_x_m=round(pos.x/100.,3),speed_mps=round(car.get_velocity().length()/100.,3),wheel=k,
            rut_depth=round(w.rut_depth,4),rut_climb=round(w.rut_climb,4),rut_cross_slope=round(w.rut_cross_slope,4),hold_lateral_n=round(w.rut_hold_lateral_n,1),hold_drag_n=round(w.rut_hold_drag_n,1),
            sinkage_m=round(w.sinkage,4),slip_cm_s=round(w.slip_magnitude,1),field_under_cm=round(mud.mud_height_cm_at(here),3),field_ahead30_cm=round(mud.mud_height_cm_at(ahead),3),
            set_s_under=round(mud.mud_set_seconds_at(here),3),set_s_ahead30=round(mud.mud_set_seconds_at(ahead),3)))
def drive_step(target_y):
    pos=car.get_actor_location();speed=car.get_velocity().length()/100.;yaw=car.get_actor_rotation().yaw
    # A heading correction through the existing test steering path; no tuning is changed.
    target_yaw=math.degrees(math.atan2(target_y-pos.y,650.));error=(target_yaw-yaw+180)%360-180;car.set_raw_steer(max(-.65,min(.65,error/24)))
    move.set_throttle_input(max(.18,min(1.,.42+(3.2-speed)*.22)));move.set_brake_input(.25 if speed>4.5 else 0.)
    return pos,speed
def tick(dt):
    global phase,last,run,world,car,move,pc,camera,mud,weather,sample_at,drive_start,volume_start,pending_shot,stage
    wall=time.monotonic()
    advance_sim()
    # Checks under a running game: in play every wait and timer of the phases counts game seconds (a fixed 1/60 s a frame), so the
    # game's state between two steps (drying, settling, the car at rest) is the same whatever the frame rate; loading and the start of
    # play count the wall clock. A `last` set on the other clock is re-based at the switch.
    now=gt() if (world is not None and phase not in ('load','loaded','warm','restart','finished')) else wall
    if (now<wall and last>now+1000.) or (now==wall and last<1000.):last=now
    try:
        if phase not in ('load','loaded','warm','finished','restart'):
            weather.set_wetness_for_test(.8 if run else 0.)
        GATE.tick(world)
        if pending_shot and world is not None:GATE.set(world,pc,True)   # the picture's render window opens with its request
        if pending_shot and now>=pending_shot[0] and GATE.ready(world,pc):
            path=pending_shot[1];pending_shot=None
            console('HighResShot %dx%d filename="%s"'%(VIEW[0],VIEW[1],path.as_posix()));GATE.expect(path)
        if world is not None:GATE.idle(world,pc,keep=pending_shot is not None)
        if (pending_shot or GATE.capturing()) and phase not in ('drive','pair_drive','spin','load','loaded','warm','restart','finished'):return
        if wall-start>WALL_CAP_S:finish('Drive check hit its %.0f min wall-clock cap'%(WALL_CAP_S/60.));return
        if phase=='load':
            assert u.get_editor_subsystem(u.LevelEditorSubsystem).load_level('/Game/GrandTour/ArtTests/LiveMudDrive/L_MudDrive');phase='loaded';last=now
        elif phase=='loaded' and now-last>6:
            report['play_mode']=begin_play();phase='warm';last=now
        elif phase=='restart' and now-last>5:
            report['play_mode_retry']=begin_play();phase='warm';last=now
        elif phase=='warm' and now-last>15:
            world=u.EditorLevelLibrary.get_game_world()
            if world is None:
                if now-last>40:raise RuntimeError('Play In Editor did not start')
                if now-last>25 and not report.get('fallback_%s'%stage):
                    u.get_editor_subsystem(u.LevelEditorSubsystem).editor_request_begin_play();report['fallback_%s'%stage]='level viewport'
                return
            cars=u.GameplayStatics.get_all_actors_of_class(world,u.GTCarPawn)
            assert cars,'Automation car missing';car=cars[0]
            move=car.get_chaos_movement();pc=u.GameplayStatics.get_player_controller(world,0)
            if pc:pc.possess(car);car.disable_input(pc)
            size=list(pc.get_viewport_size());report['viewports'].append(size)
            if str(report.get('play_mode','')).startswith('new window') and size[0]!=VIEW[0] and 'viewport_retry' not in report:
                # The first new window has come up another size (1274x682 for 1440x900 asked, 2026-10-05): once more.
                report['viewport_retry']=size;u.EditorLevelLibrary.editor_end_play();phase='restart';last=now;return
            report['viewport_size']=size;report['mode']='Play In Editor, actual possessed cockpit'
            car.reset_driving_inputs();car.set_chase_camera(False)
            car.get_drivetrain().set_low_range(True);car.get_drivetrain().set_diff_lock(True)
            mud=next(o for o in u.ObjectIterator(u.GTMudSubsystem) if o.get_outer()==world);weather=next(o for o in u.ObjectIterator(u.GTWeatherSubsystem) if o.get_outer()==world)
            patches=u.GameplayStatics.get_all_actors_of_class(world,u.GTMudPatch);assert len(patches)==2,len(patches)
            report['patches']=[dict(section=p.section_index,vertices=p.mesh_vertex_count,material=p.get_editor_property('bMaterialLoaded'),water=p.get_editor_property('bWaterMaterialLoaded'),table_cm=p.water_table_cm,repose_deg=p.repose_deg,ooze_rate=p.ooze_rate,recover_share=p.recover_share,creep_cm_per_cm=p.creep_cm_per_cm,set_seconds=p.set_seconds,bounds_min=[p.bounds_min.x,p.bounds_min.y],bounds_max=[p.bounds_max.x,p.bounds_max.y],edge_lip_cm=p.edge_lip_cm,mesh_cell_cm=p.mesh_cell_cm,
                lump_share=p.lump_share,lump_spacing_cells=p.lump_spacing_cells,lump_radius_cells=p.lump_radius_cells,throw_max=p.throw_max,fresh_min_cm=p.fresh_min_cm,clod_meshes=p.clod_mesh_count,max_clods=p.max_clods) for p in patches]
            assert all(p.get_editor_property('bMaterialLoaded') and p.get_editor_property('bWaterMaterialLoaded') for p in patches)
            camera=next(a for a in u.GameplayStatics.get_all_actors_of_class(world,u.CameraActor) if a.get_actor_label()=='Live_Overview')
            console('gt.Mud.Settle %d'%(0 if stage=='base' else 1))
            move.set_handbrake_input(True);phase='settle';last=now
        elif phase=='settle' and now-last>4:
            pc.set_view_target_with_blend(car,0.)
            car.reset_driving_inputs();move.set_handbrake_input(False);move.set_target_gear(1,True);volume_start=mud.total_lowered_cm3();drive_start=gt();GATE.start_dt();report.setdefault('drive_wall0',{})[run_label()]=(wall,u.SystemLibrary.get_frame_count());sample_at=-1.;phase='drive'
            mud.reset_settle_stats()
            label=run_label()
            csv_marks.append((label,csv_files()));console('csvprofile start')
        elif phase=='drive':
            pos,speed=drive_step(0.)
            weather.set_wetness_for_test(.8 if run else 0.)
            label=run_label()
            if gt()-sample_at>.25:
                wheels=car.get_traction().wheels
                records.append(dict(run=label,t=gt()-drive_start,x_m=pos.x/100,y_m=pos.y/100,speed_mps=speed,volume_cm3=mud.total_lowered_cm3(),sink_m=max(w.sinkage for w in wheels),water_m=max(w.water_depth_m for w in wheels),in_patch=any(w.get_editor_property('bInPatchBox') for w in wheels)))
                (OUT/'drive-progress.json').write_text(json.dumps(records[-1]))
                sample_at=gt()
            if run==0 and stage!='after':
                # Both dry crossings take the cockpit pictures (the gt.Mud.Settle 0 ones suffixed), so the two profiles carry the same three hitches.
                for mark,name in [(1800,'Cockpit_Gravel'),(4300,'Cockpit_Mud'),(9200,'Cockpit_Ford')]:
                    name+=('_Settle0' if stage=='base' else '')
                    if pos.x>=mark and name not in shots:shots.add(name);snap(name)
            if pos.x>11900 or gt()-drive_start>DRIVE_CAP_S:
                move.set_throttle_input(0);move.set_brake_input(1);move.set_handbrake_input(True)
                console('csvprofile stop')
                samples=[r for r in records if r['run']==label]
                summary=dict(run=label,wet=bool(run),settle=0 if stage in ('base','after') else 1,end_x_m=pos.x/100,max_lateral_m=max(abs(r['y_m']) for r in samples),volume_added_cm3=mud.total_lowered_cm3()-volume_start,max_sink_m=max(r['sink_m'] for r in samples),max_water_m=max(r['water_m'] for r in samples),elapsed_s=gt()-drive_start,
                    settle_frames=mud.get_settle_frames(),settle_mean_ms=round(mud.get_settle_mean_ms(),4),settle_max_ms=round(mud.get_settle_max_ms(),4),settle_awake_peak=mud.get_settle_awake_peak(),upload_mean_ms=round(mud.get_upload_mean_ms(),4),upload_max_ms=round(mud.get_upload_max_ms(),4),
                    settle_p99_ms=round(mud.get_settle_p99_ms(),4),upload_p99_ms=round(mud.get_upload_p99_ms(),4),
                    clod_frames=mud.get_clod_frames(),clod_mean_ms=round(mud.get_clod_mean_ms(),4),clod_p99_ms=round(mud.get_clod_p99_ms(),4),clod_max_ms=round(mud.get_clod_max_ms(),4),
                    settle_gate=gate(mud.get_settle_mean_ms(),mud.get_settle_p99_ms(),mud.get_settle_max_ms()) if mud.get_settle_frames()>0 else None,
                    clod_gate=gate(mud.get_clod_mean_ms(),mud.get_clod_p99_ms(),mud.get_clod_max_ms(),CLOD_GT_MEAN_MS) if mud.get_clod_frames()>0 else None,
                    throw=throw_counts(),clods=clod_counts())
                w0,f0=report['drive_wall0'].get(label,(wall,u.SystemLibrary.get_frame_count()))
                summary.update(time_base='simulated (physics) seconds',real_s=round(wall-w0,1),frames=u.SystemLibrary.get_frame_count()-f0,fps=round((u.SystemLibrary.get_frame_count()-f0)/max(.001,wall-w0),2))
                report['runs'].append(summary)
                if stage=='base':
                    # The baseline ends here; the main crossing starts on untouched ground in the same session and viewport.
                    restart_dry(1);stage='main';phase='settle';last=now;return
                if stage=='after':
                    # LM1b: the settle pair again, gt.Mud.Settle still 0, on the pair's lane (fresh since the reset) and
                    # from the very same camera, for the _Off pictures.
                    phase='pair_setup';last=now;return
                assert pos.x>11900,'Car did not complete route';assert summary['volume_added_cm3']>10000,'No deformation';assert summary['max_water_m']>.03,'No ford water contact';assert summary['max_lateral_m']<3.5,'Car left the test lane'
                if run==0:phase='pair_setup'
                else:phase='inspect'
                last=now
        elif phase=='pair_setup' and now-last>2:
            # The settle pair: a fresh rut on a fresh lane, a fixed camera behind the spot.
            spec=u.load_asset('/Game/GrandTour/ArtTests/LiveMudDrive/DA_MudDrive').spec;z=u.GTVehicleSetupLibrary.sample_terrain_height_cm(spec,PAIR_START_X,PAIR_Y)
            car.set_actor_location_and_rotation(u.Vector(PAIR_START_X,PAIR_Y,z+150),u.Rotator(),False,True);body=car.get_component_by_class(u.SkeletalMeshComponent);body.set_physics_linear_velocity(u.Vector());body.set_physics_angular_velocity_in_degrees(u.Vector());car.reset_driving_inputs();move.set_handbrake_input(True)
            pair.clear();pair.update(spot_x=PAIR_SPOT_X,lane_y=PAIR_Y,crossed={},settle=0 if stage=='after' else 1,trace=[])
            pair['patch']=next(p for p in u.GameplayStatics.get_all_actors_of_class(world,u.GTMudPatch) if p.bounds_min.x<=PAIR_SPOT_X<=p.bounds_max.x and p.bounds_min.y<=PAIR_Y<=p.bounds_max.y)
            phase='pair_hold';last=now
        elif phase=='pair_hold' and now-last>3:
            pc.set_view_target_with_blend(car,0.);move.set_handbrake_input(False);move.set_target_gear(1,True);phase='pair_drive';last=now;pair['release']=gt()
        elif phase=='pair_drive':
            pos,speed=drive_step(PAIR_Y)
            crawl_sample(gt(),'_off' if stage=='after' else '')
            wheels=car.get_traction().wheels
            for k,w in enumerate(wheels):
                c=w.contact_point
                if k not in pair['crossed'] and c.x>=PAIR_SPOT_X:pair['crossed'][k]=c.y
            if len(pair['crossed'])==len(wheels) and 'camera_set' not in pair:
                # The rut: the two contact lines on the -Y side, where they crossed the spot.
                ys=sorted(pair['crossed'].values());pair['own_rut_y']=sum(ys[:2])/2.
                if not pair_camera:
                    pair['rut_y']=pair['own_rut_y']
                    spec=u.load_asset('/Game/GrandTour/ArtTests/LiveMudDrive/DA_MudDrive').spec;zg=u.GTVehicleSetupLibrary.sample_terrain_height_cm(spec,PAIR_SPOT_X,pair['rut_y'])
                    cpos=u.Vector(PAIR_SPOT_X-320,pair['rut_y']-160,zg+150);ctarget=u.Vector(PAIR_SPOT_X+40,pair['rut_y'],zg-25)
                    pair_camera.update(location=cpos,rotation=u.MathLibrary.find_look_at_rotation(cpos,ctarget),rut_y=pair['rut_y'])
                else:
                    pair['rut_y']=pair_camera['rut_y']   # LM1b's _Off pair: the first pair's spot and camera, exactly
                camera.set_actor_location(pair_camera['location'],False,False);camera.set_actor_rotation(pair_camera['rotation'],False);camera.camera_component.set_field_of_view(55)
                pc.set_view_target_with_blend(camera,0.);pair['camera_set']=True
            if 'camera_set' in pair and 'core_cm_5'+('_off' if stage=='after' else '') not in pair:GATE.ready(world,pc)   # the watch is rendered
            if 'camera_set' in pair and 't0' not in pair and min(w.contact_point.x for w in wheels)>PAIR_SPOT_X+STAMP_REACH_CM:
                pair['t0']=gw();pair['left_at_x_m']=pos.x/100
            if pos.x>PAIR_SPOT_X+900:
                move.set_throttle_input(0);move.set_brake_input(1);move.set_handbrake_input(True);car.set_raw_steer(0.)
            sfx='_off' if stage=='after' else ''
            # LM1b trace: from the first wheel over the spot to the 5 s profile, the core cell's height, sheen and set timer
            # each tick, and the patch's awake tiles and sub-steps (what the field does between the two pictures).
            if pair['crossed'] and 'core_cm_5'+sfx not in pair:
                pair.setdefault('t_first',gw());xy=u.Vector2D(PAIR_SPOT_X,pair.get('rut_y',PAIR_Y-76.))
                pair['trace'].append(dict(t_first=round(gw()-pair['t_first'],3),t_left=round(gw()-pair['t0'],3) if 't0' in pair else None,h=round(mud.mud_height_cm_at(xy),3),fresh=round(mud.mud_fresh_at(xy),3),set_s=round(mud.mud_set_seconds_at(xy),3),awake=pair['patch'].last_awake_tiles,steps=pair['patch'].last_settle_steps,ms=round(pair['patch'].last_settle_ms,3)))
            if 't0' in pair and gw()-pair['t0']>=.3 and 'core_cm_0.3'+sfx not in pair:
                pair_profile('0.3'+sfx);shoot_now('Mud_Settle_0s'+sfx.replace('_off','_Off'))
            if 't0' in pair and gw()-pair['t0']>=5. and 'core_cm_5'+sfx not in pair:
                pair_profile('5'+sfx);shoot_now('Mud_Settle_5s'+sfx.replace('_off','_Off'))
                with open(OUT/'settle_profile.csv','w',newline='') as f:
                    wr=csv.DictWriter(f,fieldnames=['t_s','y_offset_cm','height_cm','fresh','detail_d']);wr.writeheader();wr.writerows(profile_rows)
                report['settle_pair'+sfx]={k:v for k,v in pair.items() if k not in ('crossed','mask','patch')}
                # LM2a housekeeping 4: the crawl's summary (the rows are in crawl.csv): how long the start took to cover 2.3 m.
                rows=[r for r in crawl_rows if r['settle']==(0 if stage=='after' else 1)]
                if rows:
                    x0=rows[0]['car_x_m'];moved=next((r['t_s'] for r in rows if r['car_x_m']-x0>=2.3),None)
                    report['crawl'+sfx]=dict(samples=len(rows),start_x_m=x0,seconds_to_2_3_m=moved,
                        max_rut_climb=max(r['rut_climb'] for r in rows),max_hold_drag_n=max(r['hold_drag_n'] for r in rows),max_abs_hold_lateral_n=max(abs(r['hold_lateral_n']) for r in rows),
                        max_ahead_minus_under_cm=max(r['field_ahead30_cm']-r['field_under_cm'] for r in rows))
                phase='pair_done';last=now
            if gt()-pair['release']>60:raise RuntimeError('Settle pair: the car did not leave the spot (60 game s)')
        elif phase=='pair_done' and now-last>3:
            if 'dark_line' not in report and 'dark_line_error' not in report:
                # The camera is still the pair's and the car is parked: nothing here is timed.
                try:report['dark_line']=dark_line_candidates()
                except Exception:report['dark_line_error']=traceback.format_exc()
            phase='aftercsv' if stage=='after' else 'inspect';last=now
        elif phase=='inspect' and now-last>4:
            phase='capturing';snap('Mud_After_'+('Wet' if run else 'Dry'),True);phase='aftershot';last=clock()
        elif phase=='aftershot' and now-last>6:
            if run==1:
                # Isolate the water draw without changing the saved map or simulation.
                for patch in u.GameplayStatics.get_all_actors_of_class(world,u.GTMudPatch):patch.water_mesh.set_visibility(False)
                phase='waterdiagnostic';last=now;return
            phase='capturing';snap('Boundary_Dry',True);phase='boundaryshot';last=clock()
        elif phase=='boundaryshot' and now-last>6:
            phase='capturing';snap('Mud_Long_Dry',True);phase='longshot';last=clock()
        elif phase=='longshot' and now-last>6 and 'spin' not in report:
            phase='spin_setup';last=now
        elif phase=='spin_setup' and now-last>2:
            # LM2a's spin test: a dead stop in the deepest mud of a fresh lane, held 3 s, then full throttle 3 s.
            b,x=spin_spot();spin.clear();spin.update(x=x,y=SPIN_Y,bog=round(b,3),trace=[])
            place_car(x,SPIN_Y);pc.set_view_target_with_blend(car,0.);car.get_spray().reset_throw_stats()
            spin['before']=dict(throw=throw_counts(),clods=clod_counts());phase='spin_hold';last=now
        elif phase=='spin_hold' and now-last>3:
            car.reset_driving_inputs();move.set_handbrake_input(False);move.set_brake_input(0.);move.set_target_gear(1,True);car.set_raw_steer(0.);move.set_throttle_input(1.)
            spin['start_x_m']=round(car.get_actor_location().x/100.,3);spin['t0']=gt();spin['at']=-1.;phase='spin';last=now
        elif phase=='spin':
            move.set_throttle_input(1.);move.set_brake_input(0.);car.set_raw_steer(0.)
            if gt()-spin['at']>=.1:
                spin['at']=gt()
                spin['trace'].append(dict(t_s=round(gt()-spin['t0'],2),x_m=round(car.get_actor_location().x/100.,3),wheels=[dict(slip_cm_s=round(w.slip_magnitude,1),slipping=bool(w.get_editor_property('bSlipping')),throw_share=round(w.throw_share,3),sinkage_m=round(w.sinkage,3),thrown_cm3=round(w.thrown_cm3,1)) for w in car.get_traction().wheels]))
            if gt()-spin['t0']>=SPIN_S:
                move.set_throttle_input(0.);move.set_brake_input(1.);move.set_handbrake_input(True);spin['end_x_m']=round(car.get_actor_location().x/100.,3);phase='spin_land';last=now
        elif phase=='spin_land' and now-last>3.5:
            # Every blob down (they live at most 3 s), the clods batched: the field per wheel, the volumes, the counts.
            spin['wheels']=spin_measure();spin['after']=dict(throw=throw_counts(),clods=clod_counts())
            report['spin']={k:v for k,v in spin.items() if k not in ('at','t0')}
            if pair_camera:
                camera.set_actor_location(pair_camera['location'],False,False);camera.set_actor_rotation(pair_camera['rotation'],False);camera.camera_component.set_field_of_view(55);pc.set_view_target_with_blend(camera,0.)
            path=OUT/'Mud_Clods_Dry.png';report['images'].append(str(path));pending_shot=(clock()+1.,path);phase='spin_shot1';last=now
        elif phase=='spin_shot1' and now-last>3:
            # LM3a housekeeping 2 (diagnose only): the same picture with the mud patch meshes' shadow casting off, for the
            # hard-edged black patches beside the near lumps (Mud_Clods_Dry_NoShadow.png). The clods keep theirs.
            for patch in u.GameplayStatics.get_all_actors_of_class(world,u.GTMudPatch):patch.get_editor_property('mesh').set_cast_shadow(False)
            path=OUT/'Mud_Clods_Dry_NoShadow.png';report['images'].append(str(path));pending_shot=(clock()+1.5,path);report['no_shadow_picture']=dict(mesh_cast_shadow=False,camera='the settle pair camera, as Mud_Clods_Dry.png')
            phase='noshadow_shot';last=now
        elif phase=='noshadow_shot' and now-last>4:
            for patch in u.GameplayStatics.get_all_actors_of_class(world,u.GTMudPatch):patch.get_editor_property('mesh').set_cast_shadow(True)
            phase='spin_shot1b';last=now
        elif phase=='spin_shot1b' and now-last>1:
            spec=u.load_asset('/Game/GrandTour/ArtTests/LiveMudDrive/DA_MudDrive').spec;zg=u.GTVehicleSetupLibrary.sample_terrain_height_cm(spec,spin['x'],SPIN_Y)
            aim_camera(u.Vector(spin['x']-320,SPIN_Y+160,zg+150),u.Vector(spin['x']+40,SPIN_Y,zg-25))
            path=OUT/'Mud_Spin_Dry.png';report['images'].append(str(path));pending_shot=(clock()+1.,path);phase='spin_shot2';last=now
        elif phase=='spin_shot2' and now-last>3:
            # LM2c: the owner's own view, on foot at eye level: 1.7 m up, 3 m behind where the settle pair's rut starts,
            # looking along it (Mud_OnFoot_Dry.png).
            spec=u.load_asset('/Game/GrandTour/ArtTests/LiveMudDrive/DA_MudDrive').spec;ry=pair_camera.get('rut_y',PAIR_Y-76.)
            cx=PAIR_START_X-300.;zc=u.GTVehicleSetupLibrary.sample_terrain_height_cm(spec,cx,ry);zt=u.GTVehicleSetupLibrary.sample_terrain_height_cm(spec,PAIR_START_X+900.,ry)
            aim_camera(u.Vector(cx,ry,zc+170.),u.Vector(PAIR_START_X+900.,ry,zt),65)
            report['on_foot_camera']=dict(location=[cx,ry,zc+170.],target=[PAIR_START_X+900.,ry,zt],fov=65)
            path=OUT/'Mud_OnFoot_Dry.png';report['images'].append(str(path));pending_shot=(clock()+1.,path);phase='spin_shot3';last=now
        elif phase=='spin_shot3' and now-last>3:
            phase='longshot';last=now-10.
        elif phase=='longshot' and now-last>6:
            # Replay the route over the first pass's tracks, retaining the field.
            spec=u.load_asset('/Game/GrandTour/ArtTests/LiveMudDrive/DA_MudDrive').spec;z=u.GTVehicleSetupLibrary.sample_terrain_height_cm(spec,500,0)
            car.set_actor_location_and_rotation(u.Vector(500,0,z+150),u.Rotator(),False,True);body=car.get_component_by_class(u.SkeletalMeshComponent);body.set_physics_linear_velocity(u.Vector());body.set_physics_angular_velocity_in_degrees(u.Vector());car.reset_driving_inputs();move.set_handbrake_input(True);run=1;phase='settle';last=now
        elif phase=='waterdiagnostic' and now-last>3:
            phase='capturing';snap('Mud_Diagnostic_NoRutWater',True);phase='diagnosticshot';last=clock()
        elif phase=='diagnosticshot' and now-last>6:
            for patch in u.GameplayStatics.get_all_actors_of_class(world,u.GTMudPatch):
                patch.water_mesh.set_visibility(True)
                patch.water_material.set_vector_parameter_value('DeepColor',u.LinearColor(.060,.041,.025,1))
                patch.water_material.set_scalar_parameter_value('DeepOpacity',.78)
                patch.water_material.set_scalar_parameter_value('WaterRoughness',.12)
                patch.water_material.set_scalar_parameter_value('GlossRoughness',.08)
            phase='tintcandidate';last=now
        elif phase=='tintcandidate' and now-last>3:
            phase='capturing';snap('Mud_PuddleTint_Candidate',True);phase='tintshot';last=clock()
        elif phase=='tintshot' and now-last>6:
            assert all(Path(p).exists() for p in report['images'])
            restart_dry(0);stage='after';run=0;phase='settle';last=now
        elif phase=='aftercsv' and now-last>4:
            phase='cap_done' if NO_PROFILE else 'cap_fill';last=now
        elif phase=='cap_fill':
            # LM2b: the clods at the cap, GPU with gt.Mud.Clods 1 and 0 from the settle camera (nothing else moving).
            console('gt.Mud.Clods 1');added=mud.fill_clods_for_test(1200)
            if pair_camera:camera.set_actor_location(pair_camera['location'],False,False);camera.set_actor_rotation(pair_camera['rotation'],False);camera.camera_component.set_field_of_view(55)
            pc.set_view_target_with_blend(camera,0.)
            report['clod_cap']=dict(added=added,clods=clod_counts());phase='cap_on_wait';last=now
        elif phase=='cap_on_wait' and now-last>3:
            mud.reset_settle_stats();csv_marks.append(('clods_cap_on',csv_files()));console('csvprofile start');phase='cap_on';last=now
        elif phase=='cap_on' and now-last>6:
            console('csvprofile stop');report['clod_cap']['on_game_thread']=gate(mud.get_clod_mean_ms(),mud.get_clod_p99_ms(),mud.get_clod_max_ms(),CLOD_GT_MEAN_MS) if mud.get_clod_frames()>0 else None
            console('gt.Mud.Clods 0');phase='cap_off_wait';last=now
        elif phase=='cap_off_wait' and now-last>3:
            csv_marks.append(('clods_cap_off',csv_files()));console('csvprofile start');phase='cap_off';last=now
        elif phase=='cap_off' and now-last>6:
            console('csvprofile stop');console('gt.Mud.Clods 1');phase='cap_done';last=now
        elif phase=='cap_done' and now-last>4:
            report['ok']=True;finish()
    except Exception:finish(traceback.format_exc())
handle=u.register_slate_post_tick_callback(tick)
