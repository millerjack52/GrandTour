"""Persist required Nanite shader usage on three already-Nanite scrub materials.

No graph, palette, mesh, planting, map or physics edits. Each package is backed
up immediately before its flag-only save; rollback must check the after hash.
"""
import unreal as u
import os,json,hashlib,shutil,traceback
from pathlib import Path

ROOT=Path(u.Paths.project_dir()).resolve()
OUT=Path(os.environ['GT_BENMORE_USAGE_OUT']).resolve()
assert OUT.parent==ROOT/'Art/Export/BenmoreGaea' and not OUT.exists()
OUT.mkdir()
report=dict(ok=False,scope='Persist Nanite usage on existing scrub materials',assets=[])


def sha(path):return hashlib.sha256(path.read_bytes()).hexdigest()


def graph(material):
    return [(n.get_name(),n.get_class().get_name(),n.get_editor_property('code')
             if isinstance(n,u.MaterialExpressionCustom) else None)
            for n in u.MaterialEditingLibrary.get_material_expressions(material)]


try:
    assert not u.EditorLevelLibrary.get_game_world()
    # Record the separately logged Ferrari skeletal-usage issue without making
    # assumptions from authoring scripts or changing unrelated paint materials.
    ferrari=u.load_asset('/Game/GrandTour/Vehicles/Ferrari288Good/SK_Ferrari288')
    report['ferrari_material_audit']=[]
    if ferrari:
        for slot in ferrari.get_editor_property('materials'):
            base=slot.get_editor_property('material_interface')
            while isinstance(base,u.MaterialInstance):base=base.get_editor_property('parent')
            if isinstance(base,u.Material):
                report['ferrari_material_audit'].append(dict(material=base.get_path_name(),
                    skeletal_usage=base.get_editor_property('used_with_skeletal_mesh')))
    pending=[]
    for i in range(3):
        path=f'/Game/GrandTour/Demo/BenmoreRoads/Character/M_Benmore_ScrubLeaf{i}'
        material=u.load_asset(path)
        assert isinstance(material,u.Material)
        file=ROOT/'Content'/(path.removeprefix('/Game/')+'.uasset')
        backup=OUT/file.name
        shutil.copy2(file,backup)
        row=dict(asset=path,file=str(file),backup=str(backup),before_sha256=sha(file),
                 used_with_nanite_before=material.get_editor_property('used_with_nanite'))
        report['assets'].append(row)
        pending.append((material,row,graph(material)))
    (OUT/'install-report.json').write_text(json.dumps(report,indent=2))
    for material,row,original in pending:
        u.MaterialEditingLibrary.set_material_usage(material,u.MaterialUsage.MATUSAGE_NANITE)
        assert material.get_editor_property('used_with_nanite')
        assert graph(material)==original
        assert u.EditorAssetLibrary.save_loaded_asset(material)
        row.update(saved=True,after_sha256=sha(Path(row['file'])))
        (OUT/'install-report.json').write_text(json.dumps(report,indent=2))
    report['ok']=True
except Exception:
    report['error']=traceback.format_exc()
    u.log_error(report['error'])
finally:
    (OUT/'install-report.json').write_text(json.dumps(report,indent=2))
    u.SystemLibrary.quit_editor()
