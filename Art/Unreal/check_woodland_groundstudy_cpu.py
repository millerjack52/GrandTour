"""NullRHI runtime validation while GPU rendering is unavailable. No driving."""
import unreal as u
from pathlib import Path
import json,time,traceback,re,math
OUT=Path(u.Paths.project_dir())/'Art/Export/BenmoreWoodland'
report=dict(ok=False,rendering_checked=False,driving_tested=False,sites={})
busy=False;world=None
def run():
    global world
    les=u.get_editor_subsystem(u.LevelEditorSubsystem)
    assert les.load_level('/Game/GrandTour/ArtTests/BenmoreWoodland/L_Benmore_Woodland')
    assert u.GTPlayWindowLibrary.request_play_in_new_window(640,400);yield 12
    world=u.EditorLevelLibrary.get_game_world();assert world
    pc=u.GameplayStatics.get_player_controller(world,0);car=u.GameplayStatics.get_player_pawn(world,0)
    surface=u.GameplayStatics.get_all_actors_of_class(world,u.GTLandscapeSurface)[0]
    assert surface.grass_is_visual_cover
    grass=next(a for a in u.GameplayStatics.get_all_actors_of_class(world,u.GTMixedGroundDetails) if a.generate_around_player)
    move=car.get_chaos_movement();remembered=None
    for index,site in enumerate(json.loads((OUT/'authoring.json').read_text())['sites'],1):
        pc.select_lane(index);car.disable_input(pc);move.set_handbrake_input(True);yield 5
        x,y=site['center'];q=surface.sample_surface(u.Vector2D(x,y))
        assert q.native_substance_response==(site['name']!='Ford')
        assert 0<grass.grass.get_instance_count()<18000
        report['sites'][site['name']]=dict(instances=grass.grass.get_instance_count(),native=q.native_substance_response,depth_cm=q.sinkage_cap_cm)
        if index==2:
            t=grass.grass.get_instance_transform(grass.grass.get_instance_count()//2,True);p=t.translation
            grass.apply_review_grass_contact(u.Vector2D(p.x,p.y),True);yield .2
            assert re.search(r'removed=[1-9]',grass.grass_report());remembered=[p.x,p.y]
        if index==3:
            candidates=[]
            for dx in range(-2400,2401,150):
                for dy in range(-2400,2401,150):
                    q=surface.sample_surface(u.Vector2D(x+dx,y+dy))
                    if q.grass_cover>.5 and q.sinkage_cap_cm>30 and q.native_substance_response:candidates.append((dx*dx+dy*dy,x+dx,y+dy,q))
            assert candidates
            _,px,py,q=min(candidates,key=lambda v:v[0]);before=q.surface_delta_cm
            for _ in range(12):
                surface.apply_review_soil_stroke(u.Vector2D(px-80,py),u.Vector2D(px+80,py),32,20,.4);yield .06
            after=surface.sample_surface(u.Vector2D(px,py));assert after.surface_delta_cm<before-.3
            report['covered_mud']=dict(point=[px,py],grass=q.grass_cover,depth_cm=q.sinkage_cap_cm,before_cm=before,after_cm=after.surface_delta_cm,native=True)
    pc.select_lane(2);car.disable_input(pc);move.set_handbrake_input(True);yield 4
    report['grass_return']=grass.grass_report();assert re.search(r'removed=[1-9]',report['grass_return'])
    # Cross a streaming boundary without driving, then return. A changed focus
    # must retain unique slots and the persistent removed state.
    p=car.get_actor_location();car.set_actor_location(p+u.Vector(500,0,0),False,True);yield 1
    coords=[]
    for i in range(grass.grass.get_instance_count()):
        t=grass.grass.get_instance_transform(i,True).translation;coords.append((round(t.x,2),round(t.y,2)))
    assert len(set(coords))==len(coords),'Recycled grass slots overlap'
    car.set_actor_location(p,False,True);yield 1
    assert re.search(r'removed=[1-9]',grass.grass_report())
    report['streaming_unique_instances']=len(coords)
    report['ok']=True
    yield from finish()
def finish():
    global world
    u.EditorLevelLibrary.editor_end_play();yield 3;world=None
    u.get_editor_subsystem(u.LevelEditorSubsystem).load_level('/Engine/Maps/Entry');yield 2
steps=run();deadline=0;started=time.monotonic();failed=False
def tick(dt):
    global busy,steps,deadline,failed
    if busy:return
    busy=True
    try:
        assert time.monotonic()-started<360,'CPU runtime check deadline'
        if time.monotonic()>=deadline:deadline=time.monotonic()+next(steps)
    except StopIteration:
        (OUT/'groundstudycpu.json').write_text(json.dumps(report,indent=2));u.unregister_slate_post_tick_callback(handle)
        steps=None;u.EditorPythonScripting.set_keep_python_script_alive(False)
    except Exception:
        report.update(ok=False,error=traceback.format_exc());u.log_error(report['error'])
        if failed:
            (OUT/'groundstudycpu.json').write_text(json.dumps(report,indent=2));u.SystemLibrary.quit_editor()
        else:failed=True;steps=finish();deadline=time.monotonic()+next(steps)
    finally:busy=False
u.EditorPythonScripting.set_keep_python_script_alive(True);handle=u.register_slate_post_tick_callback(tick)
