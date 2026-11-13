"""Export read-only saved LiDAR response samples and material programs."""
import unreal as u,json,sys,traceback,time
from pathlib import Path
R=Path('C:/GrandTour');O=R/'Art/Export/FloraDrive/LidarMud';O.mkdir(parents=True,exist_ok=True)
sys.path.insert(0,str(R/'Art/Unreal'));import lidar_logging_trial as trial
report={'ok':False}
try:
    assert u.get_editor_subsystem(u.LevelEditorSubsystem).load_level('/Game/GrandTour/ArtTests/LidarStudy/L_LidarStudy')
    aa=u.get_editor_subsystem(u.EditorActorSubsystem).get_all_level_actors();s=next(a for a in aa if isinstance(a,u.GTLandscapeSurface))
    keys='enable_wheel_support use_soil_shear_response use_rut_interaction use_native_mud_shader_updates use_native_substance_response use_native_water_response grass_is_visual_cover use_granular_response layer_depth_scale maximum_layer_depth_cm bearing_strength settlement_speed_scale'
    report['settings']={k:s.get_editor_property(k) for k in keys.split()}
    path=trial.route(json.loads((R/'Art/Export/LidarStudy/Place/roads.json').read_text()));report['samples']=[]
    for station in [170,200,214,230,260,290,340,400,500,552,610,667]:
        for across in [0,.83,1.6,2.5]:
            x,y,_=trial.at(path,station,across);v=s.sample_surface(u.Vector2D(x,y))
            vals={k:v.get_editor_property(k) for k in 'sinkage_cap_cm softness wetness cohesion grass_cover clay_weight bearing_strength settlement_speed_scale native_friction native_linear_resistance native_push_resistance friction_scale'.split()}
            report['samples'].append(dict(station=station,across=across,x=x,y=y,**vals))
    visual=next(a for a in aa if isinstance(a,u.GTMudRunnerVisual));report['materials']={}
    for role,m in [('ground',visual.material),('tread',visual.track_material)]:
        nodes=[]
        for e in u.MaterialEditingLibrary.get_material_expressions(m):
            r={'name':e.get_name(),'desc':str(e.get_editor_property('desc')),'type':e.get_class().get_name()}
            if isinstance(e,u.MaterialExpressionCustom):r.update(code=str(e.get_editor_property('code')),inputs=[str(x.get_editor_property('input_name')) for x in e.get_editor_property('inputs')])
            if isinstance(e,(u.MaterialExpressionScalarParameter,u.MaterialExpressionVectorParameter)):r.update(parameter=str(e.get_editor_property('parameter_name')),value=str(e.get_editor_property('default_value')))
            nodes.append(r)
        report['materials'][role]={'path':m.get_path_name(),'nodes':nodes}
    report['ok']=True
except Exception:report['error']=traceback.format_exc()
(O/'reference.json').write_text(json.dumps(report,indent=2))
u.get_editor_subsystem(u.LevelEditorSubsystem).load_level('/Engine/Maps/Entry')
for key in list(globals()):
    if not key.startswith('__') and key not in ['u','time']:globals()[key]=None
u.SystemLibrary.collect_garbage();end=time.monotonic()+3
def quit(dt):
    if time.monotonic()>end:u.unregister_slate_post_tick_callback(handle);u.SystemLibrary.quit_editor()
u.EditorPythonScripting.set_keep_python_script_alive(True);handle=u.register_slate_post_tick_callback(quit)
