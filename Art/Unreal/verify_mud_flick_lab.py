"""Fresh commandlet read of saved maps/assets, including the repaired source map."""
import json
import traceback
from pathlib import Path
import unreal as u

ROOT = Path(u.Paths.project_dir()).resolve()
OUT = ROOT / 'Art/Export/DustLab'
report = {'ok': False}


def world_actors(world):
    prefix = world.get_path_name() + ':PersistentLevel.'
    # Package-loaded worlds in a commandlet have no initialized level collection;
    # inspect their serialized actors rather than the gameplay actor iterator.
    return [a for a in u.ObjectIterator(u.Actor) if a.get_path_name().startswith(prefix)]


def inventory(world):
    rows = []
    for actor in world_actors(world):
        if isinstance(actor, u.GTMudFlickLab):
            continue
        label = actor.get_actor_label().replace('L_MudDrive', 'LEVEL').replace('L_MudFlickLab', 'LEVEL')
        p, r, s = actor.get_actor_location(), actor.get_actor_rotation(), actor.get_actor_scale3d()
        meshes = []
        for c in actor.get_components_by_class(u.StaticMeshComponent):
            mesh = c.get_editor_property('static_mesh')
            meshes.append([mesh.get_path_name() if mesh else None,
                           [c.get_material(i).get_path_name() if c.get_material(i) else None for i in range(c.get_num_materials())]])
        rows.append([actor.get_class().get_path_name(), label,
                     [round(v, 3) for v in (p.x, p.y, p.z, r.pitch, r.yaw, r.roll, s.x, s.y, s.z)], sorted(meshes, key=str)])
    return sorted(rows, key=str)


try:
    source = u.load_asset('/Game/GrandTour/ArtTests/LiveMudDrive/L_MudDrive')
    private = u.load_asset('/Game/GrandTour/ArtTests/DustLab/L_MudFlickLab')
    assert source and private
    source_labs = [a for a in world_actors(source) if isinstance(a, u.GTMudFlickLab)]
    private_labs = [a for a in world_actors(private) if isinstance(a, u.GTMudFlickLab)]
    report['source_prototype_actors'] = len(source_labs)
    report['private_prototype_actors'] = len(private_labs)
    assert len(source_labs) == 0 and len(private_labs) == 1
    source_rows, private_rows = inventory(source), inventory(private)
    assert len(source_rows) > 10, 'Source actor inventory did not load'
    report['source_actor_count'] = len(source_rows)
    report['private_baseline_actor_count'] = len(private_rows)
    report['baseline_actor_transforms_meshes_materials_match'] = source_rows == private_rows
    if source_rows != private_rows:
        report['source_only'] = [r for r in source_rows if r not in private_rows]
        report['private_only'] = [r for r in private_rows if r not in source_rows]
    assert source_rows == private_rows, 'Baseline actor inventory differs'
    system = private_labs[0].get_editor_property('mud_system')
    assert system and system.get_path_name().startswith('/Game/GrandTour/ArtTests/DustLab/')
    report['system'] = system.get_path_name()
    report['ok'] = True
except Exception:
    report['error'] = traceback.format_exc()
    u.log_error(report['error'])
finally:
    (OUT / 'mud-verify-report.json').write_text(json.dumps(report, indent=2))

