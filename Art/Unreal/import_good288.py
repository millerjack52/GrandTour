"""Replacement Ferrari: isolated skeletal import and drivable project test map."""
import unreal as u,json,hashlib,traceback
from pathlib import Path
ROOT=Path(u.Paths.project_dir()).resolve();OUT=ROOT/'Art/Export/VehicleTools/ferrari288-good-game-v01'
DEST='/Game/GrandTour/Vehicles/Ferrari288Good';MAP='/Game/GrandTour/Test/Ferrari288/L_Ferrari288_Test'
E=u.EditorAssetLibrary;A=u.AssetToolsHelpers.get_asset_tools();M=u.MaterialEditingLibrary;S=u.get_editor_subsystem(u.SkeletalMeshEditorSubsystem);V=u.GTVehicleSetupLibrary;LES=u.get_editor_subsystem(u.LevelEditorSubsystem)
report={'ok':False,'level':MAP}
def prop(o,**kw):
 for k,v in kw.items():o.set_editor_property(k,v)
 return o
def save(o):assert E.save_loaded_asset(o,False)
def bp(name,parent):
 asset=E.load_asset(DEST+'/'+name) if E.does_asset_exist(DEST+'/'+name) else A.create_asset(name,DEST,u.Blueprint,prop(u.BlueprintFactory(),parent_class=parent))
 u.BlueprintEditorLibrary.compile_blueprint(asset);return asset
def material(name):
 m=E.load_asset(DEST+'/Materials/M_'+name) if E.does_asset_exist(DEST+'/Materials/M_'+name) else A.create_asset('M_'+name,DEST+'/Materials',u.Material,u.MaterialFactoryNew())
 M.delete_all_material_expressions(m);M.set_base_material_usage(m,u.MaterialUsage.MATUSAGE_SKELETAL_MESH,True);return m
def scalar(m,val,pin):
 n=prop(M.create_material_expression(m,u.MaterialExpressionConstant),r=val);assert M.connect_material_property(n,'',pin)
