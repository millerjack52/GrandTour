"""Repeat the real interaction, driving and steering regression for the tuned Ferrari."""
from pathlib import Path
p=Path('C:/GrandTour/Art/Unreal/test_benmore_fleet_driving.py');s=p.read_text()
s=s.replace("OUT=Path('C:/GrandTour/Art/Export/BenmoreFleet/Driving')","OUT=Path('C:/GrandTour/Art/Export/BenmoreFleet/FerrariPower')")
s=s.replace("OUT/'runtime-report.json'","OUT/'road-drive-report.json'")
s=s.replace("a.get_actor_label().startswith('Benmore_Fleet_')","a.get_actor_label()=='Benmore_Fleet_Ferrari288'")
s=s.replace('assert len(cars)==12,len(cars)','assert len(cars)==1,len(cars)')
exec(compile(s,str(p),'exec'))
