# Benmore integration: our ground, surfaces, spray and deformation in the Gaea review level

Main session, 2026-10-12. The owner: "Let's implement these new materials into gaea benmore review level. That is
where I am doing my testing now. It helps to see performance on a larger map."

**Owner's choices:**
- **All four parts:**
  - ground detail and scatter;
  - surface types and wheel spray;
  - deformable gravel roads;
  - mud bogs.
- **GPT (the Codex app) is not running.** We may replace and add anything in the Benmore files.
- **At the end:** write a prompt that onboards GPT to the changes.

**The level:**
- `/Game/GrandTour/Demo/BenmoreRoads/Gaea/L_Benmore_GaeaReview`: 2240 × 2404 m, about 5.4 km².
- A 2017² Landscape at 124.0079 cm per quad, Z scale 200, at (-125000, -125000, 0) cm. X is east, Y north.
- Its own terrain material, a review variant of `M_Benmore_FullCover`: compact and loose gravel road layers with
  parallax, built by `Art/Unreal/benmore_gaea_materials.py`, `benmore_reference_surface.py` and
  `benmore_gravel_pom.py`, plus `benmore_ground_detail.py`.
- Landscape grass tussocks.
- **No GTTerrainBuilder spec**, so no route sections, mud patches or surface tags: one firm-ground physical material.

Docs: `docs/BENMORE_GAEA_INTEGRATION.md`, `BENMORE_ROADS.md`, `BENMORE_GRAVEL_POM.md`, `BENMORE_VEGETATION.md`,
`BENMORE_PERFORMANCE_AUDIT.md` and `BENMORE_OPTIMISATION_PLAN.md`. The last is another session's BO1-BO8; its BO1
finding holds: landscape grass in the Lumen and ray-tracing scene costs about 8 ms.

## 0. Rules

`docs/MUDRUNNER_LESSONS_PLAN.md` section 0 holds: no timing (the owner measures performance on this map); run with a
game open and name it, never close it; the look rejections; commit only your hunks; never push.

- **Before EVERY Unreal or UBT run:** `powershell -NoProfile -File Art/wait_unreal_free.ps1` as its own command.
- **The MW1 agent** (mud and water surfaces) may still be running. It owns `Art/Unreal/live_mud_style.py`, the Niagara
  setup library and `GTSprayArt.cpp`. Don't edit those until MW1 commits. If a build fails in its files, wait.
- **The Benmore files** are untracked work by the Codex app. We may change them now. Commit the Benmore scripts we
  change or depend on, so the integration is reproducible. List them in the GPT prompt (B3).
- **Benmore water** (rivers, creek, M_GT_Water, the GTWaterField/Sheet code) stays as it is. Our rut water lives only in
  deform patches.
