"""Compare two standalone runs. Requires Pillow. Write review media beside the runs."""
import argparse
import csv
import gzip
import json
import math
import statistics
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont


def timings(run):
    if run.is_file():trace=run
    else:trace, = run.glob("timing.csv*")
    opener = gzip.open if trace.suffix == ".gz" else open
    with opener(trace, "rt", encoding="utf-8-sig", newline="") as stream:
        rows = list(csv.DictReader(stream))
    metrics = {}
    for field in ("FrameTime", "GPUTime", "GPU/Basepass", "GPU/ShadowDepths"):
        values = []
        for row in rows:
            try:
                value = float(row[field])
            except (ValueError, TypeError):
                continue
            if value > 0 and math.isfinite(value):
                values.append(value)
        if not values:
            raise ValueError(f"Missing {field} in {trace}")
        metrics[field] = dict(frames=len(values), median_ms=statistics.median(values),
                              p95_ms=statistics.quantiles(values, n=100, method="inclusive")[94])
    return metrics


def sheet(before, after, shots, output):
    width, height, label = 720, 405, 36
    sheet = Image.new("RGB", (width*2, (height+label)*len(shots)), (28, 31, 29))
    draw = ImageDraw.Draw(sheet)
    try:
        font = ImageFont.truetype("segoeui.ttf", 21)
    except OSError:
        font = ImageFont.load_default()
    for row, (shot, caption) in enumerate(shots):
        for col, (run, stage) in enumerate(((before, "Before"), (after, "Pilot"))):
            x, y = col*width, row*(height+label)
            draw.text((x+12, y+4), f"{stage}   /   {caption}", font=font, fill="white")
            with Image.open(run/(shot+".png")) as image:
                sheet.paste(image.convert("RGB").resize((width, height), Image.Resampling.LANCZOS), (x, y+label))
    sheet.save(output, quality=92, subsampling=0)

def moss_comparison(before,after):
    width=650
    panel=Image.new('RGB',(width*2,620),(28,31,29))
    draw=ImageDraw.Draw(panel)
    try:font=ImageFont.truetype('segoeui.ttf',19)
    except OSError:font=ImageFont.load_default()
    for col,(run,title) in enumerate(((before,'Previous bend'),(after,'Revised bend'))):
        with Image.open(run/'interior.png') as frame:
            frame=frame.convert('RGB')
            x=col*width
            draw.text((x+10,4),title,font=font,fill='white')
            panel.paste(frame.resize((width,366),Image.Resampling.LANCZOS),(x,32))
            draw.text((x+10,402),'Same frame, foreground detail',font=font,fill='white')
            w,h=frame.size
            box=(round(.31*w),round(.67*h),round(.84*w),round(.94*h))
            panel.paste(frame.crop(box).resize((width,186),Image.Resampling.LANCZOS),(x,432))
    panel.save(after/'moss-and-grass.jpg',quality=94,subsampling=0)

