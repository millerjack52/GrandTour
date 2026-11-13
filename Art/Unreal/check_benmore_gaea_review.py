"""Reload the review map, verify saved heights/grounding, capture static editor views.

No PIE, driving, performance suite or timing measurements.
"""
import unreal as u
from pathlib import Path
import array,hashlib,json,time,traceback
ROOT=Path(u.Paths.project_dir()).resolve();OUT=ROOT/'Art/Export/BenmoreGaea';DATA=OUT/'integration'
data=json.loads((DATA/'assets.json').read_text());install=json.loads((DATA/'unreal-import-report.json').read_text());assert install['ok']
LEVEL=install['level'];act=u.get_editor_subsystem(u.EditorActorSubsystem);les=u.get_editor_subsystem(u.LevelEditorSubsystem)
phase='load';started=time.monotonic();last=started;index=0;report={'ok':False,'level':LEVEL,'mode':'Static editor views; no driving or timing checks','views':[]}
u.EditorPythonScripting.set_keep_python_script_alive(True)


def finish(error=None):
    global phase
    phase='done';report['ok']=error is None
    if error:report['error']=error;u.log_error(error)
    report['source_map_unchanged']=hashlib.sha256((ROOT/'Content/GrandTour/Demo/BenmoreRoads/L_Benmore_Drive.umap').read_bytes()).hexdigest()==data['source_map_sha256']
    (DATA/'unreal-review-report.json').write_text(json.dumps(report,indent=2));u.unregister_slate_post_tick_callback(handle);u.SystemLibrary.quit_editor()


def tick(dt):
    global phase,last,index,world,land,rt,cameras,task
    now=time.monotonic()
    try:
        if now-started>650:raise RuntimeError('Bounded static Gaea review timed out')
        if phase=='load':
            phase='loading';assert les.load_level(LEVEL);world=u.get_editor_subsystem(u.UnrealEditorSubsystem).get_editor_world()
            actors=act.get_all_level_actors();land=next(a for a in actors if isinstance(a,u.Landscape))
            assert not any(a.get_actor_label().startswith(('Benmore_River_Bank_','Benmore_River_Surface_')) for a in actors)
            surface=next(a for a in actors if a.get_actor_label()=='Benmore_Gaea_CreekSurface');assert str(surface.static_mesh_component.get_collision_profile_name())=='NoCollision'
            for label,expected in install['road_dressing_after'].items():
                a=next(a for a in actors if a.get_actor_label()==label)
                assert sum(c.get_instance_count() for c in a.get_components_by_class(u.InstancedStaticMeshComponent))==expected[0]
            cameras=[next(a for a in actors if a.get_actor_label()=='Benmore_Gaea_Camera_'+r['name']) for r in data['cameras']]
            rt=u.RenderingLibrary.create_render_target2d(world,2017,2017,u.TextureRenderTargetFormat.RTF_RGBA8)
            phase='warm';last=now
        elif phase=='warm' and now-last>15:
            phase='exporting';assert land.landscape_export_heightmap_to_render_target(rt,True,True);phase='verify';last=now
        elif phase=='verify' and now-last>10:
            phase='verifying';assert land.landscape_export_heightmap_to_render_target(rt,True,True)
            pixels=u.RenderingLibrary.read_render_target(world,rt,False);values=array.array('H',((int(c.r)<<8)|int(c.g) for c in pixels));del pixels
            digest=hashlib.sha256(values.tobytes()).hexdigest();assert digest==data['height_sha256']
            report['saved_height_sha256']=digest;report['all_saved_height_samples_exact']=True
            ignore=[a for a in act.get_all_level_actors() if not isinstance(a,u.LandscapeProxy)];errors=[]
            for x,y,z,gap in json.loads((DATA/'support-samples.json').read_text())[::3]:
                hit=u.SystemLibrary.line_trace_single(world,u.Vector(x,y,z+20000),u.Vector(x,y,z-20000),u.TraceTypeQuery.TRACE_TYPE_QUERY1,True,ignore,u.DrawDebugTrace.NONE,True);assert hit is not None
                actual=[v for v in hit.to_tuple() if isinstance(v,u.Vector)][0].z;errors.append(abs(actual-z)/100)
            assert errors and max(errors)<.05
            report['saved_collision_support']={'samples':len(errors),'max_error_m':max(errors)}
            phase='view'
        elif phase=='view':
            camera=cameras[index]
            u.get_editor_subsystem(u.UnrealEditorSubsystem).set_level_viewport_camera_info(camera.get_actor_location(),camera.get_actor_rotation())
            u.SystemLibrary.execute_console_command(world,'grass.FlushCache');phase='grow';last=now
        elif phase=='grow' and now-last>35:
            phase='capturing';path=DATA/(data['cameras'][index]['name']+'.png')
            task=u.AutomationLibrary.take_high_res_screenshot(1440,900,str(path),cameras[index])
            report['views'].append({'image':str(path),'camera':data['cameras'][index]['name'],'visually_reviewed':False})
            phase='shot';last=now
        elif phase=='shot' and now-last>6:
            path=Path(report['views'][-1]['image'])
            if not path.exists() or path.stat().st_size<1000:
                if now-last<35:return
                raise RuntimeError('Static editor screenshot was not written: '+str(path))
            index+=1
            if index==len(cameras):finish()
            else:phase='view'
    except Exception:finish(traceback.format_exc())


handle=u.register_slate_post_tick_callback(tick)
