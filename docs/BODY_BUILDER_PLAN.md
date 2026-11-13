# Body builder plan

Written 2026-10-02. The owner: "build a tool which builds a model using the Tripo one as a guide for
form and shape, as well as placement of details", then "make a full plan, and do it". This file is
the full plan for that tool. `docs/CAR_BODY_PIPELINE_PLAN.md` is the overview; this replaces its
stages BT1 to BT4 (the proof is now the master surface, because a panel is only a region of it).

## 0. The design in one page

The cage (v01, v02) failed because the mesh **was** the surface: 600 points copied from a noisy
guide, on a layout that could not follow corners or arches. The builder separates three things.

1. **Master surfaces** are smooth functions with few numbers, fitted to the blueprint as a whole:
   - a **wall** that runs right round the lower body (front fascia, sides, tail) as one function;
   - **top** surfaces (bonnet with fender tops, rear deck, later the roof);
   - **rounds** between wall and top, built as true arcs with a measured radius.
   A function with knots every 20 cm cannot ripple or fold.
2. **The mesh is only a sampling** of those functions. Where rows and columns go cannot bend the
   surface, so layout mistakes cost triangles, not shape.
3. **Panels are regions** of the masters, bounded by lines measured from the approved image, with a
   gap, an edge round and a return. Details are placed from the blueprint and filled by GPT's parts.

The lower body ("tub") and the cabin ("greenhouse") are two such rounded shells; the greenhouse
sits on the tub along the belt, the cowl and the backlight base.

## 1. Stages

| Stage | Output | Gate |
|---|---|---|
| BT0 | Dropped 2026-10-02 (owner: no separate reference shell). The owner's look at each gate is the bar; the style numbers in section 2 are dials set at owner gate 2 | None |
| **BT1** | Tub master: wall, bonnet and deck tops, shoulder rounds, sampled as one clean mesh | Fable look at clay, gloss, stripes and numbers |
| BT2 | Greenhouse master on the tub: glass walls, pillars, roof, rail rounds. Full clay master | **Owner gate 1** |
| BT3 | Panel map from the approved image; panels cut from the masters with gaps, rounds, returns, arch lips | **Owner gate 2** |
| BT4 | Details located on the blueprint (lamps, grille, handles, scoops, wing, pod, flaps, mirrors); GPT workshop parts fitted there | Owner look at the dressed car |
| BT5 | Materials, UVs, GT Paint bakes, export, Unreal vehicle setup | Owner drives it |
| BT6 | Pathfinder through BT1 to BT5 with no new design work | Pipeline counts as working |

Fable writes each stage block in this file before the stage runs; Opus executes; no stage is called
passing on numbers alone. Stop rules: BT1 or BT2 fails Fable's look twice, or owner gate 1 fails
twice: switch to the template morph in the pipeline plan.

## 2. Style numbers (defaults until BT0 measures the owner's shell)

`PANEL_GAP = 0.006`, `EDGE_ROUND = 0.004`, `RETURN_DEPTH = 0.015`, `GLASS_INSET = 0.006`,
`BELT_ROUND_R = 0.03`, `LEDGE_W = 0.05`, `ARCH_LIP_W = 0.04`. Metres.

## 3. Inputs, frames, rules

- Frames and the reference registration: `docs/SCAFFOLD_CAGE_PLAN.md` section 1 (car frame in
  metres, front = -Y, mid-wheelbase origin on the ground, reference px to car).
- From `Art/Export/VehicleTools/impreza-scaffold-cage-v02/`: `maps.npz` (clean SIDE, TOP, FRONT,
  REAR on 1 cm grids; accessories removed and inpainted; from the corrected, centred,
  outline-corrected blueprint), `reference-lines.json` (arch legs, `z_arch`, `z_low`, belt line),
  `scaffold-corrected.blend`.
