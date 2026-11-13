"""Save isolated Nanite willow candidates; never save original meshes/materials.

All candidate materials retain their graphs and add the Nanite usage flag. The
trial uses ordinary Nanite, with the four existing fallback LODs retained.
"""
import unreal as u
import os, json, hashlib, traceback
from pathlib import Path

ROOT = Path(u.Paths.project_dir()).resolve()
OUT = Path(os.environ['GT_BENMORE_WILLOW_TRIAL']).resolve()
assert OUT.parent == ROOT/'Art/Export/BenmoreGaea' and not OUT.exists()
OUT.mkdir()
DEST = '/Game/GrandTour/Demo/BenmoreRoads/PerformanceTrials/' + OUT.name
report = dict(ok=False, destination=DEST, meshes=[], materials=[], originals=[])
eal = u.EditorAssetLibrary
sm = u.get_editor_subsystem(u.StaticMeshEditorSubsystem)


def file_for(asset):
    return ROOT/'Content'/(asset.get_path_name().split('.')[0].removeprefix('/Game/')+'.uasset')


def protect(asset):
    file = file_for(asset)
    row = dict(asset=asset.get_path_name(), file=str(file),
               sha256=hashlib.sha256(file.read_bytes()).hexdigest())
    if row not in report['originals']: report['originals'].append(row)


def run():
    assert not u.EditorLevelLibrary.get_game_world()
    assert not eal.does_directory_exist(DEST), 'Trial destination already exists'
    materials = {}
    for variant in ('Young', 'Windswept', 'Weathered', 'Broad'):
        source = u.load_asset('/Game/GrandTour/Demo/BenmoreRoads/Scenery/SM_Willow_'+variant)
        assert source and not source.get_editor_property('nanite_settings').enabled
        assert sm.get_lod_count(source) == 4
        protect(source)
        screens = list(sm.get_lod_screen_sizes(source))
        clone = eal.duplicate_asset(source.get_path_name(), DEST+'/'+source.get_name()+'_Nanite')
        assert clone
        for index, slot in enumerate(source.get_editor_property('static_materials')):
            material = slot.get_editor_property('material_interface')
            assert isinstance(material, u.Material), 'Do not flatten material instances'
            key = material.get_path_name()
            if key not in materials:
                protect(material)
                candidate = eal.duplicate_asset(key, DEST+'/'+material.get_name())
                assert isinstance(candidate, u.Material)
                u.MaterialEditingLibrary.set_material_usage(candidate, u.MaterialUsage.MATUSAGE_NANITE)
                assert candidate.get_editor_property('used_with_nanite')
                assert len(u.MaterialEditingLibrary.get_material_expressions(candidate)) == len(u.MaterialEditingLibrary.get_material_expressions(material))
                assert eal.save_loaded_asset(candidate)
                materials[key] = candidate
                report['materials'].append(dict(source=key, candidate=candidate.get_path_name()))
            clone.set_material(index, materials[key])
        settings = clone.get_editor_property('nanite_settings')
        settings.enabled = True
        settings.shape_preservation = u.NaniteShapePreservation.NONE
        sm.set_nanite_settings(clone, settings, True)
        assert clone.get_editor_property('nanite_settings').enabled
        assert sm.get_lod_count(clone) == 4
        assert sm.set_lod_screen_sizes(clone, screens)
        assert list(sm.get_lod_screen_sizes(clone)) == screens
        assert sm.get_convex_collision_count(clone) == sm.get_convex_collision_count(source)
        assert eal.save_loaded_asset(clone)
        report['meshes'].append(dict(source=source.get_path_name(), candidate=clone.get_path_name(),
            source_vertices=[sm.get_number_verts(source,i) for i in range(4)],
            fallback_vertices=[sm.get_number_verts(clone,i) for i in range(4)], screens=screens))
        (OUT/'trial-report.json').write_text(json.dumps(report,indent=2))
    report['ok'] = True


try: run()
except Exception:
    report['error'] = traceback.format_exc()
    u.log_error(report['error'])
finally:
    for row in report['originals']:
        row['unchanged'] = hashlib.sha256(Path(row['file']).read_bytes()).hexdigest() == row['sha256']
        if not row['unchanged']: report['ok'] = False
    (OUT/'trial-report.json').write_text(json.dumps(report,indent=2))
    u.SystemLibrary.quit_editor()
