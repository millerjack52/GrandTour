"""Recovered Plants/GRASS motion and alpha coverage; explicit UE lighting bridge."""
import unreal as u
from pathlib import Path
from benmore_river_life_materials import Graph,props
BASE='/Game/GrandTour/ArtTests/BenmoreWoodland'
WIND=r'''
// Plants_009 GRASS. Source metres/Y-up become centimetres/Z-up here.
// Instance UV seeds replace the source packed block-root bytes.
float2 seed=floor(frac(Pivot.xy/1666.666667)*255+.5)/255;
float phase=Time+dot(seed,float2(43.3709984,17.9130001));
float3 angles=frac(phase*float3(.0636619776,.216450721,.598422587)+.5)*6.28318548-3.14159274;
float wave=cos(angles.x)*cos(angles.y)+.25*sin(angles.z);
// Verified against all 16 original vertices: native TEXCOORD3.x is 0 below
// 5 cm and 1 above it. It was lost by the previous OBJ import.
float weight=step(5,Local.z);
float type=2; // Existing host packed grass state is 0x20 (until removal).
float2 wind=wave*.04*weight*float2(type*.25,1-type*.25)*100*WindScale;
float3 original=P-Pivot;
float3 moved=normalize(original+float3(wind,0)+float3(0,0,.000001))*length(original);
float h=max(0,(Pivot.z+moved.z-Root)*.01);
// Source deflector decoder, with the established host contact direction.
float4 deflector=float4(.85,.65,0,Bend);
float strength=saturate((h-.1)*2.5)*deflector.w*saturate(h-deflector.z*4);
float3 contact=float3((deflector.xy-.5)*2,-.8)*strength*100;
return Removed>.5 ? float3(0,0,-100000) : moved-original+contact;
'''

def build():
 assets=u.EditorAssetLibrary;mel=u.MaterialEditingLibrary
 m=u.load_asset(BASE+'/M_GrassRecovered') or u.AssetToolsHelpers.get_asset_tools().create_asset('M_GrassRecovered',BASE,u.Material,u.MaterialFactoryNew());mel.delete_all_material_expressions(m)
 props(m,blend_mode=u.BlendMode.BLEND_MASKED,shading_model=u.MaterialShadingModel.MSM_TWO_SIDED_FOLIAGE,two_sided=True,tangent_space_normal=False,opacity_mask_clip_value=.35)
 g=Graph(m,'RecoveredPlantsGrass');uv=g.node(u.MaterialExpressionTextureCoordinate)
 tex=g.node(u.MaterialExpressionTextureSample,texture=u.load_asset('/Game/GrandTour/ArtTests/MudRoad/MixedSurfaces/T_grass_grass_short__d_a'),sampler_type=u.MaterialSamplerType.SAMPLERTYPE_LINEAR_COLOR);assert tex.texture;g.wire(uv,tex,'UVs')
 tint=g.node(u.MaterialExpressionVectorParameter,parameter_name='GrassBaseTint',default_value=u.LinearColor(1,1,1,1))
 col=g.custom(['Diffuse','Tint'],'return pow(max(Diffuse*Tint,0),2.2);');g.wire(tex,col,'Diffuse','RGB');g.wire(tint,col,'Tint','RGB');g.output(col,u.MaterialProperty.MP_BASE_COLOR)
 fade=g.node(u.MaterialExpressionPerInstanceFadeAmount);alpha=g.node(u.MaterialExpressionMultiply);g.wire(tex,alpha,'A','A');g.wire(fade,alpha,'B');g.output(alpha,u.MaterialProperty.MP_OPACITY_MASK)
 sub=g.node(u.MaterialExpressionMultiply);g.wire(col,sub,'A');g.wire(g.scalar(.10),sub,'B');g.output(sub,u.MaterialProperty.MP_SUBSURFACE_COLOR)
 g.output(g.scalar(.95),u.MaterialProperty.MP_ROUGHNESS);g.output(g.scalar(.03),u.MaterialProperty.MP_SPECULAR);g.output(g.vector((0,0,1)),u.MaterialProperty.MP_NORMAL)
 p=g.node(u.MaterialExpressionWorldPosition,world_position_shader_offset=u.WorldPositionIncludedOffsets.WPT_EXCLUDE_ALL_SHADER_OFFSETS)
 pivot=g.node(u.MaterialExpressionTransformPosition,transform_source_type=u.MaterialPositionTransformSource.TRANSFORMPOSSOURCE_INSTANCE,transform_type=u.MaterialPositionTransformSource.TRANSFORMPOSSOURCE_WORLD);g.wire(g.vector((0,0,0)),pivot,'')
 local=g.node(u.MaterialExpressionTransformPosition,transform_source_type=u.MaterialPositionTransformSource.TRANSFORMPOSSOURCE_WORLD,transform_type=u.MaterialPositionTransformSource.TRANSFORMPOSSOURCE_INSTANCE);g.wire(p,local,'')
 inputs={'P':p,'Pivot':pivot,'Local':local,'Root':g.node(u.MaterialExpressionPerInstanceCustomData,data_index=0),'Bend':g.node(u.MaterialExpressionPerInstanceCustomData,data_index=1),'Removed':g.node(u.MaterialExpressionPerInstanceCustomData,data_index=2),'Time':g.node(u.MaterialExpressionTime),'WindScale':g.node(u.MaterialExpressionScalarParameter,parameter_name='NativeGrassWindScale',default_value=1)}
 wpo=g.custom(list(inputs),WIND)
 for pin,node in inputs.items():g.wire(node,wpo,pin)
 g.output(wpo,u.MaterialProperty.MP_WORLD_POSITION_OFFSET);mel.set_material_usage(m,u.MaterialUsage.MATUSAGE_INSTANCED_STATIC_MESHES)
 assert not mel.recompile_material(m);assert assets.save_loaded_asset(m);return m


