"""Record the final bounded trial without treating visual review as owner approval."""
from pathlib import Path
import json,statistics,sys
from measure_perceived_detail import run
ROOT=Path('C:/GrandTour');QA=ROOT/'Saved/LidarAuthoringQA/PerceivedDetail';OUT=ROOT/'Art/Export/LidarStudy/FirstSection/PerceivedDetail'
pairs=[['pd-shadow-a'+str(i),'pd-shadow-b'+str(i)] for i in range(1,4)]
runs=[(run(a),run(b)) for a,b in pairs]
deltas={v:statistics.median(b['measurements'][v]['GPUTime']['median']-a['measurements'][v]['GPUTime']['median'] for a,b in runs) for v in runs[0][0]['measurements']}
spread={v:[b['measurements'][v]['GPUTime']['median']-a['measurements'][v]['GPUTime']['median'] for a,b in runs] for v in deltas}
worst=max(deltas.values());passed=worst<=1
limits=('This is a bounded review candidate, not a full-world rollout or owner visual approval. GPU temperature and clock speed varied; the paired medians do not establish a tightly controlled sub-millisecond cost. '
 'The normal detail changes shading, not silhouettes or ground geometry. The existing forest outside the 48-tree stand is unchanged. The original reference still has stronger colour composition and vegetation variety. '
 'Motion review is sampled at 12 fps and is not a high-speed traversal or frame-rate certification. No opaque terrain Nanite assembly was promoted.')
d=dict(pairs=pairs,before_label='pd-shadow-a3',after_label='pd-shadow-b3',summary='A bounded detail pass: coherent ground normals, baked fern occlusion, and a 48-tree canopy experiment. Actual unretouched game captures are shown beside the supplied references.',
 retained=['4 x 4 m ground patch: packed normal/height/AO detail while retaining the previous ground colour texture; normal-only shading is active.',
 'One existing Cascade fern variant: corrected leaflet UVs, vein normals and baked self-occlusion. Geometry, placement and wind weights are unchanged.',
 '48 existing beech trees: geometric cavity colour and Nanite voxel representation. Original tree LODs provide their shadows; transforms and collision are unchanged.',
 'TSR thin-geometry detection enabled for the candidate. This is a global reconstruction setting, not confined to the test stand.'],
 rejected=['Parallax-occlusion ground prototype and Nanite bank-skin test remain experiments.',
 'The 24-view depth-reprojected tree proxy was built, but was not selected for this review.',
 'Voxel renders with missing voxel material usage were invalidated and excluded. Global r.Nanite.Foliage=1 was unnecessary; the existing AllowVoxels setting enables this path.'],
 limitations=limits,owner_visual_acceptance='PENDING',performance_gate=dict(target_ms=1,maximum_median_paired_delta_ms=worst,observed_median_gate_passed=passed,paired_medians_ms=deltas,paired_deltas_ms=spread,confidence='Thermal and clock variation remains a limitation; no universal performance guarantee.'),
 pre_shadow_pairs=[['pd-a'+str(i),'pd-b'+str(i)] for i in range(1,4)],excluded_runs=['pd-trial-nanite','pd-trial-voxel','pd-clean-voxel','pd-clean-ao'],exclusion_reason='Material usage fallback or aborted shader compilation; superseded camera-selection runs also excluded from final comparison.')
(QA/'final-decision.json').write_text(json.dumps(d,indent=2))
accepted=dict(parallax=False,tree_mode='ao-voxel',tsr_thin_geometry_detection=1,shadow_mode='original_lod_proxy',owner_visual_acceptance='PENDING',status='bounded_review_candidate',observed_median_performance_gate_passed=passed,review='../Review/PerceivedDetail/index.html',rebuild='Art/rebuild_perceived_detail.ps1',scope='Asset rebuild only; requires the existing saved stand/map. Full-world regeneration is not integrated.')
(OUT/'accepted.json').write_text(json.dumps(accepted,indent=2))
print(json.dumps(d['performance_gate'],indent=2))
