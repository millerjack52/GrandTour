"""Saved/reloaded pigment-only mud comparison using the existing native harness."""
from pathlib import Path
R=Path('C:/GrandTour');text=(R/'Art/Unreal/trial_flora_mud.py').read_text()
changes={
 'from flora_mud_trial_baseline import verify':'from flora_woodland_mud_baseline import verify',
 'import flora_mud_trial_materials as mat':'import flora_mud_trial_materials as mat\nimport flora_woodland_materials as wood\nimport flora_woodland_mud as brown',
 "O=R/'Art/Export/FloraTrail/MudTrial'":"O=brown.O",
 "stage=os.environ.get('GT_MUD_TRIAL_STAGE','screen')":"stage=os.environ.get('GT_WOODLAND_MUD_STAGE','candidate')",
 "rows=json.loads((O/'sources.json').read_text())":"rows=json.loads((R/'Art/Export/FloraTrail/MudTrial/sources.json').read_text())",
}
for a,b in changes.items():assert text.count(a)==1,a;text=text.replace(a,b)
a=text.index(" if stage=='screen':");b=text.index(' # Wait for asynchronously',a)
text=text[:a]+'''
 row=next(r for r in rows if r['id']=='brown_mud_02');selected=[row]
 assert L.load_level(wood.MAP);world=u.get_editor_subsystem(u.UnrealEditorSubsystem).get_editor_world()
 geometry=wood.geometry(world)
 lighting=wood.audit_saved_lighting(world)
 if stage=='candidate':
  mi=brown.build()
  visual=next(a for a in A.get_all_level_actors() if isinstance(a,u.GTMudRunnerVisual))
  visual.set_editor_property('material',mi)
  assert u.EditorLoadingAndSavingUtils.save_map(world,brown.MAP)
 assert L.load_level('/Engine/Maps/Entry');assert L.load_level(brown.MAP)
 world=u.get_editor_subsystem(u.UnrealEditorSubsystem).get_editor_world()
 actual=json.dumps(wood.geometry(world)).replace(brown.MAP+'.L_FloraTrail_BrownMud','<ReviewWorld>').replace(brown.MAP,'<ReviewMap>')
 assert json.loads(actual)==geometry
 assert wood.audit_saved_lighting(world)==lighting
 visual=next(a for a in A.get_all_level_actors() if isinstance(a,u.GTMudRunnerVisual))
 assert visual.material.get_path_name()==brown.D+'/MI_WoodlandBrownMud.MI_WoodlandBrownMud'
 report['material_audit']=brown.audit(visual.material)
 surface=next(a for a in A.get_all_level_actors() if isinstance(a,u.GTLandscapeSurface))
 assert surface.simulated_water.get_editor_property('surface_material_path')==D+'/M_WaterFlat.M_WaterFlat'
 report['geometry_and_lighting_unchanged']=True;report['flat_water_preserved']=True
 textures={row['id']:{role:u.load_asset(D+'/Textures/T_'+row['id']+'_'+role+'_native') for role in ('color','normal','height','roughness')}}
 cases=[(name,row,1.) for name in ('before','brown')] if stage=='candidate' else [('brown',row,1.)]
 report['saved_map']=brown.MAP
 report['brown_hashes']={p.name:hashlib.sha256(p.read_bytes()).hexdigest() for p in (R/'Content/GrandTour/ArtTests/FloraTrail/Woodland/BrownMud').rglob('*') if p.is_file()}
''' +text[b:]
old="   if stage not in ('saved','verify'):mat.bind(mid,row,textures,enabled)"
text=text.replace(old,"   if stage=='candidate':mid.set_vector_parameter_value('WoodlandMudTint',u.LinearColor(*([1.,1.,1.] if name=='before' else brown.TINT),1))\n   tint=mid.get_vector_parameter_value('WoodlandMudTint')\n   assert max(abs(a-b) for a,b in zip([tint.r,tint.g,tint.b],[1.,1.,1.] if name=='before' else brown.TINT))<1e-5")
text=text.replace(" report['views']=[", " views=[v for v in views if v[0] in ('drive','close','distance')]+[('bank',[150,centre(150)-200,160],[650,centre(650)-500,40])]\n report['views']=[")
text=text.replace(' for i in range(48):',' for i in range(0):')
text=text.replace(" report['surface_after']=", " assert report['brown_hashes']=={p.name:hashlib.sha256(p.read_bytes()).hexdigest() for p in (R/'Content/GrandTour/ArtTests/FloraTrail/Woodland/BrownMud').rglob('*') if p.is_file()}\n report['surface_after']=")
text=text.replace("motion='48-frame move, 8 samples per candidate; not realtime performance'","motion='Not retested for pigment-only edit'")
runtime=Path('D:/GrandTourAssets/ReviewEvidence/FloraTrail/WoodlandMud/runtime.py');runtime.write_text(text)
exec(compile(text,str(runtime),'exec'),globals())
