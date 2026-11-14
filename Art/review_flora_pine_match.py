"""Ungraded source/Unreal comparisons; measurements isolate silhouette/pigment."""
import json
from pathlib import Path
import numpy as np
from PIL import Image,ImageDraw,ImageFont,ImageFilter
R=Path('C:/GrandTour');O=R/'Art/Export/FloraTrail/PineMatch'
def linear(p):
 a=np.asarray(Image.open(p).convert('RGB'),dtype=np.float64)/255
 return np.where(a<=.04045,a/12.92,((a+.055)/1.055)**2.4)
def board(paths,dest):
 w=400;h=max(round(min(392/im.width,392/im.height)*im.height) for _,p in paths for im in [Image.open(p)])+64
 out=Image.new('RGB',(w*len(paths),h),'#142025');d=ImageDraw.Draw(out);font=ImageFont.truetype('C:/Windows/Fonts/segoeui.ttf',16)
 for i,(label,path) in enumerate(paths):
  d.text((i*w+8,8),label,font=font,fill='white');im=Image.open(path).convert('RGB');im.thumbnail((392,392));out.paste(im,(i*w+4,40))
  thumb=Image.open(path).convert('RGB');thumb.thumbnail((320,320));stem=Path(dest).stem+'_'+str(i)+'_'+Path(path).stem;thumb.save(O/(stem+'_320_colour.png'));thumb.convert('L').save(O/(stem+'_320_grey.png'))
 out.save(O/dest,quality=95)
 out.convert('L').save(O/(Path(dest).stem+'_grey.jpg'),quality=95)
def main():
 source=linear(O/'source_opacity_face.png').mean(2);rows={}
 for name in ('baseline','coverage125','coverage150','screen128','depth128','mip0','mask4k','surface150','all150','static2k','static4k','candidate'):
  p=O/('ue_'+name+'_opacity.png')
  if not p.exists():continue
  a=linear(p).mean(2)
  assert a.shape==source.shape
  common=(source>.5)|(a>.5)
  rows[name]={'integrated_opacity_ratio':float(a.sum()/source.sum()),'opacity_mean_absolute_error_on_union':float(np.abs(a-source)[common].mean()),'solid_mask_iou':float(((a>.5)&(source>.5)).sum()/common.sum())}
 if (O/'ue_baseline_pigment.png').exists():
  src=linear(O/'source_pigment_face.png');ue=linear(O/'ue_baseline_pigment.png');s=source>.95
  s=np.asarray(Image.fromarray((s*255).astype('uint8')).filter(ImageFilter.MinFilter(5)))>0
  leaf=s&(src[:,:,1]>src[:,:,0]*1.15)&(src[:,:,1]>src[:,:,2]*1.6)
  rows['pigment']={'interior_leaf_pixels':int(leaf.sum()),'source_linear_mean':src[leaf].mean(0).tolist(),'unreal_linear_mean':ue[leaf].mean(0).tolist(),'linear_absolute_error':np.abs(src[leaf]-ue[leaf]).mean(0).tolist()}
 (O/'comparison-measurements.json').write_text(json.dumps(rows,indent=2));print(json.dumps(rows,indent=2))
 for case in ('warm','side','back'):
  paths=[('Blender 3.4.1 / '+case,O/('source_'+case+'.png')),('Unreal / original pine',O/('ue_baseline_'+case+'.png'))]
  if case=='warm':paths+=[('Coverage x1.25 / diagnostic',O/'ue_coverage125_warm.png'),('Coverage x1.5 / diagnostic',O/'ue_coverage150_warm.png')]
  if all(Path(p).exists() for _,p in paths):board(paths,'compare_'+case+'.jpg')
  candidates=[('Blender / '+case,O/('source_'+case+'.png'))]+[(name,O/('ue_'+name+'_'+case+'.png')) for name in ('baseline','mask4k','surface150','all150')]
  if all(p.exists() for _,p in candidates):board(candidates,'candidate_'+case+'.jpg')
  final=[('Blender 3.4.1 / source',O/('source_'+case+'.png')),('Unreal / before',O/('ue_baseline_'+case+'.png')),('Unreal / saved correction',O/('ue_candidate_'+case+'.png'))]
  if all(p.exists() for _,p in final):board(final,'saved_'+case+'.jpg')
 paths=[('Source',O/'source_warm.png')]+[(name,O/('ue_'+name+'_warm.png')) for name in ('baseline','screen128','depth128','mip0')]
 if all(p.exists() for _,p in paths):board(paths,'compare_sampling.jpg')
 if rows:board([('Source / white coverage',O/'source_opacity_face.png'),('Unreal / baseline coverage',O/'ue_baseline_opacity.png'),('Unreal / 1.25 coverage',O/'ue_coverage125_opacity.png')],'compare_coverage.jpg')
 for view in ('road','canopy','bank','valley'):
  before=O.parent/'PineTrial'/('pine_'+view+'.png');after=O/('pine_'+view+'.png')
  if before.exists() and after.exists():board([('Before / '+view,before),('Saved pine correction / '+view,after)],'scene_'+view+'.jpg')
 frames=[Image.open(p).convert('RGB') for p in sorted(O.glob('motion_??.png'))]
 if frames:frames[0].save(O/'saved_motion.webp',save_all=True,append_images=frames[1:],duration=140,loop=0,quality=90)
 if frames:
  out=Image.new('RGB',(960,180*((len(frames)+2)//3)),'#142025');d=ImageDraw.Draw(out)
  for i,im in enumerate(frames):
   thumb=im.copy();thumb.thumbnail((316,158));x=(i%3)*320;y=(i//3)*180;out.paste(thumb,(x,y+20));d.text((x+4,y+3),'Frame '+str(i*4),fill='white')
  out.save(O/'motion_samples.jpg',quality=95)
if __name__=='__main__':main()
