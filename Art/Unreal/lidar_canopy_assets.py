"""LP3: kit canopy species with a baked distant card.
SM_Canopy_0..3 are duplicates of the native plant kit's Beech_Mature, Beech_Pole, Beech_Edge and DeadSpar (their three authored
LODs and materials kept, collision removed, Nanite off) with a 6 triangle three-quad card as LOD3, baked from the mesh's own LOD0
(atlas of three views). Screen-size reference distances are 50/160/600 m; actual
transitions depend on instance scale, FOV and the global LOD bias. Meshes live in
.../LidarStudy/CanopyKit (the old OW beech/birch copies in .../Canopy are unused)."""
import unreal as u
from pathlib import Path
import sys,json,time,traceback,math,struct,shutil,hashlib
ROOT=Path(u.Paths.project_dir()).resolve();sys.path.insert(0,str(ROOT/'Art/Unreal'))
from benmore_river_life_materials import Graph,props
OUT=ROOT/'Art/Export/LidarStudy/Place';BASE='/Game/GrandTour/ArtTests/LidarStudy';DEST=BASE+'/CanopyKit'
KIT='/Game/GrandTour/Environment/NativePlants/v01'
SOURCES=['SM_NZ_Beech_Mature','SM_NZ_Beech_Pole','SM_NZ_Beech_Edge','SM_NZ_DeadSpar']
TRUNK_RADIUS_CM=[32.,9.,28.,25.]      # kit trunk radius at true scale; the collision cylinder multiplies it by the instance scale
LOD_START_M=(50.,160.,600.)            # Screen-size reference distances; actual transitions depend on scale/FOV/global LOD bias
PROJ=1.4                              # horizontal projection scale, 1/tan(HFOV/2), of a ~70 degree view
VERSION=5                             # VQ2 normal atlases and longer geometric crown range
KIT_CONTENT=ROOT/'Content/GrandTour/Environment/NativePlants/v01'
assets=u.EditorAssetLibrary;mel=u.MaterialEditingLibrary;sm=u.get_editor_subsystem(u.StaticMeshEditorSubsystem);actors=u.get_editor_subsystem(u.EditorActorSubsystem);les=u.get_editor_subsystem(u.LevelEditorSubsystem)
report={'ok':False,'meshes':[]};busy=False;temps=[]

def source_path(source):
 """An installed map-specific shape takes precedence without altering the shared kit."""
 selection=OUT/'forest-shapes.json'
 overrides=json.loads(selection.read_text()).get('sources',{}) if selection.exists() else {}
 return overrides.get(source,KIT+'/'+source)
def screen_sizes(mesh):
 r=mesh.get_bounds().sphere_radius;out=[1.]
 for d in LOD_START_M:out.append(min(out[-1]*.95,PROJ*r/(d*100)))
 # Keep the approved distance treatment when canopy assets are rebuilt.
 atmosphere=OUT/'forest-atmosphere.json'
 if atmosphere.exists():
  settings=json.loads(atmosphere.read_text());kind=mesh.get_name().rsplit('_',1)[-1]
  out[-1]*=float(settings.get('far_card_screen_multipliers',{}).get(kind,settings['far_card_screen_multiplier']))
 return out
def tree_transforms(mesh,trees,kind):
 """World transforms for the trees of one kind. The kit pivot is the trunk base (lowest vertex 6cm below it): the pivot sits on the ground and the root flare is sunk 6cm."""
 b=u.load_asset(source_path(SOURCES[kind])).get_bounds();ts=[]
 for x,y,z,k,height,yaw in trees:
  if int(k)!=kind:continue
  sc=height/(2*b.box_extent.z);ts.append(u.Transform(location=u.Vector(x,y,z-3),rotation=u.Rotator(yaw=yaw),scale=u.Vector(sc,sc,sc)))
 return ts
def trunk_transforms(mesh,trees,kind):
 """Invisible collision cylinders (engine cylinder: 100cm across, 100cm tall): kit trunk radius times the tree's scale, 4.8m tall from the ground."""
 b=u.load_asset(source_path(SOURCES[kind])).get_bounds();ts=[];diameter=2*TRUNK_RADIUS_CM[kind]/100.
 for x,y,z,k,height,yaw in trees:
  if int(k)!=kind:continue
  sc=height/(2*b.box_extent.z);ts.append(u.Transform(location=u.Vector(x,y,z+240),scale=u.Vector(diameter*sc,diameter*sc,4.8)))
 return ts
