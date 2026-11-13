"""Road soil regression and stationary rendered fixtures; never drives the car."""
import unreal as u
from pathlib import Path
import json,time,math,re
ROOT=Path(u.Paths.project_dir()).resolve();OUT=ROOT/'Art/Export/ProceduralGround'
LEVEL='/Game/GrandTour/ArtTests/ProceduralGround/L_BigMountain_Authoring'

def configure(author,road,report):
    previous=OUT/'livingroads-functional.json'
    installed=previous.exists() and json.loads(previous.read_text()).get('preset_version')==1 and json.loads(previous.read_text()).get('ok')
    if not installed:
        conditions=list(road.conditions)
        for c,values in zip(conditions,[
            (2,3,.85,.2,0,0,0,0,1),
            (42,8,.35,.65,.8,45,.18,.12,4),
            (40,22,.2,.78,.12,165,.65,.65,9),
            (90,35,.05,.95,.08,120,.85,.35,12)]):
            for key,value in zip(['mud_depth_cm','rut_depth_cm','firmness','wetness','grass_cover','track_spread_cm','churn','crossing_tracks','breakup_cm'],values):
                c.set_editor_property(key,value)
        road.conditions=conditions
    report['preset_version']=1
    report['road_condition_controls']=[{k:c.get_editor_property(k) for k in ['name','mud_depth_cm','rut_depth_cm','firmness','wetness','track_spread_cm','churn','crossing_tracks','breakup_cm']} for c in road.conditions]

def nums(s):return {k:float(v) for k,v in re.findall(r'(\w+)=(-?\d+(?:\.\d+)?)',s)}

