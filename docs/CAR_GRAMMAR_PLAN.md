# Car grammar plan

Written 2026-10-02. Owner: "Can we somehow build like a library for car modelling? Like windscreens
usually have x shape, panels usually follow these rules" and "Let's start with an SUV, like a
classic Land Cruiser." This plan builds that library and uses it to build a Land Cruiser 80 first.

## 0. What the library is

A **car grammar**: the knowledge a designer carries about what each part of a car is and how parts
relate, written as rules a person can read and numbers a program can use.

- **Hard points:** about 35 named numbers that fix a car's architecture (wheelbase, overhangs, belt
  height, cowl point, roof height, rakes, tumblehome, arch radius, ...). Section 2.
- **Rules:** one sentence plus numbers per fact ("a boxy SUV windscreen is a single cylindrical
  sheet with 30 mm of plan bow, raked 32 degrees from vertical"), with a range per body type, a
  source and a confidence. Section 3 holds the first set.
- **Layout rules:** where panels split and openings sit.
- **A construction recipe** that turns hard points and rules into master surfaces, then panels,
  then details. It reuses the surface machinery already built in `Art/VehicleTools/body_builder/`
  (smooth fields, true rounds, dense sampling, outline and fold checks), but every curve now comes
  from a rule, not from a fit to a generated mesh.
- **Checks:** every rule is re-measured on the output and reported as met or not, next to the
  outline check against the approved reference.

Tripo and other generated meshes are no longer shape authority. The approved reference images set
the proportions; the rules set the forms.

The owner's correction loop is the product: read a rule, say it is wrong, change the number, rebuild.

## 1. Stages

| Stage | Output | Gate |
|---|---|---|
| **G0** | Library skeleton with the rules of section 3 transcribed; Land Cruiser 80 hard points measured from the approved sheet and checked against the real car; a drawing of every hard point and rule line over the sheet | Owner reads the car sheet and the drawing: are the numbers right? |
| G1 | Body shell from rules: lower body, bonnet, greenhouse, with specified rounds and crowns; beside the sheet in clay, car paint and side overlay | Owner look, and the rule-compliance report |
| G2 | Panels and openings: four doors, bonnet, tailgate, all glass, with gaps, edge rounds, returns | Owner look |
| G3 | Details: flares and lower cladding, bumpers, lamps, grille, mirrors, handles, roof rack | Owner look at the dressed car |
| G4 | Game asset through the existing Land Cruiser pipeline (`Art/Vehicles/LandCruiser80`, `SK_LandCruiser80` bones, LODs) and a Proving Ground drive | Owner drives it |
| G5 | Second car (Impreza as a sedan) from the same library | Library counts as working |

Fable writes each stage block here before it runs and judges the pictures; Opus executes; the
owner decides every gate. Rules the owner corrects are changed in the library, not in the car.

## 2. Hard points (car frame: metres, X lateral, front = -Y, Z up, origin mid-wheelbase on the ground)

| Name | Meaning |
|---|---|
| WB, TRACK_F, TRACK_R | wheelbase, tracks |
| TYRE_R, TYRE_W | tyre radius and width |
| OH_F, OH_R | overhang from axle to bumper face, front and rear |
| W_BODY | body width at the doors, no mirrors, no flares |
| W_FLARE | width over the flares |
| W_ROOF | roof width between the rail rounds |
| H_SILL | body lower edge at the doors |
| H_BELT | belt line (bottom of the side glass) at the doors |
| H_COWL | windscreen base at the centre line |
| H_BONNET_F | bonnet leading edge |
| H_ROOF | roof top at the centre |
| H_BUMPER_T, H_BUMPER_B | bumper bar top and bottom |
| H_LAMP | headlamp centre |
| Y_COWL, Y_A_BASE | windscreen base at the centre; A-pillar base at the belt |
| Y_ROOF_F, Y_ROOF_R | roof front edge (windscreen top) and rear edge (rear screen top) |
| Y_RS_BASE | rear screen base |
| Y_B, Y_C, Y_D | pillar centre lines at the belt |
| RAKE_WS, RAKE_RS | windscreen and rear screen rake from vertical, degrees |
| RAKE_FRONT, RAKE_REAR | front face and tail face rake from vertical, degrees |
| TUMBLEHOME | side glass lean from vertical, degrees |
| ARCH_R, ARCH_TOP_FLAT | arch opening radius; flat length at the top of a squared arch |
| GROUND_CLEAR | underbody clearance |

Every car sheet lists each hard point with a value, a source (sheet pixels, real-car data, rule
default, owner) and a confidence (measured, derived, assumed).

## 3. Rules, first set: boxy SUV (Land Cruiser 80 style)

Format in the library: one Markdown table per subsystem with the columns ID, rule, boxy SUV
value, sedan value, source, confidence. Values are metres or degrees unless marked. Sources: R =
real-car data, S = approved sheet, P = design practice (Fable), O = owner. Confidence: M measured,
D derived, A assumed. The sedan column is filled only where known; G5 completes it.

### Greenhouse (GH)

| ID | Rule | Boxy SUV | Sedan | Src | Conf |
|---|---|---|---|---|---|
| GH-01 | The windscreen is one sheet, cylindrical about a vertical axis: plan bow sag across its width; no curvature up the glass | sag 0.030 | 0.060 | P | A |
| GH-02 | Windscreen rake from vertical | RAKE_WS 32 (28 to 38) | 60 to 65 | P | A, measure on sheet |
| GH-03 | A-pillars are straight in side view at the windscreen rake; width seen from the side | 0.090 | 0.080 | P | A |
| GH-04 | The roof is flat with a crown: sag across W_ROOF and along its length | 0.020 across, 0.015 along | 0.035, 0.030 | P | A |
| GH-05 | Roof rail round radius (roof to side glass plane) | 0.035 | 0.080 | P | A |
| GH-06 | Roof front edge round (roof to windscreen) and rear edge round | 0.040, 0.040 | 0.120, 0.100 | P | A |
| GH-07 | Side glass is flat, leaning in by TUMBLEHOME | 6 (4 to 9) | 20 to 25 | P | A, measure |
| GH-08 | Rear screen is flat, raked RAKE_RS; on a tailgate its base sits at the tailgate top | 8 (3 to 15) | 55 to 62 | P | A |
| GH-09 | B, C, D pillars are vertical in side view; widths at the belt | 0.090, 0.110, 0.150 | B 0.100 | P | A, measure |
| GH-10 | The belt is a straight horizontal line from the A-pillar base to the tail | H_BELT | rises 0.03 to the rear | S | measure |
| GH-11 | Side glass top edge = roof rail round bottom minus a header; glass corner radius | header 0.040, r 0.040 | 0.050, 0.060 | P | A |
| GH-12 | Front door glass has a fixed quarter light ahead of the drop glass only if the A-pillar base is ahead of the door line by more than this | 0.120 | 0.120 | P | A |

### Bodyside (BS)

| ID | Rule | Boxy SUV | Sedan | Src | Conf |
|---|---|---|---|---|---|
| BS-01 | Below the belt the side is one near-flat plane leaning in above the waist; waist at the belt | lean 3 | 8 to 12 | P | A |
| BS-02 | Belt edge: the top of the lower body rounds into a ledge under the glass | r 0.015, ledge 0.030 | 0.025, 0.030 | P | A |
| BS-03 | Sill: the side tucks under over the bottom part of its height, at an angle | tuck 0.060 high at 30 | 0.080 at 35 | P | A |
| BS-04 | Shoulder crease line on the bodyside at a height above the sill, depth | none | at 0.55 H, 0.004 | P | A |
| BS-05 | Arch opening: circle about the hub, radius ARCH_R = TYRE_R + margin; squared style flattens the top over ARCH_TOP_FLAT | margin 0.080, flat 0.35 x dia | 0.070, round | P/S | A, measure |
| BS-06 | Flare: a lip around the arch, width out from the body and height, with a lower cladding strip along the sill of the same material | 0.070 out, 0.060 tall; cladding 0.120 tall | lip 0.015 | S | measure |
| BS-07 | Door bottoms sit above the sill line by | 0.040 | 0.040 | P | A |

### Front (FR) and rear (RR)

| ID | Rule | Boxy SUV | Sedan | Src | Conf |
|---|---|---|---|---|---|
| FR-01 | The front face is upright, leaning forward at the top by RAKE_FRONT; the grille and lamp panel is one plane | 5 (0 to 10) | 25 to 40 | P | A, measure |
| FR-02 | Bonnet: flat with a crown across; falls from the cowl to the leading edge | crown 0.025; fall 0.040 | 0.030; 0.150 | P | A, measure |
| FR-03 | Bonnet leading edge round; front face vertical corner radius in plan | 0.035; 0.120 | 0.060; 0.250 | P | A |
| FR-04 | Bumper bar: a box across the face at H_BUMPER, protruding, wrapping round the corner along the side | 0.180 tall, 0.100 out, wraps 0.250 | 0.150, 0.060 | P | A, measure |
| FR-05 | Headlamps: rectangles on the lamp panel, outboard, centred at H_LAMP | 0.200 x 0.120 | varies | S | measure |
| RR-01 | Tail face vertical to RAKE_REAR; tailgate spans the full width between the quarter panels | 3 (0 to 6) | 15 to 25 | P | A, measure |
| RR-02 | Roof rear edge round; tail vertical corner radius in plan | 0.040; 0.100 | 0.100; 0.200 | P | A |
| RR-03 | Rear bumper as FR-04 | same | same | P | A |

### Layout (LAY)

| ID | Rule | Boxy SUV | Sedan | Src | Conf |
|---|---|---|---|---|---|
| LAY-01 | Front door leading edge continues the A-pillar base line down to the sill, raked back slightly | 5 from vertical | 10 | P | A |
| LAY-02 | B-pillar centre as a fraction of the wheelbase behind the front axle | 0.48 | 0.50 | P | A, measure |
| LAY-03 | Rear door trailing edge is vertical, ahead of the rear arch by | 0.060 | cuts into the arch | P/S | measure |
| LAY-04 | Bonnet shut lines: along the fender top at a set distance inboard of the body side; rear edge at the cowl | 0.060 | 0.080 | P | A |
| LAY-05 | Panel gap; edge round; return depth | 0.006; 0.004; 0.015 | same | O | defaults |
| LAY-06 | Tailgate split: upper glass hatch and lower drop gate, split at | H_BELT | n/a | S | measure |

The owner corrects any row; the library file is the record.

## 4. G0 block (executable)

Output folder `Art/Export/VehicleTools/landcruiser-grammar-g0-v01/`. Library at `Art/CarGrammar/`.

**4a. Skeleton.** `Art/CarGrammar/README.md` (what the library is, how to edit a rule),
`schema/hardpoints.md` (section 2), `rules/greenhouse.md`, `rules/bodyside.md`, `rules/front_rear.md`,
`rules/layout.md` (section 3, same columns), `bodytypes/boxy_suv.md` (the boxy SUV column
collected), `cars/landcruiser80.md` (4c), and `grammar.py` that parses these tables into Python
dictionaries and fails loudly on a malformed row. Tables are the single source of truth.

**4b. Reference registration.** The approved sheet is
`Art/References/Vehicles/LandCruiser80_v01/01_exterior_proportions_v2.png` (1536 x 1024; side, top,
front, rear). Register the side view on its wheel centres with WB = 2.850 m (real car). Check the
other views against the side view by the roof height (front, rear) and the length (top) and report
each view's scale; if a view disagrees by more than 3% say so and use the side view as authority.
The side view's roof is near the image top: report whether it is clipped.

**4c. Land Cruiser 80 car sheet.** Measure every hard point of section 2 from the sheet by image
analysis (edges of the body colour, the glass, the dark cladding, the tyres), each with its pixel
evidence. Real-car values to check against (Fable's recollection, to be verified against the Toyota
pages linked in `docs/LANDCRUISER_MODEL_STUDY.md` if they can be fetched; otherwise mark
"unverified"): length 4.82, width 1.93, height 1.86, wheelbase 2.85, tracks 1.595 / 1.615, tyre
275/70R16 (radius about 0.395), ground clearance 0.22. Where the sheet and the real car disagree,
the sheet wins (it is the approved style) and the difference is reported.
Also measure the "measure" rows of section 3 (rakes, tumblehome, pillar widths and positions, arch
shape, flare size, bumper, lamps, tailgate split) and write the measured value next to the rule
default.

**4d. Drawing.** `hardpoints-drawing.png`: the sheet with every measured line drawn and labelled
(belt, cowl, roof, bonnet edge, bumper, sill, pillar centres, arch circles, rakes), in a colour per
subsystem, plus a legend table of values. This is what the owner reviews.

**4e. Report.** The car sheet as a table, the view-scale check, every rule row with its measured
value, and the drawing path. No build in G0.

Rules for the run: new files only under `Art/CarGrammar/` and the output folder; nothing else
edited; no commits; headless tools only; look at the drawing before reporting.

## 5. G1 and later (blocks written after G0)

G1 builds the shell as rounded, crowned boxes from the hard points and rules: a lower body whose
plan outline, lean and rounds are rule values; a bonnet; a greenhouse with raked front and rear
faces; all rounds true arcs of the stated radii; crowns as stated sags. The construction and
sampling code from `body_builder` is reused with rule-driven curves. Output beside the sheet, with
the rule-compliance report (each rule re-measured on the shell).

## 6. G0 result and the G1 block (2026-10-02)

Owner at gate G0: "Yes, sheet height and real-car width, go ahead with G1." Decisions recorded in
`cars/landcruiser80.md` with source O: heights and lengths from the sheet; `W_BODY = 1.830`,
`W_FLARE = 1.900` (real car); `TYRE_R = 0.383` with the hub at that height (the sheet's tyre is
drawn squashed; the arch centre moves up 2.3 cm with it); tracks real 1.595 / 1.615. Rule rows
measured in G0 replace the defaults for this car. Two values set by Fable from the drawing and
flagged as dials: windscreen plan bow `GH-01 = 0.010` (the cowl point implies a nearly flat screen)
and bonnet leading-edge round `FR-03 = 0.100` (the measured 0.215 took in the whole nose curve).

### G1: the shell from rules. Output `Art/Export/VehicleTools/landcruiser-grammar-g1-v01/`

Code in `Art/CarGrammar/build/` (new), importing `grammar.py` for every number and reusing from
`Art/VehicleTools/body_builder/` the station-plane round construction, the mesh sampling, the
wheel proxies, the renders and the checks. No number is typed into the build code: it reads the
car sheet and the rules, and the report names the row each number came from.

**6a. Lower body `L` (sill to belt, nose to tail).** A loft of rounded rectangles over height z:

- Sides at `x = +-W_BODY/2`, vertical; over the bottom 0.060 the side tucks in at 30 degrees
  (BS-03).
- Front face through the bonnet edge (`Y = -2.121` at `Z = H_BONNET_F`), leaning so the top is
  1.8 degrees forward (FR-01 measured); rear face through the rear screen base (`Y = 2.523` at
  `Z = 1.161`), top 5.9 degrees forward (RR-01 measured).
- Plan corner radii: front 0.150, rear 0.100 (FR-03 / RR-02, boxy values).
- Lower edge `z_L(s)`: `H_SILL` everywhere except across each arch, where it is the arch opening:
  a circle of `ARCH_R` about the hub with its top flattened over `ARCH_TOP_FLAT` (BS-05).
- Top surface: ahead of the cowl, the **bonnet plate**: side edges run straight from the A-pillar
  foot (`Y_A_BASE`, `H_BELT`) to the bonnet edge (`-2.121`, `H_BONNET_F`); the centre line runs
  straight from the cowl (`Y_COWL`, `H_COWL`) to the bonnet edge plus 0.007; across the car a
  parabolic crown from the side value to the centre value. Behind the cowl, the **belt ledge**: a
  flat strip at `H_BELT + 0.019 * (Y - Y_A_BASE) / 2.70` (GH-10 measured).
- Round between wall and top: 0.030 everywhere (BS-02), true arc by the station-plane method.

**6b. Greenhouse `G`.** A loft of rounded rectangles from its base up to the roof rounds:

- Base outline at `H_BELT`: half-width `W_BODY/2 - 0.030` (the ledge); front edge on the
  windscreen plane, rear edge on the rear screen plane.
- Side walls lean in so the half-width at the rail tangent equals `W_ROOF/2 = 0.635`; report the
  resulting tumblehome beside the sheet's 21.1 degrees.
- Windscreen plane: through the A-pillar foot (`Y_A_BASE`, `H_BELT`) at `RAKE_WS = 50.3` degrees,
  with plan bow sag 0.010 at the centre (GH-01). Rear screen plane: through (`Y_RS_BASE`, 1.161) at
  `RAKE_RS = 22.1` degrees, top forward, same bow.
- Plan corner radii: A-pillar corners 0.080, rear corners 0.120 (new rows GH-13, GH-14; add them
  to `rules/greenhouse.md`).
- Base: where the wall meets `L`'s top (ledge at the sides, bonnet plate at the front, ledge at the
  tail), found per station as in the body builder.
