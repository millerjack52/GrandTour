"""Headless real-car comparisons on every rebuilt driving-route surface."""
import sys,json,time,traceback,re,math
from pathlib import Path
import unreal as u
ROOT=Path(u.Paths.project_dir()).resolve();sys.path.insert(0,str(ROOT/'Art/Unreal'))
from mud_route_profiles import PROFILES,LEVEL,PUDDLES
# CL2: the profiles with `thirds` are lane studies (the clay feel lane), driven by lane_run() below with three passes; the others keep the original short run.
BASE=[p for p in PROFILES if 'thirds' not in p]
CLAY=next(p for p in PROFILES if 'thirds' in p)
# The clay lane, then the same lane with its ClayWeight forced to 0 at play (the control: same wetness, same paint, no clay response), then the existing dry clay lane and mud lane.
LANE_STUDIES=[(CLAY,False),(CLAY,True)]+[(p,False) for p in BASE if p['key'] in ('DryClay','WetMud')]
THROTTLE=.65;RUN_IN_CM=1000.;PASSES=3;LATER_S=20.
OUT=ROOT/'Art/Export/MudVariants';DEST=OUT/'response-check-report.json'
report={'ok':False,'runs':[],'checks':{},'rendered_review':False,'lanes':[]};world=car=surface=move=fx=None;active=False;rows=[];clock='wall';deadline=0;busy=False
lane_on=False;lane_rec=[]
def stats(s):return {k:float(v) for k,v in re.findall(r'(\w+)=(-?[\d.]+)',s)}
def sample():
    ws=car.get_traction().wheels;t=car.get_component_by_class(u.GTVehicleTuningComponent).get_current()
    g=[u.GTLandscapeSurface.query_wheel_surface(car,w.contact_point,w.tyre_heading,25) for w in ws]
    return {'position':list(car.get_actor_location().to_tuple()),'speed':car.get_velocity().length()*.036,
        'settlement':[s.rest_wheel_support_cm-v.ground_support_cm+v.sinkage_cm for s,v in zip(g,t.wheels)],
        'support':[v.get_editor_property('bLandscapeSupport') for v in t.wheels],
        'contacts':[w.get_editor_property('bInContact') for w in ws],
        'water':[s.water_depth_cm for s in g],'effects':stats(fx.get_effect_report()),
        'fine_emitters':len(surface.get_components_by_class(u.NiagaraComponent))}
def save():DEST.write_text(json.dumps(report,indent=2))
def lane_sample():
    ws=car.get_traction().wheels;p=car.get_actor_location();v=car.get_velocity();f=car.get_actor_forward_vector();r=car.get_actor_right_vector()
    return {'t':u.GameplayStatics.get_time_seconds(world),'x':p.x,'y':p.y,'speed':v.length()*.01,'forward':(v.x*f.x+v.y*f.y)*.01,'lateral':(v.x*r.x+v.y*r.y)*.01,
        'slip':[w.slip_magnitude for w in ws],'slipping':sum(bool(w.get_editor_property('bSlipping')) for w in ws),'contacts':sum(bool(w.get_editor_property('bInContact')) for w in ws)}
def lane_drive():
    # The legacy drive's line keeping (check_mud_variants.py drive_step): steer at the lane's centre line 6.5 m ahead, throttle fixed.
    p=car.get_actor_location();yaw=car.get_actor_rotation().yaw;err=(math.degrees(math.atan2(-p.y,650.))-yaw+180)%360-180
    car.set_raw_steer(max(-.65,min(.65,err/24)));move.set_throttle_input(THROTTLE);move.set_brake_input(0)
def surface_numbers(x,y=0.):
    q=surface.sample_surface(u.Vector2D(x,y))
    return {k:getattr(q,k) for k in ('clay_weight','wetness','cohesion','friction_scale','clay_friction_scale','native_friction','native_linear_resistance','native_push_resistance','softness','sinkage_cap_cm')}
