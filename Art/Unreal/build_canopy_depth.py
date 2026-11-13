"""Build broader crowns and 24-view elevation-aware proxies in an empty world."""
import unreal as u,sys,json,time,math,struct,traceback,subprocess,hashlib
from pathlib import Path
ROOT=Path(u.Paths.project_dir()).resolve();sys.path.insert(0,str(ROOT/'Art/Unreal'))
from benmore_river_life_materials import props
import perceived_tree_proxy as proxy
BASE='/Game/GrandTour/ArtTests/LidarStudy';DEST=BASE+'/CanopyDepth'
OUT=ROOT/'Art/Export/LidarStudy/CanopyDepth';QA=ROOT/'Saved/LidarAuthoringQA/CanopyDepth';QA.mkdir(parents=True,exist_ok=True)
actors=u.get_editor_subsystem(u.EditorActorSubsystem);sm=u.get_editor_subsystem(u.StaticMeshEditorSubsystem);assets=u.EditorAssetLibrary
world=u.get_editor_subsystem(u.UnrealEditorSubsystem).get_editor_world();temps=[];report=dict(ok=False,trees=[])
N=256;W=2048;H=1024

def import_source(kind,rows):
 name='SM_CD_Beech_'+kind
 task=props(u.AssetImportTask(),filename=str(OUT/(name+'_LOD0.fbx')),destination_path=DEST,destination_name=name,automated=True,replace_existing=True,save=True)
 opt=props(u.FbxImportUI(),import_mesh=True,import_materials=False,import_textures=False,import_as_skeletal=False,mesh_type_to_import=u.FBXImportType.FBXIT_STATIC_MESH)
 props(opt.static_mesh_import_data,combine_meshes=True,auto_generate_collision=False,generate_lightmap_u_vs=False,vertex_color_import_option=u.VertexColorImportOption.REPLACE,normal_import_method=u.FBXNormalImportMethod.FBXNIM_IMPORT_NORMALS)
 task.options=opt;u.AssetToolsHelpers.get_asset_tools().import_asset_tasks([task]);mesh=u.load_asset(DEST+'/'+name);assert mesh
 if sm.get_lod_count(mesh)<3:
  opt=u.StaticMeshReductionOptions();opt.auto_compute_lod_screen_size=False
  opt.reduction_settings=[u.StaticMeshReductionSettings(percent_triangles=1.,screen_size=v) for v in (1.,.22,.08)];assert sm.set_lods(mesh,opt)==3
 for lod in [1,2]:assert sm.import_lod(mesh,lod,str(OUT/(name+'_LOD'+str(lod)+'.fbx')))==lod
 for i,s in enumerate(mesh.get_editor_property('static_materials')):
  leaf='foliage' in str(s.material_slot_name).lower()
  mesh.set_material(i,u.load_asset(BASE+'/MI_NZ_Foliage_Canopy' if leaf else '/Game/GrandTour/Environment/NativePlants/v01/M_NZ_Bark'))
 ns=sm.get_nanite_settings(mesh);ns.enabled=False;sm.set_nanite_settings(mesh,ns,True);sm.remove_collisions(mesh)
 b=mesh.get_bounds();expected=next(r['size_m'] for r in rows if r['variant']==kind and r['lod']==0)
 assert all(abs(a-b)<.03 for a,b in zip(sorted([b.box_extent.x*.02,b.box_extent.y*.02,b.box_extent.z*.02]),sorted(expected)))
 assert assets.save_loaded_asset(mesh,False);return mesh