- Roof plate at `H_ROOF` with crown sag 0.020 across and 0.015 along (GH-04); rounds to the walls:
  rail 0.035 (GH-05), front 0.040 and rear 0.040 (GH-06).
- `L`'s top rows end on `G`'s footprint.

**6c. Bumpers.** Two boxes: front from `Z = H_BUMPER_B` to `H_BUMPER_T`, face at
`Y = -(WB/2 + OH_F) = -2.216`, running 0.386 along each side, edge rounds 0.030, plan corner radius
0.060 (FR-04 measured); rear from 0.438 to 0.654, face at `+2.631`, same rounds. Simple boxes for
now; G3 shapes them.

**6d. Glass by rule, as material.** On `G`'s wall: everything is glass except the pillars and
bands: A-pillar = each front corner arc plus 0.123 along the side (GH-03 measured); B at
`Y_B +- 0.059`; C at `Y_C +- 0.057`; D from `Y = 2.17` round to the rear screen edge; a header band
0.040 below the roof round tangent (GH-11); a belt band 0.030 above the base. Windscreen and rear
screen faces are glass between their pillars and bands. Two materials: body grey, glass dark.

**6e. Wheels.** Cylinders radius `TYRE_R`, width 0.280, centred at the hubs, outer faces at
`TRACK/2 + 0.140`.

