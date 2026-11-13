"""Bind authored rest relief to all uses of the recovered mud height/normal path."""
import unreal as u
from benmore_river_life_materials import Graph,props
import benmore_woodland_materials as mat
mel=u.MaterialEditingLibrary

def material(m,texture):
 g=Graph(m,'WoodlandPhysicalRelief')
 node=next((e for e in mel.get_material_expressions(m) if isinstance(e,u.MaterialExpressionTextureObject) and str(e.get_editor_property('desc'))=='WoodlandPhysicalRelief'),None)
 if not node:node=g.node(u.MaterialExpressionTextureObject,texture=texture,sampler_type=u.MaterialSamplerType.SAMPLERTYPE_LINEAR_COLOR)
 else:node.set_editor_property('texture',texture)
 count=0
 for e in list(mel.get_material_expressions(m)):
  if not isinstance(e,u.MaterialExpressionCustom):continue
  code=str(e.get_editor_property('code'))
  if 'struct Ground {' not in code:continue
  if 'Texture2D ReliefRest' not in code:
   assert 'SamplerState PS,float DepthScale' in code and 'h=clamp(h,-thickness,15);' in code
   code=code.replace('SamplerState PS,float DepthScale','SamplerState PS,Texture2D ReliefRest,SamplerState RRS,Texture2D Style,SamplerState SS,float DepthScale')
   code=code.replace('Paint,PaintSampler,DepthScale,','Paint,PaintSampler,ReliefRest,ReliefRestSampler,Style,StyleSampler,DepthScale,')
   code=code.replace('h=clamp(h,-thickness,15);','''float4 style=Texture2DSampleLevel(Style,SS,saturate(q),0);
  float2 detail=Texture2DSampleLevel(ReliefRest,RRS,xy/12800.,0).rg;
  float weight=saturate((1-style.r)*(1-style.g)*(1-style.a))*smoothstep(4,30,thickness);
  h+=(dot(detail,float2(65280,255))*(65./65535.)-50)*weight;
  h=clamp(h,-thickness,15);''')
   e.set_editor_property('code',code)
   e.set_editor_property('inputs',list(e.get_editor_property('inputs'))+[props(u.CustomInput(),input_name='ReliefRest')])
  g.wire(node,e,'ReliefRest');count+=1
 assert count>=2,(m.get_name(),count)
 if m.get_name()!='M_Tread':
  # Restore restrained wet-soil response. Correct geometry/normal variation
  # now supplies the relief, rather than trying to hide the issue with matte paint.
  rough=mel.get_material_property_input_node(m,u.MaterialProperty.MP_ROUGHNESS)
  spec=mel.get_material_property_input_node(m,u.MaterialProperty.MP_SPECULAR)
  if isinstance(rough,u.MaterialExpressionConstant):rough.set_editor_property('r',.78)
  if isinstance(spec,u.MaterialExpressionConstant):spec.set_editor_property('r',.12)
 return mat.save(m)

def install(surface):
 texture=mat.texture('relief');props(texture,address_x=u.TextureAddress.TA_WRAP,address_y=u.TextureAddress.TA_WRAP,filter=u.TextureFilter.TF_BILINEAR)
 assert u.GTLandscapeSurfaceSetupLibrary.import_mud_relief(surface,texture,12800.)
 assert u.EditorAssetLibrary.save_loaded_asset(texture)
 for name in ['Terrain','Detail','Tread']:material(u.load_asset(mat.BASE+'/M_'+name),texture)
