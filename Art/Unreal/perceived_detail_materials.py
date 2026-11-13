"""Bounded surface-depth prototype and one fern species' baked detail."""
import unreal as u,json,sys
from pathlib import Path
ROOT=Path(u.Paths.project_dir()).resolve();sys.path.insert(0,str(ROOT/'Art/Unreal'))
from benmore_river_life_materials import Graph,props
DEST='/Game/GrandTour/ArtTests/LidarStudy/FirstSection';PD=DEST+'/PerceivedDetail'
OUT=ROOT/'Art/Export/LidarStudy/FirstSection/PerceivedDetail';QA=ROOT/'Saved/LidarAuthoringQA/PerceivedDetail'
mel=u.MaterialEditingLibrary;assets=u.EditorAssetLibrary
def textures():
 result={}
 for name in ['T_PD_SoilNH','T_PD_RockNH','T_PD_LeafNH']:
  task=props(u.AssetImportTask(),filename=str(OUT/(name+'.png')),destination_path=PD,destination_name=name,automated=True,replace_existing=True,save=True)
  u.AssetToolsHelpers.get_asset_tools().import_asset_tasks([task]);t=u.load_asset(PD+'/'+name);assert t
  props(t,srgb=False,compression_settings=u.TextureCompressionSettings.TC_VECTOR_DISPLACEMENTMAP,never_stream=True,lod_bias=0,max_texture_size=1024)
  if 'Leaf' in name:props(t,address_x=u.TextureAddress.TA_CLAMP,address_y=u.TextureAddress.TA_CLAMP)
  assets.save_loaded_asset(t);result[name]=t
 return result

