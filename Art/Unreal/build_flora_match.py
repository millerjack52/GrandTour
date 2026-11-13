"""Isolated source-colour fidelity trial; never edit the woodland or first pilot."""
import unreal as u
import json,traceback,hashlib
from pathlib import Path
ROOT=Path(u.Paths.project_dir()).resolve();OUT=ROOT/'Art/Export/LidarStudy/FloraMatch'
DEST='/Game/GrandTour/ArtTests/FloraMatch';OLD='/Game/GrandTour/ArtTests/FloraPilot'
eal=u.EditorAssetLibrary;mel=u.MaterialEditingLibrary;at=u.AssetToolsHelpers.get_asset_tools()
les=u.get_editor_subsystem(u.LevelEditorSubsystem);actors=u.get_editor_subsystem(u.EditorActorSubsystem);sm=u.get_editor_subsystem(u.StaticMeshEditorSubsystem)
report={'ok':False,'woodland_modified':False,'performance_verified':False,'meshes':[],'materials':[]}
def props(o,**kw):
 for k,v in kw.items():o.set_editor_property(k,v)
 return o
def node(m,cls,**kw):return props(mel.create_material_expression(m,cls),**kw)
def wire(a,b,p,out=''):assert mel.connect_material_expressions(a,out,b,p)
def output(n,p,out=''):assert mel.connect_material_property(n,out,p)
def scalar(m,k,v):return node(m,u.MaterialExpressionScalarParameter,parameter_name=k,default_value=v)
def fresh(name):
 m=u.load_asset(DEST+'/'+name) or at.create_asset(name,DEST,u.Material,u.MaterialFactoryNew());mel.delete_all_material_expressions(m);return m
def custom(m,names,code,kind=u.CustomMaterialOutputType.CMOT_FLOAT3):return node(m,u.MaterialExpressionCustom,code=code,output_type=kind,inputs=[props(u.CustomInput(),input_name=n) for n in names])
SETTINGS={
 'Leaf_0':('plant_0',.31075698,[(0,0),(.1681818,.4196344),(.5545454,1)]),
 'Shrubbery':('shrubbery_0',.82898891,[(0,0),(.9227271,1)]),
 'Grass':('grass_0',.87250996,[(0,0),(.3818181,.5),(1,1)]),
 'Grass.003':('grass_0',.73306769,[(0,0),(.3954544,.5),(.5409092,1)]),
 'Plant_0.001':('plant_0',.41723648,[(0,0),(1,1)])}
