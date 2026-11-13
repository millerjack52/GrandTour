"""Tree-only material bridge: preserve the purchased pigment/masks, restore leaf lighting."""
import unreal as u
from benmore_river_life_materials import Graph,props
E=u.EditorAssetLibrary;M=u.MaterialEditingLibrary
D='/Game/GrandTour/ArtTests/FloraTrail/Materials/Canopy'
def candidate(source,coverage,lighting,cfg):
 name=source.get_name()+'_'+('coverage' if coverage else '')+('_lighting' if lighting else '')
 m=u.load_asset(D+'/'+name) or E.duplicate_asset(source.get_path_name().split('.')[0],D+'/'+name)
 if E.get_metadata_tag(m,'CanopyBridgeVersion')!='1':
  g=Graph(m,'CanopyBridge');nodes=M.get_material_expressions(m)
  colour=next(n for n in nodes if isinstance(n,u.MaterialExpressionTextureSampleParameter2D) and str(n.get_editor_property('parameter_name'))=='SourcePigment')
  if coverage:
   coverage_node=next(n for n in nodes if isinstance(n,u.MaterialExpressionCustom) and 'float b=clamp(Soft' in str(n.get_editor_property('code')))
   # Keep the original atlas and zero-alpha gaps; reduce the angle-dependent erasure.
   coverage_node.set_editor_property('code','float c=pow(saturate(abs(dot(normalize(N),normalize(V)))),.7);return saturate(A*(.62+.38*c));')
  if lighting:
   props(m,shading_model=u.MaterialShadingModel.MSM_TWO_SIDED_FOLIAGE)
   albedo=g.node(u.MaterialExpressionScalarParameter,parameter_name='CanopyReflectance',default_value=cfg['reflectance'])
   transmission=g.node(u.MaterialExpressionScalarParameter,parameter_name='CanopyTransmission',default_value=cfg['transmission'])
   for scalar,prop in [(albedo,u.MaterialProperty.MP_BASE_COLOR),(transmission,u.MaterialProperty.MP_SUBSURFACE_COLOR)]:
    mul=g.node(u.MaterialExpressionMultiply);g.wire(colour,mul,'A','RGB');g.wire(scalar,mul,'B');g.output(mul,prop)
   n=g.node(u.MaterialExpressionVertexNormalWS);side=g.node(u.MaterialExpressionTwoSidedSign)
   normal=g.custom(['N','Side'],'return normalize(N)*Side;');g.wire(n,normal,'N');g.wire(side,normal,'Side');g.output(normal,u.MaterialProperty.MP_NORMAL)
   g.output(g.scalar(0),u.MaterialProperty.MP_EMISSIVE_COLOR)
   g.output(g.scalar(.85),u.MaterialProperty.MP_ROUGHNESS);g.output(g.scalar(.08),u.MaterialProperty.MP_SPECULAR);g.output(g.scalar(.55),u.MaterialProperty.MP_OPACITY)
  E.set_metadata_tag(m,'CanopyBridgeVersion','1')
 for n in M.get_material_expressions(m):
  if coverage and isinstance(n,u.MaterialExpressionCustom) and 'return saturate(A*(' in str(n.get_editor_property('code')):
   floor=float(cfg['coverage_facing_floor']);assert 0<=floor<=1
   n.set_editor_property('code',f'float c=pow(saturate(abs(dot(normalize(N),normalize(V)))),.7);return saturate(A*({floor:.6f}+{1-floor:.6f}*c));')
  if isinstance(n,u.MaterialExpressionScalarParameter):
   k=str(n.get_editor_property('parameter_name'))
   if k=='CanopyReflectance':n.set_editor_property('default_value',cfg['reflectance'])
   if k=='CanopyTransmission':n.set_editor_property('default_value',cfg['transmission'])
 E.set_metadata_tag(m,'CanopyOriginalMaterial',source.get_path_name())
 assert not M.recompile_material(m);E.save_loaded_asset(m,False);return m

def install_component(c,cfg):
 if not c.static_mesh or c.static_mesh.get_name() not in ['SM_Exact_tree','SM_Exact_pine']:return []
 if cfg.get('source_version')=='3.4.1':
  from flora_trail_source34 import install_component as install_source34
  return install_source34(c)
 changed=[]
 for i,m in enumerate(c.get_materials()):
  if m.blend_mode!=u.BlendMode.BLEND_MASKED:continue
  # Always regenerate from the approved pre-adapter material, not from itself.
  original=E.get_metadata_tag(m,'CanopyOriginalMaterial')
  source=u.load_asset(original) if original else m;assert source
  result=candidate(source,True,True,cfg);c.set_material(i,result);changed.append(result.get_path_name())
 return changed
