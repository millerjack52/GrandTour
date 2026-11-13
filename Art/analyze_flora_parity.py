"""Honest diagnostic board and evidence ledger; no per-plant colour fitting."""
from pathlib import Path
import json,hashlib
import numpy as np
from PIL import Image,ImageDraw,ImageFont
R=Path('C:/GrandTour');O=R/'Art/Export/LidarStudy/FloraParity'
source=json.loads((O/'source-contract.json').read_text());recipe=json.loads((O/'recipe.json').read_text())
base=json.loads((O/'build-report.json').read_text())
def raw(engine,name):
    x=np.fromfile(O/engine/(name+'.f32'),dtype=np.float32).reshape(512,512,4)
    assert np.isfinite(x).all(),(engine,name)
    return x[...,:3]
def floor(x):
    # Use the bright receiver region so a moving sphere shadow does not become
    # a spurious light-unit correction. This remains a provisional chart fit.
    patch=x[410:480,20:492].reshape(-1,3);lum=patch.mean(axis=1)
    return np.median(patch[lum>=np.quantile(lum,.85)],axis=0)
# Single neutral-front-chart multiplier, never a plant-specific fit.
gain=float(np.mean(floor(raw('blender','chart_front'))/np.maximum(floor(raw('unreal','chart_front')),1e-9)))
charts={}
for light in ('front','side','back','shade'):
    b=floor(raw('blender','chart_'+light));u=floor(raw('unreal','chart_'+light))*gain
    charts[light]={'blender_floor':b.tolist(),'unreal_floor_after_one_gain':u.tolist(),'relative_floor_error':float(np.mean(abs(u-b))/max(np.mean(b),1e-9))}
bounds={}
for asset in recipe['assets']:
    u=next(a for a in base['assets'] if a['key']==asset['key'])['bounds']
    lo,hi=np.array(asset['source_bounds']);centre=(lo+hi)*.5*np.array([100,-100,100]);extent=(hi-lo)*50
    bounds[asset['key']]={'max_centre_error_cm':float(max(abs(centre-np.array(u['origin'])))),'max_extent_error_cm':float(max(abs(extent-np.array(u['extent']))))}
protection={}
for path,digest in json.loads((O/'protected-baseline.json').read_text()).items():
    protection[path]=hashlib.sha256((R/path).read_bytes()).hexdigest()==digest
protection['purchased_source']=hashlib.sha256(Path(source['source']).read_bytes()).hexdigest()==source['source_sha256']
families={}
for name in ['Leaf_0','Fern_1','Shrubbery','Grass','Grass.003','Plant_0.001']:
    graph=source['groups'].get('Material:'+name)
    if not graph:continue
    n=next(n for n in graph['nodes'] if n['type']=='ShaderNodeGroup' and 'Flora' in n['name'])
    sockets={s['identifier']:s.get('default') for s in n['inputs']}
    families[name]={'facing_soft_Input_17':sockets['Input_17'],'diffuse_weight_Input_18':sockets['Input_18']}
