"""Unretouched fixed-camera Unreal evidence for the level-water candidate."""
from pathlib import Path
import json
from PIL import Image,ImageDraw,ImageFont
R=Path('C:/GrandTour');O=R/'Art/Export/FloraTrail/WaterFlat'
font=ImageFont.truetype('C:/Windows/Fonts/segoeui.ttf',20)
LABELS={'baseline':'Before / displaced water','geometry_only':'Level geometry / old normals','flat_water':'Level water / flat normals'}

def grid(items,name):
 out=Image.new('RGB',(1280,380*((len(items)+1)//2)),'#172027');d=ImageDraw.Draw(out)
 for i,(label,p) in enumerate(items):
  im=Image.open(p).convert('RGB');im.thumbnail((632,340));x=(i%2)*640;y=(i//2)*380
  d.text((x+8,y+8),label,font=font,fill='white');out.paste(im,(x+4,y+36))
  im=Image.open(p).convert('RGB');im.thumbnail((320,320));im.save(O/(p.stem+'_320_colour.png'));im.convert('L').save(O/(p.stem+'_320_grey.png'))
 out.save(O/(name+'.jpg'),quality=95);out.convert('L').save(O/(name+'_grey.jpg'),quality=95)

def main():
 assert json.loads((O/'probe-report.json').read_text())['ok']
 for view in ['drive','close','distance','context','puddle','pond']:
  items=[(label,O/('probe_'+key+'_'+view+'.png')) for key,label in LABELS.items()]
  grid(items,'controls_'+view);grid([items[0],items[-1]],'before_after_'+view)
 for key in LABELS:
  frames=[Image.open(p).convert('RGB') for p in sorted(O.glob('probe_'+key+'_motion_??.png'))]
  frames[0].save(O/(key+'_motion.webp'),save_all=True,append_images=frames[1:],duration=170,loop=0,quality=90)
 paths=sorted(O.glob('probe_flat_water_motion_??.png'))
 grid([('Flat water / motion sample '+str(i*6),p) for i,p in enumerate(paths) if i in [0,2,5,7]],'flat_water_motion_samples')
 refs=json.loads((R/'Art/Export/FloraPaletteStudy/reference-evidence.json').read_text())['sources']
 grid([('Flora Paint / woodland target',Path(refs['woodland'])),('Actual Unreal / current candidate',O/'probe_flat_water_context.png')],'reference_context')
 print('Level water comparison boards and sampled motion generated.')
if __name__=='__main__':main()
