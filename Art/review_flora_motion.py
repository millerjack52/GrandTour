"""Encode actual Unreal animation samples and summarize paired CSV timings."""
from pathlib import Path
import json,statistics,subprocess
from PIL import Image,ImageDraw
import imageio_ffmpeg
import review_flora_woodland as review
O=Path('D:/GrandTourAssets/ReviewEvidence/FloraTrail/Motion')
def main(stage='candidate',failed_process_evidence=False):
    report=json.loads((O/(stage+'-report.json')).read_text());assert report['ok']
    process=json.loads((O/(stage+'-process.json')).read_text(encoding='utf-8-sig'))
    assert process['exit_code']==0 or failed_process_evidence,'Failed process; explicitly opt in to diagnostic evidence only'
    label=stage+('-failed-process' if process['exit_code']!=0 else '')
    frames=sorted(O.glob(stage+'_animation_*.png'));assert len(frames)==48
    subprocess.run([imageio_ffmpeg.get_ffmpeg_exe(),'-y','-loglevel','error','-framerate','12','-i',str(O/(stage+'_animation_%03d.png')),'-c:v','libx264','-crf','18','-pix_fmt','yuv420p','-movflags','+faststart',str(O/(label+'-motion.mp4'))],check=True)
    gif=[]
    for path in frames:
        with Image.open(path) as src:im=src.convert('RGB')
        im.thumbnail((960,540));gif.append(im)
    gif[0].save(O/(label+'-motion.gif'),save_all=True,append_images=gif[1:],duration=83,loop=0)
    if stage=='verify':
        assert len(list(O.glob('verify_move_*.png')))==48
        subprocess.run([imageio_ffmpeg.get_ffmpeg_exe(),'-y','-loglevel','error','-framerate','12','-i',str(O/'verify_move_%03d.png'),'-c:v','libx264','-crf','18','-pix_fmt','yuv420p','-movflags','+faststart',str(O/(label+'-camera-move.mp4'))],check=True)
    review.O=O
    review.panel([('Actual Unreal / t=%.2f s'%report['animation_times'][i],frames[i]) for i in (0,12,24,36)],label+'-motion-frames.jpg')
    if stage=='candidate':
        review.panel([(case+' / '+view,O/f'candidate_{case}_{view}.png') for view in ('bank','leaves') for case in ('baseline','both')],'before-after.jpg')
        sheet=Image.new('RGB',(1280,4*200),(24,26,28));draw=ImageDraw.Draw(sheet)
        for row,view in enumerate(('drive','canopy','bank','valley')):
            for col,(case,grey) in enumerate((('baseline',False),('both',False),('baseline',True),('both',True))):
                with Image.open(O/f'candidate_{case}_{view}.png') as src:
                    im=src.convert('L').convert('RGB') if grey else src.convert('RGB')
                im.thumbnail((320,171));sheet.paste(im,(col*320,row*200+25))
                draw.text((col*320+6,row*200+6),view+' / '+case+(' / grey' if grey else ''),fill='white')
        sheet.save(O/'colour-greyscale-review.jpg',quality=95)
        refs=json.loads((Path('C:/GrandTour/Art/Export/FloraPaletteStudy')/'reference-evidence.json').read_text())['sources']
        review.panel([('Flora Paint / green woodland reference',Path(refs['woodland'])),('Actual Unreal / motion candidate bank',O/'candidate_both_bank.png'),('Flora Paint / forest-path reference',Path(refs['path'])),('Actual Unreal / motion candidate canopy',O/'candidate_both_canopy.png')],'reference-review.jpg')
    if stage in ('candidate','verify'):
        runs=report['profile_runs'];assert len(runs)==(6 if stage=='candidate' else 4)
        cases=('baseline','wind','both') if stage=='candidate' else ('baseline','leaves_only')
        summary={'scope':report['profile_scope'],'cases':{},'difference_ms':{},'limitations':['PIE/offscreen fixed camera; not Shipping or sustained driving','Two repeats per case; small deltas may be measurement noise','Playback is a deterministic sampled timeline, not a measured framerate']}
        summary['process_exit_code']=process['exit_code']
        if process['exit_code']!=0:summary['limitations'].append('Measurements completed before shutdown failure; this is diagnostic evidence, not a clean saved verification')
        summary['warnings']=sorted(set(w for r in runs for w in r['analysis']['warnings']))
        summary['unreliable_metrics']=[k for k in ('GameThreadTime','RenderThreadTime','RHIThreadTime') if any(k not in r['analysis']['metrics'] or r['analysis']['metrics'][k]['p95']<.01 for r in runs)]
        summary['native_capture_resolution']=report['images'][0]['size']
        for case in cases:
            rows=[r['analysis']['metrics'] for r in runs if r['case']==case]
            summary['cases'][case]={k:{'mean_ms':statistics.fmean(r[k]['mean'] for r in rows),'p95_ms':statistics.fmean(r[k]['p95'] for r in rows),'repeat_means_ms':[r[k]['mean'] for r in rows]} for k in ('FrameTime','GPUTime','GameThreadTime','RenderThreadTime') if k not in summary['unreliable_metrics'] and all(k in r for r in rows)}
        for case in cases[1:]:
            summary['difference_ms'][case]={k:round(v['mean_ms']-summary['cases']['baseline'][k]['mean_ms'],4) for k,v in summary['cases'][case].items()}
        (O/('performance-summary.json' if stage=='candidate' else 'leaf-performance-summary.json')).write_text(json.dumps(summary,indent=2)+'\n')
        print(json.dumps(summary,indent=2))
if __name__=='__main__':
    import sys
    main(sys.argv[1] if len(sys.argv)>1 else 'candidate','--failed-process-evidence' in sys.argv)
