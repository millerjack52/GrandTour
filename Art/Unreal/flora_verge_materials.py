"""Terrain-only woodland floor trial, reusing the installed source textures."""
import unreal as u
from benmore_river_life_materials import Graph,props,NOISE
E=u.EditorAssetLibrary;M=u.MaterialEditingLibrary
D='/Game/GrandTour/ArtTests/FloraTrail/MudTrial';TARGET=D+'/M_VergeLandscape'

def build(source,target=TARGET):
 m=u.load_asset(target) or E.duplicate_asset(source.get_path_name().split('.')[0],target);assert m
 g=Graph(m,'FloraVergeFloor')
 revision=E.get_metadata_tag(m,'FloraVergeRevision')
 if revision=='3':return m
 nodes=M.get_material_expressions(m)
 # Reuse the existing POM-aligned forest samples; no extra texture reads.
 samples={}
 for i in range(3):
  for suffix,key in [('', 'C'),('N','N')]:
   name='T_ForestGround_%02d%s'%(i+1,suffix)
   samples[key+str(i)]=next(n for n in nodes if isinstance(n,u.MaterialExpressionTextureSample) and str(n.get_editor_property('desc'))=='ForestFloorDetail' and n.get_editor_property('texture') and n.get_editor_property('texture').get_name()==name)
 if revision in ('1','2'):
  node=next(n for n in nodes if isinstance(n,u.MaterialExpressionCustom) and 'VergeNormal=' in str(n.get_editor_property('code')))
  for key,sample in samples.items():g.wire(sample,node,key,'RGB')
  code=str(node.get_editor_property('code')).replace('(patch-.5)*95.','(patch-.5)*40.').replace('smoothstep(290.,430.,edge)','smoothstep(215.,310.,edge)')
  node.set_editor_property('code',code)
  for n in nodes:
   if isinstance(n,u.MaterialExpressionTextureSample) and str(n.get_editor_property('desc'))=='FloraVergeFloor':M.delete_material_expression(m,n)
  assert not M.recompile_material(m);E.set_metadata_tag(m,'FloraVergeRevision','3');assert E.save_loaded_asset(m,False)
  return m
 originals={name:(M.get_material_property_input_node(m,p),M.get_material_property_input_node_output_name(m,p)) for name,p in [('Base',u.MaterialProperty.MP_BASE_COLOR),('OldNormal',u.MaterialProperty.MP_NORMAL),('OldRough',u.MaterialProperty.MP_ROUGHNESS)]}
 assert originals['Base'][0],source.get_path_name()
 p=g.node(u.MaterialExpressionWorldPosition)
 enabled=g.node(u.MaterialExpressionScalarParameter,parameter_name='FloraVergeEnabled',default_value=1.)
 inputs={'P':(p,''),'Enabled':(enabled,'')}
 for k,(n,out) in originals.items():inputs[k]=(n or (g.vector((0,0,1)) if k=='OldNormal' else g.scalar(.9)),out)
 for key,sample in samples.items():inputs[key]=(sample,'RGB')
 node=g.custom(list(inputs),NOISE+'''
float centre=530*sin((P.x+2200)/1050)-150;
float patch=f.n(P.xy/390.)*.7+f.n(P.xy/110.+17.)*.3;
float edge=abs(P.y-centre)+(patch-.5)*40.;
float weight=smoothstep(215.,310.,edge)*Enabled;
float moss=smoothstep(.42,.69,patch)*.78;
float litter=smoothstep(.39,.66,f.n(P.xy/275.+31.))*.62;
float3 colour=lerp(C2,C0,moss);colour=lerp(colour,C1,litter);
// Source pigment variation retained, with restrained moss and warm litter.
colour*=float3(.35,.37,.32)*lerp(.82,1.12,f.n(P.xy/740.));
float3 detail=normalize(lerp(lerp(N2,N0,moss),N1,litter));
VergeNormal=normalize(lerp(OldNormal,normalize(float3(OldNormal.xy+float2(detail.x,-detail.y)*.65,OldNormal.z)),weight));
VergeRough=lerp(OldRough,.91,weight);
return lerp(Base,colour,weight);
''',outputs=[('VergeNormal',u.CustomMaterialOutputType.CMOT_FLOAT3),('VergeRough',u.CustomMaterialOutputType.CMOT_FLOAT1)])
 for k,(n,out) in inputs.items():g.wire(n,node,k,out)
 g.output(node,u.MaterialProperty.MP_BASE_COLOR);g.output(node,u.MaterialProperty.MP_NORMAL,'VergeNormal');g.output(node,u.MaterialProperty.MP_ROUGHNESS,'VergeRough')
 assert not M.recompile_material(m);E.set_metadata_tag(m,'FloraVergeRevision','3');assert E.save_loaded_asset(m,False)
 return m

def mud_instance():
 parent=build(u.load_asset(D+'/M_MudTrial_Wet'),D+'/M_VergeMud')
 path=D+'/MI_VergeMud';mi=u.load_asset(path) or E.duplicate_asset(D+'/MI_MudTrial_brown_wet',path);assert mi
 M.set_material_instance_parent(mi,parent);assert E.save_loaded_asset(mi,False)
 return mi
