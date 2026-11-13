"""Map-local colour bridge; no edits to soil displacement or water simulation."""
import unreal as u,math
from benmore_river_life_materials import props,Graph
M=u.MaterialEditingLibrary;E=u.EditorAssetLibrary

def apply(m,cfg):
 name=m.get_name();g=Graph(m,'FloraTrailSurfacePalette');nodes=M.get_material_expressions(m)
 if E.get_metadata_tag(m,'FloraTrailSurfacePalette')=='1':
  for n in nodes:
   if isinstance(n,u.MaterialExpressionVectorParameter) and str(n.get_editor_property('parameter_name'))=='PondTint':n.set_editor_property('default_value',u.LinearColor(*cfg['pond_tint'],1))
  return
 if name in ['M_LidarDemoMud','M_ForestFloorForms','M_ForestSurround']:
  old=M.get_material_property_input_node(m,u.MaterialProperty.MP_BASE_COLOR);assert old
  p=g.node(u.MaterialExpressionWorldPosition)
  scale=g.custom(['C','P'],'float centre=530*sin((P.x+2200)/1050)-150;float shoulder=smoothstep(280.,540.,abs(P.y-centre));return C*lerp(.8,.42,shoulder);')
  g.wire(old,scale,'C');g.wire(p,scale,'P');g.output(scale,u.MaterialProperty.MP_BASE_COLOR)
 elif name.startswith('M_SM_RM_'):
  old=M.get_material_property_input_node(m,u.MaterialProperty.MP_BASE_COLOR);assert old
  scale=g.custom(['C'],'return C*.65;');g.wire(old,scale,'C');g.output(scale,u.MaterialProperty.MP_BASE_COLOR)
 elif name=='M_FloraWater':
  old=M.get_material_property_input_node(m,u.MaterialProperty.MP_BASE_COLOR);assert old
  p=g.node(u.MaterialExpressionWorldPosition)
  mask=g.custom(['P'],'float2 q=(P.xy-float2(900.,1050.))/float2(700.,500.);return 1-smoothstep(.35,.95,length(q));',u.CustomMaterialOutputType.CMOT_FLOAT1);g.wire(p,mask,'P')
  tint=g.node(u.MaterialExpressionVectorParameter,parameter_name='PondTint',default_value=u.LinearColor(*cfg['pond_tint'],1))
  colour=g.custom(['C','Pond','Tint'],'return lerp(C*.55,lerp(C*.35,Tint,.7),Pond);');g.wire(old,colour,'C');g.wire(mask,colour,'Pond');g.wire(tint,colour,'Tint');g.output(colour,u.MaterialProperty.MP_BASE_COLOR)
  output=next(n for n in nodes if isinstance(n,u.MaterialExpressionSingleLayerWaterMaterialOutput))
  refr=[(x/255.)**2.2*.9 for x in [128,118,101]];absorb=[-math.log(max(x,.001))/80 for x in refr]
  clean=lambda s:''.join(c.lower() for c in s if c.isalnum())
  for name,a,b in [('Scattering Coefficients',[.00145,.00115,.00075],[.0007,.0016,.0018]),('Absorption Coefficients',absorb,[.018,.010,.008]),('Color Scale Behind Water',refr,[.28,.42,.45])]:
   mix=g.custom(['A','B','Pond'],'return lerp(A,B,Pond);');g.wire(g.vector(a),mix,'A');g.wire(g.vector(b),mix,'B');g.wire(mask,mix,'Pond')
   pin=next(n for n in M.get_material_expression_input_names(output) if clean(n)==clean(name));g.wire(mix,output,pin)
 else:return
 E.set_metadata_tag(m,'FloraTrailSurfacePalette','1')
