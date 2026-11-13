"""Own tree LODs, baked distant cards and denser saved placement."""
import unreal as u
from pathlib import Path
import sys,json,time,traceback,math,struct,shutil,hashlib
ROOT=Path(u.Paths.project_dir()).resolve();sys.path.insert(0,str(ROOT/'Art/Unreal'))
from benmore_river_life_materials import Graph,props
OUT=ROOT/'Art/Export/BenmoreWoodland';BASE='/Game/GrandTour/ArtTests/BenmoreWoodland';DEST=BASE+'/Forest'
assets=u.EditorAssetLibrary;mel=u.MaterialEditingLibrary;sm=u.get_editor_subsystem(u.StaticMeshEditorSubsystem);actors=u.get_editor_subsystem(u.EditorActorSubsystem);les=u.get_editor_subsystem(u.LevelEditorSubsystem)
report={'ok':False,'meshes':[]};busy=False;temps=[]
def texture(path,name):
 t=props(u.AssetImportTask(),filename=str(path),destination_path=DEST,destination_name=name,automated=True,replace_existing=True,save=True)
 u.AssetToolsHelpers.get_asset_tools().import_asset_tasks([t]);a=u.load_asset(DEST+'/'+name);assert a;return a
def capture_pixels(capture,rt,source):
 capture.set_editor_property('capture_source',source);capture.capture_scene()
