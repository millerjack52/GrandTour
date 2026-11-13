"""RR1 photo-reach dressing and DG1 gravel on the existing live LiDAR ground.

No second ground/water simulation. Texture arrays are read-only references;
the existing native field supplies displacement, slide and worked coverage.
"""
import json,math,hashlib,random
from pathlib import Path
import unreal as u
from benmore_river_life_materials import Graph,props
ROOT=Path(u.Paths.project_dir()).resolve();OUT=ROOT/'Art/Export/LidarStudy/Place'
BASE='/Game/GrandTour/ArtTests/LidarStudy';DEST=BASE+'/RiverDetail'
KIT='/Game/GrandTour/Environment/NativePlants/v01';DG='/Game/GrandTour/ArtTests/DeformableGravel'
PREFIX='LidarStudy_RiverDetail_';VERSION='RR1-1'
mel=u.MaterialEditingLibrary;assets=u.EditorAssetLibrary

def grounded_material(source):
 """Owned clone: small stones track native deformation, keeping the kit untouched."""
 path=DEST+'/M_Grounded_'+source.get_name()
 m=u.load_asset(path) or assets.duplicate_asset(source.get_path_name(),path)
 if assets.get_metadata_tag(m,'LP6Grounded')=='1':return m
 g=Graph(m,'LP6Grounded')
 p=g.node(u.MaterialExpressionWorldPosition,world_position_shader_offset=u.WorldPositionIncludedOffsets.WPT_EXCLUDE_ALL_SHADER_OFFSETS)
 tex=g.node(u.MaterialExpressionTextureObjectParameter,parameter_name='GTLS_Field',texture=u.load_asset('/Engine/EngineResources/WhiteSquareTexture'),sampler_type=u.MaterialSamplerType.SAMPLERTYPE_LINEAR_COLOR)
 window=g.node(u.MaterialExpressionVectorParameter,parameter_name='GTLS_Window',default_value=u.LinearColor(0,0,1,0))
 ready=g.node(u.MaterialExpressionScalarParameter,parameter_name='GTLS_Ready',default_value=0)
 node=g.custom(['P','Field','W','Ready'],'''float2 uv=(P.xy-W.xy)/max(W.z,1);if(Ready<.5 || any(uv<0) || any(uv>1))return 0;
float edge=min(min(uv.x,uv.y),min(1-uv.x,1-uv.y));
return float3(0,0,Texture2DSampleLevel(Field,FieldSampler,uv,0).r*smoothstep(0,100/max(W.z,1),edge));''')
 for a,pin in [(p,'P'),(tex,'Field'),(window,'W'),(ready,'Ready')]:g.wire(a,node,pin)
 g.output(node,u.MaterialProperty.MP_WORLD_POSITION_OFFSET)
 # Small detail thins through its cull band rather than popping as a whole patch.
 old=mel.get_material_property_input_node(m,u.MaterialProperty.MP_OPACITY_MASK)
 oo=mel.get_material_property_input_node_output_name(m,u.MaterialProperty.MP_OPACITY_MASK)
 fade=g.node(u.MaterialExpressionPerInstanceFadeAmount);pixel=g.node(u.MaterialExpressionScreenPosition)
 mask=g.custom(['Old','Fade','Pixel'],'float n=frac(52.9829189*frac(dot(Pixel.xy,float2(.06711056,.00583715))));return Old*(Fade>n);',u.CustomMaterialOutputType.CMOT_FLOAT1)
 g.wire(old or g.scalar(1),mask,'Old',oo if old else '');g.wire(fade,mask,'Fade');g.wire(pixel,mask,'Pixel','PixelPosition')
 props(m,blend_mode=u.BlendMode.BLEND_MASKED,opacity_mask_clip_value=.5)
 g.output(mask,u.MaterialProperty.MP_OPACITY_MASK)
 assert not mel.recompile_material(m);assets.set_metadata_tag(m,'LP6Grounded','1');assets.save_loaded_asset(m);return m

