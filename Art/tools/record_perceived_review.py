"""Append review evidence to the existing project record without rewriting it."""
from pathlib import Path
import json,hashlib
ROOT=Path('C:/GrandTour');QA=ROOT/'Saved/LidarAuthoringQA/PerceivedDetail';OUT=ROOT/'Art/Export/LidarStudy/FirstSection/Review/PerceivedDetail'
d=json.loads((QA/'final-decision.json').read_text());e=json.loads((OUT/'evidence.json').read_text());gate=d['performance_gate']
marker='PERCEIVED DETAIL BOUNDED REVIEW - 2026-11-06'
rows='\n'.join('  '+v+': '+format(x,'+.3f')+' ms' for v,x in gate['paired_medians_ms'].items())
text=('\n\n'+marker+'\n'
 'Built a 4 x 4 m normal-detail ground patch, corrected one Cascade fern UV/baked-occlusion variant, and an AO/Nanite-voxel version of 48 existing beech trees. Original ground colour, vegetation layout, root contacts, terrain and collision are preserved. Original LOD geometry supplies the 48 trees\' shadows. TSR thin-geometry detection is enabled globally for this review candidate.\n'
 'Actual review: Art/Export/LidarStudy/FirstSection/Review/PerceivedDetail/index.html\n'
 'The review contains seven matched unretouched game views, the original style reference, site photographs, a labelled generated study, and four moving before/after clips. Motion samples are 12 fps, not a performance measurement.\n'
 'Three warmed alternating A/B pairs, 1600x900, TSR 75, saved v6 preset. Median paired GPU changes:\n'+rows+'\n'
 'Observed +1 ms median gate: '+('PASS' if gate['observed_median_gate_passed'] else 'NOT PASSED')+'. Temperature and clock variation prevents a tightly controlled sub-millisecond conclusion. Full raw timings, memory/pass metrics and telemetry remain in evidence.json and gpu-telemetry.csv. No whole-world or target-FPS claim.\n'
 'Geometry validation: 229 local instance hash unchanged; 207399 outside low-plant instances unchanged; 148373 main-forest geometry trees plus 12 local trees and 148385 existing colliders; 48 identical stand transforms; 608 root probes; 10285 frond probes on 152 plants; no additional clipping. Original CanopyKit packages and project descriptor match the pre-pass backup.\n'
 'Not promoted: POM ground, Nanite bank skin and the custom 24-view depth proxy. Captures with missing voxel material usage were invalidated. Ground normals add shading detail, not new silhouettes. This remains a bounded candidate with OWNER VISUAL ACCEPTANCE PENDING; the reference\'s colour composition and variety are not fully matched.\n'
 'Recipe: Art/Export/LidarStudy/FirstSection/PerceivedDetail/accepted.json. Asset-only rebuild: Art/rebuild_perceived_detail.ps1, with Unreal closed. Requires the existing saved stand; full-world regeneration is not integrated. The individual bake/import steps ran successfully; the convenience rebuild wrapper has not been rerun end-to-end.\n'
 'Variant switching: python Art/tools/select_perceived_variant.py baseline|final (Unreal closed). This switches experiment assets, not the entire map or global TSR config. Full pre-pass files are recorded in Saved/LidarAuthoringQA/PerceivedDetail/backup.json; Config/DefaultEngine.ini was also backed up there.\n')
text.encode('ascii')
for rel in ['docs/LIDAR_PLACE_PLAN.md','docs/LidarStudy.txt']:
 p=ROOT/rel
 if marker.encode() not in p.read_bytes():
  with p.open('ab') as f:f.write(text.encode('ascii'))
p=ROOT/'docs/LIDAR_PERCEIVED_DETAIL_RESEARCH.txt'
extra=('\n\nImplementation evidence, 2026-11-06: UE 5.8 local source accepts r.Nanite.AllowVoxels OR r.Nanite.Foliage for voxel support. Existing AllowVoxels=1 suffices here. Both NANITE and VOXELS material usage flags are required; the local copied bark and canopy materials have both. See the PerceivedDetail review for measured limitations and rejected variants.\n')
if b'Implementation evidence, 2026-11-06' not in p.read_bytes():
 with p.open('ab') as f:f.write(extra.encode('ascii'))
p=ROOT/'Art/Export/LidarStudy/Place/first-section.json';manifest=json.loads(p.read_text());manifest.update(latest_perceived_detail_review=str(OUT/'index.html'),latest_perceived_detail_evidence=str(OUT/'evidence.json'),perceived_detail_status='bounded_review_candidate',perceived_detail_owner_visual_acceptance='PENDING',perceived_detail_observed_median_gate_passed=gate['observed_median_gate_passed'],map_sha256=e['map_sha256']);p.write_text(json.dumps(manifest,indent=2))
p=OUT.parent/'index.html';page=p.read_text(encoding='utf-8');link='<p><a href="PerceivedDetail/index.html">Latest perceived-detail test: actual game comparisons, references and motion</a></p>'
if 'href="PerceivedDetail/index.html"' not in page:
 page=page.replace('</body>',link+'</body>');p.write_text(page,encoding='utf-8')
print('Review indexed and ASCII project records appended.')