- New scripts in `Art/VehicleTools/body_builder/`; reuse helpers from `scaffold_cage/` by import, do
  not edit them. Output to `Art/Export/VehicleTools/impreza-builder-bt1-v01/` (`debug/` inside).
- Headless Blender only, no MCP, no commits, look at every picture written. Latitude: a
  data-handling correction that keeps a step's intent may be applied and listed under deviations
  with its size; stop only if a step cannot run or a change would alter the design. The review step
  is never a stop: always write the numbers and pictures.

## 4. BT1: the tub master

### 4a. Envelope

A point `p = (x, y, z)` is **inside** the clean body when all of these hold, using `|x|` and bilinear
lookups: `|x| < SIDE[y, z]`, `z < TOP[|x|, y]`, `y > FRONT[|x|, z]`, `y < REAR[|x|, z]`. A NaN lookup
means outside. Exception: FRONT and REAR cells with x in [0.78, 1.20] and z in [1.00, 1.26] (mirror)
are "unknown" and impose no constraint.

### 4b. Station frame

Stations run from the front centre round the side to the rear centre. `Y_FAN_FRONT = -1.60`,
`Y_FAN_REAR = 1.72`, `RHO0 = 0.90`.

- Side, `Y_FAN_FRONT <= s <= Y_FAN_REAR`: origin `O = (0, s)`, outward direction `n = (1, 0)`.
- Front fan, angle `a` in [0, 90 degrees]: `s = Y_FAN_FRONT - RHO0*a` (radians), `O = (0, Y_FAN_FRONT)`,
  `n = (cos a, -sin a)`.
- Rear fan: `s = Y_FAN_REAR + RHO0*a`, `O = (0, Y_FAN_REAR)`, `n = (cos a, sin a)`.

`rho(s, z)` = distance from `O` along `n` to the envelope at height z: march inward from 2.5 m in
5 mm steps until inside, then bisect to 0.5 mm. No crossing = NaN.

### 4c. Wall field `Dw(s, z)`

- Data: `rho` on a grid, s step 0.02 over the whole range, z step 0.02 from 0.10 to 1.30.
- `y_h(s)` = the Y of the hit point at z = 0.50. `z_L(s)` = `z_arch` between the legs of an arch,
  else `z_low`, looked up at the reference column of `y_h`, clamped to columns 133..1760.
- Weights: 1 where `rho` is finite, `|d rho/dz| <= 1.2` (central difference over +-2 cm) and
  `z >= z_L - 0.02`; 0.3 for cells inside an arch opening (inpainted, not measured); 0 elsewhere.
  Cabin zone, `y_h` in [`Y_CAB0`, `Y_CAB1`] = [-0.82, 1.63]: weight 0 above `z_B(y_h) - 0.03`, where
  `z_B` is the belt line of `reference-lines.json` extended as a straight line.
- Fit: tensor-product cubic B-spline, knots every 0.20 in s and 0.15 in z, by weighted least squares
  with a second-difference penalty on the coefficients in both directions (P-spline). Penalty rows
  also force `dDw/ds = 0` at both ends of s (left-right symmetry at the centre plane).
- Penalty strength: the largest value for which the weighted RMS residual stays at or below
  `WALL_RMS_CM = 0.5`. Cells with weight 0 are filled by the penalty: that smooth extension is
  wanted, the rounds are built on it.

### 4d. Top fields

- Cowl curve `y_cowl(x)`: for x = 0, 0.02, ... 0.80, scanning rearward from y = -1.30 on clean TOP
  (smoothed 3 cm), the first y where `dZ/dy > 0.55` for 5 cm. Fit `y = a + b x^2` with one rejection
  pass. Backlight base `y_bl(x)`: scanning forward from y = 2.00, the first y where the surface
  rises forward with slope over 0.40 for 5 cm; same fit.
