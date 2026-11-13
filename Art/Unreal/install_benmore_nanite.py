"""Install a visually reviewed, measured Nanite grass stage with package backups.

Four shared grass meshes only. Source geometry, materials and conventional LODs
remain intact. No map, planting, water or vehicle setting is changed.
"""
import unreal as u
import os,json,hashlib,shutil,traceback
from pathlib import Path

ROOT=Path(u.Paths.project_dir()).resolve()
RUN=Path(os.environ['GT_BENMORE_NANITE_EVIDENCE']).resolve()
OUT=Path(os.environ['GT_BENMORE_NANITE_INSTALL_OUT']).resolve()
assert RUN.parent==ROOT/'Art/Export/BenmoreGaea/PerformanceRuns'
assert OUT.parent==ROOT/'Art/Export/BenmoreGaea' and not OUT.exists()
OUT.mkdir()
report=dict(ok=False,evidence=str(RUN),assets=[],scope='Four shared grass meshes; retain source geometry/materials/LODs')


def digest(path):return hashlib.sha256(path.read_bytes()).hexdigest()


def material_bindings(mesh):
    # UVChannelData is derived during the fallback build. Compare the authored
    # interfaces and slot identities, not transient UV density metadata.
    return [(m.get_editor_property('material_interface'),str(m.get_editor_property('material_slot_name')),
             str(m.get_editor_property('imported_material_slot_name')))
            for m in mesh.get_editor_property('static_materials')]


def run():
    assert not u.EditorLevelLibrary.get_game_world()
    evidence=json.loads((RUN/'profile-report.json').read_text())
    assert evidence['ok'] and evidence['candidate']['stage'] in ('foliage_nanite','foliage_nanite_plain')
    for name in ('changed-inputs.json','changed-content.json','external-load-invalid.json'):
        assert not (RUN/name).exists(),name
    improvements=[c['timings']['FrameTime']['median'] for c in evidence['isolation_comparisons']]
    assert improvements and all(c['saved_percent']>=5 and c['saved_ms']>abs(c['baseline_drift_ms']) for c in improvements)
    assert os.environ.get('GT_BENMORE_NANITE_VISUAL_REVIEW')==RUN.name
    voxel=evidence['candidate']['stage']=='foliage_nanite_volume'
    if voxel:
        assert (u.SystemLibrary.get_console_variable_int_value('r.Nanite.AllowVoxels') or
                u.SystemLibrary.get_console_variable_int_value('r.Nanite.Foliage'))
    metadata=json.loads((RUN/'manifest.json').read_text(encoding='utf-8-sig'))['content_metadata']
    known={line.split('|')[0].lower():line.split('|')[1:] for line in metadata}
    sm=u.get_editor_subsystem(u.StaticMeshEditorSubsystem)
    pending=[]
    assert len(evidence['candidate']['meshes'])==4
    for path in evidence['candidate']['meshes']:
        mesh=u.load_asset(path)
        assert mesh and not mesh.get_editor_property('nanite_settings').enabled
        assert sm.get_lod_count(mesh)==3
        file=ROOT/'Content'/(path.split('.')[0].removeprefix('/Game/')+'.uasset')
        prior=known[str(file).lower()]
        assert file.stat().st_size==int(prior[0])
        assert file.stat().st_mtime_ns//100+621355968000000000==int(prior[1]),'Package changed since capture'
        backup=OUT/file.name
        shutil.copy2(file,backup)
        item=dict(asset=path,file=str(file),backup=str(backup),before_sha256=digest(file),
                  vertices=[sm.get_number_verts(mesh,i) for i in range(3)],
                  screens=list(sm.get_lod_screen_sizes(mesh)),shape_preservation=evidence['candidate']['shape_preservation'])
        report['assets'].append(item)
        pending.append((mesh,item,material_bindings(mesh)))
    (OUT/'install-report.json').write_text(json.dumps(report,indent=2))
    for mesh,item,materials in pending:
        settings=mesh.get_editor_property('nanite_settings')
        settings.enabled=True
        settings.shape_preservation={'None':u.NaniteShapePreservation.NONE,'PreserveArea':u.NaniteShapePreservation.PRESERVE_AREA}[item['shape_preservation']]
        sm.set_nanite_settings(mesh,settings,True)
        assert mesh.get_editor_property('nanite_settings').enabled
        assert sm.get_lod_count(mesh)==3
        # GetNumberVerts reads render resources: Nanite rebuilds LOD0's fallback
        # representation, so those counts legitimately differ from source LOD0.
        # Only SetNaniteSettings is used; no source-geometry/LOD import or edit.
        item['nanite_render_vertices']=[sm.get_number_verts(mesh,i) for i in range(3)]
        # Nanite's fallback rebuild may also recompute conventional thresholds.
        # Keep the authored thresholds for platforms using those fallback LODs.
        assert sm.set_lod_screen_sizes(mesh,item['screens'])
        assert list(sm.get_lod_screen_sizes(mesh))==item['screens']
        assert material_bindings(mesh)==materials
    for mesh,item,_ in pending:
        assert u.EditorAssetLibrary.save_loaded_asset(mesh)
        item.update(saved=True,after_sha256=digest(Path(item['file'])))
        (OUT/'install-report.json').write_text(json.dumps(report,indent=2))
    report['ok']=True


try:run()
except Exception:
    report['error']=traceback.format_exc()
    u.log_error(report['error'])
finally:
    (OUT/'install-report.json').write_text(json.dumps(report,indent=2))
    u.SystemLibrary.quit_editor()
