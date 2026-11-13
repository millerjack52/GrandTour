"""Separate display outputs for the sRGB scene target and editor backbuffer."""
import unreal as u
from benmore_river_life_materials import props,Graph
def viewport_material():
 path='/Game/GrandTour/ArtTests/FloraGroup/M_ViewportStandard';m=u.load_asset(path)
 if not m or u.EditorAssetLibrary.get_metadata_tag(m,'SourceDisplayVersion')!='1':
  m=m or u.AssetToolsHelpers.get_asset_tools().create_asset('M_ViewportStandard','/Game/GrandTour/ArtTests/FloraGroup',u.Material,u.MaterialFactoryNew())
  u.MaterialEditingLibrary.delete_all_material_expressions(m)
  props(m,material_domain=u.MaterialDomain.MD_POST_PROCESS,blendable_location=u.BlendableLocation.BL_REPLACING_TONEMAPPER)
  g=Graph(m);scene=g.node(u.MaterialExpressionSceneTexture,scene_texture_id=u.SceneTextureId.PPI_POST_PROCESS_INPUT0)
  encode=g.custom(['C'],'float3 x=max(0.,C*View.OneOverPreExposure);return lerp(12.92*x,1.055*pow(x,1./2.4)-.055,step(.0031308,x));')
  g.wire(scene,encode,'C','Color');g.output(encode,u.MaterialProperty.MP_EMISSIVE_COLOR)
  assert not u.MaterialEditingLibrary.recompile_material(m);u.EditorAssetLibrary.set_metadata_tag(m,'SourceDisplayVersion','1');u.EditorAssetLibrary.save_loaded_asset(m,False)
 return m
def apply_to_volume(volume):
 settings=volume.settings;settings.weighted_blendables=props(u.WeightedBlendables(),array=[props(u.WeightedBlendable(),weight=1.,object=viewport_material())]);volume.settings=settings
