"""LT4: native MudRunner surface composition on the saved LiDAR logging road.

Uses recovered Mud colour arithmetic already in both ground materials. Adds
native road overlays and forest pixels before that arithmetic, then exposes
the result past the map's later peat/clay colour overrides. Physical state,
relief, live normals, displacement, water and tyre ribbons remain connected.
"""
import gc,hashlib,json,math,sys,time,traceback,shutil,re,os
from pathlib import Path
import unreal as u
ROOT=Path(u.Paths.project_dir()).resolve();sys.path.insert(0,str(ROOT/'Art/Unreal'))
from benmore_river_life_materials import Graph,props
OUT=ROOT/'Art/Export/LidarStudy/Place';DATA=OUT/'TrackDetail'
BASE='/Game/GrandTour/ArtTests/LidarStudy';DEST=BASE+'/TrackDetail';KIT='/Game/GrandTour/Environment/NativePlants/v01'
VERSION='LT4-native-1';TAG='LT4Final';PREFIX='LidarStudy_TrackLitter_'
mel=u.MaterialEditingLibrary;assets=u.EditorAssetLibrary

def manifest():return json.loads((DATA/'manifest.json').read_text())

def texture(name,lookup=False,mask=False):
 src=DATA/(name+'.png');path=DEST+'/'+name
 # Content hash metadata makes reruns cheap, with settings checked on each run.
 digest=hashlib.sha256(src.read_bytes()).hexdigest();t=u.load_asset(path)
 if not t or assets.get_metadata_tag(t,'LT4SourceSHA')!=digest:
  job=props(u.AssetImportTask(),filename=str(src),destination_path=DEST,destination_name=name,automated=True,replace_existing=True,save=True)
  u.AssetToolsHelpers.get_asset_tools().import_asset_tasks([job]);t=u.load_asset(path);assert t,path
  assets.set_metadata_tag(t,'LT4SourceSHA',digest)
 props(t,srgb=False,compression_settings=u.TextureCompressionSettings.TC_VECTOR_DISPLACEMENTMAP if lookup else u.TextureCompressionSettings.TC_BC7,
       never_stream=lookup,mip_gen_settings=u.TextureMipGenSettings.TMGS_NO_MIPMAPS if lookup else u.TextureMipGenSettings.TMGS_FROM_TEXTURE_GROUP,
       address_x=u.TextureAddress.TA_CLAMP if lookup or mask else u.TextureAddress.TA_WRAP,
       address_y=u.TextureAddress.TA_CLAMP if lookup or mask else u.TextureAddress.TA_WRAP)
 assets.save_loaded_asset(t);return t

