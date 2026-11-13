"""Repeatable same-car gravel / low-range checks in the saved LiDAR map.

Transient PIE only: no asset or level saves. This is a route-following instrument,
not a player-feel verdict or standalone performance benchmark.
"""
import bisect
import json
import math
import os
import time
import traceback
from pathlib import Path
import unreal as u

ROOT = Path(u.Paths.project_dir()).resolve()
OUT = ROOT / 'Saved/LidarAuthoringQA/Rally'
OUT.mkdir(parents=True, exist_ok=True)
LABEL = os.environ.get('GT_DUAL_DRIVE_LABEL', 'baseline')
MODE = os.environ.get('GT_DUAL_DRIVE_MODE', 'routes')
GC_STRESS = os.environ.get('GT_DUAL_DRIVE_GC_STRESS', '0') == '1'
REPORT = OUT / (LABEL + '.json')
roads = json.loads((ROOT/'Art/Export/LidarStudy/Place/roads.json').read_text())
report = dict(ok=False, label=LABEL, runs=[], gc_stress=GC_STRESS, note='PIE automated driver; no map saves; owner drive remains the feel gate')
world = pc = car = author = None
busy = False

def save():
    REPORT.write_text(json.dumps(report, indent=2))

def registry_snapshot():
    instance=u.GameplayStatics.get_game_instance(world)
    registry=None
    iterator=u.ObjectIterator(u.GTItemRegistry)
    try:
        for item in iterator:
            if item.get_outer()==instance:
                registry=item
                break
    finally:
        del iterator # Unreal object iterators pause GC while alive.
    assert registry
    # Keep names, not Python object references that could mask a GC ownership bug.
    result={name:sorted(item.get_path_name() for item in getattr(registry,'get_'+name)()) for name in ('items','parts','recipes','upgrades')}
    assert all(result.values()),result
    return result

def path(name):
    pts = next(r['points'] for r in roads if r['name'] == name)
    cum = [0.]
    for a,b in zip(pts,pts[1:]): cum.append(cum[-1] + math.dist(a,b))
    return pts,cum

def at(pts,cum,s):
    s = max(0., min(cum[-1],s))
    i = max(1,min(len(cum)-1,bisect.bisect_right(cum,s)))
    a,b = pts[i-1],pts[i]
    f = (s-cum[i-1])/max(.001,cum[i]-cum[i-1])
    return a[0]+(b[0]-a[0])*f,a[1]+(b[1]-a[1])*f

def project(pts,cum,x,y,station):
    best = (station,1e30)
    for i in range(max(1,bisect.bisect_left(cum,station-1500)),min(len(cum),bisect.bisect_right(cum,station+5000)+1)):
        a,b = pts[i-1],pts[i]
        dx,dy = b[0]-a[0],b[1]-a[1]
        f = max(0.,min(1.,((x-a[0])*dx+(y-a[1])*dy)/max(.001,dx*dx+dy*dy)))
        d = math.hypot(x-a[0]-f*dx,y-a[1]-f*dy)
        if d < best[1]: best = cum[i-1]+f*(cum[i]-cum[i-1]),d
    return best

def ground(x,y):
    xy = u.Vector2D(x,y)
    for tile in author.relief_tiles.values():
        if tile:
            p = tile.get_actor_location()
            if p.x<=x<p.x+tile.span_cm and p.y<=y<p.y+tile.span_cm: return tile.height_at(xy)
    return author.base_height_at(xy)

def settle(seconds):
    start = u.GameplayStatics.get_time_seconds(world)
    while u.GameplayStatics.get_time_seconds(world)-start < seconds: yield 0

