"""Map-owned, distance-dependent art direction; source assets remain untouched."""
import unreal as u,json,sys,os,time,traceback,zipfile
from pathlib import Path
ROOT=Path(u.Paths.project_dir()).resolve();sys.path.insert(0,str(ROOT/'Art/Unreal'))
import canopy_depth as C
import lidar_far_haze as H
from benmore_river_life_materials import Graph,props
from forest_shaders import connected_nodes
assets=u.EditorAssetLibrary;mel=u.MaterialEditingLibrary;les=u.get_editor_subsystem(u.LevelEditorSubsystem)
DEST=C.BASE+'/FirewatchStyle';QA=ROOT/'Saved/LidarAuthoringQA/FirewatchStyle';QA.mkdir(exist_ok=True)
CONFIG=ROOT/'Art/Export/LidarStudy/FirewatchStyle/recipe.json'
SCALARS=dict(Strength=0,StartCm=18000,FullCm=85000,NormalSimplification=.95,PatchVariation=.1,PatchSizeCm=9000,HazeIntensity=0,HazeStartCm=90000,HazeFullCm=240000)
VECTORS=dict(ForestColour=(.11,.23,.155,1),ShadowColour=(.055,.11,.095,1),GroundTint=(.88,1.03,.94,1),HazeColour=(.48,.61,.59,1),FieldDomain=(-185000,-185000,370000,370000),SunDirection=(-.1586355,.8996666,.4067366,0))

def enabled():return CONFIG.exists() and json.loads(CONFIG.read_text()).get('enabled',False)

def new(name,cls,factory):return u.load_asset(DEST+'/'+name) or u.AssetToolsHelpers.get_asset_tools().create_asset(name,DEST,cls,factory)

def collection():
 m=new('MPC_DistanceStyle',u.MaterialParameterCollection,u.MaterialParameterCollectionFactoryNew())
 if not list(m.get_editor_property('scalar_parameters')):
  props(m,scalar_parameters=[props(u.CollectionScalarParameter(),parameter_name=k,default_value=v) for k,v in SCALARS.items()],vector_parameters=[props(u.CollectionVectorParameter(),parameter_name=k,default_value=u.LinearColor(*v)) for k,v in VECTORS.items()])
  assert assets.save_loaded_asset(m,False)
 return m

def param(g,name):return g.node(u.MaterialExpressionCollectionParameter,collection=u.load_asset(DEST+'/MPC_DistanceStyle'),parameter_name=name)

def profiles():
 rows={}
 for name,strength,start,full,haze,hs,hf in [('Subtle',.35,200,1000,.38,1100,2800),('Medium',.72,180,850,.58,850,2400),('Strong',1.,150,700,.76,650,1900)]:
  existing=u.load_asset(DEST+'/DA_Lidar_'+name)
  factory=props(u.DataAssetFactory(),data_asset_class=u.GTDistanceStyleProfile)
  p=new('DA_Lidar_'+name,u.GTDistanceStyleProfile,factory)
  if not existing or os.environ.get('GT_STYLE_RESET_PROFILES')=='1':
   props(p,strength=strength,start_metres=start,full_metres=full,normal_simplification=.95,forest_colour=u.LinearColor(.035,.09,.065,1),shadow_colour=u.LinearColor(.018,.036,.029,1),ground_tint=u.LinearColor(.88,1.03,.94,1),patch_variation=.10,patch_size_metres=90,haze_intensity=haze,haze_start_metres=hs,haze_full_metres=hf,haze_colour=u.LinearColor(.50,.63,.57,1))
   assert assets.save_loaded_asset(p,False)
  rows[name]={k:p.get_editor_property(k) for k in ['strength','start_metres','full_metres','haze_intensity','haze_start_metres','haze_full_metres']}
 return rows

def clone(src,name):
 dst=DEST+'/'+name
 return u.load_asset(dst) or assets.duplicate_asset(src.get_path_name().split('.')[0],dst)

