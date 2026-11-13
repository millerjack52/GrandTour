"""LP6: production-map grounding, live river shores, and distance foliage.

Runs after terrain generation; safe to reapply after Install/Polish. No new solver.
"""
import json,math,time,traceback,gc,shutil,re,os
from pathlib import Path
import unreal as u
from benmore_river_life_materials import Graph,props
from lidar_grounding import GroundSampler
ROOT=Path(u.Paths.project_dir()).resolve();BASE='/Game/GrandTour/ArtTests/LidarStudy'
OUT=ROOT/'Art/Export/LidarStudy/Place';QA=ROOT/'Saved/LidarAuthoringQA/LP6'
mel=u.MaterialEditingLibrary;assets=u.EditorAssetLibrary
VERSION='LP6-1'

def water_material(m):
 nodes=list(mel.get_material_expressions(m));g=Graph(m,VERSION)
 main=next(n for n in nodes if isinstance(n,u.MaterialExpressionCustom) and 'Mask=Local>' in n.get_editor_property('code'))
 code=main.get_editor_property('code')
 code=re.sub(r'Mask=Local>[^;]+;', 'Mask=Local>.5 ? inside*step(.2,live.g) : OldMask*(1-inside);',code)
 main.set_editor_property('code',code)
 if m.get_name()=='M_RiverWater':
  for n in nodes:
   if isinstance(n,u.MaterialExpressionCustom) and str(n.get_editor_property('desc'))=='ChannelPilot':n.set_editor_property('code','return Old; // LP6 static geometry is clipped against the final built bed.')
 # The old ChannelPilot mask must not reapply the baked shoreline after live clipping.
 old=mel.get_material_property_input_node(m,u.MaterialProperty.MP_OPACITY_MASK)
 if str(old.get_editor_property('desc'))==VERSION:
  assert not mel.recompile_material(m);assert assets.save_loaded_asset(m);return
 inputs={}
 for name in ['FieldMin','FieldSize','FieldTexels','LocalSurface','FieldActive','FieldLevelCm','FieldTex']:
  inputs[name]=next(n for n in nodes if isinstance(n,(u.MaterialExpressionVectorParameter,u.MaterialExpressionScalarParameter,u.MaterialExpressionTextureObjectParameter)) and str(n.get_editor_property('parameter_name'))==name)
 inputs['P']=g.node(u.MaterialExpressionWorldPosition,world_position_shader_offset=u.WorldPositionIncludedOffsets.WPT_EXCLUDE_ALL_SHADER_OFFSETS)
 for name in ['RiverGroundTex','GTLS_Field']:
  inputs[name]=g.node(u.MaterialExpressionTextureObjectParameter,parameter_name=name,texture=u.load_asset('/Engine/EngineResources/WhiteSquareTexture'),sampler_type=u.MaterialSamplerType.SAMPLERTYPE_LINEAR_COLOR)
 inputs['GTLS_Window']=g.node(u.MaterialExpressionVectorParameter,parameter_name='GTLS_Window',default_value=u.LinearColor(0,0,1,0))
 for name in ['GTLS_Ready','RiverGroundReady']:inputs[name]=g.node(u.MaterialExpressionScalarParameter,parameter_name=name,default_value=0)
 inputs['Old']=old
 out=g.custom(list(inputs),'''
float2 uv=(P.xy-FieldMin.xy)/FieldSize.xy;
float2 cell=FieldSize.xy/FieldTexels.xy;
float2 edge=min(P.xy-FieldMin.xy-cell*.5,FieldMin.xy+FieldSize.xy-cell*.5-P.xy);
float inside=FieldActive*step(0,min(edge.x,edge.y));
if(LocalSurface<.5)return Old*(1-inside);
if(inside<.5 || RiverGroundReady<.5)return Old;
float2 bed=Texture2DSampleLevel(RiverGroundTex,RiverGroundTexSampler,uv,0).rg;
float4 water=Texture2DSampleLevel(FieldTex,FieldTexSampler,uv,0);
float2 soilUV=(P.xy-GTLS_Window.xy)/max(1,GTLS_Window.z);
float delta=0;
if(GTLS_Ready>.5 && all(soilUV>=0) && all(soilUV<=1))
 delta=Texture2DSampleLevel(GTLS_Field,GTLS_FieldSampler,soilUV,0).r;
return step(.5,bed.g)*step(.2,water.r+FieldLevelCm-bed.r-delta);
''',u.CustomMaterialOutputType.CMOT_FLOAT1)
 for name,n in inputs.items():g.wire(n,out,name)
 g.output(out,u.MaterialProperty.MP_OPACITY_MASK)
 assert not mel.recompile_material(m);assert assets.save_loaded_asset(m)

