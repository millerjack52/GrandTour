"""Read-only saved-map comparison. Never saves maps or assets."""
import unreal as u,json,hashlib,traceback,time
from pathlib import Path
R=Path('C:/GrandTour');O=R/'Saved/LidarAuthoringQA/AssetIntake';report={'ok':False,'maps':{}}
names=['FloraDrive','LidarStudy'];paths=[R/'Content/GrandTour/ArtTests'/n/('L_'+n+'.umap') for n in names]
hashes={str(p):hashlib.sha256(p.read_bytes()).hexdigest() for p in paths}
def read(obj,keys):
    out={}
    for key in keys.split():
        try:
            v=obj.get_editor_property(key)
            out[key]=v if isinstance(v,(bool,int,float,str)) or v is None else v.get_path_name() if isinstance(v,u.Object) else str(v)
        except Exception:pass
    return out
try:
    for name in names:
        assert u.get_editor_subsystem(u.LevelEditorSubsystem).load_level('/Game/GrandTour/ArtTests/'+name+'/L_'+name)
        actors=u.get_editor_subsystem(u.EditorActorSubsystem).get_all_level_actors();rows=[]
        for a in actors:
            row=None
            if isinstance(a,u.GTLandscapeSurface):
                row=read(a,'enable_wheel_support observe_player_wheels follow_player use_soil_shear_response use_rut_interaction use_native_mud_shader_updates grass_is_visual_cover separate_visual_mesh paint_size_cm paint_resolution material_resolution clay_resolution world_rest_resolution mud_relief_resolution mud_relief_tile_cm extend_water_response_to_domain paint_texture tyre_coating_material simulated_water mud_regions')
            elif isinstance(a,u.GTMudRunnerVisual):
                row=read(a,'material track_material grid_cell_cm grid_resolution follow_player_grid hide_whole_landscape water_simulation_material sediment_simulation_material')
                row['material_details']={}
                for field in ['material','track_material']:
                    m=a.get_editor_property(field)
                    if m:
                        row['material_details'][field]=read(m,'shading_model blend_mode')
                        row['material_details'][field]['textures']=[str(e.get_editor_property('texture').get_path_name()) for e in u.MaterialEditingLibrary.get_material_expressions(m) if isinstance(e,(u.MaterialExpressionTextureSample,u.MaterialExpressionTextureObject)) and e.get_editor_property('texture')]
            elif isinstance(a,u.GTProceduralRoad):
                row=read(a,'firm_gravel width_cm mud_depth_cm wetness relief_strength bed_depth_cm conditions')
            if row is not None:rows.append(dict(actor=a.get_actor_label(),type=a.get_class().get_name(),properties=row))
        report['maps'][name]=rows
    assert all(hashlib.sha256(Path(p).read_bytes()).hexdigest()==h for p,h in hashes.items())
    report.update(ok=True,maps_unchanged=True)
except Exception:report['error']=traceback.format_exc()
(O/'flora-lidar-mud-comparison.json').write_text(json.dumps(report,indent=2))
u.get_editor_subsystem(u.LevelEditorSubsystem).load_level('/Engine/Maps/Entry')
for key in list(globals()):
    if not key.startswith('__') and key not in ['u','time']:globals()[key]=None
u.SystemLibrary.collect_garbage();end=time.monotonic()+3
def quit(dt):
    if time.monotonic()>end:u.unregister_slate_post_tick_callback(handle);u.SystemLibrary.quit_editor()
u.EditorPythonScripting.set_keep_python_script_alive(True);handle=u.register_slate_post_tick_callback(quit)
