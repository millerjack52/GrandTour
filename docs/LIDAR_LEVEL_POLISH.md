# LP6: production-level polish

The owner's photographs lead the appearance. Work stays in L_LidarStudy. The
existing dirty main checkout and original LiDAR inputs are retained.

## Separate failures and their solutions

1. **Water coverage.** The transferred ChannelPilot graph disabled local water
   inside the baked river and applied a second immutable shore mask. A displaced
   static mesh cannot cover newly excavated space beyond its original triangles.
   Replace that local/static ownership rule. A bounded authored shoreline envelope
   supplies mean level/current; the final ground and native soil displacement
   determine occupancy. Keep the existing 96-square river window, disturbance
   history and wake effects. Closed mud basins retain their finite water volume.
   Refresh the reference only when nearby soil changes; shade the shoreline from
   cached ground heights plus the same published soil texture used by terrain.
   The margin is 2.5 m, deliberately not an unlimited flood simulation.

2. **Floating vegetation.** Saved pre-build elevations and padded tree-card bounds
   are inappropriate root references. Seat living plants by their ground pivot
   against final relief tiles, falling back to the landscape. Use source kit bounds
   for tree sizing. Slope-align low debris and check its footprint. Reapply after
   future terrain builds, with batched instance updates and no per-plant tick.

3. **Foliage at distance.** Straight-up card normals and missing crown shading make
   distant trees uniformly bright. Give existing baked cards rounded crown normals
   and self-shading; retain their species texture and cheap geometry. Delay overly
   aggressive LOD changes locally, without altering the global performance preset.
   The existing curved fern geometry should remain visible farther from the camera.
   Assess silhouettes, colour and transition from the actual river and across it.
   A map-owned two-sided foliage material retains the kit colours, adds restrained
   transmitted light, and blends 18% rounded plant normals into the existing frond
   normals. This improves lighting volume without replacing the native plant kit.

4. **Sparse river dressing.** Add deterministic nested cobble patches around the
   authored photo-reach bed clusters, retaining gaps and the driving crossings.
   Batch by spatial cell, mesh and collision class. Small detail has no collision or
   shadows and fades at 25-45 m. Existing large boulders/wood keep their physics.
   GTGroundedDressing binds cosmetic instances to native terrain displacement once
   at BeginPlay; shared material deformation avoids individual actor updates.

## Repeatable installation and validation

- `Art/run_lidar_polish.ps1 -Mode audit|install|check|coverage|foliage`, guarded by the existing
  Unreal slot policy. Install backs up LiDAR content before modifying assets.
- Existing Install/Polish reapply LP6 after generation once its manifest exists.
- Check sampled roots after reload, river continuity, a dry shoreline excavated
  into connected water, and existing water/closed-basin regression tests.
- Capture walking-height ford, gravel bar, rocky shallows, opened river rut and
  distant forest directly in the map. No separate showcase section.
- Compare four matched on-foot standalone views using the saved 1600x900 TSR75
  profile. Record frame/GPU/game-thread timing, including spikes. These windows
  cannot establish whole-route or display-presentation performance.
- Record actual results separately. Owner drive and visual approval remain open.

Evidence directory: `Saved/LidarAuthoringQA/LP6`.

## Installed geometry and budgets

- Final-bed river coverage is baked at 1 m spacing, 192,028 triangles versus the
  former 189,058. Coverage metadata includes the domain hash, final ground digest
  and algorithm version; reimporting the original river invalidates that cache.
- River detail now contains 12,242 instances in 99 components, with 61 solid
  instances. The S/M cobble layer uses 16 live-ground groups, no collision and no
  shadows. Its useful mesh scale is 0.65-1.25, seated by the kit's ground pivot;
  178 steep placements were rejected. This density is limited to the photo reach.
- Existing large rocks, roots, moss, wood and clearance around crossings remain.
  Small detail fades from 25 to 45 m; the shared surface texture carries its broad
  appearance farther away. Density does not mean a physics body for every pebble.
- River soil refresh remains 96 x 96 cells and is dirty-region driven, capped at
  10 Hz. Closed mud basins retain their existing finite-volume solver and tests.
- A moving capture exposed an unrelated first-use stall in the existing native
  mud-water material draw. Setup now allocates one cosmetic buffer per frame.
  In editor/standalone builds, pending material shaders are submitted asynchronously
  and drawing waits for readiness; the ordinary water and physics continue. The
  first repeated ford pass waited five frames, then resumed draws below 0.14 ms
  rather than blocking for 85-105 ms. The one-active-basin budget is unchanged.
- Final ground output digest remains DB443C52AD8AD4F3A1E2CD57E8E4716F.

Recorded checks and performance are in `Saved/LidarAuthoringQA/LP6/result.json`
when the final validation pass is complete. Earlier failed harness attempts are
retained as evidence and are not counted as successful checks.

## Final verification - 2026-10-20

Build7 and all seven water regressions passed. The saved-map check sampled 3,198
plant roots with zero seating error and verified all 16 live-ground stone groups.
Four separate native soil strokes lowered an initially dry river edge by 2.25 cm;
its runtime water depth became 1.32 cm. The editor exited normally.

Final stationary captures averaged 59.9-60.0 FPS, p95 16.673-16.681 ms; an isolated
42.524 ms frame remains. Four moving captures travelled about 49 m each and
averaged 60.0 FPS, p95 16.675-16.682 ms, worst 18.354 ms. These use the saved
1600x900 TSR75 preset, offscreen standalone. Owner visual/drive approval and
whole-route/presentation performance remain unverified. Detailed before/after
CPU/GPU numbers and failed intermediate experiments are retained in the stage
log and LP6 evidence directory. Sources and saved assets remain uncommitted.
