"""Adapt verified crown response without replacing LiDAR geometry or coverage."""
import unreal as u,json,hashlib
from pathlib import Path
from benmore_river_life_materials import Graph,props
from flora_world_art_direction import local_volume
R=Path('C:/GrandTour');CFG=json.loads((R/'Art/lidar_flora_transfer_settings.json').read_text())
D='/Game/GrandTour/ArtTests/LidarStudy/FloraTrailStyle/'+CFG['revision']
M=u.MaterialEditingLibrary;E=u.EditorAssetLibrary
def path(m):return m.get_path_name()
def eligible(m):return m and '/LidarStudy/Flora' in path(m) and '/FloraTrailStyle/' not in path(m) and any(s in m.get_name() for s in ('Path_Leaf_0','FirFar_'))
def input_node(m,prop):return M.get_material_property_input_node(m,prop),str(M.get_material_property_input_node_output_name(m,prop) or '')
def textures(m):return sorted(path(n.get_editor_property('texture')) for n in M.get_material_expressions(m) if isinstance(n,(u.MaterialExpressionTextureSample,u.MaterialExpressionTextureObject)) and n.get_editor_property('texture'))
def clone(src,cache,checks):
 if path(src) in cache:return cache[path(src)]
 name=src.get_name()+'_'+hashlib.sha1(path(src).encode()).hexdigest()[:8]
 dest=D+'/'+name;m=u.load_asset(dest)
 if m:
  assert E.get_metadata_tag(m,'LidarTransferSource')==path(src)
  cache[path(src)]=m
  if isinstance(m,u.MaterialInstanceConstant):assert m.get_editor_property('parent')==clone(src.get_editor_property('parent'),cache,checks)
  if isinstance(m,u.Material):
   assert textures(src)==textures(m);checks.append({'source':path(src),'copy':path(m),'far':'FirFar_' in src.get_name(),'textures_preserved':True,'reused':True})
  return m
 m=E.duplicate_asset(path(src).split('.')[0],dest);assert m;cache[path(src)]=m;E.set_metadata_tag(m,'LidarTransferSource',path(src))
 if isinstance(m,u.MaterialInstanceConstant):
  M.set_material_instance_parent(m,clone(src.get_editor_property('parent'),cache,checks));assert E.save_loaded_asset(m,False);return m
 assert isinstance(m,u.Material)
 far='FirFar_' in src.get_name();nodes=list(M.get_material_expressions(m));g=Graph(m,'FloraTrailTransfer')
 # Replace the former second palette treatment with the accepted woodland tint.
 found=False
 for n in nodes:
  if isinstance(n,u.MaterialExpressionVectorParameter) and str(n.get_editor_property('parameter_name'))=='MapFoliageTint':n.set_editor_property('default_value',u.LinearColor(*CFG['leaf_tint'],1));found=True
  if isinstance(n,u.MaterialExpressionScalarParameter):
   k=str(n.get_editor_property('parameter_name'))
   if k=='CrownPigmentStrength':n.set_editor_property('default_value',0.)
   if k=='MapCrownVolume':n.set_editor_property('default_value',CFG['CrownVolume'])
  if isinstance(n,u.MaterialExpressionCustom) and str(n.get_editor_property('desc'))=='FloraWorldColour':n.set_editor_property('code','return Base*Tint*lerp(.88,1.06,saturate(Variation));')
 if not found:
  old,out=input_node(m,u.MaterialProperty.MP_BASE_COLOR);c=g.custom(['C','R'],'return C*float3(.76,.86,.94)*lerp(.88,1.06,R);');g.wire(old,c,'C',out);g.wire(g.node(u.MaterialExpressionPerInstanceRandom),c,'R');g.output(c,u.MaterialProperty.MP_BASE_COLOR)
 if not far:
  props(m,tangent_space_normal=False,shading_model=u.MaterialShadingModel.MSM_TWO_SIDED_FOLIAGE)
  params={k:g.node(u.MaterialExpressionScalarParameter,parameter_name=k,default_value=CFG[k]) for k in ('LeafTransmission','CrownOcclusion','CrownVolume','CrownCard')}
  q=local_volume(g);uv=g.node(u.MaterialExpressionTextureCoordinate,coordinate_index=0)
  radial=g.custom(['Q'],'return normalize(float3((Q.xy-.5)*2.,(Q.z-.62)*1.6)+float3(0,0,.0001));');g.wire(q,radial,'Q')
  radial_world=g.node(u.MaterialExpressionTransform,transform_source_type=u.MaterialVectorCoordTransformSource.TRANSFORMSOURCE_INSTANCE,transform_type=u.MaterialVectorCoordTransform.TRANSFORM_WORLD);g.wire(radial,radial_world,'')
  card=g.custom(['UV'],'return normalize(float3((UV-.5)*1.8,.8));');g.wire(uv,card,'UV')
  card_world=g.node(u.MaterialExpressionTransform,transform_source_type=u.MaterialVectorCoordTransformSource.TRANSFORMSOURCE_TANGENT,transform_type=u.MaterialVectorCoordTransform.TRANSFORM_WORLD);g.wire(card,card_world,'')
  normal=g.custom(['Mesh','Radial','Card','CardStrength','Volume'],'''float3 mesh=normalize(lerp(float3(0,0,1),normalize(Mesh),.78));
float3 branch=normalize(lerp(mesh,normalize(Card),saturate(CardStrength)));
return normalize(lerp(branch,normalize(Radial),saturate(Volume)));''')
  for node,pin in [(g.node(u.MaterialExpressionVertexNormalWS),'Mesh'),(radial_world,'Radial'),(card_world,'Card'),(params['CrownCard'],'CardStrength'),(params['CrownVolume'],'Volume')]:g.wire(node,normal,pin)
  g.output(normal,u.MaterialProperty.MP_NORMAL)
  old,out=input_node(m,u.MaterialProperty.MP_AMBIENT_OCCLUSION)
  ao=g.custom(['Q','UV','Original','Strength'],'''float radius=length((Q.xy-.5)*2.);
float exposed=max(smoothstep(.20,.90,radius),smoothstep(.78,.98,Q.z));
float fan=lerp(.65,1.,smoothstep(.10,.85,length((UV-.5)*2.)));
return Original*lerp(1.,lerp(.35,1.,exposed)*fan,saturate(Strength));''',u.CustomMaterialOutputType.CMOT_FLOAT1)
  g.wire(q,ao,'Q');g.wire(uv,ao,'UV');g.wire(old or g.scalar(1.),ao,'Original',out);g.wire(params['CrownOcclusion'],ao,'Strength');g.output(ao,u.MaterialProperty.MP_AMBIENT_OCCLUSION)
  base,port=input_node(m,u.MaterialProperty.MP_BASE_COLOR);sub=g.custom(['C','Strength'],'return C*Strength;');g.wire(base,sub,'C',port);g.wire(params['LeafTransmission'],sub,'Strength');g.output(sub,u.MaterialProperty.MP_SUBSURFACE_COLOR)
  g.output(g.scalar(CFG['roughness']),u.MaterialProperty.MP_ROUGHNESS);g.output(g.scalar(CFG['specular']),u.MaterialProperty.MP_SPECULAR)
 assert textures(src)==textures(m)
 for pin in (u.MaterialProperty.MP_WORLD_POSITION_OFFSET,u.MaterialProperty.MP_OPACITY_MASK):
  a,ao=input_node(src,pin);b,bo=input_node(m,pin);assert (a.get_name() if a else None,ao)==(b.get_name() if b else None,bo)
 assert not M.recompile_material(m);assert E.save_loaded_asset(m,False)
 checks.append({'source':path(src),'copy':path(m),'far':far,'textures_preserved':True,'coverage_wind_preserved':True})
 return m
