# Car body pipeline plan

Written 2026-10-02 after the owner said "Create a plan to make this pipeline work". Goal: approved
reference image in, clean game-ready car body out, repeatable across the car list, with no body
surface shaped by hand or by eye.

## 1. What is proven and what is not

| Step | Status | Evidence |
|---|---|---|
| Reference approval (generated four-view sheet + side view) | Works | Owner approved the Impreza sheet ("Good. Go") |
| 3D blueprint: Tripo mesh from the approved views | Works as a shape guide only | Owner: shape looks right; as an asset "not anywhere as good as they need to be" |
| Correcting the blueprint to the approved side view | Works | Silhouette overlap 0.985, bumper face within 2 px (`Art/VehicleTools/scaffold_cage/sc1_side_fit.py`) |
| Measured lines (shoulder, roof rail, glass bottom, sill, arches) | Works | `cage-lines.json`, `reference-lines.json` |
| Body surface by script (GPT v08) | Fails likeness | Side comparison against the approved image |
| Body surface by fitted cage (v01, v02) | Fails surface quality | Pleats, folds, wavy quarters in gloss (`docs/SCAFFOLD_CAGE_PLAN.md` sections 8, 10) |
| Body surface straight from the generator | Fails surface quality | Owner verdict above |
| Fitted parts, assembly checks (GPT workshops) | Works for assembly | 12 static checks pass on v08 |

## 2. Diagnosis

Every failed attempt **created** the body surface from nothing: by script, by fitting, or by a
generator. Clean car panels depend on topology choices (loops around arches and corners, where
panels break) that none of those methods makes well. Three attempts, three methods, same wall.

**Rule for this plan: nothing in the pipeline creates body surface. It only deforms a body that is
already known to be clean.** A smooth deformation of a fair surface stays fair, and the topology
judgement is made once, by whoever built the template, not per car.

## 3. Target pipeline

```
approved image  ->  blueprint (Tripo, corrected to side view)  ->  MORPH an approved template body
                                                                    onto the blueprint
                ->  fitted parts (GPT workshops)  ->  game prep  ->  Unreal
checks at every arrow: likeness, surface, fit
```

Only the morph step is new. The steps before it exist and pass; the steps after it are GPT's
existing tooling and the Unreal pipeline.

## 4. Stages

Each stage ends at a gate. A failed gate stops the plan at that cost; nothing later is started.

### CB0. Write the bar down as checks

The owner's eye is the bar, but the pipeline needs to know before the owner looks.

- `body_checks.py` (extends `sc4_review.py`): one sheet per body with
  1. side outline against the approved image (mean and max, cm);
  2. clay and gloss/stripe renders from four fixed cameras;
  3. fold count: edges of the smoothed surface over 20 degrees that are not on a declared panel
     edge;
  4. curvature wobble: per panel, how often the curvature along the car changes sign;
  5. panel gaps: width along every seam (mean, spread).
- Calibrate on four bodies whose rank is already known: a mesh the owner names as good enough
  (needed from the owner), then Tripo, cage v02, GPT v08. The thresholds are set so the sheet ranks
  them the way the owner does.

Gate: the owner agrees the sheet's ranking matches their eye. Cost: one short agent run.

### CB1. Source a template body (sedan first)

- Criteria: clean quad topology meant for subdivision; panels already separate (doors, bonnet,
  boot, bumpers, glass); smooth simplified forms closer to the approved concept style than to a
  realistic car; no fine modelled trim; licence that allows modification and use in a shipped game.
- Three candidates, each run **unmodified** through the CB0 sheet.
- Purchases are made by the owner. A template is per body type (sedan, SUV/wagon, pickup), not per
  car.

Gate: the owner picks one template that meets the bar as it stands, or rejects all three. If the
template is not good enough, nothing downstream can be. All rejected: go to Track B or stop.

### CB2. Correspondences (no judgement, same code on both meshes)

- Run the existing line extraction on the template and on the blueprint: centre-line top profile,
  shoulder/roof-rail line, glass-bottom line, sill, arch outlines, nose and tail outlines in plan.
- Split each line at named features found by rule (cowl, roof front and rear, backlight base, boot
  edge, arch legs); pair points by position between features. About 300 to 600 point pairs, plus
  wheel centres and the ground plane.
- Debug sheet: the paired lines drawn on both meshes.

Check: after a best uniform scale and shift, no pair is more than 25 cm apart (a larger gap means a
feature was misidentified).

### CB3. Morph

- One smooth 3D warp (regularised thin-plate spline) fitted to the point pairs and applied to every
  template part together, so gaps and returns move with their panels.
- Stiffness is a named number, raised until the fold count and curvature wobble are no worse than
  the unmorphed template.
- Wheel arches: pairs around each arch keep it round; wheels are placed from the reference, not
  warped.
- Width is one dial (the reference sheet's front and top views disagree; cage runs used 0.926 of the
  Tripo width, 1.90 m at the doors).

Acceptance: side outline mean <= 1.0 cm and max <= 3.0 cm; fold count and wobble within 10% of the
template; gap spread within 1.5 mm of the template.