def firm_surface_checks():
    surface=u.GameplayStatics.get_all_actors_of_class(world,u.GTLandscapeSurface)[0]
    logging=next(r['name'] for r in roads if r.get('authoring'))
    cases=[]
    for name in ('Waimeamea Road','Riverside access'):
        cases.append((name,*at(*path(name),20000.),False))
    cases.append(('Logging mud',*at(*path(logging),25000.),True))
    cases.append(('River gravel bank',-47900.,-34200.,True))
    report['soil_strokes']=[]
    for name,x,y,yielding in cases:
        mesh=car.get_component_by_class(u.SkeletalMeshComponent)
        car.set_actor_location(u.Vector(x,y-500,ground(x,y-500)+100),False,True)
        mesh.set_physics_linear_velocity(u.Vector())
        mesh.set_physics_angular_velocity_in_degrees(u.Vector())
        car.get_chaos_movement().set_handbrake_input(True)
        yield from settle(3)
        q=surface.sample_surface(u.Vector2D(x,y))
        before=q.surface_delta_cm
        surface.apply_review_soil_stroke(u.Vector2D(x-100,y),u.Vector2D(x+100,y),70.,3.,.8)
        yield from settle(3)
        after=surface.sample_surface(u.Vector2D(x,y)).surface_delta_cm
        row=dict(name=name,depth_cap_cm=q.sinkage_cap_cm,surface_tag=str(q.surface_tag),before_cm=before,after_cm=after)
        row['ok']=(q.sinkage_cap_cm>0 and after<before-.1) if yielding else (q.sinkage_cap_cm==0 and abs(after-before)<.001)
        report['soil_strokes'].append(row)
        save()
        assert row['ok'],row

def slide(ident,cls,enabled,low=False):
    global car
    pts,cum=path('Waimeamea Road')
    x,y=at(pts,cum,43000)
    tx,ty=at(pts,cum,44000)
    yaw=math.degrees(math.atan2(ty-y,tx-x))
    if car:car.destroy_actor()
    car=u.GTVehicleSetupLibrary.spawn_actor_of_class(world,cls,u.Transform(location=u.Vector(x,y,ground(x,y)+100),rotation=u.Rotator(yaw=yaw)),'SlideCheck_'+ident)
    pc.possess(car);car.disable_input(pc);car.reset_driving_inputs();car.set_chase_camera(True)
    move=car.get_chaos_movement();drive=car.get_drivetrain()
    move.set_editor_property('high_speed_slide_recovery',.75 if enabled else 0.)
    drive.set_low_range(low);move.set_handbrake_input(True)
    yield from settle(6)
    mesh=car.get_component_by_class(u.SkeletalMeshComponent)
    origin=car.get_actor_location()
    surface=u.GameplayStatics.get_all_actors_of_class(world,u.GTLandscapeSurface)[0]
    q=surface.sample_surface(u.Vector2D(x,y))
    row=dict(car=ident,road='Waimeamea Road',slide_recovery=enabled,low_range=low,trace=[],surface={key:str(q.get_editor_property(key)) for key in ['softness','native_linear_resistance','native_push_resistance','sinkage_cap_cm']})
    report['runs'].append(row)
    # Identical 65 km/h / 20 degree lateral disturbance, not an acceleration claim.
    angle=math.radians(car.get_actor_rotation().yaw+20.)
    move.set_handbrake_input(False)
    mesh.set_physics_linear_velocity(u.Vector(math.cos(angle)*1805.556,math.sin(angle)*1805.556,0))
    mesh.set_physics_angular_velocity_in_degrees(u.Vector())
    start=u.GameplayStatics.get_time_seconds(world);last=-1
    while u.GameplayStatics.get_time_seconds(world)-start<3:
        now=u.GameplayStatics.get_time_seconds(world)-start
        move.set_throttle_input(0);move.set_brake_input(0);car.set_raw_steer(0)
        if now-last>=.05:
            last=now;v=car.get_velocity();p=car.get_actor_location()
            yaw_now=car.get_actor_rotation().yaw
            slip=(math.degrees(math.atan2(v.y,v.x))-yaw_now+180)%360-180
            row['trace'].append(dict(t=now,kmh=v.length()*.036,slip_deg=slip,lateral_m=(-(p.x-origin.x)*math.sin(math.radians(yaw))+(p.y-origin.y)*math.cos(math.radians(yaw)))*.01,yaw=yaw_now))
        yield 0
    row['max_lateral_m']=max(abs(r['lateral_m']) for r in row['trace'])
    row['integrated_slip_deg_s']=sum(abs(b['slip_deg'])*(b['t']-a['t']) for a,b in zip(row['trace'],row['trace'][1:]))
    row['recover_below_5_s']=next((r['t'] for r in row['trace'] if r['t']>.1 and abs(r['slip_deg'])<5),None)
    row['ok']=all(math.isfinite(r['slip_deg']) for r in row['trace'])
    move.set_handbrake_input(True);save()

