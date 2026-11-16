"""Encode actual Unreal animation samples and summarize paired CSV timings."""
from pathlib import Path
import json,statistics,subprocess
from PIL import Image,ImageDraw
import imageio_ffmpeg
import review_flora_woodland as review
O=Path('D:/GrandTourAssets/ReviewEvidence/FloraTrail/Motion')
def main(stage='candidate'):
    report=json.loads((O/(stage+'-report.json')).read_text());assert report['ok']
    frames=sorted(O.glob(stage+'_animation_*.png'));assert len(frames)==48
    subprocess.run([imageio_ffmpeg.get_ffmpeg_exe(),'-y','-loglevel','error','-framerate','12','-i',str(O/(stage+'_animation_%03d.png')),'-c:v','libx264','-crf','18','-pix_fmt','yuv420p','-movflags','+faststart',str(O/(stage+'-motion.mp4'))],check=True)
    gif=[]
    for path in frames:
        with Image.open(path) as src:im=src.convert('RGB')
        im.thumbnail((960,540));gif.append(im)
    gif[0].save(O/(stage+'-motion.gif'),save_all=True,append_images=gif[1:],duration=83,loop=0)
    review.O=O
    review.panel([('Actual Unreal / t=%.2f s'%report['animation_times'][i],frames[i]) for i in (0,12,24,36)],stage+'-motion-frames.jpg')
    if stage=='candidate':
        review.panel([(case+' / '+view,O/f'candidate_{case}_{view}.png') for view in ('bank','leaves') for case in ('baseline','both')],'before-after.jpg')
        runs=report['profile_runs'];assert len(runs)==6
        summary={'scope':report['profile_scope'],'cases':{},'difference_ms':{},'limitations':['PIE/offscreen fixed camera; not Shipping or sustained driving','Two repeats per case; small deltas may be measurement noise','Playback is a deterministic sampled timeline, not a measured framerate']}
        for case in ('baseline','wind','both'):
            rows=[r['analysis']['metrics'] for r in runs if r['case']==case]
            summary['cases'][case]={k:{'mean_ms':statistics.fmean(r[k]['mean'] for r in rows),'p95_ms':statistics.fmean(r[k]['p95'] for r in rows),'repeat_means_ms':[r[k]['mean'] for r in rows]} for k in ('FrameTime','GPUTime','GameThreadTime','RenderThreadTime') if all(k in r for r in rows)}
        for case in ('wind','both'):
            summary['difference_ms'][case]={k:round(v['mean_ms']-summary['cases']['baseline'][k]['mean_ms'],4) for k,v in summary['cases'][case].items()}
        (O/'performance-summary.json').write_text(json.dumps(summary,indent=2)+'\n')
        print(json.dumps(summary,indent=2))
if __name__=='__main__':
    import sys
    main(sys.argv[1] if len(sys.argv)>1 else 'candidate')
