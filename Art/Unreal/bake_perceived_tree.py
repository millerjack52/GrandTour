"""24-view colour/normal/depth capture from the actual approved beech source."""
import unreal as u,math,time,json,struct,traceback
from pathlib import Path
ROOT=Path(u.Paths.project_dir()).resolve();OUT=ROOT/'Art/Export/LidarStudy/FirstSection/PerceivedDetail';QA=ROOT/'Saved/LidarAuthoringQA/PerceivedDetail'
actors=u.get_editor_subsystem(u.EditorActorSubsystem);world=u.get_editor_subsystem(u.UnrealEditorSubsystem).get_editor_world()
N=256;W=N*8;H=N*3;progress={};temps=[];busy=False;deadline=0
def props(o,**kw):
 for k,v in kw.items():o.set_editor_property(k,v)
 return o
def run():
 source=u.load_asset('/Game/GrandTour/ArtTests/LidarStudy/ForestShapes/SM_FS1_Beech_Mature');b=source.get_bounds();size=max(b.box_extent.z,b.box_extent.x,b.box_extent.y)*2*1.09
 tree=actors.spawn_actor_from_class(u.StaticMeshActor,u.Vector(0,0,-150000));temps.append(tree);tree.static_mesh_component.set_static_mesh(source);tree.static_mesh_component.set_forced_lod_model(1)
 forest=next(a for a in actors.get_all_level_actors() if a.get_actor_label()=='LidarStudy_Forest')
 original=next(c for c in forest.get_components_by_class(u.InstancedStaticMeshComponent) if c.static_mesh and c.static_mesh.get_name()=='SM_Canopy_0')
 for i in range(tree.static_mesh_component.get_num_materials()):tree.static_mesh_component.set_material(i,original.get_material(i))
 cap=actors.spawn_actor_from_class(u.SceneCapture2D,u.Vector());temps.append(cap);cc=cap.capture_component2d
 rt=u.RenderingLibrary.create_render_target2d(world,N,N,u.TextureRenderTargetFormat.RTF_RGBA32F)
 props(cc,texture_target=rt,capture_every_frame=False,capture_on_movement=False,projection_type=u.CameraProjectionMode.ORTHOGRAPHIC,ortho_width=size,primitive_render_mode=u.SceneCapturePrimitiveRenderMode.PRM_USE_SHOW_ONLY_LIST)
 cc.show_only_component(tree.static_mesh_component);yield 3
 colour=bytearray(W*H*4);normaldepth=bytearray(W*H*4);records=[]
 for elevation in range(3):
  el=math.radians(elevation*35)
  for az in range(8):
   angle=math.tau*az/8;d=u.Vector(math.cos(el)*math.cos(angle),math.cos(el)*math.sin(angle),math.sin(el));centre=tree.get_actor_location()+b.origin;pos=centre+d*(size*2)
   cap.set_actor_location_and_rotation(pos,u.MathLibrary.find_look_at_rotation(pos,centre),False,True)
   chunks={}
   for key,mode in [('colour',u.SceneCaptureSource.SCS_BASE_COLOR),('alpha',u.SceneCaptureSource.SCS_SCENE_COLOR_HDR),('normal',u.SceneCaptureSource.SCS_NORMAL),('depth',u.SceneCaptureSource.SCS_SCENE_DEPTH)]:
    cc.set_editor_property('capture_source',mode);cc.capture_scene();yield .2
    chunks[key]=u.RenderingLibrary.read_render_target_raw_pixel_area(world,rt,0,0,N,N,False)
   covered=0;min_depth=1e9;max_depth=0
   for i in range(N*N):
    col=chunks['colour'][i];alpha=max(0,min(1,1-chunks['alpha'][i].a));nor=chunks['normal'][i];depth=chunks['depth'][i].r
    offset=(2*size-depth)/size*.5+.5
    if alpha>.5:covered+=1;min_depth=min(min_depth,depth);max_depth=max(max_depth,depth)
    index=((elevation*N+i//N)*W+az*N+i%N)*4
    colour[index:index+4]=bytes([round(max(0,min(1,v))**(1/2.2)*255) for v in [col.b,col.g,col.r]]+[round(alpha*255)])
    normaldepth[index:index+4]=bytes([round(max(0,min(1,v*.5+.5))*255) for v in [nor.b,nor.g,nor.r]]+[round(max(0,min(1,offset))*255)])
   assert covered>1000,(elevation,az,covered)
   records.append(dict(azimuth=az*45,elevation=elevation*35,pixels=covered,depth_range=[min_depth,max_depth]))
   (QA/'tree-bake-progress.json').write_text(json.dumps(dict(done=len(records),total=24)))
   yield .05
 for name,data in [('T_PD_TreeColour',colour),('T_PD_TreeNormalDepth',normaldepth)]:
  (OUT/(name+'.tga')).write_bytes(struct.pack('<BBBHHBHHHHBB',0,0,2,0,0,0,0,0,W,H,32,40)+data)
 (OUT/'tree-bake.json').write_text(json.dumps(dict(size_cm=size,centre=[b.origin.x,b.origin.y,b.origin.z],frames=records,resolution=[W,H]),indent=2))
 for a in temps:actors.destroy_actor(a)
 temps.clear();(QA/'tree-bake-complete.json').write_text(json.dumps(dict(ok=True,views=24)))
def tick(dt):
 global busy,deadline
 if busy or time.monotonic()<deadline:return
 busy=True
 try:deadline=time.monotonic()+float(next(steps))
 except StopIteration:u.unregister_slate_post_tick_callback(handle)
 except Exception:
  (QA/'tree-bake-complete.json').write_text(json.dumps(dict(ok=False,error=traceback.format_exc())))
  for a in temps:actors.destroy_actor(a)
  u.unregister_slate_post_tick_callback(handle);u.log_error(traceback.format_exc())
 finally:busy=False
steps=run();handle=u.register_slate_post_tick_callback(tick)