report={'capture_complete':len(base['images'])==28,'global_neutral_chart_gain':gain,'chart_checks':charts,'geometry_bounds_checks':bounds,'protected_unchanged':protection,'families':families,'parity_pass':False,'performance_verified':False,'limitations':['Only bounds checked numerically; normals/UVs and silhouettes require additional passes.','One neutral-plane gain does not establish identical lighting responses; shade environment and renderer BRDFs remain under test.','Colour randomisation and procedural coordinates are not yet identical.','Initial diagnostic AA disabled in Unreal; candidate fractional coverage needs temporal and motion review.','This is an asset bench, not a woodland gameplay capture.']}
(O/'comparison-report.json').write_text(json.dumps(report,indent=2))
fontpath='C:/Windows/Fonts/segoeui.ttf'
font=ImageFont.truetype(fontpath,19);small=ImageFont.truetype(fontpath,15);large=ImageFont.truetype(fontpath,26)
engines=[('blender','Blender / original source shader'),('unreal','Unreal / current map shader')]
if (O/'unreal_candidate/fern_front_face.f32').exists():engines.append(('unreal_candidate','Unreal / coverage experiment'))
rows=[('fern_front_face','Fern - direct front light'),('shrub_side_face','Shrub - side light'),('tree_back_face','Tree - back light'),('fern_shade_face','Fern - environment only')]
w=512*len(engines)+40;h=140+len(rows)*400+70
im=Image.new('RGB',(w,h),'#131c20');draw=ImageDraw.Draw(im)
draw.text((20,12),'FLORA PAINT / SHADER DIAGNOSTICS',font=large,fill='#e8efdf')
draw.text((20,49),'Shared meshes and cameras. Common linear-to-sRGB display at +2 stops. Not a finished look.',font=small,fill='#bdc9ce')
draw.text((20,72),f'Unreal neutral-chart multiplier: {gain:.4f} for every asset. Lighting calibration and temporal validation pending.',font=small,fill='#bdc9ce')
for j,(_,title) in enumerate(engines):draw.text((20+j*512,105),title,font=font,fill='#e8efdf')
for i,(name,title) in enumerate(rows):
    y=140+i*400
    for j,(engine,_) in enumerate(engines):
        x=raw(engine,name)*(1 if engine=='blender' else gain)*4
        x=np.maximum(x,0);x=np.where(x<=.0031308,x*12.92,1.055*np.power(x,1/2.4)-.055)
        pic=Image.fromarray(np.uint8(np.clip(x,0,1)*255)).resize((374,374),Image.Resampling.LANCZOS)
        im.paste(pic,(20+j*512,y+24));draw.text((20+j*512,y),title,font=small,fill='#bdc9ce')
draw.text((20,h-52),'Coverage experiment changes opacity response only. Colour, normals and transmission still differ.',font=small,fill='#edc48a')
draw.text((20,h-28),'Not approved for map rollout. Actual Blender and Unreal renders; no generated reference imagery.',font=small,fill='#edc48a')
im.save(O/'shader-diagnostics.jpg',quality=94)
close=Image.new('RGB',(480*len(engines)+40,370),'#131c20');cd=ImageDraw.Draw(close)
cd.text((20,10),'FIRST COVERAGE EXPERIMENT / NOT YET APPROVED',font=large,fill='#e8efdf')
cd.text((20,46),'Actual fern renders. Shared crop, exposure and display transform. Lighting calibration pending.',font=small,fill='#bdc9ce')
for j,(engine,title) in enumerate(engines):
    x=raw(engine,'fern_shade_face')*(1 if engine=='blender' else gain)*4
    x=np.maximum(x,0);x=np.where(x<=.0031308,x*12.92,1.055*np.power(x,1/2.4)-.055)
    pic=Image.fromarray(np.uint8(np.clip(x,0,1)*255)).crop((85,285,435,470)).resize((460,243),Image.Resampling.LANCZOS)
    close.paste(pic,(20+j*480,112));cd.text((20+j*480,82),title,font=font,fill='#e8efdf')
close.save(O/'coverage-check.jpg',quality=95)
temporal_ready=all((O/f'{mode}-report.json').exists() and json.loads((O/f'{mode}-report.json').read_text()).get('ok') for mode in ['temporal_baseline','temporal_candidate'])
if temporal_ready:
    tgain=float(np.mean(floor(raw('blender','chart_front'))/np.maximum(floor(raw('temporal_baseline','chart_front')),1e-9)))
    tc=Image.new('RGB',(1480,370),'#131c20');td=ImageDraw.Draw(tc)
    td.text((20,10),'FERN COVERAGE / SETTLED ANTI-ALIASING CHECK',font=large,fill='#e8efdf')
    td.text((20,46),'Actual renders, identical crop. Common sRGB display; one neutral-chart gain. Lighting match remains pending.',font=small,fill='#bdc9ce')
    for j,(engine,title) in enumerate([('blender','Blender / original source shader'),('temporal_baseline','Unreal / current, settled TAA'),('temporal_candidate','Unreal / coverage, settled TAA')]):
        x=raw(engine,'fern_shade_face')*(1 if engine=='blender' else tgain)*4
        x=np.maximum(x,0);x=np.where(x<=.0031308,x*12.92,1.055*np.power(x,1/2.4)-.055)
        pic=Image.fromarray(np.uint8(np.clip(x,0,1)*255)).crop((85,285,435,470)).resize((460,243),Image.Resampling.LANCZOS)
        tc.paste(pic,(20+j*480,112));td.text((20+j*480,82),title,font=font,fill='#e8efdf')
    tc.save(O/'coverage-temporal-check.jpg',quality=95)
    report['static_temporal_check']={'completed':True,'frames':32,'method':'TAA','global_neutral_chart_gain':tgain,'motion_verified':False,'TSR_verified':False}
    report['visual_review']={'coverage':'Softer, more separated fern edges than the current Unreal material; still too sparse in places.','lighting':'Source and candidate do not yet match. Receiver calibration and separate diffuse/transmission response remain open.','decision':'Keep experimental. Do not promote to woodland yet.'}
    (O/'comparison-report.json').write_text(json.dumps(report,indent=2))