def material(name,key,colour_tex):
 m=fresh(name);mel.set_material_usage(m,u.MaterialUsage.MATUSAGE_INSTANCED_STATIC_MESHES)
 if key=='Wood_material':
  col=node(m,u.MaterialExpressionTextureSampleParameter2D,parameter_name='SourceColour',texture=colour_tex,sampler_type=u.MaterialSamplerType.SAMPLERTYPE_COLOR)
  wire(node(m,u.MaterialExpressionTextureCoordinate,coordinate_index=1),col,'UVs');output(col,u.MaterialProperty.MP_BASE_COLOR)
  output(scalar(m,'Roughness',.94),u.MaterialProperty.MP_ROUGHNESS);output(scalar(m,'Specular',.08),u.MaterialProperty.MP_SPECULAR)
 else:
  tex,soft,ramp=SETTINGS[key]
  props(m,two_sided=True,tangent_space_normal=False,dither_opacity_mask=True,has_pixel_animation=False,blend_mode=u.BlendMode.BLEND_MASKED,shading_model=u.MaterialShadingModel.MSM_DEFAULT_LIT,opacity_mask_clip_value=.5)
  mask=node(m,u.MaterialExpressionTextureSampleParameter2D,parameter_name='SourceMask',texture=u.load_asset(DEST+'/T_SourceMask_'+tex),sampler_type=u.MaterialSamplerType.SAMPLERTYPE_LINEAR_GRAYSCALE)
  col=node(m,u.MaterialExpressionTextureSampleParameter2D,parameter_name='SourceColour',texture=colour_tex,sampler_type=u.MaterialSamplerType.SAMPLERTYPE_COLOR)
  wire(node(m,u.MaterialExpressionTextureCoordinate,coordinate_index=1),col,'UVs')
  tinted=node(m,u.MaterialExpressionMultiply);wire(col,tinted,'A');wire(node(m,u.MaterialExpressionVectorParameter,parameter_name='ColourMultiplier',default_value=u.LinearColor(1,1,1,1)),tinted,'B');output(tinted,u.MaterialProperty.MP_BASE_COLOR)
  normal=node(m,u.MaterialExpressionVertexNormalWS);view=node(m,u.MaterialExpressionCameraVectorWS)
  code='Mask=Mask<.04045?Mask/12.92:pow((Mask+.055)/1.055,2.4);float a=1; '+' else '.join(f'if(Mask<{x1}) a=lerp({y0},{y1},saturate((Mask-{x0})/{x1-x0}));' for (x0,y0),(x1,y1) in zip(ramp,ramp[1:]))
  code+='float b=clamp(Soft,.001,.98);float power=b<.5?2*b:.5/(1-b);float facing=pow(saturate(abs(dot(normalize(N),normalize(V)))),power);return saturate(a*lerp(.1,1.,facing)*.9333333*Density);'
  coverage=custom(m,['Mask','Soft','N','V','Density'],code,u.CustomMaterialOutputType.CMOT_FLOAT1)
  wire(mask,coverage,'Mask','R');wire(normal,coverage,'N');wire(view,coverage,'V');wire(scalar(m,'SourceEdgeSoftness',soft),coverage,'Soft');wire(scalar(m,'CoverageMultiplier',1),coverage,'Density')
  seed=node(m,u.MaterialExpressionVertexColor)
  dither=custom(m,['Coverage','Seed','Frame'],'uint leaf=(uint)(saturate(Seed)*4095.);uint2 p=(uint2)Parameters.SvPosition.xy+uint2(leaf*37u,leaf*91u);return step(ViewScalarBlueNoise(p,(uint)Frame),Coverage);',u.CustomMaterialOutputType.CMOT_FLOAT1)
  wire(coverage,dither,'Coverage');wire(seed,dither,'Seed','R');wire(custom(m,[],'return View.StateFrameIndex;',u.CustomMaterialOutputType.CMOT_FLOAT1),dither,'Frame')
  shadow=custom(m,['Coverage','Seed'],'uint leaf=(uint)(saturate(Seed)*4095.);uint2 p=(uint2)Parameters.SvPosition.xy+uint2(leaf*37u,leaf*91u);return step(ViewScalarBlueNoise(p,0u),Coverage);',u.CustomMaterialOutputType.CMOT_FLOAT1)
  wire(coverage,shadow,'Coverage');wire(seed,shadow,'Seed','R')
  switch=node(m,u.MaterialExpressionShadowReplace);wire(dither,switch,'Default');wire(shadow,switch,'Shadow');output(switch,u.MaterialProperty.MP_OPACITY_MASK)
  litnormal=custom(m,['N','Blend'],'return normalize(lerp(normalize(N),float3(0,0,1),Blend));');wire(normal,litnormal,'N');wire(scalar(m,'SourceUpNormals',1),litnormal,'Blend');output(litnormal,u.MaterialProperty.MP_NORMAL)
  output(scalar(m,'Roughness',1),u.MaterialProperty.MP_ROUGHNESS);output(scalar(m,'Specular',.03),u.MaterialProperty.MP_SPECULAR)
  # Wind remains disabled for source matching. The baked atlas is unlit colour.
 mel.recompile_material(m);assert eal.save_loaded_asset(m)
 instname=name.replace('M_','MI_',1);mi=u.load_asset(DEST+'/'+instname) or at.create_asset(instname,DEST,u.MaterialInstanceConstant,u.MaterialInstanceConstantFactoryNew());mel.set_material_instance_parent(mi,m);eal.save_loaded_asset(mi)
 report['materials'].append({'path':m.get_path_name(),'source_material':key,'authored_texture_samples':1 if key=='Wood_material' else 2})
 return mi
def restore_pilot_mesh_links():
 # SaveMap writes a copy without switching the active editor world. A prior
 # attempt therefore saved the copied mesh assignments back into the pilot.
 # Restore only those known assignments, leaving all placement/light settings.
 assert les.load_level(OLD+'/L_FloraPilot')
 count=0
 for actor in actors.get_all_level_actors():
  if isinstance(actor,u.StaticMeshActor):
   component=actor.static_mesh_component;mesh=component.static_mesh
   if mesh and mesh.get_path_name().startswith(DEST+'/SM_Match_'):
    original=u.load_asset(OLD+'/SM_Flora_'+mesh.get_name().removeprefix('SM_Match_'));assert original
    component.set_static_mesh(original);count+=1
 if count:assert les.save_current_level()
 return count
