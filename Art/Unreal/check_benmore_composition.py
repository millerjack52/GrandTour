"""Saved placement checks, the matched overlook and a view from the branch road."""
from pathlib import Path
p=Path('C:/GrandTour/Art/Unreal/check_benmore_vista_study.py');ctx={}
exec(p.read_text().rsplit("exec(compile(source,__file__,'exec'))",1)[0],ctx)
source=ctx['source'].replace('Art/Export/BenmoreVistaStudy','Art/Export/BenmoreComposition')
source=source.replace("=='M_VistaStudy_Terrain'","=='M_Composition_Terrain'")
source=source.replace("[('High_Overlook',1,150),('Hillside_Vista',1,400),('High_Overlook_Rain',1,150)]","[('High_Overlook',1,150),('Composition_Road',1,300),('Hillside_Vista',1,400)]")
source=source.replace("            if name=='Hillside_Vista':", "            if name=='Composition_Road':yaw=0\n            if name=='Hillside_Vista':")
extra='''            expected=json.loads((OUT/'placements.json').read_text())
            groups=[a for a in actors if a.get_actor_label().startswith('Benmore_Composition_')]
            rocks=[a for a in groups if isinstance(a,u.StaticMeshActor)]
            assert len(rocks)==18
            for a in rocks:
                c=a.static_mesh_component;assert str(c.get_collision_profile_name())=='BlockAll'
                assert c.get_material(0).get_name()=='M_Composition_Schist'
            totals={}
            for kind in ['shrubs','tussocks']:
                total=0
                for a in groups:
                    if not a.get_actor_label().startswith('Benmore_Composition_'+kind+'_'):continue
                    for c in a.get_components_by_class(u.InstancedStaticMeshComponent):
                        assert str(c.get_collision_profile_name())=='NoCollision'
                        total+=c.get_instance_count()
                assert total==len(expected[kind]),(kind,total)
                totals[kind]=total
            report['composition']={'formations':len(rocks),'instances':totals,'height_changed':False}
'''
needle="            phase='begin';last=now";assert source.count(needle)==1;source=source.replace(needle,extra+needle)
# Both routes must remain unobstructed, including the branch beside this study.
source=source.replace("for p in routes[0]['points'][::60]:", "for p in [p for route in routes for p in route['points'][::30]]:")
source=source.replace("len(routes[0]['points'][::60])", "sum(len(route['points'][::30]) for route in routes)")
exec(compile(source,__file__,'exec'))
