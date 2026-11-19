"""Label real Unreal captures; retain native files and honest sampled-motion limits."""
from pathlib import Path
import json,re,subprocess
from PIL import Image,ImageDraw,ImageFont
import imageio_ffmpeg
R=Path('C:/GrandTour');O=R/'Art/Export/LidarFloraTransfer'
for stage in ('before','install','verify'):
 r=json.loads((O/(stage+'-report.json')).read_text());p=json.loads((O/(stage+'-process.json')).read_text(encoding='utf-8-sig'))
 assert r['ok'] and p['exit_code']==0,stage
 assert not re.search(r'Failed to compile Material|Default Material will be used|LogShaderCompilers: Error|Fatal error',(O/(stage+'.log')).read_text(errors='replace')),stage
font=ImageFont.truetype('C:/Windows/Fonts/arial.ttf',17)
views=('road','bank','canopy','valley','long_valley')
for grey in (False,True):
 board=Image.new('RGB',(1280,365*len(views)),(23,25,27));d=ImageDraw.Draw(board)
 for row,v in enumerate(views):
  for col,(stage,label) in enumerate((('before','Before'),('verify','Saved LiDAR update'))):
   with Image.open(O/f'{stage}_{v}.png') as src:im=src.convert('L').convert('RGB') if grey else src.convert('RGB')
   im.thumbnail((640,341));board.paste(im,(640*col,365*row+24));d.text((640*col+8,365*row+3),label+' / '+v,font=font,fill='white')
 board.save(O/('greyscale-review.jpg' if grey else 'before-after.jpg'),quality=95)
 for row,v in enumerate(views):board.crop((0,365*row,1280,365*(row+1))).save(O/(v+('-greyscale.jpg' if grey else '-comparison.jpg')),quality=95)
thumb=Image.open(O/'greyscale-review.jpg');thumb.resize((640,913),Image.Resampling.LANCZOS).save(O/'greyscale-thumbnails.jpg',quality=95)
refs=json.loads((R/'Art/Export/FloraPaletteStudy/reference-evidence.json').read_text())['sources']
board=Image.new('RGB',(1280,730),(23,25,27));d=ImageDraw.Draw(board)
for row,(v,ref) in enumerate((('canopy','woodland'),('road','path'))):
 for col,(file,label) in enumerate(((O/f'verify_{v}.png','Actual saved LiDAR / '+v),(Path(refs[ref]),'Original Flora Paint reference / '+ref))):
  with Image.open(file) as src:im=src.convert('RGB')
  im.thumbnail((640,341));board.paste(im,(640*col+(640-im.width)//2,365*row+24+(341-im.height)//2));d.text((640*col+8,365*row+3),label,font=font,fill='white')
board.save(O/'lidar-and-references.jpg',quality=95)
for stage in ('before','verify'):
 assert len(list(O.glob(stage+'_move_*.png')))==12
 subprocess.run([imageio_ffmpeg.get_ffmpeg_exe(),'-y','-loglevel','error','-framerate','3','-i',str(O/(stage+'_move_%02d.png')),'-c:v','libx264','-crf','18','-pix_fmt','yuv420p',str(O/(stage+'-sampled-move.mp4'))],check=True)
print('Review sheets and 3 fps sampled-camera clips written; native images unchanged.')