def grade(src):
 dest=D+'/M_FloraTrailFinish';m=u.load_asset(dest)
 if m:return m
 m=E.duplicate_asset(path(src).split('.')[0],dest);assert m;E.set_metadata_tag(m,'LidarTransferSource',path(src))
 g=Graph(m,'FloraTrailTransferGrade');old,out=input_node(m,u.MaterialProperty.MP_EMISSIVE_COLOR);assert old
 strength=g.node(u.MaterialExpressionScalarParameter,parameter_name='FloraTrailGrade',default_value=CFG['grade_strength'])
 n=g.custom(['C','Strength'],'''float3 c=max(0.,C);
// LiDAR already has an SDR finish. Decode, apply the reviewed relative grade,
// then encode; retain its native exposure/tonemapper and existing haze pass.
float3 x=lerp(c/12.92,pow((c+.055)/1.055,2.4),step(.04045,c));
float lum=dot(x,float3(.2126,.7152,.0722));
float shadow=1-smoothstep(.01,.22,lum);
float highlight=smoothstep(.32,.85,lum);
float3 shaded=pow(max(x,0.),1./float3(1.04,1.04,1.04))*float3(.99,1.01,1.03);
float3 graded=lerp(x,shaded,shadow)*lerp(float3(1,1,1),float3(1.005,1.,.99),highlight);
x=lerp(x,graded,saturate(Strength));
return lerp(12.92*x,1.055*pow(x,1./2.4)-.055,step(.0031308,x));''')
 g.wire(old,n,'C',out);g.wire(strength,n,'Strength');g.output(n,u.MaterialProperty.MP_EMISSIVE_COLOR)
 assert not M.recompile_material(m);assert E.save_loaded_asset(m,False);return m
def install(world):
 cache={};checks=[];bindings=[];grade_bindings=[]
 for a in u.GameplayStatics.get_all_actors_of_class(world,u.Actor):
  for c in a.get_components_by_class(u.StaticMeshComponent):
   if not c.get_editor_property('visible') or c.get_editor_property('hidden_in_game'):continue
   for i,m in enumerate(c.get_materials()):
    if eligible(m):
     new=clone(m,cache,checks);c.set_material(i,new);bindings.append({'actor':a.get_actor_label(),'component':c.get_name(),'slot':i,'source':path(m),'copy':path(new)})
  if isinstance(a,u.PostProcessVolume):
   s=a.settings;items=list(s.weighted_blendables.array);changed=False
   for b in items:
    if b.object and b.object.get_name()=='M_EvergreenHaze':b.object=grade(b.object);changed=True;grade_bindings.append(a.get_actor_label())
   if changed:s.weighted_blendables=props(u.WeightedBlendables(),array=items);a.settings=s
 assert len(checks)>=6 and len(grade_bindings)==1,(len(checks),grade_bindings)
 return {'materials':checks,'bindings':bindings,'grade_volumes':grade_bindings,'settings':CFG}
def prepare(audit):
 cache={};checks=[]
 for c in audit['components']:
  if not c.get('visible',True) or c.get('hidden_in_game',False):continue
  for p in c['materials']:
   if p and '/LidarStudy/Flora' in p and any(t in p for t in ('Path_Leaf_0','FirFar_')):
    m=u.load_asset(p)
    if eligible(m):clone(m,cache,checks)
 for pp in audit['postprocess']:
  for b in pp['blendables']:
   if b['path'] and 'M_EvergreenHaze.' in b['path']:grade(u.load_asset(b['path']))
 return checks
