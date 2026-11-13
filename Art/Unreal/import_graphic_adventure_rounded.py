"""Import the approved rounded geometry as a separate drivable revision."""
from pathlib import Path
p=Path(__file__).with_name('import_graphic_adventure.py');s=p.read_text()
s=s.replace("FINISH='-gainterior' in u.SystemLibrary.get_command_line().lower()","FINISH=True")
s=s.replace('graphic-adventure-unreal-v02','graphic-adventure-unreal-v03')
s=s.replace("DEST+='/Finished'","DEST+='/Rounded'")
s=s.replace('/Game/GrandTour/Test/GraphicAdventure/L_GraphicAdventure_Test','/Game/GrandTour/Test/GraphicAdventure/L_GraphicAdventure_Rounded_Test')
s=s.replace("assert E.duplicate_asset('/Game/GrandTour/Test/L_TestTrack',MAP)","assert LES.new_level_from_template(MAP,'/Game/GrandTour/Test/L_TestTrack')")
a=s.index(' if FINISH:\n  backup=');b=s.index(' data=json.loads',a)
s=s[:a]+s[b:]
s=s.replace("scalar(g,.085,u.MaterialProperty.MP_OPACITY);scalar(g,.075,u.MaterialProperty.MP_ROUGHNESS)","scalar(g,.065,u.MaterialProperty.MP_OPACITY);scalar(g,.025,u.MaterialProperty.MP_ROUGHNESS)")
s=s.replace("u.LinearColor(.48,.63,.65,1)","u.LinearColor(.80,.90,.92,1)")
exec(compile(s,str(p),'exec'))