def steering(ident,cls,enabled,speed,pattern,low=False):
    """Open-loop steering on the saved road; no path controller can hide response."""
    global car
    pts,cum=path('Waimeamea Road')
    x,y=at(pts,cum,43000.)
    tx,ty=at(pts,cum,43400.)
    yaw=math.degrees(math.atan2(ty-y,tx-x))
    if car:car.destroy_actor()
    car=u.GTVehicleSetupLibrary.spawn_actor_of_class(world,cls,u.Transform(location=u.Vector(x,y,ground(x,y)+100),rotation=u.Rotator(yaw=yaw)),'SteeringCheck_'+ident)
    pc.possess(car);car.disable_input(pc);car.reset_driving_inputs()
    move=car.get_chaos_movement();drive=car.get_drivetrain()
    drive.set_low_range(low);move.set_handbrake_input(True)
    keyboard=pattern in ('keys','reversal')
    if keyboard:car.enable_input(pc)
    # Exercise installed runtime code, including the terrain and low-range gates.
    switch='gt.Vehicle.CountersteerResponse' if pattern=='reversal' else 'gt.Vehicle.ResponsiveSteering'
    u.SystemLibrary.execute_console_command(world,switch+' '+str(int(enabled)),pc)
    yield from settle(4)
    mesh=car.get_component_by_class(u.SkeletalMeshComponent)
    yaw=car.get_actor_rotation().yaw;angle=math.radians(yaw)
    move.set_handbrake_input(False)
    mesh.set_physics_linear_velocity(u.Vector(math.cos(angle)*speed/ .036,math.sin(angle)*speed/.036,0))
    mesh.set_physics_angular_velocity_in_degrees(u.Vector())
    row=dict(car=ident,road='Waimeamea Road',responsive=enabled,low_range=low,initial_kmh=speed,pattern=pattern,trace=[])
    if pattern=='reversal':row['countersteer_response']=enabled
    report['runs'].append(row)
    start=u.GameplayStatics.get_time_seconds(world)
    previous_key=0
    while u.GameplayStatics.get_time_seconds(world)-start<1.4:
        now=u.GameplayStatics.get_time_seconds(world)-start
        command=(1. if now<.18 else 0.) if pattern=='tap' else ((.5 if now<.45 else -.5) if now<.9 else 0.) if pattern=='reverse' else (.5 if now<.7 else 0.)
        if keyboard:
            command=(1 if now<.25 else (-1 if now<.60 else 0)) if pattern=='reversal' else (-1 if now<.16 else (1 if .28<=now<.44 else 0))
            if command!=previous_key:
                if previous_key:u.SystemLibrary.execute_console_command(world,'Input.-key '+('A' if previous_key<0 else 'D'),pc)
                if command:u.SystemLibrary.execute_console_command(world,'Input.+key '+('A' if command<0 else 'D'),pc)
                previous_key=command
        else:car.set_raw_steer(command)
        move.set_throttle_input(0);move.set_brake_input(0)
        v=car.get_velocity();p=car.get_actor_location();r=car.get_actor_rotation()
        wheels=move.get_editor_property('wheels')
        contacts=sum(bool(u.ChaosWheeledVehicleMovementComponent.break_wheel_status(move.get_wheel_state(i))[0]) for i in range(4))
        slip=(math.degrees(math.atan2(v.y,v.x))-r.yaw+180)%360-180
        row['trace'].append(dict(t=now,input=command,raw_input=car.get_raw_steer(),response_weight=car.get_steering_response_weight(),kmh=v.length()*.036,wheel_deg=sum(w.get_steer_angle() for w in wheels[:2])*.5,yaw_deg=(r.yaw-yaw+180)%360-180,yaw_rate=mesh.get_physics_angular_velocity_in_degrees().z,slip_deg=slip,roll=r.roll,contacts=contacts))
        if pattern=='reversal':
            row['trace'][-1]['solver']=json.loads(move.rally_handling_report())
            row['trace'][-1]['reversal_direction']=car.get_steering_reversal_direction()
        yield 0
    row['peak_wheel_deg']=max(abs(r['wheel_deg']) for r in row['trace'])
    if pattern=='reversal':
        row['wheel_at_043']=min(row['trace'],key=lambda r:abs(r['t']-.43))['wheel_deg']
        row['reversal_to_90_s']=next((r['t']-.25 for r in row['trace'] if r['t']>.25 and r['solver']['filtered']<=-.9),None)
    row['peak_yaw_rate']=max(abs(r['yaw_rate']) for r in row['trace'])
    row['yaw_at_07']=min(row['trace'],key=lambda r:abs(r['t']-.7))['yaw_deg']
    row['max_roll']=max(abs(r['roll']) for r in row['trace'])
    row['ok']=all(math.isfinite(r['yaw_rate']) for r in row['trace']) and row['max_roll']<35
    if keyboard:
        row['ok'] &= min(r['raw_input'] for r in row['trace'])<-.99 and max(r['raw_input'] for r in row['trace'])>.99 and abs(row['trace'][-1]['raw_input'])<.001
    car.reset_driving_inputs();move.set_handbrake_input(True);save()


