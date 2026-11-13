"""RS7 ground follow-up: shaded surface relief with physical-scale, filtered detail.

Only map-owned materials/textures. No displacement, collision or exposure changes.
World-space surface-gradient bump follows Epic's non-tangent-space formulation.
"""
import unreal as u
from benmore_river_life_materials import Graph,props
DEST='/Game/GrandTour/ArtTests/LidarStudy/FirstSection'
mel=u.MaterialEditingLibrary;assets=u.EditorAssetLibrary

SURFACE='''
float3 weights=pow(abs(N),4);weights/=max(.001,weights.x+weights.y+weights.z);
// 2 m root/litter tile, 1.1 m fractured rock, 35 cm secondary mineral grain.
float3 q=P-float3(-45800,-31600,4800);
float3 soil=Texture2DSample(Soil,SoilSampler,q.yz/200).rgb*weights.x
 +Texture2DSample(Soil,SoilSampler,q.xz/200).rgb*weights.y
 +Texture2DSample(Soil,SoilSampler,q.xy/200).rgb*weights.z;
float3 orh=Texture2DSample(ORH,ORHSampler,q.yz/200).rgb*weights.x
 +Texture2DSample(ORH,ORHSampler,q.xz/200).rgb*weights.y
 +Texture2DSample(ORH,ORHSampler,q.xy/200).rgb*weights.z;
float3 stone=Texture2DSample(Rock,RockSampler,q.yz/110).rgb*weights.x
 +Texture2DSample(Rock,RockSampler,q.xz/110).rgb*weights.y
 +Texture2DSample(Rock,RockSampler,q.xy/110).rgb*weights.z;
float3 fine=Texture2DSample(Rock,RockSampler,(q.yz+float2(32,71))/35).rgb*weights.x
 +Texture2DSample(Rock,RockSampler,(q.xz+float2(32,71))/35).rgb*weights.y
 +Texture2DSample(Rock,RockSampler,(q.xy+float2(32,71))/35).rgb*weights.z;
float rock=smoothstep(.47,.73,C.b/max(C.r,.001));
float moss=smoothstep(.94,1.38,C.g/max(C.r,.001))*(1-rock);
float rockValue=dot(stone,float3(.3,.5,.2));
float fineValue=dot(fine,float3(.3,.5,.2));
float soilValue=dot(soil,float3(.3,.5,.2));
// This inherited rock source is stored as linear data, not sRGB colour.
float rockDetail=clamp((rockValue-.38)*3.2+1.0,.38,1.58);
float soilDetail=clamp((soilValue-.055)*11+1.0,.62,1.6);
float detail=lerp(soilDetail,rockDetail,rock);
float cavity=lerp(saturate(orh.r),smoothstep(.17,.48,rockValue),rock);
float wet=(1-smoothstep(4400,4660,P.z))*(.65+.35*(1-cavity));
// Heights are centimetres. Large-scale bank shape remains in the fitted mesh.
Height=lerp(orh.b*1.5,rockValue*8.0+fineValue*.9,rock);
Height*=lerp(1,.65,moss);
Rough=clamp(lerp(orh.g,.82+(1-cavity)*.12,rock)-wet*.14,.64,.97);
AO=lerp(.70,1,cavity);
return C*detail*(.86+.14*cavity)*(1-wet*.10);
'''

BUMP='''
// Surface gradient of the height field, in world units; no tangent frame or
// stretched XY projection on steep banks. Keep distant detail well behaved.
float3 n=normalize(N),sx=ddx(P),sy=ddy(P);
float3 r1=cross(sy,n),r2=cross(n,sx);
float det=dot(sx,r1);
float3 grad=(ddx(H)*r1+ddy(H)*r2)*sign(det)/max(abs(det),.00001);
float fade=1-smoothstep(1800,5000,length(Camera-P));
grad*=fade;
float len=length(grad);grad*=min(1.0,.85/max(len,.0001));
return normalize(n-grad);
'''

