"""Map-owned first painterly material pass. Original assets remain available."""
import unreal as u,sys,time,json,traceback
from pathlib import Path
ROOT=Path(u.Paths.project_dir()).resolve();OUT=ROOT/'Art/Export/BenmorePainterly'
DEST='/Game/GrandTour/Demo/BenmoreRoads/Painterly';LEVEL='/Game/GrandTour/Demo/BenmoreRoads/L_Benmore_Drive'
sys.path.insert(0,str(ROOT/'Art/Unreal'))
import benmore_painterly_surface as paint
eal=u.EditorAssetLibrary;mel=u.MaterialEditingLibrary;assets=u.AssetToolsHelpers.get_asset_tools()
les=u.get_editor_subsystem(u.LevelEditorSubsystem);act=u.get_editor_subsystem(u.EditorActorSubsystem)
phase='load';last=time.monotonic();report={'ok':False};u.EditorPythonScripting.set_keep_python_script_alive(True)

def props(o,**values):
 for k,v in values.items():o.set_editor_property(k,v)
 return o

def clone(path,name):
 dest=DEST+'/'+name
 return u.load_asset(dest) if eal.does_asset_exist(dest) else eal.duplicate_asset(path,dest)

def custom(m,names,code,typ=u.CustomMaterialOutputType.CMOT_FLOAT3):
 return props(mel.create_material_expression(m,u.MaterialExpressionCustom),inputs=[props(u.CustomInput(),input_name=n) for n in names],code=code,output_type=typ,desc='BenmorePainterly')

def wire(a,b,pin,out=''):assert mel.connect_material_expressions(a,out,b,pin)

def solid_material(name,code,foliage=False):
 m=u.load_asset(DEST+'/'+name) if eal.does_asset_exist(DEST+'/'+name) else assets.create_asset(name,DEST,u.Material,u.MaterialFactoryNew())
 mel.delete_all_material_expressions(m)
 if foliage:props(m,two_sided=True,shading_model=u.MaterialShadingModel.MSM_TWO_SIDED_FOLIAGE)
 for usage in [u.MaterialUsage.MATUSAGE_INSTANCED_STATIC_MESHES,u.MaterialUsage.MATUSAGE_NANITE]:mel.set_base_material_usage(m,usage,True)
 p=mel.create_material_expression(m,u.MaterialExpressionWorldPosition)
 col=custom(m,['P','Base'] if foliage else ['P','Camera'],code);wire(p,col,'P')
 source=mel.create_material_expression(m,u.MaterialExpressionVertexColor if foliage else u.MaterialExpressionCameraPositionWS)
 wire(source,col,'Base' if foliage else 'Camera')
 assert mel.connect_material_property(col,'',u.MaterialProperty.MP_BASE_COLOR)
 if foliage:assert mel.connect_material_property(col,'',u.MaterialProperty.MP_SUBSURFACE_COLOR)
 for prop,val in [(u.MaterialProperty.MP_ROUGHNESS,.94),(u.MaterialProperty.MP_SPECULAR,.10)]:
  node=props(mel.create_material_expression(m,u.MaterialExpressionConstant),r=val);mel.connect_material_property(node,'',prop)
 assert not mel.recompile_material(m);assert eal.save_loaded_asset(m);return m

def recolour_terrain(m):
 nodes=list(mel.get_material_expressions(m));found=0
 for n in nodes:
  if not isinstance(n,u.MaterialExpressionCustom):continue
  inputs=[str(x.get_editor_property('input_name')) for x in n.get_editor_property('inputs')]
  if 'CoverDetail' in inputs:n.set_editor_property('code',paint.COLOR);found+=1
  if inputs==['P','HillNormal']:
   n.set_editor_property('code',paint.HILL_NORMAL)
  if 'FineNormal' in inputs:
   code=n.get_editor_property('code').replace('(fineN-coarseN)*amount','(fineN-coarseN)*(amount*.5)')
   n.set_editor_property('code',code)
 # Older copies can retain multiple colour expressions with this interface.
 # Give each the same palette, regardless of which one supplies the output.
 assert found>=1,(m.get_name(),found)

def configure_grass(m,foliage):
 nodes=list(mel.get_material_expressions(m));gout=next(n for n in nodes if isinstance(n,u.MaterialExpressionLandscapeGrassOutput))
 entries=list(gout.get_editor_property('grass_types'));types=[]
 for entry in entries:
  original=entry.get_editor_property('grass_type');name=str(entry.get_editor_property('name'))
  grass=clone(original.get_path_name(),'LGT_Painterly_'+name);varieties=list(grass.get_editor_property('grass_varieties'))
  for variety in varieties:variety.set_editor_property('override_materials',[foliage])
  grass.set_editor_property('grass_varieties',varieties);assert eal.save_loaded_asset(grass)
  entry.set_editor_property('grass_type',grass);types.append(grass.get_path_name())
 gout.set_editor_property('grass_types',entries)
 # Treat grass type assignment and output wiring as one operation.
 # Always reconnect every output, including on a second run. Keep the proven
 # site-wide vegetation masks; palette changes do not require new grass masks.
 mask=next(n for n in nodes if isinstance(n,u.MaterialExpressionTextureSample) and n.get_editor_property('texture') and n.get_editor_property('texture').get_name()=='T_Benmore_VegetationMask')
 for entry in entries:
  name=str(entry.get_editor_property('name'));channel='R' if name=='LowGrass' else ('B' if name=='TallClumps' else 'G')
  wire(mask,gout,name,channel)
 return types

