from PIL import Image,ImageDraw,ImageFont
from pathlib import Path
import json,math,argparse

p=argparse.ArgumentParser();p.add_argument('--output',default='C:/GrandTour/Art/Export/VehicleTools/pathfinder-2002-orthographic-v01');p.add_argument('--revised',action='store_true');args=p.parse_args()
out=Path(args.output)
meta=json.loads((out/'review-metadata.json').read_text())
BG=(244,243,238); INK=(34,43,49); MUTED=(91,102,106); GRID=(223,226,224); GUIDE=(91,137,146)
def font(n,bold=False):return ImageFont.truetype('C:/Windows/Fonts/arial'+('bd' if bold else '')+'.ttf',n)
def txt(im,xy,s,n=22,bold=False,fill=INK):ImageDraw.Draw(im).text(xy,s,font=font(n,bold),fill=fill)
def dash(d,p0,p1,fill=GUIDE,width=1):
    dx,dy=p1[0]-p0[0],p1[1]-p0[1];length=math.hypot(dx,dy)
    for t in range(0,int(length),16):
        q=min(t+7,length)
        d.line((p0[0]+dx*t/length,p0[1]+dy*t/length,p0[0]+dx*q/length,p0[1]+dy*q/length),fill=fill,width=width)
def panel(name):
    raw=Image.open(out/(name+'-raw.png')).convert('RGBA');w,h=raw.size
    base=Image.new('RGBA',(w,h),(*BG,255));d=ImageDraw.Draw(base)
    p=meta['views'][name]['landmarks'];ox,oy=p['origin']
    for x in range(round(ox)%150,w,150):d.line((x,0,x,h),fill=GRID,width=1)
    for y in range(round(oy)%150,h,150):d.line((0,y,w,y),fill=GRID,width=1)
    base.alpha_composite(raw);d=ImageDraw.Draw(base)
    if name=='side':
        for key in ['front_axle','rear_axle']:
            x,y=p[key];dash(d,(x,20),(x,h-14))
        dash(d,(10,p['front_axle'][1]),(w-10,p['front_axle'][1]))
        d.line((8,p['ground'][1],w-8,p['ground'][1]),fill=GUIDE,width=2)
        txt(base,(p['front_axle'][0]-46,h-33),'FRONT',16,True,MUTED)
        txt(base,(p['rear_axle'][0]-26,h-33),'REAR',16,True,MUTED)
    elif name in ['front','rear']:
        dash(d,(w/2,15),(w/2,h-16))
        dash(d,(8,p['front_axle'][1]),(w-8,p['front_axle'][1]))
        d.line((8,p['ground'][1],w-8,p['ground'][1]),fill=GUIDE,width=2)
    else:
        dash(d,(w/2,15),(w/2,h-15))
        for key in ['front_axle','rear_axle']:dash(d,(10,p[key][1]),(w-10,p[key][1]))
    return base.convert('RGB')
panels={n:panel(n) for n in meta['views']}
for n,p in panels.items():
    w,h=p.size;im=Image.new('RGB',(w+80,h+155),BG)
    txt(im,(40,24),'2002 PATHFINDER  /  '+n.upper(),28,True)
    txt(im,(40,64),'CURRENT MESH  |  True orthographic  |  Grid: 0.5 m',19,fill=MUTED)
    im.paste(p,(40,105));txt(im,(40,h+116),'Shape review only. Geometry unchanged.',18,fill=MUTED)
    im.save(out/(n+'.png'))

board=Image.new('RGB',(1640,1635),BG)
txt(board,(40,25),'2002 PATHFINDER  /  ORTHOGRAPHIC SHAPE REVIEW',34,True)
txt(board,(40,77),'Current Blender mesh. Matched scale: 300 pixels/metre. Grid: 0.5 m.',22,fill=MUTED)
txt(board,(40,127),'SIDE',24,True);board.paste(panels['side'],(40,165))
txt(board,(40,850),'FRONT',24,True);txt(board,(850,850),'REAR',24,True)
board.paste(panels['front'],(40,891));board.paste(panels['rear'],(850,891))
txt(board,(40,1580),'Dashed guides: axle centres / vehicle centreline. Solid guide: ground.',21,fill=MUTED)
board.save(out/'orthographic-overview.jpg',quality=95)

# Uniform scale and translation only. No perspective correction or nonuniform warping.
reference=Image.open('C:/GrandTour/Art/References/Vehicles/Pathfinder2002/01-crafted-utility-overall.png').convert('RGB')
crop=reference.crop((0,595,1024,966))
ref_front=(208,891);ref_rear=(769,891)
lm=meta['views']['side']['landmarks'];scale=(lm['rear_axle'][0]-lm['front_axle'][0])/(ref_rear[0]-ref_front[0])
crop=crop.resize((round(crop.width*scale),round(crop.height*scale)),Image.Resampling.LANCZOS)
target=Image.new('RGB',(1560,660),BG)
offset=(round(lm['front_axle'][0]-ref_front[0]*scale),round(lm['front_axle'][1]-(ref_front[1]-595)*scale))
target.paste(crop,offset);d=ImageDraw.Draw(target)
for k in ['front_axle','rear_axle']:
    x,y=lm[k];dash(d,(x,20),(x,644))
dash(d,(10,lm['front_axle'][1]),(1550,lm['front_axle'][1]))
compare=Image.new('RGB',(1640,1606),BG)
txt(compare,(40,24),'SIDE PROFILE  /  APPROVED TARGET vs CURRENT MESH',32,True)
txt(compare,(40,76),'Aligned by estimated wheel centres using one uniform scale.',23,fill=MUTED)
txt(compare,(40,126),'APPROVED STYLE REFERENCE',24,True)
txt(compare,(40,162),'Generated image with perspective; not a measured blueprint.',21,fill=MUTED)
compare.paste(target,(40,192))
txt(compare,(40,859),'REVISED FORM STUDY - NOT YET APPROVED' if args.revised else 'CURRENT BLENDER GEOMETRY',24,True)
txt(compare,(40,895),'New geometry, same orthographic camera and wheelbase alignment.' if args.revised else 'True side orthographic. Neutral materials; mesh unchanged.',21,fill=MUTED)
compare.paste(panels['side'],(40,926))
compare.save(out/'side-comparison.jpg',quality=96)
(out/'comparison-registration.json').write_text(json.dumps({'reference':'01-crafted-utility-overall.png','estimated_hubs_source_px':[ref_front,ref_rear],'uniform_scale':scale,'crop':[0,595,1024,966],'offset_px':offset,'warning':'Uncalibrated generated perspective reference. Alignment is visual, not a dimensional error measurement.'},indent=2))
print('LAYOUTS_READY '+str(out))
