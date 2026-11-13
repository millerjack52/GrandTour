"""Install regional native ground and recovered waves into the existing Gaea review map."""
import unreal as u
import json,sys,time,traceback,hashlib,math,random,shutil,array
from pathlib import Path
ROOT=Path(u.Paths.project_dir()).resolve();sys.path.insert(0,str(ROOT/'Art/Unreal'))
from benmore_river_life_materials import props
import benmore_native_materials as mat
from siberian_wave_materials import precombine
OUT=ROOT/'Art/Export/BenmoreNative';LEVEL='/Game/GrandTour/Demo/BenmoreRoads/Gaea/L_Benmore_GaeaReview'
assets=u.EditorAssetLibrary;actors=u.get_editor_subsystem(u.EditorActorSubsystem);les=u.get_editor_subsystem(u.LevelEditorSubsystem)
data=json.loads((OUT/'authoring.json').read_text());report={'ok':False,'level':LEVEL,'sites':[],'driving_tested':False}
def digest(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def spawn(cls,label,p=(0,0,0)):
 a=actors.spawn_actor_from_class(cls,u.Vector(*p));a.set_actor_label('Benmore_Native_'+label);return a
H=array.array('H');H.frombytes((ROOT/'Art/Export/BenmoreGaea/ShoreRefinement/reloaded-native-height.r16').read_bytes())
def height(x,y):
 fx=max(0,min(2015.999999,(x+125000)*2016/250000));fy=max(0,min(2015.999999,(y+125000)*2016/250000));i=int(fx);j=int(fy);s=fx-i;t=fy-j;k=j*2017+i
 q,r,v,w=[(H[h]-32768)*200/128 for h in [k,k+1,k+2017,k+2018]]
 return q+(r-q)*s+(w-r)*t if s>=t else q+(w-v)*s+(v-q)*t
try:
 backup=ROOT/'Saved/BenmoreNativeBackups'/str(time.time_ns());backup.mkdir(parents=True)
 mapfile=ROOT/'Content/GrandTour/Demo/BenmoreRoads/Gaea/L_Benmore_GaeaReview.umap';shutil.copy2(mapfile,backup/mapfile.name)
 if (ROOT/'Content/GrandTour/Demo/BenmoreRoads/Gaea/NativeSurfaces').exists():shutil.copytree(ROOT/'Content/GrandTour/Demo/BenmoreRoads/Gaea/NativeSurfaces',backup/'NativeSurfaces')
 report['backup']=str(backup)
 domainfile=ROOT/'Content/GrandTour/Demo/BenmoreRoads/Gaea/Morphology/DA_GC_WaterDomain.uasset'
 drivefile=ROOT/'Content/GrandTour/Demo/BenmoreRoads/L_Benmore_Drive.umap';report['protected_before']=[digest(domainfile),digest(drivefile)]
 assert les.load_level(LEVEL)
 refs={a.get_actor_label():a for a in actors.get_all_level_actors()};land=refs['Benmore_Gaea_Terrain_2500m'];sheet=refs['Benmore_RS_WaterDomain']
 for a in list(refs.values()):
  if a.get_actor_label().startswith('Benmore_Native_'):actors.destroy_actor(a)
 # The two legacy crossing overlays occupy this same ford. Keep the route and
 # imported terrain intact, but let the regional surface own its deformation.
 provider=refs['Benmore_RL_CrossingProfiles']
 source='/Game/GrandTour/Demo/BenmoreRoads/Gaea/ShoreRefinement/DA_GC_CrossingProfiles'
 profile=mat.copy(source,'DA_NativeCrossingProfiles')
 spec=profile.get_editor_property('spec');sections=list(spec.get_editor_property('sections'))
 assert len(sections)==2
 for section in sections:
  deform=section.get_editor_property('deform');deform.set_editor_property('mode',u.GTDeformProfileMode.OFF);section.set_editor_property('deform',deform)
 spec.set_editor_property('sections',sections);profile.set_editor_property('spec',spec)
 assert assets.save_loaded_asset(profile);provider.set_editor_property('spec_asset',profile)
 report['legacy_crossing_profiles_replaced']=len(sections)
 water=[mat.water(k) for k in ['River','Lake']]
 sheet.set_editor_property('ambient_wave_material',precombine());sheet.set_editor_property('ambient_wave_resolution',512)
 sheet.set_editor_property('surface_material_path',water[0].get_path_name())
 for a in sheet.get_editor_property('domain_surfaces'):a.static_mesh_component.set_material(0,water[int('Lake' in a.get_actor_label())])
 preview=sheet.get_component_by_class(u.ProceduralMeshComponent);preview.clear_all_mesh_sections();preview.set_material(0,water[0])
 textures={s['name']:{n:mat.texture(s['name'],n) for n in ['paint','rest','style','macro','cover']} for s in data['sites']}
 land.set_editor_property('landscape_material',mat.terrain(data['sites'],textures));land.set_editor_property('use_dynamic_material_instance',True)
 rng=random.Random(9640861);points=[]
 for site in data['sites']:
  name=site['name'];cx,cy=site['center'];ox,oy=site['origin'];z=site['center_height_cm'];tex=textures[name]
  soil=mat.soil(site,tex);tread=mat.soil(site,tex,True)
  s=spawn(u.GTLandscapeSurface,name+'_Surface',(cx,cy,z));s.landscape=land
  props(s,paint_origin_cm=u.Vector2D(ox,oy),paint_size_cm=site['size'],enable_wheel_support=True,observe_player_wheels=True,follow_player=True,clamp_focus_to_paint=True,separate_visual_mesh=True,use_soil_shear_response=True,use_rut_interaction=True,use_native_mud_shader_updates=site['native'],use_native_substance_response=site['native'],use_native_water_response=True,maximum_layer_depth_cm=124.)
  s.set_editor_property('layer_depth_scale',2.48);s.set_editor_property('simulated_water',sheet)
  s.extend_water_response_to_domain=name=='Ford'
  assert u.GTLandscapeSurfaceSetupLibrary.import_paint(s,tex['paint']);assert u.GTLandscapeSurfaceSetupLibrary.import_world_rest_heights(s,tex['rest'])
  regions=[]
  if name=='Ford':
   # One oriented strip matches the actual channel frame without coarse block types.
   regions=[props(u.GTLandscapeMudRegion(),name='Wet river sand',centre=u.Vector2D(cx,cy),half_size=u.Vector2D(3500,735),yaw_degrees=math.degrees(math.atan2(-.5396752,-.8418733)),granular=True,grass_cover=0,wetness=.68,cohesion=.12,relief=.1,fragment_scale=1),
            props(u.GTLandscapeMudRegion(),name='Bank sod',centre=u.Vector2D(cx,cy),half_size=u.Vector2D(2400,2400),grass_cover=1,wetness=.38,cohesion=.5,relief=.1,fragment_scale=1)]
  else:regions=[props(u.GTLandscapeMudRegion(),name='Deep bog' if name=='Bog' else 'Muddy road',centre=u.Vector2D(cx,cy),half_size=u.Vector2D(2400,2400),wetness=.95 if name=='Bog' else .76,cohesion=.52,relief=.5,fragment_scale=1)]
  s.mud_regions=regions
  v=spawn(u.GTMudRunnerVisual,name+'_Visual',(cx,cy,0));props(v,surface=s,material=soil,track_material=tread,half_size_cm=2400.,hide_whole_landscape=False)
  count=0
  if name=='Ford':
   d=spawn(u.GTMixedGroundDetails,'Ford_Grass');d.surface=s;d.grass_material=assets.load_asset('/Game/GrandTour/ArtTests/SiberianShowcase/M_Grass')
   d.grass.set_static_mesh(assets.load_asset('/Game/GrandTour/ArtTests/MudRoad/MixedSurfaces/SM_NativeShortGrass'));d.grass.set_material(0,d.grass_material)
   transforms=[]
   for yy in range(int(oy)+300,int(oy+4500),45):
    for xx in range(int(ox)+300,int(ox+4500),45):
     x=xx+rng.uniform(-18,18);y=yy+rng.uniform(-18,18);p=s.sample_surface(u.Vector2D(x,y))
     across=(x-cx)*-.5396752+(y-cy)*.8418733
     if p.sinkage_cap_cm<2 or abs(across)<970:continue
     zz=height(x,y)
     if sheet.covers(u.Vector2D(x,y)) and sheet.surface_cm_at(u.Vector2D(x,y))>zz-2:continue
     sc=rng.uniform(.85,1.3);transforms.append(u.Transform(location=u.Vector(x,y,zz-2),rotation=u.Rotator(yaw=rng.uniform(0,360)),scale=u.Vector(sc,sc,rng.uniform(.65,1.0))))
   d.grass.add_instances(transforms,False,True);d.grass.set_cull_distances(3500,6000);d.grass.set_editor_property('visible_in_ray_tracing',False);count=len(transforms)
  else:
   for i in range(24):
    x=cx+rng.uniform(-1300,1300);y=cy+rng.uniform(-650,650)
    if s.sample_surface(u.Vector2D(x,y)).sinkage_cap_cm<9:continue
    large=i%6==0;clod=spawn(u.GTMudRunnerClod,name+'_Clod_'+str(i),(x,y,height(x,y)+2));clod.large=large
    clod.body.set_static_mesh(assets.load_asset('/Game/GrandTour/ArtTests/MudRoad/NativeInteractions/SM_plants_mud_chunk_'+('b' if large else 'a')));clod.body.set_collision_profile_name('BlockAllDynamic')
  pos=(cx+350,cy-900,height(cx+350,cy-900)+240);camera=spawn(u.CameraActor,name+'_Camera',pos);camera.set_actor_rotation(u.MathLibrary.find_look_at_rotation(u.Vector(*pos),u.Vector(cx,cy,z)),False)
  report['sites'].append(dict(name=name,center=site['center'],max_layer_cm=site['depth_max_cm'],grass_instances=count,native_mud=site['native']))
 fx=spawn(u.GTMudRunnerWheelEffects,'WheelEffects')
 fx.materials=[assets.load_asset('/Game/GrandTour/ArtTests/MudRoad/NativeInteractions/M_'+n) for n in ['mud_small','mud_large','water_small','water_medium','water_large','water_fluid','mud_bits','water_drops','water_bits']];assert all(fx.materials)
 assert les.save_current_level()
 assert les.load_level('/Engine/Maps/Entry');assert les.load_level(LEVEL)
 allactors=actors.get_all_level_actors();assert len([a for a in allactors if isinstance(a,u.GTLandscapeSurface)])==3
 assert len([a for a in allactors if isinstance(a,u.GTMudRunnerVisual)])==3
 for a in allactors:
  if isinstance(a,u.GTMudRunnerVisual):assert not a.hide_whole_landscape
  if isinstance(a,u.GTWaterSheet):assert a.get_editor_property('ambient_wave_resolution')==512
 report['protected_after']=[digest(domainfile),digest(drivefile)];assert report['protected_after']==report['protected_before']
 report.update(ok=True,saved_and_reloaded=True)
except Exception:report['error']=traceback.format_exc();u.log_error(report['error'])
(OUT/'install.json').write_text(json.dumps(report,indent=2))
u.SystemLibrary.quit_editor()
