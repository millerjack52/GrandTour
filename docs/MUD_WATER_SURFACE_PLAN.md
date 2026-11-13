# Mud and water surfaces: too smooth, water too static (MW1)

Main session, 2026-10-11. The owner sent an on-foot screenshot: a first-person view along a water-filled old track,
the sun ahead. Their words: "mud and water are reading way too smooth - the water is too static."

**My read of the screenshot:**
- **The water** is a flat mirror that blows out white with the sky. Nothing moves on it.
  M_GT_MudWater's only motion is a faint ripple normal (RippleCm 6, slope 0.05) drifting at 0.6 cm/s, which is static
  to the eye.
- **The deformed mud** (rut banks and lips) reads like molten plastic: smooth rounded blobs, glossy highlights, and
  flowing folds that look like the rejected "chocolate swirls". Suspects:
  - **the texture slide** (M_GT_Mud `SlideUV` 1.0) drags the bake along with moved mud into smooth folds;
  - **the fresh sheen** (`FreshWet` 0.3);
  - **no crumbly detail** on walls and lips;
  - **field geometry** at 12.5 cm cells, reconstructed bicubic.
- The untouched mud to the right still reads lumpy.

## 0. Rules

`docs/MUDRUNNER_LESSONS_PLAN.md` section 0 holds in full: no timing; run with a game open and name it, never close it;
the look rejections; commit only your hunks; never push.

- **Before every Unreal or UBT run:** run `powershell -NoProfile -File Art/wait_unreal_free.ps1` as its own command,
  and start the run in a separate command only after UNREAL FREE.
- **Another agent (GR2 phase B, ground detail) shares the working tree.** It owns:
  - the strips' setup scripts and `Art/Unreal/ground_relief.py`;
  - the landscape material and its strips instance;
  - the ground scatter;
  - the pre-churn puddle code in GTMudPatch/GTMudField;
  - `check_wheel_spray.py`.
  Don't edit those.
- **MW1 owns:**
  - `Art/Unreal/live_mud_style.py` (M_GT_Mud, M_GT_MudWater);
  - `Source/GrandTourEditor/Private/FX/GTNiagaraSetupLibrary.*`;
  - `Source/GrandTour/Vehicle/GTSprayArt.cpp`;
  - new files.
- **Shared tree:** if a build fails in a file you didn't touch, the other agent is mid-edit. Wait (re-check every
  5 min, up to 45 min) and don't edit its files.
- **Off limits:** water simulation, Benmore and river files, and the Codex app's uncommitted hunks (GTSprayComponent.cpp
  has some).

## MW1

1. **Reproduce and diagnose first.**
   - Find a spot that matches the owner's shot: a water-filled old track (GR1c puddle) on L_MudVariants (Deep or
     Standard) or L_MudDrive. On foot, 1.6 m eye height, looking along the track with the sun 30-45° ahead of the
     view, so the grazing glare case shows.
   - Capture `MW_Before_OnFoot.png` there before any change.
   - Debug set at the same frame:
     - SlideUV 0;
     - FreshWet 0;
     - gt.Mud.POM 0;
     - the rut water hidden;
     - the roughness and normal buffer views.
   - Report which term makes the molten and swirl look, with the pixel-diff numbers.
2. **Mud (M_GT_Mud):**
   a. **Slide:** SlideUV 1.0 → 0.35, unless the debug shows the slide isn't the swirl source; then report and keep
      it.
   b. **Deformation detail.** A crisp, non-sliding detail overlay: the variant slice's normal and ORH AO at 2.6×
      tiling, turned 29°, in the field-normal frame so it holds on walls.
      - Its strength is the max of the worked mask (moved cells: the tracks or Fresh history) and smoothstep(12°, 25°,
        slope), times 0.8.
      - Switch: `gt.Mud.DeformDetail` 0/1.
   c. **Sheen:** FreshWet 0.3 → 0.12.
   d. **Broken highlights:** on wet mud outside water, roughness gets ± a noise of two octaves at 8 and 25 cm, ±0.08,
      and the floor goes from 0.45 to 0.5.
