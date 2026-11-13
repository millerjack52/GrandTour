import unreal as u,json,sys,os,traceback,hashlib,shutil,math,random
from pathlib import Path
ROOT=Path(u.Paths.project_dir()).resolve();sys.path.insert(0,str(ROOT/'Art/Unreal'))
from benmore_river_life_materials import Graph,props
from forest_shaders import connected_nodes
BASE='/Game/GrandTour/ArtTests/LidarStudy';STYLE=BASE+'/CohesiveStyle';DEST=BASE+'/CanopyInterior'
QA=ROOT/'Saved/LidarAuthoringQA/CanopyInterior';QA.mkdir(parents=True,exist_ok=True)
assets=u.EditorAssetLibrary;mel=u.MaterialEditingLibrary;sm=u.get_editor_subsystem(u.StaticMeshEditorSubsystem)
def sha(p):
 h=hashlib.sha256()
 with p.open('rb') as f:
  for b in iter(lambda:f.read(1048576),b''):h.update(b)
 return h.hexdigest()
def audit():
 assert u.get_editor_subsystem(u.LevelEditorSubsystem).load_level(BASE+'/L_LidarStudy')
 actors=u.get_editor_subsystem(u.EditorActorSubsystem).get_all_level_actors();components=[];trees=[];shrubs=[];meshes={}
 for a in actors:
  if a.get_actor_label() not in ['LidarStudy_Forest','LidarStudy_Understory']:continue
  for c in a.get_components_by_class(u.InstancedStaticMeshComponent):
   m=c.static_mesh
   if not m:continue
   name=m.get_name();bounds=m.get_bounds()
   woody=any(k in name for k in ['Coprosma','Matagouri','Shrub','BirchBush'])
   tree=name.startswith('SM_CD_Canopy_')
   components.append(dict(actor=a.get_actor_label(),mesh=m.get_path_name(),count=c.get_instance_count(),cull=[c.instance_start_cull_distance,c.instance_end_cull_distance],materials=[c.get_material(i).get_path_name() if c.get_material(i) else None for i in range(c.get_num_materials())]))
   if name not in meshes:meshes[name]=dict(lods=[m.get_static_mesh_description(i).get_triangle_count() for i in range(sm.get_lod_count(m))],bounds=[bounds.origin.x,bounds.origin.y,bounds.origin.z,bounds.box_extent.x,bounds.box_extent.y,bounds.box_extent.z])
   if not (woody or tree):continue
   for i in range(c.get_instance_count()):
    t=c.get_instance_transform(i,True);p=t.translation;s=t.scale3d
    row=[p.x,p.y,p.z,s.x,s.y,s.z,name]
    (trees if tree else shrubs).append(row)
 (QA/'placements.json').write_text(json.dumps(dict(trees=trees,shrubs=shrubs),separators=(',',':')))
 (QA/'inventory.json').write_text(json.dumps(dict(components=components,meshes=meshes),indent=2))
 codes={}
 for name in ['M_EvergreenFoliage','M_EvergreenProxy_Mature','M_EvergreenProxy_Pole','M_EvergreenProxy_Edge','M_EvergreenTerrain']:
  m=u.load_asset(STYLE+'/'+name)
  codes[name]=[dict(name=n.get_name(),desc=str(n.get_editor_property('desc')),code=n.get_editor_property('code'),inputs=[str(x.get_editor_property('input_name')) for x in n.get_editor_property('inputs')]) for n in connected_nodes(m) if isinstance(n,u.MaterialExpressionCustom)]
 (QA/'placements.json').write_text(json.dumps(dict(trees=trees,shrubs=shrubs),separators=(',',':')))
 (QA/'shader-audit.json').write_text(json.dumps(codes,indent=2))
 return dict(ok=True,components=components,meshes=meshes,trees=len(trees),woody_shrubs=len(shrubs))
