# Wet churned mud studies (04_wet, 05_variants)

LM5 phase A / A2 (docs/LIVING_MUD_PLAN.md "LM5" and "LM5 phase A2: no swirls") and LM5b phase A ("LM5b: four
churned-bog variants"), 2026-10-06. Blender art studies and bakes. No Unreal run, no C++, no live material.

- Phase A's swirled churn was rejected by the owner ("the swirls look terrible, like chocolate or something"); it is kept
  whole in `04_wet/BeforeRevision/rev9_swirls_phaseA/`.
- Phase A2 (torn lumps, flat slurry, crumbs on the ruts): the owner, "looks good, but the ruts should be the same color and
  texture as the rest. I want a number of variants for deformable mud." It is `04_wet/` and the `T_MS_Churn*` bakes.
- LM5b: four variants of that churned bog, each painted over the whole mud patch, ruts included: `05_variants/<Variant>/`
  and the `T_MS_Bog<Variant>*` bakes. **Standard is A2, bit for bit.**

The PNGs are not in git; their numbers are in `Art/Export/MudStyleUE/churn-bakes.json` (A2),
`bog-bakes-<Variant>.json` (LM5b) and `bog-standard-vs-a2.json` (the Standard check), all committed.

## Reproduce

Blender 5.1, headless, no add-ons, CPU, four threads (`B` = `"C:/Program Files/Blender Foundation/Blender 5.1/blender.exe"
-b --factory-startup --python-exit-code 1 --python`):

```
B Art/Blender/build_mud_wet_study.py -- variant=Firm          # Standard | Firm | Deep | Stony -> 05_variants/<V>
B Art/Blender/export_mud_wet.py -- variant=Firm               # -> Art/Export/MudStyleUE/T_MS_BogFirm*.png, bog-bakes-Firm.json
B Art/Blender/build_mud_wet_study.py -- variant=Standard coverage=ruts out=05_variants/Standard_A2check
B Art/Blender/check_bog_standard.py                           # Standard against A2 -> bog-standard-vs-a2.json
B Art/Blender/build_mud_wet_study.py -- variant=Standard coverage=ruts out=04_wet renders=a2   # A2 itself
B Art/Blender/export_mud_wet.py                               # A2's bakes, T_MS_Churn*
```

A variant study takes about 8 minutes (fields 15-25 s, then ChurnClose, the mask, Tile3x3, TileClose and the driver
view with the far gloss fade at 40 samples); its bakes about 1.5 minutes. `-- variant=<V> quick` renders small in about
a minute. `coverage=mud` (the default) paints the bog over 03's whole mud patch (its mud mask, 5.5-26 m and out to the
verges); `coverage=ruts` only on the ruts, as A2 did.

## LM5b: the four variants (`05_variants/`)

One generator, one parameter set per variant (`VARIANTS` in `build_mud_wet_study.py`; Standard is A2's numbers, and
its random draws are A2's, so its fields are A2's to the byte). Each variant has its own seed. The three new ones were
tuned in three quick rounds each (kept under `05_variants/<V>/BeforeRevision/quick1-3`):
- quick1: Firm read as a bed of rounded pebbles with dark outlines, Deep as glossy pebbles on near-black, Stony's stones
  as pale, evenly spaced sesame-like specks. Firm, Deep and Stony's lumps now rise out of the mud (a softer profile, a
  broad foot of mud) in nearly its own tone; the dark gaps are shallow and close to the mud's colour.
- quick2: Firm's matte tops looked darker than the semi-glossy mud round them (it reflects the sky), so the lumps read as
  craters; its mud is drier now (0.58-0.72) and the tops lighter. Deep's humps carried bright highlight spots; a little
  more matte. Stony's no-touch rule spaced the stones like a sprinkle; they now cluster into gravel patches and may
  touch, under more mud.

