"""Package unedited runtime evidence and reference provenance for the first reach."""
import hashlib,json,shutil,re,math
from pathlib import Path
ROOT=Path('C:/GrandTour');QA=ROOT/'Saved/LidarAuthoringQA/RS7'
OUT=ROOT/'Art/Export/LidarStudy/FirstSection/Review'
def read(name):return json.loads((QA/name).read_text(encoding='utf-8-sig'))
def digest(path):
 h=hashlib.sha256()
 with path.open('rb') as f:
  while chunk:=f.read(8*1024*1024):h.update(chunk)
 return h.hexdigest()
OUT.mkdir(parents=True,exist_ok=True);(OUT/'images').mkdir(exist_ok=True)
for view in ['B01','B02','B03','B04','B05']:
 shutil.copy2(QA/f'final-{view}.png',OUT/'images'/f'final-{view}.png')
 if view!='B03':shutil.copy2(QA/f'baseline-final-{view}.png',OUT/'images'/f'baseline-{view}.png')
for name in ['release-validation.json','performance-comparison.json','cameras.json','local-exposure.json','shadow-optimization.json','motion-capture.json','runner-validate.json']:
 if (QA/name).exists():shutil.copy2(QA/name,OUT/name)
perf=read('performance-comparison.json');validation=read('release-validation.json')
motion=read('motion-capture.json') if (QA/'motion-capture.json').exists() else {}
ford_log=(ROOT/'Saved/Logs/LidarPlay-RS7-ford.log').read_text(errors='replace')
ford_positions=[list(map(float,m)) for m in re.findall(r'LogCheatManager: \?BugLoc=X=([-\d.]+) Y=([-\d.]+) Z=([-\d.]+)',ford_log)]
ford_report={'positions_cm':ford_positions,'displacement_m':math.dist(ford_positions[0],ford_positions[-1])/100 if len(ford_positions)==2 else None,'engine_flood_events':ford_log.count('engine flooded'),'scope':'Short standalone driving smoke test through the existing ford; not proof of a complete crossing or exhaustive route.'}
for suffix in ['', '-driven']:
 shutil.copy2(ROOT/f'Art/Export/LidarStudy/Place/PF60-RS7-ford-ford_walk{suffix}.png',OUT/'images'/f'ford{suffix}.png')
