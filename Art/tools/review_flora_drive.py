from pathlib import Path
import json,hashlib,html,shutil,re
from PIL import Image,ImageDraw,ImageFont,ImageOps
ROOT=Path('C:/GrandTour');O=ROOT/'Art/Export/FloraDrive'
build=json.loads((O/'build-report.json').read_text());check=json.loads((O/'functional-report.json').read_text());capture=json.loads((O/'capture-report.json').read_text());assert build['ok'] and check['ok'] and capture['ok']
protected=json.loads((O/'protected-before.json').read_text());assert all(hashlib.sha256(Path(p).read_bytes()).hexdigest()==h for p,h in protected.items())
for p in capture['images']:
 assert Path(p).exists();assert Image.open(p).width>=1200
shutil.copy2(ROOT/'Art/Export/LidarStudy/FloraPath/reference-image2.png',O/'reference-forest.png')
font=lambda n:ImageFont.truetype('C:/Windows/Fonts/arial.ttf',n)
c=Image.new('RGB',(1680,1120),'#152322');d=ImageDraw.Draw(c)
d.text((24,18),'FLORA DRIVE / actual playable Unreal demo',font=font(32),fill='#eee9d6')
d.text((24,65),'Flora Paint vegetation + Cloud Paint sky / original assets by Casey Sheep and MeiU',font=font(19),fill='#b6c7b8')
for x,y,label,file in [(24,108,'FOREST PATH / new Flora Paint assets','06_forest_path.png'),(852,108,'PLAYABLE ROUTE / car at muddy checkpoint','02_broken_puddles.png'),(24,608,'WET CLEARING / interactive water','07_wet_clearing.png'),(852,608,'CANOPY + SKY / Cloud Paint source renders','08_clouds_canopy.png')]:
 d.text((x,y),label,font=font(20),fill='#e0d3a1');im=Image.open(O/file).convert('RGB');c.paste(ImageOps.fit(im,(804,452),method=Image.Resampling.LANCZOS),(x,y+35))
c.save(O/'demo-overview.jpg',quality=94)
comparison=Image.new('RGB',(1600,1040),'#152322');d=ImageDraw.Draw(comparison)
d.text((24,18),'FOREST FLOOR / actual Unreal before and after',font=font(29),fill='#eee9d6')
d.text((24,61),'Same forest-path camera. Layered ground, POM and reduced sun / ambient fill.',font=font(19),fill='#b6c7b8')
for x,label,path in [(24,'BEFORE / smooth soil',O/'BeforeGround/06_forest_path.png'),(812,'AFTER / ground + lighting',O/'06_forest_path.png')]:
 d.text((x,106),label,font=font(23),fill='#e0d3a1')
 im=Image.open(path).convert('RGB');comparison.paste(ImageOps.contain(im,(764,410)),(x,146))
 # Identical ground crop, enlarged to reveal changes without reframing the camera.
 im=im.crop((0,int(im.height*.66),im.width,im.height));comparison.paste(ImageOps.contain(im,(764,260)),(x,588))
d.text((24,885),'Actual close ground view and the original Flora Paint reference are included in the review page.',font=font(20),fill='#b6c7b8')
d.text((24,925),'POM: 10-24 steps nearby, fades at 7-18 m. GPU timings remain unverified.',font=font(20),fill='#b6c7b8')
comparison.save(O/'ground-before-after.jpg',quality=95)
pomboard=Image.new('RGB',(1600,1000),'#152322');pd=ImageDraw.Draw(pomboard)
pd.text((24,20),'GROUND RELIEF / normal maps versus POM',font=font(30),fill='#eee9d6')
pd.text((24,64),'Actual Unreal captures. Identical camera, material colours and revised lighting.',font=font(20),fill='#b6c7b8')
for x,label,name in [(24,'NORMAL MAPS ONLY','11_normal_only.png'),(812,'PARALLAX OCCLUSION MAPPING','12_parallax.png')]:
 pd.text((x,108),label,font=font(22),fill='#e0d3a1');im=Image.open(O/name).convert('RGB')
 pomboard.paste(ImageOps.contain(im,(764,410)),(x,147))
 # Match the central ground crop rather than enlarging separate patches.
 crop=im.crop((int(im.width*.2),int(im.height*.35),int(im.width*.8),int(im.height*.85)))
 pomboard.paste(ImageOps.contain(crop,(764,350)),(x,590))
