"""Depth-reprojected 24-view proxy in a bounded, transform-preserving tree stand."""
import unreal as u,json,math,sys,hashlib
from pathlib import Path
ROOT=Path(u.Paths.project_dir()).resolve();sys.path.insert(0,str(ROOT/'Art/Unreal'))
from benmore_river_life_materials import Graph,props
BASE='/Game/GrandTour/ArtTests/LidarStudy';PD=BASE+'/FirstSection/PerceivedDetail'
OUT=ROOT/'Art/Export/LidarStudy/FirstSection/PerceivedDetail';QA=ROOT/'Saved/LidarAuthoringQA/PerceivedDetail'
actors=u.get_editor_subsystem(u.EditorActorSubsystem);assets=u.EditorAssetLibrary;mel=u.MaterialEditingLibrary;sm=u.get_editor_subsystem(u.StaticMeshEditorSubsystem)
def position(g,node,src,dst,output=''):
 n=g.node(u.MaterialExpressionTransformPosition,transform_source_type=src,transform_type=dst);g.wire(node,n,'',output);return n
def material(data):
 textures={}
 for name,linear in [('T_PD_TreeColour',False),('T_PD_TreeNormalDepth',True)]:
  capture=OUT/(name+'.tga')
  if linear and data.get('canopy_depth') and (OUT/'T_CD_VolumeNormalDepth.tga').exists():capture=OUT/'T_CD_VolumeNormalDepth.tga'
  t=props(u.AssetImportTask(),filename=str(capture),destination_path=PD,destination_name=name,automated=True,replace_existing=True,save=True)
  u.AssetToolsHelpers.get_asset_tools().import_asset_tasks([t]);tex=u.load_asset(PD+'/'+name)
  props(tex,srgb=not linear,never_stream=data.get('canopy_depth',False) or not data.get('streaming',False),max_texture_size=2048,lod_bias=0,address_x=u.TextureAddress.TA_CLAMP,address_y=u.TextureAddress.TA_CLAMP)
  if data.get('streaming'):props(tex,mip_gen_settings=u.TextureMipGenSettings.TMGS_SIMPLE_AVERAGE,compression_settings=u.TextureCompressionSettings.TC_BC7)
  elif linear:props(tex,compression_settings=u.TextureCompressionSettings.TC_VECTOR_DISPLACEMENTMAP)
  else:props(tex,do_scale_mips_for_alpha_coverage=True,alpha_coverage_thresholds=u.Vector4(0,0,0,.35))
  assets.save_loaded_asset(tex);textures[name]=tex
 m=u.load_asset(PD+'/M_PD_TreeProxy') or u.AssetToolsHelpers.get_asset_tools().create_asset('M_PD_TreeProxy',PD,u.Material,u.MaterialFactoryNew())
 # Deleted custom expressions may remain as transient subobjects in UE. Make
 # them harmless before replacing the graph, including old WPO expressions.
 for expression in mel.get_material_expressions(m):
  if isinstance(expression,u.MaterialExpressionCustom):
   expression.set_editor_property('code','return 0;');expression.set_editor_property('inputs',[])
 mel.delete_all_material_expressions(m);g=Graph(m,'PDProxy')
 uv=g.node(u.MaterialExpressionTextureCoordinate);world=u.MaterialPositionTransformSource.TRANSFORMPOSSOURCE_WORLD;instance=u.MaterialPositionTransformSource.TRANSFORMPOSSOURCE_INSTANCE
 cam=position(g,g.node(u.MaterialExpressionCameraPositionWS),world,instance)
 centre=g.vector(data['centre']);size=g.scalar(data['size_cm'])
 plane=g.custom(['Camera','Centre','UV','Size'],'''float3 D=normalize(Camera-Centre);float3 R=normalize(cross(abs(D.z)>.999?float3(0,1,0):float3(0,0,1),D));float3 U=cross(D,R);return Centre+(R*(UV.x-.5)+U*(.5-UV.y))*Size;''')
 for a,key in [(cam,'Camera'),(centre,'Centre'),(uv,'UV'),(size,'Size')]:g.wire(a,plane,key)
 plane_world=position(g,plane,instance,world)
 wpo=g.node(u.MaterialExpressionSubtract);g.wire(plane_world,wpo,'A');g.wire(g.node(u.MaterialExpressionWorldPosition),wpo,'B');g.output(wpo,u.MaterialProperty.MP_WORLD_POSITION_OFFSET)
 code='''
struct Proxy {
 void frame(float az,float el,float3 L,float3 D,float Size,Texture2D CT,SamplerState CS,Texture2D NT,SamplerState NS,out float4 colour,out float3 normal,out float3 surface){
  float a=az*6.28318530718/8,e=el*.6108652382;
  float3 V=float3(cos(e)*cos(a),cos(e)*sin(a),sin(e));
  // SceneCapture looks toward -V: its screen right is cross(Z,-V).
  float3 R=float3(sin(a),-cos(a),0),U=cross(R,V);
  float2 uv=float2(dot(L,R)/Size+.5,.5-dot(L,U)/Size);
  float2 cell=float2(az,el),grid=float2(8,3);
  float2 at=(cell+clamp(uv,.002,.998))/grid;
  float z=(Texture2DSample(NT,NS,at).a-.5)*2*Size;
  float t=(z-dot(L,V))/max(.22,dot(D,V));
  float3 hit=L+D*t;surface=hit;
  uv=float2(dot(hit,R)/Size+.5,.5-dot(hit,U)/Size);
  float valid=all(uv>0)&&all(uv<1);
  at=(cell+clamp(uv,.002,.998))/grid;
  colour=Texture2DSample(CT,CS,at);colour.a*=valid;
  normal=Texture2DSample(NT,NS,at).rgb*2-1;
 }
};Proxy p;
float3 D=normalize(Camera-Centre),L=Plane-Centre;
float a=frac(atan2(D.y,D.x)/6.28318530718+1)*8;
float e=clamp(asin(D.z)/.6108652382,0,1.999);
float az=floor(a),el=floor(e),fa=frac(a),fe=frac(e);
float4 total=0;float3 normals=0;float3 surfaces=0;float coverage=0;
[unroll] for(int j=0;j<4;j++){
 float ia=fmod(az+(j%2),8),ie=el+(j/2);
 float w=(j%2?fa:1-fa)*(j/2?fe:1-fe);
 float4 c;float3 n;float3 h;p.frame(ia,ie,L,D,Size,ColourTex,ColourTexSampler,NormalTex,NormalTexSampler,c,n,h);
 total.rgb+=c.rgb*c.a*w;normals+=n*c.a*w;surfaces+=h*c.a*w;coverage+=c.a*w;
}
Opacity=coverage;LocalNormal=normalize(normals+float3(0,0,.00001));
LocalSurface=Centre+surfaces/max(coverage,.001);
return total.rgb/max(coverage,.001);
'''
 code=code.replace('grid=float2(8,3)','grid=float2(8,%d)'%data.get('grid_rows',3))
 if data.get('canopy_depth'):
  code=code.replace('colour=Texture2DSample(CT,CS,at);colour.a*=valid;', '''colour=Texture2DSample(CT,CS,at);colour.a*=valid;
  // Crown enclosure: lower, interior foliage receives less sky illumination.
  // hit is reconstructed from the captured depth, not a flat-card UV gradient.
  float leaf=smoothstep(1.08,1.30,colour.g/max(colour.r,.001));
  float enclosure=lerp(.24,1.85,smoothstep(-.08,.28,hit.z/Size));
  colour.rgb*=lerp(1,enclosure,leaf);''')
 node=g.custom(['Camera','Centre','Plane','Size','ColourTex','NormalTex'],code,outputs=[('Opacity',u.CustomMaterialOutputType.CMOT_FLOAT1),('LocalNormal',u.CustomMaterialOutputType.CMOT_FLOAT3),('LocalSurface',u.CustomMaterialOutputType.CMOT_FLOAT3)])
 for a,key in [(cam,'Camera'),(centre,'Centre'),(plane,'Plane'),(size,'Size')]:g.wire(a,node,key)
 for key,name,linear in [('ColourTex','T_PD_TreeColour',False),('NormalTex','T_PD_TreeNormalDepth',True)]:g.wire(g.node(u.MaterialExpressionTextureObject,texture=textures[name],sampler_type=u.MaterialSamplerType.SAMPLERTYPE_LINEAR_COLOR if linear else u.MaterialSamplerType.SAMPLERTYPE_COLOR),node,key)
 normal=g.node(u.MaterialExpressionTransform,transform_source_type=u.MaterialVectorCoordTransformSource.TRANSFORMSOURCE_INSTANCE,transform_type=u.MaterialVectorCoordTransform.TRANSFORM_WORLD);g.wire(node,normal,'','LocalNormal')
 g.output(node,u.MaterialProperty.MP_BASE_COLOR);g.output(node,u.MaterialProperty.MP_OPACITY_MASK,'Opacity');g.output(normal,u.MaterialProperty.MP_NORMAL)
 g.output(g.scalar(.88),u.MaterialProperty.MP_ROUGHNESS);g.output(g.scalar(.05),u.MaterialProperty.MP_SPECULAR)
 props(m,blend_mode=u.BlendMode.BLEND_MASKED,two_sided=True,tangent_space_normal=False,opacity_mask_clip_value=.35,dithered_lod_transition=True)
 if data.get('canopy_depth'):
  # Colour captures already contain the approved foliage tint. Apply only gentle
  # stand variation and enclosed-crown darkening; do not tint the bake twice.
  shade=g.custom(['C','N','P','Rand'],'''float leaf=smoothstep(1.05,1.30,C.g/max(C.r,.001));float top=saturate(N.z*.5+.5);float patch=.5+.5*sin(P.x*.00043+P.y*.00031);float3 palette=lerp(float3(.91,1.01,1.08),float3(1.04,1.01,.92),patch);float3 c=C*lerp(float3(1,1,1),palette*lerp(.94,1.06,Rand)*lerp(.76,1.06,top),leaf);AO=lerp(1,lerp(.65,1,top),leaf);Transmission=c*.08*leaf;return c;''',outputs=[('AO',u.CustomMaterialOutputType.CMOT_FLOAT1),('Transmission',u.CustomMaterialOutputType.CMOT_FLOAT3)])
  for a,key,out in [(node,'C',''),(node,'N','LocalNormal'),(g.node(u.MaterialExpressionWorldPosition),'P',''),(g.node(u.MaterialExpressionPerInstanceRandom),'Rand','')]:g.wire(a,shade,key,out)
  g.output(shade,u.MaterialProperty.MP_BASE_COLOR);g.output(shade,u.MaterialProperty.MP_AMBIENT_OCCLUSION,'AO');g.output(shade,u.MaterialProperty.MP_SUBSURFACE_COLOR,'Transmission')
  props(m,shading_model=u.MaterialShadingModel.MSM_TWO_SIDED_FOLIAGE)
 mel.set_material_usage(m,u.MaterialUsage.MATUSAGE_INSTANCED_STATIC_MESHES)
 assert not mel.recompile_material(m);assets.save_loaded_asset(m,False);return m