def patch(m,mask,spec):
 nodes=list(mel.get_material_expressions(m));g=Graph(m,'RR1')
 main=next(n for n in nodes if isinstance(n,u.MaterialExpressionCustom) and 'float3 rich=' in n.get_editor_property('code'))
 code=main.get_editor_property('code')
 if 'RR1State=field;' not in code:code=code.replace('float3 rich=','RR1State=field;\nfloat3 rich=',1)
 outputs=list(main.get_editor_property('additional_outputs'))
 if not any(str(o.get_editor_property('output_name'))=='RR1State' for o in outputs):outputs.append(props(u.CustomOutput(),output_name='RR1State',output_type=u.CustomMaterialOutputType.CMOT_FLOAT4))
 main.set_editor_property('additional_outputs',outputs);main.set_editor_property('code',code)
 final=next((n for n in nodes if str(n.get_editor_property('desc'))=='RR1Final'),None)
 if not final:
  old={p:(mel.get_material_property_input_node(m,p),mel.get_material_property_input_node_output_name(m,p)) for p in [u.MaterialProperty.MP_BASE_COLOR,u.MaterialProperty.MP_NORMAL,u.MaterialProperty.MP_ROUGHNESS]}
  final=g.custom(['Base','NativeN','NativeR','P','Camera','State','Mask','GC','GN','GO'],'return Base;',outputs=[('Normal',u.CustomMaterialOutputType.CMOT_FLOAT3),('Rough',u.CustomMaterialOutputType.CMOT_FLOAT1)])
  final.set_editor_property('desc','RR1Final')
  for prop,pin in [(u.MaterialProperty.MP_BASE_COLOR,'Base'),(u.MaterialProperty.MP_NORMAL,'NativeN'),(u.MaterialProperty.MP_ROUGHNESS,'NativeR')]:
   node,out=old[prop];assert node,(m.get_path_name(),pin);g.wire(node,final,pin,out)
  for node,pin in [(g.node(u.MaterialExpressionWorldPosition,world_position_shader_offset=u.WorldPositionIncludedOffsets.WPT_EXCLUDE_ALL_SHADER_OFFSETS),'P'),(g.node(u.MaterialExpressionCameraPositionWS),'Camera')]:g.wire(node,final,pin)
  for pin,name,sampler in [('GC','TA_GV_Color',u.MaterialSamplerType.SAMPLERTYPE_COLOR),('GN','TA_GV_Normal',u.MaterialSamplerType.SAMPLERTYPE_NORMAL),('GO','TA_GV_ORH',u.MaterialSamplerType.SAMPLERTYPE_LINEAR_COLOR)]:
   t=u.load_asset(DG+'/'+name);assert t,name
   g.wire(g.node(u.MaterialExpressionTextureObjectParameter,parameter_name='RR1'+pin,texture=t,sampler_type=sampler,sampler_source=u.SamplerSourceMode.SSM_WRAP_WORLD_GROUP_SETTINGS),final,pin)
  g.wire(g.node(u.MaterialExpressionTextureObjectParameter,parameter_name='RR1Mask',texture=mask,sampler_type=u.MaterialSamplerType.SAMPLERTYPE_LINEAR_COLOR,sampler_source=u.SamplerSourceMode.SSM_CLAMP_WORLD_GROUP_SETTINGS),final,'Mask')
 # Polish reattaches LT4; always put RR1 after its final colour pass.
 lt4=next(n for n in nodes if str(n.get_editor_property('desc'))=='LT4Final');g.wire(lt4,final,'Base')
 g.wire(main,final,'State','RR1State')
 ox,oy=spec['mask_origin_cm'];span=spec['mask_span_cm']
 final.set_editor_property('code','''
Normal=NativeN;Rough=NativeR;
float2 mu=(P.xy-float2(%f,%f))/%f;
float3 mask=Texture2DSample(Mask,GCSampler,saturate(mu)).rgb;
mask*=all(mu>=0)&&all(mu<=1);
float cover=max(mask.r,mask.g);
float2 uv=float2(P.x-State.g,-P.y+State.b)/lerp(320.,200.,mask.g);
float2 dx=ddx(uv),dy=ddy(uv);
float3 colour=Base;
[branch] if(cover>.001) {
 float4 loose=GO.SampleGrad(GCSampler,float3(uv,0),dx,dy);
 // DG1's height-aware loose/packed blend, driven by native live disturbance.
 float worked=saturate(State.a)*smoothstep(.05,1.5,max(0,-State.r));
 float packed=smoothstep(.35,.70,worked-.30*(loose.b-.2959));
 float3 c=GC.SampleGrad(GCSampler,float3(uv,0),dx,dy).rgb;
 float3 n=UnpackNormalMap(GN.SampleGrad(GCSampler,float3(uv,0),dx,dy));
 float rough=loose.g,ao=loose.r;
 [branch] if(packed>.001) {
  float4 q=GO.SampleGrad(GCSampler,float3(uv,1),dx,dy);
  c=lerp(c,GC.SampleGrad(GCSampler,float3(uv,1),dx,dy).rgb,packed);
  n=lerp(n,UnpackNormalMap(GN.SampleGrad(GCSampler,float3(uv,1),dx,dy)),packed);
  rough=lerp(rough,q.g,packed);ao=lerp(ao,q.r,packed);
 }
 float wet=mask.r*(1-mask.g);
 float broad=.94+.06*sin(P.x/430.+sin(P.y/680.));
 c*=.82*float3(1.10,.94,.73)*broad*lerp(1.,.75,wet)*(1-.15*(1-ao));
 colour=lerp(colour,c,cover);
 float fade=1-smoothstep(1800.,5500.,distance(Camera,P));
 Normal=normalize(NativeN+float3(n.x,-n.y,0)*.65*cover*fade);
 Rough=lerp(NativeR,max(.4,lerp(rough,.4,wet)),cover);
}
// Moss on the raised, damp banks; grain remains supplied by the existing ground.
float moss=mask.b*.65*(1-cover);
return lerp(colour,Base*float3(.65,.93,.48),moss);
'''%(ox,oy,span))
 g.output(final,u.MaterialProperty.MP_BASE_COLOR);g.output(final,u.MaterialProperty.MP_NORMAL,'Normal');g.output(final,u.MaterialProperty.MP_ROUGHNESS,'Rough')
 assert not mel.recompile_material(m),m.get_path_name();assets.set_metadata_tag(m,'RR1Version',VERSION);assets.save_loaded_asset(m)
 return m.get_path_name()

