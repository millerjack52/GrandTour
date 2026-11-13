# Grand Tour: richer visuals with controlled frame cost

8 November 2026. Implementation plan requested by the owner, using the Ocarina of Time remake as a technical reference. Planning only: no renderer, assets, maps, physics or quality presets changed in this pass. Evidence below comes from inspected source/configuration and existing reports; no fresh runtime benchmark or visual review was performed.

## Direction

Make Grand Tour's materials, lighting, vegetation and environmental response more convincing while improving frame consistency. Preserve the colourful woodland direction, Waimeamea reference ecology and established vehicle forms. Zelda supplies examples of presentation and resource allocation; it does not replace Grand Tour's art direction.

Start in the existing L_LidarStudy riverbank/forest reach, with the access road, ford and open paddock as control scenes. Extend successful methods to the rest of the map and then other Grand Tour maps. Keep the original driving route and terrain layout.

The existing 120 fps objective remains open. Proposed intermediate milestone: a visually accepted 60 fps route on the current RTX 4050 Laptop 6 GB profile. This is a planning milestone, not an instruction to change the current 120 fps cap or abandon the longer-term objective. Switch 2 compatibility is not a target established by this request.

## Evidence and constraints

- `GrandTour.uproject` targets UE 5.8. `Config/DefaultEngine.ini` selects Lumen GI/reflections, virtual shadow maps, Substrate and ray-tracing support, with static lighting disabled. Runtime overrides must be captured before attributing cost to a feature.
- `Art/lidar_performance.json` v6 specifies 1600 x 900 output, TSR at 75% (nominal 1200 x 675 internal), dynamic resolution disabled and a 120 fps cap. `GTLidarPerformanceSubsystem` applies this to L_LidarStudy and restores settings afterwards. The preset notes contain historical measurement limitations; newer reports must be tied to their own asset revisions.
- Clean authored surfaces and fixed exposure are the current direction. Full-screen banding, stroke warp and Kuwahara are disabled; volumetric clouds are also disabled by owner preference.
- November 6's perceived-detail trial added normal detail, one fern variant and 48 tree variants. Its combined +1 ms median GPU gate did not pass. Do not restart it as if none of the work exists or expand it as a proven solution.
- Extending conventional tree geometry farther cost approximately 9-10 ms in the broad trial, and up to 3.62 ms in the smaller trial. Both were rejected; the saved atmosphere result retained the previous tree ranges.
- Restoring shadows on shrubs and bank plants corrected missing grounding, with a single-pair GPU increase around 3-4 ms in several bank views. This is a priority for attribution, not justification for removing all plant shadows again.
- The fern-floor layer's single warmed comparison was approximately cost-neutral, but several resulting bank views still measured about 21-22 ms GPU. Cheap incremental detail does not establish a fast scene. These historical offscreen results are not current full-route performance.
- The previous PF120 pass was visually rejected for a cheap/flat appearance. Preserve the restored image quality while testing targeted improvements.

Primary local records: [current place log](LIDAR_PLACE_PLAN.md), [reference style](LIDAR_REFERENCE_STYLE.md), [perceived-detail research](LIDAR_PERCEIVED_DETAIL_RESEARCH.txt), [riverbank acceptance](LIDAR_RIVERBANK_ACCEPTANCE.txt), [vehicle style](VEHICLE_STYLE_AND_MODULAR_PARTS_PLAN.md). Existing acceptance remains specific to the version and subject actually reviewed.

## What to transfer from Zelda

| Observed principle | Grand Tour implementation direction |
| --- | --- |
| Distinct materials and convincing indirect light | Coherent roughness, normal and contact detail on existing assets; retain and tune the existing lighting system through measured experiments. |
| Strong depth and atmosphere | Preserve foreground contrast and layered forest silhouettes; use the installed height haze and local fog selectively. |
| Responsive foliage, water and atmospheric details | Extend existing nearby interactions through shared fields, bounded pools and event-driven work. |
| Detail scaled to available rendering capacity | Better near/mid/far representations, selective shadow participation and validated resolution profiles. |
| Consistent frame delivery | Profile CPU, GPU, memory and traversal stalls together, with a repeatable route. |

