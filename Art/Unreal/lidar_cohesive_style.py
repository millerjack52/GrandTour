"""Coordinated palette, crown lighting and sky; Medium remains the runtime A/B."""
import unreal as u,json,sys,os,time,traceback,hashlib,zipfile
from pathlib import Path
ROOT=Path(u.Paths.project_dir()).resolve();sys.path.insert(0,str(ROOT/'Art/Unreal'))
import canopy_depth as C
import firewatch_distance_style as F
from benmore_river_life_materials import Graph,props
from forest_shaders import connected_nodes
assets=u.EditorAssetLibrary;mel=u.MaterialEditingLibrary;les=u.get_editor_subsystem(u.LevelEditorSubsystem)
DEST=C.BASE+'/CohesiveStyle';QA=ROOT/'Saved/LidarAuthoringQA/CohesiveStyle';QA.mkdir(parents=True,exist_ok=True)
CONFIG=ROOT/'Art/Export/LidarStudy/CohesiveStyle/recipe.json'
SCALARS=dict(PaletteStrength=0,PaletteStartCm=4000,PaletteFullCm=22000,CrownDefinition=.7,SkyPaletteStrength=0)
VECTORS=dict(SunlitColour=(.085,.13,.045,1),ClearingColour=(.12,.145,.055,1),ClearingShadowColour=(.055,.08,.045,1),SkyHorizonColour=(.82,.79,.61,1),SkyZenithColour=(.36,.57,.63,1))
def enabled():return CONFIG.exists() and json.loads(CONFIG.read_text()).get('enabled',False)
def clone(src,name):return u.load_asset(DEST+'/'+name) or assets.duplicate_asset(src.get_path_name().split('.')[0],DEST+'/'+name)
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()

def backup():
 if (QA/'before.json').exists():return
 content=ROOT/'Content/GrandTour/ArtTests/LidarStudy'
 files=list((content/'FirewatchStyle').glob('*.uasset'))+[content/'L_LidarStudy.umap']
 with zipfile.ZipFile(QA/'before.zip','w',zipfile.ZIP_DEFLATED,compresslevel=1) as z:
  for p in files:z.write(p,str(p.relative_to(content)))
 report=dict(files={str(p.relative_to(ROOT)):sha(p) for p in files},state=F.protected())
 (QA/'before.json').write_text(json.dumps(report,indent=2))

def parameters():
 m=u.load_asset(F.DEST+'/MPC_DistanceStyle')
 for prop,values,cls in [('scalar_parameters',SCALARS,u.CollectionScalarParameter),('vector_parameters',VECTORS,u.CollectionVectorParameter)]:
  rows=list(m.get_editor_property(prop));names={str(p.get_editor_property('parameter_name')) for p in rows}
  for k,v in values.items():
   if k not in names:rows.append(props(cls(),parameter_name=k,default_value=u.LinearColor(*v) if isinstance(v,tuple) else v))
  m.set_editor_property(prop,rows)
 assert assets.save_loaded_asset(m,False)

def profile():
 p=clone(u.load_asset(F.DEST+'/DA_Lidar_Medium'),'DA_Lidar_Evergreen')
 props(p,palette_strength=.72,palette_start_metres=40,palette_full_metres=220,crown_definition=.72,
  forest_colour=u.LinearColor(.030,.074,.058,1),shadow_colour=u.LinearColor(.012,.030,.032,1),sunlit_colour=u.LinearColor(.085,.13,.045,1),
  clearing_colour=u.LinearColor(.12,.145,.055,1),clearing_shadow_colour=u.LinearColor(.055,.080,.045,1),ground_tint=u.LinearColor(1.04,1.,.87,1),
  sky_palette_strength=.78,sky_horizon_colour=u.LinearColor(.82,.79,.61,1),sky_zenith_colour=u.LinearColor(.36,.57,.63,1),
  haze_colour=u.LinearColor(.52,.64,.56,1),patch_variation=.07)
 assert assets.save_loaded_asset(p,False);return p