def drive(ident,cls,road,station,low,seconds):
    global car
    pts,cum = path(road)
    x,y = at(pts,cum,station)
    tx,ty = at(pts,cum,station+400)
    yaw = math.degrees(math.atan2(ty-y,tx-x))
    if car: car.destroy_actor()
    car = u.GTVehicleSetupLibrary.spawn_actor_of_class(world,cls,u.Transform(location=u.Vector(x,y,ground(x,y)+100),rotation=u.Rotator(yaw=yaw)),'RallyCheck_'+ident)
    assert car
    pc.possess(car)
    car.disable_input(pc)
    car.reset_driving_inputs()
    car.set_chase_camera(True)
    move = car.get_chaos_movement()
    drive = car.get_drivetrain()
    drive.set_low_range(low)
    drive.set_diff_lock(low)
    move.set_handbrake_input(True)
    yield from settle(7)
    row = dict(car=ident,road=road,low_range=low,diff_lock=low,start_station_m=station/100,trace=[])
    row['start_cm']=[x,y,ground(x,y)+100]
    row['start_yaw']=yaw
    row['next_100m_grade_percent']=ground(*at(pts,cum,station+10000))*.01-ground(x,y)*.01
    report['runs'].append(row)
    row['mass_kg'] = move.get_editor_property('mass')
    row['max_engine_nm'] = move.get_editor_property('engine_setup').get_editor_property('max_torque')
    row['front_drive_share'] = drive.get_editor_property('centre_split_front')
    surface=u.GameplayStatics.get_all_actors_of_class(world,u.GTLandscapeSurface)[0]
    q=surface.sample_surface(u.Vector2D(x,y))
    row['surface']={key:str(q.get_editor_property(key)) for key in ['softness','native_linear_resistance','native_push_resistance','sinkage_cap_cm','bNativeSubstanceResponse','bGranularResponse','bSoilShearResponse']}
    row['wheel_radii_cm'] = [w.get_editor_property('wheel_radius') for w in move.get_editor_property('wheels')]
    move.set_handbrake_input(False)
    if MODE=='performance':
        capture_before=set((ROOT/'Saved/Profiling/CSV').glob('*.csv'))
        for command in ['csv.UseLegacyFrameTime 0','r.GPUCsvStatsEnabled 1','csvprofile start']:
            u.SystemLibrary.execute_console_command(world,command,pc)
    start = u.GameplayStatics.get_time_seconds(world)
    s0 = station
    last = -1
    slow_since = None
    while True:
        now = u.GameplayStatics.get_time_seconds(world)-start
        if now >= seconds: break
        p = car.get_actor_location()
        station,off = project(pts,cum,p.x,p.y,station)
        speed = car.get_velocity().length()*.01
        look = max(600.,speed*75.)
        tx,ty = at(pts,cum,station+look)
        err = (math.degrees(math.atan2(ty-p.y,tx-p.x))-car.get_actor_rotation().yaw+180)%360-180
        # Pure pursuit at speed, accounting for the car's existing steering curve.
        wheelbase = 254.
        steering_angle = math.degrees(math.atan2(2*wheelbase*math.sin(math.radians(err)),look))
        keys = [(0,1),(12,.72),(25,.5),(37,.34),(50,.26),(62,.2),(75,.17),(100,.14)]
        mph = speed*2.23694
        scale = keys[-1][1]
        for (a,va),(b,vb) in zip(keys,keys[1:]):
            if mph<=b: scale=va+(vb-va)*max(0.,(mph-a)/(b-a));break
        fraction = min(.8,abs(steering_angle)/max(1.,35*scale))
        # Invert the actual input response: old driver treated a squared input as
        # linear and therefore asked for too little wheel angle on every bend.
        weight=car.get_steering_response_weight()
        magnitude=fraction if weight>=.999 else (-weight+math.sqrt(weight*weight+4*(1-weight)*fraction))/(2*(1-weight))
        steer=math.copysign(magnitude,steering_angle)
        # Slow before bends. Never use a fixed high-speed throttle into a hairpin.
        target = 22.22 if not low else 5.
        for ahead in (0,500,1000,1500,2500,3500):
            a,b,c = (at(pts,cum,station+ahead+d) for d in (0,500,1000))
            ab,bc,ac = math.dist(a,b),math.dist(b,c),math.dist(a,c)
            cross = abs((b[0]-a[0])*(c[1]-a[1])-(b[1]-a[1])*(c[0]-a[0]))
            curvature = 2*cross/max(1.,ab*bc*ac)*100
            corner = math.sqrt(1.8/max(.0001,curvature))
            target = min(target,math.sqrt(corner*corner+2*1.8*ahead*.01))
        throttle = .65 if low else max(0.,min(.9,(target-speed)*.3))
        brake = 0. if low else max(0.,min(.85,(speed-target)*.45))
        car.set_raw_steer(steer)
        move.set_throttle_input(throttle)
        move.set_brake_input(brake)
        if now-last>=.2:
            last=now
            contacts=[bool(u.ChaosWheeledVehicleMovementComponent.break_wheel_status(move.get_wheel_state(i))[0]) for i in range(4)]
            row['trace'].append(dict(t=round(now,3),s_m=round(station/100,3),off_m=round(off/100,3),kmh=round(speed*3.6,3),target_kmh=round(target*3.6,3),gear=drive.get_gear(),rpm=drive.get_engine_rpm(),engine_nm=drive.get_engine_torque_nm(),steer=steer,contacts=sum(contacts),roll=car.get_actor_rotation().roll,drive_nm=[w.drive_torque_nm for w in drive.wheels]))
            if MODE=='offroad':
                direction=car.get_steering_reversal_direction()
                row['trace'][-1]['reversal_direction']=direction
                row['trace'][-1]['response_weight']=car.get_steering_response_weight()
                assert direction==0. and car.get_steering_response_weight()==0.,'Rally steering affected low-range mud'
                row['trace'][-1]['ride_weight']=move.get_rally_suspension_weight()
                row['trace'][-1]['ride_scale']=json.loads(move.rally_handling_report())['ride_scale']
                assert row['trace'][-1]['ride_weight']==0 and row['trace'][-1]['ride_scale']==1,'Rally suspension affected low-range mud'
        if off>900 or abs(car.get_actor_rotation().roll)>65:
            row['aborted']='departed route or rolled';break
        if now>4 and speed<.2:
            if slow_since is None:slow_since=now
            if now-slow_since>5:
                row['aborted']='stalled for five seconds';break
        else:slow_since=None
        if station>cum[-1]-2500: break
        yield 0
    if MODE=='performance':u.SystemLibrary.execute_console_command(world,'csvprofile stop',pc)
    row['distance_m'] = (station-s0)*.01
    row['peak_kmh'] = max((r['kmh'] for r in row['trace']),default=0)
    row['max_off_m'] = max((r['off_m'] for r in row['trace']),default=0)
    row['max_gear'] = max((r['gear'] for r in row['trace']),default=0)
    if not low:row['reached_60_kmh']=row['peak_kmh']>=60
    row['brake_start_kmh'] = car.get_velocity().length()*.036
    stop_start = car.get_actor_location()
    brake_t = u.GameplayStatics.get_time_seconds(world)
    move.set_throttle_input(0)
    while car.get_velocity().length()>60 and u.GameplayStatics.get_time_seconds(world)-brake_t<10:
        move.set_brake_input(1)
        yield 0
    row['brake_seconds'] = u.GameplayStatics.get_time_seconds(world)-brake_t
    row['brake_distance_m'] = (car.get_actor_location()-stop_start).length()*.01
    row['brake_end_kmh'] = car.get_velocity().length()*.036
    move.set_brake_input(0)
    move.set_handbrake_input(True)
    row['ok'] = not row.get('aborted') and row['distance_m']>10 and row['brake_end_kmh']<3
    if MODE=='performance':
        yield from settle(4)
        captured=set((ROOT/'Saved/Profiling/CSV').glob('*.csv'))-capture_before
        assert len(captured)==1,captured
        row['csv']=str(captured.pop())
    save()