try:
 data=json.loads((OUT/'export-report.json').read_text());build=json.loads((OUT/'build-report.json').read_text())
 assert hashlib.sha256(Path(data['source']).read_bytes()).hexdigest()==data['source_sha256']
 world=u.get_editor_subsystem(u.UnrealEditorSubsystem).get_editor_world();u.SystemLibrary.execute_console_command(world,'Interchange.FeatureFlags.Import.FBX 0')
 task=prop(u.AssetImportTask(),filename=str(OUT/'SK_Ferrari288.fbx'),destination_path=DEST,automated=True,replace_existing=True,save=False)
 ui=prop(u.FbxImportUI(),import_mesh=True,import_as_skeletal=True,import_animations=False,import_materials=False,import_textures=False,create_physics_asset=True,mesh_type_to_import=u.FBXImportType.FBXIT_SKELETAL_MESH)
 prop(ui.skeletal_mesh_import_data,import_uniform_scale=1.,convert_scene=True,force_front_x_axis=False,convert_scene_unit=True,import_morph_targets=False,normal_import_method=u.FBXNormalImportMethod.FBXNIM_IMPORT_NORMALS)
 task.options=ui;A.import_asset_tasks([task]);sk=E.load_asset(DEST+'/SK_Ferrari288');assert sk
 for lod in [1,2]:assert S.import_lod(sk,lod,str(OUT/f'SK_Ferrari288_LOD{lod}.fbx'))==lod
 mats={}
 for name in ['Source','Palette']:
  task=prop(u.AssetImportTask(),filename=str(OUT/f'T_F288_{name}.png'),destination_path=DEST+'/Textures',automated=True,replace_existing=True,save=False);A.import_asset_tasks([task]);tex=E.load_asset(DEST+f'/Textures/T_F288_{name}');assert tex
  prop(tex,srgb=True);save(tex);m=material('F288_'+name)
  n=prop(M.create_material_expression(m,u.MaterialExpressionTextureSample),texture=tex,sampler_type=u.MaterialSamplerType.SAMPLERTYPE_COLOR);assert M.connect_material_property(n,'RGB',u.MaterialProperty.MP_BASE_COLOR)
  scalar(m,.5 if name=='Source' else .7,u.MaterialProperty.MP_ROUGHNESS);scalar(m,.05,u.MaterialProperty.MP_METALLIC);M.recompile_material(m);save(m);mats['F288_'+name]=m
 g=material('F288_Glass');prop(g,blend_mode=u.BlendMode.BLEND_TRANSLUCENT,two_sided=True,translucency_lighting_mode=u.TranslucencyLightingMode.TLM_SURFACE_PER_PIXEL_LIGHTING)
 n=prop(M.create_material_expression(g,u.MaterialExpressionConstant3Vector),constant=u.LinearColor(.72,.84,.9,1));assert M.connect_material_property(n,'',u.MaterialProperty.MP_BASE_COLOR)
 scalar(g,.09,u.MaterialProperty.MP_OPACITY);scalar(g,.06,u.MaterialProperty.MP_ROUGHNESS);scalar(g,.45,u.MaterialProperty.MP_SPECULAR);M.recompile_material(g);save(g);mats['F288_Glass']=g
 slots=list(sk.get_editor_property('materials'))
 for slot in slots:
  name=str(slot.get_editor_property('imported_material_slot_name'));assert name in mats,name;slot.material_interface=mats[name]
 sk.set_editor_property('materials',slots);pa=sk.get_editor_property('physics_asset') or S.create_physics_asset(sk,True,0)
 for n in data['bones']:
  if n!='Root':V.remove_bodies_by_bone_prefix(pa,n)
 assert V.set_compound_box_body(pa,sk,'Root',[u.Vector(0,0,85),u.Vector(-5,0,133)],[u.Vector(414,162,93),u.Vector(159,125,64)])
 V.enable_hit_events(pa)
 for o in [pa,sk,sk.get_editor_property('skeleton')]:save(o)
 wheels=[]
 for axle,tag,parent in [('Front','FL',u.GTVehicleWheelFront),('Rear','RL',u.GTVehicleWheelRear)]:
  asset=bp('BP_Ferrari288_Wheel'+axle,parent);w=u.get_default_object(asset.generated_class());d=build['wheels'][tag]
  prop(w,wheel_radius=d['radius']*450,wheel_width=d['width']*450,wheel_mass=23.,suspension_max_raise=4.,suspension_max_drop=6.,spring_rate=380.,suspension_damping_ratio=.7,max_brake_torque=1400.,max_steer_angle=25. if axle=='Front' else 0.)
  save(asset);wheels.append(asset.generated_class())
 asset=bp('BP_Ferrari288',u.GTCarPawn);pawn=u.get_default_object(asset.generated_class());mesh=pawn.get_component_by_class(u.SkeletalMeshComponent);mesh.set_skeletal_mesh_asset(sk);mesh.set_anim_instance_class(u.GTVehicleAnimInstance)
 prop(pawn,driver_eye_offset=u.Vector(-4.5,-37.35,142.65),enter_needs_open_door=False,chase_arm_length=760.,chase_pivot_height=130.)
 for camera in pawn.get_components_by_class(u.CameraComponent):
  if camera.get_name()=='DriverCamera':camera.set_field_of_view(95.)
 prop(pawn.get_body(),panel_folder=DEST,panel_prefix='NO_LEGACY_PANELS_',paint_folder=DEST,build_windscreen=False)
 prop(pawn.get_dashboard(),build_greybox=False);prop(pawn.get_component_by_class(u.GTPartSlotsComponent),show_greybox_visuals=False)
 move=pawn.get_chaos_movement();prop(move,mass=1350.,chassis_width=195.,chassis_height=150.,center_of_mass_override=u.Vector(-12,0,69))
 setups=list(move.get_editor_property('wheel_setups'))
 for i,s in enumerate(setups):s.set_editor_property('wheel_class',wheels[0 if i<2 else 1])
 move.set_editor_property('wheel_setups',setups);engine=move.get_editor_property('engine_setup');engine.set_editor_property('max_torque',320.);move.set_editor_property('engine_setup',engine)
 prop(pawn.get_drivetrain(),centre_split_front=.4,low_range_ratio=2.,centre_lock_when_on=1.);save(asset)
 gm=bp('BP_Ferrari288_TestGameMode',u.GTRunGameMode);prop(u.get_default_object(gm.generated_class()),default_pawn_class=asset.generated_class());save(gm)
 if not E.does_asset_exist(MAP):assert LES.new_level_from_template(MAP,'/Game/GrandTour/Test/L_TestTrack')
 assert LES.load_level(MAP);world=u.get_editor_subsystem(u.UnrealEditorSubsystem).get_editor_world();world.get_world_settings().set_editor_property('default_game_mode',gm.generated_class())
 actors=u.get_editor_subsystem(u.EditorActorSubsystem).get_all_level_actors();starts=[a for a in actors if isinstance(a,u.PlayerStart)];assert len(starts)==1;start=starts[0].get_actor_location()
 V.destroy_actors_with_label_prefix(world,'F288_Test_');preview=V.spawn_actor_of_class(world,u.SkeletalMeshActor,u.Transform(start+u.Vector(0,-650,-start.z),u.Rotator(),u.Vector(1,1,1)),'F288_Test_ParkedReview');c=preview.get_component_by_class(u.SkeletalMeshComponent);c.set_skeletal_mesh_asset(sk);c.set_collision_enabled(u.CollisionEnabled.NO_COLLISION)
 position=start+u.Vector(850,-1350,400);target=start+u.Vector(0,-500,90);u.get_editor_subsystem(u.UnrealEditorSubsystem).set_level_viewport_camera_info(position,u.MathLibrary.find_look_at_rotation(position,target));assert LES.save_current_level()
 bones={}
 for n,expected in data['bones'].items():
  p=c.get_socket_transform(n,u.RelativeTransformSpace.RTS_COMPONENT).translation;got=[p.x,p.y,p.z];assert max(abs(got[i]-expected[i]) for i in range(3))<.15,(n,got,expected);bones[n]=got
 bounds=sk.get_bounds();dims=[bounds.box_extent.x*2,bounds.box_extent.y*2,bounds.box_extent.z*2];expected=[data['bounds_cm'][1][i]-data['bounds_cm'][0][i] for i in range(3)];assert max(abs(a-b) for a,b in zip(dims,expected))<.2,(dims,expected)
 assert LES.load_level('/Engine/Maps/Entry');assert LES.load_level(MAP)
 report.update(ok=True,status='IMPORTED_RUNTIME_PENDING',mesh=sk.get_path_name(),pawn=asset.get_path_name(),bones_cm=bones,dimensions_cm=dims,lod_count=S.get_lod_count(sk),materials=len(slots),physics_bodies=[str(x) for x in V.describe_bodies(pa)],limits=build['limits'])
except Exception:report['error']=traceback.format_exc();u.log_error(report['error']);raise
finally:(OUT/'unreal-import-report.json').write_text(json.dumps(report,indent=2))
