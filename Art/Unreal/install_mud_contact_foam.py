"""Add bounded contact shading to the approved shared water, preserving its motion."""
import sys,time,json,traceback,shutil,hashlib
from pathlib import Path
import unreal as u
ROOT=Path(u.Paths.project_dir()).resolve();sys.path.insert(0,str(ROOT/'Art/Unreal'))
from benmore_river_life_materials import Graph
OUT=ROOT/'Art/Export/MudContactFoam';OUT.mkdir(parents=True,exist_ok=True)
PATH='/Game/GrandTour/ArtTests/MudWater/M_MudWater'
mel=u.MaterialEditingLibrary;assets=u.EditorAssetLibrary
report=dict(ok=False,material=PATH)
try:
    maps=list((ROOT/'Content/GrandTour/ArtTests/RutInteraction').glob('*.umap'))+[ROOT/'Content/GrandTour/ArtTests/MudWater/L_MudWater.umap']
    hashes={str(p):hashlib.sha256(p.read_bytes()).hexdigest() for p in maps}
    src=ROOT/'Content/GrandTour/ArtTests/MudWater/M_MudWater.uasset'
    backup=ROOT/'Saved/MudContactFoam'/str(time.time_ns());backup.mkdir(parents=True)
    shutil.copy2(src,backup/src.name);report['backup']=str(backup)
    w=u.load_asset(PATH);assert w
    mask=mel.get_material_property_input_node(w,u.MaterialProperty.MP_OPACITY_MASK)
    vertex=mel.get_material_property_input_node(w,u.MaterialProperty.MP_WORLD_POSITION_OFFSET)
    normal=mel.get_material_property_input_node(w,u.MaterialProperty.MP_NORMAL)
    preserved=[str(n.get_editor_property('code')) for n in [mask,vertex,normal]]
    prefix=preserved[0].split('return smoothstep(.05,.65,waterDepth)')[0]
    assert 'float waterDepth=' in prefix
    names=[str(i.get_editor_property('input_name')) for i in mask.get_editor_property('inputs')]
    sources=list(mel.get_inputs_for_material_expression(w,mask));assert len(names)==len(sources)
    for n in list(mel.get_material_expressions(w)):
        if str(n.get_editor_property('desc'))=='MudContactFoam':mel.delete_material_expression(w,n)
    g=Graph(w,'MudContactFoam');d=dict(zip(names,sources))
    d['FoamTexture']=g.node(u.MaterialExpressionTextureObjectParameter,parameter_name='MudFoamTex',texture=u.load_asset('/Engine/EngineResources/Black'),sampler_type=u.MaterialSamplerType.SAMPLERTYPE_LINEAR_COLOR)
    d['UnderDepth']=g.node(u.MaterialExpressionSceneDepthWithoutWater)
    d['PixelDepth']=g.node(u.MaterialExpressionPixelDepth)
    for name,value in [('ContactFoamEnabled',1),('ContactFoamAmount',1),('ShoreFoamWidthCm',3.8)]:
        d[name]=g.node(u.MaterialExpressionScalarParameter,parameter_name=name,default_value=value)
    code=prefix+r'''
float wake=Texture2DSampleLevel(FoamTexture,FoamTextureSampler,saturate(wu),0).r;
float shore=smoothstep(.4,1.1,waterDepth)*(1-smoothstep(1.1,max(1.2,ShoreFoamWidthCm),waterDepth));
// Sample the opaque scene before single-layer water: actual rocks, timber and
// tyres, including those below the undisplaced landscape's distance field.
// Foreground objects occlude the water; only its visible intersection is shaded.
float gap=max(0,UnderDepth-PixelDepth);
float objectBand=(1-smoothstep(1.5,7,gap))*smoothstep(.8,2,waterDepth);
float2 velocity=wave.ba;
float t0=frac(Time/3),t1=frac(Time/3+.5),blend=abs(t0*2-1);
float2 a=P.xy-velocity*t0*3*.45,b=P.xy-velocity*t1*3*.45;
float broad=lerp(grain.noise(a/19.+Time*.016),grain.noise(b/19.+Time*.016),blend);
float fine=lerp(grain.noise(a/2.7),grain.noise(b/2.7),blend);
float micro=lerp(grain.noise(a/.85),grain.noise(b/.85),blend);
float holes=smoothstep(.28,.52,fine)*(1-smoothstep(.61,.79,micro));
float lace=holes*lerp(.65,1,smoothstep(.48,.76,fine));
float edge=smoothstep(.10,.52,max(shore,objectBand))*smoothstep(.30,.61,broad)*lace*.85;
float active=smoothstep(.015,.38,wake)*lace*.87;
float foam=saturate(max(edge,active)*ContactFoamAmount)*saturate(ContactFoamEnabled);
Rough=lerp(.10,.57,foam);
Opacity=lerp(.16,.91,foam);
Specular=lerp(.25,.16,foam);
float3 scum=lerp(float3(.31,.29,.22),float3(.64,.62,.52),saturate(wake*2+.25));
return lerp(float3(.025,.024,.018),scum,foam);
'''
    n=g.custom(list(d),code,outputs=[(s,u.CustomMaterialOutputType.CMOT_FLOAT1) for s in ['Rough','Opacity','Specular']])
    for k,v in d.items():assert v;g.wire(v,n,k)
    for prop,pin in [(u.MaterialProperty.MP_BASE_COLOR,''),(u.MaterialProperty.MP_ROUGHNESS,'Rough'),(u.MaterialProperty.MP_OPACITY,'Opacity'),(u.MaterialProperty.MP_SPECULAR,'Specular')]:g.output(n,prop,pin)
    assert not mel.recompile_material(w);assert assets.save_loaded_asset(w)
    assert preserved==[str(n.get_editor_property('code')) for n in [mask,vertex,normal]]
    assert hashes=={str(p):hashlib.sha256(p.read_bytes()).hexdigest() for p in maps}
    (OUT/'contact-foam.hlsl').write_text(code)
    report.update(ok=True,maps_unchanged=True,waves_and_shoreline_unchanged=True,affected_maps=[str(p) for p in maps])
except Exception:report['error']=traceback.format_exc();u.log_error(report['error'])
(OUT/'setup-report.json').write_text(json.dumps(report,indent=2))
w=mask=vertex=normal=g=d=n=sources=None
u.SystemLibrary.collect_garbage();quit_at=time.monotonic()+5
def finish(dt):
    if time.monotonic()>=quit_at:u.unregister_slate_post_tick_callback(handle);u.SystemLibrary.quit_editor()
u.EditorPythonScripting.set_keep_python_script_alive(True);handle=u.register_slate_post_tick_callback(finish)
