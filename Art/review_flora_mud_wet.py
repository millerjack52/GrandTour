"""Compare actual Unreal wetness controls, with unchanged camera and lighting."""
from pathlib import Path
import json
from PIL import Image,ImageDraw,ImageFont
R=Path('C:/GrandTour');O=R/'Art/Export/FloraTrail/MudWet'
font=ImageFont.truetype('C:/Windows/Fonts/segoeui.ttf',20)
LABELS={'baseline':'Before / current mud','colour_only':'Darker colour only','roughness_only':'Lower roughness only','wet_combined':'Wet colour + varied sheen'}
def grid(items,name):
 out=Image.new('RGB',(1280,380*((len(items)+1)//2)),'#172027');d=ImageDraw.Draw(out)
 for i,(label,p) in enumerate(items):
  im=Image.open(p).convert('RGB');im.thumbnail((632,340));x=(i%2)*640;y=(i//2)*380
  d.text((x+8,y+8),label,font=font,fill='white');out.paste(im,(x+4,y+36))
  thumb=Image.open(p).convert('RGB');thumb.thumbnail((320,320));thumb.save(O/(p.stem+'_320_colour.png'));thumb.convert('L').save(O/(p.stem+'_320_grey.png'))
 out.save(O/(name+'.jpg'),quality=95);out.convert('L').save(O/(name+'_grey.jpg'),quality=95)
def main():
 assert json.loads((O/'probe-report.json').read_text())['ok']
 for view in ['drive','close','distance','context']:
  items=[(label,O/('probe_'+key+'_'+view+'.png')) for key,label in LABELS.items()]
  grid(items,'controls_'+view);grid([items[0],items[-1]],'before_after_'+view)
 for key,label in LABELS.items():
  paths=sorted(O.glob('probe_'+key+'_motion_??.png'));frames=[Image.open(p).convert('RGB') for p in paths]
  if frames:
   frames[0].save(O/(key+'_motion.webp'),save_all=True,append_images=frames[1:],duration=170,loop=0,quality=90)
   grid([(label+' / sample '+str(i*6),p) for i,p in enumerate(paths) if i in [0,3,7]],key+'_motion_samples')
 print('Wetness controls and before/after review boards generated.')
if __name__=='__main__':main()
