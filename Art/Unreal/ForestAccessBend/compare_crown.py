"""Compare the same tree in two matched pickup drives and a same-camera replay."""
import argparse
import json
import statistics
from pathlib import Path

import numpy as np
from PIL import Image, ImageDraw, ImageFont

from compare import timings


def panel(left, right, caption):
    image = Image.new('RGB', (left.width*2, left.height+37), '#202720')
    draw = ImageDraw.Draw(image)
    font = ImageFont.truetype('segoeui.ttf', 17)
    for i, (frame, title) in enumerate(((left, 'Original'), (right, 'Grouped crown'))):
        x = i*left.width
        draw.text((x+8,6),title+'   /   '+caption,fill='white',font=font)
        image.paste(frame,(x,37))
    return image


def read(run, name):
    with Image.open(run/name) as f:
        return f.convert('RGB')


def small(image):
    return image.resize((560,315),Image.Resampling.LANCZOS)


def animation(frames, duration, path):
    frames[0].save(path,save_all=True,append_images=frames[1:],duration=duration,loop=0,quality=88,method=3)


def crown_report(before, after, repeats):
    route = json.loads((after/'crown-window.json').read_text())
    original_path = json.loads((before/'motion.json').read_text())
    variant_path = json.loads((after/'motion.json').read_text())
    assert len(route) == 21 and len(variant_path) >= 25
    chase, errors = [], []
    for i, station, _ in variant_path:
        j, original_station, _ = min(original_path,key=lambda item: abs(item[1]-station))
        errors.append(abs(station-original_station))
        chase.append(panel(small(read(before,f'motion-{j:03d}.png')),small(read(after,f'motion-{i:03d}.png')),
                           f'pickup at {station:.1f} m'))
    assert max(errors)<.9, errors
    duration = [max(30,round(1000*(b[2]-a[2]))) for a,b in zip(variant_path,variant_path[1:])]
    animation(chase, duration+[duration[-1]], after/'broadleaf-drive.webp')
    frames = []
    examples = []
    for j,row in enumerate(route):
        station = row['station']
        left = read(after,f'window-before-{j:02d}.png')
        right = read(after,f'window-after-{j:02d}.png')
        frames.append(panel(small(left),small(right),f'passenger-side look at {station:.0f} m'))
        hidden = after/f'window-hidden-{j:02d}.png'
        if hidden.exists():
            # The hidden-tree diagnostic locates this particular crown even where branches overlap.
            a,b,h = [np.asarray(im,dtype=float) for im in (left,right,read(after,hidden.name))]
            delta = np.maximum(abs(a-h).mean(2),abs(b-h).mean(2))
            # The replay looks at the crown. Restrict detection to its vicinity;
            # moving water and changes in the HUD can dominate whole-frame differences.
            assert left.size == (1600,900)
            area = delta[240:656,560:1040]
            blocks = area.reshape(13,32,15,32).mean((1,3))
            by,bx = np.unravel_index(blocks.argmax(), blocks.shape)
            cx,cy = int(576+bx*32),int(256+by*32)
            w,h = 520,330
            cx=max(w//2,min(left.width-w//2,cx))
            cy=max(h//2,min(left.height-h//2,cy))
            box=(cx-w//2,cy-h//2,cx+w//2,cy+h//2)
            detail = panel(left.crop(box),right.crop(box),f'native-pixel crop at {station:.0f} m')
            examples.append((float(blocks.max()),station,box,detail,j))
    animation(frames, 360, after/'broadleaf-side.webp')
    assert examples
    _,station,box,detail,index = max(examples,key=lambda item:item[0])
    overview = frames[index].resize((1040,327),Image.Resampling.LANCZOS)
    draw = ImageDraw.Draw(overview)
    for x in (0,520):
        x0,y0,x1,y1 = box
        draw.rectangle((x+round(x0*520/1600),34+round(y0*520/1600),
                        x+round(x1*520/1600),34+round(y1*520/1600)),outline='#f2da97',width=2)
    still = Image.new('RGB',(1040,overview.height+detail.height),'#202720')
    still.paste(overview,(0,0))
    still.paste(detail,(0,overview.height))
    still.save(after/'broadleaf-window.jpg',quality=94,subsampling=0)
    chase[min(range(len(variant_path)),key=lambda j:abs(variant_path[j][1]-station))].save(after/'broadleaf-road.jpg',quality=94)
    runs = {}
    for kind, run in [('original',before),('grouped',after)]+repeats:
        data = json.loads((run/'drive.json').read_text())
        assert data['ok'] and data['station_end_m']>=69
        if 'driven_tree' in data:
            assert ('BendBroadleafTufts' in data['driven_tree']) == (kind=='grouped')
        runs[run.name]=dict(kind=kind,metrics=timings(run))
    blocks = sorted((after/'crown-cost').glob('*.csv*'))
    assert len(blocks)==6
    fixed = {b.name:timings(b) for b in blocks}
    deltas = {}
    for field in next(iter(fixed.values())):
        pairs=[]
        for a,b in zip(blocks[::2],blocks[1::2]):
            old,new=sorted((a,b),key=lambda f:'after' in f.name)
            pairs.append(fixed[new.name][field]['median_ms']-fixed[old.name][field]['median_ms'])
        deltas[field]=dict(pairs=pairs,median_ms=statistics.median(pairs))
    result=dict(drives=runs,window_cost=fixed,paired_cost_difference=deltas,window_examples=
                [dict(peak_hidden_tile_difference=n,station_m=s,crop=r) for n,s,r,_,_ in examples],
                featured_station=station,matched_chase_frames=len(chase),max_station_difference_m=max(errors))
    (after/'broadleaf-results.json').write_text(json.dumps(result,indent=2))
    return result


if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('before',type=Path)
    parser.add_argument('after',type=Path)
    parser.add_argument('--repeat',nargs=2,action='append',default=[],metavar=('original|grouped','RUN'))
    args=parser.parse_args()
    crown_report(args.before,args.after,[(kind,Path(run)) for kind,run in args.repeat])