def install():
 spec=json.loads((OUT/'river-repair.json').read_text());assert spec['version'] in (VERSION,'RR2-1')
 src=OUT/'river-detail.png';digest=hashlib.sha256(src.read_bytes()).hexdigest();mask=u.load_asset(DEST+'/T_RiverDetail')
 if not mask or assets.get_metadata_tag(mask,'RR1SourceSHA')!=digest:
  task=props(u.AssetImportTask(),filename=str(src),destination_path=DEST,destination_name='T_RiverDetail',automated=True,replace_existing=True,save=True)
  u.AssetToolsHelpers.get_asset_tools().import_asset_tasks([task]);mask=u.load_asset(DEST+'/T_RiverDetail');assert mask
  assets.set_metadata_tag(mask,'RR1SourceSHA',digest)
 props(mask,srgb=False,compression_settings=u.TextureCompressionSettings.TC_BC7,address_x=u.TextureAddress.TA_CLAMP,address_y=u.TextureAddress.TA_CLAMP)
 assets.save_loaded_asset(mask)
 mats=[patch(u.load_asset(BASE+'/M_'+name),mask,spec) for name in ['Terrain','Detail']]
 actors=u.get_editor_subsystem(u.EditorActorSubsystem);refs=actors.get_all_level_actors()
 author=next(a for a in refs if isinstance(a,u.GTProceduralGround));tiles=list(author.relief_tiles.values());before=str(author.output_digest)
 bounds=[(t.get_actor_location().x,t.get_actor_location().y,t.span_cm,t) for t in tiles]
 def ground(x,y):
  for ox,oy,span,t in bounds:
   if ox<=x<ox+span and oy<=y<oy+span:return t.height_at(u.Vector2D(x,y))
  return author.base_height_at(u.Vector2D(x,y))
 # Saved route points provide a conservative exclusion around both crossings.
 roads=json.loads((OUT/'roads.json').read_text());rp=next(r['authoring']['points_cm'] for r in roads if r.get('authoring'))
 def road_distance(x,y):
  best=1e20
  for a,b in zip(rp,rp[1:]):
   dx=b[0]-a[0];dy=b[1]-a[1];t=max(0,min(1,((x-a[0])*dx+(y-a[1])*dy)/max(1,dx*dx+dy*dy)))
   best=min(best,math.hypot(x-a[0]-t*dx,y-a[1]-t*dy))
  return best
 legacy_bars=0
 for a in refs:
  if a.get_actor_label().startswith(PREFIX):actors.destroy_actor(a)
  elif a.get_actor_label().startswith('LidarStudy_LoggingDetail_gravel_bank_'):
   actors.destroy_actor(a);legacy_bars+=1
 # LP6: nested pebble patches around authored bed clusters, with reproducible gaps.
 # Small dressing is batched, non-colliding and shadowless. Keep the driving clearance.
 items=list(spec['items']);rng=random.Random(20261020)
 for item in spec['items']:
  if 'Cobble_Cluster' not in item['mesh']:continue
  for j in range(18):
   angle=rng.uniform(0,math.tau);radius=math.sqrt(rng.random())*190
   x,y=item['xy_cm'];scale=rng.uniform(.65,1.25)
   items.append(dict(mesh='SM_NZ_Cobble_Cluster_'+rng.choice(['S','M','M']),xy_cm=[x+math.cos(angle)*radius,y+math.sin(angle)*radius],scale=scale,yaw=rng.uniform(0,360),solid=False,micro=True))
 groups={};skipped=0;seating_skipped=0;counts={};solid_count=0
 ground_surface=next(a for a in refs if isinstance(a,u.GTLandscapeSurface))
 for item in items:
  x,y=item['xy_cm'];name=item['mesh'];solid=item['solid'];distance=road_distance(x,y)
  if distance<(300 if solid else 170) and not name.startswith('SM_NZ_Cobble'):
   skipped+=1;continue
  mesh=u.load_asset(KIT+'/'+name);assert mesh,name
  scale=item['scale'];z=ground(x,y);angle=math.radians(item['yaw']);dx,dy=math.cos(angle),math.sin(angle)
  slope=(ground(x+dx*35,y+dy*35)-ground(x-dx*35,y-dy*35))/70
  side=(ground(x-dy*35,y+dx*35)-ground(x+dy*35,y-dx*35))/70
  rock='Cobble' in name or 'Boulder' in name;wood='Driftwood' in name or 'LogJam' in name
  if 'Cobble_Cluster' in name:
   # These kit meshes include a thin gravel base. Do not bridge a sharp bank
   # with that base: reject high curvature, otherwise sink its full footprint.
   box=mesh.get_bounding_box();radius=max(box.max.x-box.min.x,box.max.y-box.min.y)*scale*.55
   gx=(ground(x+30,y)-ground(x-30,y))/60;gy=(ground(x,y+30)-ground(x,y-30))/60
   error=min(ground(x+radius*math.cos(a),y+radius*math.sin(a))-z-radius*(gx*math.cos(a)+gy*math.sin(a)) for a in [j*math.pi/4 for j in range(8)])
   if error < -8:seating_skipped+=1;continue
   z+=min(0,error)
  pitch=math.degrees(math.atan(slope)) if rock or wood else 0;roll=-math.degrees(math.atan(side)) if rock or wood else 0
  # Kit stones have an intentionally buried gravel apron. Its lowest vertex is
  # not the seating pivot. Scaling that apron into the ground hid small stones.
  z-=.5 if rock else mesh.get_bounding_box().min.z*scale+3
  tf=u.Transform(location=u.Vector(x,y,z),rotation=u.Rotator(pitch=pitch,yaw=item['yaw'],roll=roll),scale=u.Vector(scale,scale,scale))
  groups.setdefault((math.floor(x/6400),math.floor(y/6400),name,solid,item.get('micro',False)),[]).append(tf)
  counts[name]=counts.get(name,0)+1;solid_count+=int(solid)
 for (cx,cy,name,solid,micro),transforms in groups.items():
  a=actors.spawn_actor_from_class(u.GTGroundedDressing if micro else u.Actor,u.Vector(cx*6400,cy*6400,0));a.set_actor_label(PREFIX+str(cx)+'_'+str(cy)+'_'+name+('_micro' if micro else ''));a.tags=['LidarRiverDetail',VERSION]
  if micro:a.set_editor_property('ground_surface',ground_surface)
  if a.root_component:a.root_component.set_mobility(u.ComponentMobility.STATIC)
  c=u.GTVegetationSubsystem.add_tagged_instances(a,u.load_asset(KIT+'/'+name),transforms,'LidarRiverDetail','BlockAll' if solid else 'NoCollision',solid)
  c.set_collision_enabled(u.CollisionEnabled.QUERY_AND_PHYSICS if solid else u.CollisionEnabled.NO_COLLISION)
  c.set_cull_distances(2500 if micro else 10000 if solid else 4500,4500 if micro else 16000 if solid else 7000)
  props(c,cast_shadow=solid or 'TreeFern' in name or any(k in name for k in ('Coprosma','Gorse','Broom','Matagouri','Shrub')),cast_shadow_as_two_sided=any(k in name for k in ('Coprosma','Gorse','Broom','Matagouri','Shrub')),visible_in_ray_tracing=False,affect_distance_field_lighting=False)
  foliage=u.load_asset(BASE+'/MI_NZ_Foliage_Bush');assert foliage
  for i,slot in enumerate(u.load_asset(KIT+'/'+name).get_editor_property('static_materials')):
   material=slot.get_editor_property('material_interface')
   if micro and material:c.set_material(i,grounded_material(material))
   if material and material.get_path_name().split('.')[0]==KIT+'/M_NZ_Foliage':c.set_material(i,foliage)
 assert str(author.output_digest)==before
 result=dict(ok=True,version=VERSION,materials=mats,instances=sum(counts.values()),components=len(groups),solid_instances=solid_count,by_mesh=counts,skipped_crossing_clearance=skipped,skipped_steep_cobble_bases=seating_skipped,replaced_legacy_bar_meshes=legacy_bars,ground_digest=before,mask_sha256=digest,physics='Existing LiDAR native ground field; DG1 loose/packed appearance, no second simulator',runtime_generation=False)
 (OUT/'riverdetail.json').write_text(json.dumps(result,indent=2))
 if (OUT/'river-plant-variety.json').exists():
  import lidar_river_plant_variety
  variety=lidar_river_plant_variety.apply()
  result=json.loads((OUT/'riverdetail.json').read_text());result['plant_variety']=variety
  (OUT/'riverdetail.json').write_text(json.dumps(result,indent=2))
 return result

