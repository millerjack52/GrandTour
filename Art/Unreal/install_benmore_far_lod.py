"""Install an evidenced extra far LOD; retain all three original LODs.

Four shared tussock mesh assets change, benefiting every map that uses them.
Run in the sole editor after reviewing the named candidate capture. Original
packages are copied to a fresh rollback directory before any source mutation.
No map, material, density, cull distance or vehicle parameter is edited.
"""
import unreal as u
import os,json,hashlib,shutil,traceback
from pathlib import Path
from benmore_far_tussock_trial import create_candidates

ROOT=Path(u.Paths.project_dir()).resolve()
RUN=Path(os.environ['GT_BENMORE_LOD_EVIDENCE']).resolve()
OUT=Path(os.environ['GT_BENMORE_LOD_INSTALL_OUT']).resolve()
assert RUN.parent==ROOT/'Art/Export/BenmoreGaea/PerformanceRuns'
assert OUT.parent==ROOT/'Art/Export/BenmoreGaea' and not OUT.exists()
OUT.mkdir()
report={'ok':False,'evidence':str(RUN),'scope':'Four shared tussock meshes; LOD0-2 retained; one added far LOD','assets':[]}


def digest(path):return hashlib.sha256(path.read_bytes()).hexdigest()


def run():
    assert not u.EditorLevelLibrary.get_game_world()
    evidence=json.loads((RUN/'profile-report.json').read_text())
    assert evidence['ok'] and evidence['candidate']['stage']=='foliage_far_lod'
    assert not (RUN/'changed-inputs.json').exists() and not (RUN/'changed-content.json').exists()
    assert not (RUN/'external-load-invalid.json').exists()
    improvements=[c['timings']['FrameTime']['median'] for c in evidence['isolation_comparisons']]
    assert improvements and all(c['saved_percent']>=5 and c['saved_ms']>abs(c['baseline_drift_ms']) for c in improvements), 'No repeatable far-LOD benefit established'
    assert os.environ.get('GT_BENMORE_LOD_VISUAL_REVIEW')==RUN.name, 'Review the named reference/candidate images before installing'
    rows=create_candidates(ROOT/'Art/Export/BenmoreGaea/FarTussockTrial_20261010_v2/manifest.json',
        '/Game/GrandTour/Demo/BenmoreRoads/PerformanceTrials/Install_'+OUT.name.replace('-','_'),
        screen_size=evidence['candidate']['far_lod_screen'])
    sm=u.get_editor_subsystem(u.StaticMeshEditorSubsystem)
    metadata=json.loads((RUN/'manifest.json').read_text(encoding='utf-8-sig'))['content_metadata']
    known={line.split('|')[0].lower():line.split('|')[1:] for line in metadata}
    # Back up and validate every original before modifying any of them.
    pending=[]
    for row in rows:
        original=u.load_asset(row['source'])
        file=ROOT/'Content'/(row['source'].split('.')[0].removeprefix('/Game/')+'.uasset')
        prior=known[str(file).lower()]
        assert file.stat().st_size==int(prior[0]), 'Source package changed since capture'
        assert file.stat().st_mtime_ns//100+621355968000000000==int(prior[1]), 'Source package timestamp changed since capture'
        backup=OUT/file.name
        shutil.copy2(file,backup)
        item=dict(asset=row['source'],file=str(file),backup=str(backup),before_sha256=digest(file),
                  near_vertices=row['near_lod_vertices'],screen_sizes=row['screen_sizes'])
        report['assets'].append(item)
        pending.append((original,row['candidate'],item))
    (OUT/'install-report.json').write_text(json.dumps(report,indent=2))
    for original,candidate,item in pending:
        assert sm.set_lod_from_static_mesh(original,3,candidate,3,True)==3
        assert sm.set_lod_screen_sizes(original,item['screen_sizes'])
        assert sm.get_lod_count(original)==4
        assert [sm.get_number_verts(original,i) for i in range(3)]==item['near_vertices']
        assert len(original.get_editor_property('static_materials'))==1
        assert original.get_material(0)==candidate.get_material(0)
        assert sm.get_lod_material_slot(original,3,0)==0
    for original,_,item in pending:
        assert u.EditorAssetLibrary.save_loaded_asset(original)
        item['after_sha256']=digest(Path(item['file']))
        item['saved']=True
        (OUT/'install-report.json').write_text(json.dumps(report,indent=2))
    report['ok']=True


try:run()
except Exception:
    report['error']=traceback.format_exc()
    u.log_error(report['error'])
finally:
    (OUT/'install-report.json').write_text(json.dumps(report,indent=2))
    u.SystemLibrary.quit_editor()