def injection(spec):
 ox,oy=spec['origin_cm'];span=spec['span_cm']
 return '''
// LT4_BEGIN: Native TerrainCommon ApplyOverlay pigment/alpha and road UV.
// World lookup, section masks and UE colour-space bridge are host bindings.
float2 lt4xy=(materialXY-float2(%f,%f))/%f;
float4 lt4m=Texture2DSampleLevel(LT4Mask,LT4MaskSampler,saturate(lt4xy),0);
lt4m.r*=all(lt4xy>=0)&&all(lt4xy<=1);
float4 lt4uv=Texture2DSampleLevel(LT4Route,LT4RouteSampler,saturate(lt4xy),0);
float lt4s=dot(lt4uv.rg,float2(65280,255))/65535*1024;
float lt4across=dot(lt4uv.ba,float2(65280,255))/65535*64-32;
float4 lt4d=Texture2DSample(Dirt,DirtSampler,materialXY*.0012);
float4 lt4g=Texture2DSample(Grass,GrassSampler,materialXY*.0012);
float2 lt4road=float2(lt4s/14,.5+lt4across/7);
float2 lt4path=float2(lt4s/12,.5+lt4across/6);
// Explicit gradients keep source mip selection valid inside the corridor branch.
float2 lt4dx=ddx(lt4road),lt4dy=ddy(lt4road);
float2 lt4px=ddx(lt4path),lt4py=ddy(lt4path);
[branch] if(lt4m.r>.001) {
 float4 forest=Texture2DSample(LT4Forest,LT4ForestSampler,materialXY*.0012);
 lt4g=lerp(lt4g,forest,lt4m.r);
 float4 overlay;
 [branch] if(lt4m.a<.5) {
  float4 a=Texture2DSampleGrad(LT4Smooth,LT4SmoothSampler,float2(lt4road.x,saturate(lt4road.y)),lt4dx,lt4dy);
  float4 b=Texture2DSampleGrad(LT4Road,LT4RoadSampler,float2(lt4road.x,saturate(lt4road.y)),lt4dx,lt4dy);
  overlay=lerp(a,b,lt4m.a*2);
 } else {
  float4 a=Texture2DSampleGrad(LT4Road,LT4RoadSampler,float2(lt4road.x,saturate(lt4road.y)),lt4dx,lt4dy);
  float4 b=Texture2DSampleGrad(LT4Path,LT4PathSampler,float2(lt4path.x,saturate(lt4path.y)),lt4px,lt4py);
  overlay=lerp(a,b,lt4m.a*2-1);
 }
 // TerrainCommon.fxh: rgb *= dirtTint; rgb *= saturate(alpha/.75);
 // overlay.a *= alpha; diffuse=lerp(diffuse,overlay,overlay.a).
 // Its overlay sampler is sRGB. Decode here, then encode for Mud's SM3 inputs.
 float alpha=lt4m.r;
 float3 linearOverlay=pow(max(overlay.rgb,0),2.2)*dirtTint*saturate(alpha/.75);
 lt4d.rgb=pow(max(lerp(pow(max(lt4d.rgb,0),2.2),linearOverlay,overlay.a*alpha),0),1/2.2);
 lt4d.a=lerp(lt4d.a,overlay.a*alpha,overlay.a*alpha);
}
// Surface composition remains independent from soil depth/firmness. Native
// normal-driven flat/churn/decal equations and live displacement stay intact.
// Live disturbance clears litter and restores full native churn coverage.
float lt4worked=saturate(field.a);
lt4m.g*=1-lt4worked;
lt4m.b=max(lt4m.b,lt4worked);
float lt4presence=presence*(.30+.70*lt4m.b)*(1-.65*lt4m.g);
// LT4_END
'''%(ox,oy,span)