def add_input(g,n,key,node):
 rows=list(n.get_editor_property('inputs'))
 if not any(str(i.get_editor_property('input_name'))==key for i in rows):
  rows.append(props(u.CustomInput(),input_name=key));n.set_editor_property('inputs',rows)
 g.wire(node,n,key)

def surface(name,ground=False):
 m=clone(u.load_asset(F.DEST+'/'+name),name.replace('Style','Evergreen'))
 n=next(n for n in connected_nodes(m) if isinstance(n,u.MaterialExpressionCustom) and str(n.get_editor_property('desc'))=='FirewatchDistance')
 old=n.get_editor_property('code')
 if '// Evergreen palette' in old:old=old.split('// Evergreen palette')[0]+'return lerp(C,target,fade);'
 g=Graph(m,'EvergreenPalette')
 for key in ['PaletteStrength','PaletteStartCm','PaletteFullCm','CrownDefinition','SunlitColour','ClearingColour','ClearingShadowColour']:add_input(g,n,key,F.param(g,key))
 tail='''
// Evergreen palette: source detail near the camera, broad colour families farther away.
float palette=smoothstep(PaletteStartCm,PaletteFullCm,d)*PaletteStrength;
float3 legacy=lerp(C,target,fade);
// The 5m-filtered canopy envelope describes crown groups rather than leaf planes.
float4 grouped=Texture2DSampleLevel(Field,View.MaterialTextureBilinearClampedSampler,uv,1);
float2 groupXY=grouped.rg*2-1;
float3 groupNormal=normalize(float3(groupXY,sqrt(max(.01,1-dot(groupXY,groupXY)))));
float definition=CrownDefinition*(1-smoothstep(StartCm,FullCm*1.4,d));
float crown=smoothstep(-.12,.72,dot(groupNormal,normalize(SunDirection.rgb)));
float crownLight=lerp(light,crown*lerp(.55,1,visibility),definition);
float3 coordinated=lerp(ShadowColour.rgb,ForestColour.rgb,smoothstep(.08,.60,crownLight));
float highlight=smoothstep(.52,.92,crownLight)*smoothstep(-.05,.62,groupNormal.z);
coordinated=lerp(coordinated,SunlitColour.rgb,highlight*.8)*(1+patch*PatchVariation);
'''
 if ground:
  add_input(g,n,'Landcover',g.node(u.MaterialExpressionTextureObject,texture=u.load_asset(C.BASE+'/T_style'),sampler_type=u.MaterialSamplerType.SAMPLERTYPE_LINEAR_COLOR))
  tail+='''
float grass=smoothstep(.3,.8,Texture2DSampleLevel(Landcover,View.MaterialTextureBilinearClampedSampler,uv,3).g);
float3 clearing=lerp(ClearingShadowColour.rgb,ClearingColour.rgb,saturate(.25+.75*light));
// Keep land-cover boundaries and modest source variation; quiet the mottled pasture.
float3 openGround=lerp(C*GroundTint.rgb,clearing,grass*.82);
coordinated=lerp(openGround,lerp(ShadowColour.rgb,ForestColour.rgb,light)*.75,saturate(cover));
'''
 else:
  tangent=m.get_editor_property('tangent_space_normal')
  tail+='Normal=normalize(lerp(Normal,'+('float3(0,0,1)' if tangent else 'normalize(lerp(groupNormal,macro,.25))')+',palette*definition));\n'
 tail+='return lerp(legacy,coordinated,palette);'
 assert 'return lerp(C,target,fade);' in old
 n.set_editor_property('code',old.replace('return lerp(C,target,fade);',tail))
 assert not mel.recompile_material(m);assert assets.save_loaded_asset(m,False);return m

