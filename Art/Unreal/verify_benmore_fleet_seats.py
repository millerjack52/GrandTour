import unreal as u,json,traceback
from pathlib import Path
OUT=Path('C:/GrandTour/Art/Export/BenmoreFleet/Driving')
MAP='/Game/GrandTour/Demo/BenmoreRoads/Gaea/L_Benmore_GaeaReview'
report={'ok':False,'cars':{}}
try:
    assert u.get_editor_subsystem(u.LevelEditorSubsystem).load_level(MAP)
    eyes={'Panda1990':[-19.44,-34.56,147.6],'Prado':[10,-42.5,193.5],'CraftedUtility':[0,-43,159],'Pathfinder2002':[0,40,146],'Impreza2003':[0,-41,136],'LandCruiser80':[-10,-43,162]}
    for a in u.get_editor_subsystem(u.EditorActorSubsystem).get_all_level_actors():
        name=a.get_actor_label().removeprefix('Benmore_Fleet_')
        if name not in eyes:continue
        bp=u.EditorAssetLibrary.load_asset('/Game/GrandTour/Vehicles/FleetDriving/'+name+'/BP_'+name+'_Fleet')
        cdo=u.get_default_object(bp.generated_class())
        report['cars'][name]={'cdo_eye':list(cdo.get_editor_property('driver_eye_offset').to_tuple()),'instance_eye':list(a.get_editor_property('driver_eye_offset').to_tuple())}
    report['ok']=True
except Exception:report['error']=traceback.format_exc()
(OUT/'seat-report.json').write_text(json.dumps(report,indent=2))
u.SystemLibrary.quit_editor()
