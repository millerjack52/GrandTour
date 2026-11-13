"""Purchased Flora Paint path composition; isolated group and lighting study."""
import unreal as u,json,sys,time,math,traceback,gc,hashlib
from pathlib import Path
R=Path('C:/GrandTour');O=R/'Art/Export/LidarStudy/FloraGroup';P=R/'Art/Export/LidarStudy/FloraPath';B=R/'Art/Export/LidarStudy/FloraParity/AssetMatch'
D='/Game/GrandTour/ArtTests/FloraGroup';LEVEL=D+'/L_FloraGroup'
sys.path.insert(0,str(R/'Art/Unreal'))
from benmore_river_life_materials import props,Graph
import flora_exact_materials as fm
A=u.get_editor_subsystem(u.EditorActorSubsystem);L=u.get_editor_subsystem(u.LevelEditorSubsystem);E=u.EditorAssetLibrary;M=u.MaterialEditingLibrary
report={'ok':False,'images':[],'components':[],'performance_verified':False,'reference':'Casey Sheep / Flora Paint forest path, supplied by user','limits':['Six source-converted foliage meshes; variants remapped for this small study, not full-pack conversion','Ground, rocks, twigs and fallen litter reuse prior scenic materials','Source lighting model supports sun plus uniform sky; local-light cases deliberately test that limitation','Temporal edge stability and whole-forest performance remain open']}
cfg=json.loads((R/'Art/flora_group_settings.json').read_text())
def save():(O/'scene-report.json').write_text(json.dumps(report,indent=2))
def spawn(cls,name,pos=(0,0,0),rotation=None):
 a=A.spawn_actor_from_class(cls,u.Vector(*pos),rotation or u.Rotator());a.set_actor_label('FloraGroup_'+name);return a
def command(s):u.SystemLibrary.execute_console_command(world,s)
def lighting(case):
 sun.light_component.set_intensity(case['sun']*.96457146);sun.light_component.set_light_color(u.LinearColor(*case['sun_colour'],1))
 sky.light_component.set_intensity(case['sky']*.89832447);sky.light_component.set_light_color(u.LinearColor(*case['sky_colour'],1))
 props(fog.component,fog_density=case['fog'],fog_inscattering_luminance=u.LinearColor(*case['fog_colour'],1))
 u.MaterialLibrary.set_vector_parameter_value(world,mpc,'SkyRadiance',u.LinearColor(*(v*case['sky']*.92909 for v in case['sky_colour']),0))
 spot.light_component.set_intensity(case['spot_cd']);fill.light_component.set_intensity(case['fill_cd'])
def capture(name,frames=64):
 for _ in range(frames):cc.capture_scene();yield .02
 u.RenderingLibrary.export_render_target(world,target,str(O),name+'.png')
 assert (O/(name+'.png')).is_file();report['images'].append(name);save()
def native_diagnostic(source):
 """Same pigment/mask, UE foliage lighting: a diagnostic, not a source-match claim."""
 path=D+'/NativeDiagnostic/'+source.get_name();mat=u.load_asset(path) or E.duplicate_asset(source.get_path_name().split('.')[0],path)
 nodes=M.get_material_expressions(mat)
 colour=next(n for n in nodes if isinstance(n,u.MaterialExpressionTextureSampleParameter2D) and str(n.get_editor_property('parameter_name'))=='SourcePigment')
 g=Graph(mat);props(mat,shading_model=u.MaterialShadingModel.MSM_TWO_SIDED_FOLIAGE)
 g.output(colour,u.MaterialProperty.MP_BASE_COLOR,'RGB');g.output(g.scalar(0),u.MaterialProperty.MP_EMISSIVE_COLOR)
 n=g.node(u.MaterialExpressionVertexNormalWS);side=g.node(u.MaterialExpressionTwoSidedSign)
 normal=g.custom(['N','S'],'return normalize(N)*S;');g.wire(n,normal,'N');g.wire(side,normal,'S');g.output(normal,u.MaterialProperty.MP_NORMAL)
 g.output(colour,u.MaterialProperty.MP_SUBSURFACE_COLOR,'RGB');g.output(g.scalar(.5),u.MaterialProperty.MP_OPACITY);g.output(g.scalar(.95),u.MaterialProperty.MP_ROUGHNESS)
 assert not M.recompile_material(mat);E.save_loaded_asset(mat,False);return mat
