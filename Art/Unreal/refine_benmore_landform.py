import unreal as u,sys,json,traceback
from pathlib import Path
ROOT=Path(u.Paths.project_dir()).resolve();OUT=ROOT/'Art/Export/BenmoreEnvironment';sys.path.insert(0,str(ROOT/'Art/Unreal'))
from benmore_bank_surface import import_landform,backdrop_material
from benmore_reference_surface import build
r={'ok':False}
try:
    les=u.get_editor_subsystem(u.LevelEditorSubsystem);assert les.load_level('/Game/GrandTour/Demo/BenmoreRoads/L_Benmore_Drive')
    import_landform();m=u.load_asset('/Game/GrandTour/Demo/BenmoreRoads/Vegetation/M_Benmore_FullCover');r['surface']=build(m);assert not u.MaterialEditingLibrary.recompile_material(m);u.EditorAssetLibrary.save_loaded_asset(m)
    backdrop_material()
    for a in u.get_editor_subsystem(u.EditorActorSubsystem).get_all_level_actors():
        if a.get_actor_label()=='Benmore_RoadVergeDetail':
            for c in a.get_components_by_class(u.InstancedStaticMeshComponent):
                if c.get_editor_property('static_mesh').get_name().startswith('SM_GR_Stone'):
                    c.set_editor_property('cast_shadow',True);c.set_editor_property('cast_contact_shadow',True)
    assert les.save_current_level();r['ok']=True
except Exception:r['error']=traceback.format_exc();u.log_error(r['error'])
(OUT/'landform-setup-report.json').write_text(json.dumps(r,indent=2));u.SystemLibrary.quit_editor()
