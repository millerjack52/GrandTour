"""Pair pickup frames by road station and present the woodland opening at driver scale."""
import argparse
import json
import math
from pathlib import Path
import statistics
import subprocess

from PIL import Image, ImageDraw, ImageFont


def read(path):
    return json.loads(path.read_text())


def closest(motion,station):
    return min(motion,key=lambda row:abs(row[1]-station))


def panel(paths,caption,width=680,labels=('Before','River study')):
    height=width*9//16
    canvas=Image.new('RGB',(width*2,height+40),'#212723')
    draw=ImageDraw.Draw(canvas)
    try:
        font=ImageFont.truetype('segoeui.ttf',19)
    except OSError:
        font=ImageFont.load_default()
    for i,(p,label) in enumerate(zip(paths,labels)):
        with Image.open(p) as img:
            canvas.paste(img.convert('RGB').resize((width,height),Image.Resampling.LANCZOS),(i*width,40))
        draw.text((i*width+12,7),f'{label}   /   {caption}',fill='white',font=font)
    return canvas


def sheet(panels,out):
    w,h=panels[0].size
    canvas=Image.new('RGB',(w,h*len(panels)))
    for i,p in enumerate(panels):
        canvas.paste(p,(0,i*h))
    canvas.save(out,quality=92,subsampling=0)


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    for name in ['before','after','output','ffmpeg']:
        parser.add_argument('--'+name,required=True,type=Path)
    args=parser.parse_args()
    runs=[args.before,args.after]
    args.output.mkdir(exist_ok=True,parents=True)
    motion=[read(p/'motion.json') for p in runs]
    for p in runs:
        drive=read(p/'drive.json')
        assert drive['ok'] and drive['station_end_m']>=72
        assert drive['driven_tree'].split('.')[-1]=='SM_Canopy_1'
    assert read(args.after/'drive.json')['river_floor_present']
    replayed=all((p/'camera-poses.json').is_file() for p in runs)
    if replayed:
        assert read(args.before/'drive.json')['source_sha256']==read(args.after/'drive.json')['source_sha256']
        assert read(args.before/'camera-poses.json')==read(args.after/'camera-poses.json')
        assert not read(args.before/'drive.json')['river_floor_present']
    targets=[row[1] for row in motion[0] if motion[1][0][1]-.4<=row[1]<=motion[1][-1][1]+.1]
    assert targets[0]<7 and targets[-1]>70
    def matched(s):
        rows=[closest(m,s) for m in motion]
        assert max(abs(row[1]-s) for row in rows)<.8,(s,rows)
        return [p/f'motion-{r[0]:03}.png' for p,r in zip(runs,rows)], abs(rows[0][1]-rows[1][1])
    sheet([panel(matched(s)[0],name) for s,name in [
        (18,'Wooded approach | 18 m'),(52,'Turn towards the water | 52 m'),
        (70,'River entry | 70 m')]],args.output/'pickup-comparison.jpg')
    sheet([panel([p/(name+'.png') for p in runs],caption) for name,caption in [
        ('turn','Apex, fixed camera'),('verge','Forest floor, fixed camera'),('water','Across the river, fixed camera')]],
        args.output/'fixed-cameras.jpg')
    sheet([panel(matched(38)[0],'Left shoulder at the turn | 38 m',540),
           panel([p/'water.png' for p in runs],'The opposite bank',540)],args.output/'river-opening.jpg')
    output=args.output/'forest-access-to-river.mp4'
    w,h=768,472
    fps=24
    pace=5.
    cmd=[str(args.ffmpeg),'-v','error','-y','-f','rawvideo','-pix_fmt','rgb24','-s',f'{2*w}x{h}',
         '-r',str(fps),'-i','-','-an','-c:v','libx264','-preset','fast','-crf','19',
         '-pix_fmt','yuv420p','-movflags','+faststart',str(output)]
    offsets=[]
    with subprocess.Popen(cmd,stdin=subprocess.PIPE) as writer:
        last_key=last_frame=None
        for k in range(math.ceil((targets[-1]-targets[0])/pace*fps)):
            s=min(targets,key=lambda x:abs(x-(targets[0]+k*pace/fps)))
            paths,delta=matched(s)
            offsets.append(delta)
            key=(paths,round(s))
            if key!=last_key:
                last_frame=panel(paths,f'Forest access to the river  |  {s:.0f} m',w).tobytes()
                last_key=key
            writer.stdin.write(last_frame)
        for shot,label in [('water','Across the water | fixed view'),('verge','Forest floor | fixed view')]:
            frame=panel([p/(shot+'.png') for p in runs],label,w).tobytes()
            for _ in range(42):
                writer.stdin.write(frame)
        writer.stdin.close()
        if writer.wait():
            raise RuntimeError('Video encode failed')
    evidence=dict(runs=[p.name for p in runs],max_station_difference_m=max(offsets),
        median_station_difference_m=statistics.median(offsets),interval_m=[targets[0],targets[-1]],
        playback_metres_per_second=pace,paired_positions=len(targets),visual_samples=list(map(len,motion)),
        camera_poses_identical=replayed)
    (args.output/'results.json').write_text(json.dumps(evidence,indent=2))
    print(json.dumps(evidence,indent=2))


if __name__=='__main__':
    main()
