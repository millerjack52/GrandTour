"""Living mud LM3a + LM3b (docs/LIVING_MUD_PLAN.md LM3a, LM3b, docs/LIVE_SNOW_DRIVE.md): drive the real car down L_SnowDrive.

Play In Editor in a new 1440x900 window (as the mud check), Clear weather, low range and the diff lock, FULL THROTTLE
(LM3b; LM3a asked about 3.2 m/s), the mud check's steering.

LM3b, the feel (housekeeping 1). First the trials, each a pass 1 on fresh snow (the field reset between them) to 111 m:
trial 0 at LM3a's numbers (gt.Snow.Plough 0.35, gt.Snow.BellyDrag 1.0) for reference, trial 1 at the patch's own
(FGTDeformProfile::SnowDefaults()), then up to five more chosen by a fit until the targets land: the 35 cm stretches
outside the drift (A 40-66 m, B 85-110 m) at 8-15 km/h mean, the drift (70-80 m, 60 cm) at 3-6 km/h mean, never stopped
(under 0.1 m/s) for more than 1 s. The fit: in a segment at a steady speed the drive equals the drag, so from a trial's
own samples the plough per unit of SnowPlough and speed (a), the belly per unit of its scale (b) and the speed (v) give
the drag the grip carries, C = k a v / 10 + s b; the next (k, s) solve k a v* / 10 + s b = C for A and the drift at the
aimed speeds (11 and 4.2 km/h). Segment means are the distance over the time between the crossings.
Then the two passes at the landed numbers: pass 1 from 5 m to 125 m in fresh snow, the car back to 5 m, pass 2 in its own
trench. Each pass: completion, the largest lateral deviation, the segment speeds, the longest stop, the drift's mean
speed (the gate: pass 2 at least 1.15x pass 1), the belly's plough volume, the drag terms (snow_samples.csv), the cost of
Settle and the clods, the spray's throw (LM3b housekeeping 2: a wheel in a snow patch throws through the Snow kind).
After pass 2: the trench profiles (snow_profile.csv), and the pictures Snow_Long.png, Snow_Cockpit.png (pass 2 at 60 m),
Snow_Trench_Close.png, Snow_Glint.png with Snow_Glint_NoGlint.png (the same frame, GlintDensity 0) and Snow_Border.png,
with the screen boxes the wrapper counts pixels in (the glint's fresh-snow box; the border box and the strips either side
of it, on Art/tools/sample_border.ps1's pattern). Last, the cost of M_GT_Snow against the clay on the same patch: the
patch mesh wears M_GT_Snow's instance or a M_GT_Mud instance with the same field parameters, alternately twice each, a
5 s CSV profile each from one camera over the snow, GPU/Basepass (and Prepass, ShadowDepths, GPUTime) means.

LM3c (docs/LIVING_MUD_PLAN.md LM3c): no trials (TRIALS False): the passes run at the patch's own numbers (LM3b's landed
SnowPlough 0.78, SnowBellyDrag 0), nothing retuned, and the feel gates are read off pass 1 and pass 2 as before. After each
pass the berm's crest along the trench (the A segment, 40-66 m): on each side the highest field cell 95-185 cm off the
line per cell column, its mean and coefficient of variation. Snow_Trench_Close.png comes with the clods' screen boxes
(every live instance of the snow patch's clod HISMs projected from its world box, the nearest on screen) and the same
frame with the clods hidden (Snow_Trench_Close_NoClods.png), for the wrapper's clod-against-snow luminance; then
Snow_Floor_Close.png, looking down into the -Y tyre's floor beside the belly's channel at 50 m. In the cost step, the first
time each material is on, Substrate's material classification (r.Substrate.ViewMode 4: green Simple, yellow Single, red
Complex tiles) as Snow_Classify_<material>.png and a ProfileGPU dump into the log between LM3C_PROFILEGPU markers.

LM4 (docs/LIVING_MUD_PLAN.md LM4): the profiles and the berm read the patch's own cell (6.25 cm; 12.5 with gt.Snow.FineGrid
0). Two more pictures after Snow_Floor_Close.png: Snow_GoW_View.png (the God of War reference's view: 2.5 m up, 2 m
behind-left of the +Y tyre track, about 35 degrees down along it) and Snow_OnFoot.png (eye level, 1.65 m over the -Y tyre's
trench floor, looking along it). After the main session (the passes, the pictures, the material's cost), the FineGrid pair
in the same session: gt.Snow.FineGrid 0 and then 1 again, each time the patches rebuilt (UGTMudSubsystem::
RebuildPatchesForTest, which reads the switch as a Play restart would), pass 1 and pass 2 driven again (Settle and upload
p99, the passes' CSV game-thread and GPU means), then two 5 s profiles from the cost camera with M_GT_Snow on; the mesh's
cells, vertices and triangles per session. Each pass reports the shards spawned (lip, floor, throw) and the lip plates that
fell in.

LM4b (docs/LIVING_MUD_PLAN.md LM4b): Snow_GoW_View.png and Snow_OnFoot.png each with gt.Snow.Parallax 0 (the plain name) and 1
(_Parallax1), then Snow_Edge_Close.png (60 cm out from the -Y trench's outer lip at 47 m, 30 cm over the snow, looking along
the lip) with its _Parallax1 twin and Snow_Edge_Mask.png (the same frame with M_GT_Snow's SnowEdgeDebug 1: the edge mask E in
red, the parallax's reach green where it is on). After the material's cost, the parallax pair in the same session: from the
cost camera (the strip view) and from the edge camera (E over 0.2 over much of the frame), 5 s profiles at gt.Snow.Parallax
0, 1, 1, 0 each; the GPU, game thread and base pass per view and setting, and 1 - 0. Then the FineGrid pair as LM4's.

LM4c (docs/LIVING_MUD_PLAN.md LM4c): the berm's crest read out to 250 cm off the line (the plough's band is 85 cm now, falling
from the wall, in piles). After Snow_Edge_Mask.png, the collapse pair: a fresh tyre cut on untouched snow 2.9 m to the +Y side of
the line from 90 to 99 m, stamped at once (UGTMudSubsystem::CutSnowTrenchForTest: 28 cm wide, 5 cm sinkage, 5 cm strokes), the
camera across the trench from the collapsing segment nearest 47.5 m, Snow_Collapse_0s.png 0.2 s after the cut and
Snow_Collapse_4s.png 4 s after it (every delay is 0.5-3 s); the collapses that fell in between, from the patch's readouts. Each
pass reports the collapses (fired, volume, clumps).

LM4d (docs/LIVING_MUD_PLAN.md LM4d): Snow_Channel_Close.png after Snow_Floor_Close.png - low along the belly's channel at 50-53 m
(60 cm over its floor, 20 cm off the line), its undulating scrape, smear ridges and spill; each pass reports the smear ridges' and
the spill's volume and the channel's clumps.
"""
import unreal as u,json,time,math,traceback,csv,statistics
from pathlib import Path
ROOT=Path(u.Paths.project_dir()).resolve()
OUT=ROOT/'Art/Export/LiveSnowDrive';OUT.mkdir(parents=True,exist_ok=True)
CSV_DIR=ROOT/'Saved/Profiling/CSV'
LEVEL='/Game/GrandTour/ArtTests/LiveSnowDrive/L_SnowDrive';SPEC='/Game/GrandTour/ArtTests/LiveSnowDrive/DA_SnowDrive'
CLAY='/Game/GrandTour/Materials/M_GT_Mud'
u.EditorPythonScripting.set_keep_python_script_alive(True)
VIEW=(1440,900)
START_X=500.;END_X=12500.;DONE_X=12000.;SNOW_X=(3000.,11000.);DRIFT_X=(7000.,8000.);COCKPIT_X=6000.
# LM3b: the segments (cm). A and B are the 35 cm outside the drift past the entry's settling and the drift's ramps.
SEGS={'entry':(3000.,6600.),'A':(4000.,6600.),'drift':(7000.,8000.),'B':(8500.,11000.)}
MARKS=sorted(set(x for seg in SEGS.values() for x in seg)|set(SNOW_X)|set(DRIFT_X))
BAND_35=(8.,15.);BAND_DRIFT=(3.,6.);STOP_MAX_S=1.;STOP_MPS=.1
AIM_A_KMH=11.;AIM_D_KMH=4.2
TRIAL_END_X=11100.;TRIAL_STALL_S=5.;TRIAL_MAX_S=150.;MAX_TRIALS=7
PASS_S=300.;STALL_S=15.;STALL_MPS=.1
PROFILE_X=(5000.,7500.)
GATE_MEAN_MS=.3;GATE_P99_MS=.7
APRON_MIN=(2380.,-620.);APRON_MAX=(11630.,630.)
TRIALS=False   # LM3c: the patch's own numbers, no retune (LM3b's trials and fit stay behind this switch)
# LM4: the FineGrid pair after the main session (gt.Snow.FineGrid 1 = the main), each its two passes and two cost profiles.
GRID_SESSIONS=[('coarse',0),('fine',1)];grid_queue=list(GRID_SESSIONS)
# LM4b: the parallax cost, per view (the cost camera, the edge camera) at gt.Snow.Parallax 0, 1, 1, 0.
PX_ORDER=[0,1,1,0];px_steps=[]
BERM_X=(4000.,6600.);BERM_Y=(95.,250.)   # LM3c: the berm's crest, the A segment, off the line (LM4c: out to 250, the 85 cm band)
COLLAPSE_Y=290.;COLLAPSE_X=(9000.,9900.);COLLAPSE_AT_X=9450.   # LM4c: the collapse pair's fresh cut (the B segment, clear of the 40-60 m pictures and the glint's snow)
CLOD_BOX_MAX=60;CLOD_MAX_M=15.;CLOD_MIN_PX=6.
phase='load';last=time.monotonic();start=last;sample_at=0;pending_shot=None;grid_cost_n=0
report={'ok':False,'passes':[],'trials':[],'images':[],'profiles':[],'viewports':[],'boxes':{},'cost':[],'grid':[]}
samples=[];profile_rows=[];csv_marks=[];shots=set()
run=None;queue=[];npass=0;cost_steps=[];cost_at=0
def console(cmd):
    u.SystemLibrary.execute_console_command(world,cmd,pc)