DETAIL='''
// Dedicated 4x4m world patch; original shading outside this patch.
float2 edge=abs(P.xy-float2(-46000,-31800));
float patch=1-smoothstep(170,230,max(edge.x,edge.y));
float dist=length(Camera-P);
float strength=patch*(1-smoothstep(1600,3000,dist));
Normal=OldNormal;AO=OldAO;Rough=OldRough;
[branch] if(strength<.001) return OldColour;
float3 w=pow(abs(N),6);w/=max(.001,w.x+w.y+w.z);
float rock=smoothstep(.47,.73,C.b/max(C.r,.001));
float2 uvs[3]={P.yz/200,P.xz/200,P.xy/200};
float3 view=normalize(Camera-P);
float2 rays[3]={view.yz,view.xz,view.xy};
float faces[3]={abs(view.x),abs(view.y),abs(view.z)};
float depth=lerp(4,5,rock);
float4 sampled[3];
for(int axis=0;axis<3;axis++){
 float2 uv=uvs[axis],dx=ddx(uv),dy=ddy(uv);
 float weight=axis==0?w.x:axis==1?w.y:w.z;
 [branch] if(weight<.02){sampled[axis]=float4(.5,.5,.5,1);continue;}
 float usePOM=Parallax*strength*(1-smoothstep(800,1500,dist))*smoothstep(.16,.3,faces[axis]);
 [branch] if(usePOM>.01){
  float2 ray=-rays[axis]/max(faces[axis],.2)*depth/200*usePOM;
  float t=0,prev=0,oldDiff=0;
  [loop] for(int j=0;j<=12;j++){
   float2 at=uv+ray*t;
   float h=lerp(Texture2DSampleGrad(Soil,SoilSampler,at,dx,dy).b,Texture2DSampleGrad(Rock,RockSampler,at,dx,dy).b,rock);
   float d=t-(1-h);
   if(d>=0||j==12){uv+=ray*lerp(prev,t,saturate(-oldDiff/max(d-oldDiff,.00001)));break;}
   prev=t;oldDiff=d;t+=1.0/12;
  }
 }
 sampled[axis]=lerp(Texture2DSampleGrad(Soil,SoilSampler,uv,dx,dy),Texture2DSampleGrad(Rock,RockSampler,uv,dx,dy),rock);
}
float2 a=(sampled[0].rg*2-1)*float2(1,-1),b=(sampled[1].rg*2-1)*float2(1,-1),c=(sampled[2].rg*2-1)*float2(1,-1);
// Surface slopes are blended in world space; original macro mesh normals survive.
float3 g=float3(0,a.x,a.y)*w.x+float3(b.x,0,b.y)*w.y+float3(c.x,c.y,0)*w.z;
g-=normalize(N)*dot(g,normalize(N));
Normal=normalize(lerp(OldNormal,normalize(N+g*.95),strength));
float4 data=sampled[0]*w.x+sampled[1]*w.y+sampled[2]*w.z;
AO=lerp(OldAO,data.a,strength);
Rough=lerp(OldRough,clamp(.71+.22*(1-data.a)+.04*data.b,.68,.95),strength);
// Preserve the approved moss/litter colour texture. Height detail augments it;
// replacing that texture with vertex colour made the prototype flatter.
float variation=lerp(.93,1.10,smoothstep(.12,.78,data.b));
float3 colour=OldColour*variation*lerp(.94,1,data.a);
return lerp(OldColour,colour,strength);
'''
def ground(tex,parallax=False):
 import lidar_bank_ground_material as old
 m=old.build('M_BankSurface');g=Graph(m,'PDGround')
 properties=[u.MaterialProperty.MP_BASE_COLOR,u.MaterialProperty.MP_NORMAL,u.MaterialProperty.MP_AMBIENT_OCCLUSION,u.MaterialProperty.MP_ROUGHNESS]
 sources=[(mel.get_material_property_input_node(m,p),mel.get_material_property_input_node_output_name(m,p)) for p in properties]
 n=g.custom(['P','N','C','Camera','Soil','Rock','Parallax','OldColour','OldNormal','OldAO','OldRough'],DETAIL,outputs=[('Normal',u.CustomMaterialOutputType.CMOT_FLOAT3),('AO',u.CustomMaterialOutputType.CMOT_FLOAT1),('Rough',u.CustomMaterialOutputType.CMOT_FLOAT1)])
 for key,cls in [('P',u.MaterialExpressionWorldPosition),('N',u.MaterialExpressionVertexNormalWS),('C',u.MaterialExpressionVertexColor),('Camera',u.MaterialExpressionCameraPositionWS)]:g.wire(g.node(cls),n,key)
 for key,name in [('Soil','T_PD_SoilNH'),('Rock','T_PD_RockNH')]:g.wire(g.node(u.MaterialExpressionTextureObject,texture=tex[name],sampler_type=u.MaterialSamplerType.SAMPLERTYPE_LINEAR_COLOR),n,key)
 param=g.node(u.MaterialExpressionScalarParameter,parameter_name='PD_Parallax',default_value=float(parallax));g.wire(param,n,'Parallax')
 for key,(node,out) in zip(['OldColour','OldNormal','OldAO','OldRough'],sources):g.wire(node,n,key,out)
 for p,out in zip(properties,['','Normal','AO','Rough']):g.output(n,p,out)
 assert not mel.recompile_material(m);assert assets.save_loaded_asset(m,False)
 if assets.does_asset_exist(DEST+'/FernFloor/T_FernFloor_Contact'):
  import fern_floor
  fern_floor.install_material()
 import lidar_bank_material_polish as polish
 if polish.enabled():polish.ground('M_BankSurface')

