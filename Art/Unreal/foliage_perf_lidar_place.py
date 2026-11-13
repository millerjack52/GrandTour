"""FoliagePerf (LP3a): cheap-to-render foliage on L_LidarStudy without changing its look. Re-runnable after any Install.
1. Layout. Every component of LidarStudy_Forest / LidarStudy_Understory is regrouped, same world transforms, override
   materials, cull distances, collision, visibility and component tag (the tag add_tagged_instances gives:
   LidarStudyForest, LidarStudyTrunks, LidarStudyUnderstory), into one component per mesh per grid cell.
   GT_FOLIAGE_CELL_CM (default DEFAULT_CELL_CM) is the cell edge in world cm, cells floor(x/edge), floor(y/edge): the
   GTProceduralGround grid keys its 64 m cells off the world origin (AGTProceduralGround exposes no patch origin of
   its own). 0 keeps one component per mesh. GT_FOLIAGE_CLASS (default DEFAULT_CLASS) is ISM or HISM. A group that
   already has the requested layout is left alone. Per-mesh instance counts are asserted equal before and after.
2. Flags on every foliage component (canopy, trunk and understory components, GTMixedGroundDetails Grass and
   DistantGrass): visible_in_ray_tracing off, affect_distance_field_lighting off, affect_dynamic_indirect_lighting off,
   shadow_cache_invalidation_behavior Rigid; SM_Canopy_0/1 LOD 2 and 3 stop casting shadows; the grass understory
   kind casts none.
3. Saves the level, reloads it, re-counts instances per mesh, components per class and mobility, re-reads the flags.
Writes Place/foliageperf.json (ok key) and Place/foliageperf-flags.json (every per-component flag change)."""
from pathlib import Path
import os
import unreal as u
ROOT=Path(u.Paths.project_dir()).resolve()
exec(compile((ROOT/'Art/Unreal/install_lidar_place.py').read_text().split('def run():')[0],'<lidar-place-helpers>','exec'))
DEFAULT_CELL_CM=0.;DEFAULT_CLASS='ISM'
CELL=float(os.environ.get('GT_FOLIAGE_CELL_CM',DEFAULT_CELL_CM));KIND=os.environ.get('GT_FOLIAGE_CLASS',DEFAULT_CLASS).upper();assert KIND in ('ISM','HISM'),KIND
CLASS_NAME='HierarchicalInstancedStaticMeshComponent' if KIND=='HISM' else 'InstancedStaticMeshComponent'
CLASS=getattr(u,CLASS_NAME);LABEL=('c%d'%CELL) if CELL else 'whole'
FOLIAGE_ACTORS=['LidarStudy_Forest','LidarStudy_Understory']
EXPECTED_CULL={'LidarStudyForest':(380000,450000),'LidarStudyUnderstory':(18000,30000),'LidarStudyTrunks':(0,0)}
ALL_FLAGS=dict(rt=('visible_in_ray_tracing',False),dfl=('affect_distance_field_lighting',False),dil=('affect_dynamic_indirect_lighting',False),cache=('shadow_cache_invalidation_behavior',u.ShadowCacheInvalidationBehavior.RIGID))
# GT_FOLIAGE_FLAGS picks a subset of rt,dfl,dil,cache,lod for A/B measurements; the default is all of them.
SELECTED=[k.strip() for k in os.environ.get('GT_FOLIAGE_FLAGS','rt,dfl,dil,cache,lod').split(',') if k.strip()];assert all(k in ALL_FLAGS or k=='lod' for k in SELECTED),SELECTED
FLAGS={ALL_FLAGS[k][0]:ALL_FLAGS[k][1] for k in SELECTED if k in ALL_FLAGS}
GRASS_MESHES=['SM_NativeShortGrass']
report=dict(ok=False,driving_tested=False,config=dict(cell_cm=CELL,component_class=CLASS_NAME,label=LABEL,flags=SELECTED),log=[],timing={})
sds=u.get_engine_subsystem(u.SubobjectDataSubsystem);sbl=u.SubobjectDataBlueprintFunctionLibrary