def haze():
 m=clone(u.load_asset(F.DEST+'/M_StyleHaze'),'M_EvergreenHaze');mel.delete_all_material_expressions(m)
 g=Graph(m,'EvergreenSkyHaze')
 names=['Scene','Depth','CameraVector','HazeColour','HazeIntensity','HazeStartCm','HazeFullCm','SkyPaletteStrength','SkyHorizonColour','SkyZenithColour']
 n=g.custom(names,'''
float sky=smoothstep(900000,1000000,Depth);
float a=smoothstep(HazeStartCm,HazeFullCm,Depth)*HazeIntensity*(1-sky);
float3 colour=lerp(Scene.rgb,HazeColour.rgb,a);
// CameraVectorWS is reconstructed per view in CalcMaterialParametersPost.
// A direction-based gradient follows the horizon when the camera pitches.
float elevation=-normalize(CameraVector).z;
float3 gradient=lerp(SkyHorizonColour.rgb,SkyZenithColour.rgb,smoothstep(0,.55,max(0,elevation)));
gradient=lerp(gradient,HazeColour.rgb*.82,smoothstep(0,.16,max(0,-elevation)));
return lerp(colour,gradient,sky*SkyPaletteStrength);
''')
 g.wire(g.node(u.MaterialExpressionSceneTexture,scene_texture_id=u.SceneTextureId.PPI_POST_PROCESS_INPUT0),n,'Scene','Color');g.wire(g.node(u.MaterialExpressionSceneDepth),n,'Depth');g.wire(g.node(u.MaterialExpressionCameraVectorWS),n,'CameraVector')
 for key in names[3:]:g.wire(F.param(g,key),n,key)
 g.output(n,u.MaterialProperty.MP_EMISSIVE_COLOR);assert not mel.recompile_material(m);assert assets.save_loaded_asset(m,False)

def build():
 parameters();profile();surface('M_StyleFoliage')
 mi=clone(u.load_asset(F.DEST+'/MI_StyleFoliage'),'MI_EvergreenFoliage');mel.set_material_instance_parent(mi,u.load_asset(DEST+'/M_EvergreenFoliage'));assert assets.save_loaded_asset(mi,False)
 for kind in ['Mature','Pole','Edge']:surface('M_StyleProxy_'+kind)
 for name in ['Terrain','Detail']:surface('M_Style'+name,True)
 haze()

def apply_haze():
 a=next(a for a in C.actors.get_all_level_actors() if a.get_actor_label()==F.H.LABEL)
 s=a.settings;s.set_editor_property('weighted_blendables',u.WeightedBlendables(array=[u.WeightedBlendable(weight=1.,object=u.load_asset(DEST+'/M_EvergreenHaze'))]));a.settings=s

def apply(select=False):
 rows=C.actors.get_all_level_actors();controller=next(a for a in rows if isinstance(a,u.GTDistanceStyleController))
 controller.cohesive=u.load_asset(DEST+'/DA_Lidar_Evergreen')
 if select:controller.profile=controller.cohesive
 controller.apply_profile()
 mapping={u.load_asset(F.DEST+'/'+n):u.load_asset(DEST+'/'+n.replace('Style','Evergreen')) for n in ['MI_StyleFoliage','M_StyleTerrain','M_StyleDetail']+['M_StyleProxy_'+k for k in ['Mature','Pole','Edge']]}
 for a in rows:
  if isinstance(a,u.LandscapeProxy) and a.get_editor_property('landscape_material') in mapping:a.set_editor_property('landscape_material',mapping[a.get_editor_property('landscape_material')])
  if isinstance(a,u.GTMudRunnerVisual) and a.material in mapping:a.material=mapping[a.material]
  if isinstance(a,u.GTProceduralGround) and a.relief_material in mapping:a.relief_material=mapping[a.relief_material]
  for c in a.get_components_by_class(u.MeshComponent):
   for i in range(c.get_num_materials()):
    if c.get_material(i) in mapping:c.set_material(i,mapping[c.get_material(i)])
 apply_haze()

