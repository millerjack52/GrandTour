"""Encode the actual viewport samples, ending before Sequencer releases the camera."""
import json,subprocess
from pathlib import Path
import imageio_ffmpeg
root=Path('C:/GrandTour');qa=root/'Saved/LidarAuthoringQA/RS7';out=root/'Art/Export/LidarStudy/FirstSection/Review/bank-motion.mp4'
report=json.loads((qa/'motion-capture.json').read_text(encoding='utf-8-sig'))
assert report['exit_code']==0 and report['frames']==144
assert all((qa/'Motion'/f'bank_{i:04d}.png').exists() for i in range(144))
subprocess.run([imageio_ffmpeg.get_ffmpeg_exe(),'-y','-hide_banner','-loglevel','error','-framerate','12','-i',str(qa/'Motion/bank_%04d.png'),'-frames:v','142','-c:v','libx264','-threads','2','-crf','18','-pix_fmt','yuv420p','-movflags','+faststart',str(out)],check=True)
report.update(video_frames=142,video_seconds=142/12,video=str(out),excluded_samples=[142,143],exclusion_reason='Sequence completed and released the camera to the player; end the review on its settled return hold.')
(qa/'motion-capture.json').write_text(json.dumps(report,indent=2)+'\n')
print(json.dumps({'video':str(out),'seconds':142/12,'bytes':out.stat().st_size}))