def review(report,save):
    push='-GTMudPush' in u.SystemLibrary.get_command_line()
    functional=json.loads((OUT/('mudpush-functional.json' if push else 'livingroads-functional.json')).read_text());assert functional['ok']
    les=u.get_editor_subsystem(u.LevelEditorSubsystem);actors=u.get_editor_subsystem(u.EditorActorSubsystem)
    assert les.load_level(LEVEL)
    editor_actors=actors.get_all_level_actors()
    road=next(a for a in editor_actors if isinstance(a,u.GTProceduralRoad) and a.get_actor_label().startswith('Road 01'))
    tiles=[a for a in editor_actors if isinstance(a,u.GTRoadReliefTile)]
    def bed(x,y):
        for t in tiles:
            o=t.get_actor_location();span=t.span_cm
            if o.x<=x<o.x+span and o.y<=y<o.y+span:return t.height_at(u.Vector2D(x,y))
        raise AssertionError(('outside road tiles',x,y))
    targets=[]
    for distance,name,minimum,maximum in [(2200,'firm',0,4),(7000,'grass',15,45),(11200,'churn',15,45),(15500,'deep',40,100)]:
        p=road.control_points.get_location_at_distance_along_spline(distance,u.SplineCoordinateSpace.WORLD)
        tangent=road.control_points.get_direction_at_distance_along_spline(distance,u.SplineCoordinateSpace.WORLD)
        candidates=[]
        for t in tiles:
            o=t.get_actor_location();soil=t.soil;n=round(math.sqrt(len(soil)))-1
            if abs(o.x+t.span_cm/2-p.x)>t.span_cm/2+1600 or abs(o.y+t.span_cm/2-p.y)>t.span_cm/2+1600:continue
            for y in range(4,n-3,4):
                for x in range(4,n-3,4):
                    c=soil[y*(n+1)+x]
                    if not minimum<=c.r<=maximum:continue
                    px=o.x+x*t.span_cm/n;py=o.y+y*t.span_cm/n
                    d=math.hypot(px-p.x,py-p.y)
                    if d>1500:continue
                    grade=math.hypot((bed(px+100,py)-bed(px-100,py))/200,(bed(px,py+100)-bed(px,py-100))/200)
                    candidates.append((d+grade*1800,px,py,bed(px,py),c.r,grade))
        assert candidates, name
        _,x,y,z,depth,grade=min(candidates)
        targets.append(dict(name=name,x=x,y=y,z=z,depth=depth,grade=grade,yaw=math.degrees(math.atan2(tangent.y,tangent.x))))
    report['targets']=targets;save()
    les.editor_set_viewport_realtime(False)
    if push:
        u.SystemLibrary.execute_console_command(u.get_editor_subsystem(u.UnrealEditorSubsystem).get_editor_world(),'r.ScreenPercentage 70')
        report['review_screen_percentage']=70
    assert u.GTPlayWindowLibrary.request_play_in_new_window(1440,900)
    until=time.monotonic()+180;world=None;car=None
    while car is None:
        yield .5;world=u.EditorLevelLibrary.get_game_world()
        if world:
            pc=u.GameplayStatics.get_player_controller(world,0);car=pc.get_car()
        assert time.monotonic()<until
    try:
        pc.possess(car);car.disable_input(pc);car.reset_driving_inputs()
        move=car.get_chaos_movement()
        report['original_reverse_as_brake']=move.get_editor_property('reverse_as_brake')
        move.set_editor_property('reverse_as_brake',False)
        move.set_use_automatic_gears(False);move.set_target_gear(0,True)
        # GrandTour's custom drivetrain maps held foot brake to reverse even
        # with Chaos reverse-as-brake disabled. Handbrake alone holds this fixture.
        move.set_throttle_input(0);move.set_brake_input(0);move.set_handbrake_input(True)
        mesh=car.get_component_by_class(u.SkeletalMeshComponent)
        surface=u.GameplayStatics.get_all_actors_of_class(world,u.GTLandscapeSurface)[0]
        report['surface_flags']={k:surface.get_editor_property(k) for k in ['use_native_substance_response','use_native_mud_shader_updates','enable_wheel_support','grass_is_visual_cover','observe_player_wheels']}
        assert all(report['surface_flags'].values()),report['surface_flags']
        camera=u.GTVehicleSetupLibrary.spawn_actor_of_class(world,u.CameraActor,u.Transform(),'LivingRoadStationaryCamera')
        camera.camera_component.set_field_of_view(64);camera.camera_component.set_constraint_aspect_ratio(False)
        for cmd in ['DisableAllScreenMessages','r.MotionBlurQuality 0','t.MaxFPS 60','t.IdleWhenNotForeground 0','Slate.bAllowThrottling 0','showhud']:
            u.SystemLibrary.execute_console_command(world,cmd,pc)
        def aim(p):
            target=u.Vector(p['x'],p['y'],p['z']);eye=target+(u.Vector(600,-300,500) if p.get('name') in ['deep','probe'] else u.Vector(-450,-650,650))
            eye.z=max(eye.z,bed(eye.x,eye.y)+200)
            camera.set_actor_location_and_rotation(eye,u.MathLibrary.find_look_at_rotation(eye,target),False,True)
            pc.set_view_target_with_blend(camera,0)
        def capture(name):
            path=OUT/(('MudPush_' if push else 'LivingRoads_')+name+'.png');stamp=time.time()
            u.GameplayStatics.set_game_paused(world,True);yield .3
            u.SystemLibrary.execute_console_command(world,'HighResShot 1440x900 filename="'+path.as_posix()+'"',pc)
            until=time.monotonic()+45
            while not path.exists() or path.stat().st_mtime<stamp:assert time.monotonic()<until;yield .3
            u.GameplayStatics.set_game_paused(world,False)
            report.setdefault('images',[]).append(str(path));save()
        def settle(seconds):
            # Wall-clock waits can be mostly GPU stalls rather than physics time.
            # Do not sample an airborne car or half-uploaded terrain as settled.
            until=u.GameplayStatics.get_time_seconds(world)+seconds;timeout=time.monotonic()+240
            while u.GameplayStatics.get_time_seconds(world)<until or not nums(surface.get_surface_report()).get('textures_ready',0):
                assert time.monotonic()<timeout,'Simulation/terrain uploads did not settle'
                yield .2
        if push:
            # Isolate field deformation from vehicle integration under GPU contention.
            # This is explicitly a controlled stamp fixture, not a driving/contact test.
            p=targets[-1];mesh.set_simulate_physics(False)
            surface.set_editor_property('observe_player_wheels',False)
            car.set_actor_location_and_rotation(u.Vector(p['x'],p['y'],p['z']+45),u.Rotator(yaw=p['yaw']),False,True)
            report['vehicle_physics_frozen_for_field_fixture']=True
            yield 1
            yield from settle(0)
        report['cases']=[]
        for p in ([] if push else targets):
            car.set_actor_location_and_rotation(u.Vector(p['x'],p['y'],p['z']+110),u.Rotator(yaw=p['yaw']),False,True)
            mesh.set_physics_linear_velocity(u.Vector());mesh.set_physics_angular_velocity_in_degrees(u.Vector())
            car.reset_driving_inputs();move.set_brake_input(0);move.set_handbrake_input(True)
            aim(p);yield from settle(10);aim(p);yield 2
            case=dict(name=p['name'],native=nums(move.native_substance_report()),soil=nums(surface.get_surface_report()),samples=[])
            for _ in range(12):
                wheels=[]
                for i,w in enumerate(car.get_traction().wheels):
                    s=surface.sample_surface(u.Vector2D(w.contact_point.x,w.contact_point.y))
                    ws=u.ChaosWheeledVehicleMovementComponent.break_wheel_status(move.get_wheel_state(i))
                    wheels.append(dict(contact=w.get_editor_property('bInContact'),tread_cm_s=w.tread_cm_per_s,spring_force=ws[4],drive_torque=ws[11],brake_torque=ws[12],depth=s.sinkage_cap_cm,compression=s.compression_cm,q=s.native_extrude_cm,softness=s.softness,delta=s.surface_delta_cm))
                drive=car.get_drivetrain().get_drive_input();assert abs(drive)<.0001,drive
                case['samples'].append(dict(native=nums(move.native_substance_report()),wheels=wheels,position=list(car.get_actor_location().to_tuple()),velocity=list(car.get_velocity().to_tuple()),gear=move.get_current_gear(),throttle=move.get_throttle_input(),drive_input=drive))
                yield .2
            report['cases'].append(case);save()
            assert max(s['native']['soil_contacts'] for s in case['samples'])>=3,case
            assert max(s['native']['soil_hits'] for s in case['samples'])>=3,case
            if p['name']!='firm':assert max(s['native']['native_mud_contacts'] for s in case['samples'])>=3,case
            assert max(abs(w['tread_cm_s']) for s in case['samples'] for w in s['wheels'])<20,('unexpected parked wheelspin',case)
            yield from capture(p['name'])
        # A controlled deformation fixture beside the stationary car. It exercises
        # the native CPU extrusion and GPU-equation update, not a driven route.
        p=targets[-1];q=u.Vector2D(p['x']+250,p['y']);start=q-u.Vector2D(100,0);end=q+u.Vector2D(100,0)
        before=surface.sample_surface(q);before_stats=nums(surface.get_surface_report())
        if push:
            yield from push_review(surface,world,pc,q,p,aim,capture,report,save)
        for _ in range(0 if push else 24):
            surface.apply_review_native_contact(q,.8)
            surface.apply_review_soil_stroke(start,end,35,min(30,before.sinkage_cap_cm),.7)
            yield .05
        yield 2
        after=surface.sample_surface(q);after_stats=nums(surface.get_surface_report())
        report['controlled_deformation']=dict(before_q=before.native_extrude_cm,after_q=after.native_extrude_cm,before_height=before.surface_delta_cm,after_height=after.surface_delta_cm,native_cells_added=after_stats['native_cells']-before_stats['native_cells'])
        assert after.native_extrude_cm>before.native_extrude_cm and after.surface_delta_cm<before.surface_delta_cm-.5,report['controlled_deformation']
        assert after_stats['native_cells']>before_stats['native_cells']
        aim(dict(name='probe',x=q.x,y=q.y,z=p['z']));yield 2;yield from capture('deformation_probe')
        report.update(ok=True,stationary_soil_contacts_verified=not push,driving_tested=False,captures_complete=True);save()
        camera.destroy_actor()
    finally:
        u.GameplayStatics.set_game_paused(world,False);u.EditorLevelLibrary.editor_end_play();yield 3
    world=pc=car=move=mesh=surface=camera=None
    until=time.monotonic()+60
    while u.EditorLevelLibrary.get_game_world():assert time.monotonic()<until;yield .5
    les.load_level('/Engine/Maps/Entry');yield 3

