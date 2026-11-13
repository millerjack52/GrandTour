"""Fixed-step editor water motion, without driving or frame-time collection.

The impulse exercises the real local field. Ambient-only frames are labelled
separately; neither sequence is evidence of vehicle interaction or performance.
"""
import unreal as u
import sys, json, time, traceback
from pathlib import Path
ROOT=Path(u.Paths.project_dir()).resolve()
sys.path.insert(0,str(ROOT/'Art/Unreal'))
import install_benmore_gaea_creek as shared
OUT=ROOT/'Art/Export/BenmoreGaea/FlowWaves';OUT.mkdir(exist_ok=True)
AFTER='-GTWavesAfter' in u.SystemLibrary.get_command_line()
SUFFIX='After' if AFTER else 'Before'
report=dict(ok=False,driving_tested=False,timings_collected=False,images=[],samples=[])
busy=False

def bind(sheet):
    components=[sheet.get_component_by_class(u.ProceduralMeshComponent)]+[a.static_mesh_component for a in sheet.get_editor_property('domain_surfaces')]
    return [c.get_material(0) for c in components if isinstance(c.get_material(0),u.MaterialInstanceDynamic)]

def shot(camera,name):
    path=OUT/(name+'_'+SUFFIX+'.png');requested=time.time()
    u.AutomationLibrary.take_high_res_screenshot(1280,800,str(path),camera);yield .5
    while not path.exists() or path.stat().st_mtime<requested:
        if time.time()-requested>60:raise RuntimeError('Screenshot timeout: '+str(path))
        yield 1
    report['images'].append(str(path))

def run():
    assert shared.les.load_level(shared.LEVEL)
    refs=shared.refs();sheet=refs['Benmore_RS_WaterDomain'];camera=refs['Benmore_RL_Camera_Ford']
    p=shared.crossings[0]['center_m'];focus=u.Vector2D(p[0]*100,p[1]*100)
    pos=u.Vector((p[0]+5)*100,(p[1]-6)*100,(shared.height(shared.after,p[0]+5,p[1]-6)+1.7)*100)
    target=u.Vector(p[0]*100,p[1]*100,p[2]*100)
    camera.set_actor_location(pos,False,False);camera.set_actor_rotation(u.MathLibrary.find_look_at_rotation(pos,target),False)
    u.get_editor_subsystem(u.UnrealEditorSubsystem).set_level_viewport_camera_info(pos,camera.get_actor_rotation())
    sheet.preview_water_at(focus,0,True);yield 30
    report['camera']={'position':pos.to_tuple(),'target':target.to_tuple(),'focus':focus.to_tuple()}
    sample_points=[u.Vector2D(focus.x+x*62.5,focus.y+y*62.5) for y in range(-8,9) for x in range(-8,9)]
    mean=[sheet.surface_cm_at(q) for q in sample_points]
    report['mean_flow_cmps']=sheet.flow_cm_per_s_at(focus).to_tuple()
    for mode,count in [('Ambient',60 if AFTER else 20),('Impulse',24)]:
        step=1/12 if AFTER and mode=='Ambient' else .25
        sheet.preview_water_at(focus,0,True)
        if mode=='Impulse':report['impulse_m3']=sheet.add_impulse(focus,140,4)
        for i in range(count):
            if i:sheet.preview_water_at(focus,step,False)
            phase=12+i*step
            if AFTER:sheet.preview_ambient_waves(phase)
            else:
                for m in bind(sheet):m.set_scalar_parameter_value('WaterTimeOverride',phase)
            delta=[sheet.surface_cm_at(q)-z for q,z in zip(sample_points,mean)]
            report['samples'].append(dict(mode=mode,time=i*step,min_cm=min(delta),max_cm=max(delta),rms_cm=(sum(d*d for d in delta)/len(delta))**.5))
            yield .25
            yield from shot(camera,mode+'%02d'%i)
    # Same clock on either side of a real 10 m recenter. No clock-animation claim.
    sheet.preview_water_at(focus,0,True)
    for i in range(2):
        if i:sheet.preview_water_at(u.Vector2D(focus.x+1000,focus.y),0,False)
        if AFTER:sheet.preview_ambient_waves(12)
        else:
            for m in bind(sheet):m.set_scalar_parameter_value('WaterTimeOverride',12)
        yield 1
        yield from shot(camera,'Shift%d'%i)
    if AFTER:
        # A shallow-angle pair exposes real silhouette/depth variation as well
        # as normal changes. This camera is temporary and never saved.
        z=sheet.surface_cm_at(focus)
        low=u.Vector(focus.x,focus.y,z+25)
        ahead=u.Vector(focus.x-516,focus.y-305,z+1)
        camera.set_actor_location(low,False,False)
        camera.set_actor_rotation(u.MathLibrary.find_look_at_rotation(low,ahead),False)
        sheet.preview_water_at(focus,0,True);sheet.preview_ambient_waves(12)
        for gain in [0,1]:
            for m in bind(sheet):m.set_scalar_parameter_value('AmbientGain',gain)
            yield 3
            yield from shot(camera,'Relief'+('On' if gain else 'Off'))
        camera.set_actor_location(pos,False,False)
        camera.set_actor_rotation(u.MathLibrary.find_look_at_rotation(pos,target),False)
        # Put the replacement boundary across the inspected ford, then move it
        # one block. Ambient phase must remain world-anchored on both surfaces.
        for i in range(2):
            sheet.preview_water_at(u.Vector2D(focus.x+2000+i*1000,focus.y),0,True)
            sheet.preview_ambient_waves(12);yield 1
            yield from shot(camera,'Join%d'%i)
        # Non-driving views of the same material at an inner bar, in the long
        # reach and on the lake. Static/editor previews only, no frame timings.
        for name,pos,target,at in [v for v in shared.views() if v[0] in ['Reach','BarGround']]:
            camera.set_actor_location(u.Vector(*pos),False,False)
            camera.set_actor_rotation(u.MathLibrary.find_look_at_rotation(u.Vector(*pos),u.Vector(*target)),False)
            sheet.preview_water_at(u.Vector2D(*at),0,True);sheet.preview_ambient_waves(12);yield 12
            yield from shot(camera,name)
        pos=u.Vector(-166150,-3100,330);target=u.Vector(-166800,-2700,60)
        camera.set_actor_location(pos,False,False);camera.set_actor_rotation(u.MathLibrary.find_look_at_rotation(pos,target),False)
        sheet.preview_water_at(u.Vector2D(-166800,-2700),0,True);sheet.preview_ambient_waves(12);yield 12
        yield from shot(camera,'Lake')
    report['ok']=True

def finish(error=None):
    global gen
    gen=None
    if error:report['error']=error;report['ok']=False;u.log_error(error)
    (OUT/('motion-'+SUFFIX.lower()+'.json')).write_text(json.dumps(report,indent=2))
    u.unregister_slate_post_tick_callback(handle);u.SystemLibrary.quit_editor()

def tick(dt):
    global busy,next_at
    if busy:return
    try:
        if time.monotonic()-started>700:raise RuntimeError('Motion review timeout')
        if time.monotonic()<next_at:return
        busy=True;next_at=time.monotonic()+next(gen)
    except StopIteration:finish()
    except Exception:finish(traceback.format_exc())
    finally:busy=False

gen=run();started=time.monotonic();next_at=started
handle=u.register_slate_post_tick_callback(tick)