def interior_mesh():
 out=ROOT/'Art/Export/LidarStudy/CanopyInterior';name='SM_ForestInterior'
 mesh=u.load_asset(DEST+'/'+name)
 if not mesh:
  world=u.get_editor_subsystem(u.UnrealEditorSubsystem).get_editor_world();u.SystemLibrary.execute_console_command(world,'Interchange.FeatureFlags.Import.FBX 0')
  task=props(u.AssetImportTask(),filename=str(out/'SM_ForestInterior_LOD0.fbx'),destination_path=DEST,destination_name=name,automated=True,replace_existing=True,save=True)
  opt=props(u.FbxImportUI(),import_mesh=True,import_materials=False,import_textures=False,import_as_skeletal=False,mesh_type_to_import=u.FBXImportType.FBXIT_STATIC_MESH)
  props(opt.static_mesh_import_data,combine_meshes=True,auto_generate_collision=False,generate_lightmap_u_vs=False,normal_import_method=u.FBXNormalImportMethod.FBXNIM_IMPORT_NORMALS)
  task.options=opt;u.AssetToolsHelpers.get_asset_tools().import_asset_tasks([task]);mesh=u.load_asset(DEST+'/'+name);assert mesh
  for i in [1,2]:assert sm.import_lod(mesh,i,str(out/f'SM_ForestInterior_LOD{i}.fbx'))==i
  assert sm.set_lod_screen_sizes(mesh,[1.,.065,.025]);sm.remove_collisions(mesh)
  ns=sm.get_nanite_settings(mesh);ns.enabled=False;sm.set_nanite_settings(mesh,ns,True)
 m=u.load_asset(DEST+'/M_ForestInterior') or u.AssetToolsHelpers.get_asset_tools().create_asset('M_ForestInterior',DEST,u.Material,u.MaterialFactoryNew())
 mel.delete_all_material_expressions(m);g=Graph(m,'ForestInterior')
 props(m,blend_mode=u.BlendMode.BLEND_OPAQUE,shading_model=u.MaterialShadingModel.MSM_DEFAULT_LIT,two_sided=False,tangent_space_normal=False,dithered_lod_transition=True)
 from perceived_tree_proxy import position
 origin=position(g,g.vector((0,0,0)),u.MaterialPositionTransformSource.TRANSFORMPOSSOURCE_INSTANCE,u.MaterialPositionTransformSource.TRANSFORMPOSSOURCE_WORLD)
 n=g.node(u.MaterialExpressionVertexNormalWS);mpc=u.load_asset(BASE+'/FirewatchStyle/MPC_DistanceStyle')
 colour=g.custom(['N','Forest','Shadow','Rand'],'float top=saturate(N.z*.55+.45);return lerp(Shadow,Forest,top)*lerp(.90,1.05,Rand);')
 for a,key in [(n,'N'),(g.node(u.MaterialExpressionCollectionParameter,collection=mpc,parameter_name='ForestColour'),'Forest'),(g.node(u.MaterialExpressionCollectionParameter,collection=mpc,parameter_name='ShadowColour'),'Shadow'),(g.node(u.MaterialExpressionPerInstanceRandom),'Rand')]:g.wire(a,colour,key)
 g.output(colour,u.MaterialProperty.MP_BASE_COLOR);g.output(n,u.MaterialProperty.MP_NORMAL)
 ao=g.custom(['N'],'return .58+.42*saturate(N.z*.5+.5);',u.CustomMaterialOutputType.CMOT_FLOAT1);g.wire(n,ao,'N');g.output(ao,u.MaterialProperty.MP_AMBIENT_OCCLUSION)
 fade=g.custom(['P','Origin','Camera'],'float d=length(Camera-Origin);float a=smoothstep(14000,24000,d)*(1-smoothstep(95000,130000,d));return (P-Origin)*(a-1);')
 for a,key in [(g.node(u.MaterialExpressionWorldPosition),'P'),(origin,'Origin'),(g.node(u.MaterialExpressionCameraPositionWS),'Camera')]:g.wire(a,fade,key)
 g.output(fade,u.MaterialProperty.MP_WORLD_POSITION_OFFSET);g.output(g.scalar(.94),u.MaterialProperty.MP_ROUGHNESS);g.output(g.scalar(.04),u.MaterialProperty.MP_SPECULAR)
 mel.set_material_usage(m,u.MaterialUsage.MATUSAGE_INSTANCED_STATIC_MESHES);assert not mel.recompile_material(m);assert assets.save_loaded_asset(m,False)
 mesh.set_material(0,m);assert assets.save_loaded_asset(mesh,False)
 counts=[mesh.get_static_mesh_description(i).get_triangle_count() for i in range(sm.get_lod_count(mesh))];assert counts==[120,80,60],counts
 assert 350<mesh.get_bounds().box_extent.z*2<600, str(mesh.get_bounds())
 return mesh,counts