**6f. Mesh and files.** Dense sampling as in the body builder (stations about 0.03 along the
outline, rows about 0.03 up the walls, 12 rows across each round). `LandCruiser80_Shell.blend`
with L, G, bumpers and wheels as separate objects. Everything mirrored about X.

**6g. Rule compliance report.** Re-measure on the built mesh and list spec against measured:
roof height, belt height, cowl point, bonnet edge, overhangs, windscreen rake (plane fit to the
windscreen glass faces), rear screen rake, tumblehome (plane fit to the side glass), rail round
radius (curvature across the round), arch radius, bumper heights, roof width, pillar positions.
Each row: rule or hard point, spec, measured, difference, pass if within 5 mm or 0.5 degrees.

**6h. Pictures.** `shell-views.png` (2 x 4: sheet crops of side, front, rear, top over the shell
from matching orthographic cameras, clay with glass tint and wheels); `shell-gloss.png` (car paint
and stripes, front and rear three-quarter); `shell-side.png` (shell in clay over the sheet's side
view at the G0 registration: 194.552 px/m, hubs at px 429.38 and 983.86, ground at 349.79; and the
shell outline in magenta over the sheet); `shell-quarters.png` (clay with glass tint and wheels,
front and rear three-quarter, large).

Checks: outline against the sheet's side view over the body (not the flares, tyres or mirrors):
mean and max, cm; fold detector as before, excluding the base junctions and the lower boundary.
Targets: outline mean <= 1.5 cm, max <= 4 cm; fold max <= 12 degrees. The review is never a stop.

