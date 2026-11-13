"""Isolated purchaser study of Casey Sheep's forest-path composition."""
import unreal as u,json,math,re,traceback,hashlib,os
from pathlib import Path
ROOT=Path(u.Paths.project_dir()).resolve();OUT=ROOT/'Art/Export/LidarStudy/FloraPath';DEST='/Game/GrandTour/ArtTests/FloraPath';LEVEL=DEST+'/L_FloraPath'
eal=u.EditorAssetLibrary;at=u.AssetToolsHelpers.get_asset_tools();mel=u.MaterialEditingLibrary
les=u.get_editor_subsystem(u.LevelEditorSubsystem);actors=u.get_editor_subsystem(u.EditorActorSubsystem);sm=u.get_editor_subsystem(u.StaticMeshEditorSubsystem)
report={'ok':False,'woodland_modified':False,'performance_verified':False,'materials':[],'meshes':[],'components':[]}
prior=json.loads((OUT/'build-report.json').read_text()) if (OUT/'build-report.json').exists() else {}
completed={r['name']:r for r in prior.get('meshes',[])} if os.environ.get('GT_FLORA_PATH_REBUILD_ASSETS')!='1' else {}
if completed:report['materials']=prior.get('materials',[])
def props(o,**kw):
 for k,v in kw.items():o.set_editor_property(k,v)
 return o
def node(m,c,**kw):return props(mel.create_material_expression(m,c),**kw)
def wire(a,b,p,out=''):assert mel.connect_material_expressions(a,out,b,p)
def output(a,p,out=''):assert mel.connect_material_property(a,out,p)
def scalar(m,n,v):return node(m,u.MaterialExpressionScalarParameter,parameter_name=n,default_value=v)
def custom(m,names,code,kind=u.CustomMaterialOutputType.CMOT_FLOAT3):return node(m,u.MaterialExpressionCustom,code=code,output_type=kind,inputs=[props(u.CustomInput(),input_name=n) for n in names])
def mult(m,a,b,ao='',bo=''):
 n=node(m,u.MaterialExpressionMultiply);wire(a,n,'A',ao);wire(b,n,'B',bo);return n
def spawn(cls,label,pos=(0,0,0),rot=None):
 a=actors.spawn_actor_from_class(cls,u.Vector(*pos),rot or u.Rotator());a.set_actor_label('FloraPath_'+label);return a
def texture(filename,name,mask=False):
 path=DEST+'/'+name;tex=u.load_asset(path)
 if not tex:
  task=props(u.AssetImportTask(),filename=str(filename),destination_path=DEST,destination_name=name,automated=True,replace_existing=True,save=True);at.import_asset_tasks([task]);tex=u.load_asset(path)
 assert tex,path
 props(tex,srgb=not mask,compression_settings=u.TextureCompressionSettings.TC_ALPHA if mask else u.TextureCompressionSettings.TC_DEFAULT,max_texture_size=2048)
 eal.save_loaded_asset(tex);return tex
