"""Read-only visibility isolation of the pale FloraTrail verge."""
from pathlib import Path
R=Path('C:/GrandTour');source=R/'Art/Unreal/trial_flora_mud.py';text=source.read_text()
changes={
 'from flora_mud_trial_baseline import verify':'from flora_verge_baseline import verify',
 "O=R/'Art/Export/FloraTrail/MudTrial'":"O=R/'Art/Export/FloraTrail/VergeStudy'",
 "stage=os.environ.get('GT_MUD_TRIAL_STAGE','screen')":"stage='probe'",
 "rows=json.loads((O/'sources.json').read_text())":"rows=json.loads((R/'Art/Export/FloraTrail/MudTrial/sources.json').read_text())",
}
for old,new in changes.items():assert text.count(old)==1,old;text=text.replace(old,new)
a=text.index(" if stage=='screen':");b=text.index(' # Wait for asynchronously',a)
text=text[:a]+'''
 report['trial_hashes_before']=trial_hashes()
 row=next(r for r in rows if r['id']=='brown_mud_02');selected=[row]
 assert L.load_level(D+'/L_FloraTrail_MudFlat');world=u.get_editor_subsystem(u.UnrealEditorSubsystem).get_editor_world()
 textures={row['id']:{role:u.load_asset(D+'/Textures/T_'+row['id']+'_'+role+'_native') for role in ('color','normal','height','roughness')}}
 cases=[(name,row,1.) for name in ['baseline','no_forms','no_surround','no_apron','no_grid']]
''' +text[b:]
old=" report['live_dynamic_materials']=[m.get_path_name() for m in mids]"
text=text.replace(old,old+'''
 actors=u.GameplayStatics.get_all_actors_of_class(world,u.StaticMeshActor)
 targets={k:next(a for a in actors if a.get_actor_label()=='FloraDrive_'+label) for k,label in [('no_forms','ForestFloorForms'),('no_surround','WoodedSurround'),('no_apron','ForestApron')]}
''')
old=" report['views']=[{'name':n,'position':p,'target':t} for n,p,t in views];report['surface_before']=surface.get_surface_report()"
text=text.replace(old," views=[('puddle',[350,centre(350)-280,150],[850,centre(850),-5]),('verge',[150,centre(150)-200,160],[650,centre(650)-500,0])]\n"+old)
old=" for name,row,enabled in cases:"
text=text.replace(old,old+"\n  for k,a in targets.items():a.set_actor_hidden_in_game(k==name)\n  grid.set_visibility(name!='no_grid')")
text=text.replace("   if stage not in ('saved','verify'):mat.bind(mid,row,textures,enabled)","   pass # Visibility-only diagnostic; material inputs untouched.")
a=text.index('  # A continuous short forward move');b=text.index(" if stage=='saved':",a);text=text[:a]+text[b:]
text=text.replace(" report['surface_after']=surface.get_surface_report();", " for a in targets.values():a.set_actor_hidden_in_game(False)\n grid.set_visibility(True)\n assert report['trial_hashes_before']==trial_hashes();report['trial_packages_unchanged']=True\n report['surface_after']=surface.get_surface_report();")
text=text.replace("motion='48-frame move, 8 samples per candidate; not realtime performance'","motion='Not tested in visibility isolation'")
exec(compile(text,str(source),'exec'),globals())
