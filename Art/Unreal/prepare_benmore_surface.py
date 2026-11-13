"""Export the actual installed render surfaces without changing the map."""
import unreal as u
import sys,json,traceback
from pathlib import Path
ROOT=Path(u.Paths.project_dir()).resolve();sys.path.insert(0,str(ROOT/'Art/Unreal'))
import install_benmore_gaea_creek as s
OUT=ROOT/'Art/Export/BenmoreGaea/WaterSurface_20261011';OUT.mkdir(exist_ok=True)
r={'ok':False}
try:
    assert s.les.load_level(s.LEVEL)
    r['surfaces']=[]
    for label in ['Benmore_RL_Stream','Benmore_RL_Outlet']:
        c=s.refs()[label].static_mesh_component;m=c.static_mesh
        t=u.AssetExportTask();t.object=m;t.filename=str(OUT/(label+'.fbx'));t.automated=True;t.prompt=False
        t.exporter=u.StaticMeshExporterFBX();assert u.Exporter.run_asset_export_task(t)
        r['surfaces'].append(dict(label=label,mesh=m.get_path_name(),transform=list(c.get_world_location().to_tuple())))
    mat=u.load_asset('/Game/GrandTour/Demo/BenmoreRoads/Gaea/WaterDetail/M_GC_DomainRiver')
    for prop,name in [(u.MaterialProperty.MP_WORLD_POSITION_OFFSET,'vertex'),(u.MaterialProperty.MP_BASE_COLOR,'pixel')]:
        n=u.MaterialEditingLibrary.get_material_property_input_node(mat,prop)
        (OUT/(name+'.hlsl')).write_text(str(n.get_editor_property('code')))
    r['ok']=True
except Exception:r['error']=traceback.format_exc();u.log_error(r['error'])
(OUT/'prepare-report.json').write_text(json.dumps(r,indent=2))
u.SystemLibrary.quit_editor()