def rut_transect(x):
    # The deepest cell across the lane at x (y -250..250 cm every 5 cm): compression below the rest relief, and the lowest surface level.
    comp=(0.,None);low=(0.,None)
    for iy in range(-250,251,5):
        q=surface.sample_surface(u.Vector2D(x,float(iy)))
        if q.compression_cm>comp[0]:comp=(q.compression_cm,iy)
        if q.surface_delta_cm<low[0]:low=(q.surface_delta_cm,iy)
    return {'compression_cm':round(comp[0],2),'at_y_cm':comp[1],'lowest_surface_cm':round(low[0],2),'lowest_at_y_cm':low[1]}
def decay_cells():
    m=re.search(r'decay_cells=(\d+)',surface.get_surface_report());return int(m.group(1)) if m else -1
def lane_run(p,height,clay_off=False):
    global world,car,surface,move,fx,lane_on,lane_rec
    assert u.GTPlayWindowLibrary.request_play_in_new_window(960,600);yield 'wall',5
    world=u.EditorLevelLibrary.get_game_world();pc=u.GameplayStatics.get_player_controller(world,0);car=pc.get_car();pc.possess(car)
    car.disable_input(pc);car.reset_driving_inputs();move=car.get_chaos_movement()
    surface=u.GameplayStatics.get_all_actors_of_class(world,u.GTLandscapeSurface)[0]
    assert len(u.GameplayStatics.get_all_actors_of_class(world,u.GTMudPatch))==0,'Legacy patches still active'
    mesh=car.get_component_by_class(u.SkeletalMeshComponent)
    if clay_off:
        # The control: the lane's regions keep their wetness and cohesion, but ClayWeight 0 (the sample, the substance numbers and the field's decay hold all read it live).
        regions=list(surface.get_editor_property('mud_regions'))
        for r in regions:
            if r.get_editor_property('clay_weight')>0:r.set_editor_property('clay_weight',0.)
        surface.set_editor_property('mud_regions',regions)
    car.get_drivetrain().set_low_range(True);car.get_drivetrain().set_diff_lock(True)
    x0,x1=float(p['start']),float(p['end']);third=(x1-x0)/3.;edges=[(x0+k*third,x0+(k+1)*third) for k in range(3)]
    names=[t[0] for t in p['thirds']] if 'thirds' in p else ['Third1','Third2','Third3']
    lane={'key':p['key']+('_ClayOff' if clay_off else ''),'clay_off':clay_off,'start_cm':x0,'end_cm':x1,'third_cm':third,'thirds':names,'throttle':THROTTLE,'run_in_cm':RUN_IN_CM,'passes':[],'numbers':[],'camber':'none (flat plane)'}
    for k,(a,b) in enumerate(edges):lane['numbers'].append(dict(third=names[k],mid_cm=(a+b)/2,**surface_numbers((a+b)/2)))
    def place():
        x=x0-RUN_IN_CM;car.set_actor_location_and_rotation(u.Vector(x,0,height(x,0)+140),u.Rotator(),False,True)
        mesh.set_physics_linear_velocity(u.Vector());mesh.set_physics_angular_velocity_in_degrees(u.Vector());car.reset_driving_inputs();move.set_handbrake_input(True)
    report['lanes'].append(lane)
    for n in range(PASSES):
        place();lane_on=False;yield 'sim',3
        lane_rec=[];move.set_handbrake_input(False);lane_on=True;began=u.GameplayStatics.get_time_seconds(world)
        while car.get_actor_location().x<x1-80. and u.GameplayStatics.get_time_seconds(world)-began<40.:yield 'sim',.1
        lane_on=False;move.set_throttle_input(0);move.set_brake_input(1.);rec=list(lane_rec);yield 'sim',1
        per=[]
        for k,(a,b) in enumerate(edges):
            be=b-80. if k==2 else b   # the pass stops braking-bound at x1 - 80, so the last third is timed to there
            inside=[r for r in rec if a<=r['x']<b];cross=[r['t'] for r in rec if r['x']>=a][:1],[r['t'] for r in rec if r['x']>=be][:1]
            took=(cross[1][0]-cross[0][0]) if cross[0] and cross[1] else None
            per.append({'third':names[k],'rows':len(inside),'timed_cm':be-a,'crossing_s':round(took,3) if took else None,'mean_speed_mps':round((be-a)*.01/took,3) if took else None,
                'sample_mean_speed_mps':round(sum(r['speed'] for r in inside)/len(inside),3) if inside else None,'exit_speed_mps':round(inside[-1]['speed'],3) if inside else None,
                'peak_wheel_slip':round(max((max(r['slip']) for r in inside),default=0.),1),'slipping_share':round(sum(r['slipping'] for r in inside)/max(1,4*len(inside)),3),
                'peak_sideways_mps':round(max((abs(r['lateral']) for r in inside),default=0.),3),'mean_abs_y_cm':round(sum(abs(r['y']) for r in inside)/len(inside),1) if inside else None,
                'min_contacts':min((r['contacts'] for r in inside),default=None),'rut':rut_transect((a+b)/2),'decay_cells':decay_cells()})
        lane['passes'].append({'pass':n+1,'reached_cm':car.get_actor_location().x,'thirds':per});save()
    # Rut depth after the third pass, then the car parked 8 m beside the lane's middle (off the soil paint, so it stamps nothing, and inside the 3 x 3 tile window the field decays in,
    # which follows the player) and the same transects LATER_S of game time later.
    xm=(x0+x1)/2;car.set_actor_location_and_rotation(u.Vector(xm,800.,height(xm,800.)+140),u.Rotator(),False,True)
    mesh.set_physics_linear_velocity(u.Vector());mesh.set_physics_angular_velocity_in_degrees(u.Vector());car.reset_driving_inputs();move.set_handbrake_input(True);yield 'sim',1
    lane['decay_cells_after_passes']=decay_cells();yield 'sim',LATER_S/2;lane['decay_cells_half_later']=decay_cells();yield 'sim',LATER_S/2
    lane['decay_cells_later']=decay_cells();lane['later_s']=LATER_S
    lane['ruts_later']=[dict(third=names[k],**rut_transect((a+b)/2)) for k,(a,b) in enumerate(edges)]
    lane['ruts_after_passes']=[dict(third=t['third'],**t['rut']) for t in lane['passes'][-1]['thirds']]
    car.reset_driving_inputs();save()
    world=car=surface=move=None;u.EditorLevelLibrary.editor_end_play();yield 'wall',3