## 7. G1 v01 result and the v02 block (2026-10-02)

Fable's look at `landcruiser-grammar-g1-v01` (`shell-quarters.png`, `shell-side.png`): the rule
build works. The shell is crisp and clean, reads as the boxy SUV, and the side outline sits on the
sheet everywhere except the windscreen and the nose top. 28 of 35 compliance rows pass.

Faults and their causes, all in the numbers, not the construction:

1. **Windscreen 19 cm too far back.** G0 recorded `RAKE_WS = 50.3` as "from vertical", but the
   slope it came from (1.203 px/px) is 50.3 degrees from *horizontal*, i.e. **39.7 from vertical**.
   With 39.7 the plane through the A-pillar foot reaches the roof at Y = -0.197, which is the
   sheet's `Y_ROOF_F = -0.191`, and passes 3 cm behind the cowl point, which a plan bow of 0.030
   (the GH-01 default) closes. The rear screen's 22.1 is from vertical and is right.
2. **Nose top corner 5 to 8 cm above the sheet.** Fable's dial `FR-03 = 0.100` was wrong; the G0
   measurement of 0.215 was closer. Use 0.200.
3. **Belt 1 cm high at mid-doors.** The ledge formula anchored `H_BELT` at the A-pillar foot; G0
   measured it at mid-doors. Anchor at mid-doors (Y = 0.75).
