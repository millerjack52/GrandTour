"""Arrange unchanged native captures into labelled review sheets and sampled clips."""
from pathlib import Path
import json,subprocess,sys,re
from PIL import Image,ImageDraw,ImageFont
import imageio_ffmpeg
R=Path('C:/GrandTour');cfg=json.loads((R/'Art/flora_transmission_settings.json').read_text());O=R/'Art/Export/FloraTransmissionStudy'/cfg['revision']
stage=sys.argv[1] if len(sys.argv)>1 else 'compare'
r=json.loads((O/(stage+'-report.json')).read_text());p=json.loads((O/(stage+'-process.json')).read_text(encoding='utf-8-sig'));assert r['ok'] and p.get('exit_code')==0,'Wait for successful renderer completion'
assert not re.search(r'Failed to compile Material|Default Material will be used|LogShaderCompilers: Error|Fatal error',(O/(stage+'.log')).read_text(errors='replace')),'Shader/runtime warning disqualifies this run'
names=list(cfg['profiles']) if stage=='compare' else [cfg['selected']]
font=ImageFont.truetype('C:/Windows/Fonts/arial.ttf',15)
if stage=='compare':
 for grey in (False,True):
  sheet=Image.new('RGB',(320*len(names),200*5),(23,25,27));d=ImageDraw.Draw(sheet)
  for row,view in enumerate(('road','bank','canopy','crowns','valley')):
   for col,name in enumerate(names):
    with Image.open(O/f'{stage}_{name}_{view}.png') as src:im=src.convert('L').convert('RGB') if grey else src.convert('RGB')
    im.thumbnail((320,171));sheet.paste(im,(320*col,200*row+25));d.text((320*col+5,200*row+5),name+' / '+view,font=font,fill='white')
  sheet.save(O/('greyscale-thumbnails.jpg' if grey else 'colour-comparison.jpg'),quality=95)
for name in names:
 frames=sorted(O.glob(stage+'_'+name+'_move_*.png'))
 if not frames:continue
 assert len(frames)==12
 subprocess.run([imageio_ffmpeg.get_ffmpeg_exe(),'-y','-loglevel','error','-framerate','3','-i',str(O/(stage+'_'+name+'_move_%02d.png')),'-c:v','libx264','-crf','18','-pix_fmt','yuv420p',str(O/(stage+'_'+name+'_sampled-move.mp4'))],check=True)
print('Reviewed',stage,len(r['images']),'native captures at',r['images'][0]['size'])
if stage=='compare':
 for view in ('road','bank','canopy','crowns','valley'):
  sheet=Image.new('RGB',(637,365*2),(23,25,27));d=ImageDraw.Draw(sheet)
  for row,(name,label) in enumerate((('baseline','Before: accepted CrownForm scene'),('gentle_grade','Candidate: transmission + less crown occlusion + subtle grade'))):
   with Image.open(O/f'compare_{name}_{view}.png') as src:im=src.copy()
   im.thumbnail((637,341));sheet.paste(im,(0,365*row+24));d.text((10,365*row+4),label,font=font,fill='white')
  sheet.save(O/(view+'-before-after.jpg'),quality=95)
 refs=json.loads((R/'Art/Export/FloraPaletteStudy/reference-evidence.json').read_text())['sources']
 sheet=Image.new('RGB',(1280,365*3),(23,25,27));d=ImageDraw.Draw(sheet)
 for row,(view,ref) in enumerate((('bank','woodland'),('canopy','path'),('crowns','sunlit'))):
  for col,(path,label) in enumerate(((O/f'compare_gentle_grade_{view}.png','Actual Unreal candidate / '+view),(Path(refs[ref]),'Original Flora Paint reference / '+ref))):
   with Image.open(path) as src:im=src.convert('RGB')
   im.thumbnail((640,341));sheet.paste(im,(640*col+(640-im.width)//2,365*row+24+(341-im.height)//2));d.text((640*col+8,365*row+4),label,font=font,fill='white')
 sheet.save(O/'candidate-and-references.jpg',quality=95)
 sheet=Image.new('RGB',(1280,163*3),(23,25,27));d=ImageDraw.Draw(sheet)
 for row,name in enumerate(('baseline','combined','gentle_grade')):
  for col,index in enumerate((0,3,6,9,11)):
   with Image.open(O/f'compare_{name}_move_{index:02d}.png') as src:im=src.convert('RGB')
   im.thumbnail((256,137));sheet.paste(im,(256*col,163*row+24));d.text((256*col+5,163*row+3),name+' / sample '+str(index),font=font,fill='white')
 sheet.save(O/'sampled-move-contact-sheet.jpg',quality=95)