def run():
 assert les.load_level(BASE+'/L_Benmore_Woodland');world=u.get_editor_subsystem(u.UnrealEditorSubsystem).get_editor_world()
 backup=ROOT/'Saved/BenmoreWoodlandBackups'/('forest-'+str(time.time_ns()));shutil.copytree(ROOT/'Content/GrandTour/ArtTests/BenmoreWoodland',backup);report['backup']=str(backup)
 protected=list((ROOT/'Content/GrandTour/Demo/BenmoreRoads/Gaea/NativeSurfaces').glob('M_NativeDomain*.uasset'))+[ROOT/'Content/GrandTour/Demo/BenmoreRoads/Gaea/L_Benmore_GaeaReview.umap',ROOT/'Content/GrandTour/Demo/BenmoreRoads/Gaea/Morphology/DA_GC_WaterDomain.uasset']
 hashes={str(p):hashlib.sha256(p.read_bytes()).hexdigest() for p in protected}
 old=next(a for a in actors.get_all_level_actors() if a.get_actor_label() in ['Woodland_Forest','Woodland_DenseForest'])
 bindings={int(c.static_mesh.get_name()[-1]):list(c.get_materials()) for c in old.get_components_by_class(u.InstancedStaticMeshComponent) if c.static_mesh and c.static_mesh.get_name().startswith('SM_Fir_')}
 report['old_count']=sum(c.get_instance_count() for c in old.get_components_by_class(u.InstancedStaticMeshComponent) if c.static_mesh and c.static_mesh.get_name().startswith('SM_Fir_'))
 meshes=[]
 for k in range(3):
  path=DEST+'/SM_Fir_'+str(k);mesh=u.load_asset(path) or assets.duplicate_asset('/Game/GrandTour/ArtTests/SiberianShowcase/SM_Fir_'+str(k),path)
  ns=sm.get_nanite_settings(mesh);ns.enabled=False;sm.set_nanite_settings(mesh,ns,True)
  for slot,m in enumerate(bindings[k]):mesh.set_material(slot,m)
  opts=props(u.StaticMeshReductionOptions(),auto_compute_lod_screen_size=False,reduction_settings=[props(u.StaticMeshReductionSettings(),percent_triangles=p,screen_size=s) for p,s in [(1,1),(.55,.26),(.22,.12)]])
  assert sm.set_lods(mesh,opts)>=3
  b=mesh.get_bounds();size=max(b.box_extent.z*2,b.box_extent.x*2,b.box_extent.y*2)*1.06
  tree=actors.spawn_actor_from_class(u.StaticMeshActor,u.Vector(0,0,-100000));temps.append(tree);tree.static_mesh_component.set_static_mesh(mesh)
  tree.static_mesh_component.set_forced_lod_model(1)
  cap=actors.spawn_actor_from_class(u.SceneCapture2D,u.Vector(0,0,-100000));temps.append(cap);cc=cap.capture_component2d
  rt=u.RenderingLibrary.create_render_target2d(world,512,512,u.TextureRenderTargetFormat.RTF_RGBA16F)
  props(cc,texture_target=rt,capture_every_frame=False,capture_on_movement=False,projection_type=u.CameraProjectionMode.ORTHOGRAPHIC,ortho_width=size,primitive_render_mode=u.SceneCapturePrimitiveRenderMode.PRM_USE_SHOW_ONLY_LIST)
  cc.show_only_component(tree.static_mesh_component)
  yield 10
  atlas=bytearray(512*512*3*4)
  for view in range(3):
   angle=math.radians(view*60);centre=tree.get_actor_location()+b.origin
   pos=centre+u.Vector(math.cos(angle)*size*2,math.sin(angle)*size*2,0)
   cap.set_actor_location_and_rotation(pos,u.MathLibrary.find_look_at_rotation(pos,centre),False,True)
   capture_pixels(cc,rt,u.SceneCaptureSource.SCS_BASE_COLOR);yield 2
   colors=u.RenderingLibrary.read_render_target_raw_pixel_area(world,rt,0,0,512,512,False)
   capture_pixels(cc,rt,u.SceneCaptureSource.SCS_SCENE_COLOR_HDR);yield 2
   alpha=u.RenderingLibrary.read_render_target_raw_pixel_area(world,rt,0,0,512,512,False)
   assert len(colors)==len(alpha)==512*512,(len(colors),len(alpha))
   covered=0
   for i,(c,a) in enumerate(zip(colors,alpha)):
    op=max(0,min(1,1-a.a));covered+=op>.5
    idx=((i//512)*1536+view*512+i%512)*4
    atlas[idx:idx+4]=bytes([round(max(0,min(1,v))**(1/2.2)*255) for v in (c.b,c.g,c.r)]+[round(op*255)])
   assert covered>1000,('empty bake',k,view,covered)
  tga=OUT/('FirAtlas_'+str(k)+'.tga');tga.write_bytes(struct.pack('<BBBHHBHHHHBB',0,0,2,0,0,0,0,0,1536,512,32,40)+atlas)
  tex=texture(tga,'T_FirAtlas_'+str(k));props(tex,srgb=True,address_x=u.TextureAddress.TA_CLAMP,address_y=u.TextureAddress.TA_CLAMP);assets.save_loaded_asset(tex)
  mpath=DEST+'/M_FirFar_'+str(k);m=u.load_asset(mpath) or u.AssetToolsHelpers.get_asset_tools().create_asset('M_FirFar_'+str(k),DEST,u.Material,u.MaterialFactoryNew());mel.delete_all_material_expressions(m)
  props(m,blend_mode=u.BlendMode.BLEND_MASKED,shading_model=u.MaterialShadingModel.MSM_DEFAULT_LIT,two_sided=True,tangent_space_normal=False,opacity_mask_clip_value=.35)
  mel.set_material_usage(m,u.MaterialUsage.MATUSAGE_INSTANCED_STATIC_MESHES)
  g=Graph(m,'BakedFir');uv=g.node(u.MaterialExpressionTextureCoordinate);sample=g.node(u.MaterialExpressionTextureSample,texture=tex,sampler_type=u.MaterialSamplerType.SAMPLERTYPE_COLOR);g.wire(uv,sample,'UVs');g.output(sample,u.MaterialProperty.MP_BASE_COLOR,'RGB');g.output(sample,u.MaterialProperty.MP_OPACITY_MASK,'A');g.output(g.vector((0,0,1)),u.MaterialProperty.MP_NORMAL);g.output(g.scalar(.9),u.MaterialProperty.MP_ROUGHNESS);g.output(g.scalar(.05),u.MaterialProperty.MP_SPECULAR);assert not mel.recompile_material(m);assets.save_loaded_asset(m)
  lines=[]
  for view in range(3):
   angle=math.radians(view*60);right=(-math.sin(angle),math.cos(angle));idx=view*4+1
   for side,up in [(-1,-1),(1,-1),(1,1),(-1,1)]:lines.append('v %f %f %f'%(b.origin.x+right[0]*side*size/2,b.origin.y+right[1]*side*size/2,b.origin.z+up*size/2))
   for ux,uy in [(0,0),(1,0),(1,1),(0,1)]:lines.append('vt %f %f'%((view+ux)/3,uy))
   lines+=['f %d/%d %d/%d %d/%d'%(idx,idx,idx+1,idx+1,idx+2,idx+2),'f %d/%d %d/%d %d/%d'%(idx,idx,idx+2,idx+2,idx+3,idx+3)]
  obj=OUT/('FirFar_'+str(k)+'.obj');obj.write_text('\n'.join(lines))
  ui=props(u.FbxImportUI(),import_mesh=True,import_materials=False,import_textures=False,import_as_skeletal=False,mesh_type_to_import=u.FBXImportType.FBXIT_STATIC_MESH)
  props(ui.static_mesh_import_data,combine_meshes=True,auto_generate_collision=False,convert_scene=False,convert_scene_unit=False)
  task=props(u.AssetImportTask(),filename=str(obj),destination_path=DEST,destination_name='SM_FirFar_'+str(k),automated=True,replace_existing=True,save=True,options=ui);u.AssetToolsHelpers.get_asset_tools().import_asset_tasks([task]);far=u.load_asset(DEST+'/SM_FirFar_'+str(k));assert far;far.set_material(0,m);assets.save_loaded_asset(far)
  assert sm.set_lod_from_static_mesh(mesh,3,far,0,False)==3
  assert sm.set_lod_screen_sizes(mesh,[1,.26,.12,.055])
  for section in range(mesh.get_num_sections(3)):sm.enable_section_cast_shadow(mesh,False,3,section)
  sm.remove_collisions(mesh);assets.save_loaded_asset(mesh);meshes.append(mesh)
  report['meshes'].append(dict(path=path,vertices=[sm.get_number_verts(mesh,j) for j in range(4)],screens=list(sm.get_lod_screen_sizes(mesh)),nanite=False))
  actors.destroy_actor(tree);actors.destroy_actor(cap);temps.clear();yield 1
 # Replace only this map's forest after every new mesh has built successfully.
 for a in list(actors.get_all_level_actors()):
  if a!=old and a.get_actor_label().startswith('Woodland_DenseForest'):actors.destroy_actor(a)
 trees=json.loads((OUT/'dense-trees.json').read_text());actor=actors.spawn_actor_from_class(u.Actor,u.Vector());actor.set_actor_label('Woodland_DenseForest');trunks=[]
 for k,mesh in enumerate(meshes):
  b=mesh.get_bounds();ts=[];src=u.load_asset('/Game/GrandTour/ArtTests/SiberianShowcase/SM_Fir_'+str(k));sb=src.get_bounds()
  for x,y,z,kind,h,yaw in trees:
   if kind!=k:continue
   # Use source bounds: padded billboard bounds must not change the tree scale.
   sc=h/(2*sb.box_extent.z)
   ts.append(u.Transform(location=u.Vector(x,y,z-(sb.origin.z-sb.box_extent.z)*sc-8),rotation=u.Rotator(yaw=yaw),scale=u.Vector(sc,sc,sc)))
   trunks.append(u.Transform(location=u.Vector(x,y,z+220),scale=u.Vector(.35,.35,4.4)))
  c=u.GTVegetationSubsystem.add_tagged_instances(actor,mesh,ts,'DenseForest','NoCollision',True);c.set_cull_distances(75000,90000);c.set_editor_property('visible_in_ray_tracing',False)
 c=u.GTVegetationSubsystem.add_tagged_instances(actor,u.load_asset('/Engine/BasicShapes/Cylinder'),trunks,'WoodlandTrunks','BlockAll',False);c.set_visibility(False);c.set_hidden_in_game(True);c.set_collision_enabled(u.CollisionEnabled.QUERY_AND_PHYSICS)
 actors.destroy_actor(old)
 assert les.save_current_level();assert les.load_level('/Engine/Maps/Entry');assert les.load_level(BASE+'/L_Benmore_Woodland')
 assert hashes=={str(p):hashlib.sha256(p.read_bytes()).hexdigest() for p in protected}
 report.update(ok=True,trees=len(trees),protected_hashes=hashes);yield 2
 les.load_level('/Engine/Maps/Entry');yield 4
def finish():
 for a in temps:
  if a:actors.destroy_actor(a)
 (OUT/'forestinstall.json').write_text(json.dumps(report,indent=2));u.unregister_slate_post_tick_callback(handle);u.SystemLibrary.quit_editor()
steps=run();deadline=0;started=time.monotonic()
def tick(dt):
 global busy,deadline
 if busy:return
 busy=True
 try:
  assert time.monotonic()-started<840
  if time.monotonic()>=deadline:deadline=time.monotonic()+next(steps)
 except StopIteration:finish()
 except Exception:report['error']=traceback.format_exc();u.log_error(report['error']);finish()
 finally:busy=False
u.EditorPythonScripting.set_keep_python_script_alive(True);handle=u.register_slate_post_tick_callback(tick)
