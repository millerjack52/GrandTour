"""Linear-light measurements and unretouched native-render comparison boards."""
from pathlib import Path
import json,hashlib
import numpy as np
from PIL import Image,ImageDraw,ImageFont
R=Path('C:/GrandTour');O=R/'Art/Export/FloraTreeLightBench'
reports={k:json.loads((O/k/'report.json').read_text()) for k in ['blender34','blender51','unreal']}
processes={k:json.loads((O/(k+'-process.json')).read_text()) for k in reports}
assert all(r['ok'] for r in reports.values())
assert all(p['exit_code']==0 for p in processes.values())
assert reports['blender34']['source_hash']==reports['blender51']['source_hash']
assert reports['blender34']['fbx_hash']==reports['blender51']['fbx_hash']==reports['unreal']['source_fbx_sha256']
log=(O/'unreal.log').read_text(errors='replace')
assert not any(s in log for s in ['Failed to compile Material','Default Material will be used','LogShaderCompilers: Error','Fatal error'])
protected=json.loads((O/'protected-before.json').read_text())
for p,h in protected.items():assert hashlib.sha256(Path(p).read_bytes()).hexdigest()==h,p
def raw(folder,name):return np.fromfile(O/folder/(name+'.f32'),np.float32).reshape(768,768,4)[:,:,:3]
def median(a):return np.median(a,axis=0).astype(float).tolist()
def rel(a,b):return float(np.mean(np.abs(a-b))/max(1e-6,np.mean(a)))
pig=raw('blender34','tree_pigment_face');opacity=raw('blender34','tree_opacity_face')[:,:,0];other=raw('unreal','tree_opacity_face')[:,:,0]
mask=(opacity>.95)&(other>.9)&(pig[:,:,1]>.8*pig[:,:,0])&(pig[:,:,1]>1.5*pig[:,:,2]);mask[390:]=False
assert mask.sum()>5000
metrics={'canopy_mask':'Reference opacity > .95, candidate opacity > .9, upper 390 rows, G > .8 R and G > 1.5 B in source pigment; no sky/floor. Scene-linear RGB, no image grading.','pixels':int(mask.sum()),'lighting':{},'grey':{}}
for case in json.loads((O/'recipe.json').read_text())['cases']:
 name=case['name'];b=raw('blender34','tree_'+name)[mask];u=raw('unreal','matched_'+name)[mask];old=raw('unreal','current_'+name)[mask]
 metrics['lighting'][name]={'blender_median_rgb':median(b),'matched_median_rgb':median(u),'previous_median_rgb':median(old),'matched_relative_rgb_error':rel(b,u),'previous_relative_rgb_error':rel(b,old)}
 b=raw('blender34','chart_'+name)[650:730,20:160].reshape(-1,3);u=raw('unreal','chart_'+name)[650:730,20:160].reshape(-1,3)
 metrics['grey'][name]={'blender_median_rgb':median(b),'unreal_median_rgb':median(u),'relative_error':rel(b,u)}
metrics['version_front']={'blender34_median_rgb':median(raw('blender34','tree_front')[mask]),'blender51_median_rgb':median(raw('blender51','tree_front')[mask]),'pigment_relative_error':rel(raw('blender34','tree_pigment_face')[mask],raw('blender51','tree_pigment_face')[mask])}
metrics['coverage']={'source_integral':float(opacity[:390].sum()),'candidate_integral':float(other[:390].sum()),'ratio':float(other[:390].sum()/opacity[:390].sum())}
if (O/'unreal/matched_sun_unshadowed.f32').exists():
 b=raw('blender34','tree_sun_unshadowed')[mask];a=raw('unreal','matched_sun_unshadowed')[mask]
 metrics['unshadowed_lobe']={'blender_median_rgb':median(b),'unreal_median_rgb':median(a),'relative_rgb_error':rel(b,a)}
 b=raw('blender34','tree_sun_only');ground=np.zeros((768,768),bool);ground[450:680,415:660]=True;ground&=(b[:,:,0]<.10)&(b[:,:,0]>.005)
 metrics['shadow_probes']={'ground_mask':'Rows 450:680, columns 415:660; source linear red .005 to .1, avoiding tree trunk.','source_ground_mean':float(b[ground].mean()),'cases':{}}
 for name in ['matched_sun_only','matched_sun_cascade','shadow_coverage_65','shadow_coverage_35','shadow_coverage_15','shadow_bias_1_5','shadow_bias_4_0','shadow_bias_8_0']:
  if (O/'unreal'/(name+'.f32')).exists():
   a=raw('unreal',name);metrics['shadow_probes']['cases'][name]={'crown_median_rgb':median(a[mask]),'crown_relative_rgb_error':rel(b[mask],a[mask]),'ground_mean':float(a[ground].mean()),'ground_relative_rgb_error':rel(b[ground],a[ground])}
