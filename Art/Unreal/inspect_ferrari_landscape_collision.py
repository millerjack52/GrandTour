import unreal as u,json,traceback
from pathlib import Path
r={}
try:
    assert u.get_editor_subsystem(u.LevelEditorSubsystem).load_level('/Game/GrandTour/Demo/BenmoreRoads/Gaea/L_Benmore_GaeaReview')
    a=next(a for a in u.get_editor_subsystem(u.EditorActorSubsystem).get_all_level_actors() if isinstance(a,u.LandscapeProxy))
    r['default']=str(a.get_editor_property('default_phys_material'))
    r['collision']=[]
    for c in a.get_components_by_class(u.LandscapeHeightfieldCollisionComponent):
        row={}
        for p in ['component_layer_infos','physical_material_render_objects','cooked_physical_materials']:
            row[p]=[str(v) for v in c.get_editor_property(p)]
        r['collision'].append(row)
    r['material']=str(a.get_editor_property('landscape_material').get_editor_property('phys_material'))
except Exception:r['error']=traceback.format_exc()
Path('C:/GrandTour/Art/Export/BenmoreFleet/FerrariGroundContact/collision.json').write_text(json.dumps(r,indent=2))
u.SystemLibrary.quit_editor()