if __name__=='__main__':
 import time,traceback,gc
 result=dict(ok=False);busy=False
 def run():
  global result
  les=u.get_editor_subsystem(u.LevelEditorSubsystem);assert les.load_level(BASE+'/L_LidarStudy');yield 1
  result=install();result['ok']=False
  assert les.save_current_level();result['ok']=True;result['saved']=True
  (OUT/'riverdetail.json').write_text(json.dumps(result,indent=2));yield 1
  gc.collect();les.load_level('/Engine/Maps/Entry');yield 4
 steps=run();deadline=0;began=time.monotonic()
 def tick(dt):
  global busy,deadline,steps
  if busy:return
  busy=True
  try:
   assert time.monotonic()-began<900
   if time.monotonic()>=deadline:deadline=time.monotonic()+next(steps)
  except StopIteration:u.unregister_slate_post_tick_callback(handle);steps=None;gc.collect();u.SystemLibrary.quit_editor()
  except Exception:
   result.update(ok=False,error=traceback.format_exc());(OUT/'riverdetail.json').write_text(json.dumps(result,indent=2));u.log_error(result['error']);u.unregister_slate_post_tick_callback(handle);u.SystemLibrary.quit_editor()
  finally:busy=False
 u.EditorPythonScripting.set_keep_python_script_alive(True);handle=u.register_slate_post_tick_callback(tick)