- `A_front(x, y)`: fit to clean TOP cells with slope magnitude under 1.0 and `y < y_cowl(x) - 0.03`,
  domain x in [0, 1.1], y in [-2.25, -0.55]. `A_rear(x, y)`: the same for `y > y_bl(x) + 0.03`,
  y in [1.45, 2.35]. Same P-spline method, knots every 0.20, `TOP_RMS_CM = 0.4`, penalty rows force
  `dA/dx = 0` at x = 0.
- Tub top `U(x, y)`: `A_front` for `y <= Y_CAB0 - 0.10`; the belt ledge `z_B(y)` for
  `Y_CAB0 <= y <= Y_CAB1`; `A_rear` for `y >= Y_CAB1 + 0.10`; smoothstep blends between.

### 4e. Shoulder round, per station, in the station plane (rho, z)

- Wall curve `rho = Dw(s, z)`. Top curve `z = U` along the ray. Both are defined everywhere by
  their fits.
- Round of radius R: offset the wall curve inward by R and the top curve downward by R (along their
  own normals in the plane), intersect the two offset polylines to get the centre; the tangent
  points are the centre pushed back out along each normal. If there is no intersection, halve R
  until there is; count these.
- Radius: outside the cabin zone, per station, the R in [0.02, 0.30] that minimises the RMS distance
  between the built profile and the envelope profile in that plane (envelope sampled by rays from a
  point 0.4 m inside the corner, 15 to 75 degrees). Then median of 5 stations and a P-spline along s
  with knots every 0.50. Inside the cabin zone `R = BELT_ROUND_R`; blend over 0.15 m at each end.
- Station profile = wall from `z_L` to its tangent point, the arc, then the top inward from its
  tangent point to the end point: the centre line or fan centre; or the cowl curve less 2 cm (front)
  or the backlight base plus 2 cm (rear) if the ray meets it first; or `LEDGE_W` in the cabin zone.

### 4f. The mesh

One grid: stations every 0.03 in s; per station 30 wall rows (even in z between `z_L` and the wall
tangent point), 6 arc rows, 14 top rows (`rho_k = rho_t - (rho_t - rho_end) * (k/14)^1.3`). Merge
coincident points (the front fan centre becomes a pole; fine for this stage), drop zero-area faces,
mirror in X, shade smooth. Wheel proxies as in the cage plan. Save `Impreza_Tub_Master.blend` with
the mesh, the proxies and the decimated blueprint in a hidden collection.

### 4g. Checks and pictures

Numbers to `report.json`:

1. Each fit: penalty used, weighted RMS and 95th-percentile residual, number of coefficients.
2. Rounds: stations solved at the first R, stations that needed halving, min / median / max R by
   zone (nose, front side, cabin, rear side, tail).
3. Distance from every mesh vertex to the corrected blueprint, excluding the exclusion boxes, arch
   openings and the front fascia behind the lamp-pod box: median, p95, max and where.
4. Fold detector: largest dihedral angle between adjacent faces and the count over 10 degrees,
   excluding the open lower boundary and the pole fan.
5. Bonnet and deck centre-line profile against the top of the reference silhouette, over columns
   outside the accessory boxes: mean and max, cm.
6. Width at the doors, length, shoulder height at Y = -1.27, 0, 1.27.

Targets: (3) median <= 1.0 cm, p95 <= 3.5 cm (flares, lamp bulges and bumper detail are smoothed
away on purpose); (4) max <= 12 degrees; (5) mean <= 1.0 cm, max <= 2.5 cm.

Pictures (Workbench; clay = studio light with cavity, single grey):

- `tub-views.png`, 2 x 4: blueprint row (front, rear, front three-quarter, rear three-quarter), tub
  row from the same cameras.
- `tub-gloss.png`: car-paint matcap and horizontal-stripe matcap, front and rear three-quarter.
- `tub-side.png`: tub in clay with wheel proxies in the reference frame; and the tub outline over
  the approved side image.
- `debug/tub-fields.png`: the wall field as an image over (s, z) with its weights, R along s, the
  cowl and backlight curves on TOP.