def csv_files():
    return set(p.name for p in CSV_DIR.glob('*.csv')) if CSV_DIR.exists() else set()
def begin_play():
    lib=getattr(u,'GTPlayWindowLibrary',None)
    if lib and lib.request_play_in_new_window(VIEW[0],VIEW[1]):return 'new window %dx%d'%VIEW
    u.get_editor_subsystem(u.LevelEditorSubsystem).editor_request_begin_play();return 'level viewport'
def spec():
    return u.load_asset(SPEC).spec
def ground(x,y):
    return u.GTVehicleSetupLibrary.sample_terrain_height_cm(spec(),x,y)
def surface_z(x,y):
    # The snow surface (the ground, the snow top and the field over it) or the ground outside the patch.
    xy=u.Vector2D(x,y);return ground(x,y)+mud.snow_top_cm_at(xy)+mud.mud_height_cm_at(xy)
def column_stats(rows,header,name):
    if name not in header:return None
    i=header.index(name);vals=[]
    for r in rows:
        try:vals.append(float(r[i]))
        except (ValueError,IndexError):pass
    if not vals:return None
    vals.sort()
    return dict(mean=round(statistics.fmean(vals),3),median=round(statistics.median(vals),3),p99=round(vals[min(len(vals)-1,max(0,math.ceil(.99*len(vals))-1))],3),max=round(vals[-1],3))
COLUMNS=['FrameTime','GameThreadTime','GPUTime','GPU/Basepass','GPU/Prepass','GPU/ShadowDepths','GTMud/GameThread/Settle','GTMud/GameThread/Upload','GTMud/GameThread/Clods']
def parse_profiles():
    seen=[m[1] for m in csv_marks]+[csv_files()]
    for k,(label,before) in enumerate(csv_marks):
        new=sorted(seen[k+1]-before);entry=dict(run=label,csv=None)
        if new:
            path=CSV_DIR/new[0];entry['csv']=str(path)
            with open(path,newline='') as f:rows=list(csv.reader(f))
            header=rows[0];body=[]
            for r in rows[1:]:
                if not r or r[0].startswith('[') or r[0]=='EVENTS':break
                body.append(r)
            entry['frames']=len(body)
            for name in COLUMNS:
                stats=column_stats(body,header,name)
                if stats:entry[name]=stats
        report['profiles'].append(entry)
    # LM3b: the snow material's cost against the clay's, the mean of each material's two profiles.
    by={}
    for e in report['profiles']:
        if str(e['run']).startswith('cost_'):by.setdefault(e['run'].split('_')[1],[]).append(e)
    if by:
        out={}
        for mat,entries in by.items():
            out[mat]={col:round(statistics.fmean([e[col]['mean'] for e in entries if col in e]),4) for col in ['GPU/Basepass','GPU/Prepass','GPU/ShadowDepths','GPUTime','FrameTime'] if any(col in e for e in entries)}
            out[mat]['frames']=sum(e.get('frames',0) for e in entries)
        if 'snow' in out and 'clay' in out:
            out['snow_minus_clay']={col:round(out['snow'][col]-out['clay'][col],4) for col in out['snow'] if col in out['clay'] and col!='frames'}
        if 'snow' in out and 'nosss' in out:
            out['snow_minus_nosss']={col:round(out['snow'][col]-out['nosss'][col],4) for col in out['snow'] if col in out['nosss'] and col!='frames'}
        # Every GPU pass that differs between two of the materials by 0.03 ms or more (the CSVs' means).
        try:
            per={}
            for e in report['profiles']:
                if not str(e['run']).startswith('cost_') or not e.get('csv'):continue
                with open(e['csv'],newline='') as f:rows=list(csv.reader(f))
                h=rows[0];body=[x for x in rows[1:] if x and not x[0].startswith('[') and x[0]!='EVENTS']
                for i,col in enumerate(h):
                    if not col.startswith('GPU/'):continue
                    v=[]
                    for x in body:
                        try:v.append(float(x[i]))
                        except (ValueError,IndexError):pass
                    if v:per.setdefault(col,{}).setdefault(e['run'].split('_')[1],[]).append(statistics.fmean(v))
            def diff(a,b):
                return {col:round(statistics.fmean(d[a])-statistics.fmean(d[b]),3) for col,d in per.items() if a in d and b in d and abs(statistics.fmean(d[a])-statistics.fmean(d[b]))>=.03}
            out['passes_snow_minus_clay']=diff('snow','clay');out['passes_snow_minus_nosss']=diff('snow','nosss')
        except Exception:out['passes_error']=traceback.format_exc()
        report['cost_summary']=out
    # LM4b: the parallax pair (px_<view>_<parallax>_<n>): the means per view and setting, and 1 - 0 per view.
    px={}
    for e in report['profiles']:
        run_=str(e['run'])
        if run_.startswith('px_'):
            parts=run_.split('_');px.setdefault(parts[1],{}).setdefault(parts[2],[]).append(e)
    if px:
        pout={}
        for view,by_val in px.items():
            pout[view]={}
            for val,entries in by_val.items():
                pout[view][val]={col:round(statistics.fmean([e[col]['mean'] for e in entries if col in e]),4) for col in ['GPUTime','GameThreadTime','FrameTime','GPU/Basepass'] if any(col in e for e in entries)}
                pout[view][val]['profiles']=len(entries);pout[view][val]['frames']=sum(e.get('frames',0) for e in entries)
            if '0' in pout[view] and '1' in pout[view]:
                pout[view]['on_minus_off']={col:round(pout[view]['1'][col]-pout[view]['0'][col],4) for col in pout[view]['1'] if col in pout[view]['0'] and col not in ('profiles','frames')}
        report['parallax_summary']=pout
    # LM4: the FineGrid sessions' cost-camera profiles (grid_<label>_<n>) and the main session's M_GT_Snow ones (cost_snow_<n>, FineGrid 1).
    grid={}
    for e in report['profiles']:
        run_=str(e['run'])
        key=('main' if run_.startswith('cost_snow_') else run_.split('_')[1]) if (run_.startswith('grid_') or run_.startswith('cost_snow_')) else None
        if key:grid.setdefault(key,[]).append(e)
    if grid:
        gout={}
        for key,entries in grid.items():
            gout[key]={col:round(statistics.fmean([e[col]['mean'] for e in entries if col in e]),4) for col in ['GPUTime','GameThreadTime','FrameTime','GPU/Basepass','GPU/ShadowDepths'] if any(col in e for e in entries)}
            gout[key]['profiles']=len(entries);gout[key]['frames']=sum(e.get('frames',0) for e in entries)
        report['grid_summary']=gout
def finish(error=None):
    global phase
    phase='finished'
    if error:report['error']=error
    try:console('gt.Snow.Plough -1');console('gt.Snow.BellyDrag -1');console('gt.Snow.Parallax -1')
    except Exception:pass
    try:parse_profiles()
    except Exception:report['profile_error']=traceback.format_exc()
    try:
        if samples:
            keys=[]
            for r in samples:
                for k in r:
                    if k not in keys:keys.append(k)
            with open(OUT/'snow_samples.csv','w',newline='') as f:
                wr=csv.DictWriter(f,fieldnames=keys);wr.writeheader();wr.writerows(samples)
        if profile_rows:
            with open(OUT/'snow_profile.csv','w',newline='') as f:
                wr=csv.DictWriter(f,fieldnames=list(profile_rows[0].keys()));wr.writeheader();wr.writerows(profile_rows)
    except Exception:report['csv_error']=traceback.format_exc()
    (OUT/'drive-report.json').write_text(json.dumps(report,indent=2));u.unregister_slate_post_tick_callback(handle);u.EditorLevelLibrary.editor_end_play();u.SystemLibrary.quit_editor()
def gate(mean,p99,mx):
    return dict(mean_ms=round(mean,4),p99_ms=round(p99,4),max_ms=round(mx,4),ok=bool(mean<=GATE_MEAN_MS and p99<=GATE_P99_MS))
