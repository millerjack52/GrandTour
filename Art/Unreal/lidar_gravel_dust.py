"""GD1: enable existing bounded wheel dust in the actual LiDAR map.

Configuration is shared by the focused installer and full terrain installers.
No particle assets, traction, mud or water settings are modified.
"""
import unreal as u

INTENSITY = 1.2
LEVEL = '/Game/GrandTour/ArtTests/LidarStudy/L_LidarStudy'


def configure():
    actors = u.get_editor_subsystem(u.EditorActorSubsystem)
    rows = [a for a in actors.get_all_level_actors() if isinstance(a, u.GTVehicleSurfaceEffects)]
    assert len(rows) == 1, 'Expected one existing vehicle surface-effects coordinator'
    manager = rows[0]
    assert manager.dust_system, 'Existing dry-dust Niagara system is missing'
    manager.set_editor_property('bEnabled', True)
    manager.dust_intensity = INTENSITY
    # Legacy standalone fixtures must not add a second plume to the manager's.
    for a in actors.get_all_level_actors():
        if isinstance(a, u.GTDustLab):
            a.intensity = 0.
    return dict(version='gd1-1', intensity=INTENSITY, system=manager.dust_system.get_path_name(),
                mud_system=manager.mud_system.get_path_name() if manager.mud_system else None,
                mud_intensity=manager.mud_intensity)


def validate(world):
    rows = u.GameplayStatics.get_all_actors_of_class(world, u.GTVehicleSurfaceEffects)
    assert len(rows) == 1 and rows[0].dust_system and rows[0].get_editor_property('bEnabled')
    assert abs(rows[0].dust_intensity-INTENSITY) < .001


