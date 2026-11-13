"""HS1: install photo-led buildings at the surveyed house clearing, without rebuilding terrain."""
from pathlib import Path
import unreal as u
import sys,json,math,time,traceback,os,shutil,gc,hashlib,re
ROOT=Path(u.Paths.project_dir()).resolve();sys.path.insert(0,str(ROOT/'Art/Unreal'))
OUT=ROOT/'Art/Export/LidarStudy/Homestead';QA=ROOT/'Saved/LidarAuthoringQA/HS1';QA.mkdir(parents=True,exist_ok=True)
BASE='/Game/GrandTour/ArtTests/LidarStudy';DEST=BASE+'/Homestead'
SITE=json.loads((ROOT/'Art/References/Homestead/site-layout.json').read_text())
ANCHOR=tuple(SITE['anchor_cm']);YAW=float(SITE['yaw'])
GARAGE=tuple(SITE['garage_local_cm'])
E=u.EditorAssetLibrary;M=u.MaterialEditingLibrary
def xy(x,y):
 x=-x  # authored right becomes the viewer's right in Unreal's left-handed frame
 a=math.radians(YAW);return ANCHOR[0]+x*math.cos(a)-y*math.sin(a),ANCHOR[1]+x*math.sin(a)+y*math.cos(a)
def props(o,**kw):
 for k,v in kw.items():o.set_editor_property(k,v)
 return o
def clears_vegetation(wx,wy):
 """Shared arrival-court footprint for installation and saved-map validation."""
 dx=wx-ANCHOR[0];dy=wy-ANCHOR[1]
 if abs(dx)>4000 or abs(dy)>4000:return False
 angle=math.radians(-YAW)
 x=-(dx*math.cos(angle)-dy*math.sin(angle));y=dx*math.sin(angle)+dy*math.cos(angle)
 return (-900<x<900 and -1000<y<650) or (GARAGE[0]-500<x<GARAGE[0]+600 and GARAGE[1]-1700<y<GARAGE[1]+500) or ((x-300)/1900)**2+((y+1800)/1700)**2<1
def survey():
 from lidar_grounding import GroundSampler
 refs=u.get_editor_subsystem(u.EditorActorSubsystem).get_all_level_actors();g=next(a for a in refs if isinstance(a,u.GTProceduralGround));sampler=GroundSampler(g)
 # Local 1m samples cover foundations and feathered apron; all are final relief heights.
 heights=[[sampler.height(*xy(x,y)) for x in range(-2400,2401,100)] for y in range(-4400,1601,100)]
 r=dict(ok=True,anchor_cm=ANCHOR,yaw=YAW,mirror_x=True,garage_local_cm=GARAGE,grid_origin=[-2400,-4400],step_cm=100,heights_cm=heights,ground_digest=str(g.output_digest))
 (OUT/'ground-survey.json').write_text(json.dumps(r));return r
def material():
 mat=u.load_asset(DEST+'/M_Homestead')
 if not mat:mat=u.AssetToolsHelpers.get_asset_tools().create_asset('M_Homestead',DEST,u.Material,u.MaterialFactoryNew())
 nodes=M.get_material_expressions(mat);v=next((n for n in nodes if isinstance(n,u.MaterialExpressionVertexColor)),None)
 if not v:v=M.create_material_expression(mat,u.MaterialExpressionVertexColor)
 assert M.connect_material_property(v,'',u.MaterialProperty.MP_BASE_COLOR)
 # Vertex alpha stores surface finish: rough timber, quieter metal and glass.
 rough=M.get_material_property_input_node(mat,u.MaterialProperty.MP_ROUGHNESS)
 if not isinstance(rough,u.MaterialExpressionLinearInterpolate):rough=M.create_material_expression(mat,u.MaterialExpressionLinearInterpolate)
 rough.set_editor_property('const_a',.25);rough.set_editor_property('const_b',.82)
 assert M.connect_material_expressions(v,'A',rough,'Alpha')
 assert M.connect_material_property(rough,'',u.MaterialProperty.MP_ROUGHNESS)
 for prop,value in [(u.MaterialProperty.MP_SPECULAR,.22)]:
  n=M.get_material_property_input_node(mat,prop)
  if not isinstance(n,u.MaterialExpressionConstant):n=M.create_material_expression(mat,u.MaterialExpressionConstant)
  n.r=value;assert M.connect_material_property(n,'',prop)
 M.recompile_material(mat);E.save_loaded_asset(mat);return mat
