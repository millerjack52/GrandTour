"""Package actual viewport samples; playback speed is not a performance result."""
import json,subprocess
from pathlib import Path
from PIL import Image,ImageDraw,ImageFont
import imageio_ffmpeg
ROOT=Path('C:/GrandTour');QA=ROOT/'Saved/LidarAuthoringQA/RS7'
OUT=ROOT/'Art/Export/LidarStudy/FirstSection/Review/PeatMoss';OUT.mkdir(parents=True,exist_ok=True)
report=json.loads((QA/'PeatMossMotion-capture.json').read_text(encoding='utf-8-sig'))
assert report['exit_code']==0 and report['render_validation_passed'] and report['frames']==72
folder=Path(report['directory'])
subprocess.run([imageio_ffmpeg.get_ffmpeg_exe(),'-y','-hide_banner','-loglevel','error','-framerate','12','-i',str(folder/'bank_%04d.png'),'-frames:v','72','-c:v','libx264','-threads','2','-crf','18','-pix_fmt','yuv420p','-movflags','+faststart',str(OUT/'bank-motion.mp4')],check=True)
sheet=Image.new('RGB',(1600,520),'#19221b');draw=ImageDraw.Draw(sheet);font=ImageFont.truetype('C:/Windows/Fonts/arial.ttf',22)
for j,i in enumerate([0,10,20,30,40,50,60,71]):
    x=j%4*400;y=j//4*260;draw.text((x+8,y+8),f'Actual game — {i/12:.2f}s',font=font,fill='white')
    im=Image.open(folder/f'bank_{i:04d}.png');im.thumbnail((400,225));sheet.paste(im,(x,y+32))
sheet.save(OUT/'motion-contact.jpg',quality=95)
report.update(video='bank-motion.mp4',seconds=6,inspection='Viewport samples at 12 fps, not real-time performance evidence')
(OUT/'motion-evidence.json').write_text(json.dumps(report,indent=2));print(OUT/'bank-motion.mp4')
