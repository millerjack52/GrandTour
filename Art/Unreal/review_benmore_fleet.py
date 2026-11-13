"""Fresh-process persistence checks and three rendered fleet views; no map writes."""
import unreal as u,json,time,traceback,hashlib
from pathlib import Path
OUT=Path('C:/GrandTour/Art/Export/BenmoreFleet')
saved=json.loads((OUT/'placement-report.json').read_text());assert saved['ok']
MAP=saved['map'];UE=u.get_editor_subsystem(u.UnrealEditorSubsystem)
LES=u.get_editor_subsystem(u.LevelEditorSubsystem);ACT=u.get_editor_subsystem(u.EditorActorSubsystem)
report={'ok':False,'images':[]};phase='load';last=time.monotonic();started=last;index=0
LC_ONLY='-GTFleetLCOnly' in u.SystemLibrary.get_command_line()
u.EditorPythonScripting.set_keep_python_script_alive(True)
def finish(error=None):
    report['ok']=error is None
    if error:report['error']=error;u.log_error(error)
    (OUT/('landcruiser-review-report.json' if LC_ONLY else 'review-report.json')).write_text(json.dumps(report,indent=2))
    u.unregister_slate_post_tick_callback(handle)
    u.SystemLibrary.quit_editor()
def tick(dt):
    global phase,last,world,views,index,camera,task
    now=time.monotonic()
    try:
        if now-started>420:raise RuntimeError('Fleet review timeout')
        if phase=='load':
            phase='loading';assert LES.load_level(MAP)
            world=UE.get_editor_world();actors=ACT.get_all_level_actors();by_label={a.get_actor_label():a for a in actors}
            assert len(actors)==saved['saved_actor_count']
            for row in saved['cars']:
                a=by_label[row['label']]
                assert a.get_class().get_path_name()==row['class']
                assert max(abs(x-y) for x,y in zip(a.get_actor_location().to_tuple(),row['location']))<.01
                assert len(a.get_components_by_class(u.MeshComponent))>=row['mesh_components']
            report['reopened_cars']=len(saved['cars'])
            originals={a.get_path_name():a for a in actors}
            for path,row in saved['original_actors'].items():
                a=originals[path]
                assert a.get_actor_label()==row['label']
                assert max(abs(x-y) for x,y in zip(a.get_actor_location().to_tuple(),row['location']))<.01
                assert max(abs(x-y) for x,y in zip(a.get_actor_rotation().to_tuple(),row['rotation']))<.01
            report['original_actors_unchanged']=len(saved['original_actors'])
            camera=by_label['Benmore_Fleet_Overview']
            views=[('FleetOverview',camera.get_actor_location(),camera.get_actor_rotation(),65)]
            for name in (['LandCruiser80'] if LC_ONLY else ['Ferrari288','Prado','Impreza2003']):
                a=by_label['Benmore_Fleet_'+name];p=a.get_actor_location()
                c=p+a.get_actor_forward_vector()*650-a.get_actor_right_vector()*600+u.Vector(0,0,360)
                views.append((name,c,u.MathLibrary.find_look_at_rotation(c,p+u.Vector(0,0,110)),55))
            u.SystemLibrary.execute_console_command(world,'t.MaxFPS 20')
            phase='view'
        elif phase=='view':
            name,pos,rot,fov=views[index]
            camera.set_actor_location(pos,False,False);camera.set_actor_rotation(rot,False);camera.camera_component.set_field_of_view(fov)
            UE.set_level_viewport_camera_info(pos,rot)
            phase='warm';last=now
        elif phase=='warm' and now-last>25:
            path=OUT/(views[index][0]+'.png')
            task=u.AutomationLibrary.take_high_res_screenshot(1440,900,str(path),camera)
            phase='shot';last=now
        elif phase=='shot' and now-last>4:
            path=OUT/(views[index][0]+'.png')
            if not path.exists():
                if now-last<30:return
                raise RuntimeError('Screenshot not written '+str(path))
            report['images'].append(str(path));index+=1
            if index==len(views):
                current=Path('C:/GrandTour/Content/GrandTour/Demo/BenmoreRoads/Gaea/L_Benmore_GaeaReview.umap')
                assert hashlib.sha256(current.read_bytes()).hexdigest()==saved['saved_sha256']
                finish()
            else:phase='view'
    except Exception:finish(traceback.format_exc())
handle=u.register_slate_post_tick_callback(tick)