def save():(OUT/'foliageperf.json').write_text(json.dumps(report,indent=2,default=str))
def log(msg):report['log'].append(msg);u.log(msg)
def foliage_components(refs):
 out=[]
 for a in refs:
  if a.get_actor_label() in FOLIAGE_ACTORS:out+=[(a,c) for c in a.get_components_by_class(u.InstancedStaticMeshComponent) if c.static_mesh]
  elif isinstance(a,u.GTMixedGroundDetails):out+=[(a,c) for c in [a.grass,a.distant_grass] if c]
 return out
def inventory(refs):
 out={}
 for a in refs:
  if a.get_actor_label() in FOLIAGE_ACTORS:
   meshes={};classes={};mobility={}
   for c in a.get_components_by_class(u.InstancedStaticMeshComponent):
    if not c.static_mesh:continue
    n=c.static_mesh.get_name();meshes[n]=meshes.get(n,0)+c.get_instance_count();k=c.get_class().get_name();classes[k]=classes.get(k,0)+1;m=str(c.get_editor_property('mobility')).split('.')[-1].split(':')[0];mobility[m]=mobility.get(m,0)+1
   out[a.get_actor_label()]=dict(instances=meshes,components=classes,mobility=mobility)
 return out

def new_component(parent,name):
 r=sds.add_new_subobject(u.AddNewSubobjectParams(parent_handle=parent,new_class=CLASS))
 handle,why=(r if isinstance(r,tuple) else (r,None))
 assert sbl.is_handle_valid(handle),str(why)
 assert sds.rename_subobject(handle,u.Text(name)),name
 c=sbl.get_object(sbl.get_data(handle));assert isinstance(c,CLASS) and c.get_class().get_name()==CLASS_NAME,(name,c)
 return c

def settings(c):
 tags=[str(t) for t in c.get_editor_property('component_tags')];assert len(tags)==1 and tags[0] in EXPECTED_CULL,tags
 cull=(c.get_editor_property('instance_start_cull_distance'),c.get_editor_property('instance_end_cull_distance'));assert cull==EXPECTED_CULL[tags[0]],(tags,cull)
 assert c.get_editor_property('num_custom_data_floats')==0
 return dict(tag=tags[0],mesh=c.static_mesh.get_path_name(),profile=str(c.get_collision_profile_name()),enabled=c.get_collision_enabled(),cast=c.get_editor_property('cast_shadow'),visible=c.get_editor_property('visible'),hidden=c.get_editor_property('hidden_in_game'),materials=[m.get_path_name() if m else None for m in c.get_editor_property('override_materials')],cull=cull)

def groups_of(actor):
 groups={}
 for c in actor.get_components_by_class(u.InstancedStaticMeshComponent):
  if c.static_mesh:groups.setdefault((str(c.get_editor_property('component_tags')[0]),c.static_mesh.get_path_name()),[]).append(c)
 return groups

def layout_ok(cs):
 if any(c.get_class().get_name()!=CLASS_NAME for c in cs):return False
 if not CELL:return len(cs)==1
 pre='%s_%s_%s_x'%(str(cs[0].get_editor_property('component_tags')[0]),cs[0].static_mesh.get_name(),LABEL);return all(c.get_name().startswith(pre) for c in cs)