def patch_material(m,textures,spec):
 nodes=list(mel.get_material_expressions(m))
 main=next(n for n in nodes if isinstance(n,u.MaterialExpressionCustom) and 'float3 rich=' in n.get_editor_property('code'))
 code=main.get_editor_property('code')
 # The upstream native program is kept as the restoration source inside the
 # asset metadata, so an LT4 rerun cannot accumulate wrappers or replace physics.
 original=code
 if '// LT4_BEGIN' in original:
  original=re.sub(r'\n// LT4_BEGIN.*?// LT4_END\n','',original,flags=re.S)
  original=original.replace('v3=float4(grassTint,lerp(max(mud,sandCover),1-lt4m.g,lt4m.r))','v3=float4(grassTint,max(mud,sandCover))')
  original=original.replace('v5=float4(lerp(max(presence,sandCover),lt4presence,lt4m.r),shade,flat,decalWeight)','v5=float4(max(presence,sandCover),shade,flat,decalWeight)')
  original=original.replace('#define SAMPLE4(p) lt4d','#define SAMPLE4(p) Texture2DSample(Dirt,DirtSampler,p)',1).replace('#define SAMPLE5(p) lt4g','#define SAMPLE5(p) Texture2DSample(Grass,GrassSampler,p)',1)
  original=original.replace('LT4Colour=pow(max(oC0.rgb,0),2.2);\nLT4Coverage=lt4m.r;\n','',1)
 assets.set_metadata_tag(m,'LT4OriginalProgram',original)
 assert original.count('#define SAMPLE4(p) Texture2DSample(Dirt,DirtSampler,p)')==1
 marker='float4 v3=float4(grassTint,max(mud,sandCover))'
 assert marker in original,'Unexpected native state; refuse guessed replacement'
 code=original.replace(marker,injection(spec)+marker,1)
 code=code.replace('v3=float4(grassTint,max(mud,sandCover))','v3=float4(grassTint,lerp(max(mud,sandCover),1-lt4m.g,lt4m.r))',1)
 code=code.replace('v5=float4(max(presence,sandCover),shade,flat,decalWeight)','v5=float4(lerp(max(presence,sandCover),lt4presence,lt4m.r),shade,flat,decalWeight)',1)
 code=code.replace('#define SAMPLE4(p) Texture2DSample(Dirt,DirtSampler,p)','#define SAMPLE4(p) lt4d',1)
 code=code.replace('#define SAMPLE5(p) Texture2DSample(Grass,GrassSampler,p)','#define SAMPLE5(p) lt4g',1)
 code=code.replace('float3 rich=oC0.rgb', 'LT4Colour=pow(max(oC0.rgb,0),2.2);\nLT4Coverage=lt4m.r;\nfloat3 rich=oC0.rgb',1)
 oldinputs=list(main.get_editor_property('inputs'));names=[str(v.get_editor_property('input_name')) for v in oldinputs]
 for key in textures:
  if key not in names:oldinputs.append(props(u.CustomInput(),input_name=key))
 main.set_editor_property('inputs',oldinputs)
 # Unreal connections store output indices. Removing then appending our pins
 # shifts later layers (RR1State float4 could become LT4Coverage float1).
 # Preserve every existing index and append only genuinely missing outputs.
 outputs=list(main.get_editor_property('additional_outputs'))
 for name,kind in [('LT4Colour',u.CustomMaterialOutputType.CMOT_FLOAT3),('LT4Coverage',u.CustomMaterialOutputType.CMOT_FLOAT1)]:
  output=next((o for o in outputs if str(o.get_editor_property('output_name'))==name),None)
  if output is None:outputs.append(props(u.CustomOutput(),output_name=name,output_type=kind))
  else:output.set_editor_property('output_type',kind)
 main.set_editor_property('additional_outputs',outputs);main.set_editor_property('code',code)
 g=Graph(m,'LT4Inputs')
 for key,t in textures.items():
  matches=[n for n in nodes if str(n.get_editor_property('desc'))=='LT4Texture:'+key]
  node=matches[0] if matches else g.node(u.MaterialExpressionTextureObject,texture=t,sampler_type=u.MaterialSamplerType.SAMPLERTYPE_LINEAR_COLOR)
  node.set_editor_property('desc','LT4Texture:'+key);node.set_editor_property('texture',t);g.wire(node,main,key)
 final=next((n for n in nodes if isinstance(n,u.MaterialExpressionCustom) and str(n.get_editor_property('desc'))==TAG),None)
 if not final:
  old=mel.get_material_property_input_node(m,u.MaterialProperty.MP_BASE_COLOR);oldout=mel.get_material_property_input_node_output_name(m,u.MaterialProperty.MP_BASE_COLOR)
  g=Graph(m,TAG);final=g.custom(['Base','NativeRoad','Coverage','Strength'],'return lerp(Base,NativeRoad,Coverage*Strength);')
  strength=g.node(u.MaterialExpressionScalarParameter,parameter_name='LT4Strength',default_value=1.)
  g.wire(strength,final,'Strength');g.wire(old,final,'Base',oldout)
 g.wire(main,final,'NativeRoad','LT4Colour');g.wire(main,final,'Coverage','LT4Coverage');g.output(final,u.MaterialProperty.MP_BASE_COLOR)
 river=next((n for n in nodes if str(n.get_editor_property('desc'))=='RR1Final'),None)
 if river and any(str(o.get_editor_property('output_name'))=='RR1State' for o in outputs):g.wire(main,river,'State','RR1State')
 if (OUT/'road-style.json').exists():
  import lidar_road_style
  lidar_road_style.patch_material(m)
 assert not mel.recompile_material(m),m.get_path_name()
 assets.set_metadata_tag(m,'LT4Version',VERSION);assets.save_loaded_asset(m)
 return dict(material=m.get_path_name(),native_program=main.get_name(),original_sha256=hashlib.sha256(original.encode()).hexdigest(),shader_sha256=hashlib.sha256(code.encode()).hexdigest(),version=VERSION)

