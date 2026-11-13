"""Read the saved driving Landscape and inventory placed assets; never save/edit the source map."""
import unreal as u
import array,json,time,traceback,hashlib
from pathlib import Path
ROOT=Path(u.Paths.project_dir()).resolve();OUT=ROOT/'Art/Export/BenmoreGaea/source';OUT.mkdir(parents=True,exist_ok=True)
LEVEL='/Game/GrandTour/Demo/BenmoreRoads/L_Benmore_Drive';N=2017
phase='load';started=time.monotonic();last=started;report={'ok':False,'source_level':LEVEL,'resolution':N}
u.EditorPythonScripting.set_keep_python_script_alive(True)
def finish(error=None):
    global phase
    phase='done';report['ok']=error is None
    if error:report['error']=error;u.log_error(error)
    (OUT/'unreal-export-report.json').write_text(json.dumps(report,indent=2))
    u.unregister_slate_post_tick_callback(handle);u.SystemLibrary.quit_editor()
def tick(dt):
    global phase,last,world,land,rt,map_hash
    try:
        if time.monotonic()-started>300:raise RuntimeError('Read-only Gaea export timed out')
        if phase=='load':
            phase='loading'
            map_hash=hashlib.sha256((ROOT/'Content/GrandTour/Demo/BenmoreRoads/L_Benmore_Drive.umap').read_bytes()).hexdigest()
            assert u.get_editor_subsystem(u.LevelEditorSubsystem).load_level(LEVEL)
            world=u.get_editor_subsystem(u.UnrealEditorSubsystem).get_editor_world()
            actors=u.get_editor_subsystem(u.EditorActorSubsystem).get_all_level_actors()
            lands=[a for a in actors if isinstance(a,u.Landscape)];assert len(lands)==1
            land=lands[0];report['location_cm']=list(land.get_actor_location().to_tuple());report['scale']=list(land.get_actor_scale3d().to_tuple())
            assert max(abs(a-b) for a,b in zip(report['location_cm'],[-125000,-125000,0]))<.1
            assert max(abs(a-b) for a,b in zip(report['scale'],[250000/2016,250000/2016,200]))<.001
            phase='warm';last=time.monotonic()
        elif phase=='warm' and time.monotonic()-last>10:
            phase='exporting';rt=u.RenderingLibrary.create_render_target2d(world,N,N,u.TextureRenderTargetFormat.RTF_RGBA8)
            assert land.landscape_export_heightmap_to_render_target(rt,True,True)
            phase='read';last=time.monotonic()
        elif phase=='read' and time.monotonic()-last>10:
            phase='reading';assert land.landscape_export_heightmap_to_render_target(rt,True,True)
            colors=u.RenderingLibrary.read_render_target(world,rt,False);assert len(colors)==N*N
            values=array.array('H',((int(c.r)<<8)|int(c.g) for c in colors));del colors
            assert 0<min(values)<max(values)<65535
            (OUT/'H_Current_Unreal_2017.r16').write_bytes(values.tobytes())
            anchors=[]
            for j in [0,17,289,731,1008,1501,1999,2016]:
                for i in [0,31,417,809,1008,1613,1981,2016]:
                    anchors.append({'pixel':[i,j],'local_m':(values[j*N+i]-32768)/64})
            reference=array.array('f');reference.frombytes((ROOT/'Art/Export/BenmoreRoads/height_local_south_up.f32').read_bytes())
            report['canonical_max_difference_m']=max(abs((v-32768)/64-reference[i]) for i,v in enumerate(values))
            rows=[];instances=0
            for a in u.get_editor_subsystem(u.EditorActorSubsystem).get_all_level_actors():
                row={'label':a.get_actor_label(),'class':a.get_class().get_name(),'location_cm':list(a.get_actor_location().to_tuple()),'rotation':list(a.get_actor_rotation().to_tuple()),'scale':list(a.get_actor_scale3d().to_tuple()),'components':[]}
                for c in a.get_components_by_class(u.StaticMeshComponent):
                    mesh=c.get_editor_property('static_mesh')
                    if not mesh:continue
                    item={'name':c.get_name(),'mesh':mesh.get_path_name(),'materials':[c.get_material(i).get_path_name() if c.get_material(i) else None for i in range(c.get_num_materials())]}
                    if isinstance(c,u.InstancedStaticMeshComponent):
                        tr=[]
                        for i in range(c.get_instance_count()):
                            t=c.get_instance_transform(i,True);tr.append([*t.translation.to_tuple(),*t.rotation.to_tuple(),*t.scale3d.to_tuple()])
                        item['instances_world_xyz_quat_xyzw_scale']=tr;instances+=len(tr)
                    row['components'].append(item)
                rows.append(row)
            (OUT/'placement-snapshot.json').write_text(json.dumps({'source_level':LEVEL,'actors':rows,'instance_count':instances},separators=(',',':')))
            after=hashlib.sha256((ROOT/'Content/GrandTour/Demo/BenmoreRoads/L_Benmore_Drive.umap').read_bytes()).hexdigest();assert map_hash==after
            report.update(source_map_sha256=after,source_map_unchanged=True,anchors=anchors,actor_count=len(rows),instance_count=instances,encoded_range=[min(values),max(values)],height_sha256=hashlib.sha256(values.tobytes()).hexdigest(),separate_river_bank_meshes_excluded=True)
            finish()
    except Exception:finish(traceback.format_exc())
handle=u.register_slate_post_tick_callback(tick)