def bake(source,kind):
 folder=OUT/kind;folder.mkdir(exist_ok=True)
 b=source.get_bounds();size=max(b.box_extent.z,b.box_extent.x,b.box_extent.y)*2*1.09
 tree=actors.spawn_actor_from_class(u.StaticMeshActor,u.Vector(0,0,-150000));temps.append(tree);tree.static_mesh_component.set_static_mesh(source);tree.static_mesh_component.set_forced_lod_model(1)
 cap=actors.spawn_actor_from_class(u.SceneCapture2D,u.Vector());temps.append(cap);cc=cap.capture_component2d
 rt=u.RenderingLibrary.create_render_target2d(world,N,N,u.TextureRenderTargetFormat.RTF_RGBA32F)
 props(cc,texture_target=rt,capture_every_frame=False,capture_on_movement=False,projection_type=u.CameraProjectionMode.ORTHOGRAPHIC,ortho_width=size,primitive_render_mode=u.SceneCapturePrimitiveRenderMode.PRM_USE_SHOW_ONLY_LIST)
 cc.show_only_component(tree.static_mesh_component);yield 3
 colour=bytearray(W*H*4);normaldepth=bytearray(W*H*4);records=[]
 for elevation in range(3):
  el=math.radians(elevation*35)
  for az in range(8):
   angle=math.tau*az/8;d=u.Vector(math.cos(el)*math.cos(angle),math.cos(el)*math.sin(angle),math.sin(el));centre=tree.get_actor_location()+b.origin;pos=centre+d*(size*2)
   cap.set_actor_location_and_rotation(pos,u.MathLibrary.find_look_at_rotation(pos,centre),False,True);chunks={}
   for key,mode in [('colour',u.SceneCaptureSource.SCS_BASE_COLOR),('alpha',u.SceneCaptureSource.SCS_SCENE_COLOR_HDR),('normal',u.SceneCaptureSource.SCS_NORMAL),('depth',u.SceneCaptureSource.SCS_SCENE_DEPTH)]:
    cc.set_editor_property('capture_source',mode);cc.capture_scene();yield .15
    chunks[key]=u.RenderingLibrary.read_render_target_raw_pixel_area(world,rt,0,0,N,N,False)
   covered=0
   for i in range(N*N):
    col=chunks['colour'][i];alpha=max(0,min(1,1-chunks['alpha'][i].a));nor=chunks['normal'][i];depth=chunks['depth'][i].r
    offset=(2*size-depth)/size*.5+.5;covered+=int(alpha>.5);index=((elevation*N+i//N)*W+az*N+i%N)*4
    colour[index:index+4]=bytes([round(max(0,min(1,v))**(1/2.2)*255) for v in [col.b,col.g,col.r]]+[round(alpha*255)])
    normaldepth[index:index+4]=bytes([round(max(0,min(1,v*.5+.5))*255) for v in [nor.b,nor.g,nor.r]]+[round(max(0,min(1,offset))*255)])
   assert covered>1000,(kind,elevation,az,covered)
   records.append(dict(azimuth=az*45,elevation=elevation*35,pixels=covered));(QA/'progress.json').write_text(json.dumps(dict(kind=kind,done=len(records),total=24)));yield .01
 for name,data in [('T_PD_TreeColour',colour),('T_PD_TreeNormalDepth',normaldepth)]:
  (folder/(name+'.tga')).write_bytes(struct.pack('<BBBHHBHHHHBB',0,0,2,0,0,0,0,0,W,H,32,40)+data)
 data=dict(size_cm=size,centre=[b.origin.x,b.origin.y,b.origin.z],frames=records,resolution=[W,H],grid_rows=4,streaming=True,canopy_depth=True,source_sha256=hashlib.sha256((OUT/('SM_CD_Beech_'+kind+'_LOD0.fbx')).read_bytes()).hexdigest())
 (folder/'tree-bake.json').write_text(json.dumps(data,indent=2))
 for a in temps:actors.destroy_actor(a)
 temps.clear();u.RenderingLibrary.release_render_target2d(rt)
 subprocess.run([str(ROOT/'Saved/Tools/TerrainPython/Scripts/python.exe'),str(ROOT/'Art/tools/prepare_canopy_depth_atlases.py'),str(folder)],check=True,creationflags=subprocess.CREATE_NO_WINDOW)
 return data

def install_proxy(source,kind,k,data):
 proxy.OUT=OUT/kind;proxy.PD=DEST+'/'+kind;m=proxy.material(data)
 if u.load_asset(DEST+'/T_CD_Lighting'):
  import canopy_lighting
  canopy_lighting.wrap(m)
 c=data['centre'];h=data['size_cm']/2;lines=['v %f %f %f'%(c[0],c[1]+y,c[2]+z) for y,z in [(-h,-h),(h,-h),(h,h),(-h,h)]]
 lines+=['vt 0 1','vt 1 1','vt 1 0','vt 0 0','f 1/1 2/2 3/3','f 1/1 3/3 4/4']
 f=OUT/kind/'SM_CD_Proxy.obj';f.write_text('\n'.join(lines))
 task=props(u.AssetImportTask(),filename=str(f),destination_path=DEST+'/'+kind,destination_name='SM_CD_Proxy',automated=True,replace_existing=True,save=True)
 opt=props(u.FbxImportUI(),import_mesh=True,import_materials=False,import_textures=False,import_as_skeletal=False,mesh_type_to_import=u.FBXImportType.FBXIT_STATIC_MESH)
 props(opt.static_mesh_import_data,combine_meshes=True,auto_generate_collision=False,convert_scene=False,convert_scene_unit=False);task.options=opt
 u.AssetToolsHelpers.get_asset_tools().import_asset_tasks([task]);quad=u.load_asset(DEST+'/'+kind+'/SM_CD_Proxy');quad.set_material(0,m);assets.save_loaded_asset(quad,False)
 path=DEST+'/SM_CD_Canopy_'+str(k);mesh=u.load_asset(path) or assets.duplicate_asset(source.get_path_name().split('.')[0],path)
 for lod in range(3):assert sm.set_lod_from_static_mesh(mesh,lod,source,lod,True)==lod
 assert sm.set_lod_from_static_mesh(mesh,3,quad,0,True)==3
 # Keep the same world-distance transitions despite the broader new bounds.
 for i in range(mesh.get_num_sections(3)):sm.enable_section_cast_shadow(mesh,False,3,i)
 # WPO can rotate the square out of its imported plane. Cover its corner radius
 # in each axis, then compensate LOD screens for the resulting bounds.
 mesh.set_editor_property('positive_bounds_extension',u.Vector());mesh.set_editor_property('negative_bounds_extension',u.Vector())
 b=mesh.get_bounds();r=h*math.sqrt(2)
 positive=u.Vector(*[max(0,ctr+r-(o+e)) for ctr,o,e in zip(c,[b.origin.x,b.origin.y,b.origin.z],[b.box_extent.x,b.box_extent.y,b.box_extent.z])])
 negative=u.Vector(*[max(0,(o-e)-(ctr-r)) for ctr,o,e in zip(c,[b.origin.x,b.origin.y,b.origin.z],[b.box_extent.x,b.box_extent.y,b.box_extent.z])])
 mesh.set_editor_property('positive_bounds_extension',positive);mesh.set_editor_property('negative_bounds_extension',negative)
 import canopy_depth
 assert sm.set_lod_screen_sizes(mesh,canopy_depth.distance_screens(mesh,k))
 assert assets.save_loaded_asset(mesh,False)
 return dict(kind=kind,mesh=path,views=24,size_cm=data['size_cm'],vertices=[sm.get_number_verts(mesh,i) for i in range(4)],screens=list(sm.get_lod_screen_sizes(mesh)))

def run():
 u.SystemLibrary.execute_console_command(world,'Interchange.FeatureFlags.Import.FBX 0')
 rows=json.loads((OUT/'manifest.json').read_text())['models']
 for k,kind in enumerate(['Mature','Pole','Edge']):
  source=import_source(kind,rows);yield 1
  path=OUT/kind/'tree-bake.json';data=json.loads(path.read_text()) if path.exists() else {}
  digest=hashlib.sha256((OUT/('SM_CD_Beech_'+kind+'_LOD0.fbx')).read_bytes()).hexdigest()
  if data.get('source_sha256')!=digest:data=yield from bake(source,kind)
  subprocess.run([str(ROOT/'Saved/Tools/TerrainPython/Scripts/python.exe'),str(ROOT/'Art/tools/build_canopy_volume_normals.py'),kind],check=True,creationflags=subprocess.CREATE_NO_WINDOW)
  report['trees'].append(install_proxy(source,kind,k,data));yield 3
 report['ok']=True

busy=False;deadline=0;steps=run()
def tick(dt):
 global busy,deadline
 if busy or time.monotonic()<deadline:return
 busy=True
 try:deadline=time.monotonic()+float(next(steps))
 except StopIteration:
  (QA/'build-result.json').write_text(json.dumps(report,indent=2));u.unregister_slate_post_tick_callback(handle);u.SystemLibrary.quit_editor()
 except Exception:
  report.update(ok=False,error=traceback.format_exc());(QA/'build-result.json').write_text(json.dumps(report,indent=2));u.log_error(report['error']);u.unregister_slate_post_tick_callback(handle);u.SystemLibrary.quit_editor()
 finally:busy=False
u.EditorPythonScripting.set_keep_python_script_alive(True);handle=u.register_slate_post_tick_callback(tick)
