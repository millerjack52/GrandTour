"""Rebuild established gravel roads in the saved map; preserve mud and river banks."""
import bisect
import gc
import json
import math
import os
import shutil
import sys
import time
import traceback
from pathlib import Path
import unreal as u

ROOT = Path(u.Paths.project_dir()).resolve()
sys.path.insert(0, str(ROOT/'Art/Unreal'))
import lidar_firm_roads as policy
from lidar_grounding import GroundSampler

QA = ROOT/'Saved/LidarAuthoringQA/FR1'
QA.mkdir(parents=True, exist_ok=True)
LEVEL = '/Game/GrandTour/ArtTests/LidarStudy/L_LidarStudy'
report = dict(ok=False, version=policy.VERSION, roads={}, owner_drive_pending=True)
busy = False
PRESENTATION_ONLY=os.environ.get('GT_FIRM_ROADS_PRESENTATION_ONLY')=='1'


def save():
    (QA/('water.json' if PRESENTATION_ONLY else 'apply.json')).write_text(json.dumps(report, indent=2))


def survey(author, roads, surface):
    g = GroundSampler(author)
    result = {}
    for name, road in roads.items():
        spline = road.control_points
        pts = [spline.get_location_at_spline_point(i,u.SplineCoordinateSpace.WORLD)
               for i in range(spline.get_number_of_spline_points())]
        cum = [0.]
        for a,b in zip(pts,pts[1:]):cum.append(cum[-1]+math.hypot(b.x-a.x,b.y-a.y))
        samples = []
        for s in range(500, int(cum[-1]-500), 200):
            i = min(len(pts)-1,bisect.bisect_right(cum,s))
            a,b = pts[i-1],pts[i]
            f = (s-cum[i-1])/(cum[i]-cum[i-1])
            x,y = a.x+(b.x-a.x)*f,a.y+(b.y-a.y)*f
            d = math.hypot(b.x-a.x,b.y-a.y)
            depths = []
            for side in (-.30,0,.30):
                xx,yy=x-(b.y-a.y)/d*road.width_cm*side,y+(b.x-a.x)/d*road.width_cm*side
                depths.append(surface.sample_surface(u.Vector2D(xx,yy)).sinkage_cap_cm)
            samples.append(dict(s_m=s*.01,x=x,y=y,z=g.height(x,y),depths_cm=depths))
        rough = [abs(b['z']-(a['z']+c['z'])*.5) for a,b,c in zip(samples,samples[1:],samples[2:])]
        result[name] = dict(samples=samples,roughness_rms_cm=math.sqrt(sum(v*v for v in rough)/max(1,len(rough))),
                            roughness_p95_cm=sorted(rough)[int(len(rough)*.95)],
                            max_depth_cm=max(max(r['depths_cm']) for r in samples))
    return result


def protected(author, refs):
    import lidar_homestead as homestead
    g = GroundSampler(author)
    points = []
    # House/garage foundations, bank and mainland attachment. Full logging tile
    # signatures are checked separately outside its road junction.
    for x0,y0,r in [(*homestead.xy(0,0),700),(*homestead.xy(*homestead.GARAGE),350),(-47900,-34200,500),(-49200,-36100,500)]:
        points += [(x0+x,y0+y) for x in range(-r,r+1,100) for y in range(-r,r+1,100)]
    # Include the complete baked homestead apron survey, not just foundations.
    points += [homestead.xy(x,y) for x in range(-2400,2401,100) for y in range(-4400,1601,100)]
    logging = [a for a in refs if isinstance(a,u.GTProceduralRoad) and a.actor_has_tag('LidarMudTrack')]
    for a in logging:
        for i in range(10,a.control_points.get_number_of_spline_points()-1):
            p=a.control_points.get_location_at_spline_point(i,u.SplineCoordinateSpace.WORLD)
            points += [(p.x+dx,p.y+dy) for dx,dy in [(0,0),(-100,0),(100,0),(0,-100),(0,100)]]
    heights = [g.height(x,y) for x,y in points]
    soft_points=[(-47900.,-34200.)]
    for a in logging:
        for i in range(10,a.control_points.get_number_of_spline_points()-1):
            p=a.control_points.get_location_at_spline_point(i,u.SplineCoordinateSpace.WORLD)
            soft_points.append((p.x,p.y))
    caps=[author.surface.sample_surface(u.Vector2D(x,y)).sinkage_cap_cm for x,y in soft_points]
    condition_keys=['name','start_metres','end_metres','blend_metres','mud_depth_cm','rut_depth_cm','wetness','firmness','grass_cover','water_fill_cm','basin_depth_cm','track_spread_cm','churn','crossing_tracks','breakup_cm']
    designs=[]
    for a in logging:
        xyz=[a.control_points.get_location_at_spline_point(i,u.SplineCoordinateSpace.WORLD) for i in range(a.control_points.get_number_of_spline_points())]
        designs.append(dict(name=a.get_actor_label(),conditions=[{k:c.get_editor_property(k) for k in condition_keys} for c in a.conditions],points=[[p.x,p.y,p.z] for p in xyz]))
    return dict(points=points,heights=heights,soft_caps=caps,logging=designs)


