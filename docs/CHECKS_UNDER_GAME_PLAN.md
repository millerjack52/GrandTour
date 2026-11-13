# Rendered checks that run properly while a game is open

Main session, 2026-10-10. The owner: "make it run whilst gow is running then. Optimise it properly".

**Why the checks crawl under a game** (1-6 fps under GoWR or Ace7Game):
- **Every drive frame is rendered,** although only the pictures need it. GoW holds the GPU, so each frame waits
  behind it.
- **The per-tick GPU wait** (VRAM_SOAK's fix for the residency overflow on camera jumps) runs on every tick. Under a
  game, each tick waits behind the game's own queue.
- **Physics advances by real frame time,** so a slow frame rate changes the drive (clamped deltas), not just its
  speed. Wall-clock limits then time out.

**The fix** (applies to `check_mud_variants.py`, `check_deformable_gravel.py`, `check_live_mud_drive.py`,
`check_wheel_spray.py`, and any other rendered PIE check that drives):

1. **Fixed time step.**
   - Run the editor with UE's fixed time step: `-UseFixedTimeStep -FPS=60`, or the equivalent that takes effect in
     PIE, so every frame advances exactly 1/60 s of game time whatever the real frame rate.
   - Verify it: log the world's delta seconds over 300 frames, all of them 0.01667 ± 1e-4.
   - If the command line doesn't take in editor PIE, set it from Python or C++ (`FApp::SetUseFixedTimeStep`,
     `FApp::SetFixedDeltaTime`) at the start of play, and report which worked.
2. **Game-time limits.** Every drive limit, leg cap and stall timer counts game time. A wall-clock safety cap of
   40 min stays.
3. **No rendering while driving.**
   - In the drive phases, turn scene rendering off for the play viewport (`ShowFlag.Rendering 0`, or the
     viewport's `bDisableWorldRendering`; use what works headless).
   - Before each picture: turn rendering on, wait for warm-up (30 frames, or more if the check already waits longer
     for streaming or shaders), capture, then turn it off again.
   - Anything a gate reads from the GPU (the PBR sampler, buffer dumps, pictures, Niagara counts) happens only inside
     those rendered windows.
   - Check that no gate reads GPU state during driving. The gameplay mirrors are CPU-side (the track paint's CPU grid,
     the mud field, the spray pools). Report any gate that had to move.
4. **GPU wait only while rendering.** VRAM_SOAK's per-tick readback runs only in the rendered windows. With no
   rendering there is nothing to pile up.
5. **Correctness against today.**
   - Each check's gates still pass, run without a game.
   - Section speeds move less than 5 % against the committed baselines; fixed dt may shift them slightly.
   - Then run each check with a game open: it must complete with the same gates.
   - The baselines are re-based to the fixed-step run.
6. **Report.**
   - The check's wall-clock duration and frame rate, with and without the game, as a pipeline measure only. This is
     tooling, not game performance: no game frame-time or cost numbers.
   - The delta-seconds verification.
   - The gate results.

Switch for the owner: `GT_CHECK_RENDER_ALWAYS=1` restores per-frame rendering, for debugging a drive visually.

*Done 2026-10-10 (VEHICLE_BUILD_SYSTEM 102). Items 1-4 built (Art/Unreal/check_render.py; the four checks and their wrappers). The fixed step takes on the command line in editor Play In Editor: every world delta 0.016667 s over 300 drive frames in all eight fixed-step runs. ShowFlag.Rendering works headless. Item 5: no game - L_MudVariants 362 s, L_GravelDeform 268 s, L_MudDrive 372 s, spray 191 s, all complete; GoWR open - L_MudVariants 1,420 s (it did not finish in 40 min before), L_GravelDeform 392 s, both complete; L_MudDrive and the spray check with a game owed. Speeds: fixed step 5-12 % faster than the real step on the same ground (L_MudVariants 31.95 / 29.19 / 1.73 / 21.86 against 30.04 / 27.66 / 1.55 / 19.81 km/h), over the 5 % asked; with and without GoWR within 3 %. Gates that moved: PBR_CarryWet (fixed: median 0.439 / 0.231 with GoWR; real step 0.451 PASS) and the spray's droplets above the arch (0.099 against 0.452); the spray's muddy splash fails both ways (GR1b's Deep has no rut water). Baselines re-based to the fixed-step no-game runs. Item 6: this note and section 102.*