| | Standard | Firm | Deep | Stony |
|---|---|---|---|---|
| lumps | 950, 3.0-15.0 cm (median 7.6), 37.5 % | 2650, 3.0-10.0 cm (median 5.5), 50 % | 350, 5.0-15.0 cm (median 9.7), 18.9 % | 800, 3.0-13.0 cm (median 6.6), 24.7 % |
| crumbs | 1700, 4.2 % | 2500, 6.2 % | 500, 1.2 % | 1300, 3.1 % |
| stones | - | - | - | 1800, 1.2-6.0 cm (median 3.1), 7.6 % visible |
| open mud / wet gaps | 57 % / 1.6 % | 41 % / 3.7 % | 79 % / 0.7 % | 71 % / 1.1 % |
| height range | -0.74..+3.54 cm | -0.30..+2.13 cm | -0.45..+1.75 cm | -0.42..+2.47 cm |
| value (L* x clay) | 0.599 | 0.720 | 0.501 | 0.620 |
| HSV value / saturation x clay | 0.629 / 1.25 | 0.703 / 0.95 | 0.529 / 1.27 | 0.624 / 1.11 |
| roughness: mud 5/50/95 % | 0.22 / 0.30 / 0.38 | 0.58 / 0.64 / 0.72 | 0.15 / 0.22 / 0.28 | 0.22 / 0.33 / 0.58 |
| roughness: lump tops, crumbs | 0.83, 0.83 | 0.88, 0.89 | 0.51, 0.61 | 0.80, 0.80 (stone tops 0.58) |
| seam ratio Color (R/G/B) | 1.08 / 1.09 / 1.11 | 0.95 / 0.99 / 1.00 | 0.85 / 0.83 / 1.00 | 0.82 / 0.78 / 0.76 |
| seam ratio Normal (R/G/B) | 1.07 / 1.11 / 1.03 | 1.02 / 1.02 / 0.97 | 0.98 / 1.06 / 0.96 | 0.93 / 0.85 / 0.94 |
| seam ratio Rough / Height | 1.27 / 1.05 | 0.95 / 0.94 | 0.80 / 0.92 | 0.84 / 0.77 |
| largest edge-step z (any map) | 2.0 | 1.23 | 1.05 | 2.16 |
| coherence colour / height | 0.008 / 0.014 | 0.006 / 0.002 | 0.007 / 0.016 | 0.009 / 0.005 |
| 3x3 repeat, window mean / contrast max z (bakes) | 3.28 / 3.41 | 3.33 / 4.07 | 3.45 / 3.47 | 3.38 / 4.41 |
| far / mid / near row band index (Driver, with the fade) | 0.023 / 0.026 / 0.021 | 0.021 / 0.015 / 0.016 | 0.018 / 0.027 / 0.018 | 0.022 / 0.021 / 0.018 |

Seam ratios below 1 mean the wrapped edge steps are smaller than the average inside step; the z-scores (all under 3,
the largest 2.16) say no edge stands out of its own tile's spread. For the band index, A2's `Driver.png` (no fade) read
0.043 / 0.035 / 0.021 and 03's clay-only ruts 0.024 / 0.013 / 0.006.

**Standard against A2** (`bog-standard-vs-a2.json`): the three fields and the four bakes are byte-identical; the renders
of `Standard_A2check` (Standard on the ruts only) against 04_wet's are pixel-identical for ChurnClose, Tile3x3, TileClose
and the mask (largest difference 0), and the driver view with the fade differs by 1 level in 8 bits on 0.0039 % of its
pixels (mean 0.000013).

### What the variant renders contain

Every `05_variants/<V>/Driver.png` carries the far gloss fade. All four keep 03's clay outside the mud patch.
- **Standard.** Driver: the whole mud road is dark, glossy bog with brown rounded lumps; the ruts show by their shape
  only; some sky sheen at mid distance, the far rows calm. ChurnClose: lumps with dark wet rims and glossy collars on
  dark glossy mud everywhere; up close they read like rounded stones or cobbles set in mud, as A2's did. Tile3x3: an even
  field with broad darker open patches, no repeat I can pick out. TileClose: as A2's.
