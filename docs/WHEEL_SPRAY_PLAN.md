# Wheel spray: painterly particles for mud and gravel

Main session, 2026-10-10. The owner said "We need to add particles". They chose wheel spray for mud and gravel first,
in a painterly style matching the ground. Dust trails, snow powder and water/steam come later.

## 0. Rules for the agent

`docs/MUDRUNNER_LESSONS_PLAN.md` section 0 holds in full: no timing; the foreign-Unreal wait; run with a game open,
never close it; the owner's look rejections; headless Blender for assets; docs per stage; commit only the stage's
files, hunk by hunk; never push. On top of that:

- **Never touch** the water simulation or Benmore, or the Water and Steam spray kinds' code paths (GTSprayWater.cpp
  stays as it is). Snow keeps its greybox drawing.
- **The gameplay stays exactly as it is.** UGTSprayComponent's CPU pools, emission rules, thrown-blob volumes (LM2a
  `SpawnThrown`, `DepositThrown`), splat traces (MR1) and body hits (MR2) are unchanged. This stage changes only how
  they are drawn, and adds purely cosmetic layers on top. With `gt.Spray.Art 0` the spray is today's greybox,
  identical to before.
- **Look rules for particles** (from the owner's rejections and the ground's style):
  - **Matte:** wet mud particles' roughness is at least 0.45, the same as MRP.
  - **Varied, never uniform:**
    - sizes follow a power law (mostly small);
    - every particle gets a random rotation;
    - emission comes in clumped bursts driven by noise, not a constant stream;
    - no ribbons, streaks or trails that draw regular lines.
  - **The ground's palette:** the mud variant slice colours (wetter is darker), and gravel from the TA_GV arrays.
  - **Painterly:** dab-shaped silhouettes with soft painted edges, made in Blender in the style-study workflow. No
    photographic smoke.

## P0: can Niagara be authored by script here? (time-boxed, report only)

Niagara is not used anywhere in the project yet, though the spray component's header says "Replace the drawing with
Niagara in the art pass". Everything here is built headless, so first find out whether a Niagara system can be made
and edited from a Python commandlet in UE 5.8. Limit this to about 45 minutes of effort.

1. **Create a system** at `/Game/GrandTour/FX/NS_GT_Probe` from an engine template emitter (a sprite burst or fountain
   template under `/Niagara/`).
2. **Edit it by script:**
   - set the sprite renderer's material;
   - expose User parameters: `SpawnRate` float, `BaseVelocity` vector, `Tint` colour, `SizeScale` float;
   - drive the spawn rate from `User.SpawnRate`.
3. **Prove it from C++ or Python in PIE:** a UNiagaraComponent with User.SpawnRate 200 emits, and a -RenderOffScreen
   capture shows sprites.
4. **Report** which of steps 1-3 worked, the APIs used, and the blockers. Also report whether the Niagara plugin and
   module are already enabled (`.uproject`, `GrandTour.Build.cs`).

The main session then picks the drawing path for P2:
- **Path N (Niagara):** cosmetic layers as GPU Niagara emitters driven by User parameters; the gameplay blobs drawn as
  meshes as in Path C.
- **Path C (CPU cards):** cosmetic layers as small extra CPU pools in UGTSprayComponent, drawn by ISMs of
  camera-facing cards (billboarding in the material's world position offset), with masked, dithered opacity, so no
  sorting is needed.

## P1: painterly assets (headless Blender; needed by both paths)

`Art/Blender/build_spray_assets.py` exports to `Art/Export/WheelSpray/`:

1. **Mud clumps (meshes).** 8 small thrown clumps, 2-8 cm at authoring scale, 80-200 triangles. They come from
   LM2c's clod recipe (`build_mud_clods.py`), with torn, stretched shapes: a third are elongated 1.8-3x, as thrown wet
   mud is. These replace the spheres for the Mud kind's CPU blobs. Material: a variant of M_GT_Clod (the variant slice
   through PatchVariant), wet (Fresh 1), roughness at least 0.45.
