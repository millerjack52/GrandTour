"""Living mud LM5b (docs/LIVING_MUD_PLAN.md LM5b phase B item 6, docs/MUD_VARIANTS.md): drive the real car down
L_MudVariants once, dry.

Play In Editor in a new 1440x900 window (as the L_MudDrive and L_SnowDrive checks), Clear weather and wetness 0 held, low
range and the diff lock, FULL THROTTLE (the snow check's drive: the brake only past 12 m/s, a guard; its steering to the line)
from 5 m to 200 m, through Firm (30-55 m), Standard (75-100 m), Deep (120-145 m) and Stony (165-190 m). Completion: the car
past 200 m inside 300 s with no stop (under 0.1 m/s) longer than 15 s. Per section: the time between the car crossing its
start and its end and the mean speed that gives, the largest and the mean sinkage of the wheels whose contact was inside the
section (samples every 0.25 s), the field's lowered volume added while the car was in it, and the patch's numbers as play
built them (variant, scales, RecoverShare, LumpShare, ThrowMax, water table, the mesh instance's MudVariant, the clods'
instance). Then, the car hidden, per section two pictures of its own -Y rut (the lowest field cell across the line at the
section's middle): MudVariants_<V>_OnFoot.png (eye level, 1.7 m over the rut 3 m into the section, looking along it 12 m) and
MudVariants_<V>_Close.png (0.9 m over the ground 1.4 m back and 0.9 m to the side, looking down into the rut).
NO cost or timing measurement (the owner's rule): no CSV profile, no stat readout. Writes Art/Export/MudVariants/drive-report.json
and drive_samples.csv.
MudRunner MR1 (docs/MUDRUNNER_LESSONS_PLAN.md MR1 item 8), after those pictures, functional only (completion and pictures):
- Carry_Exit.png: the car drives on from where it stopped to 223 m (its rear wheels about 31 m past Stony's 190 m exit) and
  parks; the camera just behind it, 1.9 m up, looks back at the carried tracks; the track paint's G from 197 to 221 m is
  reported per side of the car (the most of any cell 20-150 cm to that side, every 25 cm: mean per 5 m, gap share);
- Carry_Grass.png: the car is set on the gravel at 153.5 m, 3 m left of the line, runs up into fresh Stony mud along that
  line to 166 m, then is steered at the verge (205 m, 12.5 m left), out of the box's side and through the tussocks; the car
  hidden, the camera 2.9 m from the verge point with the most mud, looking at the clumps' feet; G under the wheels' path on
  the verge is reported;
- Splat_Post.png: the car is set in fresh Deep mud (124.4 m, 3.4 m left), its left rear wheel 1.5 m in front of
  SplatPost_Deep (121.6 m, 4.2 m left, at the bog's left edge), and pulls away at full throttle for 6 s, spinning; the car
  hidden, a view of the post's face toward the car; the splats (landscape, decals and what they landed on), the traces and
  the thrown blobs that splatted. (Held still the wheels dig one spot to the sinkage cap and stop lowering mud: 266 blobs in
  6 s against 1,584 pulling away, 2026-10-08.)
MudRunner MR2 (docs/MUDRUNNER_LESSONS_PLAN.md MR2: the housekeeping and item 7), functional only:
- a drive that does not reach 200 m (it stalled under a game twice, 2026-10-08; with GoWR open the editor ran at 1.3 frames a
  second, MR2's first run) is followed by a scripted pass (FAST): the car set 2 m before each section it did not get through
  and driven 6 m into it (at most 240 s each), Stony's leg driven on out to 210 m for the carried tracks (the section pictures
  wait until after MR2); the verge run from 2 m before Stony at 3 m left, through 11 m of its mud, then out at the verge (from
  180 m it left the mud at once and carried none, the seventh run); each leg ended by distance within 300 s, the
  spin-up by its blobs (480, as 6 s of the clean run); every placement waits for the car to come to rest (a fixed wait left it
  in the air at those frame rates);
- Carry_Grass from 1.4 m (0.6 m up) of the verge point with the most mud, at the clumps' feet, and Carry_Grass_Off from the same
  camera with gt.Mud.GrassMud 0 (the pair shows the muddy feet against none);
- the splat and trace counts per second of play (the drive, the whole run), the traces the band skipped, the landscape splats
  the height test made, the decals that waited for their shaders (and whether the material was ready at the spin-up);
- Car_Muddy_Side.png and Car_Muddy_Rear.png: after everything, the car set on the gravel at 212 m, still, and shot from its
  left side and from behind; the body state (regions, lines, wash, MudWet, tyres, hits), the car's thrown blobs on the body.
MudRunner MR2b (docs/MUDRUNNER_LESSONS_PLAN.md MR2b items 3-4), functional only:
- Car_Muddy_Side from 6.4 m off the car's right side (the whole car, both arches' fans); the droplet-density boxes (behind the
  right rear arch and mid-door, the same height band on the door) in world space with the camera, for Art/count_car_droplets.py
  (the wrapper runs it on the picture: the dark-spot count in each box);
- the body state's spray fans (FanCoat, FanDir per wheel);
- Carry_Grass's camera on a verge point the car crossed and did not park on (none within 4 m of where it stopped).
MudRunner MR3 (docs/MUDRUNNER_LESSONS_PLAN.md MR3 item 1, rut pools only), functional only:
- Rut_Muddy.png: the car set 2.5 m into Deep on the drive's ruts (their rut pools), full throttle for 4 s of game time (it spins and
  churns them), then moved away to the gravel (a parked car keeps stamping as it sinks) and hidden; the camera 3.4 m from the
  most churned spot (the most turbidity in a 60 cm box over a 20 x 10 cm scan of the stretch), 1.9 m up on the +Y side, looking
  down at it; Rut_Settled.png: the same camera 60 s of game time later. The patch's turbidity readout round the spot at each.
- MR3b: and a grazing pair from eye level (1.65 m over the ground, 3 m from the spot on the +Y side), 3.5 s after each:
  Rut_Muddy_Low.png and Rut_Settled_Low.png.
MudRunner MRP (docs/MUDRUNNER_LESSONS_PLAN.md MRP item 4), functional only (no timing), after MR3, the car hidden:
- the look pictures with gt.Mud.PBR 1: Mud_PBR_OnFoot.png (Standard's on-foot view) and Mud_PBR_Close.png (60 cm from untouched
  mud 3.2 m right of the line, 25 cm up, across the lumps: the parallax's depth), each with gt.Mud.POM 2 (the default) and 0
  (Mud_PBR_OnFoot_POM0.png, Mud_PBR_Close_POM0.png); Rut_Settled_PBR.png (MR3's pool camera, 60+ s after the churn); then the car
  set on the gravel at 212 m and Car_Muddy_PBR.png (Car_Muddy_Side's camera);
- the PBR validation captures: HighResShot's buffer dump (BaseColor, Roughness, MaterialAO; uncompressed EXR) of the car
  (PBR_Car: the sill band between the arches, its world corners for the sampler, and MudWet), the gravel (PBR_Calib: roughness 0.9
  by construction, the dumps' encoding) and each variant's ground (PBR_<V>_Ground: 2.2 m over its -Y rut, looking down about
  50 degrees); the rut water is translucent (no GBuffer), so its row is the material's formula over the pool's turbidity
  (mrp.water_model). The wrapper runs Art/sample_mud_pbr.py on them.
- MRP follow-up: Mud_PBR_Close_Steep.png (POM 2), the close-up's spot from 80 cm back and 29 cm up (about 20 degrees above the
  ground: a grazing view across the lumps, where the parallax's steps show most), and Mud_PBR_Close_Steep_NoShadow.png (the same
  with gt.Mud.POMShadow 0: the march's bands apart from the shadow's); and, after the captures, the weather's test
  wetness held at 1 for Carry_Wet_PBR.png (fresh tracks first: the car driven out of Stony's mud from 183 m to 215 m, dry; then 1.9 m
  up, looking down about 50 degrees at the strongest carried mud 200-206 m within 1.5 m of the line) and its buffer dump
  PBR_CarryWet (the carried mud's roughness under the rain floor against the gravel's), then back to 0.
MudRunner MR4 (docs/MUDRUNNER_LESSONS_PLAN.md MR4 execution block item 6), functional only (no timing):
- the CPU maps soft-<V>.png: each patch's softness S as grey, 1 px per cell (row 0 the box's -Y edge, X to the right), the route
  line (y 0) a 1-px red line; each patch's amplitude, the means of its lerps, its soft share and blob count;
- before driving (the car parked at 5 m, out of view): Soft_Standard_Before.png and Soft_Firm_Before.png, 1.7 m over the ground
  11 m from the biggest soft blob within 2.5 m of the line (else the biggest), from its -X side turned 30 degrees toward +Y,
  looking at the blob's centroid; Soft_Top.png, 20 m up at 65 m, 20 m to the -Y side, looking 45 degrees down at the line
  between Firm and Standard (FOV 90); after the drive, the car hidden, Soft_Standard_After.png from the Before camera;
- per section: the mean speed against the committed drive-report (git HEAD's, before MR4) and the share of the wheel path's
  cells (route line +-1 m, the section's 25 m) that are soft (S over 0.6).
MudRunner MR5 (docs/MUDRUNNER_LESSONS_PLAN.md MR5 execution block item 7), functional only (no timing):
- before driving (the car parked at 5 m, out of view): Chunks_Before.png, 2.5 m up at 73 m, 7.5 m to the -Y side, looking across
  Standard's start (83 m on the line, FOV 60); Chunks_Close.png, on foot (1.7 m eye height) 3.5 m from the biggest cluster in
  Standard (the chunk with the most others within 1.5 m, with them), from its -X side turned 30 degrees toward -Y; Chunks_Firm.png,
  Chunks_Before's camera moved to Firm's start (28 m, looking at 38 m);
- after the drive (or the scripted pass), the car hidden, Chunks_After.png from Chunks_Before's camera;
- per section (each patch's AGTMudPatch::DescribeMudChunks): the chunk count, the breaks by trigger, the awake peak, the volume
  deposited and lost - before driving, after the drive and at the end - and the subsystem's world-wide awake peak.
"""
import unreal as u,json,time,math,traceback,csv,statistics,os,sys
from pathlib import Path
ROOT=Path(u.Paths.project_dir()).resolve()
# Checks under a running game (docs/CHECKS_UNDER_GAME_PLAN.md, Art/Unreal/check_render.py): the editor steps a fixed 1/60 s
# (Art/check_mud_variants.ps1's -UseFixedTimeStep -FPS=60, verified over 300 frames of the drive), the scene is rendered only from a
# picture's request (30 frames of warm-up) until its file lands, and for the two GPU reads of the track paint (MR1's exit profile and
# the verge points); the per-tick GPU wait runs only while rendering. GT_CHECK_RENDER_ALWAYS=1 renders every frame.
sys.path.insert(0,str(ROOT/'Art/Unreal'))
from check_render import Gate
GATE=Gate()
OUT=ROOT/'Art/Export/MudVariants';OUT.mkdir(parents=True,exist_ok=True)
LEVEL='/Game/GrandTour/ArtTests/MudVariants/L_MudVariants';SPEC='/Game/GrandTour/ArtTests/MudVariants/DA_MudVariants'
u.EditorPythonScripting.set_keep_python_script_alive(True)
VIEW=(1440,900)
# GPU wait each tick (GT_CHECK_PACE=0 off): -RenderOffScreen has no swap chain, so command lists pile up past D3D12's residency slots.
PACE=os.environ.get('GT_CHECK_PACE','1').strip()!='0';pace_rt=None
def gpu_pace():
    # docs/VRAM_SOAK.md: one 1x1 render target readback on the game world; the RHI's read waits for the GPU to finish its work.
    global pace_rt
    gw=u.EditorLevelLibrary.get_game_world()
    if gw is None:return
    try:gone=pace_rt is None or pace_rt.get_outer() is None
    except Exception:gone=True   # a PIE restart collected it
    if gone:pace_rt=u.RenderingLibrary.create_render_target2d(gw,1,1,u.TextureRenderTargetFormat.RTF_RGBA8)
    u.RenderingLibrary.read_render_target_pixel(gw,pace_rt,0,0)
