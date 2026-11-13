from pathlib import Path
p=Path(__file__).with_name('verify_graphic_adventure_interior.py')
s=p.read_text().replace('graphic-adventure-unreal-v02','graphic-adventure-unreal-v03').replace('graphic-adventure-interior-v01/GraphicAdventure_Interior.blend','graphic-adventure-rounded-v01/GraphicAdventure_Rounded.blend')
exec(compile(s,str(p),'exec'))