def foliage_materials():
 result=[]
 # Map-owned foliage shader: retain authored colours, soften planar frond lighting
 # with a small rounded-normal contribution and restrained transmitted light.
 path=BASE+'/M_LP6_Foliage'
 leaf=u.load_asset(path) or assets.duplicate_asset('/Game/GrandTour/Environment/NativePlants/v01/M_NZ_Foliage',path)
 if assets.get_metadata_tag(leaf,'LP6Foliage')!='1':
  g=Graph(leaf,'LP6Leaf');base=mel.get_material_property_input_node(leaf,u.MaterialProperty.MP_BASE_COLOR)
  out=mel.get_material_property_input_node_output_name(leaf,u.MaterialProperty.MP_BASE_COLOR)
  p=g.node(u.MaterialExpressionWorldPosition);centre=g.node(u.MaterialExpressionObjectPositionWS);vn=g.node(u.MaterialExpressionVertexNormalWS)
  n=g.custom(['P','Centre','N'],'float3 radial=normalize(float3((P.xy-Centre.xy)*.012,.65));return normalize(lerp(N,radial,.18));')
  for a,pin in [(p,'P'),(centre,'Centre'),(vn,'N')]:g.wire(a,n,pin)
  g.output(n,u.MaterialProperty.MP_NORMAL)
  colour=g.custom(['Base','P'],'float v=sin(P.x*.13+sin(P.y*.09))*sin(P.z*.17+P.y*.08);return Base*(.96+.04*v);')
  g.wire(base,colour,'Base',out);g.wire(p,colour,'P');g.output(colour,u.MaterialProperty.MP_BASE_COLOR)
  sub=g.node(u.MaterialExpressionMultiply);g.wire(colour,sub,'A');g.wire(g.scalar(.20),sub,'B');g.output(sub,u.MaterialProperty.MP_SUBSURFACE_COLOR)
  props(leaf,two_sided=True,tangent_space_normal=False,shading_model=u.MaterialShadingModel.MSM_TWO_SIDED_FOLIAGE,dithered_lod_transition=True)
  g.output(g.scalar(.85),u.MaterialProperty.MP_ROUGHNESS);g.output(g.scalar(.05),u.MaterialProperty.MP_SPECULAR)
  assert not mel.recompile_material(leaf);assets.set_metadata_tag(leaf,'LP6Foliage','1');assets.save_loaded_asset(leaf)
 for name in ['MI_NZ_Foliage_Bush','MI_NZ_Foliage_Canopy']:
  mi=u.load_asset(BASE+'/'+name);mel.set_material_instance_parent(mi,leaf);mel.update_material_instance(mi);assets.save_loaded_asset(mi)
 result.append(path)
 for k in range(4):
  import lidar_canopy_assets
  if lidar_canopy_assets.shade_far_card(k):
   result.append(BASE+'/CanopyKit/M_FirFar_'+str(k));continue
  m=u.load_asset(BASE+'/CanopyKit/M_FirFar_'+str(k));assert m
  g=Graph(m,'LP6Canopy')
  normal=next((n for n in mel.get_material_expressions(m) if str(n.get_editor_property('desc'))=='LP6CanopyNormal'),None)
  if not normal:
   normal=g.custom(['P','Centre'],'return normalize(float3((P.xy-Centre.xy)*.003, .55));')
   normal.set_editor_property('desc','LP6CanopyNormal')
   g.wire(g.node(u.MaterialExpressionWorldPosition),normal,'P')
   g.wire(g.node(u.MaterialExpressionObjectPositionWS),normal,'Centre')
   g.output(normal,u.MaterialProperty.MP_NORMAL)
   # Preserve baked species texture/tint; add crown self-shading absent on crossed cards.
   old=mel.get_material_property_input_node(m,u.MaterialProperty.MP_BASE_COLOR)
   oo=mel.get_material_property_input_node_output_name(m,u.MaterialProperty.MP_BASE_COLOR)
   shade=g.custom(['Base','UV'],'float crown=smoothstep(.25,.9,UV.y);return Base*lerp(.58,.82,crown);')
   g.wire(old,shade,'Base',oo);g.wire(g.node(u.MaterialExpressionTextureCoordinate),shade,'UV');g.output(shade,u.MaterialProperty.MP_BASE_COLOR)
  props(m,dithered_lod_transition=True)
  assert not mel.recompile_material(m);assets.save_loaded_asset(m);result.append(m.get_path_name())
 if (OUT/'reference-style.json').exists():
  import lidar_reference_style
  lidar_reference_style.foliage_palette()
 return result