def water_regression():
    """Actual LiDAR shore opening and remote-contact streaming regression."""
    import sys
    sys.path.insert(0,str(ROOT/'Art/Unreal'))
    from lidar_grounding import GroundSampler
    sampler=GroundSampler(author)
    surface=u.GameplayStatics.get_all_actors_of_class(world,u.GTLandscapeSurface)[0]
    sheet=next(s for s in u.GameplayStatics.get_all_actors_of_class(world,u.GTWaterSheet) if s.get_editor_property('domain_ground_surface'))
    car.reset_driving_inputs()
    car.get_chaos_movement().set_handbrake_input(True)
    yield from settle(4)
    assert pc.exit_car()
    walker=pc.get_player_character()
    cx,cy=-47938.65804392218,-37813.65804392218
    walker.set_actor_location(u.Vector(cx+200,cy+200,sampler.height(cx+200,cy+200)+100),False,True)
    yield from settle(4)
    candidates=[]
    for dx in range(-600,601,25):
        for dy in range(-600,601,25):
            x,y=cx+dx,cy+dy;q=u.Vector2D(x,y)
            if sheet.covers(q):continue
            soil=surface.sample_surface(q)
            if soil.sinkage_cap_cm<2:continue
            for vx,vy in ((25,0),(-25,0),(0,25),(0,-25)):
                w=u.Vector2D(x+vx,y+vy)
                if not sheet.covers(w):continue
                gap=sampler.height(x,y)+soil.surface_delta_cm-sheet.surface_cm_at(w)
                available=soil.sinkage_cap_cm+soil.surface_delta_cm-gap
                if .3<gap<6 and available>1:candidates.append((-available,x,y,w.x,w.y))
    assert candidates,'No erodible shore candidate in the reference reach'
    _,x,y,wx,wy=min(candidates);q=u.Vector2D(x,y);wet=u.Vector2D(wx,wy)
    before=surface.sample_surface(q).surface_delta_cm
    ref=json.loads((ROOT/'Art/Export/LidarStudy/Place/authoring-reference.json').read_text())['river_points_cm']
    remote=next(u.Vector2D(p[0],p[1]) for p in ref[::50] if math.hypot(p[0]-x,p[1]-y)>20000 and sheet.covers(u.Vector2D(p[0],p[1])))
    old=sheet.review_water_column(wet)
    sheet.review_water_contact(remote,10.)
    impulse=sheet.add_impulse(remote,100.,2.)
    after_remote=sheet.review_water_column(wet)
    report['remote_water_contact']=dict(before_r=old.r,after_r=after_remote.r,remote_impulse=impulse)
    assert old.r>100 and old.r==after_remote.r and impulse==0,report['remote_water_contact']
    for _ in range(4):
        surface.apply_review_soil_stroke(wet,u.Vector2D(x+(x-wx)*3,y+(y-wy)*3),100.,35.,.8)
        yield .15
    yield from settle(2)
    soil=surface.sample_surface(q)
    report['live_shore']=dict(point=[x,y],before_cm=before,after_cm=soil.surface_delta_cm,wet_after=sheet.covers(q),depth_cm=soil.water_depth_cm)
    assert soil.surface_delta_cm<before-.5 and sheet.covers(q) and soil.water_depth_cm>.5,report['live_shore']
    # Height-only hot path must remain equivalent at native/legacy boundaries,
    # including the freshly deformed shore and dry gravel. No force tolerances.
    checks=0;maximum=0.
    for centre in [(x,y),(-43919.,-41176.),(-24987.,-63021.),(-151000.,99000.)]:
        for dx in range(-400,401,40):
            for dy in range(-400,401,40):
                point=u.Vector2D(centre[0]+dx,centre[1]+dy)
                full=surface.sample_surface(point)
                for native,expected in [(False,full.surface_delta_cm),(True,full.native_upper_cm-5.-full.native_extrude_cm)]:
                    error=abs(surface.contact_height_cm(point,native)-expected)
                    maximum=max(maximum,error);checks+=1
                    assert error<.0001,(point,native,error)
    report['contact_height_equivalence']=dict(checks=checks,max_error_cm=maximum)
    save()


