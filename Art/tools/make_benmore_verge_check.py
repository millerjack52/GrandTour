"""Derive the verge capture check from the established saved-road checker."""
from pathlib import Path
root=Path(__file__).resolve().parents[2]
text=(root/'Art/Unreal/check_benmore_reference_roads.py').read_text()
text=text.replace("OUT=ROOT/'Art/Export/BenmoreReferenceRoads'","OUT=ROOT/'Art/Export/BenmoreVerges'")
text=text.replace("report['saved_gravel_instances']=count;report['gravel_collision']='NoCollision'", """report['saved_gravel_instances']=count;report['gravel_collision']='NoCollision'
            verge=next(a for a in actors if a.get_actor_label()=='Benmore_RoadVergeDetail')
            counts={}
            for c in verge.get_components_by_class(u.InstancedStaticMeshComponent):
                assert str(c.get_collision_profile_name())=='NoCollision'
                counts[c.get_editor_property('static_mesh').get_name()]=c.get_instance_count()
            expected=json.loads((OUT/'setup-report.json').read_text())['instance_total']
            assert sum(counts.values())==expected
            report['saved_verge_instances']=sum(counts.values());report['verge_meshes']=counts""")
text=text.replace("phase='moving';name,x,y,yaw=views[index]", """phase='moving';name,x,y,yaw=views[index]
            if name=='Road_Surface_Detail':
                a=math.radians(yaw);x-=math.sin(a)*1.2;y+=math.cos(a)*1.2;yaw+=30""")
text=text.replace("row['editor_frame_interval_ms']=", "row['editor_tick_diagnostic_not_a_benchmark']=")
text=text.replace("assert near>5,('Grass did not follow camera',views[index],near)", """if near<=5 and now-last<150:
                phase='grow';return
            assert near>5,('Grass did not follow camera',views[index],near)""")
text=text.replace("assert set(by_mesh)=={'SM_TS_Straw','SM_TS_Rust','SM_TS_Weathered','SM_TS_Fine'},('Unexpected grass meshes',by_mesh)", """if set(by_mesh)!={'SM_TS_Straw','SM_TS_Rust','SM_TS_Weathered','SM_TS_Fine'} and now-last<150:
                phase='grow';return
            assert set(by_mesh)=={'SM_TS_Straw','SM_TS_Rust','SM_TS_Weathered','SM_TS_Fine'},('Unexpected grass meshes',by_mesh)""")
(root/'Art/Unreal/check_benmore_verges.py').write_text(text)
