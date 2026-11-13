"""Unsaved runtime swaps for prepared willow trial assets, outside timed frames."""
import json, hashlib
from pathlib import Path
import unreal as u
from benmore_performance_stages import swap_mesh, component_count

bindings = []
details = {}
active = False


def prepare(world):
    if bindings: return
    root = Path(u.Paths.project_dir()).resolve()
    reports = sorted((root/'Art/Export/BenmoreGaea').glob('WillowTrial_*/trial-report.json'), reverse=True)
    assert reports, 'Prepare isolated willow assets before profiling'
    path = reports[0]
    report = json.loads(path.read_text())
    assert report['ok'] and len(report['meshes']) == 4, 'Latest willow preparation failed'
    for row in report['originals']:
        file = Path(row['file']).resolve()
        assert file.is_relative_to(root/'Content')
        assert hashlib.sha256(file.read_bytes()).hexdigest() == row['sha256'], 'Source changed since willow preparation'
    mesh_map = {row['source']: u.load_asset(row['candidate']) for row in report['meshes']}
    material_map = {row['source']: u.load_asset(row['candidate']) for row in report['materials']}
    assert all(mesh and mesh.get_editor_property('nanite_settings').enabled for mesh in mesh_map.values())
    assert all(mat and mat.get_editor_property('used_with_nanite') for mat in material_map.values())
    for actor in u.GameplayStatics.get_all_actors_of_class(world, u.Actor):
        for c in actor.get_components_by_class(u.StaticMeshComponent):
            source = c.static_mesh
            if not source or source.get_path_name() not in mesh_map: continue
            assert not isinstance(c, u.GrassInstancedStaticMeshComponent), 'Generated grass needs a separate regeneration path'
            overrides = list(c.get_editor_property('override_materials'))
            replacement = []
            for material in overrides:
                assert not material or material.get_path_name() in material_map, 'Unknown willow material override'
                replacement.append(material_map[material.get_path_name()] if material else None)
            bindings.append((c, source, mesh_map[source.get_path_name()], overrides, replacement,
                             component_count(c), c.is_visible()))
    assert bindings and len({source.get_path_name() for _,source,*_ in bindings}) == 4
    details.update(report=str(path), bindings=[dict(component=c.get_path_name(), source=s.get_path_name(),
        candidate=n.get_path_name(), instances=count, visible=visible,
        actor_hidden=c.get_owner().get_editor_property('hidden'))
        for c,s,n,_,_,count,visible in bindings])


def verify():
    for c,source,candidate,original_overrides,candidate_overrides,count,visible in bindings:
        assert c.static_mesh == (candidate if active else source)
        assert list(c.get_editor_property('override_materials')) == (candidate_overrides if active else original_overrides)
        assert component_count(c) == count and c.is_visible() == visible, 'Willow count or visibility changed'


def get(world):
    prepare(world)
    verify()
    return float(active)


def set_value(value, world):
    global active
    assert value in (0,1)
    prepare(world)
    # Register every original before the first mutation, allowing a failed swap
    # to be restored by the profiler's normal finalisation path.
    for c,source,candidate,original_overrides,candidate_overrides,_,_ in bindings:
        c.set_editor_property('override_materials', candidate_overrides if value else original_overrides)
        # SetStaticMesh refreshes render state after both mesh and overrides
        # have changed. MarkRenderStateDirty is not a reflected Python API.
        swap_mesh(c, candidate if value else source)
    active = bool(value)
    verify()


def metadata():
    return details