4. **Hard crease along the belt.** The greenhouse wall leaves the shoulder round's tangent with no
   flat ledge. Keep a flat ledge of 0.030 (BS-02) between the round's tangent and the glass base.
5. **Sill tuck crease.** Round the tuck edge with 0.015.

### G1 v02. Output `landcruiser-grammar-g1-v02/`

- Car sheet: `RAKE_WS = 39.7` (from vertical; note the correction and the evidence in the row),
  `GH-01 = 0.030`, `FR-03 = 0.200`, belt anchor at mid-doors. Everything else as v01, including the
  agent's recorded interpretations.
- Build, compliance, outline, folds and the four pictures as section 6. Targets unchanged.
  The fold detector now excludes the sill tuck edge as a designed crease, and reports it separately.

### 7a. Correction to section 7 (2026-10-02)

Fable's "39.7 from vertical" was wrong; the agent's check stands: the sheet's windscreen centre line
runs from the cowl (-0.764, 1.231) to the roof front (-0.191, 1.707), 50.3 degrees from vertical,
and its base sits 0.185 m ahead of the A-pillar foot at the belt and 0.073 m ahead at the roof. The
sheet's top view shows the same thing: the screen's base edge bows forward strongly at the centre,
its top edge much less.

Decision: anchor the windscreen at the centre and let the bow vary with height.

