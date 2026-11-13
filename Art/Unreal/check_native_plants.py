"""NP3 (docs/NATIVE_PLANT_KIT_PLAN.md): capture L_NativePlants at the owner angles and read the assets back.

capture_tussock_style.py's tick pattern under -RenderOffScreen: read back LODs and convex hulls of the 50 assets (20 bush/open + the 15 S1 floor
and river meshes + the 15 S2b verge meshes), load the level, play-simulate, wait for shader compiling to go quiet, then a 1600 x 900 high-res screenshot from each NZ_ camera
into Art/Export/NativePlants/v01/UE_<view>.png (twelve views; S1 adds FloorLogs, on foot 4 m from a log in the fern mass, and Riverbed, driver height
up the dry riverbed strip; S2b adds DenseFloor, on foot in the stand looking at the ground 3 m ahead, EdgeBand, driver height 10 m out from the paddock edge band,
and Shelterbelt, on foot 25 m along the west shelterbelt row). Run through Art/native_plants.ps1 -Mode Check.
NP4: each PNG's mean pixel value (R, G, B over every 4th pixel of every 4th row) goes into capture-report.json 'captures';
ok also needs FernMass and EdgeWall above 40/255; S1 puts Riverbed under the same gate; FloorLogs, a shaded
fern-mass interior like TowardSun, is captured and reported with its mean but does not gate (its mean sits just under 40 at NP4c's lighting).
S2b: EdgeBand and Shelterbelt gate at the same 40; DenseFloor is a shaded floor view like FloorLogs and only reports its mean.
"""
import unreal as u, json, time, traceback, subprocess, zlib, struct
from pathlib import Path
ROOT=Path(u.Paths.project_dir()).resolve(); OUT=ROOT/'Art/Export/NativePlants/v01'
SRC='/Game/GrandTour/Environment/NativePlants/v01'; LEVEL='/Game/GrandTour/ArtTests/NativePlants/L_NativePlants'
ORDER=['Beech_Mature','Beech_Pole','Beech_Edge','DeadSpar','CrownFern_A','CrownFern_B','CrownFern_C','TreeFern_A','TreeFern_B','TreeFern_Young',
       'Harakeke_A','Harakeke_B','Coprosma_A','Coprosma_B','Matagouri_A','Matagouri_B','TiKouka_A','TiKouka_B','Kanuka_A','Kanuka_B']
FLOOR=['Kiokio_A','Kiokio_B','Log_A','Log_B','Stump_A','MossHummock_A','MossHummock_B','Cobble_Cluster_S','Cobble_Cluster_M','Cobble_Cluster_L','CobbleBar',
       'Driftwood_A','LogJam','Boulder_A','Boulder_B']
VERGE=['Gorse_A','Gorse_B','Broom_A','Rush_A','Rush_B','Thistle_A','VergeTussock_A','VergeTussock_B','Radiata_Young','Radiata_Mature','Macrocarpa',
       'TwigLitter_A','TwigLitter_B','RootTangle_A','LeafLitter_A']
VIEWS=['Lineup','LineupFar','Driver','FernMass','TowardSun','EdgeWall','Top','FloorLogs','Riverbed','DenseFloor','EdgeBand','Shelterbelt']
USABLE_MEAN=40.   # NP4: a capture counts as usable above this mean pixel value (0-255); FernMass and EdgeWall must be usable
MUST_BE_USABLE=('FernMass','EdgeWall','Riverbed','EdgeBand','Shelterbelt')   # TowardSun, S1's FloorLogs and S2b's DenseFloor are shaded interior views: reported, not gating
u.EditorPythonScripting.set_keep_python_script_alive(True)
phase='load'; index=0; start=time.monotonic(); last=start; cpu=None; quiet=0
report={'ok':False,'level':LEVEL,'images':[],'assets':[]}