def regroup(actor,cs):
 began=time.monotonic();s=settings(cs[0]);assert all(settings(c)==s for c in cs[1:]),'mixed settings in one group'
 mesh=cs[0].static_mesh;materials=[u.load_asset(p) if p else None for p in s['materials']];transforms=[]
 for c in cs:transforms+=[c.get_instance_transform(i,True) for i in range(c.get_instance_count())]
 n=len(transforms);assert n==sum(c.get_instance_count() for c in cs);cells={}
 for t in transforms:cells.setdefault((math.floor(t.translation.x/CELL),math.floor(t.translation.y/CELL)) if CELL else (0,0),[]).append(t)
 transforms=None;parent=sds.k2_gather_subobject_data_for_instance(actor)[0];made=0
 for (i,j),ts in sorted(cells.items()):
  h=new_component(parent,'%s_%s_%s_x%d_y%d'%(s['tag'],mesh.get_name(),LABEL,i,j));h.set_mobility(u.ComponentMobility.STATIC);h.set_static_mesh(mesh)
  for slot,m in enumerate(materials):
   if m:h.set_material(slot,m)
  h.set_editor_property('component_tags',[s['tag']]);h.set_collision_profile_name(s['profile']);h.set_collision_enabled(s['enabled']);h.set_cast_shadow(s['cast']);h.set_cull_distances(*s['cull'])
  if not s['visible']:h.set_visibility(False)
  if s['hidden']:h.set_hidden_in_game(True)
  h.add_instances(ts,False,True);assert h.get_instance_count()==len(ts);made+=len(ts)
 assert made==n,(s['tag'],mesh.get_name(),made,n)
 for c in cs:c.destroy_component(c)
 sizes=[len(v) for v in cells.values()];row=dict(actor=actor.get_actor_label(),tag=s['tag'],mesh=s['mesh'],instances=n,components_before=len(cs),components_after=len(cells),largest=max(sizes),seconds=round(time.monotonic()-began,1),cull=list(s['cull']),collision=dict(profile=s['profile'],enabled=str(s['enabled'])),cast_shadow=s['cast'],visible=s['visible'],hidden_in_game=s['hidden'],materials=s['materials'])
 log('regroup %s %s [%s %s]: %d instances, %d -> %d components (largest %d) in %.0fs'%(s['tag'],mesh.get_name(),CLASS_NAME,LABEL,n,len(cs),len(cells),max(sizes),row['seconds']));return row

def apply_flags(c):
 changes={}
 for k,v in FLAGS.items():
  before=c.get_editor_property(k)
  if before!=v:c.set_editor_property(k,v);changes[k]=[str(before),str(v)]
 if 'lod' in SELECTED and c.static_mesh and c.static_mesh.get_name() in GRASS_MESHES and c.get_editor_property('cast_shadow'):c.set_cast_shadow(False);changes['cast_shadow']=[True,False]
 return changes

def lod_shadows():
 sm=u.get_editor_subsystem(u.StaticMeshEditorSubsystem);rows={}
 for k in range(2):
  mesh=u.load_asset(BASE+'/Canopy/SM_Canopy_'+str(k));assert mesh;n=sm.get_lod_count(mesh);assert n==4,n
  verts=[sm.get_number_verts(mesh,j) for j in range(n)];sections={};changed=False
  for lod in range(n):
   for sec in range(mesh.get_num_sections(lod)):
    before=sm.is_section_cast_shadow_enabled(mesh,lod,sec);want=lod<2
    if before!=want:sm.enable_section_cast_shadow(mesh,want,lod,sec);changed=True;log('%s LOD %d section %d cast_shadow %s -> %s'%(mesh.get_name(),lod,sec,before,want))
    sections['lod%d_sec%d'%(lod,sec)]=dict(before=before,after=sm.is_section_cast_shadow_enabled(mesh,lod,sec))
  if changed:assert assets.save_loaded_asset(mesh)
  rows[mesh.get_name()]=dict(sections=sections,saved=changed,vertices_before=verts,vertices_after=[sm.get_number_verts(mesh,j) for j in range(n)])
 return rows