def texture(path,name):
 t=props(u.AssetImportTask(),filename=str(path),destination_path=DEST,destination_name=name,automated=True,replace_existing=True,save=True)
 u.AssetToolsHelpers.get_asset_tools().import_asset_tasks([t]);a=u.load_asset(DEST+'/'+name);assert a;return a

def tint_far_card(k,rgb):
 """Update the tint anywhere in the graph, including below LP6 crown shading."""
 m=u.load_asset(DEST+'/M_FirFar_'+str(k));assert m
 # Search only the connected BaseColor graph. UE can retain orphan expressions
 # briefly after rebuilding, and an orphan tint must not be reused.
 todo=[mel.get_material_property_input_node(m,u.MaterialProperty.MP_BASE_COLOR)];seen=set();cur=None
 while todo:
  node=todo.pop()
  if not node or node.get_name() in seen:continue
  seen.add(node.get_name())
  if isinstance(node,u.MaterialExpressionConstant3Vector) and str(node.get_editor_property('desc'))=='ForestShaderTint':
   colour=node.get_editor_property('constant')
   if any(abs(a-b)>1e-6 for a,b in zip((colour.r,colour.g,colour.b),rgb)):
    node.set_editor_property('constant',u.LinearColor(*rgb,1))
    assert not mel.recompile_material(m);assert assets.save_loaded_asset(m)
   return
  if isinstance(node,u.MaterialExpressionMultiply) and str(node.get_editor_property('desc'))=='LP3cTint':cur=node;break
  todo.extend(n for n in mel.get_inputs_for_material_expression(m,node) if n)
 if cur:
  vec=[n for n in mel.get_inputs_for_material_expression(m,cur) if isinstance(n,u.MaterialExpressionConstant3Vector)]
  assert len(vec)==1;vec[0].set_editor_property('constant',u.LinearColor(*rgb,1))
 else:
  old=mel.get_material_property_input_node(m,u.MaterialProperty.MP_BASE_COLOR)
  oo=mel.get_material_property_input_node_output_name(m,u.MaterialProperty.MP_BASE_COLOR)
  g=Graph(m,'LP3cTint');mul=g.node(u.MaterialExpressionMultiply);g.wire(old,mul,'A',oo);g.wire(g.vector(rgb),mul,'B');g.output(mul,u.MaterialProperty.MP_BASE_COLOR)
 assert not mel.recompile_material(m);assert assets.save_loaded_asset(m)
def shade_far_card(k):
 """VQ2: baked object-space leaf normals rotate with each tree instance.
 No baked sun direction; the six-triangle far card responds to the level light.
 """
 import forest_shaders
 if forest_shaders.enabled():
  forest_shaders.ensure_atlases()
  existing=u.load_asset(DEST+'/M_FirFar_'+str(k))
  if forest_shaders.imported_atlas_current(k) and existing and any(str(n.get_editor_property('desc'))=='ForestShaderTint' for n in forest_shaders.connected_nodes(existing)):
   return True
  forest_shaders.far_material(k)
  return True
 m=u.load_asset(DEST+'/M_FirFar_'+str(k));nt=u.load_asset(DEST+'/T_FirNormal_'+str(k))
 if not m or not nt:return False
 g=Graph(m,'VQ2Far');nodes=list(mel.get_material_expressions(m))
 todo=[mel.get_material_property_input_node(m,u.MaterialProperty.MP_NORMAL)];seen=set();existing=None
 while todo:
  node=todo.pop()
  if not node or node.get_name() in seen:continue
  seen.add(node.get_name())
  if str(node.get_editor_property('desc'))=='VQ2FarNormal':existing=node;break
  todo.extend(n for n in mel.get_inputs_for_material_expression(m,node) if n)
 if not existing:
  uv=g.node(u.MaterialExpressionTextureCoordinate);sample=g.tex(nt,uv)
  decode=g.custom(['Packed'],'float3 n=Packed*2-1;return normalize(lerp(n,float3(0,0,1),.18));')
  decode.set_editor_property('desc','VQ2FarNormal');g.wire(sample,decode,'Packed','RGB')
  world=g.node(u.MaterialExpressionTransform,transform_source_type=u.MaterialVectorCoordTransformSource.TRANSFORMSOURCE_LOCAL,transform_type=u.MaterialVectorCoordTransform.TRANSFORM_WORLD)
  g.wire(decode,world,'');g.output(world,u.MaterialProperty.MP_NORMAL)
  # Neutralize LP6's broad dark gradient if upgrading an already shaded material.
  for n in nodes:
   if isinstance(n,u.MaterialExpressionCustom) and 'float crown=smoothstep' in n.get_editor_property('code'):n.set_editor_property('code','return Base;')
 props(m,dithered_lod_transition=True,tangent_space_normal=False)
 assert not mel.recompile_material(m);assert assets.save_loaded_asset(m)
 return True