def wrap(m,ground=False):
 if any(str(n.get_editor_property('desc'))=='FirewatchDistance' for n in connected_nodes(m)):
  if ground:unify_forest_floor(m)
  return
 g=Graph(m,'FirewatchDistance')
 inputs={}
 for name,prop in [('C',u.MaterialProperty.MP_BASE_COLOR),('N',u.MaterialProperty.MP_NORMAL),('OldAO',u.MaterialProperty.MP_AMBIENT_OCCLUSION),('SS',u.MaterialProperty.MP_SUBSURFACE_COLOR)]:
  n=mel.get_material_property_input_node(m,prop);out=mel.get_material_property_input_node_output_name(m,prop)
  if not n:n=g.scalar(1) if name=='OldAO' else g.vector((0,0,1) if name=='N' else (0,0,0));out=''
  inputs[name]=(n,out)
 # All current canopy normals are world-space; terrain may use tangent-space.
 tangent=m.get_editor_property('tangent_space_normal')
 names=list(inputs)+['P','Camera','Field','Strength','StartCm','FullCm','NormalSimplification','ForestColour','ShadowColour','GroundTint','PatchVariation','PatchSizeCm','FieldDomain','SunDirection']
 code='''
float d=length(P-Camera);float fade=smoothstep(StartCm,FullCm,d)*Strength;
float2 uv=(P.xy-FieldDomain.xy)/FieldDomain.zw;
float4 field=Texture2DSampleLevel(Field,FieldSampler,uv,3);
float2 xy=field.rg*2-1;float3 macro=normalize(float3(xy,sqrt(max(.01,1-dot(xy,xy)))));
float facing=smoothstep(-.15,.75,dot(macro,normalize(SunDirection.rgb)));
float visibility=smoothstep(.08,.9,field.b);
float light=saturate(.22+.78*facing)*lerp(.45,1,visibility);
float2 p=P.xy/max(500,PatchSizeCm);
float patch=(sin(p.x*.73+p.y*.31)+sin(p.y*.91-p.x*.24))*.5;
float3 target=lerp(ShadowColour.rgb,ForestColour.rgb,light)*(1+patch*PatchVariation);
'''
 if ground:code+='''
// Retain land-cover identity; remove only high-frequency contrast with distance.
float lum=dot(C,float3(.2126,.7152,.0722));
target=lerp(C,lum.xxx,.18)*GroundTint.rgb;
Normal=normalize(lerp(N,macro,fade*NormalSimplification*.65));
'''
 else:code+='Normal=normalize(lerp(N,'+('float3(0,0,1)' if tangent else 'macro')+',fade*NormalSimplification));\n'
 code+='AO=lerp(OldAO,1,fade);Subsurface=SS*(1-fade);return lerp(C,target,fade);'
 n=g.custom(names,code,outputs=[('Normal',u.CustomMaterialOutputType.CMOT_FLOAT3),('AO',u.CustomMaterialOutputType.CMOT_FLOAT1),('Subsurface',u.CustomMaterialOutputType.CMOT_FLOAT3)])
 for key,(a,out) in inputs.items():g.wire(a,n,key,out)
 for key in names[len(inputs)+3:]:g.wire(param(g,key),n,key)
 g.wire(g.node(u.MaterialExpressionWorldPosition),n,'P');g.wire(g.node(u.MaterialExpressionCameraPositionWS),n,'Camera')
 g.wire(g.node(u.MaterialExpressionTextureObject,texture=u.load_asset(C.DEST+'/T_CD_Lighting'),sampler_type=u.MaterialSamplerType.SAMPLERTYPE_LINEAR_COLOR),n,'Field')
 for prop,out in [(u.MaterialProperty.MP_BASE_COLOR,''),(u.MaterialProperty.MP_NORMAL,'Normal'),(u.MaterialProperty.MP_AMBIENT_OCCLUSION,'AO'),(u.MaterialProperty.MP_SUBSURFACE_COLOR,'Subsurface')]:g.output(n,prop,out)
 assert not mel.recompile_material(m);assert assets.save_loaded_asset(m,False)
 if ground:unify_forest_floor(m)