def placements():
 raw=json.loads((QA/'placements.json').read_text());grid={}
 for t in raw['trees']:grid.setdefault((math.floor(t[0]/2500),math.floor(t[1]/2500)),[]).append(t)
 cells={};rr=random.Random(1907)
 # Both bush and tree roots are already grounded and excluded from roads.
 # Tree-root anchors cover the interior where detailed ferns have culled out.
 shrubs=list(raw['shrubs'])+list(raw['trees']);rr.shuffle(shrubs)
 for s in shrubs:
  cell=(math.floor(s[0]/2500),math.floor(s[1]/2500))
  if cell in cells:continue
  nearby=[t for dx in [-1,0,1] for dy in [-1,0,1] for t in grid.get((cell[0]+dx,cell[1]+dy),[]) if (t[0]-s[0])**2+(t[1]-s[1])**2<1800**2 and abs(t[2]-s[2])<1200]
  if not nearby:continue
  # Existing woody plant roots provide grounding and established clearances.
  # Irregular gaps keep a sparse mid-storey rather than a continuous hedge.
  if rr.random()<.22:continue
  cells[cell]=s
 candidates=list(cells.values());rr.shuffle(candidates);candidates=candidates[:9000]
 # Build broken thickets around each seed from existing nearby root anchors.
 # This concentrates coverage into stands instead of scattering single dots.
 grouped=[];used=set()
 for s in candidates:
  cell=(math.floor(s[0]/2500),math.floor(s[1]/2500))
  neighbors=[t for dx in [-1,0,1] for dy in [-1,0,1] for t in grid.get((cell[0]+dx,cell[1]+dy),[]) if 350**2<(t[0]-s[0])**2+(t[1]-s[1])**2<1050**2 and abs(t[2]-s[2])<600]
  rr.shuffle(neighbors)
  for t in [s]+neighbors[:2]:
   key=(round(t[0]),round(t[1]))
   if key not in used:used.add(key);grouped.append(t)
 candidates=grouped[:22000]
 result=[]
 for s in candidates:
  scale=rr.uniform(.48,.78)
  cell=(math.floor(s[0]/2500),math.floor(s[1]/2500))
  near=[t[2] for dx in [-1,0,1] for dy in [-1,0,1] for t in grid.get((cell[0]+dx,cell[1]+dy),[]) if (t[0]-s[0])**2+(t[1]-s[1])**2<(500*scale)**2 and abs(t[2]-s[2])<500]
  base=s[2]-25
  result.append(u.Transform(location=u.Vector(s[0],s[1],base),rotation=u.Rotator(yaw=rr.uniform(0,360)),scale=u.Vector(scale,scale*rr.uniform(.8,1.18),rr.uniform(.22,.36))))
 assert result
 return result,dict(source_woody_plants=len(shrubs),candidate_cells=len(cells),clusters=len(result),cell_metres=25,max_clusters=22000,grounding='Upright plants at existing rooted tree/shrub elevations; 25 cm embed')
