# Waimeamea place plan (L_LidarStudy)

Written 2026-10-16 after picking up GPT's LINZ LiDAR study. Companion to `docs/LidarStudy.txt`
(what is built, provenance, limits) and `docs/ProceduralGroundPlan.txt` (the authoring tool).
Goal: the owner's own land, drivable and recognisable from the road, not a generated screenshot.

## What we know and do not know

Known (registered, 2-5 m accuracy): the 1 m LINZ DEM of the whole block; OSM roads and river
name (Waimeamea River, Waimeamea Road, unpaved); the Esri aerial showing dense native bush on
the north and west, grazed paddocks with fence lines and dark shelterbelt rows in the south, a
pale 3-4 m gravel access road climbing north through the paddocks into the bush with one
hairpin, a small pond at the bend, lighter scrub strips along gullies, and the house with
sheds in a bush clearing at the road end. The river runs in a deeply incised bush gully west
and north of the house.

Ground level is now covered by ten owner photos in `Art/References/Waimeamea/` with the
reading in `NOTES.md` there: silver-beech type bush with dark mossy trunks and a massed
crown-fern and tree-fern understory; UTV-width peat-mud bush tracks; a 10-15 m tannin-amber
river over grey cobbles, fordable at hub depth, mirror pools and white riffles; bright grazed
paddocks with a rank-grass band at the bush wall; a timber house with iron roof, black iron
garage and gravel yard. Still missing: the hairpin, the pond, the gate and the fences.

## Faults seen on 2026-10-16 (captures, no drive yet)

1. Ponds and river render as flat matte slabs with a hard shoreline; GPT's polish pass had no
   visible effect.
2. Steep road sections (Field spur ridge climb) show faceted dark banks: the relief tiles
   interpolate the 1.8 m landscape resample and the authored 22 cm cut/fill cannot recover the
   real bench.
3. Open clearings carry dark zigzag marks in the overview capture; cause unknown.
4. One broadleaf tree look everywhere, no species, age or edge structure; the house is only an
   anchor point.
5. Play frame rate unknown; a cold check renders ~3 s per frame in the hidden editor.

## Stages

Each stage: Fable writes the brief, one Opus agent executes, one Unreal at a time via
`Art/lidar_place.ps1` (Install / Polish / Check) or a stage-specific ps1, captures at owner
angles (on foot, toward the sun, at joins, after repeat driving), then the owner drives. The
reference photos LEAD once they exist; until then stages marked (refs) stay provisional.

### LP0 — First drive and references (owner)
- Owner drives `Play-LidarStudy.bat`, keys 1-4, the whole 5.7 km, and names what is wrong in
  play (feel first, look second).
- Owner supplies the photos listed at the end. Phone shots, overcast is fine.
- Output: a verdict list that reorders LP1-LP5. Gate for everything below.

### LP1 — Road bench from the 1 m source
Problem: `Art/Export/LidarStudy/height.r16` is a 1.835 m resample; the road bench is 3-4 m
wide and survives in the 1 m DEM but not in the landscape. The relief tiles (50 cm spacing)
only interpolate the landscape, so steep sections become side slopes with a 22 cm bed cut.
- Verify first: cross-sections from `dem.npy` at ten stations (gate, paddock straight,
  hairpin, pond bend, ridge climb, house approach) to confirm the bench is actually in the
  1 m data. If it is not, LP1 becomes an authored cut/fill profile instead.
- Preferred build: `prepare_lidar_place.py` writes a 1 m corridor height texture (road
  mask ±6 m, blended to the landscape at the edge); `GTProceduralGround::CaptureBase` honours
  it inside the corridor so every relief tile carries the real bench. Rejected: re-importing
  the landscape at 1 m (4097² everywhere for a 4 m road).
- Keep the recovered MudRunner 2 m sampling, 2 m shoulders and crown on top of the bench.
  Inside bank gets a cut-face soil (clay, roots); outside edge gets fill.
- Checks: cross-slope < 3° at all four sites and along 95% of the corridor; tile count and
  triangle count unchanged; existing GTProceduralGround oracle checks still pass.
- Gate: owner drives the hairpin and the ridge climb; captures from the driver's eye and on
  foot at the cut face.

LP1 status 2026-10-16: BUILT, three rounds. Round 1 (discrete bench runs, +-8 m) and round 2
(tracked runs, Viterbi) still failed Riverside access (p95 7.9 then 6.3 deg, max 22 deg: clipped
wide benches, flip-flopping candidates, one gully with no bench). Round 3 passed: continuous
offset path (-12..+12 m at 0.5 m, cost = car-track cross-slope + 0.15/m from the digitised
line, drift <= 1 m per 5 m station, ends pinned), private cut/fill 22 -> 60 cm, Install skip
test now a digest of roads/sites/trees. Corridor (car track, degrees): Riverside access
p95 1.84 max 7.36; Pond field spur p95 4.65 max 8.94; Waimeamea p95 0.71 max 10.25 (its end
station at the private junction, the one spot to watch); Waterhouse p95 1.26. All four sites
level. Lines moved a mean 4.9 m (Riverside) and 2.6 m (spur), never more than 12 m. Field spur
capture: the sawtooth banks are gone, the bed climbs the ridge smoothly, one small dark cut
remains near the crest. Gate: owner drives the hairpin and the bush climb.

### LP2 — Water that reads as water
- Diagnose before changing anything: the cloned `M_<patch>Water` materials, the MID-of-MID
  warnings in the check log, and whether the ambient wave render target reaches the three
  static-mesh surfaces. One eye-level capture at the pond and at the river beside the house
  after every change; no top-down judging.
- Target look (photos 03-07): tannin amber water, clear over an orange-brown cobble bed in
  the shallows, tea-dark mirror pools with full tree reflections, white broken water on
  riffles, current along the flow texture; grey cobble bars and sand patches at the edges
  with moss and logs; banks of crown fern and tree fern over the water. Shoreline is a
  depth fade over the cobble bed, never a hard edge. The river must be fordable at hub
  depth with the bed visible through the water.
- Gate: owner drives to the pond bend and the river by the house.

LP2 status 2026-10-16: binding fixed, pond right, river open (LP2b running). Root cause of the
flat slabs in the check captures: AGTWaterSheet::BindWaterWindow wrapped a surface's existing
dynamic instance (left by the editor-side preview and copied into PIE, DomainMaterials being
Transient) in a second instance with no valid parent, so the surface drew the default
material; in the owner's play path the water already reflected. Fix in GTWaterDomainSheet.cpp:
reuse the sheet's own instance, rebuild any other from its parent, never wrap. New
lidar_place.ps1 modes WaterDiag (eye-level captures to Place/water/) and Water (re-runnable
look pass: tannin colours, roughness .02 pools, turbidity .1, foam gated to riffles, warm
colour behind water). Pond capture: tea-dark mirror, tree reflections, soft amber shallows.
River capture: a sheet 3 m above the valley floor with trees in it, because prepare's river
surface follows the priority-flood filled profile (pools up to 4.6 m deep) and the tree
exclusion is a 9 m line buffer while the water spans 20 m. LP2b (built, two rounds): channel bottom = min of the 1 m DEM within +-12 m, 21 m mean,
depth 0.3-1.2 m with a 20 cm floor over the raw bottom, surface may not rise downstream faster
than 2 cm/m, depth capped at 1.5 m, trees and understory excluded by the actual wet mask plus
1.8 m, flow 0.3-1.5 m/s from the surface slope (riffle gate open on 27% of wet cells, no pools),
rock/wet style under the water. Result: the river sits in a channel, no trees in it, soft
edges, continuous except 17 dry stretches >= 10 m where the DEM channel bottom humps 0.6-3 m
above both neighbours (listed in prepare.json water[River].dry_stretches; five within 300 m of
the house, the nearest 30 m long at 79 m). Those need the owner: log jam, culvert, bridge, real
drop or DEM artefact, then LP2c either carves the channel through the landscape or steps the
surface. Still wrong in the captures, for the next water pass: heavy sparkle noise on the
surface, the painterly rock bank reads as marbled slab not cobbles, no cobble bed material
exists, two straight orange lines cross the water near the house (unexplained). Sky light: owner chose 1.5
(2026-10-16, from the 8.0 vs 1.5 capture pairs); water_lidar_place.py sets it on the saved level,
so it survives a re-install as long as the Water pass re-runs.

### LP3 — Bush with the real character (photos 01, 08, 09, 10)
- Canopy: tall straight close-set trunks with dark mossy bark (no white-barked birch look),
  high small-leaved crowns, wind-shaped at edges, bleached dead spars above the canopy and
  at margins. Pole stands (dense thin trunks) along tracks and edges.
- Understory: massed crown fern knee to waist high everywhere under the canopy, tree
  ferns scattered through it and thick at gully and river edges; almost no shrub layer
  inside the stand; coprosma and small scrub only at the bush margin and on cut banks.
- Ground: black peat, roots, moss, fallen branches, puddles; bush tracks are UTV width
  peat mud with ferns to the edge.
- Bush edge against pasture: a dense dark wall to the ground with a band of rank grass and
  scrub in front.
- Existing assets first (OW DressingLab trees re-barked and re-crowned, shrub library,
  dense tussock); new Blender assets for crown fern and tree fern, which we do not have.
- Gate: on-foot look at the bush edge by the hairpin and from the track at speed, judged
  against photos 01 and 08.

LP3a status 2026-10-17 (foliage perf prep, Sonnet session): NEGATIVE RESULT, rolled back, level
unchanged, Check passes. Splitting the forest and understory into 64 m HISM cells raised draw
calls from ~1,800 to ~8,600 and occlusion queries from ~90 to ~5,000; hidden-editor GPU time
went from 23-30 ms to 54-69 ms at the four sites. UE 5.8's GPU scene already culls ISM
instances individually, so the split only adds components; do not do it. The flag set alone
(ray tracing off, distance-field and dynamic-indirect off, VSM cache rigid, LOD2 canopy shadows
off) measured 3-4 ms slower against a repeat baseline that itself varies 1-2 ms; the flags were
not separated, so which one costs is unknown. New re-runnable modes FoliagePerf
(Art/Unreal/foliage_perf_lidar_place.py, env GT_FOLIAGE_CELL_CM / GT_FOLIAGE_CLASS /
GT_FOLIAGE_FLAGS; its default applies the flags, which measured slower) and FoliageStat
(Art/Unreal/stat_lidar_place.py, per-site GPU/game/render ms via the CSV profiler). Baseline
to beat, hidden editor 1440x900: GPU 23.0 / 22.6 / 27.9 / 27.2 ms at Access entrance / Pond
bend / Riverside house / Field spur. Lesson for LP3 and LP6: measure in play on the owner's
machine, change one thing at a time, and treat anything under 2 ms as noise.

LP3 status 2026-10-18: PLACED, look gate not met, LP3b running. The kit is on the map: canopy
144,498 trees as SM_Canopy_0..3 (Beech_Mature 41k, Beech_Pole 96k, Beech_Edge 5k, DeadSpar
2.7k; kit LODs plus a baked 6-triangle card from 120 m) in /ArtTests/LidarStudy/CanopyKit;
understory 101k by mesh name in a near band (35 m of roads, 60 m of sites, 40 m of the house)
at 1.8 m and a far regime at 12 m: crown ferns 72k, tree ferns 7k, litter, hummocks, logs,
stumps, kiokio by the river, margin scrub (coprosma, gorse, broom, tussock) and flax and
tussock by the house. Corridor, sites and water unchanged, check passes. Fable's look at
Bush_track: a sapling plantation on orange clay and bright grass, not photo 11: pole crowns
too small for the 8 m grid (42% cover), ferns too sparse for their size, floor painted as
grass under the canopy, kit greens read lime under this light, dead spars glow white. LP3b:
5 m grid in the near band with mature/pole clumps (target 60-75% cover), fern spacing 1.0 m
with bigger ferns, floor style under the forest mask cut to dark wet peat, tint instances if
the kit materials expose a parameter. FoliageStat before/after unusable: the owner's game was
on the GPU; draw calls +11-25%, components 6 -> 31.
LP3b result 2026-10-18: canopy 147k (mature 69k, pole 70k, edge 5.6k, spar 2.1k), crown cover
67%; understory 164k (near band 90k at 1.0 m, 66k crown ferns B/C-heavy); Bush_track much
closer (sky 40% -> 22%, trunks dark and close-set, ferns continuous to the edge); House_yard's
bush wall now a closed mass. New fault: the floor under the canopy is terracotta (25% orange
pixels in the overview) because M_Terrain reads only style R sand, G grass, A rock, never wet,
so cutting grass exposed raw dirt; and the kit materials have no tint parameter. LP3c: a peat
term in the LiDAR ground material clones driven by style wet and grass, a Tint parameter in
M_NZ_Foliage/M_NZ_Bark with darker instances on the fern/litter components and the spars.
Note for CL1: style R is the sand slot in M_Terrain; on this map clay takes that slot.
LP3c result 2026-10-18: peat term in the LiDAR M_Terrain/M_Detail clones (style wet > .55, not
grass, not river rock; linear peat .045/.034/.024 with three-octave litter flecks fading with
distance); Tint VectorParameter added to M_NZ_Foliage/M_NZ_Bark (importer add_tint, no mesh
re-import); MI_NZ_Foliage_Bush (.62,.70,.60) on ferns, litter, hummocks, tree-fern fronds and
kiokio; MI_NZ_Bark_Spar (.42,.40,.38) on the spars and their far card. Overview: orange floor
gone (bright orange 9.1% -> 0.1%), no tile pattern, spars gone, paddocks unchanged. Bush_track:
ferns 15% darker but still saturated green; stand still thin poles with sky through small pale
crowns; track still orange (clay, CL1). LP3 held here at the owner gate. For the plant kit, not
this map: beech crowns need larger, denser clusters for a closed canopy, and crown-fern green
needs to move grey-green (photo 11); tree ferns read as palms at distance.


LP3d status 2026-10-18 (grass, Sonnet, ~0.24M): pasture_patch in the ground clones (style G >
.8, no clay, no peat: linear (.085,.21,.045) with 2.5 m / 0.4 m noise and 8% mown patches),
LidarCoverTint (.70,1,.55), M_LidarGrass GrassBaseTint (.48,.88,.42), distance Diffuse
(.60,.95,.55), Paddock_middle capture. Tan patches gone, pasture green to the fence; but
Paddock_middle reads neon lime, flat, with a regular lattice of distant tufts, and the gate
view is still dark olive; no straw-headed rank band appears. Hard limit found:
GTMixedGroundDetails exposes only GrassSpacingCm (C++ clamps 45-100 cm, already 45), card
scale is hard-coded (near XY .95-1.6, Z .7-1.2), cards keep with probability min(1, 1.5 G).
LP3e (after NP5): C++ lower the spacing clamp to 30 cm and add BladeScale and a style-G straw
tint for the rank band; pasture warmed to about (.12,.21,.04), cover tint (.85,1,.7), near
cards brighter; measure the card cost at 35 cm spacing in play.
NP5 landed 2026-10-18 (see docs/NATIVE_PLANT_KIT_PLAN.md): canopy closed on the bush side of
the track, bush wall continuous from the house; lit leaves still bright and angular, so LP3e
also puts a darker tint instance on the canopy foliage slots.
LP3e status 2026-10-18 (Sonnet, ~0.26M; build 41 s, 0 errors): GTMixedGroundDetails gained
BladeScale (.5-1.5) and RankBandScale (1.4), the GrassSpacingCm floor is 30 cm, near cards
carry a 4th per-instance float Straw (band where style G is .3-.8) read by an LP3eStraw node on
M_LidarGrass; this map: spacing 35 (near cards 1.65x, +0.1 ms editor frame), BladeScale .8,
pasture (.12,.21,.04), cover tint (.85,1,.70), GrassBaseTint (.52,.82,.36), distance diffuse
(.62,.88,.46); MI_NZ_Foliage_Canopy (.55,.62,.50) on SM_Canopy_0..2 and their far cards.
Fable's look: Paddock_middle reads as dense grazed pasture to the fence with the bush wall
behind (a little hotter than photo 09); Bush_track reads as a dark closed canopy, massed crown
fern to the edge, tree ferns, wet grey clay track between banks (close to photo 11). Open:
the straw rank band is invisible (a multiply, needs a lerp toward tan, and the G .3-.8 band is
only 2-4 m wide), distant tufts still a lattice at range, leaf silhouettes angular (kit asset),
tree ferns read as palms. GATE: owner drives.


### LP4 — Paddocks, fences and the house clearing (photos 02, 09; fences and pond still unseen)
- Pasture: bright grazed green with a rank seed-head band along the bush wall; fence lines
  digitised from the aerial as splines (post-and-wire actor, gates where the road crosses),
  provisional until the owner photographs them.
- House and garage as simple massing at the surveyed anchor from photo 02: timber
  weatherboard house with a light iron roof and wraparound deck, black iron garage with a
  roller door, gravel yard, lawn, flax and tussock clumps on the bank. No invented detail
  beyond the photo.
- Pond edge provisional until photographed.
- Owner rule 2026-10-18: "the 3 paddocks are just grass": inside the three paddock polygons
  nothing but pasture (no scrub band, litter, tussock, rushes, thistle, trees); fences on
  their boundaries, gates where the track crosses, a cattle stop at the Waimeamea Road
  entrance; the clay track still crosses them.
- Gate: owner recognises the place from the gate and from the house.

### LP1b — Clay and gravel road surfaces (owner 2026-10-17)
- Public roads (Waimeamea, Waterhouse) are grey river gravel: a gravel surface with a crown,
  loose shoulders, two worn wheel lines and a sparse grass centre strip, using the project's
  deformable gravel response (docs/DEFORMABLE_GRAVEL_PLAN.md) on the corridor.
