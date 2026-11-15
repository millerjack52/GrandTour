"""Staged palette, coverage, light and depth trial with fixed native captures."""
from pathlib import Path
R=Path('C:/GrandTour');p=R/'Art/Unreal/trial_flora_mud.py';text=p.read_text()
changes={
 'from flora_mud_trial_baseline import verify':'from flora_woodland_baseline import verify',
 'import flora_mud_trial_materials as mat':'import flora_mud_trial_materials as mat\nimport flora_woodland_materials as wood',
 "O=R/'Art/Export/FloraTrail/MudTrial'":"O=wood.O",
 "stage=os.environ.get('GT_MUD_TRIAL_STAGE','screen')":"stage=os.environ.get('GT_WOODLAND_STAGE','candidate')",
 "rows=json.loads((O/'sources.json').read_text())":"rows=json.loads((R/'Art/Export/FloraTrail/MudTrial/sources.json').read_text())",
}
for a,b in changes.items():assert text.count(a)==1,a;text=text.replace(a,b)
a=text.index(" if stage=='screen':");b=text.index(' # Wait for asynchronously',a)
text=text[:a]+'''
 row=next(r for r in rows if r['id']=='brown_mud_02');selected=[row]
 assert L.load_level(wood.BASE);world=u.get_editor_subsystem(u.UnrealEditorSubsystem).get_editor_world()
 geometry=wood.geometry(world)
 origins={(actor,c.get_name(),i):m.get_path_name() for actor,c,i,m,role in wood.slots(world)}
 roles={(actor,c.get_name(),i):role for actor,c,i,m,role in wood.slots(world)}
 report['source_slots']=[{'actor':k[0],'component':k[1],'slot':k[2],'material':v,'role':roles[k]} for k,v in origins.items()]
 report['source_geometry']=geometry
 if stage=='candidate':
  exists=E.does_asset_exist(wood.MAP)
  if exists:
   assert L.load_level(wood.MAP);world=u.get_editor_subsystem(u.UnrealEditorSubsystem).get_editor_world()
  for actor,c,i,m,role in wood.slots(world):
   source=u.load_asset(origins[(actor,c.get_name(),i)]);c.set_material(i,wood.clone(source,role))
  report['saved_lighting']=wood.lighting(world,True,True)
  assert wood.geometry(world)==geometry
  assert L.save_current_level() if exists else u.EditorLoadingAndSavingUtils.save_map(world,wood.MAP)
 assert L.load_level('/Engine/Maps/Entry');assert L.load_level(wood.MAP)
 world=u.get_editor_subsystem(u.UnrealEditorSubsystem).get_editor_world()
 report['reloaded_lighting']=wood.audit_saved_lighting(world)
 report['saved_geometry']=wood.geometry(world)
 assert wood.geometry(world)==geometry
 report['geometry_and_instances_unchanged']=True;report['saved_map']=wood.MAP
 report['saved_slots']=[];detailtextures={}
 for actor,c,i,m,role in wood.slots(world):
  source=u.load_asset(origins[(actor,c.get_name(),i)])
  assert m.get_path_name().startswith(wood.D+'/Materials/')
  def bindings(material):return {str(n.get_editor_property('parameter_name')):n.get_editor_property('texture') for n in M.get_material_expressions(material) if isinstance(n,u.MaterialExpressionTextureSampleParameter2D)}
  oldtex=bindings(source);newtex=bindings(m);assert oldtex==newtex
  detailtextures.update({t.get_path_name():t for t in newtex.values()})
  report['saved_slots'].append({'component':c.get_name(),'slot':i,'material':m.get_path_name(),'role':role})
 report['source_textures_preserved']=True
 surface=next(a for a in A.get_all_level_actors() if isinstance(a,u.GTLandscapeSurface))
 assert surface.simulated_water.get_editor_property('surface_material_path')==D+'/M_WaterFlat.M_WaterFlat'
 assert surface.landscape.landscape_material.get_name()=='M_VergeLandscape'
 assert next(a for a in A.get_all_level_actors() if isinstance(a,u.GTMudRunnerVisual)).material.get_name()=='MI_VergeMud'
 fern=next(c for a in A.get_all_level_actors() for c in a.get_components_by_class(u.InstancedStaticMeshComponent) if c.static_mesh and c.static_mesh.get_name()=='SM_Exact_fern')
 assert fern.get_instance_count()==159 and fern.get_material(0).get_path_name().startswith('/Game/GrandTour/ArtTests/FloraTrail/FernSurface/')
 report['original_ferns_preserved']=True
 textures={row['id']:{role:u.load_asset(D+'/Textures/T_'+row['id']+'_'+role+'_native') for role in ('color','normal','height','roughness')}}
 cases=[(name,row,1.) for name in ('baseline','materials','coverage','lighting','final','reverse_light')] if stage=='candidate' else [('final',row,1.)]
 cmd('r.Streaming.FullyLoadUsedTextures 1');deadline=time.monotonic()+180
 for path,t in detailtextures.items():
  expected=4096 if 'Bark' in path or 'Mask4K' in path else 2048
  while t.blueprint_get_size_x()<expected:
   assert time.monotonic()<deadline,(path,expected,t.blueprint_get_size_x());yield .5
 report['source_texture_dimensions']={path:[t.blueprint_get_size_x(),t.blueprint_get_size_y()] for path,t in detailtextures.items()}
 report['candidate_hashes_before']={p.relative_to(R/'Content').as_posix():hashlib.sha256(p.read_bytes()).hexdigest() for p in (R/'Content/GrandTour/ArtTests/FloraTrail/Woodland').rglob('*') if p.is_file()}
''' +text[b:]
old=" report['live_dynamic_materials']=[m.get_path_name() for m in mids]"
text=text.replace(old,old+'''
 live=[]
 for actor,c,i,m,role in wood.slots(world):
  original=u.load_asset(origins[(actor,c.get_name(),i)])
  mid=c.create_dynamic_material_instance(i,m);assert mid
  live.append((c,i,original,mid,role))
''')
old=" report['views']=[{'name':n,'position':p,'target':t} for n,p,t in views];report['surface_before']=surface.get_surface_report()"
text=text.replace(old," views=[v for v in views if v[0]=='drive']+[('bank',[150,centre(150)-200,160],[650,centre(650)-500,40]),('canopy',[-1200,-900,130],[1500,1300,300]),('crowns',[-1200,-900,130],[500,1300,1550]),('valley',[-3600,-2700,2300],[500,500,400])]\n"+old)
text=text.replace(" for name,row,enabled in cases:"," for name,row,enabled in cases:\n  for c,i,original,mid,role in live:\n   c.set_material(i,original if name=='baseline' else mid)\n   if role=='canopy':mid.set_scalar_parameter_value('WoodlandStableCoverage',0. if name=='materials' else 1.)\n  report.setdefault('lighting_cases',{})[name]=wood.audit_saved_lighting(world) if stage=='verify' else wood.lighting(world,name in ('lighting','final','reverse_light'),name in ('final','reverse_light'),name=='reverse_light')")
text=text.replace("   if stage not in ('saved','verify'):mat.bind(mid,row,textures,enabled)","   pass # Ground deformation and water unchanged.")
text=text.replace("  for view,pos,target in views:\n   look", "  for view,pos,target in views:\n   if name=='reverse_light' and view not in ('drive','bank','canopy'):continue\n   look")
text=text.replace("  for i in range(48):", "  for i in range(48 if name in ('baseline','final') else 0):")
text=text.replace("xx=-1900+i*5;yy=centre(xx);look([xx,yy,height(xx,yy)+150],[xx+1500,centre(xx+1500),height(xx+1500,centre(xx+1500))+60])","xx=150+i*4;yy=centre(xx)-200;look([xx,yy,160],[xx+500,centre(xx+500)-500,40])")
old=" report['surface_after']=surface.get_surface_report();"
text=text.replace(old," assert report['candidate_hashes_before']=={p.relative_to(R/'Content').as_posix():hashlib.sha256(p.read_bytes()).hexdigest() for p in (R/'Content/GrandTour/ArtTests/FloraTrail/Woodland').rglob('*') if p.is_file()}\n"+old)
runtime=Path('D:/GrandTourAssets/ReviewEvidence/FloraTrail/Woodland/runtime.py');runtime.write_text(text)
exec(compile(text,str(runtime),'exec'),globals())
