"""Map-local Flora Paint corrections shared by the baker and woodland finish.

Do not modify purchased source materials. In particular, never bake independent
frames of stochastic opacity into colour/alpha/normal textures.
"""
import unreal as u
from benmore_river_life_materials import Graph,props
E=u.EditorAssetLibrary;M=u.MaterialEditingLibrary
D='/Game/GrandTour/ArtTests/LidarStudy/FloraWorld'

def base_material(mat):
 while isinstance(mat,u.MaterialInstanceConstant):mat=mat.get_editor_property('parent')
 return mat

def shape_material(mat,bake=False):
 """Preserve imported normals and retain continuous painted alpha, without noise."""
 if not isinstance(mat,u.Material) or mat.blend_mode!=u.BlendMode.BLEND_MASKED:return False
 changed=False
 for n in M.get_material_expressions(mat):
  if isinstance(n,u.MaterialExpressionScalarParameter):
   name=str(n.get_editor_property('parameter_name'))
   if name=='NormalUpBlend':n.set_editor_property('default_value',.28 if 'Leaf' in mat.get_name() else .18);changed=True
   if name=='Transmission':n.set_editor_property('default_value',.32 if 'Leaf' in mat.get_name() else .42)
  if isinstance(n,u.MaterialExpressionCustom) and str(n.get_editor_property('desc'))=='PathPainterlyCoverage':
   # The artist's painted mask already provides the edge shape. Spatial AA
   # keeps it stable; no View.StateFrameIndex / independent random frames.
   n.set_editor_property('code','float c=smoothstep(.015,max(.05,Softness),saturate(Coverage));return saturate((c-.22)/max(fwidth(c),.035)+.5);')
   changed=True
 props(mat,dither_opacity_mask=False,dithered_lod_transition=False)
 return changed

def bake_override(component):
 """Separate deterministic parents for capture, source pack untouched."""
 cache={}
 def clone(src):
  key=src.get_path_name()
  if key in cache:return cache[key]
  dst=D+'/BakeMaterials/'+src.get_name()
  m=u.load_asset(dst) or E.duplicate_asset(key.split('.')[0],dst);cache[key]=m
  if isinstance(m,u.MaterialInstanceConstant):
   M.set_material_instance_parent(m,clone(src.get_editor_property('parent')))
   for name,val in [('NormalUpBlend',.28),('Transmission',.32)]:M.set_material_instance_scalar_parameter_value(m,name,val)
  elif isinstance(m,u.Material):
   shape_material(m,True);assert not M.recompile_material(m)
  assert E.save_loaded_asset(m,False)
  return m
 for i,src in enumerate(component.get_materials()):
  if src:component.set_material(i,clone(src))

def plant_pigment(mat):
 """A small number of coherent copper/olive/teal plant colonies, not RGB noise."""
 if not any(s in mat.get_name() for s in ['Fern','Grass','Small_Plant','Shrubbery']):return False
 if not isinstance(mat,u.Material) or mat.blend_mode!=u.BlendMode.BLEND_MASKED:return False
 if any(str(n.get_editor_property('desc'))=='FloraPlantPigment' for n in M.get_material_expressions(mat)):return False
 src=M.get_material_property_input_node(mat,u.MaterialProperty.MP_BASE_COLOR);out=str(M.get_material_property_input_node_output_name(mat,u.MaterialProperty.MP_BASE_COLOR));assert src
 g=Graph(mat,'FloraPlantPigment')
 n=g.custom(['Base','P','Random','Strength'],'''float field=.5+.5*sin(P.x*.0019+sin(P.y*.0021)*2.4);
float colony=saturate(field*.8+Random*.2);
float3 copper=float3(.43,.18,.09),teal=float3(.055,.19,.155);
float lum=dot(Base,float3(.2126,.7152,.0722));
float warm=smoothstep(.68,.83,colony),cool=1-smoothstep(.19,.35,colony);
float3 a=lerp(Base,copper*(lum/max(.01,dot(copper,float3(.2126,.7152,.0722)))),warm*Strength);
return lerp(a,teal*(lum/max(.01,dot(teal,float3(.2126,.7152,.0722)))),cool*Strength*.7);''')
 g.wire(src,n,'Base',out);g.wire(g.node(u.MaterialExpressionWorldPosition,world_position_shader_offset=u.WorldPositionIncludedOffsets.WPT_EXCLUDE_ALL_SHADER_OFFSETS),n,'P')
 g.wire(g.node(u.MaterialExpressionPerInstanceRandom),n,'Random')
 g.wire(g.node(u.MaterialExpressionScalarParameter,parameter_name='MapPlantPigment',default_value=.68),n,'Strength');g.output(n,u.MaterialProperty.MP_BASE_COLOR)
 return True