def capture_pixels(capture,rt,source):
 capture.set_editor_property('capture_source',source);capture.capture_scene()
def lod_row(mesh,path,source):
 tris=[]
 for j in range(sm.get_lod_count(mesh)):
  try:tris.append(int(mesh.get_static_mesh_description(j).get_triangle_count()))
  except Exception:tris.append(None)
 return dict(path=path,source=source_path(source),lods=sm.get_lod_count(mesh),vertices=[sm.get_number_verts(mesh,j) for j in range(sm.get_lod_count(mesh))],triangles=tris,screens=[round(x,4) for x in sm.get_lod_screen_sizes(mesh)],
  sphere_radius_cm=round(mesh.get_bounds().sphere_radius,1),lod_start_m=[0.,*LOD_START_M],nanite=False)
def source_signature():
 """What the four kit meshes are right now: vertex and triangle counts per LOD, bounds and the .uasset file stamp (size, mtime), so a kit re-import
 (new geometry or only new vertex colours) changes the signature and the canopy meshes and far cards are baked again."""
 sig={}
 for src in SOURCES:
  path=source_path(src);m=u.load_asset(path);assert m,('canopy source missing',path)
  b=m.get_bounds();f=ROOT/'Content'/(path.removeprefix('/Game/')+'.uasset');st=f.stat() if f.exists() else None;tris=[]
  for j in range(sm.get_lod_count(m)):
   try:tris.append(int(m.get_static_mesh_description(j).get_triangle_count()))
   except Exception:tris.append(None)
  sig[src]=dict(source=path,vertices=[sm.get_number_verts(m,j) for j in range(sm.get_lod_count(m))],triangles=tris,origin=[round(x,1) for x in (b.origin.x,b.origin.y,b.origin.z)],
   extent=[round(x,1) for x in (b.box_extent.x,b.box_extent.y,b.box_extent.z)],uasset=[st.st_size,st.st_mtime_ns] if st else None)
 return sig
def cached():
 cache=OUT/'canopy-assets.json'
 if not cache.exists():return None
 c=json.loads(cache.read_text())
 if c.get('version')!=VERSION or c.get('sources')!=SOURCES or len(c.get('meshes',[]))!=4:return None
 if c.get('source_signature')!=source_signature():return None
 if not all(u.load_asset(DEST+'/T_FirNormal_'+str(k)) for k in range(4)):return None
 ms=[u.load_asset(DEST+'/SM_Canopy_'+str(k)) for k in range(4)]
 if not all(ms):return None
 for k,m in enumerate(ms):
  if sm.get_lod_count(m)!=4 or [sm.get_number_verts(m,j) for j in range(4)]!=c['meshes'][k]['vertices'] or not (OUT/('FirAtlas_'+str(k)+'.tga')).exists():return None
 return c,ms
