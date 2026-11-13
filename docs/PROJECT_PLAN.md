# GrandTour – Project Plan

Working title: **GrandTour** (Unreal Engine 5.8, C++ + Blueprint, solo developer)

This document is the scope contract. The game design doc (GDD) describes the dream;
this describes what actually gets built, in what order, and what gets cut if time runs out.
Read this before adding any feature.

---

## 1. One-paragraph pitch

A near-future wasteland has been abandoned to storms and radiation. The wealthy stage a televised
race across it. You are a driver with a car, a mobile garage, and a small support crew. Each **leg**
of the race is a run across hostile terrain against the clock. Out there you stop, get out, and
work: harvest materials with your tools, strip wrecks for parts, patch the car by hand when it
breaks. Back at the convoy base you craft at the workbench, work on the car at the lift, sell what
you don't need, and upgrade the crew before the next leg. Pacific Drive's car-as-companion survival
loop, with Top Gear / Grand Tour tone and race framing.

## 2. Design pillars (the three things every feature must serve)

1. **The car is the character, and you keep it alive with your own hands.** Damage, wear, and
   upgrades are visible and felt. You get out, open the bonnet, swap the part. You know your car.
2. **Every stop is a gamble.** Getting out of the car means exposure. Push further, harvest longer,
   or get back in and extract before the weather turns.
3. **It's a show.** Race standings, broadcast framing, commentary-style flavour. The tone is dry
   humour over a grim world, not misery.

If a feature doesn't clearly serve one of these, it goes on the cut list.

## 3. Core loop

```
 Convoy Base (walkable mobile garage)
   |- Workbench: craft parts and tools from harvested materials
   |- Car lift: install / remove / repair parts, tune
   |- Trader: sell resources -> currency, buy what you can't craft
   |- Crew: upgrade support team (unlocks stations, better trades, scouting info)
   '- Depart on next leg
        v
 Run (one leg of the race, one bounded map)
   |- Drive checkpoint-to-checkpoint under a leg timer / rival pressure
   |- Hazards: weather fronts, radiation zones, terrain, wrecks
   |- Get out: harvest nodes with tools, strip wrecks, field-repair the car
   |- Exposure: hazards hurt you on foot; the car is shelter
   '- Extract at leg finish (or bail out early at a cost)
        v
 Results: leg time, standings vs rivals, haul tally -> back to Base
```

The **minimum fun** test: is driving a slightly-broken car across dangerous ground, stopping to
get out and rip something useful off a wreck while the sky darkens, fun on its own? Everything else
is layered on top of a "yes".

## 4. Scope tiers

### Tier 1 – Must ship (the game)

**Car**
- First-person driving from the driver's seat, with one car (chassis + frame, never swapped) and
  a socket-based build system: engine with sub-parts, tyres, suspension (which is also the
  clearance part), two rear modules (bed / wagon), cut body panels, and bolt-on accessories.
  See docs/VEHICLE_BUILD_SYSTEM.md.
- A cockpit you can read: working dashboard gauges (speed, fuel, part warnings) on the physical
  dash rather than a screen HUD, plus free look with the right stick / mouse.
- Car condition model: per-part health, fuel, and a small set of wear effects (pulling, misfires,
  reduced grip). Visible damage on the mesh.
- Enter/exit the car anywhere. The car stays where you left it.

**Terrain and traction**
- Ground surface types that change handling: tarmac, dirt, mud, snow, sand. Soft surfaces cut grip,
  add drag, and can bog the car if you stop or slow in the wrong place.
- Tyre tracks left in mud and snow: visible ruts behind the car with a normal-mapped groove, and
  mesh displacement where the engine supports it reliably. Tracks fade over a leg, never persist
  between legs.
- **Winch** as a gadget-slot part. Getting bogged means getting out, walking the hook to an anchor
  (tree, rock, wreck), getting back in, and reeling. Rigging time is exposure time. Anchors are
  placed by hand per leg; some are weak and will fail.

**On foot**
- First-person character: walk, sprint, interact, with visible arms holding the current tool.
  No jumping puzzles, no climbing, no combat.
- Player exposure meter: hazards drain it on foot; it recovers in the car and at base.
- Three tools, each unlocking a kind of harvesting:
  - **Pry bar / salvage tool** – strips parts and scrap from wrecks.
  - **Cutter / extractor** – harvests raw materials from resource nodes (the rare stuff lives in
    hazard zones).
  - **Repair kit / jack** – field repairs on the car using carried materials.
- Carried inventory with a weight or slot limit, plus the car's boot as bulk storage.

