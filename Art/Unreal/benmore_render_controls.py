"""Reversible, unsaved render diagnostics for the exclusive Benmore profiler.

No vehicle simulation, assets or handling are changed. Hidden fleet/foliage
experiments are attribution only and must never become shipping settings.
"""
import unreal as u

BUNDLES = {
    # UE 5.8 Medium cache cadence only. Preserve gather, geometry and reflection
    # modes; this tests lighting refresh work separately from removing GI.
    'Diagnostic.LumenCacheUpdates': {
        'r.LumenScene.DirectLighting.UpdateFactor': 128,
        'r.LumenScene.Radiosity.UpdateFactor': 128,
    },
    # Opaque GI controls from UE 5.8 High. Keep hardware ray tracing, reflection
    # quality, surface-cache allocation and translucent water/spray unchanged.
    'Diagnostic.HighOpaqueGI': {
        'r.Lumen.ScreenProbeGather.DownsampleFactor': 32,
        'r.Lumen.ScreenProbeGather.RadianceCache.ProbeResolution': 16,
        'r.Lumen.ScreenProbeGather.RadianceCache.NumProbesToTraceBudget': 100,
        'r.Lumen.ScreenProbeGather.StochasticInterpolation': 1,
        'r.Lumen.ScreenProbeGather.IrradianceFormat': 1,
        'r.Lumen.ScreenProbeGather.ShortRangeAO.DownsampleFactor': 2,
        'r.Lumen.ScreenProbeGather.ShortRangeAO.BentNormal': 0,
        'r.Lumen.ScreenProbeGather.ShortRangeAO.HorizonSearch.HZB': 1,
    }
}
originals = {}
groups = {}
lod_components = []


def prepare(flag, world):
    if flag == 'Diagnostic.FleetFarLOD' and not lod_components:
        player=u.GameplayStatics.get_player_pawn(world,0)
        for actor in u.GameplayStatics.get_all_actors_of_class(world,u.GTCarPawn):
            if actor==player:continue
            for c in actor.get_components_by_class(u.SkeletalMeshComponent):
                mesh=c.get_skeletal_mesh_asset()
                if mesh and '/Vehicles/FleetDriving/' in mesh.get_path_name() and len(u.GTRenderOptimisationLibrary.get_skeletal_lod_screen_sizes(mesh))==4:
                    lod_components.append((c,c.get_forced_lod()))
        assert len(lod_components)==5,'Expected the five inactive fleet LOD trials'
    elif flag in BUNDLES and flag not in originals:
        originals[flag] = {f:u.SystemLibrary.get_console_variable_float_value(f)
                           for f in BUNDLES[flag]}
    elif flag == 'Diagnostic.ParkedFleetVisible' and flag not in groups:
        player=u.GameplayStatics.get_player_pawn(world,0)
        groups[flag]=[(a,not a.get_editor_property('hidden')) for a in
                      u.GameplayStatics.get_all_actors_of_class(world,u.GTCarPawn)
                      if a != player]
        assert any(v for _,v in groups[flag]), 'No visible parked fleet'
    elif flag == 'Diagnostic.AuthoredTussocksVisible' and flag not in groups:
        groups[flag]=[]
        for actor in u.GameplayStatics.get_all_actors_of_class(world,u.Actor):
            for c in actor.get_components_by_class(u.StaticMeshComponent):
                if isinstance(c,u.GrassInstancedStaticMeshComponent):continue
                if c.static_mesh and c.static_mesh.get_path_name().startswith(
                        '/Game/GrandTour/ArtTests/TussockStyle/SM_TS_'):
                    groups[flag].append((c,c.is_visible()))
        assert any(v for _,v in groups[flag]), 'No visible authored tussocks'
    elif flag == 'Diagnostic.WillowsVisible' and flag not in groups:
        groups[flag]=[(c,c.is_visible())
            for actor in u.GameplayStatics.get_all_actors_of_class(world,u.Actor)
            for c in actor.get_components_by_class(u.StaticMeshComponent)
            if c.static_mesh and '/Scenery/SM_Willow_' in c.static_mesh.get_path_name()]
        assert len({c.static_mesh.get_path_name() for c,_ in groups[flag]})==4,'Expected four willow families'
        assert any(v for _,v in groups[flag]),'No visible willows'


def visible(obj):
    return not obj.get_editor_property('hidden') if isinstance(obj,u.Actor) else obj.is_visible()


def get(flag, world):
    prepare(flag,world)
    if flag=='Diagnostic.FleetFarLOD':
        if all(c.get_forced_lod()==old for c,old in lod_components):return 0.
        assert all(c.get_forced_lod()==4 for c,_ in lod_components),'Partial fleet LOD override'
        return 1.
    if flag in BUNDLES:
        current={f:u.SystemLibrary.get_console_variable_float_value(f) for f in BUNDLES[flag]}
        if current==BUNDLES[flag]:return 1.
        assert current==originals[flag], 'Partial GI settings / competing override'
        return 0.
    if flag in groups:
        if all(visible(obj)==old for obj,old in groups[flag]):return 1.
        assert all(not visible(obj) for obj,_ in groups[flag]), 'Partial visibility override'
        return 0.
    raise ValueError(flag)


def set_value(flag,value,world,pc):
    prepare(flag,world)
    assert value in (0,1)
    if flag=='Diagnostic.FleetFarLOD':
        for c,old in lod_components:c.set_forced_lod(4 if value else old)
    elif flag in BUNDLES:
        for name,setting in (BUNDLES[flag] if value else originals[flag]).items():
            u.SystemLibrary.execute_console_command(world,name+' '+str(setting),pc)
    elif flag in groups:
        for obj,old in groups[flag]:
            show=old if value else False
            if isinstance(obj,u.Actor):obj.set_actor_hidden_in_game(not show)
            else:obj.set_visibility(show)
    else:raise ValueError(flag)
    assert get(flag,world)==value, 'Render diagnostic failed to apply/restore'


def metadata():
    return dict(original_bundles=originals,candidate_bundles=BUNDLES,
                fleet_lod_components=[dict(component=c.get_path_name(),original_forced_lod=old) for c,old in lod_components],
                visibility_groups={f:[dict(object=o.get_path_name(),visible=v,
                    mesh=o.static_mesh.get_path_name() if isinstance(o,u.StaticMeshComponent) and o.static_mesh else None,
                    instances=o.get_instance_count() if isinstance(o,u.InstancedStaticMeshComponent) else None) for o,v in rows]
                                   for f,rows in groups.items()})


def vehicle_lods(world):
    return [dict(actor=a.get_path_name(),mesh=c.get_skeletal_mesh_asset().get_path_name(),
                 predicted_lod=c.get_predicted_lod_level(),forced_lod=c.get_forced_lod())
            for a in u.GameplayStatics.get_all_actors_of_class(world,u.GTCarPawn)
            for c in a.get_components_by_class(u.SkeletalMeshComponent)
            if c.get_skeletal_mesh_asset()]
