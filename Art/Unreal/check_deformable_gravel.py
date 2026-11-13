"""Real Chaos-car passes, repeat compaction, fresh shoulder lane, field and material checks.
Deformable gravel DG1 item 6 (docs/DEFORMABLE_GRAVEL_PLAN.md): after the study's three passes and its four pictures (Before, FirstPass,
RepeatedPass, ShoulderPass) and ten checks, the DG1 set on the Loose section (M_GT_Gravel, the loose stones):
- Gravel_Close: on foot, the eye 1.7 m up, 3 m from the first pass's -Y rut's outer edge, 90 deg; Gravel_Close_POM0 the same with
  gt.Gravel.POM 0; Gravel_Wet the same at the weather's wetness 1;
- Gravel_Low: 0.5 m above the ground, looking 9 m along that rut;
- the pale edge line's diagnosis: the study's RepeatedPass view again with MPC_TrackPaint GravelDebug 1 (the flat vertex normal, no
  field slope, for the parallax's frame and the lighting), 2 (no texture slide with the field), 3 (no baked detail normal)
  and 4 (the lighting's normal flat, the parallax's frame the field's) (gt.Gravel.Debug): Gravel_RepeatedPass_Debug1..4; and
  Gravel_RepeatedPass_POM0 (gt.Gravel.POM 0); the Close view with Debug 1-3 (DG1b: the windrow walls' streaks): Gravel_Close_Debug1..3;
- the PBR captures: HighResShot buffer dumps (BaseColor, Roughness, MaterialAO; uncompressed EXR, linear) of the Loose ground and its
  ruts from 2.2 m, dry and at wetness 1 (PBR_Gravel_Dry / PBR_Gravel_Wet), and (DG1b) the same view with the field, the landscape and
  the grass hidden, the loose stones alone (PBR_Gravel_Stones); python Art/sample_gravel_pbr.py reads them;
- the stones (AGTMudPatch::DescribeGravelStones) before and after the passes.
A per-tick GPU wait (docs/VRAM_SOAK.md; GT_CHECK_PACE=0 off): -RenderOffScreen has no swap chain.
Checks under a running game (docs/CHECKS_UNDER_GAME_PLAN.md, Art/Unreal/check_render.py): the editor steps a fixed 1/60 s
(-UseFixedTimeStep -FPS=60, verified over 300 frames of the first pass), the scene is rendered only for the pictures (30 frames
of warm-up before each, until its file lands; the dg1 views throughout), and the GPU wait runs only then.
"""
import unreal as u,json,time,math,traceback,os,sys
from pathlib import Path
ROOT=Path(u.Paths.project_dir()).resolve();OUT=ROOT/'Art/Export/DeformableGravel'
sys.path.insert(0,str(ROOT/'Art/Unreal'))
from check_render import Gate
GATE=Gate();SHOTQ=[]
DEST='/Game/GrandTour/ArtTests/DeformableGravel';VIEW=(1440,900)
report={'ok':False,'passes':[],'images':[]};phase='load';last=time.monotonic();start=last;run=0;records=[]
# Checks: game-time limits (2026-10-10, the owner: a running game holds the editor to a fraction of real time): the pass cap (100 s)
# and the sampling are in SIMULATED seconds (gt(): the physics clock, see advance_sim); WALL_CAP_S (40 min) is the only wall-clock limit.
world=None;pc=None;WALL_CAP_S=2400.;PASS_CAP_S=100.
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
dg1={'queue':[],'current':None,'wet':0.,'shot_t':0.}
u.EditorPythonScripting.set_keep_python_script_alive(True)
PACE=os.environ.get('GT_CHECK_PACE','1').strip()!='0';pace_rt=None
def gpu_pace():
    global pace_rt
    gw=u.EditorLevelLibrary.get_game_world()
    if gw is None:return
    try:gone=pace_rt is None or pace_rt.get_outer() is None
    except Exception:gone=True
    if gone:pace_rt=u.RenderingLibrary.create_render_target2d(gw,1,1,u.TextureRenderTargetFormat.RTF_RGBA8)
    u.RenderingLibrary.read_render_target_pixel(gw,pace_rt,0,0)
