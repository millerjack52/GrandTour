"""A reusable dressed forest-track study around the approved scanned landscape mud."""
import json
import hashlib
import math
import random
import shutil
import struct
import time
import traceback
import zlib
from pathlib import Path
import unreal as u

ROOT=Path(u.Paths.project_dir()).resolve()
DEST='/Game/GrandTour/ArtTests/LandscapeMudScene'
LEVEL=DEST+'/L_LandscapeMudScene'
SOURCE='/Game/GrandTour/ArtTests/LandscapeMudVariants'
OUT=ROOT/'Art/Export/LandscapeMudScene';OUT.mkdir(parents=True,exist_ok=True)
assets=u.EditorAssetLibrary;mel=u.MaterialEditingLibrary
actors=u.get_editor_subsystem(u.EditorActorSubsystem);les=u.get_editor_subsystem(u.LevelEditorSubsystem)
report=dict(ok=False,level=LEVEL,counts={},images=[],performance_measured=False)
phase='setup';last=started=time.monotonic();busy=False;index=0;world=pc=surface=None
VIEWS=[('approach',(-1120,-120,165),(600,60,35)),
       ('debris',(-400,-280,160),(100,150,0)),
       ('puddle',(330,260,160),(820,-80,0)),
       ('reverse',(1080,120,165),(-600,-60,25)),
       ('low_detail',(-150,-240,70),(150,90,0)),
       ('overview',(-1300,-1500,1700),(0,0,0))]

def props(o,**kw):
    for k,v in kw.items():o.set_editor_property(k,v)
    return o

def line(x):return 110*math.sin(x/410)+45*math.sin(x/180)

def smooth(a,b,x):
    t=max(0,min(1,(x-a)/(b-a)));return t*t*(3-2*t)

def paint():
    # Numeric authoring data: R thickness, G water-table depth, B gravel, A softness.
    n=512;raw=bytearray()
    for j in range(n):
        raw.append(0)
        y=(j+.5)/n*3150-1575
        for i in range(n):
            x=(i+.5)/n*3150-1575;d=abs(y-line(x))
            width=235+28*math.sin(x/197)+20*math.sin(x/71)
            mask=(1-smooth(width,width+100,d))*(1-smooth(1250,1450,abs(x)))
            basin=math.exp(-((x-570)/390)**2-((y-line(x))/190)**2)
            depth=(25+20*basin)*mask
            table=12-10*basin
            raw.extend((round(depth/50*255),round(table/50*255),0,round((.67+.27*basin)*mask*255)))
    def chunk(k,b):return struct.pack('>I',len(b))+k+b+struct.pack('>I',zlib.crc32(k+b)&0xffffffff)
    p=OUT/'scene-paint.png'
    p.write_bytes(b'\x89PNG\r\n\x1a\n'+chunk(b'IHDR',struct.pack('>IIBBBBB',n,n,8,6,0,0,0))+chunk(b'IDAT',zlib.compress(raw))+chunk(b'IEND',b''))
    task=props(u.AssetImportTask(),filename=str(p),destination_path=DEST,destination_name='T_ScenePaint',automated=True,replace_existing=True,save=True)
    u.AssetToolsHelpers.get_asset_tools().import_asset_tasks([task])
    t=assets.load_asset(DEST+'/T_ScenePaint');assert t
    props(t,srgb=False,compression_settings=u.TextureCompressionSettings.TC_VECTOR_DISPLACEMENTMAP,mip_gen_settings=u.TextureMipGenSettings.TMGS_NO_MIPMAPS)
    return t

def place_light(cls,label,pos,rot=None):
    a=actors.spawn_actor_from_class(cls,u.Vector(*pos),u.Rotator(*rot) if rot else u.Rotator())
    a.set_actor_label('MudScene_'+label);return a

