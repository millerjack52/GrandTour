"""Create/review six mud characters on one isolated landscape. No benchmarks or Benmore saves."""
import json
import math
import shutil
import struct
import sys
import time
import traceback
import zlib
from pathlib import Path
import unreal as u

ROOT=Path(u.Paths.project_dir()).resolve()
sys.path.insert(0,str(ROOT/'Art/Unreal'))
from landscape_surface_material import build,COLOR,NORMAL,DISPLACEMENT,ROUGHNESS,SPECULAR
DEST='/Game/GrandTour/ArtTests/LandscapeMudVariants'
LEVEL=DEST+'/L_LandscapeMudVariants'
OUT=ROOT/'Art/Export/LandscapeSurface';OUT.mkdir(parents=True,exist_ok=True)
# Depth and softness are paint data. Wetness/cohesion/relief/fragment scale are independent character controls.
PRESETS=[
    dict(key='dry_loam',title='Dry compacted loam',depth=10,soft=.15,wet=0,cohesion=.18,relief=.2,scale=.55,table=50),
    dict(key='damp_loam',title='Damp loam',depth=10,soft=.5,wet=.5,cohesion=.32,relief=.65,scale=.8,table=50),
    dict(key='dry_clay',title='Dry clay crust',depth=30,soft=.22,wet=.03,cohesion=.6,relief=.5,scale=1.15,table=50),
    dict(key='wet_clay',title='Wet sticky clay',depth=30,soft=.8,wet=.85,cohesion=.92,relief=1.,scale=1.4,table=12),
    dict(key='crumbly_soil',title='Dry churned soil',depth=20,soft=.3,wet=.02,cohesion=.08,relief=.85,scale=.75,table=50),
    dict(key='saturated_bog',title='Deep saturated mud',depth=50,soft=1,wet=1,cohesion=.75,relief=.4,scale=1.65,table=2),
]
for i,p in enumerate(PRESETS):p.update(x=(-1000,0,1000)[i%3],y=(-700,700)[i//3])
les=u.get_editor_subsystem(u.LevelEditorSubsystem)
assets=u.EditorAssetLibrary
actors=u.get_editor_subsystem(u.EditorActorSubsystem)
report=dict(ok=False,level=LEVEL,presets=PRESETS,images=[],performance_measured=False)
phase='setup';last=start=time.monotonic();busy=False;index=0
world=surface=pc=camera=None
CAPTURES=[(i,'before') for i in range(len(PRESETS))]+[(3,'gentle')]+[(i,'after') for i in range(len(PRESETS))]
CAPTURES.append((-1,'overview'))
CAPTURES += [(3,'clay'),(5,'clay'),(3,'curved'),(3,'curved_clay'),(3,'sun'),(3,'join'),(3,'worked'),(3,'worked_clay'),(3,'pom_off'),(3,'pom_on'),(3,'overcast'),(5,'overcast')]


def prepare_clay_review():
    # A local review switch strips colour/grain, retaining the same displacement and field normals.
    material=assets.load_asset(DEST+'/M_LandscapeSurface');assert material
    mel=u.MaterialEditingLibrary
    expressions=list(mel.get_material_expressions(material))
    parameter=next((e for e in expressions if isinstance(e,u.MaterialExpressionScalarParameter) and str(e.get_editor_property('parameter_name'))=='GTLS_ClayReview'),None)
    path=ROOT/'Content/GrandTour/ArtTests/LandscapeMudVariants/M_LandscapeSurface.uasset'
    stamp=path.stat().st_mtime_ns
    backup=ROOT/'Saved/LandscapeMudVariants'/str(time.time_ns());backup.mkdir(parents=True)
    shutil.copy2(path,backup/path.name)
    report['material_backup']=str(backup/path.name)
    if parameter is None:parameter=mel.create_material_expression(material,u.MaterialExpressionScalarParameter)
    parameter.set_editor_property('parameter_name','GTLS_ClayReview');parameter.set_editor_property('default_value',0.)
    count=0
    for e in expressions:
        if not isinstance(e,u.MaterialExpressionCustom):continue
        code=e.get_editor_property('code')
        if 'return saturate((h*Enabled+50)/65)' in code:e.set_editor_property('code',DISPLACEMENT);continue
        if 'float3 fine=' in code:code='if(ClayReview>.5) return float3(.32,.32,.32);\n'+COLOR
        elif 'GTLS_ROUGHNESS' in code:code='if(ClayReview>.5) return .9;\n'+ROUGHNESS
        elif 'GTLS_SPECULAR' in code:code='if(ClayReview>.5) return .08;\n'+SPECULAR
        elif 'float2 slope=' in code:code=NORMAL.replace('return normalize(float3(BaseN.xy-tilt,BaseN.z));','return normalize(float3(BaseN.xy-lerp(tilt,slope,ClayReview),BaseN.z));')
        else:continue
        inputs=list(e.get_editor_property('inputs'))
        if not any(str(entry.get_editor_property('input_name'))=='ClayReview' for entry in inputs):
            entry=u.CustomInput();entry.set_editor_property('input_name','ClayReview');inputs.append(entry)
        e.set_editor_property('inputs',inputs);e.set_editor_property('code',code)
        assert mel.connect_material_expressions(parameter,'',e,'ClayReview');count+=1
    assert count==4
    mel.recompile_material(material)
    assert path.stat().st_mtime_ns==stamp,'Review material changed during load'
    assets.save_loaded_asset(material)


def set_clay(enabled, pom=True):
    landscape=surface.get_editor_property('landscape')
    count=0
    for component in landscape.get_components_by_class(u.LandscapeNaniteComponent):
        for i in range(component.get_num_materials()):
            material=component.get_material(i)
            if isinstance(material,u.MaterialInstanceDynamic):
                material.set_scalar_parameter_value('GTLS_ClayReview',1. if enabled else 0.)
                material.set_scalar_parameter_value('GTLS_POMEnabled',1. if pom else 0.);count+=1
    assert count>0,'No live landscape material for clay review'


def stamp_curved(p):
    # Additional steering/crossing art view; straight control captures above remain unchanged.
    x,y=p['x'],p['y']
    for i in range(56):
        a=-300+i*10.;b=a+10.
        ya=170*math.sin(a/230);yb=170*math.sin(b/230)
        dx,dy=b-a,yb-ya;length=math.hypot(dx,dy)
        for side in (-75,75):
            ox=-dy/length*side;oy=dx/length*side
            surface.stamp_wheel(u.Vector2D(x+a+ox,y+ya+oy),u.Vector2D(x+b+ox,y+yb+oy),u.Vector2D(dx/length,dy/length),28.,24.)
    report['after_curved']=surface.get_surface_report()

def stamp_worked(p):
    # Wider truck footprints and several wandering lines compare a used lane with the references.
    # Width is an explicit art-fixture input, never a change to observed vehicle tyres.
    x,y=p['x'],p['y']
    for lane in range(4):
        for i in range(54):
            a=-320+i*12.;b=a+12.
            def path(v):return (lane-1.5)*65+55*math.sin(v/(145+lane*19)+lane*1.7)
            ya,yb=path(a),path(b)
            dx,dy=b-a,yb-ya;length=math.hypot(dx,dy)
            depth=12+9*(.5+.5*math.sin(a/93+lane*2.1))
            surface.stamp_wheel(u.Vector2D(x+a,y+ya),u.Vector2D(x+b,y+yb),u.Vector2D(dx/length,dy/length),48.,depth)
    report['after_worked']=surface.get_surface_report()


def smooth(a,b,x):
    t=max(0,min(1,(x-a)/(b-a)));return t*t*(3-2*t)

def paint_file():
    n=512;data=bytearray()
    for y in range(n):
        data.append(0)
        for x in range(n):
            wx=(x+.5)/n*3150-1575;wy=(y+.5)/n*3150-1575
            rgba=(0,255,0,0)
            for p in PRESETS:
                dx=abs(wx-p['x']);dy=abs(wy-p['y'])
                mask=(1-smooth(370,440,dx))*(1-smooth(440,550,dy))
                if mask>0:
                    rgba=(round(255*p['depth']/50*mask),round(255*p['table']/50),0,round(255*p['soft']*mask));break
            data.extend(rgba)
    def chunk(k,b):return struct.pack('>I',len(b))+k+b+struct.pack('>I',zlib.crc32(k+b)&0xffffffff)
    path=OUT/'variants-paint.png'
    path.write_bytes(b'\x89PNG\r\n\x1a\n'+chunk(b'IHDR',struct.pack('>IIBBBBB',n,n,8,6,0,0,0))+chunk(b'IDAT',zlib.compress(data))+chunk(b'IEND',b''))
    return path

def setup():
    if assets.does_asset_exist(LEVEL):
        assert les.load_level(LEVEL)
        return
    # Partial setups are deliberately not overwritten.
    assert not assets.does_asset_exist(DEST+'/M_LandscapeSurface'),'Partial setup exists; preserve and inspect it'
    task=u.AssetImportTask()
    for k,v in dict(filename=str(paint_file()),destination_path=DEST,destination_name='T_MudVariantPaint',automated=True,save=True,replace_existing=False).items():task.set_editor_property(k,v)
    u.AssetToolsHelpers.get_asset_tools().import_asset_tasks([task])
    tex=assets.load_asset(DEST+'/T_MudVariantPaint');assert tex
    tex.set_editor_property('srgb',False)
    tex.set_editor_property('compression_settings',u.TextureCompressionSettings.TC_VECTOR_DISPLACEMENTMAP)
    tex.set_editor_property('mip_gen_settings',u.TextureMipGenSettings.TMGS_NO_MIPMAPS)
    material=build(tex,destination=DEST)
    assert les.new_level(LEVEL)
    ew=u.get_editor_subsystem(u.UnrealEditorSubsystem).get_editor_world()
    ew.get_world_settings().set_editor_property('default_game_mode',u.GTRunGameMode)
    land=u.GTLandscapeSurfaceSetupLibrary.create_prototype_landscape(ew,material);assert land
    land.set_editor_property('enable_nanite',True)
    land.set_editor_property('nanite_skirt_enabled',True)
    land.set_editor_property('nanite_skirt_depth',100.)
    s=actors.spawn_actor_from_class(u.GTLandscapeSurface,u.Vector(0,0,0))
    s.set_actor_label('Mud_Variants_One_Surface')
    s.set_editor_property('landscape',land)
    s.set_editor_property('paint_origin_cm',u.Vector2D(-1575,-1575))
    s.set_editor_property('paint_size_cm',3150.)
    assert u.GTLandscapeSurfaceSetupLibrary.import_paint(s,tex)
    regions=[]
    for i,p in enumerate(PRESETS):
        r=u.GTLandscapeMudRegion()
        for k,v in dict(name=p['key'],centre=u.Vector2D(p['x'],p['y']),half_size=u.Vector2D(450,560),wetness=p['wet'],cohesion=p['cohesion'],relief=p['relief'],fragment_scale=p['scale']).items():r.set_editor_property(k,v)
        regions.append(r)
        pos=u.Vector(p['x']-360,p['y']-350,165);target=u.Vector(p['x']+20,p['y']+20,0)
        c=actors.spawn_actor_from_class(u.CameraActor,pos,u.MathLibrary.find_look_at_rotation(pos,target))
        c.set_actor_label('MudReview_'+p['key']);c.camera_component.set_field_of_view(70.)
        label=actors.spawn_actor_from_class(u.TextRenderActor,u.Vector(p['x']-390,p['y']-570,60),u.Rotator(0,-90,0))
        label.set_actor_label('Label_'+p['key'])
        label.text_render.set_text(str(i+1)+'. '+p['title']+' | '+str(p['depth'])+' cm layer')
        label.text_render.set_world_size(25.)
    s.set_editor_property('mud_regions',regions)
    c=actors.spawn_actor_from_class(u.CameraActor,u.Vector(-1800,-2300,2600),u.MathLibrary.find_look_at_rotation(u.Vector(-1800,-2300,2600),u.Vector(0,0,0)))
    c.set_actor_label('MudReview_overview');c.camera_component.set_field_of_view(65.)
    actors.spawn_actor_from_class(u.SkyAtmosphere,u.Vector())
    sun=actors.spawn_actor_from_class(u.DirectionalLight,u.Vector(0,0,1000),u.Rotator(-30,-25,0))
    sun.light_component.set_editor_property('intensity',5.)
    sun.light_component.set_editor_property('atmosphere_sun_light',True)
    sky=actors.spawn_actor_from_class(u.SkyLight,u.Vector(0,0,1000))
    sky.light_component.set_editor_property('real_time_capture',True)
    actors.spawn_actor_from_class(u.PlayerStart,u.Vector(0,-1400,150))
    assets.save_loaded_asset(tex)
    u.EditorLevelLibrary.set_level_viewport_camera_info(u.Vector(-1800,-2300,2600),u.Rotator(-45,50,0))
    assert les.save_current_level()

def stamp_all():
    # Identical footprint/sweep and nominal pressure stages. Softness determines the requested response,
    # then field cohesion, floor shape and available lip capacity constrain the resulting deformation.
    for p in PRESETS:
        x,y=p['x'],p['y']
        for pressure in (12.,30.):
            for step in range(48):
                a=-300+step*12.5;b=a+12.5
                for side in (-85,85):
                    surface.stamp_wheel(u.Vector2D(x+a,y+side),u.Vector2D(x+b,y+side),u.Vector2D(1,0),28.,min(p['depth'],pressure*p['soft']))
        for _ in range(30):surface.stamp_wheel(u.Vector2D(x+180,y+85),u.Vector2D(x+180,y+85),u.Vector2D(1,0),28.,p['depth']*p['soft'])
        samples=[]
        for a in (-250,-125,0,125,180,250):
            q=surface.sample_surface(u.Vector2D(x+a,y+85))
            samples.append(dict(x=a,delta_cm=q.surface_delta_cm,water_cm=q.water_depth_cm,cap_cm=q.sinkage_cap_cm))
        p['runtime_samples']=samples
    report['after']=surface.get_surface_report()

def write_gallery():
    descriptions=[
        'Small impressions in a compact, low-relief surface.',
        'Deeper, softer impressions with small broken clods.',
        'Flatter crust plates with fissures and shallow cuts.',
        'Sheared sheets and folded slabs beside deeper cuts, with limited water in low pockets.',
        'Mixed fragments with interrupted edges and moderate sinkage.',
        'Low initial relief, deep channels and shallow standing water.',
    ]
    cards=[]
    for p,description in zip(PRESETS,descriptions):
        cards.append(f'''<article><h2>{p['title']} <span>{p['depth']} cm layer</span></h2>
<p>{description}</p><div class="pair"><figure><img src="mud_{p['key']}_before.png"><figcaption>Before</figcaption></figure>
<figure><img src="mud_{p['key']}_after.png"><figcaption>After matching wheel sweeps</figcaption></figure></div></article>''')
    comparisons=''
    for key,title in [('wet_clay','Wet clay'),('saturated_bog','Saturated mud')]:
        if (OUT/'before_pbr'/('mud_'+key+'_after.png')).exists():
            comparisons+=f'''<article><h2>{title}: previous and scanned surface</h2><div class="pair">
<figure><img src="before_pbr/mud_{key}_after.png"><figcaption>Previous procedural surface</figcaption></figure>
<figure><img src="mud_{key}_after.png"><figcaption>Scanned relief, deformation and parallax</figcaption></figure></div></article>'''
    diagnostics=''
    for key,stage,title in [('wet_clay','overcast','Worked wet clay: overcast'),('saturated_bog','overcast','Deep wet mud: overcast'),('wet_clay','gentle','Shallower 10 cm wheel pass'),('wet_clay','worked','Overlapping wandering passes'),('wet_clay','worked_clay','Worked lane: geometry'),('wet_clay','pom_off','Close view: parallax off'),('wet_clay','pom_on','Same close view: parallax on'),('wet_clay','clay','Wet clay geometry'),('saturated_bog','clay','Saturated mud geometry'),
                            ('wet_clay','curved','Curved and crossing passes'),('wet_clay','curved_clay','Crossed tracks: geometry'),
                            ('wet_clay','sun','Opposite viewing direction'),('wet_clay','join','Mud / firm-ground join')]:
        if (OUT/f'mud_{key}_{stage}.png').exists():diagnostics+=f'<figure><img src="mud_{key}_{stage}.png"><figcaption>{title}</figcaption></figure>'
    references=''.join(f'<a href="reference-mudrunner-{i}.jpg"><img style="height:280px;object-fit:contain" src="reference-mudrunner-{i}.jpg" alt="Owner MudRunner reference {i}"></a>' for i in range(1,4) if (OUT/f'reference-mudrunner-{i}.jpg').exists())
    (OUT/'mud-variants.html').write_text('''<!doctype html><html lang="en"><meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1"><title>Mud variants</title>
<style>body{margin:32px auto;padding:0 24px;max-width:1600px;background:#191b18;color:#e7e3d7;font:16px/1.5 system-ui}
h1{font-size:36px;margin-bottom:8px}h2{font-size:23px}span{font-size:16px;color:#c3b997;margin-left:16px}
article{border-top:1px solid #45483c;margin-top:32px}.pair{display:grid;grid-template-columns:1fr 1fr;gap:16px}
figure{margin:0}img{width:100%;display:block}figcaption{padding:8px 0;color:#babdae}
@media(max-width:800px){.pair{grid-template-columns:1fr}}a{color:#ded1a8}</style>
<h1>Mud variants</h1><p>Six surface studies: dry and wet, shallow and deep. Layer depth is available mud thickness;
actual rut depth depends on softness, shape and room for displaced soil.</p>
<p>Scanned height data now forms the broad terrain relief and participates in excavation and deposition.
Matched colour, normal, roughness and occlusion maps provide the surface detail; parallax adds close relief.
The matching sweeps are an art fixture, not a vehicle physics benchmark. Deep straight sweeps are stress views;
the additional shallow and worked-lane views show different disturbance histories.</p>
<p>CC0 scans: <a href="https://polyhaven.com/a/brown_mud_02">Brown Mud 02</a> and
<a href="https://polyhaven.com/a/mud_cracked_dry_03">Mud Cracked Dry 03</a> (Poly Haven).</p>'''+
        ('<h2>Owner references</h2><div class="pair">'+references+'</div>' if references else '')+comparisons+
        '<h2>Geometry and difficult views</h2><div class="pair">'+diagnostics+'</div>'+''.join(cards)+
        '<h2>Layout</h2><img src="mud_overview_overview.png" alt="Six mud patches on the comparison landscape"></html>',encoding='utf-8')


def finish(error=None):
    global phase,last,world,surface,pc,camera
    if error:report['error']=error;u.log_error(error)
    (OUT/'variants-report.json').write_text(json.dumps(report,indent=2))
    if not error:write_gallery()
    phase='ending';last=time.monotonic()
    world=surface=pc=camera=None
    u.EditorLevelLibrary.editor_end_play()

def body():
    global phase,last,index,world,surface,pc,camera,shot_time
    now=time.monotonic()
    if phase=='ending':
        if now-last>5 and u.EditorLevelLibrary.get_game_world() is None:
            u.unregister_slate_post_tick_callback(handle);u.SystemLibrary.quit_editor()
        return
    if now-start>600:finish('Variant capture timed out');return
    if phase=='setup':
        setup();prepare_clay_review()
        from landscape_mud_pbr import install
        install(DEST,PRESETS,report)
        phase='play';last=time.monotonic()
    elif phase=='play' and now-last>8:
        assert u.GTPlayWindowLibrary.request_play_in_new_window(1440,900)
        phase='warm';last=now
    elif phase=='warm' and now-last>15:
        world=u.EditorLevelLibrary.get_game_world()
        if world is None:return
        pc=u.GameplayStatics.get_player_controller(world,0)
        surface=next(iter(u.GameplayStatics.get_all_actors_of_class(world,u.GTLandscapeSurface)))
        surface.set_editor_property('observe_player_wheels',False);surface.set_editor_property('follow_player',False)
        report['before']=surface.get_surface_report()
        assert 'displacement_scale_valid=1' in report['before']
        phase='aim';last=now
    elif phase=='aim':
        i,stage=CAPTURES[index];key=PRESETS[i]['key'] if i>=0 else 'overview'
        if stage=='after' and i==0:stamp_all()
        if stage=='gentle':
            p=PRESETS[i]
            for step in range(48):
                a=-300+step*12.5;b=a+12.5
                for side in (-85,85):
                    surface.stamp_wheel(u.Vector2D(p['x']+a,p['y']+side),u.Vector2D(p['x']+b,p['y']+side),u.Vector2D(1,0),28.,10.)
        set_clay('clay' in stage,stage!='pom_off')
        if stage=='curved':stamp_curved(PRESETS[i])
        if stage=='worked':stamp_worked(PRESETS[i])
        camera=next(a for a in u.GameplayStatics.get_all_actors_of_class(world,u.CameraActor) if a.get_actor_label()=='MudReview_'+key)
        if stage in ('sun','join','worked','worked_clay'):
            p=PRESETS[i]
            pos=u.Vector(p['x']+350,p['y']-320,160) if stage in ('sun','worked','worked_clay') else u.Vector(p['x']-430,p['y']-420,160)
            target=u.Vector(p['x']-100,p['y']+80,0) if stage in ('sun','worked','worked_clay') else u.Vector(p['x']-390,p['y'],0)
            camera.set_actor_location(pos,False,False);camera.set_actor_rotation(u.MathLibrary.find_look_at_rotation(pos,target),False)
        if stage in ('pom_off','pom_on'):
            p=PRESETS[i];pos=u.Vector(p['x']+210,p['y']-180,60);target=u.Vector(p['x']-50,p['y']+20,0)
            camera.set_actor_location(pos,False,False);camera.set_actor_rotation(u.MathLibrary.find_look_at_rotation(pos,target),False)
        if stage=='overcast':
            weather=next(o for o in u.ObjectIterator(u.GTWeatherSubsystem) if o.get_outer()==world)
            weather.set_state(weather.find_state('Overcast'),True)
            p=PRESETS[i];pos=u.Vector(p['x']-360,p['y']-350,165);target=u.Vector(p['x']+20,p['y']+20,0)
            camera.set_actor_location(pos,False,False);camera.set_actor_rotation(u.MathLibrary.find_look_at_rotation(pos,target),False)
        pc.set_view_target_with_blend(camera,0.)
        phase='capture';last=now
    elif phase=='capture' and now-last>3:
        i,stage=CAPTURES[index];key=PRESETS[i]['key'] if i>=0 else 'overview'
        path=OUT/('mud_'+key+'_'+stage+'.png')
        report['images'].append(str(path));shot_time=time.time()
        u.SystemLibrary.execute_console_command(world,'HighResShot 1440x900 filename="'+path.as_posix()+'"',pc)
        phase='wait';last=now
    elif phase=='wait' and now-last>3:
        path=Path(report['images'][-1])
        if not path.exists() or path.stat().st_mtime<shot_time:return
        index+=1
        if index==len(CAPTURES):report['ok']=True;finish();return
        phase='aim';last=now

def tick(dt):
    global busy
    if busy:return
    busy=True
    try:body()
    except Exception:finish(traceback.format_exc())
    finally:busy=False

u.EditorPythonScripting.set_keep_python_script_alive(True)
handle=u.register_slate_post_tick_callback(tick)