def place_car(x,y):
    z=ground(x,y);car.set_actor_location_and_rotation(u.Vector(x,y,z+150),u.Rotator(),False,True);body=car.get_component_by_class(u.SkeletalMeshComponent);body.set_physics_linear_velocity(u.Vector());body.set_physics_angular_velocity_in_degrees(u.Vector());car.reset_driving_inputs();move.set_handbrake_input(True)
def aim_camera(cpos,ctarget,fov=55):
    camera.set_actor_location(cpos,False,False);camera.set_actor_rotation(u.MathLibrary.find_look_at_rotation(cpos,ctarget),False);camera.camera_component.set_field_of_view(fov);pc.set_view_target_with_blend(camera,0.)
def queue_shot(name,delay=1.):
    global pending_shot
    path=OUT/(name+'.png');report['images'].append(str(path));pending_shot=(time.monotonic()+delay,path)
def project(pt):
    r=u.GameplayStatics.project_world_to_screen(pc,pt,False)
    if r is None:return None
    if isinstance(r,tuple):
        if len(r)==2 and isinstance(r[0],bool):return r[1] if r[0] else None
        return r[0]
    return r
def screen_box(points):
    sp=[project(p) for p in points]
    on=sum(1 for s in sp if s is not None and 0<=s.x<=VIEW[0] and 0<=s.y<=VIEW[1])
    xs=[s.x for s in sp if s is not None];ys=[s.y for s in sp if s is not None]
    return dict(x0=round(min(xs),1),y0=round(min(ys),1),x1=round(max(xs),1),y1=round(max(ys),1),corners_on_screen=on,corners=len(points)) if xs else None
def ground_rect(x0,x1,y0,y1,zf):
    return [u.Vector(x,y,zf(x,y)) for x in (x0,x1) for y in (y0,y1)]
def track_offset(side,default):
    # LM4: how far off the line the tyre's trench floor lies on that side (the last profile across at 50 m), cm.
    for a in reversed(report.get('profiles_across',[])):
        if abs(a['x_cm']-5000.)<20.:
            for t in a['trenches']:
                if t['side']==side:return abs(t['floor_y_off_cm'])
    return default
def drive_step(target_y):
    # LM3b: full throttle (the brake only past 12 m/s, a guard), the mud check's steering.
    pos=car.get_actor_location();speed=car.get_velocity().length()/100.;yaw=car.get_actor_rotation().yaw
    target_yaw=math.degrees(math.atan2(target_y-pos.y,650.));error=(target_yaw-yaw+180)%360-180;car.set_raw_steer(max(-.65,min(.65,error/24)))
    move.set_throttle_input(1.);move.set_brake_input(.4 if speed>12. else 0.)
    return pos,speed
def snow_patch():
    return next((p for p in u.GameplayStatics.get_all_actors_of_class(world,u.GTMudPatch) if p.medium==u.GTDeformMedium.SNOW),None)
def surface_material(m):
    # LM4e cut 4: the surface may be chunks (gt.Snow.MeshLod); the patch's helper sets every one.
    p=snow_patch()
    if hasattr(p,'set_surface_material_for_test'):p.set_surface_material_for_test(m)
    else:p.mesh.set_material(0,m)
def clod_hisms():
    p=snow_patch()
    return list(p.get_components_by_class(u.HierarchicalInstancedStaticMeshComponent)) if p else []
def instance_transform(h,i):
    r=h.get_instance_transform(i,True)
    if isinstance(r,tuple):return r[1] if r[0] else None
    return r
def clod_boxes():
    # LM3c item 4: every live clod (an instance at a non-zero scale) of the snow patch's clod HISMs, its world box (the mesh's
    # box extent x its largest scale, every way, so a rotated clod is inside it) projected to the screen; the nearest
    # CLOD_BOX_MAX wholly on screen, within CLOD_MAX_M of the camera and CLOD_MIN_PX across.
    cam=camera.get_actor_location();out=[];live=0
    for h in clod_hisms():
        mesh=h.get_editor_property('static_mesh')
        if not mesh:continue
        e=mesh.get_bounds().box_extent;ext=max(e.x,e.y,e.z)
        for i in range(h.get_instance_count()):
            t=instance_transform(h,i)
            if t is None:continue
            sc=t.scale3d;k=max(abs(sc.x),abs(sc.y),abs(sc.z))
            if k<1e-3:continue
            live+=1;c=t.translation;r=ext*k
            d=math.sqrt((c.x-cam.x)**2+(c.y-cam.y)**2+(c.z-cam.z)**2)
            if d>CLOD_MAX_M*100.:continue
            b=screen_box([u.Vector(c.x+sx*r,c.y+sy*r,c.z+sz*r) for sx in (-1,1) for sy in (-1,1) for sz in (-1,1)])
            if not b or b['corners_on_screen']<8 or b['x1']-b['x0']<CLOD_MIN_PX:continue
            b.update(dist_cm=round(d,1),radius_cm=round(r,2),hism=h.get_name(),instance=i,world=[round(c.x,1),round(c.y,1),round(c.z,1)])
            out.append(b)
    out.sort(key=lambda b:b['dist_cm'])
    return out[:CLOD_BOX_MAX],live
