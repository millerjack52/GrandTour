"""Enable the measured additional vehicle LOD at distance, without rebuilding geometry."""
import unreal as u
import os,json,hashlib,shutil,traceback
from pathlib import Path

ROOT=Path(u.Paths.project_dir()).resolve()
OUT=Path(os.environ['GT_BENMORE_FLEET_LOD_OUT']).resolve()
EVIDENCE=Path(os.environ['GT_BENMORE_FLEET_LOD_EVIDENCE']).resolve()
TRIAL=ROOT/'Art/Export/BenmoreGaea/FleetLODTrial_20261011T080724682Z/install-report.json'
assert OUT.parent==ROOT/'Art/Export/BenmoreGaea' and not OUT.exists()
assert EVIDENCE.parent==ROOT/'Art/Export/BenmoreGaea/PerformanceRuns'
evidence=json.loads((EVIDENCE/'profile-report.json').read_text())
assert evidence['ok']
comparison=next(c for c in evidence['comparisons'] if c['feature']=='fleet_far_lod' and c['view']=='Vegetation')
assert comparison['timings']['FrameTime']['median']['exceeds_screening_threshold']
trial=json.loads(TRIAL.read_text());assert trial['ok'] and len(trial['assets'])==5
OUT.mkdir()
editor=u.get_editor_subsystem(u.SkeletalMeshEditorSubsystem)
helper=u.GTRenderOptimisationLibrary
report=dict(ok=False,promoted=False,assets=[],evidence=str(EVIDENCE),trial=str(TRIAL),screen_size=.20,
            visual_review='Full-size reference/candidate road images inspected; distant silhouettes and colours retained',
            scope='Automatic distance LOD only; 80 FPS not yet verified')


def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def write():(OUT/'install-report.json').write_text(json.dumps(report,indent=2))


try:
    assert not u.EditorLevelLibrary.get_game_world()
    # Check every package before changing the first one. A later shared edit
    # needs fresh review, not an automatic overwrite or automatic promotion.
    for row in trial['assets']:
        assert row['saved'] and sha(Path(row['file']))==row['after_sha256']
        assert sha(Path(row['backup']))==row['before_sha256']
    for old in trial['assets']:
        mesh=u.load_asset(old['asset']);before=old['after']
        assert list(helper.get_skeletal_lod_screen_sizes(mesh))==before['screens']
        backup=OUT/Path(old['file']).name
        # Rollback of this promotion restores the actual pre-trial package.
        shutil.copy2(old['backup'],backup)
        row=dict(asset=old['asset'],file=old['file'],backup=str(backup),before_sha256=old['before_sha256'],
                 trial_sha256=old['after_sha256'],before=old['before'],saved=False)
        report['assets'].append(row);write()
        settings=editor.get_lod_build_settings(mesh,3)
        assert helper.configure_generated_far_lod(mesh,3,20000,.20)
        # This supported API posts the editor change, updating render-data
        # screen thresholds. It keeps the existing geometry build settings.
        editor.set_lod_build_settings(mesh,3,settings)
        after=dict(vertices=[editor.get_num_verts(mesh,i) for i in range(4)],
                   sections=[editor.get_num_sections(mesh,i) for i in range(4)],
                   screens=list(helper.get_skeletal_lod_screen_sizes(mesh)))
        assert after['vertices']==before['vertices'] and after['sections']==before['sections']
        assert after['screens'][:3]==before['screens'][:3] and abs(after['screens'][3]-.20)<1e-6
        assert mesh.get_editor_property('skeleton').get_path_name()==before['skeleton']
        assert mesh.get_editor_property('physics_asset').get_path_name()==before['physics']
        materials=[dict(slot=str(s.get_editor_property('material_slot_name')),imported=str(s.get_editor_property('imported_material_slot_name')),
                        material=s.get_editor_property('material_interface').get_path_name() if s.get_editor_property('material_interface') else None)
                   for s in mesh.get_editor_property('materials')]
        assert materials==before['materials']
        assert u.EditorAssetLibrary.save_loaded_asset(mesh)
        row.update(saved=True,after=after,after_sha256=sha(Path(old['file'])));write()
    report.update(ok=True,promoted=True)
except Exception:
    report['error']=traceback.format_exc();u.log_error(report['error'])
finally:
    write();u.SystemLibrary.quit_editor()