- **Performance hygiene** (the owner measures; we don't):
  - new scatter is out of Lumen and ray tracing (`bAffectDistanceFieldLighting`/`bAffectIndirectLighting`/
    `bVisibleInRayTracing` off), and pieces under 5 cm cast no shadows;
  - sensible cull distances;
  - a console switch for every feature.

## B1: ground detail, scatter and surface types (now; nothing of MW1's)

1. **Inventory (report first).** List:
   - the review landscape's layers (names, weight-blend), its material and instance chain, and which script builds
     them;
   - its grass types and their settings;
   - the road data (centreline polylines or masks, where they live);
   - the Gaea masks available (slope, flow or wet, channel, lake);
   - the "Review locations" from BENMORE_GAEA_INTEGRATION.md.
   Run one inspection commandlet; read the rest from scripts and docs.
2. **`MF_GT_GroundDetail`.** Move GR2's strip detail code (`Art/Unreal/ground_detail.py`) into a material function:
   - inputs: layer colour, the scrub-soil and under-grass weights, world position, the POM toggle;
   - outputs: colour (a luminance modulator with 30 % hue, as GR2), normal, roughness, AO;
   - TA_GD arrays, the A2 anti-tile, POM within 15-25 m and a fade between 25 and 40 m, all read from
     `MPC_GT_GroundDetail`.
   Re-point the strips' materials to it only if it compiles to the same result; otherwise leave the strips alone and
   report.
3. **Benmore material:**
   - call the function on the review material's non-road ground layers (grass ground, scrub, dirt, verge soil);
   - keep the gravel road layers as they are (Codex's approved gravel with its parallax);
   - make it part of the Benmore material builder, so a rebuild keeps it.
   - Switch: `gt.Ground.Detail` 0/1 (the same MPC).
4. **Scatter as landscape grass.** New grass types `LGT_GT_SoilScatter` and `LGT_GT_GrassLitter` with the GR2 meshes:
   - **Placement:**
     - clods and pebbles on soil and scrub layers; litter near tussock ground; twigs sparse;
     - the GR2 densities (clods 0.6, pebbles 1.5, twigs 0.05 per m²; litter 0.25 where tussock ground);
     - clustering from a world-position noise in the grass output weight (the GR2 3 m cluster, sharpened);
     - none on roads or water.
   - **Per variety:** align to the surface, random yaw, scale ranges, a negative Z offset for the manifest embeds.
   - **Cull:** pebbles and twigs start 15 m / end 25 m; clods 20 / 35; litter 15 / 25.
   - **Lighting:** out of Lumen and ray tracing; no shadows for pebbles, litter or twigs.
   - Tussock bases are skipped on Benmore: grass types can't put them under GPT's tussocks. Report.
   - **Switches:** `gt.Ground.Scatter` 0/1 and `gt.Ground.ScatterDensity` (an MPC scale on the grass weight; flush the
     grass cache when it changes).
5. **Surface types.**
   - **Physical materials per landscape layer:**
     - compact gravel → a firm gravel surface;
     - loose gravel → a loose gravel surface;
     - verge, grass and scrub → Dirt;
     - creek bed and wet → Mud or wet Dirt.
   - Use the existing GT surface rows and tags. Where no gravel row exists, use Dirt's traction numbers under a gravel
     physical material and say so.
   - **Add to `UGTSurfacePhysMaterial`:**
     - `bGravelSpray`, default false: this surface throws gravel grit and dust;
     - `SprayTintA`, `SprayTintB` and `DustTint`, default zero (zero = the code's own defaults).
   - Set them on the gravel physical materials from the Benmore gravel palette. B1b wires the spray to them.
   - Report the layer → physical material table.
6. **Tests and pictures.**
   - Every Mud, Snow, Gravel, Spray, Relief and Scatter test passes, CRCs unchanged. The biome test shows The Hide and
     L_Proving unchanged.
   - **Pictures** at three review locations (sun behind the camera):
     - on foot at 1.7 m on open ground: `BI_OnFoot_<loc>.png`, plus a detail 0 / scatter 0 pair;
     - a road-verge view: `BI_Verge_<loc>.png`;
     - a far view: `BI_Far_<loc>.png`.
   - Report the instance counts near the camera (from the grass stats) and the material instruction and sampler
     counts against today's.
7. **Commit:** "Benmore B1: ground detail, soil scatter as landscape grass, surface types", including the Benmore
   scripts it changes or depends on.

*B1 done 2026-10-12 (VEHICLE_BUILD_SYSTEM 108; GoWR open at every run; no timing; tests waived by the owner mid-stage, the one
pre-waiver run 22/22 and biome PASS). Inventory: M_GC_Terrain has no layer blends (six paint layers, Scrub 1.0 everywhere, none
sampled), so "layers" are its mask regions; a GTTerrainBuilder exists (Benmore_RL_CrossingProfiles, 2 sections). MF_GT_GroundDetail +
MPC_GT_GroundDetail built; the strips not re-pointed (a third collection: "A material may only reference 2 different collections");
the review material now reads MPC_GT_GroundDetail + MPC_TrackPaint (Codex's gravel POM switch moved to BenmoreGravelPOM), pixel 1,090 ->
1,827, samplers 24 -> 28. LGT_GT_SoilScatter / LGT_GT_GrassLitter (pebbles and twigs as pivot-sunk SM_GD_*_LG copies: no Z offset
in FGrassVariety); a collection value does not reach the grass weight render, so gt.Ground.Scatter scales the grass densities.
Surfaces by a Landscape Physical Material Output: GravelFirm / GravelLoose (Dirt's numbers, bGravelSpray, palette tints), WetGround
(bed, silt banks, lake), FirmGround (the rest). No water asset touched; detail and scatter off the beds, banks and lake. Pictures
Art/Export/BenmoreB1/BI_*.png.*

## B1b: spray on Benmore surfaces (after MW1 commits)

Wire `GTSprayArt.cpp`:
- `bGravelSpray` on the contact's physical material switches on the gravel grit and dust layers, as `bInGravelPatch`
  does;
- the physical material's tints override GritTintA/B and DustTint where non-zero.
Pictures: the car driving on a Benmore gravel road (chase and close), and on a verge.

*B1b done 2026-10-12 (tests not run (owner); no timing). The surface comes from the Chaos wheel state (FWheelStatus::PhysMaterial:
the landscape's physical material output reaches the wheels' heightfield, so no UGTSurfaceQueryLibrary trace per tick):
UGTSprayComponent::GravelSpraySurface. bGravelSpray switches GravelGrit and GravelDust on as bInGravelPatch does, and at gt.Spray.Art 1
stops the grey CPU Dust spheres there as a gravel patch does (Benmore gravel is Surface.Dirt); non-zero SprayTintA/B and DustTint
override the code's tints. Mud roads (moved from MRD1): the fine mud rate x AGTMudPatch::MudRoadSprayScale (MRD1's field) when over 1,
in that patch's box. Pictures Art/Export/BenmoreB1b (Art/benmore_b1b.ps1, capture.json, each with a same-frame _NoSprites):
B1b_Gravel_Chase 11.7 m/s, grit 120 / dust 60; B1b_Gravel_Close 1.2 s into a launch, 2.5 m/s, grit 25 / dust 9; B1b_Verge 8.6 m/s on
FirmGround, grit 1 / dust 0 and the CPU grey Dust 118 (today's greybox on Dirt). The spray is low-contrast on the road: the B1 tints
match the road gravel (owner's look). Three capture runs (the first two: the scripted car left its path, the close camera stood in a
tussock, a high camera hid the spray against the road).*

## B1c: paler gravel dust, no soot in shadow, bigger grit (the owner's look at B1b)

DustTint the road's matrix x1.35, SprayTintA/B the stone faces x1.15 / x0.85; the dust pale in the car's shadow (median luminance in
shadow at least 0.5 x in sun, B1b_Gravel_Close, P2c's method with the NoSprites difference as the mask); on bGravelSpray surfaces grit
1.5-4 cm and GritRate x1.5; B1c_Gravel_Chase's sprite pixels at least 1.5 x B1b's 83,054. The same three cameras.

*B1c done 2026-10-12 (tests not run (owner); no timing). **Soot:** P2c's emissive floor (DustTint x DustFloor) is absolute, so at
Benmore's fixed EV100 13.6 (a 60,000 lux sun) it was about 1/15,000 of the strips' (EV100 0.25 or under) and the dust in shadow showed
only Benmore's weak sky fill (shadowed ground 0.035 against 0.29 in sun). M_GT_SprayDust's floor now fades, past EV100 about 4, to a
display-referred one (x DustFloorDisplay 2.5 x 1/exposure: EyeAdaptationInverse); at the strips' exposures it is exactly P2c's.
**Tints** (benmore_gt_ground.TINTS): the matrix is GravelFirm's 15-35 % band (the packed fines; the loose surface's own low band is the
cavities between its stones), dust (0.243, 0.238, 0.224) on both. **Grit:** User.GritSizeMin / GritSizeSpan (1 + 2 by default, 1.5 +
2.5 on a gravel surface). Setup Art/benmore_b1c.ps1; pictures Art/benmore_b1b.ps1 -Stage B1c (Art/Export/BenmoreB1c), gates
Art/sample_benmore_spray.py (gates.json): chase sprite pixels 1,269,169 (15.3 x B1b's); dust in shadow 0.438 against 0.516 in sun,
0.848 (B1b 0.343); the same frame at DustFloorDisplay 1.5 0.765, at 4 0.891. The dust now reads white, and the low chase camera sits in
the cloud (a veil over the frame): DustFloorDisplay is the owner's number. A placed Benmore_VehicleSurfaceEffects (another session's
DustLab / MudFlickLab, saved into the review map 2026-10-12) replaces the spray's dust and mud while gt.SurfaceEffects is 1; the
pictures ran at 0.*

## B2: deform zones and streamed patches (after MW1 commits)

The strips' patches come from route sections and an apron of 4 MPC boxes. Neither scales to a 5 km² map with no
route builder. Design:

1. **`AGTDeformZone`** (placed in any level):
   - a spline with a width (roads) or a box (bogs);
   - medium (Mud/Gravel/Snow), a profile (mud variant or gravel firm/loose), PreChurnScale.
   - It tiles itself onto a world grid of 24 × 24 m tiles (192² cells at 12.5 cm). Cells outside the zone stay inert.
2. **Streaming** (UGTMudSubsystem):
   - at most 9 active tiles, nearest to the active vehicles and the on-foot player;
   - activate within 40 m, release beyond 60 m;
   - a released tile keeps its field's changed cells (sparse, compressed) in an LRU cache capped at 128 MB, so ruts are
     there when you come back.
   - Base heights come from the landscape's own height data (bilinear on its 1.24 m grid, the same surface the
     landscape renders), not the terrain spec.
3. **Visibility and apron without the 4-box limit.**
   - Active tiles write a coverage mask (zone membership, dilated by one cell) and a variant id into a small
     world-aligned RT co-located with the track paint's window (it scrolls with it).
   - The landscape material reads it: an opacity mask where an active patch draws, and the variant apron blend over the
     coverage gradient.
   - Report the masked-landscape implications. The owner measures the cost.
   - The strips keep their current MPC path, and their CRCs and tests stay unchanged.
4. **Benmore placement:**
   - **Roads:** gravel zones along the road centrelines, at the road width. The profile is firm on compact gravel and
     loose on loose gravel (by layer weight along the line).
   - **Bogs:** up to 6 mud zones from the Gaea masks:
     - flat (slope under 4°), low and wet (near the creek or channel, or a high flow mask);
     - at least 150 m², 15-40 m across, within 30 m of a road so they can be reached;
     - variants: Standard or Deep near water, Firm or Stony elsewhere; PreChurnScale 1.
     Report each bog's location so the owner can drive to it.
5. **Tests:**
   - zone tiling and determinism;
   - activate, release and reactivate with the field restored exactly;
   - the LRU cap;
   - coverage mask cells;
   - all existing tests pass.
   **A drive check on Benmore:** along a road through two gravel zones and into one bog, completing under the fixed
   step. **Pictures:** ruts in Benmore gravel, a bog before and after, the patch edge (apron) up close.
6. **Commits:** "Benmore B2a: deform zones and streamed patches", then "Benmore B2b: gravel roads and bogs on Benmore".

*B2a done 2026-10-12 (tests not run (owner); no timing; GoWR and the Codex app running). `AGTDeformZone` (GTDeformZone.h): a road
stretch (the road's own vertices plus 15 m either side, a width, an arc range whose two ends are waved cuts shared by key with the next
stretch, so stretches partition the road) or a bog blob (a box with a lobed outline); it carries an `FGTRouteSection`, so
`AGTMudPatch::ApplySection` takes it unchanged. **Units:** a tiled (gravel) zone's 24 m world tiles, 192 x 192 cells at 12.5 cm, the
field one cell wider each side (the overlap the neighbour owns; a wheel's stroke also goes into the live neighbour, `StampZoneNeighbours`,
and the noise lattice runs on in world cells); **a mud zone is one patch over its box, not tiles** (a fact against item 1: GR1c's pairs and
MRD1's braided tracks, debris, clod fields and chunks are laid out per patch box, its route through the box, its rim and its section
seed, so 24 m tiles would put a seam every 24 m; mud road stretches are kept to 30-60 m: their patches ran 41k-71k cells, the bogs'
110k-141k).
**Streaming** (GTMudSubsystemZones.cpp, a 0.1 s timer): foci the player's pawn and camera, any GTCarPawn possessed or over 3 m/s, a test
focus; on within 40 m of a unit's box, off past 60 m; nearest first, at most 9 tile-equivalents (9 x 192^2 = 331,776 cells; a mud
patch counts its own cells); one activation a pass. **Cache:** a released unit's changed cells (height, lump, offset, tracks, heading,
phase against its field at activation) zlib-packed into an LRU of 128 MB, restored after the pre-churn when the unit comes back.
**Base heights:** the patch mesh's landscape GetHeightAtLocation as before (the landscape's collision heights, 124 cm grid). **Coverage:**
a 1024^2 BGRA8 transient texture (4 MB), 25 cm texels over 256 m round the first focus, recentred past 32 m - not the track paint's
128 m window: a unit can be live 60 m + 24 m from a focus that is 20 m from that window's centre, 104 m per axis; R the zone share of
each texel's four cells, G the apron (200 cm round a mud zone, chamfer), B the variant; set into every landscape's dynamic material
instances (GTDeformCoverage, GTDeformWindow). M_GC_Terrain was already Masked (clip 0.5, the shore's hole): its opacity mask x
(coverage R < 0.5), and the apron leans its colour and roughness to the variant's mean bog albedo, noise-broken; pixel 1,827 -> 1,874,
samplers 28 -> 29 (Art/Unreal/benmore_deform_zones.py, hooked into benmore_gt_ground.attach so install_benmore_shore's rebuild keeps
it). The patch draws only its zone cells and a one-cell ring, the edge vertices 1 cm and the ring 4 cm under the ground (the landscape
covers them outside the hole), skirts 40 cm deep on its own region's border. A mud zone's pre-churn fades over 150 cm at a blob's edge,
at most a fifth of the half width across a road (64 cm), so the old tracks run across the running surface. Inside a mud zone the traction
reads the zone's PM_Mud / PM_Bog rows (Benmore's ground has no Mud or Bog layer). M_GT_Gravel_Zone: M_GT_Gravel copied with GravelTint;
the strips keep M_GT_Gravel. **Strips unchanged:** L_MudVariants Relief_OnFoot before (HEAD build) and after, Art/Export/BenmoreB2/Strips:
mean |diff| 1.44 of 255, the mud road band mean 1.53 (p99 10), sky 0.55, grass 3.57 (wind, TAA, the moving rut water); no systematic
change (diff.json, the x8 diff picture).*

*B2b done 2026-10-12 (tests not run (owner); no timing). Art/benmore_b2_plan.py -> Art/Export/BenmoreB2/plan.json; placed by
Art/Unreal/setup_benmore_b2.py (folder GT_DeformZones, the map saved after an unchanged-timestamp check; Benmore_VehicleSurfaceEffects
untouched). **Facts against the addendum:** T_Gaea_Flow is a flow-direction field (RG the downhill direction, A the steepness: 7.4 on the
bed against 29.9 elsewhere), not an accumulation - a D8 accumulation of the review landscape's heights (5 m) stands in, "top 25 %"
taken over the road's samples; no road comes within 40 m of the creek or channel (the bed's alpha: 61 m at the nearest on the Terrace
loop, 327 m on the Hillside branch) and the lake (ground under 48 cm) lies at the map's west edge, so every MudRoad stretch is a drainage
crossing; B1's physical material splits across the road (the wheel paths firm, crown and edges loose), so every stretch is
Loose-dominant (loose share 0.50-0.64) and no Firm gravel zone exists. **Roads:** 3,706 m; 39 gravel zones 2,759 m (Terrace loop 25 /
1,840 m, Hillside branch 14 / 919 m), 31 MudRoad zones 947 m (25.6 %; the 35 % cap not reached: runs within 30 m of another are dropped);
16-60 m mud stretches (the loop's seam splits one run 29 + 16 m), 27-118 m gravel. **Bogs:** six, all Firm or Stony (none within 40 m of
water), up to 40 m along the long axis and 15-28 m across it (405-654 m^2), 18-24 m from a road, 20-89 m from a MudRoad stretch; the landscape grass is kept out of them by a copy of
T_RL_Vegetation with their outlines painted out (/Game/GrandTour/Terrain/DeformZones/T_RL_Vegetation, swapped into M_GC_Terrain).
**Gravel tint:** B1's palette over the TA_GV mean (1.07, 1.00, 1.03) left the patch far warmer and darker than Codex's road at the live
tile's edge (display-linear ratio road / patch 1.35, 1.59, 2.21); x that ratio^(1/1.3) = (1.35, 1.44, 1.89) closed it to 1.16, 1.27,
1.56 - still visible (B2_Edge_PaletteTint.png is the first). Pictures Art/Export/BenmoreB2/B2_*.png: B2_Road_Mud and B2_Top from
capture.json; B2_Edge and B2_Road_Gravel(_NoDust) from capture_edge_gravel.json (the corrected tint; the scripted car left its path
once, the second start held it); B2_Bog_1-6 from capture_bogs.json (capture.json's bogs had lost their yaw: Rotator's positional order).
In B2_Road_Gravel the car at 7.4 m/s sank 5 cm (the Loose profile's cap) on all four wheels across two gravel zones; 9 tiles live,
5 released tiles cached in 114,880 bytes. Seen in the pictures, for the owner's look: the joint between a mud and a gravel stretch and
the live tile's edge are straight or cell-stepped lines; the bogs read as dark near-ellipses with a hard outline; the TA_GV gravel
shows its cell pattern and thin dark lines along the rut walls.*

*B2c done 2026-10-13 (tests not run (owner); no timing; GoWR open). **Gravel zones wear Codex's road:** M_GC_Terrain_Zone is
M_GC_Terrain itself, copied by benmore_deform_zones.attach_deform after it wires the review material (so install_benmore_shore's rebuild
remakes it), the deformation on top: setup_m6_mud's field displacement and slope (soft-capped at 0.3), Codex's `loose` taken to 0 where
the field has tracks in each of its five TRACKS nodes (the packed gravel), the parallax's strength x0.5 there, x0.92 value and a 12 %
windrow shade; pixel 2,071, samplers 32. A zone patch takes the landscape's own vertex normals (central differences on its 124 cm grid,
bilinear) and its vertex factory's tangent (N.z, 0, -N.x). No loose stones on Benmore zones. **The stones were not black from the
material:** B2_Edge looks 143 deg from the sun (into it), so every small mesh shows its shadowed side - Codex's verge stones draw as black
in the same frame; with the sun behind (B2_Road_Gravel, 24 deg) the same M_GT_GravelStone stones drew pale. What did come from the
material: M_GT_Gravel's FINISH blends to the strip's verge grass at |y| over 3.75-5.9 m (the strips' road runs along y = 0), so on
Benmore every gravel patch was the strip's grass colour - the sandy mosaic, and why no tint closed the gap. **Gate:** the 1 m strips
either side of the live tile's border differ by 12.6 / 12.9 / 12.8 % in that frame and by 12.6 / 12.6 / 11.8 % with no patch (the
road's own wheel path against its crown), so the border strips measure the road, not the seam; the patch against the landscape it
replaces, the same pixels (B2_Edge_NoPatch.png: the patches hidden, the coverage off): 0.08 / 0.08 / 0.14 % (edge-gate.json). **The
dither:** the coverage's A (each texel the mean of its four cells' opacity, blurred 2 texels, held to the patch's own drawn cells) gives a
pixel to the patch where the interleaved-gradient dither (with the frame index) is under A, faded over 40-60 m from the camera (not in
shadow passes), and to the landscape where not - never both, so no sinks and no z-fight; M_GC_Terrain pixel 1,874 -> 1,938, samplers 29 ->
31. **Mud zones:** every zone outline is tested at a point warped by one shared field (100-250 cm at 15 and 8 m, so stretches still
partition the road; ends included); a mud road's zone is 4 m wider than the road (TrackWidthCm keeps the tracks on it) and thins out over
a 1.5-3 m feather; M_GT_Mud_Zone is M_GT_Mud x MudTint, drawn by the dither. **Palette:** the landscape's base colour captured round each
mud zone (1.5 m squares 7-9 m off a road's edge, 6-8 m off a bog; median of 20-24), value x0.62 and saturation x1.15: soil about (0.24-0.34,
0.20-0.27, 0.13-0.16) linear to wet mud (0.09-0.12, 0.07-0.09, 0.04-0.05); MudTint = that over the variant's bake mean. The clods and
chunks keep the strips' red (their materials have no tint). **Far maps (no pop-in):** AGTDeformZone::BakeMudMaps at setup -
T_GT_MudZoneMask 4096^2 at 50 cm over 2,048 m from (-1,302, -1,258) m, BC7 (21 MB with mips), R the mud's opacity (48,127 texels), G
the apron 2 m out (26,722); T_GT_MudZoneColour 1024^2 at 2 m. The review material draws the mud as the zone's wet colour x the bog
bake's luminance (3 m tile) under R, and in the apron wet-darkens the ground (more on Codex's wheel paths: the tracks run on as wet dark
ruts) with splatter; the live patch crossfades in over 40-60 m. B2_MudFar: the stretch at 101 m, not live, drawn from the maps. **Bogs:**
not a profile path difference - the pre-churn log matches the strips' Firm bog (hummocks +-5-20 cm, surface -29.6..20.0 cm against
-29.3..19.9, 0.25 % of cells under the -25 cm table against 0.37 %); the live field over a 6 m square at the middle: Bog 1 -25.4..+7.7 cm
(sd 4.6), Bog 3 -10.3..+7.5 (sd 3.2). They read flat because the hummock amplitude is clustered low by design, the strips' bake was
near-black under Benmore's sun (now the palette), B2's camera stands 12 m outside at 1.7 m (Bog 3's middle 75 cm above the eye's
ground), and the -25 cm table lies under almost all of the floor (MRD1 moved the road's to -10 cm for the same reason). Not tuned
(a -10 cm table and PreChurnScale 1.5 are the obvious next step, for the owner's look). Vegetation painted out inside the inner 70 %.
**Spray:** GravelSpraySurface returns null inside a live mud zone (UGTMudSubsystem::IsInLiveMudZone). Pictures Art/Export/BenmoreB2:
B2_Edge (+ _NoPatch), B2_Road_Mud, B2_Top, B2_Bog_1, B2_Bog_3, B2_MudFar (capture_b2c.json; the edge from capture_b2c_edge.json, two
retakes for the capture script's own bugs: the projection is in the PIE viewport's 1274 x 682, not the picture's 1440 x 900, and the
twin); B2's versions in Art/Export/BenmoreB2/B2/.*

## B3: GPT onboarding prompt

Write `docs/BENMORE_HANDOFF_FOR_GPT.md`, a prompt the owner pastes into the Codex app:
- what changed in Benmore (files, assets, scripts, switches);
- what GPT now shares (the material function, physical materials, grass types, deform zones);
- how its builders must call them so a rebuild keeps them;
- the wait script and its mutex;
- the file-ownership rules;
- where the docs are.

## Decisions after B1c and MRD1c (main session, 2026-10-12)

- **Dust is GPT's.** The owner chose "GPT's dust wins". GPT's `Benmore_VehicleSurfaceEffects` actor
  (DustLab/MudFlickLab, `gt.SurfaceEffects`, docs/DUST_LAB.md) owns vehicle dust on Benmore. We stop all work on dust.
  - B1c's DustFloorDisplay stays where it is; it only matters at gt.SurfaceEffects 0.
  - Our gravel grit and mud spray stay unless GPT replaces them.
  - B3 must say this.
- **Mud roads (MRD1c, dfba690) are accepted for the owner's gate.** Irregular, tapered, reflective pools; braided
  tracks; silt surface.

## B2 addendum: what goes where on Benmore (main session, 2026-10-12)

**Road zones** (from `Art/Export/BenmoreRoads/road-manifest.json`: the Terrace loop at 6.4 m wide, the Hillside branch
at 4.4 m), cut into stretches of 30-120 m:
- **MudRoad profile (MRD1c)** where the stretch is low and wet: the Gaea Flow mask in its top 25 %, or within 40 m of the
  creek or channel masks, or under 3° slope near the lake. Cap: no more than 35 % of the total road length, so most
  driving stays on gravel.
- **Gravel (DG1b profiles)** everywhere else: firm where B1's PM traces said firm (the wheel paths), loose on the crown
  and edges. A zone's patch takes the profile by the dominant B1 physical material along the stretch.
- **Visual join:** the road zone's patch draws the deform material, and the landscape under it is masked (B2 item 3).
  The gravel patch must read like GPT's road gravel at its edge. Use the TA_GV arrays, tinted toward the
  M_GC_Terrain road colour sampled along the line (report the delta).

**Bogs:** as B2 item 4, MudRoad-adjacent: Standard or Deep near water, Firm or Stony elsewhere, PreChurnScale 1, at most
6. Report each with world coordinates and the nearest review camera.

**Don't touch:**
- GPT's Benmore_VehicleSurfaceEffects actor and the GTDustLab/GTMudFlickLab code, except to read whether they need to
  know about deform zones (report it);
- river, creek and lake water.

**Owner settings:** skip tests; one capture run per stage; the commit says "tests not run (owner)".

**Pictures** (B2b):
- `B2_Road_Gravel.png`: chase, on a gravel zone with ruts forming;
- `B2_Road_Mud.png`: on foot, along a MudRoad stretch;
- `B2_Bog_<n>.png`: each bog before driving;
- `B2_Edge.png`: a zone edge against GPT's gravel and the landscape, close;
- `B2_Top.png`: one stretch from 30 m up.

## B2c: from my look at B2 (main session, 2026-10-12)

**What reads right:** the mud road stretch's interior (B2_Road_Mud): braided ruts, reflective pools, sticks.

**What fails:**
1. **Gravel zones don't belong to GPT's road** (B2_Edge):
   - a hard diagonal seam where the tile starts;
   - a pale sandy pebble mosaic against GPT's grey-brown gravel;
   - near-black loose stones scattered on it (DG1b's stones drawing dark on Benmore).
   Tinting the TA_GV arrays can't close that gap.
2. **Mud zones are rectangles of the strips' red-brown mud** dropped onto a pale road:
   - straight sides, a stair-stepped (12.5 cm) end in B2_Top;
   - a palette far redder and darker than Benmore's soil.
3. **Bogs read as flat dark bands** (B2_Bog_3), like a strip of tarmac, with hard edges.
4. **Pop-in:** mud stretches show as plain gravel road beyond 40-60 m until their tile switches on.
5. **Our spray** throws gravel grit on mud zones (GravelSpraySurface reads the landscape's physical material under the
   patch).

**Fixes:**
1. **Gravel zones wear GPT's road material.** The gravel patch material samples the same gravel layers, textures,
   tiling, world UVs, tints and POM that M_GC_Terrain uses for the road (factor them into a material function both
   call; the builder keeps it). Our deformation goes on top:
   - field displacement and normals;
   - the DG1 track blend toward a packed variant made from the same layers (×0.92 value, POM ×0.5);
   - the windrow heaps.
   - **No DG1b loose stones on Benmore zones:** GPT's verge stones exist already. Report why the stones drew near-black
     on Benmore; fix it if it's the material.
   - Gate: B2_Edge shows no visible seam. The mean colour difference between 1 m strips either side of the tile edge,
     on untouched gravel, is ≤ 2 % per channel.
2. **Mud zones in Benmore's palette with soft, irregular edges.**
   - **Tint:** each mud zone's mud is the surrounding landscape soil colour (sampled around the zone at setup), made
     wetter (value ×0.55-0.7, saturation ×1.15), not the strips' red. Keep the bake's detail.
   - **Outline:**
     - the zone outline is noise-warped (±1-2.5 m at 6-15 m wavelength) on all sides, ends included;
     - mud thins out over a 1.5-3 m feather: tracks continue as wet dark ruts onto the gravel, then fade;
     - the landscape apron gets a wet-darkened gravel blend with splatter;
     - no straight line and no 12.5 cm stair-step: the coverage mask is softened (bilinear plus a 2-texel blur) where
       it drives the visual blend.
3. **Bogs.**
   - Pre-churn hummocks and puddles must actually show. Find why the bog reads flat; it is likely a profile path
     difference from the strips.
   - Outlines noise-warped as in item 2, with tussocks encroaching on the rim (the grass painted out only inside the
     inner 70 %).
   - The same Benmore-palette tint.
4. **No pop-in.** Bake a static mud-zone mask texture (the outlines, 50 cm per texel) into the Benmore material. Beyond
   the live tiles, mud zones draw as wet mud-coloured landscape, a flat colour from the item 2 tint plus the bake's
   detail, crossfading into the live patch over 40-60 m.
5. **Spray on mud zones.** A one-line change in GTSprayArt.cpp: inside an active mud patch, GravelSpraySurface returns
   null, so no gravel grit. Stage that hunk only; GPT's hunks in the file stay unstaged.
6. **Pictures:** retake B2_Edge, B2_Road_Mud, B2_Top, B2_Bog_1 and B2_Bog_3 with the same cameras, plus
   `B2_MudFar.png` (a mud stretch from 80-150 m, to check the pop-in). Commit "Benmore B2c: gravel zones in GPT's road
   material, soft-edged mud in Benmore's palette, no pop-in (tests not run (owner))".
