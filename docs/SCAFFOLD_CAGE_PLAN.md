# Scaffold cage plan (Impreza, first case)

Goal: a clean quad subdivision cage for the Impreza **primary body surface**, fitted by measurement
to (a) the approved side reference and (b) the Tripo scaffold the owner accepted by look on
2026-10-02. No panels, glass, lamps or accessories in this stage: one continuous shell with wheel
arch openings, shown in clay. The owner's look at the result is the gate.

Why this route: GPT's v08 was built from one traced side view and guessed cross-sections, and its
checks measure assembly, not likeness. Here the cross-sections are sampled from a 3D scaffold and the
side view is forced onto the approved image, so no surface position is chosen by eye.

Design decisions in this file are fixed. If a measurement contradicts one (a stop condition below),
report the number and stop; do not redesign.

## 0. Rules for the run

- New scripts only, in `Art/VehicleTools/scaffold_cage/`. Do not edit any existing file in
  `Art/VehicleTools/`, `Art/References/`, `Art/Export/VehicleTools/` or `~/.codex/`.
- Outputs go to a fresh folder `Art/Export/VehicleTools/impreza-scaffold-cage-v01/` (next free
  `vNN` if a rerun produces a new reviewable revision). Debug images in its `debug/` subfolder.
- Blender runs headless: `"C:\Program Files\Blender Foundation\Blender 5.1\blender.exe" -b
  --python-exit-code 1 --python SCRIPT -- ARGS`. Do not use the Blender MCP session (the owner's
  Blender is open). System Python has PIL 12 and numpy; Blender's Python has numpy only.
- No git commits. No changes to memory files.
- Every named constant below is a module-level constant with the same name.
- **Latitude (revision 3).** A data-handling correction that keeps the stated intent of a step
  (centring an offset, closing a one-pixel gap in a mask, seeding a fill, fixing a classifier) may
  be applied without stopping. List each one under "deviations" in the report with its measured
  size. Stop only for a section 6 condition, a failed stage acceptance, or a change that would move
  the surface by more than 1 cm or alter the cage layout.
- Look at each debug image you write before moving on (Read the PNG). A stage is not done on
  numbers alone.

## 1. Inputs and frames

| Thing | Value |
|---|---|
| Approved side reference `REF_SIDE` | `Art/References/Vehicles/Impreza2003/orthographic-reset-v01/02-side-profile.png`, 1881x836, nose to image-left |
| Reference registration | 400 px per artistic metre, mid-wheelbase at px x = 893, ground at px y = 757 |
| Wheel centres (reference) | px (386, 614) and (1400, 614); radius 143 px |
| Tripo scaffold | `Art/References/Vehicles/Impreza2003/tripo-scaffold-v01/impreza-tripo.glb`, one mesh, 1.13 M verts, single outer shell with a closed flat underside, no interior |
| Scaffold silhouette already rendered | `.../tripo-scaffold-v01/tripo-side-registered.png`, 2081x836 RGBA, alpha = silhouette, 100 px pad left and right, otherwise in the reference pixel frame |

