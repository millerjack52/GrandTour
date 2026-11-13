"""Import the three latest modelling studies as modular static Blueprint actors.

Run with the editor closed via UnrealEditor-Cmd -run=pythonscript.
Only owns /Game/GrandTour/Vehicles/ModelStudies and its dedicated review map.
"""
import unreal as u, json, traceback, hashlib
from pathlib import Path
ROOT=Path(u.Paths.project_dir()).resolve()
SRC=ROOT/'Art/Export/VehicleTools/new-cars-unreal-v01'
DEST='/Game/GrandTour/Vehicles/ModelStudies'
MAP='/Game/GrandTour/ArtTests/NewCars/L_NewCarsReview'
CARS=['CraftedUtility','Pathfinder2002','Impreza2003']
E=u.EditorAssetLibrary; A=u.AssetToolsHelpers.get_asset_tools(); M=u.MaterialEditingLibrary
SE=u.get_editor_subsystem(u.StaticMeshEditorSubsystem)
V=u.GTVehicleSetupLibrary
report=dict(status='STARTED',review_level=MAP,cars=[],limitations=['Static art review actors; no Chaos driving, gameplay selection or door animation hooked up.','Full detail geometry retained; no production LOD or material-atlas optimisation.','Body box collision is for placement and simple queries, not vehicle physics.'])
def prop(o,**kw):
 for k,v in kw.items():o.set_editor_property(k,v)
 return o
def material(name,folder,s):
 path=folder+'/'+name
 m=E.load_asset(path) if E.does_asset_exist(path) else A.create_asset(name,folder,u.Material,u.MaterialFactoryNew())
 M.delete_all_material_expressions(m)
 def scalar(value,target):
  n=prop(M.create_material_expression(m,u.MaterialExpressionConstant),r=value)
  assert M.connect_material_property(n,'',target)
 def color(value,target):
  n=prop(M.create_material_expression(m,u.MaterialExpressionConstant3Vector),constant=u.LinearColor(*value[:3],1))
  assert M.connect_material_property(n,'',target)
 glass=s.get('transmission',0)>.05 or ('glass' in s.get('source','').lower() and 'mirror' not in s.get('source','').lower())
 prop(m,two_sided=glass,blend_mode=u.BlendMode.BLEND_TRANSLUCENT if glass else u.BlendMode.BLEND_OPAQUE)
 if glass:
  prop(m,translucency_lighting_mode=u.TranslucencyLightingMode.TLM_SURFACE_PER_PIXEL_LIGHTING)
  scalar(.22 if 'lens' not in s.get('source','').lower() else .32,u.MaterialProperty.MP_OPACITY)
 color(s['base_color'],u.MaterialProperty.MP_BASE_COLOR)
 scalar(max(.12,s.get('roughness',.5)),u.MaterialProperty.MP_ROUGHNESS)
 scalar(s.get('metallic',0),u.MaterialProperty.MP_METALLIC)
 scalar(s.get('specular',.5),u.MaterialProperty.MP_SPECULAR)
 if s.get('emission_strength',0)>0:color([x*s['emission_strength'] for x in s['emission']],u.MaterialProperty.MP_EMISSIVE_COLOR)
 errors=M.recompile_material(m);assert not errors,(name,errors)
 assert E.save_loaded_asset(m)
 return m
