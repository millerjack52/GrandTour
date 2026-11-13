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