2. **Mud spatter atlas** `T_GT_SprayMud`: 4x4 frames of painterly wet droplet clusters, from single drops to ragged
   splats with satellites. Colour comes from the material, so the atlas is RGBA: R a soft height for the lighting
   normal, G unused, B unused, A the coverage with soft painted edges. 1024. Used by the fine-droplet layer.
3. **Gravel grit atlas** `T_GT_SprayGrit`: 4x4 frames of tiny angular chips, single and in small clusters. They are
   coloured by the material from the TA_GV Loose stone-face palette (as DG1b's stones are), and alpha-masked. 1024.
4. **Dust puff flipbook** `T_GT_SprayDust`: 4x4 frames over the puff's life, from a tight clump of dabs that spreads
   and thins. It is painted, not smoke-like: overlapping dabs, soft edges, no wisps. Greyscale coverage only, with the
   colour set per surface (gravel: the matrix colour of the Loose bake, lightened ×1.15). 1024.
5. **Renders for the main session's look gate:**
   - `Assets_Clumps.png`: the clumps on a ground plane, in the M_GT_Clod Standard colours;
   - `Atlas_Sheets.png`: the three atlases on grey and on the ground colour.

Stop after P0 and P1 and report: the P0 outcome, the asset paths, triangle counts, atlas paths, and the renders (don't
describe them). P2 is written once the main session has picked a path and looked at the assets.

## P2: integration (main session, 2026-10-10, after P0/P1)

*Done 2026-10-10 (VEHICLE_BUILD_SYSTEM 99): P1b clumps (8 x 276 triangles, 1.6-6 cm, smooth, no cuts); UGTNiagaraSetupLibrary
(BuildWheelSpray, every input write guarded by GetEmitterTopology: module, input name, type, visible/editable, never a static switch
for links) called by Art/setup_wheel_spray.ps1; NS_GT_WheelSpray (MudDroplets and GravelGrit GPU with depth-buffer collision,
GravelDust CPU); one component per wheel from UGTSprayComponent (GTSprayArt.cpp), bursts b(t), bInGravelPatch and PatchVariant on
the wheel; the Mud kind drawn as the clumps (M_GT_SprayClump); gt.Spray.Art / Fine / FineScale; GrandTour.Spray.Art. Read
differently from the text: DustRate x saturate(1 - wetness / 0.6) (zero from 0.6, as asked); the grit's colour is a random point
between GritTintA and GritTintB per particle, varied +-10 % per chip by G. The plan's gravel rates are sparse: the pictures add
the drive and the launch at gt.Spray.FineScale 4.*

*P2b done 2026-10-10 (the main session's look; VEHICLE_BUILD_SYSTEM 99, P2b): the white blots were not the droplets - their base
colour is MudTint (the BaseColor buffer in the sprites' custom-depth mask: Standard 0.0359, Deep 0.0324) - but the CPU Water kind's
pale spray, 29-53 alive in every mud picture (the uncommitted water work's lower splash thresholds fire it in the muddy ruts; not
touched here). Fixed on the way: the collision module killed occluded and offscreen droplets (17-54 alive in a spin, now 466-541),
the emitters sit at hub height, the dust is lit per pixel. Gravel: grit 30 a second a wheel at full, 1-3 cm; dust 8, 60-200 cm,
opacity 0.5. The camera rule (3/4 rear, sun within 60 deg behind: 6.7-23.5 deg), Spray_Mud_Close and Spray_Gravel_Close, the base
colour gate (Art/sample_spray_pbr.py) and the Kill On Collision frame check (mud gone at its first hit, grit at its second).*

*P2c done 2026-10-10 (VEHICLE_BUILD_SYSTEM 99, P2c): the dust's light from MPC_GT_Spray, base colour DustTint x DustLit 0.7 and an
emissive sky floor DustTint x DustFloor 1.4 (the asked 0.3 left the dust in the car's shadow at 0.26 of the sunlit dust in the first
run); dust in shadow 0.775 of dust in sun (asked 0.5). The dark streak was not a flipbook frame, the depth fade or sorting: it did
not recur, a same-frame hide rules out the CPU grey dust, and the only thing that darkens a lit puff is a sun shadow on the per-pixel
lit dust (P2b's lighting), which the floor lifts. Droplets 2-8 cm, their throw's upward part x1.3: 43 % of the visible droplet pixels
above the arch line (asked 25 %). Spray_Mud_Close_NoWater: the same paused frame without the CPU Water spray.*

*P2d done 2026-10-10 (VEHICLE_BUILD_SYSTEM 99, P2d): rooster-tail droplets - clumps of about ten (MudRate / 10 a second) sharing a
velocity within 15 deg and +-20 % of BaseVelocity (upward part x1.3), each droplet +-8 %, the upward launch capped at 700 cm/s:
droplet height p95 1.37 m in Spray_Mud_Drive (a CPU estimate from the launch velocities; asked 2.5 m), the 32 px cell CV 3.376 ->
3.817. Deep exempt from the wet x0.8 (its droplets 0.0319). The muddy rut splash: new CPU Water particles take the mud of the wheel
they left when it is in a Mud patch (the rut water's turbidity, the variant's MudTint at max(0.6, sqrt(turbidity)), Alpha to 0.85),
through the Water ISM's custom data 2-6 and a path added onto M_GT_WaterSpray by setup_wheel_spray.py; Codex's water hunks and
GTSprayWater.cpp untouched. Its pixels in Spray_Mud_Close: 4386, median luminance 0.1011, R 0.165 > G 0.089 > B 0.030.*

**P0 outcome:** Niagara can be authored headless through UE 5.8's `UNiagaraExternalEditUtilities` (experimental and
C++ only, so Python calls a C++ editor function). An input linked by a wrong name, such as a static switch, crashes
the editor. **Chosen path:**
- **Hybrid.** The cosmetic layers are GPU Niagara.
- The gameplay mud blobs stay as CPU particles, now drawn as clump meshes.
- Gravel's flicked stones stay DG1's HISM stones.

**My look at P1:**
- The three atlases pass.
- The clumps fail: hard facets and flat shading read as small brown rocks, and the 8 cm flake as a stone slab.

0. **P1b, clumps.**
   - Smooth shading. One subdivision level with noise displacement (each mesh at most 300 triangles).
   - Droopy, torn silhouettes. The "string" family tapers into a tail.
   - The largest is 6 cm.
   - Re-render `Assets_Clumps.png` with the Standard bog bake's colour (triplanar) instead of flat brown. Continue
     without waiting; I judge the clumps in the game pictures.
1. **The probe becomes the setup.**
   - `GTNiagaraProbe` becomes `UGTNiagaraSetupLibrary` (editor module), with no probe names left.
   - Its one build function, `BuildWheelSpray`, is called from `Art/Unreal/setup_wheel_spray.py`.
   - **Crash guard:** before any `SetStackInputData`, read `GetEmitterTopology` and assert that the module, the input
     name and the input's type match exactly. If one doesn't, fail with the name; never link.
   - Keep `Niagara`, `NiagaraCore` and `NiagaraEditor` in GrandTourEditor.Build.cs, and add `Niagara` to
     GrandTour.Build.cs for the runtime component.
   - Delete the probe's assets and Python.
2. **`NS_GT_WheelSpray`**, three emitters built from engine templates, GPU sim where depth-buffer collision is used.
   User parameters: `MudRate`, `GritRate`, `DustRate`, `BaseVelocity` (world cm/s), `MudTint`, `GritTintA`,
   `GritTintB`, `DustTint`, `SizeScale`.
   - **MudDroplets:**
     - sprites from T_GT_SprayMud, a random frame;
     - size 1-6 cm, power-law;
     - velocity BaseVelocity ± a 35° cone and ±40 % speed;
     - gravity 980, drag 0.3, life 0.6-1.4 s, killed on depth-buffer collision;
     - masked (alpha test 0.33), lit, colour MudTint, roughness 0.5.
   - **GravelGrit:**
     - T_GT_SprayGrit frames;
     - size 0.5-2 cm;
     - colour lerp(GritTintA, GritTintB, G);
     - gravity 980, one bounce on depth collision (restitution 0.3) and then death, life 0.8-1.5 s;
     - masked, lit.
   - **GravelDust:**
     - the T_GT_SprayDust flipbook over each particle's life;
     - size 30-120 cm, growing ×2.5;
     - drag 1.5, a slight rise of 20 cm/s, life 1.5-3 s;
     - translucent, lit, maximum opacity 0.35, colour DustTint.
3. **Emission (C++, UGTSprayComponent).**
   - One UNiagaraComponent per wheel, attached at its contact.
   - Each tick, set the User parameters from the existing per-wheel kind selection and rates. Nothing in the CPU
     pools changes.
   - **Mud** (Mud or Bog tag):
     - MudRate = 6 × the Mud kind's current emission rate;
     - MudTint = the patch variant's slice mean colour (from the bake manifests, × 0.8 for wet), or the Standard
       colour outside a patch;
     - BaseVelocity = the direction and speed the CPU emission already uses.
   - **Gravel** (a new per-wheel `bInGravelPatch`, set the way `bInSnowPatch` is: the contact's patch has
     Medium == Gravel):
     - GritRate = 10 × max(speed factor, slip factor), using the same factors the Dust kind uses;
     - DustRate = 2.5 × the same × (1 − weather wetness), so it is zero above wetness 0.6;
     - GritTintA/B and DustTint from the TA_GV Loose palette (DG1b's stone colours, and the matrix colour × 1.15);
     - with `gt.Spray.Art 1`, the gravel's grey Dust spheres stop. Dirt outside gravel keeps its greybox dust.
   - **Bursts:** every rate is multiplied by b(t) = (0.3 + 1.4 × n(t))², where n is a per-wheel smooth noise at 3 Hz,
     renormalised so the mean of b is 1. Clumps, never a constant stream.
4. **Mud blobs drawn as clumps.** With `gt.Spray.Art 1`:
   - the Mud kind's ISM draws the 8 P1b clumps (one ISM per mesh, the mesh picked by particle id), scaled to the
     blob's size;
   - the strings stretch ×1.5 along their velocity, and the others tumble at a random spin of 2-8 rev/s;
   - material `M_GT_SprayClump`, from M_GT_Clod's builder: the variant slice from per-instance custom data (the slice
     of the patch the blob left), wet (Fresh 1), roughness at least 0.45.
   - The Snow, Water and Steam kinds draw as before.
5. **Switches:**
   - `gt.Spray.Art`: 0 is today's greybox, exactly;
   - `gt.Spray.Fine`: 0 turns the Niagara layers off;
   - `gt.Spray.FineScale`: the multiplier on all three rates, default 1.
6. **Tests:**
   - The spray test passes at Art 0 and at 1, with identical CPU emission and thrown volumes.
   - New `GrandTour.Spray.Art` (CPU):
     - bInGravelPatch is set on a gravel patch and not on mud or snow;
     - the burst mean is 1 ± 5 % over 60 s;
     - every rate is 0 at Fine 0;
     - DustRate is 0 at wetness 0.7;
     - the clump mesh choice is deterministic per particle id.
   - All Mud, Snow and Gravel tests, with the CRC unchanged.
7. **Pictures** (a new `Art/Unreal/check_wheel_spray.py`, rendered; mid-action captures):
   - L_MudVariants:
     - `Spray_Mud_Spin.png`: side view 4 m away, the car stuck in Deep with the throttle held;
     - `Spray_Mud_Spin_Greybox.png`: the same at Art 0;
     - `Spray_Mud_Drive.png`: a chase camera 6 m behind and 2 m up at about 25 km/h in Standard.
   - L_GravelDeform:
     - `Spray_Gravel_Drive.png`: a chase camera at about 40 km/h on Loose;
     - `Spray_Gravel_Launch.png`: side view, a full-throttle launch from a standstill on Loose;
     - `Spray_Gravel_Wet.png`: the same drive at wetness 1, with no dust.
   - Also report the live counts per emitter at each capture, from the Niagara component's particle counts.
8. **Docs and commit.**
   - Docs: the next free VEHICLE_BUILD_SYSTEM section at commit time, the devlog, BACKLOG, a Done note here, and the
     owner's test list (gt.Spray.Art / Fine / FineScale, the rates, `stat Niagara`).
   - Commit "Wheel spray P1-P2: painterly mud and gravel spray (Niagara droplets, grit, dust; clump-drawn mud blobs)",
     hunk by hunk. P1's script and exports go in it.