lines=['FLORA PARITY - FIRST IMPLEMENTATION RECORD','2026-11-13','','Status: source audit and initial renderer harness implemented. Full parity NOT passed.','','Source audit: 30 materials, 41 scoped graphs, 39 image records.','Source Blender 5.1.2 / Eevee / Standard view. Original file preserved.','','Verified shader structure:', 'Mix Shader: (1 - Shadow) * Translucent + Shadow * Diffuse.', 'Diffuse roughness 0.5; mesh normal. Translucent uses Combine XYZ (0,0,-10).', 'Mix Shader.001 introduces Alpha Mask coverage.', 'Layer Weight Facing and Mix.002 multiply covered shading by 1 - 0.9 * Facing.', 'Facing Soft is Input_17. Other identically named Soft sockets control random colour.', 'Emission branch is present; full branch selection must remain in the port.', '', 'Family values (source defaults; do not interpret Shadow as shadow-map opacity):']
lines += [f'{n}: facing softness {v["facing_soft_Input_17"]:.8f}, diffuse weight {v["diffuse_weight_Input_18"]:.8f}' for n,v in families.items()]
lines += ['', 'Confirmed current Unreal differences:', '- Masked Two Sided Foliage is a single native lighting approximation.', '- Current PathPainterlyCoverage applies a threshold/filter-width edge operation, not the source Facing mix.', '- Current FloraWorld wrappers add pigment shifts, root/tip tinting and modified normals absent from the exact source group.', '- Source mask blur and Generated-coordinate texture semantics need separate comparison.', '', 'First isolated candidate:', 'Art/Unreal/flora_parity_coverage.py restores the source Facing equation per family.', 'Keeps current pigment/lighting to isolate coverage. No extra texture samples.', 'Native dithered masking approximates fractional coverage; it is NOT identical to Eevee transparent shading.', 'Candidate not approved: needs settled temporal-AA and motion, shadow, mip-distance checks.', '', 'Harness:', '28 Blender + 28 Unreal captures: fern/shrub/tree, two camera angles, four lighting cases plus neutral chart.', 'Same frozen FBX geometry. Source Blender material slots restored by name with polygon indices retained.', 'Bench-local UE material instances disable wind. Current map materials and maps are untouched.', 'Float32 scene-linear RGB retained; native display PNG also retained.', 'Geometry bounds error and neutral-chart error recorded in comparison-report.json.', 'Single front neutral-chart multiplier only, never independent per-plant colour fitting.', '', 'Next implementation order:', '1. Finish colour-only, alpha-only and normal passes; lock Generated coordinates and random inputs.', '2. Validate light/display calibration and temporal coverage; restore source blur only if needed.', '3. Compare native and Substrate diffuse/transmission candidates with separate source normal semantics.', '4. Accept only improvements across front/side/back/shade and camera motion; then existing forest path.', '5. Roll into LiDAR after the scene passes. Performance profiling/60fps remains a later explicit gate.', '', 'Blender Layer Weight implementation checked against:', 'https://github.com/blender/blender/blob/v5.1.2/source/blender/gpu/shaders/material/gpu_shader_material_layer_weight.glsl', '', 'Protected hashes: '+str(protection), 'Performance: unverified. No 60fps claim.']
(O/'FIRST_IMPLEMENTATION.txt').write_text('\n'.join(lines))
assert all(protection.values()),protection
print(json.dumps({'board':str(O/'shader-diagnostics.jpg'),'gain':gain,'charts':charts,'bounds':bounds,'protected':all(protection.values())}))