def build_distance_cover():
 """UE distance tier: native atlas/alpha, without contact or wind evaluation.

 Plants has a separate FAR permutation, but these distances and larger clumps
 are host choices, not recovered MudRunner runtime constants.
 """
 assets=u.EditorAssetLibrary;mel=u.MaterialEditingLibrary
 m=u.load_asset(BASE+'/M_GrassDistance') or u.AssetToolsHelpers.get_asset_tools().create_asset('M_GrassDistance',BASE,u.Material,u.MaterialFactoryNew())
 mel.delete_all_material_expressions(m)
 props(m,blend_mode=u.BlendMode.BLEND_MASKED,shading_model=u.MaterialShadingModel.MSM_TWO_SIDED_FOLIAGE,two_sided=True,tangent_space_normal=False,opacity_mask_clip_value=.35)
 g=Graph(m,'DistanceGrassAdapter');uv=g.node(u.MaterialExpressionTextureCoordinate)
 tex=g.node(u.MaterialExpressionTextureSample,texture=u.load_asset('/Game/GrandTour/ArtTests/MudRoad/MixedSurfaces/T_grass_grass_short__d_a'),sampler_type=u.MaterialSamplerType.SAMPLERTYPE_LINEAR_COLOR);g.wire(uv,tex,'UVs')
 col=g.custom(['Diffuse'],'return pow(max(Diffuse,0),2.2);');g.wire(tex,col,'Diffuse','RGB');g.output(col,u.MaterialProperty.MP_BASE_COLOR)
 p=g.node(u.MaterialExpressionWorldPosition);cam=g.node(u.MaterialExpressionCameraPositionWS);fade=g.node(u.MaterialExpressionPerInstanceFadeAmount)
 alpha=g.custom(['Alpha','Fade','P','Camera'],'return Alpha*Fade*smoothstep(1800,2600,length(P.xy-Camera.xy));',u.CustomMaterialOutputType.CMOT_FLOAT1)
 g.wire(tex,alpha,'Alpha','A');g.wire(fade,alpha,'Fade');g.wire(p,alpha,'P');g.wire(cam,alpha,'Camera');g.output(alpha,u.MaterialProperty.MP_OPACITY_MASK)
 sub=g.node(u.MaterialExpressionMultiply);g.wire(col,sub,'A');g.wire(g.scalar(.10),sub,'B');g.output(sub,u.MaterialProperty.MP_SUBSURFACE_COLOR)
 g.output(g.scalar(.95),u.MaterialProperty.MP_ROUGHNESS);g.output(g.scalar(.03),u.MaterialProperty.MP_SPECULAR);g.output(g.vector((0,0,1)),u.MaterialProperty.MP_NORMAL)
 mel.set_material_usage(m,u.MaterialUsage.MATUSAGE_INSTANCED_STATIC_MESHES)
 assert not mel.recompile_material(m);assert assets.save_loaded_asset(m);return m