Gate: owner looks at clay, gloss and the side comparison beside the approved image. This is the
gate that decides the plan. Cost to reach it: CB0 to CB3, about three agent runs plus the template.

- CB3b, only if the gate says "right family, wrong car": pull the morphed body toward the blueprint
  at scales above 15 cm only, then rerun the checks.

### CB4. Character parts

What makes it this car: lamps, grille, bumper inserts, bonnet scoop, roof scoop, wing, lamp pod,
mudflaps, mirrors.

- Apertures are cut on the morphed shell from outlines measured on the approved image.
- Parts come from GPT's workshops, fitted to the measured apertures and mounts.
- GPT's 12 assembly checks plus the CB0 sheet.

Gate: owner look at the dressed car.

### CB5. Game prep and Unreal

Material slots, UVs, GT Paint panel bakes, export, vehicle setup, Proving Ground drive.

Gate: owner drives it.

### CB6. Second car

Pathfinder on an SUV template, CB1 to CB5 again. The pipeline counts as working only when a second
car passes with no new design work.

## 5. Track B (only if CB1 finds no acceptable template)

Build panels from shapes that cannot ripple: one low-order patch per panel (bonnet, roof, door
side), sweeps for bumpers, fillets between them, each fitted to the blueprint inside its measured
boundary lines.

- Proof first: bonnet plus one front fender only, through the CB0 sheet.
- Gate: owner look at those two panels in gloss. Fail: stop; the body shell is then a job for a
  modeller.

Track B is riskier than the morph because it creates surface again, in a more constrained way.

## 6. Roles and stop rules

- Fable writes each stage block, judges the sheets, gates. Opus (or GPT/Codex) executes. The owner
  decides every gate.
- No stage is reported as passing on numbers alone; the pictures are looked at first.
- Stop the plan if: CB0's ranking cannot be made to match the owner's; CB1 and Track B both fail;
  CB3 fails twice on the same template.

## 7. Needed from the owner to start

1. One mesh that meets the bar (any car, from any source), to calibrate CB0.
2. Whether a bought template is acceptable, and a rough price ceiling per template.

## 8. Revision 2 (2026-10-02): the builder tool is the main route

Owner: "I don't see why we can't build a tool which builds a model using the Tripo one as a guide
for form and shape, as well as placement of details." Agreed as the main route. The template morph
(CB1 to CB3) becomes the fallback. The owner will also supply a shell they like.

Why the first guided build (cage v01/v02) failed, and what the tool does differently:

| Cage v01/v02 | Builder tool |
|---|---|
| Treated the car as one sheet draped over about 45 cross-sections | Builds the car panel by panel, as a car is made |
| About 600 free points, each copied from the Tripo surface, noise included | Each panel is one simple smooth shape with 16 to 30 numbers, fitted to the Tripo surface as a whole |
| Panel edges, corners and arches fell wherever the grid happened to be | Panel edges are measured lines from the approved image and the Tripo texture |
| No idea of a panel gap, an edge round or an arch lip | Those are fixed style numbers, measured from the shell the owner likes |

A shape with that few numbers cannot ripple or fold, which is the fault that sank the cage.

### Stages

- **BT0. Bar and style numbers.** CB0's check sheet, calibrated on the owner's liked shell. From the
  same shell, measure the style numbers the tool will reuse: panel gap width, edge round radius,
  how much crown a panel carries, arch lip section. Gate: the sheet ranks bodies as the owner does.
- **BT1. Panel map.** For the Impreza, every panel boundary as a 3D curve on the corrected
  blueprint: door splits, glass outlines, arch outlines from the approved side image; bonnet, boot,
  bumper and lamp outlines from the Tripo texture and the top, front and rear views. Gate: owner
  looks at the panel map drawn on the blueprint.
- **BT2. Three-panel proof.** Bonnet, front fender with its arch, front door. One low-order patch
  each, least-squares fitted to the blueprint inside its boundary, edges rounded and gapped with the
  style numbers. Through the check sheet. Gate: owner look in gloss.
- **BT3. Hard-part proof.** One front bumper corner with its lamp opening (sweep plus patches). The
  nose and tail are where simple shapes are most likely to look too plain. Gate: owner look.
- **BT4. Full shell.** All panels, glass as its own panels. Acceptance as CB3. Gate: owner look;
  this gate decides the route.
- **BT5. Details from the blueprint.** Lamps, handles, vents, scoops, wing, pod, mudflaps, mirrors
  are located on the Tripo mesh and texture by colour and shape, then GPT's workshop parts are
  fitted at those positions. Gate: owner look at the dressed car.
- **BT6. Game prep and Unreal** (as CB5). **BT7. Second car** (as CB6).

Stop rules: BT2 fails twice, or BT3 fails twice, switch to the template morph (CB1 to CB3).

## 9. Revision 3 (2026-10-02): full builder plan

Owner: "let's make a full plan, and do it". The builder's full plan, with the executable block for
its first stage, is `docs/BODY_BUILDER_PLAN.md`. It replaces stages BT1 to BT4 above: the proof is
now the master surface (tub, then greenhouse), and panels are cut from it afterwards.