def fern(tex):
 import lidar_first_section as section
 source=u.load_asset(DEST+'/M_BankLeaf');m=assets.duplicate_asset(source.get_path_name().split('.')[0],PD+'/M_PD_Fern') if not assets.does_asset_exist(PD+'/M_PD_Fern') else u.load_asset(PD+'/M_PD_Fern')
 # Start each application from the original leaf graph, without stacking wrappers.
 for node in list(mel.get_material_expressions(m)):
  if str(node.get_editor_property('desc'))=='PDLeaf':mel.delete_material_expression(m,node)
 g=Graph(m,'PDLeaf');uv=g.node(u.MaterialExpressionTextureCoordinate);s=g.tex(tex['T_PD_LeafNH'],uv)
 normal=g.custom(['T'],'float2 xy=(T.rg*2-1)*.9;return normalize(float3(xy,sqrt(saturate(1-dot(xy,xy)))));');g.wire(s,normal,'T','RGBA');g.output(normal,u.MaterialProperty.MP_NORMAL)
 ao=g.custom(['T','SelfAO'],'return clamp(T.a*SelfAO.x,.42,1);',u.CustomMaterialOutputType.CMOT_FLOAT1);g.wire(s,ao,'T','RGBA');g.wire(g.node(u.MaterialExpressionTextureCoordinate,coordinate_index=1),ao,'SelfAO');g.output(ao,u.MaterialProperty.MP_AMBIENT_OCCLUSION)
 rough=g.custom(['T'],'return .60+.20*T.a-.10*T.b;',u.CustomMaterialOutputType.CMOT_FLOAT1);g.wire(s,rough,'T','RGBA');g.output(rough,u.MaterialProperty.MP_ROUGHNESS)
 props(m,tangent_space_normal=True);assert not mel.recompile_material(m);assets.save_loaded_asset(m,False)
 sm=u.get_editor_subsystem(u.StaticMeshEditorSubsystem);mesh=u.load_asset(DEST+'/SM_RS7_Cascade_0');before=[sm.get_number_verts(mesh,i) for i in range(3)]
 w=u.get_editor_subsystem(u.UnrealEditorSubsystem).get_editor_world();u.SystemLibrary.execute_console_command(w,'Interchange.FeatureFlags.Import.FBX 0')
 task=props(u.AssetImportTask(),filename=str(OUT/'SM_RS7_Cascade_0_LOD0.fbx'),destination_path=DEST,destination_name='SM_RS7_Cascade_0',automated=True,replace_existing=True,save=True)
 opt=props(u.FbxImportUI(),import_mesh=True,import_materials=False,import_textures=False,import_as_skeletal=False,mesh_type_to_import=u.FBXImportType.FBXIT_STATIC_MESH)
 props(opt.static_mesh_import_data,combine_meshes=True,auto_generate_collision=False,generate_lightmap_u_vs=False,vertex_color_import_option=u.VertexColorImportOption.REPLACE,normal_import_method=u.FBXNormalImportMethod.FBXNIM_IMPORT_NORMALS);task.options=opt
 u.AssetToolsHelpers.get_asset_tools().import_asset_tasks([task]);mesh=u.load_asset(DEST+'/SM_RS7_Cascade_0')
 for lod in [1,2]:assert sm.import_lod(mesh,lod,str(OUT/('SM_RS7_Cascade_0_LOD'+str(lod)+'.fbx')))==lod
 sm.set_lod_screen_sizes(mesh,[1.,.025,.007]);sm.remove_collisions(mesh)
 for i,slot in enumerate(mesh.get_editor_property('static_materials')):
  mesh.set_material(i,m if 'foliage' in str(slot.material_slot_name).lower() else u.load_asset(DEST+'/M_BankEarth'))
 assert assets.save_loaded_asset(mesh,False)
 import lidar_bank_material_polish as polish
 if polish.enabled():polish.leaf('PerceivedDetail/M_PD_Fern')
 return dict(vertices_before=before,vertices_after=[sm.get_number_verts(mesh,i) for i in range(3)],uv_channels=sm.get_num_uv_channels(mesh,0),planting=section.snapshot())

def apply(parallax=False):
 import lidar_first_section as section
 before=section.snapshot();outside=section.outside_snapshot();tex=textures();ground(tex,parallax);result=fern(tex)
 assert section.snapshot()==before and section.outside_snapshot()==outside
 result.update(ok=True,parallax=parallax,scope='4x4m ground material patch and Cascade_0 species; shape and instance transforms retained',outside=outside)
 (QA/'surface-install.json').write_text(json.dumps(result,indent=2));return result
