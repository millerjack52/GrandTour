"""Create unassigned mesh clones with one additional distant LOD.

Run only in the sole editor, before PIE. Does not load/save a map or edit the
approved mesh library. Clones remain unsaved for inspection by the caller.
"""
import hashlib
import json
from pathlib import Path, PurePosixPath

SOURCE_ROOT = '/Game/GrandTour/ArtTests/TussockStyle/'
TRIAL_ROOT = '/Game/GrandTour/Demo/BenmoreRoads/PerformanceTrials/'


def create_candidates(manifest_path, destination_root, screen_size=.008):
    import unreal as u

    if (not destination_root.startswith(TRIAL_ROOT) or
            '..' in PurePosixPath(destination_root).parts):
        raise ValueError('Use a fresh directory beneath PerformanceTrials')
    if not 0 < screen_size < .025:
        raise ValueError('The extra LOD must start beyond the existing far LOD')
    if u.EditorLevelLibrary.get_game_world():
        raise RuntimeError('Create candidate meshes before Play mode')
    manifest_file = Path(manifest_path).resolve()
    data = json.loads(manifest_file.read_text(encoding='utf-8-sig'))
    rows = data['models']
    assert sorted(r['variant'] for r in rows) == ['Fine', 'Rust', 'Straw', 'Weathered']
    eal = u.EditorAssetLibrary
    sm = u.get_editor_subsystem(u.StaticMeshEditorSubsystem)
    pending = []
    # Validate the entire input set before creating any clone.
    for row in rows:
        fbx = Path(row['fbx']).resolve()
        assert fbx.parent == manifest_file.parent and fbx.suffix.lower() == '.fbx'
        assert hashlib.sha256(fbx.read_bytes()).hexdigest() == row['fbx_sha256']
        assert row['lod'] == 3 and row['triangles'] == (24 if row['variant'] == 'Fine' else 48)
        source = u.load_asset(SOURCE_ROOT + 'SM_TS_' + row['variant'])
        assert source and sm.get_lod_count(source) == 3
        assert not source.get_editor_property('nanite_settings').enabled, 'This trial requires conventional mesh LODs'
        screens = list(sm.get_lod_screen_sizes(source))
        assert len(screens) == 3 and screen_size < screens[-1]
        vertices = [sm.get_number_verts(source, i) for i in range(3)]
        destination = destination_root.rstrip('/') + '/SM_TS_' + row['variant'] + '_FarLOD'
        assert not eal.does_asset_exist(destination), 'Refusing to overwrite an existing trial'
        pending.append((source, destination, fbx, screens, vertices))

    results = []
    for source, destination, fbx, screens, vertices in pending:
        clone = eal.duplicate_asset(source.get_path_name(), destination)
        assert clone
        assert sm.import_lod(clone, 3, str(fbx)) == 3
        # FBX LOD import can append its exported material slot. This grass has
        # one section/material; remap that new section to the retained slot before
        # removing the unused imported slot. Near LOD section bindings stay intact.
        assert len(source.get_editor_property('static_materials')) == 1
        assert clone.get_num_sections(3) == 1
        sm.set_lod_material_slot(clone, 0, 3, 0)
        clone.set_editor_property('static_materials', source.get_editor_property('static_materials'))
        assert sm.get_lod_material_slot(clone, 3, 0) == 0
        assert sm.set_lod_screen_sizes(clone, screens + [screen_size])
        assert sm.get_lod_count(clone) == 4
        assert [sm.get_number_verts(clone, i) for i in range(3)] == vertices
        assert list(sm.get_lod_screen_sizes(clone))[:3] == screens
        assert clone.get_material(0) == source.get_material(0)
        assert len(clone.get_editor_property('static_materials')) == 1
        for lod in range(3):
            assert clone.get_num_sections(lod) == source.get_num_sections(lod)
            for section in range(source.get_num_sections(lod)):
                assert sm.get_lod_material_slot(clone, lod, section) == sm.get_lod_material_slot(source, lod, section)
        results.append({'source': source.get_path_name(), 'candidate': clone,
                        'screen_sizes': screens + [screen_size], 'near_lod_vertices': vertices})
    return results
