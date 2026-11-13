"""Live logging pools on the saved LiDAR map; retain the authoring bake."""
import unreal as u
from pathlib import Path
import json,time,shutil,math,re,traceback,os
import lidar_logging_trial as trial
ROOT=Path(u.Paths.project_dir()).resolve()
BASE='/Game/GrandTour/ArtTests/LidarStudy'
OUT=ROOT/'Art/Export/LidarStudy/Place'
PREFIX='LidarStudy_LiveRutWater_'
assets=u.EditorAssetLibrary;mel=u.MaterialEditingLibrary

def materials():
 result={}
 for name in ['Water','WaterSim','WaterSediment','Waves']:
  source='/Game/GrandTour/ArtTests/MudLab/M_Lab'+name
  path=BASE+'/RutWater/M_'+name
  m=assets.load_asset(path) or assets.duplicate_asset(source,path)
  assert m,source
  if name!='Waves':
   for node in mel.get_material_expressions(m):
    if isinstance(node,u.MaterialExpressionCustom):
     code=node.get_editor_property('code')
     # The source fixture assumed a flat base and a 50 cm layer. The LiDAR
     # bed is the relief mesh and the streamed field already supplies its
     # clamped displacement (up to 124 cm). Preserve native water arithmetic.
     start=code.find('  float2 q=(xy-PW.xy)/PW.z;')
     end=code.find('\n }\n};Ground ground;',start)
     if start>=0 and end>=0:
      code=code[:start]+'''  float2 uv=(xy-W.xy)/max(W.z,1);
  float edge=min(min(uv.x,uv.y),min(1-uv.x,1-uv.y));
  return Texture2DSampleLevel(Field,FS,saturate(uv),0).r*Ready*smoothstep(0,100/max(W.z,1),edge);'''+code[end:]
     node.set_editor_property('code',code)
   assert not mel.recompile_material(m)
  assert assets.save_loaded_asset(m)
  result[name]=m
 return result

def spray_materials():
 # Source sprites encode their displayed colour; the original unlit adapter
 # was authored in the low-exposure study. Undo UE's scene pre-exposure just
 # as the recovered woodland billboard bridge does, keeping native alpha,
 # distortion, texture, tint and emission arithmetic intact.
 result=[]
 for name in ['mud_small','mud_large','water_small','water_medium','water_large','water_fluid','mud_bits','water_drops','water_bits']:
  source='/Game/GrandTour/ArtTests/MudRoad/NativeInteractions/M_'+name
  path=BASE+'/RutWater/M_Spray_'+name
  m=assets.load_asset(path) or assets.duplicate_asset(source,path)
  node=mel.get_material_property_input_node(m,u.MaterialProperty.MP_EMISSIVE_COLOR)
  assert isinstance(node,u.MaterialExpressionCustom),source
  code=node.get_editor_property('code')
  if 'View.OneOverPreExposure' not in code:
   assert 'return pow(max(s.rgb,0),2.2)*Tint.rgb;' in code
   node.set_editor_property('code',code.replace('return pow(max(s.rgb,0),2.2)*Tint.rgb;','return pow(max(s.rgb,0),2.2)*Tint.rgb*View.OneOverPreExposure;'))
  assert not mel.recompile_material(m)
  assert assets.save_loaded_asset(m)
  result.append(m)
 return result