- Private roads and the bush climbs are clay where cut (photo 10's orange cut bank) and peat
  mud under the canopy: a clay condition on the cut-bank stretches and the paddock track, mud
  on the bush track; the register_to_bench corridor knows where the cut faces are (chosen
  offset against the DEM profile), so clay goes on cut faces and the climbs automatically.
- Corrected by photos 11 and 12 (2026-10-17): the private track is bare clay, not gravel,
  with two wheel ruts and a rank grass centre strip in the open; the bush climb is a churned
  grey-brown clay slurry with sharp rut walls, tree-fern skirts and crown fern to the edge;
  open ground near the hut is a bare clay yard with puddles. Only the two public roads carry
  gravel. Orange clay shows on cut banks.
- Road conditions in prepare carry the surface class; GTRoadCondition gets a clay weight once
  CL2 exists. Gate: owner drives the gravel straight, the hairpin and the clay climb.

LP1b + CL1 status 2026-10-18: BUILT (Sonnet, ~0.46M tokens). The clay weight is NOT in style
R: the C++ reads style R as sand (granular on, native mud off, cohesion down) and
AGTProceduralGround::Rebuild lerps style R to 0 in every road corridor. It travels in a new
atlas Place/clay.png -> T_clay (R clay weight, G orange cut face where the DEM is steeper than
24-40 deg, B bush slurry). Track corridor 14.0k m2, yard 1.2k m2 (minus the 12 x 8 m house
rectangle, forest and river), cut band 3.1k m2 (246 of 337 Riverside stations), orange 652 m2.
Grass cleared in the yard and on orange cells. Materials: two wrapper custom nodes CL1Colour
(dry crust .34/.27/.17 with a crack network, wet .20/.14/.08, bush slurry .18/.15/.12, rut
darkening from paint depth, orange on the G channel) and CL1Rough (roughness toward .25 where
wet > .6) in M_Terrain and M_Detail; the peat patch untouched. Conditions: Riverside access
Clay track 0-438 / Clay slurry 414-648 / Clay track 624-758 / Clay slurry 734-1696 plus the
Damp hollow; Pond field spur slurry / track / slurry; public roads Firm gravel. Check passes
(Riverside p95 2.54, spur p95 4.58 close to the 5 limit). Look: Clay_track_open reads as pale
crusted clay (best match to photo 12) but without the two ruts and grass centre; Bush_track is
dark glossy blue-grey wet clay with a sheen but no rut walls or lumps (smooth apron, wider
than a UTV track); the yard reads as pale sand (no puddles, no ruts). Those three are
deformation and condition effects for CL2, not paint. Orange never fires visibly.

### CL1-CL3 — Deformable clay (owner 2026-10-17; builds on the mud and gravel soil work)
- CL1 Clay material (photos 10, 11, 12): pale tan to ochre with a cracked crust when dry,
  dark brown and glossy with standing puddles when wet, grey-brown slurry with sharp rut
  walls on the bush climbs, orange only on fresh cut banks; with the painterly dab layer; a
  clay weight in the style masks on the whole private track, the yard, cut banks and climbs.
- CL2 Clay soil response in the mud contact model: high cohesion, firmness that falls steeply
  with wetness, low wet friction (slick), ruts that hold their shape and do not slump back,
  little clod throw, smearing spray. Parameter study on L_MudVariants first, then the LiDAR
  map; feel judged by the owner against driving a wet clay track.
- CL3 Clay and gravel road conditions on the LiDAR map (LP1b) with the owner's drive as gate.

CL design (2026-10-17, from the code): the soil shear state (GTMudContactModel FState: wetness,
cohesion, disturbance, compression, granular) is filled per contact from the surface sample,
whose Wetness and Cohesion come only from the authored mud regions' shape (ShapeAt R/G); the
LiDAR map has no regions, so clay needs a mask: the style atlas red channel, unused today,
becomes the clay weight (prepare writes it on the private corridor, the yard and cut banks).
SampleSurface then takes Cohesion = max(region, .9 x clay) and Wetness = max(region, clay x
the paint wet channel), and enables the shear state where clay > .5. On this map the active
contact path is the native substance (bNativeSubstanceResponse): clay gets its own per-contact
substance numbers from the sample (dry: friction 2.2 -> 2.0, push resistance 36 -> 50, linear
resistance 10 -> 16; wet: friction -> 1.0 through the sample's FrictionScale, push resistance
-> 42) so it is slick when wet and holds ruts. Rut retention: the field's per-cell decay
(DecayingCells) is scaled by (1 - clay) so clay ruts do not recover. Clod throw and spray use
the smear variant. The clay material reads the same channel: dry crust (.34,.27,.17) with
cracks, wet (.20,.14,.08) glossy with puddles in the rut floors, bush slurry (.18,.15,.12),
cut banks (.42,.22,.08). Feel is proven on L_MudVariants with one clay section (dry, damp,
wet) before the LiDAR corridor, judged by the owner.

CL2 status 2026-10-18: BUILT (Sonnet, ~0.38M tokens; build 59 s, 0 errors). The surface carries
the clay atlas (ClayCells 8-bit, ClayAt/ClayWeightAt/HasClay; regions gained ClayWeight;
ImportClayAtlas in the setup library). SampleSurface: cohesion lerp(.5,.92,clay), granular off
and shear state on where clay > .5, native friction/linear/push blend from mud defaults
(2.2/10/36) to clay dry (2.0/16/50) and wet (1.0/14/42) between wetness .45 and .6, tyre grip
scale .55 when wet (applied through ClayFrictionScale on the soil path, which was the only
place the sample's FrictionScale could act). Rut retention: the field's decay loop only decays
Fresh and Turbidity (cosmetic); no code anywhere recovers rut depth, so clay's 'ruts hold' is
expressed only as 0 decaying cells on clay versus ~24k elsewhere. LiDAR read-backs: open track
clay 1.0 / friction scale .87 / cohesion .92 / wetness .45; bush climb 1.0 / .43 / .92 / .90;
public road 0 / .94 / .5. L_MudVariants gained a ClayLane (dry .3, damp .5, wet .8) with a
control: slipping share rises with wetness on clay (.39 -> .49 -> .58, flat on the control),
speed 0.6-1.6 m/s above the control (push resistance 50 makes it firm and fast, not sticky),
rut depth equal across thirds (softness equal), lateral slide untested (flat lane). Look of the
clay lane unchecked. Gate: owner drives the LiDAR bush climb wet and the ClayLane, and says
whether wet clay should also be stickier (raise wet linear resistance) or deeper.

### LP7 — Level adjustment guide (owner 2026-10-17, after the gates)
`docs/LIDAR_LEVEL_GUIDE.md`: how to move or add a road (aligned-features, prepare, Install),
change a site, change road conditions, add or remove a water patch, swap or re-tint a plant
layer, re-run Install / Polish / Water / Check, where every number lives, and what never to
edit by hand because a script regenerates it. Written once the map passes its gates, so it
describes the final pipeline rather than a moving one.

LP4 status 2026-10-18: BUILT (Sonnet, ~0.40M tokens). Farm set imported (11 meshes, hulls as
manifest). Paddocks found from the registered aerial (pasture colour), not the OSM masks (the
NE field is 81% "scrub" in OSM and all open ground joins into one region): NE at the Pond spur
3.98 ha, the square west of the lane 3.50 ha, the oval east of the lane 2.44 ha (a 3.4 ha west
field 70 m off the road was not taken; candidates in Place/paddocks.json). Inside them: grass
.95, no understory (751 removed), no trees (29 removed), clay only on the track. Hardware 594:
534 fence modules, 33 strainers, 3 gates (one per paddock at its nearest approach to the lane;
no road crosses a paddock boundary), 1 cattle stop with 12 m wings at the Waimeamea junction
plus letterbox, name sign and give way, 7 culverts on drainage crossings (accumulation >= 4,000
m², headwall uphill, mouths buried since the terrain is not carved), 7 power poles on the open
stretches, 3 troughs, 3 bales. LidarStudy_Farm ISM components with hull collision. Check passes;
corridor and sites unchanged. Fable's look at Paddock_gate: reads as a NZ farm gateway, wires
readable, plain grazed paddock to the bush line; grass dull olive with bare patches, bush line
thin (kit crowns), gate a little pale. Overview: the oval paddock still carries the LP5 zigzag
scars. Gate: the owner's drive through the entrance and the gates.

### GP1-GP3 — Grass that is cheap and reads as pasture (owner 2026-10-18: "not happy with the
grass, visual and performance wise")
Diagnosis: GTMixedGroundDetails draws single cards around the player (near cards on a spacing
grid, distant cards beyond) with a per-card colour; at 35 cm spacing the paddocks need 1.65x
the instances of 45 cm and still read as a dotted lattice with a neon flat colour, and every
card is a shadow-casting, wind-moving instance that invalidates virtual shadow map pages.
Photo 09: grazed pasture is a dense yellow-green mat, no visible individual tufts beyond a few
metres, a straw-headed rank band only at the bush wall.
- GP1 Clump meshes (Blender, kit pipeline): SM_NZ_PastureClump_S/M/L (25/40/60 cm across,
  12/20/30 blades, 2 LODs: full and a 6-blade cross), grazed short (8-14 cm), vertex colour
  dark base to lighter tips, yellow-green; SM_NZ_RankClump_A/B (50/70 cm, taller 30-45 cm,
  with 6-10 seed heads, straw tints) for the band. Budgets S/M/L <= 120/200/300 triangles,
  rank <= 400. No collision.
- GP2 Engine and placement: GTMixedGroundDetails gets a clump mode: a mesh set per cover
  class (pasture S/M/L by a per-clump noise, rank A/B in the G .3-.8 band), spacing 65 cm in
  pasture (about 3.5x fewer instances than 35 cm cards), per-clump yaw and scale noise so no
  grid shows, cull at 45 m with a dithered fade, no shadow casting beyond 15 m (a second
  shadow-free component for the outer ring), ShadowCacheInvalidationBehavior Rigid, wind only
  in the inner 20 m; the distant-card layer OFF inside the three paddocks (the ground
  material's pasture colour plus a clump-shadow speckle noise carries the look beyond 45 m)
  and ON only in the verge and rank bands. Palette from photo 09: base (.11,.19,.035), tips
  (.26,.34,.09), straw lerp (not multiply) toward (.42,.36,.16) in the band; 15% desaturation
  on the ground pasture colour. A console toggle gt.Grass.Clumps 0/1 to A/B in play.
GP1 status 2026-10-18 (Sonnet, ~0.32M): five meshes built, validated (NATIVE_VALIDATION_OK 10,
two LODs each) and imported: PastureClump_S/M/L 90/149/225 tris (LOD1 18/30/42), RankClump_A/B
288/388 (58/74), vertex alpha 0 at the base to 1 at the tip (survives the FBX round trip;
not readable in the Unreal Python API), bases 2 cm below ground. Agent's look at
Assembly_Pasture: a sparse scatter of dark tufts on a pale plane, no mat (clumps cover about
2-4% of the ground at 65 cm), colour muted sage; the rank band reads as photo 09's straw-headed
band. The mat has to come from the ground material (GP2's pasture colour) with clumps as
texture, which is the design.
GP2 landed 2026-10-18 (Sonnet, ~0.28M; see the agent's GP2 status paragraph): clump mode behind
gt.Grass.Clumps (default 1), PastureClump_M at 65 cm with a RankGrass component (RankClump_A at
78 cm in the G .3-.8 band), distant cards skipped where G > .8, LOD1 at 12 m by an instance
LOD distance scale, M_LidarClump/M_LidarRank vertex-colour clones of the card material.
Access entrance: 3.2k near + .65k rank + 2.5k distant = 6.3k instances against 38.4k with cards
at 45 cm. Fable's look at Paddock_middle: a smooth bright mat with no lattice (the right base),
clumps sparse tiny straw-yellow sprigs, ground too smooth and lime up close. GP2b (numbers):
spacing 45, the L clump, tint (.78,.92,.62), ground noise 35% at 0.4 m plus a 0.12 m micro
octave within 12 m, colour (.11,.20,.045).
GP2b landed 2026-10-19 (Sonnet, ~0.15M): spacing 45 (rank 54 by the 1.2x rule), the L clump, tint
(.78,.92,.62), ground (.11,.20,.045) with three noise octaves (2.5 m 24%, 0.4 m 35%, 0.12 m 15%
within 12 m). Near clumps 2.1x GP2 (Access entrance 6.7k near + 1.3k rank + 2.5k distant =
10.5k against 38.4k cards). Look: clumps now read as green grass clumps with yellow tips, no
lattice, a little texture within 5 m; the mat beyond is still smooth, darker (value .50 vs the
photo's .64) and less yellow (R/G .83 vs .95). Remaining levers are two numbers in
install_lidar_place.py pasture_patch (raise pasture red toward R/G .95 and brightness) and the
40 cm spacing floor; left for the owner to set in play.
GP2c landed 2026-10-18 (Sonnet): owner on the GP2b ground "It still doesn't look that good" (screenshot Art/References/Waimeamea/13: blotchy noise carpet, HUD sink 14.6 cm).
(1) Firm paddocks (prepare): paint depth 7.60 cm -> 1.51 cm and firmness .205 -> .898 inside the three paddocks off the track (30,276 cells; the 32 track cells keep their paint). The brief's 2 cm gave
4.86 cm at the NE trough because SampleSurface multiplies the atlas depth by the surface's LayerDepthScale 2.48, so the atlas depth is 1.5 cm (1.57 after the 8-bit byte) and sinkage_cap_cm is 3.89 there (Check asserts <= 4).
(2) Tiled pasture (Install): the GP2b noise octaves, the pasture and mown colours and the 15% desaturation are gone from the colour program. New wrapper node GP2cPasture sits between the program and CL1Colour
(peat keeps priority via 1-peat mask, clay and the rock mix and the cover tint still follow): T_Landscape_Grass_01_A at 1.5 m blended 35% with itself at 5.3 m (rotated 29 degrees) times a 12 m +-8% brightness octave
(hue never), tint measured from the tile (Grass mean linear .0903/.2307/.0306, display R/G .642 V .518) as (3.1826,1.2817,2.3160) so the final albedo after the downstream cover tint (.85,1,.70) lands on display
(.534,.580,.249) = R/G .92 value .58; T_Landscape_DryGrass_01_A (mean display .740/.548/.228) at 25% in the 8% mown patches and 60% in the rank band, own tint (.8441,1.0919,2.5096) to a straw (.66,.57,.33).
Texture samples are TextureSample nodes on the shared wrap sampler. (3) Normal: GP2cNormal wraps the Normal property's input, T_Landscape_Grass_01_N at 1.5 m, 50% within 20 m fading to 0 at 40 m, pasture only, off the clay.
(4) Check: sinkage assert at the trough, Paddock_chase (car 11 m +X of the trough, 5 m up / 9 m behind, 25 degrees down, FOV 68; the brief's +6 m put the car on a hay bale), GP2c material readbacks. Install digest now includes the
atlas PNGs (a paint-only prepare change used to leave the stale atlas in the saved level). Look: blotches gone (48 px block-mean luminance spread .020 against .047 in the owner's screenshot), fine blade-scale texture, no visible
repeat at the chase distance; render colour R/G 1.03 and value .52 near / .58 mid / .64 far against the photo's .945 / .66: yellower and a little darker than the photo, so the lever is the two target triples in install_lidar_place.py
(GP2C_TARGET_DISPLAY grass; (.546,.65,.28) would aim the render at the photo). HUD-equivalent sink at the chase spot 6.4 cm (14.6 cm in the screenshot), above the 3.9 cm cap because the wheel yield model adds support and load terms and
paint softness .53 is untouched. Captures before: Place/before_GP2c.
GP2d landed 2026-10-18 (Sonnet, numbers only): (1) pasture target GP2C_TARGET_DISPLAY grass (.5336,.58,.2494) -> (.546,.65,.28), tint (3.1826,1.2817,2.3160) -> (3.3459,1.6474,2.9146) against the measured tile (mean linear .0903/.2307/.0306); render now R/G .94-.98 and value .55 near / .62 mid / .67 far (was 1.04-1.05, .51 / .62 / .64): a fresh yellow-green, no longer ochre.
(2) Turf softness: prepare paint channel 3 .53 -> .22 in the paddocks off the track (PAD_SOFT; trough softness .2196), and PAD_DEPTH_CM 1.5 -> 1.0 (trough sinkage_cap_cm 3.89 -> 2.43). The chase-spot worst-wheel sink did NOT move: 6.4 cm (GP2c) -> 7.5 cm (softness .22, depth 1.5) -> 6.4 cm (depth 1.0); the other three wheels sit at 5.5-5.8 cm in every run.
The HUD number is the traction component's own Wheel.Sinkage (GTTractionComponent.cpp PatchSinkage: the Grass surface type's MaxSinkage, WetSink and the soft-spot scale), not the landscape paint, so paint depth and softness cannot get it under 3 cm; the lever is the Grass surface's MaxSinkage / SinkageRate (data or C++).
(3) Clumps: CLUMP_TINT (.78,.92,.62) -> (.88,.96,.60), ClumpSpacingCm 45 -> 40 (the C++ floor): near pasture clumps x1.26-1.27 (Access entrance 6687 -> 8518, +1732 rank). Captures before: Place/before_GP2d.
- GP3 Measure in play on the owner's machine: stat unit and stat gpu at Paddock_middle and
  Access_entrance with gt.Grass.Clumps 0 and 1, and with grass off; target: clumps cost no
  more than half of what the 35 cm cards cost. Then the owner's look at the same spots.

GP2 status 2026-10-18: BUILT (Sonnet). GTMixedGroundDetails clump mode behind gt.Grass.Clumps (default 1; 0 =
cards at GrassSpacingCm 45): Grass streams SM_NZ_PastureClump_M on a 65 cm lattice, new RankGrass streams
SM_NZ_RankClump_A on 78 cm where the band weight is over .2, distant cards skip G over .8; LOD1 at 12 m by an
InstanceLODDistanceScale derived in C++ from the mesh's own LOD1 screen size (no mesh edit). M_LidarClump
(tint .95,.92,.80) / M_LidarRank (1,1,1): clones of the card material with the mesh vertex colour in place of
the diffuse texture and no texture alpha; ground pasture colour 15% desaturated. Check passes: near/rank/distant
Access entrance 3194/652/2490, Pond bend 1655/399/3077, Riverside house 574/465/782, Field spur 1967/586/2537
(cards at 45: 8122 near + 30301 distant at the first site). Hidden-editor frame times show no difference
(22.3 / 24.0 / 26.0 ms clumps / cards / clumps again; drift larger than the effect), so GP3 on the owner's
machine is still the measure. Look: no lattice and a smooth warm mat of colour, but the clumps are sparse thin
straw-coloured sprigs on it, not a dense tufted mat; the levers are ClumpSpacingCm (45 to 50), the L mesh, and
the vertex-colour value or the tint (the tips read straw-yellow, the dark base is hidden). Captures before: Place/before_GP2.

### GP4 — Dense grass (owner 2026-10-19, references Art/References/Grass/01-03: "This is what I want")
The clumps-on-texture approach (GP1-GP2d) is replaced in the paddocks by full-coverage grass
geometry: near the car the ground is not visible between blades, the grass waves, and it fades
at 30-40 m into a ground colour matched to the grass tips so no edge shows (reference 03).
- GP4a Patch meshes (Blender, kit pipeline): SM_NZ_GrassPatch_A/B/C, a 70 x 70 cm patch of
  120-160 thin blades (2-3 triangles each, opaque, no alpha) 25-45 cm tall with 15% clover and
  3% flower heads, three variants, vertex colour dark base (.05,.11,.02) to bright tip
  (.30,.40,.10), vertex alpha 0 base to 1 tip for wind weight; LOD0 <= 420 tris, LOD1 <= 130
  (every third blade, widened), LOD2 <= 24 (a six-card cross); byte-stable; no collision.
- GP4b Placement and look: clump mode with PastureClumpMesh = the patch, ClumpSpacingCm 55
  (patches overlap for 100% coverage), per-patch yaw and scale .8-1.25, LOD1 at 10 m, LOD2 at
  22 m, cull 38 m with the material's distance fade; wind amplitude in the material from the
  vertex alpha; the contact program bends and removes whole patches under the wheels; the
  rank band keeps the RankClump; the pasture ground colour under and beyond the patches set
  to the patch's rendered tip colour measured in the capture so the 38 m fade is invisible;
  gt.Grass.Clumps 0 still restores cards for the A/B. Cost: expect about 10k patches within
  38 m; measure with FoliageStat as a coarse check and the owner's stat unit as the real one.
  If play cost is too high the levers are spacing 65, LOD1 at 7 m and cull 30 m.

GP4 status 2026-10-19: BUILT (GP4a Sonnet ~0.27M, GP4b Sonnet ~0.46M). Patches SM_NZ_GrassPatch_A/B/C:
70 cm, 130 blades (106 grass, 20 clover, 4 flower), blade width 10-16 mm (the first 5-8 mm build
left 26% ground visible mid-frame; doubling the width took it to 5%), 414/108-117/24 triangles,
mean tip height 28 cm, vertex alpha base 0 to tip 1. Engine: three pasture components (A/B/C by
hash) with per-component contact state, ClumpStreamRadiusCm 4000, GrassCullStart/End 3000/3800,
LOD1 at 10 m, LOD2 at 22 m (via the LOD2 screen size .1591 set on the meshes), scale .8-1.25,
spacing 55. Material: GP4Dither fades on PerInstanceFadeAmount (no pop), GP4Wind weights the
recovered wind by vertex alpha, wind scale 2. Distance match: ground target (.537,.637,.272),
no ring at the fade. Counts: Access entrance 7.6k near + 1.2k rank + 2.5k distant; paddock
interior 16.6k patches within 38 m (the heavy case; levers spacing 65, LOD1 at 7 m, cull 30 m).
Hidden-editor GPU +1.2 to +4.7 ms per site (coarse). Fable's look at Paddock_chase: a continuous
dense fine-bladed yellow-green carpet, no ground between blades, car sitting in it, smooth fade:
reference 03's look; shorter and more uniform than reference 01 (no sweeping 50 cm blades,
clumps or visible flowers). Owner decides height and the play cost with stat unit.

### Owner verdict 2026-10-19 and the three fixes
"It doesn't look good, and where has the proper deformation gone? The roads are super slow and
boggy, but they don't deform at all. Also they should be gravel roads. Go for a Breath of the
Wild style grass, possibly with a shader." Facts: the soil field deforms more than before
(check surface report excavated 1.23M cm3 against .61M before CL1, push cells 2.2M against
1.3M); the slow boggy feel is the Clay slurry/track conditions and clay substance numbers; the
missing ruts are a rendering question on the relief-tile material (M_Detail clone) which now
carries the LP3c peat, CL1 clay, GP2c pasture and GP2c normal wrappers.
- RD1 Roads are gravel: every road gets the gravel condition (public as now; private mud 4,
  rut 2, firmness .85, wetness .25, grass .15 centre strip); clay stays only on the cut band
  (atlas R zero on the corridors); the corridor look becomes grey river gravel (the painterly
  gravel tile) with darker wheel lines; a Drive step in the check drives 25 m on the open
  Riverside stretch and 25 m on the bush climb and captures the ruts from behind, reports the
  surface delta across the track and whether the relief MIDs carry MR_VisualWindow; if the
  delta is there and the capture is flat, the material displacement path is repaired.
- GS1 Grass shader: a stylised material on the patches: half-Lambert wrap lighting, base to
  tip gradient from vertex colour, tip highlight toward the sun, rim, two-wave wind with gusts
  weighted by vertex alpha, per-patch macro colour variation, flat normals, warm subsurface;
  contact bend and remove and the dither fade kept.
- GS2 Grass mesh: patches 40-65 cm, blades grouped in 5-7 tufts with gaps so silhouettes read
  as clumps, 8% flower heads, blade width scale 2.2; same LOD budgets; re-import.

RD1 status 2026-10-18 (Sonnet; rd1-3, nothing committed): every road is gravel and the roads show ruts.
(1) Conditions: public roads Firm gravel 0-length as before; both private roads 'Gravel track' (mud 4, rut 2, firm .85, wet .25,
grass .15, churn .05, spread 25, breakup 2) 0-1695.8 m (Riverside access) and 0-260.8 m (Pond field spur) plus the Damp hollow
(814-983.6 m / 125.2-151.3 m, unchanged); private road base parameters now gravel too (mud 4, wetness .25, centre grass .15).
prepare: clay atlas R is zero on the road corridors (old 3.4 m track mask removed, 13,988 m2) and the 1.9 m carriageway strip is
carved out of the yard disc (78 m2); the cut band (.8, 3,108 m2) and the rest of the yard (1.0) stay clay. Read-backs: clay weight
on the open track .015, the bush climb 0, the public road 0, the cut-band probe .59 (friction 2.08, linear 13.5, push 44.2); the
road points now carry the mud-default numbers (2.2 / 10 / 36), clay was 2.0 / 16 / 50 and 1.0 / 14 / 42.
(2) Look: the clay atlas ALPHA (a constant 255 before) is the road lateral distance for all four roads (d / 6.4 m + .5, left
positive, 1 = far; bilinear sampling of that linear field is exact between 1.8 m texels, so the corridor and the wheel lines are
read from it). RD1Gravel (between CL1Colour and the rock mix) and RD1Rough (around CL1Rough) in M_Terrain and M_Detail, RD1Tread
on the tread ribbons' emissive: T_gravel (T_Gravel_Painted_v1.png, sRGB, wrap, 2048) at 1.0 m blended 30% with itself at 3.7 m
(rotated 31 degrees), saturation .20 toward grey and a measured tint to a linear albedo (.19,.186,.182), wheel lines at |d| = .82 m
(+-.2 m, 25% darker, roughness x.85 on .85), full gravel at |d| < 2.0 m fading to none at 2.6 m, grass cover (style G .12 to .6)
shows through, cut banks keep CL1's clay and orange. Tread ribbons lose their dirt hue on the corridor (they were orange).
(3) Rut diagnosis (Check Drive step, Ruts_open / Ruts_bush; GT_CHECK_DRIVE_ONLY=1 runs only that step, GT_CHECK_HIDE_TILES=1 adds a
capture with every relief tile hidden). The soil field was deforming but the road tiles covered it: AGTRoadReliefTile meshes were
built with M_Detail (the visual-grid material: opaque INSIDE the player window, no MR_ActiveGrid parameter, and the tile's own MID is
never registered with the surface, so GTLS_Ready 0 and GTLS_Field 'Black'), so inside the window each tile drew its undisplaced rest
surface coplanar with the visual grid and hid every rut and tread ribbon; with the tiles hidden the same frame showed two clean
tyre ruts. The wrappers did NOT break anything: the World Position Offset chain (39 nodes, GTLS_Field / Window / Ready and
MR_VisualWindow all upstream) and the opacity mask chain of the clones are node-for-node the template's. Repair: relief_material =
M_Terrain (RELIEF_KIND in Install), the material the tile code is written for (mask 1 - dither(window) x MR_ActiveGrid, so the tile
is cut away exactly where the grid draws); Check asserts the tile MID's parent, MR_ActiveGrid 1 and the window.
(4) Still open, reported not patched: on the OPEN gravel stretch the soil layer is only 0.8-1.7 cm thick (mud 4 cm x mottle x softness)
and Field.NativeBaseAlpha (paint depth / 3) gates native mud updates at .75, i.e. 2.25 cm, so the field writes nothing there
(excavated 0, push cells 0, surface delta -0.43 cm before and after the drive); on the bush climb the layer is 2-3 cm at the wheel
lines and the first pass leaves 3.1 cm ruts (compression 1.9 cm). The lever is the gravel track's mud depth (about 8 to 10 cm for
2.5 cm or more at the wheel lines); the owner decides how deformable gravel should be. Gate: owner drives the open track, the climb
and Waimeamea Road and says whether gravel should rut.

GS1/GS2 status 2026-10-19: BUILT. GS2 (Sonnet ~0.28M): patches rebuilt at 110 blades in 5-7
tufts (tuft blades median 48 cm, tips 36-38 cm, fillers 16 cm), 9 flower stalks (white/purple/
yellow), width scale 2.2, LODs 414/126/24, coverage better than the lawn build (ground visible
mid-frame 1.9% against 3.0%); re-imported (Install/Polish re-apply the LOD2 screen size). GS1
(Sonnet ~0.37M): M_LidarClump/M_LidarRank gained GS1Style (normal flattened 70% to up, vertex
gradient with +15% at the tip, sun tip highlight pow 4 x .25, rim on a 30%-flat normal faded
12-30 m, 6 m + 24 m macro colour drift between (.72,.95,.60) and (1,.95,.62), flowers kept
raw with +.1 emissive to 25 m, subsurface .2 tip-weighted, roughness .70, specular .10) and
GS1Wind (3.5 m and 11 m travelling waves plus a 25 m gust field, alpha-squared weighted, 4.5 cm
calm / 9 cm gust at the tip; the recovered program keeps only contact bend and removal). Look:
individual tip-lit blades in clumps with flowers, colour drifting in patches, no glare, clean
fade, ground beyond the fade within 5/255 of the grass. Thinner and less saturated than
reference 01 by design (photo 09 hue). Wind motion unverified in stills. RD1b (final pass):
gravel depths raised so the open stretches rut shallowly.

RD1b status 2026-10-19 (Sonnet ~0.17M): Gravel track mud 4 -> 9, rut 3, firmness .80; Firm gravel
mud 2 -> 5, rut 2, firmness .90. Drive step: open gravel ruts 3.3-3.9 cm raw after one pass
(about 2.8-3.4 net), bush climb 4.3-5.8 cm; compression 3.5 / 4.4 cm; the ruts now render
(RD1's M_Terrain tile fix). Corridor unchanged within rounding. Fable's look: Ruts_open reads as
a grey gravel farm track with two pressed rut lines and tussock verges; Paddock_chase reads as
a dense tufted meadow with lit tips, flower specks and colour drift, the car sitting in it:
the closest yet to references 01/03. Open: gravel ruts a touch deep for a firm road (mud 7-8
would land under 3 cm), public road base mud still 2, bush ruts slightly warm-tinted, wind
unverified in stills, paddock HUD sink still from the Grass surface type's max sinkage
(decision open). GATE: owner drives.

### LP5 — Clearing marks and bank shading
- Diagnose the zigzag marks (distant grass cards, shadow acne, relief normals or a mask step)
  and the faceted bank shading; fix; capture toward the sun and on foot.

### LP6 — Play performance (runs alongside)
- Measure on the first drive (stat unit, GPU, VRAM) at the four sites and at the hairpin;
  write the numbers into `docs/LidarStudy.txt`. 144k canopy ISMs, 135k understory, 2011
  relief tiles are the suspects; HISM cull distances, LOD ratios and tile streaming are the
  levers. No look stage ships over the frame budget.

### PF1 — Frame hitch every second or so (owner 2026-10-19, driving L_LidarStudy)
Measured, found and fixed 2026-10-19. Nothing committed.

**Method.** Every periodic game-thread worker that could stall a frame is wrapped in `GT_PERF_SCOPE` (`Source/GrandTour/Core/GTPerfProbe.h`): a cycle stat in `stat GTPerf` and, while `gt.Perf.LogSpikes` is 1, a
wall-clock probe that logs any single call above 2 ms (`LogGTPerf: GTPERF_SPIKE <worker> <ms> work=<count> frame=<n>`) and keeps calls, mean, max and every call above 2 ms (2 keeps the numbers without the log lines; 0 is
off). `gt.Perf.Reset` clears, `gt.Perf.Dump <label>` writes `Saved/Profiling/gt_perf_<label>.json` (per worker: calls, mean, max, calls above 2 and 4 ms, the interval between the calls above 4 ms; every spike with the
frame times of the frames around it; the 40 slowest frames with the worst probe in each). Probed: `RefreshGrass` and its parts, `StreamDistantGrass`, `IndexGrass`, `AGTLandscapeSurface` Focus / Observe / Upload / BindTextures /
shadow invalidate, `FGTLandscapeSurfaceField::Step` (and its native part), `AGTMudRunnerVisual` Tick / window move / grid build / bind / track sections / clod sweep, `AGTWaterSheet` TickDomain / MoveWaterWindow /
UploadField / UploadRiverDetail / field and river-detail steps. Run: `GT_CHECK_DRIVE_ONLY=1 GT_CHECK_PERF=1 powershell -NoProfile -File Art/lidar_place.ps1 -Mode Check` (about 3.2 min; the Benmore profile pipeline is
bound to L_Benmore_GaeaReview and its own drive script, so the Check harness and its Drive step were used). Per leg: a 10 s idle window, then the drive with a Dump at its end: the 25 m open-road stretch, the 25 m bush
climb (both RD1), and a 40 m drive across the NE paddock (from 12 m beside the paddock-1 trough toward the nearest clear fence run, throttle .5, low range, diff lock; `GT_CHECK_PERF` only). The hidden editor's absolute frame
time (17-34 ms here) means nothing; the per-call durations are real.

**Before** (NE paddock leg, 11.3 s, mean speed 3.6 m/s; per worker: calls / mean ms / max ms / calls above 4 ms / interval between them in s):

| worker | before | after |
|---|---|---|
| near grass refresh (`RefreshGrass` -> `GrassStream.Slice`) | 11 / 54.5 / 56.1 / 11 / 0.96 | 44 / 1.16 / 1.6 / 0 / - |
| `IndexGrass` (full re-index after every refresh) | 11 / 5.8 / 6.2 / 11 / 0.96 | gone (kept incrementally) |
| distant grass (`StreamDistantGrass`, recentre 12.4 ms) | 333 / 0.81 / 13.7 / 4 / 2.20 | 354 / 0.04 / 1.5 / 0 / - |
| visual grid window move (`WindowMove` -> `WindowFlip`) | 7 / 32.4 / 33.8 / 7 / 1.53 | 6 / 1.38 / 1.8 / 0 / - |
| tread ribbons (`TrackSections`) | 333 / 2.14 / 32.7 / 10 / 1.02 | 348 / 0.51 / 1.2 / 0 / - |
| surface field `Focus` (tile crossing) | 333 / 0.14 / 23.3 / 2 / 4.23 | 354 / 0.24 / 1.3 / 0 / - |
| field texture bind on window publish (`BindTextures` -> `BindSlice`) | 2 / 5.7 / 6.1 / 2 / 4.51 | 10 / 1.13 / 1.3 / 0 / - |
| `Upload` (contains the bind on a publish) | 178 / 1.59 / 6.3 / 2 / 4.51 | 177 / 1.53 / 1.7 / 0 / - |
| `FGTLandscapeSurfaceField::Step` | 333 / 1.65 / 3.2 / 0 / - | 354 / 0.87 / 2.5 / 0 / - |
| `Water.MoveWindow` (10 m window) | 2 / 1.74 / 1.8 / 0 / - | 2 / 1.60 / 1.7 / 0 / - |
| `MudVisual.Tick` as a whole | 333 / 2.99 / 64.6 / 10 / 1.02 | 354 / 0.75 / 2.3 / 0 / - |

Open road leg (25 m): grass refresh 7 calls, mean 49.1, max 50.1 (every 0.96 s); window move 4 calls, mean 25.7, max 27.2 (every 1.50 s); distant recentre 3 calls, 12.0 ms (every 2.22 s); `Focus` 26.3 ms (every 4.4 s);
bind 8.0 ms. After: nothing above 2.2 ms. Bush climb: the same pattern (45 / 26 / 12 / 25 ms), after: nothing above 2.4 ms. Frames in a leg with any probe above 4 ms: 29 / 30 / 49 before (open / bush / paddock), 0 / 0 / 0 after;
frames with a probe above 10 ms came every 0.45-0.47 s on average before. Frame time (hidden editor, ms, p99 / max; idle windows 20-24 / 21-25): open 72.8 / 75.4 -> 41.1 / 47.5, bush 75.2 / 78.6 -> 28.1 / 30.0,
paddock 102.7 / 111.7 -> 34.5 / 36.9. Example frame series (ms, frames -2..+3 around the spike): before `[24.2, 21.0, 72.0, 26.9, 26.3, 27.7]` with `RefreshGrass` at 49.4 ms; after nothing but ~24 per frame.

**Cause.** The pawn crossing a 4 m grid step recentred the clump streaming, which rebuilt its whole disc in one call (`SampleSurface` and `GroundHeightAt` for about 28,000 lattice cells, 45-55 ms, then a full
`IndexGrass` pass over every instance, 2-6 ms); the visual grid rebuilt its 148,000-vertex mesh every 8 m (25-34 ms: 148k height queries, 7 ms in `CreateMeshSection`, 1.5 ms rebinding 2,011 relief tiles) and the distant card
layer re-listed a 60,000-cell box every 8 m (12 ms); a 16 m tile crossing built three 65,536-cell field tiles in one `Focus` (23-26 ms) and a texture-window publish set three parameters on every landscape component
(4-8 ms); the tread ribbons re-clipped and re-sampled a whole 256-segment section every frame and all sixteen on every window move (2-33 ms).

**Changed** (what each computes is unchanged; only when and how often):
- `GTMixedGroundStreaming.cpp`, `GTMixedGroundDetails.cpp/.h`: clump streaming is an incremental ring job. A job moves the 4 m centre, walks only the lattice cells that enter the new disc (`FRingCursor`: rows nearest the
  centre first, the cells inside both discs skipped without a test), frees the instances that left (Leave), evaluates the entering cells under a 1.0 ms budget per tick (Enter; `EvalClumpCell` is the old per-cell code), refills
  the freed slots first and adds the rest with one `AddInstances` per component per slice, then closes leftover slots by moving the last instance in (Compact). The contact bookkeeping (originals, packed state, root heights,
  buckets, bent and removed sets, custom data, remembered contacts) is kept per instance (`WritePastureSlot`, `MovePastureSlot`, `RemoveLastPastureSlot`) instead of rebuilt; the render state is rebuilt when the job ends and
  every sixth slice. One job at a time; a jump of three radii abandons the one in flight (teleport); BeginPlay runs the first job at once. The distant layer uses the same ring walk (Leave, then Enter under the rest of the
  1.5 ms tick budget). `gt.Grass.Clumps 0` (cards) keeps its original full refresh and `IndexGrass`. `StreamingConsistency(bRebuild)` re-evaluates the whole disc the old way and compares.
- `GTMudRunnerVisual.cpp/.h`: when the grid is 12.5 cm and n x 800 cm wide (the LiDAR and Benmore levels, 4800 cm) the follow grid is a pool of 48 world-anchored 800 cm tiles (65 x 65 vertices): a move builds only the
  entering tiles (heights under a 1.0 ms budget with a one-vertex apron for the normals, one `UpdateMeshSection` each), then flips the window (re-bind) in its own tick; retained tiles are never touched and left tiles stay
  masked by the material's window test until reused. The material has no UV or vertex-colour inputs (checked in the M_Detail chains), so the tile UVs are free. Other sizes keep the single mesh. The tread ribbons are built in
  world coordinates (no rebuild on a move) and each segment's clipped geometry is computed once and cached.
- `GTLandscapeSurfaceField.cpp/.h`, `GTLandscapeSurface.cpp/.h`: `Prefetch` initialises the 5 x 5 tiles around the focus a few rows per tick (a crossing finds its tiles built; a half-built one is finished by `Focus`); a
  window publish rebinds the field textures and the window on each landscape component's material a slice per tick (`PumpLandscapeBind`: a component not reached yet keeps a complete older binding; no new refresh starts
  until the pass ends) and skips the unchanged parameters; the decay of each window tile runs every ninth frame over the whole elapsed time (`bSliceDecay`, runtime only; tests keep the per-frame loop).
- `GTWaterDomainSheet.cpp`, `GTWaterSheet.cpp`: probes only. `check_lidar_place.py`: the `GT_CHECK_PERF` legs and `streaming_consistency` asserts at the four sites.

**Verified.** `bash Art/build.sh`: 0 errors. Normal `lidar_place.ps1 -Mode Check`: `check.json` ok, driving_tested; the four sites' grass counts are identical to the pre-change Check (near 7574 / 3634 / 827 / 3901, pasture a/b/c
split, rank 1194 / 771 / 725 / 1276, distant 2531 / 3192 / 821 / 2633); `StreamingConsistency(True)` at each site and after each drive leg: bookkeeping ok, rebuild_missing 0, rebuild_extra 0 (live instances = exactly the
cells a from-scratch pass accepts); the nine-point contact test bends and removes in all three components (8 / 4 / 6 removed); corridor p95 / max within the Check limits (Pond field spur 4.65 / 8.94, Riverside access 1.84 / 7.36, Waimeamea Road 0.83 / 10.25, Waterhouse Road 1.30 / 5.08); RD1 drive checks pass; the cards fallback toggle in the cost probe works.

**Residual / not claimed.** `SurfaceField.Step` still reaches 2.2-2.5 ms in 2-5 % of frames (its native contact update, about 0.8 ms every frame, is the cost; not sliced: it is the tyre-contact update itself);
`MudVisual.WindowFlip` is 1.2-1.8 ms (the window re-bind of the landscape and the 2,011 relief tiles must land in one frame or the landscape mask and the grid disagree); `Water.MoveWindow` 1.5-2.0 ms; grass slices run to
1.0-1.6 ms by design. The open road leg still has six frames of 38-47 ms (p99 41) with no probed worker above 2.2 ms in them (the idle windows have none, max 24-25 ms); they are unattributed (physics, render thread or GC) and an Insights CPU
trace is the next tool. A grass cell is evaluated when it enters the disc and not again while it stays inside (the old refresh re-tested interior cells, so a cell that gained more than 2 cm of water inside the disc lost its clump at the
next recentre); the window's outermost normal ring uses central differences like the rest. After a teleport the first fill of about 28,000 cells takes ~0.5-1 s of ticks. The automation suite was not run (the rules
allow the ps1 runners only).

Order: LP0, then LP1 and LP2 together (different files), LP5, LP3, LP4; LP6 measured at every
gate. No stage ships without an owner drive.


### LA1 — Track and river-bed authoring tools, 2026-10-19

Owner request: add a 4WD track down across the river to the old logging site and
make tools for editing it. Chose direct Unreal controls and **bed depth/ford only**,
not a changed river course. Corrected the new track to **mud**; existing roads stay
gravel. Photo archived at `Art/References/LoggingTrack/Photo_01.jpg`. Owner then
corrected the interpretation: not always pronounced ruts; use our MudRunner studies.

Built: `GTLidarAuthoringPath` editor controls and Tools > LiDAR Place commands for
new mud track / bed reach, ground projection, local mud conditions, target-depth
fitting, width/depth preview, profile inspection and export/reload. Drafts are in
`Art/LidarAuthoring/edits.json` (empty: no real route or crossing invented). Default
track width 2.4 m is provisional, mud depth 18 cm / firmness .45 / wetness .65 are
editable setup values; initial old-rut depth and relief strength are both 0. Local
conditions use the existing FGTRoadCondition controls and the generator's 3D knot
distance. Solid relief, soil availability, old ruts and live deformation remain
separate. Dirt-path relief is optional. Narrow-track vegetation clearance follows
its width with a .6 m mask transition, instead of the existing gravel raster blur.

River bed controls edit derived 2017-square terrain; depth .10–1.50 m, unchanged
course/surface, configurable bed width and bank blend, end fade up to 5 m. Edits are
limited to the existing wet channel; overlap, invalid depth and excessive cut/fill
are rejected. Terrain/collision import uses a layer-aware height accessor with exact
readback, before road base capture. The new track's wet crossing preserves the bed.
Water-domain depth and shore/mesh preparation use the edited collision-height surface
inside the bed footprint. Original DEM and registered vectors stay untouched.

`lidar_place.ps1` adds ValidateDesign, Prepare (staged output plus backup), ApplyDesign
(prepare -> Install -> Polish -> Water -> Check), and AuthoringCheck. Every editor
launch calls wait_unreal_free; the old timeout Stop-Process was removed. Install now
digests water outputs and the derived heightmap too, checks design/source/height
digests, and restores design controls from JSON. Check reads bed-height probes and
supports the additional mud road without changing existing gravel condition checks.

Verification: guarded editor build succeeded, 0 errors. Nine focused Python tests
passed. AuthoringCheck passed in Entry with process exit 0: menu registration,
wrong-level guard, mud/bed export-reload, local condition retention, zero-rut condition
defaults, ground snapping and depth fitting.
Blank preparation reproduced all 23 existing bake output files exactly (only the
prepare report gained authoring metadata); derived height equals source SHA256
`deba359a50b01fedb76af13cc6846162983408c3a76c5032e421de543507d75d`, 0 changed vertices.
A synthetic fixture under Saved/LidarAuthoringQA added one mud track and one bed edit:
20 terrain vertices changed, maximum 78.5012 cm, 22 water-depth cells changed;
existing four road records, clay/gravel atlas, river course, surface levels and flow
values stayed identical. These are QA fixture numbers, not a proposed real ford.

Limits/gate: saved L_LidarStudy was not installed or saved during this work; a real
route, full Install/Polish/Water/Check and owner drive remain after layout. River-bed
sculpting has the landscape's 1.835 m resolution. Water Fill in local Conditions must
stay 0: the older road-pool builder resets child domains, so pool baking is rejected
by this tool rather than risking the river/pond domains. General LP7 guide remains
after the owner gates; tool instructions are `docs/LIDAR_AUTHORING_TOOLS.md`.

### LT1 — Owner logging-route driving trial (19 October 2026)

Owner request: build the saved dirt-through-two-crossings route, then solid mud,
softer mud and bogs with large puddles; increase the car's power in high and low.
The owner's 25-point spline is 202.147 m (3D control-polygon length). XY/Z controls
are preserved. Existing access/public roads retain their gravel conditions.

Trial condition ranges (m from the house): dirt 0–164 (5 cm soil, firmness .90,
wetness .25); solid mud 158–181 (18 cm, .65, .55); softer track 170–202.14
(35 cm, .32, .85). Climb bog 173–185: 55 cm soil, firmness .22, wetness .95,
95 cm broad basin, fill cap 28 cm, 5 m blend. Upper bog 188–201: 65 cm soil,
firmness .18, wetness 1, 55 cm broad basin, fill cap 25 cm, 4 m blend. All old-rut
depths remain zero. These are provisional authoring values, not site measurements
or predicted wheel sinkage. Basin depth, soil depth, water depth and rut depth are
independent; final pool area/depth must be read from the generated collision bed.

`BasinDepthCm` is a host authoring control, not a newly recovered native algorithm.
Road water now rebuilds its child list from BaseWaterDomain before adding its own
pool. River/pond children survive and repeated rebuilds do not accumulate pools.
The LiDAR ford guard queries the original domain, excluding its own generated bogs
from river-bed protection. JSON/editor condition serialization supports the bowl.

Default car peak engine torque 320 → 480 Nm; normalized curve at idle (800 rpm)
.65 → .85, giving 208 → 408 Nm before throttle/condition/drivetrain losses. Keys:
0 rpm .65, 800 .85, 1500 .95, 2500 1, 4000 .9, 5000 .65. Gear and final-drive
ratios unchanged; low range remains 2.5. This affects the default car across maps.

The installer adds seven native-kit stones (five large beside the drive corridor,
two small embedded) and three small cobble-bar pieces on the river point. Driving
spawn/recovery point 1 moves to 3 m along the house end of the logging route.
`LoggingCheck` verifies saved pool depths against collision, the existing three
water domains and high/low uphill progress, then captures dirt/crossings/bogs.

Validation so far: guarded C++ build passed (26.83 s), ten Python design tests
passed, source syntax checks passed. Prepare completed. Install/Polish/Water/Check
and the new driving test are in progress; owner driving is still the gate.

First saved LT1 measurements: 73 wet cells at 25 cm; climb pool 1.6875 m² / 4.624 cm
maximum depth, upper pool 2.875 m² / 4.236 cm. Collision-bed depth error below
0.000001 cm; all three original water children preserved. Those pools were too
small for the requested large puddles. LT2 keeps the bog fill cap constant inside
the blended basin footprint (the old longitudinal fade was reducing the whole
connected basin via its minimum allowed fill). Spill-level clipping remains.
The LT2 guarded build passed in 24.24 s. LT2 Install saved/reloaded successfully and
exited 0. Climb pool: 8.3125 m², 26.2808 cm maximum; upper pool: 8.1875 m²,
14.9927 cm maximum. Both are spill-limited below their fill caps. Final material,
runtime and driving checks are pending below.

The installer successfully saved and reloaded LT1, but Unreal returned Windows
access-violation status -1073741819 after logging normal shutdown. This is tracked
separately from the successful map validation; no editor process was killed.

Final gate evidence (19 October, reports under Art/Export/LidarStudy/Place):
- LT2 Install, Polish and Water completed with process exit 0. The Polish pass
  already in flight still used the old three-child replacement. Water repaired it
  by rebuilding from the saved base: 264 wet cells before/after and the terrain/soil
  digest identical. Future Polish preserves generated children alongside the three
  refreshed river/pond domains; Water retains a checked repair for legacy saves.
- General Check: every assertion passed, four site/contact/vegetation checks,
  17 captures, original river/pond disturbance probes and both existing-road 25 m
  drives with visible deformation. New logging-road cross-slope at 22 samples:
  median 1.01 degrees, p95 6.61, maximum 9.03; no station over 10 degrees.
  Check wrote ok=true but its process returned -1073741819 on shutdown. The
  intermittent exit failure remains undiagnosed; this is not a clean process pass.
- LoggingCheck: ok=true, process exit 0. At .65 throttle with diffs locked, the
  same uphill start at 159 m advanced 24.298 m in high range and 30.208 m in low
  (24-second limit or 30 m target). Maximum lateral offsets .242 m / .176 m;
  maximum observed engine torque 286.93 / 311.90 Nm. Current tuning confirmed
  480 Nm peak in both runs. Low range reached the limiter in soft ground; this
  smoke test establishes pulling ability, not unrestricted bog traversal.
- Runtime probes at 40 / 166 / 179 / 195 m, offset .85 m: yielding-layer caps
  2.76 / 12.25 / 38.73 / 49.46 cm; softness .100 / .345 / .772 / .819.
  These are sampled capacities, not wheel sinkage. Existing 50 cm runtime layer
  cap retained; authored 55/65 cm bog settings are not promised settlement depths.
- Saved pools verified against collision again in LoggingCheck; river/pond
  probes retained. Reviewed Logging_dirt.png, Logging_crossings.png and
  Logging_bogs.png. Broad puddles are visible; no uniform pre-authored wheel ruts.
- No Unreal process left running. No commits. Owner drive remains pending.

Drive via Play-LidarStudy.bat: start at 3 m along the house end of the owner's
saved 202 m route. 1 returns to this start; V toggles high/low, X the diff locks,
Backspace reloads fresh ground/vehicle state. The route is only the currently
drawn section; no continuation to an unmarked logging-site location was invented.

### LT3 — Extended route, terrain-led variation and loose obstacles (19 October 2026)

Owner saved/closed Unreal after correcting snap and asked for a varied MudRunner-like
drive: local widths, boggiest dips, intermittent flooded ruts, fallen logs and movable
clumps. The saved map exported cleanly (exit 0; map SHA unchanged): 96 points,
713.721295776 m. All XYZ controls remain exactly as saved. Snap now uses the selected
built road's current route, updates that road and synchronizes the export design in
one Undo transaction; it no longer snaps an old design while leaving the selected
road floating. AuthoringCheck passed with real editor exit 0, including moved/extended
built-road selection, design roundtrip and unrelated-selection rejection.

Width is persisted as per-control widths_m, resampled with XYZ, restored as spline
Scale Y, and used in road generation and vegetation clearance. LT3 control widths
are 2.2146–4.3344 m. House through the second crossing stays firm dirt (0–164 m).
Solid mud blends over 156–186 m; mixed bush mud continues to the end. Narrow firmer
climb 228–270 m, worn climbing grooves 319–368, dry crest/passing place 392–475,
uneven descent 480–530, broken rutted approach 590–642. The natural hollows were
identified from the owner's elevation profile, not evenly spaced by a scatter rule.

| Hollow / condition range (m) | Soil cm | Firmness | Wetness | Rut cm | Basin cm | Fill cap cm |
|---|---:|---:|---:|---:|---:|---:|
| First broad churn, 199–225 | 48 | .27 | .94 | 5 | 42 | 20 |
| Saddle wheel channels, 277–310 | 55 | .24 | .97 | 17 | 24 | 16 |
| Shelf wet pockets, 537–568 | 43 | .30 | .92 | 9 | 28 | 13 |
| Deep gully, 646–686 | 70 | .16 | 1 | 22 | 45 | 32 |

Natural dip stations approximately 214 / 290 / 552 / 667 m. Fill caps are not
promised water depths; final priority-flood/collision readbacks follow below. Native
road reconstruction is reused; local basin/condition composition is host authoring.
The separated wet areas need approximately 1,630,035 survey samples at 25 cm, so the
bounded authoring guard increases from 1.5M to 2M. Per-frame water/mud resolution is
unchanged. Editor build passed in 24.55 s. Eleven Python design tests passed,
including varying widths through resampling and vegetation masking.

Six loose native logs at stations 239/335/485/579/621/700 m, lengths 1.5–2.6 m and
masses 24–70 kg; thirty existing mud-chunk meshes, 26–44 cm, in irregular groups
on firmer shoulders beside wet/churned sections. All have prepared convex hulls,
individual physics bodies and continuous collision detection. The first settling
audit caught four small clumps falling through and several hidden beneath the
yielding surface. Moving them onto firm shoulders, excluding the thin smear mesh,
and enabling CCD fixed the audit: all 36 bodies remained above ground after eight
simulation seconds (lowest bounding-box top 9.28 cm). This is now a permanent
LoggingCheck assertion, not merely a physics-enabled flag check.
The subsequent saved-level test caught clump 18 falling through (top -355.14 cm).
LT3b therefore samples the complete rotated clump footprint, not just its long
axis, and starts its hull 10 cm above the highest sample to avoid initial overlap
on steep shoulders. Install can refresh this dressing alone when both the full
inputs digest and saved road digest match; it backs up the map and verifies the
unchanged pools before saving. The failed check is retained under
Saved/LidarAuthoringQA/LT3-saved-clump-failure. Fresh-load verification follows below.
The saved LT3b check still failed only clump 18 (top -369.00 cm); all other 35
bodies remained above ground, lowest top 9.25 cm. LT3c relocates that clump to
station 434 m, 0.7 m across, on the firm crest: chunk variant 0, 38 cm, 17.2 kg.
This also provides a loose clod in the driving line. The prepared input comparison
confirmed only logging_trial.json changed. Install reconstructs the previous
manifest from its recorded source fields (preserving CRLF) and requires the full
old digest to match before reusing terrain for a manifest-only dressing update.
The logs/chunks are movable; breakage/fragmentation is not added by this pass. River
rocks and the small cobble bar retain their earlier placement. The 480 Nm engine
tune and range ratios remain unchanged. Recovery 1 is the start, 2–5 approach the
four hollows; 6–9 retain the original recovery locations.

Inputs: Art/LidarAuthoring/edits.json and logging_trial.json. Composition is recorded
in Art/tools/compose_logging_trial.py; obstacles are deterministically specified,
not newly scattered each launch. Prepare copies their manifest into the digested
inputs. Install marker LT3 forces one rebuild. The ordered Install/Polish/Water/Check
completed with clean exits, including four sites, driving checks and 17 captures.
Later LT3b/c dressing-only corrections preserved the verified terrain and water.
Their saved data and reload assertions passed, but several automated editor
shutdowns returned access violation -1073741819 after normal shutdown messages.
LT3c's cached retry also had this shutdown failure; it is not counted as a clean
Install. Gameplay verification was therefore run independently on the saved map.

Measured pool areas / maximum depths: first hollow 24.5625 m² / 20 cm; saddle
15.625 m² / 16 cm; shelf 10.25 m² / 13 cm; gully 21.375 m² / 32 cm. Total 1,149
wet 25 cm cells (71.8125 m²). All three original river/pond children survive.
Fine road geometry: 1,004,400 triangles in 2,232 tiles. Regenerated vegetation:
148,858 canopy and 200,234 understory instances; 594 farm pieces. Original four
gravel roads and source terrain heights remain unchanged.

Initial automated drives at 65% throttle, locked diffs: high and low range each
climbed 30.15 m. Low range cleared the first hollow (34.09 m), shelf (39.12 m) and
gully (48.07 m). The saddle advanced 20.93 m of its 41 m target in 45 s and stopped;
the driver deviated up to 1.23 m, so this does not establish whether a human line
can clear it. The 70 kg log moved 10.14 m during vehicle contact, with zero drift
before contact. A representative clump responded to an impulse by 17.61 cm.
Visual review includes an unobstructed log, broken shelf pools and deep gully pool.

Recovery keys 7–9 were missing their input bindings despite the HUD listing them;
these are now bound and the editor build passed (27.35 s). Install and Water each
had an earlier shutdown access violation after successful report generation; their
retries, full Check, LoggingCheck, AuthoringCheck and corrected obstacle review
all exited 0. Failed attempts are retained under Saved/LidarAuthoringQA. Owner
drive remains the acceptance gate. No commits.

LT3c saved-map verification distinguishes the rendered mud surface from the
mineral bed used by rigid bodies. All 36 objects stay above that physical floor;
the lowest measured top clearance was 9.25 cm. Six logs and 29 clods exceeded
2 cm above the visible surface; clod 12 settled to +1.28 cm above visible mud,
but +28.86 cm above the mineral bed. A blanket visible-surface assertion wrongly
rejected this expected burial in soft mud. The check now requires every body above
the mineral bed, all logs visible, and at least 90% of clods visible.

Latest 65%-throttle, locked-diff range runs advanced 30.13 m high / 30.24 m low.
The subsequent automated low-range bog runs did not clear their targets: first
23.47/34 m; saddle 15.19/41 m; shelf 37.40/39 m; gully 17.45/48 m. These differ
from the initial runs above and are retained under Saved/LidarAuthoringQA/LT3c-bog-sequence.
The later log test stopped before impact (3.22 m travel, log still 6.31 m away).
A fresh standing-start test also stopped short (1.25 m travel); its capture shows
22.9 cm sinkage on the approach, rather than a demonstrated failure to move the log.
Contact-only testing now uses a documented 2.5 m/s rolling vehicle approach to
isolate prop response from stationary sinkage. This does not prove that the
65%-throttle driver can traverse the approach or the bogs. Owner driving is needed
to set difficulty and assess line choice and momentum.

Final LT3c contact-only check passed, with clean editor exit 0 at 14:39 local.
From the documented 2.5 m/s rolling start, the car moved the settled 70 kg log
52.78 cm (baseline drift 0; closest car 174.14 cm; vehicle progress 2.95 m).
The representative clod moved 13.03 cm under the impulse check. Saved widths,
four pools, original river/pond probes, 480 Nm tuning's prior range checks and all
36 simulated-body floor checks remain recorded. The final contact report is
Art/Export/LidarStudy/Place/loggingcheck.json; the separate full bog sequence is
preserved under Saved/LidarAuthoringQA/LT3c-bog-sequence. The successful contact
check does not erase those incomplete bog crossings or the Install shutdown
failures. No Unreal remains running; no commits. Ready for the owner's drive.

## Photos the owner can supply (ten shots, phone, any weather)

1. The gate off Waimeamea Road: road surface, width, verges, fence.
2. The straight through the paddocks: fence type, pasture, a shelterbelt.
3. The hairpin and its banks: cut face, drainage, surface.
4. The pond from the road: edge plants, water colour, whether it is a dam.
5. The climb into the bush: road surface, bank and the bush edge together.
6. Inside the bush beside the road: trunks, ferns, understory, light.
7. The river near the house: bed, banks, width, water colour.
8. The house clearing from the road end: house and sheds, massing only.
9. A wet hollow or gully edge if there is one: flax, rushes, tree ferns.
10. Any view you want to recognise in the game, for example looking back down the valley.

Also useful in a sentence each: what the road is made of, which trees dominate the bush, what
the paddocks are used for, and the time of day and weather you picture it in.


### LT4 — native surface detail directly on the saved logging route (2026-10-19)

Owner rejected further isolated test sections and reiterated getting as close to
MudRunner as possible. All installation and captures use L_LidarStudy itself.
Five new owner references are in Art/References/LoggingTrack/Photo_02..06.jpg;
firm littered stretches, exposed roots/branches and concentrated wet hollows
remain the composition target, without making every section deeply rutted.

Implementation: Art/tools/build_lidar_track_detail.py converts original installed
editor DDS pixels (forest, dirt road, smooth dirt road, dirt path) to PNG without
repainting; manifest.json records source paths/hashes. Native road UV defaults
are 7m width / 14m repeat for dirt and smooth dirt, 6m / 12m for dirt path.
TerrainCommon.fxh ApplyOverlay's alpha and pigment arithmetic is retained with
an explicit colour-space bridge into the existing recovered Mud SM3 program.
The original flat/churn/normal/decal arithmetic and physical surface programs
are kept. A new colour output passes the native result beyond the later LiDAR
peat/clay colour overrides, on this corridor only, in BOTH M_Terrain/M_Detail.
This is not a new independent painterly mud shader. The independent surface
masks and switching between the three profiles are authored host composition.
Full native overlay POM, source lightmaps/projectors and complete editor rebuild
parity are not claimed. No new displacement or normal-map approximation added.

Route mapping: one uncompressed 1024-square RGBA lookup with two 16-bit values
(station, lateral offset), plus BC7 composition mask; 458m square domain,
44.7265625cm mask texels. Detail textures retain their source resolution and
repeat scale; the route mask resolution is not their texture resolution. Lookup
is non-streaming/without mips; source textures are mipmapped and streamable.
Built all-mip sizes total 18.8125 MiB across six textures (measured through
GTMudArtLibrary; actual resident memory can be lower).

Dressing uses the executed native 800-budget candidate pattern bank (16 variants,
200 candidates per 8m square) and recovered density probability gate, density
multiplier .06. Host masks, cell seeds, RNG scheduling, surface seating and NZ
mesh substitutions remain adapters. Final composition has 327 fine-litter
instances: TwigLitter_A 96, TwigLitter_B 115, LeafLitter_A 116; 35 spatially
grouped components, cull end 38m, no collision or dynamic shadows. No additional
physics bodies; existing six movable logs and thirty clods remain. Original
road terrain/soil digest EF32B3B001D2091927A1F02B371CE89F and 1,149 wet cells
are unchanged.

New guarded modes: Art/lidar_place.ps1 -Mode TrackDetail installs this appearance
pass on the existing saved level; -Mode TrackDetailCheck reloads it and captures
the actual route at stations 247, 432 and 551m. Prepare regenerates detail inputs
after preparing the route; Polish reapplies the native surface/dressing pass,
so the normal prepare -> Install -> Polish -> Water -> Check order retains it.
Standalone appearance installation does not regenerate terrain. Backups of the
map and two affected materials precede installation under Saved/LidarStudyBackups/LT4-*.

Initial development checks: first baseline script had an Unreal Python struct
property-access error, corrected before taking the baseline. First installation
saved successfully but a validator incorrectly counted a scalar parameter as
a second final colour wrapper; corrected to count Custom expressions only.
The first graph construction logged transient missing-input shader warnings
while pins were being connected; the subsequent runtime load compiled without
those errors. A repeated installation preserves the original upstream native
program SHA in both materials, without stacking wrappers. First-pass evidence
(104 litter instances) is archived under Saved/LidarAuthoringQA/LT4-first-pass.

Baseline stationary hidden-editor mean/p95 ms: firm 23.93/27.99, crest
22.00/25.37, bog 20.99/24.70. First pass: firm 23.36/27.40, crest
21.60/24.61, bog 21.71/25.48. Five-second windows, same cameras, uncapped,
not isolated GPU measurements or full driving acceptance. Baseline and first
visual check completed their assertions/captures but the processes returned
-1073741819 during shutdown; their process reports retain the failures.
Final denser-litter pass validation and timings follow below.

LT4 final result (21:33 UTC): the denser 327-instance map was saved and reloaded,
then the live disturbance binding was corrected: Field alpha is C.Track
(GTLandscapeSurfaceField::Pack). Worked cells suppress the authored litter mask
and restore native churn coverage; soil/deformation programs remain unchanged.
A materials-only repair saved the two materials and reloaded the saved map,
without regenerating or resaving its terrain/dressing. Final saved-material and
PIE checks passed their assertions; only the original colour Custom expression
changed among existing surface programs in each material. Final source/mask
bake repeated byte-identically. No C++ build was needed.

Final stationary mean/p95 ms: firm 23.40/27.08, crest 21.91/26.72,
bog 21.61/24.87. Compared with baseline, means change -0.53/-0.10/+0.61ms;
p95 changes -0.90/+1.36/+0.18ms. These short measurements do not establish
a full-route performance guarantee. Additional geometry is noncolliding,
culled at 38m and has shadows disabled; all original movable obstacles remain.
Captures: TrackDetail_after_firm.png, TrackDetail_after_crest.png,
TrackDetail_after_bog.png under Art/Export/LidarStudy/Place. Reports include
texture format/all-mip sizes and unchanged geometry/water validation.

IMPORTANT PROCESS STATUS: final TrackDetail and TrackDetailCheck both have
report ok=true and successful saved-map reloads, but both processes returned
-1073741819 on shutdown, after their normal shutdown/log-close messages.
The guarded wrapper correctly reports these runs as failed; this pre-existing
shutdown fault is not resolved or counted as a clean process pass. Unreal is
closed. The owner's drive and appearance judgement remain the acceptance gate.

### LT5 — live logging-rut water (2026-10-19)

Owner reports the baked rut pools fail to fill newly deformed ground and asks
where the recovered wheel spray/churning went. Inspection: the saved
Woodland_WheelEffects actor and all nine native sprite materials were present.
Generated road water was a clipped static mesh plus an immutable child domain;
neither could grow a shoreline when the live soil changed. Its domain renderer
also bypassed the recovered SimulationWithMud sediment/water path.

Art/Unreal/lidar_rut_water.py installs directly into L_LidarStudy. The saved
authoring bake remains 1,149 wet samples; terrain/soil digest remains
EF32B3B001D2091927A1F02B371CE89F. During play the four bogs replace only the
generated child domain and its static rendered mesh. The river and two pond
children stay on their existing path. Four closed water fields are seeded from
the original 25cm samples, including separate initial puddle elevations; no
automatic filling of every low point below a single flat plane. Field widths
57/74/35/52 cells (3,249/5,476/1,225/2,704 cells). Authored seed volumes
1.916936604/0.946365946/0.542294910/2.740630427 cubic metres. One nearest basin
steps; sleeping basins retain water and their own visual state.

Live bed changes use the existing revision/dirty-region path at 10Hz and
conservative closed-basin solver. A new dry rut receives water only through
connected flow; excavation does not create water. Native water/sediment MRT
arithmetic and Waves are reused from MudLab in four LiDAR material clones,
with the flat 50cm fixture's ground adapter replaced by the actual streamed
LiDAR displacement. Native effects rates/sprites are unchanged. The host
water solver, lighting and simulation scheduling remain adapters, not a claim
of complete native-engine equivalence. Native cosmetic targets update at 30Hz
only for the awake basin; water texture upload remains capped at 30Hz.

Guarded modes RutWater/RutWaterCheck install and validate this saved map.
Polish reapplies the installation after a route rebuild. The first install
saved successfully and exited 0; the C++ editor build succeeded. The map was
backed up under Saved/LidarStudyBackups/RutWater-1792450022123998100.
Actual-map live deformation, wheel-emission and performance results follow.

LT5 validation: seven targeted tests passed (MovingWaterBed, EmitterLuaOracle,
InteractionVisuals, MovingDomain, MudContactFoam, PassiveDetail, RiverReference).
First live check caught an unsaved cloned M_Waves asset: physical water worked
but native_steps remained zero. Saving all four material clones fixed that.
The materials-only repair saved successfully but returned the previously seen
-1073741819 shutdown exit; this is retained in rutwater-process.json, not called
a clean process pass. A subsequent full saved-map check exited 0, report ok=true.

The first shoreline fixture incorrectly selected its source from the original
bake after driving had already redistributed the water. Corrected to require a
currently wet source and move the car away from the cut. In actual L_LidarStudy,
point (-44025,-41275) cm started dry; live soil displacement changed from
+0.468279 to -0.531715 cm and water grew from 0 to 0.963302 cm after six seconds.
Coverage became true; wet cells 383 -> 387. Basin volume 1.91693666 ->
1.91693670 m3 (4e-8 m3 difference); no depth clamp. This is a transient PIE
regression on the actual track, not a saved synthetic test section.

Four-second real-car throttle passes, stations 214/290/552/667: native small
water sprays 411/210/94/319; native fluid bursts 2/3/1/2. Recovered emitter
rules/rates are unchanged. The native simulation advances independently per
basin, and the checks assert exactly one awake basin. Closed-water solver mean
times at those locations .139/.130/.034/.075 ms. Final stationary five-second
window: editor tick mean 17.449ms, p95 22.365ms (285 samples). GTPerf frame mean
17.027ms, p95 21.899ms; combined MudTick work across four actors ~.204ms/frame,
including ~.073ms/frame in native visual submission. CPU worker measurements,
not isolated GPU timings or a before/after/full-route performance guarantee.

Evidence archived under Saved/LidarAuthoringQA/LT5-passed-regression; seven test
results in LT5-automation.json. Main real-map captures RutWater_drive_*.png and
RutWater_opened_rut.png. The first side cameras were obscured by ferns and were
replaced by on-track cameras. Further close emission/readback review follows.

LT5 spray diagnosis: real-wheel placement was correct (rear wheel centres around
Z=4940cm, water ~4933cm; 68/89 live small sprays above water in one sample,
mean parent alpha .267, launch vertical velocity 2.43m/s). The black flecks
visible against the car were the native sprites under physical daylight
exposure: the original adapter was unlit and used low-exposure display colour.
LiDAR-owned M_Spray_* copies now undo View.PreExposure, matching the existing
woodland tread-ribbon bridge. Native source textures, alpha, distortion,
particle rates, launch equations and oracle are unchanged. Other study
materials are untouched. PlacementReport is a read-only diagnostic. The
close diagnostic camera hides instanced vegetation only in transient PIE,
then restores visibility for an in-map capture. Evidence before correction:
Saved/LidarAuthoringQA/LT5-spray-before-exposure. Final visual check pending.

LT5 final saved-map spray check PASSED (23:18:20–23:20:10 UTC), process exit 0.
All nine saved LiDAR-owned spray materials and exposure adapters checked.
Real wheel throttle emitted 420 small water parents and 5 fluid bursts in the
close review. Native state / sediment maximum sampled RGB changes:
0.374755859 / 0.086914062. Close diagnostic images now visibly show
water sheets and droplets at the tyre. Vegetation was restored before
RutWater_spray_in_map.png; no diagnostic visibility changes were saved.
Evidence: Saved/LidarAuthoringQA/LT5-spray-passed. The material install saved
successfully but again exited with the known shutdown access violation
(-1073741819); the subsequent fresh saved-map check exited cleanly. Unreal
is closed. No human acceptance drive has been claimed.

Install/Polish/Water/Check, logging check and track-detail scripts now exclude
MudInitialDomain sheets when selecting the main river/pond sheet, so adding
four bogs does not make their selection depend on actor order. Python syntax
checks passed. Full terrain pipeline was not rerun for this selector-only
change. Existing passing physical deformation and CPU performance evidence
is retained in LT5-passed-regression. Native spray trajectories/rates remain
those checked by the original-Lua oracle; exposure compensation is a host
rendering adapter, not a claim of complete original-engine lighting parity.


### RR1 � wider rocky photo reach; full-course continuity (2026-10-20 UTC)

Owner paired references: Waimeamea 14-16. Scope explicitly confirmed: photo reach
first, continuity throughout. Art/tools/lidar_river_repair.py derives a cut-only
bed from the original height, frozen course and frozen surface elevations.
Detailed reach stations 3160-3540 m, with 35m end blends; the saved route's point
between crossings is protected. A 2m minimum-envelope allowance avoids terrain
interpolation bridging sharp source water-level steps. Lateral excavation is
bounded to 4.5m outside / 5.5m inside the reach; no terrain fill. Original source
height SHA256 deba359a50b01fedb76af13cc6846162983408c3a76c5032e421de543507d75d.
Derived height SHA256 0f67132553dfb4cfb40143d0e61d543502c6d4b4a77c8a8f8cd0830c7fdd817e.
21,753 vertices changed, maximum cut 522.008cm. Water render, domains and terrain
now sample the same quantized triangular bed rather than mixing the 1m DEM with
coarser landscape collision. Staged 2m domain check: all 7,189 course stations
associate with one connected water component; 10 total components including
small off-course pools. Maximum station-to-wet-cell distance 4.459m, at the
preserved dry point. No water-level/course changes. Source remains untouched.

Photo dressing candidates: 1,042, deterministic seed 20261020. Cobble clusters,
boulders, crown fern/kiokio, moss hummocks, root tangles and ten driftwood/jam
candidates. Final installation excludes obstructions from the drive corridor.
Baked 64m instance groups, small detail cull 45-70m, solid pieces 100-160m;
no runtime generation or extra simulations. Solid boulders and bank-held wood
use collision; small detail does not. DG1 loose/packed colour, normal and ORH
arrays are reused read-only with a warm tint and the current native live field.
Its WPO and collision stay on the current LiDAR architecture; this is not the
old independent DG1 simulator. No additional POM layer in RR1. Keep LT4 native
composition and LT5 rut-water/FX. Polish order: LT4 -> RR1 -> LT5, then Water.

Offline check: Art/tools/check_lidar_river.py. Saved-map check and captures:
Art/Unreal/check_lidar_river.py, Art/lidar_place.ps1 -Mode RiverCheck.
Pre-change map/input backup: Saved/LidarAuthoringBackups/RR1-4ed15eca-de62-4a94-bfae-d6e934ed53d0.
Unreal install, final visual/runtime checks and owner drive are pending below.

RR1 install passed, process exit 0, saved and reloaded. New ground digest:
DB443C52AD8AD4F3A1E2CD57E8E4716F. Counts versus pre-RR1: canopy
148858 -> 148420; understory 200234 -> 199834; river mesh triangles
133080 -> 189058. The cut footprint extends at most 6.144m from the course
outside the detailed reach, 11.076m inside. Sampled crossing depths: first
roughly 29-71cm; second 22-40cm. The dry corner point is retained.
Initial dressing: 1026 instances / 84 groups, 61 solid instances, 16 candidates
excluded for track clearance. Counts: cobble S/M/L 103/202/328, boulders A/B
18/33, crown ferns B/C 64/48, kiokio A/B 80/38, moss A/B 30/29, roots 36,
young tree ferns 7, driftwood 9, log jam 1. Foliage uses MI_NZ_Foliage_Bush.
The initial gravel addition exceeded the landscape shader's 32-sampler limit
(33); RR1 now shares its wrap sampler across colour/normal/ORH and the bounded
mask. A separate RiverDetail command permits local material/dressing refreshes.
Polish saved successfully and exited 0 but was correctly rejected for that
shader error; the subsequent correction must pass fresh-map checks below.

RR1 material correction and Water both passed with process exit 0. Fresh shader
statistics: M_Terrain 29 samplers / 1583 representative pixel instructions;
M_Detail 28 / 1555. DG1 Colour/Normal/ORH + local mask all-mip bytes:
5,636,096 / 11,206,656 / 11,206,656 / 1,441,792 (about 28.1 MiB total).
Final collision-aware scan of all domain wet cells finds 19,448 collision-wet
cells and one course component for all 7,189 stations (10 components including
side pools), maximum course-to-wet-cell distance 445.916cm. One shallow fringe
cell at (-47800,-33200) is hidden by the built road edge: baked depth 6.176cm,
actual ground 9.188cm above water. It does not break the channel; the coarse
shore query retains this small approximation. All four live rut sheets survive.

The initial all-in-one asset audit/capture run was abnormally slow (reported
editor dt capped at 125ms, VSM marking queue warnings). Do NOT treat those
clamped numbers as an actual FPS measurement. A fresh in-map wall-clock A/B
run (RiverPerf, process exit 0) measured: full river with car hidden 17.319ms
mean /31ms p95; car visible 18.391/32; new dressing hidden 19.100/32; water
hidden 18.396/31; shadows off 16.989/31; live gravel mask off 21.362/32.
These are sequential 8-second hidden-editor windows, not GPU timings or a
human drive. They show no material regression from the new dressing in this
run; the earlier slow review's precise cause was not established. Quality
settings were restored, no diagnostic visibility state saved. Material stats
and all-mip inspection are now opt-in via GT_RIVER_ASSET_STATS=1, separated
from normal visual checks. RiverCheck records wall time instead of capped dt.
Evidence before the final seating correction: Saved/LidarAuthoringQA/RR1-initial.


RR1 final seating and RiverCheck (2026-10-20 01:11 UTC): RiverDetail saved and
exited 0; RiverCheck also passed with exit 0. Removed the three old raised
LoggingDetail gravel-bank meshes. Cobble cluster bases now sample their full
footprint, sink into the fitted ground, and reject sharp-bank placements that
would bridge it. Final 995 instances / 83 groups / 61 solid, 31 steep-base
exclusions and 16 drive-clearance exclusions. Cobble S/M/L: 102/198/302;
all other counts above unchanged. Captures RR1_ford, RR1_bar,
RR1_rocky_shallows and RR1_continuity inspected in the actual map. Existing
lighting remains dark under the canopy; this is not a lighting acceptance.
Wall-clock stationary windows: ford 18.179ms mean /31ms p95 (257 samples),
bar 19.646/32 (237), rocky shallows 23.439/32 (196). These are short hidden-
editor checks, not the owner's drive or GPU profiling. The river continuity
and all four live-rut-sheet checks passed again on the final saved map.

RutWaterCheck then correctly rejected the old rutwater.json ground digest:
the interrupted Polish run had not refreshed the LT5 installation report.
Refresh the existing four LT5 basins against the new installed domain before
claiming the deformation/spray regression. The main Check's normal/roughness
assertions now follow the exact RR1 NativeN/NativeR pins while verifying the
Normal/Rough output names; the existing native material checks are retained.


LT5 after RR1: RutWater refresh saved successfully, process exit 0, with the
new ground digest. RutWaterCheck then passed with process exit 0 (2026-10-20
01:19 UTC). All seven automation tests passed: MovingWaterBed, EmitterLuaOracle,
InteractionVisuals, MovingDomain, MudContactFoam, PassiveDetail, RiverReference.
Actual car inputs in basins 214/290/552/667 emitted 249/163/85/184 small-water
parents and 4/2/5/2 fluid bursts. New cut at (-43925,-40775)cm lowered soil from
-0.279990 to -1.279987cm; water depth rose from 0 to 0.958532cm, and volume
1.91693671 -> 1.91693666m3. One basin awake at a time, four live sheets, no
baked duplicate. Short idle editor-dt window: mean17.586/p9521.009ms; use RR1's
wall-clock windows above for the river. Evidence: Saved/LidarAuthoringQA/RR1-passed.
Polish now publishes rutwater.json after its successful level save, preventing
the stale-report check failure on subsequent full pipeline runs.


Final main Check passed, process exit 0 (2026-10-20 01:28 UTC). Four sites,
material graphs, native water queries, vegetation/farm counts, grass streaming
and contact behaviour passed. Both 25m RD1 drives passed; road relief uses
M_Terrain with the live visual window, and the bush drive writes real ruts.
Logging mud track cross-slope p50/p95/max: 1.029 / 4.447 / 8.764 degrees at
73 stations. Its saved route still requires the owner's drive acceptance.
The first main Check stopped on one remaining legacy direct-roughness-node
assertion; that check now uses the same verified RR1 native-input traversal.
Final evidence in Saved/LidarAuthoringQA/RR1-passed includes rivercheck,
riverperf, riverdetail, rutwatercheck and check reports, process statuses and
captures. Unreal exited normally; no commit, no source LiDAR overwrite.
Owner drive and visual comparison to photos remain pending. Launch with
Play-LidarStudy.bat. Existing canopy lighting is unchanged.


### PF60 - owner request: get L_LidarStudy running at 60 fps (2026-10-20 UTC)
Target: RTX 4050 Laptop 6GB, standalone game at launcher output 1600x900.
All work stays in the actual map. No source LiDAR, road controls, simulation
settings, placed instance density or global project scalability edits.

Evidence tools: Profile60 (PIE CPU/GPU separation); Art/profile_lidar_play.ps1
(standalone CSV, same chase views, optional real Enhanced Input throttle/brake);
Art/tools/analyze_lidar_play_perf.py (warm-window mean/p95/p99, excludes teleport
and HighResShot frames). Source engine commands checked locally, no synthetic
fixed timestep. Each game quits normally after capture. Hidden/offscreen;
these short windows do not establish a full-route no-hitch guarantee.

native: r.ScreenPercentage 100
river: 78.5 fps mean; frame mean/p95/p99/max 12.740/14.999/16.286/47.704 ms; GPU mean/p95 12.126/13.844 ms (840 frames).
bog214: 60.3 fps mean; frame mean/p95/p99/max 16.579/20.166/21.220/22.551 ms; GPU mean/p95 16.075/19.039 ms (840 frames).
bog552: 57.0 fps mean; frame mean/p95/p99/max 17.534/20.878/22.403/55.043 ms; GPU mean/p95 16.954/19.909 ms (840 frames).
access: 53.3 fps mean; frame mean/p95/p99/max 18.757/22.692/24.338/25.410 ms; GPU mean/p95 18.182/21.929 ms (840 frames).

balanced85: r.ScreenPercentage 85,r.Shadow.Virtual.NonNanite.IncludeInCoarsePages 0,r.Shadow.Virtual.SMRT.RayCountDirectional 4,r.Shadow.Virtual.ResolutionLodBiasDirectional -0.5
river: 90.1 fps mean; frame mean/p95/p99/max 11.103/13.085/14.161/87.260 ms; GPU mean/p95 10.630/12.168 ms (840 frames).
bog214: 68.4 fps mean; frame mean/p95/p99/max 14.626/17.936/19.229/19.607 ms; GPU mean/p95 14.121/16.574 ms (840 frames).
bog552: 65.1 fps mean; frame mean/p95/p99/max 15.364/18.409/20.025/49.819 ms; GPU mean/p95 14.800/17.590 ms (840 frames).
access: 60.3 fps mean; frame mean/p95/p99/max 16.584/20.413/21.236/22.599 ms; GPU mean/p95 16.027/19.597 ms (840 frames).

lod85: r.ScreenPercentage 85,r.Shadow.Virtual.NonNanite.IncludeInCoarsePages 0,r.Shadow.Virtual.SMRT.RayCountDirectional 4,r.Shadow.Virtual.ResolutionLodBiasDirectional -0.5,r.StaticMeshLODDistanceScale 2
river: 98.1 fps mean; frame mean/p95/p99/max 10.194/12.267/13.721/18.531 ms; GPU mean/p95 9.566/11.182 ms (840 frames).
bog214: 86.6 fps mean; frame mean/p95/p99/max 11.543/13.379/14.751/16.216 ms; GPU mean/p95 11.042/12.673 ms (840 frames).
bog552: 82.4 fps mean; frame mean/p95/p99/max 12.143/14.256/16.136/16.705 ms; GPU mean/p95 11.617/13.582 ms (840 frames).
access: 74.7 fps mean; frame mean/p95/p99/max 13.383/16.086/17.156/52.720 ms; GPU mean/p95 12.761/15.609 ms (840 frames).

drive85: r.ScreenPercentage 85,r.Shadow.Virtual.NonNanite.IncludeInCoarsePages 0,r.Shadow.Virtual.SMRT.RayCountDirectional 4,r.Shadow.Virtual.ResolutionLodBiasDirectional -0.5,r.StaticMeshLODDistanceScale 2
river: 96.4 fps mean; frame mean/p95/p99/max 10.377/12.873/13.396/14.440 ms; GPU mean/p95 9.865/11.719 ms (440 frames).
bog214: 66.4 fps mean; frame mean/p95/p99/max 15.056/17.268/18.545/22.018 ms; GPU mean/p95 14.238/16.051 ms (440 frames).
bog552: 67.3 fps mean; frame mean/p95/p99/max 14.857/17.488/19.104/29.942 ms; GPU mean/p95 14.071/16.434 ms (440 frames).
access: 57.8 fps mean; frame mean/p95/p99/max 17.302/20.967/22.642/27.268 ms; GPU mean/p95 16.418/19.453 ms (440 frames).

dynamic: r.ScreenPercentage 85,r.Shadow.Virtual.NonNanite.IncludeInCoarsePages 0,r.Shadow.Virtual.SMRT.RayCountDirectional 4,r.Shadow.Virtual.ResolutionLodBiasDirectional -0.5,r.StaticMeshLODDistanceScale 2,r.DynamicRes.MinScreenPercentage 60,r.DynamicRes.MaxScreenPercentage 85,r.DynamicRes.FrameTimeBudget 14,r.DynamicRes.OperationMode 2
river: 95.6 fps mean; frame mean/p95/p99/max 10.460/12.962/13.762/14.316 ms; GPU mean/p95 9.918/12.456 ms (440 frames).
bog214: 69.6 fps mean; frame mean/p95/p99/max 14.367/16.411/17.800/27.103 ms; GPU mean/p95 13.480/15.431 ms (440 frames).
bog552: 72.7 fps mean; frame mean/p95/p99/max 13.749/16.473/17.643/28.791 ms; GPU mean/p95 12.837/15.475 ms (440 frames).
access: 60.4 fps mean; frame mean/p95/p99/max 16.568/21.006/22.632/24.872 ms; GPU mean/p95 15.109/17.888 ms (440 frames).

Native bottleneck: basepass, prepass and shadow geometry; game thread usually
below budget. PIE overstates cost. 85% TSR plus lower shadow samples/coarse
pages alone failed the target. Static mesh LOD distance scale 2 passed the
stationary p95 gate but failed while driving at access. Dynamic resolution
60-85%, 14ms target improved bogs but still failed access; it hit 60% minimum
there, indicating resolution alone is insufficient. Do not claim those
intermediate runs deliver a steady 60. Some isolated GC-related long frames
remain in uncapped captures. No experimental GC settings enabled.

Next measured change: component WPO disable distance 30m for canopy, 25m for
understory/river dressing only. Near wind stays; current grass/deformation and
water components excluded. Same meshes/transforms/collision/counts. New helper
lidar_render_budget.py, RenderBudget mode; Polish reapplies it before saving.
Pre-change level backup is in the helper report. Final target validation below.

PF60 correction and CPU fix (2026-10-19 continuation):
The user correctly challenged the foliage-wind explanation. import_native_plants.py
uses dense_tussock_material.configure, which has no WPO connection; canopy uses
the same M_NZ_Foliage parent. Only grass has authored sway. The 25/30m decorative
WPO limits were ineffective, not a measured wind saving. Removed RenderBudget
mode/helper and Polish hook, restored L_LidarStudy.umap byte-for-byte from the
PF60 pre-experiment backup (SHA256 equality checked). All earlier river/track
work remains in that backup. A saved-material audit accompanies TreadCheck.

The actual CPU fix is GTMudRunnerVisual.cpp/.h: separate procedural component
per 256-segment tread section, same 4096-segment ring, 16 sections/material and
clipping equations. UE ProceduralMeshComponent CreateMeshSection recreates the
whole scene proxy; one component previously uploaded all older sections whenever
a new section changed. Access driving EndOfFrameUpdates mean fell from 6.193ms
(wind85) to .737ms (tread85). GPU still limited access: tread85 mean59.3fps,
p95 frame19.543ms, GPU15.984/17.993ms mean/p95. This is NOT yet a 60fps pass.
Build passed after fixing a TObjectPtr range-loop declaration. Added real-map
TreadCheck for section isolation, bounded capacity/wrap and unchanged collision.

PF60 additional measured candidates (all standalone driving, normal exit0):
shadow85: r.ScreenPercentage 85,r.Shadow.Virtual.NonNanite.IncludeInCoarsePages 0,r.Shadow.Virtual.SMRT.RayCountDirectional 4,r.Shadow.Virtual.ResolutionLodBiasDirectional 0.5,r.StaticMeshLODDistanceScale 2,r.Shadow.Virtual.Clipmap.WPODisableDistance.LodBias 0
('river', 96.6, 12.786, None, None)
('bog214', 70.4, 16.948, None, None)
('bog552', 70.5, 16.864, None, None)
('access', 57.7, 21.748, None, None)
lod3: r.ScreenPercentage 85,r.Shadow.Virtual.NonNanite.IncludeInCoarsePages 0,r.Shadow.Virtual.SMRT.RayCountDirectional 4,r.Shadow.Virtual.ResolutionLodBiasDirectional -0.5,r.StaticMeshLODDistanceScale 3
('river', 98.1, 12.589, None, 4.27)
('bog214', 75.2, 15.666, None, 10.84)
('bog552', 73.9, 16.044, None, 21.44)
('access', 61.5, 18.578, None, 36.85)
adaptive: r.ScreenPercentage 85,r.Shadow.Virtual.NonNanite.IncludeInCoarsePages 0,r.Shadow.Virtual.SMRT.RayCountDirectional 4,r.Shadow.Virtual.ResolutionLodBiasDirectional -0.5,r.StaticMeshLODDistanceScale 3,r.DynamicRes.MinScreenPercentage 70,r.DynamicRes.MaxScreenPercentage 85,r.DynamicRes.FrameTimeBudget 13,r.DynamicRes.OperationMode 2
('river', 93.6, 13.255, {'min': 85.0, 'mean': 85.0, 'max': 85.0}, 3.92)
('bog214', 73.4, 15.806, {'min': 70.0, 'mean': 71.98, 'max': 82.46}, 13.13)
('bog552', 73.7, 16.21, {'min': 70.0, 'mean': 70.08, 'max': 72.48}, 21.5)
('access', 61.3, 18.619, {'min': 70.0, 'mean': 70.0, 'max': 70.0}, 40.2)
csm: r.ScreenPercentage 85,r.Shadow.Virtual.Enable 0,r.StaticMeshLODDistanceScale 2
('river', 80.4, 15.379, None, 4.08)
('bog214', 47.2, 22.823, None, 22.34)
('bog552', 56.2, 20.712, None, 21.36)
('access', 49.6, 22.988, None, 39.95)
All still miss the access p95 target. Conventional shadows were distinctly slower and rejected.
Saved material audit: M_NZ_Foliage, M_NZ_Bark and all four baked canopy far-card parents have no WPO input.
First TreadCheck stopped on a Python API naming error (KismetProceduralMeshLibrary is exposed as ProceduralMeshLibrary); corrected for rerun.
More detailed lod3 access CSV: game thread9.324ms, render thread16.257ms; render-thread Visibility wait5.540ms. GPU time alone does not isolate a pure shader/pixel bottleneck.

PF60 selected candidate (before capped validation):
visibility: r.ScreenPercentage 85,r.Shadow.Virtual.NonNanite.IncludeInCoarsePages 0,r.Shadow.Virtual.SMRT.RayCountDirectional 4,r.Shadow.Virtual.ResolutionLodBiasDirectional -0.5,r.StaticMeshLODDistanceScale 3,r.HZBOcclusion 1,r.Shadow.Virtual.Clipmap.LastLevel 17
('river', 101.9, {'mean_ms': 9.811, 'p95_ms': 11.338, 'p99_ms': 12.396, 'max_ms': 14.153, 'samples': 440}, {'mean_ms': 9.097, 'p95_ms': 10.897, 'p99_ms': 11.871, 'max_ms': 12.085, 'samples': 440}, 4.29)
('bog214', 78.8, {'mean_ms': 12.687, 'p95_ms': 15.073, 'p99_ms': 16.008, 'max_ms': 27.049, 'samples': 440}, {'mean_ms': 11.403, 'p95_ms': 13.484, 'p99_ms': 13.947, 'max_ms': 14.445, 'samples': 440}, 11.19)
('bog552', 79.6, {'mean_ms': 12.569, 'p95_ms': 14.678, 'p99_ms': 15.639, 'max_ms': 27.412, 'samples': 440}, {'mean_ms': 11.786, 'p95_ms': 13.767, 'p99_ms': 14.472, 'max_ms': 14.785, 'samples': 440}, 21.55)
('access', 65.1, {'mean_ms': 15.363, 'p95_ms': 17.964, 'p99_ms': 28.974, 'max_ms': 31.651, 'samples': 440}, {'mean_ms': 14.273, 'p95_ms': 16.32, 'p99_ms': 17.095, 'max_ms': 18.521, 'samples': 440}, 36.62)
balanced75: r.ScreenPercentage 75,r.Shadow.Virtual.NonNanite.IncludeInCoarsePages 0,r.Shadow.Virtual.SMRT.RayCountDirectional 4,r.Shadow.Virtual.ResolutionLodBiasDirectional 0.5,r.Shadow.Virtual.ResolutionLodBiasDirectionalMoving 0.5,r.StaticMeshLODDistanceScale 3,r.HZBOcclusion 1,r.Shadow.Virtual.Clipmap.LastLevel 17
('river', 106.7, {'mean_ms': 9.375, 'p95_ms': 11.21, 'p99_ms': 12.03, 'max_ms': 12.896, 'samples': 440}, {'mean_ms': 8.472, 'p95_ms': 10.292, 'p99_ms': 11.199, 'max_ms': 11.542, 'samples': 440}, 2.78)
('bog214', 78.9, {'mean_ms': 12.678, 'p95_ms': 14.74, 'p99_ms': 16.327, 'max_ms': 26.151, 'samples': 440}, {'mean_ms': 11.46, 'p95_ms': 13.385, 'p99_ms': 13.748, 'max_ms': 14.224, 'samples': 440}, 11.35)
('bog552', 79.7, {'mean_ms': 12.55, 'p95_ms': 14.767, 'p99_ms': 17.887, 'max_ms': 27.575, 'samples': 440}, {'mean_ms': 11.661, 'p95_ms': 13.764, 'p99_ms': 14.338, 'max_ms': 16.774, 'samples': 440}, 21.47)
('access', 67.8, {'mean_ms': 14.742, 'p95_ms': 16.867, 'p99_ms': 27.081, 'max_ms': 30.88, 'samples': 440}, {'mean_ms': 13.695, 'p95_ms': 15.463, 'p99_ms': 15.889, 'max_ms': 16.418, 'samples': 440}, 36.54)
balanced75 passes the short uncapped p95 <=16.9ms check. Isolated27-31ms spikes remain; not a full-route lock.
Art/lidar_performance.json stores this profile plus t.MaxFPS60; open_lidar_study.ps1 uses it on launch (Play at1600x900). -OriginalQuality skips launch overrides. -ShowFPS displays the counter. Profile script -UseSavedProfile tests the exact commands; -Uncapped removes only the cap. No global engine config edits.

PF60 capped saved-preset validation:
('river', 60.0, {'mean_ms': 16.666, 'p95_ms': 17.954, 'p99_ms': 18.64, 'max_ms': 20.252, 'samples': 440}, {'mean_ms': 8.489, 'p95_ms': 10.184, 'p99_ms': 11.234, 'max_ms': 11.433, 'samples': 440}, 3.86)
('bog214', 60.0, {'mean_ms': 16.67, 'p95_ms': 21.082, 'p99_ms': 22.937, 'max_ms': 25.194, 'samples': 440}, {'mean_ms': 11.981, 'p95_ms': 13.529, 'p99_ms': 14.093, 'max_ms': 16.556, 'samples': 440}, 16.47)
('bog552', 60.0, {'mean_ms': 16.669, 'p95_ms': 20.28, 'p99_ms': 21.766, 'max_ms': 23.684, 'samples': 440}, {'mean_ms': 11.029, 'p95_ms': 13.228, 'p99_ms': 14.319, 'max_ms': 14.846, 'samples': 440}, 21.35)
('access', 60.0, {'mean_ms': 16.67, 'p95_ms': 19.624, 'p99_ms': 20.675, 'max_ms': 23.128, 'samples': 440}, {'mean_ms': 13.838, 'p95_ms': 16.121, 'p99_ms': 16.934, 'max_ms': 17.247, 'samples': 440}, 39.81)
All four means60.0fps; capped FrameTime p95 is17.954/21.082/20.280/19.624ms, so do not claim perfect 16.67ms pacing or a full-route locked60. This is a usable 60fps-average preset with measured uncapped headroom and remaining pacing variation. Captures are offscreen standalone Development, short straight throttle inputs (sometimes entering the verge), not a full-route steering assessment.

PF60 final regression: TreadCheck passed with normal exit0. Closed section geometry unchanged after append; ring wraps at4096 segments,16 components with one section each, common material and no collision. Actual material audit confirms no tree/fern WPO. Saved map SHA256 matches pre-FPS backup: 644bf03863ee48cb247993dda3b8f717e9b2042cd480e499b787f26f3a9cb751. Evidence Saved/LidarAuthoringQA/PF60/result.json. Source compiled successfully; no commits. Owner drive remains the gate.

PF60 pacing correction (2026-10-20 UTC):
The previous capped CSV used -csvCaptureFrames, which forces legacy end-of-frame timing. UE CsvProfiler.cpp UpdateFrameTime documents that mixing cap waits with variable work creates false pacing noise. Runtime CsvProfile FRAMES=5000 with csv.UseLegacyFrameTime0 measures logical boundaries after the tick-rate wait. This corrects measurement, not rendering performance; prior uncapped results remain useful. No quality preset/map edits in this follow-up.
Art/profile_lidar_play.ps1 now starts a runtime capture; analyze_lidar_play_perf.py labels the timing method and states that it is not presentation timing. GTPerfProbe.cpp schema2 reports engine logical delta as frame_ms and retains wall-clock end_frame_interval_ms; logical delta can be overridden by fixed-step simulation. A worker cost affects the next logical interval, so same-frame correlation is not causation. Build passed.
logical60:
('river', 60.0, {'mean_ms': 16.668, 'p95_ms': 16.681, 'p99_ms': 16.702, 'max_ms': 16.846, 'samples': 440}, {'mean_ms': 8.609, 'p95_ms': 10.82, 'p99_ms': 11.171, 'max_ms': 12.166, 'samples': 440}, 3.84)
('bog214', 60.0, {'mean_ms': 16.671, 'p95_ms': 16.679, 'p99_ms': 16.908, 'max_ms': 17.16, 'samples': 440}, {'mean_ms': 11.276, 'p95_ms': 12.606, 'p99_ms': 13.224, 'max_ms': 13.851, 'samples': 440}, 16.94)
('bog552', 60.0, {'mean_ms': 16.669, 'p95_ms': 16.684, 'p99_ms': 16.773, 'max_ms': 16.955, 'samples': 440}, {'mean_ms': 10.031, 'p95_ms': 12.071, 'p99_ms': 13.058, 'max_ms': 13.566, 'samples': 440}, 17.13)
('access', 60.0, {'mean_ms': 16.669, 'p95_ms': 16.685, 'p99_ms': 16.777, 'max_ms': 16.838, 'samples': 440}, {'mean_ms': 11.39, 'p95_ms': 13.21, 'p99_ms': 13.55, 'max_ms': 14.213, 'samples': 440}, 36.3)
pacingcheck60:
('river', 60.0, {'mean_ms': 16.667, 'p95_ms': 16.674, 'p99_ms': 16.692, 'max_ms': 16.714, 'samples': 440}, {'mean_ms': 8.65, 'p95_ms': 10.865, 'p99_ms': 11.135, 'max_ms': 11.983, 'samples': 440}, 3.84)
('bog214', 60.0, {'mean_ms': 16.668, 'p95_ms': 16.677, 'p99_ms': 16.701, 'max_ms': 16.784, 'samples': 440}, {'mean_ms': 11.697, 'p95_ms': 12.907, 'p99_ms': 13.833, 'max_ms': 16.557, 'samples': 440}, 17.26)
('bog552', 60.0, {'mean_ms': 16.669, 'p95_ms': 16.682, 'p99_ms': 16.708, 'max_ms': 16.995, 'samples': 440}, {'mean_ms': 10.203, 'p95_ms': 12.009, 'p99_ms': 12.384, 'max_ms': 12.686, 'samples': 440}, 21.48)
('access', 60.0, {'mean_ms': 16.668, 'p95_ms': 16.675, 'p99_ms': 16.705, 'max_ms': 17.05, 'samples': 440}, {'mean_ms': 11.278, 'p95_ms': 12.835, 'p99_ms': 13.793, 'max_ms': 14.535, 'samples': 440}, 36.36)
Both runs pass all four logical p95<=16.9ms windows at1600x900 with the existing saved preset. GTPerf logical statistics agree; retained end-interval series still shows the old noise. This does not establish swapchain presentation timing, entire-route performance or owner acceptance. No new foliage animation or density reduction. Map SHA256 unchanged: 644bf03863ee48cb247993dda3b8f717e9b2042cd480e499b787f26f3a9cb751.
Evidence Saved/LidarAuthoringQA/PF60-pacing/result.json, CSVs, logs and probe reports; prior PF60 evidence retained.


GS3 (2026-10-20): grounded BOTW-inspired grass installed directly in L_LidarStudy. Owner acceptance pending.
New map-owned GrassGS3 meshes: 3 near variants 144/40/12 triangles, 48/20/6 blades, root footprint70cm, height27-47cm; far patch72/12 triangles, 36/12 blades, 2m root footprint. Vertex-colour dark roots/olive-green tips,9% dry blades. Near approximate LOD transitions7/16m, fade32-40m,55cm spacing,46m stream radius. Far overlaps25-38m, fades125-150m,2m spacing,180m streaming guard radius. Independent component LOD scaling compensates the saved preset's global scale3. Far wind fades65-90m; no far collision, shadows or contact metadata. Existing incremental time-sliced streaming retained.
M_GS3_Near retains wheel/deformation response and wind, removes artificial glow/rim/flowers. M_GS3_Far uses cheap vertex colour, upward normals and simple wind. M_Terrain/M_Detail pasture inputs now share blade field-scale colour and compressed flattened-grass/thatch detail from EXISTING bitmap textures. No new photographic/AI texture generated. Native plant assets and rank grass remain separate.
Grass install/check modes: Art/lidar_place.ps1 -Mode Grass / GrassCheck. Install restores GS3 properties when assets exist; Polish reapplies GS3 material edits. Blueprint/map properties opt in; other maps keep legacy behavior. gt.Grass.Distance toggles distant grass for comparison. Art/open_lidar_study.ps1 -Play -Paddock -ShowFPS starts the actual paddock.
Build, import triangle budgets and material compilation passed. GrassCheck normal exit0: near21982 (7461/7190/7331), distant11736. Radial bins <=40/80/125/150/180m:1261/3762/5289/1291/122. Near full-reference rebuild missing0/extra0 in all layers. Contact after test bent33/22/27, removed10/5/9. Ground output digest preserved DB443C52AD8AD4F3A1E2CD57E8E4716F. Full prechange map/material backup Saved/LidarAuthoringBackups/GS3-1792517216377900300.
Performance: unchanged saved1600x900 TSR75 preset, logical runtime CSV, screenshots/teleport warmup excluded. Uncapped drives have matching starts/input schedules, not identical trajectories (elapsed time depends on frame rate). No blanket performance improvement claimed.
gs3-before:
  paddock_mid: meanFPS=73.5; frame={'mean_ms': 13.607, 'p95_ms': 17.885, 'p99_ms': 21.873, 'max_ms': 25.46, 'samples': 440}; GPU={'mean_ms': 10.735, 'p95_ms': 12.246, 'p99_ms': 12.73, 'max_ms': 13.415, 'samples': 440}; GameThread={'mean_ms': 9.599, 'p95_ms': 13.465, 'p99_ms': 15.21, 'max_ms': 15.965, 'samples': 440}
  paddock_gate: meanFPS=99.4; frame={'mean_ms': 10.059, 'p95_ms': 12.548, 'p99_ms': 13.869, 'max_ms': 26.174, 'samples': 440}; GPU={'mean_ms': 8.026, 'p95_ms': 9.989, 'p99_ms': 10.954, 'max_ms': 11.703, 'samples': 440}; GameThread={'mean_ms': 5.979, 'p95_ms': 7.972, 'p99_ms': 9.183, 'max_ms': 9.753, 'samples': 440}
  river: meanFPS=104.8; frame={'mean_ms': 9.544, 'p95_ms': 11.387, 'p99_ms': 12.057, 'max_ms': 12.35, 'samples': 440}; GPU={'mean_ms': 8.523, 'p95_ms': 10.571, 'p99_ms': 11.435, 'max_ms': 11.63, 'samples': 440}; GameThread={'mean_ms': 4.877, 'p95_ms': 6.065, 'p99_ms': 6.756, 'max_ms': 9.087, 'samples': 440}
  access: meanFPS=75.9; frame={'mean_ms': 13.176, 'p95_ms': 15.724, 'p99_ms': 22.104, 'max_ms': 29.044, 'samples': 440}; GPU={'mean_ms': 11.946, 'p95_ms': 13.238, 'p99_ms': 13.813, 'max_ms': 14.297, 'samples': 440}; GameThread={'mean_ms': 8.541, 'p95_ms': 11.664, 'p99_ms': 12.79, 'max_ms': 14.652, 'samples': 440}
gs3-after:
  paddock_mid: meanFPS=76.1; frame={'mean_ms': 13.149, 'p95_ms': 19.364, 'p99_ms': 23.029, 'max_ms': 26.521, 'samples': 440}; GPU={'mean_ms': 10.398, 'p95_ms': 11.809, 'p99_ms': 12.239, 'max_ms': 12.65, 'samples': 440}; GameThread={'mean_ms': 8.683, 'p95_ms': 12.246, 'p99_ms': 13.512, 'max_ms': 14.746, 'samples': 440}
  paddock_gate: meanFPS=93.5; frame={'mean_ms': 10.7, 'p95_ms': 13.883, 'p99_ms': 14.931, 'max_ms': 25.776, 'samples': 440}; GPU={'mean_ms': 8.09, 'p95_ms': 10.335, 'p99_ms': 11.35, 'max_ms': 11.816, 'samples': 440}; GameThread={'mean_ms': 6.493, 'p95_ms': 9.218, 'p99_ms': 10.522, 'max_ms': 12.054, 'samples': 440}
  river: meanFPS=105.3; frame={'mean_ms': 9.496, 'p95_ms': 10.981, 'p99_ms': 11.671, 'max_ms': 13.075, 'samples': 440}; GPU={'mean_ms': 8.605, 'p95_ms': 10.787, 'p99_ms': 11.41, 'max_ms': 11.586, 'samples': 440}; GameThread={'mean_ms': 4.811, 'p95_ms': 5.836, 'p99_ms': 6.279, 'max_ms': 7.118, 'samples': 440}
  access: meanFPS=74.6; frame={'mean_ms': 13.404, 'p95_ms': 16.973, 'p99_ms': 21.196, 'max_ms': 29.655, 'samples': 440}; GPU={'mean_ms': 12.106, 'p95_ms': 13.221, 'p99_ms': 13.914, 'max_ms': 14.308, 'samples': 440}; GameThread={'mean_ms': 8.649, 'p95_ms': 12.005, 'p99_ms': 12.99, 'max_ms': 15.578, 'samples': 440}
gs3-final60:
  paddock_mid: meanFPS=59.9; frame={'mean_ms': 16.692, 'p95_ms': 16.686, 'p99_ms': 17.209, 'max_ms': 20.149, 'samples': 440}; GPU={'mean_ms': 10.503, 'p95_ms': 11.845, 'p99_ms': 12.392, 'max_ms': 12.831, 'samples': 440}; GameThread={'mean_ms': 9.029, 'p95_ms': 12.777, 'p99_ms': 15.012, 'max_ms': 16.75, 'samples': 440}
  paddock_gate: meanFPS=60.0; frame={'mean_ms': 16.667, 'p95_ms': 16.685, 'p99_ms': 16.693, 'max_ms': 16.835, 'samples': 440}; GPU={'mean_ms': 8.516, 'p95_ms': 11.028, 'p99_ms': 11.535, 'max_ms': 12.01, 'samples': 440}; GameThread={'mean_ms': 5.673, 'p95_ms': 7.546, 'p99_ms': 8.931, 'max_ms': 11.117, 'samples': 440}
  river: meanFPS=59.8; frame={'mean_ms': 16.723, 'p95_ms': 16.675, 'p99_ms': 16.688, 'max_ms': 41.531, 'samples': 440}; GPU={'mean_ms': 8.53, 'p95_ms': 10.797, 'p99_ms': 11.243, 'max_ms': 12.101, 'samples': 440}; GameThread={'mean_ms': 4.625, 'p95_ms': 5.627, 'p99_ms': 6.817, 'max_ms': 41.367, 'samples': 440}
  access: meanFPS=60.0; frame={'mean_ms': 16.669, 'p95_ms': 16.68, 'p99_ms': 16.78, 'max_ms': 16.843, 'samples': 440}; GPU={'mean_ms': 11.838, 'p95_ms': 13.465, 'p99_ms': 14.272, 'max_ms': 15.089, 'samples': 440}; GameThread={'mean_ms': 8.989, 'p95_ms': 12.621, 'p99_ms': 14.018, 'max_ms': 15.043, 'samples': 440}
gs3-distance:
  paddock_mid: meanFPS=75.9; frame={'mean_ms': 13.18, 'p95_ms': 19.664, 'p99_ms': 20.77, 'max_ms': 29.248, 'samples': 1840}; GPU={'mean_ms': 8.336, 'p95_ms': 10.474, 'p99_ms': 11.305, 'max_ms': 12.461, 'samples': 1840}; GameThread={'mean_ms': 6.471, 'p95_ms': 8.894, 'p99_ms': 10.18, 'max_ms': 13.041, 'samples': 1840}
  fully warmed stationary distant on/off={"on": {"FrameTime": {"mean_ms": 13.012, "p95_ms": 19.891, "p99_ms": 21.392, "max_ms": 26.968, "samples": 290}, "GPUTime": {"mean_ms": 8.262, "p95_ms": 10.038, "p99_ms": 11.169, "max_ms": 11.2, "samples": 290}, "GameThreadTime": {"mean_ms": 6.385, "p95_ms": 8.65, "p99_ms": 10.18, "max_ms": 10.386, "samples": 290}}, "off": {"FrameTime": {"mean_ms": 13.057, "p95_ms": 19.567, "p99_ms": 21.363, "max_ms": 21.806, "samples": 290}, "GPUTime": {"mean_ms": 8.268, "p95_ms": 10.011, "p99_ms": 11.823, "max_ms": 12.073, "samples": 290}, "GameThreadTime": {"mean_ms": 6.441, "p95_ms": 8.675, "p99_ms": 10.019, "max_ms": 11.475, "samples": 290}}}
  paddock_gate: meanFPS=98.3; frame={'mean_ms': 10.169, 'p95_ms': 12.231, 'p99_ms': 14.885, 'max_ms': 16.565, 'samples': 1840}; GPU={'mean_ms': 8.266, 'p95_ms': 9.312, 'p99_ms': 11.408, 'max_ms': 12.877, 'samples': 1840}; GameThread={'mean_ms': 5.816, 'p95_ms': 7.617, 'p99_ms': 8.448, 'max_ms': 9.511, 'samples': 1840}
  fully warmed stationary distant on/off={"on": {"FrameTime": {"mean_ms": 10.007, "p95_ms": 11.382, "p99_ms": 12.247, "max_ms": 14.633, "samples": 290}, "GPUTime": {"mean_ms": 8.445, "p95_ms": 9.541, "p99_ms": 11.9, "max_ms": 12.877, "samples": 290}, "GameThreadTime": {"mean_ms": 5.742, "p95_ms": 7.397, "p99_ms": 8.674, "max_ms": 9.017, "samples": 290}}, "off": {"FrameTime": {"mean_ms": 9.896, "p95_ms": 11.149, "p99_ms": 11.907, "max_ms": 12.148, "samples": 290}, "GPUTime": {"mean_ms": 8.367, "p95_ms": 9.493, "p99_ms": 11.714, "max_ms": 12.06, "samples": 290}, "GameThreadTime": {"mean_ms": 5.652, "p95_ms": 7.15, "p99_ms": 8.069, "max_ms": 8.822, "samples": 290}}}
Capped four drives average59.8-60.0fps, all logical p95<=16.9ms; worst river frame41.531ms, paddock20.149ms. This is NOT perfect lock or whole-route/display proof. Distant on/off mean GPU deltas about-0.006/+0.078ms in two fixed chase views, near measurement noise and view dependent; not a zero-cost claim. Uncapped paddock p95 regresses17.885->19.364ms despite meanGPU improving10.735->10.398ms; retained as a limitation. Grass streaming worker scopes remained below2ms in the paddock drive. Visual QA ground/chase/overview and exact-view far-off captures saved.
Evidence Saved/LidarAuthoringQA/GS3/result.json plus CSVs, logs, probes, reports and images. No commits. Owner drive is the gate.


GS3-2 (2026-10-20 UTC): owner feedback - visible distant cutoff, more sway, remove car noise, smaller toggleable info panel.
Kept the150m outer grass limit, density, meshes and saved graphics preset. Far blades shrink into the ground from85-145m; spatially varying density fade starts around90m and ends147m, with the existing125-150m instance cull fade as a final bound. Distant wind fades100-140m. Ground pasture now has filtered world-space tuft/strand variation plus the existing bitmap detail; green albedo(.15,.20,.078) better matches standing cover. No new texture bitmap. Near GS1Wind now uses two coherent travelling waves, peak tip offset16.8cm at the retained scale2 before contact/masking; roots remain anchored. Far uses the same phases with peak10.2cm before distance fading.
GTMudLab controller mutes only its car audio component on possession. Engine, tyre, skid and impact synth silent; environment audio untouched. Compact HUD338x72 instead of580x174 at reference1440wide, opacity.68,85% text scale; speed/range/diffs, sink/water, minimal key hint. F1 binding toggles bShowDriveInfo; global bShowHUD also respected.
Build passed. Focused Grass installer initially hit transient disconnected-input compile warnings, then an exit access violation after a successful save. Reworked materials to update nodes in place, removed the persistent AssetTools UObject reference, and avoided redundant map saves with float-tolerant actor comparison. Final Grass install returned0 with no material errors; independent saved-map GrassCheck returned0 and passed. Hidden-PIE forced-key injection did not validate F1 reliably; handler and rendered visibility checked there, physical keyboard check is recorded separately.
GrassCheck: wind scale2; car muted=true,playing=false,RMS0. Near21982,far11736; full-reference near streaming missing0/extra0. All three layers still bend and remove under contact. Ground digest DB443C52AD8AD4F3A1E2CD57E8E4716F unchanged. Actual ground/chase/overview, hidden HUD and two-time sway images retained in Saved/LidarAuthoringQA/GS3-2.
Performance: unchanged1600x900 TSR75 saved preset, standalone offscreen logical runtime CSV, four short same-start driving samples; loading, screenshots and teleports excluded.
paddock_mid: meanFPS=60.0; frame={'mean_ms': 16.669, 'p95_ms': 16.674, 'p99_ms': 16.711, 'max_ms': 17.019, 'samples': 440}; GPU={'mean_ms': 10.332, 'p95_ms': 11.688, 'p99_ms': 11.972, 'max_ms': 12.237, 'samples': 440}; GameThread={'mean_ms': 8.715, 'p95_ms': 12.22, 'p99_ms': 13.828, 'max_ms': 15.824, 'samples': 440}
paddock_gate: meanFPS=60.0; frame={'mean_ms': 16.668, 'p95_ms': 16.673, 'p99_ms': 16.699, 'max_ms': 16.752, 'samples': 440}; GPU={'mean_ms': 7.92, 'p95_ms': 10.593, 'p99_ms': 11.177, 'max_ms': 11.511, 'samples': 440}; GameThread={'mean_ms': 5.825, 'p95_ms': 7.352, 'p99_ms': 8.488, 'max_ms': 10.683, 'samples': 440}
river: meanFPS=59.8; frame={'mean_ms': 16.717, 'p95_ms': 16.674, 'p99_ms': 16.696, 'max_ms': 38.434, 'samples': 440}; GPU={'mean_ms': 8.281, 'p95_ms': 10.296, 'p99_ms': 11.285, 'max_ms': 12.069, 'samples': 440}; GameThread={'mean_ms': 4.618, 'p95_ms': 5.528, 'p99_ms': 6.352, 'max_ms': 37.89, 'samples': 440}
access: meanFPS=60.0; frame={'mean_ms': 16.67, 'p95_ms': 16.683, 'p99_ms': 16.799, 'max_ms': 16.962, 'samples': 440}; GPU={'mean_ms': 11.645, 'p95_ms': 12.931, 'p99_ms': 13.774, 'max_ms': 14.402, 'samples': 440}; GameThread={'mean_ms': 8.915, 'p95_ms': 12.254, 'p99_ms': 13.219, 'max_ms': 14.232, 'samples': 440}
All four logical p95<=16.9ms; means59.8-60.0fps, isolated38.434ms river hitch. No full-route/display-presentation or perfect-lock claim. Owner drive remains the gate. No commits. Evidence Saved/LidarAuthoringQA/GS3-2/result.json.

LP6 production-level polish - 2026-10-20 UTC
Plan: docs/LIDAR_LEVEL_POLISH.md. Implemented directly in L_LidarStudy; no separate test section. Owner photos remain the look reference.
Water: replaced baked/local overlap masking; clipped static geometry against final bed. Coverage LP6-coverage-2: 192028 triangles (formerly189058),112828 vertices,124253 ground samples,100cm grid,250cm shore envelope. Existing96x96/62.5cm live window retained; dirty-bed refresh capped10Hz. Native soil texture clips live shore; closed mud basins retain finite volume.
Ground digest unchanged: DB443C52AD8AD4F3A1E2CD57E8E4716F. Domain SHA256: 60d19219ba83bba77f26eebf65375af48f96daaaeb942974d93d7c7a8d28952d.
Grounding: final-relief seating, ground-pivot living plants, source kit bounds for future tree sizing, slope/footprint checks for debris. Saved-map sampled roots=3198; maxerror_cm=0.0.
Foliage: four far-card materials use rounded crown normals and0.58-0.82 crown shading. Canopy/understory LODdistance scales2.0/1.6. Map-owned two-sided leaf material blends18% rounded normal,20% subsurface colour,roughness0.85/specular0.05; original kit retained.
Dressing: instances12242/components99/solid61. Sixteen non-colliding native-ground groups all bound (GTLS_Ready1). S/M mesh scale0.65-1.25,25-45m fade,no small-detail shadows;178 steep placements skipped. Existing large rocks/logs and crossing clearance retained.
Water saved-map regression: previously dry point [-47938.65804392218, -37813.65804392218]; {"point": [-47938.65804392218, -37813.65804392218], "gap_cm": 0.8848780393600464, "before_cm": -1.1688328981399536, "after_cm": -3.4159278869628906, "wet_before": false, "wet_after": true, "depth_cm": 1.3231544494628906, "authoring_depth_cm": 1.3231544494628906, "diagnostics": "GTWATERSTATS GTWaterSheet_1 (Domain): 1298 frames, frame 18.70 ms mean / 400.00 worst (53 fps mean), field step 0.352 ms mean / 2.883 worst over 1298 stepping frames, sub-steps 1421 asked / 1386 run (cap 4, burst 8 of 0.0167 s), clamps 5, deficit 0.572 s; since the field was built: 1 coarse frames (the last at a Courant number of 0.20) and 1 frames dropped by the 0.25 s bound"}. Review contacts must span frames because native contacts MAX-composite per frame.
Build7 succeeded. Final numerical regressions: {"succeeded": 7, "succeededWithWarnings": 0, "failed": 0, "notRun": 0, "totalDuration": 2.9253692626953125}. Final saved-map check normal exit0; earlier harness/enum failures retained and superseded.
Moving validation found cold material draw stalls84.969/105.020ms; allocating targets over frames alone did not resolve them. Shader readiness gate submits asynchronous jobs and retains prior/base water. Final ford:5 shader-wait frames,213 draws thereafter,drawpeak0.138ms,total native visualpeak3.215ms. Physics and one-active-basin budget unchanged.
All performance runs: actual saved LiDAR map, offscreen standalone,1600x900,TSR75,saved preset,t.MaxFPS60,logical-after-tick-rate-wait CSV; screenshot/teleport/loading frames excluded. lp6-before baseline; lp6-after initial installed; lp6-walk initial moving; lp6-walk-final setup-only diagnostic (not final accepted performance); lp6-ready final moving; lp6-final final stationary.
lp6-before:
  ford_walk: meanFPS=60.0; Frame={"mean_ms": 16.677, "p95_ms": 16.672, "p99_ms": 16.683, "max_ms": 25.388, "samples": 840}; GPU={"mean_ms": 8.029, "p95_ms": 9.691, "p99_ms": 10.352, "max_ms": 10.742, "samples": 840}; GameThread={"mean_ms": 5.111, "p95_ms": 6.16, "p99_ms": 7.212, "max_ms": 7.99, "samples": 840}; travel_xy_m=stationary
  bar_walk: meanFPS=60.0; Frame={"mean_ms": 16.668, "p95_ms": 16.673, "p99_ms": 16.689, "max_ms": 16.952, "samples": 840}; GPU={"mean_ms": 8.178, "p95_ms": 10.108, "p99_ms": 11.146, "max_ms": 11.966, "samples": 840}; GameThread={"mean_ms": 5.366, "p95_ms": 6.461, "p99_ms": 7.821, "max_ms": 9.142, "samples": 840}; travel_xy_m=stationary
  shallows_walk: meanFPS=59.9; Frame={"mean_ms": 16.695, "p95_ms": 16.675, "p99_ms": 16.688, "max_ms": 40.331, "samples": 840}; GPU={"mean_ms": 8.376, "p95_ms": 10.099, "p99_ms": 10.37, "max_ms": 11.956, "samples": 840}; GameThread={"mean_ms": 5.165, "p95_ms": 6.378, "p99_ms": 6.935, "max_ms": 39.698, "samples": 840}; travel_xy_m=stationary
  forest_across: meanFPS=60.0; Frame={"mean_ms": 16.667, "p95_ms": 16.672, "p99_ms": 16.68, "max_ms": 16.727, "samples": 840}; GPU={"mean_ms": 8.233, "p95_ms": 9.124, "p99_ms": 10.317, "max_ms": 11.958, "samples": 840}; GameThread={"mean_ms": 5.28, "p95_ms": 6.265, "p99_ms": 7.64, "max_ms": 8.561, "samples": 840}; travel_xy_m=stationary
lp6-after:
  ford_walk: meanFPS=60.0; Frame={"mean_ms": 16.667, "p95_ms": 16.671, "p99_ms": 16.681, "max_ms": 16.837, "samples": 840}; GPU={"mean_ms": 8.351, "p95_ms": 10.279, "p99_ms": 10.398, "max_ms": 11.335, "samples": 840}; GameThread={"mean_ms": 5.315, "p95_ms": 6.313, "p99_ms": 7.211, "max_ms": 8.77, "samples": 840}; travel_xy_m=stationary
  bar_walk: meanFPS=60.0; Frame={"mean_ms": 16.667, "p95_ms": 16.671, "p99_ms": 16.682, "max_ms": 16.806, "samples": 840}; GPU={"mean_ms": 8.602, "p95_ms": 10.668, "p99_ms": 10.781, "max_ms": 11.392, "samples": 840}; GameThread={"mean_ms": 5.59, "p95_ms": 6.623, "p99_ms": 7.95, "max_ms": 8.752, "samples": 840}; travel_xy_m=stationary
  shallows_walk: meanFPS=59.9; Frame={"mean_ms": 16.696, "p95_ms": 16.673, "p99_ms": 16.686, "max_ms": 41.203, "samples": 840}; GPU={"mean_ms": 8.898, "p95_ms": 10.637, "p99_ms": 11.52, "max_ms": 11.996, "samples": 840}; GameThread={"mean_ms": 5.521, "p95_ms": 6.528, "p99_ms": 6.828, "max_ms": 41.291, "samples": 840}; travel_xy_m=stationary
  forest_across: meanFPS=60.0; Frame={"mean_ms": 16.668, "p95_ms": 16.682, "p99_ms": 16.689, "max_ms": 16.914, "samples": 840}; GPU={"mean_ms": 8.889, "p95_ms": 9.48, "p99_ms": 10.685, "max_ms": 11.548, "samples": 840}; GameThread={"mean_ms": 5.584, "p95_ms": 6.582, "p99_ms": 7.045, "max_ms": 8.48, "samples": 840}; travel_xy_m=stationary
lp6-walk:
  ford_walk: meanFPS=59.4; Frame={"mean_ms": 16.836, "p95_ms": 16.681, "p99_ms": 16.695, "max_ms": 90.665, "samples": 440}; GPU={"mean_ms": 10.284, "p95_ms": 11.655, "p99_ms": 12.489, "max_ms": 12.998, "samples": 440}; GameThread={"mean_ms": 7.133, "p95_ms": 9.784, "p99_ms": 12.312, "max_ms": 22.086, "samples": 440}; travel_xy_m=49.41
  bar_walk: meanFPS=60.0; Frame={"mean_ms": 16.668, "p95_ms": 16.675, "p99_ms": 16.725, "max_ms": 16.965, "samples": 440}; GPU={"mean_ms": 11.445, "p95_ms": 13.295, "p99_ms": 14.502, "max_ms": 15.971, "samples": 440}; GameThread={"mean_ms": 7.179, "p95_ms": 9.723, "p99_ms": 10.885, "max_ms": 15.531, "samples": 440}; travel_xy_m=48.96
  shallows_walk: meanFPS=60.0; Frame={"mean_ms": 16.668, "p95_ms": 16.673, "p99_ms": 16.723, "max_ms": 16.824, "samples": 440}; GPU={"mean_ms": 11.971, "p95_ms": 13.934, "p99_ms": 14.871, "max_ms": 16.359, "samples": 440}; GameThread={"mean_ms": 7.48, "p95_ms": 9.673, "p99_ms": 11.175, "max_ms": 16.084, "samples": 440}; travel_xy_m=48.96
  forest_across: meanFPS=60.0; Frame={"mean_ms": 16.668, "p95_ms": 16.676, "p99_ms": 16.702, "max_ms": 16.83, "samples": 440}; GPU={"mean_ms": 12.008, "p95_ms": 13.845, "p99_ms": 14.396, "max_ms": 14.637, "samples": 440}; GameThread={"mean_ms": 7.125, "p95_ms": 9.806, "p99_ms": 10.853, "max_ms": 14.295, "samples": 440}; travel_xy_m=48.96
lp6-walk-final:
  ford_walk: meanFPS=59.2; Frame={"mean_ms": 16.882, "p95_ms": 16.684, "p99_ms": 16.726, "max_ms": 110.68, "samples": 440}; GPU={"mean_ms": 10.384, "p95_ms": 12.31, "p99_ms": 13.386, "max_ms": 14.423, "samples": 440}; GameThread={"mean_ms": 7.495, "p95_ms": 11.067, "p99_ms": 12.518, "max_ms": 22.086, "samples": 440}; travel_xy_m=49.53
  bar_walk: meanFPS=60.0; Frame={"mean_ms": 16.668, "p95_ms": 16.671, "p99_ms": 16.683, "max_ms": 16.903, "samples": 440}; GPU={"mean_ms": 11.096, "p95_ms": 12.886, "p99_ms": 13.674, "max_ms": 15.794, "samples": 440}; GameThread={"mean_ms": 6.96, "p95_ms": 9.547, "p99_ms": 10.376, "max_ms": 15.959, "samples": 440}; travel_xy_m=48.97
  shallows_walk: meanFPS=60.0; Frame={"mean_ms": 16.668, "p95_ms": 16.682, "p99_ms": 16.743, "max_ms": 16.888, "samples": 440}; GPU={"mean_ms": 11.011, "p95_ms": 12.46, "p99_ms": 13.712, "max_ms": 15.159, "samples": 440}; GameThread={"mean_ms": 7.331, "p95_ms": 9.574, "p99_ms": 11.758, "max_ms": 14.642, "samples": 440}; travel_xy_m=48.96
  forest_across: meanFPS=60.0; Frame={"mean_ms": 16.668, "p95_ms": 16.679, "p99_ms": 16.689, "max_ms": 16.907, "samples": 440}; GPU={"mean_ms": 11.309, "p95_ms": 13.185, "p99_ms": 13.57, "max_ms": 14.195, "samples": 440}; GameThread={"mean_ms": 7.195, "p95_ms": 9.803, "p99_ms": 11.373, "max_ms": 13.906, "samples": 440}; travel_xy_m=48.96
lp6-ready:
  ford_walk: meanFPS=60.0; Frame={"mean_ms": 16.673, "p95_ms": 16.681, "p99_ms": 16.738, "max_ms": 18.354, "samples": 440}; GPU={"mean_ms": 10.222, "p95_ms": 11.673, "p99_ms": 12.185, "max_ms": 12.536, "samples": 440}; GameThread={"mean_ms": 7.194, "p95_ms": 9.68, "p99_ms": 12.28, "max_ms": 15.627, "samples": 440}; travel_xy_m=48.98
  bar_walk: meanFPS=60.0; Frame={"mean_ms": 16.668, "p95_ms": 16.681, "p99_ms": 16.752, "max_ms": 16.845, "samples": 440}; GPU={"mean_ms": 11.183, "p95_ms": 12.659, "p99_ms": 14.597, "max_ms": 16.3, "samples": 440}; GameThread={"mean_ms": 7.125, "p95_ms": 9.578, "p99_ms": 11.096, "max_ms": 16.014, "samples": 440}; travel_xy_m=48.96
  shallows_walk: meanFPS=60.0; Frame={"mean_ms": 16.672, "p95_ms": 16.675, "p99_ms": 16.756, "max_ms": 17.751, "samples": 440}; GPU={"mean_ms": 10.942, "p95_ms": 12.466, "p99_ms": 13.862, "max_ms": 14.722, "samples": 440}; GameThread={"mean_ms": 7.411, "p95_ms": 9.876, "p99_ms": 12.37, "max_ms": 16.156, "samples": 440}; travel_xy_m=48.97
  forest_across: meanFPS=60.0; Frame={"mean_ms": 16.67, "p95_ms": 16.682, "p99_ms": 16.806, "max_ms": 16.924, "samples": 440}; GPU={"mean_ms": 11.711, "p95_ms": 13.253, "p99_ms": 14.29, "max_ms": 15.241, "samples": 440}; GameThread={"mean_ms": 7.367, "p95_ms": 10.351, "p99_ms": 11.26, "max_ms": 14.915, "samples": 440}; travel_xy_m=48.97
lp6-final:
  ford_walk: meanFPS=59.9; Frame={"mean_ms": 16.694, "p95_ms": 16.673, "p99_ms": 16.685, "max_ms": 38.753, "samples": 840}; GPU={"mean_ms": 8.466, "p95_ms": 10.219, "p99_ms": 11.316, "max_ms": 11.649, "samples": 840}; GameThread={"mean_ms": 5.445, "p95_ms": 6.469, "p99_ms": 6.888, "max_ms": 7.295, "samples": 840}; travel_xy_m=stationary
  bar_walk: meanFPS=60.0; Frame={"mean_ms": 16.667, "p95_ms": 16.678, "p99_ms": 16.687, "max_ms": 16.855, "samples": 840}; GPU={"mean_ms": 9.037, "p95_ms": 10.38, "p99_ms": 11.583, "max_ms": 12.087, "samples": 840}; GameThread={"mean_ms": 5.638, "p95_ms": 6.725, "p99_ms": 7.002, "max_ms": 7.688, "samples": 840}; travel_xy_m=stationary
  shallows_walk: meanFPS=59.9; Frame={"mean_ms": 16.698, "p95_ms": 16.673, "p99_ms": 16.686, "max_ms": 42.524, "samples": 840}; GPU={"mean_ms": 9.486, "p95_ms": 10.84, "p99_ms": 12.338, "max_ms": 12.634, "samples": 840}; GameThread={"mean_ms": 5.618, "p95_ms": 6.925, "p99_ms": 7.522, "max_ms": 41.838, "samples": 840}; travel_xy_m=stationary
  forest_across: meanFPS=60.0; Frame={"mean_ms": 16.667, "p95_ms": 16.681, "p99_ms": 16.691, "max_ms": 16.85, "samples": 840}; GPU={"mean_ms": 9.894, "p95_ms": 12.002, "p99_ms": 13.6, "max_ms": 16.878, "samples": 840}; GameThread={"mean_ms": 5.808, "p95_ms": 6.94, "p99_ms": 7.727, "max_ms": 9.249, "samples": 840}; travel_xy_m=stationary
Final moving four short passes:60.0FPS mean,p9516.675-16.682ms,max18.354ms,~49m each. Final stationary59.9-60.0FPS,p9516.673-16.681ms,isolated42.524ms frame. Not a whole-route/display-presentation/perfect-lock claim.
Evidence: Saved/LidarAuthoringQA/LP6/result.json,TestsFinal,check.json,coverage.json,foliage.json; actual-map LP6_* and PF60-lp6-* screenshots in Art/Export/LidarStudy/Place. Install/Polish reapply LP6 after terrain generation; static reimport invalidates coverage metadata. Everything remains uncommitted. Owner drive/visual gate OPEN.

## FS1 - forest shape revision directly in L_LidarStudy - 2026-10-20

Owner approval to proceed after Waimeamea photo/tree-shape discussion and Art Tips for Building Forests reference. No separate test level. Native kit source assets preserved; map-owned mature/pole/edge crowns now use unequal branches and overlapping radial leaf groups instead of NP5 horizontal tiers. Mature clear boles, narrow pole stands, lower asymmetric edge crowns; existing placement cohorts and dead spars retained.
Files: Art/Blender/build_lidar_forest.py; Art/Unreal/lidar_forest_shapes.py; Art/Unreal/lidar_canopy_assets.py; Art/Unreal/install_lidar_place.py (shared idempotent tint); Art/run_lidar_forest.ps1; docs/LIDAR_FOREST_SHAPES.md. Outputs ForestFS1, map ForestShapes/CanopyKit, and L_LidarStudy. All uncommitted.
Triangles LOD0/1/2/far: Mature 18897/6419/1466/6; Pole 5945/1945/501/6; Edge 18897/6419/1466/6. Mature/edge retain all32 boughs, pole21. No new per-tree runtime tick, collision or instance density. Three-view 1536x512 atlases, alpha-coverage mips threshold0.35. Source geometry bounds prevent card inflation on repeated bake. Source bounds also used for future tree/trunk scale.
Saved forest counts unchanged: Mature69855, Pole70886, Edge5554, Spar2125 =148420. Root check2116 samples, max error0cm. Ground digest DB443C52AD8AD4F3A1E2CD57E8E4716F unchanged.
Import recovery: first attempt crashed in UE SetLodFromStaticMesh after set_lods emptied authored destination descriptions, before level save. Now preserve/validate existing authored LODs and update in place. Final full import exited0/saved but strict runner rejected transient old custom-node disconnections during graph replacement. Builder neutralises old custom nodes before deleting. Subsequent separate clean check exited0, no shader compilation errors, source cache matches; applying tint twice leaves all four graphs unchanged. Check includes alpha mip preservation. Original map/canopy backups retained under Saved/LidarAuthoringBackups/FS1-*.
Performance: existing saved1600x900 TSR75 preset, offscreen standalone; excludes loading/teleport/screenshot frames. Source CSV paths and all CPU/GPU percentiles in Saved/LidarAuthoringQA/FS1/result.json. Baseline/final stationary840 measured frames/site; prototype340; moving440. Not a whole-route or display timing guarantee.
fs1-before:
  paddock_mid: FPS 59.8; frame mean/p95/p99/max 16.719/16.685/16.742/55.521ms; GPU mean/p95/max 7.708/8.973/11.642ms; GT mean/p95/max 5.710/7.037/9.184ms.
  paddock_gate: FPS 60.0; frame mean/p95/p99/max 16.667/16.681/16.690/16.760ms; GPU mean/p95/max 7.235/8.734/10.666ms; GT mean/p95/max 5.352/6.456/9.006ms.
  river: FPS 59.9; frame mean/p95/p99/max 16.697/16.676/16.685/42.179ms; GPU mean/p95/max 8.447/10.165/11.957ms; GT mean/p95/max 6.117/7.382/41.925ms.
  access: FPS 60.0; frame mean/p95/p99/max 16.668/16.681/16.694/16.912ms; GPU mean/p95/max 9.036/10.667/12.717ms; GT mean/p95/max 5.340/6.452/7.948ms.
fs1-mature:
  paddock_mid: FPS 59.8; frame mean/p95/p99/max 16.718/16.688/16.948/26.546ms; GPU mean/p95/max 8.100/9.400/10.663ms; GT mean/p95/max 5.831/7.152/8.402ms.
  paddock_gate: FPS 60.0; frame mean/p95/p99/max 16.667/16.680/16.688/16.694ms; GPU mean/p95/max 7.279/8.842/9.959ms; GT mean/p95/max 5.365/6.413/7.843ms.
  river: FPS 59.6; frame mean/p95/p99/max 16.784/16.674/16.681/56.532ms; GPU mean/p95/max 8.401/10.020/11.415ms; GT mean/p95/max 5.985/7.310/8.460ms.
  access: FPS 60.0; frame mean/p95/p99/max 16.667/16.672/16.681/16.767ms; GPU mean/p95/max 9.019/10.408/12.022ms; GT mean/p95/max 5.412/6.684/7.556ms.
fs1-final:
  paddock_mid: FPS 60.0; frame mean/p95/p99/max 16.668/16.674/16.690/16.966ms; GPU mean/p95/max 7.245/8.319/9.749ms; GT mean/p95/max 5.356/6.414/8.123ms.
  paddock_gate: FPS 60.0; frame mean/p95/p99/max 16.667/16.674/16.686/16.734ms; GPU mean/p95/max 6.863/8.631/9.769ms; GT mean/p95/max 5.384/6.534/9.160ms.
  river: FPS 59.9; frame mean/p95/p99/max 16.701/16.681/16.689/44.520ms; GPU mean/p95/max 8.484/9.886/11.409ms; GT mean/p95/max 6.025/7.132/44.161ms.
  access: FPS 60.0; frame mean/p95/p99/max 16.668/16.673/16.714/16.866ms; GPU mean/p95/max 8.832/9.882/12.994ms; GT mean/p95/max 5.338/6.524/8.102ms.
fs1-walk:
  ford_walk: FPS 59.5; frame mean/p95/p99/max 16.802/16.686/18.690/56.840ms; GPU mean/p95/max 10.276/11.588/64.779ms; GT mean/p95/max 8.246/11.532/17.037ms; travelled49.32m.
  bar_walk: FPS 59.9; frame mean/p95/p99/max 16.684/16.690/16.962/20.048ms; GPU mean/p95/max 11.283/13.255/15.654ms; GT mean/p95/max 8.042/10.660/18.059ms; travelled49.01m.
  shallows_walk: FPS 59.9; frame mean/p95/p99/max 16.707/16.685/16.817/27.041ms; GPU mean/p95/max 10.969/12.558/14.240ms; GT mean/p95/max 8.398/10.866/18.204ms; travelled49.06m.
  forest_across: FPS 60.0; frame mean/p95/p99/max 16.671/16.681/16.815/17.778ms; GPU mean/p95/max 10.641/12.150/13.973ms; GT mean/p95/max 7.092/9.742/15.045ms; travelled48.97m.
fs1-ford-repeat:
  ford_walk: FPS 60.0; frame mean/p95/p99/max 16.670/16.676/16.724/17.140ms; GPU mean/p95/max 10.125/11.456/13.044ms; GT mean/p95/max 7.080/9.592/16.988ms; travelled48.97m.
Initial moving ford had one64.779ms GPU sample (logical frame max56.840ms); repeat averaged60.0FPS, p9516.676ms, max17.140ms, GPU max13.044ms. Retain both; cause not conclusively attributed. Stationary river isolated44.520ms remains. No material compilation errors in clean check/final runtime sessions. Owner drive and visual approval pending.


## HS1 - riverside homestead and vehicle garage (2026-10-20)
Owner supplied four house/garage photographs and requested on-foot vehicle selection. Originals preserved unchanged in Art/References/Homestead; architecture/rebuild details in docs/LIDAR_HOMESTEAD.md. Implemented directly in L_LidarStudy. Owner correction: rotate 90 degrees to face the river. Final placement yaw 0, authored X reflected for Unreal handedness; anchor (-52264.44549,-26256.74983)cm. Garage authored offset (1200,-1000)cm, on the right from the river. House ground datum 5354.7009cm; garage/bay floor 5181.2742cm. House checkpoint moved to [-53651.44549, -28206.74983, 5281.27421875].
House 6732 triangles/15 UCX hulls; garage 2702/9; graded apron 1972 triangles with static complex collision. Opaque vertex-colour buildings, reduced .42/.16 distance LODs; weatherboards, veranda, steps/rails, roof seams, flue, solar panels and two-bay charcoal garage. Lawn/gravel vertex blend; outer apron seam buried up to 28cm to absorb native mesh curvature between survey samples. Terrain source unchanged: DB443C52AD8AD4F3A1E2CD57E8E4716F.
Builder: Art/Blender/build_lidar_homestead.py; Unreal placement/material/import: Art/Unreal/lidar_homestead.py; guarded runner Art/run_lidar_homestead.ps1; saved-map integration check Art/Unreal/check_lidar_homestead.py. Full Place installer reapplies the shared placement; orientation/anchor mismatch refuses stale apron data. Art/open_lidar_study.ps1 -Play -ShowFPS -House is available. Final installation removed 419 additional overlapping vegetation roots; earlier layout revisions cleared 102, 623 and 436. No native terrain regeneration, lighting change or commit.
C++: reusable GTGarage station; safe controller replacement; walking station HUD in MudLab; existing character station selection exposed for scripts. E at closed roller opens/closes; scroll selects; T collects; Tab or walking away closes; F enters/exits. Twelve canonical drivable models, one current vehicle. Exact boot stacks retained; parked replacement inherits audio mute. Fresh car condition/parts/tuning, not transferred. Refuses occupied bay, excessive boot weight, moving/occupied car or active winch. Only retires old car after successful replacement/capacity validation.
Validation: guarded build succeeded (Homestead-Build2.log). Final install and final check exited 0. Saved-map check: 12 swaps, three Wire retained through each, exactly one car after every replacement, current-row duplicate refused, actual door trace/hold, occupied-bay and capacity rollback, driving refusal, entry, normal throttle injection and walk-away menu close passed. Short PIE throttle response: 41.0864cm travel, peak trace speed 194.7994cm/s, throttle reached 0.6. This is a response check, not a route drive or FPS evidence. Readback checks imported vertex handedness, connected material colour and House checkpoint. Inspected HS1_house_front.png, HS1_house_overview.png and HS1_garage_menu.png in Art/Export/LidarStudy/Place. Owner drive/visual acceptance pending.
Corrections during development: Unreal VertexColor colour output is unnamed (RGB connection had silently failed); FBX handedness corrected on both render and UCX meshes; checkpoint properties use get_editor_property. A 2.5s post-spawn test delay was insufficient for one car; the test now waits for the real stopped threshold. Asset-only import saved successfully but crashed during editor shutdown, so that experimental runner mode was removed. Full install and subsequent saved-asset runtime checks are clean. No Unreal process was killed.
Performance: hs1-final standalone capture is CONTENDED, not acceptance evidence. Skate.exe was concurrently consuming most of the GPU: Windows counter sample Skate72.12%, Unreal14.74%; NVIDIA total99%, 5336/6141MiB, 1320MHz, 30.46W, 88C, software thermal slowdown active. User notified and offered a clean rerun after closing Skate. No other application was closed. Keep this run separate from prior FS1 60FPS results. Any later clean result follows separately.

HS1 contended capture completed with exit0,1600x900 TSR75, saved60FPS preset. Measurements retained for provenance only; acceptance_valid=false.
  house_arrival: FPS9.1; frame mean/p95/p99/max 110.289/168.357/203.402/256.019ms; GPU mean/p95/max 103.157/157.134/243.999ms; GT mean/p95/max 7.132/10.603/72.075ms; 840 samples. Concurrent Skate remained open; no clean rerun yet.
  garage_door: FPS10.0; frame mean/p95/p99/max 99.848/160.7/177.685/263.706ms; GPU mean/p95/max 92.946/144.429/207.175ms; GT mean/p95/max 7.192/10.409/61.653ms; 840 samples. Concurrent Skate remained open; no clean rerun yet.

## HS2 - owner-photo homestead correction (2026-10-21 UTC)

Owner rejected HS1 resemblance. Changed Art/Blender/build_lidar_homestead.py and Art/Unreal/lidar_homestead.py, generated FBX/GLB/blend/layout/manifest/ground survey/perf poses, Homestead assets and L_LidarStudy.umap. No C++ edits or commits.
Geometry: separate lean-to veranda roof below the silver main gable; green perpendicular wing roof with solar panels; lighter timber, clad foundation skirts and partly solid veranda balustrade. House 8108 triangles / 15 hulls; garage 2702 / 9; graded lawn/court 3482 static collision triangles. Four placed actors remain; no new ticking actors. Building LOD fractions remain .42/.16 at screen sizes .12/.035.
River-facing yaw 0, anchor (-52264.44549,-26256.74983) cm unchanged. House datum 5259.292792968749 cm, 95.408085937501 cm below HS1; first floor datum+95 cm. Garage authored offset (1060,-880) cm, slab 6.56x6.48 m, floor 5186.074335937499 cm. Compact garage uses render/collision scales (.8,.9,.9). Door local (1209.6,-1225), stand (1209.6,-1395), bay (1209.6,-1830) cm. Checkpoint world (-53474.04549,-28086.74983,5286.074335937499) cm, yaw -90. Door/bay/stand now derived from layout. Installer rejects stale garage offsets as well as yaw/anchor.
Ground: floor clears maximum sampled actual building footprint by 18 cm; former broad level yard shelf replaced by a 9.5 m lawn feather. Gravel court follows final relief; outer seams buried 28 cm. Local static positive fill/veneer only. Native ground digest unchanged DB443C52AD8AD4F3A1E2CD57E8E4716F. Ground-material marker 4 rebuilds independently of FBX digest.
Validation: final guarded install and fresh saved-map check exited 0. Door trace/hold opens menu; all 12 replacements retain inventory and exactly one car; current row, occupied bay, overloaded boot and driving replacement refused; entry and walking away work. Normal-throttle response check travelled 2155.4420 cm, peak 1028.3373 cm/s. Functional response, not owner drive acceptance. Reports archived Saved/LidarAuthoringQA/HS2. Final images Art/Export/LidarStudy/Place/HS2_house_front.png, HS2_house_overview.png, HS2_garage_menu.png inspected in real map.
Initial inspect and first install produced reports but exited -1073741819 after shutdown. Added Entry unload to inspection and released editor-world reference before install unload; subsequent inspection, final install and check exited 0. Prior sources/views preserved Saved/LidarAuthoringBackups/HS2-source. No Unreal process killed.

Clean standalone performance: hs2-clean, exit 0, RTX 4050 Laptop 6GB, output1600x900, saved LiDAR60fps preset TSR75% capped60; logical after-tick-rate-wait frame timing. Skate absent before/during capture. GPU sample 60%, 68C, 3506MiB VRAM; software thermal slowdown Not Active (pre-capture52C). Prior hs1-final contended run retained and invalid for acceptance.
CSV: C:\GrandTour\Saved\Profiling\CSV\Profile(20261020_190730).csv
Scope: Standalone offscreen game, on-foot camera; excludes loading, teleports and screenshot frames; not display presentation timing. 840 measured frames per pose; no display-presentation or whole-route 60fps claim.
house_arrival: 60.0 FPS; frame {"mean_ms": 16.667, "p95_ms": 16.681, "p99_ms": 16.688, "max_ms": 16.701, "samples": 840}; GPU {"mean_ms": 8.281, "p95_ms": 9.952, "p99_ms": 11.028, "max_ms": 11.182, "samples": 840}; GT {"mean_ms": 3.346, "p95_ms": 4.406, "p99_ms": 5.182, "max_ms": 5.775, "samples": 840}; over16.9ms 0.0%.
garage_door: 60.0 FPS; frame {"mean_ms": 16.667, "p95_ms": 16.679, "p99_ms": 16.686, "max_ms": 16.779, "samples": 840}; GPU {"mean_ms": 7.702, "p95_ms": 9.085, "p99_ms": 9.984, "max_ms": 10.234, "samples": 840}; GT {"mean_ms": 3.338, "p95_ms": 4.199, "p99_ms": 5.36, "max_ms": 6.235, "samples": 840}; over16.9ms 0.0%.
Both measured stationary views pass p95<=16.9ms. Owner visual/drive review remains the gate.


## RR2 - restore attached deformable gravel bank (2026-10-21 UTC)
Owner screenshot identified the inside point between logging-track crossings as an island after river reshaping. RR1 protected only a narrow route ribbon and its derived drainage guide excavated behind the point. RR2 protects an explicit bank/mainland polygon in Art/LidarAuthoring/river_banks.json, lowers its front toward water+0.35m and blends rearward into the mainland. The derived guide moves at most 8m, only stations 3284..3372, with 18m end blends. Original source vectors/DEM and all river surface elevations remain unchanged. This is a local derived course correction to restore the attached bank, not a new full-course alignment.
Terrain preparation: Art/tools/lidar_river_repair.py RR2-1 and prepare_lidar_place.py. Seven existing route control points (23..29) lowered 8.11..69.41cm, XY unchanged, to prevent rebuilding the old raised ridge. Last condition end clamped from 713.7212957760393 to new 3D length 713.6648824734824m. Prior route retained in Saved/LidarAuthoringQA/RR2/edits-before.json. Existing vegetation records outside the local correction preserved exactly; 13 canopy and 419 understory candidates removed locally. Prepare counts 148407 canopy / 199415 understory before homestead clearance.
Bank validation checks actual final relief as well as offline terrain: 0.5m grid, dry margin >12cm, erosion for a 3m-wide mainland connection, bank probe (-479,-342)m and mainland (-492,-361)m. Final bank above water 0.46660452m; mainland 3.09359658m; connection passes. All 7189 river stations remain on one connected collision-wet component; furthest nearest wet cell 1.58114m. The controlled transient PIE gravel stroke changed surface delta from -0.408609 to -1.408604cm; sinkage cap 4.613458cm. No deformation fixture was saved into the level. Four live rut-water sheets retained.
Source height SHA256 deba359a50b01fedb76af13cc6846162983408c3a76c5032e421de543507d75d unchanged. Final road-ground digest 8D447603F1A414A8637E08491F2B048D. Homestead survey maximum height difference exactly 0.0cm; only its survey/layout digest updated, architecture and placement unchanged.
Pipeline fixes encountered: river-detail installer accepts RR2 data while retaining RR1 material version; LT4 reruns preserve native custom-output indices instead of removing/reappending pins, and explicitly reconnect RR1State float4 before compilation. This fixes State.g/b/a swizzle errors after a full Install. Polish now reapplies homestead clearance after tree reseeding; shared clears_vegetation footprint is used by placement and general count validation. No new runtime actor types, simulation or per-frame scans.
Validation status must remain explicit: final Install saved/reloaded and exited 0. Final Polish and Water reports completed successfully with protected assets unchanged and no shader compile failures, but exited -1073741819 after the shutdown log. Releasing remaining generated-domain references did not resolve the shutdown exit. Focused RiverCheck assertions/captures all passed but its editor process had the same nonzero shutdown exit. General Check exited 0 but report failed at its obsolete M_LidarClump expectation; GS3 M_GS3_Near is intentionally installed. Do not describe the whole batch pipeline as clean. These reports and initial failures are archived in Saved/LidarAuthoringQA/RR2.
Actual map preview: Art/Export/LidarStudy/Place/RR2_bank_from_mainland.png and RR2_gravel_deformation.png. RR2_attached_bank.png is occluded by foreground canopy and is not a useful review view. Owner drive/appearance acceptance remains pending.
Standalone rr2-bank run exited 0, RTX4050 Laptop 6GB, 1600x900 TSR75%, saved capped60 preset, Skate absent before run. Both stationary on-foot views pass p95<=16.9ms, 840 measured frames each, excluding teleports/loading/screenshots; no whole-route or display-presentation claim. GPU sampled 48C before / 53C after.
gravel_point: 60.0 fps; frame {"mean_ms": 16.667, "p95_ms": 16.676, "p99_ms": 16.686, "max_ms": 16.73, "samples": 840}; GPU {"mean_ms": 7.915, "p95_ms": 9.705, "p99_ms": 10.716, "max_ms": 11.6, "samples": 840}; over16.9ms 0.0%.
mainland_connection: 60.0 fps; frame {"mean_ms": 16.667, "p95_ms": 16.681, "p99_ms": 16.691, "max_ms": 16.825, "samples": 840}; GPU {"mean_ms": 8.577, "p95_ms": 10.109, "p99_ms": 10.848, "max_ms": 11.009, "samples": 840}; over16.9ms 0.0%.
CSV: C:\GrandTour\Saved\Profiling\CSV\Profile(20261020_201124).csv
No commit. No Unreal process killed. Original maps protected.


RH1 2026-10-21 UTC: owner wants the same cars on fast gravel and slow off-road, with more forgiving high-speed slides. Added speed-blended post-peak lateral force retention in GTSoilVehicleMovement (30-65km/h, default strength0.75), preserving peak grip and bypassing low range, low speed, deep mud and water. No power, suspension, terrain or asset edits. gt.Vehicle.SlideRecovery 0/1 provides old/new A/B. Build and five force/mud/rut tests pass, normal exits. Actual Chaos slide force +35.3% at79.2km/h/40deg; tested low-range/low-speed/peak forces identical. Three-car LiDAR slide trials reduce integrated slip4.4-6.3%; Suzuki lateral travel worsens, so owner feel gate remains. Six route regressions pass, low-range travel within5% of baseline; see Saved/LidarAuthoringQA/Rally/regression.json. No new60fps claim. IMPORTANT broader rally blocker: Waimeamea Road station200m samples native mud=true, granular=false despite gravel appearance; road rebuild zeros styleR. Separate explicit road surface authoring fix needed; do not lower shared mud resistance. Full results, files, controls and limitations in docs/LIDAR_RALLY_HANDLING.md. Uncommitted.


FR1 - Firm gravel rally roads (2026-10-21 UTC)
Owner: established gravel roads, including Riverside access, need not deform;
make them smoother for faster rally driving. Same cars retain off-road tuning.
Implemented opt-in bFirmGravel and 16 m longitudinal profile filter in the
procedural road builder. Zero yielding depth / softness across the carriageway,
50 cm interpolation guard, soil transition through shoulder; overlap resolution
prevents another road shoulder from reintroducing mud at a firm-road junction.
Firm cut/fill limit 120 cm; road XY and widths preserved. All four established
roads use the shared lidar_firm_roads.py policy. Logging designs remain separate.
Riverside final 35 m retains its existing geometric profile, with 16 m blend on
the approach, preserving the house and baked apron; physical soil is still rigid.
Installer version rd1-5-fr1 plus firm_gravel fr1-1 gate persists the policy.
Targeted runner Art/firm_lidar_roads.ps1 saves map and paint/style/macro masks.
Build succeeded; targeted editor rebuild, save and reload exited 0. Before digest
8D447603F1A414A8637E08491F2B048D; after 6AE1F9489CE5EC408044BFEC06A9FE25.
8,565 samples (three lanes at 2 m intervals): all zero yielding depth.
Two-metre profile midpoint residual RMS cm, before -> after:
Riverside 1.883 -> 1.243 (-34.0%); Pond spur 3.350 -> 2.148 (-35.9%);
Waimeamea 0.623 -> 0.406 (-34.9%); Waterhouse 0.886 -> 0.256 (-71.1%).
1,004,400 triangles unchanged; 1,948 tiles rebuilt and 284 retained. Second
rebuild identical digest, zero changed tiles. Protected house/apron, river-bank
and logging ground samples: maximum elevation change 0 cm. Logging controls,
conditions and sampled mud/bank yielding depths unchanged (maximum change 0 cm).
Backups and full samples: Saved/LidarAuthoringQA/FR1/apply.json and backup path
recorded there. Full house survey and layout recertified against new map digest.
No engine, tyre, suspension, gearing or off-road force coefficients changed.
Driving and soil-stroke checks running; owner drive remains acceptance gate.
No new standalone 60 fps claim.


FR1 water preservation: road rebuild recreated the static pool mesh visible.
Restored its hidden-in-game state, retaining all four live rut basins. Compared
the complete old and regenerated water seed arrays and extents: identical.
GTProceduralRoadWater.inl now carries the hidden state into future rebuilt
meshes. Saved/reloaded with exit 0; ground digest unchanged. Evidence:
Saved/LidarAuthoringQA/FR1/water.json; Saved/Logs/FirmRoads-Water.log.


FR1 drive validation (2026-10-21 UTC):
Waimeamea 40 s high-range peaks: Range Rover 76.942, BMW 73.753, Suzuki 74.786
km/h; all completed the finite drive/brake check. Original access driver went
wide and stopped; its old broad pass flag is not route acceptance. Driver now
uses 5 m bend samples, stronger earlier braking and detects five-second stalls.
Repeat Riverside 35 s from station 1290 m:
RangeRover: distance 89.100 m, peak 39.476 km/h, max offset 8.956 m, pass False; departed route or rolled.
BMW: distance 274.903 m, peak 41.971 km/h, max offset 1.488 m, pass True; completed finite segment.
Suzuki: distance 273.233 m, peak 41.734 km/h, max offset 1.086 m, pass True; completed finite segment.
The automatic Range Rover drive remains failed; owner drive is the feel gate.
BMW and Suzuki passed this finite segment, not the full route. Logging 15 s
low range: RR 52.494 m, Suzuki 10.412 m, BMW -1.893 m (failed). No exact
pre-change baseline for that logging segment; no off-road coefficient change.
Both runs passed all four soil-stroke cases: roads stayed at zero, logging mud
and river gravel each yielded ~1 cm (caps 5.700 and 4.613 cm).
Evidence: Saved/LidarAuthoringQA/Rally/firm-roads.json, firm-access.json and
Saved/LidarAuthoringQA/FR1/validation-summary.json. Raw overall route results
remain false; do not present all routes as passed. No new FPS certification.


## HS3 - house placement and cleanup (2026-10-21 UTC)

Owner satellite references lead the correction. Registered aerial pixel (613,363.5), 0.625m/pixel, resolves to world (-51137.5,-26131.25)cm. House moved 11.34m mostly east; yaw -65deg follows roof axis with veranda NW toward river/court. Garage local (540,-1100)cm. Canonical Art/References/Homestead/site-layout.json supplies placement; survey, apron, door, collection bay, recovery checkpoint and benchmark cameras follow it. Original new references archived unchanged. Registration and dimensions are image estimates.

Model: trimmed joined roofs, recessed framed wall openings, cleaner weatherboard laps, closed side undercroft, unobstructed solar array, vertex-alpha surface roughness. House 8050 triangles/17 hulls (previous 8108/15); garage 2702/9; apron 3382 triangles (previous 3482). Native terrain digest unchanged at 6AE1F9489CE5EC408044BFEC06A9FE25; source DEM SHA256 deba359a50b01fedb76af13cc6846162983408c3a76c5032e421de543507d75d. House datum 5494.447cm, garage floor 5234.119cm. Removed 261 intersecting vegetation instances. Road validation now protects the current registered footprint.

Guarded install and views exited 0. First gameplay check passed assertions but exited -1073741819 after shutdown log close; archived as HS3/check-shutdown-fault.*. Released remaining editor/PIE wrappers before teardown. Full repeat: 12 swaps, inventory retained, one car, door/menu, bay obstruction, capacity refusal, duplicate/refusal while driving, entry and walk-away all passed; normal-input departure 14.18m; editor exit 0. No C++ change/build required.

Standalone hs3-relocated: 1600x900, saved TSR75 capped preset, 840 measured frames/view. House arrival / garage door: 60.0/60.0 FPS; frame p95 16.680/16.671ms; GPU mean 8.637/7.705ms; exit 0. Stationary offscreen scope only, excluding loads/teleports/screenshots, not whole-route or presentation timing. Evidence Saved/LidarAuthoringQA/HS3 and Place/playperf-hs3-relocated-summary.json. Final views Place/HS3_house_front.png, HS3_house_overview.png, HS3_garage_menu.png. Source/exports backup Saved/LidarAuthoringBackups/HS3-source; map backup HS1-1792611552074800600. Owner visual/drive review remains gate. No commits.


## HS4 - longer L wing and usable veranda stairs (2026-10-21 UTC)

Owner: extend wing behind garage; steps lead nowhere; model in Blender. Wing now 10.3m long (was 7.4), front Y=-6.5m, 4.5m projection beyond main wall. Roof/walls/floor/foundation/simple collision extended together. Stairs moved to X=1.45m inside the L, 1.8m balustrade opening, continuous veranda deck terminating before wing wall. Blender source/export/BLEND rebuilt; existing house anchor and garage placement retained. House 8367 triangles/17 hulls (+317 triangles), garage 2702/9, apron 3382. Same materials, actors and LOD policy. House datum 5502.183cm; garage 5234.119cm.

Guarded install/check exit 0. Twelve garage swaps and existing refusal/inventory checks passed. Real walking movement traversed seven waypoints up stairs, through railing opening, along deck and back down; 99.29cm rise, no falling or obstruction, only initial placement teleported. Native digest 6AE1F9489CE5EC408044BFEC06A9FE25 and source DEM checksum unchanged. Evidence Saved/LidarAuthoringQA/HS4, final Place/HS4_house_front.png and HS4_house_overview.png. Source/export backup Saved/LidarAuthoringBackups/HS4-source; pre-install map backup recorded in HS4/install.json. No new FPS claim, C++ edits or commits. Owner review remains gate.

NEXT, explicitly reserved by owner: high-speed driving has inadequate steering. Do not consider it addressed by the house pass; driving code/tuning were untouched.

RH2 - responsive steering, 2026-10-21.
Owner reference: Forza Horizon 4; first input-response pass, not its physics reconstruction.
New GTResponsiveSteering helper + automation test; GTCarPawn integration; dual-driving probes/driver inverse fixed.
High range 30-60 km/h blend: original squared input to linear; rise 2.5 -> 6/s, return 5 -> 8/s. Existing faster per-car rates retained.
Low range any speed, <=30 km/h, mud/bog/snow bypass. Sinkage fade 6-12 cm; water fade 1-5 cm.
Wheel lock/speed curve, tyre peak grip, RH1 slide recovery, power, suspension, mud/water/terrain unchanged.
Console gt.Vehicle.ResponsiveSteering 0 original / 1 revised (default); per-car HighSpeedSteeringResponse 0..1.
Build succeeded; ResponsiveSteering + SlideRecovery + SubstanceOracle + LivePush + RutWallWork + DirectionalSoilFlow: 6 passed, exit 0.
Installed code LiDAR probes: 36 runs, 18 paired checks passed; 80 km/h taps/half-stick, 90 km/h reversals, 20 km/h both ranges and 90 km/h low range.
80 km/h half-stick peak wheel degrees / heading change at 0.7 seconds, original -> revised:
RangeRover: wheel 2.016 -> 4.065; heading 4.653 -> 9.398 degrees.
BMW: wheel 2.013 -> 4.055; heading 3.915 -> 7.995 degrees.
Suzuki: wheel 2.022 -> 4.082; heading 4.963 -> 9.090 degrees.
Riverside 35-second high-range route (includes corrected AI input inverse, cannot isolate RH2):
RangeRover: 305.686 m; peak 46.260 km/h; max centreline offset 0.516 m; pass=True.
BMW: 281.930 m; peak 42.718 km/h; max centreline offset 0.411 m; pass=True.
Suzuki: 271.311 m; peak 41.799 km/h; max centreline offset 0.521 m; pass=True.
Soil Waimeamea Road: depth cap 0.000000 cm; deformation 0.000000 -> 0.000000 cm; pass=True.
Soil Riverside access: depth cap 0.000000 cm; deformation 0.000000 -> 0.000000 cm; pass=True.
Soil Logging mud: depth cap 5.699537 cm; deformation -0.247748 -> -1.247745 cm; pass=True.
Soil River gravel bank: depth cap 4.613458 cm; deformation -0.408609 -> -1.408604 cm; pass=True.
Evidence Saved/LidarAuthoringQA/Rally/responsive-steering.json, responsive-steering-access.json; Saved/Automation/ResponsiveSteering; docs/LIDAR_RALLY_HANDLING.md.
No map or asset saves. No fresh FPS benchmark. Owner drive remains acceptance gate; high-speed probe coasts after velocity injection, not a sustained throttle test.


## RH3 - consistent keyboard response and normal-Play performance (2026-10-21)

Owner feedback: RH2 still felt delayed/uneven on keyboard and performance had
regressed. RH3 removes speed-dependent blending of the input filter on firm
high-range surfaces. The existing speed-dependent maximum steering lock remains.
Linear response rises at 6/s and returns at 8/s throughout firm high range;
authored faster rates survive. Low range, contacted mud/bog/snow, sinkage and
water bypass/fades remain as RH2. Tyre force curves, power, suspension and slide
recovery are not retuned by this pass. This supersedes RH2's <=30 km/h bypass.

The ordinary editor launch log had no performance commands: directional shadow
bias was -1.5 rather than the saved preset's +0.5. PIE also defaults to overriding
game screen percentage. A new GTLidarPerformanceSubsystem applies the canonical
Art/lidar_performance.json when L_LidarStudy begins Game/PIE, respects explicit
higher-priority overrides and restores prior settings on the last play world's
shutdown. The JSON is staged as a runtime dependency (packaged build untested).
OriginalQuality launcher uses -GTLidarPerformance=0; gt.Lidar.PerformanceAuto 0
before Play is another opt-out. Version 2 keeps TSR at 75%, uses mesh LOD scale
4 instead of 3 and shadow bias 1 instead of 0.5. Density is unchanged; the
tradeoff is earlier mesh simplification and lower shadow resolution. Output
resolution remains whatever the player/editor chooses; measurements below are
1600x900. The preset caps normal play to 60 fps; captures are uncapped.

Water profiling exposed two avoidable costs. RefreshDomainBed now samples only
supported cells and preserves the live field without copying/rebuilding it if
reference depths did not change. TickWaterDomain alone owns player-centred
streaming: remote parked-car lids/impulses are clipped instead of repeatedly
moving the simulation away from the player. Whole-course coverage/immersion
queries remain independent of this local surface-wave window.

Validation:
- Editor builds succeeded: Saved/Logs/rh3-build.txt and rh3-water-build.txt.
- Nine automation tests passed, exit 0, Saved/Automation/RH3: ResponsiveSteering,
  SlideRecovery, DirectionalSoilFlow, RutWallWork, LivePush, SubstanceOracle,
  MovingDomain, RiverReference and ShoreEnvelope.
- 24 actual A/D keyboard sequences, 12 paired comparisons, all handling checks
  passed in the saved LiDAR map. Three cars (Range Rover/BMW/Suzuki), 20/40/80
  km/h high range, 20 km/h low range. Each sequence presses A for 160 ms,
  releases, presses D for 160 ms, then releases; input trace reaches both signs
  and returns to zero. Initial velocity is injected and the car coasts for
  1.4 seconds: this is not a sustained throttle/cornering or owner-feel verdict.
  High-range peak wheel-angle ratios on/off were 5.13-5.73 for these short taps;
  low-range ratios were 0.97-1.00 with response weight exactly zero.
  Evidence: Saved/LidarAuthoringQA/Rally/rh3-keyboard.json. Its subsequent water
  setup failed because the car was still moving too fast to exit, so the whole
  report must NOT be treated as a fully successful run despite its old ok=true
  field. The runner now sets ok=false on exceptions and waits for braking before
  the water test. All keyboard comparisons completed before this setup failure.
- Separate water-mode rerun passed with normal editor/wrapper exit:
  Saved/LidarAuthoringQA/Rally/rh3-water.json. All 14 preset values applied without
  test-side profile commands and restored exactly after PIE. A remote contact
  left local water height exactly 4488.623535 cm and returned zero remote impulse.
  At (-47938.658044,-37813.658044), a soil stroke lowered terrain delta from
  -1.168833 to -3.417597 cm; the formerly dry shore became wet, depth 1.556757 cm.
  Reproduce with Art/check_lidar_dual_driving.ps1 -Mode water -Label <new-label>.

Performance on RTX 4050 Laptop 6 GB, Development offscreen standalone, 1600x900,
uncapped; 440 measured frames per scene, excludes loading/teleports/screenshots:

| Scene | Stock mean FPS / p95 ms | Prior saved preset, steering off | RH3 final mean FPS / p95 ms |
| --- | --- | --- | --- |
| River | 51.4 / 29.844 | 77.4 / 16.302 | 89.9 / 12.944 |
| Bog 214 | 31.3 / 42.458 | 55.8 / 23.447 | 69.7 / 17.920 |
| Bog 552 | 30.9 / 47.408 | 63.3 / 20.201 | 71.9 / 17.657 |
| Access stress | 36.1 / 37.846 | 60.8 / 22.183 | 64.6 / 19.052 |

These are short fixed-heading LOW-range throttle stress scenes, NOT completed
rally routes. In particular, the old access fixture drives into trees/off-road;
its screenshot must not be used to claim successful road following. Stock used
100% screen percentage and stock quality; the prior and final saved presets use
75%. The improvement combines configuration and code changes, not steering
alone. Final GPU p95: 11.290, 13.658, 16.081, 15.488 ms in table order. Full-frame
p95 still exceeds 16.667 ms in three scenes: NO locked-60 or full-route claim.
SteeringResponse CSV scope mean 0.000822 ms / p95 0.0013 ms across warmed final
capture frames (mostly low-range bypass; not a high-range A/B cost comparison).
Water.LiveRiverBed mean per-call cost old -> final, table order:
3.2520 -> 1.2447, 3.7703 -> 0.3160, 3.6776 -> 0.2993, 3.3781 -> 0.0443 ms.
Final window log has seven moves for initial placement, four teleports and two
local focus movements, without repeated far-contact recentering. Final bog view
was inspected: full foliage, ground detail and mud remain visible.

Evidence: Art/Export/LidarStudy/Place/playperf-rh3-{stock,saved-off,tuned,final}
metadata/summary JSON, Saved/Profiling/gt_perf_PF60-rh3-final-*.json and final CSV
Saved/Profiling/CSV/Profile(20261021_154828).csv. Reproduce final capture:
Art/profile_lidar_play.ps1 -Label <new-label> -UseSavedProfile -Uncapped -Drive -Probes.
No map/assets were saved, no commits made, Unreal closed normally. Owner driving
remains the acceptance gate; remaining streaming/rendering spikes are documented
rather than hidden by average FPS.


## PF120 - 2026-10-21 UTC: 120 fps target, first optimization pass

STATUS: TARGET NOT MET. User asked for smoother driving and a 120 fps target.
The retained preset caps at 120; this is NOT a claim of sustained 120. The budget
is 8.333 ms. Saved normal-Play preset is Art/lidar_performance.json version 5.
No map or art assets saved; steering/traction tuning and physics rates unchanged.

Implemented:
- Height-only wheel contact queries in GTLandscapeSurface and GTVehicleTuningComponent.
  Preserve the 9x9 support grid and native height sentinel; skip the legacy grid
  that native support immediately overwrote. Four footprint probes now read only
  the thickness, rest height and bed delta they actually need. Vehicle tick scope
  at the two bogs fell from 4.325/4.580 ms in the pre-change render trial to
  1.196/1.200 ms in the first optimized trial (different graphics configuration;
  CPU scope comparison only, not a controlled whole-frame code-only A/B).
- GTWaterDomainSheet no longer samples the domain twice per window cell, and
  queries ground only inside the authored shore envelope. Live depth and shore
  deformation still use the same physical field.
- GTMixedGroundDetails/Streaming use UE5.8 MarkRenderInstancesDirty for instance
  changes. Engine SendRenderInstanceData_Concurrent flushes tracked changes and
  updates bounds without rebuilding the complete scene proxy. Mud clumps skip
  unchanged transforms and reuse their existing full surface sample. Grass
  density, wind, bend/removal, near/far ranges and simulation are retained.
- GTItemRegistry's four reflected raw-pointer arrays converted to TObjectPtr.
  ObjectPtrDecay preserves the existing const raw-array getter API. Build and
  runtime registry snapshots succeeded. No raw reflected object-pointer array
  declarations remain in project headers under the checked source scan.
- Preset: TSR 66.667%, fixed resolution scale; mesh LOD scale 6; VSM directional
  static/moving bias 2, two SMRT rays; coarse non-Nanite pages off; clipmap last
  level 17; HZB on; ForceAllRayTracingEffects=0 and Lumen.Reflections.Allow=0;
  terrain visual upload budget 0.5 ms; VSync off; 120 cap. Normal PIE/game applies
  it and restores prior values on leaving Play. This lowers image resolution,
  shadow detail and mesh detail; it does not thin vegetation or simplify soil.
  Original preset copy: Saved/PerformancePresets/lidar_performance-before-pf120.json.

RTX4050 Laptop 6 GB, Development offscreen standalone, 1600x900, uncapped.
Below: mean FPS / p95 full-frame milliseconds. Every scene has 440 measured
frames from the existing fixed-heading LOW-range stress fixture. Loading,
teleports and screenshots are excluded. Travel length differs with frame rate;
these are short scene comparisons, NOT full rally-route or presentation timing.
The access fixture heads into trees/off-road and must not be called a rally run.

| Trial | River | Bog214 | Bog552 | Access stress |
| --- | --- | --- | --- | --- |
| pf120-render | 101.4 / 11.940 | 80.8 / 14.854 | 91.4 / 13.829 | 77.7 / 16.204 |
| pf120-contact-csm | 105.7 / 12.218 | 73.3 / 15.617 | 83.3 / 14.334 | 71.8 / 17.956 |
| pf120-lod | 104.6 / 11.154 | 84.8 / 14.211 | 94.9 / 12.461 | 76.7 / 16.354 |
| pf120-raster | 114.1 / 10.529 | 87.0 / 13.282 | 92.4 / 13.005 | 73.7 / 16.413 |
| pf120-budget | 106.2 / 10.776 | 87.5 / 13.677 | 103.6 / 11.503 | 80.0 / 15.573 |
| pf120-instances | 99.0 / 11.556 | 85.2 / 14.482 | 100.0 / 12.063 | 82.3 / 15.705 |
| pf120-adaptive | 106.3 / 10.702 | 84.5 / 14.963 | 99.4 / 12.151 | 79.4 / 15.652 |

RH3 previous comparable final: 89.9/12.944, 69.7/17.920, 71.9/17.657,
64.6/19.052, respectively. Retained PF120 graphics/code capture is
pf120-instances: 99.0, 85.2, 100.0, 82.3 fps; p99 12.693, 15.656, 13.180,
21.709 ms; maxima 25.969, 27.975, 27.582, 41.834 ms. These still exceed
8.333 ms. No whole-map locked-60 or locked-120 claim. GC pointer storage changes
came after this short capture; none of the rejected GC settings are retained.

Experiment settings and outcomes (full commands in each playperf metadata JSON):
- render: 66.667%, LOD4, VSM bias2, rays2, expensive RT effects/reflections off.
- contact-csm: height optimization, conventional shadows 1024/two cascades/0.6
  distance and RT disabled. Rejected: dense forest was slower.
- lod: 66.667%, LOD6, VSM bias2/rays2, RT effects/reflections off, uploads0.5ms.
- raster: 60%, LOD6, RT disabled, VRS enabled. Rejected: distance-field fallback
  increased GPU cost and the dense/access scenes did not improve enough.
- budget: 60%, LOD8, shadow bias3. Rejected additional visual compromises.
- instances: retained lod settings plus incremental grass/clump updates and
  redundant water-query removal. No large isolated FPS gain claimed for grass.
- adaptive: 50-75% dynamic resolution, 8.333ms budget, otherwise retained settings.
  It bottomed out at 50% in the heavy view and did not solve the bottleneck;
  rejected in favor of sharper fixed 66.667%.

Actual road-following instrumentation added via -Mode performance to
Art/check_lidar_dual_driving.ps1 and Art/Unreal/check_lidar_dual_driving.py.
It records CSV only during a 40s Waimeamea Road drive and 35s Riverside access
run, then checks water/terrain, ends PIE and checks preset restoration.
Art/tools/analyze_lidar_play_perf.py --routes <label> reports all captured
frames, including GC and streaming spikes. These are hidden PIE plus Python
controller overhead, not standalone. Requested window 1600x900; physical
viewport was not recorded in these initial captures (future runs now record it).

Retained-settings route evidence: Saved/LidarAuthoringQA/Rally/pf120-roads.json
and pf120-roads-perf.json. Range Rover: Waimeamea 532.183 m, 77.578 km/h peak,
max offset 0.33 m; Riverside 302.08 m, 46.38 km/h, max offset 0.51 m. Both passed.
All 17 profile values applied automatically and restored. Whole-capture mean FPS
66.0 / 60.2; p95 18.179 / 18.030 ms; p99 20.852 / 30.911 ms; worst frame
1290.920 / 1401.998 ms. CSV events correlate those worst frames with GC; first
route GC scope was 1258.023 ms. Do NOT hide these in the short stress results.

Rejected incremental-GC investigation:
- Tested gc.AllowIncrementalReachability=1, time limit0.001s and
  gc.AllowIncrementalGather=1 (UE labels these experimental). The normal
  pf120-gc-roads-final run averaged 69.3/66.5 fps, p95 17.635/17.308 ms,
  max32.064/32.105ms, with registry snapshots and profile restoration passing.
  However, its captures had no GC timing columns/cycle events, so those clean
  maxima do NOT prove garbage collection was fixed.
- Forced continuous incremental collection with gc.VerifyNoUnreachableObjects=1
  in pf120-gc-verify exposed a first reachability iteration around774ms, despite
  later iterations near1-2ms. The time limit is soft and the first traversal is
  not sufficiently sliced. REJECTED: all gc.* settings removed from saved v5.
  Pointer-storage cleanup retained. This diagnostic is artificial GC stress,
  not a representative FPS measurement. Do not use its FPS as normal gameplay.
- Next performance work must address the expensive first GC traversal/object
  ownership graph, plus forest/shadow render passes and moving terrain/water
  windows. Merely lowering resolution further did not meet 120.

Validation:
- Guarded builds succeeded; latest pointer cleanup build log pf120-gc-build.txt.
- Saved/Automation/PF120/index.json: nine tests passed (eight clean, RiverReference
  with unrelated HTTP connectivity timeout warning): ResponsiveSteering,
  SlideRecovery, DirectionalSoilFlow, RutWallWork, LivePush, SubstanceOracle,
  MovingDomain, RiverReference, ShoreEnvelope. These ran after contact/water/
  instance edits, before the later registry-pointer-only change.
- Actual map height oracle: 3528 native/legacy comparisons, max error
  0.000001430511 cm. Deforming the tested dry shore opened water; remote contact
  did not recenter the local water. Reports pf120-height-check and pf120-roads.
- GrassCheck initially failed because check.json had been overwritten and no
  longer held gp2c_chase camera coordinates. Fixed the test to use the dedicated
  Art/Unreal/lidar_grass_check_views.json fixture, retained from before_GS1.
  Rerun passed normally (grasscheck-process.json exit0, report_ok true).
  21982 near instances, 11736 distant; distant bins 40/80/125/150/180m:
  1260/3760/5293/1291/121. Three-layer rebuild had zero missing/extra instances.
  Bend counts after contact33/23/21, removal11/6/6; wind scale2; no far collision
  or shadows; audio mute and info-toggle checks passed. Ground/distance/contact
  images inspected in the actual LiDAR map.
- Registry runtime snapshot:24 items,15 parts,7 recipes,7 upgrades, unchanged
  across the normal incremental-GC experiment. Public getters work after storage
  conversion. Additional forced verification outcomes are recorded below.

Reproduce retained standalone capture:
  Art/profile_lidar_play.ps1 -Label <new> -UseSavedProfile -Uncapped -Drive -Probes
  Saved/Tools/TerrainPython/Scripts/python.exe Art/tools/analyze_lidar_play_perf.py <new>
Reproduce normal editor road measurement:
  Art/check_lidar_dual_driving.ps1 -Mode performance -Label <new>
  Saved/Tools/TerrainPython/Scripts/python.exe Art/tools/analyze_lidar_play_perf.py --routes <new>
Every build/editor launch used Art/wait_unreal_free.ps1 and the shared mutex.
No user editor killed, no commits, no map saves. Owner drive remains the feel gate.

PF120 final diagnostic outcome (2026-10-21 UTC): pf120-gc-verify completed and
Unreal exited normally. 248 incremental cycles completed;251 no-unreachable-
reference verification passes;900 reachability iterations, worst998.01ms.
No GC reference errors/assertions. Registry24/15/7/7 and preset restoration passed.
Forced continuous-GC routes covered77.122m /67.054m, peak42.00/40.38km/h;
7.4/7.5fps means, p95 802.110/799.815ms, max1025.699/855.089ms. These artificial
stress timings demonstrate WHY the experimental collector settings were rejected;
they are NOT normal-game performance. Retained v5 contains17 commands and NO gc.*
overrides. Normal gameplay corresponds to pf120-roads, with the documented
60.2-66.0fps editor averages and periodic collection hitches still unresolved.
Do not attribute pf120-gc-roads-final's clean maxima to a proven GC fix.
The explicit test-only GT_DUAL_DRIVE_GC_STRESS=1 flag now supplies its own three
experimental collector commands, continuous collection and reference checking;
these are never written to the gameplay preset. The object iterator used by the
registry test is explicitly destroyed before driving, so it cannot retain a GC
pause. No Unreal process left running at completion. 120fps remains an open target.


### VQ1 - 2026-10-21: restore quality after PF120 visual rejection
User roadside screenshot rejects the cheap/flat appearance after the 120 fps pass.
Changed Art/lidar_performance.json to version 6, LiDAR balanced visual quality.
Restored the version-2 visual settings: screen percentage 66.667 -> 75,
static mesh LOD distance scale 6 -> 4, directional and moving shadow bias 2 -> 1,
directional shadow rays 2 -> 4. Removed forced RT-effects-off and Lumen-reflections-off
commands so a fresh process follows project settings. Retained t.MaxFPS 120,
gt.LandscapeMud.UploadBudgetMs 0.5 and all PF120 CPU/code optimizations.
Saved rejected v5 preset at Saved/PerformancePresets/lidar_performance-pf120-v5.json.
Existing editor processes launched with v5 ExecCmds must restart: console priority
otherwise prevents the automatic play preset from restoring those values.
Validation: JSON parses, no duplicate commands, every v2 visual command retained;
no Unreal launch, asset rebuild, visual comparison or fresh benchmark this pass.
This combined configuration is NOT verified at 120 fps. Earlier PF120 numbers
must not be attributed to v6. No handling or off-road physics changes.
Next art priorities inferred from screenshot and foliage source: preserve crown volume
and shading across distant LODs (legacy SM_Canopy_0/1 LOD2/3 have shadows disabled),
reduce repeated verge clump silhouettes and improve grass/soil transition and grounding.
Evaluate each on the actual map at matching cameras, with image and timing comparisons;
do not reduce global quality further to claim the target. Photos remain art authority.


### VQ2 - 2026-10-21 local: visuals first, actual LiDAR forest and verges
Owner approved prioritising visuals after rejecting the PF120 quality reductions.
No additional global quality cuts; v6 visual preset remains TSR75, LOD4, VSM bias1
and four directional shadow rays with a120 cap (not a performance guarantee).

Changes:
- lidar_canopy_assets.py v5 bakes a three-view object-space normal atlas alongside
  each existing colour atlas. Far cards now rotate those normals into instance
  world space and respond to the level lighting instead of a broad radial normal
  and colour gradient. Four1536x512 normal atlases, six-triangle cards retained.
- Screen-size reference distances35/80/120 ->50/160/600m. These are authoring
  references BEFORE global LOD bias, instance scale and camera projection;
  do NOT claim geometric trees draw to600m in the saved LOD4 preset.
- Active CanopyKit geometric LODs0-2 cast shadows; LOD3 cards remain shadowless.
  The earlier foliage_perf_lidar_place.py shadow-disable helper targets legacy
  /Canopy/SM_Canopy_0/1, not the active /CanopyKit set. The confirmed regression
  was early card transitions and insufficient card shading, not proof that all
  active middle LODs had their shadows disabled.
- lidar_level_polish.py reapplies the new far shading. Tint/normal helpers search
  the connected output graph to avoid reusing detached expressions after rebuild.
- build_lidar_grass_gs3.py adds SM_GS3_Verge:72 fine curved blades,216/96/60 tris,
  varied22-57cm design heights, dark roots and green/straw variation. Its shader
  shares the pasture palette/travelling wind, with spatial height/colour variation.
- lidar_grass_gs3.py assigns the new rank mesh/material through the normal
  Install/Polish override. No new actor tick or collision. The initial road review
  still showed six-blade pasture LOD spikes, so near grass lower LODs are revised
  from144/40/12 to144/64/36 tris, with narrower1/1.35/1.7 width multipliers.
  Near spacing55cm, fade32-40m, far geometry range150m and wheel contact remain.
- Focused installer: Art/run_lidar_visual_quality.ps1 (with -Check), backed by
  Art/Unreal/lidar_visual_quality.py. No terrain regeneration or driving edits.

Saved-map verification: ground digest 6AE1F9489CE5EC408044BFEC06A9FE25 unchanged; 148385 canopy instances unchanged.
Per-component counts of forest, collision trunks and understory unchanged, saved
and reloaded; canopy source cache valid and repeated material application adds
no nodes. Saved/LidarAuthoringQA/VQ2/install.json and check.json hold evidence.
Initial source backup: Saved/LidarAuthoringBackups/VQ2-source; original content
backup: Saved/LidarAuthoringBackups/VQ2-1792636395597225400.

Actual-map images: Place/PF60-vq2-before-*.png and PF60-vq2-after-*.png, at the
paddock middle, gate, river and access. Gate tree line now shows shaded crowns
instead of broad flat sheets. The four 'after' images PRECEDE the final pasture
LOD refinement; final road and GrassCheck captures are recorded separately.

Capture timing is CONTENDED: Skate.exe (pid8252) was observed alongside Unreal.
These are NOT valid clean before/after cost estimates and are not120fps evidence.
Uncapped1600x900, TSR75 stationary samples640frames/site. Recorded meanFPS/p95ms:
site                 before         after(first visual iteration)
paddock middle       50.7/23.781     29.4/40.266
paddock gate         51.4/24.567     35.7/36.000
river                27.9/43.728     26.7/46.742
access               21.6/56.309     22.1/55.235
Full summaries include p99/max and GPU timing in playperf-vq2-{before,after}-summary.json.
Do not attribute this difference entirely to these changes or declare them free.
Both standalone capture processes exited normally; no whole-map performance claim.

Tooling issues recorded rather than hidden:
- First bake hit an orphan tint-node assertion; connected-graph lookup fixed it.
- Initial verge graph used an invalid VertexColor output label; corrected to the
  default RGB output, and used the existing custom dither pattern.
- Full install and later Grass import saved successfully but returned access
  violation exit code-1073741819 after logging normal shutdown. No material
  compile errors were logged. Fresh VQ2 -Check exited0 and validated connected
  normal output/tint idempotence; fresh standalone play exited0. The import
  shutdown defect is unresolved and the strict wrappers still flag it.
- Initial GrassCheck failed at950 distant instances because its18s delay ended
  during streaming. The checker now waits (bounded180s) for StreamingConsistency
  to leave busy BEFORE density assertions. Density thresholds are unchanged.


VQ2 final validation (2026-10-21 local):
- Final grass meshes saved with144/64/36 near and216/96/60 verge triangles.
  Grass install report ok=true, map_resaved=false; saved actor already configured.
- After waiting for actual streaming completion, GrassCheck in-world assertions
  passed:21982 near instances and11719 distant, bins40/80/125/150/180m =
  1259/3764/5289/1291/108. Three-layer rebuild has zero missing/extra instances.
  Wind scale2, muted audio and HUD toggle assertions passed. Contact bent counts
  36/22/31 and removed12/5/9. Far grass remains no-collision/no-shadow.
- IMPORTANT: this fresh PIE check ALSO returned-1073741819 after logging normal
  shutdown, despite report.ok=true. Thus the remaining issue is editor shutdown,
  not proven to be confined to importing. Strict GrassCheck wrapper correctly
  reports failure. Do not describe this as an entirely clean automation run.
- Fresh standalone final-road capture exited0 and was visually inspected, alongside
  the final GrassCheck paddock and contact images. Final road image is
  Art/Export/LidarStudy/Place/PF60-vq2-final-road-access.png. Gate before/after pairs
  remain the clearest crown-shading comparison. No Unreal left running.
- All six edited/new Python modules passed py_compile. No C++ build was required;
  no driving, terrain physics, grass streaming density/range or car tuning edited.
- Consolidated evidence Saved/LidarAuthoringQA/VQ2/review.json; final grass reports
  copied there so later GrassCheck runs cannot overwrite this evidence. Final
  contended road timings are in playperf-vq2-final-road-summary.json. They remain
  unsuitable for a clean performance comparison. Owner visual acceptance pending.


### GD1 - gravel wheel dust in the LiDAR map (2026-10-21)
- Owner requested dust on gravel. Enabled the existing three-layer dry-dust Niagara system through the map's vehicle-surface coordinator, intensity 1.2 (previously zero). Shared FX assets and mud intensity/system were not edited. Standalone legacy fixtures stay at zero to avoid duplicate clouds. Both LiDAR install paths now retain this policy, including cached install paths; both LiDAR checks validate it.
- First real Riverside access drive reached 51.2 km/h with zero dust: the smooth road collision material reports Surface.Tarmac, while authored terrain identifies Gravel. GTDustLab now uses the authored classification. GTTractionComponent caches AuthoredSurface, GroundWetness and GroundWaterDepthCm from its EXISTING per-wheel surface query; the cosmetic effect adds no terrain query. This does not change the physical SurfaceTag, tyre grip, steering, support or deformation. Authored Mud/Grass/FirmGround override legacy dust classification; legacy maps retain fallback. Water depth and local/weather wetness suppress emission. Native gravel uses the existing grey-brown gravel tint.
- Source: Source/GrandTour/Vehicle/{GTTractionComponent.h,.cpp,GTDustLab.h,.cpp,GTDustLabTests.cpp}. Authoring: Art/Unreal/lidar_gravel_dust.py, Art/run_lidar_gravel_dust.ps1, install_lidar_study.py, install_lidar_place.py, check_lidar_study.py, check_lidar_place.py.
- Focused install backed up the map under Saved/LidarAuthoringBackups/GD1-1792641785623843900, saved and reloaded. Ground digest unchanged: 6AE1F9489CE5EC408044BFEC06A9FE25. Mud system and intensity 1.4 unchanged; no water or geometry edits. Installer completed assertions, then encountered the pre-existing editor shutdown access violation (-1073741819). Strict launcher rejected that process; install-process.json records it.
- Build succeeded. GrandTour.DustLab.Emission and MudFlick: 2 passed, 0 failed. Emission tests now cover authored firm gravel without a deformable patch, native/subsystem water, airborne contacts, non-dust authored terrain overriding a legacy gravel contact, and legacy/snow behaviour. Python syntax checks passed.
- Actual-map review: first native-aware drive emitted 99 peak particles then suppressed emission in gravel authored at roughly 0.7-0.8 wetness. Functional gates passed; that review also hit the known shutdown fault. A dry-corridor review helper initially used the editor actor API during PIE; corrected to runtime relief tiles, failure report retained.
- Final review uses an existing 150 m Riverside access corridor beginning at road point 303, around (-54297,-12023) cm, with authored wetness about 0.25; no weather/soil override for the dry driving. Reached 51.12 km/h, peak 199 live particles. Captures show 109 and 173 particles; tyre puffs and drifting trail are visible in sun and subdued in deep shade. Idle rate zero, wet override stopped new emission, old particles fully drained after 14 seconds, legacy dust suppressed. Final review and process both passed, exit 0. Images and reports: Saved/LidarAuthoringQA/GD1. No Unreal left open.
- Rates/lifetimes remain bounded, old particles retain birth tint and world positions, and drained systems deactivate. This was a functional/visual check, not a before/after GPU benchmark or a 120 fps claim. No car handling parameters or shared spray assets were changed.


### RH4 - bounded rally reversal response and runoff repair (2026-10-23 UTC)
- Full audit/evidence/owner drive: docs/LIDAR_RALLY_HANDLING.md RH4. Retained one
  input change: deliberate full opposite steering blends to 12/s above 30-60
  km/h, with existing low-range/mud/water gates. Initial turn-in/release remain
  6/8. Steering lock, tyre forces/recovery, drivetrain and saved v6 graphics
  unchanged; audio muted. Extra-lock experiment rejected and removed.
- Added LandscapeRecessDepthCm default400; existing rally map uses5 cm. Assets
  backed up before rebuild. Save/reload and297 dry Gravel samples passed; LiDAR
  map unchanged. Matching screenshots show the broad runoff trench removed.
- Guarded final build and10 native tests passed. Real-key 80 km/h reversal to
  90% opposite input fell from332/297/296 to185/194/200 ms (RR/BMW/Suzuki).
  Baseline and candidate completed full controlled laps, exit0; no uniform
  tracking improvement claim (RR max offset2.47 ->3.41m). Owner feel gate open.
- Final captured editor mean11.84-12.01ms, p95 13.14-13.67ms, worst162-181ms.
  Actual viewport1274x682 despite1600x900 request; Python control included.
  No120fps claim or graphics reduction. Prior first-frame759/1591ms baseline
  artefacts were report serialization, not proven GC; raw captures retained.
- Low-range response/reversal gates zero for all3. Live mud trial overallFAIL:
  RR43.41m pass; BMW-1.89m stalled; Suzuki6.70m below10m. River remote-contact,
  shore-opening and3528 height comparisons passed. Offroad and reversal runs
  returned-1073741819 after shutdown; recorded separately from in-world results.
  Startup SparseArray crash also remains recorded; engine issue not solved.
- Final visual/functional Review passed exit0 (98.18km/h straight smoke,
  dust/checkpoints/service BMW swap). Saved/RallyHandlingQA/rh4-final-review.
  Launch Art/rally_handling.ps1 -Mode Play. A/B console:
  gt.Vehicle.CountersteerResponse 0/1. No user Unreal killed; old document bytes
  preserved on append. All3 full laps and10 tests do not replace owner drive.


RH5 (2026-10-23/24 UTC): owner requested less smooth gravel, thrown stones and visible
steering sway. Added circuit-only 4 cm firm physical relief, corrected authored
Gravel recognition in the existing chip emitter, and bounded high-speed firm-ground
suspension compliance with exact low-range restoration. Contrasting RR/BMW/Suzuki
probes, full corners, native regression suite and live off-road/river evidence are
recorded in docs/LIDAR_RALLY_HANDLING.md and Saved/RallyHandlingQA/rh5-validation-summary.json.
Keep documented route/process failures separate from successful in-world checks.
Graphics unchanged, audio muted; owner drive still required. Historical
LidarAuthoringBackups was inspected only; no deletion.

RS1 (2026-11-05): owner chose L_LidarStudy for the supplied dense, varied,
colourful style reference (Art/References/ReferenceStyle/2026-11-05.jpg).
Map-wide coordinated near/far/ground grass palette, lighter foliage and skylight;
219 additional native-kit verge plants in a bounded access-road study. Pastures
excluded; terrain digest, original forest/understory counts and grass distances
preserved before/after and after save/reload. Initial banded colour trial replaced
by irregular patches (rs1-2). Both installs and all three standalone view captures
exit 0. Final GrassCheck passes: coverage, streaming consistency, bending/removal,
muted audio; process exit 0. Four short matched stationary GPU means essentially
unchanged (details in docs/LIDAR_REFERENCE_STYLE.md); not a driving benchmark or
120 fps claim. No handling/terrain regeneration or graphics reduction. Rebuild
hooks preserve the style; full rebuild pipeline not rerun. Original binary backup
Saved/LidarAuthoringBackups/RS1-1793911144198362000. Final evidence and images:
Saved/LidarAuthoringQA/RS1/review.json and Images/. Owner visual/drive acceptance
remains open. No Unreal left running; no commits or unrelated reversions.
RS2 road material follow-up, 2026-11-05: warmer softer gravel, lifted mud midtones,
and live rut/lip colour response saved to M_Terrain/M_Detail. Map hash unchanged;
no physics or geometry changes. Clean reapply and saved-material check exited 0;
reapplication stable. Three gravel probes remained firm (zero sinkage/softness).
Short low-range mud drive progressed 21.20 m and changed sampled surface height
by up to 8.83 cm. Four matched stationary performance views showed no observed
cost increase; this is not a full performance or handling acceptance claim.
Evidence, initial rejected shader-edit attempt, limitations and previews:
Saved/LidarAuthoringQA/RS2/review.json. Original material backup:
Saved/LidarAuthoringBackups/RS2-1793912450057048800.
RS3 river planting, 2026-11-05: replaced repeated low ferns in the bounded river
reach with 2,354 plants across 270 mixed clusters, nine mesh shapes and restrained
sage/olive/gold colour variation. Heights, widths, spacing and exposed gravel gaps
vary. Original outside-reach instances preserved, 270 cm road clearance; terrain,
water, solid objects and roads unchanged. Saved reload, deterministic reapplication
and final runtime captures passed; both final Unreal processes exited 0. Sparse
first pass rejected visually. Original map backup:
Saved/LidarAuthoringBackups/RS3-1793913658946374900.
Evidence and same-camera before/after: Saved/LidarAuthoringQA/RS3/review.json.
RS4 steep-bank material, 2026-11-05: replaced top-down-only rock projection with
world XY/YZ/XZ blending in M_Terrain/M_Detail. Warmer stone, irregular earth/moss
pockets and restored rock contrast in rs4-2. Map SHA unchanged; all other custom
programs and final property connections preserved. Repeat application and fresh
saved readback passed. Final install and capture processes both exited 0.
Original material backup: Saved/LidarAuthoringBackups/RS4-1793916564645915000.
Evidence: Saved/LidarAuthoringQA/RS4/review.json and Images. This changes the surface
appearance, not slope geometry; no new performance/handling benchmark was run.
RS5 bank planting, 2026-11-05: root support and plant habit corrected in the river
reach. Removed 65 unsupported tree ferns; replaced 253 low fern clumps with arched
kiokio fitted downhill, narrowed across the bank and rooted into it. Shrubs stay
mostly upright on viable ground; moss/root mats flatten to the face. Flat and
outside-study transforms preserved exactly. 873 root crowns checked at eight rim
points each; maximum rim gap -5 cm. Saved reload, idempotence and runtime material
preservation checks passed; final install and review processes exited 0.
Backup: Saved/LidarAuthoringBackups/RS5-1793917649476001900.
Evidence/limitations: Saved/LidarAuthoringQA/RS5/review.json. PIE ran under memory
pressure; streamed grass in the pictures is not a density/performance comparison.
2026-11-05 RS6 - user-selected rocky river bank
The river bend now uses 21 partly buried angular outcrop pieces in seven overlapping
formations. 84 upright rush, tussock, compact shrub and flax clumps are rooted on
actual collision-traced rock ledges and seams. Flat fern rosettes are cleared from
the outcrop footprints. 55 obstructing tree visuals and their 55 trunk colliders
were removed together; all other instance transforms are preserved exactly.
The map-owned M_BankStone uses the same world-space rock texture, scale and
stone/earth/moss pigment code as RS4's bank. It replaces the imported pack's pale
rock and bright green caps. New ledge plants use MI_NZ_Foliage_Bush.
No DEM, road, water, terrain material or lighting change belongs to this pass.
Four root probes per plant are buried at least 4 cm into rock. Outcrop support
samples are embedded by 55 cm; full rock bounds remain at least 15.26 m from road
centreline segments. Tree/collider root pairs are checked after clearing.
Recipe: Art/Unreal/lidar_rocky_bank.py. Guarded repeat install:
  powershell -File Art/preview_lidar_rocky_bank.ps1 -Install
RS3 reapplies RS6 after RS5 when rocky-bank.json exists; RS3/RS4/RS5 review scripts
recognise the RS6 saved checkpoint. Full terrain regeneration was not rerun.
Backup: Saved/LidarAuthoringBackups/RS6-1793920301782955600/L_LidarStudy.umap
QA: Saved/LidarAuthoringQA/RS6/install.json, validation.json and Final-*.png.
Visual evidence is from the editor viewport, not a new driving/PIE benchmark.
2026-11-05 RS6 REJECTED by owner after visual review.
The oversized, separated boulders and perched shrubs do not meet the requested
riverbank quality. Restore the pre-RS6 saved map; archive the rejected map and
disable rocky-bank.json so normal regeneration does not reapply this attempt.
RS6 code and screenshots remain as rejected experiment evidence, not approved art.
Next design work should prove one small bank section first: embedded, connected
rock structure, crevice-rooted vegetation, and material/light coherence. Do not
repeat the rejected boulder row across the river reach.
2026-11-06 PHOTO-BASED REFERENCE AND ACCEPTANCE CONTRACT
Owner corrected generic generated fern repetition and asked to use the existing
site photographs. Photo-based study v03 received positive direction feedback.
Primary photos: 04 steep-bank growth; 08 layered/varied fern understory; 15 warm
gravel/moss transition. Original photos retain authority over generated details.
Study: Art/References/ReferenceStyle/PhotoBased/waimeamea-bank-v03.png
Plan: docs/LIDAR_RIVERBANK_ACCEPTANCE.txt (five evidence-backed acceptance gates).
Generated concepts v01/v02 are superseded. Do not replace the photographed fern
community with a generic shrub garden or enforce the discarded three-fern cap.
Current implementation remains RS5; new implementation gates are NOT TESTED.
2026-11-06 - RS7 FIRST BOUNDED RIVERBANK SECTION BUILT
The owner authorized implementation after endorsing the photo-based v03 direction.
The saved L_LidarStudy map now contains a 22 m river frontage by 15.6 m slope span,
centred at -45800,-31600 cm. Four bank-specific fern forms (12 mesh variants),
152 ferns, 51 grass clumps, 14 small toe-cobble clusters, fitted moss/earth/rock
and 12 local bark overrides replace 74 low plants within this bounded section.
Shared plant assets remain unchanged. No whole-bank expansion was performed.

Review: Art/Export/LidarStudy/FirstSection/Review/index.html
Five actual standalone game views are supplied beside owner photos 04/08/15,
the original woodland style image and approved v03 study. Four matched before
views are included. B03's original camera was below ground, so no invalid before
view is presented. A roughly 12-second actual-game camera sequence is included;
it is sampled at 12 fps and is not a live performance measurement.

Root contact: 608 probes, maximum positive gap 1.2 cm. Surface registration error
at five probes: below 0.04 cm. Repeat-build and saved/reloaded snapshots match
(229 local instances). Outside low-plant hash preserves 207399 instances. Tree
visual/collider total remains 148385. Original terrain digest is unchanged.
Saved v6, 1600x900: four warmed matched views show mean GPU differences from
-0.28 to +0.56 ms; no graphics-preset reduction. New small-foliage batch shadows
were disabled to meet the provisional additional-cost budget, preserving geometry.
No 120 fps claim is made.

The new validate runner passed against the final saved map. A standalone ford
smoke test moved 8.6 m without an engine-flood event; it does not prove a complete
crossing. Acceptance gate D remains NOT TESTED in full. Owner visual acceptance
is PENDING. The bounded section is delivered for visual review, not certified
for expansion. Gate evidence, limitations, hashes and rollback instructions are
in the review directory. The original brighter woodland reference remains visible
in the comparison; an exact visual match is not claimed.

Backup: Saved/LidarAuthoringBackups/RS7-1793994925613427600/
Recipe: Art/Unreal/lidar_first_section.py
Validate/rebuild wrapper: Art/rebuild_lidar_first_section.ps1
Manifest: Art/Export/LidarStudy/Place/first-section.json
The rejected RS6 rocky-bank.json remains disabled.
2026-11-06 - RS7 GROUND MATERIAL DETAIL FOLLOW-UP
The owner approved the improvement but reported blurred/flat ground. The two
map-owned bank ground materials now use 2 m root/litter soil detail, 1.1 m rock
fractures and 35 cm mineral detail, with filtered world-space bump, cavity shading
and spatial roughness/dampness variation. Two map-owned 2K soil textures remain
resident; shared source textures and global rendering settings are unchanged.
This is shading relief, not physical displacement: map geometry, plant placements,
root support, collision and exposure remain the previously checked version.
The first runtime attempt flattened the inherited linear-data rock range; this
was corrected before the final ground-final captures. The final standalone game
captures reload the saved material assets successfully. Editor preview images and
the superseded ground-detail capture are diagnostic, not delivery evidence.
Review and final timing record:
Art/Export/LidarStudy/FirstSection/Review/GroundDetail/index.html
Art/Export/LidarStudy/FirstSection/Review/GroundDetail/evidence.json
Implementation: Art/Unreal/lidar_bank_ground_material.py
Material backup: Saved/LidarAuthoringBackups/RS7Ground-1794001850837697000/
Earlier first-section images and motion clip remain historical evidence. The
original review page links to the current ground-material comparison.
2026-11-06 - RS7 PHYSICAL SURFACE RELIEF FOLLOW-UP
The owner reported that the textured ground still read as flat and instructed
that discovered causes should be implemented. The bank mesh itself is rebuilt:
10 cm sampling, 70648 faces, irregular soil hummocks, embedded mineral features,
stepped rock lips facing the river, and several stronger root runs. Mild cavity
colour follows geometric recesses. This is a geometry change with matching
complex-as-simple collision, not another shading-only update.
The approved plant layout is frozen in plant-layout.json for deterministic rebuild.
6191 contact constraints preserve existing roots and low fronds. All 229 local
instance transforms and 207399 outside low plants remain unchanged. Validation
covers 608 root probes and 10285 frond samples across 152 plants; penetration did
not increase. The original procedural terrain digest, road network and exposure
remain unchanged. Only the fitted first-section surface asset is reimported.
Source recipe: Art/Unreal/lidar_bank_relief_detail.py
Data: Art/Export/LidarStudy/FirstSection/physical-relief.json
Build: Art/Blender/build_lidar_bank_surface.py
Review/evidence: Art/Export/LidarStudy/FirstSection/Review/PhysicalRelief/index.html
Art/Export/LidarStudy/FirstSection/Review/PhysicalRelief/evidence.json
The older GroundDetail images are the preceding material-only revision. Current
first-section review links point to the physical-relief comparison. A complete
live walking/driving route remains a separate gate, not implied by these probes.

2026-11-06 - FOREST ATMOSPHERE FOLLOW-UP
Owner: add forest fog and improve distant forest depth while keeping the original
colourful woodland reference. Existing height fog began at 1100 m, missing most
forest views. Saved L_LidarStudy now uses light height haze from 18 m, density
0.024, falloff 0.1, opacity cap 0.62, base elevation 45 m, cool luminance
(550,850,1050). Two low-density LocalFogVolume actors sit deeper in the river
woodland; full volumetric fog stays off. Sun, sky light and exposure unchanged.

Two longer geometric tree-range trials were measured and rejected: the broad
extension cost about 9-10 ms in forest views; the modest trial still reached
+3.62 ms. Final is the measured fog-only state. The four original canopy meshes
were restored byte-for-byte from the pre-change backup, retaining all tree LODs.
Distant forest improvement in this pass comes from depth-dependent colour and
contrast. Better distant crown shapes still need better cheap representations;
this pass does not claim that asset work is complete.

Plant snapshot, outside planting, DEM digest, tree counts and near LOD checks
passed. Final saved map was rendered in standalone with identical cameras and
saved v6 at 1600x900. GPU mean changes in one matched pair were -0.47 to +1.63 ms across
four views; not full-route performance proof. Source screenshots are unchanged.
Authoring editor had one abnormal teardown after successful saving/validation;
subsequent editor and standalone runs exited cleanly. No new runtime material
compile error found. Full route, temporal transition and owner visual gates remain.

Recipe: Art/Unreal/lidar_forest_atmosphere.py; settings in
Art/Export/LidarStudy/Place/forest-atmosphere.json.
Review: Art/Export/LidarStudy/FirstSection/Review/Atmosphere/index.html
Evidence: same directory/evidence.json; isolation and rejected trials under
Saved/LidarAuthoringQA/Atmosphere and Saved/LidarAuthoringQA/RS7.


PERCEIVED DETAIL BOUNDED REVIEW - 2026-11-06
Built a 4 x 4 m normal-detail ground patch, corrected one Cascade fern UV/baked-occlusion variant, and an AO/Nanite-voxel version of 48 existing beech trees. Original ground colour, vegetation layout, root contacts, terrain and collision are preserved. Original LOD geometry supplies the 48 trees' shadows. TSR thin-geometry detection is enabled globally for this review candidate.
Actual review: Art/Export/LidarStudy/FirstSection/Review/PerceivedDetail/index.html
The review contains seven matched unretouched game views, the original style reference, site photographs, a labelled generated study, and four moving before/after clips. Motion samples are 12 fps, not a performance measurement.
Three warmed alternating A/B pairs, 1600x900, TSR 75, saved v6 preset. Median paired GPU changes:
  D01: +1.018 ms
  B01: +0.786 ms
  B04: +1.193 ms
  F01: +0.912 ms
  F02: +1.531 ms
  G01: +0.931 ms
  T01: +0.264 ms
Observed +1 ms median gate: NOT PASSED. Temperature and clock variation prevents a tightly controlled sub-millisecond conclusion. Full raw timings, memory/pass metrics and telemetry remain in evidence.json and gpu-telemetry.csv. No whole-world or target-FPS claim.
Geometry validation: 229 local instance hash unchanged; 207399 outside low-plant instances unchanged; 148373 main-forest geometry trees plus 12 local trees and 148385 existing colliders; 48 identical stand transforms; 608 root probes; 10285 frond probes on 152 plants; no additional clipping. Original CanopyKit packages and project descriptor match the pre-pass backup.
Not promoted: POM ground, Nanite bank skin and the custom 24-view depth proxy. Captures with missing voxel material usage were invalidated. Ground normals add shading detail, not new silhouettes. This remains a bounded candidate with OWNER VISUAL ACCEPTANCE PENDING; the reference's colour composition and variety are not fully matched.
Recipe: Art/Export/LidarStudy/FirstSection/PerceivedDetail/accepted.json. Asset-only rebuild: Art/rebuild_perceived_detail.ps1, with Unreal closed. Requires the existing saved stand; full-world regeneration is not integrated. The individual bake/import steps ran successfully; the convenience rebuild wrapper has not been rerun end-to-end.
Variant switching: python Art/tools/select_perceived_variant.py baseline|final (Unreal closed). This switches experiment assets, not the entire map or global TSR config. Full pre-pass files are recorded in Saved/LidarAuthoringQA/PerceivedDetail/backup.json; Config/DefaultEngine.ini was also backed up there.


SHRUB SHADOW CORRECTION - 2026-11-06
Restored dynamic and two-sided shadow casting on 2446 woody shrubs and 152 RS7 bank plants (2598 unchanged transforms). The earlier no-shadow foliage policy removed self-shadowing and ground anchoring; mesh sections already supported shadows. Corrected the installation, reference-style, bank planting, river-variety, river-detail and first-section authoring rules. Planting hashes, terrain and root-contact checks pass.
Actual before/after review: Art/Export/LidarStudy/FirstSection/Review/ShrubShadows/index.html
Single warmed A/B GPU deltas (indicative; thermal variation and prior +1 ms gate remain unresolved): D01 +3.65 ms, B01 +3.88 ms, B04 +3.02 ms, F01 +0.35 ms.
Backup: C:\GrandTour\Saved\LidarAuthoringBackups\ShrubShadows-1794020359369439800


FERN FLOOR LAYER - 2026-11-06
Added a bank-owned fitted forest-floor layer: 1339 fallen leaves, 117 twig fragments, 303 connected root runs and 271 moss clods, totalling 30840 static triangles. A 512x512 short-range occlusion bake traces the actual 152 fern instances and fitted bank. No changes to the underlying terrain mesh, collision, vegetation placement, sun or exposure. Planting and root-contact checks pass. Small decorative pieces have no collision.
Review: Art/Export/LidarStudy/FirstSection/Review/FernFloor/index.html
Rebuild: Blender --background --python Art/Blender/build_fern_floor.py, then run fern_floor.run() in the existing authoring editor. Bake is static: rebuild after changes to the bank or planting. The perceived-detail material rebuild preserves this installed layer. Full-world regeneration is not integrated.
One warmed A/B GPU comparison (indicative, not a repeated gate): D01 +0.03 ms, B01 -0.07 ms, B04 +0.10 ms, G01 -0.02 ms.
