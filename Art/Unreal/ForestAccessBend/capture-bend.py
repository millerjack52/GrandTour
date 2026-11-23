"""Capture a real pickup drive of the forest-access bend in standalone UE."""
import json
import math
import os
import statistics
import time
import traceback
import sys
from pathlib import Path

import unreal as u

out = Path(os.environ["GT_BEND_DRIVE_OUTPUT"])
here = Path(os.environ["GT_BEND_DRIVE_SCRIPT"]).parent
out.mkdir(parents=True, exist_ok=True)
world = pc = None
samples = []
timed = False

def cmd(text):
    u.SystemLibrary.execute_console_command(world, text, pc)

def photo(name):
    image = out / (name + ".png")
    cmd('Shot filename="' + image.as_posix() + '" -nosuffix')
    deadline = time.monotonic() + 20
    while not any(f.stat().st_size >= 32 for f in out.glob(name+"*.png")):
        if time.monotonic() > deadline:
            raise RuntimeError("Screenshot missing: " + image.name)
        yield

def profile_dressing(components,csv_dir):
    """Bound the cost of the relief, fern bed and pine grove in the same inland view."""
    import shutil
    review=out/'dressing-cost'
    review.mkdir(exist_ok=True)
    try:
        for i,visible in enumerate((True,False,False,True,True,False)):
            for component in components:component.set_visibility(visible)
            for _ in range(32):yield
            before=set(csv_dir.glob('Profile*.csv*'))
            cmd('csvprofile start')
            for _ in range(96):yield
            cmd('csvprofile stop')
            limit=time.monotonic()+15
            while time.monotonic()<limit:
                matches=set(csv_dir.glob('Profile*.csv*'))-before
                if matches and max(p.stat().st_size for p in matches)>5000:break
                yield
            else:raise RuntimeError('Missing fixed-view floor timing trace')
            for _ in range(6):yield
            file=max(matches,key=lambda p:p.stat().st_mtime)
            state='visible' if visible else 'hidden'
            shutil.copyfile(file,review/(f'{i+1}-{state}'+''.join(file.suffixes)))
    finally:
        for component in components:component.set_visibility(True)

def sunset_study(actors,cam,car,roadside,ground):
    """Compare a low cross-light against saved daylight in the running game."""
    suns=[a for a in actors if isinstance(a,u.DirectionalLight) and a.light_component.visible]
    sun=next((a for a in suns if a.get_actor_label()=='Sun'),None) or max(suns,key=lambda a:a.light_component.intensity)
    light=sun.light_component
    rotation=sun.get_actor_rotation()
    intensity=light.intensity
    temperature=light.temperature
    kelvin=light.use_temperature
    poses=json.loads((here.parents[1]/'lidar_driving_baseline_poses.json').read_text())
    paddock=next(p for p in poses if p['name']=='paddock_mid')
    x,y=paddock['x'],paddock['y']
    vista=u.Vector(x,y,ground(x,y)+225)
    yaw=math.radians(paddock['yaw'])
    views=[('bend',roadside(40,.4,245),roadside(55,-3,83)),
           ('woods',roadside(51,0,180),roadside(56,11,125)),
           ('ridge',vista,vista+u.Vector(20000*math.cos(yaw),20000*math.sin(yaw),80))]
    def daylight():
        sun.set_actor_rotation(rotation,False)
        light.set_temperature(temperature);light.set_editor_property('use_temperature',kelvin)
        light.set_intensity(intensity)
    movement=car.get_chaos_movement()
    car.reset_driving_inputs()
    movement.set_throttle_input(0)
    movement.set_brake_input(1)
    movement.set_handbrake_input(True)
    try:
        for name,eye,look in views:
            if name=='ridge':
                pc.set_view_target_with_blend(car,0)
                # Keep the streaming source near the camera and the pickup behind it.
                px=x-1800*math.cos(yaw);py=y-1800*math.sin(yaw)
                cmd(f"BugItGo {px:.2f} {py:.2f} {ground(px,py)+145:.2f} 0 {paddock['yaw']:.3f} 0")
                movement.set_handbrake_input(True)
            cam.set_actor_location_and_rotation(eye,u.MathLibrary.find_look_at_rotation(eye,look),False,True)
            pc.set_view_target_with_blend(cam,0)
            for mode in ('daylight','low-sun'):
                if mode=='low-sun':
                    sun.set_actor_rotation(u.Rotator(pitch=-11,yaw=54),False)
                    light.set_editor_property('use_temperature',True)
                    light.set_temperature(4050.)
                    light.set_intensity(.67*intensity)
                    assert abs(sun.get_actor_rotation().pitch+11)<.1
                end=time.monotonic()+5
                while time.monotonic()<end:yield
                yield from photo('study-'+name+'-'+mode)
            daylight()
    finally:daylight()
    (out/'sunset-study.json').write_text(json.dumps(dict(
        original_pitch=rotation.pitch,original_yaw=rotation.yaw,original_intensity=intensity,
        original_temperature=temperature,study_pitch=-11,study_yaw=54,study_kelvin=4050,
        study_intensity=.67*intensity,restored_pitch=sun.get_actor_rotation().pitch,
        restored_intensity=light.intensity),indent=2))

