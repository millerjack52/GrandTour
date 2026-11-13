"""Append an inactive, cheaper distance LOD to the five audited heavy vehicles.

Only mesh rendering data is saved. Imported LOD0-2, materials, skeleton and
physics bindings are checked. Automatic selection stays disabled for the new
LOD until an explicit visual/performance comparison approves its screen size.
Run in the sole editor after the rendering helper has been built.
"""
import unreal as u
import os,json,hashlib,shutil,traceback
from pathlib import Path

ROOT=Path(u.Paths.project_dir()).resolve()
OUT=Path(os.environ['GT_BENMORE_FLEET_LOD_OUT']).resolve()
assert OUT.parent==ROOT/'Art/Export/BenmoreGaea' and not OUT.exists()
OUT.mkdir()
report=dict(ok=False,promoted=False,assets=[],
            scope='Inactive LOD3 trial; imported near LODs and vehicle physics preserved')
editor=u.get_editor_subsystem(u.SkeletalMeshEditorSubsystem)
helper=u.GTRenderOptimisationLibrary
audit=json.loads((ROOT/'Art/Export/BenmoreGaea/VehicleAudit_20261011T072120941Z/install-report.json').read_text())
paths=sorted({r['mesh'].split('.')[0] for r in audit['vehicle_lod_audit']
              if len(r['lod_vertices'])==3 and r['lod_vertices'][-1]>=90000})
assert len(paths)==5


def write(): (OUT/'install-report.json').write_text(json.dumps(report,indent=2))
def sha(p): return hashlib.sha256(p.read_bytes()).hexdigest()
def snapshot(mesh):
    n=editor.get_lod_count(mesh)
    return dict(vertices=[editor.get_num_verts(mesh,i) for i in range(n)],
                sections=[editor.get_num_sections(mesh,i) for i in range(n)],
                screens=list(helper.get_skeletal_lod_screen_sizes(mesh)),
                skeleton=mesh.get_editor_property('skeleton').get_path_name(),
                physics=mesh.get_editor_property('physics_asset').get_path_name(),
                materials=[dict(slot=str(s.get_editor_property('material_slot_name')),imported=str(s.get_editor_property('imported_material_slot_name')),
                                material=s.get_editor_property('material_interface').get_path_name() if s.get_editor_property('material_interface') else None)
                           for s in mesh.get_editor_property('materials')])


try:
    assert not u.EditorLevelLibrary.get_game_world()
    for path in paths:
        mesh=u.load_asset(path)
        assert isinstance(mesh,u.SkeletalMesh)
        before=snapshot(mesh)
        assert len(before['vertices'])==3 and min(before['screens'])>0.000001
        file=(ROOT/'Content'/path.removeprefix('/Game/')).with_suffix('.uasset')
        backup=OUT/file.name
        assert not backup.exists()
        shutil.copy2(file,backup)
        row=dict(asset=path,file=str(file),backup=str(backup),before_sha256=sha(file),before=before,saved=False)
        report['assets'].append(row);write()
        # The engine's "add LOD" branch only creates new levels. It does not
        # regenerate imported levels when bRegenerateEvenIfImported is false.
        assert editor.regenerate_lod(mesh,4,False,False)
        assert helper.configure_generated_far_lod(mesh,3,20000,0.000001)
        assert editor.regenerate_lod(mesh,4,False,False)
        after=snapshot(mesh)
        row['after']=after;write()
        for name in ('vertices','sections','screens'):
            assert after[name][:3]==before[name],(path,name,'Imported LOD changed')
        for name in ('skeleton','physics','materials'):
            assert after[name]==before[name],(path,name,'Binding changed')
        assert 0<after['vertices'][3]<=40000 and after['vertices'][3]<before['vertices'][2]*.5
        assert u.EditorAssetLibrary.save_loaded_asset(mesh)
        row.update(saved=True,after=after,after_sha256=sha(file));write()
        u.log('BENMORE_FAR_LOD_TRIAL '+path+' '+str(after['vertices']))
    report['ok']=True
except Exception:
    report['error']=traceback.format_exc();u.log_error(report['error'])
finally:
    write()
    u.SystemLibrary.quit_editor()
