"""Panda-specific adapter for the established modular static vehicle importer."""
from pathlib import Path
src=Path('C:/GrandTour/Art/Unreal/import_new_cars.py').read_text()
src=src.replace("new-cars-unreal-v01","panda-unreal-v01").replace("/Game/GrandTour/Vehicles/ModelStudies","/Game/GrandTour/Vehicles/Panda")
src=src.replace("/Game/GrandTour/ArtTests/NewCars/L_NewCarsReview","/Game/GrandTour/ArtTests/Panda/L_PandaReview")
src=src.replace("CARS=['CraftedUtility','Pathfinder2002','Impreza2003']","CARS=['Panda1990']")
src=src.replace("scalar(.22 if 'lens' not in s.get('source','').lower() else .32", "scalar(.065 if 'lens' not in s.get('source','').lower() else .32")
src=src.replace("scalar(max(.12,s.get('roughness',.5))", "scalar(max(.018,s.get('roughness',.5))")
src=src.replace("two_sided=glass", "two_sided=False")
src=src.replace("c.set_editor_property('cast_shadow',True)","c.set_editor_property('cast_shadow',part['group']!='Glass')")
src=src.replace("y=(i-1)*440","y=i*440")
src=src.replace("pos=u.Vector(1350,-1500,850);target=u.Vector(0,0,80)","pos=u.Vector(530,-600,340);target=u.Vector(0,0,95)")
insert='''
 cockpit=spawn(world,u.CameraActor,'NC_Camera_Panda1990_Cockpit',pos=(-19.44,-34.56,147.6+z))
 cockpit.set_actor_rotation(u.Rotator(pitch=-12,yaw=0,roll=0),False);cockpit.camera_component.set_field_of_view(90)
 report['glass']={'blend':'Translucent','opacity':0.065,'roughness':0.018,'cast_shadow':False}
 report['cockpit_camera']='NC_Camera_Panda1990_Cockpit'
'''
src=src.replace(" assert les.save_current_level()",insert+" assert les.save_current_level()",1)
exec(compile(src,'import_new_cars.py','exec'))
exec(compile(Path('C:/GrandTour/Art/Unreal/refine_panda_review.py').read_text(),'refine_panda_review.py','exec'))