- `RAKE_WS` stays 50.3 from vertical.
- The windscreen plane passes through the cowl point (`Y_COWL`, `H_COWL`) at the centre.
- **GH-01 revised:** the plan bow sag is not constant; it is `BOW_BASE` at the glass base and
  `BOW_TOP` at the roof round tangent, linear between. For this car `BOW_BASE = 0.185`,
  `BOW_TOP = 0.073` (source S, measured). The boxy-SUV default becomes 0.060 / 0.030, sedan
  0.080 / 0.050 (assumed).
- The A-pillar follows the windscreen's side edge (GH-03), so it lands on the sheet's A-pillar foot
  and roof corner by construction; the sheet's 45 degree pillar strip is an inconsistency of the
  generated drawing and is not used.
- The rear screen keeps a constant bow of 0.030.

Everything else in section 7 stands.

## 8. G1 v02 result (2026-10-02): at owner gate G1

31 of 37 compliance rows pass (the misses are 6 to 12 mm or under 1.6 degrees, each explained by a
construction choice); outline mean 1.21 cm (target 1.5), max 6.7 cm at the nose top where the
sheet's nose is rounder than a 0.200 round; folds max 9.0 degrees. Fable's look: the windscreen
now sits on the sheet's, the shell is crisp and clean and reads as the car. Remaining: nose top
6 cm proud, a twist banding on the windscreen from the shrinking bow, a wavy spot at the rear
screen's lower corners, the tuck edge breaking at the arch ends. Next: owner gate G1, then G2
(panels and openings).

