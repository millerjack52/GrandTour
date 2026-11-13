import unreal as u,json,traceback
from pathlib import Path
root=Path(u.Paths.project_dir()).resolve();qa=root/'Saved/LidarAuthoringQA/LeafGeometry';qa.mkdir(parents=True,exist_ok=True)
sm=u.get_editor_subsystem(u.StaticMeshEditorSubsystem);rows=[]
for k in range(3):
 m=u.load_asset('/Game/GrandTour/ArtTests/LidarStudy/CanopyDepth/SM_CD_Canopy_'+str(k));b=m.get_bounds()
 rows.append(dict(kind=k,path=m.get_path_name(),screens=list(sm.get_lod_screen_sizes(m)),radius=b.sphere_radius,bounds=[b.origin.x,b.origin.y,b.origin.z,b.box_extent.x,b.box_extent.y,b.box_extent.z],triangles=[m.get_static_mesh_description(i).get_triangle_count() for i in range(sm.get_lod_count(m))],slots=[dict(name=str(s.material_slot_name),path=s.material_interface.get_path_name() if s.material_interface else '') for s in m.get_editor_property('static_materials')],section_slots=[[sm.get_lod_material_slot(m,l,j) for j in range(m.get_num_sections(l))] for l in range(sm.get_lod_count(m))]))
(qa/'audit.json').write_text(json.dumps(rows,indent=2));u.SystemLibrary.quit_editor()
