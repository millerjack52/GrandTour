import unreal as u,json,traceback
from pathlib import Path
ROOT=Path(u.Paths.project_dir()).resolve();OUT=ROOT/'Art/Export/BenmoreEnvironment';OUT.mkdir(exist_ok=True)
r={}
try:
    u.get_editor_subsystem(u.LevelEditorSubsystem).load_level('/Game/GrandTour/Demo/BenmoreRoads/L_Benmore_Drive')
    actors=u.get_editor_subsystem(u.EditorActorSubsystem).get_all_level_actors()
    r['actors']=[{'label':a.get_actor_label(),'class':a.get_class().get_name(),'location':str(a.get_actor_location())} for a in actors if any(x in a.get_class().get_name() for x in ['Light','Fog','Sky','Atmosphere'])]
    r['mesh_api']=str(getattr(u,'ProceduralMeshLibrary',None))
    r['meshes']={}
    for k in [1,2,3]:
        m=u.load_asset('/Game/GrandTour/Demo/BenmoreRoads/Scenery/SM_Benmore_Rock'+str(k))
        v,tri,n,uv,t=u.ProceduralMeshLibrary.get_section_from_static_mesh(m,0,0)
        r['meshes'][str(k)]={'vertices':[[p.x,p.y,p.z] for p in v],'triangles':list(tri)}
    r['normal_transform']=str(u.MaterialExpressionTransform.__doc__)
    r['transform_enums']=[x for x in dir(u) if 'MaterialVectorCoord' in x]
except Exception:r['error']=traceback.format_exc()
(OUT/'inspection.json').write_text(json.dumps(r));u.SystemLibrary.quit_editor()