Digital Foundry's observations do not disclose Nintendo's complete implementation. Baked GI, a particular occlusion algorithm, engine lineage and internal scheduling must not be described as confirmed Nintendo techniques here. The Unreal choices below are proposals for Grand Tour. In particular, do not add baked lightmaps under the current Lumen configuration: Epic documents that Lumen disables their contribution. Surface-detail/AO baking is a separate technique.

## Ordered implementation stages

### VP0 - Establish the actual baseline

1. Record source state, asset hashes, active experimental variants, map revision, resolved CVars, build type, output/internal resolution and GPU power/temperature/clocks.
2. Include the installed physical relief, shrub shadows, fern floor and global TSR thin-geometry setting in that inventory. `select_perceived_variant.py` does not restore the entire map or global config.
3. Reuse fixed B01-B05 riverbank poses and existing D/F/G/T comparison views. Add a repeatable route covering access, wooded bank, ford, open paddock, cockpit and exterior camera; include lateral movement, approach/recede, camera reversal and water/spray activity.
4. Reuse `Art/profile_lidar_play.ps1`, `Art/tools/measure_perceived_detail.py` and `GTPerfProbe`. Confirm their windows exclude screenshots and setup, and that the moving test actually travels the intended route. Collect an uncapped diagnostic separately from paced presentation tests.
5. Measure at least three alternating warmed A/B pairs for changes, plus a separately labelled first traversal and a multi-minute steady drive. Use standalone for development attribution and a packaged build for release verification. Honour the existing Unreal reservation and never terminate an owner's process.

Deliverable: baseline manifest, raw CSV/Insights traces, pass timings, memory residency and matched unretouched game captures. A failed or thermally incomparable run remains labelled invalid/inconclusive.

### VP1 - Recover frame time without flattening the scene

First implementation priority, before adding heavier visual effects.

- Isolate bank/shrub shadow work: shadow depth, VSM page updates and invalidation, foliage deformation, material masking and Lumen membership. Test nearby full shadows plus cheaper distant shadow representation, retaining visible ground anchoring and crown depth.
- Compare a simpler shadow-only proxy on one representative plant group. Check silhouette, detached shadows, backlighting, wind and transitions; reject a cheaper proxy that visibly disagrees with the plants.
- Inspect existing spray/rain/instance update and parked-vehicle work against current source. Earlier Benmore audit recommendations are hypotheses until verified; do not reapply already completed fixes.
- Identify masked overdraw, avoidable component churn, CPU spikes and memory pressure from the baseline. Make one attributable change at a time. Texture/pool cuts need residency and traversal evidence, not just a lower allocation number.

Gate: repeatable reduction in the currently limiting work, with approved-looking plant grounding preserved and no increased hitches. The first goal is to bring the measured bank cost toward the 16.7 ms frame budget; no savings are promised in advance.

### VP2 - Improve material depth at gameplay distance

- Continue the existing 4 x 4 m ground patch and fern study. Separate their costs from the tree experiment before deciding what to retain.
- Bake coherent normals, roughness and local occlusion from the actual source forms. Keep authored colour clean, preserve material scale, and avoid treating dark pigment as geometric depth.
- Keep real geometry where roots, stones and leaf edges change silhouettes. Use normal detail for small surface structure. Retain the fitted fern-floor layer as a candidate, with bake invalidation whenever planting or the bank changes.
- Trial material AO without duplicating excessive darkness already supplied by Lumen, contact shading and the floor bake. Preserve readable damp soil, moss, gravel and leaf surfaces in sun and shade.
- Only test short-range parallax if normal detail fails a specific close-view requirement. Reuse the research's distance/angle fades and steep-bank projection considerations; full-bank iterative triplanar POM is not the default.

Gate: visible gain in normal gameplay framing and motion at the same TSR75 baseline, without sliding textures, crushed shadows or extra collision changes. Record each feature's incremental CPU/GPU/memory cost.

