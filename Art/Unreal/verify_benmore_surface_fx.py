"""Independent saved-map read after installation; no writes to assets."""
import json,sys,traceback
from pathlib import Path
import unreal as u
ROOT=Path(u.Paths.project_dir()).resolve();OUT=ROOT/'Art/Export/DustLab'
sys.path.insert(0,str(ROOT/'Art/Unreal'))
from benmore_surface_fx_inventory import LEVEL, inventory, actors_in
report={'ok':False}

def authored_rows(rows):
    result=[]
    for row in rows:
        # Renderer-only editor helpers, not authored scene content. Match their
        # exact type/assets so ordinary camera actors and meshes stay covered.
        if row[0]=='ChaosDebugDrawActor' and row[2]=='/Script/Engine.Actor' and not row[4]:continue
        meshes=[m for m in row[4] if not (m[0].startswith('CameraProxyMeshComponent_')
            and m[1]=='/Engine/EditorMeshes/MatineeCam_SM.MatineeCam_SM'
            and m[2]==['/Engine/EditorMaterials/MatineeCam_mat.MatineeCam_mat'])]
        result.append(row[:4]+[meshes])
    return result

try:
    # Match the initialized editor-world baseline. Loading only the package
    # leaves component world transforms at identity and omits editor helpers.
    assert u.get_editor_subsystem(u.LevelEditorSubsystem).load_level(LEVEL)
    world=u.get_editor_subsystem(u.UnrealEditorSubsystem).get_editor_world()
    assert world
    actors=actors_in(world)
    managers=[a for a in actors if isinstance(a,u.GTVehicleSurfaceEffects)]
    assert len(managers)==1
    baseline=json.loads((OUT/'benmore-actors-before.json').read_text())
    actual=inventory(world)
    (OUT/'benmore-actors-saved.json').write_text(json.dumps(actual,indent=2))
    before={row[0]:row for row in baseline};after={row[0]:row for row in actual}
    raw_differences=[{'name':name,'before':before.get(name),'after':after.get(name)}
        for name in sorted(before.keys()|after.keys()) if before.get(name)!=after.get(name)]
    (OUT/'benmore-editor-helper-differences.json').write_text(json.dumps(raw_differences,indent=2))
    report['editor_helper_difference_count']=len(raw_differences)
    assert authored_rows(actual)==authored_rows(baseline),'Existing authored actor inventory differs'
    install=json.loads((OUT/'benmore-setup-report.json').read_text())
    manager=managers[0]
    assert manager.dust_system.get_path_name()==install['dust']
    assert manager.mud_system.get_path_name()==install['mud']
    report.update(ok=True,baseline_actors=len(baseline),compared_actors=len(authored_rows(baseline)),coordinators=1,
                  dust=manager.dust_system.get_path_name(),mud=manager.mud_system.get_path_name())
except Exception:
    report['error']=traceback.format_exc();u.log_error(report['error'])
finally:
    (OUT/'benmore-verify-report.json').write_text(json.dumps(report,indent=2))
