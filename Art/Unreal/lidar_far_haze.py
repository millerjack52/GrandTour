"""A low-cost, distance-only haze over the furthest LiDAR ridges."""
import unreal as u,json,sys,os,time,traceback
from pathlib import Path
ROOT=Path(u.Paths.project_dir()).resolve();sys.path.insert(0,str(ROOT/'Art/Unreal'))
import canopy_depth as C
import lidar_first_section as S
import lidar_forest_atmosphere as A
from benmore_river_life_materials import Graph,props
DEST=C.BASE+'/FarHaze';LABEL='LidarStudy_FarHaze';QA=ROOT/'Saved/LidarAuthoringQA/FarHaze';QA.mkdir(exist_ok=True)
mel=u.MaterialEditingLibrary;assets=u.EditorAssetLibrary;les=u.get_editor_subsystem(u.LevelEditorSubsystem)

def build(settings):
 m=u.load_asset(DEST+'/M_FarHaze') or u.AssetToolsHelpers.get_asset_tools().create_asset('M_FarHaze',DEST,u.Material,u.MaterialFactoryNew())
 mel.delete_all_material_expressions(m)
 props(m,material_domain=u.MaterialDomain.MD_POST_PROCESS,blendable_location=u.BlendableLocation.BL_SCENE_COLOR_AFTER_TONEMAPPING,blendable_priority=10)
 g=Graph(m,'FarRidgeHaze')
 scene=g.node(u.MaterialExpressionSceneTexture,scene_texture_id=u.SceneTextureId.PPI_POST_PROCESS_INPUT0)
 depth=g.node(u.MaterialExpressionSceneDepth)
 node=g.custom(['Scene','Depth','Range','Colour'],'''
// No grain or lighting change: a smooth veil over distant geometry only.
float amount=smoothstep(Range.x,Range.y,Depth)*Range.z;
// Preserve the sky; the level's geometry lies well inside this distance.
amount*=1-smoothstep(900000,1000000,Depth);
return lerp(Scene.rgb,Colour,amount);
''')
 for a,p,o in [(scene,'Scene','Color'),(depth,'Depth',''),(g.vector((settings['start_cm'],settings['end_cm'],settings['opacity'])),'Range',''),(g.vector(settings['colour_sdr']),'Colour','')]:g.wire(a,node,p,o)
 g.output(node,u.MaterialProperty.MP_EMISSIVE_COLOR)
 assert not mel.recompile_material(m);assert assets.save_loaded_asset(m,False)
 return m

def apply(settings):
 m=u.load_asset(DEST+'/M_FarHaze');assert m,'Build FarHaze material before applying'
 a=next((a for a in C.actors.get_all_level_actors() if a.get_actor_label()==LABEL),None) or C.actors.spawn_actor_from_class(u.PostProcessVolume,u.Vector())
 a.set_actor_label(LABEL);props(a,unbound=True,priority=10.,blend_weight=1.,enabled=True)
 s=a.settings;s.set_editor_property('weighted_blendables',u.WeightedBlendables(array=[u.WeightedBlendable(weight=1.,object=m)]));a.settings=s
 return a

def state():
 rows=C.actors.get_all_level_actors()
 fog=next(a for a in rows if isinstance(a,u.ExponentialHeightFog));f=fog.component
 return dict(bank=S.snapshot(),understory=S.outside_snapshot(),instances={a.get_actor_label()+'/'+c.get_name():dict(mesh=c.static_mesh.get_path_name(),materials=[c.get_material(i).get_path_name() if c.get_material(i) else None for i in range(c.get_num_materials())],**C.fingerprint(c)) for a in rows if a.get_actor_label()=='LidarStudy_Forest' or a.get_actor_label().startswith('LidarStudy_LevelDetail_') for c in a.get_components_by_class(u.InstancedStaticMeshComponent)},ground=[str(a.output_digest) for a in rows if isinstance(a,u.GTProceduralGround)],fog={k:f.get_editor_property(k) for k in ['fog_density','fog_height_falloff','start_distance','fog_max_opacity']})

def validate():
 assert state()==json.loads((QA/'protected.json').read_text())
 a=next(a for a in C.actors.get_all_level_actors() if a.get_actor_label()==LABEL)
 assert a.unbound and a.enabled and a.blend_weight==1
 b=list(a.settings.weighted_blendables.array);assert len(b)==1 and b[0].object==u.load_asset(DEST+'/M_FarHaze') and b[0].weight==1
 return dict(protected_packages=C.validate_protected(),planting_terrain_canopy_materials_and_existing_fog_unchanged=True)

def main():
 stage=os.environ.get('GT_FAR_HAZE_STAGE','install');report=dict(ok=False,stage=stage);control=dict(busy=False,deadline=0)
 def run():
  assert les.load_level(C.BASE+'/L_LidarStudy');yield 2
  settings=json.loads(A.CONFIG.read_text())['far_haze']
  if stage=='install':
   if not (QA/'protected.json').exists():(QA/'protected.json').write_text(json.dumps(state(),indent=2))
   build(settings);apply(settings);report.update(validate());assert les.save_current_level();report['saved']=True
  else:report.update(validate());report['saved_reload']=True
  report.update(ok=True,settings=settings);yield 1
 steps=run()
 def tick(dt):
  if control['busy'] or time.monotonic()<control['deadline']:return
  control['busy']=True
  try:control['deadline']=time.monotonic()+float(next(steps))
  except StopIteration:
   (QA/(stage+'.json')).write_text(json.dumps(report,indent=2));u.unregister_slate_post_tick_callback(control['handle']);u.SystemLibrary.quit_editor()
  except Exception:
   report.update(ok=False,error=traceback.format_exc());(QA/(stage+'.json')).write_text(json.dumps(report,indent=2));u.log_error(report['error']);u.unregister_slate_post_tick_callback(control['handle']);u.SystemLibrary.quit_editor()
  finally:control['busy']=False
 u.EditorPythonScripting.set_keep_python_script_alive(True);control['handle']=u.register_slate_post_tick_callback(tick)

if __name__=='__main__':main()
