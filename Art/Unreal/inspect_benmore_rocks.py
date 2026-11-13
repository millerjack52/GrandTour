import unreal as u,json
from pathlib import Path
report=[];mel=u.MaterialEditingLibrary
for i in [1,2,3]:
    mesh=u.load_asset('/Game/GrandTour/Demo/BenmoreRoads/Scenery/SM_Benmore_Rock'+str(i))
    for slot in range(len(mesh.get_editor_property('static_materials'))):
        m=mesh.get_material(slot)
        report.append({'mesh':i,'slot':slot,'material':m.get_path_name(),'scalars':{str(n):mel.get_material_instance_scalar_parameter_value(m,n) for n in mel.get_scalar_parameter_names(m)},'vectors':{str(n):str(mel.get_material_instance_vector_parameter_value(m,n)) for n in mel.get_vector_parameter_names(m)}})
(Path(u.Paths.project_dir()).resolve()/'Art/Export/BenmoreScenery/rock-materials.json').write_text(json.dumps(report,indent=2))
u.SystemLibrary.quit_editor()