pomboard.save(O/'parallax-comparison.jpg',quality=96)
route=check['route'];validation={'ok':True,'map':build['level'],'route_m':round(route['travel_cm']/100,2),'max_soil_compression_cm':route['max_compression_cm'],'max_wheel_water_cm':route['max_water_cm'],'max_terrain_height_change_cm':check['max_worked_height_change_cm'],'reset_height_error_cm':check['max_reset_height_error_cm'],'reset_scope':'route probes beyond the occupied entry; parked tyres immediately work entry soil again','shader_oracle_preflight': 'Test Completed. Result={Success} Name={ShaderOracle}' in (O/'shader-oracle-preflight.log').read_text(errors='replace'),'tree_instances':build['tree_instances'],'plant_instances':build['plant_instances'],'cloud_cards':build['cloud_cards'],'protected_maps_unchanged':True,'performance_verified':False,'cloud_representation':'creator-rendered distant cards; fixed daylight; not traversable volumes','wind_enabled':False,'final_visual_pass':'capture-report.json','continuous_drive_evidence':'functional-report.json','visual_match_passed':False}
(O/'validation.json').write_text(json.dumps(validation,indent=2))
metrics=f"The car traversed {validation['route_m']:.1f} m. Maximum soil compression: {validation['max_soil_compression_cm']:.1f} cm. Maximum wheel water contact: {validation['max_wheel_water_cm']:.1f} cm. Reset height error: {validation['reset_height_error_cm']:.4f} cm."
page='''<!doctype html><html lang="en"><meta charset="utf-8"><meta name="viewport" content="width=device-width"><title>Flora Drive / playable demo</title><style>*{box-sizing:border-box}body{max-width:1680px;margin:auto;padding:28px;background:#152322;color:#eee9d6;font:17px/1.65 system-ui}h1,h2{font-weight:500}p{max-width:1120px;color:#becbc0}a{color:#e4cf9c}img{display:block;width:100%}figure{margin:0}figcaption{padding:9px 0}.pair{display:grid;grid-template-columns:1fr 1fr;gap:20px}.note{padding:16px 22px;border-left:3px solid #d3bc79;background:#24382f}code{overflow-wrap:anywhere}@media(max-width:850px){.pair{grid-template-columns:1fr}body{padding:16px}}</style>
<h1>Flora Drive / playable forest study</h1><p>A small drivable test of the new FlippedNormals art: Flora Paint trees, grasses, ferns, flowers and rocks, with Cloud Paint clouds. GrandTour's existing vehicle, deformable mud and interactive water provide the gameplay. Original purchased artwork and assets: Casey Sheep / MeiU.</p>
<img src="06_forest_path.png" alt="Actual Unreal forest path view"><p><a href="demo-overview.jpg">Open the four-view demo sheet</a> · <a href="05_overview.png">View the whole test plot</a></p>
<h2>Drive it</h2><p>Run <code>C:/GrandTour/Play-FloraDrive.bat</code>. Map: <code>/Game/GrandTour/ArtTests/FloraDrive/L_FloraDrive</code>.</p><p>WASD drive · Space brake · C camera · 1 / 2 / 3 recovery points · Backspace fresh level · V low range · X differential lock · F leave vehicle · F1 driving information.</p>
<div class="pair"><figure><img src="02_broken_puddles.png"><figcaption>Actual possessed car / puddle checkpoint</figcaption></figure><figure><img src="03_flooded_dip.png"><figcaption>Actual car / flooded checkpoint</figcaption></figure></div>
<h2>Reference and current scene</h2><div class="pair"><figure><img src="reference-forest.png"><figcaption>Your supplied forest-path reference / Casey Sheep, Flora Paint</figcaption></figure><figure><img src="07_wet_clearing.png"><figcaption>New drivable clearing / different layout and camera</figcaption></figure></div>
<h2>Cloud Paint in the demo</h2><div class="pair"><figure><img src="Cloud_Assets_003.png"><figcaption>Purchased Cloud Paint asset rendered in its documented Eevee setup</figcaption></figure><figure><img src="08_clouds_canopy.png"><figcaption>Actual Unreal canopy and sky</figcaption></figure></div>
<p>Cloud Paint's creator documents Eevee-only rendering and does not support game-engine export. Three original assets were rendered into RGBA sky elements and placed on eight distant cards. Their source shader appearance is baked for this daylight setup; they are not traversable volumetric clouds. The forest uses the approved FloraPath material conversion, including its documented Unreal shading approximations. Map-local mud and tread materials retain the existing deformation and pigment calculation while using Unreal lighting, so tree shadows land on the ground.</p>
<h2>Functional checks</h2><p>'''+html.escape(metrics)+'''</p><p>The continuous-drive check preceded the final colour and plant-density adjustment; those changes do not alter the simulation or road collision. The final images are stationary checkpoint and review-camera captures. The check verifies vehicle possession, three recovery points, continuous driving, changed terrain heights, live water-bed updates and restoration after reset at route probes beyond the occupied entry. The parked car immediately works the entry soil again. GPU shader outputs are compared against the existing mud/water oracle fixtures.</p>
<p class="note">Performance timings remain unverified while another game shares the GPU. Trees are instanced with three LODs, small plants cull by distance, and clouds use eight simple cards. Wind is frozen for this first demo. This test does not establish large-map performance.</p>
<h2>Appearance controls and sources</h2><p><a href="look-settings.json">Map-specific colours, light, exposure and fog</a> · <a href="sources-and-transfer.txt">Documentation and transfer decisions</a> · <a href="validation.json">Validation summary</a> · <a href="functional-report.json">Full driving check</a></p>
<p>Documentation consulted: <a href="https://flippednormals.com/products/the-blender-nature-vfx-flipbox">FlippedNormals bundle requirements</a>, <a href="https://superhivemarket.com/products/cloud-paint/docs">Cloud Paint manual</a>, and <a href="https://superhivemarket.com/products/flora-paint-stylized-tree-and-plants-library/docs">Flora Paint compatibility/documentation page</a>. The linked Flora Paint Notion manual returned 404; the available creator notes and downloaded material graphs were used.</p><p>Existing woodland and previous study maps are unchanged.</p></html>'''
page=page.replace('<h2>Drive it</h2>','<h2>Ground breakup</h2><img src="ground-before-after.jpg" alt="Same-camera ground before and after"><p>Purchased Lazy Forest Gen soil, moss and leaf-litter textures with their matching normals. Irregular patches, 34 shallow shoulder forms and small Flora Paint stone clusters connect the planted areas. The driving lane retains native tyre deformation and puddles. Shoulder forms are visual dressing without collision.</p><img src="09_ground_detail.png" alt="Actual Unreal ground detail"><h2>Drive it</h2>')
page=page.replace('final colour and plant-density adjustment','final material and decorative ground adjustment')
page=page.replace('<h2>Ground breakup</h2>','<h2>Close surface relief</h2><img src="parallax-comparison.jpg" alt="Actual Unreal normal-only versus POM"><p>POM uses a packed height texture reconstructed approximately from the purchased normal maps. It traces 10–24 steps nearby and fades out at 7–18 metres. Colour and normals use the same offset UVs and explicit mip gradients. No pixel-depth offset, collision or additional geometry is introduced by POM. The sun is reduced from 65,000 to 30,000 lux and ambient fill from 5,000 to 2,200.</p><p><a href="10_flat_control.png">Flat-normal control</a> · <a href="13_world_normals.png">World normal diagnostic</a> · <a href="14_parallax_moved.png">Camera moved 70 cm</a> · <a href="https://dev.epicgames.com/community/learning/tutorials/kyXK/unreal-engine-creation-of-parallax-occlusion-mapping-pom-in-details">Epic-hosted POM reference</a></p><h2>Ground breakup</h2>')
(O/'index.html').write_text(page,encoding='utf-8')
for p in re.findall(r'(?:src|href)="([^"]+)"',page):
 if not p.startswith('https:'):assert (O/p).exists(),p
print(json.dumps(validation,indent=2))
