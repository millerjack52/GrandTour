"""Instance-space pigment volumes: art direction without screen-space blur.

Keep the purchased masks, real lighting, mesh silhouettes and contact graph.
All effects are map-local, parameterized and add no texture samples or geometry.
"""
import unreal as u
from benmore_river_life_materials import Graph
M=u.MaterialEditingLibrary

def parameter(g,name,value):
 return g.node(u.MaterialExpressionScalarParameter,parameter_name=name,default_value=value)

def local_volume(g):
 # Instance bounds, not the kilometre-wide HISM component bounds. Evaluate
 # mesh coordinates before wind/deformation and interpolate to the pixel stage.
 bounds=g.node(u.MaterialExpressionBounds)
 q=g.custom(['P','Lo','Hi'],'return (P-Lo)/max(Hi-Lo,float3(.1,.1,.1));')
 g.wire(g.node(u.MaterialExpressionPreSkinnedPosition),q,'P')
 g.wire(bounds,q,'Lo','Min');g.wire(bounds,q,'Hi','Max')
 v=g.node(u.MaterialExpressionVertexInterpolator)
 pins=M.get_material_expression_input_names(v);g.wire(q,v,str(pins[0]) if pins else '')
 return v

def world_centre(g):
 v=g.node(u.MaterialExpressionVertexInterpolator)
 pins=M.get_material_expression_input_names(v)
 g.wire(g.node(u.MaterialExpressionObjectPositionWS),v,str(pins[0]) if pins else '')
 return v