def run():
    global world,car,surface,move,fx,active,rows
    assert u.get_editor_subsystem(u.LevelEditorSubsystem).load_level(LEVEL)
    spec=u.load_asset('/Game/GrandTour/ArtTests/MudVariants/DA_ResponseRoute').spec
    height=lambda x,y:u.GTVehicleSetupLibrary.sample_terrain_height_cm(spec,x,y)
    yield 'wall',3
    for p in BASE:
        assert u.GTPlayWindowLibrary.request_play_in_new_window(960,600);yield 'wall',5
        world=u.EditorLevelLibrary.get_game_world();pc=u.GameplayStatics.get_player_controller(world,0);car=pc.get_car();pc.possess(car)
        car.disable_input(pc);car.reset_driving_inputs();move=car.get_chaos_movement()
        surface=u.GameplayStatics.get_all_actors_of_class(world,u.GTLandscapeSurface)[0]
        fx=surface.get_component_by_class(u.GTLandscapeWheelEffects);assert fx
        assert len(u.GameplayStatics.get_all_actors_of_class(world,u.GTMudPatch))==0,'Legacy patches still active'
        x=p['start']+500;car.set_actor_location_and_rotation(u.Vector(x,0,height(x,0)+140),u.Rotator(),False,True)
        mesh=car.get_component_by_class(u.SkeletalMeshComponent);mesh.set_physics_linear_velocity(u.Vector());mesh.set_physics_angular_velocity_in_degrees(u.Vector())
        car.get_drivetrain().set_low_range(True);car.get_drivetrain().set_diff_lock(True);move.set_handbrake_input(True)
        yield 'sim',4
        settled=sample();rows=[settled]
        if p['key']=='PuddledBog':
            cx,cy,rx,ry=PUDDLES[0];wet=[]
            for py in range(-200,201,50):
                for px in range(-250,251,50):
                    s=surface.sample_surface(u.Vector2D(cx+px,cy+py))
                    if s.water_depth_cm>1:wet.append(s.water_depth_cm)
            report['puddle_probe']={'wet_area_m2':len(wet)*.25,'max_depth_cm':max(wet,default=0)}
        move.set_handbrake_input(False);move.set_brake_input(0);active=True
        yield 'sim',4
        active=False;move.set_throttle_input(0);rows.append(sample())
        r={'key':p['key'],'settled':settled,'samples':rows,'end_kmh':rows[-1]['speed'],
           'travel_cm':rows[-1]['position'][0]-rows[0]['position'][0]}
        report['runs'].append(r);save()
        car.reset_driving_inputs();world=car=surface=move=fx=None
        u.EditorLevelLibrary.editor_end_play();yield 'wall',3
    # CL2: the lane studies (the clay lane's three thirds, and the WetMud and DryClay lanes in the same three-pass protocol), one play session each.
    for lane_p,off in LANE_STUDIES:
        yield from lane_run(lane_p,height,off)
    by={r['key']:r for r in report['runs']}
    mean=lambda k:sum(by[k]['settled']['settlement'])/4
    report['checks']={
        'all_four_variants':len(by)==4,
        'clay_lane_studied':len(report['lanes'])==len(LANE_STUDIES),
        'clay_weight_on_every_third':all(n['clay_weight']>.9 for n in next(l for l in report['lanes'] if l['key']==CLAY['key'])['numbers']),
        'no_clay_on_the_mud_lanes':all(n['clay_weight']<.01 for l in report['lanes'] if l['key']!=CLAY['key'] for n in l['numbers']),
        'clay_off_control_has_no_clay':all(n['clay_weight']<.01 and abs(n['native_friction']-2.2)<.01 for l in report['lanes'] if l['key']==CLAY['key']+'_ClayOff' for n in l['numbers']),
        'wet_clay_slicker_than_dry':(lambda n:n[2]['native_friction']<n[0]['native_friction']-.5 and n[2]['clay_friction_scale']<n[0]['clay_friction_scale']-.2)(next(l for l in report['lanes'] if l['key']==CLAY['key'])['numbers']),
        'lane_passes_finite':all(math.isfinite(v) for l in report['lanes'] for q in l['passes'] for t in q['thirds'] for v in [t['peak_wheel_slip'],t['rut']['compression_cm']]),
        'clay_firmer_than_wet_mud':mean('DryClay')+3<mean('WetMud'),
        'deep_bog_sinks_more_than_standard':mean('DeepBog')>mean('WetMud')+2,
        'puddled_bog_is_soft':mean('PuddledBog')>15,
        'large_connected_puddle_coverage':report['puddle_probe']['wet_area_m2']>8,
        'mud_spray_emits':all(r['samples'][-1]['effects']['emitted']>0 for r in report['runs'] if r['key']!='DryClay'),
        'fine_spray_emitters_created':all(r['samples'][-1]['fine_emitters']>0 for r in report['runs'] if r['key']!='DryClay'),
        'vehicle_makes_progress':all(r['travel_cm']>25 for r in report['runs']),
        'tyres_keep_contact':all(sum(sum(s['contacts']) for s in r['samples'])>=len(r['samples'])*3 for r in report['runs']),
        'finite_motion':all(math.isfinite(v) for r in report['runs'] for s in r['samples'] for v in s['position']+[s['speed']]),
    }
    report['ok']=all(report['checks'].values());save()
    u.unregister_slate_post_tick_callback(handle);u.SystemLibrary.quit_editor()
steps=run()
def tick(dt):
    global busy,clock,deadline
    if busy:return
    busy=True
    try:
        if lane_on:
            lane_drive();lane_rec.append(lane_sample())
        if active:
            move.set_throttle_input(.65);move.set_brake_input(0);rows.append(sample())
        now=u.GameplayStatics.get_time_seconds(world) if clock=='sim' and world else time.monotonic()
        if now<deadline:return
        clock,delay=next(steps)
        deadline=(u.GameplayStatics.get_time_seconds(world) if clock=='sim' and world else time.monotonic())+delay
    except StopIteration:pass
    except Exception:
        report['error']=traceback.format_exc();save();u.log_error(report['error']);u.unregister_slate_post_tick_callback(handle);u.SystemLibrary.quit_editor()
    finally:busy=False
u.EditorPythonScripting.set_keep_python_script_alive(True);handle=u.register_slate_post_tick_callback(tick)
