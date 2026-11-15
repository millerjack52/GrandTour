"""Coverage/light/rock-detail isolation, followed by fresh saved-map verification."""
from pathlib import Path
R=Path('C:/GrandTour');source=R/'Art/Unreal/trial_flora_mud.py';text=source.read_text()
changes={
 'from flora_mud_trial_baseline import verify':'from flora_understory_baseline import verify',
 'import flora_mud_trial_materials as mat':'import flora_mud_trial_materials as mat\nimport flora_understory_materials as under',
 "O=R/'Art/Export/FloraTrail/MudTrial'":"O=R/'Art/Export/FloraTrail/UnderstoryStudy'",
 "stage=os.environ.get('GT_MUD_TRIAL_STAGE','screen')":"stage=os.environ.get('GT_UNDERSTORY_STAGE','candidate')",
 "rows=json.loads((O/'sources.json').read_text())":"rows=json.loads((R/'Art/Export/FloraTrail/MudTrial/sources.json').read_text())",
}
for old,new in changes.items():assert text.count(old)==1,old;text=text.replace(old,new)
a=text.index(" if stage=='screen':");b=text.index(' # Wait for asynchronously',a)
text=text[:a]+'''
 row=next(r for r in rows if r['id']=='brown_mud_02');selected=[row]
 target=under.D+'/L_FloraTrail_Understory'
 exists=E.does_asset_exist(target)
 assert L.load_level(target if stage=='verify' or exists else D+'/L_FloraTrail_Verge');world=u.get_editor_subsystem(u.UnrealEditorSubsystem).get_editor_world()
 cmd('Interchange.FeatureFlags.Import.FBX 0')
 items=under.snapshot(world);assert len(items)==16,len(items)
 if stage!='verify':
  if exists:
   oldorigins=json.loads((O/'origins.json').read_text())
   items=[(c,u.load_asset(oldorigins[c.get_name()]['mesh']),[u.load_asset(m) for m in oldorigins[c.get_name()]['materials']],count) for c,mesh,mats,count in items]
  origins={c.get_name():{'mesh':mesh.get_path_name(),'materials':[m.get_path_name() for m in mats],'count':count} for c,mesh,mats,count in items}
  (O/'origins.json').write_text(json.dumps(origins,indent=2))
  for c,mesh,mats,count in items:
   if mesh.get_name() in under.PLANTS:
    for variant in ('coverage','lighting','combined'):
     for m in mats:under.plant(m,variant,True)
 rockmeshes=under.rocks(stage!='verify')
 if stage!='verify':
  report['installed_components']=under.apply(items,'combined',rockmeshes)
  assert L.save_current_level() if exists else u.EditorLoadingAndSavingUtils.save_map(world,target)
  assert L.load_level('/Engine/Maps/Entry');assert L.load_level(target);world=u.get_editor_subsystem(u.UnrealEditorSubsystem).get_editor_world()
 report['saved_map']=target
 report['saved_components']=[{'component':c.get_name(),'mesh':mesh.get_path_name(),'materials':[m.get_path_name() for m in mats],'instances':count} for c,mesh,mats,count in under.snapshot(world)]
 origins=json.loads((O/'origins.json').read_text())
 report['geometry_audit']=[]
 S=u.get_editor_subsystem(u.StaticMeshEditorSubsystem)
 for c,mesh,mats,count in under.snapshot(world):
  origin=origins[c.get_name()];assert count==origin['count']
  assert mesh.get_path_name()==origin['mesh'] if mesh.get_name() in under.PLANTS else mesh.get_name().startswith('SM_Detail_FP_Rock')
  assert all(m.get_path_name().startswith(under.D) for m in mats)
  oldmesh=u.load_asset(origin['mesh'])
  assert S.get_lod_count(mesh)==S.get_lod_count(oldmesh)
  assert mesh.get_static_mesh_description(0).get_triangle_count()==oldmesh.get_static_mesh_description(0).get_triangle_count()
  report['geometry_audit'].append({'mesh':mesh.get_path_name(),'lods':S.get_lod_count(mesh),'triangles':mesh.get_static_mesh_description(0).get_triangle_count(),'instances':count})
  if mesh.get_name() in under.PLANTS:
   for m,oldpath in zip(mats,origin['materials']):
    def bindings(material):return {str(n.get_editor_property('parameter_name')):n.get_editor_property('texture').get_path_name() for n in M.get_material_expressions(material) if isinstance(n,u.MaterialExpressionTextureSampleParameter2D)}
    assert bindings(m)==bindings(u.load_asset(oldpath))
    emissive=M.get_material_property_input_node(m,u.MaterialProperty.MP_EMISSIVE_COLOR)
    assert isinstance(emissive,u.MaterialExpressionConstant) and emissive.get_editor_property('r')==0
 surface=next(a for a in A.get_all_level_actors() if isinstance(a,u.GTLandscapeSurface))
 assert surface.simulated_water.get_editor_property('surface_material_path')==D+'/M_WaterFlat.M_WaterFlat'
 assert surface.landscape.landscape_material.get_name()=='M_VergeLandscape'
 assert next(a for a in A.get_all_level_actors() if isinstance(a,u.GTMudRunnerVisual)).material.get_name()=='MI_VergeMud'
 textures={row['id']:{role:u.load_asset(D+'/Textures/T_'+row['id']+'_'+role+'_native') for role in ('color','normal','height','roughness')}}
 cases=[(name,row,1.) for name in ('baseline','coverage','lighting','rocks','combined')] if stage=='candidate' else [('combined',row,1.)]
 detailtextures=[u.load_asset(under.D+'/Rocks/T_'+m.get_name()) for m in rockmeshes.values()]
 for c,mesh,mats,count in under.snapshot(world):
  if mesh.get_name() in under.PLANTS:
   for m in mats:
    detailtextures.extend(n.get_editor_property('texture') for n in M.get_material_expressions(m) if isinstance(n,u.MaterialExpressionTextureSampleParameter2D))
 cmd('r.Streaming.FullyLoadUsedTextures 1');deadline=time.monotonic()+180
 for t in detailtextures:
  while t.blueprint_get_size_x()<2048:
   assert time.monotonic()<deadline,(t.get_path_name(),t.blueprint_get_size_x());yield .5
 report['detail_texture_sizes']={t.get_path_name():[t.blueprint_get_size_x(),t.blueprint_get_size_y()] for t in detailtextures}
 report['candidate_hashes_before']={p.relative_to(R/'Content').as_posix():hashlib.sha256(p.read_bytes()).hexdigest() for p in (R/'Content/GrandTour/ArtTests/FloraTrail/UnderstoryTrial').rglob('*') if p.is_file()}
''' +text[b:]
old=" report['live_dynamic_materials']=[m.get_path_name() for m in mids]"
text=text.replace(old,old+'''
 liveitems=[]
 for c,mesh,mats,count in under.snapshot(world):
  original=origins[c.get_name()];liveitems.append((c,u.load_asset(original['mesh']),[u.load_asset(m) for m in original['materials']],count))
''')
old=" report['views']=[{'name':n,'position':p,'target':t} for n,p,t in views];report['surface_before']=surface.get_surface_report()"
text=text.replace(old," views.extend([('puddle',[350,centre(350)-280,150],[850,centre(850),-5]),('verge',[150,centre(150)-200,160],[650,centre(650)-500,0]),('bank',[350,centre(350)-240,85],[650,centre(650)-320,10])])\n if stage=='candidate':views=[v for v in views if v[0] in ('verge','bank','drive')]\n"+old)
text=text.replace(" for name,row,enabled in cases:"," for name,row,enabled in cases:\n  if stage=='candidate':under.apply(liveitems,name,rockmeshes,gameplay=True)")
text=text.replace("   if stage not in ('saved','verify'):mat.bind(mid,row,textures,enabled)","   pass # Ground/water inputs remain unchanged.")
text=text.replace("xx=-1900+i*5;yy=centre(xx);look([xx,yy,height(xx,yy)+150],[xx+1500,centre(xx+1500),height(xx+1500,centre(xx+1500))+60])","xx=150+i*4;yy=centre(xx)-200;look([xx,yy,160],[xx+500,centre(xx+500)-500,0])")
text=text.replace(" if stage=='saved':\n  yield from drive_check"," if stage=='verify':\n  yield from drive_check")
old=" report['surface_after']=surface.get_surface_report();"
text=text.replace(old," assert report['candidate_hashes_before']=={p.relative_to(R/'Content').as_posix():hashlib.sha256(p.read_bytes()).hexdigest() for p in (R/'Content/GrandTour/ArtTests/FloraTrail/UnderstoryTrial').rglob('*') if p.is_file()}\n"+old)
runtime=R/'Art/Export/FloraTrail/UnderstoryStudy/runtime.py';runtime.write_text(text)
exec(compile(text,str(runtime),'exec'),globals())