try:
 eal.make_directory(DEST)
 report['pilot_mesh_links_restored']=restore_pilot_mesh_links()
 level=DEST+'/L_FloraMatch'
 if not eal.does_asset_exist(level):
  assert les.load_level(OLD+'/L_FloraPilot')
  assert u.EditorLoadingAndSavingUtils.save_map(u.get_editor_subsystem(u.UnrealEditorSubsystem).get_editor_world(),level)
  assert les.load_level(level)
 else:assert les.load_level(level)
 world=u.get_editor_subsystem(u.UnrealEditorSubsystem).get_editor_world();u.SystemLibrary.execute_console_command(world,'Interchange.FeatureFlags.Import.FBX 0')
 for name in ['plant_0','shrubbery_0','grass_0']:
  path=DEST+'/T_SourceMask_'+name;mask=eal.duplicate_asset(OLD+'/T_Flora_'+name,path) if not eal.does_asset_exist(path) else u.load_asset(path)
  props(mask,compression_settings=u.TextureCompressionSettings.TC_GRAYSCALE,srgb=False,max_texture_size=4096);eal.save_loaded_asset(mask)
 manifest=json.loads((OUT/'source-colour-manifest.json').read_text());models={}
 for row in manifest:
  colour_name='T_'+row['source']+'_Colour'
  task=props(u.AssetImportTask(),filename=str(OUT/row['colour_atlas']),destination_path=DEST,destination_name=colour_name,automated=True,replace_existing=True,save=True);at.import_asset_tasks([task]);tex=u.load_asset(DEST+'/'+colour_name);assert tex
  props(tex,srgb=True,compression_settings=u.TextureCompressionSettings.TC_DEFAULT,max_texture_size=row['colour_atlas_size']);eal.save_loaded_asset(tex)
  materials=[material('M_'+row['source']+'_'+key.replace('.','_'),key,tex) for key in row['materials']]
  task=props(u.AssetImportTask(),filename=str(OUT/(row['mesh']+'.fbx')),destination_path=DEST,destination_name=row['mesh'],automated=True,replace_existing=True,save=True)
  opt=props(u.FbxImportUI(),import_mesh=True,import_as_skeletal=False,import_materials=False,import_textures=False,import_animations=False,mesh_type_to_import=u.FBXImportType.FBXIT_STATIC_MESH)
  props(opt.static_mesh_import_data,combine_meshes=True,auto_generate_collision=False,generate_lightmap_u_vs=False,normal_import_method=u.FBXNormalImportMethod.FBXNIM_IMPORT_NORMALS,vertex_color_import_option=u.VertexColorImportOption.REPLACE);task.options=opt;at.import_asset_tasks([task])
  mesh=u.load_asset(DEST+'/'+row['mesh']);assert mesh
  for idx,mat in enumerate(materials):mesh.set_material(idx,mat)
  build=sm.get_lod_build_settings(mesh,0);props(build,recompute_normals=False,recompute_tangents=True);sm.set_lod_build_settings(mesh,0,build);sm.remove_collisions(mesh)
  triangles=mesh.get_static_mesh_description(0).get_triangle_count();assert triangles==row['triangles']
  assert sm.get_num_uv_channels(mesh,0)==2
  eal.save_loaded_asset(mesh);models[row['source'].removeprefix('FP_')]=mesh
  report['meshes'].append({'mesh':mesh.get_path_name(),'triangles':triangles,'uv_channels':2,'colour_atlas':row['colour_atlas']})
 for a in actors.get_all_level_actors():
  if isinstance(a,u.StaticMeshActor):
   c=a.static_mesh_component;mesh=c.static_mesh
   if mesh and mesh.get_name().startswith('SM_Flora_'):c.set_static_mesh(models[mesh.get_name().removeprefix('SM_Flora_')])
 assert les.save_current_level()
 for row in report['materials']:
  stats=mel.get_statistics(u.load_asset(row['path']));row['compiled_stats']={k:getattr(stats,k) for k in ['num_pixel_shader_instructions','num_vertex_shader_instructions','num_pixel_texture_samples']}
 protected=json.loads((ROOT/'Art/Export/LidarStudy/FloraShader/protected-before.json').read_text())
 for row in protected:
  with Path(row['file']).open('rb') as f:row['unchanged']=hashlib.file_digest(f,'sha256').hexdigest()==row['sha256']
  if '/FloraPilot/L_FloraPilot.umap' in Path(row['file']).as_posix():
   row['note']='Pilot was re-saved after restoring its original mesh assignments; file hash may differ. Production map and original meshes must remain byte-identical.'
  else:assert row['unchanged'],row['file']
 report['protected']=protected;report['ok']=True
except Exception:report['error']=traceback.format_exc();u.log_error(report['error'])
(OUT/'unreal-build.json').write_text(json.dumps(report,indent=2))
def quit(dt):
 u.unregister_slate_post_tick_callback(handle);u.SystemLibrary.quit_editor()
u.EditorPythonScripting.set_keep_python_script_alive(True);handle=u.register_slate_post_tick_callback(quit)