cache={}
def material(key,setting,atlas=None):
 name='M_Path_'+re.sub('[^a-zA-Z0-9_]','_',key)+('_'+atlas.get_name() if atlas else '')
 if name in cache:return cache[name]
 m=u.load_asset(DEST+'/'+name) or at.create_asset(name,DEST,u.Material,u.MaterialFactoryNew());mel.delete_all_material_expressions(m)
 mel.set_material_usage(m,u.MaterialUsage.MATUSAGE_INSTANCED_STATIC_MESHES)
 vc=node(m,u.MaterialExpressionVertexColor)
 if atlas:
  colour=node(m,u.MaterialExpressionTextureSampleParameter2D,parameter_name='PaintedColour',texture=atlas,sampler_type=u.MaterialSamplerType.SAMPLERTYPE_COLOR)
  wire(node(m,u.MaterialExpressionTextureCoordinate,coordinate_index=1),colour,'UVs')
 else:
  colour=custom(m,['C'],'return lerp(C/12.92,pow((C+.055)/1.055,2.4),step(.04045,C));');wire(vc,colour,'C')
 tint=node(m,u.MaterialExpressionVectorParameter,parameter_name='PaletteTint',default_value=u.LinearColor(1,1,1,1));base=mult(m,colour,tint);output(base,u.MaterialProperty.MP_BASE_COLOR)
 output(scalar(m,'Roughness',.94),u.MaterialProperty.MP_ROUGHNESS);output(scalar(m,'Specular',.04),u.MaterialProperty.MP_SPECULAR)
 if setting['foliage']:
  props(m,two_sided=True,tangent_space_normal=False,blend_mode=u.BlendMode.BLEND_MASKED,shading_model=u.MaterialShadingModel.MSM_TWO_SIDED_FOLIAGE,opacity_mask_clip_value=.16,dither_opacity_mask=False)
  tex=texture(Path(data['source']).parent/'textures'/setting['mask'],'T_Mask_'+Path(setting['mask']).stem,True)
  sample=node(m,u.MaterialExpressionTextureSampleParameter2D,parameter_name='PaintedMask',texture=tex,sampler_type=u.MaterialSamplerType.SAMPLERTYPE_ALPHA)
  ramp=setting['ramp'];code='float x=Mask<.04045?Mask/12.92:pow((Mask+.055)/1.055,2.4);float a=1.;'
  code+=' else '.join(f'if(x<{x1}) a=lerp({y0},{y1},saturate((x-{x0})/{max(x1-x0,.0001)}));' for (x0,y0),(x1,y1) in zip(ramp,ramp[1:]))
  code+='return saturate(a*Gain);';alpha=custom(m,['Mask','Gain'],code,u.CustomMaterialOutputType.CMOT_FLOAT1);wire(sample,alpha,'Mask','R');wire(scalar(m,'Coverage',1),alpha,'Gain');output(alpha,u.MaterialProperty.MP_OPACITY_MASK)
  normal=node(m,u.MaterialExpressionVertexNormalWS);lit=custom(m,['N','Up'],'return normalize(lerp(normalize(N),float3(0,0,1),Up));');wire(normal,lit,'N');wire(scalar(m,'NormalUpBlend',.7 if key=='Leaf_0' else .3),lit,'Up');output(lit,u.MaterialProperty.MP_NORMAL)
  output(mult(m,base,scalar(m,'Transmission',.55 if key=='Leaf_0' else .75)),u.MaterialProperty.MP_SUBSURFACE_COLOR)
  output(scalar(m,'TransmissionOpacity',.5),u.MaterialProperty.MP_OPACITY)
  if setting.get('emission',0)>0:
   colourglow=node(m,u.MaterialExpressionVectorParameter,parameter_name='FlowerGlowColour',default_value=u.LinearColor(*setting['emission_colour']));output(mult(m,colourglow,scalar(m,'FlowerGlow',350)),u.MaterialProperty.MP_EMISSIVE_COLOR)
 mel.recompile_material(m);eal.save_loaded_asset(m)
 mi_name=name.replace('M_','MI_',1);mi=u.load_asset(DEST+'/'+mi_name) or at.create_asset(mi_name,DEST,u.MaterialInstanceConstant,u.MaterialInstanceConstantFactoryNew());mel.set_material_instance_parent(mi,m);eal.save_loaded_asset(mi);cache[name]=mi
 report['materials'].append({'path':m.get_path_name(),'foliage':setting['foliage'],'texture_samples':int(atlas is not None)+int(setting['foliage'])});return mi
