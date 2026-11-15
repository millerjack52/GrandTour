"""Road-only texture wrapper. Keep native deformation, terrain and water inputs."""
import unreal as u,json
from pathlib import Path
from benmore_river_life_materials import props,Graph
R=Path('C:/GrandTour');O=R/'Art/Export/FloraTrail/MudTrial';D='/Game/GrandTour/ArtTests/FloraTrail/MudTrial'
M=u.MaterialEditingLibrary;E=u.EditorAssetLibrary;T=u.AssetToolsHelpers.get_asset_tools()
def texture(row,role,native=False):
 name='T_'+row['id']+'_'+role+('_native' if native else '')
 path=D+'/Textures/'+name;t=u.load_asset(path)
 if not t or E.get_metadata_tag(t,'MudTrialSourceRevision')!='normalized8_v1':
  src=row['files'][role]['engine_path' if native else 'screen_path']
  task=props(u.AssetImportTask(),filename=src,destination_path=D+'/Textures',destination_name=name,automated=True,save=True,replace_existing=True,replace_existing_settings=True);T.import_asset_tasks([task]);t=u.load_asset(path);assert t
 props(t,srgb=role=='color',max_texture_size=4096 if native else 1024,lod_bias=0,compression_settings=u.TextureCompressionSettings.TC_NORMALMAP if role=='normal' else u.TextureCompressionSettings.TC_DEFAULT if role=='color' else u.TextureCompressionSettings.TC_GRAYSCALE)
 if role=='normal':props(t,flip_green_channel=row['id']=='stylized_dry_mud')
 E.set_metadata_tag(t,'MudTrialSourceRevision','normalized8_v1');assert E.save_loaded_asset(t,False);return t