def main():
    import gc, json, math, os, shutil, time, traceback
    from pathlib import Path
    root = Path(u.Paths.project_dir()).resolve()
    out = root/'Saved/LidarAuthoringQA/GD1'; out.mkdir(parents=True, exist_ok=True)
    review = os.environ.get('GT_GRAVEL_DUST_REVIEW') == '1'
    mode = 'review' if review else 'install'
    report = dict(ok=False, mode=mode, samples=[], images=[])
    les = u.get_editor_subsystem(u.LevelEditorSubsystem)
    actors = u.get_editor_subsystem(u.EditorActorSubsystem)
    state = dict(world=None, car=None, lab=None, camera=None, pc=None, move=None)
    busy = False; deadline = 0.; began = time.monotonic()

    def save(): (out/(mode+'.json')).write_text(json.dumps(report, indent=2))
    def wait(seconds):
        start = u.GameplayStatics.get_time_seconds(state['world'])
        while u.GameplayStatics.get_time_seconds(state['world'])-start < seconds: yield .05
    def sample():
        car, lab = state['car'], state['lab']
        wheels = car.get_traction().wheels
        return dict(speed_kmh=car.get_velocity().length()*.036, rate=lab.total_rate,
                    live=lab.get_live_particles(), emitting=lab.emitting_wheels,
                    tags=[str(w.get_editor_property('SurfaceTag').get_editor_property('tag_name')) for w in wheels],
                    authored=[str(w.get_editor_property('AuthoredSurface')) for w in wheels],
                    wetness=[float(w.get_editor_property('GroundWetness')) for w in wheels],
                    mud=[bool(w.get_editor_property('bInMudPatch')) for w in wheels],
                    water=[float(w.get_editor_property('WaterDepthM')) for w in wheels])
    def view():
        car=state['car']; p=car.get_actor_location(); f=car.get_actor_forward_vector(); r=car.get_actor_right_vector()
        eye=p-f*1300+r*550+u.Vector(0,0,480)
        state['camera'].set_actor_location_and_rotation(eye,u.MathLibrary.find_look_at_rotation(eye,p-f*100),False,True)
    def capture(name):
        view(); world=state['world']; path=out/(name+'.png'); stamp=time.time()
        u.GameplayStatics.set_game_paused(world,True); yield .3
        u.SystemLibrary.execute_console_command(world,'HighResShot 1440x900 filename="'+path.as_posix()+'"',state['pc'])
        until=time.monotonic()+45
        while not path.exists() or path.stat().st_mtime<stamp:
            assert time.monotonic()<until; yield .2
        report['images'].append(dict(path=str(path),state=sample())); save()
        u.GameplayStatics.set_game_paused(world,False)

    def run():
        assert les.load_level(LEVEL); yield 2
        if not review:
            backup=root/'Saved/LidarAuthoringBackups'/('GD1-'+str(time.time_ns())); backup.mkdir(parents=True)
            shutil.copy2(root/'Content/GrandTour/ArtTests/LidarStudy/L_LidarStudy.umap',backup/'L_LidarStudy.umap')
            refs=actors.get_all_level_actors(); author=next(a for a in refs if isinstance(a,u.GTProceduralGround))
            digest=str(author.output_digest)
            manager=next(a for a in refs if isinstance(a,u.GTVehicleSurfaceEffects))
            oldmud=(manager.mud_system,manager.mud_intensity)
            report['before_intensity']=manager.dust_intensity
            report['configuration']=configure()
            assert oldmud==(manager.mud_system,manager.mud_intensity)
            assert str(author.output_digest)==digest
            assert les.save_current_level()
            refs=author=manager=oldmud=None;gc.collect();les.load_level('/Engine/Maps/Entry');yield 3
            assert les.load_level(LEVEL); yield 2
            validate(u.get_editor_subsystem(u.UnrealEditorSubsystem).get_editor_world())
            report.update(backup=str(backup),ground_digest=digest,mud_unchanged=True,reloaded=True)
        else:
            validate(u.get_editor_subsystem(u.UnrealEditorSubsystem).get_editor_world())
            les.editor_set_viewport_realtime(False)
            assert u.GTPlayWindowLibrary.request_play_in_new_window(1440,900)
            until=time.monotonic()+180
            while not state['world']:
                state['world']=u.EditorLevelLibrary.get_game_world();assert time.monotonic()<until;yield .2
            world=state['world']; pc=u.GameplayStatics.get_player_controller(world,0);car=pc.get_car()
            state.update(pc=pc,car=car,move=car.get_chaos_movement())
            pc.possess(car);car.disable_input(pc);car.reset_driving_inputs()
            move=state['move'];move.set_throttle_input(0);move.set_brake_input(0);move.set_handbrake_input(True)
            car.get_drivetrain().set_low_range(False)
            site=json.loads((root/'Art/Export/LidarStudy/Place/installed-sites.json').read_text())[0]
            points=next(r['points'] for r in json.loads((root/'Art/Export/LidarStudy/Place/roads.json').read_text()) if r['name']=='Riverside access')
            surface=u.GameplayStatics.get_all_actors_of_class(world,u.GTLandscapeSurface)[0]
            samples=[surface.sample_surface(u.Vector2D(*p)) for p in points]
            # Review a naturally dry 150 m of the existing road, rather than overriding
            # its authored moisture to make a cloud appear on wet ground.
            span=30
            eligible=[i for i in range(len(points)-span) if all(str(s.surface_tag)=='Gravel' and s.water_depth_cm<1 for s in samples[i:i+span])]
            assert eligible, 'No dry-gravel review corridor'
            index=min(eligible,key=lambda i:sum(s.wetness*s.wetness for s in samples[i:i+span]))
            x,y=points[index]; nxt=points[index+1]
            height=None
            for tile in u.GameplayStatics.get_all_actors_of_class(world,u.GTRoadReliefTile):
                origin=tile.get_actor_location()
                if origin.x<=x<origin.x+tile.span_cm and origin.y<=y<origin.y+tile.span_cm:
                    height=tile.height_at(u.Vector2D(x,y));break
            assert height is not None, 'Dry road has no runtime collision tile'
            site=dict(center=[x,y],center_height_cm=height,yaw=math.degrees(math.atan2(nxt[1]-y,nxt[0]-x)))
            report['dry_corridor']=dict(start_index=index,wetness=[s.wetness for s in samples[index:index+span]],site=site)
            surface=samples=tile=None
            x,y=site['center'];car.set_actor_location_and_rotation(u.Vector(x,y,site['center_height_cm']+100),u.Rotator(yaw=site['yaw']),False,True)
            body=car.get_component_by_class(u.SkeletalMeshComponent)
            body.set_physics_linear_velocity(u.Vector());body.set_physics_angular_velocity_in_degrees(u.Vector())
            for cmd in ['DisableAllScreenMessages','t.MaxFPS 60','t.IdleWhenNotForeground 0','Slate.bAllowThrottling 0','showhud']:
                u.SystemLibrary.execute_console_command(world,cmd,pc)
            camera=u.GTVehicleSetupLibrary.spawn_actor_of_class(world,u.CameraActor,u.Transform(),'GravelDustReview')
            camera.camera_component.set_constraint_aspect_ratio(False);camera.camera_component.set_field_of_view(65.)
            state['camera']=camera;pc.set_view_target_with_blend(camera,0);view()
            yield from wait(15)
            labs=[a for a in u.GameplayStatics.get_all_actors_of_class(world,u.GTDustLab) if a.target_car==car and a.intensity>0]
            assert len(labs)==1, 'Expected one active dust emitter for the selected car'
            lab=labs[0];state['lab']=lab
            report['idle']=sample();assert lab.total_rate<.01,report['idle']
            report['normal_weather_override']=lab.wetness_override
            move.set_handbrake_input(False)
            start=u.GameplayStatics.get_time_seconds(world); shot=0
            while u.GameplayStatics.get_time_seconds(world)-start<14:
                p=car.get_actor_location(); index=min(range(len(points)),key=lambda i:(points[i][0]-p.x)**2+(points[i][1]-p.y)**2)
                target=points[min(index+3,len(points)-1)]
                heading=math.degrees(math.atan2(target[1]-p.y,target[0]-p.x))
                err=(heading-car.get_actor_rotation().yaw+180)%360-180
                car.set_raw_steer(max(-.45,min(.45,err/28)))
                speed=car.get_velocity().length()/100
                move.set_throttle_input(max(.05,min(1.,.4+(12.-speed)*.3)))
                move.set_brake_input(.25 if speed>14. else 0.)
                view();report['samples'].append(sample())
                elapsed=u.GameplayStatics.get_time_seconds(world)-start
                if shot<2 and elapsed>(5 if shot==0 else 11):
                    yield from capture('GravelDust-'+str(shot));shot+=1
                yield .1
            assert max(s['live'] for s in report['samples'])>20, 'No live gravel dust on actual road'
            assert max(s['emitting'] for s in report['samples'])>=2, 'No grounded dusty wheels'
            report['peak_live']=max(s['live'] for s in report['samples'])
            # Transient review override, never saved: particles must stop spawning in wet conditions.
            lab.wetness_override=1.;yield from wait(.5)
            report['wet']=sample();assert lab.total_rate==0
            move.set_throttle_input(0);move.set_brake_input(1);move.set_handbrake_input(True)
            yield from wait(14)
            report['drained']=sample();assert lab.get_live_particles()==0
            report['legacy_dust_suppressed']=bool(car.get_spray().get_editor_property('bExternalDustEffects'))
            assert report['legacy_dust_suppressed']
            world=pc=car=move=body=camera=lab=labs=None
            for key in state:state[key]=None
            gc.collect();u.EditorLevelLibrary.editor_end_play();yield 4
            until=time.monotonic()+30
            while u.EditorLevelLibrary.get_game_world():assert time.monotonic()<until;yield .2
        assert les.load_level('/Engine/Maps/Entry');gc.collect();yield 4
        report['ok']=True;save()

    steps=run()
    def tick(dt):
        nonlocal busy,deadline,steps
        if busy:return
        busy=True
        try:
            assert time.monotonic()-began<900,'Gravel dust timeout'
            if time.monotonic()>=deadline:deadline=time.monotonic()+next(steps)
        except StopIteration:
            u.unregister_slate_post_tick_callback(handle);steps=None;gc.collect();u.SystemLibrary.quit_editor()
        except Exception:
            report.update(ok=False,error=traceback.format_exc());save();u.log_error(report['error'])
            u.unregister_slate_post_tick_callback(handle);u.SystemLibrary.quit_editor()
        finally:busy=False
    u.EditorPythonScripting.set_keep_python_script_alive(True)
    handle=u.register_slate_post_tick_callback(tick)


if __name__=='__main__':main()