START_X=500.;DONE_X=20000.;PASS_S=300.;STALL_S=15.;STOP_MPS=.1
# Checks: game-time limits (2026-10-10, the owner: a running game holds the editor to a fraction of real time). Every drive limit -
# PASS_S, STALL_S, the legs' caps (FAST_CAP_S, TP_MAX_S, MR1's 40 / 30 s, MR1_SPIN_S), the settle waits - is in SIMULATED seconds (gt(), the physics
# clock, see advance_sim; gsince() since the phase began), and every reported drive time and speed is in game time. WALL_CAP_S is the
# only wall-clock limit: 40 min for the whole check.
WALL_CAP_S=2400.
SECTIONS=[('Firm',3000.,5500.),('Standard',7500.,10000.),('Deep',12000.,14500.),('Stony',16500.,19000.)]
VARIANT_INDEX={'Standard':0,'Firm':1,'Deep':2,'Stony':3}
phase='load';last=time.monotonic();start=last;sample_at=0;pending_shot=None;PARKED=False;car=None
world=None;pc=None
# MR3b: the ticks so far. A picture waits SHOT_FRAMES ticks as well as 1.5 s after its camera moves: at a game's 2 frames a second
# 1.5 s was 3 frames and the moved camera was not yet in the picture (the first grazing runs' Rut_Muddy showed the camera after it).
# The phases wait while a picture is pending and for SHOT_HOLD ticks after its command, so no camera moves before the capture.
FRAME=0;SHOT_FRAMES=10;SHOT_HOLD=0
report={'ok':False,'images':[],'viewports':[],'sections':[],'patches':[]}
samples=[];run=None;shot_queue=[]
def console(cmd):
    u.SystemLibrary.execute_console_command(world,cmd,pc)
def begin_play():
    lib=getattr(u,'GTPlayWindowLibrary',None)
    if lib and lib.request_play_in_new_window(VIEW[0],VIEW[1]):return 'new window %dx%d'%VIEW
    u.get_editor_subsystem(u.LevelEditorSubsystem).editor_request_begin_play();return 'level viewport'
def spec():
    return u.load_asset(SPEC).spec
def ground(x,y):
    return u.GTVehicleSetupLibrary.sample_terrain_height_cm(spec(),x,y)
def surface_z(x,y):
    return ground(x,y)+mud.mud_height_cm_at(u.Vector2D(x,y))
def finish(error=None):
    global phase
    phase='finished'
    if error:report['error']=error
    try:report['check_run']=GATE.report()
    except Exception:report['check_run_error']=traceback.format_exc().splitlines()[-1]
    try:
        if 'chunks' in report:chunk_report('end')   # MR5
    except Exception:report['chunks_end_error']=traceback.format_exc().splitlines()[-1]
    try:
        if samples:
            keys=[]
            for r in samples:
                for k in r:
                    if k not in keys:keys.append(k)
            with open(OUT/'drive_samples.csv','w',newline='') as f:
                wr=csv.DictWriter(f,fieldnames=keys);wr.writeheader();wr.writerows(samples)
    except Exception:report['csv_error']=traceback.format_exc()
    (OUT/'drive-report.json').write_text(json.dumps(report,indent=2));u.unregister_slate_post_tick_callback(handle);u.EditorLevelLibrary.editor_end_play();u.SystemLibrary.quit_editor()
def place_car(x,y):
    z=ground(x,y);car.set_actor_location_and_rotation(u.Vector(x,y,z+150),u.Rotator(),False,True);body=car.get_component_by_class(u.SkeletalMeshComponent);body.set_physics_linear_velocity(u.Vector());body.set_physics_angular_velocity_in_degrees(u.Vector());car.reset_driving_inputs();move.set_handbrake_input(True)
def aim_camera(cpos,ctarget,fov):
    camera.set_actor_location(cpos,False,False);camera.set_actor_rotation(u.MathLibrary.find_look_at_rotation(cpos,ctarget),False);camera.camera_component.set_field_of_view(fov);pc.set_view_target_with_blend(camera,0.)
def drive_step(target_y):
    global PARKED
    PARKED=False
    pos=car.get_actor_location();speed=car.get_velocity().length()/100.;yaw=car.get_actor_rotation().yaw
    target_yaw=math.degrees(math.atan2(target_y-pos.y,650.));error=(target_yaw-yaw+180)%360-180;car.set_raw_steer(max(-.65,min(.65,error/24)))
    move.set_throttle_input(1.);move.set_brake_input(.4 if speed>12. else 0.)
    return pos,speed
def patch_for(x0,x1):
    mid=.5*(x0+x1)
    return next((p for p in u.GameplayStatics.get_all_actors_of_class(world,u.GTMudPatch) if p.bounds_min.x<=mid<=p.bounds_max.x),None)
def sample(now,pos,speed):
    wheels=car.get_traction().wheels
    row=dict(t_s=round(now-run['start'],3),x_m=round(pos.x/100.,3),y_m=round(pos.y/100.,3),speed_mps=round(speed,3),lowered_cm3=round(mud.total_lowered_cm3(),0))
    for k,w in enumerate(wheels):
        row.update({'w%d_x_m'%k:round(w.contact_point.x/100.,3),'w%d_sink_cm'%k:round(w.sinkage*100.,2),'w%d_in_box'%k:bool(w.get_editor_property('bInPatchBox')),
                    'w%d_in_mud'%k:bool(w.get_editor_property('bInMudPatch')),'w%d_contact'%k:bool(w.get_editor_property('bInContact')),'w%d_friction_scale'%k:round(w.friction_scale,4),'w%d_slip'%k:round(w.slip_magnitude,1),'w%d_load'%k:round(w.mud_load,3),
                    # GR1c checks follow-up (the frame-rate finding): the traction's terms per wheel, for the sections' means.
                    'w%d_rr'%k:round(w.rolling_resistance,4),'w%d_plough'%k:round(w.diag_plough_drag,4),'w%d_belly'%k:round(w.diag_belly_drag,4),
                    'w%d_surf'%k:round(w.diag_surface_drag,4),'w%d_rut'%k:round(w.rut_depth,4),'w%d_climb'%k:round(w.rut_climb,4),
                    'w%d_tyre_n'%k:round(w.load*.01,1),'w%d_slipping'%k:bool(w.get_editor_property('bSlipping'))})
    samples.append(row)
def rut_y(x):
    # The -Y tyre's rut at x: the lowest field cell 30-160 cm to the -Y side of the line (5 cm steps).
    best=(None,1e9)
    for i in range(27):
        y=-30.-5.*i;h=mud.mud_height_cm_at(u.Vector2D(x,y))
        if h<best[1]:best=(y,h)
    return best
def section_summary(name,x0,x1):
    c=run['cross'];t=(c[x1]-c[x0]) if (x0 in c and x1 in c) else None
    sinks=[]
    for r in samples:
        for k in range(4):
            key='w%d_x_m'%k
            if key in r and x0/100.<=r[key]<=x1/100. and r['w%d_contact'%k]:sinks.append(r['w%d_sink_cm'%k])
    inside=[r for r in samples if x0/100.<=r['x_m']<=x1/100.]
    lowered=(inside[-1]['lowered_cm3']-inside[0]['lowered_cm3']) if len(inside)>1 else None
    def wmean(key,scale=1.):
        v=[float(r['w%d_%s'%(k,key)])*scale for r in inside for k in range(4) if r.get('w%d_in_mud'%k) and ('w%d_%s'%(k,key)) in r]
        return round(statistics.fmean(v),4) if v else None
    terms=dict(rolling_resistance=wmean('rr'),plough=wmean('plough'),belly=wmean('belly'),surface=wmean('surf'),rut_depth=wmean('rut'),rut_climb=wmean('climb'),
               tyre_load_n=wmean('tyre_n'),slip=wmean('slip'),slipping_share=wmean('slipping'),samples=len(inside))
    return dict(variant=name,start_m=x0/100.,end_m=x1/100.,crossed=bool(t),time_s=round(t,2) if t else None,mean_speed_mps=round((x1-x0)/100./t,3) if t else None,
                mean_speed_kmh=round(3.6*(x1-x0)/100./t,2) if t else None,min_speed_mps=round(min((r['speed_mps'] for r in inside),default=0.),3),
                max_sinkage_cm=round(max(sinks),2) if sinks else None,mean_sinkage_cm=round(statistics.fmean(sinks),2) if sinks else None,wheel_samples=len(sinks),
                lowered_cm3_while_inside=round(lowered,0) if lowered is not None else None,
                mean_friction_scale=round(statistics.fmean([r['w%d_friction_scale'%k] for r in inside for k in range(4) if r.get('w%d_in_mud'%k)]),4) if any(r.get('w%d_in_mud'%k) for r in inside for k in range(4)) else None,
                traction_means=terms)
def queue_pictures():
    for name,x0,x1 in SECTIONS:
        mid=.5*(x0+x1);ry,rh=rut_y(mid)
        report['ruts'][name]=dict(x_cm=mid,y_cm=ry,field_cm=round(rh,2))
        xa=x0+300.;xb=x0+1500.
        foot=(u.Vector(xa,ry,surface_z(xa,ry)+170.),u.Vector(xb,ry,surface_z(xb,ry)),65.)
        zc=surface_z(mid,ry)
        close=(u.Vector(mid-140.,ry+90.,surface_z(mid-140.,ry+90.)+90.),u.Vector(mid+30.,ry,zc-10.),50.)
        for kind,(cpos,ctarget,fov) in [('OnFoot',foot),('Close',close)]:
            shot_queue.append(('MudVariants_%s_%s'%(name,kind),cpos,ctarget,fov))
    # MR4: the Standard soft-spot view again, after the drive, from the Before camera.
    cam=report.get('soft',{}).get('cameras',{}).get('Soft_Standard_Before')
    if cam:shot_queue.append(('Soft_Standard_After',u.Vector(*cam['location']),u.Vector(*cam['target']),cam['fov']))
    # MR5: the chunks across Standard's start again, from the Before camera.
    cam=report.get('chunks',{}).get('cameras',{}).get('Chunks_Before')
    if cam:shot_queue.append(('Chunks_After',u.Vector(*cam['location']),u.Vector(*cam['target']),cam['fov']))
# ---- MudRunner MR4: readable soft spots (docs/MUDRUNNER_LESSONS_PLAN.md MR4 execution block item 6) ---------------------------
SOFT_EYE_CM=170.;SOFT_VIEW_CM=1100.;SOFT_VIEW_DEG=30.;SOFT_TOP=((6500.,-2000.,2000.),(6500.,0.,0.),90.)
soft_queue=[];soft_maps={}
def soft_baseline():
    # The committed drive-report (before MR4) for the speed comparison: git's HEAD copy, else the file as it stood at the start.
    import subprocess
    try:
        out=subprocess.run(['git','show','HEAD:Art/Export/MudVariants/drive-report.json'],cwd=str(ROOT),capture_output=True,timeout=30)
        if out.returncode==0:return 'git HEAD',json.loads(out.stdout.decode('utf-8'))
    except Exception:pass
    try:return 'the file at the start',json.loads((OUT/'drive-report.json').read_text())
    except Exception:return None,None
