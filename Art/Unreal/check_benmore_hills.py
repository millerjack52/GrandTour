"""Reuse the three character viewpoints with additional saved-backdrop checks."""
from pathlib import Path
root=Path('C:/GrandTour')
source=(root/'Art/Unreal/check_benmore_character.py').read_text()
assert source.count('Art/Export/BenmoreCharacter')==1
source=source.replace('Art/Export/BenmoreCharacter','Art/Export/BenmoreHills')
# These two views cover the revised background and the nearer playable slopes.
source=source.replace("('Terrace_Fence',0,40),",'')
needle="            phase='begin';last=now"
assert source.count(needle)==1
extra='''            hills=[a for a in actors if a.get_actor_label().startswith('Benmore_Hills_')]
            assert len(hills)==4
            report['background_meshes']=[]
            for a in hills:
                c=a.static_mesh_component;assert str(c.get_collision_profile_name())=='NoCollision';assert not a.get_actor_enable_collision()
                assert a.get_actor_location().length()<.001
                mesh=c.get_editor_property('static_mesh');assert mesh.get_editor_property('nanite_settings').enabled
                report['background_meshes'].append(mesh.get_path_name())
            fog=next(a for a in actors if a.get_actor_label()=='Benmore_DistanceHaze');assert abs(fog.component.get_editor_property('fog_max_opacity')-.52)<.001
'''
source=source.replace(needle,extra+needle)
exec(compile(source,__file__,'exec'))
