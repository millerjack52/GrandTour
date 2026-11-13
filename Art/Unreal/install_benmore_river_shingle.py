"""Install approved Mackenzie shingle on the existing Benmore riverbed."""
import array
import hashlib
import json
import shutil
import sys
import time
import traceback
from pathlib import Path
import unreal as u

ROOT=Path(u.Paths.project_dir()).resolve();sys.path.insert(0,str(ROOT/'Art/Unreal'))
import benmore_river_shingle as mud
LEVEL='/Game/GrandTour/Demo/BenmoreRoads/Gaea/L_Benmore_GaeaReview'
MAT='/Game/GrandTour/Demo/BenmoreRoads/Gaea/ShoreRefinement/M_GC_Terrain'
OUT=ROOT/'Art/Export/BenmoreRiverShingle';OUT.mkdir(parents=True,exist_ok=True)
les=u.get_editor_subsystem(u.LevelEditorSubsystem);actors=u.get_editor_subsystem(u.EditorActorSubsystem)
assets=u.EditorAssetLibrary
report={'ok':False,'images':[],'performance_measured':False,'map':LEVEL}
previous_report=json.loads((OUT/'install-report.json').read_text()) if (OUT/'install-report.json').exists() else {}
busy=False;next_at=0;started=time.monotonic()
grid=array.array('f');grid.frombytes((ROOT/'Art/Export/BenmoreGaea/Morphology/height_local_south_up.f32').read_bytes())

def height(x,y):
    fx=max(0,min(2015.99999,(x+1250)*2016/2500));fy=max(0,min(2015.99999,(y+1250)*2016/2500))
    i=int(fx);j=int(fy);s=fx-i;t=fy-j;k=j*2017+i;q,r,v,w=grid[k],grid[k+1],grid[k+2017],grid[k+2018]
    return q+(r-q)*s+(w-r)*t if s>=t else q+(w-v)*s+(v-q)*t

VIEWS=[('WetBank',(-681.8,225.8,1.6),(-682.04,229.41,.15)),
       ('SiltBank',(-613.84,223.0,1.6),(-613.84,227.0,.12)),
       ('DryVerge',(-746,-450,1.6),(-750,-447,.1)),
       ('Ford',(-671,208,2.5),(-680,220,.5))]

def file_for(asset,extension='.uasset'):
    return (ROOT/'Content'/asset.removeprefix('/Game/')).with_suffix(extension)

def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()

def refs():return {a.get_actor_label():a for a in actors.get_all_level_actors()}

def signature():
    result=[]
    for a in actors.get_all_level_actors():
        if isinstance(a,u.CameraActor):continue
        v=a.get_actor_location();s=a.get_actor_scale3d()
        d={'label':a.get_actor_label(),'class':a.get_class().get_name(),'location':[v.x,v.y,v.z],'scale':[s.x,s.y,s.z]}
        if isinstance(a,u.LandscapeProxy):d['material']=a.get_editor_property('landscape_material').get_path_name()
        result.append(d)
    return sorted(result,key=lambda d:d['label'])

def capture(suffix):
    bylabel=refs();sheet=bylabel['Benmore_RS_WaterDomain'];camera=bylabel['Benmore_RL_Camera_Ford']
    camera.camera_component.set_editor_property('constrain_aspect_ratio',False)
    camera.camera_component.set_field_of_view(72.)
    for name,pos,target in VIEWS:
        p=u.Vector(pos[0]*100,pos[1]*100,(height(*pos[:2])+pos[2])*100)
        t=u.Vector(target[0]*100,target[1]*100,(height(*target[:2])+target[2])*100)
        sheet.preview_water_at(u.Vector2D(target[0]*100,target[1]*100),0,True)
        for a in sheet.get_editor_property('domain_surfaces'):
            m=a.static_mesh_component.get_material(0)
            if isinstance(m,u.MaterialInstanceDynamic):m.set_scalar_parameter_value('WaterTimeOverride',12)
        camera.set_actor_location(p,False,False);camera.set_actor_rotation(u.MathLibrary.find_look_at_rotation(p,t),False)
        u.get_editor_subsystem(u.UnrealEditorSubsystem).set_level_viewport_camera_info(p,camera.get_actor_rotation())
        yield 30 if name==VIEWS[0][0] else 12
        path=OUT/(name+'_'+suffix+'.png');requested=time.time()
        u.AutomationLibrary.take_high_res_screenshot(1440,900,str(path),camera);yield 3
        while not path.exists() or path.stat().st_mtime<requested:
            if time.time()-requested>60:raise RuntimeError('Screenshot timeout: '+str(path))
            yield 1
        report['images'].append(str(path))

