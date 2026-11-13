"""Record observations and authoring data; preserve references and previous revisions."""
import json, shutil
from pathlib import Path

ROOT=Path('C:/GrandTour/Art/Export/VehicleTools')
OUT=ROOT/'shape-character-v01'
if OUT.exists():
    raise RuntimeError('Use a new revision; do not replace shape observations or manual work.')
OUT.mkdir()
BASE=ROOT/'reference-fit-v01'
obs=json.loads((BASE/'reference-observations.json').read_text())
for name in ['side-reference.png','front-reference.png','original-a-reference.png']:
    shutil.copy2(BASE/name,OUT/name)
shutil.copy2('C:/GrandTour/Art/References/Vehicles/BoardDerived_2026-09-30/00-user-source-board.png',OUT/'source-board.png')
features=[
 dict(id='rear_lower_tuck',region=[756,132,831,281],source='side-reference.png',
      observation='Below the belt shoulder, the rear body recedes toward the front as it approaches the underside; the tail is not a vertical slab.',
      evidence='Explicit user correction, supported by secondary side contour. Original A exposes only a narrow rear edge.',confidence='high direction / provisional amount',
      control='rear_profile_uv; shape key Rear lower tuck',review='registered side and rear-quarter'),
 dict(id='bumper_underturn',region=[779,220,834,269],source='side-reference.png',
      observation='Rear bumper projects beyond the body but its outer lower edge turns inward; its top ledge and bottom return have different depths.',
      evidence='User correction and secondary side view.',confidence='high direction / provisional amount',
      control='rear_bumper_uv; shape key Bumper underside return',review='side rear close-up and rear-quarter'),
 dict(id='bonnet_drop',region=[34,120,282,180],source='side-reference.png',
      observation='Bonnet rises gently toward the scuttle but rolls down more steeply over its short leading nose.',
      evidence='Original A front-quarter and secondary side agree on a dropped nose.',confidence='high',
      control='bonnet_crown_uv',review='side silhouette and front-quarter'),
 dict(id='bonnet_shoulders',region=[25,217,357,267],source='source-board.png',
      observation='A broad raised centre meets narrow shoulder terraces through oblique folds; the outer lip turns down over the wing.',
      evidence='Visible changes of plane in original A, top-left vehicle.',confidence='high structure / medium section depth',
      control='bonnet_section; shape key Bonnet shoulder relief',review='front and front-quarter under broad side light'),
 dict(id='roof_crown',region=[341,10,762,43],source='side-reference.png',
      observation='Roof has a shallow crown and eased front/rear transitions above a thin projecting gutter.',
      evidence='Original A shows cross-car crown; secondary side suggests longitudinal crown.',confidence='high crown / medium longitudinal amount',
      control='roof_crown_uv and roof_section; shape key Roof crown',review='side, front and top'),
 dict(id='cabin_taper',region=[25,115,502,279],source='source-board.png',
      observation='Cabin narrows above the body shoulder; screen pillars rake inward across the car and backward in side view.',
      evidence='Original A screen trapezoid and secondary front; camera remains uncertain.',confidence='high direction / medium amount',
      control='cabin_half_width_bottom/top; shape key Cabin inward taper',review='front plus both quarters'),
 dict(id='body_shoulder',region=[347,216,499,289],source='source-board.png',
      observation='A sloped ledge below the windows rolls outward into the broad side plane, rather than continuing as one flat wall.',
      evidence='Original A window-to-body transition and shaded side band.',confidence='medium-high',
      control='side_section_v_width',review='front cross-section and grazing-light quarter'),
 dict(id='sill_tuck',region=[222,232,563,287],source='side-reference.png',
      observation='Below the main side plane the body narrows toward the sill; the low trim follows the bend, not a separate square skirt.',
      evidence='Original A lower side and secondary end views. Exact width is inferred.',confidence='medium',
      control='side_section_v_width; shape key Lower side tuck',review='front/rear and low quarter'),
 dict(id='arch_shoulders',region=[57,180,731,285],source='side-reference.png',
      observation='Openings have a broad upper arc and angled lower runouts with a narrow rolled painted lip; avoid expedition flares.',
      evidence='Original A narrow lips. Secondary side used for initial arc locations.',confidence='high narrow lip / medium outline',
      control='front_arch_uv, rear_arch_uv and arch_lip_width',review='side plus quarter'),
 dict(id='window_rhythm',region=[281,34,780,139],source='side-reference.png',
      observation='Front, rear-door and cargo glass form unequal bays; cargo opening tapers into a wider rear sail pillar.',
      evidence='Original A; secondary side supplies provisional planar outlines.',confidence='high arrangement / medium ratios',
      control='window_profiles_uv',review='side and front-quarter'),
 dict(id='rear_upper_rake',region=[743,30,818,151],source='side-reference.png',
      observation='The upper tail slopes outward down to the belt; below the widest region the direction reverses into the lower tuck.',
      evidence='Secondary side plus user lower-body correction; original rear glazing is mostly hidden.',confidence='medium',
      control='cabin rear top/base and rear_profile_uv',review='side and rear-quarter'),
]
for f in features:
    f['status']='observed; geometry to be demonstrated; not user accepted'
