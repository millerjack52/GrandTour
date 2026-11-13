"""Private shared-solver prototype; preserve the accepted proving-ground level."""
import sys,json,time,traceback,shutil,hashlib
from pathlib import Path
import unreal as u
ROOT=Path(u.Paths.project_dir()).resolve();sys.path.insert(0,str(ROOT/'Art/Unreal'))
import mud_proving_materials as m
from benmore_river_life_materials import Graph,props
BASE='/Game/GrandTour/ArtTests/MudWater';LEVEL=BASE+'/L_MudWater'
OUT=ROOT/'Art/Export/MudWaterShared';OUT.mkdir(parents=True,exist_ok=True)
les=u.get_editor_subsystem(u.LevelEditorSubsystem);actors=u.get_editor_subsystem(u.EditorActorSubsystem);assets=u.EditorAssetLibrary
report=dict(ok=False,level=LEVEL)
try:
    baseline_file=ROOT/'Content/GrandTour/ArtTests/MudProvingGround/L_MudProvingGround.umap'
    baseline_hash=hashlib.sha256(baseline_file.read_bytes()).hexdigest()
    folder=ROOT/'Content/GrandTour/ArtTests/MudWater'
    if folder.exists():
        backup=ROOT/'Saved/MudWater'/str(time.time_ns());shutil.copytree(folder,backup);report['backup']=str(backup)
    if assets.does_asset_exist(LEVEL):assert les.load_level(LEVEL)
    else:
        assert les.load_level('/Game/GrandTour/ArtTests/MudProvingGround/L_MudProvingGround')
        world=u.get_editor_subsystem(u.UnrealEditorSubsystem).get_editor_world()
        assert u.EditorLoadingAndSavingUtils.save_map(world,LEVEL)
        # save_map makes a copy; it does not switch the active editor world.
        world=None
        assert les.load_level(LEVEL)
    # Start with the accepted muddy SingleLayerWater optics, then replace its motion and shoreline outputs.
    path=BASE+'/M_MudWater'
    w=assets.load_asset(path) or assets.duplicate_asset(m.BASE+'/M_ProvingPool',path)
    assert w
    for e in list(u.MaterialEditingLibrary.get_material_expressions(w)):u.MaterialEditingLibrary.delete_material_expression(w,e)
    g=Graph(w,'SharedMudWater')
    slw=g.node(u.MaterialExpressionSingleLayerWaterMaterialOutput)
    clean=lambda s:''.join(c.lower() for c in s if c.isalnum())
    for pin,value in [('Scattering Coefficients',(.008,.006,.0038)),('Absorption Coefficients',(.018,.024,.035)),('Color Scale Behind Water',(.82,.78,.65))]:
        actual=next(n for n in u.MaterialEditingLibrary.get_material_expression_input_names(slw) if clean(n)==clean(pin));g.wire(g.vector(value),slw,actual)
    actual=next(n for n in u.MaterialEditingLibrary.get_material_expression_input_names(slw) if clean(n)=='phaseg');g.wire(g.scalar(.1),slw,actual)
    g.output(g.vector((.025,.024,.018)),u.MaterialProperty.MP_BASE_COLOR)
    for prop,value in [(u.MaterialProperty.MP_OPACITY,.16),(u.MaterialProperty.MP_ROUGHNESS,.10),(u.MaterialProperty.MP_SPECULAR,.25)]:g.output(g.scalar(value),prop)
    d=m.inputs(g,assets.load_asset(m.BASE+'/T_ProvingPaint'),assets.load_asset(m.BASE+'/T_ProvingRest'))
    d['Wave']=g.node(u.MaterialExpressionTextureObjectParameter,parameter_name='FieldTex',texture=u.load_asset('/Engine/EngineResources/Black'),sampler_type=u.MaterialSamplerType.SAMPLERTYPE_LINEAR_COLOR)
    d['BaseBed']=g.node(u.MaterialExpressionTextureObjectParameter,parameter_name='MudBaseTex',texture=u.load_asset('/Engine/EngineResources/Black'),sampler_type=u.MaterialSamplerType.SAMPLERTYPE_LINEAR_COLOR)
    for name,value in [('FieldMin',(-1575,-1575,0,0)),('FieldSize',(3150,3150,0,0)),('FieldTexels',(126,126,0,0))]:
        d[name]=g.node(u.MaterialExpressionVectorParameter,parameter_name=name,default_value=u.LinearColor(*value))
    d['Level']=g.node(u.MaterialExpressionScalarParameter,parameter_name='FieldLevelCm',default_value=-4.509804)
    common='''
struct MudWaves {
 float4 read(Texture2D T,SamplerState S,float2 uv,float2 size) {
  float2 q=clamp(uv*size-.5,0,size-1),a=floor(q),f=frac(q);
  float4 t00=Texture2DSampleLevel(T,S,(a+.5)/size,0);
  float4 t10=Texture2DSampleLevel(T,S,(min(a+float2(1,0),size-1)+.5)/size,0);
  float4 t01=Texture2DSampleLevel(T,S,(min(a+float2(0,1),size-1)+.5)/size,0);
  float4 t11=Texture2DSampleLevel(T,S,(min(a+1,size-1)+.5)/size,0);
  float4 v=lerp(lerp(t00,t10,f.x),lerp(t01,t11,f.x),f.y);
  float4 weights=float4((1-f.x)*(1-f.y),f.x*(1-f.y),(1-f.x)*f.y,f.x*f.y)*step(.20001,float4(t00.g,t10.g,t01.g,t11.g));
  float sum=dot(weights,float4(1,1,1,1));
  v.r=sum>1.e-6 ? dot(weights,float4(t00.r,t10.r,t01.r,t11.r))/sum : 0;
  return v;
 }
};MudWaves waves;
float2 wu=(P.xy-FieldMin.xy)/max(FieldSize.xy,1);
float4 wave=waves.read(Wave,WaveSampler,wu,FieldTexels.xy);
float baseBed=Texture2DSampleLevel(BaseBed,BaseBedSampler,saturate(wu),0).r;
float waterDepth=min(wave.g,max(0,Level+wave.r-baseBed-height));
'''
    m.output(g,d,common+'return smoothstep(.05,.65,waterDepth)*(all(wu>=0)&&all(wu<=1));',u.MaterialProperty.MP_OPACITY_MASK)
    m.output(g,d,common+'return float3(0,0,wave.r);',u.MaterialProperty.MP_WORLD_POSITION_OFFSET,u.CustomMaterialOutputType.CMOT_FLOAT3)
    m.output(g,d,common+'''
float2 texel=1/max(FieldTexels.xy,1);
float dx=waves.read(Wave,WaveSampler,wu+float2(texel.x,0),FieldTexels.xy).r-waves.read(Wave,WaveSampler,wu-float2(texel.x,0),FieldTexels.xy).r;
float dy=waves.read(Wave,WaveSampler,wu+float2(0,texel.y),FieldTexels.xy).r-waves.read(Wave,WaveSampler,wu-float2(0,texel.y),FieldTexels.xy).r;
float2 cell=max(FieldSize.xy/FieldTexels.xy,1);
float2 n=-float2(dx,dy)/(2*cell);
// Sub-centimetre optical roughness follows the flow; the wave shape above is physical.
float2 q=P.xy-wave.ba*Time*.2;
n+=float2(cos(dot(q,float2(.043,.021))+Time*.7),sin(dot(q,float2(-.031,.052))+Time*.5))*.003;
return normalize(float3(n*smoothstep(0,1,waterDepth),1));
''',u.MaterialProperty.MP_NORMAL,u.CustomMaterialOutputType.CMOT_FLOAT3)
    assert not u.MaterialEditingLibrary.recompile_material(w);assert assets.save_loaded_asset(w)
    s=next(a for a in actors.get_all_level_actors() if isinstance(a,u.GTLandscapeSurface))
    s.set_editor_property('puddle_surface',None);s.set_editor_property('simulated_water',None)
    for a in list(actors.get_all_level_actors()):
        if a.get_actor_label() in ['ProvingGround_ConnectedWater','MudWater_SharedPond']:actors.destroy_actor(a)
    sheet=actors.spawn_actor_from_class(u.GTWaterSheet,u.Vector())
    sheet.set_actor_location(u.Vector(0,0,0),False,True)
    sheet.set_actor_label('MudWater_SharedPond')
    for name,value in [('mud_surface',s),('mud_half_size_cm',1575.),('mud_cell_cm',25.),('base_level_cm',-4.509804),('surface_material_path',path)]:sheet.set_editor_property(name,value)
    s.set_editor_property('simulated_water',sheet)
    assert les.save_current_level()
    assert hashlib.sha256(baseline_file.read_bytes()).hexdigest()==baseline_hash,'Accepted baseline changed'
    report.update(ok=True,water_material=path,cell_cm=25,maximum_cells=16384,baseline_unchanged=True)
except Exception:report['error']=traceback.format_exc();u.log_error(report['error'])
(OUT/'setup-report.json').write_text(json.dumps(report,indent=2))
s=sheet=w=g=d=a=world=None
les.load_level('/Engine/Maps/Entry');u.SystemLibrary.collect_garbage();quit_at=time.monotonic()+5
def finish(dt):
    if time.monotonic()>=quit_at:u.unregister_slate_post_tick_callback(handle);u.SystemLibrary.quit_editor()
u.EditorPythonScripting.set_keep_python_script_alive(True);handle=u.register_slate_post_tick_callback(finish)