def import_car(car):
 manifest=json.loads((SRC/car/'manifest.json').read_text())
 assert hashlib.sha256(Path(manifest['source']).read_bytes()).hexdigest()==manifest['source_sha256'],'Source changed since export'
 folder=DEST+'/'+car
 mats={k:material(k,folder+'/Materials',v) for k,v in manifest['materials'].items()}
 meshes={}; checks=[]
 for part in manifest['parts']:
  assert hashlib.sha256(Path(part['file']).read_bytes()).hexdigest()==part['sha256']
  name=part['name']
  task=prop(u.AssetImportTask(),filename=part['file'],destination_path=folder+'/Meshes',destination_name=name,automated=True,replace_existing=True,save=False)
  ui=prop(u.FbxImportUI(),import_mesh=True,import_as_skeletal=False,import_animations=False,import_materials=False,import_textures=False,mesh_type_to_import=u.FBXImportType.FBXIT_STATIC_MESH)
  prop(ui.static_mesh_import_data,combine_meshes=True,auto_generate_collision=False,generate_lightmap_u_vs=False,import_uniform_scale=1.,convert_scene=True,force_front_x_axis=False,convert_scene_unit=True,normal_import_method=u.FBXNormalImportMethod.FBXNIM_IMPORT_NORMALS,remove_degenerates=False)
  task.options=ui;A.import_asset_tasks([task])
  mesh=E.load_asset(folder+'/Meshes/'+name);assert isinstance(mesh,u.StaticMesh),name
  slots=list(mesh.get_editor_property('static_materials'));slot_check=[]
  for slot in slots:
   key=str(slot.get_editor_property('imported_material_slot_name'))
   assert key in mats,(name,key,list(mats))
   slot.material_interface=mats[key];slot_check.append(key)
  mesh.set_editor_property('static_materials',slots)
  SE.remove_collisions(mesh)
  if part['group']=='Body':SE.add_simple_collisions(mesh,u.ScriptingCollisionShapeType.BOX)
  b=mesh.get_bounds();origin=b.origin;extent=b.box_extent
  actual=[[origin.x-extent.x,origin.y-extent.y,origin.z-extent.z],[origin.x+extent.x,origin.y+extent.y,origin.z+extent.z]]
  error=max(abs(actual[j][i]-part['bounds_local_cm'][j][i]) for i in range(3) for j in range(2))
  assert error<.15,(name,'FBX bounds mismatch',error,actual,part['bounds_local_cm'])
  E.set_metadata_tag(mesh,'GT.SourceBlend',manifest['source'])
  E.set_metadata_tag(mesh,'GT.SourceHash',manifest['source_sha256'])
  E.set_metadata_tag(mesh,'GT.ImportScope','Static review; preserves source detail')
  assert E.save_loaded_asset(mesh)
  meshes[name]=mesh
  checks.append(dict(mesh=mesh.get_path_name(),bounds_error_cm=error,material_slots=slot_check,source_triangles=part['triangles']))
 # Blueprint components retain their exported local pivots and placement offsets.
 bpname='BP_'+car+'_Review';bppath=folder+'/'+bpname
 if E.does_asset_exist(bppath):bp=E.load_asset(bppath)
 else:bp=A.create_asset(bpname,folder,u.Blueprint,prop(u.BlueprintFactory(),parent_class=u.Actor))
 assert bp
 sub=u.get_engine_subsystem(u.SubobjectDataSubsystem);lib=u.SubobjectDataBlueprintFunctionLibrary
 handles=sub.k2_gather_subobject_data_for_blueprint(bp)
 root=handles[0]
 existing={}
 for h in handles:
  obj=lib.get_object(lib.get_data(h))
  if isinstance(obj,u.StaticMeshComponent):existing[obj.get_name().replace('_GEN_VARIABLE','')]=(h,obj)
 for part in manifest['parts']:
  component_name='Part_'+part['group']
  if component_name in existing:h,c=existing[component_name]
  else:
   h,fail=sub.add_new_subobject(u.AddNewSubobjectParams(parent_handle=root,new_class=u.StaticMeshComponent,blueprint_context=bp))
   assert not str(fail),(part['name'],str(fail))
   assert sub.rename_subobject(h,u.Text(component_name))
   c=lib.get_object(lib.get_data(h))
  assert isinstance(c,u.StaticMeshComponent)
  c.set_static_mesh(meshes[part['name']])
  c.set_editor_property('relative_location',u.Vector(*part['pivot_cm']))
  c.set_editor_property('mobility',u.ComponentMobility.MOVABLE)
  c.set_collision_enabled(u.CollisionEnabled.QUERY_ONLY if part['group']=='Body' else u.CollisionEnabled.NO_COLLISION)
  c.set_editor_property('cast_shadow',True)
 u.BlueprintEditorLibrary.compile_blueprint(bp)
 assert E.save_loaded_asset(bp)
 return manifest,bp,dict(car=car,blueprint=bppath,triangles=manifest['triangles'],parts=len(manifest['parts']),checks=checks)
def spawn(world,cls,label,pos=(0,0,0),rot=(0,0,0)):
 a=V.spawn_actor_of_class(world,cls,u.Transform(u.Vector(*pos),u.Rotator(*rot),u.Vector(1,1,1)),label)
 assert a,label
 return a