def push_review(surface,world,pc,q,p,aim,capture,report,save):
    """Same-camera cut/raise measurements and crossing strokes, not vehicle driving."""
    surface.set_editor_property('observe_player_wheels',False)
    points=[q+u.Vector2D(x*12.5,y*12.5) for y in range(-22,23) for x in range(-24,25)]
    def heights():return [surface.sample_surface(v).surface_delta_cm for v in points]
    initial=heights();stats0=nums(surface.get_surface_report())
    aim(dict(name='probe',x=q.x,y=q.y,z=p['z']));yield 2
    yield from capture('before_contacts')
    # Two wheel lines with unequal depths, then an offset overlapping pass.
    # The first line crosses q so the physical extrusion probe has the same location.
    for i in range(28):
        for offset,depth in [(0,32),(155,18)]:
            a=q+u.Vector2D(-180,offset);b=q+u.Vector2D(180,offset)
            surface.apply_review_soil_stroke(a,b,35,depth,.7)
        surface.apply_review_native_contact(q,.8)
        yield .06
    yield 2;first=heights();stats1=nums(surface.get_surface_report())
    delta=[b-a for a,b in zip(initial,first)]
    report['push_fixture']=dict(max_cut_cm=-min(delta),max_raise_cm=max(delta),
        raised_samples=sum(v>1 for v in delta),cut_samples=sum(v< -1 for v in delta),
        native_push_cells=stats1['push_cells']-stats0['push_cells'],
        cut_cm3=stats1['excavated_cm3']-stats0['excavated_cm3'],
        deposited_cm3=stats1['deposited_cm3']-stats0['deposited_cm3'])
    save()
    assert min(delta)< -10 and max(delta)>2,report['push_fixture']
    assert report['push_fixture']['native_push_cells']>0 and report['push_fixture']['deposited_cm3']>0
    yield from capture('after_contacts')
    for i in range(20):
        surface.apply_review_soil_stroke(q+u.Vector2D(-100,-120),q+u.Vector2D(110,220),35,25,.3)
        yield .06
    yield 2;cross=heights()
    report['push_fixture']['crossing_changed_samples']=sum(abs(b-a)>1 for a,b in zip(first,cross))
    assert report['push_fixture']['crossing_changed_samples']>15
    yield from capture('crossing_contacts')
    # Record water validity only. Domain road pools have prebuilt basin geometry;
    # finite samples do not prove new-rut flooding or free shoreline expansion.
    sheets=u.GameplayStatics.get_all_actors_of_class(world,u.GTWaterSheet)
    report['push_fixture']['water_samples']=[]
    for sheet in sheets:
        col=sheet.review_water_column(q)
        values=[col.r,col.g,col.b,col.a]
        assert all(math.isfinite(v) for v in values)
        report['push_fixture']['water_samples'].append(values)
    save()
