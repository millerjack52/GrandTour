"""Coverage-only pine probes in the approved CrownForm woodland."""
from pathlib import Path
R=Path('C:/GrandTour');text=(R/'Art/Unreal/trial_flora_mud.py').read_text()
changes={
 'from flora_mud_trial_baseline import verify':'from flora_pine_brush_baseline import verify',
 'import flora_mud_trial_materials as mat':'import flora_mud_trial_materials as mat\nimport flora_pine_brush_materials as crown\nimport flora_woodland_materials as wood\nimport flora_woodland_mud as brown',
 "O=R/'Art/Export/FloraTrail/MudTrial'":"O=crown.O",
 "stage=os.environ.get('GT_MUD_TRIAL_STAGE','screen')":"stage=os.environ.get('GT_PINE_BRUSH_STAGE','candidate')",
 "rows=json.loads((O/'sources.json').read_text())":"rows=json.loads((R/'Art/Export/FloraTrail/MudTrial/sources.json').read_text())",
}
for a,b in changes.items():assert text.count(a)==1,a;text=text.replace(a,b)
a=text.index(" if stage=='screen':");b=text.index(' # Wait for asynchronously',a)
text=text[:a]+'''
 row=next(r for r in rows if r['id']=='brown_mud_02');selected=[row]
 assert L.load_level(crown.BASE);world=u.get_editor_subsystem(u.UnrealEditorSubsystem).get_editor_world()
 geometry=crown.geometry(world);lighting=wood.audit_saved_lighting(world)
 origins={(a,c.get_name(),i):m.get_path_name() for a,c,i,m,role in wood.slots(world)}
 if stage!='verify':
  for a,c,i,m,role in wood.slots(world):
   if crown.eligible(c,role):c.set_material(i,crown.clone(m))
  assert u.EditorLoadingAndSavingUtils.save_map(world,crown.MAP)
 assert L.load_level('/Engine/Maps/Entry');assert L.load_level(crown.MAP)
 world=u.get_editor_subsystem(u.UnrealEditorSubsystem).get_editor_world()
 assert crown.geometry(world)==geometry;report['geometry_and_instances_unchanged']=True
 assert wood.audit_saved_lighting(world)==lighting;report['saved_lighting']=lighting
 report['slots']=[];detailtextures={}
 for a,c,i,m,role in wood.slots(world):
  original=u.load_asset(origins[(a,c.get_name(),i)])
  if not crown.eligible(c,role):assert m==original
  else:
   assert m.get_path_name().startswith(crown.D+'/M_Brush_')
   def textures_of(mat):return {str(n.get_editor_property('parameter_name')):n.get_editor_property('texture') for n in M.get_material_expressions(mat) if isinstance(n,u.MaterialExpressionTextureSampleParameter2D)}
   assert crown.protected_outputs(m)==crown.protected_outputs(original)
   assert textures_of(m)==textures_of(original)
   detailtextures.update({t.get_path_name():t for t in textures_of(m).values()})
  report['slots'].append({'actor':a,'component':c.get_name(),'slot':i,'role':role,'material':m.get_path_name(),'mesh':c.static_mesh.get_path_name()})
  if role=='bark':
   for n in M.get_material_expressions(m):
    if isinstance(n,u.MaterialExpressionTextureSampleParameter2D):
     t=n.get_editor_property('texture')
     if t:detailtextures[t.get_path_name()]=t
 visual=next(a for a in A.get_all_level_actors() if isinstance(a,u.GTMudRunnerVisual));report['mud']=brown.audit(visual.material)
 surface=next(a for a in A.get_all_level_actors() if isinstance(a,u.GTLandscapeSurface))
 assert surface.simulated_water.get_editor_property('surface_material_path')==D+'/M_WaterFlat.M_WaterFlat'
 report['flat_water_preserved']=True;report['noncanopy_materials_preserved']=True
 textures={row['id']:{role:u.load_asset(D+'/Textures/T_'+row['id']+'_'+role+'_native') for role in ('color','normal','height','roughness')}}
 cases=[(name,row,1.) for name in crown.PROFILES] if stage=='candidate' else [(crown.CFG['selected'],row,1.)]
 cmd('r.Streaming.FullyLoadUsedTextures 1');deadline=time.monotonic()+180
 for path,t in detailtextures.items():
  expected=4096 if 'Bark' in path or 'Mask4K' in path else 2048
  while t.blueprint_get_size_x()<expected:
   assert time.monotonic()<deadline,path;yield .5
 report['source_texture_dimensions']={p:[t.blueprint_get_size_x(),t.blueprint_get_size_y()] for p,t in detailtextures.items()}
 report['saved_map']=crown.MAP;report['approved_palette_outputs_preserved']=True;report['experiment_only']=True
 root=R/'Content'/crown.D.removeprefix('/Game/')
 report['candidate_hashes']={p.name:hashlib.sha256(p.read_bytes()).hexdigest() for p in root.rglob('*') if p.is_file()}
''' +text[b:]
old=" report['live_dynamic_materials']=[m.get_path_name() for m in mids]"
text=text.replace(old,old+'''
 live=[]
 for a,c,i,m,role in wood.slots(world):
  if crown.eligible(c,role):
   mid=c.create_dynamic_material_instance(i,m);assert mid
   live.append(mid)
 assert live,'No pine materials found for comparison'
 report['saved_brush_parameters']=[crown.audit(mid) for mid in live]
 report['brush_profiles']=crown.PROFILES
''')
text=text.replace(" report['views']=[", " views=[v for v in views if v[0]=='drive']+[('bank',[150,centre(150)-200,160],[650,centre(650)-500,40]),('canopy',[-1200,-900,130],[1500,1300,300]),('crowns',[-1200,-900,130],[500,1300,1550]),('valley',[-3600,-2700,2300],[500,500,400])]\n focus=crown.focus_views(world);views+=focus;report['pine_focus_views']=focus\n report['views']=[")
text=text.replace(" for name,row,enabled in cases:"," for name,row,enabled in cases:\n  if stage=='candidate':\n   for mid in live:crown.configure(mid,crown.PROFILES[name])")
text=text.replace("   if stage not in ('saved','verify'):mat.bind(mid,row,textures,enabled)","   tint=mid.get_vector_parameter_value('WoodlandMudTint')\n   assert max(abs(a-b) for a,b in zip([tint.r,tint.g,tint.b],brown.TINT))<1e-5")
text=text.replace("xx=-1900+i*5;yy=centre(xx);look([xx,yy,height(xx,yy)+150],[xx+1500,centre(xx+1500),height(xx+1500,centre(xx+1500))+60])", "xx=-1200+i*4;look([xx,-900,130],[500,1300,1550])")
text=text.replace(" report['surface_after']=", " assert report['candidate_hashes']=={p.name:hashlib.sha256(p.read_bytes()).hexdigest() for p in root.rglob('*') if p.is_file()}\n report['surface_after']=")
runtime=Path('D:/GrandTourAssets/ReviewEvidence/FloraTrail/PineBrush/runtime.py');runtime.write_text(text)
exec(compile(text,str(runtime),'exec'),globals())
