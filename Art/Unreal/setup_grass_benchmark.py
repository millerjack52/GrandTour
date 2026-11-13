"""Two disposable benchmark copies; never modifies the style level itself."""
import unreal as u
from pathlib import Path
import json
base='/Game/GrandTour/ArtTests/RoadFordStyle/'
eal=u.EditorAssetLibrary
les=u.get_editor_subsystem(u.LevelEditorSubsystem)
act=u.get_editor_subsystem(u.EditorActorSubsystem)
report=[]
for enabled in [False,True]:
    dest=base+'L_GrassPerf_'+('On' if enabled else 'Off')
    # SaveMap creates a new package; loading the source anew restores the source state.
    assert les.load_level(base+'L_RoadFordStyle')
    world=u.get_editor_subsystem(u.UnrealEditorSubsystem).get_editor_world()
    world.get_world_settings().set_editor_property('default_game_mode',u.load_class(None,'/Script/Engine.GameModeBase'))
    count=0
    for actor in act.get_all_level_actors():
        if isinstance(actor,u.PlayerStart):
            actor.set_actor_location(u.Vector(700,-32,215),False,False)
            actor.set_actor_rotation(u.Rotator(pitch=-2,yaw=-2),False)
        for c in actor.get_components_by_class(u.InstancedStaticMeshComponent):
            if c.component_has_tag('GrassCoverage'):
                c.set_visibility(enabled,False)
                count+=c.get_instance_count()
    assert count>8000, 'Grass instances missing'
    assert u.EditorLoadingAndSavingUtils.save_map(world,dest)
    report.append(dict(level=dest,grass_visible=enabled,instances=count))
assert les.load_level(base+'L_RoadFordStyle')
(Path(u.Paths.project_dir())/'Art/Export/RoadFordStyle/grass-benchmark-maps.json').write_text(json.dumps(report,indent=2))
u.log('GRASS_BENCHMARK_MAPS_OK '+json.dumps(report))
