# Mackenzie ford colour study

2026-10-06. Exploratory Blender material and sky comparisons in `Art/Export/LevelPalette/palette-01`.

## Recommended direction: straw and sage

Use warm, dry straw as the dominant land colour; reserve greener foliage for the river corridor. Keep the gravel and stones restrained, with dark earthy brown wet mud. Use cooler, lighter distant hills and blue-green water to balance the land. The water is a small accent, rather than a colour applied to nearby rocks.

The user's lakeside willow photograph is the primary visual reference. The regional tourism authority also identifies golden grasslands and turquoise glacial lakes as characteristic of the Mackenzie landscape: https://www.mackenzienz.com/. A shallow ford should not automatically inherit the opaque turquoise appearance of a glacial lake.

## Comparison

- `current`: existing source-scene materials, with the approved new willow meshes substituted.
- `natural`: straw and sage; warmer grass, neutral stone, earthy mud and lighter blue distant hills. Recommended starting point.
- `golden`: stronger gold/blue-green contrast. More overt stylisation, with a greater risk of making the entire bank yellow.
- `muted`: quieter olive/beige ground and cooler stone. A softer option, with less of the dry high-country impression.

Each has an editable `.blend` and matching `.jpg`. All use the same six willow placements, new broad/young willow geometry, camera, sun, ambient fill, exposure, AgX transform and render settings. Only the tested materials, hill emission and camera-visible sky vary. New willow foliage and bark are held constant. The original source scene and Unreal level have not been overwritten or imported.

`Art/Blender/build_level_palette_study.py` rebuilds all four. `-- --skip-current` rebuilds the three alternatives. `palettes.json` stores Blender linear RGB values, not display hex values. The ground study retains original texture luminance and UV biome/wet masks while remapping colour; this is an art-direction experiment, not an engine-ready replacement shader.

## What still needs development

The studies resolve colour relationships only. The distant ridge remains one simple backdrop with limited spatial depth, and the water remains a static opaque placeholder. Layered terrain, atmospheric separation and more convincing water will be needed for a finished scene. Review a brighter, less heavy lighting treatment after selecting the palette; do not brighten every material to compensate for lighting.

For engine implementation, port material relationships under fixed exposure first, preserve linear vertex-colour handling, and compare driver and overview views in Unreal. Local greener ground near water should follow the wet corridor rather than a global green tint. Keep dark tree trunks as accents and enough value separation for the road to remain readable.

## Validation

Four source scenes rendered successfully in Blender. Visual review covers the final images. The inline comparison checks all four selectors, the monochrome value check and restoring saved selection. These are Blender previews; no Unreal validation is claimed.

## Later direction: grounded and painterly

On 2026-10-07 the user found the Benmore daylight result bland and selected a
grounded painterly direction. The natural straw-and-sage palette remains a
starting relationship; the new treatment also addresses larger colour areas,
cool schist, plant grouping and selective detail. See
`docs/BENMORE_PAINTERLY_STYLE.md` for the concept, implementation and review.