### VP3 - Give distant forest better volume per millisecond

- Compare the same approved beech source and placements using current crossed cards, a view-dependent depth impostor, and the existing bounded Nanite/voxel candidate.
- Begin with the existing 48-tree stand. Measure in the actual forest view, not only a single isolated tree. Include depth/base passes, shadows, atlas residency, animation and transition costs.
- Use full-sphere coverage or retain geometry where trees can be viewed from below. Preserve near/far colour, species form and density through transitions.
- Investigate Epic's Impostor Baker as a contained candidate; the current six-triangle cards are already very cheap geometrically, so more advanced impostors are not automatically faster.
- Treat UE 5.8 Nanite Foliage as experimental. Check actual feature/asset use, material flags and vertex-data contracts; `r.Nanite.AllowVoxels=1` alone is not proof of a complete foliage pipeline.

Gate: fewer flat-card turns, stable crown volume and no conspicuous transition flash, with measured total cost acceptable in the representative stand. Choose a winner before increasing tree coverage. Do not extend ordinary LOD ranges again without new evidence.

### VP4 - Make local interaction convincing and bounded

- Audit existing wind, grass bending/removal, soil deformation, water disturbance and wheel spray before adding systems.
- Keep contact response around the player/active car in a bounded shared field or instance update region. Far vegetation receives cheaper ambient motion; cosmetic debris uses capped pools and deactivates when idle.
- Reuse existing water/terrain ownership and dirty-region updates. Dust, spray and vegetation response should communicate speed, contact and surface type without obscuring the driving line.
- Keep decorative detail separate from physics collision and traction. Preserve suspension, steering, tyre response, water drag and tuned driving values.

Gate: clear response during driving, walking and stopping; no stale trails, pool overflow, per-plant ticking or material ground detachment. Run relevant existing vegetation, spray, water and surface regressions when those systems change.

### VP5 - Add atmosphere only where it helps composition

- Start with the saved height haze and two local fog volumes. Review across-river layers, sunlit/shaded bank separation and road visibility at unchanged exposure.
- Prototype reactive ground mist in one authored pocket only if its visual role is useful after VP1-VP4. Compare a cheap local approximation with any simulated version and bound screen coverage, update frequency and active count.
- Check fog/transparency overdraw with vegetation and spray together. Keep volumetric clouds disabled. Do not hide weak distant geometry by making all views opaque with fog.

Gate: improved depth and readable traversal, with cost fitting the recovered budget. Reactive mist is optional and comes after materials, shadows and forest representations.

### VP6 - Carry the material language onto the vehicle

- Use the existing selected car and cockpit, retaining approved proportions and fitted components.
- Separate paint, rubber, glass, bare metal, cloth and wet dirt through measured material response. Review bonnet highlights, window readability, tyre contact and cockpit shading from actual gameplay cameras.
- Allocate geometry to visible panel profiles, lamp recesses and wheel shapes; bake small detail where it survives reconstruction better. Check material-slot/draw costs as well as triangle counts.
- Validate LOD transitions, doors, steering/suspension clearance, cockpit visibility and weather response. Preserve editable source assemblies and manual edits.

Gate: vehicle and environment belong to the same visual world in clear/overcast/wet conditions, without losing accepted shape or mechanical behaviour.

### VP7 - Stabilize reconstruction, package and roll out

- Keep TSR75 fixed through earlier comparisons. Isolate the existing thin-geometry detection setting and inspect foliage stability during camera movement, wind and disocclusion.
- Test alternative reconstruction/resolution choices only as a separate quality experiment. Any dynamic-resolution trial requires verifying support in the installed engine/target, a defined quality floor, and real runtime changes. It cannot solve CPU stalls or memory eviction.
- Capture shader/PSO first-use and streaming hitches in a cooked/package run. Resolve their actual causes with engine-supported preparation and bounded loading work; avoid masking them with average FPS.
- Promote winning recipes into Prepare/Install/Polish rebuild hooks. Include dependency hashes for static bakes, asset backups and rollback manifests. Prove an end-to-end rebuild in an isolated copy before relying on it.
- Expand to one additional representative reach, then the route and other maps. Keep failed candidates and reasons in the evidence log.