def ground_material(name,lawn=False):
 mat=u.load_asset(DEST+'/'+name)
 if mat and E.get_metadata_tag(mat,'HS1Ready')=='4':return mat
 if not mat:mat=u.AssetToolsHelpers.get_asset_tools().create_asset(name,DEST,u.Material,u.MaterialFactoryNew())
 else:M.delete_all_material_expressions(mat)
 p=M.create_material_expression(mat,u.MaterialExpressionWorldPosition)
 uv=props(M.create_material_expression(mat,u.MaterialExpressionCustom),code='return P.xy / 140.;',output_type=u.CustomMaterialOutputType.CMOT_FLOAT2,inputs=[props(u.CustomInput(),input_name='P')]);assert M.connect_material_expressions(p,'',uv,'P')
 col=props(M.create_material_expression(mat,u.MaterialExpressionCustom),code='float3 turf=float3(.19,.255,.105)*clamp(1+(dot(Lawn,float3(.2126,.7152,.0722))/.1864-1)*.7,.5,1.5); return lerp(Stone*float3(.72,.76,.75),turf,saturate(Mask.r));',output_type=u.CustomMaterialOutputType.CMOT_FLOAT3,inputs=[props(u.CustomInput(),input_name=n) for n in ['Lawn','Stone','Mask']])
 for pin,path in [('Lawn','/Game/ANGRY_MESH/StylizedPack_MeadowEnvironment/Textures/Landscape/T_Landscape_Grass_01_A'),('Stone',BASE+'/T_gravel')]:
  tex=M.create_material_expression(mat,u.MaterialExpressionTextureSample);tex.texture=u.load_asset(path);assert tex.texture
  assert M.connect_material_expressions(uv,'',tex,'UVs')
  assert M.connect_material_expressions(tex,'RGB',col,pin)
 mask=M.create_material_expression(mat,u.MaterialExpressionVertexColor)
 assert M.connect_material_expressions(mask,'',col,'Mask')
 assert M.connect_material_property(col,'',u.MaterialProperty.MP_BASE_COLOR)
 rough=M.create_material_expression(mat,u.MaterialExpressionConstant);rough.r=.94;M.connect_material_property(rough,'',u.MaterialProperty.MP_ROUGHNESS)
 M.recompile_material(mat);E.set_metadata_tag(mat,'HS1Ready','4');E.save_loaded_asset(mat);return mat