def install():
 spec=manifest();assert spec['version']==VERSION
 assert hashlib.sha256((OUT/'roads.json').read_bytes()).hexdigest()==spec['route_sha256'],'Rebuild track detail masks for the current route first'
 actors=u.get_editor_subsystem(u.EditorActorSubsystem);refs=actors.get_all_level_actors()
 author=next(a for a in refs if isinstance(a,u.GTProceduralGround));before=str(author.output_digest);wet=author.road_pool_wet_samples
 textures={key:texture(name,lookup=key=='LT4Route',mask=key=='LT4Mask') for key,name in [('LT4Route','T_RouteUV'),('LT4Mask','T_Composition'),('LT4Forest','tiles_forest__d_a'),('LT4Road','overlays_dirt_road__d_a'),('LT4Path','overlays_dirt_path__d_a'),('LT4Smooth','overlays_dirt_road_smooth__d_a')]}
 materials=[patch_material(u.load_asset(BASE+'/M_'+n),textures,spec) for n in ['Terrain','Detail']]
 if os.environ.get('GT_TRACK_DETAIL_MATERIALS_ONLY')=='1':
  # Explicit appearance-only repair: require the saved dressing to be current.
  state=json.loads((DATA/'installed.json').read_text())
  assert state['route_sha256']==spec['route_sha256'] and state['ground_digest']==before
  assert state['litter_instances']==len(spec['instances'])
  validate(refs)
  state.update(materials=materials,materials_only=True)
  (DATA/'installed.json').write_text(json.dumps(state,indent=2),encoding='utf-8')
  return state
 tiles=list(author.relief_tiles.values())
 def ground(x,y):
  for t in tiles:
   o=t.get_actor_location()
   if o.x<=x<o.x+t.span_cm and o.y<=y<o.y+t.span_cm:return t.height_at(u.Vector2D(x,y))
  return author.base_height_at(u.Vector2D(x,y))
 for a in refs:
  if a.get_actor_label().startswith(PREFIX):actors.destroy_actor(a)
 groups={};accepted=0;skipped=0
 sheet=next(a for a in refs if isinstance(a,u.GTWaterSheet) and not a.get_editor_property('mud_initial_domain'))
 for item in spec['instances']:
  x,y=item['x_cm'],item['y_cm'];z=ground(x,y)
  if sheet.covers(u.Vector2D(x,y)) and sheet.surface_cm_at(u.Vector2D(x,y))>z+1:skipped+=1;continue
  name=item['mesh'];mesh=u.load_asset(KIT+'/'+name);assert mesh,name
  scale=item['scale'];angle=math.radians(item['yaw']);dx,dy=math.cos(angle),math.sin(angle)
  slope=(ground(x+dx*25,y+dy*25)-ground(x-dx*25,y-dy*25))/50
  side=(ground(x-dy*25,y+dx*25)-ground(x+dy*25,y-dx*25))/50
  z-=mesh.get_bounding_box().min.z*scale*.65+2
  tf=u.Transform(location=u.Vector(x,y,z),rotation=u.Rotator(pitch=math.degrees(math.atan(slope)),yaw=item['yaw'],roll=-math.degrees(math.atan(side))),scale=u.Vector(scale,scale,scale*.65))
  groups.setdefault((math.floor(x/6400),math.floor(y/6400),name),[]).append(tf);accepted+=1
 counts={}
 for (cx,cy,name),transforms in groups.items():
  a=actors.spawn_actor_from_class(u.Actor,u.Vector(cx*6400,cy*6400,0));a.set_actor_label(PREFIX+str(cx)+'_'+str(cy)+'_'+name)
  a.tags=['LidarTrackDetail',VERSION]
  c=u.GTVegetationSubsystem.add_tagged_instances(a,u.load_asset(KIT+'/'+name),transforms,'LidarTrackLitter','NoCollision',False)
  c.set_collision_enabled(u.CollisionEnabled.NO_COLLISION);c.set_cull_distances(2800,3800)
  props(c,cast_shadow=False,visible_in_ray_tracing=False,affect_distance_field_lighting=False)
  counts[name]=counts.get(name,0)+len(transforms)
 assert str(author.output_digest)==before and author.road_pool_wet_samples==wet
 result=dict(version=VERSION,materials=materials,litter_instances=accepted,skipped_underwater=skipped,litter_components=len(groups),by_mesh=counts,cull_cm=[2800,3800],additional_physics_bodies=0,
             ground_digest=before,pool_cells=wet,route_sha256=spec['route_sha256'],sources=spec['sources'],host_adapters=spec['host_adapters'])
 (DATA/'installed.json').write_text(json.dumps(result,indent=2),encoding='utf-8')
 return result

