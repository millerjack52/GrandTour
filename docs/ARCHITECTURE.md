# GrandTour – Technical Architecture

Companion to PROJECT_PLAN.md. This describes how the project is laid out and how systems
talk to each other, so decisions are made once and applied consistently.

---

## 1. C++ vs Blueprint

**C++ owns:** data types, save data, core systems, anything that needs to be fast or tested.
**Blueprint owns:** content (specific parts, cars, legs), tuning values, UI layout, VFX hookup,
anything you'd iterate on in the editor.

Rule of thumb: if you'd want to change it without recompiling, it's Blueprint or a Data Asset.
If it has invariants that must hold (inventory can't go negative, a part fits one slot), it's C++.

Practical pattern: C++ base classes with `UPROPERTY(EditDefaultsOnly)` and
`BlueprintNativeEvent` hooks, Blueprint subclasses for each concrete thing.

## 2. Module layout

Keep a single runtime module until it hurts. Sub-folders inside the module by system, not by class
type. Split into separate modules only when compile times or dependency tangles force it.

```
Source/GrandTour/
  GrandTour.Build.cs
  Core/          Game instance, run subsystem, player controller, save game
  Vehicle/       Car pawn, tuning pipeline, condition/damage model, wear effects, winch
  Environment/   Conditions profile sampling, environment modifiers, briefing data
  Terrain/       Surface types, traction model, sinkage/bogging, track-painting subsystem
  Character/     Player character, exposure meter, tool selection, enter/exit
  Interaction/   IGTInteractable interface, interaction component, prompt data
  Inventory/     Inventory component (character + car boot), item stacks, transfer
  Parts/         Part definitions, install/remove logic
  Tools/         Tool definitions and tool-use logic
  Harvest/       Harvest nodes, wrecks, loot tables
  Crafting/      Recipe definitions, crafting station base, workbench / car lift / trader
  Run/           Leg flow: checkpoints, timer, extraction, results
  Hazards/       Hazard volume base, weather front, radiation zone
  Weather/       Weather subsystem: state machine, global wetness/snow/wind, rain occlusion capture
  Economy/       Currency, prices, upgrade definitions, crew upgrades
  Base/          Convoy base game mode and crew upgrade services
  Race/          Leg sequence, rival standings simulation, ending
  UI/            C++ widget bases only; layouts live in Content/GrandTour/UI
```

Add `Source/GrandTourEditor/` later only if you need custom editor tooling (e.g. a leg validator).

Prefix all project classes with `GT` (`AGTCarPawn`, `UGTPartDefinition`) so they're easy to
find and never collide with engine names.

## 3. Content layout

```
Content/
  GrandTour/                 <- everything project-authored lives under one root
    Core/                    GameMode, GameInstance, PlayerController BPs, input configs
    Vehicles/
      Bodies/                Car body BPs + meshes
      Parts/                 Part Data Assets by slot (Engine/, Tyres/, Suspension/, Armour/, Gadgets/)
      Materials/
    Characters/
      Player/                Player character BP, first-person arms mesh, arms anim BP, tool animations
    Tools/                   Tool Data Assets, tool meshes, tool-use montages
    Items/                   Resource / material Data Assets
    Harvest/                 Harvest node BPs, wreck BPs, loot tables
    Crafting/
      Recipes/               Recipe Data Assets
      Stations/              Workbench, car lift, trader BPs
    Legs/
      Leg01_Name/            One folder per leg: level, sublevels, leg-specific data
      Shared/                Reusable environment kit, PCG graphs
    Hazards/                 Hazard BPs, VFX, materials
    Weather/                 Weather state Data Assets, rain/snow Niagara, sky and cloud presets, weather audio
    Materials/
      Master/                The master materials everything derives from (see Weather and wet materials)
      Functions/             MF_Weather and other shared material functions
      MPC/                   Material Parameter Collections (MPC_Weather, MPC_Player)
    Terrain/                 Physical materials per surface, landscape layer materials, track render targets, winch anchor BPs
    Base/                    Base level + base UI
    Economy/                 Price tables, upgrade Data Assets, crew Data Assets
    UI/                      Widgets, styles, fonts, CommonUI setup
    Audio/
    VFX/
    Test/                    Greybox test maps and dev-only assets (never shipped)
  Developers/                Personal scratch (already exists, keep it out of builds)
```

Naming: Unreal standard prefixes (`BP_`, `DA_`, `DT_`, `M_`, `MI_`, `SM_`, `SK_`, `T_`, `WBP_`,
`L_` for levels, `NS_` for Niagara, `IA_`/`IMC_` for input). Part assets: `DA_Part_Engine_V6Basic`.

## 4. Data-driven design

Everything the player can own, install, buy or find is a **Primary Data Asset** subclass so it can be
referenced by ID, loaded on demand via the Asset Manager, and listed in the editor.

```
UGTItemDefinition       : base for anything that sits in an inventory: name, icon, weight, stack size, base price
  UGTResourceDefinition : + where it spawns (hazard tag)
  UGTPartDefinition     : + slot, stat modifiers, mesh, damage params, rarity
  UGTToolDefinition     : + harvest tag it satisfies (Tool.Pry, Tool.Cut, Tool.Repair), use time, mesh, montage
UGTRecipeDefinition     : station tag, inputs (item + count), output (item + count), craft time
UGTUpgradeDefinition    : target (station tier / crew), tier, cost, effect
UGTLegDefinition        : level to load, leg number, par time, hazard set, conditions profile, rival par times
UGTCrewMemberDefinition : role, upgrade track, lines
```

Harvest nodes and wrecks are placed actors, not data assets, but each references a loot table
(Data Table of item + weight rows) and a required tool tag.

Weather states are also data assets (`UGTWeatherStateDefinition`), see Weather and wet materials.

Runtime state (what the player actually has) is plain `USTRUCT`s referencing those by
`FPrimaryAssetId`, held in a `UGTSaveGame`. This keeps saves small and lets you rebalance parts
without invalidating saves.

## 5. System boundaries

```
UGTGameInstance
  '- UGTRunSubsystem (GameInstanceSubsystem): owns "current campaign" state across level loads
        |- FGTCampaignState : current leg index, standings, currency, inventory, car loadout
        '- Save/Load via UGTSaveGame

Both levels:
  AGTPlayerController   : owns the possession swap. Possesses AGTCarPawn while driving and
                          AGTPlayerCharacter on foot. Both pawns always exist; the unpossessed one idles.
  AGTPlayerCharacter    : first-person camera + arms + UGTInteractionComponent + UGTInventoryComponent
                          + UGTExposureComponent + current tool
  AGTCarPawn            : Chaos wheeled vehicle + UGTPartSlotsComponent + UGTConditionComponent
                          + UGTInventoryComponent (boot). Implements IGTInteractable (enter, open boot,
                          repair a part with the repair tool).

Per-leg level:
  AGTRunGameMode        : spawns car + character with loadout, runs leg timer, checkpoints, extraction
  AGTRunGameState       : timer, checkpoint index, run-scoped state
  AGTHazardVolume       : base; AGTWeatherFront (moves), AGTRadiationZone (static)
  AGTHarvestNode        : IGTInteractable; requires a tool tag, takes time, rolls loot table
  AGTWreck              : AGTHarvestNode variant that yields parts and scrap; can also be a winch anchor
  AGTWinchAnchor        : IGTInteractable; strength rating, may fail under load

Per-level subsystem:
  UGTTrackPaintSubsystem: owns the track render target that follows the player and stamps wheel
                          contacts into it each tick (see Terrain and traction)

Base level:
  AGTBaseGameMode       : spawns car + character, reads/writes campaign state through the subsystem
  AGTCraftingStation    : IGTInteractable base; opens a station UI filtered by station tag
    BP_Workbench        : recipes tagged Station.Workbench
    BP_CarLift          : install / remove / repair / tune parts on the parked car
    BP_Trader           : buy / sell against price table
```

### Interaction

One interface, one component, every interactable:

- `IGTInteractable` exposes `CanInteract(Instigator)`, `GetPrompt()`, `GetHoldTime()`, `Interact()`.
- `UGTInteractionComponent` on the character traces from the camera each tick (first person makes
  this simple: you interact with what you look at), shows the prompt, and drives hold-to-use.
  The car has a simpler variant for in-seat interactions (exit, glovebox, gadget switches).
- Tool requirements are just a Gameplay Tag check inside `CanInteract`: node needs `Tool.Cut`,
  character's current tool grants `Tool.Cut`. No special-casing per node type.

### Enter / exit

- Exit: controller unpossesses the car, teleports the character to a clear exit socket, possesses
  the character, swaps `IMC_Driving` for `IMC_OnFoot`. Car keeps simulating physics and the
  handbrake engages. Cover the swap with a short camera blend from the seat camera to the
  character camera through the door position; a hard cut is acceptable for Tier 1.
- Enter: reverse. Character is hidden and collision-disabled rather than destroyed, so its
  inventory and state survive trivially.
- Build this in M2 on a test map and keep that map for the life of the project. Possession swaps
  are where jank lives.

Cross-system communication goes through the subsystem and **Gameplay Tags**, not direct
references between actors. Hazards apply effects by tag (`Hazard.Weather`, `Hazard.Radiation`),
parts grant resistances by tag, and the condition component resolves the result. This lets you add a
third hazard type without touching the car.

Consider the Gameplay Ability System (GAS) only if the tag/effect model outgrows a simple component.
For Tier 1 it's overkill; a `UGTConditionComponent` with a small effect list is enough.

## 6. Vehicle

The part layering, socket graph and compatibility rules are specified in
VEHICLE_BUILD_SYSTEM.md. This section covers physics, camera and cockpit.

- Enable the **Chaos Vehicles** plugin. Car pawn derives from `AWheeledVehiclePawn`.
- Part stats feed the Chaos movement component at spawn and on install (torque curve, mass,
  tyre friction, suspension params). Keep a `FGTVehicleTuning` struct that's rebuilt from installed
  parts, then applied in one place.
- Condition effects modify the same tuning struct (e.g. damaged suspension = softer springs on one
  side) so there's a single pipeline: parts -> tuning -> condition modifiers -> Chaos.
- Camera: first person, attached to a head socket on the driver's seat. Free look on the right
  stick / mouse with auto-recentre. Smooth the camera against chassis roll and pitch with tunable
  lag and a "stable horizon" option so rough terrain doesn't nauseate.
- Cockpit: a separate interior mesh with materials for gauge faces. Gauges are driven by a
  `UGTDashboardComponent` reading the condition component: needle rotations, warning lights, and a
  glass material that cracks with body damage. No screen-space HUD while driving except the leg
  timer and prompts.
- Damage must be visible from the seat: windscreen cracks, warning lights, steam from the bonnet,
  a wheel visibly wrong in the mirror later. Exterior damage still matters on foot and at the lift.

## 6a. Terrain and traction

Two systems share one source of truth: the **surface under each wheel**.

**Source:** every landscape layer and drivable mesh carries a `UPhysicalMaterial` subclass
(`UGTSurfacePhysMaterial`) with: friction scale, rolling drag, sinkage rate, max sinkage, track
depth, and a surface tag (`Surface.Mud`, `Surface.Snow`, etc.). Chaos already reports the physical
material per wheel contact, so no extra tracing.

**Gameplay (`UGTTractionComponent` on the car):**
- Per wheel, keeps a `Sinkage` value that rises while on soft ground (faster at low speed and under
  wheelspin) and falls on firm ground.
- Feeds the tuning pipeline: friction scale and rolling drag per wheel, so it goes through the same
  parts -> tuning -> condition -> Chaos path as everything else.
- Bogged state: two or more wheels over max sinkage and speed below a threshold. Throttle now
  digs deeper instead of moving. Exposed on the dash as a warning light.

**Visual (`UGTTrackPaintSubsystem`):**
- One world-aligned render target (say 128 m square) that re-centres on the player as they move,
  scrolling its contents so tracks behind you survive until they leave the window.
- Each tick, each wheel with sinkage above a small threshold stamps a soft brush at its contact
  point, depth scaled by sinkage and track depth. Tracks fade slowly via a decay pass.
- Landscape and soft-ground meshes sample the render target through a material function that
  outputs a rut normal and, where enabled, a displacement value. This function is the only place
  that changes if the displacement approach changes.
- Also drives spray/snow-kick Niagara emitters and tyre audio by surface tag.

Tier 2's "weather leaves mud behind" is a second, coarser render target the weather front paints
into, read by the same material function and the surface material's sinkage rate.

## 6b. Car body: damage, deformation, dirt and wet

**Regions.** The body is split into damage regions. Each region maps to the parts it protects, so
one impact event does everything: damage the parts, record a dent, update the panel.

| Region | Parts damaged | Visible consequence |
|--------|---------------|---------------------|
| Front | engine, radiator, headlights | steam, misfires, dark road at night |
| Front-left / front-right arch | that corner's suspension, tyre, steering | pulling, wheel visibly canted |
| Rear-left / rear-right arch | that corner's suspension, tyre | bounce, tyre blowout risk |
| Rear | fuel tank, boot storage, winch if rear-mounted | fuel leak, boot won't open |
| Doors / sides | armour, exposure seal | hazards leak into the cabin faster |
| Roof | armour, gadgets mounted up top | gadget failure |
| Glass | windscreen, windows | cracks, visibility, rain gets in |

`UGTConditionComponent` owns region -> part mapping. Impacts arrive from Chaos hit events with
a location and impulse; the component resolves the region from the hit location in car space.

**Deformation is procedural, not sculpted.** No per-panel morph targets.

- The car keeps a capped list of **impact records**: local position, radius, depth, direction.
  Target 32 slots. New impacts within a slot's radius merge into it (deepen) instead of taking a
  new slot; when the list is full the shallowest is dropped.
- The list is written to a small float texture on the car (one row per impact) and read by the
  body material, which pushes vertices inward along the surface normal with a smooth falloff per
  impact and perturbs the normal analytically from the same function so dents shade correctly
  without a normal recompute.
- Displacement path: **Nanite displacement if it's stable on static meshes in 5.8**, otherwise
  World Position Offset on a body mesh dense enough to bend (roughly 60–100k triangles for the
  shell is fine). This is the same spike as the terrain displacement question; answer both at once.
- Body panels stay **separate static meshes** attached to the vehicle. They share the impact
  texture so dents cross panel seams consistently, and a panel whose region health hits zero
  detaches and becomes a physics prop. Glass is its own mesh with a crack material driven by region
  health, not by displacement.
- Collision is never deformed. The visual dent is cosmetic; the mechanical effect comes from part
  health. Nobody notices, and it avoids Chaos instability.
- **Repair clears dents.** Repairing a part at the lift removes impact records inside its region;
  a field repair removes the deepest one. The impact list is saved with the campaign state, so the
  car looks the same after a load.

**Surface state** is one master body material with layered parameters, driven by
`UGTBodyStateComponent`:

- Dirt: per-region amount, masked by a baked height gradient so sills get filthy before the roof.
  Rises with wheel spray by surface tag (mud fast, dirt/gravel as dust, tarmac none). Falls in rain
  and at the base wash.
- Wetness: read from the global weather wetness (see Weather and wet materials), plus a local
  boost from puddles and spray, drying over time. Drives roughness, specular, and a drip normal.
  Uses Substrate's clear coat so paint, dirt and water layer properly; this is the main reason
  Substrate stays enabled.
- Snow: world-up mask on top surfaces, tied to the snow surface and weather.
- Windscreen: rain drops and streaks, mud throw-up, and wipers as a real mechanic driven by the
  electrics part. Wipers that die with damaged electrics is a designed hazard interaction.

Tier 2: paint splatter into the car's UV space with a render target for real spray patterns, and
a local scrape/scratch mask keyed off the same impact list.

## 6c. Environmental conditions

The environment of a leg acts on the car and the player as a system, not as scripted events.

- **Profile.** `UGTLegDefinition` carries a conditions profile: a set of condition tags
  (`Env.*`) with intensity curves along the leg, so a value can change as the player progresses
  (for example with altitude or time). `UGTEnvironmentComponent` on the car samples the profile
  at the car's position each tick and exposes the current values.
- **Effect on the car.** The tuning pipeline gains an environment stage:
  parts -> tuning -> environment modifiers -> condition modifiers -> Chaos. Most conditions are
  multipliers resolved from tags. Where a condition needs continuous state (something that
  accumulates and recovers), it gets a small model with sources and sinks inside the environment
  component. Keep those to one or two; everything else is a multiplier.
- **Effect on the player.** Conditions scale exposure drain on foot by tag.
- **Part answers.** `UGTPartDefinition` already declares resistance tags for hazards. Environment
  uses the same list: a part that counters a condition carries its tag and a strength. Consumables
  are items that grant a temporary resistance.
- **Readability.** Every condition drives a dash instrument or an in-cabin cue, using the
  dashboard component, and appears in the pre-departure briefing at the base. Briefing precision
  is a crew upgrade: low tiers show a coarse summary, high tiers show the intensity curves.
- **Failure.** Condition effects ramp: reduced performance first, then a warning, then part
  damage. No condition may take a part from healthy to dead without a readable window.

## 6d. Weather and wet materials

**Rule: every material in the project derives from a master material, and every master includes
`MF_Weather`.** No exceptions, including imported assets, which get reparented on import. This
is what makes rain affordable: wetness is one global parameter, not a per-material feature.

**Master material set** (aim for five, resist adding more):

| Master | Used for |
|--------|----------|
| M_Master_Environment | landscape layers, rocks, buildings, props, wrecks |
| M_Master_Foliage | grass, trees, with wind and subsurface |
| M_Master_Vehicle | car body panels (Substrate clear coat, dents, dirt, see Car body) |
| M_Master_Glass | windscreen, windows, headlights |
| M_Master_Character | first-person arms, tools |

Each takes the usual base colour / normal / roughness / metallic / AO inputs and hands the
result through `MF_Weather` before output.

**`MF_Weather`** reads `MPC_Weather` and applies, in order:
- Wetness: darkens base colour on porous surfaces (a per-material porosity scalar), drops
  roughness toward a wet value, blends a water normal with rain ripples on upward-facing surfaces.
- Puddles: on the environment master only, a puddle mask from a low-frequency noise gated by
  world-up and a per-instance "can pool" scalar, so puddles appear in dips and not on walls.
- Snow: world-up mask with per-material snow amount, blended over the wet result.
- Occlusion: a top-down capture (see below) masks wetness and snow to zero under cover.

**`MPC_Weather`** holds the globals the subsystem writes each frame: Wetness (0–1, rises fast in
rain, dries slowly), RainIntensity, SnowAmount, WindDirection, WindStrength, Temperature (drives
whether precipitation is rain or snow), and the occlusion capture's world bounds.

**`UGTWeatherSubsystem`** (world subsystem):
- Owns a state machine over `UGTWeatherStateDefinition` data assets: clear, overcast, rain,
  storm, snow. Each state has target values for the MPC, sky/cloud settings, and audio. The
  subsystem blends between states over a transition time.
- The weather front hazard doesn't own its own effects: it tells the subsystem "storm here" and
  the subsystem blends toward storm as the front approaches the player. Static legs without a
  front just pick a state.
- Drives the rain Niagara system, which is camera-attached (rain only exists around the player)
  and spawns drops, spray and ground splashes by intensity.
- Runs the **rain occlusion capture**: an orthographic scene capture pointing straight down from
  above the player, rendering depth only into a render target that re-centres with the player.
  Materials compare their world height against the captured depth to decide if they're under
  cover; the rain Niagara does the same to kill drops under roofs. This is cheap and standard,
  and it's what keeps the base garage dry.

**Weather feeds gameplay**, via the same sources everything else uses:
- `UGTSurfacePhysMaterial` gains wet grip and wet drag values. `UGTTractionComponent` lerps
  between dry and wet by global wetness, so wet tarmac is slick and wet dirt tends toward mud.
- Exposure drain on foot scales with RainIntensity and Temperature.
- The car body's wetness and windscreen rain read the same MPC values.

Tier 2 hooks: a flow map for water running down slopes, flood volumes that rise with wetness,
lightning strikes, wind forces on the car and character.

## 6e. Winch

- The winch is a `UGTPartDefinition` in a gadget slot that adds `UGTWinchComponent` to the car
  when installed: cable length, pull force, reel speed, and a `UCableComponent` for the visual.
- Rigging on foot: interact with the bumper to take the hook. The character carries it on a
  tether (walking past the cable length stops you). Interact with an `AGTWinchAnchor` to attach.
  Any wreck, tree or rock the level designer marks is an anchor; each has a strength rating.
- Reeling from the seat: hold Reel to apply a force along the cable toward the anchor, capped by
  pull force and the anchor's strength. Over-strength anchors snap, the cable whips, the winch part
  takes damage. Anchors can also be used deliberately: pulling a wreck off a node it blocks.
- The cable is a force, not a physics constraint. Constraints between a Chaos vehicle and a static
  body are a source of instability; a clamped spring force reads the same and never explodes.
- Letting go (VEHICLE_BUILD_SYSTEM 51): on foot, E empty-handed on the anchor the winch holds
  ("Detach winch hook", 0.5 s hold) or at the nose ("Release winch", 0.3 s); in the seat, Release
  Winch (G, DPad Up). All three call `Release()`: the hook is stowed and the pull stops at once;
  the drawn cable then runs back to the drum at `RewindSpeed` (500 cm/s, proposed) and hides.

## 7. Input

Enhanced Input (already enabled). Two Input Mapping Contexts in the code, `IMC_Driving` and
`IMC_OnFoot`; the controller swaps them on possession change. No `IMC_UI` is built: the results
screen's continue is Enter / pad Menu, bound on the controller. Brought to the code 2026-09-22
(`GTCarPawn.cpp` BuildDrivingMappings, `GTPlayerCharacter.cpp` BuildOnFootMappings); Recentre,
Headlights and Pause are not mapped.

- Driving: Throttle (W, Up; RT), Brake/Reverse (S, Down; LT), Steer (A/D, Left/Right; left stick
  X), Handbrake (Space; B), Look (mouse; right stick), Exit (F; Y), Reel winch (R hold; X), Camera
  (C; R3), Diff lock (X; DPad right), Low range (V; DPad down), Release winch (G; DPad up).
- On foot: Move (WASD; left stick), Look (mouse; right stick), Sprint (LShift; L3), Interact hold
  (E; A), Tool next/prev (wheel; DPad right/left), Inventory (Tab; View), Drop hook (G; X), Head
  bob (H), Transfer (T; Y), Jump (Space; B).
Rebinding via CommonUI's input settings later; don't hand-roll a rebinding screen.

## 8. Levels and streaming

One persistent level per leg, with sublevels for lighting/audio/geometry if the leg gets large.
World Partition is fine for a leg if it's big, but a leg is bounded by design so start without it.
Legs and base are loaded with `OpenLevel`; campaign state (including both inventories and the
car loadout) survives because it lives in the Game Instance subsystem.

## 9. Save system

- `UGTSaveGame` holds `FGTCampaignState` and a version number.
- Save on arriving at base and on leg completion. No mid-leg saves in Tier 1 (a leg is a "run").
- Slot 0 only for now; add slots in M7 if wanted.

## 9a. Player character and animation

- First person: a `UCameraComponent` on a `UCharacterMovementComponent` capsule, plus a
  first-person arms skeletal mesh attached to the camera. Start from Epic's First Person template
  arms and swap the rifle for tool sockets. No full-body mesh, no shadow body.
- Tool use is a short arms animation per tool (swing, cut, wrench). A static hold pose with a
  timed progress ring is the Tier 1 fallback if animation time runs out.
- Head bob and sprint FOV kick are procedural on the camera, each with an options toggle.
- `UGTExposureComponent` is a single 0–100 meter. Hazard volumes drain it by tag; the car and base
  restore it. Hitting zero forces a "drag yourself back to the car" fail state, not death.

## 10. Rendering settings

The blank template enabled hardware ray tracing, Lumen (GI method 1, reflection method 1),
Substrate materials, and Virtual Shadow Maps. Recommended for this project:

- Keep Lumen and VSM.
- **Turn off `r.RayTracing`** until there's a reason to need it. It raises shader compile times and
  the min-spec, and Lumen software GI already gives the look.
- Substrate: decide now. Keeping it is fine, but many Fab/marketplace materials are non-Substrate
  and get converted on import, which occasionally misbehaves. If in doubt, disable it now; enabling
  later is easier than disabling later.

## 11. Plugins to enable at M0

- ChaosVehiclesPlugin (and add `ChaosVehicles` to Build.cs dependencies)
- CommonUI (already configured in DefaultGame.ini)
- GameplayTags (engine, on by default)
- Niagara (on by default)
- PCG (defer to Tier 2 unless greyboxing wants it)
- ModelingToolsEditorMode (already on; useful for greyboxing)

## 12. Version control

- Git with Git LFS for `.uasset`, `.umap`, and binary media. `.gitignore` and `.gitattributes`
  are in the project root.
- Commit `Config/`, `Content/`, `Source/`, `*.uproject`, `docs/`. Never commit `Binaries/`,
  `Intermediate/`, `Saved/`, `DerivedDataCache/`, `.vs/`, or generated `.sln` files.
- One branch (`main`) until there's a reason for more. Tag milestone builds (`m1-driving`, etc.).

## 13. Testing

- Automation tests in C++ for the pure-data systems: inventory maths and transfer, part slot rules,
  recipe validation (inputs available, output fits), price calculation, save round-trip. These are cheap and catch the bugs that are miserable to find in play.
- Everything else is play-tested. Keep `Content/GrandTour/Test/` maps for isolated tests
  (car on flat plane, one hazard volume, etc.).