assert max(v['relative_error'] for v in metrics['grey'].values())<.025, 'Neutral receiver calibration failed'
assert all(v['matched_relative_rgb_error']<v['previous_relative_rgb_error'] for v in metrics['lighting'].values()), 'Candidate does not improve every lighting case'
(O/'measurements.json').write_text(json.dumps(metrics,indent=2))

bg=(17,25,27);ink='#e5e9df';muted='#b5c5bf';font=ImageFont.truetype('C:/Windows/Fonts/segoeui.ttf',28);small=ImageFont.truetype('C:/Windows/Fonts/segoeui.ttf',21)
def tile(board,path,x,y,w,h):
 im=Image.open(path).convert('RGB');im.thumbnail((w,h),Image.Resampling.LANCZOS);board.paste(im,(x+(w-im.width)//2,y+(h-im.height)//2))
board=Image.new('RGB',(1536,1160),bg);d=ImageDraw.Draw(board)
d.text((18,12),'SAME FLORA PAINT TREE / source-version colour and lighting match',font=font,fill=ink)
for col,(folder,prefix,label) in enumerate([('blender34','tree','Blender 3.4.1 / original material'),('unreal','current','Unreal / previous scene response'),('unreal','matched','Unreal / source-matched response')]):
 x=12+col*508;d.text((x,58),label,font=small,fill=ink)
 for row,case in enumerate(['front','warm']):tile(board,O/folder/(prefix+'_'+case+'.png'),x,90+row*518,500,500)
d.text((18,1120),'Top: neutral daylight. Bottom: warm sun + cool sky. Actual native renders; no image recolouring.',font=small,fill=muted)
board.save(O/'same-tree-comparison.jpg',quality=95)
board=Image.new('RGB',(1536,1115),bg);d=ImageDraw.Draw(board)
d.text((18,12),'LIGHTING VALIDATION / Blender 3.4.1 (left) and Unreal (right) in each pair',font=font,fill=ink)
for row,cases in enumerate([['front','side','back'],['sky','warm','sun_only']]):
 for col,case in enumerate(cases):
  x=12+col*508;y=64+row*510;d.text((x,y),case.replace('_',' ').title(),font=small,fill=ink)
  for j,(folder,prefix) in enumerate([('blender34','tree'),('unreal','matched')]):tile(board,O/folder/(prefix+'_'+case+'.png'),x+j*250,y+42,246,440)
board.save(O/'lighting-comparison.jpg',quality=95)
board=Image.new('RGB',(1536,650),bg);d=ImageDraw.Draw(board)
d.text((18,12),'WHY THE TARGET DRIFTED / same original tree, same light, same exposure',font=font,fill=ink)
for col,(folder,label) in enumerate([('blender34','Author-specified Blender 3.4.1'),('blender51','Blender 5.1.2'),('unreal','Unreal / matched to 3.4.1')]):
 x=12+col*508;d.text((x,60),label,font=small,fill=ink);tile(board,O/folder/('matched_front.png' if folder=='unreal' else 'tree_front.png'),x,98,500,500)
d.text((18,612),'The purchased readme specifies Blender 3.4.1. The newer renderer changes the leaf-light response.',font=small,fill=muted)
board.save(O/'renderer-version-comparison.jpg',quality=95)
validation={'ok':True,'source_author':'Casey Sheep / Flora Paint','processes':processes,'measurements':metrics,'reports':reports,'protected_packages_and_settings':len(protected),'production_unchanged':True,'performance_verified':False,'shadow_decision':'Retain coverage 1 and default VSM normal bias .5. Reduced coverage weakened ground shadows; increased bias did not improve the crown. Cascaded shadows changed the ground shadow and are not selected.','images':['same-tree-comparison.jpg','lighting-comparison.jpg','renderer-version-comparison.jpg'],'limitations':['Single tree material family, not a whole-pack conversion','Capture-specific Standard display; production viewport migration not attempted','Residual opacity and shadow differences are measured, not claimed exact','No runtime performance benchmark']}
(O/'review-report.json').write_text(json.dumps(validation,indent=2)+'\n')
(R/'docs/validation/flora-tree-lightbench.json').write_text(json.dumps(validation,indent=2)+'\n')
print(json.dumps({'ok':True,'grey':metrics['grey'],'lighting':metrics['lighting']},indent=2))
