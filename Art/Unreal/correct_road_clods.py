"""Remove excessive road-wide clods without resetting the user's other rules."""
import unreal as u
from pathlib import Path
import json,hashlib,traceback,time,shutil,gc
ROOT=Path(u.Paths.project_dir()).resolve();OUT=ROOT/'Art/Export/ProceduralGround';BASE='/Game/GrandTour/ArtTests/ProceduralGround'
actors=u.get_editor_subsystem(u.EditorActorSubsystem);les=u.get_editor_subsystem(u.LevelEditorSubsystem);assets=u.EditorAssetLibrary
report=dict(ok=False,visual_checked=False,driving_tested=False);busy=False
def save():(OUT/'clodcorrection-functional.json').write_text(json.dumps(report,indent=2))
def inventory():
 rows={};hashes={}
 for a in actors.get_all_level_actors():
  if 'GT.ProceduralGround.Output' not in [str(t) for t in a.tags]:continue
  for c in a.get_components_by_class(u.InstancedStaticMeshComponent):
   name=str(c.component_tags[0]);rows[name]=rows.get(name,0)+c.get_instance_count()
   for i in range(c.get_instance_count()):
    t=c.get_instance_transform(i,True)
    value=[c.static_mesh.get_path_name(),*t.translation.to_tuple(),*t.rotation.to_tuple(),*t.scale3d.to_tuple()]
    hashes.setdefault(name,[]).append(json.dumps(value))
 return rows,{k:hashlib.sha256('\n'.join(sorted(v)).encode()).hexdigest() for k,v in hashes.items()}
def run():
 backup=OUT/'BeforeClodCorrection'
 if not backup.exists():shutil.copytree(ROOT/'Content/GrandTour/ArtTests/ProceduralGround',backup)
 assert les.load_level(BASE+'/L_BigMountain_Authoring')
 author=next(a for a in actors.get_all_level_actors() if isinstance(a,u.GTProceduralGround))
 before,before_hash=inventory();report['before']=before
 terrain=author.current_terrain_digest();tiles={(k.x,k.y):v.get_path_name() for k,v in author.get_editor_property('relief_tiles').items()}
 rules=list(author.scatter_rules);index=next(i for i,r in enumerate(rules) if str(r.name)=='MudClods');r=rules[index]
 for k,v in dict(candidate_budget=64,density=.3,habitat=u.GTScatterHabitat.VERGE,road_debris=False,road_clearance_cm=30,verge_width_cm=350,cluster_strength=.95,cull_distance_cm=12000).items():r.set_editor_property(k,v)
 variants=list(r.variants)
 assert len(variants)==2
 for v,lo,hi in zip(variants,[.55,.5],[1.1,.9]):v.min_size=lo;v.max_size=hi
 r.variants=variants;rules[index]=r;author.scatter_rules=rules
 assert author.rebuild(),author.last_message;yield 2
 after,after_hash=inventory();report['after']=after
 assert 0<after.get('MudClods',0)<200,after
 assert all(after_hash[k]==v for k,v in before_hash.items() if k!='MudClods'),'Other generated layers changed'
 assert author.current_terrain_digest()==terrain
 report['changed_relief_tiles']=author.changed_relief_tiles
 assert author.changed_relief_tiles==0 and {(k.x,k.y):v.get_path_name() for k,v in author.get_editor_property('relief_tiles').items()}==tiles
 baseline=author.output_digest;assert author.rebuild() and author.output_digest==baseline and author.changed_cells==0
 report.update(other_layers_unchanged=True,terrain_unchanged=True,repeatable=True,digest=baseline)
 for t in [author.paint_texture,author.style_texture,author.macro_texture]:assert assets.save_loaded_asset(t)
 assert les.save_current_level();yield 3
 assert les.load_level('/Engine/Maps/Entry');assert les.load_level(BASE+'/L_BigMountain_Authoring')
 after_reload,h=inventory();assert after_reload==after and h==after_hash
 report['saved_and_reloaded']=True
 for p,d in json.loads((OUT/'install.json').read_text())['protected'].items():assert hashlib.sha256((ROOT/p).read_bytes()).hexdigest()==d,p
 report.update(ok=True,protected_unchanged=True);save();les.load_level('/Engine/Maps/Entry');yield 4
steps=run();deadline=0
def tick(dt):
 global busy,deadline,steps
 if busy:return
 busy=True
 try:
  if time.monotonic()>=deadline:deadline=time.monotonic()+next(steps)
 except StopIteration:u.unregister_slate_post_tick_callback(handle);steps=None;gc.collect();u.SystemLibrary.quit_editor()
 except Exception:
  report['error']=traceback.format_exc();save();u.log_error(report['error']);u.unregister_slate_post_tick_callback(handle);u.SystemLibrary.quit_editor()
 finally:busy=False
u.EditorPythonScripting.set_keep_python_script_alive(True);handle=u.register_slate_post_tick_callback(tick)
