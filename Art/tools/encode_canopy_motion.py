from pathlib import Path
import subprocess,json,argparse
import imageio_ffmpeg
ROOT=Path('C:/GrandTour');QA=ROOT/'Saved/LidarAuthoringQA/CanopyDepth'
p=argparse.ArgumentParser();p.add_argument('--label',default='canopy-depth-valley');p.add_argument('--directory',default='Saved/CDMotion');p.add_argument('--output',default='valley.mp4');a=p.parse_args()
report=json.loads((ROOT/f'Saved/LidarAuthoringQA/RS7/{a.label}-capture.json').read_text(encoding='utf-8-sig'))
assert report['exit_code']==0 and report['render_validation_passed'] and report['frames']==72
subprocess.run([imageio_ffmpeg.get_ffmpeg_exe(),'-y','-framerate','12','-i',str(ROOT/a.directory/'bank_%04d.png'),'-vf','scale=1280:720','-c:v','libx264','-crf','19','-pix_fmt','yuv420p','-movflags','+faststart',str(QA/a.output)],check=True,stdout=subprocess.DEVNULL,stderr=subprocess.PIPE)
print(QA/a.output)