try:
 data=json.loads((OUT/'scene-manifest.json').read_text());eal.make_directory(DEST)
 assert les.load_level(LEVEL) if eal.does_asset_exist(LEVEL) else les.new_level(LEVEL)
 for a in list(actors.get_all_level_actors()):
  if a.get_actor_label().startswith('FloraPath_'):actors.destroy_actor(a)
 world=u.get_editor_subsystem(u.UnrealEditorSubsystem).get_editor_world();world.get_world_settings().set_editor_property('default_game_mode',u.GameModeBase)
 u.SystemLibrary.execute_console_command(world,'Interchange.FeatureFlags.Import.FBX 0')
 models={}
 for row in data['meshes']:
  if row['name'] in completed and eal.does_asset_exist(DEST+'/'+row['name']):
   models[row['name']]=u.load_asset(DEST+'/'+row['name']);report['meshes'].append(completed[row['name']]);continue
  if os.environ.get('GT_FLORA_PATH_SCENE_ONLY')=='1':
   mesh=u.load_asset(DEST+'/'+row['name']);assert mesh,row['name'];models[row['name']]=mesh;report['meshes'].append({'name':row['name'],'triangles':mesh.get_static_mesh_description(0).get_triangle_count(),'lods':sm.get_lod_count(mesh),'uvs':sm.get_num_uv_channels(mesh,0)});continue
  atlas=texture(OUT/row['atlas'],'T_'+Path(row['atlas']).stem) if row['atlas'] else None
  mats=[material(k,data['materials'][k],atlas) for k in row['materials']]
  path=DEST+'/'+row['name'];mesh=u.load_asset(path)
  if not mesh:
   task=props(u.AssetImportTask(),filename=str(OUT/(row['name']+'.fbx')),destination_path=DEST,destination_name=row['name'],automated=True,replace_existing=True,save=True)
   opt=props(u.FbxImportUI(),import_mesh=True,import_as_skeletal=False,import_materials=False,import_textures=False,import_animations=False,mesh_type_to_import=u.FBXImportType.FBXIT_STATIC_MESH)
   props(opt.static_mesh_import_data,combine_meshes=True,auto_generate_collision=False,generate_lightmap_u_vs=False,normal_import_method=u.FBXNormalImportMethod.FBXNIM_IMPORT_NORMALS,vertex_color_import_option=u.VertexColorImportOption.REPLACE);task.options=opt;at.import_asset_tasks([task]);mesh=u.load_asset(path)
  assert mesh
  for idx,mat in enumerate(mats):mesh.set_material(idx,mat)
  build=sm.get_lod_build_settings(mesh,0);props(build,recompute_normals=False,recompute_tangents=True,use_full_precision_u_vs=True);sm.set_lod_build_settings(mesh,0,build);sm.remove_collisions(mesh)
  n=mesh.get_editor_property('nanite_settings');n.enabled=False;sm.set_nanite_settings(mesh,n,True)
  assert sm.get_num_uv_channels(mesh,0)==row['uv_channels']
  triangles=mesh.get_static_mesh_description(0).get_triangle_count();removed=row['triangles']-triangles
  assert 0<=removed<=max(8,row['triangles']*.001),(row['name'],triangles,row['triangles'])
  # Preserve near-camera detail; automatic reduction is restricted to distant trees.
  if row['source'].startswith('FP_Tree') and sm.get_lod_count(mesh)==1:
   opts=u.StaticMeshReductionOptions();opts.auto_compute_lod_screen_size=False;opts.reduction_settings=[u.StaticMeshReductionSettings(percent_triangles=p,screen_size=s) for p,s in [(1.,1.),(.5,.12),(.22,.035)]];assert sm.set_lods(mesh,opts)==3
  eal.save_loaded_asset(mesh);models[row['name']]=mesh;report['meshes'].append({'name':row['name'],'triangles':triangles,'source_triangles':row['triangles'],'import_removed_triangles':removed,'lods':sm.get_lod_count(mesh),'uvs':row['uv_channels']})
 owner=spawn(u.Actor,'Instances');buckets={}
 for p in data['instances']:buckets.setdefault(p['mesh'],[]).append(u.Transform(location=u.Vector(*p['location_cm']),rotation=u.Quat(*p['quat']).rotator(),scale=u.Vector(*p['scale'])))
 for name,ts in buckets.items():
  tree='Tree' in name;solid=tree or 'Rock' in name or 'Ground1' in name
  # Important foreground foliage casts real shadows; tiny litter does not.
  shadow=solid or any(k in name for k in ['Ferns','Shrubbery','Grass','Miscanthus'])
  c=u.GTVegetationSubsystem.add_tagged_instances(owner,models[name],ts,'FloraPathStudy','NoCollision',shadow)
  c.set_cull_distances(0,0) if solid else c.set_cull_distances(4500,6500)
  props(c,visible_in_ray_tracing=False,affect_distance_field_lighting=solid,shadow_cache_invalidation_behavior=u.ShadowCacheInvalidationBehavior.RIGID)
  report['components'].append({'mesh':name,'instances':len(ts),'casts_shadow':shadow,'cull_end_cm':0 if solid else 6500})
 spawn(u.SkyAtmosphere,'Atmosphere')
 light=data['light'];v=[-light['matrix'][i][2] for i in range(3)];sun=spawn(u.DirectionalLight,'Sun',(0,0,2000),u.Rotator(pitch=math.degrees(math.asin(v[2])),yaw=math.degrees(math.atan2(-v[1],v[0]))))
 props(sun.light_component,intensity=65000.,light_color=u.Color(255,232,193,255),atmosphere_sun_light=True,light_source_angle=2.,volumetric_scattering_intensity=.65)
 sky=spawn(u.SkyLight,'Sky');sky.light_component.set_mobility(u.ComponentMobility.MOVABLE);props(sky.light_component,real_time_capture=True,intensity=.8)
 fog=spawn(u.ExponentialHeightFog,'Haze',(0,0,300));props(fog.component,fog_density=.055,fog_height_falloff=.06,start_distance=250.,fog_max_opacity=.94,fog_inscattering_luminance=u.LinearColor(.28,.4,.63,1),enable_volumetric_fog=True,volumetric_fog_scattering_distribution=.55,volumetric_fog_albedo=u.Color(180,205,245,255),volumetric_fog_distance=7000.)
 pp=spawn(u.PostProcessVolume,'Exposure');props(pp,unbound=True,priority=500.,blend_weight=1.);ps=pp.settings
 for k,v in dict(auto_exposure_min_brightness=12.,auto_exposure_max_brightness=12.,auto_exposure_bias=0.,bloom_intensity=.12,lens_flare_intensity=0.,vignette_intensity=.12,local_exposure_highlight_contrast_scale=1.,local_exposure_shadow_contrast_scale=1.).items():props(ps,**{'override_'+k:True,k:v})
 pp.settings=ps
 cam=data['camera'];pos=[cam['position'][0]*100,-cam['position'][1]*100,cam['position'][2]*100];f=cam['forward'];pitch=math.degrees(math.asin(f[2]));yaw=math.degrees(math.atan2(-f[1],f[0]));fov=math.degrees(cam['angle'])
 camera=spawn(u.CameraActor,'ReferenceCamera',pos,u.Rotator(pitch=pitch,yaw=yaw));props(camera.camera_component,field_of_view=fov,aspect_ratio=2.,constrain_aspect_ratio=False);props(camera,auto_activate_for_player=u.AutoReceiveInput.PLAYER0)
 spawn(u.GTDistanceStyleController,'ReviewCamera');spawn(u.PlayerStart,'Start',pos)
 assert les.save_current_level()
 # Trigger compilation now so capture does not silently show fallback materials.
 for row in report['materials']:
  st=mel.get_statistics(u.load_asset(row['path']));row['pixel_instructions']=st.num_pixel_shader_instructions
 report.update(ok=True,level=LEVEL,camera={'position':pos,'pitch':pitch,'yaw':yaw,'fov':fov},instances=sum(len(v) for v in buckets.values()),source_attribution=data['attribution'])
except Exception:report['error']=traceback.format_exc();u.log_error(report['error'])
(OUT/'build-report.json').write_text(json.dumps(report,indent=2))
def quit(dt):
 u.unregister_slate_post_tick_callback(handle);u.SystemLibrary.quit_editor()
u.EditorPythonScripting.set_keep_python_script_alive(True);handle=u.register_slate_post_tick_callback(quit)