def unify_forest_floor(m):
 n=next(n for n in connected_nodes(m) if isinstance(n,u.MaterialExpressionCustom) and str(n.get_editor_property('desc'))=='FirewatchDistance')
 code=n.get_editor_property('code')
 shared=code.replace('Field,FieldSampler','Field,View.MaterialTextureBilinearClampedSampler').replace('ForestCover,ForestCoverSampler','ForestCover,View.MaterialTextureBilinearClampedSampler')
 if 'ForestCover' in code:
  if shared!=code:
   n.set_editor_property('code',shared);assert not mel.recompile_material(m);assert assets.save_loaded_asset(m,False)
  return
 code=shared
 g=Graph(m,'FirewatchForestFloor')
 n.set_editor_property('inputs',list(n.get_editor_property('inputs'))+[props(u.CustomInput(),input_name='ForestCover')])
 g.wire(g.node(u.MaterialExpressionTextureObject,texture=u.load_asset(C.BASE+'/ForestGround/T_FG_Coverage'),sampler_type=u.MaterialSamplerType.SAMPLERTYPE_LINEAR_COLOR),n,'ForestCover')
 code=code.replace('target=lerp(C,lum.xxx,.18)*GroundTint.rgb;','float cover=Texture2DSampleLevel(ForestCover,View.MaterialTextureBilinearClampedSampler,uv,3).r;\ntarget=lerp(lerp(C,lum.xxx,.18)*GroundTint.rgb,target*.75,saturate(cover));')
 n.set_editor_property('code',code);assert not mel.recompile_material(m);assert assets.save_loaded_asset(m,False)

def build_haze():
 m=new('M_StyleHaze',u.Material,u.MaterialFactoryNew());mel.delete_all_material_expressions(m)
 props(m,material_domain=u.MaterialDomain.MD_POST_PROCESS,blendable_location=u.BlendableLocation.BL_SCENE_COLOR_AFTER_TONEMAPPING,blendable_priority=10)
 g=Graph(m,'FirewatchHaze');names=['Scene','Depth','HazeColour','HazeIntensity','HazeStartCm','HazeFullCm']
 n=g.custom(names,'float a=smoothstep(HazeStartCm,HazeFullCm,Depth)*HazeIntensity; a*=1-smoothstep(900000,1000000,Depth); return lerp(Scene.rgb,HazeColour.rgb,a);')
 g.wire(g.node(u.MaterialExpressionSceneTexture,scene_texture_id=u.SceneTextureId.PPI_POST_PROCESS_INPUT0),n,'Scene','Color');g.wire(g.node(u.MaterialExpressionSceneDepth),n,'Depth')
 for key in names[2:]:g.wire(param(g,key),n,key)
 g.output(n,u.MaterialProperty.MP_EMISSIVE_COLOR);assert not mel.recompile_material(m);assert assets.save_loaded_asset(m,False)

def build():
 collection();rows=profiles()
 source=u.load_asset(C.BASE+'/MI_NZ_Foliage_Canopy');parent=clone(source.get_editor_property('parent'),'M_StyleFoliage');wrap(parent)
 instance=clone(source,'MI_StyleFoliage');mel.set_material_instance_parent(instance,parent);assert assets.save_loaded_asset(instance,False)
 for k,kind in enumerate(['Mature','Pole','Edge']):
  mesh=u.load_asset(C.DEST+'/SM_CD_Canopy_'+str(k));slot=C.sm.get_lod_material_slot(mesh,3,0);wrap(clone(mesh.get_material(slot),'M_StyleProxy_'+kind))
 for name in ['Terrain','Detail']:wrap(clone(u.load_asset(C.BASE+'/M_'+name),'M_Style'+name),ground=True)
 build_haze();return rows

