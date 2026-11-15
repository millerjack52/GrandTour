"""Reuse the established capture/drive lifecycle for level water only."""
from pathlib import Path
R=Path('C:/GrandTour');source=R/'Art/Unreal/trial_flora_mud.py';text=source.read_text()
changes={
 'from flora_mud_trial_baseline import verify':'from flora_water_flat_baseline import verify',
 'import flora_mud_trial_materials as mat':'import flora_mud_trial_materials as mat\nimport flora_water_flat_materials as water',
 "O=R/'Art/Export/FloraTrail/MudTrial'":"O=R/'Art/Export/FloraTrail/WaterFlat'",
 "stage=os.environ.get('GT_MUD_TRIAL_STAGE','screen')":"stage=os.environ.get('GT_WATER_FLAT_STAGE','probe')",
 "rows=json.loads((O/'sources.json').read_text())":"rows=json.loads((R/'Art/Export/FloraTrail/MudTrial/sources.json').read_text())",
}
for old,new in changes.items():assert text.count(old)==1,old;text=text.replace(old,new)
a=text.index(" if stage=='screen':");b=text.index(' # Wait for asynchronously',a)
text=text[:a]+'''
 row=next(r for r in rows if r['id']=='brown_mud_02');selected=[row]
 target=D+'/L_FloraTrail_MudFlat'
 assert L.load_level(target if stage=='verify' else D+'/L_FloraTrail_MudWet')
 world=u.get_editor_subsystem(u.UnrealEditorSubsystem).get_editor_world()
 sheet=next(a for a in A.get_all_level_actors() if isinstance(a,u.GTWaterSheet))
 report['water_source']=sheet.get_editor_property('surface_material_path')
 if stage!='verify':
  wm=water.build(report['water_source']);sheet.set_editor_property('surface_material_path',wm.get_path_name())
  assert u.EditorLoadingAndSavingUtils.save_map(world,target)
  assert L.load_level('/Engine/Maps/Entry');assert L.load_level(target)
  world=u.get_editor_subsystem(u.UnrealEditorSubsystem).get_editor_world()
  sheet=next(a for a in A.get_all_level_actors() if isinstance(a,u.GTWaterSheet))
 assert sheet.get_editor_property('surface_material_path')==water.TARGET+'.M_WaterFlat'
 visual=next(a for a in A.get_all_level_actors() if isinstance(a,u.GTMudRunnerVisual))
 assert visual.material.get_path_name()==D+'/MI_MudTrial_brown_wet.MI_MudTrial_brown_wet'
 report['saved_material']=visual.material.get_path_name();report['saved_map']=target
 report['water_material']=sheet.get_editor_property('surface_material_path')
 textures={row['id']:{role:u.load_asset(D+'/Textures/T_'+row['id']+'_'+role+'_native') for role in ('color','normal','height','roughness')}}
 cases=[(name,row,1.) for name in water.PROFILES] if stage=='probe' else [('flat_water',row,1.)]
''' +text[b:]
old=" report['live_dynamic_materials']=[m.get_path_name() for m in mids]"
assert text.count(old)==1
text=text.replace(old,old+'''
 sheet=u.GameplayStatics.get_all_actors_of_class(world,u.GTWaterSheet)[0]
 mesh=next(c for c in sheet.get_components_by_class(u.ProceduralMeshComponent) if c.get_name()=='SurfaceMesh')
 water_mid=mesh.get_material(0);assert isinstance(water_mid,u.MaterialInstanceDynamic)
 report['water_mesh']={'location':mesh.get_world_location().to_tuple(),'rotation':str(mesh.get_world_rotation()),'scale':mesh.get_world_scale().to_tuple(),'material':water_mid.get_path_name(),'level_cm':water_mid.get_scalar_parameter_value('FieldLevelCm')}
 assert abs(mesh.get_world_location().z-water_mid.get_scalar_parameter_value('FieldLevelCm'))<.001
 vertices,triangles,normals,uvs,tangents=u.ProceduralMeshLibrary.get_section_from_procedural_mesh(mesh,0)
 report['water_mesh']['vertex_count']=len(vertices)
 report['water_mesh']['local_z_range']=[min(v.z for v in vertices),max(v.z for v in vertices)]
 assert report['water_mesh']['local_z_range']==[0.,0.]
 report['saved_water_controls']={k:water_mid.get_scalar_parameter_value(k) for k in ('FloraWaterFlat','FloraWaterQuietNormals')}
 assert all(abs(v-1.)<.00001 for v in report['saved_water_controls'].values())
 report['physical_columns_before']=[{'xy':[x,centre(x)],'column':sheet.review_water_column(u.Vector2D(x,centre(x))).to_tuple()} for x in range(-2000,2300,200)]
''')
old=" report['views']=[{'name':n,'position':p,'target':t} for n,p,t in views];report['surface_before']=surface.get_surface_report()"
assert text.count(old)==1
text=text.replace(old," views.extend([('puddle',[350,centre(350)-280,150],[850,centre(850),-5]),('pond',[350,650,180],[1050,1050,-5])])\n"+old)
old="   if stage not in ('saved','verify'):mat.bind(mid,row,textures,enabled)"
assert text.count(old)==1;text=text.replace(old,"   if stage=='probe':water.configure(water_mid,water.PROFILES[name])")
old=" if stage=='saved':\n  yield from drive_check";assert text.count(old)==1
text=text.replace(old," if stage=='verify':\n  yield from drive_check")
exec(compile(text,str(source),'exec'),globals())