def validate(refs):
 spec=manifest();assert hashlib.sha256((OUT/'roads.json').read_bytes()).hexdigest()==spec['route_sha256']
 rows=[]
 for n in ['Terrain','Detail']:
  m=u.load_asset(BASE+'/M_'+n);assert assets.get_metadata_tag(m,'LT4Version')==VERSION
  nodes=list(mel.get_material_expressions(m));final=[e for e in nodes if isinstance(e,u.MaterialExpressionCustom) and str(e.get_editor_property('desc'))==TAG];assert len(final)==1,('Final wrapper count',n,len(final))
  assert mel.get_material_property_input_node(m,u.MaterialProperty.MP_BASE_COLOR)==final[0]
  main=next(e for e in nodes if isinstance(e,u.MaterialExpressionCustom) and '// LT4_BEGIN' in e.get_editor_property('code'))
  assert main.get_editor_property('code').count('// LT4_BEGIN')==1
  rows.append(m.get_path_name())
 components=[c for a in refs if a.get_actor_label().startswith(PREFIX) for c in a.get_components_by_class(u.InstancedStaticMeshComponent)]
 count=sum(c.get_instance_count() for c in components);assert count>50,count
 assert all(c.get_collision_enabled()==u.CollisionEnabled.NO_COLLISION for c in components)
 state=DATA/'installed.json'
 before=json.loads((state if state.exists() else OUT/'trackdetail-before.json').read_text());author=next(a for a in refs if isinstance(a,u.GTProceduralGround))
 assert str(author.output_digest)==before['ground_digest'] and author.road_pool_wet_samples==before['pool_cells']
 return dict(materials=rows,litter_instances=count,ground_and_pools_unchanged=True)

def run():
 les=u.get_editor_subsystem(u.LevelEditorSubsystem)
 backup=ROOT/'Saved/LidarStudyBackups'/('LT4-'+str(time.time_ns()));backup.mkdir(parents=True)
 folder=ROOT/'Content/GrandTour/ArtTests/LidarStudy'
 for name in ['L_LidarStudy.umap','M_Terrain.uasset','M_Detail.uasset']:shutil.copy2(folder/name,backup/name)
 report['backup']=str(backup)
 assert les.load_level(BASE+'/L_LidarStudy');report.update(install());yield 1
 if not report.get('materials_only'):assert les.save_current_level()
 report['saved']=True
 les.load_level('/Engine/Maps/Entry');yield 3
 assert les.load_level(BASE+'/L_LidarStudy');report['reload']=validate(u.get_editor_subsystem(u.EditorActorSubsystem).get_all_level_actors())
 report['ok']=True;save();les.load_level('/Engine/Maps/Entry');yield 3

def save():(OUT/'trackdetail.json').write_text(json.dumps(report,indent=2),encoding='utf-8')

if __name__=='__main__':
 report=dict(ok=False);steps=run();deadline=0;busy=False;began=time.monotonic()
 def tick(dt):
  global deadline,busy,steps
  if busy:return
  busy=True
  try:
   assert time.monotonic()-began<1200,'Track detail install timeout'
   if time.monotonic()>=deadline:deadline=time.monotonic()+next(steps)
  except StopIteration:u.unregister_slate_post_tick_callback(handle);steps=None;gc.collect();u.SystemLibrary.quit_editor()
  except Exception:
   report['error']=traceback.format_exc();save();u.log_error(report['error']);u.unregister_slate_post_tick_callback(handle);u.SystemLibrary.quit_editor()
  finally:busy=False
 u.EditorPythonScripting.set_keep_python_script_alive(True);handle=u.register_slate_post_tick_callback(tick)
