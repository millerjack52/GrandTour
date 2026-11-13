# Mackenzie driving blockout

**Current terrain direction:** the user subsequently selected the whole real Benmore shoreline/terrace area below candidate C, approximately 2.24 x 2.40 km. See [Benmore full site](BENMORE_FULL_SITE.md). Keep this original playable blockout as a route-rhythm reference; its fixed road positions and synthetic height queries do not apply to the new geography.

First playable layout, 2026-10-06. This is a route and scale test, before Gaea terrain development or the finished art pass.

## Open and drive

Run `Art/play_mackenzie_blockout.ps1`, or open `/Game/GrandTour/Demo/MackenzieBlockout/L_Mackenzie_Blockout` in Unreal and press Play. The launcher uses the existing car and driving systems, skips loading saved progression, and holds clear weather for this review.

W/S throttle/brake, A/D steering, Space handbrake, C cockpit/chase camera. F exits the car. Console `GTGoto Start`, `GTGoto Ford`, `GTGoto Shortcut`, and `GTGoto Ridge` reset to named locations; `GTGoto list` lists them.

The road leaves the shed/start area, follows the open southern terrain, crosses the eastern ford, and reaches the shortcut junction. Stay on the wider road to climb around the northern/western ridge and return to the shed. The narrower branch crosses the centre and rejoins on the west side. Light marker posts identify the main loop.

## Layout

- Exactly 1000 x 1000 m Landscape, 1009 x 1009 height samples, 64 components.
- Main road: 2350.7 m closed loop, 6.4 m nominal width plus feathered shoulders.
- Optional track: 698.9 m, 4 m nominal width, rougher than the main road.
- Main-route elevation: approximately -2.8 to 42.6 m relative to the map origin.
- Ford: at route distance approximately 569 m, with a nominal 28 cm water level above the lowest bed sample. It uses the existing flowing-water actor; local simulated depth varies. The firm bed has deformation disabled for this layout test.
- Simple shed, roadside markers and signs. Legacy willow meshes are temporary silhouettes at the crossing, not the new finished family.

The terrain is generated from `DA_Mackenzie_Blockout`. `TerrainBuilder` rebuilds it using the existing Grand Tour terrain API. Three authored terrain planes create a broad graded shortcut approach and level transitions at its ends. This explicitly joins the independently generated alternate-road profile to the main road.

## Rebuild and validation

`Art/rebuild_mackenzie_blockout.ps1` backs up this map's content folder into `Saved/MackenzieBackups` before rebuilding. Close this map before rebuilding it. The generator only creates assets in `/Game/GrandTour/Demo/MackenzieBlockout`; existing vehicle tuning, test maps, shared materials and project defaults are not edited.

`Art/check_mackenzie_blockout.ps1` loads the saved map in a separate Unreal process, probes terrain collision across both routes, captures actual game renders and drives representative sections. It writes `Art/Export/MackenzieBlockout/drive-report.json` and PNGs. `Art/Unreal/survey_mackenzie_route.py` checks the entire route centre lines at one-metre intervals, including the closed-loop seam and shortcut join; output is `route-survey.json`. `setup-report.json` contains the actual layout samples and dimensions.

These checks establish loading, collision continuity and representative driveability. They do not establish that every corner is enjoyable at every speed, or provide a performance benchmark. The user accepted this layout as a first pass on 2026-10-06; keep it as the terrain-development baseline.

Validated on the final saved layout: 921 collision probes, no misses, maximum sampled collision/analytic height difference approximately 6.5 cm. Six representative driving runs passed: start, ford, ridge, lower shortcut, shortcut climb and shortcut exit. The centre-line survey sampled 2352 points around the loop and 700 along the shortcut; maximum one-metre sampled grades were 13.8% and 24.5% respectively. The shortcut is the more demanding route. The loop seam changes height by 11.1 cm over the surveyed one-metre interval.

## Review priorities

Judge road width, bend rhythm, sight lines, hill gradients, ford entry/exit and whether the shortcut is worth taking. The ground materials, car presentation, trees, sky and outer map edges are blockout placeholders. Larger terrain cuts and the shape of the river corridor should be redesigned during the next terrain pass after route feedback.

Next, carry the accepted layout into Gaea for the broader landforms and erosion. Keep the route, junction heights and ford as constraints. Reconcile Gaea heights with the project's deterministic terrain sampling before replacing the generated base; importing a heightmap alone does not update the existing gameplay height queries.

The starting heightmap, aligned protection masks and route guide are in `Art/Export/MackenzieGaea/first-pass`. See [Gaea handoff](MACKENZIE_GAEA_HANDOFF.md) for setup and height encoding.