Report: the numbers against the targets, deviations, and a plain list of what looks wrong in the
pictures and where. No verdict.

## 5. Later stages (blocks written before each runs)

- **BT2 greenhouse.** Same method one level up: a wall field round the cabin from the belt and cowl
  up (fan centres about (0, 0.0) and (0, 0.9), inside every slice up to the roof), a roof top field,
  header and rail rounds with measured radius, base found as the intersection with `U`. Glass and
  pillars are regions of that one wall.
- **BT3 panels.** Side-view lines from the approved image map straight into the wall's (s, z)
  coordinates; top-view lines into (x, y). Each panel is a block-structured grid in those
  coordinates, so rows follow arch edges and shut lines by construction, then gap, edge round,
  return and arch lip from the style numbers.
- **BT4 to BT6** as in the stage table.

## 6. BT1 v01 result and the v02 block (2026-10-02)

Fable's look at `impreza-builder-bt1-v01` (`tub-views.png`, `tub-gloss.png`): the method holds.
The sides, doors and arches are clean, with none of the cage's pleats or folds. Not passing yet:
the nose and tail are lumpy (the fit still follows intake, plate and lamp detail), there is a sharp
crease behind the rear arch (the round's radius drops from 0.25 to 0.03 within 15 cm), the rounds
show banding (6 rows per arc), and the bonnet has a broad shallow dip. Distance to the blueprint
median 0.92 cm, p95 3.31 cm.

v02 changes, output to `impreza-builder-bt1-v02/`. Everything else in section 4 stands, including
the agent's accepted deviations (penalty floor rule as the base value, round validity checks).

1. **Robust fits (wall and both tops).** After the first fit, four reweighting passes: each data
   weight is multiplied by `(1 - (r/c)^2)^2` for `|r| < c`, else 0, with residual r and
   `ROBUST_C_CM = 2.0`. Detail more than 2 cm off the smooth surface (intakes, plate recess, lamp
   bulges, vents) stops steering the fit. Inpainted cells in the top fits get weight 0, not 0.3.
2. **Three smoothness variants.** Penalty = the v01 value times 1, 4 and 16, for the wall and the
   tops together: variants `P1`, `P4`, `P16`. Build the full tub for each. Fable picks by look.
3. **Rounds.** 16 arc rows (was 6). R bounds [0.02, 0.40]. The blend between the measured R and
   `BELT_ROUND_R` runs over 0.60 m of s (was 0.15), centred on each end of the cabin zone.
4. **Sampling.** Wall rows: 4 rows evenly from `z_L` up to `z_env`, then 27 rows evenly from
   `z_env` to the wall tangent point, where `z_env` = running maximum of `z_L` over +-0.10 m of s,
   Gaussian 0.05 m, then `max(z_env, z_L)`. Outside the arch spans `z_L(s)` is smoothed with a
   Gaussian of 0.10 m (legs stay sharp).
5. **Pictures.** `tub-variants.png`: car-paint matcap, front and rear three-quarter, one row per
   variant, labelled. Plus the four section-4g pictures for each variant in its own subfolder, and
   the 4g numbers per variant.

## 7. BT1 v02 result and the BT2 block (2026-10-02)

Fable's look at `impreza-builder-bt1-v02/tub-variants.png`: **P4 passes.** Nose, tail, sides and
rounds are clean in car paint; distance to the blueprint median 1.09 cm, p95 3.52 cm. P1 keeps a
146 degree fold on the tail deck corner; P16 over-smooths (lower nose and tail flare out, tail end
15.9 cm low). Known P4 faults carried into BT2: a 20 degree notch at the cowl hand-over, a
centre-line seam on the tail face, a faint crease behind the rear arch.

`SMOOTH = 4` (penalty multiplier) is now the default for every fit.

### BT2: greenhouse master on the P4 tub. Output `impreza-builder-bt2-v01/`

**7a. Fix carried from BT1.** Symmetry at the centre plane is made exact, not penalised: at both
ends of s the first two B-spline coefficients of every row are tied equal (and the same at x = 0
for the top fields). Refit the P4 tub with this; the tail seam must be gone.

**7b. Greenhouse station frame.** `Y_GF = 0.05`, `Y_GR = 0.85`, `RHO0_G = 0.75`. Side stations
`s = y` between them with `n = (1, 0)`; front fan `s = Y_GF - RHO0_G*a`, `O = (0, Y_GF)`,
`n = (cos a, -sin a)`; rear fan `s = Y_GR + RHO0_G*a`, `O = (0, Y_GR)`, `n = (cos a, sin a)`.
`rho_g(s, z)` by the same envelope march (from 2.0 m), z from 0.95 to 1.70.

**7c. Greenhouse wall field `Dg(s, z)`.** Data grid s step 0.02, z step 0.02. Weight 1 where
`rho_g` is finite, `|d rho/dz| <= 2.5`, and the point is at least 3 cm above the tub top `U` at its
(x, y); else 0. Fit as the tub wall: knots 0.10 in s and 0.12 in z, robust passes with
`ROBUST_C_CM = 1.5`, penalty = floor rule times `SMOOTH`, exact symmetry at both ends.

**7d. Roof field `A_roof(x, y)`.** Clean TOP cells with z > 1.35 and slope magnitude under 0.45;
inpainted cells weight 0; domain x in [0, 0.85], y in [-0.65, 1.55]; knots 0.20; robust; penalty
rule times `SMOOTH`; exact symmetry at x = 0.

**7e. Header and rail round.** The BT1 round construction between `Dg` and `A_roof` in each
greenhouse station plane; R measured per station in [0.03, 0.30], median of 5, P-spline along s
with knots every 0.50. 16 arc rows.

**7f. Base.** Per greenhouse station, `z_base` = the lowest z at or above 0.95 where the wall point
is on the tub top: `z - U(x, y) = 0` at `(x, y) = O + Dg(s, z) n`. The base points form the
greenhouse footprint curve in plan.

**7g. Join.** Tub top rows now end on the footprint curve: each tub station's top curve runs inward
from its tangent point to where its ray crosses the footprint (or to the centre if it never does).
This replaces the cowl curve less 2 cm, the backlight curve plus 2 cm and the fixed ledge width.

**7h. Mesh.** Greenhouse grid: stations every 0.03 in s; 24 wall rows from `z_base` to the wall
tangent point, 16 arc rows, 12 roof rows to the centre line or fan centre. Merge, mirror, shade
smooth. Tub mesh as BT1 v02 P4 with 7a and 7g. Save `Impreza_Body_Master.blend` (tub, greenhouse,
wheel proxies, hidden decimated blueprint).

**7i. Glass tint, a visual aid only (not the panel map).** A second material, dark grey, on
greenhouse wall faces that are glass by these rough rules: side-facing faces whose (y, z) falls on
the reference image's dark mask (rows 150..360); front- and rear-facing faces more than 6 cm above
the base, more than 4 cm below the wall tangent point and more than 9 cm inboard of the wall's
widest point at that height.

**7j. Checks and pictures.** Numbers as 4g for the whole body, with the fold detector also skipping
the tub-to-greenhouse junction and the roof poles, plus the upper outline of the whole master
against the reference silhouette (columns outside the accessory boxes): mean and max. Targets:
distance median <= 1.2 cm, p95 <= 4.0 cm; fold max <= 12 degrees; outline mean <= 1.2 cm,
max <= 3.5 cm.

Pictures: `master-views.png` (2 x 4, blueprint row over master row, clay);
`master-gloss.png` (car paint and stripes, front and rear three-quarter);
`master-side.png` (master in clay with wheel proxies in the reference frame; outline over the
approved side image); `master-zones.png` (grey body, dark glass tint, wheel proxies: front
three-quarter, rear three-quarter, side, front); `debug/gh-fields.png`.

## 8. BT2 v01 result and the v02 block (2026-10-02)

Fable's look at `impreza-builder-bt2-v01` (`master-zones.png`, `master-gloss.png`): the surface
quality is there (clean in car paint, no folds on the greenhouse, outline mean 0.74 cm, distance
median 0.79 cm, p95 3.21 cm). The **form is too soft**: it reads as a generic rounded sedan. The
rounds are two to three times the blueprint's (side rail 0.19 m, headers on the 0.30 bound, front
shoulder 0.24), and a crease runs from the A-pillar base along the fender top.

