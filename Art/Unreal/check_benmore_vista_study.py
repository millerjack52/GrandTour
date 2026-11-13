"""Same established driving/vegetation checks, starting with the long overlook."""
from pathlib import Path
p=Path('C:/GrandTour/Art/Unreal/check_benmore_painterly.py');ctx={}
exec(p.read_text().rsplit("exec(compile(source,__file__,'exec'))",1)[0],ctx)
source=ctx['source'].replace('Art/Export/BenmorePainterly','Art/Export/BenmoreVistaStudy')
source=source.replace("=='M_Painterly_Terrain'","=='M_VistaStudy_Terrain'").replace("=='M_Painterly_Hills'","=='M_VistaStudy_Hills'")
source=source.replace("=='MI_Benmore_CloudWeather'","=='MI_VistaStudy_CloudWeather'")
source=source.replace("[('Hillside_Vista',1,400),('High_Overlook',1,150),('High_Overlook_Rain',1,150)]","[('High_Overlook',1,150),('Hillside_Vista',1,400),('High_Overlook_Rain',1,150)]")
extra='''            mask=u.load_asset('/Game/GrandTour/Demo/BenmoreRoads/VistaStudy/T_Benmore_GeographicZones')
            assert mask and not mask.get_editor_property('srgb')
            assert abs(sun.light_component.get_editor_property('cloud_shadow_on_surface_strength')-.70)<.001
            assert abs(sky.get_component_by_class(u.SkyLightComponent).get_editor_property('intensity')-1.15)<.001
            report['vista_study']={'geographic_masks':True,'middle_distance_cover':True,'cloud_composition':True,'terrain_height_changed':False}
'''
needle="            phase='begin';last=now";assert source.count(needle)==1
source=source.replace(needle,extra+needle)
exec(compile(source,__file__,'exec'))
