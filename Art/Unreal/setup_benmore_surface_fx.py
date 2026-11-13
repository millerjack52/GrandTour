"""User-authorized Benmore integration: add one coordinator; keep existing actors intact."""
import json
import sys
import time
import traceback
from pathlib import Path
from datetime import datetime
import unreal as u

ROOT=Path(u.Paths.project_dir()).resolve()
OUT=ROOT/'Art/Export/DustLab'
sys.path.insert(0,str(ROOT/'Art/Unreal'))
from benmore_surface_fx_inventory import LEVEL, inventory
u.EditorPythonScripting.set_keep_python_script_alive(True)
report={'ok':False,'level':LEVEL}
levels=u.get_editor_subsystem(u.LevelEditorSubsystem)
eal=u.EditorAssetLibrary
try:
    backup=json.loads((OUT/'benmore-backup.json').read_text())
    assert Path(backup['backup'],'L_Benmore_GaeaReview.umap').exists(), 'No before-map backup'
    run='/Game/GrandTour/FX/VehicleSurface/Benmore_'+datetime.now().strftime('%Y%m%d_%H%M%S')
    dust_src=json.loads((OUT/'setup-report.json').read_text())['system'].split('.')[0]
    mud_src=json.loads((OUT/'mud-setup-report.json').read_text())['system'].split('.')[0]
    dust=eal.duplicate_asset(dust_src,run+'/NS_DryDust')
    mud=eal.duplicate_asset(mud_src,run+'/NS_MudFlick')
    assert dust and mud
    assert eal.save_loaded_asset(dust) and eal.save_loaded_asset(mud)
    assert levels.load_level(LEVEL)
    world=u.get_editor_subsystem(u.UnrealEditorSubsystem).get_editor_world()
    assert world.get_path_name().startswith(LEVEL+'.')
    before=inventory(world)
    baseline=OUT/'benmore-actors-before.json'
    if not baseline.exists(): baseline.write_text(json.dumps(before,indent=2))
    assert before==json.loads(baseline.read_text()),'Existing map actors changed since FX baseline'
    actors=u.get_editor_subsystem(u.EditorActorSubsystem)
    managers=[a for a in actors.get_all_level_actors() if isinstance(a,u.GTVehicleSurfaceEffects)]
    assert len(managers)<=1,'Multiple surface-effect coordinators'
    manager=managers[0] if managers else actors.spawn_actor_from_class(u.GTVehicleSurfaceEffects,u.Vector())
    manager.set_actor_label('Benmore_VehicleSurfaceEffects')
    manager.dust_system=dust; manager.mud_system=mud
    manager.dust_intensity=2.4; manager.mud_intensity=1.4
    assert inventory(world)==before,'Existing actors changed during install'
    report['baseline_actors']=len(before)
    report['cars']=sum(isinstance(a,u.GTCarPawn) for a in actors.get_all_level_actors())
    report['terrain_builders']=[a.get_actor_label() for a in actors.get_all_level_actors() if isinstance(a,u.GTTerrainBuilder)]
    wet=eal.load_asset('/Game/GrandTour/Demo/BenmoreRoads/Gaea/Surfaces/PM_Benmore_WetGround')
    if wet: report['wet_ground_tag']=str(wet.surface_tag.get_editor_property('tag_name'))
    assert levels.save_current_level()
    report.update(ok=True,dust=dust.get_path_name(),mud=mud.get_path_name(),backup=backup['backup'])
except Exception:
    report['error']=traceback.format_exc(); u.log_error(report['error'])
finally:
    (OUT/'benmore-setup-report.json').write_text(json.dumps(report,indent=2))
    for name in ('world','manager','managers','a'): globals().pop(name,None)
    quit_at=time.monotonic()+4.; quit_stage=0
    def quit_tick(dt):
        global quit_at,quit_stage
        if time.monotonic()<quit_at:return
        if quit_stage==0:
            levels.load_level('/Engine/Maps/Entry');quit_stage=1;quit_at=time.monotonic()+4.;return
        u.unregister_slate_post_tick_callback(quit_handle);u.SystemLibrary.quit_editor()
    quit_handle=u.register_slate_post_tick_callback(quit_tick)