def import_asset(name):
 digest=hashlib.sha256((OUT/(name+'.fbx')).read_bytes()+b'HS1mesh-v3').hexdigest()
 existing=u.load_asset(DEST+'/'+name)
 if existing and E.get_metadata_tag(existing,'HS1MeshKey')==digest:return existing
 task=props(u.AssetImportTask(),filename=str(OUT/(name+'.fbx')),destination_path=DEST,destination_name=name,automated=True,replace_existing=True,save=False)
 opt=props(u.FbxImportUI(),import_mesh=True,import_materials=False,import_textures=False,import_as_skeletal=False,mesh_type_to_import=u.FBXImportType.FBXIT_STATIC_MESH)
 props(opt.static_mesh_import_data,combine_meshes=True,auto_generate_collision=False,generate_lightmap_u_vs=False,vertex_color_import_option=u.VertexColorImportOption.REPLACE,normal_import_method=u.FBXNormalImportMethod.FBXNIM_IMPORT_NORMALS)
 task.options=opt;u.AssetToolsHelpers.get_asset_tools().import_asset_tasks([task]);mesh=u.load_asset(DEST+'/'+name);assert mesh,name
 if name=='SM_HomesteadGrade':
  for i,s in enumerate(mesh.static_materials):mesh.set_material(i,ground_material('M_HomesteadLawn' if 'Lawn' in str(s.material_slot_name) else 'M_HomesteadGravel','Lawn' in str(s.material_slot_name)))
  mesh.get_editor_property('body_setup').set_editor_property('collision_trace_flag',u.CollisionTraceFlag.CTF_USE_COMPLEX_AS_SIMPLE)
 else:mesh.set_material(0,material())
 sm=u.get_editor_subsystem(u.StaticMeshEditorSubsystem)
 opt=u.StaticMeshReductionOptions();opt.auto_compute_lod_screen_size=False;opt.reduction_settings=[u.StaticMeshReductionSettings(percent_triangles=1.,screen_size=1.),u.StaticMeshReductionSettings(percent_triangles=.42,screen_size=.12),u.StaticMeshReductionSettings(percent_triangles=.16,screen_size=.035)]
 if name!='SM_HomesteadGrade':sm.set_lods(mesh,opt)
 E.set_metadata_tag(mesh,'HS1MeshKey',digest);assert E.save_loaded_asset(mesh);return mesh
def roster():
 base='/Game/GrandTour/Vehicles/'
 specs=[('Range Rover Classic',None),('BMW E39 Touring','Bodies/E39Touring/BP_E39Touring'),('Opel Kadett A','Bodies/KadettA/BP_KadettA'),('Suzuki SJ413','Bodies/SJ413/BP_SJ413'),('Ferrari 288','Ferrari288Good/BP_Ferrari288'),('Graphic Adventure','GraphicAdventure/Rounded/BP_GraphicAdventure')]
 specs += [(title,'FleetDriving/'+key+'/BP_'+key+'_Fleet') for key,title in [('Panda1990','Fiat Panda 1990'),('Prado','Toyota Prado'),('LandCruiser80','Toyota Land Cruiser 80'),('Pathfinder2002','Nissan Pathfinder 2002'),('Impreza2003','Subaru Impreza 2003'),('CraftedUtility','Crafted Utility')]]
 rows=[]
 for title,path in specs:
  cls=u.load_class(None,'/Script/GrandTour.GTCarPawn') if not path else u.load_class(None,base+path+'.'+path.split('/')[-1]+'_C')
  assert cls,title
  rows.append(props(u.GTGarageVehicle(),name=title,vehicle_class=cls))
 return rows