def run():
 before=protected();backup=ROOT/'Saved/LidarStudyBackups'/('FoliagePerf-'+str(time.time_ns()));shutil.copytree(ROOT/'Content/GrandTour/ArtTests/LidarStudy',backup);report['backup']=str(backup);prune_backups(backup.parent)
 assert les.load_level(LEVEL);refs=actors.get_all_level_actors();report['before']=inventory(refs);report['regroup']=[];save()
 for a in refs:
  if a.get_actor_label() in FOLIAGE_ACTORS:
   a.modify()
   for key,cs in sorted(groups_of(a).items()):
    if layout_ok(cs):log('keep %s %s: %d component(s) already %s'%(key[0],key[1].split('.')[-1],len(cs),LABEL));continue
    report['regroup'].append(regroup(a,cs));save();yield 1
 refs=actors.get_all_level_actors();after_split=inventory(refs)
 for label in FOLIAGE_ACTORS:
  assert after_split[label]['instances']==report['before'][label]['instances'],(label,after_split[label],report['before'][label])
  assert list(after_split[label]['components'])==[CLASS_NAME] and list(after_split[label]['mobility'])==['STATIC'],after_split[label]
 report['after_layout']=after_split;save();yield 1
 comps=foliage_components(refs);details={};summary={}
 for a,c in comps:
  ch=apply_flags(c)
  if ch:
   details[a.get_actor_label()+'/'+c.get_name()]=ch
   for k in ch:summary[k]=summary.get(k,0)+1
 (OUT/'foliageperf-flags.json').write_text(json.dumps(details,separators=(',',':'),default=str))
 grass={a.get_actor_label()+'/'+c.get_name():dict(changes=details.get(a.get_actor_label()+'/'+c.get_name(),{}),cast_shadow=c.get_editor_property('cast_shadow')) for a,c in comps if isinstance(a,u.GTMixedGroundDetails)}
 report['flags']=dict(components=len(comps),changed=summary,target={k:str(v) for k,v in FLAGS.items()},grass=grass,detail_file=str(OUT/'foliageperf-flags.json'))
 log('flags: %d foliage components, changes %s'%(len(comps),summary));comps=None;save();yield 1
 report['lod_shadows']=lod_shadows() if 'lod' in SELECTED else 'skipped';save();yield 3
 assert les.save_current_level();report['level_saved']=True;save()
 refs=a=c=None;gc.collect();yield 2
 assert les.load_level('/Engine/Maps/Entry');yield 3
 assert les.load_level(LEVEL);refs=actors.get_all_level_actors();report['after_reload']=inventory(refs)
 for label in FOLIAGE_ACTORS:assert report['after_reload'][label]==after_split[label],(label,report['after_reload'][label],after_split[label])
 bad=[]
 for a,c in foliage_components(refs):
  for k,v in FLAGS.items():
   if c.get_editor_property(k)!=v:bad.append((a.get_actor_label(),c.get_name(),k,str(c.get_editor_property(k))))
  if 'lod' in SELECTED and c.static_mesh and c.static_mesh.get_name() in GRASS_MESHES and c.get_editor_property('cast_shadow'):bad.append((a.get_actor_label(),c.get_name(),'cast_shadow',True))
 assert not bad,bad[:10]
 assert protected()==before;report.update(ok=True,protected_unchanged=len(before),elapsed_s=round(time.monotonic()-began,1));save()
 refs=a=c=None;gc.collect();yield 2;les.load_level('/Engine/Maps/Entry');yield 4

steps=run();deadline=0;began=time.monotonic()
def tick(dt):
 global deadline,busy,steps
 if busy:return
 busy=True
 try:
  assert time.monotonic()-began<2400,'FoliagePerf timeout'
  if time.monotonic()>=deadline:deadline=time.monotonic()+next(steps)
 except StopIteration:u.unregister_slate_post_tick_callback(handle);steps=None;gc.collect();u.SystemLibrary.quit_editor()
 except Exception:
  report['error']=traceback.format_exc();save();u.log_error(report['error']);u.unregister_slate_post_tick_callback(handle);u.SystemLibrary.quit_editor()
 finally:busy=False
u.EditorPythonScripting.set_keep_python_script_alive(True);handle=u.register_slate_post_tick_callback(tick)