def run():
 global world,sun,sky,fog,spot,fill,mpc,cc,target
 E.make_directory(D)
 if E.does_asset_exist(LEVEL):
  assert L.load_level(LEVEL)
  for a in A.get_all_level_actors():
   if a.get_actor_label().startswith('FloraGroup_'):A.destroy_actor(a)
 else:assert L.new_level(LEVEL)
 world=u.get_editor_subsystem(u.UnrealEditorSubsystem).get_editor_world();world.get_world_settings().set_editor_property('default_game_mode',u.GameModeBase)
 for s in ['Interchange.FeatureFlags.Import.FBX 0','r.AntiAliasingMethod 4','r.ScreenPercentage 100','r.MotionBlurQuality 0','r.EyeAdaptationQuality 0','r.Shadow.Virtual.Enable 1','r.Shadow.Virtual.Cache 1','r.DistanceFieldAO 0','r.Lumen.DiffuseIndirect.Allow 0','r.Lumen.Reflections.Allow 0','gt.Look.Post 0','r.LUT.TonemappingMethod 0','r.LUT.TonemappingSDRInvEOTF 0']:command(s)
 fm.D=D+'/Assets';fm.O=B;models={}
 old_recipe=json.loads((B/'recipe.json').read_text())
 for asset in old_recipe['assets']:models[asset['key']]=fm.import_asset(asset)
 fm.O=O
 for asset in json.loads((O/'extra-assets.json').read_text())['assets']:models[asset['key']]=fm.import_asset(asset)
 from flora_group_bark import install
 report['bark']=install(models)
 mpc=fm.lighting_controls()
 data=json.loads((P/'scene-manifest.json').read_text());buckets={};oldbounds={};newbounds={key:m.get_bounds().box_extent for key,m in models.items()}
 for row in data['instances']:
  name=row['mesh'];key=None
  if 'Tree_D' in name:key='pine'
  elif 'Tree_B' in name:key='tree'
  elif 'Ferns' in name:key='fern'
  elif 'Shrubbery' in name or 'Small_Plants' in name:key='shrub'
  elif 'Dry_Grass' in name:key='drygrass'
  elif 'Grass' in name or 'Miscanthus' in name:key='grass'
  elif 'Flower' in name:continue
  source=u.load_asset('/Game/GrandTour/ArtTests/FloraPath/'+name);assert source,name
  scale=list(row['scale']);mesh=models[key] if key else source
  if key:
   oldbounds.setdefault(name,source.get_bounds().box_extent);a=oldbounds[name];b=newbounds[key]
   ratio=max(a.x,a.y,a.z)/max(b.x,b.y,b.z)
   scale=[s*ratio for s in scale]
  bucket=key or name;buckets.setdefault(bucket,{'mesh':mesh,'transforms':[],'candidate':bool(key)})['transforms'].append(u.Transform(location=u.Vector(*row['location_cm']),rotation=u.Quat(*row['quat']).rotator(),scale=u.Vector(*scale)))
 owner=spawn(u.Actor,'InstancedPlants');components=[]
 for name,bucket in buckets.items():
  shadow=bucket['candidate'] or 'Rock' in name or 'Ground' in name
  c=u.GTVegetationSubsystem.add_tagged_instances(owner,bucket['mesh'],bucket['transforms'],'FloraGroup','NoCollision',shadow)
  c.set_cull_distances(0,0);props(c,visible_in_ray_tracing=False,shadow_cache_invalidation_behavior=u.ShadowCacheInvalidationBehavior.RIGID)
  components.append((name,c));report['components'].append({'mesh':bucket['mesh'].get_path_name(),'instances':len(bucket['transforms']),'source_conversion':bucket['candidate'],'casts_shadows':shadow})
 # The pack's original camera and directional light supply the composition.
 f=data['camera']['forward'];pos=data['camera']['position'];position=[pos[0]*100,-pos[1]*100,pos[2]*100]
 rotation=u.Rotator(pitch=math.degrees(math.asin(f[2])),yaw=math.degrees(math.atan2(-f[1],f[0])))
 fov=math.degrees(data['camera']['angle']);cam=spawn(u.CameraActor,'ReferenceCamera',position,rotation)
 props(cam.camera_component,field_of_view=fov,aspect_ratio=2.,constrain_aspect_ratio=True);cam.set_editor_property('auto_activate_for_player',u.AutoReceiveInput.PLAYER0)
 spawn(u.PlayerStart,'Start',position);u.get_editor_subsystem(u.UnrealEditorSubsystem).set_level_viewport_camera_info(cam.get_actor_location(),rotation)
 ray=[-data['light']['matrix'][i][2] for i in range(3)];direction=u.Vector(ray[0],-ray[1],ray[2])
 sun=spawn(u.DirectionalLight,'Sun',rotation=u.MathLibrary.find_look_at_rotation(u.Vector(),direction));sun.light_component.set_mobility(u.ComponentMobility.MOVABLE)
 props(sun.light_component,light_source_angle=2.,volumetric_scattering_intensity=.7)
 sun.set_editor_property('tags',[u.Name('GTWeatherUnmanaged')])
 u.MaterialLibrary.set_vector_parameter_value(world,mpc,'SunDirection',u.LinearColor(-ray[0],ray[1],-ray[2],0))
 # Save map-specific defaults as well as runtime overrides, for reopening the map.
 ps=mpc.get_editor_property('vector_parameters')
 for p in ps:
  if str(p.get_editor_property('parameter_name'))=='SunDirection':p.set_editor_property('default_value',u.LinearColor(-ray[0],ray[1],-ray[2],0))
  if str(p.get_editor_property('parameter_name'))=='SkyRadiance':p.set_editor_property('default_value',u.LinearColor(*(v*cfg['cases'][0]['sky']*.92909 for v in cfg['cases'][0]['sky_colour']),0))
 mpc.set_editor_property('vector_parameters',ps);E.save_loaded_asset(mpc,False)
 sky=spawn(u.SkyLight,'Sky');sky.light_component.set_mobility(u.ComponentMobility.MOVABLE)
 sky.set_editor_property('tags',[u.Name('GTWeatherUnmanaged')])
 props(sky.light_component,source_type=u.SkyLightSourceType.SLS_SPECIFIED_CUBEMAP,cubemap=u.load_asset('/Game/GrandTour/ArtTests/FloraParity/AssetMatch/T_ParityWhite'),real_time_capture=False,lower_hemisphere_is_black=False,cast_shadows=False)
 sky.light_component.recapture_sky()
 fog=spawn(u.ExponentialHeightFog,'ForestHaze',(0,0,150));fog.set_editor_property('tags',[u.Name('GTWeatherUnmanaged')])
 props(fog.component,fog_height_falloff=.08,start_distance=150.,fog_max_opacity=.94,enable_volumetric_fog=True,volumetric_fog_scattering_distribution=.5,volumetric_fog_albedo=u.Color(185,207,235,255),volumetric_fog_distance=5000.)
 # A simple distant sky supplies the backdrop; no new cloud system is introduced.
 mat=u.load_asset(D+'/M_Backdrop') or u.AssetToolsHelpers.get_asset_tools().create_asset('M_Backdrop',D,u.Material,u.MaterialFactoryNew())
 M.delete_all_material_expressions(mat);props(mat,two_sided=True,shading_model=u.MaterialShadingModel.MSM_UNLIT);g=Graph(mat);g.output(g.vector((.25,.34,.48)),u.MaterialProperty.MP_EMISSIVE_COLOR);M.recompile_material(mat);E.save_loaded_asset(mat,False)
 bg=spawn(u.StaticMeshActor,'Backdrop');bg.static_mesh_component.set_static_mesh(u.load_asset('/Engine/BasicShapes/Sphere'));bg.set_actor_scale3d(u.Vector(1500,1500,1500));bg.static_mesh_component.set_material(0,mat);props(bg.static_mesh_component,cast_shadow=False,visible_in_ray_tracing=False)
 spot=spawn(u.SpotLight,'WarmLocalSpot',cfg['spot_position_cm']);spot.set_actor_rotation(u.MathLibrary.find_look_at_rotation(spot.get_actor_location(),u.Vector(*cfg['spot_target_cm'])),False)
 props(spot.light_component,intensity_units=u.LightUnits.CANDELAS,attenuation_radius=1000.,inner_cone_angle=24.,outer_cone_angle=48.,source_radius=12.,cast_shadows=True,volumetric_scattering_intensity=.35)
 spot.light_component.set_mobility(u.ComponentMobility.MOVABLE);spot.light_component.set_light_color(u.LinearColor(1,.63,.30,1))
 fill=spawn(u.PointLight,'CoolLocalFill',cfg['fill_position_cm']);fill.light_component.set_mobility(u.ComponentMobility.MOVABLE)
 props(fill.light_component,intensity_units=u.LightUnits.CANDELAS,attenuation_radius=650.,source_radius=35.,cast_shadows=False,volumetric_scattering_intensity=.1);fill.light_component.set_light_color(u.LinearColor(.24,.5,1,1))
 display=u.load_asset('/Game/GrandTour/ArtTests/FloraParity/AssetMatch/M_SourceStandardDisplay_02');assert display
 pp=spawn(u.PostProcessVolume,'Display');props(pp,unbound=True,priority=1000.,blend_weight=1.)
 settings=pp.settings
 for k,v in dict(auto_exposure_method=u.AutoExposureMethod.AEM_MANUAL,auto_exposure_apply_physical_camera_exposure=False,auto_exposure_bias=cfg['exposure_stops'],bloom_intensity=.02,vignette_intensity=0.,film_grain_intensity=0.,lens_flare_intensity=0.,motion_blur_amount=0.,local_exposure_highlight_contrast_scale=1.,local_exposure_shadow_contrast_scale=1.,tone_curve_amount=0.,expand_gamut=0.,blue_correction=0.).items():props(settings,**{'override_'+k:True,k:v})
 settings.weighted_blendables=props(u.WeightedBlendables(),array=[props(u.WeightedBlendable(),weight=1.,object=display)]);pp.settings=settings
 capture_actor=spawn(u.SceneCapture2D,'ReviewCapture',position,rotation);cc=capture_actor.capture_component2d
 target=u.RenderingLibrary.create_render_target2d(world,1200,600,u.TextureRenderTargetFormat.RTF_RGBA8_SRGB)
 props(cc,capture_every_frame=False,capture_on_movement=False,always_persist_rendering_state=True,fov_angle=fov,post_process_blend_weight=1.,capture_source=u.SceneCaptureSource.SCS_FINAL_COLOR_LDR,texture_target=target)
 cc.post_process_settings=settings;cc.show_flag_settings=[props(u.EngineShowFlagsSetting(),show_flag_name=n,enabled=True) for n in ['TemporalAA','AntiAliasing','Fog','Atmosphere']]
 lighting(cfg['cases'][0]);assert L.save_current_level();yield 8
 report.update(level=LEVEL,settings=cfg,instances=sum(len(b['transforms']) for b in buckets.values()),camera={'position_cm':position,'rotation':list(rotation.to_tuple()),'fov':fov},lighting_model='Unmodified source sun+uniform-sky candidate; native spot/point test lights',performance_budget={'instanced_components':len(components),'shadow_casting_local_lights':1,'unshadowed_local_fill_lights':1,'render_resolution':[1200,600]})
 for case in cfg['cases']:
  lighting(case);yield 2;yield from capture(case['name'])
 # Compare native UE foliage response under exactly the same local-light rig.
 stored=[]
 for name,c in components:
  if name not in models:continue
  for i,m in enumerate(c.get_materials()):
   if m.blend_mode==u.BlendMode.BLEND_MASKED:stored.append((c,i,m));c.set_material(i,native_diagnostic(m))
 yield 5;yield from capture('05_local_native_diagnostic')
 for c,i,m in stored:c.set_material(i,m)
 lighting(cfg['cases'][0]);yield 2;yield from capture('00_reference_sun')
 cc.texture_target=None;A.destroy_actor(capture_actor);u.RenderingLibrary.release_render_target2d(target);target=None
 # SceneCapture's sRGB target encodes linear output automatically. The editor
 # backbuffer needs explicit Standard encoding when replacing its tonemapper.
 from flora_group_display import apply_to_volume
 apply_to_volume(pp)
 assert L.save_current_level();report['ok']=True;save();yield 2
 # Keep captures and process validation separate. Never hide a nonzero exit.
 command('r.RHIThread.Enable 0');yield 2
 assert L.load_level('/Engine/Maps/Entry');yield 2
 world=cc=sun=sky=fog=spot=fill=mpc=None;fm.S=fm.T=None;gc.collect();u.SystemLibrary.collect_garbage();yield 2
steps=run();state={'busy':False,'deadline':0}
def tick(dt):
 global steps
 if state['busy'] or time.monotonic()<state['deadline']:return
 state['busy']=True
 try:state['deadline']=time.monotonic()+next(steps)
 except StopIteration:
  u.unregister_slate_post_tick_callback(state['handle']);steps=None;gc.collect();u.EditorPythonScripting.set_keep_python_script_alive(False);u.SystemLibrary.quit_editor()
 except Exception:
  report['error']=traceback.format_exc();save();u.log_error(report['error']);u.unregister_slate_post_tick_callback(state['handle']);u.SystemLibrary.quit_editor()
 finally:state['busy']=False
u.EditorPythonScripting.set_keep_python_script_alive(True);state['handle']=u.register_slate_post_tick_callback(tick)
