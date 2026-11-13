"""Undo this chat's powertrain tuning after the user clarified the actual wheel-sinking fault."""
import unreal as u,json,traceback,hashlib
from pathlib import Path
ROOT=Path('C:/GrandTour');OUT=ROOT/'Art/Export/BenmoreFleet/FerrariGroundContact';OUT.mkdir(exist_ok=True)
OLD=json.loads((OUT.parent/'FerrariPower/before.json').read_text())['saved_instance']
report={'ok':False}
def restore(pawn):
    m=pawn.get_chaos_movement();m.modify();e=m.get_editor_property('engine_setup')
    for k,v in OLD['engine'].items():e.set_editor_property(k,v)
    curve=e.get_editor_property('torque_curve');curve.set_editor_property('external_curve',None);e.set_editor_property('torque_curve',curve);m.set_editor_property('engine_setup',e)
    t=m.get_editor_property('transmission_setup')
    for k,v in OLD['transmission'].items():t.set_editor_property(k,v)
    m.set_editor_property('transmission_setup',t);d=pawn.get_drivetrain();d.modify();d.set_editor_property('centre_split_front',OLD['split_front'])
try:
    bp=u.load_asset('/Game/GrandTour/Vehicles/Ferrari288Good/BP_Ferrari288');bp.modify();restore(u.get_default_object(bp.generated_class()));assert u.EditorAssetLibrary.save_loaded_asset(bp,False)
    les=u.get_editor_subsystem(u.LevelEditorSubsystem);assert les.load_level('/Game/GrandTour/Demo/BenmoreRoads/Gaea/L_Benmore_GaeaReview')
    a=next(a for a in u.get_editor_subsystem(u.EditorActorSubsystem).get_all_level_actors() if a.get_actor_label()=='Benmore_Fleet_Ferrari288');a.modify();restore(a);assert les.save_current_level()
    report['original_powertrain_restored']=OLD
    report['wheel_defaults']=[]
    for s in a.get_chaos_movement().get_editor_property('wheel_setups'):
        wc=u.get_default_object(s.get_editor_property('wheel_class'))
        report['wheel_defaults'].append({'bone':str(s.get_editor_property('bone_name')),'class':wc.get_class().get_path_name(),'offset':list(s.get_editor_property('additional_offset').to_tuple()),'settings':{k:str(wc.get_editor_property(k)) for k in ['wheel_radius','wheel_width','suspension_max_raise','suspension_max_drop','spring_rate','suspension_damping_ratio','suspension_smoothing','sweep_shape','offset']}})
    p=OUT.parent/'placement-report.json';r=json.loads(p.read_text());r['saved_sha256']=hashlib.sha256((ROOT/'Content/GrandTour/Demo/BenmoreRoads/Gaea/L_Benmore_GaeaReview.umap').read_bytes()).hexdigest();r['ferrari_power_tune_reverted']=True;p.write_text(json.dumps(r,indent=2))
    report['ok']=True
except Exception:report['error']=traceback.format_exc();u.log_error(report['error'])
(OUT/'restore-power-report.json').write_text(json.dumps(report,indent=2));u.SystemLibrary.quit_editor()