def install(mat,cfg):
 name=mat.get_name()
 plant=any(t in name for t in ['M_Path_Fern','M_Path_Grass','M_Path_Plant','M_Path_Shrubbery'])
 wood=name.startswith('M_Path_Wood') or name=='M_FloraDebrisWood'
 crown=name.startswith(('M_Path_Leaf','M_FirFar'))
 if not (plant or wood or crown):return None
 tag='FloraReferenceVolumes'
 existing=[n for n in M.get_material_expressions(mat) if str(n.get_editor_property('desc'))==tag]
 defaults={'PlantRootDepth':cfg.get('plant_root_depth',.42),'PlantTipWarmth':cfg.get('plant_tip_warmth',.30),
           'PlantVolumeNormal':cfg.get('plant_volume_normal',.32),'BarkMossStrength':cfg.get('bark_moss',.48),
           'CrownPigmentStrength':cfg.get('crown_pigment',.24)}
 if existing:
  for n in existing:
   if isinstance(n,u.MaterialExpressionScalarParameter):
    key=str(n.get_editor_property('parameter_name'))
    if key in defaults:n.set_editor_property('default_value',defaults[key])
   if wood and isinstance(n,u.MaterialExpressionCustom):
    code=str(n.get_editor_property('code'))
    if 'float moss=' in code:
     code=code.replace('smoothstep(.40,.75,stroke)*smoothstep(.12,.40,broken)*(1-smoothstep(.07,.29,Q.z))','smoothstep(.58,.80,stroke)*smoothstep(.35,.65,broken)*(1-smoothstep(.035,.20,Q.z))')
     code=code.replace('float3(.10,.145,.032)*clamp(lum/.10,.6,1.7)','float3(.11,.14,.04)*clamp(lum/.10,.25,1.35)')
     n.set_editor_property('code',code)
  return 'updated'
 g=Graph(mat,tag)
 src=M.get_material_property_input_node(mat,u.MaterialProperty.MP_BASE_COLOR)
 port=str(M.get_material_property_input_node_output_name(mat,u.MaterialProperty.MP_BASE_COLOR));assert src
 q=local_volume(g) if plant or wood else None
 centre=world_centre(g)
 if plant:
  colour=g.custom(['Base','Q','Centre','Depth','Warmth'],'''
float height=saturate(Q.z);
float edge=saturate(length((Q.xy-.5)*2));
float open=smoothstep(.12,.76,height)*lerp(.67,1.,edge);
float3 shade=float3(.62,.79,.78);
float3 pigment=Base*lerp(1.,shade,Depth*(1-open));
// Ochre at exposed tips, blue-green at the root: pigment, not fake emissive light.
float tips=smoothstep(.52,.94,height);
pigment*=lerp(float3(1,1,1),float3(1.20,1.065,.79),tips*Warmth);
// Broad colonies, constant per clump; avoids every blade becoming a rainbow.
float colony=.5+.5*sin(Centre.x*.00135+sin(Centre.y*.0017)*2.1);
float coral=smoothstep(.73,.91,colony);
float lum=dot(pigment,float3(.2126,.7152,.0722));
float3 rust=float3(.35,.115,.062);rust*=lum/max(.01,dot(rust,float3(.2126,.7152,.0722)));
return lerp(pigment,rust,coral*.46);
''')
  g.wire(src,colour,'Base',port);g.wire(q,colour,'Q');g.wire(centre,colour,'Centre')
  g.wire(parameter(g,'PlantRootDepth',defaults['PlantRootDepth']),colour,'Depth')
  g.wire(parameter(g,'PlantTipWarmth',defaults['PlantTipWarmth']),colour,'Warmth')
  old=M.get_material_property_input_node(mat,u.MaterialProperty.MP_NORMAL)
  normalport=str(M.get_material_property_input_node_output_name(mat,u.MaterialProperty.MP_NORMAL));assert old
  n=g.custom(['N','P','Centre','Q','Strength'],'''
float3 d=P-Centre;
float3 dome=normalize(float3(d.xy,max(12.,length(d.xy)*.65)));
float blend=Strength*lerp(.55,1.,smoothstep(.05,.7,Q.z));
return normalize(lerp(normalize(N),dome,blend));
''')
  g.wire(old,n,'N',normalport);g.wire(q,n,'Q');g.wire(centre,n,'Centre')
  g.wire(g.node(u.MaterialExpressionWorldPosition,world_position_shader_offset=u.WorldPositionIncludedOffsets.WPT_EXCLUDE_ALL_SHADER_OFFSETS),n,'P')
  g.wire(parameter(g,'PlantVolumeNormal',defaults['PlantVolumeNormal']),n,'Strength');g.output(n,u.MaterialProperty.MP_NORMAL)
 elif wood:
  colour=g.custom(['Base','Q','Centre','Strength'],'''
// Tall, broken patches on lower bark, rather than horizontal moss rings.
float2 v=(Q.xy-.5)*2;
float angle=atan2(v.y,v.x);
float stroke=.5+.5*sin(angle*5.+sin(Q.z*43.+angle*3.)*1.1+Centre.x*.013);
float broken=.5+.5*sin(Q.z*29.+angle*2.4);
float moss=smoothstep(.58,.80,stroke)*smoothstep(.35,.65,broken)*(1-smoothstep(.035,.20,Q.z));
float lum=dot(Base,float3(.2126,.7152,.0722));
float3 green=float3(.11,.14,.04)*clamp(lum/.10,.25,1.35);
return lerp(Base,green,moss*Strength);
''')
  g.wire(src,colour,'Base',port);g.wire(q,colour,'Q');g.wire(centre,colour,'Centre')
  g.wire(parameter(g,'BarkMossStrength',defaults['BarkMossStrength']),colour,'Strength')
 else:
  colour=g.custom(['Base','Centre','Strength'],'''
// 20-60m families unify adjacent trees; leaves retain the source painted detail.
float field=.5+.5*sin(Centre.x*.00031+sin(Centre.y*.00027)*2.2);
float3 family=lerp(float3(.75,.93,.90),float3(1.12,1.02,.73),smoothstep(.12,.88,field));
return Base*lerp(float3(1,1,1),family,Strength);
''')
  g.wire(src,colour,'Base',port);g.wire(centre,colour,'Centre')
  g.wire(parameter(g,'CrownPigmentStrength',defaults['CrownPigmentStrength']),colour,'Strength')
 g.output(colour,u.MaterialProperty.MP_BASE_COLOR)
 # Ensure the transmission colour follows the final pigment, not an earlier wrapper.
 for n in M.get_material_expressions(mat):
  if isinstance(n,u.MaterialExpressionMultiply) and str(n.get_editor_property('desc'))=='FloraCoherentTransmission':g.wire(colour,n,'A')
 return 'plant' if plant else 'bark' if wood else 'crown'
