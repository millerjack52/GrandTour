"""Import the corrected v15 Prado as a modular static assembly and review level.

Uses the same FBX, bounds, material-slot and reopen checks as the earlier cars.
Owns only Prado assets and L_PradoReview; does not change gameplay maps.
"""
from pathlib import Path

base = Path('C:/GrandTour/Art/Unreal/import_new_cars.py')
src = base.read_text()

def replace_once(old, new):
    global src
    assert src.count(old) == 1, ('Importer changed; inspect adapter', old)
    src = src.replace(old, new, 1)

replace_once('new-cars-unreal-v01', 'prado-unreal-v01')
src = src.replace('/Game/GrandTour/Vehicles/ModelStudies', '/Game/GrandTour/Vehicles/Prado')
replace_once('/Game/GrandTour/ArtTests/NewCars/L_NewCarsReview', '/Game/GrandTour/ArtTests/Prado/L_PradoReview')
replace_once("CARS=['CraftedUtility','Pathfinder2002','Impreza2003']", "CARS=['Prado']")
# Lens transmission is a Blender shading choice, not a request for transparent lamps.
replace_once("glass=s.get('transmission',0)>.05 or ('glass' in s.get('source','').lower() and 'mirror' not in s.get('source','').lower())", "glass=('glass' in s.get('source','').lower() and 'mirror' not in s.get('source','').lower())")
replace_once('two_sided=glass', "two_sided=('paint' in s.get('source','').lower())")
replace_once("scalar(.22 if 'lens' not in s.get('source','').lower() else .32,u.MaterialProperty.MP_OPACITY)", "scalar(.065,u.MaterialProperty.MP_OPACITY)")
replace_once("scalar(max(.12,s.get('roughness',.5))", "scalar(max(.018,s.get('roughness',.5))")
replace_once("c.set_editor_property('cast_shadow',True)", "c.set_editor_property('cast_shadow',part['group']!='Glass')")
# Source uses flat palette materials without a UV normal map; do not derive
# MikkTSpace tangents from absent UVs. Keep the exported surface normals.
replace_once('remove_degenerates=False)', 'remove_degenerates=False,normal_generation_method=u.FBXNormalGenerationMethod.BUILT_IN)')
replace_once('y=(i-1)*440', 'y=i*440')
replace_once("[('Front',(650,y-600,310),(0,y,95)),('Rear',(-640,y+610,290),(0,y,95)),('Side',(0,y-900,120),(0,y,120))]", "[('Front',(710,y-710,390),(0,y,142)),('Rear',(-710,y+710,350),(0,y,135)),('Side',(0,y-1020,145),(0,y,145)),('FrontClose',(490,y-210,250),(30,y,195))]")
replace_once('pos=u.Vector(1350,-1500,850);target=u.Vector(0,0,80)', 'pos=u.Vector(710,-710,390);target=u.Vector(0,0,142)')
replace_once("pos=(1350,-1500,850));start.set_actor_rotation", "pos=(710,-710,390));start.set_actor_rotation")

extra = '''
 cockpit=spawn(world,u.CameraActor,'NC_Camera_Prado_Cockpit',pos=(10,-42.5,193.5+z))
 cockpit.set_actor_rotation(u.MathLibrary.find_look_at_rotation(u.Vector(10,-42.5,193.5+z),u.Vector(85,-20,142.5+z)),False)
 cockpit.camera_component.set_field_of_view(84)
 forward=spawn(world,u.CameraActor,'NC_Camera_Prado_CabinForward',pos=(10,-42.5,193.5+z))
 forward.set_actor_rotation(u.Rotator(pitch=-12,yaw=0,roll=0),False)
 forward.camera_component.set_field_of_view(90)
 report['glass']={'blend':'Translucent','opacity':0.065,'cast_shadow':False,'classification':'Glazing only; colored rear lamp lenses opaque'}
 actors=u.get_editor_subsystem(u.EditorActorSubsystem).get_all_level_actors()
 for a in actors:
  if isinstance(a,u.CameraActor):a.camera_component.set_editor_property('constrain_aspect_ratio',False)
  if a.get_actor_label()=='NC_Sky':
   c=a.get_component_by_class(u.SkyLightComponent)
   prop(c,real_time_capture=False,source_type=u.SkyLightSourceType.SLS_SPECIFIED_CUBEMAP,cubemap=E.load_asset('/Engine/MapTemplates/Sky/DaylightAmbientCubemap'),intensity=1.5,lower_hemisphere_is_black=False)
   c.recapture_sky()
  if a.get_actor_label()=='NC_Exposure':
   a.set_editor_property('priority',200.)
   s=a.get_editor_property('settings')
   prop(s,ambient_cubemap=E.load_asset('/Engine/MapTemplates/Sky/DaylightAmbientCubemap'),override_ambient_cubemap_intensity=True,ambient_cubemap_intensity=.35)
   a.set_editor_property('settings',s)
'''
replace_once(' assert les.save_current_level()', extra + ' assert les.save_current_level()')
exec(compile(src, str(base), 'exec'))
