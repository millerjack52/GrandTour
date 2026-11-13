"""Encode unretouched game viewport samples; retain provenance and review sheets."""
import json,subprocess,argparse
from pathlib import Path
from PIL import Image,ImageDraw
import imageio_ffmpeg
ROOT=Path('C:/GrandTour');QA=ROOT/'Saved/LidarAuthoringQA/RS7';OUT=ROOT/'Art/Export/LidarStudy/FirstSection/Review/PerceivedDetail';OUT.mkdir(parents=True,exist_ok=True)
p=argparse.ArgumentParser();p.add_argument('label');p.add_argument('name');a=p.parse_args()
report=json.loads((QA/(a.label+'-capture.json')).read_text(encoding='utf-8-sig'));assert report['exit_code']==0 and report['frames']==report.get('requested_frames',144) and report['render_validation_passed']
count=report['frames'];video_frames=count-2 if count==144 else count
folder=Path(report['directory']);assert all((folder/f'bank_{i:04d}.png').exists() for i in range(count))
video=OUT/(a.name+'.mp4')
subprocess.run([imageio_ffmpeg.get_ffmpeg_exe(),'-y','-hide_banner','-loglevel','error','-framerate','12','-i',str(folder/'bank_%04d.png'),'-frames:v',str(video_frames),'-c:v','libx264','-threads','2','-crf','18','-pix_fmt','yuv420p','-movflags','+faststart',str(video)],check=True)
sheet=Image.new('RGB',(1600,1036),'#111b17');draw=ImageDraw.Draw(sheet)
for j,i in enumerate([round(j*(video_frames-1)/7) for j in range(8)]):
 image=Image.open(folder/f'bank_{i:04d}.png');image.thumbnail((800,450))
 # Half-size unsharpened contact samples, two columns and four rows.
 image.resize((400,225)).save(OUT/(a.name+f'-sample-{i}.png'))
 x=(j%4)*400;y=(j//4)*259;sheet.paste(image.resize((400,225)),(x,y+30));draw.text((x+8,y+8),f'{a.name} | {i/12:.1f}s',fill='#ffffff')
sheet=sheet.crop((0,0,1600,518));sheet.save(OUT/(a.name+'-contact.png'))
report.update(video=str(video),video_frames=video_frames,seconds=video_frames/12,excluded_samples=list(range(video_frames,count)),exclusion_reason='Last two samples excluded for full-length sequences when the review camera releases; 72-sample clips cover the six-second outward move without the repeated return.')
(OUT/(a.name+'-capture.json')).write_text(json.dumps(report,indent=2));print(video)
