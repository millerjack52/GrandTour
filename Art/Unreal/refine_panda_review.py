import unreal as u
MAP='/Game/GrandTour/ArtTests/Panda/L_PandaReview'
les=u.get_editor_subsystem(u.LevelEditorSubsystem);assert les.load_level(MAP)
actors=u.get_editor_subsystem(u.EditorActorSubsystem).get_all_level_actors()
for a in actors:
 if a.get_actor_label()=='NC_Camera_Panda1990_Cockpit':
  a.set_actor_rotation(u.Rotator(pitch=-12,yaw=0,roll=0),False)
  a.camera_component.set_editor_property('constrain_aspect_ratio',False)
 if isinstance(a,u.CameraActor):a.camera_component.set_editor_property('constrain_aspect_ratio',False)
 if a.get_actor_label()=='NC_Sky':
  c=a.get_component_by_class(u.SkyLightComponent)
  c.set_editor_property('real_time_capture',False)
  c.set_editor_property('source_type',u.SkyLightSourceType.SLS_SPECIFIED_CUBEMAP)
  c.set_editor_property('cubemap',u.load_asset('/Engine/MapTemplates/Sky/DaylightAmbientCubemap'))
  c.set_editor_property('intensity',1.5)
  c.set_editor_property('lower_hemisphere_is_black',False)
  c.recapture_sky()
 if a.get_actor_label()=='NC_Exposure':
  # Soft ambient fill for a neutral material/assembly review, including enclosed cabin.
  a.set_editor_property('priority',200.)
  s=a.get_editor_property('settings')
  s.set_editor_property('ambient_cubemap',u.load_asset('/Engine/MapTemplates/Sky/DaylightAmbientCubemap'))
  s.set_editor_property('override_ambient_cubemap_intensity',True)
  s.set_editor_property('ambient_cubemap_intensity',.35)
  a.set_editor_property('settings',s)
assert les.save_current_level()
print('PANDA_REVIEW_REFINED')
