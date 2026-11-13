"""Run the existing two-view regression and validate the added scrub patches."""
from pathlib import Path
p=Path('C:/GrandTour/Art/Unreal/check_benmore_vistas.py')
wrapper=p.read_text().replace("extra='''", "extra='''            mosaics=next(a for a in actors if a.get_actor_label()=='Benmore_Reference_ScrubMosaics')\n            total=0\n            for c in mosaics.get_components_by_class(u.InstancedStaticMeshComponent):\n                assert str(c.get_collision_profile_name())=='NoCollision'\n                total+=c.get_instance_count()\n            assert total==3771,total\n            report['reference_scrub_instances']=total\n")
wrapper=wrapper.replace("exec(compile(source,__file__,'exec'))", "source=source.replace('Art/Export/BenmoreVistas','Art/Export/BenmoreReferenceVistas')\nexec(compile(source,__file__,'exec'))")
wrapper=wrapper.replace("fog_max_opacity')-.30", "fog_max_opacity')-.20").replace("start_distance')-80000", "start_distance')-110000").replace("'fog_max_opacity':.30,'fog_start_m':800", "'fog_max_opacity':.20,'fog_start_m':1100")
exec(compile(wrapper,str(p),'exec'))
