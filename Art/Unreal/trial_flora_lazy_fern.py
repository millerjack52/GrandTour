"""Use the established fixed-camera/motion harness for the owned fern model."""
from pathlib import Path
R=Path('C:/GrandTour');p=R/'Art/Unreal/trial_flora_mud.py';text=p.read_text()
changes={
 'from flora_mud_trial_baseline import verify':'from flora_lazy_fern_baseline import verify',
 'import flora_mud_trial_materials as mat':'import flora_mud_trial_materials as mat\nimport flora_lazy_fern as fern',
 "O=R/'Art/Export/FloraTrail/MudTrial'":"O=fern.O",
 "stage=os.environ.get('GT_MUD_TRIAL_STAGE','screen')":"stage=os.environ.get('GT_LAZY_FERN_STAGE','candidate')",
 "rows=json.loads((O/'sources.json').read_text())":"rows=json.loads((R/'Art/Export/FloraTrail/MudTrial/sources.json').read_text())",
}
for a,b in changes.items():assert text.count(a)==1,a;text=text.replace(a,b)
a=text.index(" if stage=='screen':");b=text.index(' # Wait for asynchronously',a)
text=text[:a]+'''
 row=next(r for r in rows if r['id']=='brown_mud_02');selected=[row]
 assert L.load_level(fern.BASE);world=u.get_editor_subsystem(u.UnrealEditorSubsystem).get_editor_world()
 signature=fern.signature(world);c=fern.component(world)
 old_mesh=c.static_mesh;old_material=c.get_material(0)
 report['baseline_fern']={'mesh':old_mesh.get_path_name(),'material':old_material.get_path_name(),'bounds':old_mesh.get_bounds().box_extent.to_tuple()}
 if stage=='candidate':
  exists=E.does_asset_exist(fern.MAP)
  if exists:
   assert L.load_level(fern.MAP);world=u.get_editor_subsystem(u.UnrealEditorSubsystem).get_editor_world();c=fern.component(world)
   assert fern.signature(world)==signature
  mesh,material=fern.build(world);c.set_static_mesh(mesh);c.set_material(0,material)
  assert fern.signature(world)==signature
  assert L.save_current_level() if exists else u.EditorLoadingAndSavingUtils.save_map(world,fern.MAP)
 assert L.load_level('/Engine/Maps/Entry');assert L.load_level(fern.MAP)
 world=u.get_editor_subsystem(u.UnrealEditorSubsystem).get_editor_world()
 assert fern.signature(world)==signature
 c=fern.component(world);mesh=c.static_mesh;material=c.get_material(0)
 assert mesh.get_path_name()==fern.D+'/SM_LazyFern02.SM_LazyFern02'
 assert material.get_path_name()==fern.D+'/M_LazyFern.M_LazyFern'
 report['fern']={'mesh':mesh.get_path_name(),'lods':u.get_editor_subsystem(u.StaticMeshEditorSubsystem).get_lod_count(mesh),'instances':c.get_instance_count(),'triangles':mesh.get_static_mesh_description(0).get_triangle_count(),'bounds':mesh.get_bounds().box_extent.to_tuple()}
 assert report['fern']['lods']==3 and report['fern']['instances']==159 and report['fern']['triangles']==2816
 report['other_scene_components_and_instance_transforms_unchanged']=True;report['saved_map']=fern.MAP
 surface=next(a for a in A.get_all_level_actors() if isinstance(a,u.GTLandscapeSurface))
 assert surface.simulated_water.get_editor_property('surface_material_path')==D+'/M_WaterFlat.M_WaterFlat'
 assert surface.landscape.landscape_material.get_name()=='M_VergeLandscape'
 assert next(a for a in A.get_all_level_actors() if isinstance(a,u.GTMudRunnerVisual)).material.get_name()=='MI_VergeMud'
 textures={row['id']:{role:u.load_asset(D+'/Textures/T_'+row['id']+'_'+role+'_native') for role in ('color','normal','height','roughness')}}
 cases=[(name,row,1.) for name in ('baseline','lazy_fern')] if stage=='candidate' else [('lazy_fern',row,1.)]
 cmd('r.Streaming.FullyLoadUsedTextures 1');deadline=time.monotonic()+180
 report['fern_textures']={}
 for role in ('Colour','Coverage','Normal','Transmission'):
  t=u.load_asset(fern.D+'/T_LazyFern_'+role)
  while t.blueprint_get_size_x()!=4096:
   assert time.monotonic()<deadline,role;yield .5
  report['fern_textures'][role]={'size':[t.blueprint_get_size_x(),t.blueprint_get_size_y()],'srgb':t.get_editor_property('srgb'),'source_sha256':E.get_metadata_tag(t,'SourceSHA256')}
 report['candidate_hashes_before']={p.relative_to(R/'Content').as_posix():hashlib.sha256(p.read_bytes()).hexdigest() for p in (R/'Content/GrandTour/ArtTests/FloraTrail/LazyFern').rglob('*') if p.is_file()}
''' +text[b:]
old=" report['live_dynamic_materials']=[m.get_path_name() for m in mids]"
text=text.replace(old,old+'''
 fern_component=fern.component(world)
 if stage=='candidate':fern_component.set_mobility(u.ComponentMobility.MOVABLE)
 positions=[fern_component.get_instance_transform(i,True).translation for i in range(fern_component.get_instance_count())]
 fern_target=min(positions,key=lambda p:math.dist((p.x,p.y),(450,-250)))
 report['close_fern_position']=fern_target.to_tuple()
''')
old=" report['views']=[{'name':n,'position':p,'target':t} for n,p,t in views];report['surface_before']=surface.get_surface_report()"
text=text.replace(old," fx,fy,fz=fern_target.to_tuple()\n views=[v for v in views if v[0]=='drive']+[('verge',[150,centre(150)-200,160],[650,centre(650)-500,0]),('fern',[fx-120,fy+180,fz+130],[fx,fy,fz+35])]\n"+old)
text=text.replace(" for name,row,enabled in cases:"," for name,row,enabled in cases:\n  wanted=old_mesh if name=='baseline' else mesh\n  fern_component.set_static_mesh(wanted)\n  assert fern_component.static_mesh==wanted, 'Live mesh swap failed'\n  fern_component.set_material(0,old_material if name=='baseline' else material)")
text=text.replace("   if stage not in ('saved','verify'):mat.bind(mid,row,textures,enabled)","   pass # Ground and water stay unchanged.")
text=text.replace("xx=-1900+i*5;yy=centre(xx);look([xx,yy,height(xx,yy)+150],[xx+1500,centre(xx+1500),height(xx+1500,centre(xx+1500))+60])","xx=150+i*4;yy=centre(xx)-200;look([xx,yy,160],[xx+500,centre(xx+500)-500,0])")
old=" report['surface_after']=surface.get_surface_report();"
text=text.replace(old," assert report['candidate_hashes_before']=={p.relative_to(R/'Content').as_posix():hashlib.sha256(p.read_bytes()).hexdigest() for p in (R/'Content/GrandTour/ArtTests/FloraTrail/LazyFern').rglob('*') if p.is_file()}\n"+old)
runtime=Path('D:/GrandTourAssets/ReviewEvidence/FloraTrail/LazyFern/runtime.py');runtime.write_text(text)
exec(compile(text,str(runtime),'exec'),globals())