def install():
 refs=u.get_editor_subsystem(u.EditorActorSubsystem).get_all_level_actors()
 author=next(a for a in refs if isinstance(a,u.GTProceduralGround));ground=GroundSampler(author)
 digest=str(author.output_digest);rows=[]
 import lidar_water_coverage
 coverage=lidar_water_coverage.install(author);yield .1
 for a in refs:
  if a.get_actor_label() not in ['LidarStudy_Forest','LidarStudy_Understory']:continue
  for c in a.get_components_by_class(u.InstancedStaticMeshComponent):
   mesh=c.static_mesh
   if not mesh:continue
   name=mesh.get_name();n=c.get_instance_count();changed=0;max_delta=0;ts=[]
   trunk=name=='Cylinder'
   plant=trunk or name.startswith(('SM_Canopy','SM_CD_Canopy')) or any(s in name for s in ['Fern','Kiokio','Coprosma','Harakeke','Kanuka','TiKouka','Matagouri','Rush','Grass','Tussock'])
   for i in range(n):
    tf=c.get_instance_transform(i,True);new=ground.seat(mesh,tf,plant)
    if trunk:new.translation=u.Vector(tf.translation.x,tf.translation.y,ground.height(tf.translation.x,tf.translation.y)+240)
    delta=abs(new.translation.z-tf.translation.z);max_delta=max(max_delta,delta);changed+=delta>.1;ts.append(new)
   if ts:
    # One batched update; never dirty the render tree for each individual plant.
    assert c.batch_update_instances_transforms(0,ts,True,True,True)
   if not trunk:c.set_lod_distance_scale(2.0 if name.startswith(('SM_Canopy','SM_CD_Canopy')) else 1.6)
   rows.append(dict(mesh=name,count=n,changed=changed,max_correction_cm=round(max_delta,2)))
   u.log('LP6 grounded '+name+' '+str(n));yield .01
 surface=next(a for a in refs if isinstance(a,u.GTLandscapeSurface))
 sheet=next(a for a in refs if isinstance(a,u.GTWaterSheet) and a.get_editor_property('water_domain') and not a.get_editor_property('mud_initial_domain'))
 props(sheet,domain_ground_surface=surface,domain_shore_margin_cm=250)
 for name in ['River','AccessPond','MappedPond']:water_material(u.load_asset(BASE+'/M_'+name+'Water'));yield .1
 mats=foliage_materials();yield .1
 import lidar_river_detail
 detail=lidar_river_detail.install();yield .1
 assert str(author.output_digest)==digest
 result=dict(ok=True,version=VERSION,coverage=coverage,grounding=rows,far_materials=mats,river_detail=detail,ground_digest=digest,owner_accepted=False)
 (OUT/'levelpolish.json').write_text(json.dumps(result,indent=2))
 return result

if __name__=='__main__':
 report={'ok':False};busy=False
 def run():
  global report
  QA.mkdir(parents=True,exist_ok=True)
  if os.environ.get('GT_LP6_PHASE')=='foliage':
   report=dict(ok=True,materials=foliage_materials());(QA/'foliage.json').write_text(json.dumps(report,indent=2));yield 5;return
  backup=ROOT/'Saved/LidarAuthoringBackups'/('LP6-'+str(time.time_ns()))
  shutil.copytree(ROOT/'Content/GrandTour/ArtTests/LidarStudy',backup)
  (QA/'backup.json').write_text(json.dumps({'path':str(backup)}))
  les=u.get_editor_subsystem(u.LevelEditorSubsystem);assert les.load_level(BASE+'/L_LidarStudy');yield 1
  report=yield from install();report['ok']=False
  assert les.save_current_level();report.update(ok=True,saved=True)
  (QA/'install.json').write_text(json.dumps(report,indent=2));yield 1
  gc.collect();les.load_level('/Engine/Maps/Entry');yield 4
 steps=run();deadline=0
 def tick(dt):
  global busy,deadline,steps
  if busy:return
  busy=True
  try:
   if time.monotonic()>=deadline:deadline=time.monotonic()+next(steps)
  except StopIteration:u.unregister_slate_post_tick_callback(handle);steps=None;gc.collect();u.SystemLibrary.quit_editor()
  except Exception:
   report.update(ok=False,error=traceback.format_exc());(QA/('foliage.json' if os.environ.get('GT_LP6_PHASE')=='foliage' else 'install.json')).write_text(json.dumps(report,indent=2));u.log_error(report['error']);u.unregister_slate_post_tick_callback(handle);u.SystemLibrary.quit_editor()
  finally:busy=False
 u.EditorPythonScripting.set_keep_python_script_alive(True);handle=u.register_slate_post_tick_callback(tick)
