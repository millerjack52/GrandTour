"""Diagnostic comparison layout, preserving both source images.
Uniform camera registration from wheelbase; no silhouette warping or artwork edits.
"""
import sys,json
from pathlib import Path
from PIL import Image,ImageDraw,ImageFont
folder=Path(sys.argv[1]);ref=Image.open(folder/'02-side-profile.png').convert('RGB');render=Image.open(folder/'side.png').convert('RGB')
# Blender ortho scale is horizontal 4.85 m; source registration is 400 px/m.
native_ppm=render.width/4.85;scale=400/native_ppm
tx=893-render.width/2*scale;ty=757-.9*400-render.height/2*scale
aligned=render.transform(ref.size,Image.Transform.AFFINE,(1/scale,0,-tx/scale,0,1/scale,-ty/scale),resample=Image.Resampling.BICUBIC,fillcolor=(205,207,208))
canvas=Image.new('RGB',(1881,2*837+156),(245,243,237));canvas.paste(ref,(0,56));canvas.paste(aligned,(0,949));draw=ImageDraw.Draw(canvas)
font=ImageFont.truetype('C:/Windows/Fonts/segoeui.ttf',30);small=ImageFont.truetype('C:/Windows/Fonts/segoeui.ttf',21)
draw.text((34,10),'APPROVED REFERENCE',fill=(25,32,40),font=font);draw.text((34,901),'BLENDER REBUILD — same wheel-centre registration',fill=(25,32,40),font=font)
for yoff in [56,949]:
 for x in [386,1400]:draw.line([(x,yoff+710),(x,yoff+800)],fill=(31,134,151),width=2)
 draw.line([(70,yoff+757),(1800,yoff+757)],fill=(31,134,151),width=1)
draw.text((34,1798),'Generated reference is an artistic target. Alignment uses uniform scale and translation only.',fill=(50,60,70),font=small)
canvas.resize((1254,1220),Image.Resampling.LANCZOS).save(folder/'side-reference-comparison.png')
(folder/'comparison-registration.json').write_text(json.dumps({'render_pixels_per_metre':native_ppm,'reference_pixels_per_artistic_metre':400,'uniform_scale':scale,'translation_px':[tx,ty],'warping':False},indent=2))
print(folder/'side-reference-comparison.png')