def setup():
    global scene_surface
    if assets.does_asset_exist(LEVEL):
        assert les.load_level(LEVEL)
        source=ROOT/'Content/GrandTour/ArtTests/LandscapeMudScene/L_LandscapeMudScene.umap'
        backup=ROOT/'Saved/LandscapeMudScene'/str(time.time_ns());backup.mkdir(parents=True)
        shutil.copy2(source,backup/source.name);report['backup']=str(backup/source.name)
    else:assert les.new_level(LEVEL)
    ew=u.get_editor_subsystem(u.UnrealEditorSubsystem).get_editor_world()
    ew.get_world_settings().set_editor_property('default_game_mode',u.GTRunGameMode)
    # Only generated dressing/lights/cameras in this dedicated study are refreshed.
    for a in actors.get_all_level_actors():
        if a.get_actor_label().startswith('MudScene_') and not isinstance(a,(u.GTLandscapeSurface,u.LandscapeProxy)):
            actors.destroy_actor(a)
    matpath=DEST+'/M_MudScene'
    if not assets.does_asset_exist(matpath):assert assets.duplicate_asset(SOURCE+'/M_LandscapeSurface',matpath)
    mat=assets.load_asset(matpath);t=paint()
    for e in mel.get_material_expressions(mat):
        if isinstance(e,u.MaterialExpressionTextureObjectParameter) and str(e.get_editor_property('parameter_name'))=='GTLS_Paint':e.set_editor_property('texture',t)
    mel.recompile_material(mat);assets.save_loaded_asset(mat)
    lands=[a for a in actors.get_all_level_actors() if isinstance(a,u.LandscapeProxy)]
    land=lands[0] if lands else u.GTLandscapeSurfaceSetupLibrary.create_prototype_landscape(ew,mat)
    assert land;land.set_actor_label('MudScene_Landscape')
    land.set_actor_location(u.Vector(-3150,-3150,0),False,False);land.set_actor_scale3d(u.Vector(100,100,100))
    props(land,landscape_material=mat,enable_nanite=True,nanite_skirt_enabled=True,nanite_skirt_depth=100.)
    displacement=next(e for e in mel.get_material_expressions(mat) if isinstance(e,u.MaterialExpressionCustom) and 'return saturate((h*Enabled+50)/65)' in e.get_editor_property('code'))
    assert u.GTLandscapeSurfaceSetupLibrary.connect_displacement(mat,displacement,0,100.)
    mel.recompile_material(mat);assets.save_loaded_asset(mat)
    surfaces=[a for a in actors.get_all_level_actors() if isinstance(a,u.GTLandscapeSurface)]
    s=surfaces[0] if surfaces else actors.spawn_actor_from_class(u.GTLandscapeSurface,u.Vector())
    s.set_actor_label('MudScene_Surface');scene_surface=s
    props(s,landscape=land,paint_origin_cm=u.Vector2D(-1575,-1575),paint_size_cm=3150.,observe_player_wheels=True,follow_player=True)
    assert u.GTLandscapeSurfaceSetupLibrary.import_paint(s,t)
    region=props(u.GTLandscapeMudRegion(),name='Forest_track',centre=u.Vector2D(),half_size=u.Vector2D(1575,1575),wetness=.82,cohesion=.86,relief=.68,fragment_scale=1.3)
    s.set_editor_property('mud_regions',[region])
    assert u.GTLandscapeSurfaceSetupLibrary.import_rest_heights(s,assets.load_asset(SOURCE+'/PBR/T_brown_mud_02_Displacement'),assets.load_asset(SOURCE+'/PBR/T_mud_cracked_dry_03_Displacement'))
    dressing(s)
    place_light(u.SkyAtmosphere,'Atmosphere',(0,0,0))
    sun=place_light(u.DirectionalLight,'Sun',(0,0,1400),(-38,-25,0))
    props(sun.light_component,intensity=3.,atmosphere_sun_light=True,light_source_angle=8.)
    sky=place_light(u.SkyLight,'Sky',(0,0,900));props(sky.light_component,real_time_capture=True,intensity=3.)
    fog=place_light(u.ExponentialHeightFog,'Mist',(0,0,-100))
    props(fog.get_component_by_class(u.ExponentialHeightFogComponent),fog_density=.018,fog_height_falloff=.25,start_distance=1400.)
    for key,pos,target in VIEWS:
        camera=actors.spawn_actor_from_class(u.CameraActor,u.Vector(*pos),u.MathLibrary.find_look_at_rotation(u.Vector(*pos),u.Vector(*target)))
        camera.set_actor_label('MudScene_Camera_'+key);camera.camera_component.set_field_of_view(72.)
        camera.camera_component.set_editor_property('constrain_aspect_ratio',False)
    place_light(u.PlayerStart,'PlayerStart',(-1240,-440,160),(0,10,0))
    u.EditorLevelLibrary.set_level_viewport_camera_info(u.Vector(-1120,-120,165),u.MathLibrary.find_look_at_rotation(u.Vector(-1120,-120,165),u.Vector(600,60,35)))
    assets.save_loaded_asset(t);assert les.save_current_level()