mapping=dict(vehicle='Crafted Utility A',status='First case study, not a proven general recognition system',
    source_priority=['User corrections','Original user board, column A','Generated A multiview sheet (secondary/inconsistent)'],
    uncertainty='Pixel traces are artistic observations, not calibrated physical dimensions. Hidden surfaces and end-view widths remain interpretations.',features=features)
(OUT/'shape-map.json').write_text(json.dumps(mapping,indent=2))
s=obs['side']
spec=dict(schema='gt.shape-character.1',units='authoring metres; converted from approximate side registration',
    registration={k:s[k] for k in ['width','height','pixels_per_metre','axle_front_world','axle_rear_world','axle_z','front_hub_px','rear_hub_px']},
    bonnet_crown_uv=s['traces']['bonnet_silhouette'],roof_crown_uv=s['traces']['roof_crown'],roof_gutter_uv=s['traces']['roof_gutter'],
    side_top_uv=[[38,170],[113,164],[196,158],[274,151],[280,139],[470,138],[630,138],[809,136],[819,167]],
    side_section_v_width=[[136,.856],[151,.895],[170,.918],[235,.921],[253,.900],[278,.854]],
    longitudinal_width=[[32,.955],[78,.992],[142,1],[638,1],[763,.987],[819,.955]],
    front_profile_uv=[[38,170],[32,180],[32,229],[48,273]],
    rear_profile_uv=[[809,136],[819,167],[813,200],[809,223],[800,247],[783,263],[765,278]],
    front_arch_uv=[[57,276],[63,250]]+s['traces']['front_arch']+[[223,277]],
    rear_arch_uv=[[560,277]]+s['traces']['rear_arch']+[[725,273]],
    rear_bumper_uv=[[784,230],[813,225],[827,230],[826,253],[819,260],[783,268]],
    front_bumper_uv=[[32,229],[12,233],[10,252],[15,259],[29,266],[67,269],[71,242],[67,233]],
    bonnet_section=[[0,0],[.62,.001],[.72,.003],[.79,.026],[.92,.030],[1,.060]],
    roof_section=[[0,0],[.72,.010],[.93,.026],[1,.043]],
    cabin_half_width_bottom=.856,cabin_half_width_top=.767,roof_half_width=.798,
    cabin_bottom_v=136,cabin_top_v=40,cabin_front_bottom_u=280,cabin_front_top_u=350,
    cabin_rear_bottom_u=809,cabin_rear_top_u=755,
    window_profiles_uv={k:s['traces'][k] for k in ['front_window','rear_window','cargo_window']},
    wheel_half_track=.795,wheel_width=.240,tyre_radius=.392,arch_lip_width=.017,
    note='Interpretation from references. Geometry parameters are not factory measurements. Original A remains primary; do not claim side tracing resolves cross-view ambiguity.')
(OUT/'shape-spec.json').write_text(json.dumps(spec,indent=2))
(OUT/'reference-observations.json').write_text(json.dumps(obs,indent=2))
print(OUT)
