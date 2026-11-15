"""Compare native Unreal captures of the isolated verge treatment."""
from pathlib import Path
import json
from PIL import Image,ImageDraw,ImageFont
R=Path('C:/GrandTour');O=R/'Art/Export/FloraTrail/VergeStudy'
FONT=ImageFont.truetype('C:/Windows/Fonts/segoeui.ttf',20)

def grid(items,name):
 canvas=Image.new('RGB',(1280,380*((len(items)+1)//2)),'#172027');d=ImageDraw.Draw(canvas)
 for i,(label,path) in enumerate(items):
  im=Image.open(path).convert('RGB');im.thumbnail((632,340));x=(i%2)*640;y=(i//2)*380
  d.text((x+8,y+8),label,font=FONT,fill='white');canvas.paste(im,(x+4,y+36))
  im=Image.open(path).convert('RGB');im.thumbnail((320,320));im.save(O/(path.stem+'_320_colour.png'));im.convert('L').save(O/(path.stem+'_320_grey.png'))
 canvas.save(O/(name+'.jpg'),quality=95);canvas.convert('L').save(O/(name+'_grey.jpg'),quality=95)

def main():
 assert json.loads((O/'candidate-report.json').read_text())['ok']
 for view in ['drive','close','distance','context','puddle','verge']:
  grid([('Before / pale verge',O/('candidate_baseline_'+view+'.png')),('Candidate / woodland floor',O/('candidate_woodland_floor_'+view+'.png'))],'before_after_'+view)
 paths=sorted(O.glob('candidate_woodland_floor_motion_??.png'));frames=[Image.open(p).convert('RGB') for p in paths]
 frames[0].save(O/'woodland_floor_motion.webp',save_all=True,append_images=frames[1:],duration=170,loop=0,quality=90)
 grid([('Motion sample '+str(i*6),p) for i,p in enumerate(paths) if i in [0,2,5,7]],'motion_samples')
 refs=json.loads((R/'Art/Export/FloraPaletteStudy/reference-evidence.json').read_text())['sources']
 grid([('Flora Paint / woodland target',Path(refs['woodland'])),('Actual Unreal / verge candidate',O/'candidate_woodland_floor_verge.png')],'reference_verge')
if __name__=='__main__':main()