def dressing(s):
    rng=random.Random(2026101401)
    anchor_groups=[];bounds={};samples=[]
    palette={}
    def muted_material(source):
        if not source:return source
        path=source.get_path_name()
        if path in palette:return palette[path]
        name='M_Forest_'+hashlib.sha1(path.encode()).hexdigest()[:10]
        destination=DEST+'/'+name
        m=assets.load_asset(destination) if assets.does_asset_exist(destination) else assets.duplicate_asset(path,destination)
        assert m,path
        palette[path]=m
        if isinstance(m,u.MaterialInstanceConstant):
            mel.set_material_instance_parent(m,muted_material(source.get_editor_property('parent')))
        elif isinstance(m,u.Material):
            for prop in [u.MaterialProperty.MP_BASE_COLOR,u.MaterialProperty.MP_SUBSURFACE_COLOR]:
                old=mel.get_material_property_input_node(m,prop)
                if not old:continue
                if isinstance(old,u.MaterialExpressionCustom) and old.get_editor_property('desc')=='MudScene muted forest palette':continue
                output=mel.get_material_property_input_node_output_name(m,prop)
                n=props(mel.create_material_expression(m,u.MaterialExpressionCustom),desc='MudScene muted forest palette',
                    output_type=u.CustomMaterialOutputType.CMOT_FLOAT3,inputs=[props(u.CustomInput(),input_name='C')],
                    code='float l=dot(C,float3(.2126,.7152,.0722)); return lerp(C,l*float3(.86,.92,.67),.78)*.82;')
                assert mel.connect_material_expressions(old,output,n,'C')
                assert mel.connect_material_property(n,'',prop)
            mel.set_material_usage(m,u.MaterialUsage.MATUSAGE_INSTANCED_STATIC_MESHES)
            mel.recompile_material(m)
        assets.save_loaded_asset(m)
        return m
    grassmat=assets.load_asset(DEST+'/M_VergeGrass') if assets.does_asset_exist(DEST+'/M_VergeGrass') else u.AssetToolsHelpers.get_asset_tools().create_asset('M_VergeGrass',DEST,u.Material,u.MaterialFactoryNew())
    for e in list(mel.get_material_expressions(grassmat)):mel.delete_material_expression(grassmat,e)
    props(grassmat,two_sided=True,shading_model=u.MaterialShadingModel.MSM_TWO_SIDED_FOLIAGE)
    node=props(mel.create_material_expression(grassmat,u.MaterialExpressionCustom),output_type=u.CustomMaterialOutputType.CMOT_FLOAT3,
        inputs=[props(u.CustomInput(),input_name=n) for n in ('P','V')],code='''
float patch=frac(sin(dot(floor(P.xy/180),float2(12.9898,78.233)))*43758.5453);
float tip=saturate(P.z/55.);
float3 root=float3(.045,.062,.023),straw=float3(.23,.21,.115);
return lerp(root,straw,saturate(tip*.7+patch*.28))*(.8+.3*dot(V.rgb,float3(.3,.5,.2)));
''')
    for cls,pin in [(u.MaterialExpressionWorldPosition,'P'),(u.MaterialExpressionVertexColor,'V')]:assert mel.connect_material_expressions(mel.create_material_expression(grassmat,cls),'',node,pin)
    for prop in [u.MaterialProperty.MP_BASE_COLOR,u.MaterialProperty.MP_SUBSURFACE_COLOR]:assert mel.connect_material_property(node,'',prop)
    for prop,value in [(u.MaterialProperty.MP_ROUGHNESS,.9),(u.MaterialProperty.MP_SPECULAR,.1)]:
        c=props(mel.create_material_expression(grassmat,u.MaterialExpressionConstant),r=value);mel.connect_material_property(c,'',prop)
    mel.set_material_usage(grassmat,u.MaterialUsage.MATUSAGE_INSTANCED_STATIC_MESHES);mel.recompile_material(grassmat);assets.save_loaded_asset(grassmat)
    def group(key,paths,rows,axis='xy',sink=0.,anchor=False,floating=False):
        a=actors.spawn_actor_from_class(u.Actor,u.Vector());a.set_actor_label('MudScene_Detail_'+key)
        if floating:a.set_editor_property('tags',['MudStudyFloat'])
        if anchor:anchor_groups.append(a)
        counts=0
        for k,path in enumerate(paths):
            mesh=assets.load_asset(path);assert mesh,path
            b=mesh.get_bounds();bounds[path]=[b.box_extent.x*2,b.box_extent.y*2,b.box_extent.z*2]
            ts=[]
            for row in rows:
                if row['kind']%len(paths)!=k:continue
                sc=row['size']/(2*b.box_extent.z if axis=='z' else 2*max(b.box_extent.x,b.box_extent.y))
                sz=sc*row.get('flatten',1.)
                z=-(b.origin.z-b.box_extent.z)*sz-row.get('sink',sink)
                ts.append(u.Transform(u.Vector(row['x'],row['y'],z),u.Rotator(yaw=row['yaw']),u.Vector(sc,sc,sz)));counts+=1
                if anchor:samples.append(dict(category=key,x=row['x'],y=row['y'],size=row['size']))
            if not ts:continue
            c=u.GTVegetationSubsystem.add_tagged_instances(a,mesh,ts,'MudStudy','BlockAll' if key in ('trees','logs') else 'NoCollision',key not in ('grass','litter','pebbles'))
            if key=='grass':c.set_material(0,grassmat)
            if key in ('shrubs','trees','logs'):
                for slot in range(c.get_num_materials()):c.set_material(slot,muted_material(c.get_material(slot)))
            if key in ('branches','twigs'):c.set_material(0,assets.load_asset('/Game/GrandTour/Demo/BenmoreRoads/Scenery/M_Benmore_WillowBark'))
            if anchor:c.set_mobility(u.ComponentMobility.MOVABLE)
            props(c,affect_distance_field_lighting=False,visible_in_ray_tracing=key in ('trees','logs','rocks'),receives_decals=False)
            c.set_cull_distances(10000,18000)
        report['counts'][key]=counts
    def row(x,y,size,kind=0,**extra):return dict(x=x,y=y,size=size,kind=kind,yaw=rng.uniform(0,360),**extra)
    scene='/Game/GrandTour/Demo/BenmoreRoads/Scenery/'
    gd='/Game/GrandTour/ArtTests/GroundDetail/'
    grass=[];shrubs=[];trees=[]
    # A continuous low verge, with patches of taller straw and an open running surface.
    for _ in range(3000):
        x=rng.uniform(-1500,1500);y=rng.uniform(-1500,1500);d=abs(y-line(x))
        if d<265 or rng.random()>.48+.28*math.sin(x/310)*math.sin(y/230):continue
        size=rng.uniform(20,44) if d<460 else rng.uniform(28,58)
        grass.append(row(x,y,size,rng.randrange(3)))
    for _ in range(60):
        x=rng.uniform(-1480,1480);side=rng.choice((-1,1));y=line(x)+side*rng.uniform(440,1350)
        if abs(y)>1480:continue
        shrubs.append(row(x,y,rng.uniform(70,150),rng.randrange(2)))
    for x,y,size,kind in [(-820,-780,1050,1),(-250,780,950,1),(750,-900,800,0),(1280,840,1250,2),(-1250,950,1100,2)]:trees.append(row(x,y,size,kind))
    for _ in range(22):
        x=rng.uniform(-1450,1450);y=rng.choice((-1,1))*rng.uniform(880,1450)
        if any(math.hypot(x-r['x'],y-r['y'])<350 for r in trees):continue
        trees.append(row(x,y,rng.uniform(750,1250),rng.randrange(3)))
    for _ in range(58):
        x=rng.uniform(-2900,2900);y=rng.uniform(-2900,2900)
        if abs(x)<1450 and abs(y)<1500:continue
        trees.append(row(x,y,rng.uniform(850,1450),rng.randrange(3)))
    for _ in range(1800):
        x=rng.uniform(-2900,2900);y=rng.uniform(-2900,2900)
        if abs(x)<1450 and abs(y)<1500:continue
        grass.append(row(x,y,rng.uniform(35,65),rng.randrange(3)))
    group('grass',['/Game/GrandTour/ArtTests/TussockStyle/SM_TS_'+k for k in ['Straw','Rust','Fine']],grass,'z',sink=4)
    group('shrubs',['/Game/GrandTour/Dressing/Nanite/SM_GTN_SM_BirchBush_01_Summer','/Game/GrandTour/Dressing/Nanite/SM_GTN_SM_BirchBush_04_Summer'],shrubs,'z',sink=8)
    group('trees',[scene+'SM_Willow_Young','/Game/OWGame/Dev/DressingLab/Trees/SM_OWBirch_Sparse_A','/Game/OWGame/Dev/DressingLab/Trees/SM_OWFir_AncientSparse_A'],trees,'z',sink=12)
    stones=[];pebbles=[];twigs=[];branches=[];litter=[]
    # Debris collects in loose islands on shoulders; density falls sharply inside tyre lines.
    centres=[(-800,-245),(-470,240),(-100,-225),(350,260),(800,-260),(1000,225)]
    for cx,side in centres:
        cy=line(cx)+side
        for _ in range(rng.randrange(18,34)):
            x=cx+rng.gauss(0,65);y=cy+rng.gauss(0,38)
            pebbles.append(row(x,y,rng.uniform(3,11),rng.randrange(4),flatten=rng.uniform(.55,.85),sink=1.2))
        for _ in range(5):stones.append(row(cx+rng.gauss(0,68),cy+rng.gauss(0,42),rng.uniform(14,38),rng.randrange(3),flatten=rng.uniform(.6,.9),sink=3.))
        for _ in range(rng.randrange(14,24)):
            litter.append(row(cx+rng.gauss(0,65),cy+rng.gauss(0,40),rng.uniform(5,12),rng.randrange(4),sink=.25))
        for _ in range(5):twigs.append(row(cx+rng.gauss(0,55),cy+rng.gauss(0,45),rng.uniform(15,34),rng.randrange(3),sink=.7))
        for _ in range(2):branches.append(row(cx+rng.gauss(0,42),cy+rng.gauss(0,36),rng.uniform(52,95),rng.randrange(2),sink=.8,flatten=1.6))
    # A few transported pieces reach the track, without filling it with a uniform scatter.
    for x,yaw in [(-650,28),(-190,-32),(530,14),(850,-24)]:
        r=row(x,line(x)+rng.choice((-145,145)),rng.uniform(65,105),rng.randrange(2),sink=.8,flatten=1.6);r['yaw']=yaw;branches.append(r)
    group('pebbles',[gd+'SM_GD_Pebble'+str(k) for k in range(4)],pebbles,anchor=True)
    group('rocks',[scene+'SM_Benmore_Rock'+str(k) for k in (1,2,3)],stones,anchor=True)
    group('twigs',[gd+'SM_GD_Twig'+str(k) for k in range(3)],twigs,anchor=True)
    group('branches',['/Game/GrandTour/ArtTests/MudRoads/SM_MRD_Branch'+str(k) for k in range(2)],branches,anchor=True)
    group('litter',[gd+'SM_GD_Litter'+str(k) for k in range(4)],litter,anchor=True,floating=True)
    logs=[row(-530,line(-530)-405,240,0,sink=8),row(450,line(450)+490,320,1,sink=10),row(1040,-490,200,0,sink=7)]
    logs[0]['yaw']=8;logs[1]['yaw']=-12
    group('logs',['/Game/ANGRY_MESH/StylizedPack_MeadowEnvironment/Meshes/Props/Props_Summer/SM_Log_0'+str(k)+'_Summer' for k in (1,2)],logs)
    study=actors.spawn_actor_from_class(u.GTMudDetailStudy,u.Vector());study.set_actor_label('MudScene_RuntimeDressing')
    props(study,surface=s,debris_groups=anchor_groups,seed_tracks_on_play=True)
    report['mesh_dimensions_cm']=bounds;report['debris_samples']=samples