**Car frame (metres):** X lateral (+X = car's left), Y along the car (**front = -Y**), Z up, origin at
mid-wheelbase on the ground. Reference px to car: `Y = (px_x - 893)/400`, `Z = (757 - px_y)/400`.
Wheel centres: Y = -1.2675 and +1.2675, Z = 0.3575.

**GLB native to car frame (before correction):** after glTF import the mesh has front = -Y, up = +Z,
ground at z = 0. `S = 4.5594`; `X = x*S`, `Y = (y + 0.0025)*S`, `Z = z*S`. (From a tyre circle fit:
native wheel centres y = -0.2805 / +0.2755.)

Measured so far (uniform registration on wheel centres): silhouette overlap with the reference 0.876;
the scaffold is about 7% too tall, its nose about 48 px too long, tail aligned. Body half-width about
1.01 to 1.03 m before correction. The wing blade floats above the boot with a real gap; the boot
surface exists under it. The lamp pod and scoops are fused bumps.

## 2. Stage SC1: side fit and reference lines (system Python, `sc1_side_fit.py`)

### 2a. Side warp

Find a warp that maps the scaffold silhouette `T` (crop columns 100..1980 of the alpha) onto the
reference silhouette `R` (pixels whose max channel distance from the background colour at (5,5)
exceeds 0.10).

- Control columns (reference px): `CTRL = [51, 135, 221, 386, 551, 720, 893, 1066, 1235, 1400, 1565, 1680, 1791]`.
- Unknowns per control: `d_k` (px, source column shift) and `s_k` (height scale). Linear
  interpolation between controls, constant beyond the ends.
- Warped mask: `Tw(x, y) = T(x + d(x), 757 - (757 - y)/s(x))`, nearest neighbour.
- Evaluation region `E`: rows y < 735, minus these boxes (reference px, `x0,x1,y0,y1`):
  lamp pod `0,150,385,505`; front tow hook `0,95,540,625`; bonnet scoop `295,480,280,345`;
  roof scoop `900,1075,60,135`; wing `1575,1881,150,315`; exhaust `1690,1881,575,640`;
  front mudflap `520,585,530,735`; rear mudflap `1535,1600,530,735`; wheel discs radius 175 px at
  both wheel centres. Draw the boxes on the reference, look, and widen any that does not fully cover
  its accessory (keep them as tight as that allows). Record the final boxes.
- Revision 2 (2026-10-02, after the first SC1 run): `R` has its holes filled (flood fill from the
  image border; the cream stripe and lamp lenses are body). Final boxes from run 1: lamp pod
  `0,150,385,540`; front tow hook `0,95,540,640`; bonnet scoop `286,480,280,345`; roof scoop
  `900,1092,60,135`; the rest as listed.
- **Nose term (revision 2).** The silhouette cannot see the bumper face (it is behind the pod and
  hook boxes), and run 1 left it about 40 px too far forward. Add a second term: blue masks
  (section 2b definition, with the brightness floor) of the reference and of the warped scaffold
  render (RGB of `tripo-side-registered.png`, same warp), compared over the nose window
  `N` = columns 0..230, rows 385..735. The pod and hook are not blue, so they drop out by colour.
- Objective: `IoU(Tw, R)` over `E` plus `0.5 * IoU(blue_Tw, blue_R)` over `N` minus
  `1e-5 * sum((d_k - d_{k+1})^2)` minus `2.0 * sum((s_k - s_{k+1})^2)`.
- Coordinate descent from `d = 0`, `s = 0.93`. Step sizes for d: 8, 4, 2, 1 px; for s: 0.02, 0.01,
  0.005, 0.0025. At each step size sweep all controls (try +step and -step, keep improvements) until
  a full sweep changes nothing.
- Smooth: sample `d(x)` and `s(x)` per pixel, Gaussian sigma 25 px. `h(x) = x + d(x)` must be strictly
  increasing. `g` = numerical inverse of `h` (scaffold column to reference column).
- `WIDTH_SCALE` = mean of `s(x)` over columns 386..1400.

Write `side-fit.json` (controls, d, s, per-pixel tables, IoU before/after over `E`, `WIDTH_SCALE`)
and `debug/side-fit-overlay.png` (reference with the warped scaffold outline in magenta, boxes drawn).

Acceptance: IoU over `E` >= 0.955; all `s_k` in [0.86, 1.00]; all `|d_k|` <= 80; `h` monotone;
bumper-face offset <= 6 px (median over rows 545..605 of the forward-most blue column, warped
scaffold against reference).

### 2b. Reference lines (same script)

All from `REF_SIDE`, per pixel column, written to `reference-lines.json` and drawn on
`debug/reference-lines.png`.

- **Blue body mask:** HSV hue in [200, 240] degrees, saturation > 0.45 and value > 0.2. **Red mask:**
  hue < 15 or > 345, saturation > 0.6 and value > 0.2. **Dark mask:** value < 0.5 and
  saturation < 0.45. (Revision 2: the value floor keeps near-black tyre pixels out of blue and red.)
  Revision 3: before reading the arch profile and the lower boundary, close vertical gaps of up to
  4 px in the blue mask (a one-pixel bumper seam at row 464 otherwise notches the rear arch).
- **Arch legs:** for each wheel, scan along rows 609..619 from the wheel centre forward and rearward;
  the leg column is the first column that is blue or red (median over the rows). Four leg columns.
- **Arch profile** `z_arch(px)`: for columns strictly between the legs of one arch, the bottom of the
  lowest blue run that starts above row 464 (revision 2: this is the reading the first run used);
  median filter 9 px.
- **Lower boundary** `z_low(px)` for the three segments outside the arches (px 133 to front leg,
  between arches, rear leg to px 1760): the lowest blue pixel in the column. Columns that contain
  more than 10 red pixels (dilated 6 px) are filled by linear interpolation from their neighbours.
  Then median filter 15 px inside each segment.
- **Belt** `z_belt(px)` (revision 2): the measured glass bottom is the lowest dark pixel of the
  largest dark run per column, rows 150..360. Fit a **straight line** by least squares over columns
  695..1300 only (side glass, clear of the mirror, the A-pillar and the rear-screen strip), one
  rejection pass at 4 px. The line is the belt and is evaluated, extended, over columns 607..1560.
  `DLO_SPAN = [607, 1300]`.

Look at `debug/reference-lines.png`: the lower boundary must follow the bottom of the blue body and
the arch edges, the belt must sit on the bottom edge of the side glass.

## 3. Stage SC2: corrected scaffold and depth maps (Blender, `sc2_maps.py`)

1. Import the GLB, move vertices to the car frame, then apply the warp per vertex:
   `px_s = 893 + 400*Y`; `px_r = g(px_s)`; `Y' = (px_r - 893)/400`; `Z' = Z * s(px_r)`;
   `X' = X * WIDTH_SCALE`. Object transform identity. Save `scaffold-corrected.blend`.
2. Check: silhouette of the corrected mesh by side ray casts on the reference pixel grid at half
   resolution; IoU over `E` must be within 0.01 of SC1's value.
3. Depth maps on a 1 cm grid by `Object.ray_cast` from outside inward (first hit):
   - `SIDE[y, z]` = hit X, rays along -X from X = +3, y in [-2.30, 2.40], z in [0, 1.80]; also the
     mirror side (rays along +X from X = -3, value = -hit X).
   - `TOP[x, y]` = hit Z, rays along -Z from Z = +3, x in [0, 1.20]; also at -x.
   - `FRONT[x, z]` = hit Y, rays along +Y from Y = -4; also at -x.
   - `REAR[x, z]` = hit Y, rays along -Y from Y = +4; also at -x.
   No hit = NaN.
4. **Centre first (revision 3).** The scaffold sits about 8 mm towards +X. From the raw SIDE maps
   take `X0` = median over cells valid on both sides of half the side-to-side difference; shift the
   corrected mesh by `-X0` in X, re-save `scaffold-corrected.blend`, and recompute all raw maps.
   After centring at least 95% of SIDE cells must agree within the 1.5 cm tolerance.
   **Symmetrise:** per cell, if both sides are valid and differ by less than 1.5 cm take the mean;
   if they differ by more, take the less protruding side (smaller X for SIDE, smaller Z for TOP,
   larger Y for FRONT, smaller Y for REAR). This removes one-sided parts (tow hooks, exhaust).
5. **Wing:** for TOP cells with y in [1.62, 2.30], start the rays at a ceiling between the boot and
   the blade instead of Z = +3. Measure the gap on the centre-plane profile of the corrected mesh
   (boot top and blade underside) and put the ceiling midway. Rays that start inside the end-plate
   solids return a far or back-facing hit: mark those cells NaN (hit Z more than 15 cm below the
   median of the valid cells in that row of y).
6. **Exclusions** (set to NaN, then inpaint). Initial boxes in the car frame; draw them on a
   grayscale image of each raw map, look, and adjust so each part is covered with about 3 cm margin
   and as little body as possible. Record final boxes.
   - SIDE (Y, Z): mirror `[-0.74,-0.49] x [1.01,1.21]`; front mudflap `[-0.95,-0.77] x [0,0.56]`;
     rear mudflap `[1.59,1.78] x [0,0.56]`; arch openings: every cell with Y between an arch's legs
     (widened 3 cm each side) and Z below `z_arch(Y) + 0.04`.
   - TOP (X, Y): bonnet scoop `[0,0.36] x [-1.50,-1.02]`; roof scoop `[0,0.26] x [0.02,0.47]`;
     wing end-plate feet `[0.60,0.95] x [1.62,2.30]` (only if step 5 left bumps there); mirror
     `[0.80,1.20] x [-0.74,-0.49]`.
   - FRONT (X, Z): lamp pod `[0,0.72] x [0.60,0.93]`.
7. **Inpaint** NaN cells that lie inside an exclusion (or were rejected in step 5) by Laplace
   relaxation from their valid neighbours (4-neighbour Jacobi, NaN cells outside the body are simply
   not neighbours; iterate until the largest change is under 0.1 mm). Then a NaN-aware Gaussian,
   `MAP_SIGMA_CM = 2.0`.
8. Save `maps.npz` (raw, clean, grid origins, final boxes) and `debug/map-side.png`, `map-top.png`,
   `map-front.png`, `map-rear.png` (clean map as grayscale, boxes outlined, raw beside it).

The surface between the headlamps behind the lamp pod is inpainted, not measured. That is accepted:
the pod is remounted there later. Say so in the report.

## 4. Stage SC3: the cage (Blender, `sc3_cage.py`, reads `maps.npz` and the two json files only)

Half cage for X >= 0, Mirror modifier (X, clipping, merge 1 mm), then Subdivision Surface
(Catmull-Clark, levels 2, `use_limit_surface` on). Object name `GT_Impreza_BodyCage`. Quads only.
Bilinear lookups into the clean maps.

### 4a. Lines along the car (per 1 cm of Y, then sampled at stations)

- `T` (top/side separatrix: fender shoulder, A-pillar, roof rail, C-pillar, rear shoulder): on the
  TOP row for that Y, scan X outward from 0.25; `x_T` = first X where the slope `-dZ/dX`
  (central difference over +-2 cm) is >= 1.0 and stays >= 1.0 for 2 cm. If the map ends first,
  `x_T` = last valid X minus 1 cm. `z_T = TOP[x_T, Y]`. Median filter 7 cm then Gaussian sigma 3 cm
  along Y, on both `x_T` and `z_T`.
- `B` (revision 4): `z_B = min(z_belt line, z_T - 0.05)` at **every** column, with the belt line
  extended as a straight line over the whole car (revision 2 limited it to columns 607..1560, which
  left a 5 cm hump at the A-pillar base). So B is the fender shoulder at the front, the glass bottom through the cabin,
  stays on the extended belt line under the C-pillar, and hands back to the rear shoulder where T
  comes down to it. Gaussian sigma 3 cm.
- `L` (lower boundary): `z_arch` between arch legs, `z_low` elsewhere. Not smoothed across legs.

Write `debug/lines-side.png`: `z_T`, `z_B`, `z_L` and the station positions drawn over `REF_SIDE`;
and `debug/lines-top.png`: `x_T(Y)` over the clean TOP map. Look at both: T must run along the
fender shoulder, climb the A-pillar, follow the roof rail and come down the C-pillar; B must follow
the glass bottom; nothing may jitter.

### 4b. Stations (constant-Y sections)

- Ends: `Y_FRONT = -1.90`, `Y_REAR` = the Y, searched in [1.95, 2.20], where the centre-line profile
  `TOP[0, Y]` first falls at 45 degrees going rearward (fallback 2.10).
- Per arch, 11 stations: leg-outer and leg-inner at each leg (`leg -+ 0.0125`, outer has the segment
  lower boundary, inner has `z_arch`), and seven between the legs at span fractions
  0.08, 0.20, 0.35, 0.50, 0.65, 0.80, 0.92.
- Kink stations: cowl = the Y in [-0.95, -0.60] with the strongest concave bend of `TOP[0, Y]`;
  backlight base = the same in [1.50, 1.80]; each with holding stations at +-0.05.
- Fill every gap so no spacing exceeds `MAX_STATION_GAP = 0.13`; merge stations closer than 2 cm
  except the leg pairs.

### 4c. Twelve vertices per station (index j)

| j | Position |
|---|---|
| 0..4 | `X = f_j * x_T`, `f = [0, 0.30, 0.58, 0.82, 1.0]`, `Z = TOP[X, Y]` (j = 4 is T) |
| 5 | `Z = z_B + 0.5*(z_T - z_B)`, `X = SIDE[Y, Z]` |
| 6 | `Z = z_B`, `X = SIDE[Y, Z]` (B) |
| 7..11 | `Z = z_B - g*(z_B - z_L)`, `g = [0.22, 0.45, 0.68, 0.87, 1.0]`, `X = SIDE[Y, Z]`; for j = 11 look up X at `z_L + 0.015` but keep `Z = z_L` |

Repair (revision 4): NaN lookups are filled by interpolation along the row (same j, neighbouring
stations); report how many. The median outlier replacement of revision 1 is **removed**: at the
nose, the tail and the arch legs it flagged the real taper and would have moved the surface by up to
22.7 cm. Accessories are already handled in the maps.

### 4d. End caps

Front cap from the ring at station `Y_FRONT`: columns c = 0..4 use `f_c`; rows r = 0..7 are ring
vertices j = 4..11 (`x_side(r)`, `z_side(r)`). Centre heights: `z_ctr(0)` = ring j = 0 height,
`z_ctr(7) = z_L(Y_FRONT)`, others by the same fractions as the side rows. Interior vertex (c, r) for
c = 0..3, r = 1..7: `X = f_c * x_side(r)`, `Z = z_ctr(r) + f_c^2 * (z_side(r) - z_ctr(r))`,
`Y = FRONT[X, Z]`, clamped to `Y <= Y_FRONT - 0.01`. Row r = 0 and column c = 4 are the ring itself.
Rear cap the same with REAR and `Y >= Y_REAR + 0.01`.

### 4e. Fit the limit surface to the samples

Targets `t` = the sampled positions. Start with cage = targets. Repeat 8 times: evaluate the object
(depsgraph), read the first N evaluated vertices (they correspond to the cage vertices in order;
verify once by distance), `cage += t - evaluated`, keeping centre-line vertices at X = 0. Report the
max residual each pass.

### 4f. Review extras

- Wheel proxies: cylinders radius 0.3575, width 0.25, at both wheel centres each side; outer face at
  the median raw SIDE value within 0.2 m of the wheel centre. Dark material.
- Decimated copy of the corrected scaffold (ratio 0.05) in a hidden collection
  `REF | Tripo scaffold (corrected)`.
- Save `Impreza_Scaffold_Cage.blend`.

## 5. Stage SC4: checks and pictures (`sc4_review.py`)

Numbers, written to `report.json`:

1. Cage face count, all quads, non-manifold edges other than the open lower boundary = 0.
2. Fit residual after the last pass (max, mm).
3. Distance from every evaluated (subdivided) vertex to the corrected scaffold
   (`closest_point_on_mesh`), excluding vertices inside any exclusion box, inside the arch openings,
   or on the front cap behind the lamp-pod box: median, 95th percentile, max, and where the max is.
4. Side silhouette of the evaluated cage (ray casts on the reference grid) against the reference:
   upper-contour deviation over columns outside the accessory boxes (mean, max, cm); arch-edge
   deviation against `z_arch` (max, cm).
5. Body width at the doors, overall length and height of the cage.
6. Which axis GPT's `Art/VehicleTools/rebuild_impreza_orthographic.py` uses for the car's length and
   which way is forward (read only; one line in the report).

Acceptance: (2) < 2 mm; (3) median <= 0.6 cm and p95 <= 2.0 cm; (4) upper contour mean <= 1.0 cm and
max <= 3.0 cm, arch max <= 1.5 cm.

Pictures (Workbench, studio light, cavity on, single mid-grey, film transparent then composited on
grey 205,207,208):

- `side-comparison.png`, three rows in the reference frame with wheel-centre ticks and ground line:
  approved reference; evaluated cage in clay with wheel proxies; cage outline (magenta) over the
  reference.
- `views.png`, 2 x 4: top row the corrected scaffold in clay (front, rear, front three-quarter, rear
  three-quarter), bottom row the cage from the same cameras.
- `cage-wire.png`: the control cage edges over the shaded surface, front three-quarter and side.
- `gloss.png`: front and rear three-quarter with a glossy matcap or specular studio light, to judge
  surface fairness.

## 6. Stop conditions (report the number, do not work around)

- SC1 acceptance fails after the descent has converged.
- `T` cannot be made continuous along the car by the stated filters.
- More than 5% of cage lookups were NaN and needed filling.
- The limit-surface fit (4e) does not converge: if the max residual is not falling by pass 3, retry
  once with the update damped by 0.7; if it still grows, stop.
- SC4 (revision 4): never a stop. Always write `report.json` and all four pictures, then report
  which acceptance numbers failed and where. Three fix attempts on implementation bugs at most.
- Wing (revision 4): the step-5 rejection test is "first hit is back-facing", as applied in run 3,
  not the 15 cm test.

## 7. Report format

Per stage: what ran, the acceptance numbers against their limits, final exclusion boxes, repairs
counted, anything invented rather than measured, every stop condition met, and the paths of the four
pictures and the debug images. No verdict on whether the car looks right; that is judged from the
pictures by Fable and then the owner.

## 8. v01 result (2026-10-02): outline fits, surface fails the look

Fable's look at `impreza-scaffold-cage-v01` (`side-comparison.png`, `views.png`); the owner had not
ruled when this was written.

- Works: side warp (overlap 0.985, bumper face within 2 px); cage outline on the reference (mean
  1.1 cm over the body); distance to the scaffold median 0.30 cm, p95 1.80 cm; all quads; doors and
  roof read smooth.
- Fails: the nose and tail caps are rippled, each arch leg has a vertical fold, the front fender and
  C-pillar base are creased. It reads as a sheet draped over the car, not as bodywork.
- Causes, all in this plan's design, not in the execution:
  1. The maps are smoothed at 2 cm but the cage has about 12 cm between sections, so grille, intake
     and lamp detail aliases into ripples.
  2. The fit (4e) interpolates every sample exactly, which copies that noise instead of averaging it.
  3. The leg station pairs 2.5 cm apart have very different row heights, which folds the surface.
- If there is a v02: replace 4e with a least-squares fit of the limit surface to dense samples with a
  fairness (cage Laplacian) term; smooth the FRONT and REAR maps at about 5 cm; set the interior row
  heights from a lower line smoothed across the arch legs so only the boundary row jumps.

## 9. v02 (revision 5, owner said "do the second run" 2026-10-02)

Same stages and the same scripts (edit your own files in `Art/VehicleTools/scaffold_cage/`), output
to a fresh folder `Art/Export/VehicleTools/impreza-scaffold-cage-v02/`. SC1 is not rerun: copy
`side-fit.json`, `reference-lines.json` and `sc1-masks.npz` from v01. Everything not listed here
stays as in sections 1 to 7. The aim of v02 is a **fair** surface: smooth highlights, no ripples, no
folds. Where fairness and exact agreement with the scaffold conflict at a scale under about 10 cm,
fairness wins; the scaffold's small detail (grille, intakes, lamps, handles, panel grooves) is not
part of the primary surface.

### 9a. SC2 changes

1. **Outline correction `s2` (new step, after the warp and centring, before the maps).** v01's bonnet
   front sat 3.5 to 4.2 cm below the reference because the warp's height scale is too coarse there.
   Per reference column, `ratio = z_ref_top / z_mesh_top`, where `z_ref_top` is the top of the filled
   reference silhouette and `z_mesh_top` the top of the corrected mesh's side silhouette. Use only
   columns 150..1575 that are outside the SC1 accessory boxes; clip the ratio to [0.95, 1.08];
   interpolate linearly across the excluded spans; hold the end values constant beyond 150 and 1575;
   Gaussian sigma 30 px. Apply `Z' = Z * s2(px(Y))` to the mesh, save the blend, then compute maps.
   Report min, max and the value at columns 200, 250, 700, 1200, 1500.
2. **Map smoothing:** `MAP_SIGMA_CM` is now per map: SIDE 3.0, TOP 3.0, FRONT 5.0, REAR 5.0.

### 9b. SC3 changes

1. **Shoulder rows:** `SHOULDER_DROP = 0.12`. The B rule becomes
   `z_B = min(z_belt line, z_T - SHOULDER_DROP)` (was 0.05). Row j = 5 stays midway between T and B.
2. **Regular T at the ends.** Within `END_BLEND = 0.30` m of `Y_FRONT` and of `Y_REAR`, blend the
   measured `x_T` towards `0.80 * W(Y)` with a smoothstep weight that is 1 at the end station and 0
   at 0.30 m from it. `W(Y)` = the largest clean SIDE value in that column of Y (local half-width).
   Then `z_T = TOP[x_T, Y]` as before. (v01's T curled inward on a local seam at the nose and tail
   and wrecked the end rings.)
3. **Interior rows ride a smooth lower line.** `z_env` = running maximum of `z_L` over +-10 cm of Y,
   then Gaussian sigma 5 cm, then `max(z_env, z_L)`. Rows j = 7..10 use
   `Z = z_B - g*(z_B - z_env)` with `g = [0.22, 0.45, 0.68, 0.87]`. Row j = 11 stays on the true
   `z_L` (X looked up at `z_L + 0.015`). Only the boundary row jumps at the arch legs.
4. **Sharp leg-bottom corners.** Mesh attribute `crease_vert` (FLOAT, POINT) = 1.0 on the j = 11
   vertex of each leg-outer station (four per side). Check that the evaluated position equals the
   control position there.
5. **Target fairing.** After sampling, one pass per row j of `v_i += 0.5 * (mean of the two
   station neighbours, weighted by inverse spacing, - v_i)` on the measured coordinate only (Z for
   j = 0..4, X for j = 5..11), for interior stations. Do not modify the cowl and backlight kink
   stations or their holding stations, the end stations, or j = 11 at the leg stations.
6. **Fit passes:** `FIT_PASSES = 3`, undamped (was 8). The residual limit is dropped; report the
   residual after each pass. A looser fit that stays fair is the intent.

### 9c. SC4 changes

Same numbers and the same four pictures. Limits for v02: distance to the corrected scaffold median
<= 0.8 cm and p95 <= 3.0 cm; upper outline mean <= 1.0 cm and max <= 3.0 cm over columns 150..1700;
arch edge p95 <= 2.0 cm. Also report the largest dihedral angle between adjacent faces of the
evaluated mesh (degrees, and where), as a fold detector. SC4 is still never a stop.

In the report, list what you can see wrong in the four pictures (ripples, folds, creases, flat
spots, where on the car), as you did for v01.

## 10. v02 result (2026-10-02): still fails the look; route closed

Fable's look at `impreza-scaffold-cage-v02` (`views.png`, `gloss.png`); the owner had not ruled when
this was written.

- Numbers: distance to scaffold median 0.48 cm, p95 2.17 cm; upper outline mean 0.78 cm, max 3.75 cm
  (bonnet front corner); arch edge p95 1.25 cm; largest dihedral 177 degrees (a fold-back at the
  front ring corner); 208 edges over 30 degrees.
- Look: less rippled than v01 in clay, but the gloss and stripe views show a pleat at each front
  corner, a crease along the front fender, vertical folds at all four arch legs, a wavy rear quarter
  and a lumpy tail. It still reads as a draped sheet.
- Why a third run of this recipe is not recommended: the remaining faults are in the layout itself.
  Constant-Y sections with a box-corner cap cannot follow the rounded nose and tail corners or the
  arch openings; those need loops that run around the arches and corners, which is a modeller's
  topology, not a parameter change.
- What is worth keeping: the side warp (SC1), the corrected, centred scaffold
  (`scaffold-corrected.blend`, upper outline within about 0.8 cm of the approved side view), the
  measured lines (`cage-lines.json`, `reference-lines.json`) and the comparison checks (SC4), as a
  snap target and a likeness check for retopology done by hand.
