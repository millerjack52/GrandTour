"""Compare the long lake view and a high overlook with normal game rendering."""
from pathlib import Path
source=Path('C:/GrandTour/Art/Unreal/check_benmore_character.py').read_text()
source=source.replace('Art/Export/BenmoreCharacter','Art/Export/BenmoreVistas')
source=source.replace("[('Hillside_Vista',1,400),('Terrace_Fence',0,40),('Sheltered_Scrub',1,150)]","[('Hillside_Vista',1,400),('High_Overlook',1,150)]")
source=source.replace("if name=='Sheltered_Scrub':x=278;y=115;yaw=90","if name=='High_Overlook':x=750;y=500;yaw=215")
source=source.replace("camera.set_actor_location(u.Vector(x*100", "camera.camera_component.set_field_of_view(82 if name=='High_Overlook' else 72)\n            camera.set_actor_location(u.Vector(x*100")
source=source.replace("pitch=-7 if name=='Hillside_Vista' else -4", "pitch=-7")
needle="            phase='begin';last=now"
extra='''            report['vista_scene']={}
            hills=[a for a in actors if a.get_actor_label().startswith('Benmore_Hills_')];assert len(hills)==4
            for a in hills:assert not a.get_actor_enable_collision()
            fog=next(a for a in actors if a.get_actor_label()=='Benmore_DistanceHaze')
            assert abs(fog.component.get_editor_property('fog_max_opacity')-.30)<.001
            assert abs(fog.component.get_editor_property('start_distance')-80000)<1
            sun=next(a for a in actors if isinstance(a,u.DirectionalLight) and a.get_actor_label()=='Sun')
            r=sun.get_actor_rotation();assert abs(r.pitch+27)<.01 and abs(r.yaw+125)<.01
            report['vista_scene']={'fog_max_opacity':.30,'fog_start_m':800,'sun_rotation':str(r)}
            lake=next(a for a in actors if a.get_actor_label()=='Benmore_Vista_Lake')
            assert not lake.get_actor_enable_collision()
            assert str(lake.static_mesh_component.get_collision_profile_name())=='NoCollision'
            assert abs(lake.get_actor_location().z-60)<.01
            assert lake.static_mesh_component.get_material(0).get_name()=='M_Benmore_VistaLake'
            mask=u.load_asset('/Game/GrandTour/Demo/BenmoreRoads/Vistas/T_Benmore_LakeCoverage')
            assert mask is not None
            report['lake']={'collision':'NoCollision','height_above_datum_m':.6,'coverage_source_size':[1368,1277],'texture_resource_size_at_load':[mask.blueprint_get_size_x(),mask.blueprint_get_size_y()]}
'''
assert source.count(needle)==1;source=source.replace(needle,extra+needle)
exec(compile(source,__file__,'exec'))