def finish(error=None):
    global phase
    phase='finished'
    if error:report['error']=error
    report['samples']=records
    try:report['check_run']=GATE.report()
    except Exception:report['check_run_error']=traceback.format_exc().splitlines()[-1]
    (OUT/'drive-report.json').write_text(json.dumps(report,indent=2))
    u.unregister_slate_post_tick_callback(handle);u.EditorLevelLibrary.editor_end_play();u.SystemLibrary.quit_editor()
def console(cmd):u.SystemLibrary.execute_console_command(world,cmd,pc)
def reset_car(x=500.,y=0.):
    z=u.GTVehicleSetupLibrary.sample_terrain_height_cm(spec,x,y)
    car.reset_driving_inputs();move.set_handbrake_input(True)
    car.set_actor_location_and_rotation(u.Vector(x,y,z+150),u.Rotator(),False,True)
    body=car.get_component_by_class(u.SkeletalMeshComponent)
    body.set_physics_linear_velocity(u.Vector());body.set_physics_angular_velocity_in_degrees(u.Vector())
def measure():
    result={}
    for name,x0,x1 in [('firm',3600,4800),('loose',8900,10300)]:
        vals=list(mud.mud_cell_heights_cm(u.Vector2D(x0,-380),u.Vector2D(x1,380)))
        result[name]={'min_cm':min(vals),'max_cm':max(vals),'lowered_cell_sum_cm':sum(-v for v in vals if v<0),'cut_cells':sum(v<-.10 for v in vals)}
    return result
def shot(name):
    # Queued: tick fires it once the scene has rendered for the gate's warm-up, and the phases wait until its file lands.
    path=OUT/(name+'.png');report['images'].append(str(path));SHOTQ.append(path)
def view():
    z=u.GTVehicleSetupLibrary.sample_terrain_height_cm(spec,9500,0)
    pos=u.Vector(8840,-265,z+75);target=u.Vector(9720,0,z-2)
    aim(pos,target,62.)
def aim(pos,target,fov):
    camera.set_actor_location(pos,False,False);camera.set_actor_rotation(u.MathLibrary.find_look_at_rotation(pos,target),False)
    camera.camera_component.set_field_of_view(fov);pc.set_view_target_with_blend(camera,0.)
def terrain(x,y):return u.GTVehicleSetupLibrary.sample_terrain_height_cm(spec,x,y)
def stones():return [p.describe_gravel_stones() for p in sorted(u.GameplayStatics.get_all_actors_of_class(world,u.GTMudPatch),key=lambda p:p.section_index)]
def rut_profile(x):
    # The first pass's ruts across the Loose section at x: each 12.5 cm cell's lowest height in a 50 cm band along x.
    rows=[]
    for k in range(-24,24):
        y=6.25+k*12.5   # the cells' centres
        vals=list(mud.mud_cell_heights_cm(u.Vector2D(x-31.,y-5.),u.Vector2D(x+31.,y+5.)))
        rows.append((y,min(vals) if vals else 0.))
    return rows