3. **Water (M_GT_MudWater, plus rings):**
   a. **Wind ruffle.**
      - Two ripple octaves at 25 cm and 11 cm, slopes 0.12 and 0.08, drifting 10 and 16 cm/s along the wind (read
        MPC_Weather's wind if it exists, else a fixed direction plus a slow wander).
      - A gust mask (cat's paws): a 2.5 m noise drifting with the wind, ×0.3-×1.6, so ruffled and calm patches move
        across the water.
      - Shallow edges (under 2 cm) are calmer, ×0.4.
   b. **Roughness:** settled water 0.15 → 0.2 base, ruffled patches up to 0.3. Churned water stays as it is. F0 stays
      0.02.
   c. **Drift.** The froth and turbidity pattern and a sparse fleck layer (straw bits, bubbles: dark and light 2-6 mm
      specks, density with turbidity) advect at 3-6 cm/s along the track's downhill direction. Take that from the
      field height's gradient in the material, or the patch's route axis if the gradient is flat.
   d. **Rings.** A new Niagara emitter, WaterRings (in NS_GT_WheelSpray or its own system, through the setup library
      and its guard):
      - flat ring sprites on the water surface, spawned where a wheel moves in rut water (depth at the contact over
        1 cm), at 1-6 rings/s per wheel with speed, and at each on-foot footstep in water (find the character's step
        hook, or a 0.45 s cadence while moving in water);
      - each ring expands 0.1 → 1.2 m over 1.2-2 s and fades out;
      - a painterly ring atlas (headless Blender, 2×2 soft painted rings, irregular);
      - translucent, depth-tested.
      - Switch: `gt.Mud.WaterRings` 0/1.
   e. **Rain rings:** if the weather has rain ripples on other surfaces, apply them to rut water too. Report.
   f. Switch: `gt.Mud.WaterMotion` 0/1 (0 = today's water).
4. **Gates:**
   - **Motion:** a fixed camera on the water, two frames 0.5 s apart (game time). The mean absolute luminance change
     in the water mask is ≥ 2/255, and ≥ 15 % of the water pixels change by more than 4/255. Report gt.Mud.WaterMotion
     0 against 1.
   - **Glare:** in the owner-view frame, water pixels at luminance > 0.95 are ≤ 5 % (report before and after).
   - **Mud PBR:** wet deformed mud outside water has a roughness p5 ≥ 0.5 (the PBR sampler). Base colour stays inside
     the soil band.
   - **Regression:** every Mud, Snow, Gravel, Spray and Relief test passes; CRCs unchanged.
5. **Pictures** (a new `Art/Unreal/check_mud_water.py` that follows CHECKS_UNDER_GAME_PLAN, with continuous rendering
   for the motion frames):
   - `MW_Before_OnFoot.png` and `MW_After_OnFoot.png` (the same frame);
   - `MW_Water_t0.png`, `MW_Water_t05.png`, `MW_Water_t10.png`;
   - `MW_Rings.png` (the car driving through a puddle at about 10 km/h, side view, sun behind the camera);
   - `MW_Mud_Close.png` (a deformed bank at 2 m);
   - the debug set.
6. **Docs and commit.**
   - Docs: MUD_VARIANTS.md (the switch table), VEHICLE_BUILD_SYSTEM (the next free section at commit time), the
     devlog, BACKLOG, and a Done note here.
   - Commit "Mud and water MW1: crisp deformed mud, moving rut water, rings".

*Done 2026-10-12 (VEHICLE_BUILD_SYSTEM 106; GoWR open for the after check and the tests). Item 1: on Deep's old-track puddle
(2.3 cm) and a fresh Deep bank, the parallax is the term that changes the walls (gt.Mud.POM 0: 9.9 / 9.6 of 255 against the same
frame; SlideUV 0: 1.05 / 0.54 and FreshWet 0: 1.10 / 0.58, the capture floor 0.49-0.71), so SlideUV stays 1.0 (2a's condition) and
POM is unchanged (not in the plan). Items 2b-d, 3a-c and 3f built in Art/Unreal/live_mud_style.py; 3d: NS_GT_WaterRings and
UGTMudWaterSubsystem (wheels from the traction component's rut water, 1-6 rings/s; footsteps on a 0.45 s cadence - the character
has no step event; GTSprayArt.cpp untouched, it carries the Codex app's hunks); 3e: no rain ripples exist on other surfaces, none
added. Gates: motion on the puddle PASS (2.29 / 2.26 of 255, 18.4 / 19.6 % over 4/255; WaterMotion 0: 0.36, 0 %), on the car's
fresh churned pool FAIL (0.92 / 1.06, 1.7 / 3.0 %: opaque slurry at roughness 0.5); glare 0 % before and after (the blow-out did not
reproduce at this frame); wet mud roughness p5 0.451 -> 0.498 (the 0.5 floor, one 8-bit step under), base colour unchanged (0.0318 /
0.0220, under the 0.0325 band floor before and after on Deep's slice); 22 Mud/Snow/Gravel/Spray/Relief tests Success, CRCs as
e68eb79. The rings frame is at 1.7 km/h (Deep bogs the car), no ring alive at it; MW_Rings_Test shows the rings render (4,067 water
pixels changed). Open: the owner's look; a 10 km/h rings frame on firmer puddles; the fresh-pool motion.*

## MW1b (the main session, 2026-10-12, after its look at MW1)

No parallax on deformed mud; the mud matte toward a low sun (dry 0.8-0.95, wet 0.62-0.8, floor 0.62, specular occlusion from the
AO; mud glare gate <= 3 % over 0.9); Deep softened (normal, AO and parallax x0.5); the churned pool's swirls found and removed;
churned water ripples at 0.15; the rings frame on a Standard or Firm puddle at about 10 km/h with rings alive.

*Done 2026-10-12 (VEHICLE_BUILD_SYSTEM 107; GoWR open; tests: one run before the owner's "dont worry about test runs", 22 Success,
CRCs unchanged; none after). Walls POM on/off 11.18 -> 0.69 of 255 (PASS); mud over 0.9: 10.3 % -> 0.0 % (PASS); wet roughness p5
0.498 -> 0.639, dry 0.455 -> 0.800; the swirls were the per-pixel drift (it warped the froth and the mottle into arcs) and the ruffle's
crests stretched across the wind (long diagonal bands) - now one drift direction per patch and an isotropic ruffle; puddle motion
2.07 / 2.39, 19 / 22 % (PASS); the fresh pool's 0.65 / 0.82, 0.9 / 1.8 % (FAIL); rings frame on Firm at 7.1 km/h, 1 ring alive. Deep's
ring blisters still visible, fainter, in MW_After_OnFoot: a rebake is the owner's call. The Python restore of a patch instance's
scalar did not take (106's owner-frame SlideUV / FreshWet rows are unreliable); those toggles now run last.*
