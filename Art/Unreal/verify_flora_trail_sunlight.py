"""Reload and verify the daylight correction without modifying saved material assets."""
from pathlib import Path
p=Path('C:/GrandTour/Art/Unreal/review_source34_flora_trail.py')
s=p.read_text().replace("O=R/'Art/Export/FloraTrail/Source34'","O=R/'Art/Export/FloraTrail/Sunlight'")
s=s.replace('from flora_trail_asset_audit import verify','from flora_trail_asset_audit import verify,await_bark_textures').replace(" report['assets_before']=verify(world)"," yield from await_bark_textures()\n report['assets_before']=verify(world)")
exec(compile(s,__file__,'exec'),globals())