def finish(error=None):
    global phase,last,world,pc,surface
    if error:report['error']=error;u.log_error(error)
    (OUT/'scene-report.json').write_text(json.dumps(report,indent=2))
    if not error:
        cards=''.join(f'<figure><a href="{key}.png"><img src="{key}.png"></a><figcaption>{key.replace("_"," ").title()}</figcaption></figure>' for key,_,_ in VIEWS)
        (OUT/'mud-scene.html').write_text('''<!doctype html><meta charset="utf-8"><title>Mud forest-track study</title>
<style>body{max-width:1500px;margin:32px auto;padding:0 24px;background:#191d19;color:#e0dccd;font:17px/1.5 system-ui}h1{font-size:32px}main{display:grid;grid-template-columns:1fr 1fr;gap:24px}figure{margin:0}img{width:100%}figcaption{padding:8px 0}a{color:#c4d4b9}@media(max-width:800px){main{grid-template-columns:1fr}}</style>
<h1>Mud forest-track study</h1><p>A short worn track with wet hollows, grass shoulders, fallen wood, leaf litter and embedded stones.
Debris is grouped around the margins; the running surface stays readable. The small debris follows the deforming surface during Play.</p>
<p>Open <b>/Game/GrandTour/ArtTests/LandscapeMudScene/L_LandscapeMudScene</b> and Play to inspect or drive it.
The road starts worn; further wheel contacts can deform it. Small debris is decorative, without collision or rigid-body interaction.</p><main>'''+cards+'</main>',encoding='utf-8')
    phase='ending';last=time.monotonic();world=pc=surface=None
    u.EditorLevelLibrary.editor_end_play()