def run():
    assert les.load_level(LEVEL)
    mapfile=file_for(LEVEL,'.umap');matfile=file_for(MAT)
    loaded_map_time=mapfile.stat().st_mtime_ns;loaded_mat_time=matfile.stat().st_mtime_ns
    report['map_sha256_before']=sha(mapfile);report['placement_before']=signature()
    backup=ROOT/'Saved/BenmoreRiverShingle'/str(time.time_ns());backup.mkdir(parents=True)
    shutil.copy2(matfile,backup/matfile.name);shutil.copy2(mapfile,backup/mapfile.name)
    report['backup']=str(backup)
    report['original_backup']=previous_report.get('original_backup',previous_report.get('backup',str(backup)))
    material=assets.load_asset(MAT);assert material
    # Keep physical-material and landscape-grass nodes and their wiring intact.
    def custom_outputs(m):
        return [{'name':n.get_name(),'class':n.get_class().get_name(),
                 'inputs':[v.get_name() if v else None for v in u.MaterialEditingLibrary.get_inputs_for_material_expression(m,n)]}
                for n in u.MaterialEditingLibrary.get_material_expressions(m)
                if isinstance(n,(u.MaterialExpressionLandscapeGrassOutput,u.MaterialExpressionLandscapePhysicalMaterialOutput))]
    before_outputs=custom_outputs(material)
    already=any(str(n.get_editor_property('desc'))==mud.TAG for n in u.MaterialEditingLibrary.get_material_expressions(material))
    if not already:yield from capture('Before')
    else:
        report['baseline_retained']=True
        report['images'].extend(str(OUT/(name+'_Before.png')) for name,_,_ in VIEWS if (OUT/(name+'_Before.png')).exists())
    assert mapfile.stat().st_mtime_ns==loaded_map_time,'Benmore was saved externally; aborting'
    assert matfile.stat().st_mtime_ns==loaded_mat_time,'Terrain material was saved externally; aborting'
    report['material']=mud.attach(material)
    assert custom_outputs(material)==before_outputs,'Physical material or grass output changed'
    assert mapfile.stat().st_mtime_ns==loaded_map_time and matfile.stat().st_mtime_ns==loaded_mat_time
    assert assets.save_loaded_asset(material)
    mouth=refs().get('Benmore_RL_MouthBed')
    if mouth:
        mm=mouth.static_mesh_component.get_material(0)
        assert isinstance(mm,u.Material)
        mf=file_for(mm.get_path_name().split('.')[0]);mtime=mf.stat().st_mtime_ns
        shutil.copy2(mf,backup/mf.name)
        report['mouth_material']=mud.attach(mm)
        assert mf.stat().st_mtime_ns==mtime,'Mouth material was saved externally'
        assert assets.save_loaded_asset(mm)
    yield 25
    # Clear preview-only water MIDs/camera edits without saving them into the map.
    assert les.load_level('/Engine/Maps/Entry');assert les.load_level(LEVEL)
    assert signature()==report['placement_before']
    material=assets.load_asset(MAT)
    assert any(str(n.get_editor_property('desc'))==mud.TAG for n in u.MaterialEditingLibrary.get_material_expressions(material))
    yield from capture('After')
    assert les.load_level('/Engine/Maps/Entry');assert les.load_level(LEVEL)
    report['map_sha256_after']=sha(mapfile)
    assert report['map_sha256_before']==report['map_sha256_after']
    assert signature()==report['placement_before']
    report['map_saved']=False;report['material_saved']=True;report['physical_and_grass_outputs_unchanged']=True
    report['ok']=True

def finish(error=None):
    if error:report['error']=error;u.log_error(error)
    (OUT/'install-report.json').write_text(json.dumps(report,indent=2))
    if report['ok']:
        rows=''.join('<section><h2>'+name+'</h2><div>'+''.join('<figure><a href="'+name+'_'+suffix+'.png"><img src="'+name+'_'+suffix+'.png"></a><figcaption>'+suffix+'</figcaption></figure>' for suffix in ['Before','After'])+'</div></section>' for name,_,_ in VIEWS)
        (OUT/'benmore-river.html').write_text('<!doctype html><meta charset="utf-8"><title>Benmore river shingle</title><style>body{background:#191c19;color:#e3e0d5;font:17px/1.5 system-ui;margin:30px auto;max-width:1550px;padding:0 24px}div{display:grid;grid-template-columns:1fr 1fr;gap:18px}figure{margin:0}img{width:100%}h2{font-size:21px}@media(max-width:750px){div{grid-template-columns:1fr}}</style><h1>Benmore — approved river shingle</h1><p>Approved Mackenzie shingle blended through the existing riverbed masks, with dry-to-wet shading and varied distant texture sampling. Existing mud margins, river geometry, physical surfaces and water are retained.</p>'+rows,encoding='utf-8')
    u.unregister_slate_post_tick_callback(handle);u.SystemLibrary.quit_editor()

def tick(dt):
    global busy,next_at
    if busy:return
    try:
        if time.monotonic()-started>1000:raise RuntimeError('Benmore material capture timed out')
        if time.monotonic()<next_at:return
        busy=True;delay=next(gen);next_at=time.monotonic()+delay
    except StopIteration:finish()
    except Exception:finish(traceback.format_exc())
    finally:busy=False

u.EditorPythonScripting.set_keep_python_script_alive(True)
gen=run();handle=u.register_slate_post_tick_callback(tick)

