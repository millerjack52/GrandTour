"""Long-view lighting, atmospheric separation, sky and hillside geology."""
import unreal as u,sys,json,time,traceback
from pathlib import Path
ROOT=Path(u.Paths.project_dir()).resolve();OUT=ROOT/'Art/Export/BenmoreVistas';DEST='/Game/GrandTour/Demo/BenmoreRoads/Vistas'
sys.path.insert(0,str(ROOT/'Art/Unreal'))
from benmore_reference_surface import build
from benmore_bank_surface import backdrop_material
from benmore_character_sky import build as skybuild
les=u.get_editor_subsystem(u.LevelEditorSubsystem);act=u.get_editor_subsystem(u.EditorActorSubsystem);eal=u.EditorAssetLibrary
phase='load';last=time.monotonic();report={'ok':False};u.EditorPythonScripting.set_keep_python_script_alive(True)
def finish(err=None):
    global phase
    phase='done';report['ok']=err is None
    if err:report['error']=err;u.log_error(err)
    (OUT/'setup-report.json').write_text(json.dumps(report,indent=2));u.unregister_slate_post_tick_callback(handle);u.SystemLibrary.quit_editor()
def tick(dt):
    global phase,last
    try:
        if phase=='load':
            phase='working';assert les.load_level('/Game/GrandTour/Demo/BenmoreRoads/L_Benmore_Drive')
            world=u.get_editor_subsystem(u.UnrealEditorSubsystem).get_editor_world();eal.make_directory(DEST)
            if not eal.does_asset_exist('/Game/GrandTour/Demo/BenmoreRoads/L_Benmore_BeforeVistas'):assert u.EditorLoadingAndSavingUtils.save_map(world,'/Game/GrandTour/Demo/BenmoreRoads/L_Benmore_BeforeVistas')
            ground=u.load_asset('/Game/GrandTour/Demo/BenmoreRoads/Vegetation/M_Benmore_FullCover')
            for mat,name in [(ground,'M_BeforeVistas_Ground'),(u.load_asset('/Game/GrandTour/Demo/BenmoreRoads/Environment/M_Benmore_Backdrop'),'M_BeforeVistas_Backdrop'),(u.load_asset('/Game/GrandTour/Demo/BenmoreRoads/Character/M_Benmore_SoftSky'),'M_BeforeVistas_Sky')]:
                if not eal.does_asset_exist(DEST+'/'+name):assert eal.duplicate_asset(mat.get_path_name(),DEST+'/'+name)
            report['surface']=build(ground);assert not u.MaterialEditingLibrary.recompile_material(ground);eal.save_loaded_asset(ground);backdrop_material();report['sky']=skybuild()
            report['scene_before']={}
            for a in act.get_all_level_actors():
                if isinstance(a,u.DirectionalLight) and a.get_actor_label()=='Sun':
                    c=a.light_component;report['scene_before']['sun']={'rotation':str(a.get_actor_rotation()),'intensity':c.get_editor_property('intensity'),'source_angle':c.get_editor_property('light_source_angle'),'use_temperature':c.get_editor_property('use_temperature'),'temperature':c.get_editor_property('temperature')}
                    a.set_actor_rotation(u.Rotator(pitch=-27,yaw=-125),False);c.set_intensity(10.0);c.set_editor_property('light_source_angle',1.2);c.set_editor_property('use_temperature',True);c.set_temperature(6000)
                elif isinstance(a,u.SkyLight) and a.get_actor_label()=='Sky':
                    report['scene_before']['sky_intensity']=a.light_component.get_editor_property('intensity');a.light_component.set_intensity(1.1)
                elif a.get_actor_label()=='Benmore_DistanceHaze':
                    c=a.component;report['scene_before']['fog']={k:c.get_editor_property(k) for k in ['start_distance','fog_max_opacity','fog_height_falloff']}
                    c.set_editor_property('start_distance',80000.);c.set_editor_property('fog_max_opacity',.30)
            assert 'sun' in report['scene_before'] and 'fog' in report['scene_before']
            report['scene_after']={'sun_pitch':-27,'sun_yaw':-125,'sun_intensity':10,'sun_temperature':6000,'sky_intensity':1.1,'fog_start_m':800,'fog_max_opacity':.30}
            phase='warm';last=time.monotonic()
        elif phase=='warm' and time.monotonic()-last>40:
            phase='saving';assert les.save_current_level();finish()
    except Exception:finish(traceback.format_exc())
handle=u.register_slate_post_tick_callback(tick)