def validate():
 before=json.loads((QA/'before.json').read_text());assert F.protected()==before['state']
 for path,digest in before['files'].items():
  if path.endswith(('L_LidarStudy.umap','MPC_DistanceStyle.uasset')):continue
  assert sha(ROOT/path)==digest,path
 rows=C.actors.get_all_level_actors();c=next(a for a in rows if isinstance(a,u.GTDistanceStyleController));assert c.profile==u.load_asset(DEST+'/DA_Lidar_Evergreen')
 world=u.get_editor_subsystem(u.UnrealEditorSubsystem).get_editor_world();mpc=c.parameters
 for preset,value in [('Medium',0),('Cohesive',.72)]:
  c.set_style_preset(preset);assert abs(u.MaterialLibrary.get_scalar_parameter_value(world,mpc,'PaletteStrength')-value)<.0001
 p=c.profile;sky=p.sky_palette_strength;sun=p.sunlit_colour;fog=p.haze_intensity
 try:
  p.sky_palette_strength=.21;p.sunlit_colour=u.LinearColor(.1,.2,.3,1);c.apply_profile()
  assert abs(u.MaterialLibrary.get_scalar_parameter_value(world,mpc,'SkyPaletteStrength')-.21)<.0001
  assert abs(u.MaterialLibrary.get_vector_parameter_value(world,mpc,'SunlitColour').b-.3)<.0001
  assert abs(u.MaterialLibrary.get_scalar_parameter_value(world,mpc,'HazeIntensity')-fog)<.0001
  assert c.medium.palette_strength==0 and c.medium.sky_palette_strength==0
 finally:p.sky_palette_strength=sky;p.sunlit_colour=sun;c.apply_profile()
 assert next(a for a in rows if isinstance(a,u.Landscape)).get_editor_property('landscape_material')==u.load_asset(DEST+'/M_EvergreenTerrain')
 for comp in next(a for a in rows if a.get_actor_label()=='LidarStudy_Forest').get_components_by_class(u.InstancedStaticMeshComponent):
  if comp.static_mesh and comp.static_mesh.get_name() in ['SM_CD_Canopy_0','SM_CD_Canopy_1','SM_CD_Canopy_2']:assert comp.get_material(1)==u.load_asset(DEST+'/MI_EvergreenFoliage')
 return dict(protected_packages=C.validate_protected(),baseline_materials_and_profiles_unchanged=True,planting_ground_low_fog_unchanged=True,preset_switches_passed=True,independent_sky_palette_haze_controls=True)

def main():
 stage=os.environ.get('GT_COHESIVE_STAGE','install');report=dict(ok=False,stage=stage);control=dict(busy=False,deadline=0)
 def run():
  assert les.load_level(C.BASE+'/L_LidarStudy');yield 2
  if stage=='refine':
   surface('M_StyleFoliage')
   for kind in ['Mature','Pole','Edge']:surface('M_StyleProxy_'+kind)
   for name in ['Terrain','Detail']:surface('M_Style'+name,True)
   report.update(validate())
  elif stage=='install':
   backup();build();apply(True);report.update(validate());assert les.save_current_level()
   CONFIG.parent.mkdir(parents=True,exist_ok=True);CONFIG.write_text(json.dumps(dict(enabled=True,profile=DEST+'/DA_Lidar_Evergreen'),indent=2));report['saved']=True
  else:report.update(validate());report['saved_reload']=True
  report['ok']=True;yield 1
 steps=run()
 def tick(dt):
  if control['busy'] or time.monotonic()<control['deadline']:return
  control['busy']=True
  try:control['deadline']=time.monotonic()+float(next(steps))
  except StopIteration:
   (QA/(stage+'.json')).write_text(json.dumps(report,indent=2));u.unregister_slate_post_tick_callback(control['handle']);u.SystemLibrary.quit_editor()
  except Exception:
   report['error']=traceback.format_exc();(QA/(stage+'.json')).write_text(json.dumps(report,indent=2));u.log_error(report['error']);u.unregister_slate_post_tick_callback(control['handle']);u.SystemLibrary.quit_editor()
  finally:control['busy']=False
 u.EditorPythonScripting.set_keep_python_script_alive(True);control['handle']=u.register_slate_post_tick_callback(tick)
if __name__=='__main__':main()