def apply():
 rows=C.actors.get_all_level_actors();forest=next(a for a in rows if a.get_actor_label()=='LidarStudy_Forest');bindings=[]
 for c in forest.get_components_by_class(u.InstancedStaticMeshComponent):
  mesh=c.static_mesh
  if not mesh or not mesh.get_name().startswith('SM_CD_Canopy_'):continue
  k=int(mesh.get_name().rsplit('_',1)[1])
  if k>2:continue
  slot=C.sm.get_lod_material_slot(mesh,3,0)
  c.set_material(1,u.load_asset(DEST+'/MI_StyleFoliage'));c.set_material(slot,u.load_asset(DEST+'/M_StyleProxy_'+['Mature','Pole','Edge'][k]))
  bindings.append(dict(component=c.get_name(),geometry_slot=1,proxy_slot=slot))
 a=next((a for a in rows if isinstance(a,u.GTDistanceStyleController)),None) or C.actors.spawn_actor_from_class(u.GTDistanceStyleController,u.Vector())
 a.set_actor_label('LidarStudy_DistanceStyle')
 props(a,profile=a.profile or u.load_asset(DEST+'/DA_Lidar_Medium'),subtle=u.load_asset(DEST+'/DA_Lidar_Subtle'),medium=u.load_asset(DEST+'/DA_Lidar_Medium'),strong=u.load_asset(DEST+'/DA_Lidar_Strong'),parameters=u.load_asset(DEST+'/MPC_DistanceStyle'),sun=next(a for a in rows if isinstance(a,u.DirectionalLight)))
 a.apply_profile()
 ground_bindings=0
 mapping={u.load_asset(C.BASE+'/M_'+name):u.load_asset(DEST+'/M_Style'+name) for name in ['Terrain','Detail']}
 for actor in rows:
  if isinstance(actor,u.LandscapeProxy) and actor.get_editor_property('landscape_material') in mapping:
   actor.set_editor_property('landscape_material',mapping[actor.get_editor_property('landscape_material')]);ground_bindings+=1
  if isinstance(actor,u.GTMudRunnerVisual) and actor.material in mapping:actor.material=mapping[actor.material];ground_bindings+=1
  if isinstance(actor,u.GTProceduralGround) and actor.relief_material in mapping:actor.relief_material=mapping[actor.relief_material];ground_bindings+=1
  for c in actor.get_components_by_class(u.MeshComponent):
   for i in range(c.get_num_materials()):
    if c.get_material(i) in mapping:c.set_material(i,mapping[c.get_material(i)]);ground_bindings+=1
 apply_haze()
 import lidar_cohesive_style as cohesive
 if cohesive.enabled():cohesive.apply()
 return dict(controller=a.get_name(),bindings=bindings,ground_bindings=ground_bindings)

def apply_haze():
 rows=C.actors.get_all_level_actors()
 fog=next(a for a in rows if a.get_actor_label()==H.LABEL);s=fog.settings;s.set_editor_property('weighted_blendables',u.WeightedBlendables(array=[u.WeightedBlendable(weight=1.,object=u.load_asset(DEST+'/M_StyleHaze'))]));fog.settings=s
 import lidar_cohesive_style as cohesive
 if cohesive.enabled():cohesive.apply_haze()

def protected():
 s=H.state()
 for name,value in s['instances'].items():
  if name.startswith('LidarStudy_Forest/'):value.pop('materials')
 return s