def build(name):
 assert name in ['M_BankSurface','M_BankEarth']
 import lidar_bank_material_polish as polish
 if polish.enabled() and assets.does_asset_exist(DEST+'/'+name):
  return polish.ground(name)
 m=u.load_asset(DEST+'/'+name)
 if not m:m=u.AssetToolsHelpers.get_asset_tools().create_asset(name,DEST,u.Material,u.MaterialFactoryNew())
 mel.delete_all_material_expressions(m);g=Graph(m,'RS7GroundDetail')
 props(m,two_sided=False,shading_model=u.MaterialShadingModel.MSM_DEFAULT_LIT,
       tangent_space_normal=False,dithered_lod_transition=True,
       blend_mode=u.BlendMode.BLEND_MASKED if name=='M_BankSurface' else u.BlendMode.BLEND_OPAQUE)
 vc=g.node(u.MaterialExpressionVertexColor);p=g.node(u.MaterialExpressionWorldPosition)
 n=g.node(u.MaterialExpressionVertexNormalWS)
 def tex(source,target,linear=False):
  t=u.load_asset(DEST+'/'+target) or assets.duplicate_asset(source,DEST+'/'+target)
  # World-projected custom UVs are opaque to the texture streamer's mesh-UV
  # estimate. Keep only these two small bank-owned detail maps resident.
  props(t,max_texture_size=2048,lod_bias=0,filter=u.TextureFilter.TF_DEFAULT,never_stream=True)
  assets.save_loaded_asset(t)
  return g.node(u.MaterialExpressionTextureObject,texture=t,sampler_type=u.MaterialSamplerType.SAMPLERTYPE_LINEAR_COLOR if linear else u.MaterialSamplerType.SAMPLERTYPE_COLOR)
 soil=tex('/Game/GrandTour/ArtTests/GroundDetail/Bakes/T_GD_SoilUnderGrassColor','T_BankSoilColour')
 orh=tex('/Game/GrandTour/ArtTests/GroundDetail/Bakes/T_GD_SoilUnderGrassORH','T_BankSoilORH',True)
 rock=g.node(u.MaterialExpressionTextureObject,texture=u.load_asset('/Game/GrandTour/ArtTests/BenmoreWoodland/T_tiles_rock_slope__d_a'))
 surface=g.custom(['C','P','N','Soil','ORH','Rock'],SURFACE,outputs=[(k,u.CustomMaterialOutputType.CMOT_FLOAT1) for k in ['Height','Rough','AO']])
 for value,key in [(vc,'C'),(p,'P'),(n,'N'),(soil,'Soil'),(orh,'ORH'),(rock,'Rock')]:g.wire(value,surface,key)
 g.output(surface,u.MaterialProperty.MP_BASE_COLOR)
 g.output(surface,u.MaterialProperty.MP_ROUGHNESS,'Rough');g.output(surface,u.MaterialProperty.MP_AMBIENT_OCCLUSION,'AO')
 bump=g.custom(['H','P','N','Camera'],BUMP)
 for value,key,out in [(surface,'H','Height'),(p,'P',''),(n,'N',''),(g.node(u.MaterialExpressionCameraPositionWS),'Camera','')]:g.wire(value,bump,key,out)
 g.output(bump,u.MaterialProperty.MP_NORMAL);g.output(g.scalar(.18),u.MaterialProperty.MP_SPECULAR)
 if name=='M_BankSurface':
  props(m,opacity_mask_clip_value=.01)
  mask=g.custom(['A','P','EdgeTex'],'float n=Texture2DSample(EdgeTex,EdgeTexSampler,(P.xy-float2(-45800,-31600))*.032).g;return A-n*.98;',u.CustomMaterialOutputType.CMOT_FLOAT1)
  g.wire(vc,mask,'A','A');g.wire(p,mask,'P');g.wire(rock,mask,'EdgeTex');g.output(mask,u.MaterialProperty.MP_OPACITY_MASK)
 mel.set_material_usage(m,u.MaterialUsage.MATUSAGE_INSTANCED_STATIC_MESHES)
 assert not mel.recompile_material(m)
 assert assets.save_loaded_asset(m)
 return m