shutil.copy2(ROOT/'Art/Export/LidarStudy/Place/playperf-RS7-ford.json',OUT/'ford-runtime.json')
(OUT/'ford-check.json').write_text(json.dumps(ford_report,indent=2)+'\n')
acceptance={
 'date':'2026-11-06','build':'RS7 first bounded bank section',
 'state':'Built and saved; owner visual review pending; no expansion authorized by this record',
 'scope':{'frontage_m':22,'slope_span_m':15.6,'center_cm':[-45800,-31600],'new_ferns':152,'fern_forms':4,'fern_meshes':12,'grass_clumps':51,'toe_cobbles':14,'local_tree_material_overrides':12},
 'map':'/Game/GrandTour/ArtTests/LidarStudy/L_LidarStudy',
 'map_sha256':digest(ROOT/'Content/GrandTour/ArtTests/LidarStudy/L_LidarStudy.umap'),
 'owned_asset_sha256':{p.name:digest(p) for p in sorted((ROOT/'Content/GrandTour/ArtTests/LidarStudy/FirstSection').glob('*.uasset'))},
 'reference_authority':['Owner Waimeamea photos 04, 08, 15','Original woodland image for colour, variety and readability','Approved generated v03 study as secondary interpretation'],
 'views':read('cameras.json'),
 'reference_mapping':{'B01':['photo08','style','study'],'B02':['photo04','photo08'],'B03':['photo04'],'B04':['photo15','style'],'B05':['photo04','photo15']},
 'render':{'mode':'actual standalone game','resolution':[1600,900],'preset':'saved v6','local_exposure_ev100':11,'images_retouching':False,'capture_only':'HUD and car hidden; fixed saved camera actors','new_small_foliage_shadows':False},
 'gates':{
  'A_composition':{'status':'PASS','reviewer':'agent visual review, not owner acceptance','reason':'Five actual game views show continuous sloped bank with embedded exposed ribs, variable plant groups and open patches. No detached boulder wall.','evidence':['images/final-B01.png','images/final-B03.png','images/final-B04.png']},
  'B_plant_form_support':{'status':'PASS','reviewer':'agent visual and technical review','reason':'Four authored growth forms, asymmetric upright and hanging fronds; 608 root probes with 1.2 cm maximum positive gap; reload and deterministic placements match.','evidence':['images/final-B02.png','images/final-B03.png','release-validation.json']},
  'C_materials_light':{'status':'PASS','reviewer':'agent visual review, not owner acceptance','reason':'Shared moss/earth colour treatment, dark local bark, grouped olive/lime/cool foliage and bronze ageing; final gameplay captures use saved local exposure.','evidence':['images/final-B02.png','images/final-B05.png','local-exposure.json']},
  'D_motion_gameplay':{'status':'NOT TESTED','reason':'Partial evidence completed: 11.83-second actual game camera sequence, near/far return, held views, and 8.62 m standalone ford driving smoke test with no engine-flood event. Complete crossing and full live temporal/LOD route are not certified by these samples; do not mark the full gate passed.','evidence':['bank-motion.mp4','motion-capture.json','ford-check.json','images/ford-driven.png']},
  'E_performance_reproducibility':{'status':'PASS','reason':'Matched 180-frame warmed windows in four views; maximum mean GPU increase 0.56 ms at saved v6. Deterministic rebuild, save/reload and outside instance hashes pass.','evidence':['performance-comparison.json','release-validation.json']}
 },
 'owner_visual_acceptance':'PENDING',
 'limitations':['Only this 22 m section is rebuilt; surrounding old banks remain visible.','B03 camera was corrected after the original baseline; no matched before image is supplied for B03.','Source photographs are relationship references, not registered camera matches.','Motion render is an inspection sequence sampled at 12 fps, not a live frame-rate benchmark.','The original bright woodland palette is interpreted for the shaded site; this is not a claim of exact visual matching.','Performance sampling covers four fixed warmed views, not an exhaustive whole-map drive.'],
 'gpu_delta_ms':perf['gpu_delta_ms'],'motion_capture':motion,'ford_check':ford_report,'validation':validation,
 'image_hashes':{p.relative_to(OUT).as_posix():digest(p) for folder in ['images','references'] for p in sorted((OUT/folder).glob('*')) if p.is_file()}
}
(OUT/'acceptance.json').write_text(json.dumps(acceptance,indent=2)+'\n')
html=(OUT/'index.html').read_text(encoding='utf-8')
html=html.replace('See measured report','Mean GPU change: -0.28 to +0.56 ms across four matched views')
(OUT/'index.html').write_text(html,encoding='utf-8')
manifest={'build':'RS7','review':str(OUT/'index.html'),'acceptance':str(OUT/'acceptance.json'),'map_sha256':acceptance['map_sha256'],'owner_visual_acceptance':'PENDING','scope_m':[22,15.6],'backup':read('backup.json')}
(ROOT/'Art/Export/LidarStudy/Place/first-section.json').write_text(json.dumps(manifest,indent=2)+'\n')
instructions='''WAIMEAMEA FIRST SECTION - RS7 DELIVERY
2026-11-06

Open index.html for five actual standalone game views alongside the owner photos,
original colour/density reference, and approved generated study. Game captures
are unedited. The original style image is only cropped by the review page's CSS;
the complete unchanged file remains available. Camera poses are in cameras.json.

The saved map is /Game/GrandTour/ArtTests/LidarStudy/L_LidarStudy.
The new reach is centred at X=-45800, Y=-31600 cm, 22 m along the river and
15.6 m across the slope. B01 is CameraActor_1; B03 is CameraActor_3.
The Level Sequence LS_BankReview is review-only and does not auto-play in game.

Revalidate from C:/GrandTour with:
  powershell -NoProfile -File Art/rebuild_lidar_first_section.ps1 -Mode Validate
Rebuild the existing bounded reach, preserving a new backup, with:
  powershell -NoProfile -File Art/rebuild_lidar_first_section.ps1 -Mode Rebuild
Both wrappers reserve the sole Unreal slot. Do not run a second editor/game.
Blender generators and the saved dense ground survey precede asset import.
The rebuild runner refuses a changed terrain digest: resurvey/refit is required.

The original pre-section map and the matched-camera baseline remain under:
  Saved/LidarAuthoringBackups/RS7-1793994925613427600/
Original source plant and tree placements are recorded under:
  Saved/LidarAuthoringQA/RS7/source-removals.json
  Saved/LidarAuthoringQA/RS7/forest-sources.json
Restoring a baseline map discards this section and its local actor overrides;
the map-owned asset folder can remain unused. Shared plant assets were not edited.

Technical results and limitations are in acceptance.json. Agent review and owner
visual acceptance are separate. This delivery does not authorize expanding the
treatment to other banks. The surrounding old treatment remains visible.
'''
(OUT/'DELIVERY.txt').write_text(instructions,encoding='ascii')
print(json.dumps({'review':str(OUT),'images':len(acceptance['image_hashes']),'max_gpu_delta_ms':max(perf['gpu_delta_ms'].values())}))
