"""Install a bank-owned fitted forest-floor layer without changing the terrain or plants."""
import unreal as u,json,sys,hashlib
from pathlib import Path
ROOT=Path(u.Paths.project_dir()).resolve();sys.path.insert(0,str(ROOT/'Art/Unreal'))
import lidar_first_section as section
from benmore_river_life_materials import Graph,props
BASE=section.DEST;DEST=BASE+'/FernFloor';OUT=ROOT/'Art/Export/LidarStudy/FirstSection/FernFloor';QA=ROOT/'Saved/LidarAuthoringQA/FernFloor'
mel=u.MaterialEditingLibrary;assets=u.EditorAssetLibrary
CONTACT='''
float2 p=P.xy-float2(-45800,-31600);
float2 ab=float2(.6*p.x-.8*p.y,-.8*p.x-.6*p.y);
float2 uv=float2(ab.x/2200+.5,.5-ab.y/1560);
float inside=(abs(ab.x)<1100 && abs(ab.y)<780)?1:0;
float occ=lerp(1,Texture2DSample(Contact,ContactSampler,uv).r,inside);
occ=lerp(1,occ,Strength);
OutAO=min(OldAO,occ);
// Stable short-range cavity shading comes from ray tests against the actual
// fern stand and fitted floor, independent of the sun direction.
float shade=.18+.82*pow(max(.3,occ),.9);
float covered=smoothstep(.08,.48,1-occ);
float mottled=.70+.30*sin(P.x*.047+sin(P.y*.051))*sin(P.y*.039);
float value=dot(OldColour,float3(.25,.6,.15));
float3 earth=float3(.18,.125,.065)*(value/.15);
return lerp(OldColour,earth,covered*mottled*.52)*shade;
'''

def install_material():
 import peat_moss_ground
 if peat_moss_ground.enabled():return peat_moss_ground.ground()
 texture=u.load_asset(DEST+'/T_FernFloor_Contact');assert texture
 import lidar_bank_material_polish as polish
 contact_code=polish.CONTACT if polish.enabled() else CONTACT
 m=u.load_asset(BASE+'/M_BankSurface');g=Graph(m,'FFContact')
 existing=next((n for n in mel.get_material_expressions(m) if isinstance(n,u.MaterialExpressionCustom) and str(n.get_editor_property('desc'))=='FFContact'),None)
 if existing:existing.set_editor_property('code',contact_code)
 else:
  sources=[(mel.get_material_property_input_node(m,p),mel.get_material_property_input_node_output_name(m,p)) for p in [u.MaterialProperty.MP_BASE_COLOR,u.MaterialProperty.MP_AMBIENT_OCCLUSION]]
  n=g.custom(['P','Contact','OldColour','OldAO','Strength'],contact_code,outputs=[('OutAO',u.CustomMaterialOutputType.CMOT_FLOAT1)])
  g.wire(g.node(u.MaterialExpressionWorldPosition),n,'P');g.wire(g.node(u.MaterialExpressionTextureObject,texture=texture,sampler_type=u.MaterialSamplerType.SAMPLERTYPE_LINEAR_COLOR),n,'Contact')
  g.wire(g.node(u.MaterialExpressionScalarParameter,parameter_name='FF_ContactStrength',default_value=1.),n,'Strength')
  for key,(node,out) in zip(['OldColour','OldAO'],sources):g.wire(node,n,key,out)
  g.output(n,u.MaterialProperty.MP_BASE_COLOR);g.output(n,u.MaterialProperty.MP_AMBIENT_OCCLUSION,'OutAO')
 assert not mel.recompile_material(m);assert assets.save_loaded_asset(m,False)
 return m

