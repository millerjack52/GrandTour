"""Recover the accepted baseline from the untouched clone made before the setup edits."""
import unreal as u
import json,time,shutil,traceback
from pathlib import Path
root=Path(u.Paths.project_dir()).resolve();out=root/'Art/Export/MudWaterShared'
report=dict(ok=False)
les=u.get_editor_subsystem(u.LevelEditorSubsystem);actors=u.get_editor_subsystem(u.EditorActorSubsystem)
try:
    assert les.load_level('/Game/GrandTour/ArtTests/MudWater/L_MudWater')
    found=actors.get_all_level_actors()
    assert not any(isinstance(a,u.GTWaterSheet) for a in found),'Recovery clone already changed'
    s=next(a for a in found if isinstance(a,u.GTLandscapeSurface))
    assert s.puddle_surface and not s.simulated_water and s.layer_depth_scale==1 and s.bearing_strength==1
    backup=root/'Saved/MudWaterRepair'/str(time.time_ns());backup.mkdir(parents=True)
    for relative in ['MudProvingGround/L_MudProvingGround.umap','MudWater/L_MudWater.umap']:
        shutil.copy2(root/'Content/GrandTour/ArtTests'/relative,backup/Path(relative).name)
    pool_transform=s.puddle_surface.get_actor_transform()
    pool_mesh=s.puddle_surface.static_mesh_component.static_mesh
    pool_material=s.puddle_surface.static_mesh_component.get_material(0)
    expected_land_material=s.landscape.landscape_material.get_path_name()
    found=s=None
    assert les.load_level('/Game/GrandTour/ArtTests/MudProvingGround/L_MudProvingGround')
    s=next(a for a in actors.get_all_level_actors() if isinstance(a,u.GTLandscapeSurface))
    s.set_editor_property('simulated_water',None)
    for a in list(actors.get_all_level_actors()):
        if a.get_actor_label()=='MudWater_SharedPond':actors.destroy_actor(a)
    pool=actors.spawn_actor_from_class(u.StaticMeshActor,u.Vector(0,0,-4.509804))
    pool.set_actor_label('ProvingGround_ConnectedWater');pool.set_actor_transform(pool_transform,False,True)
    c=pool.static_mesh_component;c.set_static_mesh(pool_mesh);c.set_material(0,pool_material)
    c.set_collision_enabled(u.CollisionEnabled.NO_COLLISION);c.set_cast_shadow(False)
    s.set_editor_property('puddle_surface',pool)
    assert s.layer_depth_scale==1 and s.bearing_strength==1 and s.landscape.landscape_material.get_path_name()==expected_land_material
    assert not any(isinstance(a,u.GTWaterSheet) for a in actors.get_all_level_actors())
    assert les.save_current_level()
    report.update(ok=True,backup=str(backup),recovered_from='Untouched pre-edit L_MudWater pool transform, mesh and material; removed only the added water actor and links',depth=s.layer_depth_scale,bearing=s.bearing_strength)
except Exception:report['error']=traceback.format_exc();u.log_error(report['error'])
(out/'repair-report.json').write_text(json.dumps(report,indent=2))
found=s=world=pool=c=a=None
les.load_level('/Engine/Maps/Entry');u.SystemLibrary.collect_garbage();quit_at=time.monotonic()+5
def finish(dt):
    if time.monotonic()>=quit_at:u.unregister_slate_post_tick_callback(handle);u.SystemLibrary.quit_editor()
u.EditorPythonScripting.set_keep_python_script_alive(True);handle=u.register_slate_post_tick_callback(finish)