def png_mean(path, step=4):
    """Mean of R, G and B (0-255) over every step-th pixel of every step-th row of an 8-bit RGB or RGBA PNG.
    Pillow when the interpreter has it; otherwise a stdlib decoder (Unreal's Python ships no Pillow)."""
    try:
        from PIL import Image
        im = Image.open(path).convert('RGB'); w, h = im.size; px = im.load(); tot = 0; n = 0
        for y in range(0, h, step):
            for x in range(0, w, step):
                p = px[x, y]; tot += p[0] + p[1] + p[2]; n += 3
        return tot / n
    except ImportError:
        pass
    data = Path(path).read_bytes()
    assert data[:8] == b'\x89PNG\r\n\x1a\n', 'not a PNG: ' + str(path)
    pos = 8; idat = []; hdr = None
    while pos < len(data):
        ln, typ = struct.unpack('>I4s', data[pos:pos + 8]); body = data[pos + 8:pos + 8 + ln]; pos += 12 + ln
        if typ == b'IHDR': hdr = struct.unpack('>IIBBBBB', body)
        elif typ == b'IDAT': idat.append(body)
        elif typ == b'IEND': break
    w, h, depth, ctype, _, _, interlace = hdr
    assert depth == 8 and interlace == 0 and ctype in (2, 6), 'unsupported PNG %s' % (hdr,)
    bpp = 3 if ctype == 2 else 4; stride = w * bpp
    raw = zlib.decompress(b''.join(idat))
    prev = bytearray(stride); tot = 0; n = 0
    for y in range(h):
        off = y * (stride + 1); ft = raw[off]; row = bytearray(raw[off + 1:off + 1 + stride])
        if ft == 1:
            for i in range(bpp, stride): row[i] = (row[i] + row[i - bpp]) & 255
        elif ft == 2:
            row = bytearray([(a + b) & 255 for a, b in zip(row, prev)])
        elif ft == 3:
            for i in range(stride):
                left = row[i - bpp] if i >= bpp else 0
                row[i] = (row[i] + ((left + prev[i]) >> 1)) & 255
        elif ft == 4:
            for i in range(stride):
                a = row[i - bpp] if i >= bpp else 0; b = prev[i]; c = prev[i - bpp] if i >= bpp else 0
                p = a + b - c; pa = abs(p - a); pb = abs(p - b); pc = abs(p - c)
                row[i] = (row[i] + (a if pa <= pb and pa <= pc else b if pb <= pc else c)) & 255
        elif ft != 0:
            raise ValueError('bad PNG filter %d' % ft)
        prev = row
        if y % step == 0:
            for x in range(0, w, step):
                o = x * bpp; tot += row[o] + row[o + 1] + row[o + 2]; n += 3
    return tot / n

def capture_stats():
    out=[]
    for view,path in zip(VIEWS,report['images']):
        try:mean=round(png_mean(path),2)
        except Exception:report.setdefault('mean_errors',[]).append(view+': '+traceback.format_exc()); mean=None
        out.append(dict(view=view,path=path,mean=mean,usable=mean is not None and mean>USABLE_MEAN))
    return out

def shader_cpu():
    try:
        r=subprocess.run(['powershell','-NoProfile','-Command','(Get-Process ShaderCompileWorker -ErrorAction SilentlyContinue | Measure-Object CPU -Sum).Sum'],capture_output=True,text=True,timeout=20)
        return float(r.stdout.strip() or 0)
    except Exception:return -1.

def readback():
    manifest=json.loads((OUT/'manifest.json').read_text())
    hulls={r['asset']:r['hulls'] for r in manifest['models'] if r['lod']==0}
    sm=u.get_editor_subsystem(u.StaticMeshEditorSubsystem); good=True
    for short in ORDER+FLOOR+VERGE:
        mesh=u.EditorAssetLibrary.load_asset(SRC+'/SM_NZ_'+short)
        if not mesh:report['assets'].append(dict(name=short,missing=True)); good=False; continue
        n=len(mesh.get_editor_property('body_setup').get_editor_property('agg_geom').get_editor_property('convex_elems'))
        lods=sm.get_lod_count(mesh); want=hulls.get('SM_NZ_'+short)
        flag=str(mesh.get_editor_property('body_setup').get_editor_property('collision_trace_flag')).strip('<>').split(':')[0].split('.')[-1] if short in FLOOR or short in VERGE else None
        report['assets'].append(dict(name=short,lods=lods,hulls=n,manifest_hulls=want,screens=[round(x,4) for x in sm.get_lod_screen_sizes(mesh)],
                                     sections=[mesh.get_num_sections(l) for l in range(lods)],collision=flag,ok=lods==3 and n==want))
        good=good and lods==3 and n==want
    return good

