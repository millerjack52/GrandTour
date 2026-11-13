"""Match the purchased source's lighting and Standard display response in a test map."""
import unreal as u,json,math,traceback
from pathlib import Path
ROOT=Path(u.Paths.project_dir()).resolve();OUT=ROOT/'Art/Export/LidarStudy/FloraMatch';DEST='/Game/GrandTour/ArtTests/FloraMatch'
eal=u.EditorAssetLibrary;mel=u.MaterialEditingLibrary;at=u.AssetToolsHelpers.get_asset_tools();les=u.get_editor_subsystem(u.LevelEditorSubsystem);actors=u.get_editor_subsystem(u.EditorActorSubsystem)
def props(o,**kw):
 for k,v in kw.items():o.set_editor_property(k,v)
 return o
report={'ok':False,'test_rig_only':True}
try:
 target=DEST+'/L_FloraReferenceRig'
 assert les.load_level(target if eal.does_asset_exist(target) else DEST+'/L_FloraMatch')
 if not eal.does_asset_exist(target):
  assert u.EditorLoadingAndSavingUtils.save_map(u.get_editor_subsystem(u.UnrealEditorSubsystem).get_editor_world(),target)
  assert les.load_level(target)
 task=props(u.AssetImportTask(),filename=str(OUT/'source-world.hdr'),destination_path=DEST,destination_name='T_SourceWorld',automated=True,replace_existing=True,save=True);at.import_asset_tasks([task]);cube=u.load_asset(DEST+'/T_SourceWorld');assert isinstance(cube,u.TextureCube)
 for a in list(actors.get_all_level_actors()):
  if isinstance(a,u.SkyAtmosphere) or isinstance(a,u.CameraActor):actors.destroy_actor(a)
  elif isinstance(a,u.StaticMeshActor) and a.get_actor_label()!='FloraPilot_Tree':actors.destroy_actor(a)
  elif isinstance(a,u.DirectionalLight):
   x,y,z=.676684916,.854503572,6.10810566
   dx=-math.sin(y)*math.cos(x)*math.cos(z)-math.sin(x)*math.sin(z)
   dy=-math.sin(y)*math.cos(x)*math.sin(z)+math.sin(x)*math.cos(z);dz=-math.cos(y)*math.cos(x)
   a.set_actor_rotation(u.Rotator(pitch=math.degrees(math.asin(dz)),yaw=math.degrees(math.atan2(-dy,dx))),False)
   props(a.light_component,intensity=20.9,atmosphere_sun_light=False,light_source_angle=1.5)
  elif isinstance(a,u.SkyLight):
   a.light_component.set_mobility(u.ComponentMobility.MOVABLE)
   props(a.light_component,source_type=u.SkyLightSourceType.SLS_SPECIFIED_CUBEMAP,cubemap=cube,intensity=1.,real_time_capture=False,lower_hemisphere_is_black=False)
   a.light_component.recapture_sky()
 # Standard sRGB display transform, used solely for this controlled source rig.
 mat=u.load_asset(DEST+'/M_SourceStandardDisplay') or at.create_asset('M_SourceStandardDisplay',DEST,u.Material,u.MaterialFactoryNew());mel.delete_all_material_expressions(mat)
 props(mat,material_domain=u.MaterialDomain.MD_POST_PROCESS,blendable_location=u.BlendableLocation.BL_REPLACING_TONEMAPPER)
 scene=props(mel.create_material_expression(mat,u.MaterialExpressionSceneTexture),scene_texture_id=u.SceneTextureId.PPI_POST_PROCESS_INPUT0)
 custom=props(mel.create_material_expression(mat,u.MaterialExpressionCustom),inputs=[props(u.CustomInput(),input_name='Scene')],output_type=u.CustomMaterialOutputType.CMOT_FLOAT3,code='float3 c=max(Scene.rgb*View.OneOverPreExposure,0);return saturate(lerp(12.92*c,1.055*pow(c,1./2.4)-.055,step(.0031308,c)));')
 assert mel.connect_material_expressions(scene,'Color',custom,'Scene');assert mel.connect_material_property(custom,'',u.MaterialProperty.MP_EMISSIVE_COLOR);mel.recompile_material(mat);eal.save_loaded_asset(mat)
 for a in actors.get_all_level_actors():
  if isinstance(a,u.PostProcessVolume):
   ps=a.settings
   for k,v in dict(auto_exposure_min_brightness=0.,auto_exposure_max_brightness=0.,auto_exposure_bias=0.,bloom_intensity=0.,vignette_intensity=0.,lens_flare_intensity=0.,local_exposure_highlight_contrast_scale=1.,local_exposure_shadow_contrast_scale=1.).items():
    ps.set_editor_property('override_'+k,True);ps.set_editor_property(k,v)
   ps.set_editor_property('weighted_blendables',u.WeightedBlendables(array=[u.WeightedBlendable(weight=1.,object=mat)]));a.settings=ps
 camera=actors.spawn_actor_from_class(u.CameraActor,u.Vector(1500,-2000,1200),u.Rotator(pitch=math.degrees(math.atan2(-700,2500)),yaw=math.degrees(math.atan2(2000,-1500))))
 camera.set_actor_label('FloraSourceCamera');props(camera.camera_component,projection_mode=u.CameraProjectionMode.ORTHOGRAPHIC,ortho_width=1300.,aspect_ratio=1.,constrain_aspect_ratio=False)
 props(camera,auto_activate_for_player=u.AutoReceiveInput.PLAYER0)
 calibration=at.create_asset('M_CalibrationGrey',DEST,u.Material,u.MaterialFactoryNew()) if not eal.does_asset_exist(DEST+'/M_CalibrationGrey') else u.load_asset(DEST+'/M_CalibrationGrey')
 mel.delete_all_material_expressions(calibration)
 for prop,value in [(u.MaterialProperty.MP_BASE_COLOR,.18),(u.MaterialProperty.MP_ROUGHNESS,1.),(u.MaterialProperty.MP_SPECULAR,0.)]:
  expression=props(mel.create_material_expression(calibration,u.MaterialExpressionConstant),r=value);mel.connect_material_property(expression,'',prop)
 mel.recompile_material(calibration);eal.save_loaded_asset(calibration)
 grey=actors.spawn_actor_from_class(u.StaticMeshActor,u.Vector(0,0,2000));grey.set_actor_label('CalibrationGrey');grey.static_mesh_component.set_static_mesh(u.load_asset('/Engine/BasicShapes/Cube'));grey.set_actor_scale3d(u.Vector(2,2,2));grey.static_mesh_component.set_material(0,calibration)
 calcam=actors.spawn_actor_from_class(u.CameraActor,u.Vector(1500,-2000,2700),camera.get_actor_rotation());calcam.set_actor_label('CalibrationCamera');props(calcam.camera_component,projection_mode=u.CameraProjectionMode.ORTHOGRAPHIC,ortho_width=400.,constrain_aspect_ratio=False)
 assert les.save_current_level();stats=mel.get_statistics(mat)
 report.update(ok=True,level=target,camera_name=camera.get_name(),calibration_camera=calcam.get_name(),camera_position=[1500,-2000,1200],ortho_width_cm=1300,colour_transform='Standard sRGB, isolated rig only',sun_intensity=20.9,source_sun_energy=18,world_colour=[.2047979087,.3521454334,.6382719874],postprocess_pixel_instructions=stats.num_pixel_shader_instructions)
except Exception:report['error']=traceback.format_exc();u.log_error(report['error'])
(OUT/'reference-rig.json').write_text(json.dumps(report,indent=2))
def quit(dt):
 u.unregister_slate_post_tick_callback(handle);u.SystemLibrary.quit_editor()
u.EditorPythonScripting.set_keep_python_script_alive(True);handle=u.register_slate_post_tick_callback(quit)
