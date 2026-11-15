"""Actual-render contact sheets, semantic crops, thumbnails and short motion strip."""
from pathlib import Path
import json
from PIL import Image,ImageDraw,ImageFont
R=Path('C:/GrandTour');O=R/'Art/Export/FloraTrail/UnderstoryStudy'
FONT=ImageFont.truetype('C:/Windows/Fonts/segoeui.ttf',20)
def grid(items,name,width=640):
 h=380 if width==640 else 215
 canvas=Image.new('RGB',(width*2,h*((len(items)+1)//2)),'#172027');d=ImageDraw.Draw(canvas)
 for i,(label,path) in enumerate(items):
  im=Image.open(path).convert('RGB');im.thumbnail((width-8,h-40));x=(i%2)*width;y=(i//2)*h
  d.text((x+8,y+5),label,font=FONT,fill='white');canvas.paste(im,(x+4,y+36))
 canvas.save(O/(name+'.jpg'),quality=95)
def main():
 report=json.loads((O/'candidate-report.json').read_text());assert report['ok']
 for view in ('drive','verge','bank'):
  grid([(label,O/('candidate_'+key+'_'+view+'.png')) for key,label in [('baseline','Before'),('coverage','Coverage only'),('lighting','Lighting only'),('rocks','Rock detail only'),('combined','Combined candidate')]],'diagnosis_'+view)
  after=O/('verify_combined_'+view+'.png')
  if not after.exists():after=O/('candidate_combined_'+view+'.png')
  grid([('Before',O/('candidate_baseline_'+view+'.png')),('Saved candidate' if after.name.startswith('verify') else 'Candidate',after)],'before_after_'+view)
 for p in O.glob('*_*.png'):
  if '_320_' in p.name or p.name.startswith('crop_'):continue
  im=Image.open(p).convert('RGB');im.thumbnail((320,320));im.save(O/(p.stem+'_320_colour.png'));im.convert('L').save(O/(p.stem+'_320_grey.png'))
 for kind in ('colour','grey'):
  grid([(case+' / '+view,O/('candidate_'+case+'_'+view+'_320_'+kind+'.png')) for view in ('verge','bank','drive') for case in ('baseline','combined')],'thumbnails_'+kind,320)
 for case in ('baseline','combined'):
  paths=sorted(O.glob('candidate_'+case+'_motion_??.png'));frames=[Image.open(p).convert('RGB') for p in paths]
  frames[0].save(O/(case+'_motion.webp'),save_all=True,append_images=frames[1:],duration=170,loop=0,quality=90)
  grid([('Motion '+str(i*6),p) for i,p in enumerate(paths) if i in (0,2,5,7)],case+'_motion_samples')
 refs=json.loads((R/'Art/Export/FloraPaletteStudy/reference-evidence.json').read_text())['sources']
 grid([('Flora Paint / woodland target',Path(refs['woodland'])),('Actual Unreal / saved candidate',O/'verify_combined_verge.png')],'reference_verge')
if __name__=='__main__':main()
