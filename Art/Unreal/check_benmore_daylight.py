"""Saved daylight settings and the established two-view driving/vegetation checks."""
from pathlib import Path
p=Path('C:/GrandTour/Art/Unreal/check_benmore_vistas.py');ctx={}
exec(p.read_text().split("exec(compile(source,__file__,'exec'))")[0],ctx)
source=ctx['source'].replace('Art/Export/BenmoreVistas','Art/Export/BenmoreDaylight')
source=source.replace("fog_max_opacity')-.30", "fog_max_opacity')-.20").replace("start_distance')-80000", "start_distance')-110000").replace("'fog_max_opacity':.30,'fog_start_m':800", "'fog_max_opacity':.20,'fog_start_m':1100")
source=source.replace('abs(r.pitch+27)<.01 and abs(r.yaw+125)<.01','abs(r.pitch+24)<.01 and abs(r.yaw+80)<.01')
source=source.replace("[('Hillside_Vista',1,400),('High_Overlook',1,150)]", "[('Hillside_Vista',1,400),('High_Overlook',1,150),('High_Overlook_Rain',1,150)]")
source=source.replace("name=='High_Overlook'", "name.startswith('High_Overlook')")
source=source.replace("            camera.set_actor_location(u.Vector(x*100", "            if name.endswith('_Rain'):console('gt.Look.Weather Rain')\n            camera.set_actor_location(u.Vector(x*100")
source=source.replace("phase=='grow' and now-last>100", "phase=='grow' and now-last>(45 if views[index][0].endswith('_Rain') else 100)")
source=source.replace("            report['views'].append(row);", "            if views[index][0].endswith('_Rain'):\n                rain=u.MaterialLibrary.get_scalar_parameter_value(world,u.load_asset('/Game/GrandTour/Materials/MPC_Weather'),'RainIntensity');assert rain>.3;row['rain_intensity']=rain\n            report['views'].append(row);")
source=source.replace("        elif phase=='grow' and now-last>", "        elif phase=='grow' and index==0 and now-last>18 and not report.get('exposure_preview'):\n            report['exposure_preview']=True;console('HighResShot 1200x750 filename=\"'+(OUT/'Exposure_Preview.png').as_posix()+'\"')\n        elif phase=='grow' and now-last>")
extra='''            native=next(a for a in actors if a.get_actor_label()=='Benmore_Daylight_Clouds')
            assert isinstance(native,u.VolumetricCloud)
            sky=next(a for a in actors if isinstance(a,u.SkyLight) and a.get_actor_label()=='Sky')
            assert sky.get_component_by_class(u.SkyLightComponent).get_editor_property('real_time_capture')
            assert abs(sun.light_component.get_editor_property('intensity')-60000)<1
            pp=next(a for a in actors if a.get_actor_label()=='Benmore_Daylight_Grade')
            assert pp.get_editor_property('priority')==400
            assert not next(a for a in actors if a.get_actor_label()=='ReviewExposure').get_editor_property('enabled')
            ps=pp.get_editor_property('settings');assert abs(ps.get_editor_property('auto_exposure_min_brightness')-13.6)<.001
            assert abs(ps.get_editor_property('auto_exposure_max_brightness')-13.6)<.001
            fogsun=fog.component.get_editor_property('directional_inscattering_luminance')
            assert abs(fogsun.r-.030)<.0001 and abs(fogsun.g-.028)<.0001 and abs(fogsun.b-.025)<.0001
            cloudmi=native.get_component_by_class(u.VolumetricCloudComponent).get_editor_property('material')
            assert cloudmi.get_name()=='MI_Benmore_CloudWeather'
            for param,name in [('Layout_CloudGlobalPattern','T_CloudPattern'),('Layout_CloudHeightProfile','T_Profile_08'),('Noise_Texture3D','VT_PerlinWorley_Balanced')]:
                assert u.MaterialEditingLibrary.get_material_instance_texture_parameter_value(cloudmi,param).get_name()==name
            mosaic=next(a for a in actors if a.get_actor_label()=='Benmore_Reference_ScrubMosaics')
            counts=0
            for c in mosaic.get_components_by_class(u.InstancedStaticMeshComponent):
                assert str(c.get_collision_profile_name())=='NoCollision';counts+=c.get_instance_count()
            assert counts==3771
            cloudmat=u.load_asset('/Game/GrandTour/Demo/BenmoreRoads/Daylight/M_Benmore_VolumeClouds')
            rain_nodes=[n for n in u.MaterialEditingLibrary.get_material_expressions(cloudmat) if isinstance(n,u.MaterialExpressionCollectionParameter)]
            assert len(rain_nodes)==2
            assert all(str(n.get_editor_property('parameter_name'))=='RainIntensity' for n in rain_nodes)
            report['daylight']={'sun_lux':60000,'exposure_ev100':13.6,'native_clouds':True,'skylight_realtime_capture':True,'rain_cloud_inputs':len(rain_nodes),'reference_scrub_instances':counts}
'''
needle="            phase='begin';last=now";assert source.count(needle)==1;source=source.replace(needle,extra+needle)
exec(compile(source,__file__,'exec'))