def dg1_plan():
    # The views from the field as the passes left it: the -Y rut's centre (the lowest cell on that side) and its outer edge (where
    # the cut comes back above -0.5 cm going outward).
    x=9500.;prof=rut_profile(x);neg=[r for r in prof if r[0]<0]
    yc,zc=min(neg,key=lambda r:r[1])
    ye=yc
    for y,h in sorted(neg,key=lambda r:-r[0]):
        if y<=yc and h>-.5:ye=y;break
    report['dg1_ruts']=dict(x_cm=x,profile=[[round(y,1),round(h,2)] for y,h in prof],minus_y_rut_centre_cm=yc,minus_y_rut_depth_cm=round(zc,2),minus_y_rut_outer_edge_cm=ye)
    gz=terrain(x,ye)
    edge=u.Vector(x,ye,gz)
    a=math.radians(30.)
    close=(u.Vector(x-300.*math.cos(a),ye-300.*math.sin(a),terrain(x-300.*math.cos(a),ye-300.*math.sin(a))+170.),edge,90.)
    low=(u.Vector(x-500.,yc,terrain(x-500.,yc)+50.),u.Vector(x+400.,yc,terrain(x+400.,yc)),70.)
    rz=terrain(x+100.,yc)
    ground=(u.Vector(x-50.,yc-40.,rz+220.),u.Vector(x+120.,yc,rz),50.)
    z=terrain(9500,0);rep=(u.Vector(8840,-265,z+75),u.Vector(9720,0,z-2),62.)
    q=[('Gravel_Close',close,dict(pom=2)),('Gravel_Close_POM0',close,dict(pom=0)),('Gravel_Low',low,dict(pom=2)),('Gravel_Wet',close,dict(pom=2,wet=1.)),
       ('Gravel_RepeatedPass_Debug1',rep,dict(debug=1.)),('Gravel_RepeatedPass_Debug2',rep,dict(debug=2.)),('Gravel_RepeatedPass_Debug3',rep,dict(debug=3.)),('Gravel_RepeatedPass_Debug4',rep,dict(debug=4.)),('Gravel_RepeatedPass_Debug5',rep,dict(debug=5.)),('Gravel_RepeatedPass_Debug6',rep,dict(debug=6.)),('Gravel_RepeatedPass_POM0',rep,dict(pom=0)),('Gravel_Close_Debug1',close,dict(debug=1.)),('Gravel_Close_Debug2',close,dict(debug=2.)),('Gravel_Close_Debug3',close,dict(debug=3.)),
       ('PBR_Gravel_Dry',ground,dict(pom=2,dump=True)),('PBR_Gravel_Wet',ground,dict(pom=2,wet=1.,dump=True)),
       ('PBR_Gravel_Stones',ground,dict(pom=2,dump=True,hide=True))]
    report['dg1_views']={n:dict(location=[round(v[0].x,1),round(v[0].y,1),round(v[0].z,1)],target=[round(v[1].x,1),round(v[1].y,1),round(v[1].z,1)],fov=v[2],settings=s) for n,v,s in q}
    return q
def dg1_tick(now):
    global phase,last
    if phase=='dg1_next' and now-last>4. and (dg1['current'] is None or written(dg1['current']) or now-last>30.):
        if not dg1['queue']:
            console('gt.Gravel.POM 2');console('r.PostProcessingColorFormat 0');dg1['wet']=0.
            console('gt.Gravel.Debug 0')
            report['stones_after']=stones();finish(None if report['ok'] else 'One or more driving checks failed');return
        name,(pos,target,fov),s=dg1['queue'].pop(0)
        console('gt.Gravel.POM %d'%s.get('pom',2));dg1['wet']=s.get('wet',0.)
        console('gt.Gravel.Debug %d'%int(s.get('debug',0)))
        if s.get('dump'):
            console('r.BufferVisualizationOverviewTargets BaseColor,Roughness,MaterialAO');console('r.SaveEXR.CompressionQuality 0');console('r.PostProcessingColorFormat 1')
        else:
            console('r.PostProcessingColorFormat 0')
        if s.get('hide'):
            # DG1b: the stones alone in the buffers - the gravel field, the landscape and the grass hidden (the last view).
            for p in u.GameplayStatics.get_all_actors_of_class(world,u.GTMudPatch):p.set_surface_visible_for_test(False)
            for a in u.GameplayStatics.get_all_actors_of_class(world,u.LandscapeProxy):a.set_actor_hidden_in_game(True)
            for a in u.GameplayStatics.get_all_actors_of_class(world,u.Actor):
                if a.get_actor_label()=='TS_ApprovedTussock':a.set_actor_hidden_in_game(True)
        aim(pos,target,fov);dg1['current']=(name,bool(s.get('dump')));dg1['pending']=now+3.5;dg1['shot_t']=time.time();phase='dg1_shoot';last=now
    elif phase=='dg1_shoot' and now>=dg1['pending'] and GATE.ready(world,pc):
        name,dump=dg1['current'];path=OUT/(name+'.png');report['images'].append(str(path))
        if dump:report.setdefault('dumps',[]).append(dict(name=name,base=str((OUT/name).as_posix()),wetness=dg1['wet'],camera=report['dg1_views'][name]))
        console('HighResShot %dx%d%s filename="%s"'%(VIEW[0],VIEW[1],' 0 0 0 0 0 1 1' if dump else '',path.as_posix()))
        GATE.expect(OUT/name);phase='dg1_next';last=now
def written(cur):
    name,dump=cur
    f=OUT/((name+'_MaterialAO.exr') if dump else (name+'.png'))
    return f.exists() and f.stat().st_mtime>=dg1['shot_t']