try:
 world=u.get_editor_subsystem(u.UnrealEditorSubsystem).get_editor_world()
 u.SystemLibrary.execute_console_command(world,'Interchange.FeatureFlags.Import.FBX 0')
 cars=[]
 for car in CARS:
  manifest,bp,result=import_car(car);cars.append((manifest,bp));report['cars'].append(result)
  u.log('NEW_CARS_IMPORTED '+car)
 les=u.get_editor_subsystem(u.LevelEditorSubsystem)
 assert les.load_level(MAP) if E.does_asset_exist(MAP) else les.new_level(MAP)
 world=u.get_editor_subsystem(u.UnrealEditorSubsystem).get_editor_world()
 V.destroy_actors_with_label_prefix(world,'NC_')
 world.get_world_settings().set_editor_property('default_game_mode',u.GameModeBase)
 for i,(manifest,bp) in enumerate(cars):
  y=(i-1)*440
  z=-manifest['bounds_cm'][0][2]+1
  actor=spawn(world,bp.generated_class(),'NC_'+manifest['car'],pos=(0,y,z))
  components=actor.get_components_by_class(u.StaticMeshComponent)
  assert len(components)==len(manifest['parts']),(manifest['car'],'Missing Blueprint parts',len(components))
  for c in components:
   assert c.static_mesh and all(c.get_material(k) for k in range(c.get_num_materials()))
  report['cars'][i]['placed_components']=len(components)
  report['cars'][i]['placement_cm']=[0,y,z]
  for view,position,target in [('Front',(650,y-600,310),(0,y,95)),('Rear',(-640,y+610,290),(0,y,95)),('Side',(0,y-900,120),(0,y,120))]:
   camera=spawn(world,u.CameraActor,'NC_Camera_'+manifest['car']+'_'+view,pos=position)
   camera.set_actor_rotation(u.MathLibrary.find_look_at_rotation(u.Vector(*position),u.Vector(*target)),False)
   camera.camera_component.set_field_of_view(42)
 floor=V.spawn_static_mesh_actor(world,E.load_asset('/Engine/BasicShapes/Cube'),u.Transform(u.Vector(0,0,-10),u.Rotator(),u.Vector(200,200,.2)),'NC_Floor')
 floor.static_mesh_component.set_material(0,material('M_ReviewFloor',DEST+'/Shared',dict(base_color=[.16,.175,.19,1],roughness=.85)))
 sun=spawn(world,u.DirectionalLight,'NC_Key',pos=(0,0,800),rot=(-42,-35,0))
 dc=sun.get_component_by_class(u.DirectionalLightComponent);dc.set_intensity(4.)
 dc.set_editor_property('atmosphere_sun_light',True)
 sky=spawn(world,u.SkyLight,'NC_Sky',pos=(0,0,800))
 prop(sky.get_component_by_class(u.SkyLightComponent),real_time_capture=True,intensity=1.)
 spawn(world,u.SkyAtmosphere,'NC_Atmosphere')
 pp=spawn(world,u.PostProcessVolume,'NC_Exposure');prop(pp,unbound=True)
 settings=pp.get_editor_property('settings')
 prop(settings,override_auto_exposure_min_brightness=True,override_auto_exposure_max_brightness=True,auto_exposure_min_brightness=.25,auto_exposure_max_brightness=.25,override_motion_blur_amount=True,motion_blur_amount=0.)
 pp.set_editor_property('settings',settings)
 pos=u.Vector(1350,-1500,850);target=u.Vector(0,0,80)
 rot=u.MathLibrary.find_look_at_rotation(pos,target)
 overview=spawn(world,u.CameraActor,'NC_Camera_Overview',pos=(pos.x,pos.y,pos.z))
 overview.set_actor_rotation(rot,False);overview.camera_component.set_field_of_view(48)
 start=spawn(world,u.PlayerStart,'NC_PlayerStart',pos=(1350,-1500,850));start.set_actor_rotation(rot,False)
 u.get_editor_subsystem(u.UnrealEditorSubsystem).set_level_viewport_camera_info(pos,rot)
 assert les.save_current_level()
 assert les.load_level('/Engine/Maps/Entry')
 assert les.load_level(MAP)
 actors=u.get_editor_subsystem(u.EditorActorSubsystem).get_all_level_actors()
 for car in CARS:assert any(a.get_actor_label()=='NC_'+car for a in actors)
 report['status']='IMPORTED_AND_REOPENED'
 u.log('NEW_CARS_SUCCESS '+MAP)
except Exception:
 report['status']='FAILED';report['error']=traceback.format_exc();u.log_error(report['error']);raise
finally:(SRC/'unreal-import-report.json').write_text(json.dumps(report,indent=2))
