from pathlib import Path
import json
OUT=Path('C:/GrandTour/Art/Export/VehicleTools/ferrari288-expedition-v01')
s=Path('C:/GrandTour/Art/Unreal/test_good288.py').read_text()
s=s.replace("s=s.replace('graphic-adventure-unreal-v01','ferrari288-good-game-v01')", "s=s.replace('graphic-adventure-unreal-v01','ferrari288-expedition-v01')")
s=s.replace("exec(compile(s,str(p),'exec'))",'''s=s.replace("report['mass_kg']=mesh.get_mass()", "equipment=next(c for c in car.get_components_by_class(u.StaticMeshComponent) if c.get_name().startswith('Expedition_Kit'));assert equipment.get_attach_parent()==mesh;assert equipment.get_editor_property('relative_location').length()<.01;assert equipment.get_editor_property('static_mesh').get_name()=='SM_Ferrari288_Expedition';report['equipment_attached']=True;report['mass_kg']=mesh.get_mass()")
s=s.replace("report['forward_distance_cm']=", "equipment=next(c for c in car.get_components_by_class(u.StaticMeshComponent) if c.get_name().startswith('Expedition_Kit'));assert (equipment.get_world_location()-car.get_component_by_class(u.SkeletalMeshComponent).get_world_location()).length()<.1;report['equipment_follows_driving']=True;report['forward_distance_cm']=")
s=s.replace(".set_forced_lod(2);", ".set_forced_lod(2);next(c for c in car.get_components_by_class(u.StaticMeshComponent) if c.get_name().startswith('Expedition_Kit')).set_editor_property('forced_lod_model',2);")
s=s.replace(".set_forced_lod(3);", ".set_forced_lod(3);next(c for c in car.get_components_by_class(u.StaticMeshComponent) if c.get_name().startswith('Expedition_Kit')).set_editor_property('forced_lod_model',3);")
exec(compile(s,str(p),'exec'))''')
exec(compile(s,'C:/GrandTour/Art/Unreal/test_good288.py','exec'))