def tick(dt):
    global phase,last,world,pc,car,move,mud,weather,spec,camera,run,pass_start,volume0,sample_at,run_wall0,run_frames0
    now=time.monotonic()
    advance_sim()
    try:
        GATE.tick(world)
        GATE.idle(world,pc if world is not None else None,keep=bool(SHOTQ) or phase.startswith('dg1'))
        if PACE and GATE.on:gpu_pace()
        if SHOTQ:
            # A queued picture: the scene on for the warm-up, then the capture; nothing else moves meanwhile.
            if GATE.ready(world,pc):
                path=SHOTQ.pop(0);console('HighResShot %dx%d filename="%s"'%(VIEW[0],VIEW[1],path.as_posix()));GATE.expect(path)
            return
        if GATE.capturing():return
        if now-start>WALL_CAP_S:raise RuntimeError('Gravel driving check hit its %.0f min wall-clock cap'%(WALL_CAP_S/60.))
        if phase.startswith('dg1'):
            weather.set_wetness_for_test(dg1['wet']);dg1_tick(now);return
        if phase=='load':
            phase='loading'
            assert u.get_editor_subsystem(u.LevelEditorSubsystem).load_level(DEST+'/L_GravelDeform')
            phase='loaded';last=now
        elif phase=='loaded' and now-last>8:
            phase='starting'
            assert u.GTPlayWindowLibrary.request_play_in_new_window(*VIEW)
            phase='warm';last=now
        elif phase=='warm' and now-last>16:
            world=u.EditorLevelLibrary.get_game_world()
            if world is None:return
            pc=u.GameplayStatics.get_player_controller(world,0)
            car=u.GameplayStatics.get_all_actors_of_class(world,u.GTCarPawn)[0];move=car.get_chaos_movement()
            pc.possess(car);car.disable_input(pc);car.get_drivetrain().set_low_range(True);car.get_drivetrain().set_diff_lock(True)
            mud=next(o for o in u.ObjectIterator(u.GTMudSubsystem) if o.get_outer()==world)
            weather=next(o for o in u.ObjectIterator(u.GTWeatherSubsystem) if o.get_outer()==world)
            spec=u.load_asset(DEST+'/DA_GravelDeform').spec
            patches=u.GameplayStatics.get_all_actors_of_class(world,u.GTMudPatch);assert len(patches)==2,len(patches)
            report['patches']=[dict(section=p.section_index,material=p.material_path,material_loaded=bool(p.get_editor_property('bMaterialLoaded')),has_profile=bool(p.get_editor_property('bHasProfile')),cap_cm=p.profile_max_sinkage_m*100,rate_cm_s=p.profile_sinkage_rate*100,cell_cm=p.mesh_cell_cm,vertices=p.mesh_vertex_count,bounds_min=[p.bounds_min.x,p.bounds_min.y],bounds_max=[p.bounds_max.x,p.bounds_max.y],stones_per_m2=p.gravel_stones_per_m2) for p in patches]
            # DG1: M_GT_Gravel on the field (the study checked M_GravelField's name here).
            assert all(p['material_loaded'] and p['has_profile'] and 'M_GT_Gravel' in p['material'] for p in report['patches']),report['patches']
            report['stones_before']=stones()
            camera=next(a for a in u.GameplayStatics.get_all_actors_of_class(world,u.CameraActor) if a.get_actor_label()=='Gravel_Review')
            weather.set_wetness_for_test(0.);mud.reset_fields_for_test();reset_car();view();console('showhud')
            phase='before';last=now
        elif phase=='before' and now-last>5:
            report['before']=measure();shot('Gravel_Before');phase='hold';last=now
        elif phase=='hold' and now-last>4:
            car.reset_driving_inputs();move.set_handbrake_input(False);move.set_brake_input(0.);move.set_target_gear(1,True)
            pc.set_view_target_with_blend(car,0.);volume0=mud.total_lowered_cm3();pass_start=gt();run_wall0=now;run_frames0=u.SystemLibrary.get_frame_count();sample_at=-1.;phase='drive';GATE.start_dt()
        elif phase=='drive':
            weather.set_wetness_for_test(0.)
            pos=car.get_actor_location();speed=car.get_velocity().length()/100.;target_y=225. if run==2 else 0.
            target_yaw=math.degrees(math.atan2(target_y-pos.y,650.));error=(target_yaw-car.get_actor_rotation().yaw+180)%360-180
            car.set_raw_steer(max(-.65,min(.65,error/24)))
            move.set_throttle_input(max(.18,min(1.,.42+(3.2-speed)*.22)));move.set_brake_input(.25 if speed>4.5 else 0.)
            if gt()-sample_at>.20:
                wheels=car.get_traction().wheels
                # Match actual wheel contacts to the saved patch bounds; DiagMaxSink is C++ only.
                caps=[p['cap_cm'] for w in wheels if w.get_editor_property('bInContact') and w.get_editor_property('bInProfiledPatch') for p in report['patches'] if p['bounds_min'][0]<=w.contact_point.x<=p['bounds_max'][0] and p['bounds_min'][1]<=w.contact_point.y<=p['bounds_max'][1]]
                row=dict(run=run,x_m=pos.x/100,y_m=pos.y/100,speed_mps=speed,sink_cm=max(w.sinkage for w in wheels)*100,visible_sink_cm=max(w.visible_sinkage for w in wheels)*100,profile=bool(caps),field_read=max(w.rut_depth for w in wheels),water_m=max(w.water_depth_m for w in wheels),cap_cm=max(caps,default=0.))
                row['t_s']=round(gt()-pass_start,3);records.append(row);sample_at=gt();(OUT/'drive-progress.json').write_text(json.dumps(row))
            if pos.x>12500:
                move.set_throttle_input(0);move.set_brake_input(1);move.set_handbrake_input(True)
                rows=[r for r in records if r['run']==run]
                frames=u.SystemLibrary.get_frame_count()-run_frames0
                report['passes'].append(dict(run=run,label=['first','repeat','fresh_shoulder'][run],game_s=round(gt()-pass_start,2),real_s=round(now-run_wall0,1),frames=frames,fps=round(frames/max(.001,now-run_wall0),2),volume_added_cm3=mud.total_lowered_cm3()-volume0,fields=measure(),max_sink_cm=max(r['sink_cm'] for r in rows),max_lateral_error_m=max(abs(r['y_m']-target_y/100) for r in rows),profile_samples=sum(r['profile'] for r in rows),max_field_read=max(r['field_read'] for r in rows),max_water_m=max(r['water_m'] for r in rows),stones=stones()))
                view();phase='review';last=now
            elif gt()-pass_start>PASS_CAP_S:raise RuntimeError('Car stalled at %.1f m (%.0f game s)'%(pos.x/100,PASS_CAP_S))
        elif phase=='review' and now-last>6:
            shot(['Gravel_FirstPass','Gravel_RepeatedPass','Gravel_ShoulderPass'][run]);phase='aftershot';last=now
        elif phase=='aftershot' and now-last>4:
            if run<2:
                run+=1;reset_car(7600. if run==2 else 500.,225. if run==2 else 0.);phase='hold';last=now
            else:
                a,b,c=report['passes']
                checks={
                    'both_profiles_contacted':any(r['profile'] and r['cap_cm']<3 for r in records) and any(r['profile'] and r['cap_cm']>4 for r in records),
                    'firm_shallow_rut':-.0>a['fields']['firm']['min_cm']>-2.8,
                    'loose_deeper_rut':-1>a['fields']['loose']['min_cm']>-5.9,
                    # DG1b: re-based for Loose to under 6 cm (the study's 3 cm ridge cap + DG1's 2.5 cm heaps, by design); Firm keeps under 4.
                    'small_positive_ridges':0<a['fields']['loose']['max_cm']<6 and 0<a['fields']['firm']['max_cm']<4,
                    'second_pass_moves_less':0<=b['volume_added_cm3']<a['volume_added_cm3'],
                    'fresh_lane_moves_gravel':c['volume_added_cm3']>1000,
                    'wheels_read_retained_ruts':b['max_field_read']>.1,
                    'dry_no_water':max(p['max_water_m'] for p in report['passes'])<.001,
                    'tracks_remain':b['fields']['loose']['cut_cells']>=a['fields']['loose']['cut_cells']*.9,
                    'stays_drivable':all(p['max_lateral_error_m']<.7 for p in report['passes'])}
                report['checks']=checks;report['ok']=all(checks.values())
                # DG1: the car out of the pictures, then the queue.
                car.set_actor_hidden_in_game(True)
                dg1['queue']=dg1_plan();dg1['current']=None;phase='dg1_next';last=now
    except Exception:finish(traceback.format_exc())
handle=u.register_slate_post_tick_callback(tick)