def berm_crest(label,yc):
    # LM3c item 3, on the strip: per cell column of the A segment, on each side, the highest field cell (over the snow top,
    # the lumps included) BERM_Y off the line; the mean and the coefficient of variation (sd / mean) per side.
    p=snow_patch();b0=p.bounds_min;out=dict(after_pass=label,x_cm=list(BERM_X),y_off_cm=list(BERM_Y));c=patch_cell(p);out['cell_cm']=round(c,3)
    xs=cell_centres(BERM_X[0],BERM_X[1],b0.x,c)
    for side in (-1,1):
        ys=cell_centres(yc+BERM_Y[0],yc+BERM_Y[1],b0.y,c) if side>0 else cell_centres(yc-BERM_Y[1],yc-BERM_Y[0],b0.y,c)
        peaks=[max(mud.mud_height_cm_at(u.Vector2D(x,y)) for y in ys) for x in xs]
        m=statistics.fmean(peaks);sd=statistics.pstdev(peaks);srt=sorted(peaks);med=srt[len(srt)//2];p90=srt[min(len(srt)-1,int(.9*len(srt)))]
        # LM3c follow-up: the spikes, the 90th percentile and the highest against the median (the test asks 1.3x and 1.6x at most).
        out['+Y' if side>0 else '-Y']=dict(stations=len(peaks),mean_cm=round(m,3),sd_cm=round(sd,3),cv=round(sd/m,4) if m>0 else None,min_cm=round(min(peaks),2),max_cm=round(max(peaks),2),
            median_cm=round(med,2),p90_cm=round(p90,2),p90_x_median=round(p90/med,3) if med>0 else None,max_x_median=round(max(peaks)/med,3) if med>0 else None)
    cvs=[out[k]['cv'] for k in ('-Y','+Y') if out[k]['cv'] is not None]
    out['cv_mean']=round(statistics.fmean(cvs),4) if cvs else None
    report['berm_crest']=report.get('berm_crest',[])+[out]
def patch_cell(p=None):
    # LM4: the patch's own cell (6.25 cm; 12.5 with gt.Snow.FineGrid 0).
    p=p or snow_patch();return (p.bounds_max.x-p.bounds_min.x)/max(1,p.cells_x)
def cell_centres(lo,hi,origin,cell=12.5):
    i0=math.ceil((lo-origin)/cell-.5);i1=math.floor((hi-origin)/cell-.5)
    return [origin+(i+.5)*cell for i in range(i0,i1+1)]
def trench_profile(label,x_want,y_centre):
    p=snow_patch();b0=p.bounds_min;c=patch_cell(p)
    x=min(cell_centres(x_want-c,x_want+c,b0.x,c),key=lambda v:abs(v-x_want))
    rows=[]
    for y in cell_centres(y_centre-260.,y_centre+260.,b0.y,c):
        xy=u.Vector2D(x,y);top=mud.snow_top_cm_at(xy);h=mud.mud_height_cm_at(xy)
        rows.append(dict(after_pass=label,x_cm=round(x,2),y_cm=round(y,2),y_off_cm=round(y-y_centre,2),snow_top_cm=round(top,3),field_cm=round(h,3),surface_over_ground_cm=round(top+h,3),lump_cm=round(mud.mud_lump_cm_at(xy),3)))
    profile_rows.extend(rows)
    out=dict(after_pass=label,x_cm=round(x,2),y_centre_cm=round(y_centre,1),snow_top_cm=round(max(r['snow_top_cm'] for r in rows),2),centre_field_cm=None,trenches=[])
    mid=min(rows,key=lambda r:abs(r['y_off_cm']));out['centre_field_cm']=mid['field_cm'];out['centre_over_ground_cm']=mid['surface_over_ground_cm']
    for side in (-1,1):
        window=[r for r in rows if 30.<=side*r['y_off_cm']<=130.]
        if not window:continue
        floor=min(window,key=lambda r:r['surface_over_ground_cm']);k=rows.index(floor)
        lip=floor;wall=0.;j=k
        while 0<=j+side<len(rows) and side*(rows[j+side]['y_off_cm']-floor['y_off_cm'])<=110.:
            step=rows[j+side]['field_cm']-rows[j]['field_cm'];wall=max(wall,step)
            if rows[j+side]['field_cm']>lip['field_cm']:lip=rows[j+side]
            j+=side
        out['trenches'].append(dict(side='+Y' if side>0 else '-Y',floor_y_off_cm=floor['y_off_cm'],floor_over_ground_cm=floor['surface_over_ground_cm'],floor_field_cm=floor['field_cm'],
            lip_y_off_cm=lip['y_off_cm'],lip_over_snow_top_cm=lip['field_cm'],lip_over_ground_cm=lip['surface_over_ground_cm'],wall_step_cm=round(wall,2),wall_deg=round(math.degrees(math.atan(wall/c)),1)))
    report['profiles_across'] =report.get('profiles_across',[])+[out]
def sample(now,pos,speed):
    t=car.get_traction();wheels=t.wheels
    row=dict(run=run['label'],npass=run.get('npass',0),t_s=round(now-run['start'],3),x_m=round(pos.x/100.,3),y_m=round(pos.y/100.,3),speed_mps=round(speed,3),
        belly_snow_cm=round(t.belly_snow_cm,2),belly_in_snow=bool(t.get_editor_property('bBellyInSnow')),belly_ploughed_cm3=round(t.belly_ploughed_cm3,0))
    for k,w in enumerate(wheels):
        row.update({'w%d_sink_cm'%k:round(w.sinkage*100.,2),'w%d_snow_ahead_cm'%k:round(w.snow_ahead_cm,2),'w%d_rr'%k:round(w.rolling_resistance,4),'w%d_surface'%k:round(w.diag_surface_drag,4),
            'w%d_plough'%k:round(w.diag_plough_drag,4),'w%d_belly'%k:round(w.diag_belly_drag,4),'w%d_friction_scale'%k:round(w.friction_scale,4),'w%d_slip'%k:round(w.slip_magnitude,1),'w%d_in_snow'%k:bool(w.get_editor_property('bInSnowPatch'))})
    samples.append(row)
def wmean(r,key):
    return statistics.fmean([r['w%d_%s'%(k,key)] for k in range(4)])
def seg_speeds(c):
    out={}
    for name,(lo,hi) in SEGS.items():
        if lo in c and hi in c and c[hi]>c[lo]:
            mps=(hi-lo)/100./(c[hi]-c[lo]);out[name]=dict(s=round(c[hi]-c[lo],3),mps=round(mps,3),kmh=round(mps*3.6,2))
        else:out[name]=None
    a=out.get('A');b=out.get('B')
    if a and b:
        mps=((SEGS['A'][1]-SEGS['A'][0])+(SEGS['B'][1]-SEGS['B'][0]))/100./(a['s']+b['s']);out['35cm']=dict(s=round(a['s']+b['s'],3),mps=round(mps,3),kmh=round(mps*3.6,2))
    else:out['35cm']=None
    return out
def landed(seg,stop_s):
    ok=lambda v,band:v is not None and band[0]<=v['kmh']<=band[1]
    return bool(ok(seg['A'],BAND_35) and ok(seg['B'],BAND_35) and ok(seg['drift'],BAND_DRIFT) and stop_s<=STOP_MAX_S)
def miss(seg,stop_s):
    # How far outside the bands a trial is (km/h, normalised by the band's width), for the best of the trials if none lands.
    def out(v,band):
        if v is None:return 3.
        x=v['kmh'];return max(0.,band[0]-x,x-band[1])/(band[1]-band[0])
    return out(seg['A'],BAND_35)+out(seg['B'],BAND_35)+out(seg['drift'],BAND_DRIFT)+max(0.,stop_s-STOP_MAX_S)
def fit_terms(rows,k,s,lo,hi,v_mean):
    rs=[r for r in rows if lo/100.<=r['x_m']<=hi/100.]
    a=[wmean(r,'plough')/(k*r['speed_mps']/10.) for r in rs if k>0 and r['speed_mps']>.15]
    b=[wmean(r,'belly')/s for r in rs if s>0]
    a=statistics.fmean(a) if a else None;b=statistics.fmean(b) if b else None
    return dict(a=round(a,4) if a else None,b=round(b,4) if b else None,v=v_mean,rows=len(rs))
def next_trial(done):
    # The latest trial's drag carried (C) per segment; a and b the mean over the trials that have them.
    last=done[-1];k,s=last['plough'],last['belly']
    def mean_of(seg,key):
        v=[t['fit'][seg][key] for t in done if t['fit'][seg][key]]
        return statistics.fmean(v) if v else None
    aA,bA,aD,bD=mean_of('A','a'),mean_of('A','b'),mean_of('drift','a'),mean_of('drift','b')
    vA=last['seg']['A']['mps'] if last['seg']['A'] else None;vD=last['seg']['drift']['mps'] if last['seg']['drift'] else None
    if not (aA and bA and vA):return None
    CA=k*aA*vA/10.+s*bA
    CD=(k*aD*vD/10.+s*bD) if (vD and aD and bD) else ((.97*s*bD) if bD else None)
    tA=AIM_A_KMH/3.6;tD=AIM_D_KMH/3.6
    if CD is not None and aD and bD:
        m00,m01,m10,m11=aA*tA/10.,bA,aD*tD/10.,bD;det=m00*m11-m01*m10
        if abs(det)>1e-7:
            kn=(CA*m11-m01*CD)/det;sn=(m00*CD-m10*CA)/det
        else:kn,sn=None,None
    else:kn,sn=None,s
    if sn is None or kn is None or kn<=0:sn=min(max(s,0.),2.);kn=(CA-sn*bA)/(aA*tA/10.)
    if sn<0 or sn>2:sn=min(max(sn,0.),2.);kn=(CA-sn*bA)/(aA*tA/10.)
    kn=min(max(kn,.05),3.)
    return dict(plough=round(kn,3),belly=round(sn,3),why='fit: C_A %.4f, C_drift %s, a_A %.4f, b_A %.4f, a_drift %s, b_drift %s'%(CA,'%.4f'%CD if CD is not None else None,aA,bA,'%.4f'%aD if aD else None,'%.4f'%bD if bD else None))
def start_run(kind,label,plough=None,belly=None,npass_=0,session='main'):
    # plough / belly None: the patch's own (the cvars at -1).
    global run,phase,last
    console('gt.Snow.Plough %s'%(plough if plough is not None else -1));console('gt.Snow.BellyDrag %s'%(belly if belly is not None else -1))
    if kind=='trial' or npass_==1:mud.reset_fields_for_test()
    run=dict(kind=kind,label=label,plough_cvar=plough,belly_cvar=belly,npass=npass_,session=session)
    place_car(START_X,0.);phase='settle';last=time.monotonic()
def end_run(now,pos,why):
    global phase,last
    move.set_throttle_input(0);move.set_brake_input(1);move.set_handbrake_input(True);car.set_raw_steer(0.)
    rows=[r for r in samples if r['run']==run['label']]
    c=run['cross'];seg=seg_speeds(c)
    p=snow_patch()
    k=run['plough_cvar'] if run['plough_cvar'] is not None else p.snow_plough
    s=run['belly_cvar'] if run['belly_cvar'] is not None else p.snow_belly_drag
    stop_s=round(run['stop_max'],3)
    if run['kind']=='trial':
        fit={name:fit_terms(rows,k,s,lo,hi,(seg[name] or {}).get('mps')) for name,(lo,hi) in SEGS.items() if name in ('A','drift','B')}
        t=dict(trial=len(report['trials']),label=run['label'],plough=round(k,4),belly=round(s,4),from_patch=run['plough_cvar'] is None,ended=why,end_x_m=round(pos.x/100.,2),elapsed_s=round(now-run['start'],2),
            seg=seg,longest_stop_s=stop_s,longest_stop_at_m=run['stop_at'],fit=fit)
        t['landed']=landed(seg,stop_s);t['miss']=round(miss(seg,stop_s),3)
        report['trials'].append(t);phase='after_trial';last=now
        return
    console('csvprofile stop')
    snow=[r for r in rows if SNOW_X[0]/100.<=r['x_m']<=SNOW_X[1]/100.]
    drift_s=(c[DRIFT_X[1]]-c[DRIFT_X[0]]) if (DRIFT_X[0] in c and DRIFT_X[1] in c) else None
    drift=[r for r in rows if DRIFT_X[0]/100.<=r['x_m']<=DRIFT_X[1]/100.]
    sp=car.get_spray()
    summary=dict(npass=run['npass'],plough=round(k,4),belly=round(s,4),ended=why,end_x_m=round(pos.x/100.,3),completed=bool(pos.x>=DONE_X),elapsed_s=round(now-run['start'],2),
        max_lateral_m=round(max((abs(r['y_m']) for r in snow),default=0.),3),seg=seg,longest_stop_s=stop_s,longest_stop_at_m=run['stop_at'],
        drift_s=round(drift_s,3) if drift_s else None,drift_mean_mps=round((DRIFT_X[1]-DRIFT_X[0])/100./drift_s,3) if drift_s else None,
        drift_min_mps=round(min((r['speed_mps'] for r in drift),default=0.),3),drift_max_belly_snow_cm=round(max((r['belly_snow_cm'] for r in drift),default=0.),2),
        drift_mean_rr=round(statistics.fmean([wmean(r,'rr') for r in drift]),4) if drift else None,
        drift_mean_plough=round(statistics.fmean([wmean(r,'plough') for r in drift]),4) if drift else None,
        drift_mean_belly=round(statistics.fmean([wmean(r,'belly') for r in drift]),4) if drift else None,
        drift_mean_surface=round(statistics.fmean([wmean(r,'surface') for r in drift]),4) if drift else None,
        drift_mean_friction_scale=round(statistics.fmean([wmean(r,'friction_scale') for r in drift]),4) if drift else None,
        a_mean_rr=round(statistics.fmean([wmean(r,'rr') for r in rows if SEGS['A'][0]/100.<=r['x_m']<=SEGS['A'][1]/100.]),4) if any(SEGS['A'][0]/100.<=r['x_m']<=SEGS['A'][1]/100. for r in rows) else None,
        snow_mean_mps=round(statistics.fmean([r['speed_mps'] for r in snow]),3) if snow else None,
        plough_cm3=round(mud.snow_ploughed_cm3()-run['plough0'],0),plough_berm_cm3=round(mud.snow_plough_berm_cm3()-run['berm0'],0),lowered_cm3=round(mud.total_lowered_cm3()-run['lowered0'],0),
        settle_frames=mud.get_settle_frames(),settle=gate(mud.get_settle_mean_ms(),mud.get_settle_p99_ms(),mud.get_settle_max_ms()) if mud.get_settle_frames()>0 else None,settle_awake_peak=mud.get_settle_awake_peak(),
        upload_mean_ms=round(mud.get_upload_mean_ms(),4),upload_p99_ms=round(mud.get_upload_p99_ms(),4),upload_max_ms=round(mud.get_upload_max_ms(),4),
        clod_frames=mud.get_clod_frames(),clods=gate(mud.get_clod_mean_ms(),mud.get_clod_p99_ms(),mud.get_clod_max_ms()) if mud.get_clod_frames()>0 else None,
        clods_live=p.clods_live if p else None,clods_bank=p.clods_from_bank if p else None,clods_throw=p.clods_from_throw if p else None,
        throw_blobs=sp.get_throw_blobs_emitted(),throw_blobs_snow=sp.get_throw_blobs_snow(),throw_landed_cm3=round(sp.get_throw_landed_cm3(),0),throw_lost_cm3=round(sp.get_throw_lost_cm3(),0),
        refill_passes=p.refill_passes if p else None,refilling=bool(p.get_editor_property('bRefilling')) if p else None,
        session=run.get('session','main'),cell_cm=round(patch_cell(p),3) if p else None,shards=bool(p.get_editor_property('bShards')) if p else None,
        clods_floor=p.clods_from_floor if p else None,lip_chunks_queued=p.lip_chunks_queued if p else None,floor_chunks_queued=p.floor_chunks_queued if p else None,
        wall_drops=p.wall_drops if p else None,wall_drop_cm3=round(p.wall_drop_cm3,0) if p else None,
        collapses_fired=p.collapses_fired if p else None,collapse_cm3=round(p.collapse_cm3,0) if p else None,collapse_segs_armed=p.collapse_segs_armed if p else None,collapse_clumps_queued=p.collapse_clumps_queued if p else None,
        smear_cm3=round(p.smear_cm3,0) if p else None,spill_cm3=round(p.spill_cm3,0) if p else None,spill_clumps_queued=p.spill_clumps_queued if p else None,clods_channel=p.clods_from_channel if p else None)
    summary['feel_landed']=landed(seg,stop_s)
    report['passes'].append(summary);phase='after_pass';last=now
def tick(dt):
    global phase,last,world,car,move,pc,camera,mud,weather,sample_at,pending_shot,cost_at,sun_l,grid_cost_n
    now=time.monotonic()
    try:
        if pending_shot and now>=pending_shot[0]:
            path=pending_shot[1];pending_shot=None
            console('HighResShot %dx%d filename="%s"'%(VIEW[0],VIEW[1],path.as_posix()))
        if now-start>3600:finish('Snow drive check timed out');return
        if phase=='load':
            assert u.get_editor_subsystem(u.LevelEditorSubsystem).load_level(LEVEL);phase='loaded';last=now
        elif phase=='loaded' and now-last>6:
            report['play_mode']=begin_play();phase='warm';last=now
        elif phase=='restart' and now-last>5:
            report['play_mode_retry']=begin_play();phase='warm';last=now
        elif phase=='warm' and now-last>15:
            world=u.EditorLevelLibrary.get_game_world()
            if world is None:
                if now-last>40:raise RuntimeError('Play In Editor did not start')
                return
            cars=u.GameplayStatics.get_all_actors_of_class(world,u.GTCarPawn);assert cars,'Automation car missing';car=cars[0]
            move=car.get_chaos_movement();pc=u.GameplayStatics.get_player_controller(world,0)
            if pc:pc.possess(car);car.disable_input(pc)
            size=list(pc.get_viewport_size());report['viewports'].append(size)
            if str(report.get('play_mode','')).startswith('new window') and size[0]!=VIEW[0] and 'viewport_retry' not in report:
                report['viewport_retry']=size;u.EditorLevelLibrary.editor_end_play();phase='restart';last=now;return
            report['viewport_size']=size;report['mode']='Play In Editor, actual possessed cockpit'
            car.reset_driving_inputs();car.set_chase_camera(False)
            car.get_drivetrain().set_low_range(True);car.get_drivetrain().set_diff_lock(True)
            mud=next(o for o in u.ObjectIterator(u.GTMudSubsystem) if o.get_outer()==world);weather=next(o for o in u.ObjectIterator(u.GTWeatherSubsystem) if o.get_outer()==world)
            clear=weather.find_state('Clear')
            if clear:weather.set_state(clear,True)
            weather.set_wetness_for_test(0.);report['weather']=weather.get_state_name()
            patches=u.GameplayStatics.get_all_actors_of_class(world,u.GTMudPatch);assert len(patches)==1,len(patches)
            p=patches[0];assert p.medium==u.GTDeformMedium.SNOW,str(p.medium)
            report['patch']=dict(section=p.section_index,medium=str(p.medium),bounds_min=[p.bounds_min.x,p.bounds_min.y],bounds_max=[p.bounds_max.x,p.bounds_max.y],cells=[p.cells_x,p.cells_y],vertices=p.mesh_vertex_count,
                material=p.get_editor_property('bMaterialLoaded'),material_path=p.material_path,clod_material=p.clod_material_path,water=p.get_editor_property('bWaterMaterialLoaded'),
                snow_depth_cm=p.snow_depth_cm,snow_edge_cm=p.snow_edge_cm,ridge_return=p.ridge_return,rut_shoulder_cm=p.rut_shoulder_cm,repose_deg=p.repose_deg,set_seconds=p.set_seconds,
                lump_share=p.lump_share,lump_max_cm=p.lump_max_cm,throw_max=p.throw_max,clod_bank_per_cm=p.clod_bank_per_cm,clod_throw_chance=p.clod_throw_chance,snow_plough=p.snow_plough,snow_belly_drag=p.snow_belly_drag,
                plough_return=p.plough_return,plough_lump_share=p.plough_lump_share,plough_bank_variation=p.plough_bank_variation,refill_cm_per_min=p.refill_cm_per_min,profile_max_sinkage_m=p.profile_max_sinkage_m,profile_sinkage_rate=p.profile_sinkage_rate,displace_down_cm=p.displace_down_cm,
                snow_top_at_drift_cm=round(mud.snow_top_cm_at(u.Vector2D(7500,0)),2),snow_top_at_50m_cm=round(mud.snow_top_cm_at(u.Vector2D(5000,0)),2),snow_top_at_entry_cm=round(mud.snow_top_cm_at(u.Vector2D(2900,0)),2),
                apron_box_matches=bool(abs(p.bounds_min.x-APRON_MIN[0])<1 and abs(p.bounds_min.y-APRON_MIN[1])<1 and abs(p.bounds_max.x-APRON_MAX[0])<1 and abs(p.bounds_max.y-APRON_MAX[1])<1))
            report['patch'].update(cell_cm=round(patch_cell(p),3),mesh_triangles=p.mesh_triangle_count,shards=bool(p.get_editor_property('bShards')),clod_meshes=p.clod_mesh_count,
                snow_top_undulation_cm=p.snow_top_undulation_cm,wall_step_cm=[p.wall_step_min_cm,p.wall_step_max_cm],wall_drop_share=p.wall_drop_share,plates=bool(p.get_editor_property('bLumpPlates')))
            # LM4c: the talus per cell, the collapses and the piles as the patch took them.
            report['patch'].update(cell_repose=bool(p.get_editor_property('bCellRepose')),loose_repose_deg=p.loose_repose_deg,wall_repose_deg=[p.wall_repose_deg,p.wall_repose_range_deg],
                collapse_chance=p.collapse_chance,collapse_delay_s=[p.collapse_delay_min_s,p.collapse_delay_max_s],collapse_top=[p.collapse_top_min,p.collapse_top_max],
                plough_band_cm=p.plough_band_cm,plough_falling=bool(p.get_editor_property('bPloughFallingProfile')),pile_cluster=[p.pile_cluster_min,p.pile_cluster_max])
            mid=p.mesh_material
            report['patch']['mesh_material_parent']=mid.get_base_material().get_path_name() if mid else None
            report['patch']['lug_tilt_deg']=mid.get_scalar_parameter_value('LugTiltDeg') if mid else None
            report['patch']['glint_density']=mid.get_scalar_parameter_value('GlintDensity') if mid else None
            sun=next(iter(u.GameplayStatics.get_all_actors_of_class(world,u.DirectionalLight)),None)
            f=sun.get_actor_forward_vector() if sun else u.Vector(.472,-.756,-.454);sun_l=u.Vector(-f.x,-f.y,-f.z)
            report['sun_toward']=[round(sun_l.x,3),round(sun_l.y,3),round(sun_l.z,3)]
            camera=next(a for a in u.GameplayStatics.get_all_actors_of_class(world,u.CameraActor) if a.get_actor_label()=='Live_Overview')
            # The trials: LM3a's numbers for reference, then the patch's own, then the fit's. LM3c: none (TRIALS False), the
            # passes at the patch's own numbers.
            if TRIALS:
                queue.extend([('trial','trial0_lm3a',.35,1.),('trial','trial1_defaults',None,None)])
                phase='next_run';last=now
            else:
                report['trials_skipped']='LM3c: no trials, the passes at the patch\'s own numbers (no retune)'
                report['landed']=dict(trial=None,label='the patch (no trials)',plough=p.snow_plough,belly=p.snow_belly_drag,landed=None,from_patch=True)
                start_run('pass','pass1',None,None,1)
        elif phase=='next_run':
            kind,label,k,s=queue.pop(0);start_run(kind,label,k,s)
        elif phase=='settle' and now-last>4:
            pc.set_view_target_with_blend(car,0.)
            car.reset_driving_inputs();move.set_handbrake_input(False);move.set_target_gear(1,True)
            run.update(start=now,cross={},stop_since=None,stop_max=0.,stop_at=None,plough0=mud.snow_ploughed_cm3(),berm0=mud.snow_plough_berm_cm3(),lowered0=mud.total_lowered_cm3())
            if run['kind']=='pass':
                mud.reset_settle_stats();car.get_spray().reset_throw_stats()
                csv_marks.append((run['label'],csv_files()));console('csvprofile start')
            sample_at=0;phase='drive'
        elif phase=='drive':
            pos,speed=drive_step(0.)
            weather.set_wetness_for_test(0.)
            for mark in MARKS:
                if mark not in run['cross'] and pos.x>=mark:run['cross'][mark]=now
            if now-sample_at>=.25:sample(now,pos,speed);sample_at=now
            if run['kind']=='pass' and run['npass']==2 and pos.x>=COCKPIT_X and 'Snow_Cockpit' not in shots:shots.add('Snow_Cockpit');queue_shot('Snow_Cockpit',.1)
            # The longest stop: under 0.1 m/s once the car has left the start.
            stopped=pos.x>START_X+100. and speed<STOP_MPS
            if stopped:
                run['stop_since']=run['stop_since'] or now
                if now-run['stop_since']>run['stop_max']:run['stop_max']=now-run['stop_since'];run['stop_at']=round(pos.x/100.,2)
            else:run['stop_since']=None
            stalled=run['stop_since'] is not None and pos.x>SNOW_X[0]+100.
            why=None
            if run['kind']=='trial':
                if pos.x>=TRIAL_END_X:why='reached %.0f m'%(TRIAL_END_X/100.)
                elif stalled and now-run['stop_since']>=TRIAL_STALL_S:why='stalled at %.2f m'%(pos.x/100.)
                elif now-run['start']>=TRIAL_MAX_S:why='timed out at %.2f m'%(pos.x/100.)
            else:
                if pos.x>=END_X:why='reached the end'
                elif stalled and now-run['stop_since']>=STALL_S:why='stalled at %.2f m'%(pos.x/100.)
                elif now-run['start']>=PASS_S:why='timed out at %.2f m'%(pos.x/100.)
            if why:end_run(now,pos,why)
        elif phase=='after_trial' and now-last>2:
            done=report['trials'];tuned=[t for t in done if t['label']!='trial0_lm3a']
            if queue:phase='next_run';return
            pick=None
            if tuned and tuned[-1]['landed']:pick=tuned[-1]
            elif len(done)>=MAX_TRIALS:pick=min(tuned or done,key=lambda t:t['miss'])
            else:
                nxt=next_trial(done)
                if nxt is None:pick=min(tuned or done,key=lambda t:t['miss'])
                else:
                    report.setdefault('fits',[]).append(nxt)
                    queue.append(('trial','trial%d_fit'%len(done),nxt['plough'],nxt['belly']));phase='next_run';return
            report['landed']=dict(trial=pick['trial'],label=pick['label'],plough=pick['plough'],belly=pick['belly'],landed=pick['landed'],from_patch=pick['from_patch'])
            k=None if pick['from_patch'] else pick['plough'];s=None if pick['from_patch'] else pick['belly']
            start_run('pass','pass1',k,s,1)
        elif phase=='after_pass' and now-last>3 and run.get('session','main')!='main':
            # LM4: a FineGrid session's passes: pass 2 in its own trench, then its cost profiles.
            if run['npass']==1:start_run('pass',run['session']+'_pass2',run['plough_cvar'],run['belly_cvar'],2,run['session'])
            else:phase='grid_cost_aim';last=now
        elif phase=='after_pass' and now-last>3:
            y_line=[r['y_m']*100. for r in samples if r['run']=='pass1' and DRIFT_X[0]/100.<=r['x_m']<=DRIFT_X[1]/100.]
            yc=statistics.fmean(y_line) if y_line else 0.
            report['line_y_cm']=round(yc,2)
            for x in PROFILE_X:trench_profile('pass%d'%run['npass'],x,yc)
            try:berm_crest('pass%d'%run['npass'],yc)
            except Exception:report['berm_crest_error']=traceback.format_exc()
            if run['npass']==1:start_run('pass','pass2',run['plough_cvar'],run['belly_cvar'],2)
            else:phase='shots';last=now
        elif phase=='shots' and now-last>2:
            yc=report.get('line_y_cm',0.);zl=ground(5600.,yc);zt=ground(8400.,yc)
            aim_camera(u.Vector(5600.,yc+130.,zl+170.),u.Vector(8400.,yc,zt),60)
            report['long_camera']=dict(location=[5600.,yc+130.,zl+170.],target=[8400.,yc,zt],fov=60)
            queue_shot('Snow_Long');phase='shot_long';last=now
        elif phase=='shot_long' and now-last>3:
            yc=report.get('line_y_cm',0.);z=ground(7500.,yc-80.)
            cpos=u.Vector(7150.,yc-200.,z+190.);ctarget=u.Vector(7650.,yc-80.,z+10.)
            aim_camera(cpos,ctarget,50);report['close_camera']=dict(location=[cpos.x,cpos.y,cpos.z],target=[ctarget.x,ctarget.y,ctarget.z],fov=50)
            queue_shot('Snow_Trench_Close');phase='shot_close';last=now
        elif phase=='shot_close' and now-last>3:
            # LM3c item 4: the clods' boxes in this frame, then the same frame with the clods hidden (the wrapper's mask).
            try:
                boxes,live=clod_boxes();report['boxes_clods']=boxes;report['clods_live_at_close']=live
            except Exception:report['boxes_clods']=[];report['clod_boxes_error']=traceback.format_exc()
            for h in clod_hisms():h.set_visibility(False,False)
            queue_shot('Snow_Trench_Close_NoClods',1.5);phase='clods_back';last=now
        elif phase=='clods_back' and now-last>3.5:
            for h in clod_hisms():h.set_visibility(True,False)
            # LM3c: down into the -Y tyre's floor beside the belly's channel at 50 m (the channel at the frame's right).
            yc=report.get('line_y_cm',0.);fz=surface_z(5060.,yc-85.);cz=surface_z(4900.,yc-20.)
            cpos=u.Vector(4900.,yc-20.,cz+120.);ctarget=u.Vector(5060.,yc-85.,fz)
            aim_camera(cpos,ctarget,55);report['floor_camera']=dict(location=[cpos.x,round(cpos.y,1),round(cpos.z,1)],target=[ctarget.x,round(ctarget.y,1),round(ctarget.z,1)],fov=55)
            queue_shot('Snow_Floor_Close');phase='shot_floor';last=now
        elif phase=='shot_floor' and now-last>3:
            # LM4d: low along the belly's channel - 60 cm over its floor at 50 m, 20 cm to +Y of the line, looking 2.5 m along it.
            yc=report.get('line_y_cm',0.);fz=surface_z(5000.,yc+20.);tz=surface_z(5250.,yc-10.)
            cpos=u.Vector(5000.,yc+20.,fz+60.);ctarget=u.Vector(5250.,yc-10.,tz)
            aim_camera(cpos,ctarget,55);report['channel_camera']=dict(location=[cpos.x,round(cpos.y,1),round(cpos.z,1)],target=[ctarget.x,round(ctarget.y,1),round(ctarget.z,1)],fov=55)
            queue_shot('Snow_Channel_Close');phase='shot_channel';last=now
        elif phase=='shot_channel' and now-last>3:
            # LM4: the God of War reference's view - 2.5 m up, 2 m behind and 0.75 m to the left (+Y) of the +Y tyre's track,
            # about 35 degrees down along it (the centre ray meets the track 3.6 m ahead). LM4b: with gt.Snow.Parallax 0 here.
            yc=report.get('line_y_cm',0.);yt=yc+track_offset('+Y',82.)
            cz=surface_z(5000.,yt+75.)+250.;tx=5000.+250./math.tan(math.radians(35.));tz=surface_z(tx,yt)
            aim_camera(u.Vector(5000.,yt+75.,cz),u.Vector(tx,yt,tz),60)
            report['gow_camera']=dict(location=[5000.,round(yt+75.,1),round(cz,1)],target=[round(tx,1),round(yt,1),round(tz,1)],fov=60,track_y_cm=round(yt,1),pitch_deg=round(math.degrees(math.atan2(cz-tz,tx-5000.)),1))
            console('gt.Snow.Parallax 0');queue_shot('Snow_GoW_View',1.5);phase='shot_gow';last=now
        elif phase=='shot_gow' and now-last>3.5:
            console('gt.Snow.Parallax 1');queue_shot('Snow_GoW_View_Parallax1',1.5);phase='shot_gow_p';last=now
        elif phase=='shot_gow_p' and now-last>3.5:
            # LM4: on foot - eye level, 1.65 m over the -Y tyre's trench floor at 46 m, looking along the trench.
            yc=report.get('line_y_cm',0.);yt=yc-track_offset('-Y',82.)
            fz=surface_z(4600.,yt);tz=surface_z(6000.,yt)
            aim_camera(u.Vector(4600.,yt,fz+165.),u.Vector(6000.,yt,tz+40.),65)
            report['onfoot_camera']=dict(location=[4600.,round(yt,1),round(fz+165.,1)],target=[6000.,round(yt,1),round(tz+40.,1)],fov=65,floor_z=round(fz,1))
            console('gt.Snow.Parallax 0');queue_shot('Snow_OnFoot',1.5);phase='shot_onfoot';last=now
        elif phase=='shot_onfoot' and now-last>3.5:
            console('gt.Snow.Parallax 1');queue_shot('Snow_OnFoot_Parallax1',1.5);phase='shot_onfoot_p';last=now
        elif phase=='shot_onfoot_p' and now-last>3.5:
            # LM4b: the lip close up - the -Y trench's outer lip (30 cm out past the tyre's line), the camera 60 cm further out
            # and 30 cm over the snow at 47 m, looking along the lip to 53 m.
            yc=report.get('line_y_cm',0.);lip=yc-track_offset('-Y',82.)-30.
            cy=lip-60.;cz=surface_z(4700.,cy)+30.;tz=surface_z(5300.,lip)+3.
            aim_camera(u.Vector(4700.,cy,cz),u.Vector(5300.,lip,tz),55)
            report['edge_camera']=dict(location=[4700.,round(cy,1),round(cz,1)],target=[5300.,round(lip,1),round(tz,1)],fov=55,lip_y_cm=round(lip,1))
            console('gt.Snow.Parallax 0');queue_shot('Snow_Edge_Close',1.5);phase='shot_edge';last=now
        elif phase=='shot_edge' and now-last>3.5:
            console('gt.Snow.Parallax 1');queue_shot('Snow_Edge_Close_Parallax1',1.5);phase='shot_edge_p';last=now
        elif phase=='shot_edge_p' and now-last>3.5:
            mid=snow_patch().mesh_material;report['edge_debug_default']=mid.get_scalar_parameter_value('SnowEdgeDebug')
            mid.set_scalar_parameter_value('SnowEdgeDebug',1.);queue_shot('Snow_Edge_Mask',1.5);phase='shot_edgemask';last=now
        elif phase=='shot_edgemask' and now-last>3.5:
            snow_patch().mesh_material.set_scalar_parameter_value('SnowEdgeDebug',report.get('edge_debug_default',0.))
            console('gt.Snow.Parallax -1');phase='collapse_cut';last=now
        elif phase=='collapse_cut' and now-last>1.5:
            # LM4c: the collapse pair - a fresh cut on untouched snow, the camera across its trench from a segment that collapses,
            # the same frame 0.2 s and 4 s after the cut.
            yc=report.get('line_y_cm',0.);ty=yc+COLLAPSE_Y;p=snow_patch();fired0=p.collapses_fired
            segs=[(v.x,v.y,v.z,v.w) for v in mud.cut_snow_trench_for_test(u.Vector2D(COLLAPSE_X[0],ty),u.Vector2D(COLLAPSE_X[1],ty),28.,5.)]
            cut_at=now
            pick=min(segs,key=lambda v:abs(v[0]-COLLAPSE_AT_X)) if segs else (COLLAPSE_AT_X,ty,1.,0.)
            sx,sy,side,delay=pick;side=1. if side>=0 else -1.
            cx=sx-60.;cy=ty-side*120.;cz=surface_z(cx,cy)+70.;tz=surface_z(sx,ty+side*40.)-10.
            aim_camera(u.Vector(cx,cy,cz),u.Vector(sx,ty+side*22.,tz),50)
            report['collapse_pair']=dict(cut_y_cm=round(ty,1),cut_x_cm=list(COLLAPSE_X),segments=[[round(a,1),round(b,1),int(c),round(d,2)] for a,b,c,d in segs],chosen=[round(sx,1),round(sy,1),int(side),round(delay,2)],
                camera=dict(location=[round(cx,1),round(cy,1),round(cz,1)],target=[round(sx,1),round(ty+side*22.,1),round(tz,1)],fov=50),fired_before=fired0,cut_s=round(cut_at-start,2))
            queue_shot('Snow_Collapse_0s',.2);phase='collapse_wait';last=now
        elif phase=='collapse_wait' and now-last>3.8:
            queue_shot('Snow_Collapse_4s',.2);phase='collapse_done';last=now
        elif phase=='collapse_done' and now-last>2.:
            p=snow_patch();cp=report.get('collapse_pair',{})
            cp.update(fired_after=p.collapses_fired,fired_between=p.collapses_fired-cp.get('fired_before',0),collapse_cm3_total=round(p.collapse_cm3,0),clumps_queued_total=p.collapse_clumps_queued)
            # The glint: untouched snow 2.6 m to the +Y side of the line at 50 m (sunlit: the sun stands to +Y), seen from
            # the sun's mirror direction so the half-vector stands near the normal, 3.4 m off, 40 degrees.
            yc=report.get('line_y_cm',0.);tx,ty=5000.,yc+260.;tz=surface_z(tx,ty)
            v=u.Vector(-sun_l.x,-sun_l.y,max(sun_l.z,.25));n=math.sqrt(v.x*v.x+v.y*v.y+v.z*v.z);v=u.Vector(v.x/n,v.y/n,v.z/n)
            cpos=u.Vector(tx+340.*v.x,ty+340.*v.y,tz+340.*v.z);aim_camera(cpos,u.Vector(tx,ty,tz),40)
            report['glint_camera']=dict(location=[round(cpos.x,1),round(cpos.y,1),round(cpos.z,1)],target=[tx,round(ty,1),round(tz,1)],fov=40,box_cm=[tx-40.,tx+40.,ty-40.,ty+40.])
            phase='glint_box';last=now
        elif phase=='glint_box' and now-last>2:
            tx0,tx1,ty0,ty1=report['glint_camera']['box_cm']
            report['boxes']['glint']=screen_box(ground_rect(tx0,tx1,ty0,ty1,surface_z))
            queue_shot('Snow_Glint');phase='glint_off';last=now
        elif phase=='glint_off' and now-last>3:
            mid=snow_patch().mesh_material;report['glint_density_default']=mid.get_scalar_parameter_value('GlintDensity')
            mid.set_scalar_parameter_value('GlintDensity',0.);queue_shot('Snow_Glint_NoGlint',1.5);phase='glint_restore';last=now
        elif phase=='glint_restore' and now-last>4:
            snow_patch().mesh_material.set_scalar_parameter_value('GlintDensity',report['glint_density_default'])
            # The border: the +Y side of the box at 45 m, from 6 m outside it and 2.5 m up, looking at the border's middle
            # (sample_border.ps1's eye-height camera 3 m out put the strip outside the box below the frame).
            by=APRON_MAX[1];cz=ground(4500.,by+600.)+250.;tz=surface_z(4500.,by)
            aim_camera(u.Vector(4500.,by+600.,cz),u.Vector(4500.,by,tz),60)
            report['border_camera']=dict(location=[4500.,by+600.,round(cz,1)],target=[4500.,by,round(tz,1)],fov=60,border_y_cm=by)
            phase='border_box';last=now
        elif phase=='border_box' and now-last>2:
            by=APRON_MAX[1]
            report['boxes']['border']=screen_box(ground_rect(4300.,4700.,by-60.,by+60.,surface_z))
            report['boxes']['snowstrip']=screen_box(ground_rect(4350.,4650.,by-200.,by-100.,surface_z))
            report['boxes']['landstrip']=screen_box(ground_rect(4350.,4650.,by+100.,by+200.,ground))
            # The step at the edge itself: 20 cm strips 10 cm either side of the border.
            report['boxes']['edge_in']=screen_box(ground_rect(4350.,4650.,by-30.,by-10.,surface_z))
            report['boxes']['edge_out']=screen_box(ground_rect(4350.,4650.,by+10.,by+30.,ground))
            mid=snow_patch().mesh_material;report['border_defaults']=dict(SnowSSS=mid.get_scalar_parameter_value('SnowSSS'),SnowF0=mid.get_scalar_parameter_value('SnowF0'))
            queue_shot('Snow_Border');phase='border_nosss';last=now
        elif phase=='border_nosss' and now-last>3:
            # Diagnostics for the edge: the same frame with the patch's subsurface off, then also with its F0 at the
            # landscape's (legacy Specular 0.5 = F0 0.04).
            snow_patch().mesh_material.set_scalar_parameter_value('SnowSSS',0.);queue_shot('Snow_Border_NoSSS',1.5);phase='border_f0';last=now
        elif phase=='border_f0' and now-last>4:
            snow_patch().mesh_material.set_scalar_parameter_value('SnowF0',.04);queue_shot('Snow_Border_NoSSS_F004',1.5);phase='border_restore';last=now
        elif phase=='border_restore' and now-last>4:
            mid=snow_patch().mesh_material
            for k,v in report['border_defaults'].items():mid.set_scalar_parameter_value(k,v)
            phase='cost_aim';last=now
        elif phase=='cost_aim' and now-last>3:
            # The cost: one camera over the snow at 50 m, looking down across the trench; the patch wears M_GT_Snow or a clay
            # instance with the same field parameters, alternately.
            yc=report.get('line_y_cm',0.);tz=surface_z(5000.,yc)
            cpos=u.Vector(4300.,yc-450.,tz+900.);aim_camera(cpos,u.Vector(5200.,yc+50.,tz),70)
            report['cost_camera']=dict(location=[cpos.x,round(cpos.y,1),round(cpos.z,1)],target=[5200.,round(yc+50.,1),round(tz,1)],fov=70)
            p=snow_patch();snow_mid=p.mesh_material
            clay=u.MaterialLibrary.create_dynamic_material_instance(world,u.load_asset(CLAY))
            for name in ('MudField','MudTread','MudLayer'):
                tex=snow_mid.get_texture_parameter_value(name)
                if tex:clay.set_texture_parameter_value(name,tex)
            for name in ('PatchMin','PatchSize','PatchTexels'):clay.set_vector_parameter_value(name,snow_mid.get_vector_parameter_value(name))
            for name in ('LugPeriodCm','DiagZ0','DiagZRange','MudDiagnostic'):clay.set_scalar_parameter_value(name,snow_mid.get_scalar_parameter_value(name))
            # ABCCBA, so a steady drift of the GPU's timing over the six profiles cancels in each mean; 'nosss' is M_GT_Snow
            # with SnowSSS 0 (every pixel Default Lit), which splits the subsurface's lighting cost out.
            sss=snow_mid.get_scalar_parameter_value('SnowSSS');report['cost_sss_default']=sss
            cost_steps.extend([('snow',snow_mid,sss),('clay',clay,None),('nosss',snow_mid,0.),('nosss',snow_mid,0.),('clay',clay,None),('snow',snow_mid,sss)])
            report['cost_pictures']=[];phase='cost_set';last=now
        elif phase=='cost_set' and now-last>2:
            if not cost_steps:
                surface_material(snow_patch().mesh_material)
                p1=report['passes'][0] if report['passes'] else {};p2=report['passes'][1] if len(report['passes'])>1 else {}
                ratio=(p2['drift_mean_mps']/p1['drift_mean_mps']) if (p1.get('drift_mean_mps') and p2.get('drift_mean_mps')) else None
                report['gates']=dict(both_completed=bool(p1.get('completed') and p2.get('completed')),drift_ratio=round(ratio,3) if ratio else None,drift_ratio_ok=bool(ratio and ratio>=1.15),
                    feel_pass1_landed=bool(p1.get('feel_landed')),cost_ok=all((r.get('settle') or {}).get('ok',True) and (r.get('clods') or {}).get('ok',True) for r in report['passes']))
                pm=snow_patch();report['grid'].append(dict(label='main',fine_grid=1,cell_cm=round(patch_cell(pm),3),cells=[pm.cells_x,pm.cells_y],mesh_vertices=pm.mesh_vertex_count,mesh_triangles=pm.mesh_triangle_count,shards=bool(pm.get_editor_property('bShards'))))
                # LM4b: the parallax pair next, from the cost camera and the edge camera.
                for view in ('strip','edge'):
                    for val in PX_ORDER:px_steps.append((view,val))
                phase='px_set';last=now;return
            name,material,sss=cost_steps.pop(0);surface_material(material)
            if sss is not None:material.set_scalar_parameter_value('SnowSSS',sss)
            report['cost'].append(dict(material=name,parent=material.get_base_material().get_path_name(),snow_sss=sss))
            # A picture of what is measured, the first time each material is on, taken before its profile starts.
            if len(report['cost'])<=3:queue_shot('Snow_Cost_'+name.capitalize(),1.)
            phase='cost_warm';last=now
        elif phase=='cost_warm' and now-last>3.5:
            label='cost_%s_%d'%(report['cost'][-1]['material'],len(report['cost']))
            csv_marks.append((label,csv_files()));console('csvprofile start');phase='cost_run';last=now
        elif phase=='cost_run' and now-last>5:
            console('csvprofile stop')
            # LM3c item 5: the first time each material is on, Substrate's classification and a ProfileGPU dump.
            phase='classify' if len(report['cost'])<=3 else 'cost_set';last=now
        elif phase=='classify' and now-last>1:
            name=report['cost'][-1]['material'];console('r.Substrate.ViewMode 4')
            queue_shot('Snow_Classify_'+name.capitalize(),1.5);phase='classify_off';last=now
        elif phase=='classify_off' and now-last>3.5:
            name=report['cost'][-1]['material'];console('r.Substrate.ViewMode 0');console('r.ProfileGPU.ShowUI 0')
            u.log('LM3C_PROFILEGPU_BEGIN '+name);console('ProfileGPU');phase='profilegpu_wait';last=now
        elif phase=='profilegpu_wait' and now-last>3:
            u.log('LM3C_PROFILEGPU_END '+report['cost'][-1]['material']);phase='cost_set';last=now
        elif phase=='px_set' and now-last>2:
            # LM4b: one parallax profile - the view, gt.Snow.Parallax, a warm-up, 5 s of CSV.
            if not px_steps:
                console('gt.Snow.Parallax -1');phase='grid_next';last=now;return
            view,val=px_steps.pop(0);cc=report['cost_camera'] if view=='strip' else report['edge_camera']
            aim_camera(u.Vector(*cc['location']),u.Vector(*cc['target']),cc['fov']);console('gt.Snow.Parallax %d'%val)
            report.setdefault('parallax_cost',[]).append(dict(view=view,parallax=val));phase='px_warm';last=now
        elif phase=='px_warm' and now-last>3.5:
            e=report['parallax_cost'][-1];csv_marks.append(('px_%s_%d_%d'%(e['view'],e['parallax'],len(report['parallax_cost'])),csv_files()))
            console('csvprofile start');phase='px_run';last=now
        elif phase=='px_run' and now-last>5:
            console('csvprofile stop');phase='px_set';last=now
        elif phase=='grid_next' and now-last>2:
            # LM4: the next FineGrid session: the switch, the patches rebuilt (the switch is read when they are built), its passes.
            if not grid_queue:
                console('gt.Snow.FineGrid 1')
                assert all(Path(q).exists() for q in report['images']),'a picture is missing'
                report['ok']=True;finish();return
            label,val=grid_queue.pop(0)
            console('gt.Snow.FineGrid %d'%val);n=mud.rebuild_patches_for_test();p=snow_patch()
            report['grid'].append(dict(label=label,fine_grid=val,patches=n,cell_cm=round(patch_cell(p),3),cells=[p.cells_x,p.cells_y],mesh_vertices=p.mesh_vertex_count,mesh_triangles=p.mesh_triangle_count,shards=bool(p.get_editor_property('bShards'))))
            start_run('pass',label+'_pass1',None,None,1,label)
        elif phase=='grid_cost_aim' and now-last>2:
            cc=report['cost_camera'];aim_camera(u.Vector(*cc['location']),u.Vector(*cc['target']),cc['fov']);grid_cost_n=0;phase='grid_cost_warm';last=now
        elif phase=='grid_cost_warm' and now-last>3.5:
            grid_cost_n+=1;csv_marks.append(('grid_%s_%d'%(run['session'],grid_cost_n),csv_files()));console('csvprofile start');phase='grid_cost_run';last=now
        elif phase=='grid_cost_run' and now-last>5:
            console('csvprofile stop');phase='grid_cost_warm' if grid_cost_n<2 else 'grid_next';last=now
    except Exception:finish(traceback.format_exc())
handle=u.register_slate_post_tick_callback(tick)