def run():
    les = u.get_editor_subsystem(u.LevelEditorSubsystem)
    assert les.load_level(LEVEL)
    les.editor_set_viewport_realtime(False)
    refs = u.get_editor_subsystem(u.EditorActorSubsystem).get_all_level_actors()
    author = next(a for a in refs if isinstance(a,u.GTProceduralGround))
    surface = author.surface
    if PRESENTATION_ONLY:
        backup=QA/('water-backup-'+time.strftime('%Y%m%d-%H%M%S'))
        backup.mkdir()
        shutil.copy2(ROOT/'Content/GrandTour/ArtTests/LidarStudy/L_LidarStudy.umap',backup/'L_LidarStudy.umap')
        report['backup']=str(backup)
        digest=author.output_digest
        report['water']=policy.preserve_live_water(author,refs)
        assert author.output_digest==digest
        assert les.save_current_level()
        refs=author=surface=None
        gc.collect()
        les.load_level('/Engine/Maps/Entry')
        yield 3
        assert les.load_level(LEVEL)
        refs=u.get_editor_subsystem(u.EditorActorSubsystem).get_all_level_actors()
        author=next(a for a in refs if isinstance(a,u.GTProceduralGround))
        assert author.road_water_mesh.get_editor_property('hidden')
        assert author.output_digest==digest
        report.update(ok=True,saved_and_reloaded=True,ground_digest=digest)
        save()
        refs=author=None
        gc.collect()
        les.load_level('/Engine/Maps/Entry')
        yield 3
        return
    roads = {}
    for name in policy.NAMES:
        matches=[a for a in refs if isinstance(a,u.GTProceduralRoad) and a.get_actor_label()=='LidarStudy_'+name]
        assert len(matches)==1,(name,[a.get_actor_label() for a in refs if isinstance(a,u.GTProceduralRoad)])
        roads[name]=matches[0]
        assert not matches[0].actor_has_tag('LidarMudTrack')
    backup=QA/('backup-'+time.strftime('%Y%m%d-%H%M%S'))
    backup.mkdir()
    packages=[LEVEL]+[t.get_path_name().split('.')[0] for t in (author.paint_texture,author.style_texture,author.macro_texture)]
    for package in packages:
        path=ROOT/'Content'/package.removeprefix('/Game/')
        path=path.with_suffix('.umap' if package==LEVEL else '.uasset')
        shutil.copy2(path,backup/path.name)
    report['backup']=str(backup)
    report['before_digest']=author.output_digest
    report['previously_firm']={name:road.get_editor_property('firm_gravel') for name,road in roads.items()}
    report['before']=survey(author,roads,surface)
    before_protected=protected(author,refs)
    report['before_triangles']=author.relief_triangles
    save()
    for road in roads.values():policy.configure(road)
    assert author.rebuild(),author.last_message
    yield 3
    report['after']=survey(author,roads,surface)
    after_protected=protected(author,refs)
    report['protected_max_height_change_cm']=max(abs(a-b) for a,b in zip(before_protected['heights'],after_protected['heights']))
    report['protected_changes']=[dict(x=p[0],y=p[1],before=a,after=b) for p,a,b in zip(before_protected['points'],before_protected['heights'],after_protected['heights']) if abs(a-b)>.01]
    assert report['protected_max_height_change_cm']<.01, 'Protected foundations or gravel bank moved'
    assert before_protected['logging']==after_protected['logging'],'Logging design changed'
    report['protected_max_depth_change_cm']=max(abs(a-b) for a,b in zip(before_protected['soft_caps'],after_protected['soft_caps']))
    assert report['protected_max_depth_change_cm']<.001,'Logging mud or gravel bank yielding depth changed'
    report['after_digest']=author.output_digest
    report['triangles']=author.relief_triangles
    report['changed_tiles']=author.changed_relief_tiles
    report['retained_tiles']=author.retained_relief_tiles
    assert report['triangles']==report['before_triangles'],'Unexpected geometry budget increase'
    for name in policy.NAMES:
        a,b=report['before'][name],report['after'][name]
        report['roads'][name]=dict(before_roughness_cm=a['roughness_rms_cm'],after_roughness_cm=b['roughness_rms_cm'],max_depth_cm=b['max_depth_cm'])
        # Polyline centres differ slightly from the generated natural cubic in
        # sharp bends. Keep every exceptional sample visible for inspection.
        bad=[r for r in b['samples'] if max(r['depths_cm'])>.001]
        report['roads'][name]['nonzero_depth_samples']=bad
        assert not bad,(name,'yielding road samples',bad[:3])
        assert b['roughness_rms_cm']<=a['roughness_rms_cm']+.001 if report['previously_firm'][name] else b['roughness_rms_cm']<a['roughness_rms_cm'],(name,'profile did not become smoother')
    save()
    stable_digest=author.output_digest
    assert author.rebuild(),author.last_message
    report['repeat_digest_stable']=author.output_digest==stable_digest
    report['repeat_changed_tiles']=author.changed_relief_tiles
    assert report['repeat_digest_stable'] and author.changed_relief_tiles==0,'Road rebuild is not repeatable'
    report['water']=policy.preserve_live_water(author,u.get_editor_subsystem(u.EditorActorSubsystem).get_all_level_actors())
    for texture in (author.paint_texture,author.style_texture,author.macro_texture):
        assert u.EditorAssetLibrary.save_loaded_asset(texture)
    assert les.save_current_level()
    refs=roads=surface=author=None
    gc.collect()
    assert les.load_level('/Engine/Maps/Entry')
    yield 3
    assert les.load_level(LEVEL)
    refs=u.get_editor_subsystem(u.EditorActorSubsystem).get_all_level_actors()
    author=next(a for a in refs if isinstance(a,u.GTProceduralGround))
    assert author.output_digest==report['after_digest']
    for name in policy.NAMES:
        road=next(a for a in refs if isinstance(a,u.GTProceduralRoad) and a.get_actor_label()=='LidarStudy_'+name)
        assert road.get_editor_property('firm_gravel') and road.mud_depth_cm==0
    report.update(ok=True,saved_and_reloaded=True)
    policy.record_install_metadata(ROOT,report)
    save()
    refs=author=road=None
    gc.collect()
    les.load_level('/Engine/Maps/Entry')
    yield 3


steps=run()
began=time.monotonic()
deadline=0
def tick(dt):
    global busy,deadline,steps
    if busy or time.monotonic()<deadline:return
    busy=True
    done=False
    try:
        assert time.monotonic()-began<1200,'Firm road rebuild timeout'
        deadline=time.monotonic()+next(steps)
    except StopIteration:done=True
    except Exception:
        report['ok']=False;report['error']=traceback.format_exc();save();u.log_error(report['error']);done=True
    finally:busy=False
    if done:
        u.unregister_slate_post_tick_callback(handle)
        steps=None
        gc.collect()
        u.SystemLibrary.quit_editor()

u.EditorPythonScripting.set_keep_python_script_alive(True)
handle=u.register_slate_post_tick_callback(tick)
