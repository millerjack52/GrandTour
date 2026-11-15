"""Wet shading over the accepted clod texture; native geometry/water unchanged."""
import unreal as u
from benmore_river_life_materials import props,Graph
D='/Game/GrandTour/ArtTests/FloraTrail/MudTrial';E=u.EditorAssetLibrary;M=u.MaterialEditingLibrary
PARENT=D+'/M_MudTrial_Wet';INSTANCE=D+'/MI_MudTrial_brown_wet'
PARAMS={'Colour':1.,'Roughness':1.,'Normals':1.,'DampRough':.48,'FilmRough':.16,'Darken':.48,'NormalKeep':.55}
PROFILES={'baseline':{'Colour':0.,'Roughness':0.,'Normals':0.},'colour_only':{'Colour':1.,'Roughness':0.,'Normals':0.},'roughness_only':{'Colour':0.,'Roughness':1.,'Normals':0.},'wet_combined':{'Colour':1.,'Roughness':1.,'Normals':1.}}

def build():
 m=u.load_asset(PARENT) or E.duplicate_asset(D+'/M_MudTrial_ground',PARENT);assert m
 if E.get_metadata_tag(m,'MudWetRevision')!='1':
  nodes=M.get_material_expressions(m)
  wrapper=next(n for n in nodes if isinstance(n,u.MaterialExpressionCustom) and 'TrialRoughness=lerp' in str(n.get_editor_property('code')))
  native=next(n for n in nodes if isinstance(n,u.MaterialExpressionCustom) and 'RR1State=field;' in str(n.get_editor_property('code')))
  # Reuse the native live/rest height calculation already used by the material.
  outputs=list(native.get_editor_property('additional_outputs'));outputs.append(props(u.CustomOutput(),output_name='MudWetState',output_type=u.CustomMaterialOutputType.CMOT_FLOAT2))
  native.set_editor_property('additional_outputs',outputs)
  code=str(native.get_editor_property('code'));anchor='float wet=mud*lerp(.62,1.,1-smoothstep(WaterLevel,WaterLevel+5,height));';assert code.count(anchor)==1
  native.set_editor_property('code',code.replace(anchor,anchor+'\nMudWetState=float2(height,wet);'))
  g=Graph(m,'MudWetResponse')
  # Keep the connected graph valid while adding inputs to its existing output.
  temporary=[g.vector((.12,.1,.08)),g.vector((0,0,1)),g.scalar(.5)]
  for n,prop in zip(temporary,[u.MaterialProperty.MP_BASE_COLOR,u.MaterialProperty.MP_NORMAL,u.MaterialProperty.MP_ROUGHNESS]):g.output(n,prop)
  params={k:g.node(u.MaterialExpressionScalarParameter,parameter_name='MudWet'+k,default_value=v) for k,v in PARAMS.items()}
  # Sample the same relief-aligned UV as colour/normal, so cavities and film agree.
  uv=next(n for n in nodes if isinstance(n,u.MaterialExpressionCustom) and 'HeightTexSampler' in str(n.get_editor_property('code')) and 'int steps=' in str(n.get_editor_property('code')))
  height=g.node(u.MaterialExpressionTextureSampleParameter2D,parameter_name='MudTrialHeight',texture=u.load_asset(D+'/Textures/T_brown_mud_02_height_native'),sampler_type=u.MaterialSamplerType.SAMPLERTYPE_LINEAR_GRAYSCALE,sampler_source=u.SamplerSourceMode.SSM_WRAP_WORLD_GROUP_SETTINGS,mip_value_mode=u.TextureMipValueMode.TMVM_DERIVATIVE)
  g.wire(uv,height,'UVs')
  du=next(n for n in nodes if isinstance(n,u.MaterialExpressionCustom) and str(n.get_editor_property('code'))=='return ddx(UV);');dv=next(n for n in nodes if isinstance(n,u.MaterialExpressionCustom) and str(n.get_editor_property('code'))=='return ddy(UV);')
  g.wire(du,height,'DDX(UVs)');g.wire(dv,height,'DDY(UVs)')
  inputs=list(wrapper.get_editor_property('inputs'))
  for name in ['WetState','ReliefHeight']+['Wet'+k for k in PARAMS]:inputs.append(props(u.CustomInput(),input_name=name))
  wrapper.set_editor_property('inputs',inputs)
  g.wire(native,wrapper,'WetState','MudWetState');g.wire(height,wrapper,'ReliefHeight','R')
  for k,n in params.items():g.wire(n,wrapper,'Wet'+k)
  code=str(wrapper.get_editor_property('code'))
  start=code.index('float3 n=normalize(')
  code=code[:start]+'''
// Damp clod tops remain rougher; live low ground and relief cavities take film.
float low=1-smoothstep(-3.,12.,WetState.x);
float cavity=1-smoothstep(.32,.66,ReliefHeight);
float moisture=saturate(.38+.40*low+.20*saturate((WetState.y-.62)/.38));
float film=saturate(.20+.55*low+.25*cavity)*moisture;
float normalScale=lerp(1.,WetNormalKeep,film*WetNormals);
float3 n=normalize(float3(NativeNormal.xy+float2(Normal.x,-Normal.y)*Strength*normalScale,NativeNormal.z));
TrialNormal=normalize(lerp(OldNormal,n,mask));
float dryRough=clamp(Roughness*.65+OldRough*.35,.08,.96);
float wetRough=clamp(lerp(WetDampRough,WetFilmRough,film)+.035*(Roughness-.85),.10,.65);
TrialRoughness=lerp(OldRough,lerp(dryRough,wetRough,WetRoughness),mask);
return lerp(Base,Colour*wet*lerp(1.,WetDarken,moisture*WetColour),mask);
'''
  wrapper.set_editor_property('code',code)
  g.output(wrapper,u.MaterialProperty.MP_BASE_COLOR);g.output(wrapper,u.MaterialProperty.MP_NORMAL,'TrialNormal');g.output(wrapper,u.MaterialProperty.MP_ROUGHNESS,'TrialRoughness')
  for n in temporary:M.delete_material_expression(m,n)
  assert not M.recompile_material(m);E.set_metadata_tag(m,'MudWetRevision','1');assert E.save_loaded_asset(m,False)
 mi=u.load_asset(INSTANCE) or E.duplicate_asset(D+'/MI_MudTrial_brown_mud_02',INSTANCE);assert mi
 M.set_material_instance_parent(mi,m);assert E.save_loaded_asset(mi,False);return mi

def configure(mi,values,persistent=False):
 for k,v in {**PARAMS,**values}.items():
  if persistent:M.set_material_instance_scalar_parameter_value(mi,'MudWet'+k,v)
  else:mi.set_scalar_parameter_value('MudWet'+k,v)
 if persistent:M.update_material_instance(mi);assert E.save_loaded_asset(mi,False)