def run():
    global world,pc,car,author
    les = u.get_editor_subsystem(u.LevelEditorSubsystem)
    assert les.load_level('/Game/GrandTour/ArtTests/LidarStudy/L_LidarStudy')
    if MODE in ('offroad','reversal'):yield 5
    author = next(a for a in u.get_editor_subsystem(u.EditorActorSubsystem).get_all_level_actors() if isinstance(a,u.GTProceduralGround))
    les.editor_set_viewport_realtime(False)
    profile=json.loads((ROOT/'Art/lidar_performance.json').read_text())['commands']
    names=[command.split()[0] for command in profile]
    before={name:u.SystemLibrary.get_console_variable_float_value(name) for name in names}
    assert u.GTPlayWindowLibrary.request_play_in_new_window(1600,900)
    while not world:
        world=u.EditorLevelLibrary.get_game_world()
        yield .2
    pc=u.GameplayStatics.get_player_controller(world,0)
    report['requested_resolution']=[1600,900]
    report['viewport_resolution']=list(pc.get_viewport_size())
    car=pc.get_car()
    commands=profile
    if MODE in ('keyboard','water','performance','offroad','reversal'):
        applied={name:u.SystemLibrary.get_console_variable_float_value(name) for name in names}
        report['automatic_profile']=dict(before=before,applied=applied)
        if MODE in ('offroad','reversal'):report['automatic_profile']['note']='Preset preapplied at process startup to avoid changing render configuration during PIE. This does not test automatic profile application/restoration.'
        assert all(abs(applied[c.split()[0]]-float(c.split()[1]))<.001 for c in profile),applied
        commands=[] # Validate normal PIE startup, without the test applying its own quality preset.
    for cmd in commands+['t.IdleWhenNotForeground 0','Slate.bAllowThrottling 0','gt.Perf.LogSpikes 1']:
        u.SystemLibrary.execute_console_command(world,cmd,pc)
    yield from settle(5)
    if MODE=='performance':
        report['registry_before']=registry_snapshot()
        u.SystemLibrary.execute_console_command(world,'gc.DumpAnalyticsToLog 1',pc)
        if GC_STRESS:
            # Deliberate diagnostic overrides, never saved in the gameplay preset.
            for command in ['Log LogGarbage Log','gc.AllowIncrementalReachability 1','gc.IncrementalReachabilityTimeLimit 0.001','gc.AllowIncrementalGather 1','gc.VerifyNoUnreachableObjects 1','gc.ContinuousIncrementalGC 1']:
                u.SystemLibrary.execute_console_command(world,command,pc)
    specs=[('RangeRover',u.GTCarPawn),('BMW',u.load_class(None,'/Game/GrandTour/Vehicles/Bodies/E39Touring/BP_E39Touring.BP_E39Touring_C')),('Suzuki',u.load_class(None,'/Game/GrandTour/Vehicles/Bodies/SJ413/BP_SJ413.BP_SJ413_C'))]
    for ident,cls in specs:
        assert cls,ident
        if MODE=='water':break
        elif MODE=='offroad':
            logging=next(r['name'] for r in roads if r.get('authoring'))
            yield from drive(ident,cls,logging,22000.,True,15.)
        elif MODE=='reversal':
            for speed,low in ((80,False),(20,True)):
                for enabled in (False,True):yield from steering(ident,cls,enabled,speed,'reversal',low)
        elif MODE=='performance':
            yield from drive(ident,cls,'Waimeamea Road',20000.,False,40.)
            yield from drive(ident,cls,'Riverside access',129000.,False,35.)
            break
        elif MODE=='keyboard':
            for speed,low in ((20,False),(40,False),(80,False),(20,True)):
                for enabled in (False,True):yield from steering(ident,cls,enabled,speed,'keys',low)
        elif MODE=='steering':
            for speed,pattern,low in ((80,'tap',False),(80,'half',False),(90,'reverse',False),(20,'half',True),(20,'half',False),(90,'half',True)):
                for enabled in (False,True):yield from steering(ident,cls,enabled,speed,pattern,low)
        elif MODE=='slides':
            for enabled in (False,True):yield from slide(ident,cls,enabled)
        elif MODE=='access':
            yield from drive(ident,cls,'Riverside access',129000.,False,35.)
        elif MODE=='firm':
            yield from drive(ident,cls,'Waimeamea Road',20000.,False,40.)
            yield from drive(ident,cls,'Riverside access',129000.,False,35.)
            logging=next(r['name'] for r in roads if r.get('authoring'))
            yield from drive(ident,cls,logging,22000.,True,15.)
        else:
            yield from drive(ident,cls,'Waimeamea Road',20000.,False,40.)
            yield from drive(ident,cls,'Riverside access',129000.,True,15.)
    if MODE in ('firm','access'):yield from firm_surface_checks()
    if MODE in ('steering','keyboard','reversal'):
        report['comparisons']=[]
        for a,b in zip(report['runs'][::2],report['runs'][1::2]):
            bypass=a['low_range']
            ratio=b['peak_wheel_deg']/max(.001,a['peak_wheel_deg'])
            yaw_ratio=abs(b['yaw_at_07'])/max(.001,abs(a['yaw_at_07']))
            weights=[r['response_weight'] for r in b['trace'] if r['t']>.1]
            ok=(abs(ratio-1)<.06 and max(weights)==0) if bypass else (ratio>1.7 and (MODE=='keyboard' or yaw_ratio>1.4) and min(weights)>.95)
            if MODE=='reversal':
                ratio=(b['peak_wheel_deg']/max(.001,a['peak_wheel_deg'])) if bypass else abs(b['wheel_at_043'])/max(.001,abs(a['wheel_at_043']))
                ok=(abs(ratio-1)<.1 and max(weights)==0) if bypass else (ratio>1.5 and b['reversal_to_90_s'] is not None and b['reversal_to_90_s']<.23)
            report['comparisons'].append(dict(car=a['car'],pattern=a['pattern'],kmh=a['initial_kmh'],low=a['low_range'],wheel_ratio=ratio,yaw_ratio=yaw_ratio,ok=ok))
    report['ok']=all(r['ok'] for r in report['runs']) and all(c['ok'] for c in report.get('comparisons',[]))
    if MODE in ('keyboard','water','performance','offroad'):
        yield from water_regression()
        if MODE=='performance':
            report['registry_after']=registry_snapshot()
            assert report['registry_before']==report['registry_after'],'Registry references changed across collection'
            if GC_STRESS:
                u.SystemLibrary.execute_console_command(world,'gc.ContinuousIncrementalGC 0',pc)
        car.reset_driving_inputs()
        car=pc=world=author=None
        u.EditorLevelLibrary.editor_end_play()
        yield 2
        restored={name:u.SystemLibrary.get_console_variable_float_value(name) for name in names}
        report['automatic_profile']['restored']=restored
        report['automatic_profile']['restore_ok']=all(abs(restored[n]-before[n])<.001 for n in names)
        assert report['automatic_profile']['restore_ok'],report['automatic_profile']
    save()

steps=run()
began=time.monotonic()
deadline=0
def tick(dt):
    global busy,deadline,steps
    if busy or time.monotonic()<deadline:return
    busy=True
    done=False
    try:
        assert time.monotonic()-began<1000,'Drive check timeout'
        deadline=time.monotonic()+next(steps)
    except StopIteration:done=True
    except Exception:
        report['ok']=False;report['error']=traceback.format_exc();save();u.log_error(report['error']);done=True
    finally:busy=False
    if done:
        u.unregister_slate_post_tick_callback(handle)
        u.EditorLevelLibrary.editor_end_play()
        u.SystemLibrary.quit_editor()

u.EditorPythonScripting.set_keep_python_script_alive(True)
handle=u.register_slate_post_tick_callback(tick)