def build(source,row,role):
 path=D+'/M_MudTrial_'+role;m=u.load_asset(path) or E.duplicate_asset(source.get_path_name().split('.')[0],path);assert m
 if E.get_metadata_tag(m,'MudTrial')=='1':return m
 originals={k:(M.get_material_property_input_node(m,p),M.get_material_property_input_node_output_name(m,p)) for k,p in [('Base',u.MaterialProperty.MP_BASE_COLOR),('OldNormal',u.MaterialProperty.MP_NORMAL),('OldRough',u.MaterialProperty.MP_ROUGHNESS)]}
 assert all(n for n,out in originals.values())
 native=next((n for n in M.get_material_expressions(m) if str(n.get_editor_property('desc'))=='FloorSourceNormal'),originals['OldNormal'][0])
 native_out='' if native!=originals['OldNormal'][0] else originals['OldNormal'][1]
 g=Graph(m,'MudTextureTrial');p=g.node(u.MaterialExpressionWorldPosition);cam=g.node(u.MaterialExpressionCameraPositionWS);v=g.node(u.MaterialExpressionCameraVectorWS)
 params={k:g.node(u.MaterialExpressionScalarParameter,parameter_name='MudTrial'+k,default_value=value) for k,value in [('Enabled',1.),('TileCm',row['tile_cm']),('ReliefCm',2.8),('NormalStrength',1.)]}
 uv=g.custom(['P','Scale'],'return float2(P.x,-P.y)/max(Scale,20.);',u.CustomMaterialOutputType.CMOT_FLOAT2);g.wire(p,uv,'P');g.wire(params['TileCm'],uv,'Scale')
 ht=g.node(u.MaterialExpressionTextureObjectParameter,parameter_name='MudTrialHeight',texture=texture(row,'height'),sampler_type=u.MaterialSamplerType.SAMPLERTYPE_LINEAR_GRAYSCALE)
 pom=g.custom(['UV','P','Camera','V','N','Scale','Depth','Enabled','HeightTex'],'''
float2 dx=ddx(UV),dy=ddy(UV);float facing=dot(normalize(N),normalize(V));
float strength=Enabled*(1-smoothstep(800.,1800.,length(Camera-P)))*smoothstep(.06,.17,facing);
if(strength<.001)return UV;
float2 ray=float2(-V.x,V.y)*(Depth*strength*max(N.z,.1)/max(facing,.08))/max(Scale,20.);
int steps=(int)lerp(24.,10.,saturate(facing));float t=0,previousT=0,previousDiff=0;
[loop] for(int i=0;i<=24;i++){
 float h=Texture2DSampleGrad(HeightTex,HeightTexSampler,UV+ray*t,dx,dy).r;
 float diff=t-(1-h);if(diff>=0||i==steps){float a=saturate(-previousDiff/max(diff-previousDiff,.00001));return UV+ray*lerp(previousT,t,a);}
 previousT=t;previousDiff=diff;t+=1./steps;
}return UV;
''',u.CustomMaterialOutputType.CMOT_FLOAT2)
 for key,node,out in [('UV',uv,''),('P',p,''),('Camera',cam,''),('V',v,''),('N',native,native_out),('Scale',params['TileCm'],''),('Depth',params['ReliefCm'],''),('Enabled',params['Enabled'],''),('HeightTex',ht,'')]:g.wire(node,pom,key,out)
 du=g.custom(['UV'],'return ddx(UV);',u.CustomMaterialOutputType.CMOT_FLOAT2);dv=g.custom(['UV'],'return ddy(UV);',u.CustomMaterialOutputType.CMOT_FLOAT2);g.wire(uv,du,'UV');g.wire(uv,dv,'UV')
 samples={}
 for key,role in [('Colour','color'),('Normal','normal'),('Roughness','roughness')]:
  n=g.node(u.MaterialExpressionTextureSampleParameter2D,parameter_name='MudTrial'+key,texture=texture(row,role),sampler_type=u.MaterialSamplerType.SAMPLERTYPE_NORMAL if role=='normal' else u.MaterialSamplerType.SAMPLERTYPE_COLOR if role=='color' else u.MaterialSamplerType.SAMPLERTYPE_LINEAR_GRAYSCALE,mip_value_mode=u.TextureMipValueMode.TMVM_DERIVATIVE,sampler_source=u.SamplerSourceMode.SSM_WRAP_WORLD_GROUP_SETTINGS)
  g.wire(pom,n,'UVs');g.wire(du,n,'DDX(UVs)');g.wire(dv,n,'DDY(UVs)');samples[key]=n
 wrapper=g.custom(['P','Base','OldNormal','OldRough','NativeNormal','Colour','Normal','Roughness','Enabled','Strength'],'''
float centre=530*sin((P.x+2200)/1050)-150;
float mask=(1-smoothstep(230.,320.,abs(P.y-centre)))*smoothstep(-2900.,-2450.,P.x)*(1-smoothstep(2450.,2900.,P.x))*Enabled;
// Preserve authored wetness modulation; candidate pigment receives no hue grade.
float wet=lerp(.68,1.,saturate((OldRough-.2)/.6));
float3 n=normalize(float3(NativeNormal.xy+float2(Normal.x,-Normal.y)*Strength,NativeNormal.z));
TrialNormal=normalize(lerp(OldNormal,n,mask));
TrialRoughness=lerp(OldRough,clamp(Roughness*.65+OldRough*.35,.08,.96),mask);
return lerp(Base,Colour*wet,mask);
''',outputs=[('TrialNormal',u.CustomMaterialOutputType.CMOT_FLOAT3),('TrialRoughness',u.CustomMaterialOutputType.CMOT_FLOAT1)])
 for key,(node,out) in originals.items():g.wire(node,wrapper,key,out)
 for key,node,out in [('P',p,''),('NativeNormal',native,native_out),('Enabled',params['Enabled'],''),('Strength',params['NormalStrength'],'')]+[(k,n,'RGB' if k!='Roughness' else 'R') for k,n in samples.items()]:g.wire(node,wrapper,key,out)
 g.output(wrapper,u.MaterialProperty.MP_BASE_COLOR);g.output(wrapper,u.MaterialProperty.MP_NORMAL,'TrialNormal');g.output(wrapper,u.MaterialProperty.MP_ROUGHNESS,'TrialRoughness')
 assert not M.recompile_material(m);E.set_metadata_tag(m,'MudTrial','1');assert E.save_loaded_asset(m,False);return m
def bind(mid,row,textures,enabled=1.):
 for key,role in [('Colour','color'),('Normal','normal'),('Roughness','roughness'),('Height','height')]:mid.set_texture_parameter_value('MudTrial'+key,textures[row['id']][role])
 mid.set_scalar_parameter_value('MudTrialTileCm',row['tile_cm']);mid.set_scalar_parameter_value('MudTrialEnabled',enabled)


def instance(row,textures):
 name='MI_MudTrial_'+row['id'];mi=u.load_asset(D+'/'+name) or T.create_asset(name,D,u.MaterialInstanceConstant,u.MaterialInstanceConstantFactoryNew())
 M.set_material_instance_parent(mi,u.load_asset(D+'/M_MudTrial_ground'))
 for key,role in [('Colour','color'),('Normal','normal'),('Roughness','roughness'),('Height','height')]:
  M.set_material_instance_texture_parameter_value(mi,'MudTrial'+key,textures[row['id']][role])
 for key,value in [('Enabled',1.),('TileCm',row['tile_cm']),('ReliefCm',2.8),('NormalStrength',1.)]:M.set_material_instance_scalar_parameter_value(mi,'MudTrial'+key,value)
 M.update_material_instance(mi);assert E.save_loaded_asset(mi,False);return mi