## 9. G2 block: panels and openings (2026-10-02, owner: "Yes, go ahead with G2")

Output `Art/Export/VehicleTools/landcruiser-grammar-g2-v01/`; code in `Art/CarGrammar/build/`.
The G1 v02 masters are unchanged. Every panel is a **region of a master grid**: the lower body
grid `L` (station along the plan outline x profile row: wall, round, top) and the greenhouse grid
`G` (station x row: wall, round, roof). A region is a station range with a bottom and a top
boundary per station; boundaries that fall between existing rows or stations get a row or station
inserted at the exact position (the masters are analytic, so any sample is exact). Each panel is
its own object. Numbers come from the car sheet, the rules and the new layout rows below; no
number is typed into the build.

### 9a. New and revised layout rows (add to `rules/layout.md`, boxy-SUV value / sedan value)

| ID | Rule | Boxy SUV | Sedan | Src |
|---|---|---|---|---|
| LAY-01 (used) | Front door leading edge: through the A-pillar foot, bottom forward, rake from vertical | 7.4 (measured) | 10 | S |
| LAY-02 (used) | Front and rear door split at the B-pillar centre line `Y_B` | 0.336 (measured) | | S |
| LAY-03 (used) | Rear door trailing edge at the belt, as a distance behind the rear arch opening's front edge; rake from vertical, bottom forward; the door's lower rear corner is cut by the arch opening | 0.293; 6.4 | | S |
| LAY-04 (used) | Bonnet shut line along the fender top, inboard of the body side | 0.060 | 0.080 | P |
| LAY-05 (used) | Gap; edge chamfer; return depth | 0.006; 0.004; 0.015 | same | O |
| LAY-06 (used) | Tailgate split height; tailgate half-width | 0.999 (measured); 0.660 (S, rear view) | n/a | S |
| LAY-07 new | Door bottom edge above the sill line (BS-07); the rocker strip below belongs to the body | 0.040 | 0.040 | P |
| LAY-08 new | Door window frames: the door carries its frame up to the header band; frame width round the glass | 0.035 | 0.035 | P |
| LAY-09 new | Cowl strip between the bonnet rear edge and the windscreen base | 0.040 | 0.060 | P |
| LAY-10 new | Front panel seam: a vertical seam at the end of the front plan corner arc (fender to grille panel); rear quarter runs to the end of the rear corner arc | at the arc end | same | P |
| LAY-11 new | Lower tailgate bottom edge above the rear bumper top | 0.010 | n/a | P |
| LAY-12 new | Hinges: doors on a vertical axis at the leading edge; bonnet on a transverse axis at its rear edge; lower tailgate on a transverse axis at its bottom edge; upper hatch on a transverse axis at the roof rear round tangent | | | P |

### 9b. Panels (half car, mirrored where symmetric; tailgate and bonnet are single objects)

