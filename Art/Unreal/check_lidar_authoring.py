"""Editor smoke check on Entry only. Does not load or save L_LidarStudy."""
import unreal as u
from pathlib import Path
import json
import sys
import traceback

ROOT=Path(u.Paths.project_dir()).resolve();sys.path.insert(0,str(ROOT/'Art/Unreal'))
report={'ok':False,'lidar_level_touched':False}
OUT=ROOT/'Art/Export/LidarStudy/Place';OUT.mkdir(parents=True,exist_ok=True)
try:
    import lidar_authoring_editor as editor
    editor.register_menu()
    assert u.ToolMenus.get().find_menu('LevelEditor.MainMenu.Tools.LiDARPlace')
    report['menu_registered']=True
    try:editor.require_level()
    except RuntimeError:report['wrong_level_guard']=True
    else:raise AssertionError('Wrong-level guard accepted Entry')
    # Exercise actual editor actions, but redirect their data and level guard to a disposable QA fixture.
    world=u.get_editor_subsystem(u.UnrealEditorSubsystem).get_editor_world()
    editor.require_level=lambda:world
    fixture=ROOT/'Saved/LidarAuthoringQA/editor-edits.json'
    fixture.parent.mkdir(parents=True,exist_ok=True);editor.design.DEFAULT=fixture
    editor.new_track();track=editor.paths()[0]
    assert track.rut_depth_cm==0 and track.relief_strength==0
    original=[track.control_points.get_location_at_spline_point(k,u.SplineCoordinateSpace.WORLD)
              for k in range(track.control_points.get_number_of_spline_points())]
    for k,p in enumerate(original):
        track.control_points.set_location_at_spline_point(k,p+u.Vector(0,0,500),u.SplineCoordinateSpace.WORLD,False)
    track.control_points.update_spline()
    # The installed road is a separate actor. Its selection must resolve to the
    # live editable design, without replacing it with an exported copy.
    built=editor.ACTORS.spawn_actor_from_class(u.GTProceduralRoad,u.Vector())
    built.tags=['LidarMudTrack','LidarDesign:'+track.design_id]
    # Deliberately different XY and point count: regression for snapping the old
    # design while leaving the owner's moved/extended built spline in mid-air.
    route=[[p.x+700,p.y+200,p.z+800] for p in original]
    route.append([route[-1][0]+600,route[-1][1]+200,route[-1][2]+100])
    editor.set_points(built,route)
    built.width_cm=260.
    for k in range(len(route)):built.control_points.set_scale_at_spline_point(k,u.Vector(1,[.9,1.3,1.5,1.][k],1),False)
    built.control_points.update_spline()
    editor.ACTORS.set_selected_level_actors([built]);editor.fit_track()
    assert list(editor.ACTORS.get_selected_level_actors())==[built]
    for actor in (built,track):
        assert actor.control_points.get_number_of_spline_points()==len(route)
        for k,p in enumerate(route):
            q=actor.control_points.get_location_at_spline_point(k,u.SplineCoordinateSpace.WORLD)
            assert abs(q.x-p[0])<.01 and abs(q.y-p[1])<.01 and abs(q.z-editor.current_height(*p[:2]))<.01
            assert actor.control_points.get_spline_point_type(k)==u.SplinePointType.LINEAR
    report['built_track_selection_snap']=True
    report['moved_extended_built_route_preserved']=True
    expected=[2.34,3.38,3.9,2.6]
    assert editor.serialize(track)['widths_m']==expected
    report['variable_width_snap']=True
    # Reject a generic gravel road before changing any design.
    built.tags=[];editor.ACTORS.set_selected_level_actors([built])
    try:editor.selected_tracks()
    except ValueError:report['unrelated_selection_rejected']=True
    else:raise AssertionError('Unrelated road accepted as a mud design')
    editor.ACTORS.destroy_actor(built);editor.ACTORS.set_selected_level_actors([track])
    editor.add_condition();c=track.conditions[0]
    assert c.rut_depth_cm==0 and c.water_fill_cm==0
    c.name='Local wet hollow';c.start_metres=5;c.end_metres=15;c.blend_metres=2
    track.conditions=[c]
    editor.preview_selected();first=editor.serialize(track);editor.save_designs()
    editor.ACTORS.destroy_actor(track)
    # Default Python arguments bind at import time: explicitly redirect the loader in this fixture.
    real_load=editor.design.load;editor.design.load=lambda:real_load(fixture)
    editor.load_designs();restored=editor.paths()[0]
    assert editor.serialize(restored)==first
    report['track_roundtrip']=True;report['local_conditions_roundtrip']=True;report['ground_snap']=True;report['local_condition_defaults']=True
    editor.ACTORS.destroy_actor(restored)
    # A fixed river fixture exercises viewport creation, depth fitting and bed controls.
    editor.water_reference=lambda:[[i*100,0,1000] for i in range(-40,41)]
    u.get_editor_subsystem(u.UnrealEditorSubsystem).set_level_viewport_camera_info(u.Vector(0,0,2000),u.Rotator())
    editor.new_bed();bed=editor.paths()[0];bed.target_depth_metres=.5;editor.fit_bed();editor.preview_selected()
    row=editor.serialize(bed);assert all(abs(p[2]-950)<.01 for p in row['points_cm'])
    editor.save_designs();editor.ACTORS.destroy_actor(bed);editor.load_designs()
    assert editor.serialize(editor.paths()[0])==row
    report['bed_roundtrip']=True;report['depth_fit']=True
    for a in editor.paths():editor.ACTORS.destroy_actor(a)
    report['ok']=True
except Exception:
    report['error']=traceback.format_exc();u.log_error(report['error'])
finally:
    (OUT/'authoringcheck.json').write_text(json.dumps(report,indent=2))
    u.SystemLibrary.quit_editor()
