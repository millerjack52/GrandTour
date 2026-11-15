"""Fixed fern texture/gradient controls; baseline light, normals and geometry."""
from pathlib import Path
R=Path('C:/GrandTour');source=R/'Art/Unreal/trial_flora_mud.py';text=source.read_text()
changes={
 'from flora_mud_trial_baseline import verify':'from flora_fern_surface_baseline import verify',
 'import flora_mud_trial_materials as mat':'import flora_mud_trial_materials as mat\nimport flora_fern_surface as fern',
 "O=R/'Art/Export/FloraTrail/MudTrial'":"O=R/'Art/Export/FloraTrail/FernSurface'",
 "stage=os.environ.get('GT_MUD_TRIAL_STAGE','screen')":"stage=os.environ.get('GT_FERN_SURFACE_STAGE','candidate')",
 "rows=json.loads((O/'sources.json').read_text())":"rows=json.loads((R/'Art/Export/FloraTrail/MudTrial/sources.json').read_text())",
}
for old,new in changes.items():assert text.count(old)==1,old;text=text.replace(old,new)
a=text.index(" if stage=='screen':");b=text.index(' # Wait for asynchronously',a)
text=text[:a]+'''
 row=next(r for r in rows if r['id']=='brown_mud_02');selected=[row]
 target=fern.D+'/L_FloraTrail_Fern';exists=E.does_asset_exist(target)
 assert L.load_level(target if stage=='verify' or exists else '/Game/GrandTour/ArtTests/FloraTrail/UnderstoryTrial/L_FloraTrail_Understory')
 world=u.get_editor_subsystem(u.UnrealEditorSubsystem).get_editor_world()
 signature=fern.scene_signature(world)
 if not (O/'scene-baseline.json').exists():(O/'scene-baseline.json').write_text(json.dumps(signature,indent=2))
 (O/'scene-loaded.json').write_text(json.dumps(signature,indent=2))
 assert signature==json.loads((O/'scene-baseline.json').read_text())
 c=fern.component(world);mesh=c.static_mesh
 report['fern']={'mesh':mesh.get_path_name(),'lods':u.get_editor_subsystem(u.StaticMeshEditorSubsystem).get_lod_count(mesh),'instances':c.get_instance_count(),'triangles':mesh.get_static_mesh_description(0).get_triangle_count()}
 assert report['fern']['lods']==3 and report['fern']['instances']==159
 if stage!='verify':
  c.set_material(0,fern.build())
  assert L.save_current_level() if exists else u.EditorLoadingAndSavingUtils.save_map(world,target)
  assert L.load_level('/Engine/Maps/Entry');assert L.load_level(target);world=u.get_editor_subsystem(u.UnrealEditorSubsystem).get_editor_world()
 saved_signature=fern.scene_signature(world);(O/'scene-reloaded.json').write_text(json.dumps(saved_signature,indent=2))
 assert saved_signature==signature
 c=fern.component(world);assert c.static_mesh==mesh
 material=c.get_material(0);assert material.get_path_name()==fern.D+'/M_FernSurface.M_FernSurface'
 source_material=u.load_asset(fern.SOURCE)
 for prop in (u.MaterialProperty.MP_NORMAL,u.MaterialProperty.MP_OPACITY_MASK,u.MaterialProperty.MP_EMISSIVE_COLOR,u.MaterialProperty.MP_ROUGHNESS,u.MaterialProperty.MP_SPECULAR):
  old=M.get_material_property_input_node(source_material,prop);new=M.get_material_property_input_node(material,prop)
  assert old.get_class()==new.get_class()
  if isinstance(old,u.MaterialExpressionCustom):assert old.get_editor_property('code')==new.get_editor_property('code')
  if isinstance(old,u.MaterialExpressionConstant):assert old.get_editor_property('r')==new.get_editor_property('r')
 for param in ('SourcePigment','SourceCoverage'):
  def tex(m):return next(n.get_editor_property('texture') for n in M.get_material_expressions(m) if isinstance(n,u.MaterialExpressionTextureSampleParameter2D) and str(n.get_editor_property('parameter_name'))==param)
  assert tex(source_material)==tex(material)
 assert material.get_editor_property('opacity_mask_clip_value')==source_material.get_editor_property('opacity_mask_clip_value')
 report['preserved_source_bindings_normals_coverage']=True;report['other_scene_components_unchanged']=True;report['saved_map']=target
 surface=next(a for a in A.get_all_level_actors() if isinstance(a,u.GTLandscapeSurface))
 assert surface.simulated_water.get_editor_property('surface_material_path')==D+'/M_WaterFlat.M_WaterFlat'
 assert surface.landscape.landscape_material.get_name()=='M_VergeLandscape'
 assert next(a for a in A.get_all_level_actors() if isinstance(a,u.GTMudRunnerVisual)).material.get_name()=='MI_VergeMud'
 textures={row['id']:{role:u.load_asset(D+'/Textures/T_'+row['id']+'_'+role+'_native') for role in ('color','normal','height','roughness')}}
 cases=[(name,row,1.) for name in ('baseline','paint','gradient','combined')] if stage=='candidate' else [('combined',row,1.)]
 paint=u.load_asset(fern.D+'/T_FernPaint');cmd('r.Streaming.FullyLoadUsedTextures 1');deadline=time.monotonic()+180
 while paint.blueprint_get_size_x()!=2048:
  assert time.monotonic()<deadline;yield .5
 report['paint_texture']={'size':[paint.blueprint_get_size_x(),paint.blueprint_get_size_y()],'source_sha256':E.get_metadata_tag(paint,'SourceSHA256')}
 report['candidate_hashes_before']={p.relative_to(R/'Content').as_posix():hashlib.sha256(p.read_bytes()).hexdigest() for p in (R/'Content/GrandTour/ArtTests/FloraTrail/FernSurface').rglob('*') if p.is_file()}
''' +text[b:]
old=" report['live_dynamic_materials']=[m.get_path_name() for m in mids]"
text=text.replace(old,old+'''
 fern_component=fern.component(world);fern_mid=fern_component.create_dynamic_material_instance(0)
 assert fern_mid and fern_mid.get_scalar_parameter_value('FernDetailStrength')==1 and fern_mid.get_scalar_parameter_value('FernGradientStrength')==1
 positions=[fern_component.get_instance_transform(i,True).translation for i in range(fern_component.get_instance_count())]
 fern_target=min(positions,key=lambda p:math.dist((p.x,p.y),(450,-250)))
 report['close_fern_position']=fern_target.to_tuple()
''')
old=" report['views']=[{'name':n,'position':p,'target':t} for n,p,t in views];report['surface_before']=surface.get_surface_report()"
text=text.replace(old," fx,fy,fz=fern_target.to_tuple()\n views=[v for v in views if v[0]=='drive']+[('verge',[150,centre(150)-200,160],[650,centre(650)-500,0]),('fern',[fx-120,fy+180,fz+130],[fx,fy,fz+35])]\n"+old)
text=text.replace(" for name,row,enabled in cases:"," for name,row,enabled in cases:\n  fern_mid.set_scalar_parameter_value('FernDetailStrength',1. if name in ('paint','combined') else 0.)\n  fern_mid.set_scalar_parameter_value('FernGradientStrength',1. if name in ('gradient','combined') else 0.)")
text=text.replace("   if stage not in ('saved','verify'):mat.bind(mid,row,textures,enabled)","   pass # Existing ground and water remain unchanged.")
text=text.replace("xx=-1900+i*5;yy=centre(xx);look([xx,yy,height(xx,yy)+150],[xx+1500,centre(xx+1500),height(xx+1500,centre(xx+1500))+60])","xx=150+i*4;yy=centre(xx)-200;look([xx,yy,160],[xx+500,centre(xx+500)-500,0])")
old=" report['surface_after']=surface.get_surface_report();"
text=text.replace(old," assert report['candidate_hashes_before']=={p.relative_to(R/'Content').as_posix():hashlib.sha256(p.read_bytes()).hexdigest() for p in (R/'Content/GrandTour/ArtTests/FloraTrail/FernSurface').rglob('*') if p.is_file()}\n"+old)
runtime=R/'Art/Export/FloraTrail/FernSurface/runtime.py';runtime.write_text(text)
exec(compile(text,str(runtime),'exec'),globals())