Gate: repeatable build, visual comparisons, full-route timing, memory soak and regression checks at the declared hardware/profile. Technical passes and owner visual acceptance remain separate results.

## Performance and acceptance contract

Proposed gates, to be checked against VP0; not measurements or achieved guarantees:

- Intermediate quality milestone: uncapped full-frame p95 at or below approximately 16.7 ms on the defined route, with p99, maximum and every hitch over 33.3 ms reported. Also verify a paced 60 Hz run; a percentile alone does not prove locked 60 fps.
- Longer-term target: 8.33 ms frame budget for 120 fps at an explicitly stated quality/output profile. Do not remove approved visual qualities just to report the cap as achieved.
- CPU and GPU overlap; do not sum their totals into a fictitious frame budget. Attribute the limiting path from traces.
- Recover headroom before promoting additions. Retain the earlier proposed +1 ms combined visual-cost ceiling as an experimental upper bound, not permission to add 1 ms to already slow views. The overall route budget takes precedence.
- Stay within the runtime-reported available video-memory budget, with a proposed 10% reserve during traversal. Physical 6 GB capacity is not the available application budget. Report pools, residency, evictions and peak use together.
- Match cameras, route, weather, exposure and resolution for A/B. Record thermal variance and avoid treating tiny single-pair differences as wins. Review actual frames and native-rate motion; existing 12 fps review clips do not demonstrate frame pacing.
- Check terrain/plant-placement hashes, roots/fronds, water boundaries and gameplay as appropriate. A visual feature cannot silently change driving physics or replace the established photo/vehicle references.

Each stage delivers: change and rationale, before/after media, measured costs and uncertainty, acceptance/remaining issues, touched assets/source and precise rollback. Initial execution order is VP0 -> VP1 -> VP2 -> VP3, then bounded interaction/atmosphere/vehicle work within the measured budget, followed by VP7 rollout.

## Sources

- Nintendo, [Ask the Developer, Ocarina of Time, Part 2](https://www.nintendo.com/us/whatsnew/ask-the-developer-vol-24-the-legend-of-zelda-ocarina-of-time-part-2/): artistic intent and world structure.
- Digital Foundry, [Switch 2 technical review](https://www.youtube.com/watch?v=j5sfIbuCOqI): observed materials, atmosphere, interaction and scaling; consulted through its [hosted transcript](https://tubesum.app/v/the-legend-of-zelda-ocarina-of-time-2026-switch-2-df-tech-review), with transcription uncertainty. Not Nintendo source code.
- Epic, [Lumen GI and reflections](https://dev.epicgames.com/documentation/unreal-engine/lumen-global-illumination-and-reflections-in-unreal-engine): current lighting integration and static-lighting constraints.
- Epic, [Impostor Baker](https://dev.epicgames.com/documentation/unreal-engine/impostor-baker-plugin-in-unreal-engine): view-dependent proxies and trade-offs.
- Epic, [Nanite Foliage](https://dev.epicgames.com/documentation/unreal-engine/nanite-foliage): experimental assembly/voxel/skinning pipeline.
- Epic, [TSR thin geometry detection](https://dev.epicgames.com/documentation/unreal-engine/thin-geometry-detection-with-temporal-super-resolution): temporal stability for subpixel detail.

External documentation checked 8 November 2026. Implementation must verify APIs/settings against the installed UE 5.8 source before changing them.

## Implementation status: 8 November 2026

At the owner's request, implementation started with the bounded VP2 riverbank materials and plant shading pass. Five materials are installed; Unreal installation, protected-file checks and plant-placement snapshots passed. The final visual comparison and performance validation are pending because Skate was sharing the GPU, and the owner chose to defer performance testing. No measured improvement or stage acceptance is claimed. See [Riverbank material polish](RIVERBANK_MATERIAL_POLISH.md) for changes, evidence, rebuild and rollback instructions.
