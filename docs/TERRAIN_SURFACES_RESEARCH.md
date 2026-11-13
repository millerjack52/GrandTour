# Terrain surfaces: what went wrong, how the reference games do it, and the way forward

> Follow-up after prototype `dcf749d`: the owner still rejects the shape. See section 5 below for
> the new visual/technique research. Earlier implementation proposals here are historical, not visual approval.

Main session, 2026-10-12. The owner drove the Gaea Benmore review level after B2c and sent six screenshots: "Lots of
issues. In a lot of ways, you've made it worse." The target is MudRunner, SnowRunner, Expeditions and rally-style
off-road and gravel surfaces, and the owner judges what exists as "not usable". This is research and a proposal; no
code has changed.

## 1. What the owner's screenshots show

| # | Shot | Problem |
|---|---|---|
| 1 | On foot where a mud zone meets a gravel zone | **Holes through the ground.** Blue sky shows between the mud's water and the gravel patch. There is no transition between deformable surfaces. |
| 2 | Looking down at muddy rut water | Flat orange with a **blocky square grid** and white glare patches. It reads as a coloured plane, not water. |
| 3 | A wheel-dug trench | A **moat**: a wide channel with smooth walls, full of flat orange water, glaring. |
| 4 | The car's track on gravel | A **wide trench of smooth grey-brown sand**. The gravel texture disappears where it is deformed. |
| 5 | The same, closer | A smooth trench, plus a **stray floating dark sliver** (a mesh artifact). |
| 6 | A mud road after driving | The car **carved a long channel** that filled with flat orange water. |
| — | The owner's words | "Gravel deformation is way over the top, I think we need to get rid of it." "The so-called textured surfaces … other than the gravel look terrible" (GR2's soil detail and scatter). |
| — | On screen | An engine warning: streaming geometry's always-resident memory is over 20 % of the budget (93.9 / 400 MiB). |

**Why my look gates missed this:** I judged agent-chosen camera frames: fixed angles, the sun behind, one pass, no
spinning or stuck car. The owner judges on foot and after real driving, looking toward the sun, at zone joins, after
repeated passes. **Lesson:** every terrain gate must include frames from the owner's angles. That means on foot, after
a realistic drive (including getting stuck and spinning), looking toward the sun, at every join between surface types.

## 2. How the reference games do it

**MudRunner / Spintires**, from the developer's own write-up:
- **One terrain, mud layered on it.** The world is 16 m blocks. Each block has a 25×25 base-terrain texture and, only
  where mud exists, a 128×128 mud texture:
  - R holds the mud height *relative to the base terrain*;
  - GB holds a mud offset (mud slides away from the wheels);
  - A holds the track blend.
  A channel in the base-terrain texture marks where the base is "substituted by the mud", and the mud shading blends
  into the terrain shading, so the transition is "unnoticeable". The mud is never a separate patch dropped into a hole:
  it is the same surface, with its own height above the base.
- **Mud exists only where an artist painted it** ("covered with a mud layer", painted with a brush). Firm ground has no
  mud to dig.
- **Wheels:** collision and traction come from the physics engine. Forces approximate mud when there is a mud layer or
  the wheel spins too fast. The visual displacement is computed on the GPU from primitives built from wheel and chassis
  position, size, velocity and penetration depth ("pure empirics").
- **Tracks** are separate trapezoid strips with a two-pass parallax: their heights render into their own depth
  buffer, then the tracks are drawn.
- **A tint channel** marks softer ground. Mud chunks are rigid bodies that break into smaller chunks. Mud particles are
  cosmetic.