def sunset_comparison(run):
    shots=[('ridge','Open ridge'),('woods','Forest interior'),('bend','Approach')]
    panel=Image.new('RGB',(1120,3*343),(28,31,29))
    draw=ImageDraw.Draw(panel)
    try:font=ImageFont.truetype('segoeui.ttf',17)
    except OSError:font=ImageFont.load_default()
    for row,(name,caption) in enumerate(shots):
        for col,(key,lighting) in enumerate((('daylight','Saved daylight'),('low-sun','Low sun study'))):
            with Image.open(run/f'study-{name}-{key}.png') as frame:
                x,y=col*560,row*343
                draw.text((x+9,y+2),lighting+'   /   '+caption,font=font,fill='white')
                panel.paste(frame.convert('RGB').resize((560,315),Image.Resampling.LANCZOS),(x,y+27))
    panel.save(run/'sunset-comparison.jpg',quality=94,subsampling=0)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("before", type=Path)
    parser.add_argument("after", type=Path)
    parser.add_argument("--reference", type=Path, help="Original woodland daylight reference image.")
    args = parser.parse_args()
    before, after = args.before, args.after
    if (after/'sunset-study.json').exists():sunset_comparison(after)
    if (before/'pilot-crown.png').exists() and (after/'pilot-crown.png').exists():
        moss_comparison(before,after)
        sheet(before,after,[('pilot-crown','Trial broadleaf'),('landmark','Rock shelves')],after/'crown-and-stone.jpg')
    for run in (before, after):
        if not json.loads((run/"drive.json").read_text())["ok"]:
            raise ValueError(f"Drive incomplete in {run}")
    result = {run.name: timings(run) for run in (before, after)}
    blocks=sorted((after/"dressing-cost").glob("*.csv*"))
    if blocks:
        result['stationary_dressing_cost']={f.name:timings(f) for f in blocks}
    (after/"comparison.json").write_text(json.dumps(result, indent=2))
    sheet(before, after, [("interior","Looking into the woods"), ("floor","River shoulder")], after/"forest-comparison.jpg")
    sheet(before, after, [("bend","Track at the bend"), ("fern-bed","Understorey"), ("finish","Pickup at the exit")], after/"driving-comparison.jpg")
    if args.reference:
        panel=Image.new("RGB",(1440,445),(28,31,29))
        draw=ImageDraw.Draw(panel)
        for j,(source,title) in enumerate(((args.reference,"Flora Paint woodland reference"),
                                            (after/"interior.png","LiDAR forest-access bend"))):
            with Image.open(source) as im:
                im=im.convert("RGB")
                im.thumbnail((720,405),Image.Resampling.LANCZOS)
                panel.paste(im,(720*j+(720-im.width)//2,32+(405-im.height)//2))
            draw.text((720*j+10,9),title,fill="white")
        panel.save(after/"reference-and-bend.jpg",quality=93,subsampling=0)
    if (after/"motion.json").exists():
        path = json.loads((after/"motion.json").read_text())
        if len(path) < 10 or path[-1][1] < 66:
            raise ValueError("Motion capture ended early")
        frames = []
        for i, _, _ in path:
            with Image.open(after/f"motion-{i:03}.png") as im:
                frames.append(im.convert("RGB").resize((720,405), Image.Resampling.LANCZOS))
        dt = [max(20,round((b[2]-a[2])*1000)) for a,b in zip(path,path[1:])]
        frames[0].save(after/"drive.webp", save_all=True, append_images=frames[1:],
                       duration=dt+[dt[-1]], loop=0, quality=80, method=3)
        if (before/"motion.json").exists():
            original=json.loads((before/"motion.json").read_text())
            paired=[]
            for frame,(_,station,_) in zip(frames,path):
                i,position,_=min(original,key=lambda row:abs(row[1]-station))
                if abs(position-station)>.9:raise ValueError(f"No matching pickup position at {station:.1f} m")
                pair=Image.new("RGB",(1200,362),(27,30,28))
                draw=ImageDraw.Draw(pair)
                with Image.open(before/f"motion-{i:03}.png") as old:
                    pair.paste(old.convert("RGB").resize((600,338),Image.Resampling.LANCZOS),(0,24))
                pair.paste(frame.resize((600,338),Image.Resampling.LANCZOS),(600,24))
                draw.text((10,4),f"Before   /   {position:.1f} m",fill="white")
                draw.text((610,4),f"Forest bend   /   {station:.1f} m",fill="white")
                paired.append(pair)
            paired[0].save(after/"matched-drive.webp",save_all=True,append_images=paired[1:],
                           duration=dt+[dt[-1]],loop=0,quality=82,method=3)
            best=min(range(len(path)),key=lambda i:abs(path[i][1]-47))
            paired[best].save(after/"matched-pickup.jpg",quality=94,subsampling=0)
            review=Image.new("RGB",(1200,724),(27,30,28))
            review.paste(paired[best],(0,0))
            draw=ImageDraw.Draw(review)
            for j,run in enumerate((before,after)):
                draw.text((j*600+10,366),("Before" if j==0 else "Forest bend")+"   /   looking inland",fill="white")
                with Image.open(run/"interior.png") as im:
                    review.paste(im.convert("RGB").resize((600,338),Image.Resampling.LANCZOS),(j*600,386))
            review.save(after/"pickup-and-forest.jpg",quality=94,subsampling=0)
            review.convert("L").resize((720,434),Image.Resampling.LANCZOS).save(after/"values.jpg",quality=90)