def run():
 import peat_moss_ground
 if peat_moss_ground.enabled():return peat_moss_ground.run()
 before=section.snapshot();outside=section.outside_snapshot();assets.make_directory(DEST)
 original=json.loads((ROOT/'Saved/LidarAuthoringQA/ShrubShadows/installed.json').read_text());assert before==original['local'] and outside==original['outside']
 bake=json.loads((OUT/'bake.json').read_text());placement=json.loads((section.QA/'placement.json').read_text())['placement']
 assert hashlib.sha256(json.dumps(placement,sort_keys=True).encode()).hexdigest()==bake['source_placement_sha256']
 task=props(u.AssetImportTask(),filename=str(OUT/'T_FernFloor_Contact.png'),destination_path=DEST,destination_name='T_FernFloor_Contact',automated=True,replace_existing=True,save=True)
 u.AssetToolsHelpers.get_asset_tools().import_asset_tasks([task]);texture=u.load_asset(DEST+'/T_FernFloor_Contact')
 props(texture,srgb=False,compression_settings=u.TextureCompressionSettings.TC_MASKS,never_stream=True,max_texture_size=512,lod_bias=0,address_x=u.TextureAddress.TA_CLAMP,address_y=u.TextureAddress.TA_CLAMP)
 assets.save_loaded_asset(texture,False);install_material()
 m=u.load_asset(DEST+'/M_FernFloor') or u.AssetToolsHelpers.get_asset_tools().create_asset('M_FernFloor',DEST,u.Material,u.MaterialFactoryNew())
 mel.delete_all_material_expressions(m);props(m,two_sided=True,shading_model=u.MaterialShadingModel.MSM_DEFAULT_LIT)
 g=Graph(m,'FFLitter');vc=g.node(u.MaterialExpressionVertexColor);col=g.custom(['C','AO'],'return C*(.5+.5*AO);');g.wire(vc,col,'C');g.wire(vc,col,'AO','A');g.output(col,u.MaterialProperty.MP_BASE_COLOR);g.output(vc,u.MaterialProperty.MP_AMBIENT_OCCLUSION,'A');g.output(g.scalar(.94),u.MaterialProperty.MP_ROUGHNESS);g.output(g.scalar(.08),u.MaterialProperty.MP_SPECULAR)
 assert not mel.recompile_material(m);assets.save_loaded_asset(m,False)
 world=u.get_editor_subsystem(u.UnrealEditorSubsystem).get_editor_world();u.SystemLibrary.execute_console_command(world,'Interchange.FeatureFlags.Import.FBX 0')
 task=props(u.AssetImportTask(),filename=str(OUT/'SM_FernFloor_Litter.fbx'),destination_path=DEST,destination_name='SM_FernFloor_Litter',automated=True,replace_existing=True,save=True)
 opt=props(u.FbxImportUI(),import_mesh=True,import_materials=False,import_textures=False,import_as_skeletal=False,mesh_type_to_import=u.FBXImportType.FBXIT_STATIC_MESH)
 props(opt.static_mesh_import_data,combine_meshes=True,auto_generate_collision=False,generate_lightmap_u_vs=False,vertex_color_import_option=u.VertexColorImportOption.REPLACE,normal_import_method=u.FBXNormalImportMethod.FBXNIM_IMPORT_NORMALS);task.options=opt
 u.AssetToolsHelpers.get_asset_tools().import_asset_tasks([task]);mesh=u.load_asset(DEST+'/SM_FernFloor_Litter');sm=u.get_editor_subsystem(u.StaticMeshEditorSubsystem);sm.remove_collisions(mesh)
 for i in range(len(mesh.get_editor_property('static_materials'))):mesh.set_material(i,m)
 assert mesh.get_bounds().box_extent.x>800 and mesh.get_bounds().box_extent.x<1600
 assert assets.save_loaded_asset(mesh,False)
 actors=u.get_editor_subsystem(u.EditorActorSubsystem);label='LidarStudy_RS7_FernFloor';a=next((a for a in actors.get_all_level_actors() if a.get_actor_label()==label),None)
 if not a:a=actors.spawn_actor_from_class(u.StaticMeshActor,u.Vector(*bake['world_origin']))
 a.modify();a.set_actor_label(label);a.set_actor_location(u.Vector(*bake['world_origin']),False,True);c=a.static_mesh_component;c.set_static_mesh(mesh);c.set_collision_profile_name('NoCollision');c.set_collision_enabled(u.CollisionEnabled.NO_COLLISION)
 props(c,cast_shadow=True,cast_shadow_as_two_sided=True,affect_distance_field_lighting=False,visible_in_ray_tracing=False)
 assert section.snapshot()==before and section.outside_snapshot()==outside
 validation=section.validate();assert u.get_editor_subsystem(u.LevelEditorSubsystem).save_current_level()
 (QA/'installed.json').write_text(json.dumps(dict(ok=True,bake=bake,validation=validation,local=before,outside=outside,geometry=mesh.get_path_name(),actor=label,collision=str(c.get_collision_enabled()),material=BASE+'/M_BankSurface',map_saved=True),indent=2));print('FERN_FLOOR_INSTALLED')