def finish(error=None):
    global phase
    phase='finished'
    if error:report['error']=error; u.log_error(error)
    (OUT/'capture-report.json').write_text(json.dumps(report,indent=2))
    u.log('NATIVE_PLANTS_CHECK_RESULT ok=%s'%report['ok'])
    u.unregister_slate_post_tick_callback(handle)
    u.EditorLevelLibrary.editor_end_play(); u.SystemLibrary.quit_editor()

def tick(dt):
    global phase,last,index,shot_started,cpu,quiet
    if phase=='finished':return
    now=time.monotonic()
    try:
        if now-start>900:finish('Capture timed out in phase '+phase); return
        if phase=='load':
            report['assets_ok']=readback()
            phase='loaded'; last=now
            assert u.get_editor_subsystem(u.LevelEditorSubsystem).load_level(LEVEL),'Could not load '+LEVEL
        elif phase=='loaded' and now-last>8:
            phase='warm'; last=now; u.EditorLevelLibrary.editor_play_simulate()
        elif phase=='warm' and now-last>6:
            # wait until ShaderCompileWorker CPU stops rising twice in a row (20 s minimum, 240 s cap)
            c=shader_cpu(); quiet=quiet+1 if cpu is not None and c>=0 and c-cpu<.5 else 0; cpu=c; last=now
            if (quiet>=2 and now-start>20) or now-start>240:
                report['shader_wait_s']=round(now-start,1); phase='playing'; last=now-30
        elif phase=='playing' and now-last>20:
            world=u.EditorLevelLibrary.get_game_world()
            if not world:return
            if index==0:
                report['post_mode']=u.SystemLibrary.get_console_variable_int_value('gt.Look.Post')
                report['kuwahara']=u.SystemLibrary.get_console_variable_int_value('gt.Look.Kuwahara')
                report['actors']={a.get_actor_label():len(a.get_components_by_class(u.InstancedStaticMeshComponent)) for a in u.GameplayStatics.get_all_actors_of_class(world,u.Actor) if a.get_actor_label().startswith(('NZ_Bush','NZ_Edge','NZ_River','NZ_Shelter'))}
            view=VIEWS[index]
            camera=next((a for a in u.GameplayStatics.get_all_actors_of_class(world,u.CameraActor) if a.get_actor_label()=='NZ_'+view),None)
            assert camera,'Camera NZ_'+view+' missing'
            filename=OUT/('UE_'+view+'.png')
            phase='shot'; shot_started=time.time(); report['images'].append(str(filename))
            u.AutomationLibrary.take_high_res_screenshot(1600,900,str(filename),camera=camera,delay=2)
            last=time.monotonic()
        elif phase=='shot' and now-last>8:
            output=Path(report['images'][-1])
            if not output.exists() or output.stat().st_mtime<shot_started:return
            index+=1
            if index==len(VIEWS):
                report['captures']=capture_stats()
                usable={c['view']:c['usable'] for c in report['captures']}
                report['ok']=bool(report['assets_ok']) and all(Path(p).exists() for p in report['images']) and len(report['images'])==len(VIEWS) and all(usable.get(v) for v in MUST_BE_USABLE)
                finish(None if report['ok'] else 'Asset readback or capture brightness failed (need FernMass, EdgeWall, Riverbed, EdgeBand and Shelterbelt mean > %g); see assets and captures'%USABLE_MEAN); return
            phase='playing'; last=now-12
    except Exception:finish(traceback.format_exc())
handle=u.register_slate_post_tick_callback(tick)