def build(world,force=False):
 hit=None if force else cached()
 if hit:report.update(hit[0]);return hit[1]
 assets.make_directory(DEST)
 meshes=[];report.update(ok=False,version=VERSION,sources=SOURCES,source_signature=source_signature(),meshes=[])
 for k,src in enumerate(SOURCES):
  path=DEST+'/SM_Canopy_'+str(k)
  source=u.load_asset(source_path(src));assert source
  mesh=u.load_asset(path)
  if mesh:
   # Retain UObject identity: Polish can rebuild while a saved forest references it.
   # Do not call set_lods here: UE replaces authored LOD descriptions with empty
   # reduction slots, and SetLodFromStaticMesh dereferences those empty slots.
   assert sm.get_lod_count(mesh)==4
   mesh.set_editor_property('static_materials',source.get_editor_property('static_materials'))
   for lod in range(3):
    assert mesh.get_static_mesh_description(lod) and source.get_static_mesh_description(lod)
    assert sm.set_lod_from_static_mesh(mesh,lod,source,lod,True)==lod
  else:mesh=assets.duplicate_asset(source_path(src),path)
  assert mesh,('duplicate failed',src)
  assert sm.get_lod_count(mesh) in (3,4),('canopy source has unexpected LODs',src,sm.get_lod_count(mesh))
  ns=sm.get_nanite_settings(mesh);ns.enabled=False;sm.set_nanite_settings(mesh,ns,True)
  try:mesh.set_editor_property('auto_compute_lod_screen_size',False)
  except Exception:pass
  # Existing destination bounds also contain its previous square far cards.
  # Bake from source geometry bounds, otherwise each rebuild inflates the cards.
  b=source.get_bounds();size=max(b.box_extent.z*2,b.box_extent.x*2,b.box_extent.y*2)*1.06
  tree=actors.spawn_actor_from_class(u.StaticMeshActor,u.Vector(0,0,-100000));temps.append(tree);tree.static_mesh_component.set_static_mesh(mesh)
  tree.static_mesh_component.set_forced_lod_model(1)
  cap=actors.spawn_actor_from_class(u.SceneCapture2D,u.Vector(0,0,-100000));temps.append(cap);cc=cap.capture_component2d
  rt=u.RenderingLibrary.create_render_target2d(world,512,512,u.TextureRenderTargetFormat.RTF_RGBA16F)
  props(cc,texture_target=rt,capture_every_frame=False,capture_on_movement=False,projection_type=u.CameraProjectionMode.ORTHOGRAPHIC,ortho_width=size,primitive_render_mode=u.SceneCapturePrimitiveRenderMode.PRM_USE_SHOW_ONLY_LIST)
  cc.show_only_component(tree.static_mesh_component)
  yield 10
  atlas=bytearray(512*512*3*4);normal_atlas=bytearray(512*512*3*4)
  for view in range(3):
   angle=math.radians(view*60);centre=tree.get_actor_location()+b.origin
   pos=centre+u.Vector(math.cos(angle)*size*2,math.sin(angle)*size*2,0)
   cap.set_actor_location_and_rotation(pos,u.MathLibrary.find_look_at_rotation(pos,centre),False,True)
   capture_pixels(cc,rt,u.SceneCaptureSource.SCS_BASE_COLOR);yield 2
   colors=u.RenderingLibrary.read_render_target_raw_pixel_area(world,rt,0,0,512,512,False)
   capture_pixels(cc,rt,u.SceneCaptureSource.SCS_SCENE_COLOR_HDR);yield 2
   alpha=u.RenderingLibrary.read_render_target_raw_pixel_area(world,rt,0,0,512,512,False)
   capture_pixels(cc,rt,u.SceneCaptureSource.SCS_NORMAL);yield 2
   normals=u.RenderingLibrary.read_render_target_raw_pixel_area(world,rt,0,0,512,512,False)
   assert len(normals)==512*512
   assert len(colors)==len(alpha)==512*512,(len(colors),len(alpha))
   covered=0
   for i,(c,a) in enumerate(zip(colors,alpha)):
    op=max(0,min(1,1-a.a));covered+=op>.5
    idx=((i//512)*1536+view*512+i%512)*4
    n=normals[i]
    normal_atlas[idx:idx+4]=bytes([round(max(0,min(1,v*.5+.5))*255) for v in (n.b,n.g,n.r)]+[round(op*255)])
    atlas[idx:idx+4]=bytes([round(max(0,min(1,v))**(1/2.2)*255) for v in (c.b,c.g,c.r)]+[round(op*255)])
   assert covered>1000,('empty bake',k,view,covered)
  tga=OUT/('FirAtlas_'+str(k)+'.tga');tga.write_bytes(struct.pack('<BBBHHBHHHHBB',0,0,2,0,0,0,0,0,1536,512,32,40)+atlas)
  tex=texture(tga,'T_FirAtlas_'+str(k));props(tex,srgb=True,address_x=u.TextureAddress.TA_CLAMP,address_y=u.TextureAddress.TA_CLAMP,
   do_scale_mips_for_alpha_coverage=True,alpha_coverage_thresholds=u.Vector4(0,0,0,.35));assets.save_loaded_asset(tex)
  normal_tga=OUT/('FirNormal_'+str(k)+'.tga');normal_tga.write_bytes(struct.pack('<BBBHHBHHHHBB',0,0,2,0,0,0,0,0,1536,512,32,40)+normal_atlas)
  nt=texture(normal_tga,'T_FirNormal_'+str(k));props(nt,srgb=False,address_x=u.TextureAddress.TA_CLAMP,address_y=u.TextureAddress.TA_CLAMP,
   compression_settings=u.TextureCompressionSettings.TC_VECTOR_DISPLACEMENTMAP)
  assets.save_loaded_asset(nt)
  mpath=DEST+'/M_FirFar_'+str(k);m=u.load_asset(mpath) or u.AssetToolsHelpers.get_asset_tools().create_asset('M_FirFar_'+str(k),DEST,u.Material,u.MaterialFactoryNew())
  # UE can compile stale output references during graph edits. Neutralise the
  # previous custom nodes before deleting them so partial graph edits stay valid.
  for old in mel.get_material_expressions(m):
   if isinstance(old,u.MaterialExpressionCustom):
    old.set_editor_property('code','return 0;');old.set_editor_property('inputs',[])
  mel.delete_all_material_expressions(m)
  g=Graph(m,'BakedFir');uv=g.node(u.MaterialExpressionTextureCoordinate);sample=g.node(u.MaterialExpressionTextureSample,texture=tex,sampler_type=u.MaterialSamplerType.SAMPLERTYPE_COLOR);g.wire(uv,sample,'UVs');g.output(sample,u.MaterialProperty.MP_BASE_COLOR,'RGB');g.output(sample,u.MaterialProperty.MP_OPACITY_MASK,'A');g.output(g.vector((0,0,1)),u.MaterialProperty.MP_NORMAL);g.output(g.scalar(.9),u.MaterialProperty.MP_ROUGHNESS);g.output(g.scalar(.05),u.MaterialProperty.MP_SPECULAR)
  # Property edits trigger compilation: reconnect every output before those edits.
  props(m,blend_mode=u.BlendMode.BLEND_MASKED,shading_model=u.MaterialShadingModel.MSM_DEFAULT_LIT,two_sided=True,tangent_space_normal=False,opacity_mask_clip_value=.35)
  mel.set_material_usage(m,u.MaterialUsage.MATUSAGE_INSTANCED_STATIC_MESHES)
  assert not mel.recompile_material(m);assets.save_loaded_asset(m)
  tg=Graph(m,'LP3cTint');mul=tg.node(u.MaterialExpressionMultiply);tg.wire(sample,mul,'A','RGB');tg.wire(tg.vector((.42,.40,.38) if k==3 else (.55,.62,.50)),mul,'B');tg.output(mul,u.MaterialProperty.MP_BASE_COLOR)
  shade_far_card(k)
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
  assert sm.set_lod_from_static_mesh(mesh,3,far,0,True)==3
  assert sm.get_lod_count(mesh)==4,sm.get_lod_count(mesh)
  assert sm.set_lod_screen_sizes(mesh,screen_sizes(mesh))
  for section in range(mesh.get_num_sections(3)):sm.enable_section_cast_shadow(mesh,False,3,section)
  sm.remove_collisions(mesh);assets.save_loaded_asset(mesh);meshes.append(mesh)
  report['meshes'].append(lod_row(mesh,path,src))
  actors.destroy_actor(tree);actors.destroy_actor(cap);temps.clear();yield 1
 report.update(ok=True,version=VERSION,sources=SOURCES);(OUT/'canopy-assets.json').write_text(json.dumps(report,indent=2))
 return meshes