def body():
    global phase,last,index,world,pc,surface,shot_time
    now=time.monotonic()
    if phase=='ending':
        if now-last>5 and u.EditorLevelLibrary.get_game_world() is None:u.unregister_slate_post_tick_callback(handle);u.SystemLibrary.quit_editor()
        return
    if now-started>600:raise RuntimeError('Mud scene capture timed out')
    if phase=='setup':setup();phase='play';last=time.monotonic()
    elif phase=='play' and now-last>10:
        assert u.GTPlayWindowLibrary.request_play_in_new_window(1440,900);phase='warm';last=now
    elif phase=='warm' and now-last>20:
        world=u.EditorLevelLibrary.get_game_world()
        if world is None:return
        pc=u.GameplayStatics.get_player_controller(world,0)
        surface=next(iter(u.GameplayStatics.get_all_actors_of_class(world,u.GTLandscapeSurface)))
        props(surface,observe_player_wheels=False,follow_player=False)
        pawn=u.GameplayStatics.get_player_pawn(world,0)
        if pawn:pawn.set_actor_hidden_in_game(True)
        u.SystemLibrary.execute_console_command(world,'showhud',pc)
        report['surface']=surface.get_surface_report();assert 'displacement_scale_valid=1' in report['surface']
        phase='aim'
    elif phase=='aim':
        key,_,_=VIEWS[index]
        camera=next(a for a in u.GameplayStatics.get_all_actors_of_class(world,u.CameraActor) if a.get_actor_label()=='MudScene_Camera_'+key)
        pc.set_view_target_with_blend(camera,0.);phase='capture';last=now
    elif phase=='capture' and now-last>5:
        path=OUT/(VIEWS[index][0]+'.png');shot_time=time.time();report['images'].append(str(path))
        u.SystemLibrary.execute_console_command(world,'HighResShot 1440x900 filename="'+path.as_posix()+'"',pc)
        phase='wait';last=now
    elif phase=='wait' and now-last>3:
        p=Path(report['images'][-1])
        if not p.exists() or p.stat().st_mtime<shot_time:return
        index+=1
        if index==len(VIEWS):report['ok']=True;finish();return
        phase='aim'

def tick(dt):
    global busy
    if busy:return
    busy=True
    try:body()
    except Exception:finish(traceback.format_exc())
    finally:busy=False

u.EditorPythonScripting.set_keep_python_script_alive(True)
handle=u.register_slate_post_tick_callback(tick)