def tick(dt):
 global phase,last
 try:
  if phase=='load':
   phase='building';assert les.load_level(LEVEL);eal.make_directory(DEST)
   world=u.get_editor_subsystem(u.UnrealEditorSubsystem).get_editor_world()
   backup='/Game/GrandTour/Demo/BenmoreRoads/L_Benmore_BeforePainterly'
   if not eal.does_asset_exist(backup):assert u.EditorLoadingAndSavingUtils.save_map(world,backup)
   foliage=solid_material('M_Painterly_Tussock',paint.FOLIAGE,True);rock=solid_material('M_Painterly_Schist',paint.ROCK)
   ground=clone('/Game/GrandTour/Demo/BenmoreRoads/Vegetation/M_Benmore_FullCover','M_Painterly_Terrain');recolour_terrain(ground)
   report['grass_types']=configure_grass(ground,foliage);assert not mel.recompile_material(ground);assert eal.save_loaded_asset(ground)
   backdrop=clone('/Game/GrandTour/Demo/BenmoreRoads/Environment/M_Benmore_Backdrop','M_Painterly_Hills');recolour_terrain(backdrop);assert not mel.recompile_material(backdrop);assert eal.save_loaded_asset(backdrop)
   lake=clone('/Game/GrandTour/Demo/BenmoreRoads/Vistas/M_Benmore_VistaLake','M_Painterly_Lake')
   for n in mel.get_material_expressions(lake):
    if isinstance(n,u.MaterialExpressionCustom) and 'float wide=' in n.get_editor_property('code'):
     n.set_editor_property('code','float wide=.5+.5*sin(P.x*.00012+P.y*.00019);return lerp(float3(.012,.085,.145),float3(.040,.22,.245),saturate(Shore*.65))*lerp(.98,1.02,wide);')
   assert not mel.recompile_material(lake);assert eal.save_loaded_asset(lake)
   changed={'landscapes':0,'hills':0,'rocks':0,'verge_grass_components':0}
   actors=act.get_all_level_actors()
   for a in actors:
    if isinstance(a,u.LandscapeProxy):a.set_editor_property('landscape_material',ground);changed['landscapes']+=1
    for c in a.get_components_by_class(u.StaticMeshComponent):
     mesh=c.get_editor_property('static_mesh')
     if not mesh:continue
     name=mesh.get_name()
     if a.get_actor_label().startswith('Benmore_Hills_'):c.set_material(0,backdrop);changed['hills']+=1
     elif name.startswith('SM_Benmore_Rock'):c.set_material(0,rock);changed['rocks']+=1
     elif name in ['SM_TS_Straw','SM_TS_Rust','SM_TS_Weathered','SM_TS_Fine']:c.set_material(0,foliage);changed['verge_grass_components']+=1
     elif a.get_actor_label()=='Benmore_Vista_Lake':c.set_material(0,lake)
   assert changed['hills']==4 and changed['rocks']>0 and changed['landscapes']>0,changed
   pp=next(a for a in actors if a.get_actor_label()=='Benmore_Daylight_Grade');settings=pp.get_editor_property('settings')
   values={'auto_exposure_min_brightness':13.3,'auto_exposure_max_brightness':13.3,'color_saturation':u.Vector4(1,1,1,1.02),'color_contrast':u.Vector4(1,1,1,1.0),'color_gain_shadows':u.Vector4(.96,1.01,1.10,1),'color_offset_shadows':u.Vector4(.002,.004,.009,0)}
   for k,v in values.items():settings.set_editor_property('override_'+k,True);settings.set_editor_property(k,v)
   pp.set_editor_property('settings',settings)
   sky=next(a for a in actors if isinstance(a,u.SkyLight) and a.get_actor_label()=='Sky');sky.get_component_by_class(u.SkyLightComponent).set_intensity(1.3)
   report.update(assignments=changed,exposure_ev100=13.3,skylight_intensity=1.3,height_changed=False,road_geometry_changed=False,original_meshes_preserved=True)
   u.SystemLibrary.execute_console_command(world,'grass.FlushCache');phase='warm';last=time.monotonic()
  elif phase=='warm' and time.monotonic()-last>30:
   phase='saving';assert les.save_current_level();report['ok']=True;(OUT/'setup-report.json').write_text(json.dumps(report,indent=2))
   u.unregister_slate_post_tick_callback(handle)
   p=ROOT/'Art/Unreal/check_benmore_painterly.py';exec(compile(p.read_text(),str(p),'exec'),{'__file__':str(p)})
 except Exception:
  phase='error';report['error']=traceback.format_exc();(OUT/'setup-report.json').write_text(json.dumps(report,indent=2));u.log_error(report['error']);u.unregister_slate_post_tick_callback(handle);u.SystemLibrary.quit_editor()
handle=u.register_slate_post_tick_callback(tick)