Cause: the wall fits include the lower part of each round as valid wall data, and the smoothing
spreads that bend down the wall, so wall and top no longer meet at a real corner and the best-fit
arc comes out large.

v02 changes, output `impreza-builder-bt2-v02/`. Everything else in sections 4, 6 and 7 stands.

1. **Wall data stops where the round starts (tub and greenhouse).** Per station, `slope_mid` = the
   median of `d rho/dz` over the middle third of the wall's height range (tub: `z_L` to the highest
   finite cell below any cabin cut; greenhouse: base estimate to the highest finite cell). A cell is
   valid wall data only while `|d rho/dz - slope_mid| <= 0.35`, scanning up from the middle; the
   first cell that breaks it ends the wall for that station. This replaces the absolute limits 1.2
   and 2.5. Refit both walls (robust passes and `SMOOTH = 4` as before), then re-measure every R.
2. **Longer hand-overs.** The blends of the tub top `U` between `A_front`, the belt ledge and
   `A_rear` run over 0.30 m (was 0.10).
3. **Two round variants.** `R100` uses the measured radii. `R60` multiplies every measured radius
   by `ROUND_SCALE = 0.6` (floor 0.03), a style dial for a crisper body. Build the full master for
   both.
4. **Glass tint by vertex colour**, not by face: the same rough rules evaluated per vertex and
   rendered with interpolated vertex colours, so the edges are smooth.