def install():
 actors=u.get_editor_subsystem(u.EditorActorSubsystem)
 refs=actors.get_all_level_actors()
 surface=next(a for a in refs if isinstance(a,u.GTLandscapeSurface))
 domain=next(a for a in refs if isinstance(a,u.GTWaterSheet) and a.get_editor_property('water_domain'))
 author=next(a for a in refs if isinstance(a,u.GTProceduralGround))
 seed=list(domain.get_editor_property('water_domain').road_patches)[-1]
 assert len(domain.get_editor_property('water_domain').road_patches)==4
 mats=materials();path=trial.route(json.loads((OUT/'roads.json').read_text()))
 sites=[trial.at(path,s) for s in (214,290,552,667)]
 groups=[[] for _ in sites];samples=list(seed.samples);origin=seed.origin_cm;cell=seed.cell_cm;w=seed.size_x
 for i in range(len(samples)//4):
  if samples[i*4+1]<=.005:continue
  x=origin.x+(i%w+.5)*cell;y=origin.y+(i//w+.5)*cell
  group=min(range(4),key=lambda k:(x-sites[k][0])**2+(y-sites[k][1])**2)
  groups[group].append((x,y,samples[i*4],samples[i*4+1]))
 assert sum(map(len,groups))==author.road_pool_wet_samples
 report={'basins':[],'ground_digest':str(author.output_digest),'baked_wet_cells':author.road_pool_wet_samples}
 for a in refs:
  if a.get_actor_label().startswith(PREFIX):actors.destroy_actor(a)
  if isinstance(a,u.GTRoadWaterMesh):a.set_actor_hidden_in_game(True)
 for k,points in enumerate(groups):
  assert points
  lo=[math.floor((min(p[d] for p in points)-200)/25)*25-12.5 for d in (0,1)]
  side=math.ceil(max(max(p[d] for p in points)+200-lo[d] for d in (0,1))/25)
  assert side<=128,('Pool exceeds 25cm simulation budget',k,side)
  half=side*25/2;level=max(p[2] for p in points)
  a=actors.spawn_actor_from_class(u.GTWaterSheet,u.Vector(lo[0]+half,lo[1]+half,level))
  a.set_actor_label(PREFIX+str(k))
  for key,value in dict(mud_surface=surface,mud_initial_domain=seed,mud_half_size_cm=half,mud_cell_cm=25.,base_level_cm=level,
      build_sleeping_mud_basin=True,surface_material_path=mats['Water'].get_path_name(),mud_state_material=mats['WaterSim'],
      mud_sediment_material=mats['WaterSediment'],mud_wave_material=mats['Waves']).items():a.set_editor_property(key,value)
  report['basins'].append(dict(name=a.get_actor_label(),side=side,cells=side*side,seed_volume_m3=sum(p[3]*.0625 for p in points),wet_cells=len(points),centre=[lo[0]+half,lo[1]+half],half_cm=half))
 fx=[a for a in refs if isinstance(a,u.GTMudRunnerWheelEffects)]
 report['emitter_before']=[dict(name=a.get_actor_label(),materials=[str(m) for m in a.materials]) for a in fx]
 assert len(fx)<=1,'Duplicate native emitters; inspect before removing anything'
 emitter=fx[0] if fx else actors.spawn_actor_from_class(u.GTMudRunnerWheelEffects,u.Vector())
 emitter.set_actor_label('LidarStudy_NativeWheelInteractions')
 emitter.materials=spray_materials()
 assert all(emitter.materials)
 surface.use_native_water_response=True
 report['materials']={k:v.get_path_name() for k,v in mats.items()}
 return report

if __name__=='__main__':
 report={'ok':False}
 try:
  if os.environ.get('GT_RUT_MATERIALS_ONLY')=='1':
   report=json.loads((OUT/'rutwater.json').read_text());report['ok']=False
   materials();report['material_repair']=True;report['ok']=True
  else:
   backup=ROOT/'Saved/LidarStudyBackups'/('RutWater-'+str(time.time_ns()));backup.mkdir(parents=True)
   shutil.copy2(ROOT/'Content/GrandTour/ArtTests/LidarStudy/L_LidarStudy.umap',backup/'L_LidarStudy.umap')
   les=u.get_editor_subsystem(u.LevelEditorSubsystem);assert les.load_level(BASE+'/L_LidarStudy')
   report.update(install());report['backup']=str(backup)
   assert les.save_current_level();report['ok']=True
 except Exception:report['error']=traceback.format_exc();u.log_error(report['error'])
 (OUT/'rutwater.json').write_text(json.dumps(report,indent=2))
 u.SystemLibrary.quit_editor()