**Base**
- Walkable convoy base with three stations: **workbench** (craft parts, tools, repair kits from
  materials), **car lift** (install/remove/repair/tune parts), **trader** (sell resources, buy what
  you can't craft).
- Crew upgrades as a menu at the base (station tiers, trade prices, scouting info).

**Weather**
- Weather states per leg: clear, overcast, rain, storm (the weather front), snow. A leg starts in
  one and the front moves it through others.
- Rain that makes the world wet: every environment material, the car, and the character's arms
  take on wetness, puddles form in low ground, surfaces dry out afterwards. Nothing gets wet under
  cover.
- Wet ground changes handling: every surface has a wet grip and drag value, so wet tarmac is
  slick and wet dirt turns toward mud.
- Rain, spray, wind and thunder audio; rain on the windscreen with wipers (see car body).

**Environmental conditions**
- Each leg has a conditions profile that the player learns in a briefing at the base before
  departing, and answers with part choices, consumables, and how they drive.
- Conditions act on the car through the same pipeline as parts and damage, and on the player
  through exposure. Parts counter conditions by tag, the same way they resist hazards.
- Every condition must: appear in the briefing, be readable from a gauge or cue in the car, have
  at least one part answer and one behaviour answer, and fail gradually. A condition that misses
  any of these is cut.
- Which conditions ship, and what each does, is defined in the GDD. Keep the Tier 1 count small.

**Run**
- 4–6 hand-built legs (maps), each 5–10 minutes to drive clean, longer if you stop and work.
- Two hazard types done well: **weather front** (moving zone, kills visibility, damages car and
  player) and **radiation pocket** (static, where the rare resources are). Tuned together so the
  risk/reward decision is real.
- Harvest nodes and wrecks placed by hand per leg, with loot tables.

**Framework**
- Simple economy: one currency, resource prices, crafting recipes, upgrade tiers.
- Rival AI as **standings only** (times simulated, not driven on track). Standings screen after
  each leg. Ends with a final standings / ending card.
- Save/load at base.
- Controller + keyboard/mouse, main menu, options (audio, graphics presets, input rebinding via
  Enhanced Input, plus first-person comfort: FOV slider, head bob and camera shake toggles).

### Tier 2 – Should have (if Tier 1 is done and fun)
- Crew members as characters you can talk to at base, a few lines each (text, portraits, no VO).
- Broadcast layer: commentary text pop-ups, "viewer favour" that affects sponsor payouts.
- Tool upgrades (faster harvest, access to harder node types).
- Terrain that degrades during a run: the weather front leaves mud or deepening snow behind it, so
  the route you drove in on is worse on the way back. Driving in your own ruts is easier than fresh
  ground.
- Winch upgrades (longer cable, stronger motor, pulling wrecks off loot), and using the winch to
  drag obstacles or lower the car down slopes.
- Weather depth: water flowing down slopes and pooling into rising floods, lightning strikes as a
  hazard, wind that pushes the car and the character, fog banks.
- A fourth station (e.g. resource refinery) and a third hazard type (electrical storm / EMP).
- Enterable structures on legs (small interiors with better loot).
- Route choice: two paths per leg with different risk profiles.
- More car bodies (2–3) with different base handling and their own cockpits.
- Working mirrors and an optional chase camera as an accessibility fallback.
- PCG decoration inside hand-built legs (wrecks, debris, vegetation) to speed up content.

### Tier 3 – Nice to have (only after a playable, fun build exists)
- Physically-driven rival cars on track.
- Full VO, cinematics, day/night cycle.
- Fully procedural legs.
- Base layout customisation.
- Persistent terrain deformation between legs (only makes sense if legs are ever revisited).

### Explicit cut list (not doing, don't get tempted)
- Multiplayer of any kind.
- Open world. Legs are bounded, loaded one at a time.
- Combat or enemies. Threat comes from the environment, not things with guns.
- Player survival meters beyond exposure (no hunger, thirst, sleep).
- Realistic simulation-grade vehicle physics. Arcade-with-weight is the target.
- Deep crafting trees. Recipes are flat: materials -> part / tool / consumable.
- A visible full body. First person means arms only: no legs, no body shadow rig, no third-person
  animation set. Tool use is one short arms animation per tool, and a static hold pose is an
  acceptable Tier 1 fallback.

## 5. Milestones

Each milestone ends with a playable build and a short written review: what's fun, what isn't,
what changes in the next one. Effort is a rough guide for consistent part-time work; adjust to
real availability.

| # | Milestone | Done when | Rough effort |
|---|-----------|-----------|--------------|
| M0 | Project skeleton | Git + LFS, folder structure, C++ module layout, Chaos Vehicles enabled, a car drives on a flat test map. | 1 week |
| M1 | Driving prototype | Greybox test track with tarmac, dirt, mud and snow zones. Car feels good with a controller from the driver's seat, and soft ground feels different. Tyre tracks render behind the car. Greybox cockpit with working gauges. Per-part health and fuel exist and affect handling. Damage visible from inside and outside. **Fun test #1.** | 5–6 weeks |
| M2 | On foot + tools | Enter/exit the car. First-person character with arms. Interaction system. Three tools, harvest nodes, wreck stripping, field repair. Bogging and the winch: get stuck, rig an anchor on foot, reel out. Inventory and boot. **Fun test #2 – the stop-and-work moment.** | 6–8 weeks |
| M3 | Run loop | One greybox leg with checkpoints, timer, one weather front, one radiation pocket, player exposure, hand-placed nodes and wrecks, extraction. Results screen. **Fun test #3 – the core gamble.** | 4–6 weeks |
| M4 | Base + crafting | Walkable greybox base. Workbench recipes, car lift install/remove/repair, trader. Crew upgrade menu. Save/load. Play leg -> base -> leg. **First complete loop.** | 5–7 weeks |
| M5 | Progression | Leg sequence (4–6 legs), rival standings, difficulty curve, ending. Greybox art is fine. | 4–6 weeks |
| M6 | Content + art pass | Environment art for legs and base, car exterior and cockpit interior, part and tool meshes, first-person arms, hazard VFX, audio pass, UI polish. | 12–16 weeks |
| M7 | Polish + release prep | Options, accessibility basics, performance targets, bugs, store page, trailer. | 4–6 weeks |

Total: roughly 12–15 months for Tier 1. Tier 2 items slot in after M5 only if the fun tests passed.

## 6. Key decisions made now (revisit only with a reason)

| Decision | Choice | Why |
|----------|--------|-----|
| World structure | Bounded legs, one map per leg | Open world is the #1 solo-dev project killer. Legs also match the race fiction. |
| Perspective | First person everywhere: in the seat and on foot | You are in the car, not watching it. Reading the dash, seeing the crack spread across the windscreen, and holding the tool in your hands is the fantasy. |
| On foot | Tier 1, tool-driven interaction, no combat | Getting out and working on the car is the heart of the fantasy. Combat and platforming are separate games' worth of work and don't serve the pillars. |
| Character animation | Arms only, one short animation per tool | First person removes the locomotion animation cost entirely. Keep it that way: no visible body. |
| Cockpit | Greybox interior with working gauges from M1; real interior art in M6 | The interior is now the most-seen asset in the game. It must exist early for the driving fun test, but it doesn't need to be pretty until the art pass. |
| Base | Walkable with three fixed stations, crew as a menu | Stations are the on-foot crafting fantasy. Walking crew NPCs are Tier 2. |
| Rivals | Standings only, no on-track AI | Vehicle AI on rough terrain is a deep rabbit hole. The race is against the clock and the table. |
| Vehicle physics | Chaos Vehicles plugin, tuned arcade | Ships with the engine, well documented, good enough. Don't write your own. |
| Terrain deformation | Render-target trail that drives normals (and displacement if stable), plus a gameplay "sinkage" value per wheel. Not a real soil simulation. | The gameplay effect (grip, drag, bogging) and the visual effect (ruts) are separate systems that share one data source. Either can be simplified without losing the other. |
| Car deformation | Procedural: a capped impact list drives material displacement on separate body panels. Part health comes from a region-to-part map. No sculpted damage morphs. | Moves the cost from per-panel art to a one-time shader. Any car mesh with decent density works, which makes buying a base model viable. Repair clears dents, saves store the impact list. |
| Wet materials | Every material in the project derives from a small set of master materials that all include one shared weather function. Wetness is a global parameter, never a per-material job. | Rain has to affect everything or it looks broken. The only way that's affordable is if new assets get it for free. Imported assets are reparented on import; that's the cost of the rule. |
| Environmental conditions | A per-leg profile, a pre-departure briefing, tag-based part answers, and gradual failure. Conditions are mostly multipliers; keep continuous simulations to one or two. | The environment should be a puzzle you prepare for, not a random punishment. Readability before departure and in the car is what makes preparation meaningful. |
| Winch | Gadget part, rigged on foot, manual reel from the seat | Ties the car, the on-foot layer and exposure together in one mechanic. Auto-winching from the seat would remove the gamble. |
| Art | Greybox until M6 | Art is the most time-hungry part. Prove the loop first. Use Fab/Quixel assets where they fit. |
| Language split | C++ for systems and data, Blueprint for content and tuning | See ARCHITECTURE.md. |
| Leg mission types (2026-09-14) | Legs are challenges of different kinds, in the style of the TV specials: make it along this tough road, find and photograph a rare animal, and so on. A leg definition names its type and its win condition; the time trial built in M3 is one type. | One kind of leg wears thin over a tour. Named challenges give each leg a hook and a reason to prepare differently. Implement with the M5 leg definitions. |
| Base as a camp (2026-09-14) | The base is a camp in the style of the tour's region, one camp per tour (a Bolivia tour uses the Bolivia camp throughout), not one fixed convoy base. The stations, lift and gate stay. | A tour has a well-defined look, so one camp per tour is cheap and sells the place. A "tour" is a run of legs in one region with one car (the format proposed on 2026-09-09, not yet written into sections 1 to 5). Art in M6. |
| Level design reference (2026-09-14) | Levels take heavy inspiration from MudRunner and SnowRunner: terrain that has to be read and worked through (mud, water, ruts, the winch as the answer), with some stretches built for rally driving (flowing gravel, crests, cambered bends). Said after driving The Hide's first terrain ("Not bad"). | The surface model, bogging and the winch already exist; this is what they are for. The terrain generator grows toward it (mud sections with winch points, water crossings with depth, steeper ground, narrow tracks, alternative lines) and gets a spec the user can edit, since they intend to build levels in earnest themselves. |
| Inventory and menus (2026-09-14) | Nicer inventory visuals, and menus integrated into the world where the player physically handles things rather than reading a list. Later: gameplay and base systems come first. | The on-foot layer is about handling the car and the kit. Screens are the placeholder; the M7 UI pass gets the visuals, the world-integrated version is Tier 2. |

## 7. Risks

- **Vehicle feel.** If M1 doesn't feel good, nothing else matters. Budget real time for tuning and
  be willing to try a second approach (e.g. a simplified custom wheel raycast) if Chaos fights you.
- **Displacement tech.** Both terrain ruts and car dents want mesh displacement, and the engine
  features for it have moved between versions. Do one spike at the start of M1 covering both: if
  Nanite displacement is solid in 5.8 on landscape and static meshes, use it; if not, normal-map
  ruts plus decals for terrain and World Position Offset on a dense body mesh for the car are the
  Tier 1 answers. Cap the spike at one week. Don't let it become a month.
- **Procedural dents looking like soft blobs.** Displacement-based dents push inward smoothly and
  can read as "dented balloon" rather than crumpled steel. The fix is in the material, not the
  approach: sharpen the falloff, add a crease normal at the dent rim, and layer a scratch/scuff
  mask. Budget a few days of look-dev in M6 for this.
- **Material discipline.** The wet-everything rule only holds if no asset sneaks in with its own
  material. Every Fab or marketplace import needs its materials reparented to a project master,
  which is boring work of roughly ten minutes per material. Do it on import, every time. A
  material without the weather function stands out the first time it rains.
- **Cockpit art.** In first person the interior is on screen most of the time and close to the
  camera. One good cockpit is a serious modelling job. Budget for it in M6, and consider a bought
  or Fab interior as a base to modify.
- **Motion comfort.** First-person driving on rough terrain makes some players ill. Camera
  smoothing, a stable horizon option, FOV and head-bob settings are Tier 1, not polish.
- **On-foot cost creep.** A character invites climbing, combat, animations, and interiors. The
  character exists to use tools and get back in the car. Hold that line until Tier 1 ships.
- **Enter/exit and possession bugs.** Swapping pawns while physics is live is a classic source of
  jank. Build it early (M2) and keep it in the test map for the whole project.
- **Scope creep from the fiction.** The world invites a lot of ideas. Every idea goes into the GDD
  under a tier; nothing enters the build without a milestone.
- **Content cost per leg.** If one leg takes more than ~2 weeks to greybox and tune, reduce leg
  count or size, don't extend the schedule.
- **Engine churn.** Stay on 5.8 for the whole project unless a blocking bug forces an upgrade.

## 8. Working practices

- Weekly: one playable build saved off, one short note in `docs/devlog/` on what changed and what
  the next week is.
- Every feature starts as a task in `docs/BACKLOG.md` tagged with its tier and milestone.
- Fun tests at M1, M2 and M3 are hard gates. If they fail, iterate there, don't move on.