5. **Pictures.** For each variant the five 7j pictures, plus `master-compare.png`: clay with glass
   tint and wheel proxies, front three-quarter and rear three-quarter, rows = blueprint, `R100`,
   `R60`.
6. **Numbers.** The 7j numbers per variant, round R by zone for tub and greenhouse (measured, before
   scaling), and the corner miss: the distance from the blueprint to the master along the 45 degree
   ray of each station plane, median and p95 by zone.

## 9. BT2 v02 result (2026-10-02): at owner gate 1

Both variants meet every 7j target (distance median 0.97 / 0.93 cm, p95 3.86 / 3.82 cm, fold max
10.2 / 10.0 degrees, outline mean 0.91 / 0.94 cm, max 3.5 cm).

- The refit did not shrink the radii, and the station-profile picture shows why: the cleaned
  blueprint envelope is itself that round (the roof crown rolls into the rail; an arc of about
  0.20 m fits the side rail within 1.3 cm). `R100` is therefore the faithful version; its corners
  sit on the envelope (side rail miss 0.5 cm).
- `R60` reads crisper and more car-like but sits 1 to 4 cm outside the envelope at every corner.
  It is a style choice, not a measurement.
- Fable's look at `master-compare.png`: a clean, smooth body of the right proportions in both
  variants; soft and generic as a bare master (no panel lines, flares, lamps, bumpers, wing yet).
  Remaining faults: stepped glass-tint edges (visual aid only), a crease along the belt junction in
  gloss, a small lip where the rear deck meets the backlight, the nose wraps rounder in plan than
  the blueprint's squarer fascia.
- Next: owner gate 1 (go on to BT3 panels with R100 or R60, or stop).

Owner gate 1 result (2026-10-02): rejected, "the shapes are off". The owner asked instead for a
library of car-modelling rules (what shape a windscreen has, how panels are laid out). The
fitted-master route stops here; its surface machinery (fields, rounds, sampling, checks) is
reusable under rule-driven curves.
