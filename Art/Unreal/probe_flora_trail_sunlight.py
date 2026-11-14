"""Reversible direct-sun probes using the saved calibrated materials and fixed exposure."""
from pathlib import Path
root=Path('C:/GrandTour')
text=(root/'Art/Unreal/review_source34_flora_trail.py').read_text()
changes={
 "O=R/'Art/Export/FloraTrail/Source34'":"O=R/'Art/Export/FloraTrail/Sunlight'",
 "STAGE='verify' if SAVED else 'preview'":"STAGE='probe'",
 "from flora_trail_asset_audit import verify":"from flora_trail_asset_audit import verify,await_bark_textures",
 " report['assets_before']=verify(world)":" yield from await_bark_textures()\n report['assets_before']=verify(world)",
 "mats={k:(u.load_asset(D+'/Materials/Source34/M_Source34_'+k) if SAVED else candidate(k)) for k in ['tree','pine']}":"mats={k:u.load_asset(D+'/Materials/Source34/M_Source34_'+k) for k in ['tree','pine']}",
 "for mode in (['saved'] if SAVED else ['before','candidate']):":"for mode in ['before','sun8','sun16','sun37']:",
 "if mode=='candidate':":"if mode!='before':",
 "report['lighting']=configure(world,settings())":"cfg=settings();cfg['sun_energy']={'sun8':8.,'sun16':16.,'sun37':37.52}[mode];cfg['sun_ray']=[-.233908564,-.810244143,-.537392974];report.setdefault('lighting_cases',{})[mode]=configure(world,cfg)",
 "if mode=='before' and label in ['mixed','pond']:continue":"if label in ['canopy','pond']:continue",
}
for old,new in changes.items():
 assert text.count(old)==1,old
 text=text.replace(old,new)
exec(compile(text,__file__,'exec'),globals())
