# GrandTour

Unreal Engine 5.8 vehicle and environment project.

This repository contains C++ source, project configuration, Blender/Unreal
authoring tools, launch scripts and development documentation. It follows the
existing source/config-only versioning policy: Unreal Content, purchased asset
libraries, generated art, render dumps, caches and build outputs remain local.
A clone alone is therefore not a complete playable build. Restore the licensed
Content and local art inputs before opening the maps or running asset tools.

## Development

- Open `GrandTour.uproject` with Unreal Engine 5.8 and build the editor target.
- Environment and vehicle authoring scripts live in `Art/Blender`, `Art/Unreal`
  and `Art/tools`; many currently use the development machine's absolute paths.
- Source assets must be acquired separately under their own licences.
- Agent instruction files, agent configuration, credentials and local Python
  environments are not part of the published source snapshot.

## Flora Paint appearance study

See `docs/FLORA_ASSET_MATCH_CHECKPOINT.txt` for the isolated Blender-to-Unreal
comparison, reproduction steps and outstanding limitations. The candidate is
not promoted to LiDAR. Lighting and camera-motion checks do not establish a
whole-map performance result or arbitrary local-light equivalence.

The 13 November 2026 publication is a source checkpoint, including pre-existing
project changes. It is not a release or a claim that every subsystem has been
retested. Test results for this study are recorded explicitly in
`docs/validation/flora-asset-match.json`.

The separate forest-path group study is documented in
`docs/FLORA_GROUP_STUDY.txt`, with lighting cases, dedicated source bark maps
and a saved-map texture audit. Its map and licensed inputs remain local.

The isolated **FloraTrail** driving section combines the approved source foliage conversion with deformable mud, shallow water and Rock Master banks. Run `Drive-FloraTrail.bat`; build, controls and validation are documented in `docs/FLORA_TRAIL.txt`. It leaves the LiDAR and earlier studies unchanged.

FloraTrail's tree coverage and sunlight-response refinement is documented in `docs/FLORA_TRAIL_CANOPY.txt`, including controlled material tests and current saved-map validation.

FloraTrail atmosphere controls and current saved-map visual evidence are documented in `docs/FLORA_TRAIL_ATMOSPHERE.txt`.

The tree colour response refinement and current validation are documented in `docs/FLORA_TREE_COLOUR.txt`.

The same-tree lighting calibration is documented in `docs/FLORA_TREE_LIGHTBENCH.txt`. It uses the purchased project's specified Blender 3.4.1 version. Its approved tree response is installed in FloraTrail; the initial promotion used the comparison's lighting. See `docs/FLORA_TRAIL_SOURCE34.txt` for game-view and driving validation. LiDAR remains unchanged.

FloraTrail's subsequent sunlight correction keeps those tree materials and separates scene daylight from the isolated comparison rig. See `docs/FLORA_TRAIL_SUNLIGHT.txt` and the per-scene `Art/flora_trail_sunlight_settings.json` controls.

The current palette and lighting acceptance target is `docs/FLORA_PALETTE_SUCCESS_CRITERIA.txt`. It analyses the supplied Flora Paint references, identifies remaining visual gaps and defines the review gates before broader LiDAR rollout. This is an art-direction rubric, separate from the passing technical checks.
