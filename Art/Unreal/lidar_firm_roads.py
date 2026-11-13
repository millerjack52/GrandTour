"""FR1: shared construction policy for established LiDAR gravel roads.

Logging designs and river gravel banks are deliberately not members of this set.
The material still supplies pebble detail; collision has no yielding soil or ruts.
"""
NAMES = ('Riverside access', 'Pond field spur', 'Waimeamea Road', 'Waterhouse Road')
VERSION = 'fr1-1'


def preserve_live_water(author, refs):
    import array
    import hashlib
    import unreal as u
    live=[a for a in refs if isinstance(a,u.GTWaterSheet) and a.get_editor_property('mud_initial_domain')]
    if not live:return dict(live_basins=0)
    assert len(live)==4,'Unexpected live-water layout; inspect before changing presentation'
    sheet=author.surface.simulated_water
    seed=list(sheet.get_editor_property('water_domain').road_patches)[-1]
    def signature(d):
        return (d.size_x,d.size_y,d.cell_cm,d.origin_cm.x,d.origin_cm.y,
                hashlib.sha256(array.array('f',d.samples).tobytes()).hexdigest())
    current=signature(seed)
    checked=set()
    for basin in live:
        initial=basin.get_editor_property('mud_initial_domain')
        if initial.get_path_name() not in checked:
            assert signature(initial)==current,'Road rebuild changed the live-water seed'
            checked.add(initial.get_path_name())
    pool=author.road_water_mesh
    assert pool
    before=pool.get_editor_property('hidden')
    pool.set_actor_hidden_in_game(True)
    return dict(live_basins=len(live),seed_unchanged=True,baked_hidden_before=before,baked_hidden_after=True)


def record_install_metadata(root, report):
    """Certify only this targeted rebuild; retain the previous install evidence."""
    import json
    import shutil
    from pathlib import Path
    assert report['saved_and_reloaded'] and report['repeat_digest_stable']
    assert report['protected_max_height_change_cm'] < .01
    root=Path(root)
    backup=Path(report['backup'])
    file=root/'Art/Export/LidarStudy/Place/install.json'
    installed=json.loads(file.read_text())
    assert installed['road_generation']['digest'] in (report['before_digest'],report['after_digest'])
    if not (backup/'install.json').exists():shutil.copy2(file,backup/'install.json')
    installed['firm_gravel']=dict(version=VERSION,report='Saved/LidarAuthoringQA/FR1/apply.json',
                                  before_digest=report['before_digest'],roads=report['roads'])
    installed['road_generation'].update(digest=report['after_digest'],triangles=report['triangles'])
    installed['rd1']['version']='rd1-5-fr1'
    installed['rd1']['note']='FR1 targeted firm-road rebuild; legacy condition values remain the preserved end-profile inputs. See firm_gravel.'
    file.write_text(json.dumps(installed,indent=2)+'\n')
    for name in ('ground-survey.json','layout.json'):
        file=root/'Art/Export/LidarStudy/Homestead'/name
        data=json.loads(file.read_text())
        assert data['ground_digest'] in (report['before_digest'],report['after_digest'])
        if not (backup/name).exists():shutil.copy2(file,backup/name)
        data['ground_digest']=report['after_digest']
        file.write_text(json.dumps(data,indent=2)+'\n')


def configure(road):
    road.set_editor_property('firm_gravel', True)
    road.set_editor_property('profile_smoothing_metres', 16.)
    road.set_editor_property('firm_maximum_cut_fill_cm', 120.)
    road.set_editor_property('firm_profile_end_preserve_metres', 35. if road.get_actor_label().endswith('Riverside access') else 0.)
    road.set_editor_property('mud_depth_cm', 0.)