def validate():
 assert protected()==json.loads((QA/'protected.json').read_text()),'Protected planting/ground/fog changed'
 rows=C.actors.get_all_level_actors();controller=next(a for a in rows if isinstance(a,u.GTDistanceStyleController))
 assert controller.profile==u.load_asset(DEST+'/DA_Lidar_Medium')
 checks=[];world=u.get_editor_subsystem(u.UnrealEditorSubsystem).get_editor_world();mpc=u.load_asset(DEST+'/MPC_DistanceStyle')
 defaults=[float(p.get_editor_property('default_value')) for p in mpc.get_editor_property('scalar_parameters')]
 for name in ['Subtle','Medium','Strong']:
  controller.set_style_preset(name)
  strength=u.MaterialLibrary.get_scalar_parameter_value(world,mpc,'Strength')
  haze=u.MaterialLibrary.get_scalar_parameter_value(world,mpc,'HazeIntensity')
  assert abs(strength-controller.profile.strength)<.0001 and abs(haze-controller.profile.haze_intensity)<.0001
  checks.append(dict(preset=name,strength=strength,haze=haze))
 # Exercise editing a map-owned profile without changing another profile or
 # coupling the two controls. Restore immediately; this is never saved.
 other_colour=controller.medium.forest_colour;other_haze=controller.medium.haze_intensity
 p=controller.subtle;old_colour=p.forest_colour;old_haze=p.haze_intensity
 controller.set_style_preset('Subtle')
 try:
  p.forest_colour=u.LinearColor(.12,.21,.32,1);p.haze_intensity=.19;controller.apply_profile()
  actual=u.MaterialLibrary.get_vector_parameter_value(world,mpc,'ForestColour')
  assert abs(actual.b-.32)<.0001
  assert abs(u.MaterialLibrary.get_scalar_parameter_value(world,mpc,'HazeIntensity')-.19)<.0001
  assert abs(u.MaterialLibrary.get_scalar_parameter_value(world,mpc,'Strength')-p.strength)<.0001
  assert controller.medium.forest_colour==other_colour and controller.medium.haze_intensity==other_haze
 finally:p.forest_colour=old_colour;p.haze_intensity=old_haze
 controller.set_style_preset('Medium')
 assert defaults==[float(p.get_editor_property('default_value')) for p in mpc.get_editor_property('scalar_parameters')],'Profile changed shared MPC defaults'
 for c in next(a for a in rows if a.get_actor_label()=='LidarStudy_Forest').get_components_by_class(u.InstancedStaticMeshComponent):
  if c.static_mesh and c.static_mesh.get_name() in ['SM_CD_Canopy_0','SM_CD_Canopy_1','SM_CD_Canopy_2']:
   assert c.get_material(1)==u.load_asset(DEST+'/MI_StyleFoliage')
   assert c.get_material(C.sm.get_lod_material_slot(c.static_mesh,3,0)).get_path_name().startswith(DEST)
 fog=next(a for a in rows if a.get_actor_label()==H.LABEL);b=list(fog.settings.weighted_blendables.array);assert len(b)==1 and b[0].object==u.load_asset(DEST+'/M_StyleHaze')
 assert next(a for a in rows if isinstance(a,u.Landscape)).get_editor_property('landscape_material')==u.load_asset(DEST+'/M_StyleTerrain')
 return dict(protected_packages=C.validate_protected(),planting_ground_existing_fog_unchanged=True,presets=checks,shared_collection_defaults_unchanged=True,independent_colour_haze_and_profile_edit_passed=True)

def main():
 stage=os.environ.get('GT_STYLE_STAGE','install');report=dict(ok=False,stage=stage);control=dict(busy=False,deadline=0)
 def run():
  assert les.load_level(C.BASE+'/L_LidarStudy');yield 2
  if stage=='tune':
   os.environ['GT_STYLE_RESET_PROFILES']='1';report['profiles']=profiles()
   for name in ['Terrain','Detail']:wrap(u.load_asset(DEST+'/M_Style'+name),ground=True)
   report.update(validate())
  elif stage=='install':
   if not (QA/'protected.json').exists():
    (QA/'protected.json').write_text(json.dumps(protected(),indent=2))
    with zipfile.ZipFile(QA/'before-map.zip','w',zipfile.ZIP_DEFLATED,compresslevel=1) as z:z.write(ROOT/'Content/GrandTour/ArtTests/LidarStudy/L_LidarStudy.umap','L_LidarStudy.umap')
   report['profiles']=build();report.update(apply());report.update(validate());assert les.save_current_level();report['saved']=True
   CONFIG.parent.mkdir(parents=True,exist_ok=True);CONFIG.write_text(json.dumps(dict(enabled=True,profile='Medium',assets=DEST,controller=report['controller']),indent=2))
  else:report.update(validate());report['saved_reload']=True
  report['ok']=True;yield 1
 steps=run()
 def tick(dt):
  if control['busy'] or time.monotonic()<control['deadline']:return
  control['busy']=True
  try:control['deadline']=time.monotonic()+float(next(steps))
  except StopIteration:
   (QA/(stage+'.json')).write_text(json.dumps(report,indent=2));u.unregister_slate_post_tick_callback(control['handle']);u.SystemLibrary.quit_editor()
  except Exception:
   report.update(error=traceback.format_exc());(QA/(stage+'.json')).write_text(json.dumps(report,indent=2));u.log_error(report['error']);u.unregister_slate_post_tick_callback(control['handle']);u.SystemLibrary.quit_editor()
  finally:control['busy']=False
 u.EditorPythonScripting.set_keep_python_script_alive(True);control['handle']=u.register_slate_post_tick_callback(tick)

if __name__=='__main__':main()
