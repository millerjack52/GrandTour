"""Map-local level standing water; retain the physical solver and muddy bed."""
import unreal as u
from benmore_river_life_materials import props,Graph
E=u.EditorAssetLibrary;M=u.MaterialEditingLibrary
D='/Game/GrandTour/ArtTests/FloraTrail/MudTrial'
TARGET=D+'/M_WaterFlat'
PROFILES={'baseline':(0.,0.),'geometry_only':(1.,0.),'flat_water':(1.,1.)}

def build(source):
 m=u.load_asset(TARGET) or E.duplicate_asset(source,TARGET);assert m
 if E.get_metadata_tag(m,'FloraFlatWaterRevision')=='1':return m
 nodes=[n for n in M.get_material_expressions(m) if isinstance(n,u.MaterialExpressionCustom) and 'float waterDepth=min(wave.g,' in str(n.get_editor_property('code'))]
 assert len(nodes)==7,len(nodes)
 g=Graph(m,'FloraFlatWater')
 tails=[('return smoothstep(.05,.65,waterDepth)',u.MaterialProperty.MP_OPACITY_MASK,g.scalar(1)),
        ('saturate(nativeFoam));',u.MaterialProperty.MP_BASE_COLOR,g.vector((.1,.08,.05))),
        ('return 1-transmission*(1-turbidity);',u.MaterialProperty.MP_OPACITY,g.scalar(1)),
        ('return .10;',u.MaterialProperty.MP_ROUGHNESS,g.scalar(.1)),
        ('return .25;',u.MaterialProperty.MP_SPECULAR,g.scalar(.25)),
        ('return float3(0,0,wave.r+nativeRippleCm);',u.MaterialProperty.MP_WORLD_POSITION_OFFSET,g.vector((0,0,0))),
        ('return normalize(float3(slopes,1));',u.MaterialProperty.MP_NORMAL,g.vector((0,0,1)))]
 outputs=[]
 for marker,prop,temp in tails:
  matches=[n for n in nodes if marker in str(n.get_editor_property('code'))];assert len(matches)==1,(marker,len(matches))
  outputs.append((matches[0],prop,temp));g.output(temp,prop)
 flat=g.node(u.MaterialExpressionScalarParameter,parameter_name='FloraWaterFlat',default_value=1.)
 quiet=g.node(u.MaterialExpressionScalarParameter,parameter_name='FloraWaterQuietNormals',default_value=1.)
 for n in nodes:
  inputs=list(n.get_editor_property('inputs'))
  for name in ('FlatWater','QuietNormals'):inputs.append(props(u.CustomInput(),input_name=name))
  n.set_editor_property('inputs',inputs);g.wire(flat,n,'FlatWater');g.wire(quiet,n,'QuietNormals')
  code=str(n.get_editor_property('code'))
  before='float waterDepth=min(wave.g,max(0,Level+wave.r-baseBed-height));'
  assert code.count(before)==1
  code=code.replace(before,'float waterDepth=min(wave.g,max(0,Level+wave.r*(1-FlatWater)-baseBed-height));')
  before='float nativeRippleCm=max(-waterDepth,(nativeState.r-.50195998)*80)*NativeWaterReady;'
  assert code.count(before)==1
  code=code.replace(before,before.replace('*NativeWaterReady;','*NativeWaterReady*(1-FlatWater);'))
  code=code.replace('return float3(0,0,wave.r+nativeRippleCm);','return float3(0,0,wave.r*(1-FlatWater)+nativeRippleCm);')
  code=code.replace('return normalize(float3(slopes,1));','return normalize(float3(slopes*(1-QuietNormals),1));')
  n.set_editor_property('code',code)
 for n,prop,temp in outputs:g.output(n,prop);M.delete_material_expression(m,temp)
 assert not M.recompile_material(m)
 E.set_metadata_tag(m,'FloraFlatWaterRevision','1');assert E.save_loaded_asset(m,False)
 return m

def configure(mid,profile):
 for name,value in zip(('FloraWaterFlat','FloraWaterQuietNormals'),profile):mid.set_scalar_parameter_value(name,value)