def interior_proxy():
 # Reuse the authored elevation-aware foliage atlas instead of solid shrub blobs.
 source=u.load_asset(BASE+'/CanopyDepth/Mature/SM_CD_Proxy')
 mesh=u.load_asset(DEST+'/SM_ForestInteriorBroadleaf') or assets.duplicate_asset(source.get_path_name().split('.')[0],DEST+'/SM_ForestInteriorBroadleaf')
 sm.remove_collisions(mesh);assert sm.set_lod_screen_sizes(mesh,[1.])
 # Use a standalone card and bounds that cover every WPO-facing direction.
 bake=json.loads((ROOT/'Art/Export/LidarStudy/CanopyDepth/Mature/tree-bake.json').read_text())
 mesh.set_editor_property('positive_bounds_extension',u.Vector());mesh.set_editor_property('negative_bounds_extension',u.Vector())
 b=mesh.get_bounds();r=bake['size_cm']*.71;c=bake['centre'];origin=[b.origin.x,b.origin.y,b.origin.z];ext=[b.box_extent.x,b.box_extent.y,b.box_extent.z]
 mesh.set_editor_property('positive_bounds_extension',u.Vector(*[max(0,x+r-(o+e)) for x,o,e in zip(c,origin,ext)]))
 mesh.set_editor_property('negative_bounds_extension',u.Vector(*[max(0,(o-e)-(x-r)) for x,o,e in zip(c,origin,ext)]))
 path=DEST+'/M_ForestInteriorBroadleaf'
 # Refresh the independent proxy from the final canopy shader on each install.
 if u.load_asset(path):assert assets.delete_asset(path)
 m=assets.duplicate_asset(STYLE+'/M_EvergreenProxy_Mature',path);g=Graph(m,'ForestInteriorProxy')
 from perceived_tree_proxy import position
 origin=position(g,g.vector((0,0,0)),u.MaterialPositionTransformSource.TRANSFORMPOSSOURCE_INSTANCE,u.MaterialPositionTransformSource.TRANSFORMPOSSOURCE_WORLD)
 old=mel.get_material_property_input_node(m,u.MaterialProperty.MP_WORLD_POSITION_OFFSET);out=str(mel.get_material_property_input_node_output_name(m,u.MaterialProperty.MP_WORLD_POSITION_OFFSET))
 fade=g.custom(['P','WPO','Origin','Camera'],'float d=length(Camera-Origin);float a=smoothstep(14000,24000,d)*(1-smoothstep(95000,130000,d));return (P+WPO-Origin)*a+Origin-P;')
 for node,pin,o in [(g.node(u.MaterialExpressionWorldPosition),'P',''),(old,'WPO',out),(origin,'Origin',''),(g.node(u.MaterialExpressionCameraPositionWS),'Camera','')]:g.wire(node,fade,pin,o)
 g.output(fade,u.MaterialProperty.MP_WORLD_POSITION_OFFSET)
 base=mel.get_material_property_input_node(m,u.MaterialProperty.MP_BASE_COLOR);out=str(mel.get_material_property_input_node_output_name(m,u.MaterialProperty.MP_BASE_COLOR))
 shade=g.node(u.MaterialExpressionMultiply);g.wire(base,shade,'A',out);g.wire(g.scalar(.65),shade,'B');g.output(shade,u.MaterialProperty.MP_BASE_COLOR)
 assert not mel.recompile_material(m);assert assets.save_loaded_asset(m,False)
 for i in range(len(mesh.get_editor_property('static_materials'))):mesh.set_material(i,m)
 assert assets.save_loaded_asset(mesh,False)
 counts=[mesh.get_static_mesh_description(0).get_triangle_count()];assert counts==[2]
 return mesh,counts
