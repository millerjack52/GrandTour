"""Fixed ground distribution comparisons using the existing mud review harness."""
from pathlib import Path
R=Path('C:/GrandTour');text=(R/'Art/Unreal/trial_flora_mud.py').read_text()
changes={
 'from flora_mud_trial_baseline import verify':'from flora_pine_brush_baseline import verify',
 'import flora_mud_trial_materials as mat':'import flora_mud_trial_materials as mat\nimport flora_ground_patches as ground\nimport flora_woodland_materials as wood\nimport flora_woodland_mud as brown',
 "O=R/'Art/Export/FloraTrail/MudTrial'":"O=ground.O",
 "stage=os.environ.get('GT_MUD_TRIAL_STAGE','screen')":"stage=os.environ.get('GT_GROUND_PATCH_STAGE','candidate')",
 "rows=json.loads((O/'sources.json').read_text())":"rows=json.loads((R/'Art/Export/FloraTrail/MudTrial/sources.json').read_text())",
}
for a,b in changes.items():assert text.count(a)==1,a;text=text.replace(a,b)
a=text.index(" if stage=='screen':");b=text.index(' # Wait for asynchronously',a)
text=text[:a]+'''
 row=next(r for r in rows if r['id']=='brown_mud_02');selected=[row]
 assert L.load_level(ground.BASE);world=u.get_editor_subsystem(u.UnrealEditorSubsystem).get_editor_world()
 geometry=ground.geometry(world);lighting=wood.audit_saved_lighting(world)
 origins={(a,c.get_name(),i):m.get_path_name() for a,c,i,m,role in wood.slots(world)}
 if stage!='verify':
  ground.install(world)
  assert u.EditorLoadingAndSavingUtils.save_map(world,ground.MAP)
 assert L.load_level('/Engine/Maps/Entry');assert L.load_level(ground.MAP)
 world=u.get_editor_subsystem(u.UnrealEditorSubsystem).get_editor_world()
 assert ground.geometry(world)==geometry;report['geometry_and_instances_unchanged']=True
 assert wood.audit_saved_lighting(world)==lighting;report['saved_lighting']=lighting
 assert {(a,c.get_name(),i):m.get_path_name() for a,c,i,m,role in wood.slots(world)}==origins
 report['foliage_bark_rock_materials_preserved']=True;report['ground_materials']=ground.audit(world)
 surface=next(a for a in A.get_all_level_actors() if isinstance(a,u.GTLandscapeSurface))
 assert surface.simulated_water.get_editor_property('surface_material_path')==D+'/M_WaterFlat.M_WaterFlat'
 report['flat_water_preserved']=True
 textures={row['id']:{role:u.load_asset(D+'/Textures/T_'+row['id']+'_'+role+'_native') for role in ('color','normal','height','roughness')}}
 cases=[(name,row,1.) for name in ground.PROFILES] if stage=='candidate' else [(ground.CFG['selected'],row,1.)]
 detailtextures={}
 for material in (surface.landscape.landscape_material,u.load_asset(ground.D+'/M_GroundPatchesMud')):
  for node in M.get_material_expressions(material):
   if isinstance(node,u.MaterialExpressionTextureSample):
    tex=node.get_editor_property('texture')
    if tex and tex.get_name().startswith('T_ForestGround_'):detailtextures[tex.get_path_name()]=tex
 cmd('r.Streaming.FullyLoadUsedTextures 1');deadline=time.monotonic()+180
 assert len(detailtextures)==6
 for path,tex in detailtextures.items():
  while tex.blueprint_get_size_x()<2048:
   assert time.monotonic()<deadline,path;yield .5
 report['floor_texture_dimensions']={p:[t.blueprint_get_size_x(),t.blueprint_get_size_y()] for p,t in detailtextures.items()}
 report['saved_map']=ground.MAP
 root=R/'Content'/ground.D.removeprefix('/Game/')
 report['candidate_hashes']={p.name:hashlib.sha256(p.read_bytes()).hexdigest() for p in root.rglob('*') if p.is_file()}
''' +text[b:]
old=" report['live_dynamic_materials']=[m.get_path_name() for m in mids]"
text=text.replace(old,old+'''
 landscape=surface.landscape
 terrain_mids=[c.get_material_instance_dynamic(0) for c in landscape.get_components_by_class(u.LandscapeComponent)]
 terrain_mids=[m for m in terrain_mids if m]
 assert terrain_mids
 report['saved_ground_strength']=[m.get_scalar_parameter_value('GroundPatchStrength') for m in mids+terrain_mids]
 assert all(abs(v-ground.SELECTED)<1e-5 for v in report['saved_ground_strength'])
''')
text=text.replace(" report['views']=[", " views=[v for v in views if v[0]=='drive']+[('bank',[150,centre(150)-200,160],[650,centre(650)-500,40]),('floor',[150,centre(150)-180,105],[420,centre(420)-490,0]),('canopy',[-1200,-900,130],[1500,1300,300]),('valley',[-3600,-2700,2300],[500,500,400])]\n report['views']=[")
text=text.replace(" for name,row,enabled in cases:"," for name,row,enabled in cases:\n  if stage=='candidate':\n   landscape.set_landscape_material_scalar_parameter_value('GroundPatchStrength',ground.PROFILES[name])\n   for mid in mids:mid.set_scalar_parameter_value('GroundPatchStrength',ground.PROFILES[name])\n  report.setdefault('ground_controls',{})[name]=[m.get_scalar_parameter_value('GroundPatchStrength') for m in mids+terrain_mids]\n  assert all(abs(v-ground.PROFILES[name])<1e-5 for v in report['ground_controls'][name])")
text=text.replace("   if stage not in ('saved','verify'):mat.bind(mid,row,textures,enabled)","   tint=mid.get_vector_parameter_value('WoodlandMudTint')\n   assert max(abs(a-b) for a,b in zip([tint.r,tint.g,tint.b],brown.TINT))<1e-5")
text=text.replace("xx=-1900+i*5;yy=centre(xx);look([xx,yy,height(xx,yy)+150],[xx+1500,centre(xx+1500),height(xx+1500,centre(xx+1500))+60])", "xx=150+i*4;look([xx,centre(xx)-200,160],[xx+500,centre(xx+500)-500,40])")
text=text.replace(" report['surface_after']=", " assert report['candidate_hashes']=={p.name:hashlib.sha256(p.read_bytes()).hexdigest() for p in root.rglob('*') if p.is_file()}\n report['surface_after']=")
runtime=Path('D:/GrandTourAssets/ReviewEvidence/FloraTrail/GroundPatches/runtime.py');runtime.write_text(text)
exec(compile(text,str(runtime),'exec'),globals())