def install():
 data=json.loads((OUT/'tree-bake.json').read_text());m=material(data)
 c=data['centre'];h=data['size_cm']/2
 # Import a fixed square; vertex shader turns it into an instance-local billboard.
 lines=[]
 for y,z in [(-h,-h),(h,-h),(h,h),(-h,h)]:lines.append('v %f %f %f'%(c[0],c[1]+y,c[2]+z))
 lines+=['vt 0 1','vt 1 1','vt 1 0','vt 0 0','f 1/1 2/2 3/3','f 1/1 3/3 4/4']
 f=OUT/'SM_PD_Proxy.obj';f.write_text('\n'.join(lines))
 world=u.get_editor_subsystem(u.UnrealEditorSubsystem).get_editor_world();u.SystemLibrary.execute_console_command(world,'Interchange.FeatureFlags.Import.FBX 0')
 task=props(u.AssetImportTask(),filename=str(f),destination_path=PD,destination_name='SM_PD_Proxy',automated=True,replace_existing=True,save=True)
 opt=props(u.FbxImportUI(),import_mesh=True,import_materials=False,import_textures=False,import_as_skeletal=False,mesh_type_to_import=u.FBXImportType.FBXIT_STATIC_MESH)
 props(opt.static_mesh_import_data,combine_meshes=True,auto_generate_collision=False,convert_scene=False,convert_scene_unit=False);task.options=opt
 u.AssetToolsHelpers.get_asset_tools().import_asset_tasks([task]);proxy=u.load_asset(PD+'/SM_PD_Proxy');proxy.set_material(0,m);assets.save_loaded_asset(proxy)
 source=u.load_asset(BASE+'/CanopyKit/SM_Canopy_0');mesh=u.load_asset(PD+'/SM_PD_Canopy_0') or assets.duplicate_asset(source.get_path_name().split('.')[0],PD+'/SM_PD_Canopy_0')
 assert sm.set_lod_from_static_mesh(mesh,3,proxy,0,True)==3
 sm.set_lod_screen_sizes(mesh,list(sm.get_lod_screen_sizes(source)))
 for i in range(mesh.get_num_sections(3)):sm.enable_section_cast_shadow(mesh,False,3,i)
 assets.save_loaded_asset(mesh)
 stand=next((a for a in actors.get_all_level_actors() if a.get_actor_label()=='LidarStudy_PD_Stand'),None)
 if stand:
  for c in stand.get_components_by_class(u.InstancedStaticMeshComponent):c.set_static_mesh(mesh)
 else:
  forest=next(a for a in actors.get_all_level_actors() if a.get_actor_label()=='LidarStudy_Forest')
  c=next(c for c in forest.get_components_by_class(u.InstancedStaticMeshComponent) if c.static_mesh==source)
  selected=[]
  for i in range(c.get_instance_count()):
   t=c.get_instance_transform(i,True);p=t.translation
   if -61000<p.x<-45000 and 34000<p.y<55000:selected.append((i,t))
  selected=selected[::max(1,len(selected)//48)][:48];assert len(selected)>10,len(selected)
  stand=actors.spawn_actor_from_class(u.Actor,u.Vector());stand.set_actor_label('LidarStudy_PD_Stand');stand.root_component.set_mobility(u.ComponentMobility.STATIC)
  new=u.GTVegetationSubsystem.add_tagged_instances(stand,mesh,[t for _,t in selected],'PDTreeProxy','NoCollision',True)
  new.set_cull_distances(c.get_editor_property('instance_start_cull_distance'),c.get_editor_property('instance_end_cull_distance'));new.set_lod_distance_scale(c.get_editor_property('instance_lod_distance_scale'))
  for k in ['cast_shadow','affect_distance_field_lighting','visible_in_ray_tracing','world_position_offset_disable_distance']:new.set_editor_property(k,c.get_editor_property(k))
  # Billboard turning is required at all distances, so it cannot inherit a wind cutoff.
  new.set_editor_property('world_position_offset_disable_distance',0)
  for slot in range(2):new.set_material(slot,c.get_material(slot))
  import lidar_first_section as section
  original=[section.tfkey(t) for _,t in selected]
  actual=[section.tfkey(new.get_instance_transform(i,True)) for i in range(new.get_instance_count())]
  errors=[max(abs(x-y) for x,y in zip(a,b)) for a,b in zip(original,actual)]
  (QA/'stand.json').write_text(json.dumps(dict(count=new.get_instance_count(),original_component=c.get_name(),transforms=original,actual_transforms=actual,max_component_error=max(errors),bounds_cm=[-61000,-45000,34000,55000]),indent=2))
  assert max(errors)<.01, max(errors)
  before=c.get_instance_count();assert c.remove_instances(sorted([i for i,_ in selected],reverse=True))
  assert before==c.get_instance_count()+new.get_instance_count()
 assert u.get_editor_subsystem(u.LevelEditorSubsystem).save_current_level()
 (QA/'proxy-install.json').write_text(json.dumps(dict(ok=True,views=24,kind='8 azimuth x 3 elevation depth-reprojected impostor',mesh=mesh.get_path_name(),screens=list(sm.get_lod_screen_sizes(mesh)),vertices=[sm.get_number_verts(mesh,i) for i in range(4)]),indent=2))