def install():
 assets.make_directory(DEST)
 folder=QA/'Before';folder.mkdir(exist_ok=True)
 names=['M_EvergreenFoliage']+['M_EvergreenProxy_'+k for k in ['Mature','Pole','Edge']]
 for name in names+['DA_Lidar_Evergreen']:
  src=ROOT/'Content/GrandTour/ArtTests/LidarStudy/CohesiveStyle'/(name+'.uasset')
  if not (folder/src.name).exists():shutil.copy2(src,folder/src.name)
 protected=[ROOT/'Content/GrandTour/ArtTests/LidarStudy'/x for x in ['L_LidarStudy.umap','CohesiveStyle/M_EvergreenTerrain.uasset','CohesiveStyle/M_EvergreenDetail.uasset','CohesiveStyle/M_EvergreenHaze.uasset','CohesiveStyle/MPC_PaletteFinish.uasset','FirewatchStyle/MPC_DistanceStyle.uasset']]
 hashes={str(p):sha(p) for p in protected}
 p=u.load_asset(STYLE+'/DA_Lidar_Evergreen')
 from refine_palette import VALUES
 keys=list(VALUES)+['strength','normal_simplification','palette_strength','crown_definition','haze_intensity','haze_start_metres','haze_full_metres','surface_detail_strength','surface_parallax_strength']
 palette={k:p.get_editor_property(k) for k in keys}
 mpc=u.load_asset(DEST+'/MPC_CanopyDepth') or u.AssetToolsHelpers.get_asset_tools().create_asset('MPC_CanopyDepth',DEST,u.MaterialParameterCollection,u.MaterialParameterCollectionFactoryNew())
 if not list(mpc.get_editor_property('scalar_parameters')):mpc.set_editor_property('scalar_parameters',[props(u.CollectionScalarParameter(),parameter_name='DepthStrength',default_value=0)])
 assert assets.save_loaded_asset(mpc,False)
 audit=json.loads((QA/'shader-audit.json').read_text());materials=[]
 for name in names:
  m=u.load_asset(STYLE+'/'+name);n=next(x for x in connected_nodes(m) if isinstance(x,u.MaterialExpressionCustom) and str(x.get_editor_property('desc'))=='FirewatchDistance')
  code=next(x['code'] for x in audit[name] if x['desc']=='FirewatchDistance')
  assert 'AO=lerp(OldAO,1,fade)' in code and 'NormalSimplification' in code
  code=code.replace('fade*NormalSimplification','fade*NormalSimplification*lerp(1,.20,DepthStrength)')
  code=code.replace('AO=lerp(OldAO,1,fade)','AO=lerp(OldAO,1,fade*(1-DepthStrength*.90))')
  code=code.replace('palette*definition','palette*definition*lerp(1,.20,DepthStrength)')
  code=code.replace('float d=length(P-Camera);','''float d=length(P-Camera);
float3 crownDelta=CrownP-CrownCentre-float3(0,0,CrownRadius*.20);
float3 volumeNormal=normalize(crownDelta*float3(1,1,1.6)+float3(0,0,.01));
N=normalize(lerp(N,volumeNormal,DepthStrength*.38*smoothstep(14000,28000,d)));
''')
  if name=='M_EvergreenFoliage':code=code.replace('DepthStrength*.38*smoothstep','DepthStrength*0*smoothstep')
  marker='float3 coordinated=lerp('
  assert marker in code
  code=code.replace(marker,'''// Retain individual crown orientation within the stand envelope.
float localCrown=smoothstep(-.30,.80,dot(normalize(N),normalize(SunDirection.rgb)));
float localTop=smoothstep(-.20,.65,normalize(N).z);
float localShade=lerp(.42,1,sqrt(saturate(localCrown*localTop)));
crownLight*=lerp(1,localShade,DepthStrength*.85);
float3 coordinated=lerp(''')
  code=code.replace('return lerp(legacy,coordinated,palette);','return lerp(legacy,coordinated,palette)*lerp(1,lerp(.72,1,saturate(OldAO)),DepthStrength*palette*.55);')
  g=Graph(m,'CanopyInterior');inputs=list(n.get_editor_property('inputs'))
  if 'DepthStrength' not in [str(x.get_editor_property('input_name')) for x in inputs]:
   inputs.append(props(u.CustomInput(),input_name='DepthStrength'));n.set_editor_property('inputs',inputs)
   g.wire(g.node(u.MaterialExpressionCollectionParameter,collection=mpc,parameter_name='DepthStrength'),n,'DepthStrength')
  from perceived_tree_proxy import position
  kind=name.rsplit('_',1)[-1]
  bake=json.loads((ROOT/'Art/Export/LidarStudy/CanopyDepth'/kind/'tree-bake.json').read_text()) if kind in ['Mature','Pole','Edge'] else dict(centre=[0,0,1200],size_cm=2000)
  centre=position(g,g.vector(bake['centre']),u.MaterialPositionTransformSource.TRANSFORMPOSSOURCE_INSTANCE,u.MaterialPositionTransformSource.TRANSFORMPOSSOURCE_WORLD)
  extra={'CrownCentre':centre,'CrownRadius':g.scalar(bake['size_cm']*.6)}
  for key,a in extra.items():
   rows=list(n.get_editor_property('inputs'))
   if key not in [str(x.get_editor_property('input_name')) for x in rows]:
    n.set_editor_property('inputs',rows+[props(u.CustomInput(),input_name=key)])
   g.wire(a,n,key)
  rows=list(n.get_editor_property('inputs'))
  if 'CrownP' not in [str(x.get_editor_property('input_name')) for x in rows]:
   n.set_editor_property('inputs',rows+[props(u.CustomInput(),input_name='CrownP')])
   capture=next((x for x in connected_nodes(m) if isinstance(x,u.MaterialExpressionCustom) and 'LocalSurface=Centre' in x.get_editor_property('code')),None)
   surface=position(g,capture,u.MaterialPositionTransformSource.TRANSFORMPOSSOURCE_INSTANCE,u.MaterialPositionTransformSource.TRANSFORMPOSSOURCE_WORLD,'LocalSurface') if capture else g.node(u.MaterialExpressionWorldPosition)
   g.wire(surface,n,'CrownP')
  n.set_editor_property('code',code);assert not mel.recompile_material(m);assert assets.save_loaded_asset(m,False)
  materials.append(name)
 mesh,counts=interior_proxy();transforms,placement_info=placements()
 data=u.load_asset(DEST+'/DA_ForestInterior') or u.AssetToolsHelpers.get_asset_tools().create_asset('DA_ForestInterior',DEST,u.GTForestInteriorData,props(u.DataAssetFactory(),data_asset_class=u.GTForestInteriorData))
 props(data,mesh=mesh,placements=transforms);assert assets.save_loaded_asset(data,False)
 props(p,canopy_depth_strength=1,forest_interior=data);assert assets.save_loaded_asset(p,False)
 assert all(p.get_editor_property(k)==v for k,v in palette.items()),'Palette or existing surface controls changed'
 assert all(sha(Path(path))==digest for path,digest in hashes.items()),'Protected map, palette, haze or ground changed'
 return dict(ok=True,palette_and_fog_unchanged=True,protected=hashes,materials=materials,placements=placement_info,triangles_per_lod=counts,added_tree_triangles=0,added_crown_texture_samples=0,interior_atlases='Reuses existing Mature colour/normal-depth and canopy lighting textures; no new texture residency',collision=False,dynamic_shadows=False,ray_tracing=False,cull_metres=[950,1300],near_reveal_metres=[140,240],performance_verified=False)
if __name__=='__main__':
 stage=os.environ.get('GT_CANOPY_INTERIOR_STAGE','audit')
 try:result=audit() if stage=='audit' else install()
 except Exception:result=dict(ok=False,error=traceback.format_exc());u.log_error(result['error'])
 (QA/(stage+'.json')).write_text(json.dumps(result,indent=2));u.SystemLibrary.quit_editor()
