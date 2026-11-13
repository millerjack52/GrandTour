import unreal as u,json
from pathlib import Path
r={"ok":True};sm=u.get_editor_subsystem(u.StaticMeshEditorSubsystem);mel=u.MaterialEditingLibrary
for path in ['/Game/OWGame/Dev/DressingLab/Trees/SM_OWBeech','/Game/OWGame/Dev/DressingLab/Trees/SM_OWBirch','/Game/GrandTour/ArtTests/BenmoreWoodland/Forest/SM_Fir_0']:
 m=u.load_asset(path)
 if not m:continue
 r[path]=dict(lods=sm.get_lod_count(m),vertices=[sm.get_number_verts(m,i) for i in range(sm.get_lod_count(m))],materials=[s.material_interface.get_path_name() for s in m.static_materials],bounds=str(m.get_bounds()))
 for s in m.static_materials:
  a=s.material_interface
  if isinstance(a,u.MaterialInstanceConstant):r[a.get_path_name()]=dict(vectors=[str(v) for v in mel.get_vector_parameter_names(a)],scalars=[str(v) for v in mel.get_scalar_parameter_names(a)])
Path('C:/GrandTour/Art/Export/LidarStudy/Place/audit.json').write_text(json.dumps(r,indent=2));u.SystemLibrary.quit_editor()