SOFT_BASE_FROM,SOFT_BASE=soft_baseline()
def soft_png(path,w,h,rows):
    import zlib,struct
    def chunk(t,d):return struct.pack('>I',len(d))+t+d+struct.pack('>I',zlib.crc32(t+d)&0xffffffff)
    raw=b''.join(b'\x00'+bytes(r) for r in rows)
    path.write_bytes(b'\x89PNG\r\n\x1a\n'+chunk(b'IHDR',struct.pack('>IIBBBBB',w,h,8,2,0,0,0))+chunk(b'IDAT',zlib.compress(raw,9))+chunk(b'IEND',b''))
def soft_grid(p):
    s=list(p.get_softness_bytes());sx,sy=p.cells_x,p.cells_y
    cell=(p.bounds_max.x-p.bounds_min.x)/max(1,sx)
    return dict(s=s,sx=sx,sy=sy,cell=cell,x0=p.bounds_min.x,y0=p.bounds_min.y) if len(s)==sx*sy and sx>0 else None
def soft_map(name,g):
    # S as grey, 1 px per cell (row 0 the box's -Y edge, X to the right), the route line (y 0) as a 1-px red line.
    line=int((0.-g['y0'])//g['cell']);rows=[]
    for y in range(g['sy']):
        row=bytearray()
        for x in range(g['sx']):
            v=g['s'][y*g['sx']+x];row+=bytes((255,0,0)) if y==line else bytes((v,v,v))
        rows.append(row)
    path=OUT/('soft-%s.png'%name);soft_png(path,g['sx'],g['sy'],rows);report['images'].append(str(path))
    return str(path)
def soft_blobs(g):
    # 8-connected components of S over 0.6 (a byte over 153), at least 1 m2: (cells, world centroid x, y).
    sx,sy,s=g['sx'],g['sy'],g['s'];seen=bytearray(sx*sy);out=[];need=int(math.ceil(10000./(g['cell']**2)))
    for i in range(sx*sy):
        if s[i]<=153 or seen[i]:continue
        seen[i]=1;stack=[i];n=0;mx=my=0.
        while stack:
            k=stack.pop();kx,ky=k%sx,k//sx;n+=1;mx+=kx+.5;my+=ky+.5
            for dy in (-1,0,1):
                for dx in (-1,0,1):
                    nx,ny=kx+dx,ky+dy
                    if (dx or dy) and 0<=nx<sx and 0<=ny<sy:
                        j=ny*sx+nx
                        if s[j]>153 and not seen[j]:seen[j]=1;stack.append(j)
        if n>=need:out.append((n,g['x0']+mx/n*g['cell'],g['y0']+my/n*g['cell']))
    return out
def soft_share(g,x0,x1,half_cm):
    # The share of cells within half_cm of the route line (y 0) between x0 and x1 that are soft (S over 0.6).
    n=soft=0
    for y in range(g['sy']):
        yc=g['y0']+(y+.5)*g['cell']
        if abs(yc)>half_cm:continue
        for x in range(g['sx']):
            xc=g['x0']+(x+.5)*g['cell']
            if x0<=xc<=x1:n+=1;soft+=1 if g['s'][y*g['sx']+x]>153 else 0
    return round(soft/n,4) if n else None
def soft_view(name,g):
    # Eye height over the ground, SOFT_VIEW_CM from the biggest soft blob near the line (within 2.5 m; else the biggest), from the
    # -X side turned SOFT_VIEW_DEG toward +Y, looking at the blob's centroid on the ground.
    blobs=soft_blobs(g)
    if not blobs:return None
    near=[b for b in blobs if abs(b[2])<=250.]
    n,bx,by=max(near or blobs)
    a=math.radians(SOFT_VIEW_DEG);cx=bx-SOFT_VIEW_CM*math.cos(a);cy=by+SOFT_VIEW_CM*math.sin(a)
    cpos=u.Vector(cx,cy,ground(cx,cy)+SOFT_EYE_CM);ctarget=u.Vector(bx,by,surface_z(bx,by))
    return dict(name=name,cpos=cpos,ctarget=ctarget,fov=65.,blob=dict(cells=n,area_m2=round(n*g['cell']**2/1e4,2),x_cm=round(bx,1),y_cm=round(by,1)),blobs=len(blobs))
def soft_setup():
    # The CPU maps, each patch's soft numbers, and the pictures before driving (queued for the soft_before phase).
    rep=report.setdefault('soft',{});rep['baseline_from']=SOFT_BASE_FROM;rep['patches']=[];rep['maps']=[];rep['cameras']={}
    for name,x0,x1 in SECTIONS:
        p=patch_for(x0,x1);g=soft_grid(p)
        row=dict(variant=name,has_soft_spots=bool(p.has_soft_spots()),amplitude=round(p.soft_spot_amplitude,3),mean_sink_lerp=round(p.soft_mean_sink,4),
                 mean_friction_lerp=round(p.soft_mean_friction,4),switch=u.SystemLibrary.get_console_variable_int_value('gt.Mud.SoftSpots'))
        if g:
            soft_maps[name]=g;row['share']=round(sum(1 for v in g['s'] if v>153)/len(g['s']),4);row['blobs']=len(soft_blobs(g));row['map']=soft_map(name,g)
            row['wheel_path_share_section']=soft_share(g,x0,x1,100.)
            row['wheel_path_share_box']=soft_share(g,g['x0'],g['x0']+g['sx']*g['cell'],100.)
        rep['patches'].append(row)
    for name in ('Standard','Firm'):
        g=soft_maps.get(name);v=soft_view('Soft_%s_Before'%name,g) if g else None
        if v:soft_queue.append((v['name'],v['cpos'],v['ctarget'],v['fov']));rep.setdefault('blobs',{})[name]=v['blob']
        else:rep.setdefault('missing',[]).append('Soft_%s_Before (no soft blob)'%name)
    (cx,cy,cz),(tx,ty,tz),fov=SOFT_TOP
    soft_queue.append(('Soft_Top',u.Vector(cx,cy,ground(cx,cy)+cz),u.Vector(tx,ty,ground(tx,ty)+tz),fov))
def soft_sections():
    # Per section: the mean speed against the committed drive-report, and the wheel path's soft share (route line +-1 m).
    base={s['variant']:s for s in (SOFT_BASE or {}).get('sections',[])}
    out=[]
    for s in report['sections']:
        b=base.get(s['variant'],{});g=soft_maps.get(s['variant'])
        out.append(dict(variant=s['variant'],mean_speed_mps=s['mean_speed_mps'],committed_mean_speed_mps=b.get('mean_speed_mps'),
                        speed_ratio=round(s['mean_speed_mps']/b['mean_speed_mps'],3) if s.get('mean_speed_mps') and b.get('mean_speed_mps') else None,
                        mean_sinkage_cm=s['mean_sinkage_cm'],committed_mean_sinkage_cm=b.get('mean_sinkage_cm'),
                        wheel_path_soft_share=soft_share(g,s['start_m']*100.,s['end_m']*100.,100.) if g else None))
    report['soft']['sections']=out
# ---- MudRunner MR5: breakable mud chunks (docs/MUDRUNNER_LESSONS_PLAN.md MR5 execution block item 7) -----------------------
CHUNK_VIEW=((7300.,-750.,250.),(8300.,50.,0.),60.);CHUNK_FIRM_DX=-4500.;CHUNK_CLOSE_CM=350.;CHUNK_CLUSTER_CM=150.
def chunk_rows():
    # Per section, the patch's MR5 readouts (its JSON) and the subsystem's world-wide awake peak.
    out=[]
    for name,x0,x1 in SECTIONS:
        p=patch_for(x0,x1)
        try:row=json.loads(p.describe_mud_chunks()) if p else {}
        except Exception:row={'error':traceback.format_exc().splitlines()[-1]}
        row['variant']=name;out.append(row)
    return out
def chunk_report(tag):
    rep=report.setdefault('chunks',{'cameras':{}})
    try:rep[tag]=dict(sections=chunk_rows(),awake_peak_world=mud.get_mud_chunk_awake_peak(),awake_now_world=mud.get_mud_chunk_awake_now(),capped=mud.get_mud_chunks_capped())
    except Exception:rep[tag]=dict(error=traceback.format_exc().splitlines()[-1])
def chunk_cluster(name,x0,x1):
    # The biggest cluster: the chunk with the most others within CHUNK_CLUSTER_CM (ties: the larger sizes), and the centroid of them.
    p=patch_for(x0,x1);pts=[(c.x,c.y,c.z) for c in (p.get_mud_chunks_for_check() if p else [])]
    if not pts:return None
    best=None
    for (x,y,sz) in pts:
        near=[(a,b,c) for (a,b,c) in pts if math.hypot(a-x,b-y)<=CHUNK_CLUSTER_CM]
        key=(len(near),sum(c for _,_,c in near))
        if best is None or key>best[0]:best=(key,near)
    near=best[1];cx=sum(a for a,_,_ in near)/len(near);cy=sum(b for _,b,_ in near)/len(near)
    return dict(count=len(near),x_cm=round(cx,1),y_cm=round(cy,1),sizes_cm=[round(c,1) for _,_,c in near],chunks_in_patch=len(pts))
def chunk_setup():
    # The readouts before driving and the three pictures before driving (queued with the soft spots' for the soft_before phase).
    rep=report.setdefault('chunks',{'cameras':{}});chunk_report('before')
    (cx,cy,cz),(tx,ty,tz),fov=CHUNK_VIEW
    soft_queue.append(('Chunks_Before',u.Vector(cx,cy,ground(cx,cy)+cz),u.Vector(tx,ty,ground(tx,ty)+tz),fov))
    cl=chunk_cluster('Standard',7500.,10000.);rep['cluster']=cl
    if cl:
        a=math.radians(30.);px=cl['x_cm']-CHUNK_CLOSE_CM*math.cos(a);py=cl['y_cm']-CHUNK_CLOSE_CM*math.sin(a)
        soft_queue.append(('Chunks_Close',u.Vector(px,py,ground(px,py)+SOFT_EYE_CM),u.Vector(cl['x_cm'],cl['y_cm'],surface_z(cl['x_cm'],cl['y_cm'])),65.))
    else:rep.setdefault('missing',[]).append('Chunks_Close (no chunk in Standard)')
    fx,fx2=cx+CHUNK_FIRM_DX,tx+CHUNK_FIRM_DX
    soft_queue.append(('Chunks_Firm',u.Vector(fx,cy,ground(fx,cy)+cz),u.Vector(fx2,ty,ground(fx2,ty)+tz),fov))
# ---- MudRunner MR1: the carried mud, the muddy grass, the splats --------------------------------------------------------
MR1_EXIT_X=22300.
MR1_GRASS_FROM=(15350.,-300.);MR1_GRASS_TURN_X=16600.;MR1_GRASS_TO=(20500.,-1250.);MR1_GRASS_DONE_X=20300.
MR1_SPIN_AT=(12440.,-340.);MR1_SPIN_S=6.;MR1_POST=(12160.,-420.)
MR2_CAR_X=21200.;TP_LEAD=200.;TP_INTO=600.;TP_MAX_S=240.
MR3_AT=(12250.,0.);MR3_CHURN_S=4.;MR3_SETTLE_S=60.;MR3_SCAN_DX=20.;MR3_SCAN_DY=10.
# MR2: the scripted pass's MR1 phases when the drive did not get through (FAST): shorter legs, ended by distance, each at most
# FAST_CAP_S of real time (a game running holds the editor to 1-2 frames a second and the car's physics to a fraction of that).
FAST=False;FAST_CAP_S=300.;MR1_FAST_EXIT_X=21000.;MR1_FAST_GRASS_FROM=(16300.,-300.);MR1_FAST_GRASS_TURN_X=17600.;MR1_FAST_SPIN_BLOBS=480
mr1={};paint=None;splats=None;spray=None
def subsystem(cls):
    return next(o for o in u.ObjectIterator(cls) if o.get_outer()==world)
def loads():
    return [round(w.mud_load,3) for w in car.get_traction().wheels]
def steer_to(tx,ty,throttle,top=8.):
    global PARKED
    PARKED=False
    pos=car.get_actor_location();yaw=car.get_actor_rotation().yaw;speed=car.get_velocity().length()/100.
    error=(math.degrees(math.atan2(ty-pos.y,tx-pos.x))-yaw+180)%360-180;car.set_raw_steer(max(-.65,min(.65,error/24)))
    move.set_throttle_input(throttle);move.set_brake_input(.4 if speed>top else 0.)
    return pos,speed
def park():
    # MR2b: the brake pedal held at a stop is reverse (UGTDrivetrainComponent, as Chaos's ReverseAsBrake): parked in Deep after
    # the spin-up the wheels spun backward for the whole wait and turned every spray fan forward (the third and fourth runs).
    # tick() lets the pedal go once the car is slow (PARKED); the handbrake holds it.
    global PARKED
    move.set_throttle_input(0);move.set_brake_input(1);move.set_handbrake_input(True);car.set_raw_steer(0.);PARKED=True
def shoot(name,cpos,ctarget,fov,now):
    global pending_shot
    aim_camera(cpos,ctarget,fov)
    report.setdefault('cameras',{})[name]=dict(location=[round(cpos.x,1),round(cpos.y,1),round(cpos.z,1)],target=[round(ctarget.x,1),round(ctarget.y,1),round(ctarget.z,1)],fov=fov)
    path=OUT/(name+'.png');report['images'].append(str(path));pending_shot=(now+1.5,path,FRAME+SHOT_FRAMES)
def splat_counts():
    return dict(landscape_splats=splats.get_landscape_splats(),decal_splats=splats.get_decal_splats(),live_decals=splats.get_live_decal_count(),
                traces=splats.get_trace_count(),capped_traces=splats.get_capped_traces(),ignored_hits=splats.get_ignored_hits(),
                skipped_traces=splats.get_skipped_traces(),height_splats=splats.get_height_splats(),held_decals=splats.get_held_decals(),
                pending_decals=splats.get_pending_decal_count(),
                paint_splats=paint.get_splat_count(),carried_blots=paint.get_carried_blot_count(),carried_gaps=paint.get_carried_gap_count(),
                thrown_blobs=spray.get_throw_blobs_emitted(),landed_blobs=spray.get_throw_blobs_landed(),lost_blobs=spray.get_throw_blobs_lost(),
                splatted_blobs=spray.get_throw_blobs_splatted(),splatted_cm3=round(spray.get_throw_splatted_cm3(),0),
                body_traces=spray.get_body_traces(),body_capped=spray.get_body_traces_capped(),blobs_on_car=spray.get_throw_blobs_on_car(),
                on_car_cm3=round(spray.get_throw_on_car_cm3(),0),play_s=round(u.GameplayStatics.get_time_seconds(world),2),
                frames=u.SystemLibrary.get_frame_count(),real_s=round(time.monotonic(),2))
def per_second(a,b):
    # MR2 housekeeping 4: the traces, refusals and skips per second of play between two splat_counts.
    dt=max(.001,b['play_s']-a['play_s']);fr=max(1,b['frames']-a['frames'])
    return dict(play_s=round(dt,1),real_s=round(b['real_s']-a['real_s'],1),frames=fr,fps=round(fr/max(.001,b['real_s']-a['real_s']),2),
                refused_per_frame=round((b['capped_traces']-a['capped_traces'])/fr,2),traces_per_frame=round((b['traces']-a['traces'])/fr,2),
                traces_per_s=round((b['traces']-a['traces'])/dt,1),refused_per_s=round((b['capped_traces']-a['capped_traces'])/dt,1),
                skipped_per_s=round((b['skipped_traces']-a['skipped_traces'])/dt,1),height_splats=b['height_splats']-a['height_splats'],
                body_traces_per_s=round((b['body_traces']-a['body_traces'])/dt,1),body_refused_per_s=round((b['body_capped']-a['body_capped'])/dt,1),
                blobs_on_car=b['blobs_on_car']-a['blobs_on_car'])
def body_report():
    st=car.get_body_state();bd=car.get_body()
    regions={}
    for name in ('FRONT','REAR','ARCH_FL','ARCH_FR','ARCH_RL','ARCH_RR','SIDE_L','SIDE_R','ROOF','GLASS'):
        reg=getattr(u.GTDamageRegion,name,None)
        if reg is not None:regions[name.lower()]=round(st.get_dirt(reg),3)
    g=bd.get_wheel_geom()
    return dict(describe=st.describe(),regions=regions,mud_line_cm=round(st.mud_line_cm,1),coat_line_cm=round(st.coat_line_cm,1),wash_cm=round(st.wash_cm,1),
                wash_amount=round(st.wash_amount,3),mud_wet=round(st.mud_wet,3),tyres=[round(t,3) for t in st.tyre_coat],hits=st.get_throw_hits(),glass_hits=st.get_glass_hits(),
                mud_base_z=round(bd.get_mud_base_z(),1),wheel_geom=[round(g.x,1),round(g.y,1),round(g.z,1),round(g.w,1)],tyre_slots=bd.get_tyre_slots(),
                fan_coat=[round(c,3) for c in st.fan_coat],fan_dir=[round(c,1) for c in st.fan_dir])
def cell_centre(x,y):
    # The mud grid's cell centre under (x, y): the CPU's value is the blot there (25 cm cells over the 128 m window).
    o=paint.get_origin();lo_x=o.x-6400.;lo_y=o.y-6400.
    return u.Vector(lo_x+(math.floor((x-lo_x)/25.)+.5)*25.,lo_y+(math.floor((y-lo_y)/25.)+.5)*25.,0.)
def carry_profile(x0,x1,yc):
    # The track paint's G (the CPU mirror, 25 cm cells) every 25 cm along the car's line, per side: the most of any cell 20-150 cm
    # to that side of the line (so a track that drifts is still read); per 5 m the mean, and the gap share (that most under 0.02).
    out=[]
    for side,sign in (('left (-y)',-1.),('right (+y)',1.)):
        xs=[x0+25.*i for i in range(int((x1-x0)/25.)+1)]
        best=[max(((paint.sample_coverage(u.Vector(x,yc+sign*(20.+10.*k),0.)),yc+sign*(20.+10.*k)) for k in range(14)),key=lambda t:t[0]) for x in xs]
        vals=[g for g,_y in best]
        bins=[round(statistics.fmean(vals[i:i+20]),3) for i in range(0,len(vals)-1,20)]
        # The GPU's G and B (the render target the materials read) at the CPU's best cell of each 5 m: the mirror check.
        mirror=[]
        for i in range(0,len(vals)-1,20):
            j=max(range(i,min(i+20,len(vals))),key=lambda n:vals[n]);gb=paint.read_render_target_mud(cell_centre(xs[j],best[j][1]))
            mirror.append([round(vals[j],3),round(gb.x,3),round(gb.y,3)])
        out.append(dict(side=side,mean_by_5m=bins,gap_share=round(sum(v<.02 for v in vals)/len(vals),3),max_g=round(max(vals),3),cells=len(vals),cpu_gpu_g_b=mirror))
    return out
def droplet_boxes(cpos,ctarget,fov):
    # MR2b item 3: two boxes on the car's right side (+Y, the camera's), the same height band on the door: behind the right rear
    # arch (5-50 cm behind its edge) and mid-door (50 cm about the middle between the arches' inner edges), 92-114 cm above the
    # wheel bottoms (under the belt). Their corners in world space (the car's mesh transform) with the camera, for
    # Art/count_car_droplets.py.
    bd=car.get_body();g=bd.get_wheel_geom();base=bd.get_mud_base_z();mesh=car.get_component_by_class(u.SkeletalMeshComponent)
    t=mesh.get_world_transform();front,rear,rad=g.x,g.y,g.w;mid=.5*((front-rad)+(rear+rad));side=85.
    boxes={'behind_rear_arch':(rear-rad-50.,rear-rad-5.),'mid_door':(mid-25.,mid+25.)}
    out=dict(camera=dict(location=[cpos.x,cpos.y,cpos.z],target=[ctarget.x,ctarget.y,ctarget.z],fov=fov),view=list(VIEW),z_band_cm=[92.,114.],side_y_cm=side,boxes={})
    for name,(x0,x1) in boxes.items():
        corners=[]
        for x,z in ((x0,92.),(x1,92.),(x1,114.),(x0,114.)):
            w=u.MathLibrary.transform_location(t,u.Vector(x,side,base+z));corners.append([round(w.x,2),round(w.y,2),round(w.z,2)])
        out['boxes'][name]=dict(car_x_cm=[round(x0,1),round(x1,1)],world_corners=corners)
    return out
def settled(now,since,cap=90.):
    # MR2: the car at rest on the ground after a placement (at a game's 1-2 frames a second a fixed wait left it in the air:
    # the first Car_Muddy_Side looked up at its underside), or the cap.
    pos=car.get_actor_location()
    return (car.get_velocity().length()<25. and pos.z-ground(pos.x,pos.y)<60. and gsince()>2.) or gsince()>cap   # game time (since the phase began)
def fan_trace(where):
    # MR2b: the spray fans' sides through the run's phases (the second run found every fan forward after MR1's phases).
    st=car.get_body_state();report.setdefault('fan_trace',[]).append(dict(at=where,x_m=round(car.get_actor_location().x/100.,2),fan_dir=[round(c,1) for c in st.fan_dir],fan_side=[round(c,2) for c in st.fan_side],fan_coat=[round(c,2) for c in st.fan_coat]))
def mr1_tick(now):
    global phase,last
    if phase in ('mr1_start','mr1_grass_place','mr1_grass_wait','mr1_spin_place','mr1_spin','mr1_spin_wait','mr1_done') and (not report.get('fan_trace') or report['fan_trace'][-1]['at']!=phase):fan_trace(phase)
    if phase=='mr1_start':
        car.set_actor_hidden_in_game(False);pc.set_view_target_with_blend(car,0.)
        mr1['loads_at_stop']=loads();mr1['stop_x_m']=round(car.get_actor_location().x/100.,2)
        mr1['counts_before']=splat_counts();mr1['fast']=FAST
        # FAST (the drive stalled under a game): the scripted pass's Stony leg left the car rolling through Stony; it drives on out
        # from there (set down 4 m before Stony's end from a standstill the car bogged at its exit lip for 300 s, the second run).
        car.reset_driving_inputs();move.set_handbrake_input(False);move.set_target_gear(1,True);phase='mr1_exit';last=now
    elif phase=='mr1_exit':
        pos,speed=steer_to(pos_x(car)+650.,0.,1. if FAST else .6)
        exit_x=MR1_FAST_EXIT_X if FAST else MR1_EXIT_X
        if pos.x>=exit_x or gsince()>(FAST_CAP_S if FAST else 40):
            park();mr1['exit']=dict(reached=bool(pos.x>=exit_x),x_m=round(pos.x/100.,2),loads=loads(),s=round(gsince(),1));phase='mr1_exit_wait';last=now
    elif phase=='mr1_exit_wait' and settled(now,last,30.) and GATE.ready(world,pc):   # its profile reads the GPU's G
        pos=car.get_actor_location()
        x0=19700. if not FAST else 19200.;x1=min(22100.,pos.x-250.)
        mr1['exit']['profile']=carry_profile(x0,max(x0+500.,x1),pos.y)
        gz=ground(pos.x-300.,pos.y);look=20050. if not FAST else 19400.
        shoot('Carry_Exit',u.Vector(pos.x-300.,pos.y+40.,gz+190.),u.Vector(look,pos.y,ground(look,pos.y)),35.,now);phase='mr1_grass_place';last=now
    elif phase=='mr1_grass_place' and now-last>3.5:
        place_car(*(MR1_FAST_GRASS_FROM if FAST else MR1_GRASS_FROM));mr1['grass']=dict(path=[]);phase='mr1_grass_settle';last=now
    elif phase=='mr1_grass_settle' and settled(now,last):
        car.reset_driving_inputs();move.set_handbrake_input(False);move.set_target_gear(1,True);phase='mr1_grass_drive';last=now;mr1['grass']['sample_at']=0.
    elif phase=='mr1_grass_drive':
        here=car.get_actor_location()
        turn_x=MR1_FAST_GRASS_TURN_X if FAST else MR1_GRASS_TURN_X   # FAST: 11 m of Stony's mud first (set 2 m before it)
        if here.x<turn_x:pos,speed=steer_to(here.x+650.,(MR1_FAST_GRASS_FROM if FAST else MR1_GRASS_FROM)[1],1.,10.)   # the run-up, straight into fresh mud
        else:pos,speed=steer_to(MR1_GRASS_TO[0],MR1_GRASS_TO[1],1.)
        if now-mr1['grass']['sample_at']>=.2:
            mr1['grass']['sample_at']=now
            for w in car.get_traction().wheels:
                c=w.contact_point;mr1['grass']['path'].append((c.x,c.y,w.mud_load))
        if pos.x>=MR1_GRASS_DONE_X or gsince()>(FAST_CAP_S if FAST else 30):
            park();mr1['grass'].update(reached=bool(pos.x>=MR1_GRASS_DONE_X),end_m=[round(pos.x/100.,2),round(pos.y/100.,2)],loads=loads(),s=round(gsince(),1));phase='mr1_grass_wait';last=now
    elif phase=='mr1_grass_wait' and now-last>2.5 and GATE.ready(world,pc):   # the verge points read the GPU's G
        g=mr1['grass'];verge=[(x,y,l) for x,y,l in g.pop('path') if abs(y)>800.]
        vals=[paint.sample_coverage(u.Vector(x,y,0.)) for x,y,_l in verge]
        gpu=[paint.read_render_target_mud(cell_centre(x,y)).x for x,y,_l in verge]
        g.update(verge_points=len(verge),verge_with_mud=sum(v>=.02 for v in vals),verge_mean_g=round(statistics.fmean(vals),3) if vals else None,
                 verge_mean_gpu_g=round(statistics.fmean(gpu),3) if gpu else None,
                 verge_load_first=round(verge[0][2],3) if verge else None,verge_load_last=round(verge[-1][2],3) if verge else None)
        g.pop('sample_at',None);parked=car.get_actor_location();car.set_actor_hidden_in_game(True)
        # MR2 housekeeping 2: the camera 1.4 m from the verge point with the most mud (toward the road), 0.6 m up, at the clumps' feet.
        # MR2b: only a verge point the car crossed and did not park on (none within 4 m of where it stopped: run 8's camera stood in
        # a clump the parked car had flattened).
        crossed=[(x,y) for x,y,_l in verge if math.hypot(x-parked.x,y-parked.y)>400.]
        g['verge_points_crossed']=len(crossed);g['parked_at_m']=[round(parked.x/100.,2),round(parked.y/100.,2)]
        bx,by=max(crossed or [(x,y) for x,y,_l in verge],key=lambda p:paint.sample_coverage(u.Vector(p[0],p[1],0.)),default=(19700.,-1050.))
        g['camera_at_m']=[round(bx/100.,2),round(by/100.,2),round(paint.sample_coverage(u.Vector(bx,by,0.)),3)]
        g['camera_g_wet']=[round(paint.sample_coverage(u.Vector(bx,by,0.)),3),round(paint.sample_wetness(u.Vector(bx,by,0.)),3)]
        shoot('Carry_Grass',u.Vector(bx-115.,by+80.,ground(bx-115.,by+80.)+60.),u.Vector(bx,by,ground(bx,by)+8.),60.,now);phase='mr1_grass_diag';last=now
        g['camera']=dict(location=[round(bx-115.,1),round(by+80.,1)],target=[round(bx,1),round(by,1)])
    elif phase=='mr1_grass_diag' and now-last>3.5:
        # MR2 housekeeping 2: the nearest tussock instances' origins against the ground and their G, then the same camera with
        # gt.Mud.GrassMud 0 (Carry_Grass_Off.png): the pair shows the blades' muddy feet against none.
        g=mr1['grass'];bx,by=g['camera']['target'];near=[]
        for c in u.GameplayStatics.get_all_actors_of_class(world,u.Actor):
            if c.get_actor_label()!='TS_ApprovedTussock':continue
            for comp in c.get_components_by_class(u.InstancedStaticMeshComponent):
                g.setdefault('grass_material',comp.get_material(0).get_path_name() if comp.get_material(0) else None)
                for i in range(comp.get_instance_count()):
                    t=comp.get_instance_transform(i,True)
                    if isinstance(t,tuple):t=t[-1]
                    if t is None or not hasattr(t,"translation"):continue
                    l=t.translation
                    d=math.hypot(l.x-bx,l.y-by)
                    if d<300.:near.append(dict(d_cm=round(d,1),z_minus_ground_cm=round(l.z-ground(l.x,l.y),1),scale=round(t.scale3d.z,2),g=round(paint.sample_coverage(u.Vector(l.x,l.y,0.)),3)))
        g['near_instances']=sorted(near,key=lambda r:r['d_cm'])[:8]
        mpc=u.load_asset('/Game/GrandTour/Terrain/MPC_TrackPaint');g['mpc_grass_mud']=u.MaterialLibrary.get_scalar_parameter_value(world,mpc,'GrassMud')
        console('gt.Mud.GrassMud 0');cam=g['camera']['location']
        shoot('Carry_Grass_Off',u.Vector(cam[0],cam[1],ground(cam[0],cam[1])+60.),u.Vector(bx,by,ground(bx,by)+8.),60.,now);phase='mr1_grass_restore';last=now
    elif phase=='mr1_grass_restore' and now-last>3.5:
        console('gt.Mud.GrassMud 1');phase='mr1_spin_place';last=now
    elif phase=='mr1_spin_place' and now-last>3.5:
        car.set_actor_hidden_in_game(False);place_car(*MR1_SPIN_AT);mr1['spin']=dict(before=splat_counts());phase='mr1_spin_settle';last=now
    elif phase=='mr1_spin_settle' and settled(now,last):
        car.reset_driving_inputs();move.set_handbrake_input(False);move.set_target_gear(1,True);car.set_raw_steer(0.);phase='mr1_spin';last=now
        mr1['spin']['blobs0']=spray.get_throw_blobs_emitted()
    elif phase=='mr1_spin':
        move.set_throttle_input(1.);move.set_brake_input(0.);car.set_raw_steer(0.)
        # Under a game the frames are slow and the physics slower: the spin lasts until it has thrown as many blobs as 6 s did in
        # the clean run (484), at most FAST_CAP_S.
        thrown=spray.get_throw_blobs_emitted()-mr1['spin']['blobs0']
        if (not FAST and gsince()>=MR1_SPIN_S) or (FAST and (thrown>=MR1_FAST_SPIN_BLOBS or gsince()>FAST_CAP_S)):
            park();mr1['spin'].update(end_x_m=round(car.get_actor_location().x/100.,2),loads=loads());phase='mr1_spin_wait';last=now
    elif phase=='mr1_spin_wait' and now-last>4:
        mr1['spin']['after']=splat_counts();mr1['spin']['decals_on']=sorted(set(splats.describe_decals()))
        mr1['spin']['decal_material_ready']=bool(splats.is_decal_material_ready());mr1['spin']['per_second']=per_second(mr1['spin']['before'],mr1['spin']['after'])
        if mr1['spin']['after']['decal_splats']==mr1['spin']['before']['decal_splats']:
            # The spin-up's own blobs reached no mesh (at Deep's 60 cm sinkage LM2a's blobs leave from the sunk contact and come
            # down within about half a metre): 24 synthetic blob paths from the left rear wheel's place at the post, through the
            # same splat call, so the decal path is seen. Counted apart.
            import random
            rnd=random.Random(11);gz=ground(MR1_POST[0],MR1_POST[1]);made=0
            sx,sy=MR1_SPIN_AT[0]-124.,MR1_SPIN_AT[1]-80.
            for k in range(24):
                ty=MR1_POST[1]+rnd.uniform(-12.,12.);tz=gz+rnd.uniform(15.,120.)
                start=u.Vector(sx,sy+rnd.uniform(-10.,10.),gz+rnd.uniform(10.,40.));d=u.Vector(MR1_POST[0]-start.x,ty-start.y,tz-start.z)
                end=u.Vector(start.x+1.6*d.x,start.y+1.6*d.y,start.z+1.6*d.z)
                made+=1 if splats.trace_splat(start,end,rnd.uniform(3.,8.),1000+k) else 0
            mr1['spin']['synthetic']=dict(paths=24,splats=made,decals_on=sorted(set(splats.describe_decals())))
        car.set_actor_hidden_in_game(True);gz=ground(MR1_POST[0],MR1_POST[1])
        shoot('Splat_Post',u.Vector(12330.,-190.,ground(12330.,-190.)+130.),u.Vector(MR1_POST[0],MR1_POST[1],gz+60.),55.,now);phase='mr1_done';last=now
    elif phase=='mr1_done' and now-last>3.5:
        mr1['counts_after']=splat_counts();report['mr1']=mr1
        if run.get('counts0'):mr1['whole_run_per_second']=per_second(run['counts0'],mr1['counts_after'])
        # MR2 item 7: the muddy car, still, on the gravel past Stony (its mud is whatever the run gave it: nothing is added here).
        report['mr2']=dict(before_place=body_report())
        car.set_actor_hidden_in_game(False);place_car(MR2_CAR_X,0.);phase='mr2_settle';last=now
    elif phase=='mr2_settle' and settled(now,last):
        pos=car.get_actor_location();gz=ground(pos.x,pos.y);report['mr2']['car_at_m']=[round(pos.x/100.,2),round(pos.y/100.,2)]
        report['mr2']['state']=body_report()
        # From the car's right (+Y): the sun is behind its left side here (the second run's left side was in its own shadow).
        # MR2b: 6.4 m off (MR2: 4.7 m), so the whole car and both arches' fans are in the picture.
        cpos=u.Vector(pos.x-25.,pos.y+640.,gz+110.);ctarget=u.Vector(pos.x-25.,pos.y,gz+75.)
        shoot('Car_Muddy_Side',cpos,ctarget,50.,now);phase='mr2_side';last=now
        report['mr2']['droplet_boxes']=droplet_boxes(cpos,ctarget,50.)
    elif phase=='mr2_side' and now-last>3.5:
        pos=car.get_actor_location();gz=ground(pos.x,pos.y)
        shoot('Car_Muddy_Rear',u.Vector(pos.x-560.,pos.y+170.,gz+135.),u.Vector(pos.x-120.,pos.y,gz+75.),50.,now);phase='mr2_rest';last=now
    elif phase=='mr2_rest' and now-last>3.5:
        # The section pictures the scripted pass left for after MR1 (FAST), the car hidden.
        if run.get('pictures_after_mr1'):
            car.set_actor_hidden_in_game(True)
            name,cpos,ctarget,fov=run['pictures_after_mr1'].pop(0);shoot(name,cpos,ctarget,fov,now);last=now;return
        phase='mr3_place';last=now
    elif phase.startswith('mr3_'):
        mr3_tick(now)
    elif phase=='mr2_done' and now-last>3.5:
        report['mr2']['after_pictures']=body_report()
        missing=[p for p in report['images'] if not Path(p).exists()]
        report['missing_images']=missing
        drove=bool(report['drive']['completed'] or report.get('teleport_pass_done'))
        report['ok']=bool(drove and not missing and all(p['mesh_slice_ok'] and p['clod_slice_ok'] for p in report['patches']))
        if not report['ok'] and 'error' not in report:
            report['error']='drive %s (teleport pass %s); images missing %d; slices %s'%(report['drive']['ended'],report.get('teleport_pass_done'),len(missing),[(p['variant'],p['mesh_slice_ok'],p['clod_slice_ok']) for p in report['patches']])
        finish()
# ---- MudRunner MR3: churned rut pools in Deep -------------------------------------------------------------------------------
def game_s():
    return u.GameplayStatics.get_time_seconds(world)
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
GPHASE=None;GPH0=0.
def gsince():
    return gt()-GPH0
def deep_patch():
    return patch_for(12000.,14500.)
def most_churned(x0,x1):
    # The most turbidity in a 60 cm box (3 x 6 scan cells) over a 20 x 10 cm scan of the churned stretch, both tracks.
    p=deep_patch();xs=[x0+MR3_SCAN_DX*i for i in range(int((x1-x0)/MR3_SCAN_DX)+1)];ys=[-140.+MR3_SCAN_DY*j for j in range(29)]
    grid=[[p.turbidity_at(u.Vector2D(x,y)) for y in ys] for x in xs];best=(-1.,xs[0],0.)
    for i in range(len(xs)-2):
        for j in range(len(ys)-5):
            v=sum(grid[i+a][j+b] for a in range(3) for b in range(6))
            if v>best[0]:best=(v,xs[i+1],.5*(ys[j+2]+ys[j+3]))
    return best
def mr3_view(bx,by):
    gz=surface_z(bx,by)
    return u.Vector(bx-220.,by+260.,gz+190.),u.Vector(bx,by,gz-5.),45.
def mr3_written(name):
    # MR3b: the camera moves on only once the last picture is on disk (the first grazing run's Rut_Muddy was captured after the
    # camera had already moved to Rut_Muddy_Low: a screenshot frame's hitch under a game), or after 30 s.
    f=OUT/(name+'.png')
    return f.exists() and f.stat().st_mtime>=run.get('mr3_shot_t',0.)
def mr3_shoot(name,cpos,ctarget,fov,now):
    run['mr3_shot_t']=time.time();shoot(name,cpos,ctarget,fov,now)
def mr3_low_view(bx,by):
    # MR3b: eye level about 3 m from the pool (the grazing pair).
    cx,cy=bx-120.,by+275.
    return u.Vector(cx,cy,ground(cx,cy)+165.),u.Vector(bx,by,surface_z(bx,by)-5.),50.
def mr3_tick(now):
    global phase,last
    m=report.setdefault('mr3',{})
    if phase=='mr3_place':
        car.set_actor_hidden_in_game(False);place_car(*MR3_AT);m['placed_m']=[MR3_AT[0]/100.,MR3_AT[1]/100.];phase='mr3_settle';last=now
    elif phase=='mr3_settle' and settled(now,last):
        p=deep_patch();m['before_churn']=p.describe_muddy_water(u.Vector2D(MR3_AT[0]+200.,0.),400.)
        car.reset_driving_inputs();move.set_handbrake_input(False);move.set_target_gear(1,True);car.set_raw_steer(0.)
        run['mr3_game0']=game_s();run['mr3_from']=car.get_actor_location().x;phase='mr3_churn';last=now
    elif phase=='mr3_churn':
        pos,speed=steer_to(car.get_actor_location().x+650.,0.,1.,4.)
        if game_s()-run['mr3_game0']>=MR3_CHURN_S or gsince()>FAST_CAP_S:
            park();pos=car.get_actor_location()
            m['churn']=dict(game_s=round(game_s()-run['mr3_game0'],2),real_s=round(now-last,1),from_m=round(run['mr3_from']/100.,2),end_m=[round(pos.x/100.,2),round(pos.y/100.,2)],
                            wheels_m=[[round(w.contact_point.x/100.,2),round(w.contact_point.y/100.,2)] for w in car.get_traction().wheels],slip=[round(w.slip_magnitude,1) for w in car.get_traction().wheels],
                            sink_cm=[round(w.sinkage*100.,1) for w in car.get_traction().wheels])
            # Away from the pools (a parked car keeps stamping them as it sinks) and out of the picture.
            place_car(MR2_CAR_X,0.);car.set_actor_hidden_in_game(True)
            score,bx,by=most_churned(min(run['mr3_from'],pos.x)-200.,max(run['mr3_from'],pos.x)+200.)
            p=deep_patch();m['spot']=dict(x_m=round(bx/100.,2),y_m=round(by/100.,2),box_turbidity=round(score,2),cell=round(p.turbidity_at(u.Vector2D(bx,by)),3),
                                          water_table_cm=p.water_table_cm,mud_cm=round(mud.mud_height_cm_at(u.Vector2D(bx,by)),2))
            m['at_muddy']=p.describe_muddy_water(u.Vector2D(bx,by),60.);m['tiles_at_muddy']=p.turbid_tile_count()
            cpos,ctarget,fov=mr3_view(bx,by);run['mr3_view']=(bx,by);mr3_shoot('Rut_Muddy',cpos,ctarget,fov,now);run['mr3_shot']=game_s();phase='mr3_muddy_low';last=now
    elif phase=='mr3_muddy_low' and now-last>3.5 and (mr3_written('Rut_Muddy') or now-last>30.):
        bx,by=run['mr3_view'];p=deep_patch();m['at_muddy_low']=p.describe_muddy_water(u.Vector2D(bx,by),60.);m['muddy_low_after_game_s']=round(game_s()-run['mr3_shot'],1)
        cpos,ctarget,fov=mr3_low_view(bx,by);mr3_shoot('Rut_Muddy_Low',cpos,ctarget,fov,now);phase='mr3_wait';last=now
    elif phase=='mr3_wait' and now-last>3.5 and game_s()-run['mr3_shot']>=MR3_SETTLE_S and (mr3_written('Rut_Muddy_Low') or now-last>30.):
        bx,by=run['mr3_view'];p=deep_patch()
        m['settled_after']=dict(game_s=round(game_s()-run['mr3_shot'],1),real_s=round(now-last,1))
        m['at_settled']=p.describe_muddy_water(u.Vector2D(bx,by),60.);m['cell_settled']=round(p.turbidity_at(u.Vector2D(bx,by)),3);m['tiles_at_settled']=p.turbid_tile_count()
        cpos,ctarget,fov=mr3_view(bx,by);mr3_shoot('Rut_Settled',cpos,ctarget,fov,now);phase='mr3_settled_low';last=now
    elif phase=='mr3_settled_low' and now-last>3.5 and (mr3_written('Rut_Settled') or now-last>30.):
        bx,by=run['mr3_view'];p=deep_patch();m['at_settled_low']=p.describe_muddy_water(u.Vector2D(bx,by),60.)
        cpos,ctarget,fov=mr3_low_view(bx,by);mr3_shoot('Rut_Settled_Low',cpos,ctarget,fov,now);phase='mr3_done';last=now
    elif phase=='mr3_done' and now-last>3.5 and (mr3_written('Rut_Settled_Low') or now-last>30.):
        phase='mrp_start';last=now   # MRP: the PBR pictures and captures, then the report
# ---- MudRunner MRP: physically based mud, the parallax, the PBR validation captures -------------------------------------------
# The look pictures (each POM 2 - the default - and, where asked, POM 0), then the buffer-visualisation captures: HighResShot's
# buffer dump (r.BufferVisualizationOverviewTargets BaseColor, Roughness, MaterialAO; uncompressed EXR) per variant's ground, the
# gravel (the calibration: roughness 0.9 by construction), the car; Art/sample_mud_pbr.py reads them (the wrapper runs it).
MRP_TARGETS='BaseColor,Roughness,MaterialAO'
MRP_CALIB=(6500.,260.)   # gravel between Firm and Standard, off the line (the strip's groundtex, roughness 0.9)
def shoot_dump(name,cpos,ctarget,fov,now,kind,**extra):
    # A buffer dump: the HighResShot's arguments 0 0 0 0 0 1 1 (no region, no mask, dump the buffers, HDR: EXR).
    global pending_shot
    aim_camera(cpos,ctarget,fov)
    cam=dict(location=[round(cpos.x,1),round(cpos.y,1),round(cpos.z,1)],target=[round(ctarget.x,1),round(ctarget.y,1),round(ctarget.z,1)],fov=fov)
    report.setdefault('cameras',{})[name]=cam
    report.setdefault('mrp',{}).setdefault('dumps',[]).append(dict(name=name,kind=kind,base=str((OUT/name).as_posix()),camera=cam,**extra))
    run['mrp_shot_t']=time.time();pending_shot=(now+1.5,OUT/(name+'.png'),FRAME+SHOT_FRAMES,True)
def mrp_written(name,dump=False):
    # The camera moves on only once the capture is on disk (a dump's buffers last), or after 30 s.
    f=OUT/((name+'_MaterialAO.exr') if dump else (name+'.png'))
    return f.exists() and f.stat().st_mtime>=run.get('mrp_shot_t',0.)
def mrp_look(name,cpos,ctarget,fov,now):
    run['mrp_shot_t']=time.time();shoot(name,cpos,ctarget,fov,now)
def car_mud_box():
    # The sill band (15-45 cm above the wheel bottoms) between the arches on the car's +Y side: world corners (the mesh's transform).
    bd=car.get_body();g=bd.get_wheel_geom();base=bd.get_mud_base_z();t=car.get_component_by_class(u.SkeletalMeshComponent).get_world_transform()
    x0,x1=g.y+g.w+12.,g.x-g.w-12.;side=85.
    return [[round(v.x,2),round(v.y,2),round(v.z,2)] for v in (u.MathLibrary.transform_location(t,u.Vector(x,side,base+z)) for x,z in ((x0,15.),(x1,15.),(x1,45.),(x0,45.)))]
def mrp_views():
    # Standard's on-foot view (as MudVariants_Standard_OnFoot: 1.7 m over its -Y rut 3 m in, looking 12 m along it) and the close one:
    # 60 cm from untouched, sunlit mud 3.2 m right of the line (past the +Y rut's berm, inside the patch's +-6.8 m), 25 cm up
    # (about 25 degrees down), across the lumps. (The first run's spot, 1.65 m right, looked into the +Y rut's shadow: 74 % of the
    # picture under 20 of 255.)
    x0=7500.;ry=report['ruts']['Standard']['y_cm'];xa=x0+300.;xb=x0+1500.
    foot=(u.Vector(xa,ry,surface_z(xa,ry)+170.),u.Vector(xb,ry,surface_z(xb,ry)),65.)
    tx,ty=8800.,320.;tz=surface_z(tx,ty)
    close=(u.Vector(tx-55.,ty,surface_z(tx-55.,ty)+25.),u.Vector(tx,ty,tz),50.)
    # MRP follow-up: the same spot from 80 cm back and 29 cm up: about 20 degrees above the ground, across the lumps.
    steep=(u.Vector(tx-80.,ty,tz+29.),u.Vector(tx,ty,tz),45.)
    return foot,close,steep
def ground_view(name,x0,x1):
    # A capture of a section's ground: 2.2 m over it, 1.5 m back, looking down about 50 degrees at its -Y rut's middle (the whole
    # picture inside the patch).
    mid=.5*(x0+x1);ry=report['ruts'][name]['y_cm'];gz=surface_z(mid,ry)
    return u.Vector(mid-150.,ry+40.,gz+220.),u.Vector(mid+20.,ry,gz),50.
def mrp_tick(now):
    global phase,last
    m=report.setdefault('mrp',{})
    if phase=='mrp_start':
        car.set_actor_hidden_in_game(True)
        foot,close,steep=mrp_views()
        bx,by=run['mr3_view'];rut=mr3_view(bx,by)
        # (name, POM level, view); POM 2 is the default the others leave behind.
        run['mrp_queue']=[('Mud_PBR_OnFoot_POM0',0,foot),('Mud_PBR_OnFoot',2,foot),('Mud_PBR_Close_POM0',0,close),('Mud_PBR_Close',2,close),
                          ('Mud_PBR_Close_Steep',2,steep),('Mud_PBR_Close_Steep_NoShadow',-2,steep),('Rut_Settled_PBR',2,rut)]
        p=deep_patch();m['at_rut_settled_pbr']=p.describe_muddy_water(u.Vector2D(bx,by),60.)
        # The water's roughness model (translucent: no GBuffer): the turbidity over the pool's cells round the spot, 20 cm apart.
        cells=[p.turbidity_at(u.Vector2D(bx+20.*i,by+20.*j)) for i in range(-5,6) for j in range(-5,6)]
        m['water_model']=dict(note='live_mud_style MUDDY_HLSL with gt.Mud.PBR 1: lerp(SettledRoughPBR, TurbidRoughPBR, turbidity) (froth off: settled)',
                              settled_rough=0.15,turbid_rough=0.5,turbidity=[round(c,4) for c in cells],at=[round(bx,1),round(by,1)])
        phase='mrp_look';last=now
    elif phase=='mrp_look' and now-last>3.5 and (not run.get('mrp_last') or mrp_written(run['mrp_last']) or now-last>30.):
        if not run['mrp_queue']:
            console('gt.Mud.POM 2');phase='mrp_car_place';last=now;return
        name,pom,(cpos,ctarget,fov)=run['mrp_queue'].pop(0)
        # MRP follow-up: a negative level is that POM with gt.Mud.POMShadow 0 (the stepping's cause: the march or the shadow).
        console('gt.Mud.POM %d'%abs(pom));console('gt.Mud.POMShadow %d'%(0 if pom<0 else 1));m.setdefault('pictures',[]).append(dict(name=name,pom=abs(pom),pbr=1,shadow=0 if pom<0 else 1))
        mrp_look(name,cpos,ctarget,fov,now);run['mrp_last']=name;last=now
    elif phase=='mrp_car_place' and now-last>3.5:
        car.set_actor_hidden_in_game(False);place_car(MR2_CAR_X,0.);phase='mrp_car_settle';last=now
    elif phase=='mrp_car_settle' and settled(now,last):
        pos=car.get_actor_location();gz=ground(pos.x,pos.y)
        cpos=u.Vector(pos.x-25.,pos.y+640.,gz+110.);ctarget=u.Vector(pos.x-25.,pos.y,gz+75.)
        m['car']=body_report();m['car_at_m']=[round(pos.x/100.,2),round(pos.y/100.,2)]
        run['mrp_car_view']=(cpos,ctarget)
        mrp_look('Car_Muddy_PBR',cpos,ctarget,50.,now);run['mrp_last']='Car_Muddy_PBR';phase='mrp_dumps';last=now
    elif phase=='mrp_dumps' and now-last>3.5 and (mrp_written('Car_Muddy_PBR') or now-last>30.):
        # The captures: the buffers in the materials' own (linear) values.
        console('r.BufferVisualizationOverviewTargets %s'%MRP_TARGETS);console('r.SaveEXR.CompressionQuality 0');console('r.PostProcessingColorFormat 1')
        cpos,ctarget=run['mrp_car_view']
        run['mrp_dumps']=[('PBR_Car','car',(cpos,ctarget,50.),dict(box_world=car_mud_box(),mud_wet=round(car.get_body_state().mud_wet,3)))]
        cx,cy=MRP_CALIB;cz=ground(cx,cy)
        run['mrp_dumps'].append(('PBR_Calib','calib',(u.Vector(cx-150.,cy,cz+200.),u.Vector(cx+30.,cy,cz),50.),{}))
        for name,x0,x1 in SECTIONS:
            run['mrp_dumps'].append(('PBR_%s_Ground'%name,'ground',ground_view(name,x0,x1),dict(variant=name)))
        run['mrp_last_dump']=None;phase='mrp_dump_next';last=now
    elif phase=='mrp_dump_next' and now-last>3.5 and (not run['mrp_last_dump'] or mrp_written(run['mrp_last_dump'],True) or now-last>30.):
        if not run['mrp_dumps']:
            # MRP follow-up 2: the 32-bit post-process chain off again between dumps (two runs ended out of video memory on 6 GB).
            console('r.PostProcessingColorFormat 0')
            car.set_actor_hidden_in_game(True);phase='mrp_wet';last=now;return
        name,kind,(cpos,ctarget,fov),extra=run['mrp_dumps'].pop(0)
        car.set_actor_hidden_in_game(kind!='car')
        shoot_dump(name,cpos,ctarget,fov,now,kind,**extra);run['mrp_last_dump']=name;last=now
def carry_mirror(tag):
    # GR1c checks follow-up (PBR_CarryWet): the track paint's CPU mirror against the render target the materials read, over the
    # carried-mud spot's grid (200-206 m, +-1.5 m, 25 cm), with the scene rendered or not at that moment: G and B, mean and the
    # largest difference, and the CPU's G spread (cells over 0.05).
    rows=[]
    for i in range(25):
        for j in range(13):
            p=cell_centre(20000.+25.*i,-150.+25.*j);gb=paint.read_render_target_mud(p)
            rows.append((paint.sample_coverage(p),paint.sample_wetness(p),gb.x,gb.y))
    lit=[r for r in rows if r[0]>.05 or r[2]>.05]
    def mean(v):return round(statistics.fmean(v),4) if v else None
    # And the weather the ground material reads there: MPC_Weather's wetness and occlusion window, and per cell MF_Weather's own open
    # (1 - saturate((cover - z - 20) / 40), the cover from RT_RainOcclusion's depth under the window's top) and its fill
    # (saturate(wetness x open x 1.6 - 0.25), which moves the puddles' edge until it reaches 1).
    occ=None
    try:
        mpc=u.load_asset('/Game/GrandTour/Materials/MPC_Weather');km=getattr(u,'MaterialLibrary',None) or getattr(u,'KismetMaterialLibrary')
        wet=km.get_scalar_parameter_value(world,mpc,'Wetness');on=km.get_scalar_parameter_value(world,mpc,'OcclusionEnabled')
        b=km.get_vector_parameter_value(world,mpc,'OcclusionBounds');em=weather.get_rain_emitter()
        rt=u.load_asset('/Game/GrandTour/Materials/RT_RainOcclusion');res=rt.size_x if rt else 0
        opens=[];covers=[]
        for i in range(0,25,4):
            for j in range(0,13,3):
                x,y=20000.+25.*i,-150.+25.*j
                uu=.5+(y-b.g)/(2.*max(b.a,1.));vv=.5-(x-b.r)/(2.*max(b.a,1.))
                if not rt or not (0.<uu<1. and 0.<vv<1.):continue
                d=u.RenderingLibrary.read_render_target_raw_pixel(world,rt,int(uu*res),int(vv*res),False).r
                cz=b.b-d;z=ground(x,y);covers.append(round(cz-z,1));opens.append(1.-min(1.,max(0.,(cz-z-20.)/40.)))
        occ=dict(mpc_wetness=round(wet,4),occlusion_enabled=round(on,2),bounds=[round(b.r,1),round(b.g,1),round(b.b,1),round(b.a,1)],
                 emitter=em.describe() if em else None,rt_size=res,cover_minus_ground_cm=covers,open_min=round(min(opens),3) if opens else None,
                 open_mean=round(statistics.fmean(opens),3) if opens else None,fill_min=round(min(min(1.,max(0.,wet*o*1.6-.25)) for o in opens),3) if opens else None)
    except Exception as e:
        occ=dict(error=str(e))
    return dict(tag=tag,rendering=bool(GATE.on),game_s=round(gt(),2),cells=len(rows),cells_with_mud=len(lit),weather=occ,
                cpu_g_mean=mean([r[0] for r in lit]),gpu_g_mean=mean([r[2] for r in lit]),cpu_b_mean=mean([r[1] for r in lit]),gpu_b_mean=mean([r[3] for r in lit]),
                g_abs_diff_mean=mean([abs(r[0]-r[2]) for r in lit]),g_abs_diff_max=round(max([abs(r[0]-r[2]) for r in lit] or [0.]),4),
                b_abs_diff_mean=mean([abs(r[1]-r[3]) for r in lit]),b_abs_diff_max=round(max([abs(r[1]-r[3]) for r in lit] or [0.]),4),
                cpu_g_over=[sum(r[0]>x for r in lit) for x in (.1,.2,.3,.4)])
def mrp_wet_tick(now):
    # MRP follow-up: carried mud in the rain. The tracks laid in MR1 are gone by now (the track paint's window followed the car to
    # Deep for MR3), so fresh ones first: the car set in Stony's mud at 183 m and driven out onto the gravel to 215 m (dry), parked
    # and hidden; then the test wetness held at 1 (tick), the camera 1.9 m up looking down about 50 degrees at the strongest carried
    # mud past the apron (200-206 m, within 1.5 m of the line), a picture and a dump; then the wetness back to 0.
    global phase,last
    m=report['mrp']
    if phase=='mrp_wet':
        car.set_actor_hidden_in_game(False);place_car(18300.,0.);phase='mrp_wet_settle';last=now
    elif phase=='mrp_wet_settle' and settled(now,last):
        car.reset_driving_inputs();move.set_handbrake_input(False);move.set_target_gear(1,True);run['wet_from']=now;phase='mrp_wet_drive';last=now
    elif phase=='mrp_wet_drive':
        pos,speed=steer_to(car.get_actor_location().x+650.,0.,1.,6.)
        if pos.x>=21500. or gsince()>FAST_CAP_S:
            park();m['wet_drive']=dict(end_m=round(pos.x/100.,2),s=round(gsince(),1),loads=loads());phase='mrp_wet_spot';last=now
    elif phase=='mrp_wet_spot' and now-last>3.:
        car.set_actor_hidden_in_game(True)
        best=(-1.,20200.,0.)
        for i in range(25):
            for j in range(13):
                x,y=20000.+25.*i,-150.+25.*j;g=paint.sample_coverage(u.Vector(x,y,0.))
                if g>best[0]:best=(g,x,y)
        g,vx,vy=best;m['wet_spot']=dict(x_m=round(vx/100.,2),y_m=round(vy/100.,2),coverage=round(g,3),wetness_b=round(paint.sample_wetness(u.Vector(vx,vy,0.)),3))
        m['wet_mirror']=[carry_mirror('spot')]   # GR1c checks follow-up: as the scene stands (rendered or not)
        run['wet_hold']=True
        run['wet_view']=(u.Vector(vx-150.,vy+40.,ground(vx-150.,vy+40.)+190.),u.Vector(vx+20.,vy,ground(vx+20.,vy)),50.)
        phase='mrp_wet_look';last=now
    elif phase=='mrp_wet_look' and now-last>3.:
        m['wet']=dict(wetness=round(weather.get_wetness(),3) if hasattr(weather,'get_wetness') else 1.0)
        cpos,ctarget,fov=run['wet_view'];mrp_look('Carry_Wet_PBR',cpos,ctarget,fov,now);m.setdefault('pictures',[]).append(dict(name='Carry_Wet_PBR',pom=2,pbr=1,shadow=1,wetness=1))
        phase='mrp_wet_dump';last=now
    elif phase=='mrp_wet_dump' and now-last>3.5 and (mrp_written('Carry_Wet_PBR') or now-last>30.):
        console('r.PostProcessingColorFormat 1')
        cpos,ctarget,fov=run['wet_view'];shoot_dump('PBR_CarryWet',cpos,ctarget,fov,now,'carry',wetness=1.0);phase='mrp_wet_done';last=now
    elif phase=='mrp_wet_done' and now-last>3.5 and (mrp_written('PBR_CarryWet',True) or now-last>30.):
        m.setdefault('wet_mirror',[]).append(carry_mirror('after_dump'))
        console('r.PostProcessingColorFormat 0');run['wet_hold']=False;phase='mr2_done';last=now
def pos_x(a):
    return a.get_actor_location().x
def tick(dt):
    global phase,last,world,car,move,pc,camera,mud,weather,sample_at,pending_shot,run,paint,splats,spray,FAST,FRAME,SHOT_HOLD,GPHASE,GPH0
    wall=time.monotonic()
    advance_sim()
    # Checks under a running game: in play every wait and timer of the phases counts game seconds (a fixed 1/60 s a frame), so the
    # game's state between two steps (drying, settling, the car at rest) is the same whatever the frame rate; loading and the start of
    # play count the wall clock. A `last` set on the other clock is re-based at the switch.
    now=gt() if (world is not None and phase not in ('load','loaded','warm','restart','finished')) else wall
    if (now<wall and last>now+1000.) or (now==wall and last<1000.):last=now
    if phase!=GPHASE:GPHASE=phase;GPH0=gt()   # game time at the phase's start (gsince)
    try:
        GATE.tick(world)
        if PACE and GATE.on:gpu_pace()
        if phase not in ('load','loaded','warm','finished','restart'):
            weather.set_wetness_for_test(1. if run and run.get('wet_hold') else 0.)   # MRP follow-up: 1 for Carry_Wet_PBR
        if PARKED and car is not None and car.get_velocity().length()<50.:move.set_brake_input(0.)   # MR2b: never reverse when parked
        FRAME+=1
        if pending_shot and world is not None:GATE.set(world,pc,True)   # the picture's render window opens with its request
        if pending_shot and now>=pending_shot[0] and FRAME>=pending_shot[2] and GATE.ready(world,pc):
            path=pending_shot[1];dump=len(pending_shot)>3 and pending_shot[3];pending_shot=None;SHOT_HOLD=FRAME+3
            # MRP: a buffer dump's arguments (no region, no mask, the buffers, HDR) before the filename.
            console('HighResShot %dx%d%s filename="%s"'%(VIEW[0],VIEW[1],' 0 0 0 0 0 1 1' if dump else '',path.as_posix()));GATE.expect(path)
        if world is not None:GATE.idle(world,pc,keep=pending_shot is not None)
        if wall-start>WALL_CAP_S:finish('Mud variants check hit its %.0f min wall-clock cap'%(WALL_CAP_S/60.));return
        if pending_shot or FRAME<SHOT_HOLD:return
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
            patches=u.GameplayStatics.get_all_actors_of_class(world,u.GTMudPatch);assert len(patches)==4,len(patches)
            for name,x0,x1 in SECTIONS:
                p=patch_for(x0,x1);assert p,'no patch over '+name
                mid=p.mesh_material;cmi=p.clod_material_instance
                row=dict(variant=name,section=p.section_index,slot=p.hole_slot,mud_variant=str(p.mud_variant),bounds_min=[p.bounds_min.x,p.bounds_min.y],bounds_max=[p.bounds_max.x,p.bounds_max.y],
                    cells=[p.cells_x,p.cells_y],has_profile=bool(p.get_editor_property('bHasProfile')),max_sinkage_scale=p.max_sinkage_scale,sinkage_rate_scale=p.sinkage_rate_scale,friction_scale=p.friction_scale,
                    recover_share=p.recover_share,lump_share=p.lump_share,throw_max=p.throw_max,water_table_cm=p.water_table_cm,material=p.get_editor_property('bMaterialLoaded'),
                    mesh_material_parent=mid.get_base_material().get_path_name() if mid else None,mesh_mud_variant=mid.get_scalar_parameter_value('MudVariant') if mid else None,
                    clod_meshes=p.clod_mesh_count,clod_instance=bool(cmi),clod_mud_variant=cmi.get_scalar_parameter_value('MudVariant') if cmi else None)
                row['mesh_slice_ok']=row['mesh_mud_variant'] is not None and abs(row['mesh_mud_variant']-VARIANT_INDEX[name])<.01
                row['clod_slice_ok']=(cmi is None and name=='Standard') or (cmi is not None and abs(row['clod_mud_variant']-VARIANT_INDEX[name])<.01)
                report['patches'].append(row)
            boxes=sorted((p['bounds_min'][0],p['bounds_max'][0]) for p in report['patches'])
            report['box_gaps_cm']=[round(boxes[i+1][0]-boxes[i][1],1) for i in range(3)]
            camera=next(a for a in u.GameplayStatics.get_all_actors_of_class(world,u.CameraActor) if a.get_actor_label()=='Live_Overview')
            run=dict(cross={},stop_since=None,stop_max=0.,stop_at=None)
            # MR4: the CPU maps and the before-driving pictures first (soft_before), then the drive as before.
            soft_setup()
            chunk_setup()   # MR5
            place_car(START_X,0.);phase='soft_before';last=now
        elif phase=='soft_before' and now-last>3:
            if soft_queue:
                name,cpos,ctarget,fov=soft_queue.pop(0);shoot(name,cpos,ctarget,fov,now)
                (report['chunks'] if name.startswith('Chunks_') else report['soft'])['cameras'][name]=report['cameras'][name];last=now;return
            place_car(START_X,0.);phase='settle';last=now
        elif phase=='settle' and now-last>4:
            pc.set_view_target_with_blend(car,0.)
            car.reset_driving_inputs();move.set_handbrake_input(False);move.set_target_gear(1,True)
            run['start']=gt();run['wall0']=wall;run['frames0']=u.SystemLibrary.get_frame_count();run['lowered0']=mud.total_lowered_cm3();sample_at=-1.;phase='drive';GATE.start_dt()
            paint=subsystem(u.GTTrackPaintSubsystem);splats=subsystem(u.GTMudSplatSubsystem);spray=car.get_spray();run['counts0']=splat_counts()
        elif phase=='drive':
            pos,speed=drive_step(0.)
            for name,x0,x1 in SECTIONS:
                for mark in (x0,x1):
                    if mark not in run['cross'] and pos.x>=mark:run['cross'][mark]=gt()
            if gt()-sample_at>=.25:sample(gt(),pos,speed);sample_at=gt()
            stopped=pos.x>START_X+100. and speed<STOP_MPS
            if stopped:
                run['stop_since']=run['stop_since'] or gt()
                if gt()-run['stop_since']>run['stop_max']:run['stop_max']=gt()-run['stop_since'];run['stop_at']=round(pos.x/100.,2)
            else:run['stop_since']=None
            why=None
            if pos.x>=DONE_X:why='reached %.0f m'%(DONE_X/100.)
            elif run['stop_since'] is not None and gt()-run['stop_since']>=STALL_S:why='stalled at %.2f m'%(pos.x/100.)
            elif gt()-run['start']>=PASS_S:why='timed out at %.2f m'%(pos.x/100.)
            if why:
                move.set_throttle_input(0);move.set_brake_input(1);move.set_handbrake_input(True);car.set_raw_steer(0.)
                report['drive']=dict(ended=why,completed=bool(pos.x>=DONE_X),end_x_m=round(pos.x/100.,2),elapsed_s=round(gt()-run['start'],2),
                    time_base='simulated (physics) seconds',real_s=round(wall-run['wall0'],1),frames=u.SystemLibrary.get_frame_count()-run['frames0'],
                    fps=round((u.SystemLibrary.get_frame_count()-run['frames0'])/max(.001,wall-run['wall0']),2),game_per_real=round((gt()-run['start'])/max(.001,wall-run['wall0']),3),
                    max_lateral_m=round(max((abs(r['y_m']) for r in samples),default=0.),3),longest_stop_s=round(run['stop_max'],2),longest_stop_at_m=run['stop_at'],
                    lowered_cm3=round(mud.total_lowered_cm3()-run['lowered0'],0),dry=True,throttle='full, low range, diff lock')
                report['sections']=[section_summary(name,x0,x1) for name,x0,x1 in SECTIONS]
                soft_sections()   # MR4
                chunk_report('after_drive')   # MR5
                report['drive']['splats_per_second']=per_second(run['counts0'],splat_counts());report['drive']['body']=body_report()
                phase='stopped';last=now
        elif phase=='stopped' and now-last>3:
            if not report['drive']['completed']:
                # MR2: the drive did not get through (a game running, 2026-10-08): a scripted pass, 6 m into each section it missed.
                FAST=True;report['fast']=True
                report['teleport_pass']=[];run['tp']=[(n,x0,x1) for n,x0,x1 in SECTIONS if x1 not in run['cross']]
                phase='tp_place';last=now;return
            car.set_actor_hidden_in_game(True)
            report['ruts']={};queue_pictures();phase='shot_next';last=now
        elif phase=='tp_place':
            if not run['tp']:
                report['teleport_pass_done']=True;park();car.set_actor_hidden_in_game(True)
                report['ruts']={};queue_pictures();phase='shot_next';last=now;return
            name,x0,x1=run['tp'][0];place_car(x0-TP_LEAD,0.);run['tp_from']=now;phase='tp_settle';last=now
        elif phase=='tp_settle' and settled(now,last):
            car.reset_driving_inputs();move.set_handbrake_input(False);move.set_target_gear(1,True);phase='tp_drive';last=now
        elif phase=='tp_drive':
            name,x0,x1=run['tp'][0];pos,speed=drive_step(0.)
            if gt()-sample_at>=.25:sample(gt(),pos,speed);sample_at=gt()
            # The last section (Stony) is driven on without a stop: its exit is the carried tracks' start (MR1's exit leg).
            last_leg=len(run['tp'])==1 and name=='Stony'
            if pos.x>=x0+TP_INTO or gsince()>TP_MAX_S:
                report['teleport_pass'].append(dict(section=name,from_m=round((x0-TP_LEAD)/100.,1),end_m=round(pos.x/100.,2),s=round(gsince(),1),into=bool(pos.x>=x0+TP_INTO)))
                run['tp'].pop(0)
                if last_leg:
                    report['teleport_pass_done']=True
                    report['ruts']={};queue_pictures();run['rolling']=True;phase='shot_next';last=now;return
                park();phase='tp_place';last=now
        elif phase.startswith('mr1_') or phase.startswith('mr2_') or phase.startswith('mr3_'):
            mr1_tick(now)
        elif phase.startswith('mrp_wet'):
            mrp_wet_tick(now)
        elif phase.startswith('mrp_'):
            mrp_tick(now)
        elif phase=='shot_next' and run.get('rolling'):
            # FAST: the car is still rolling through Stony; the section pictures wait (the car would leave its mud) - MR1 first.
            run['rolling']=False;run['pictures_after_mr1']=list(shot_queue);shot_queue.clear()
            paint=subsystem(u.GTTrackPaintSubsystem);splats=subsystem(u.GTMudSplatSubsystem);spray=car.get_spray()
            phase='mr1_start';last=now;return
        elif phase=='shot_next' and now-last>3:
            if not shot_queue:
                # MR1: the carried mud's phase, then the report (its end judges every picture, these and MR1's).
                paint=subsystem(u.GTTrackPaintSubsystem);splats=subsystem(u.GTMudSplatSubsystem);spray=car.get_spray()
                phase='mr1_start';last=now;return
            name,cpos,ctarget,fov=shot_queue.pop(0)
            aim_camera(cpos,ctarget,fov)
            report.setdefault('cameras',{})[name]=dict(location=[round(cpos.x,1),round(cpos.y,1),round(cpos.z,1)],target=[round(ctarget.x,1),round(ctarget.y,1),round(ctarget.z,1)],fov=fov)
            path=OUT/(name+'.png');report['images'].append(str(path));pending_shot=(now+1.5,path,FRAME+SHOT_FRAMES);last=now
    except Exception:finish(traceback.format_exc())
handle=u.register_slate_post_tick_callback(tick)