| Panel | Master grid regions |
|---|---|
| Front panel (grille and lamp face) | `L` front face and both corner arcs, from the sill to the bonnet nose round's wall tangent |
| Front fender | `L` from the corner-arc end (LAY-10) to the front door leading edge (LAY-01), rows from `z_L` (arch included) up over the shoulder round to the shut line 0.060 inboard (LAY-04) |
| Bonnet | `L` top rows inboard of the shut lines, from the nose round's wall tangent (the round rows belong to the bonnet) back to the windscreen base less the cowl strip (LAY-09); one object |
| Front door | `L` skin: stations between LAY-01 and `Y_B`, rows from door bottom (LAY-07) to the belt; plus `G` frame: stations from the A-pillar trailing edge (windscreen side edge plus GH-03) to `Y_B`, rows from the belt band to the header band; the glass region inside the frame width (LAY-08) is cut out and becomes the front door glass pane |
| Rear door | `L` skin from `Y_B` to the LAY-03 trailing edge, bottom rows cut by the rear arch opening; `G` frame from `Y_B` to `Y_C`, glass pane as above |
| Rocker | `L` from the fender's rear edge to the quarter's front edge, rows from the sill to the door bottom less a gap |
| Rear quarter | `L` from the LAY-03 edge to the rear corner-arc end, rows from `z_L` (arch) over the round to the belt ledge; plus the tail face outside the tailgate half-width (LAY-06); plus `G` from `Y_C` round to the rear corner-arc end, rows belt band to header band, with the quarter glass pane cut out (between the C-pillar and the D-pillar front edge) |
| Lower tailgate | `L` tail face between `x = +-0.660`, rows from LAY-11 to the split (LAY-06); one object |
| Upper hatch | `L` tail face between `+-0.660` from the split to the belt, plus `G` rear wall between the rear corner arcs from the belt band to the rear round tangent; the rear screen pane cut out inside a LAY-08 frame; one object |
| Cabin frame | everything of `G` not assigned above: A-pillars, windscreen header and base bands, the side header bands, the D-pillars' upper part, the rail and header rounds and the roof plate; the windscreen pane cut out inside the A-pillars and bands; one object |
| Glass panes | windscreen, front door, rear door, quarter, rear screen: the cut-out regions, inset by `GLASS_INSET = 0.006` along the surface normal |

### 9c. Gaps, chamfers, returns

Every panel boundary that meets another panel is moved inward by half the gap (LAY-05) along the
surface. Along each boundary loop: a 0.004 chamfer row at 45 degrees, then a return of 0.015
straight inward along the surface normal. Boundaries on the open lower edge (sill, arches) get
the return only. Glass panes get a 0.004 edge round and no return.

### 9d. Checks

- Gap width sampled along every seam (mean, min, max; pass within 1 mm of 0.006).
- Seam positions against the sheet: front door leading edge at the belt and at the sill, B-pillar
  line, rear door trailing edge at the belt, bonnet shut line, tailgate split, each in cm.
- Window outlines against the sheet's dark window regions (G0 mask): mean edge distance per pane.
- Outline and fold checks as G1 on the assembled panels (folds exclude seams and returns).
- Object list with face counts; each object manifold apart from its returns' open edges.

### 9e. Pictures

- `panels-quarters.png`: clay, each panel a slightly different grey, glass dark, wheels; front and
  rear three-quarter, large.
- `panels-open.png`: the same with the front doors open 50 degrees, the bonnet raised 35, the
  lower tailgate dropped 80 and the hatch raised 60, about the LAY-12 hinges; front and rear
  three-quarter.
- `panels-side.png`: clay over the sheet's side view at the G0 registration; and the seam lines in
  magenta over the sheet.
- `panels-gloss.png`: car paint, front and rear three-quarter.

Report: the checks, deviations (with sizes), what looks wrong and where, the four picture paths.
No verdict.

## 10. G2 v01 result (2026-10-02): at owner gate G2

25 objects (12 body panels, 5 glass panes, wheels, aids). Gaps 6.06 mm mean, 96% within 1 mm,
misses at junction ends. Front door edge within 0.5 cm of the sheet; rear door edge within 1.8 cm;
B line 3.5 to 6.7 cm behind the sheet's door edge (LAY-02 uses the pillar centre measured from the
glass; the sheet's door edge is at about Y 0.29); tailgate split within 0.5 mm; bonnet shut line at
6.05 cm. Outline mean 1.02 cm. Fable's look at `panels-quarters.png` and `panels-open.png`: it reads
as the car's body with real shut lines, and the opened doors, bonnet, tailgate and hatch are real
parts. Faults: a wrinkle at the bonnet nose corner, a wavy hatch base and rear screen bottom (the
G1 base line along the tail), folds where the arches cut the sill tuck, a small slot at the
A-pillar foot, the front door glass reaching the A-pillar where the sheet has a mirror sail, the B
line as above. Next: owner gate G2, then G3 (details).