def coherent_transmission(mat):
 if mat.get_editor_property('shading_model')!=u.MaterialShadingModel.MSM_TWO_SIDED_FOLIAGE:return
 if any(str(n.get_editor_property('desc'))=='FloraCoherentTransmission' for n in M.get_material_expressions(mat)):return
 g=Graph(mat,'FloraCoherentTransmission');src=M.get_material_property_input_node(mat,u.MaterialProperty.MP_BASE_COLOR);out=str(M.get_material_property_input_node_output_name(mat,u.MaterialProperty.MP_BASE_COLOR))
 n=g.node(u.MaterialExpressionMultiply);g.wire(src,n,'A',out)
 g.wire(g.node(u.MaterialExpressionScalarParameter,parameter_name='MapTransmission',default_value=.32 if 'Leaf' in mat.get_name() else .40),n,'B');g.output(n,u.MaterialProperty.MP_SUBSURFACE_COLOR)

def crown_volume(mat):
 if not mat.get_name().startswith(('M_Path_Leaf_','M_FirFar_')):return
 if any(str(n.get_editor_property('desc'))=='FloraCrownVolume' for n in M.get_material_expressions(mat)):return
 g=Graph(mat,'FloraCrownVolume');old=M.get_material_property_input_node(mat,u.MaterialProperty.MP_NORMAL);port=str(M.get_material_property_input_node_output_name(mat,u.MaterialProperty.MP_NORMAL));assert old
 n=g.custom(['N','P','Centre','Strength'],'''float3 q=P-Centre;
float3 crown=normalize(float3(q.xy,q.z*.28)+float3(0,0,.01));
return normalize(lerp(normalize(N),crown,saturate(Strength)));''')
 g.wire(old,n,'N',port);g.wire(g.node(u.MaterialExpressionWorldPosition,world_position_shader_offset=u.WorldPositionIncludedOffsets.WPT_EXCLUDE_ALL_SHADER_OFFSETS),n,'P')
 # Resolve the object centre in the vertex stage to retain HISM instance identity.
 centre=g.node(u.MaterialExpressionVertexInterpolator);pins=M.get_material_expression_input_names(centre);g.wire(g.node(u.MaterialExpressionObjectPositionWS),centre,str(pins[0]) if pins else '');g.wire(centre,n,'Centre')
 g.wire(g.node(u.MaterialExpressionScalarParameter,parameter_name='MapCrownVolume',default_value=.62),n,'Strength');g.output(n,u.MaterialProperty.MP_NORMAL)

def debris_material():
 """Native debris has vertex colours, not the purchased trees' bark-atlas UVs."""
 dst=D+'/Foliage/M_FloraDebrisWood';m=u.load_asset(dst)
 if not m:m=E.duplicate_asset('/Game/GrandTour/Environment/NativePlants/v01/M_NZ_Bark',dst)
 if not any(str(n.get_editor_property('desc'))=='FloraDebrisWood' for n in M.get_material_expressions(m)):
  g=Graph(m,'FloraDebrisWood');vc=g.node(u.MaterialExpressionVertexColor)
  n=g.custom(['C','Warm'],'float value=clamp(dot(C,float3(.2126,.7152,.0722)),.055,.32);return Warm*lerp(.7,1.3,saturate(value/.32));')
  g.wire(vc,n,'C');g.wire(g.node(u.MaterialExpressionVectorParameter,parameter_name='MapDebrisWood',default_value=u.LinearColor(.105,.063,.035,1)),n,'Warm');g.output(n,u.MaterialProperty.MP_BASE_COLOR)
 assert not M.recompile_material(m);assert E.save_loaded_asset(m,False);return m