def run():
    global world, pc, timed
    deadline = time.monotonic() + 90
    while time.monotonic() < deadline:
        package=os.environ.get("GT_BEND_DRIVE_MAP","/Game/GrandTour/ArtTests/LidarStudy/L_LidarStudy")
        world = u.find_object(None, package+".L_LidarStudy")
        if world:
            pc = u.GameplayStatics.get_player_controller(world, 0)
            if pc and pc.get_car():
                break
        yield
    car = pc.get_car()
    assert u.GameplayStatics.get_player_pawn(world, 0) == car
    sys.path.insert(0,str(here))
    from bend_layout import Road
    route=Road(json.loads((here/"drive-route.json").read_text()))
    # Runtime builds omit the road author. Trace the landscape and relief tiles;
    # skip all scenery so canopy and rocks cannot become camera ground heights.
    actors=u.GameplayStatics.get_all_actors_of_class(world,u.Actor)
    added=[a for a in actors if a.actor_has_tag("LidarStudy_ForestAccessBend_v1")]
    candidate=out.name.startswith("candidate-")
    if candidate != bool(added):
        raise RuntimeError("The running map does not match the requested comparison stage.")
    if candidate:
        stone=next(a for a in added if isinstance(a,u.StaticMeshActor) and a.static_mesh_component.get_material(0)
                   and a.static_mesh_component.get_material(0).get_name() in ("M_ForestAccessStone","M_ForestAccessBeddedStone","M_BendMossLedges"))
    study_crown = os.environ.get('GT_BEND_CROWN_STUDY') == '1'
    original_crown = os.environ.get('GT_BEND_ORIGINAL_CROWN') == '1'
    timing_only = os.environ.get('GT_BEND_TIMING_ONLY') == '1'
    if study_crown or original_crown:
        from capture_crown import BroadleafPair, examine
        pair = BroadleafPair(added, json.loads((out.parent.parent/'build.json').read_text())['broadleaf'])
        pair.select(not original_crown)
    ignored=[a for a in actors if not isinstance(a,(u.Landscape,u.GTRoadReliefTile))]
    def ground(x,y):
        hit=u.SystemLibrary.line_trace_single(world,u.Vector(x,y,25000),u.Vector(x,y,-5000),
            u.TraceTypeQuery.TRACE_TYPE_QUERY1,True,ignored,u.DrawDebugTrace.NONE,True)
        if not hit:raise ValueError(f"Ground missing at {x},{y}")
        return hit.to_tuple()[4].z
    def at(metres):
        x,y,_=route.at(metres)
        return u.Vector(x,y,0)
    def station(pos):
        return route.nearest(pos.x,pos.y)[1]
    start = at(22)
    heading = route.at(22)[2]
    cmd("EnableCheats")
    cmd(f"BugItGo {start.x:.2f} {start.y:.2f} {ground(start.x,start.y)+150:.2f} 0 {heading:.3f} 0")
    cmd("r.SetRes 1600x900w")
    cmd("r.GPUStatsEnabled 1")
    cmd("r.GPUCsvStatsEnabled 1")
    cmd("t.IdleWhenNotForeground 0")
    cmd("Slate.bAllowThrottling 0")
    car.set_chase_camera(True)
    cmd("DisableAllScreenMessages")
    car.disable_input(pc)
    car.reset_driving_inputs()
    movement = car.get_chaos_movement()
    movement.set_handbrake_input(True)
    if study_crown or original_crown or timing_only:
        cmd("gt.Lidar.AuditRenderPass warm")
    settle = time.monotonic() + 12
    while time.monotonic() < settle:
        yield
    if study_crown or original_crown or timing_only:
        cmd("gt.Lidar.AuditRenderPass warm")
        for _ in range(12):yield
    position = car.get_actor_location()
    assert math.hypot(position.x-start.x,position.y-start.y) < 450, "Pickup missed the bend approach"
    yield from photo("approach")
    car.get_drivetrain().set_low_range(True)
    car.get_drivetrain().set_diff_lock(True)
    movement.set_target_gear(1, True)
    movement.set_handbrake_input(False)
    movement.set_brake_input(0)
    csv_started = False
    csv_dir = Path(u.Paths.project_saved_dir()).resolve()/"Profiling/CSV"
    csv_dir.mkdir(parents=True,exist_ok=True)
    csv_before = set(csv_dir.glob("Profile*.csv*"))
    started = time.monotonic()
    path = []
    while time.monotonic()-started < 100:
        position = car.get_actor_location()
        along = station(position)
        path.append([along,*position.to_tuple(),car.get_actor_up_vector().z])
        if not csv_started and along >= 27:
            cmd("csvprofile start")
            csv_started = True
        if along >= 69:
            break
        target = at(along + 6)
        heading = math.degrees(math.atan2(target.y-position.y,target.x-position.x))
        error = (heading-car.get_actor_rotation().yaw+180)%360-180
        car.set_raw_steer(max(-1,min(1,error/33)))
        movement.set_sleeping(False)
        movement.set_throttle_input(.72)
        timed = 27 <= along <= 69
        yield
    timed = False
    if csv_started:
        cmd("csvprofile stop")
    movement.set_throttle_input(0)
    movement.set_brake_input(1)
    movement.set_handbrake_input(True)
    ok = path[-1][0] >= 69 and min(r[-1] for r in path) > .70
    timings = sorted(samples)
    report = {"ok":ok, "saved_bend_actors":len(added), "station_start_m":path[0][0], "station_end_m":path[-1][0],
              "timed_frames":len(samples), "p95_engine_tick_ms":timings[math.ceil(.95*len(timings))-1] if timings else None,
              "median_engine_tick_ms":statistics.median(timings) if timings else None,
              "path":path[::5]}
    if candidate:
        driven_tree = next(c for a in added for c in a.get_components_by_class(u.InstancedStaticMeshComponent)
                           if 'ForestAccessPaintedTree' in map(str,c.component_tags))
        report['driven_tree'] = driven_tree.static_mesh.get_path_name()
    (out/"drive.json").write_text(json.dumps(report,indent=2))
    if timing_only:
        import shutil
        end=time.monotonic()+20
        while time.monotonic()<end:
            ready=[f for f in set(csv_dir.glob('Profile*.csv*'))-csv_before if f.stat().st_size>5000]
            if ready:break
            yield
        else:raise RuntimeError('Timed drive produced no GPU trace')
        for _ in range(12):yield
        file=max(ready,key=lambda f:f.stat().st_mtime_ns)
        shutil.copyfile(file,out/('timing'+''.join(file.suffixes)))
        cmd('quit')
        return
    yield from photo("finish")
    def roadside(st,off,height):
        x,y,_=route.at(st,off)
        return u.Vector(x,y,ground(x,y)+height)
    cam=u.GTVehicleSetupLibrary.spawn_actor_of_class(world,u.CameraActor,u.Transform(location=roadside(49,0,180)),"ForestAccessReview")
    cam.camera_component.set_field_of_view(73)
    views = [
        ("bend",roadside(40,.4,245),roadside(55,-3,83)),
        ("river-verge",roadside(54,0,180),roadside(58,-11,95)),
        ("interior",roadside(51,0,180),roadside(56,11,125)),
        ("fern-bed",roadside(57,2.5,125),roadside(62,8,52)),
        ("floor",roadside(54,-3.1,115),roadside(57.6,-8.0,33)),
        ("crowns",roadside(50,0,180),roadside(56,-12,900))]
    if candidate:
        centre,extent=stone.get_actor_bounds(False)
        probes=[]
        for dx,dy in ((0,0),(.65,0),(-.65,0),(0,.65),(0,-.65)):
            x,y=centre.x+dx*extent.x,centre.y+dy*extent.y
            probes.append([x,y,ground(x,y)])
        added_instances=[]
        for a in added:
            for c in a.get_components_by_class(u.InstancedStaticMeshComponent):
                if not c.static_mesh or c.get_instance_count()<1:continue
                tf=c.get_instance_transform(0,True)
                p=tf.translation
                added_instances.append([c.static_mesh.get_name(),c.get_instance_count(),*p.to_tuple(),ground(p.x,p.y)])
        (out/"seating.json").write_text(json.dumps(dict(stone_centre=centre.to_tuple(),stone_extent=extent.to_tuple(),
            stone_pivot=stone.get_actor_location().to_tuple(),terrain_probes=probes,first_instances=added_instances),indent=2))
        inventory=[]
        nearest=roadside(49,0,0)
        box=u.Box()
        box.set_editor_property('min',nearest-u.Vector(3600,3600,3000))
        box.set_editor_property('max',nearest+u.Vector(3600,3600,6000))
        box.set_editor_property('is_valid',True)
        for actor in actors:
            for c in actor.get_components_by_class(u.InstancedStaticMeshComponent):
                if not c.static_mesh or not c.visible or c.hidden_in_game:continue
                ids=c.get_instances_overlapping_box(box,True)
                if ids:
                    inventory.append([actor.get_actor_label(),c.static_mesh.get_name(),len(ids),
                        str(c.get_collision_enabled()),[m.get_name() if m else "" for m in c.get_materials()]])
        (out/"local-inventory.json").write_text(json.dumps(inventory,indent=1))
        _,rock_station,rock_offset=route.nearest(centre.x,centre.y)
        side=math.copysign(1,rock_offset)
        views.extend([("landmark",roadside(rock_station-3,side*1.1,150),centre),
                      ("landmark-high",roadside(rock_station-3,rock_offset-side*2.3,290),centre),
                      ("colony",roadside(54,3.5,110),roadside(56,10.2,65))])
        pilot=next(c for a in added for c in a.get_components_by_class(u.InstancedStaticMeshComponent)
                   if 'ForestAccessPaintedTree' in map(str,c.component_tags))
        trunk=pilot.get_instance_transform(0,True).translation
        _,ts,to=route.nearest(trunk.x,trunk.y)
        views.append(('pilot-crown',roadside(ts-4,to-5,190),trunk+u.Vector(0,0,345)))
    for label,eye,look in views:
        cam.set_actor_location_and_rotation(eye,u.MathLibrary.find_look_at_rotation(eye,look),False,True)
        pc.set_view_target_with_blend(cam,0)
        end=time.monotonic()+2.5
        while time.monotonic()<end:
            yield
        yield from photo(label)
        if label in ('interior','floor') and os.environ.get('GT_BEND_ISOLATE_MOSS')=='1':
            for family,stem in [('earth','SM_ShoulderRelief_'),('hummocks','SM_NZ_MossHummock')]:
                matches=[c for a in actors for c in a.get_components_by_class(u.StaticMeshComponent)
                         if c.visible and c.static_mesh and c.static_mesh.get_name().startswith(stem)]
                try:
                    for c in matches:c.set_visibility(False)
                    for _ in range(32):yield
                    yield from photo(label+'-without-'+family)
                finally:
                    for c in matches:c.set_visibility(True)
                for _ in range(32):yield
    csv_paths=set(csv_dir.glob("Profile*.csv*"))-csv_before
    if csv_paths:
        import shutil
        file=max(csv_paths,key=lambda f:f.stat().st_mtime)
        shutil.copyfile(file,out/("timing"+"".join(file.suffixes)))
    if not ok:
        raise RuntimeError("Pickup did not traverse the full bend")
    if os.environ.get("GT_BEND_MOTION")=="1":
        if candidate:
            dressing=[a.static_mesh_component for a in added if isinstance(a,u.StaticMeshActor)
                   and a.static_mesh_component.static_mesh.get_name().startswith(('SM_ShoulderRelief_','SM_WoodlandFronds_'))]
            dressing.extend(c for a in added for c in a.get_components_by_class(u.InstancedStaticMeshComponent)
                            if 'ForestAccessPines' in map(str,c.component_tags))
            if len(dressing)==3:
                eye,look=roadside(51,0,180),roadside(56,11,125)
                cam.set_actor_location_and_rotation(eye,u.MathLibrary.find_look_at_rotation(eye,look),False,True)
                yield from profile_dressing(dressing,csv_dir)
        # Capture a separate pass so screenshot readback cannot affect the timing CSV.
        pc.set_view_target_with_blend(car,0)
        cmd(f"BugItGo {start.x:.2f} {start.y:.2f} {ground(start.x,start.y)+150:.2f} 0 {route.at(22)[2]:.3f} 0")
        settle=time.monotonic()+3
        while time.monotonic()<settle:yield
        movement.set_handbrake_input(False)
        movement.set_brake_input(0)
        movement.set_target_gear(1,True)
        snaps=[]; next_station=27.
        timeout=time.monotonic()+60
        while time.monotonic()<timeout:
            p=car.get_actor_location()
            along=station(p)
            target=at(along+6)
            yaw=math.degrees(math.atan2(target.y-p.y,target.x-p.x))
            error=(yaw-car.get_actor_rotation().yaw+180)%360-180
            car.set_raw_steer(max(-1,min(1,error/33)))
            movement.set_sleeping(False)
            movement.set_throttle_input(.65)
            if along>=next_station:
                snaps.append([len(snaps),along,time.monotonic()])
                yield from photo("motion-%03d"%(len(snaps)-1))
                next_station+=1.6
            if along>=69:break
            yield
        (out/"motion.json").write_text(json.dumps(snaps))
    if study_crown:
        yield from examine(pair,path,route,ground,cam,pc,cmd,photo,csv_dir,out)
    if os.environ.get('GT_BEND_SUNSET')=='1':
        yield from sunset_study(actors,cam,car,roadside,ground)
    cmd("quit")

worker = run()
def tick(dt):
    if worker.gi_running:
        return
    try:
        if timed:
            samples.append(dt*1000)
        next(worker)
    except StopIteration:
        u.unregister_slate_post_tick_callback(handle)
    except Exception:
        (out/"error.txt").write_text(traceback.format_exc())
        u.unregister_slate_post_tick_callback(handle)
        if world:
            cmd("quit")
handle = u.register_slate_post_tick_callback(tick)