- **Water** is its own 2D simulation (two RGBA textures swapped each frame, carrying water, height, foam and "water
  mud") on a highly tessellated mesh. It has 5 animated wave layers, pre-mixed foam where vehicles strike or the flow is
  strong, and SSR reflections. Mud shows through the water from the domain texture.
- **Only active blocks** near the truck simulate.

**SnowRunner and Expeditions** descend from the same terrain simulation, rebuilt in Saber's Swarm engine. A preview
says Expeditions brought back the series' strong deformation after SnowRunner's weaker ground. I found no public
technical detail beyond that.

**Rally (DiRT Rally 2.0, EA WRC):**
- Gravel is not dug into trenches. The surface degrades over the running order in fine steps (about 150 steps on
  gravel in DiRT Rally 2.0).
- Early cars sweep loose material off the line. Mid cars get the best grip on the cleaned line. Later cars find ruts,
  with material pushed off the line to the edges, which changes the camber.
- EA WRC layers textures as the surface degrades and feeds the changes into the track's physical geometry.
- In all of these, gravel deformation is shallow and broad: a cleaned line plus berms of loose stones. Never tyre-deep
  trenches.

**Unreal Engine techniques:**
- **Nanite landscape tessellation:** the landscape's own material displaces it. That gives no separate mesh, no holes
  and no seams, and transitions are just material blends.
  - It is experimental and needs Nanite data that is up to date.
  - The Nanite Skirt option covers proxy-edge holes.
  - Collision ignores the displacement. That is fine for us: our wheels use a sinkage model, not collision.
- **Render target + Runtime Virtual Texture + Virtual Heightfield Mesh:** the deformation is stored in a texture and
  drawn by a separate heightfield mesh on top. This is the documented route for runtime tyre trails.
- **Shallow trails** (sand, gravel) are often only normal and parallax in the material, with no geometry.

## 3. Why ours fails (root causes)

1. **Separate patch meshes over landscape holes.** Each mud or gravel patch is its own mesh, and the landscape is cut
   away beneath it. Where two patches meet, or a patch meets the landscape, their edges don't share vertices, which
   leaves sky-coloured gaps (shot 1) and stray slivers (shot 5). MudRunner avoids this entirely: one surface, mud
   stored as a height relative to it. **This is the main structural fault.**
2. **No mud-thickness limit.** Our field lets wheels dig wherever a patch exists, with sinkage caps of 22-60 cm per
   variant. Pre-churn adds more tracks, and the -10 cm water table on mud roads floods every trough. A spinning or
   repeat pass widens and deepens the trough into a moat (shots 3 and 6). In MudRunner the mud is a painted layer of
   finite thickness, and the base terrain under it is firm.
3. **Gravel deformation dug like mud** (shots 4 and 5). DG1's gravel field cuts tyre-width troughs and swaps in a
   smooth "packed" texture, so the gravel look disappears in the track. Rally gravel doesn't trench; it sweeps.
4. **Rut water is a flat coloured plane.** Its per-cell data (turbidity, froth) is drawn on the 12.5 cm field grid,
   which gives the blocky squares (shot 2). It is a single opaque-masked layer with no wave geometry, and its low
   roughness facing the sun makes white blow-out. MudRunner's water has tessellated geometry, layered animated waves,
   foam and mud in the water.
5. **The soil detail and scatter** (GR2, B1) were judged by me from agent captures; the owner judges them terrible in
   play. They also add shader cost (Benmore's terrain material went 1,090 → 1,938 instructions) and draw-call or memory
   load (the streaming warning may be partly ours).

## 4. Proposal

**Step 0, triage, so Benmore is usable for testing now:**
- Default off on Benmore: the gravel deform zones (removed), our soil detail and scatter, and the mud zones.
- Keep the surface physical materials (they don't change the look).
- This needs one setup run, and one build if defaults live in C++.

**Step 1, decide the architecture.** One terrain surface, MudRunner-style:
- **(A) Recommended: deformation as landscape displacement.**
  - A world-aligned deformation texture streamed around the car (mud height offset, slide offset, track blend, wetness,
    like MudRunner's 128² per 16 m) drives Nanite tessellation displacement on the landscape itself.
  - Surface types (gravel, soil, mud) are layers in the landscape material, so transitions are material blends with no
    holes and no seams.
  - Mud exists only where a "mud thickness" layer is painted (Gaea masks plus hand-painting), with its height above the
    firm base.
  - Wheels keep our sinkage and traction model, reading the same texture on the CPU.
  - Needs: a C++ editor helper to wire the material's displacement pin (Python can't, per GR0), Nanite on the landscape
    with skirts, and a cost check by the owner.
- **(B) Fallback, if Nanite tessellation proves too costly or unstable:** keep a heightfield mesh, but MudRunner-style.
  - One continuous mesh per active block, whose base is the landscape height everywhere: no holes. Mud is height above
    the base; ruts dig only into the mud thickness, never below the base.
  - Seams are handled by the substitution blend on a shared grid.
  - In UE, ruts below the landscape need the landscape lowered under mud areas by the mud thickness (bake it into the
    heightmap where mud is painted), so the mesh always draws on top.

**Step 2, surfaces:**
- **Gravel (rally):** no geometric deformation.
  - The track paint drives a swept line: fewer loose stones, more compact and darker, and grip changes along the line.
  - Berms of loose stones pushed to the edges, as material plus instanced stones that wheels push.
  - At most about 1-2 cm of material-only displacement in A.
- **Mud (MudRunner):**
  - finite painted thickness (10-50 cm), ruts tyre-width, material conserved into lips;
  - no widening beyond the tyre;
  - water only in hollows below a painted water table, with a fill limit;
  - chunks and clods as now.
- **Rut water (MudRunner):**
  - wave detail from layered animated normal maps, a little vertex wave on a finer mesh;
  - foam and mud mixed in, data sampled bilinearly (no grid);
  - roughness and specular clamped to stop blow-out;
  - reflections from Lumen or SSR as now.
- **Soil look:** start from GPT's approved Benmore ground materials and the owner's references, not our GR2 bakes.
  Scatter only where the owner asks for it.

**Step 3, gates that would have caught this:** owner-angle frames as in section 1, each:
- after a scripted spin-stuck and a repeat pass;
- at every surface join;
- looking toward the sun.

**Owner decisions needed:** run the triage now? Architecture A or B? Who builds it: us, GPT, or a split by area
(for example, GPT keeps Benmore materials and dust, and we build the deformation core)?

## 5. Shape research after the failed clump iterations

Research date: 2026-10-12 (owner's timezone). This is a research revision; no runtime code or assets
were changed in this pass. The owner's three MudRunner screenshots remain the primary art target.

### Strongest additional references

| Reference | What it establishes | How to use it |
| --- | --- | --- |
| [Pavel Zagrebelnyy: Mud and Water of Spintires: MudRunner](https://www.gamedeveloper.com/programming/mud-and-water-of-spintires-mudrunner) | The lead developer removes rendering layers from the same scene: decals, tracks, particles, chunks, road overlays, then the heightfield. | Compare the finished and stripped images before attributing every visible clod to displacement. |
| [Javier Perez: Dirt Road](https://meshmodeler.artstation.com/projects/xJN4B4), with [NVIDIA tutorial part 1](https://www.youtube.com/watch?v=88tsuo7CI0Q) and [part 2](https://www.youtube.com/watch?v=zdnwt3BpbOM) | The artist's finished material and map breakdown; tutorial descriptions cover Substance/Maya authoring and Unreal road-spline integration. | Best practical road-material reference. Study connected channels, interrupted edges and embedded debris. Tutorials were located; their full videos were not watched in this research pass. |
| [Tom Jacobs: Wet Mud II](https://tomjacobs101.artstation.com/projects/zAW0g4) | Artist-authored Substance material, close-up and breakdown, aimed at wet clay-like dirt and dirty pools. | Reference for low torn lobes, fine surface roughness and wet margins. This is a material render, not evidence of a game simulation. |
| [Jared Sobotta: Erosion Breakdown](https://jaredsobotta.artstation.com/projects/8brNkO) | A production artist describes large-to-small sculpting, height/ID bakes, shape/atlas scattering and directional erosion detail for The Last of Us Part I. | Build deliberate base forms and derive coherent maps, then add smaller detail. Do not copy his unrelated river-rock shapes as mud. |
| [SnowRunner: Meet the Modder, Remoh667](https://steamcommunity.com/games/1465360/announcements/detail/5694225455754433910?l=english) | Official community feature with a mod-map screenshot showing a churned vehicle corridor through wet terrain. | Additional visual reference for elongated disturbance and how terrain outside the driven line differs. This is modded scenery, not an unmodified base-game benchmark. |
| [Saber's mud authoring documentation](https://expeditions-guides.saber.games/map_modding/creating_a_map/terrain/geometry_brushes_for_terrain/mud/) | Mud appearance, depth and wetness are separately authored controls; the guide distinguishes Automatic and Extrudes modes. | Keep visible mud coverage, available depth and wetness distinct. Its editor brush values are not world-centimetre settings for our field. |

### Direct visual comparison

MudRunner's finished scene, from Zagrebelnyy's breakdown:

![MudRunner finished mud scene](https://eu-images.contentstack.com/v3/assets/blt740a130ae3c5d529/bltb5929481a21b7b8c/650ea2ffa4f1650bbde307d3/0_source.jpg/?auto=webp&disable=upscale&quality=80&width=646)

The same view stripped to its mud heightfield. Both were inspected in the browser:

![MudRunner bare mud heightfield](https://eu-images.contentstack.com/v3/assets/blt740a130ae3c5d529/bltaf87e3ce5152a484/650ea2fb6f7f77cf4d3fc36d/6_no_roads.jpg/?auto=webp&disable=upscale&quality=80&width=646)

The reference still has substantial connected relief without its chunks. Adding decorative chunks to
our present surface would therefore not fix the base shape. The finished image gains more broken
silhouettes and detail from its additional layers. This is our visual interpretation of the comparison.

Perez's road is the more useful close-up target for the next shape study:

![Javier Perez dirt-road material](https://cdna.artstation.com/p/assets/images/images/031/667/176/large/javier-perez-jperez-dirt-rox-02.jpg?1604267983)

My reading: the ruts are connected compressed channels, bordered by fragmented, slumped ground. Small
pieces sit within larger forms. Our `variation_foot.png` instead shows broad flat intervals, isolated
raised shapes, and narrow grooves bordered by spikes. Changing random seeds or fragment counts does
not change that underlying construction.

### Verified technique and its limits

Zagrebelnyy's 2017 article separates CPU physics data from GPU visual data. The mud texture holds height,
lateral offset and track blend; wheel/chassis-derived primitives update it. Larger mud chunks are rigid
bodies, and tread relief uses a separate parallax track pass. It does not publish a complete mud-shape
generator or establish that its full look comes from procedural noise.

His [2013 Spintires paper](https://www.gamedeveloper.com/programming/rendering-and-simulation-in-offroad-driving-game)
is more explicit about deformation: downward extrusion uses MIN blending, and push primitives in
front of wheels use MAX blending. That is a useful directional shape model, not proof of volume
conservation. Our finite-depth/conserved-volume requirements still need their own implementation.

Correction to the earlier architecture summary: the reference games substitute a higher-resolution
mud representation for portions of base terrain. They do not literally use one Unreal landscape.
Our continuous Nanite landscape remains a project choice for avoiding seams; the research supports
blended continuity, not a requirement to copy the original mesh arrangement.

Sobotta's workflow starts with authored large forms, uses height and ID masks, and layers smaller
elements afterwards. His directional erosion treatment provides a concrete alternative to stacking
generic noise. [Tom Martyn's first-person material notes](https://tommartyn.artstation.com/blog/q98Y/desert-scene-wip-05-learning-substance-designer)
also describe warped source shapes, slope-blur edge treatment, and separate large/small scatter passes.
These are authoring techniques; neither source is a runtime mud solver.

### Proposed construction for the next prototype

This is a recommendation from the references and our code review, not a claim about undocumented
SnowRunner internals or a completed implementation.

1. **Author a small shape library first.** Make a pressed trough, a broad sheared bank, a folded/slumped
   slab, and a cluster of broken fragments. Sculpt or procedurally author these deliberately, bake height
   and useful masks, and inspect them under a neutral clay material at wheel scale. Reject volcano-like
   profiles before adding texture. A richer formula is not a substitute for reviewing the source shapes.
2. **Compose connected ground.** Place broad deformations along disturbance paths, with overlapping
   slumped banks and a compressed centre. Use fragment shapes locally at torn edges. The current
   `RestHeight` maximum of independently scattered islands should not define the whole muddy area.
3. **Make the wheel operation directional.** Form the trough from the contact sweep, push mud forward
   and to unequal sides according to wheel motion, and flatten or break existing clods when crossed.
   Allocate only the removed volume, respect finite thickness, and keep excavation inside the tyre
   footprint. Our current lateral UV offset does not itself transport the heightfield sideways.
4. **Separate tread detail from rut volume.** Add a tyre-oriented impression mask with broken edges,
   fading on slurry and repeated churn. Do not make each tread block a large geometric mound. Keep the
   existing straight fixture as a control, but add a separate curved/crossed-path art view later.
5. **Derive material detail from the shapes.** Align height, normal, colour and roughness masks for
   compressed floors, freshly exposed faces, crumbs and saturated margins. Jacobs' close-up is useful
   here; our present muddy colour variation is too independent of the actual fractures.
6. **Keep geometry roles explicit.** A heightfield cannot represent undercut or overlapping loose
   clods. Baked fragments can improve it substantially; genuinely detached clods would need a separate,
   limited geometry layer. That would be an explicit addition to the prototype, not another terrain
   patch or permission to scatter unrelated assets across Benmore.

First deliverable should be a small static shape study beside the references, followed by one dynamic
wheel pass. Keep the current grid for that study; more simulation resolution alone will not fix these
profiles. Revisit visual-detail versus simulation resolution after the look works. No performance
claim, new purchase, full fluid solver, Benmore rollout or driving-force change follows from this research.

## Sources
- [Mud and Water of Spintires: MudRunner (Pavel Zagrebelnyy)](https://www.gamedeveloper.com/programming/mud-and-water-of-spintires-mudrunner)
- [MudRunner: porting a successful title to console (80.lv)](https://80.lv/articles/mudrunner-porting-a-successful-title-to-console/?amp=1)
- [Expeditions: A MudRunner Game preview (CGMagazine)](https://www.cgmagonline.com/articles/previews/expeditions-a-mudrunner-game)
- [DiRT Rally 2.0 track surfaces degrade with every run (GTPlanet)](https://www.gtplanet.net/dirt-rally-2-0-track-surfaces-will-degrade-with-every-run/)
- [How EA Sports WRC brings realism to rally driving (PlayStation Blog)](https://blog.playstation.com/2023/10/30/how-ea-sports-wrc-brings-realism-to-rally-driving-on-ps5-out-nov-3/)
- [Using Nanite with Landscapes (Epic docs)](https://dev.epicgames.com/documentation/en-us/unreal-engine/using-nanite-with-landscapes-in-unreal-engine)
- [Landscape displacement with Nanite (Epic community tutorial)](https://dev.epicgames.com/community/learning/tutorials/OXLa/unreal-engine-landscape-displacement-with-nanite-realistic-landscapes)
- [Level Up Your UE5 Real-Time Projects: landscape deformation (The Rookies)](https://discover.therookies.co/2025/11/14/real-time-projects-niagara-collisions-landscape-deformation-more/)
- [Creating Snow Trails in Unreal Engine 4 (Kodeco)](https://www.kodeco.com/5760-creating-snow-trails-in-unreal-engine-4?page=2)
