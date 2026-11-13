# Benmore gravel parallax

The driving map's `M_Benmore_FullCover` now adds close-range parallax occlusion mapping to the existing compact and loose gravel layers. The road layout, terrain heights, tyre collision and tussock meshes are unchanged.

The height sources are the matching 2K, 16-bit PNG displacement maps for Poly Haven's Gravel Floor 04 (fine/compact) and Gravel Floor 02 (loose). Original files and API MD5 verification are retained in `Art/Textures/RoadBenchmark/pom-download-manifest.json`. Both assets use the existing CC0 source attribution. Imported height textures are linear grayscale with mipmaps; the source PNGs remain unmodified.

## Material behaviour

- A single view-ray march samples and blends both height fields using the existing road-relative wheel-path, centre and shoulder weights. All four gravel colour/normal samples use the resulting UVs, keeping their detail aligned.
- Loose gravel repeats over 8 m, doubling its stone size from the initial 4 m material in response to the user's driving-readability feedback. Compact gravel retains its 4 m repeat. Both matching normal and height maps use their layer's scale.
- Maximum height ranges are 0.8 cm for compact gravel and 4 cm for loose gravel. Actual visible relief also depends on the source map's height range and the surface blend.
- Full effect within 15 m, smoothly fading to zero by 30 m. A dynamic branch skips height sampling outside the near road surface. There is also a grazing-angle fade to limit streaking.
- 12–28 ray steps depending on view angle, with linear refinement at the intersection. Explicit original-UV derivatives control height, colour and normal mip selection.
- The world-XY projection matches the existing textures; the view ray accounts for the terrain's underlying slope.
- Pixel Depth Offset is deliberately disabled for this initial pass. POM changes apparent surface relief; it does not provide displaced shadow geometry, exterior silhouettes or collision. Larger stones remain mesh instances.
- `ReferenceSurface/MPC_Benmore_GravelPOM` has scalar `Enabled`, default 1. Setting it to 0 through Python's `MaterialLibrary` gives a same-session normal-only comparison without editing shared project settings.

Grass and distant hillside shading retain their existing treatment. Flat grass litter could receive a separate shallow-height treatment later; upright blades and tussock silhouettes remain geometry.

## Rebuild and verification

1. Run `Art/tools/prepare_benmore_pom.py` with the terrain Python environment to fetch and verify the two matching source maps.
2. Run `Art/Unreal/setup_benmore_pom.py` in Unreal Editor to import the heights, create the control collection, rebuild and save the map's material.
3. Run `Art/Unreal/check_benmore_pom.py` to reload the saved map, compare POM on/off at detail, driver and hillside cameras, and capture a moving camera pass at 5 m/s.

The material builder integration is in `benmore_reference_surface.py` and `benmore_gravel_pom.py`. Subsequent ground-detail rebuilds retain POM when the height assets exist. A pre-POM material backup is saved as `ReferenceSurface/M_Benmore_BeforePOM`.

Reports and captures live in `Art/Export/BenmorePOM`. Editor frame intervals are a comparative check at the reported viewport size, not a packaged-game GPU benchmark. Still captures from motion cannot certify absence of temporal shimmer at every speed or display resolution.

Final saved-map checks on 2026-10-07 passed: the POM graph reloaded without shader errors, the control toggled on/off, all four approved grass meshes streamed, and the 5,704 non-colliding gravel instances remained intact. Driver, detail and hillside comparisons plus five camera positions across 40 m were captured. Visual review found no obvious stretching in those captures. The loose gravel now reads larger from driver height.

Performance remains unverified: despite successfully disabling the editor background-throttle setting temporarily, tick inputs stayed capped at 125 ms in both on/off cases. The report explicitly marks the performance comparison invalid. The camera progression was slowed around editor stalls, so it is a spatial/movement capture check rather than proof of full-speed temporal stability. The original editor throttle preference was restored before exit.