def place():
 """Shared by focused installer and future full Place rebuilds."""
 layout=json.loads((OUT/'layout.json').read_text());act=u.get_editor_subsystem(u.EditorActorSubsystem)
 assert layout.get('placement_yaw')==YAW and layout.get('anchor_cm')==list(ANCHOR) and layout.get('garage_local_cm')==list(GARAGE),'Refresh homestead survey and Blender export for this placement before installing'
 for a in act.get_all_level_actors():
  if a.get_actor_label().startswith('LidarStudy_Homestead_'):act.destroy_actor(a)
 def spawn(cls,label,x,y,z):
  a=act.spawn_actor_from_class(cls,u.Vector(*xy(x,y),z),u.Rotator(yaw=YAW));a.set_actor_label('LidarStudy_Homestead_'+label);a.set_folder_path('LiDAR/Homestead');return a
 for name,x,y,z in [('SM_RiversideHouse',0,0,layout['house_datum_cm']),('SM_RiversideGarage',*GARAGE,layout['garage_floor_cm']),('SM_HomesteadGrade',0,0,0)]:
  a=spawn(u.StaticMeshActor,name,x,y,z);c=a.static_mesh_component;c.set_static_mesh(u.load_asset(DEST+'/'+name));c.set_collision_profile_name('BlockAll');c.set_mobility(u.ComponentMobility.STATIC)
 door=spawn(u.GTGarage,'GarageDoor',*layout['door_local_cm'],layout['garage_floor_cm']+105)
 door.set_editor_property('vehicles',roster());door.set_editor_property('vehicle_spawn_transform',u.Transform(location=u.Vector(*xy(*layout['bay_local_cm']),layout['bay_height_cm']+100),rotation=u.Rotator(yaw=YAW-90)))
 for route in act.get_all_level_actors():
  if not isinstance(route,u.GTMudRoute):continue
  match=re.search(r'(\d+)\s+(?:Riverside\s+)?[Hh]ouse',str(route.get_editor_property('checkpoint_labels')))
  if match:
   points=list(route.get_editor_property('recovery_points'));index=int(match.group(1))-1
   assert 0<=index<len(points)
   points[index]=door.vehicle_spawn_transform;route.set_editor_property('recovery_points',points)
 # Give the proxy its runtime dimensions in the editor too. Keep it just in front of the roller.
 door.get_component_by_class(u.StaticMeshComponent).set_relative_scale3d(u.Vector(1,.18,2.1))
 # Clear only vegetation rooted within buildings / filled apron. Descending removals preserve indices.
 removed=0
 for owner in act.get_all_level_actors():
  if owner.get_actor_label() not in ('LidarStudy_Forest','LidarStudy_Understory'):continue
  for c in owner.get_components_by_class(u.InstancedStaticMeshComponent):
   indices=[]
   for i in range(c.get_instance_count()):
    p=c.get_instance_transform(i,True).translation
    if clears_vegetation(p.x,p.y):indices.append(i)
   for i in reversed(indices):assert c.remove_instance(i)
   removed+=len(indices)
 return dict(ok=True,layout=layout,vehicles=12,vegetation_removed=removed)

if __name__=='__main__':
 mode=os.environ.get('GT_HS1_MODE','install');report={'ok':False};busy=False
 def run():
  global report
  les=u.get_editor_subsystem(u.LevelEditorSubsystem)
  assert les.load_level(BASE+'/L_LidarStudy');yield 2
  if mode=='inspect':
   report=survey();gc.collect();les.load_level('/Engine/Maps/Entry');yield 3
   return
  backup=ROOT/'Saved/LidarAuthoringBackups'/('HS1-'+str(time.time_ns()));backup.mkdir(parents=True)
  shutil.copy2(ROOT/'Content/GrandTour/ArtTests/LidarStudy/L_LidarStudy.umap',backup/'L_LidarStudy.umap')
  world=u.get_editor_subsystem(u.UnrealEditorSubsystem).get_editor_world();u.SystemLibrary.execute_console_command(world,'Interchange.FeatureFlags.Import.FBX 0')
  material()
  # Material changes must apply even when the FBX input digest is unchanged.
  ground_material('M_HomesteadLawn',True);ground_material('M_HomesteadGravel')
  for name in ['SM_RiversideHouse','SM_RiversideGarage','SM_HomesteadGrade']:import_asset(name);yield .3
  report=place();report['backup']=str(backup);assert les.save_current_level();report['saved']=True;yield 2
  world=None;gc.collect();les.load_level('/Engine/Maps/Entry');yield 3
 steps=run();deadline=0
 def tick(dt):
  global busy,deadline,steps
  if busy:return
  busy=True
  try:
   if time.monotonic()>=deadline:deadline=time.monotonic()+next(steps)
  except StopIteration:
   (QA/(mode+'.json')).write_text(json.dumps(report,indent=2));u.unregister_slate_post_tick_callback(handle);steps=None;gc.collect();u.SystemLibrary.quit_editor()
  except Exception:
   report.update(ok=False,error=traceback.format_exc());(QA/(mode+'.json')).write_text(json.dumps(report,indent=2));u.log_error(report['error']);u.unregister_slate_post_tick_callback(handle);u.SystemLibrary.quit_editor()
  finally:busy=False
 u.EditorPythonScripting.set_keep_python_script_alive(True);handle=u.register_slate_post_tick_callback(tick)
