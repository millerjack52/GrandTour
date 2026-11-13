"""Clone the approved forest study into a drivable surface-response review. No Benmore level writes."""
import sys,json,time,traceback,math,struct,zlib,shutil
from pathlib import Path
import unreal as u
ROOT=Path(u.Paths.project_dir()).resolve();sys.path.insert(0,str(ROOT/'Art/Unreal'))
from benmore_river_life_materials import props
import mud_response_materials as materials
BASE=materials.BASE;LEVEL=BASE+'/L_MudResponse'
OUT=ROOT/'Art/Export/MudResponse';OUT.mkdir(parents=True,exist_ok=True)
les=u.get_editor_subsystem(u.LevelEditorSubsystem);actors=u.get_editor_subsystem(u.EditorActorSubsystem);assets=u.EditorAssetLibrary
report=dict(ok=False,level=LEVEL,grass_depths_cm=[2,5,8],handling_changed=True)

def smooth(a,b,x):
    t=max(0,min(1,(x-a)/(b-a)));return t*t*(3-2*t)

def setup():
    target=ROOT/'Content/GrandTour/ArtTests/MudResponse/L_MudResponse.umap'
    if target.exists():
        backup=ROOT/'Saved/MudResponse'/str(time.time_ns());backup.mkdir(parents=True);shutil.copy2(target,backup/target.name)
        assert les.load_level(LEVEL)
    else:
        assert les.load_level('/Game/GrandTour/ArtTests/LandscapeMudScene/L_LandscapeMudScene')
        world=u.get_editor_subsystem(u.UnrealEditorSubsystem).get_editor_world()
        assert u.EditorLoadingAndSavingUtils.save_map(world,LEVEL)
    land=next(a for a in actors.get_all_level_actors() if isinstance(a,u.LandscapeProxy))
    s=next(a for a in actors.get_all_level_actors() if isinstance(a,u.GTLandscapeSurface))
    study=next(a for a in actors.get_all_level_actors() if isinstance(a,u.GTMudDetailStudy))
    s.enable_wheel_support=True;study.seed_depth_scale=.28
    grass=next(a for a in actors.get_all_level_actors() if a.get_actor_label()=='MudScene_Detail_grass')
    grass.tags=list(grass.tags)+([] if 'MudStudyGrass' in [str(t) for t in grass.tags] else ['MudStudyGrass'])
    groups=list(study.debris_groups)
    if grass not in groups:study.debris_groups=groups+[grass]
    # Short grazed cover leaves the 2-8 cm surface response legible in these review strips.
    for a in actors.get_all_level_actors():
        if a.get_actor_label()=='MudScene_Detail_trees':
            for c in a.get_components_by_class(u.InstancedStaticMeshComponent):
                for i in reversed(range(c.get_instance_count())):
                    p=c.get_instance_transform(i,True).translation
                    if abs(p.x)<1800 and p.y>200:c.remove_instance(i)
        if a.get_actor_label() not in ['MudScene_Detail_grass','MudScene_Detail_shrubs']:continue
        for c in a.get_components_by_class(u.InstancedStaticMeshComponent):
            for i in reversed(range(c.get_instance_count())):
                tr=c.get_instance_transform(i,True);p=tr.translation
                if abs(p.x)>1500 or not 500<p.y<1150:continue
                if 'shrubs' in a.get_actor_label() or (math.floor(p.x/10)*17+math.floor(p.y/10)*31)%5!=0:c.remove_instance(i);continue
                bounds=c.static_mesh.get_bounding_box();height=max(1,bounds.max.z-bounds.min.z)
                scale=tr.scale3d;scale.z=min(scale.z,9/height);tr.scale3d=scale
                c.update_instance_transform(i,tr,True,True,True)
    mat=materials.ground();materials.clod();materials.tyre()
    fill=next((a for a in actors.get_all_level_actors() if a.get_actor_label()=='MudResponse_ReviewFill'),None)
    if fill is None:
        fill=actors.spawn_actor_from_class(u.DirectionalLight,u.Vector(0,0,1000),u.Rotator(-65,90,0));fill.set_actor_label('MudResponse_ReviewFill')
    props(fill.light_component,intensity=1.5,cast_shadows=False,specular_scale=.25)
    # Three shallow sod patches alongside the scanned mud.
    regions=[]
    for name,x,wet in [('Firm_turf',-1000,.18),('Damp_grass',0,.55),('Wet_grass',1000,.88)]:
        regions.append(props(u.GTLandscapeMudRegion(),name=name,centre=u.Vector2D(x,825),half_size=u.Vector2D(500,325),wetness=wet,cohesion=.55,relief=.12,fragment_scale=.65,grass_cover=1.))
    regions+=[r for r in s.get_editor_property('mud_regions') if str(r.get_editor_property('name')) not in ['Firm_turf','Damp_grass','Wet_grass']];s.set_editor_property('mud_regions',regions)
    n=512;raw=bytearray()
    for j in range(n):
        raw.append(0);y=(j+.5)/n*3150-1575
        for i in range(n):
            x=(i+.5)/n*3150-1575;line=110*math.sin(x/410)+45*math.sin(x/180);d=abs(y-line)
            width=235+28*math.sin(x/197)+20*math.sin(x/71)
            mask=(1-smooth(width,width+100,d))*(1-smooth(1250,1450,abs(x)))
            basin=math.exp(-((x-570)/390)**2-((y-line)/190)**2)
            # Soil reservoir below the existing relief; this does not pre-excavate deeper ruts.
            # The old 8-14 cm layer bottomed out in the scanned bog's 12 cm hollows.
            depth=(24+8*basin)*mask;table=5-3*basin;soft=(.78+.18*basin)*mask
            if 500<y<1150 and abs(x)<1500:
                edge=smooth(500,550,y)*(1-smooth(1100,1150,y))*(1-smooth(1400,1500,abs(x)))
                depth=(2 if x<-500 else 5 if x<500 else 8)*edge
                soft=(.2 if x<-500 else .48 if x<500 else .75)*edge;table=50
            raw.extend((round(depth/50*255),round(table/50*255),0,round(soft*255)))
    def chunk(k,b):return struct.pack('>I',len(b))+k+b+struct.pack('>I',zlib.crc32(k+b)&0xffffffff)
    png=OUT/'response-paint.png';png.write_bytes(b'\x89PNG\r\n\x1a\n'+chunk(b'IHDR',struct.pack('>IIBBBBB',n,n,8,6,0,0,0))+chunk(b'IDAT',zlib.compress(raw))+chunk(b'IEND',b''))
    task=props(u.AssetImportTask(),filename=str(png),destination_path=BASE,destination_name='T_ResponsePaint',automated=True,replace_existing=True,save=True)
    u.AssetToolsHelpers.get_asset_tools().import_asset_tasks([task]);paint=u.load_asset(BASE+'/T_ResponsePaint')
    props(paint,srgb=False,compression_settings=u.TextureCompressionSettings.TC_VECTOR_DISPLACEMENTMAP,mip_gen_settings=u.TextureMipGenSettings.TMGS_NO_MIPMAPS)
    for e in u.MaterialEditingLibrary.get_material_expressions(mat):
        if isinstance(e,u.MaterialExpressionTextureObjectParameter) and str(e.get_editor_property('parameter_name'))=='GTLS_Paint':e.set_editor_property('texture',paint)
    assert u.GTLandscapeSurfaceSetupLibrary.import_paint(s,paint)
    land.set_editor_property('landscape_material',mat)
    u.MaterialEditingLibrary.recompile_material(mat);assets.save_loaded_asset(mat);assets.save_loaded_asset(paint)
    # Authoring copy retains dressing and Nanite geometry; only its material/paint changes.
    assert les.save_current_level()
    report.update(ok=True,material=mat.get_path_name())

try:setup()
except Exception:report['error']=traceback.format_exc();u.log_error(report['error'])
(OUT/'setup-report.json').write_text(json.dumps(report,indent=2))
u.EditorPythonScripting.set_keep_python_script_alive(True)
deadline=time.monotonic()+5
def done(dt):
    if time.monotonic()>deadline:u.unregister_slate_post_tick_callback(handle);u.SystemLibrary.quit_editor()
if report['ok'] and '-GTMudResponseReview' in u.SystemLibrary.get_command_line():
    import review_mud_response
else:
    handle=u.register_slate_post_tick_callback(done)