- **Firm.** Driver: the patch is lighter mid-brown, matte and finely lumpy; ruts by shape; no sheen bands. ChurnClose:
  crowded small lumps rising out of the mud in nearly its own tone, no dark outlines; the crowded parts read as a
  crumbly, pebbly crust. Tile3x3: very even and fine-grained, with weak broad patches; it reads uniform (the owner has
  rejected "very uniform" before). TileClose: from overhead, with the sun from the lower left, the soft lumps read as
  shallow craters (a lighting illusion; the heights are domes, checked in the field preview).
- **Deep.** Driver: dark, very glossy, sky sheen over much of the patch; the lumps barely show; ruts by shape.
  ChurnClose: dark glossy mud with low, soft humps; with their broad foot several read as soft rings or blisters.
  Tile3x3: dark, scattered small glints evenly over it. TileClose: soft humps half sunk in glossy mud; a few still read as
  glossy drops.
- **Stony.** Driver: dark brown lumpy bog with fine pale gravel flecks; ruts by shape. ChurnClose: lumps plus clusters of
  pale angular chips sunk in the mud in patches; no cobbled-path tiling, but the chips are about twice the mud's
  brightness (stone tops' luminance 0.096 against the mud's 0.047) and read as light flakes more than as rounded gravel.
  Tile3x3: speckled by the chips in patches. TileClose: rounded lumps (crater-like in the overhead light, as Firm) and
  the chip clusters.

Nothing in the four reads as swirls, marbling or bands; the open questions are the pebble look (Standard, Firm's
crowded parts, Deep's humps, Stony's chips) and Firm's uniformity.

## How it's made (phase A2)

`build_mud_wet_study.py` opens revision 03's saved scene (`03/MudStyleStudy.blend`: the approved clay, the ruts, the
clods, the pools, the grass, the sun, the sky, the cameras; `build_mud_style_study.py` is not touched) and paints the
churn over the ruts and their banks through a static churn mask (vertex colours: 1 in the ruts, fading over the banks)
times a 30-80 cm breakup noise, as phase A did.

The churn is numpy fields on one 3 m tile, 2048 x 2048, periodic by construction (band-passed white noise in the
Fourier domain; every stamp wraps), so it repeats with no mirror:
- **Clods**: 950, 3.0-15.0 cm across (median 7.6), 0.26-3.39 cm high, 37.5 % cover. Each is an irregular polygon
  (6-10 corners), a third with one side torn flat, at most 1.35:1, its corners rounded, domed on the ray-normalised
  radius (no creases), with a tilted top and a soft foot of slurry squeezed up round it. Three families: half rounded
  lumps, a third low flat-topped pressed slabs, the rest broken chunks with two facets. Clustered by a 55 / 25 cm
  density field: crowded patches and open ones.
- **Dark wet gaps** where clods crowd (1.6 %), a little lower.
- **Flat slurry** between them (57 %): broad, smooth, glossy.
- **Crumbs**: 1700, 1.0-4.0 cm, angular polygons (5-7 corners, no lobes), mostly near the clods.
- **Colour**: each clod one flat umber (warm, grey-brown or red-brown, chosen by two independent 45 / 70 cm patch
  fields, +-4 %); it emerges from the slurry (the slurry's colour and gloss at its foot, its own umber from a third of
  the way up, a little lighter and matte on top). The slurry is two dark umbers in broad 55 cm patches. The whole is
  scaled so its mean CIE L* is 0.60 of the clay bake's.

The colour (linear), height, roughness and zones are written as 16-bit PNGs (`fields/F_Paint.png`, `F_Shape.png`,
`F_Zones.png`), which the node group `NG_MW_Churn` reads (colour, roughness, a bump from the height).
`export_mud_wet.py` bakes the group on one 3 m plane (UV 0-1 = one period) on `export_mud_style.py`'s pattern (Cycles
CPU, EMIT for the values, a tangent NORMAL bake with green NEG_Y), into float images it writes itself:

| map | format | contents |
| --- | --- | --- |
| `T_MS_ChurnColor` | RGB 8-bit, sRGB | the painted colour |
| `T_MS_ChurnNormal` | RGB 8-bit, DirectX tangent (as the clay's) | the bump of the height |
| `T_MS_ChurnRough` | grey 8-bit, linear | slurry 0.22-0.38, clod tops 0.83, crumbs 0.83 |
| `T_MS_ChurnHeight` | grey 16-bit, linear | 0-1 over -0.74..+3.54 cm, for the cavity |

## Numbers (`churn-bakes.json` and `04_wet/manifest.json`, measured on the files as written)

- **Tile join.** Seam ratio (mean step across the wrapped edges over the mean step inside; about 1 = no seam): colour
  1.08 / 1.09 / 1.11, normal 1.07 / 1.11 / 1.03, roughness 1.27, height 1.05. The edge step's z-score among the 2047
  interior row (column) steps: at most +2.0 (roughness, columns); every other channel +1.14 or less. A seam would stand
  far above 3.
- **Value.** Against T_MS_ClayColor: CIE L* 0.599x, HSV value 0.629x, linear luminance 0.366x, saturation 1.25x.
  Linear luminance by zone: slurry 0.038, clod tops 0.058, wet gaps 0.021.
- **Roughness.** Slurry 0.22 / 0.30 / 0.38 (5th / 50th / 95th percentile); wet gaps 0.26; the upper half of the clods
  0.83; crumbs 0.83; 60.2 % of the tile under 0.4, 27.7 % over 0.8.
- **Direction.** Structure-tensor coherence over the whole tile (0 = no dominant direction, 1 = stripes): colour
  0.008, height 0.014 (the clay bake 0.027). Over 10 cm neighbourhoods 0.094 / 0.155 (the clay's plates 0.349, phase
  A's swirls 0.23): nothing long or thin.
- **Repeat.** On the centre tile of each 3x3 render, 30 cm windows: the largest |z| of the window mean 3.28 (0.08 %
  over 3) and of the window contrast 3.41 (0.13 %) for the bakes; 3.27 / 3.39 for the study. Phase A's swirls had a
  contrast outlier of 4.99 (glint clusters); nothing stands out now.
- **Far bands** (the driver view, a new check): per rut and per image row, the mean luminance of the churn's pixels
  less its running mean over 13 rows, as a share of the mean (crosswise lines make rows differ). Far rows (445-520 of
  900, about 10-25 m) / mid (520-620) / near (620-900):

  | render | far | mid | near |
  | --- | --- | --- | --- |
  | 03, clay only (the approved ruts) | 0.024 | 0.013 | 0.006 |
  | phase A swirls (shown to the owner) | 0.040 | 0.031 | 0.025 |
  | **A2 `Driver.png`** | **0.043** | **0.035** | **0.021** |
  | A2 `Driver_FarGlossFade.png` (candidate) | 0.023 | 0.026 | 0.021 |

  For reference, the clay strip between the ruts reads 0.048 / 0.013 / 0.010.

## The renders (final, A2)

- `Driver.png` (03's driver camera): the clay road and plates as in 03. Both ruts are dark, glossy slurry with brown
  rounded lumps and small crumbs; the churn's edge over the banks is ragged. Near the camera, each lump has a darker
  wet rim and a thin sheen round its foot; to my eye the lumps read close to rounded stones or cobbles set in wet mud.
  **Beyond about 8 m the ruts show crosswise, wavy, blue-grey sheen bands** - the thing the owner asked to have gone
  (see "Far bands" below). No swirls, spirals or marbling.
- `SurfaceDetail.png` (03's close camera): two churned ruts between pale matte clay plates; dark slurry dotted with
  lumps of 3-15 cm and crumbs, clustered (crowded runs and open slurry); the lumps flat-coloured brown with lighter
  tops and dark rims. Churned 03 clods dark, clay clods pale. Some crosswise sheen in the upper (farther) rut.
- `ChurnClose.png` (1 m over lane 1): the rut's churn against plain clay. Domed lumps, flat tilted slabs and faceted
  chunks pressed into smooth dark glossy slurry, each with a glossy collar at its foot; crumbs scattered near them; a
  pale clay clod right, a pool top-left. The churn's left edge is a soft diagonal (the study's vertex mask).
- `Tile3x3.png` (9 m flat, overhead, 03's sun and sky): an even field of brown lumps on dark slurry, with broad
  irregular darker open patches; no seam lines; no repeat I can pick out.
- `TileClose.png` (1.5 m of the same plane): rounded, flat and faceted lumps, a few with one straight torn side, on
  smooth dark slurry with soft lighter/darker umber patches; crumbs as small angular bits. No lobed/clover shapes.
- `Bake_Tile3x3.png` (written by the export): the four files rendered back as a 3x3; same look and repeat numbers as
  `Tile3x3.png` (3.28 / 3.41 against 3.27 / 3.39).
- `Driver_ChurnMask.png`: the driver view as masks (R churn, G mud ground), for the far-band check.
- `Driver_FarGlossFade.png`: a **candidate, not in the bakes** (see below).

## Far bands: what they are

The crosswise bands in the far ruts are the bright sky reflected in the glossy slurry over the study's rut surface
(03's terrain: value-noise clumps on a 26 cm grid and the cut's undulation), seen at a grazing angle. Evidence, the
far ruts (rows 440-640) re-rendered from `MudWetStudy.blend`:
- with the churn's normal from the baked `T_MS_ChurnNormal` instead of the bump: the same bands;
- with no churn normal at all (flat): the same bands;
- with the churn's roughness forced to 0.65: no bands; a dark, evenly lumpy rut floor.

So the bands don't come from the churn's pattern but from gloss (asked 0.2-0.4) on undulating ground. The live field
undulates too, so the same thing can happen in game at distance. `Driver_FarGlossFade.png` shows one remedy as a
candidate for phase B: the churn's roughness rises to 0.65 between 6 and 12 m from the camera (only where it's below
0.65). The far bands drop to 03's own level (0.043 -> 0.023); the 6-12 m stretch keeps some crosswise sheen (mid
0.035 -> 0.026); the near view is unchanged. The bakes don't carry this; it's a live-material choice for the main session.

## Revisions in phase A2 (each kept under `BeforeRevision/a2_quick1`-`a2_quick6` with its generator copy)

1. `a2_quick1`: the first clods read as chiselled stones - hard polygon bevels, flat tops, dark rims - and orange on
   near-black. Rounder, domed, a soft foot, lower; clod tones closer to the slurry.
2. `a2_quick2`: still cut-stone facets (the polygon distance profile creases along its medial axis). The dome is now on
   the ray-normalised radius of a corner-rounded outline.
3. `a2_quick3`: the lumps sat on the slurry like pebbles. Each now emerges from it: the slurry's colour and gloss at its
   foot, a fillet of slurry squeezed up.
4. `a2_quick4`: torn bites (one corner pulled in) drew heart shapes. A torn side is now a straight chord; patch contrast
   up.
5. `a2_quick5`: assorted grey and orange lumps read as a pebble beach. Three shape families (domes, pressed slabs, faceted
   chunks), umbers closer, per-clod jitter +-4 %. Repeat numbers 3.81 / 3.36 -> 3.25 / 3.21.
6. Full set (`a2_quick6` is its quick look): far bands found and traced to gloss on the rut geometry (above);
   the far-gloss candidate added as a separate render.

Phase A (swirls, rejected) had nine revisions of its own: tight marbling, glitter, looped strokes, repeating rings and
pockets, then glints and crosswise smears; they're in `BeforeRevision/quick1`-`quick8`, `rev8_full` and
`rev9_swirls_phaseA`.

## Not checked, and for phase B

- No Unreal picture: nothing here has been seen in game.
- The far crosswise sheen bands are in `Driver.png` (above). Whether the live field shows them depends on its own
  undulation and the live material; the far-gloss fade is a candidate, untested in Unreal.
- To my eye the near lumps can read as rounded stones in mud; the owner's look decides.
- The value is set on the bakes (L* 0.60x the clay); the live material's wetness and Fresh terms will darken both.
