"""Exercise the rounded revision with existing driving and capture checks."""
from pathlib import Path
p=Path(__file__).with_name('test_graphic_adventure_drive.py');s=p.read_text()
s=s.replace("FINISH='-gainterior' in u.SystemLibrary.get_command_line().lower()","FINISH=True")
s=s.replace('graphic-adventure-unreal-v02','graphic-adventure-unreal-v03')
s=s.replace('/Game/GrandTour/Test/GraphicAdventure/L_GraphicAdventure_Test','/Game/GrandTour/Test/GraphicAdventure/L_GraphicAdventure_Rounded_Test')
s=s.replace("'/Finished/'","'/Rounded/'")
exec(compile(s,str(p),'exec'))
