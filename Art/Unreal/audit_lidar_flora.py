"""Read the real LiDAR map and choose a bounded, editable Flora integration area."""
import unreal as u,json,traceback,sys,hashlib,shutil
from pathlib import Path
R=Path('C:/GrandTour');O=R/'Art/Export/LidarStudy/FloraIntegration';O.mkdir(parents=True,exist_ok=True)
sys.path.insert(0,str(R/'Art/Unreal'))
import lidar_logging_trial as T
from lidar_grounding import GroundSampler
r=dict(ok=False,components=[],actors=[],assets={})
try:
    path=R/'Content/GrandTour/ArtTests/LidarStudy/L_LidarStudy.umap'
    backup=O/'Before';backup.mkdir(exist_ok=True)
    if not (backup/path.name).exists():shutil.copy2(path,backup/path.name)
    r['map_sha256']=hashlib.sha256(path.read_bytes()).hexdigest()
    assert u.get_editor_subsystem(u.LevelEditorSubsystem).load_level('/Game/GrandTour/ArtTests/LidarStudy/L_LidarStudy')
    actors=u.get_editor_subsystem(u.EditorActorSubsystem).get_all_level_actors()
    author=next(a for a in actors if isinstance(a,u.GTProceduralGround));g=GroundSampler(author)
    route=T.route(json.loads((R/'Art/Export/LidarStudy/Place/roads.json').read_text()))
    pts=[T.at(route,s) for s in range(150,281,5)]
    cx=sum(p[0] for p in pts)/len(pts);cy=sum(p[1] for p in pts)/len(pts)
    r['section']={'centre':[cx,cy,g.height(cx,cy)],'samples':[]}
    for s in range(160,271,10):
        for off in [-15,-8,0,8,15]:
            x,y,yaw=T.at(route,s,off);r['section']['samples'].append(dict(station=s,across=off,x=x,y=y,z=g.height(x,y),yaw=yaw))
    r['ground_digest']=str(author.output_digest)
    for a in actors:
        if isinstance(a,(u.GTLandscapeSurface,u.GTMudRunnerVisual,u.GTMixedGroundDetails,u.GTWaterSheet,u.DirectionalLight,u.SkyLight,u.ExponentialHeightFog,u.PostProcessVolume)):
            row=dict(label=a.get_actor_label(),type=a.get_class().get_name(),position=a.get_actor_location().to_tuple())
            if isinstance(a,u.GTMudRunnerVisual):row.update(material=a.material.get_path_name(),tread=a.track_material.get_path_name(),follow=a.follow_player_grid,half=a.half_size_cm)
            if isinstance(a,u.GTLandscapeSurface):row['soil']={k:a.get_editor_property(k) for k in ['layer_depth_scale','maximum_layer_depth_cm','bearing_strength','settlement_speed_scale','grass_is_visual_cover','use_native_mud_shader_updates']}
            if isinstance(a,u.DirectionalLight):row['intensity']=a.light_component.intensity
            r['actors'].append(row)
        for c in a.get_components_by_class(u.InstancedStaticMeshComponent):
            if not c.static_mesh:continue
            overlap=list(c.get_instances_overlapping_sphere(u.Vector(cx,cy,g.height(cx,cy)+1200),10000,True))
            row=dict(actor=a.get_actor_label(),component=c.get_name(),mesh=c.static_mesh.get_path_name(),count=c.get_instance_count(),near_count=len(overlap),materials=[m.get_path_name() if m else None for m in c.get_materials()])
            if overlap:r['components'].append(row)
    sm=u.get_editor_subsystem(u.StaticMeshEditorSubsystem)
    for row in json.loads((R/'Art/Export/LidarStudy/FloraPath/scene-manifest.json').read_text())['meshes']:
        mesh=u.load_asset('/Game/GrandTour/ArtTests/FloraPath/'+row['name'])
        if mesh:r['assets'][row['name']]=dict(lods=[mesh.get_num_triangles(i) for i in range(sm.get_lod_count(mesh))],bounds=str(mesh.get_bounds()),materials=[e.material_interface.get_path_name() for e in mesh.static_materials if e.material_interface])
    assert hashlib.sha256(path.read_bytes()).hexdigest()==r['map_sha256']
    r['ok']=True
except Exception:r['error']=traceback.format_exc();u.log_error(r['error'])
(O/'audit-report.json').write_text(json.dumps(r,indent=2))
u.get_editor_subsystem(u.LevelEditorSubsystem).load_level('/Engine/Maps/Entry');u.SystemLibrary.quit_editor()
