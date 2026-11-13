"""Unsaved LOD2 curve-segment candidates; retain near meshes and all blades."""
import hashlib,json
from pathlib import Path
from benmore_far_tussock_trial import SOURCE_ROOT,TRIAL_ROOT


def create_candidates(manifest_path,destination):
    import unreal as u
    assert destination.startswith(TRIAL_ROOT) and '..' not in destination
    assert not u.EditorLevelLibrary.get_game_world()
    file=Path(manifest_path).resolve()
    manifest=json.loads(file.read_text())
    assert sorted(row['variant'] for row in manifest['models'])==['Fine','Rust','Straw','Weathered']
    sm=u.get_editor_subsystem(u.StaticMeshEditorSubsystem)
    pending=[]
    for row in manifest['models']:
        fbx=Path(row['fbx']).resolve()
        assert fbx.parent==file.parent and hashlib.sha256(fbx.read_bytes()).hexdigest()==row['fbx_sha256']
        assert row['lod']==2 and row['area_ratio']>.90
        source=u.load_asset(SOURCE_ROOT+'SM_TS_'+row['variant'])
        assert source and sm.get_lod_count(source)==3
        assert not source.get_editor_property('nanite_settings').enabled
        assert sm.get_number_verts(source,2)==row['reference_triangles']+2*row['blades']
        screens=list(sm.get_lod_screen_sizes(source))
        assert abs(screens[2]-.025)<1e-6
        near=[sm.get_number_verts(source,i) for i in (0,1)]
        path=destination+'/SM_TS_'+row['variant']+'_Segments'
        assert not u.EditorAssetLibrary.does_asset_exist(path)
        pending.append((source,path,fbx,screens,near,row))
    results=[]
    for source,path,fbx,screens,near,row in pending:
        clone=u.EditorAssetLibrary.duplicate_asset(source.get_path_name(),path)
        assert clone and sm.import_lod(clone,2,str(fbx))==2
        assert clone.get_num_sections(2)==1 and len(source.get_editor_property('static_materials'))==1
        sm.set_lod_material_slot(clone,0,2,0)
        clone.set_editor_property('static_materials',source.get_editor_property('static_materials'))
        assert sm.set_lod_screen_sizes(clone,screens)
        assert sm.get_lod_count(clone)==3
        assert sm.get_number_verts(clone,2)==row['triangles']+2*row['blades']
        assert [sm.get_number_verts(clone,i) for i in (0,1)]==near
        assert clone.get_material(0)==source.get_material(0)
        for lod in (0,1):
            assert clone.get_num_sections(lod)==source.get_num_sections(lod)
            for section in range(source.get_num_sections(lod)):
                assert sm.get_lod_material_slot(clone,lod,section)==sm.get_lod_material_slot(source,lod,section)
        results.append({'source':source.get_path_name(),'candidate':clone,'geometry':row})
    return results
