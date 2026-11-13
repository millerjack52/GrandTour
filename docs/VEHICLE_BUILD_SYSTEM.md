# Vehicle build system

Status: design, 2026-09-08. Replaces the "one body + kits" and "sectional body" experiments in
`Art/Blender/`. Referenced from ARCHITECTURE.md section 6.

## 1. What went wrong, and the rule that fixes it

Every attempt so far (extruded slab kit, lofted subsurf body, monolithic truck, sectional body
with join planes, two families of sections) tried to **generate the car's skin from code**. A car
skin is the one thing scripts are bad at: it is a single continuous surface that has to read as a
car from every angle, and every section boundary is another place for it to go wrong. Hand
modelling a full body hit the same wall from the other side.

The rule for this system: **scripts build structure and bolt-ons, never skin. Skin is one shell,
obtained once and cut into panels by a script.** Everything the player swaps is either structure
(boxes, tubes, plates, which scripts do well), a cut of that one shell, or a self-contained
accessory that sits on a socket and does not need to blend into anything.

This is also why Slate Auto works: the base truck is deliberately slab-sided so accessories bolt
onto flat faces and hard seams. We copy that.

**There is one car.** One chassis, one frame, one shell. The player never swaps into a different
car; they change what is bolted to the one they have. Attachment comes from the car staying the
same object underneath every rebuild: same cage, same dent history, same engine they have been
nursing. Silhouette variety comes from rear modules, ride height and accessories, not from
frames.

## 2. Layers

Bottom to top. Each layer only knows about the sockets of the layer below it.

| Layer | What it is | Who authors it | Player swaps |
|---|---|---|---|
| L0 Chassis | Ladder rails, crossmembers, floor, engine bay, hub mounts, tank cradle. The Chaos vehicle pawn. | Script | Never |
| L0 Running gear | Suspension (ride height, travel), wheels + tyres (radius, width, offset), fuel tank | Script | Yes |
| L1 Engine | Block in the bay with sub-sockets: intake, exhaust, turbo, radiator, electrics | Script | Yes, engine and sub-parts |
| L2 Frame | Cage + floor + stations that fix the silhouette. Boxy, Range Rover Classic / Defender / Slate proportions. | Script | Never |
| L2 Rear module | Pickup bed or wagon (SUV) behind the cabin | Script + shell cut | Yes |
| L3 Panels | Nose, bonnet, wings, doors, roof, rear quarters, tailgate, glass. These are the damage panels. | One shell, cut by script | Yes, per panel |
| L4 Accessories | Racks, bars, lamps, cladding, sliders, snorkel, spares, cap, tonneau, cans | Script | Yes |

### L0 Chassis
- Fixed geometry: wheelbase 2.60 m, track 1.60 m, bay envelope 0.9 x 0.7 x 0.6 m. Range Rover
  Classic is 2.54 m; Slate is 2.8 m.
- Provides sockets: `Hub_FL/FR/RL/RR`, `Bay`, `Tank`, `Frame_Mount` (pattern of 6 points),
  `Bumper_F`, `Bumper_R`, `Under_F`, `Under_R`, `Sill_L/R`, `Exhaust_Out`.
- Visible from underneath, from the lift, and wherever panels are missing. Mechanical greeble only:
  rails, crossmembers, tank, driveshaft, exhaust run. Never needs to look like a car.
- Owns the Chaos setup. Wheel positions come from `Hub_*` plus the installed suspension and wheel
  offsets. Frame and panels never move a wheel.
- Built 2026-09-08 by `chassis.py` to the user's Land Rover Series brochure: box-section ladder
  frame (rails at x = 0.45, top at z = 0.58, seven crossmembers, six body outriggers, spring
  hangers, front bumper), live axles with offset diffs on leaf springs with dampers, steering box,
  drag link, track rod and column, steel wheels (r 0.41), fuel tank between the rails, exhaust
  with silencer down the right rail, battery. The engine (`Engine` collection: block, sump, head,
  rocker cover, timing cover, fan, water pump, intake and exhaust manifolds, carburettor, air
  filter, dynamo, distributor, starter, radiator with header tank and hoses, bell housing,
  gearbox, transfer box, both propshafts with UJs, gear and transfer levers) sits down between
  the rails behind the front axle so it clears the bonnet. The body drops onto the frame with
  `BODY_LIFT = 0.06`, so the shell floor sits between the rails rather than on top.

### L0 Running gear
- **Suspension is the clearance part.** Each suspension part sets ride height offset, travel and
  stiffness. Longer-travel suspension lifts the whole frame and body by its offset, so arch
  clearance grows with it and bigger tyres become legal. Tiers: stock (0 mm, short travel),
  heavy duty (+50, medium), long travel (+100, long, softer), and a rally set (+120, long,
  stiff rebound). A Dakar build is the same car on long-travel suspension, which is also how
  the real ones get their clearance.
- **Wheels** carry tyre radius, width, offset (stance) and the visual (alloy, steel, knobbly,
  rally). Bigger tyres need arch clearance, which is the one numeric rule in the system.
- **Tank** sets capacity and mass at the rear.

### L1 Engine
- The engine is a part that plugs into `Bay` and **provides its own sub-sockets**: `Intake`,
  `Exhaust_Manifold`, `Turbo`, `Radiator`, `Electrics`. Sub-parts change stats and are visible
  with the bonnet open.
- Engines have a **size class** (S, M, L). The bay takes all three, but the bonnet station has a
  height allowance that takes S and M only, unless a `Bonnet_Scoop` panel is fitted, which raises
  the allowance to L. This is the model for every incompatibility in the game: a wall with a
  door, not a wall.

### L2 Frame
- The frame is what stays on the car when panels come off. It is the shell's own structural
  skin (floor pan, the cladding band below the sill line, the B pillar strips, the windscreen
  surround), the interior (this model's pillars above the belt line are part of the interior
  mesh), and scripted structure behind them: inner sills, bulkhead, scuttle, inner wings, four
  wheel-arch tubs, transmission tunnel. Roof height 1.85 m, belt 1.30, sill 0.70, arch radius 0.50.
- It is not a part. It is never removed, sold or replaced. Rigidity (damage spread between
  regions) and base armour live on panels and armour parts, not on the frame.
- **There is no tube cage in the frame.** The first attempt put one there and it showed through
  the glass. A roll cage is an accessory (`Acc_RollCage`) that sits inboard of the glass line.
- The cabin seam is followed by the rear module socket `SOCKET_Rear`, which takes **Wagon** (the
  shell's own rear panels plus a tailgate sill; exposes `SOCKET_Roof_Rear`, `SOCKET_Tailgate`) or
  **Bed** (pickup: cab back wall with window, floor, sides with wheel wells, tailgate, valance;
  exposes `SOCKET_Bed_Top`, `SOCKET_Bed_Cage`, `SOCKET_Tailgate`). A lower, sportier look would
  be a third rear module on the same frame, not a new frame.
- The frame also carries `SOCKET_Roof_Front`, `SOCKET_Snorkel`, `SOCKET_Sill_L/R`,
  `SOCKET_Arch_FL/FR/RL/RR`, `SOCKET_Cage`, `SOCKET_Bonnet_Lamps`.

### L3 Panels
- One **shell**, hand-made once or acquired (low-poly, flat-shaded, which matches the locked
  style; see section 9). The shell is scaled to the 2.60 m wheelbase, placed on the frame, and
  `cut_panels.py` bisects it on the frame's seam planes into named panels, each pivoted at its
  frame station socket.
- Panel list (as cut on 2026-09-08 by `cut_panels.py`): `Nose`, `Bonnet`, `Wing_L/R`,
  `Door_F_L/R`, `Door_R_L/R`, `Roof`, `Quarter_L/R`, `Roof_Rear`, `Tail`, `Glass_Front`,
  `Glass_Side_L/R`, `Glass_Quarter_L/R`, `Glass_Rear`. Everything behind the cabin seam
  (`Quarter_*`, `Roof_Rear`, `Tail`, `Glass_Quarter_*`, `Glass_Rear`) is the wagon rear module;
  the bed comes from the bed script. Loose trim (grille, lamps, mirrors, handles) is parented to
  the panel whose region contains it.
- **Frame skin.** The cut also peels off the parts of the shell that are structure, not panel:
  the floor pan, both sills (everything below the sill line), the B and C pillar strips, and the
  windscreen surround. These are `SM_FrameSkin_*` and never leave the car, so a door hole is
  bounded by a sill and two pillars rather than being a hole in the side.
- Panel **variants** are local edits of one cut panel, never a new shell: `Bonnet_Scoop`,
  `Bonnet_Vented`, `Door_Cutaway`, `Roof_Sunroof`, `Wing_Flared`. Each is an hour of work, not
  a week.
- Panels are the damage panels from ARCHITECTURE.md (separate static meshes sharing the impact
  texture; detach at zero region health). Nothing there changes.

### L4 Accessories
Self-contained meshes at socket transforms. They do not have to blend into the body, which is
why scripts can build them. Grouped by the socket they need:

| Socket | Accessories |
|---|---|
| `Roof_Front` (frame), `Roof_Rear` (wagon or cap) | Light bar, roof rack (takes both), roof tent (takes both), spare wheel, sand ladders |
| `Bumper_F` | Bull bar, winch bumper (adds `Winch`), lamp pod pair |
| `Bumper_R` | Tow bar, jerry can carrier, swing-out spare |
| `Under_F` | Skid plate |
| `Sill_L/R` | Rock sliders, side steps, side-mounted sand ladders |
| `Arch_*` (frame, has radius) | Cladding narrow / wide, flare, mud flap |
| `Snorkel` (frame) | Snorkel (requires the intake sub-socket to accept it) |
| `Bed_Top` | Cap (adds `Roof_Rear`), tonneau, cage |
| `Bed_Cage` | Spares, cans, tool boxes |

Cladding is the one accessory that must follow the body: it is generated parametrically from the
arch socket's radius and the chosen width.

## 3. Sockets and compatibility

Everything installable is a `Part`. A part declares:

```
Requires : socket type, plus optional constraints (size class, clearance)
Provides : sockets it exposes once installed (type, transform, size class, group)
Occupies : occupancy groups it consumes (a rack takes Roof_Front + Roof_Rear)
Envelope : local bounding box used for clearance checks
Stats    : contributions to FGTVehicleTuning (mass, CoG, drag, armour, capacity, etc.)
```

Four rule kinds, resolved at install time at the car lift. The lift UI always says **why** a part
does not fit and, where there is one, **what would make it fit**.

1. **Socket type.** A rack needs `Roof_*`. A pickup with no cap has no `Roof_Rear`, so a full rack
   will not fit until a cap is on. Fit the cap, the rack fits.
2. **Occupancy.** One part per socket, and groups for parts that span sockets. Light bar and roof
   tent both want `Roof_Front`; pick one.
3. **Envelope / clearance.** The numeric rules, kept to three:
   - Tyre: `arch_radius + lift - tyre_radius >= 0.05 m`, and `tyre_width <= cladding_width`.
     Long-travel suspension with wide cladding takes a 33-inch knobbly; stock does not.
   - Engine: `engine_height <= bay_height + bonnet_allowance`. Scoop bonnet raises the allowance.
   - Roof load: `sum(roof accessory mass) <= roof rating`. A tent needs the wagon rear or a cap,
     because the frame's own `Roof_Front` rating is too low on its own.
4. **Dependency.** A turbo needs an engine that provides `Turbo`. A snorkel needs an intake
   sub-part with the `Snorkel_OK` tag. A winch needs the winch bumper. Removing a provider ejects
   its dependants into the inventory.

Rules 1, 2 and 4 are tag matching. Rule 3 is three inequalities. The resolver is small enough
to live in C++ with the other invariants (a part fits one socket, no orphaned dependants).

## 4. Example builds

| Look | Rear | Running gear | Engine | Accessories |
|---|---|---|---|---|
| Slate SUV | Bed + Cap | Stock, alloys | M | Light bar |
| Expedition wagon | Wagon | Heavy duty +50, 31" knobbly | M + snorkel intake | Rack, snorkel, bull bar, skid plate, spare on tailgate |
| Prerunner | Bed + Cage | Long travel +100, 33" knobbly, wide cladding | L + `Bonnet_Scoop` | Lamp pods, sliders, spares in cage |
| Dakar | Wagon | Rally +120, 31" knobbly, wide cladding, offset wheels | M + turbo | Rack with spares + ladders, lamp pod, skid plate, mud flaps |
| Stripped racer | Bed, no cap | Stock, steelies | L + `Bonnet_Scoop` | Doors and bonnet removed; cage and engine on show |

The Dakar is not a special kit. It is what falls out when the rally suspension raises the arch
clearance enough for wide cladding and knobblies under the same three rules as everything else.

## 5. Physics and tuning

The body affects driving only through `FGTVehicleTuning` contributions, so the existing pipeline
(parts -> tuning -> environment -> condition -> Chaos) is untouched:

- Suspension: ride height, travel, spring and damper rates, CoG height (lift raises it, which is
  the cost of clearance).
- Rear module: mass at the rear, roof rating change (wagon adds roof, cap adds roof).
- Panels: mass and armour per region; a missing panel exposes its region's parts.
- Accessories: mass at their socket transform, drag, and tags (winch, lamps, snorkel wading depth).
- Engine, wheels and tank: as already designed.

Collision stays a fixed hull for the frame plus a box per rear module. Accessories add no
collision except the bull bar and skid plate (they exist to take hits).

## 6. Blender authoring pipeline (as built, 2026-09-08)

All in `Art/Blender/`. One command rebuilds everything from the Poly Pizza GLB, so nothing is
hand-edited and any station or part can be changed and rebuilt:

```
import build_car; build_car.build()      # -> Car.blend, 46 parts, one mesh each, stock config shown
build_car.preview("expedition")          # verification renders to the scratch folder
build_car.export()                       # -> Art/Export/SM_*.fbx + parts_manifest.json
```

| Module | Job |
|---|---|
| `build_car.py` | Orchestrates: fresh GLB import scaled to WB 2.60 with axles at y = -1.3 / +1.3 and tyres on z = 0, then cut, materials, frame, chassis, rear modules, accessories, finalize. `CONFIGS` holds the demo builds (stock, stock_rack, expedition, pickup_cap, prerunner, stripped). |
| `cut_panels.py` | Seam stations measured on the model (A post -0.65, B pillar 0.39, cabin seam 1.05, tailgate 2.05, cladding top 0.70, bonnet line 1.05, belt 1.30, drip 1.62) and the bisect tree. Validates area conservation and no empty piece. |
| `materials.py` | Palette texture to flat materials: every face sampled at its UV, shades merged to 23 colours, no texture left in the file. `M_Body_Paint`, `M_Body_Cladding`, `M_Glass` are named for the game to address. |
| `frame.py` | Frame structure, frame skin, interior split at the cabin seam, frame sockets, and the panel PartSpecs with hinge pivots (doors at their leading edge, bonnet at the scuttle, tailgate at the top). |
| `chassis.py` | Ladder chassis, engine with sub-sockets, four suspension tiers (spacer block and longer dampers per lift, propshafts re-angled), steel and knobbly wheels. |
| `rear_modules.py` | Wagon and Bed modules. |
| `accessories.py` | LightBar, RoofRack and RackBag (the model's own, CC-BY), JerryCans, Snorkel, RockSlider_L/R, SpareWheel, RollCage, BullBar, SkidPlate, Cap. |
| `carlib.py` | PartSpec, join-to-one-mesh with pivot, root hierarchy, sockets, `apply_config`, render helper, FBX export and manifest. |
| `kitlib.py` | Primitive helpers shared with the earlier scripts. |

Rules carried over from the earlier attempts (they still apply):
- Booleans use the MANIFOLD solver only. `bisect_plane(clear_outer=True)` removes the normal side.
- Validate before rendering: area conserved by the cut, no empty mesh, every socket present in
  the manifest. Never send diagnostic views (exploded parts, debug colours); send the assembled
  car with its materials.
- Call `view_layer.update()` before parenting anything to a freshly created object, or the
  child's world matrix is computed against a stale parent and it floats away.
- Style: hard-edged low-poly, flat shaded, no textures. The shell is decimated to that by the
  material flatten; scripted parts are built that way.

**Root hierarchy** (Blender and Unreal alike):

```
Vehicle_Root       ground contact centre; z = tyre radius - 0.41 so bigger tyres lift everything
  Chassis_Root     z = suspension lift (0 / 0.05 / 0.10 / 0.12)   -> SM_Chassis, SM_Engine, chassis accessories
    Body_Root      z = BODY_LIFT 0.06 (SOCKET_Body on the chassis) -> SM_Frame, panels, glass, interior,
                                                                      rear modules, body accessories
  Suspension_Root  z = 0                                          -> SM_Suspension_<tier> (axles never move)
  wheels           at the hub positions, right side yawed 180
```

**Export contract** (`Art/Export/parts_manifest.json`): one FBX per part, mesh at its pivot,
`SOCKET_*` empties as children (Unreal makes static-mesh sockets from them). Every part is
rotated +90 degrees about Z at export so the car faces +X, Unreal's vehicle forward; manifest
positions are in that frame, metres. Fields per part: `group`, `space` (vehicle / chassis /
body / suspension), `pivot_m`, `requires` (socket), `provides` (sockets with local positions),
`depends`, `occupies`, `tags` (`wagon`, `bed`, `lift:x`, `tyre_r:x`), `mass_kg`, `triangles`,
`materials`. Total 26k triangles for all 46 parts. Assumption to verify on the first Unreal
import: if the car faces sideways, change `carlib.EXPORT_YAW`.

## 7. Unreal data model

Extends what is in ARCHITECTURE.md rather than replacing it:

- `UGTPartDefinition` gains `Requires` (socket type + constraints), `Provides` (array of
  `FGTSocketDef`: type, relative transform, size class, group), `Occupies` (gameplay tags) and
  `Envelope` (box). The existing `slot` field becomes the `Requires` socket type, so engine /
  tyres / suspension / armour / gadgets are unchanged in spirit.
- `UGTPartSlotsComponent` becomes a socket graph: root sockets from the chassis and frame, each
  installed part adds its provided sockets as children. Install = attach the part's mesh
  component to the socket transform. Remove = detach the part and everything hanging from its
  provided sockets.
- `UGTBuildRules` (C++, static functions): `CanInstall(part, socket, graph) -> FGTFitResult`
  with a reason enum and an optional "would fit if" hint. Used by the lift UI and by the wreck
  loot roll so found parts are never unusable forever.
- Save: the graph is a list of `(socket path, part id)` pairs, which fits the existing
  `FPrimaryAssetId` save shape.

## 8. Scope

This replaces "one car body" in PROJECT_PLAN tier 1, not adds to it. The *system* is cheap: one
resolver, one manifest importer, socket-based attachment. The *content* is where the time goes,
so it is tiered:

| Tier | Content | Estimate |
|---|---|---|
| 1 (ship) | Chassis, frame, one shell cut into panels, Bed + Wagon, suspension stock + heavy duty, 3 wheels, 1 tank, engine M with 2 sub-part choices each, 8 accessories (rack, light bar, bull bar, skid plate, sliders, cap, tonneau, spare) | 3 weeks of art alongside M6 |
| 2 | Long travel + rally suspension, wide cladding, lamp pods, ladders, mud flaps, engines S and L, scoop bonnet, snorkel, turbo, wheel offsets | 1–2 weeks |
| 3 | Panel variants, roof tent, tow bar, jerry cans, second engine family, a third rear module | as time allows |

Tier 1 is one car with kits, exactly what the plan promised. Tier 2 is where the Dakar build
arrives, and it is all running gear and accessories on sockets that already exist.

## 9. Assumptions to check

- **A shell can be acquired.** Done: "Range Rover" by IvOfficial on Poly Pizza (CC-BY, credit
  required), in `Art/Blender/ref/polypizza_rangerover/`. Scaled 0.74 to the 2.60 m wheelbase,
  cut into 20 panels with area conserved exactly; result in `Art/Blender/Shell_Panels.blend`
  and `Shell_Panels_manifest.json`. Still to do: replace the palette texture with flat
  materials, and set panel pivots at hinge points once the frame sockets exist.
- **Cut panels still take the impact displacement.** Cutting the shell into 23 panel and glass
  meshes must not break the shared impact texture. It should not, since panels were always
  separate meshes, but the M1 displacement spike should be done on the cut set, not a single body.
- **Export axes.** `EXPORT_YAW` = +90 about Z is expected to give +X forward in Unreal with
  Unreal's default FBX import. Check on the first import.
- **Lift alone reads as a Dakar.** The real Dakars sit high on long-travel suspension with wide
  arches, and the reference renders (959, Range Rover) are both boxy enough that +120 mm with
  cladding and a rack should carry it. If it still reads as "the same truck," the answer is
  accessory silhouette (rack, spares, lamps), not a second frame.

## 10. Body modelling brief (hand-modelled body around the chassis)

> Historical (2026-09-11): `Chassis_Jig.blend`, `build_car.py` and `cut_panels.py` are gone from
> `Art/`. The numbers below were fixed by the scripted chassis; the hand-modelled body in section 12
> now fixes them.

Decision 2026-09-08: the scripted chassis stays; the body is modelled by hand around it. Open
`Art/Blender/Chassis_Jig.blend`: rolling chassis, engine, stock suspension, steel wheels, and a
`Jig` collection of wireframe station planes and keep-out volumes. Model in that file's world
space (ground at z = 0, front is -Y, left is +X) and everything below still fits.

**Fixed by the chassis (metres)**

| Item | Value |
|---|---|
| Wheelbase / track | 2.60 / 1.60, hubs at y = -1.30 and +1.30, x = +-0.80, z = 0.41 |
| Tyres | steel 0.41 radius x 0.26 wide; knobbly 0.4425 x 0.30; suspension lifts 0 / 0.05 / 0.10 / 0.12 |
| Arch clearance to leave | radius 0.50 round each hub, 0.40 wide (the red cylinders); a lifted knobbly reaches z 0.97 |
| Frame rails | x = +-0.45, top at z 0.58; outriggers reach x = +-0.88 |
| Body floor | sits at z 0.49 between the rails (SOCKET_Body on the chassis is at z 0.06 above the frame origin) |
| Engine bay | block behind the front axle, top at z 1.06, radiator face at y -1.86; bonnet needs z >= 1.12 |
| Bulkhead / A post | y = -0.65 |
| Steering wheel (RHD) | centre x -0.43, y -0.20, z 1.20; seat H-point socket at (0, 0.15, 0.64) |
| Frame ends | y = -1.98 front horns (chassis bumper to -2.10), y = 2.25 rear crossmember |
| Exhaust outlet | x -0.72, y 2.30, z 0.44 |
| Chassis sockets | Bay, Tank, Bumper_F (0, -2.10, 0.54), Bumper_R (0, 2.25, 0.54), Under_F (0, -1.45, 0.49), Exhaust_Out, Body, Seat |

**Stations the part system expects** (yellow and cyan planes in the jig; move them if the new
body wants different lines, then update `cut_panels.py` to match): nose -1.85, A post -0.65,
screen top -0.30, B pillar 0.39, cabin seam 1.05 (rear module socket), tailgate 2.05, rear end
2.41; sill top 0.76, bonnet line 1.11, belt 1.36, drip rail 1.68, roof 1.91; side skin at +-0.90.

**How to build it so the pipeline takes it as-is**

- Model half the body, Mirror modifier with clipping, hard edges, flat shading, no textures.
  Put a loop cut at every station above so panel edges land on the shut lines.
- Keep the outer skin, the floor pan, the sills below the sill line, the pillar strips and the
  windscreen surround as separate objects (or separate them at the end): those are the frame
  skin. Everything else splits into the panel set (nose, bonnet, wings, four doors, roof,
  quarters, rear roof, tail, glass per opening).
- Name the pieces `CUT_<name>` using the names in `cut_panels.py` and put them in a collection
  called `Cut`; `build_car.build()` can then skip the cut and use them directly (a small switch
  to add when the body exists).
- Wheel arches: boolean a cylinder (MANIFOLD solver) of radius 0.50 at each hub, then close the
  opening with a tub. Glass is its own faces with `M_Glass`.
- Accessories mount on frame sockets. If the new body moves the roof, sills or A pillar, update
  `frame.SOCKETS` and the accessories follow.

## 11. Range Rover body (scripted from the user's four-view reference, 2026-09-09)

> Historical (2026-09-11): `rr_body.py` and `RangeRover_Body.blend` are gone from `Art/`; the user
> rejected the scripted body and modelled their own (section 12).

`Art/Blender/rr_body.py` builds a Range Rover Classic 4-door body and a basic interior directly
on the chassis, box-modelled from the reference blueprints: solid union of front box, cabin box and
greenhouse frustum, sharp exterior edges bevelled (roof cap 4.5 cm, everything else 2 cm), hollowed
with cabin / greenhouse / engine-bay voids, wheel arches cut with cylinders (tub walls kept), window
openings cut through the greenhouse walls, then bonnet, castellations, grille, lamps, indicators,
bumpers, mirrors, handles, shut lines, rub strips, roof ribs, wipers, tail lamps, plate, and the
interior (dash, binnacle, console, tunnel, two seats, bench, door cards, headliner, pedals; the
steering wheel and levers come from the chassis). Result: `Art/Blender/RangeRover_Body.blend`
(body + chassis + jig), and `Art/Export/SM_RR_Body.fbx`, `SM_RR_Glass.fbx`, `SM_RR_Interior.fbx`.

Stations measured from the reference (chassis space, ground z = 0): nose face -1.87, front bumper
to -1.99, A post -0.70, screen top -0.41, B pillar 0.27, rear door edge 1.27, rear glass top 1.98,
rear glass base 2.28, tail 2.33, rear bumper 2.46; sill 0.31, bumper 0.43-0.57, bonnet 1.11, belt
1.27, drip 1.68, roof 1.77; body +-0.90, greenhouse +-0.88 at the belt to +-0.76 at the drip. Cabin
floor at 0.60 clears the chassis rails; the engine top (1.06) clears the bonnet underside (1.08).

Not yet done for this body: the panel cut (its stations differ from the Poly Pizza shell's, so
`cut_panels.py` needs A post -0.70, B pillar 0.27, seam 1.27, tail 2.33, sill 0.31 and a
BODY_LIFT of 0 before the pipeline can split it), and 8-hole wheels to match the reference.

## 12. Hand-modelled Range Rover blockout and the Unreal pipeline (2026-09-11)

The scripted chassis, jig and `rr_body.py` from sections 10 and 11 no longer exist on disk.
The user's hand-modelled blockout `Art/rangerover.blend` is the source of truth, and the body
now fixes the numbers the chassis used to fix:

| Item | Value (Blender space, metres) |
|---|---|
| Overall length / width / height | 4.61 / 1.86 / 1.79 (real 108-inch LSE: 4.65 / 1.82 / 1.79) |
| Wheelbase / track | 2.751 / 1.568; hubs at y = -1.602 (front) and +1.149 (rear), x = +-0.784, z = 0.38 |
| Tyre | radius 0.38, width 0.248 (real 205R16 is ~0.37) |
| Vehicle origin | body length centre, 0.226 behind the axle midpoint. Undecided; move the whole model +0.226 in Y if you want the axle-midpoint convention. The export follows the file. |
| Conventions | metres, ground z = 0, front -Y, left +X, half modelled with Mirror modifiers, flat shaded, no materials |

**Object rules the exporter relies on**

- Every mesh object outside the `Reference` and `Jig` collections is a part. Names must be
  unique after stripping Blender's `.001` suffix (the exporter appends a number and warns).
- Wheel objects start with `wheel` (any case); their corner comes from position, not name.
- Objects with fewer than 4 faces are skipped (stray quads, empty meshes).
- Placeholder material by name: `interior` -> M_Interior, `pillar` / `bumper` -> M_Trim,
  wheels -> M_Wheel, everything else M_Body. Unreal creates those slots.
- A part with no vertex within 2 cm of x = 0 and geometry on both sides is a mirrored pair
  and is also exported as `_L` / `_R` static meshes.

**Export: `Art/export_rangerover.bat`** (save the .blend first; the script reads the file on
disk and never writes it). It runs headless Blender with `Art/Blender/export_rangerover.py`:
bake Mirror, Merge by Distance at 1 mm, rotate +90 deg about Z so the nose is +X, scale to
centimetres with the scene unit scale set to 0.01 so the FBX exporter adds no scale of its own
(leaving the scene at metres made everything 100x too big in Unreal), default FBX axes.
Skeleton: `Root` at the origin, `Wheel_FL` / `Wheel_FR` / `Wheel_RL` / `Wheel_RR` at the hubs
(bones point along the car's left, +Y in export space, which imports as an identity bone
rotation; bones pointing up import with a 90 degree roll and break Chaos, see below), body
parts skinned rigidly to Root, each wheel to its bone. The armature
object is named `Armature` and the meshes are not parented to it: both Unreal FBX importers drop
Blender's armature null only under exactly those conditions, otherwise it becomes an extra root
bone. Output in `Art/Export/`: `SK_RangeRover.fbx`, `Static/SM_RR_<Part>.fbx` (origin at the
vehicle origin; `SM_RR_Wheel` has its origin at the hub) and `manifest.json` (hubs in Unreal cm,
wheel radius and width, warnings about doubles, internal faces and names).

**Import: `Art/import_rangerover.bat`** (close the editor first) or drag the FBX files into the
Content Browser. Destination `Content/GrandTour/Vehicles/Bodies/RangeRover` for the skeletal
mesh and skeleton, `.../RangeRover/Panels` for the static meshes. Verified in UE 5.8 on
2026-09-11: bounds 461 x 186 x 179 cm, bones at (160.2, -78.4, 37.9) FL, (160.2, 78.4, 37.9) FR,
(-114.9, -78.4, 37.9) RL, (-114.9, 78.4, 37.9) RR, so front is +X and left is -Y; every bone at
scale 1; slots M_Body, M_Trim, M_Wheel; the import does not create a physics asset. Renaming an
object in Blender leaves the old static mesh behind; the import script lists those as stale.

**Unreal side (done 2026-09-11, verified headless)**

- `Art/setup_m0.bat` (`Art/Unreal/setup_m0.py`): creates `SK_RangeRover_PhysicsAsset`, removes the
  four wheel bodies and their constraints, fits one box round the body (X -229..232, Y +-93,
  Z 39..179 cm) and builds `Content/GrandTour/Test/L_DriveTest` (400 m floor, sun, sky, fog,
  PlayerStart). Re-run after any re-import that changes the skeleton: it refits the box from the
  reference pose and leaves an existing map alone. Body setups are not reachable from Python and
  the editor actor subsystem crashes in a commandlet, so `UGTVehicleSetupLibrary` (C++) does the
  physics edits and the actor spawning.
- C++ in `Source/GrandTour/Vehicle` and `Source/GrandTour/Core`:
  `AGTCarPawn` (WheeledVehiclePawn: SK_RangeRover, wheel setups on `Wheel_FL..RR`, 2100 kg,
  torque curve, four-speed automatic with auto reverse, 4WD, centre of mass (22.6, 0, 60), driver
  camera at (10, 40, 135) with free look and auto-recentre, Enhanced Input built at runtime when
  no input assets are assigned: W/S or triggers, A/D or left stick, Space or B handbrake, mouse or
  right stick look); `UGTVehicleWheelFront` / `Rear` (38 cm radius, 25 cm wide, 35 degree steer,
  rear handbrake); `UGTVehicleAnimInstance` (poses the wheel bones from the Chaos wheel state in
  code, same maths as the Wheel Controller node, so no Animation Blueprint is needed yet);
  `AGTDriveTestGameMode` (default pawn is the car; with `-GTDriveTest` it holds full throttle for
  8 s, logs GTDRIVETEST lines and quits).
- `Config/DefaultEngine.ini`: EditorStartupMap and GameDefaultMap are L_DriveTest and
  GlobalDefaultGameMode is GTDriveTestGameMode. Change these when the real game mode exists.
- `Art/drive_test.bat`: the headless proof. Result 2026-09-11: PASS, 0 to 73 km/h in 7 s, 1-2
  shift at 3950 rpm, dead straight, 79.6 m in 8 s, car settled at z = 2 cm.
- Traps found on the way: Chaos treats the root body's frame as the vehicle frame, so the root
  bone must import with identity rotation (up-pointing bones gave a 90 degree roll that put the
  mass-centre override 60 cm to the side at ground level and launched the car on spawn; bones
  along the car's right gave yaw 180 and the car drove tail first). Git Bash rewrites `/Game/...`
  arguments unless `MSYS_NO_PATHCONV=1`. Interchange refuses to merge a changed bone hierarchy
  into an existing skeleton: delete `SK_RangeRover_Skeleton` first when bones are added.
- Still manual or later: materials (M_Body, M_Trim, M_Wheel, M_Interior are empty slots; make
  instances of the project master material and set them Two Sided until the shells are cleaned);
  a `Head` socket if the camera should follow a rigged seat; an Animation Blueprint once the rig
  grows beyond wheels; a Blueprint child of AGTCarPawn for tuning in the editor; the M0 row also
  lists Git + LFS, which is not initialised yet.

**Blockout cleanup before the next export** (from the 2026-09-11 inspection; none blocks
import): delete the empty `BOOT` and the one-quad `frontDoors.001`; Merge by Distance on the
doors, bumper and roof; delete internal faces (Select All by Trait, Non Manifold, Multiple
Faces only) on the doors, bumper, bonnet, arches; turn on Mirror clipping everywhere; set wheel
origins to geometry and apply their rotation; lower the interior tub top below the door belt
line; give every object a unique name (the saved file still has `bonnet.001`, `rearPanel.001`,
`Vert.008`, `wheel.001` to `.003`); one zero-area face somewhere (Unreal logged a zero-length
normal): Mesh, Clean Up, Degenerate Dissolve.

## 13. M1 driving prototype, slice 1 (2026-09-11)

What exists on top of section 12, all headless-verified with `Art/surface_test.bat`:

- **Surfaces**: `UGTSurfacePhysMaterial` (Source/GrandTour/Terrain) assets
  `Content/GrandTour/Terrain/Surfaces/PM_{Tarmac,Dirt,Mud,Snow}`. Chaos reads the inherited
  Friction for dry grip; the traction component reads the rest. The numbers live in the table in
  `Art/Unreal/setup_m1_track.py` and are re-applied on every run of `Art/setup_m1_track.bat`:
  tune them there, not in the editor.

  | Surface | Friction | Wet x | Crr | Sink m/s | Max m | Drag x | Plough | Track |
  |---|---|---|---|---|---|---|---|---|
  | Tarmac | 0.70 | 0.75 | 0.012 | 0 | 0 | 0 | 0 | 0 |
  | Dirt | 0.62 | 0.80 | 0.030 | 0.01 | 0.05 | 1.0 | 0.02 | 0.3 |
  | Mud | 0.45 | 0.95 | 0.070 | 0.05 | 0.30 | 1.0 | 0.10 | 1.0 |
  | Snow | 0.35 | 1.00 | 0.060 | 0.04 | 0.25 | 1.0 | 0.08 | 0.8 |

  Drag per wheel as a fraction of its load = Crr x (1 + Drag x sinkage) + Plough x sinkage x
  (speed / 10 m/s)^2, capped at 0.6. First gear pushes about 0.26 g, so the Crr x (1 + Drag)
  product decides whether a car can pull away and Plough decides how hard speed is punished.
  Untagged ground is dry tarmac. Grip at full sinkage drops 30 % on mud and snow, 20 % on dirt.
- **Pipeline**: `AGTCarPawn::Tick` runs Traction -> Condition -> `UGTVehicleTuningComponent`
  (base captured from the movement component on the first tick, then base -> traction ->
  condition -> Chaos: `SetMaxEngineTorque`, `SetDragCoefficient`, `SetWheelFrictionMultiplier`,
  applied on change) and applies steering as input + condition pull. Rolling resistance is
  `AddForce` on the body: sum of contact wheels' Crr x mass x g / 4, faded below 50 cm/s.
- **Traction**: sinkage grows at SinkageRate x (0.3 settling + 0.7 rolling above 1 m/s + 1.5 x
  wheelspin, slip / 300 cm/s) and recovers at 0.2 m/s on firm ground. Bogged = two wheels past
  90 % sinkage, spinning, and speed under 60 cm/s; while bogged torque x0.35. Easing off clears it,
  so a bogged car can be crawled out with gentle throttle; the winch is for when that fails.
  Tuned 2026-09-11 after the first hand drive ("too sticky"): parked 4 s in mud the car still
  pulls away, 0 to 44 km/h in 7.5 s (`Art/mud_test.bat`), while mud at speed still slows it,
  81 to 70 km/h over 60 m at full throttle, and snow to 54 (`Art/surface_test.bat`).
- **Wheels and camera** (2026-09-11, "very jolty" on the rough patch, then "soft and floaty",
  then "slightly too jolty"): wheels sweep a sphere instead of a ray, travel 12 cm up / 16 cm
  down, spring rate 340 with damping ratio 0.62. How Chaos 5.8 reads these (SuspensionSystem.h,
  ChaosWheeledVehicleMovementComponent.cpp): spring force = compression from full drop x rate
  (rate x100 internally), damping = ratio x critical for the sprung mass (~525 kg a corner with
  the mass centre between the axles), so 250 is 1.10 Hz, 340 is 1.28 Hz and 400 is 1.39 Hz;
  static sag at 340 is 15 cm of the 28 cm travel. `SpringPreload` is stored but never used by
  the force model, and `SuspensionSmoothing` only filters the drawn wheel offset, not the
  physics, so neither is a ride control. History: 250 / 0.5 felt soft and floaty, 400 / 0.75
  slightly too jolty (a sharp crest makes the damper spike: at 13 m/s over a 15 cm ridge the
  damping force is about nine times the static wheel load), 340 / 0.62 is the middle and is
  NOT yet felt by the user. The eye point is damped vertically (12 per second, 8 cm max) on top
  of the rotation lag and stable horizon; the rough patch is ten smooth 8..15 cm ridges every
  3 m instead of hard-edged boxes. `Art/rough_test.bat` drives it at full throttle and reports:
  peak and RMS vertical g over 50 ms windows, peak pitch rate, the largest single-step vertical
  velocity jump (the jolt), and after the last ridge the settle time and bounce count (the
  float). The 50 ms peak g varies 3.4..6.3 between identical runs (uncapped headless frames),
  so tune on the step jump and settle time: 400 / 0.75 gave 18 cm/s, 340 / 0.62 gives 12..14
  cm/s, settles in 0.1 s with no bounce.
- **Condition**: parts Engine, Radiator, Steering, FuelTank, Suspension x4, Tyre x4, Body,
  Glass. Torque x (0.4 + 0.6 engine), misfire cuts to x0.1 for 0.15 s at random below half engine
  health, tyre grip x (0.5 + 0.5 health), steering bias 0.25 x (left - right suspension health),
  radiator under half health damages the engine while driving. Fuel 81 L, idle 1.5 L/h, full load
  30 L/h, x10 time compression, tank under half health leaks up to 0.5 L/s. Impacts: no damage
  under 150 cm/s deltaV, full at 1500; regions by car-space position (front X > 150, rear
  X < -150, arches |Y| > 60 near the axles, roof Z > 150, glass Z 115..150 within |X| < 120,
  else sides); dents merge within radius, 32 slots, shallowest dropped.
- **Track**: `Art/setup_m1_track.bat` -> `L_TestTrack` (now the startup map). Surface straight
  along +X from x = 0: 60 m lanes tarmac, dirt, mud, snow, wall at 245 m, kerb markers at each
  lane start; PlayerStart at x = -25 m. At y = +40 m: 12 deg climb, plateau, descent, jump ramp,
  rough patch, slalom. Materials: `M_GT_Environment` master (BaseColor, Roughness; add MF_Weather
  here) with MI_Env_{Tarmac,Dirt,Mud,Snow,Greybox,Marker}.
- **Cockpit** (2026-09-11, greybox; left-hand drive since the user's fourth drive, so every Y
  below is -40, the car's left): `UGTDashboardComponent` on the pawn at (58, -40, 121) pitched
  75 degrees so its local Z faces the driver's eye at (10, -40, 135); the dials sit just above the
  steering wheel rim, in front of the blockout's dash wall (the tub's dash top is at Z 120 from
  X 80 forward). It drives three needles (speedo 0..160 km/h and tacho 0..6000 rpm over a 240
  degree sweep, fuel over 90 degrees, with needle lag) and five warning lights (engine below half
  health or misfiring, coolant, fuel under 15 %, bogged, any suspension corner below half) from
  the movement, condition and traction components, and turns the steering wheel with the front wheels' actual steer angle (Chaos rate-limits it;
  the raw keyboard input is binary and made the wheel snap; the user confirmed it "looks right"
  on the fourth drive).
  With `bBuildGreybox` it builds the dash from engine primitives at runtime: dial faces, rims,
  needles, lights, a dash slab hugging the tub's dash wall (centre (75, 0, 103), 10 x 170 x 24),
  a binnacle hood behind the cluster (centre (70, -40, 119), 16 x 32 x 18) and a 38 cm steering
  wheel at (46, -40, 96) pitched 70 degrees made of twelve rim segments, three spokes and a hub,
  so the dials are visible through it. All parts are transient and collision-free, so nothing
  is saved into levels and the real interior mesh can replace the slab later while the gauges
  stay component-driven. Materials are dynamic instances of `M_GT_Prop` (BaseColor, Roughness,
  EmissiveColor x EmissiveStrength) created by `Art/setup_m1_cockpit.bat`; lights are emissive
  12 when lit. `Describe()` prints needle angles and lit lights; `CheckDialVisibility(eye)`
  reports any greybox part whose bounds cross the eye-to-dial lines (the surface test logs it).
  Lesson: a rotator's yaw is about the parent's vertical axis, so anything that must spin about
  a tilted axis needs a fixed tilted pivot with a spinning child, as the wheel and needles do.
- **Tyre tracks** (2026-09-11, ARCHITECTURE 6a): `UGTTrackPaintSubsystem`
  (Source/GrandTour/Terrain) owns a 128 m square, 2048 px window that follows the player's car.
  Every tick `AGTCarPawn::PaintTracks` stamps each wheel that is in contact with sinkage x track
  depth above 0.02: a soft-edged quad from last tick's contact point to this one, as wide as the
  tyre, added into the red channel of `RT_TrackPaint`. A moving wheel deposits sinkage x track
  depth once on every point it passes whatever the frame rate (the quad is at least one width
  long and the amount scales with distance / width), a stationary spinning wheel digs at half
  that per second. When the car is 20 m from the window centre the contents shift by a whole
  number of texels through a scratch target (the window is snapped to 50 cm cells) and a decay
  pass multiplies the target by exp(-dt / 120 s) every half second (float target, so slow decay
  survives quantisation). `MPC_TrackPaint` carries `TrackOrigin` (centre x, y, size cm, pixels)
  and `TrackDepthCm` (12). A 256-cell CPU grid mirrors every stamp and decay (peak depth of the
  streak per cell, so front and rear wheels on one line read about twice the sinkage) for
  gameplay queries (`SampleDepth`) and headless tests; under -NullRHI only the grid runs.
  Materials, built by `Art/setup_m1_trackpaint.bat` (after setup_m1_track): `MF_TrackPaint`
  is one custom HLSL node (five `Texture2DSampleLevel` taps so it compiles in the vertex shader
  too) returning NormalWS (finite-difference rut normal), RutDepth and Displacement (0, 0,
  -depth x TrackDepthCm); `M_GT_Environment` calls it behind a `TrackStrength` scalar times
  the vertex normal's up component, world-to-tangent transforms the normal into the Normal pin
  and Displacement goes to World Position Offset (no effect on the 8-vertex greybox slabs; the
  normal carries the look until the displacement spike). MI_Env_Tarmac / Greybox / Marker have
  TrackStrength 0, Dirt / Mud / Snow 1. This function is the one place to change when the
  displacement approach changes. Assets live in `Content/GrandTour/Terrain` (RT, MPC) and
  `Materials` (MF); the script is idempotent (the function is rebuilt, the master's nodes are
  tagged "TrackPaint:" in their description and replaced, collection parameter ids survive).
  Verified: `Art/track_test.bat` (`-GTTrackTest`, 16 s down the lanes) PASS headless: no cells
  while on tarmac, mud 0.85 / snow 1.33 under both wheel paths, 0 beside them, 12 recentres;
  `Art/track_test.bat gpu` (`-RenderOffScreen`, real D3D12, reads the target back) PASS with
  the render target at 1.08 on the mud path and 0 beside it against the grid's 0.90, at a
  frame rate fifteen times lower. Traps: a `-NullRHI` commandlet translates the material graph
  but compiles no shaders, so `recompile_material`'s empty error list does not prove the HLSL;
  the off-screen game run is the HLSL check (proved with a deliberately broken custom node: the
  commandlet stayed silent, the game run logged the HLSL error). `-GTProbeMaterial=/Game/Path/M_X`
  on any `-RenderOffScreen` test run puts that material on a cube so it must compile; grep the
  log for "Failed to compile". `unreal.Vector4f()` takes no constructor arguments. Structs whose fields are EditAnywhere (`CustomInput`, `CustomOutput`,
  `CollectionScalarParameter`) are reachable from Python even without BlueprintType.
- **Body panels, dents and detach** (2026-09-11, ARCHITECTURE 6b): `UGTBodyComponent`
  (Source/GrandTour/Vehicle). At BeginPlay it scans the Panels folder through the asset registry
  and attaches every `SM_RR_*` static mesh except the wheels to the skeletal mesh at the car
  origin (20 panels; the export keeps the car's pivot, so a panel's local space is car space),
  with no collision (the chassis box collides for the whole car), hides the skeletal mesh's
  M_Body and M_Trim slots with `ShowMaterialSection` so only its wheels still draw, and gives
  the panels dynamic instances of `M_GT_Vehicle` by slot name (body sand, trim near-black,
  interior dark). Panel to region by a name table: Bonnet* / FrontPanel / Bumper are Front, the
  arches and doors their corners and sides, Trunk / RearPanel* Rear, Roof / Vert Roof,
  BaseInterior and Pillars structural (never detach); unknown names fall back to the bounds
  centre. Dents: the condition's 32-slot impact list is written to a 32 x 2 float texture (row
  0 local position + radius, row 1 outward direction + depth) whenever `ImpactsVersion` changes,
  and `MF_Dents` (one custom HLSL node) loops it per vertex and pixel: vertices move against the
  outward direction by depth x (1 - (d/r)^2)^2 x saturate(dot(direction, normal)), so a frontal
  hit dents the grille and not the roof, and the normal tilts toward the dent centre by the
  analytic slope; the function feeds World Position Offset and Normal of `M_GT_Vehicle`. The
  record's `LocalDirection` is OUTWARD (minus the hit's impact normal; the body test logs
  (1, 0, 0) for the wall). Region health: every impact subtracts its severity from the struck
  region's own health (separate from part health, `GetRegionHealth`); at zero the body detaches
  that region's panels: KeepWorld, PhysicsActor profile that ignores Pawn / PhysicsBody / Vehicle
  (they start inside the chassis box; before the ignore the solver blasted the car 150 m into
  the air), simulate, car velocity + 3 m/s outward + a tumble. A greybox windscreen (a 58 x 150 x
  1 cm slab at (81, 0, 143) pitched 128 degrees, from the dash top to the roof's front edge)
  carries `M_GT_Glass` with Crack = 1 - glass region health (uniform whitening and thickening;
  a crack pattern comes with the in-seat damage feedback item). `ResolveRegion` now takes the
  outward direction first and the position second, because a box-to-box contact point can sit
  on an edge: a frontal wall hit had resolved to Roof and thrown the roof off; underside hits
  go to the nearest corner's arch (suspension). Materials by `Art/setup_m1_body.bat`:
  RT_ImpactsDefault (only the ImpactTex parameter's default; linear so the sampler compiles),
  MF_Dents, M_GT_Vehicle (BaseColor, Roughness, Metallic; the Substrate clear coat of
  ARCHITECTURE 6d is deferred, its pins are not reachable from Python) and M_GT_Glass
  (translucent, two-sided, BaseColor, Opacity, Roughness, Crack). Idempotent: the function and
  the masters are rebuilt from scratch. Verified: `Art/body_test.bat` (`-GTBodyTest`: teleport
  to the snow lane 35 m before the wall, full throttle, judge two seconds after the stop) PASS
  headless and with `gpu` (both masters compile): 20 panels attached, 2 slots hidden, the wall
  hit kills the Front region, Bonnet / Bonnet2 / Bumper / FrontPanel come off and simulate, 16
  stay on; surface, track, mud, rough and flat regressions pass. Trap: an asset loaded by a
  constructor `FObjectFinder` is rooted for the run, and `delete_all_material_expressions`
  then asserts (!IsRooted) when a setup script rebuilds it, so the body component loads its
  materials in BeginPlay; the cockpit script leaves M_GT_Prop alone for the same reason.
- **Body surface state** (2026-09-11, ARCHITECTURE 6b/6d): `UGTBodyStateComponent` keeps dirt
  per damage region, wetness and snow. Each wheel in contact sprays by surface tag once it rolls
  (spray = speed / 5 m/s, plus wheelspin): mud 0.15/s of dirt and wets the body, dirt and sand
  0.05/s of dust, snow 0.25/s of snow and a little wet, tarmac nothing; the wheel's own arch
  takes the full amount, its side 0.35, its end of the car 0.15 (front) or 0.3 (rear), the roof
  0.05 only above 15 m/s, the windscreen 0.1 from the front wheels. Wetness and snow are
  whole-body values set by the strongest wheel, not the sum; wetness dries at 0.01/s (the
  traction component's global wetness is a floor for the rain to come), snow melts at 0.02/s;
  `Wash()` is the base wash. `UGTBodyComponent` gives every panel its own dynamic material and
  writes Dirt (its region), Wetness and Snow each tick; the windscreen gets the glass region's
  dirt. `M_GT_Vehicle` now runs BaseColor / Roughness through a Grime node (dirt heaviest at
  the sills: mask = Dirt x (1 - (localZ - 35) / 90)^1.5, browner and rougher) and then through
  `MF_Weather`, with the dirt mask as porosity so wet dirt darkens; `M_GT_Glass` gained Dirt
  (browner, thicker). `MF_Weather` and `MPC_Weather` (`Art/setup_m1_weather.bat`, run before
  setup_m1_body) are the ARCHITECTURE 6d function and collection: inputs BaseColor, Roughness,
  Porosity, LocalWetness, LocalSnow; reads Wetness and SnowAmount from the collection (plus
  RainIntensity, WindStrength, Temperature, WindDirection, OcclusionBounds for M3); wet darkens
  porous surfaces and drops roughness to 0.15, snow whitens upward-facing surfaces; outputs
  BaseColor, Roughness, Wet, Snow. The environment, prop and glass masters still have to be
  routed through it (the "remaining masters" item). Verified: `Art/bodystate_test.bat`
  (`-GTBodyStateTest`, 16 s down the lanes) PASS headless and `gpu`: clean on tarmac, leaving
  the mud arches 0.55 > sides 0.39 > roof 0.11, wet 0.89, windscreen 0.11, snow 0.5 after the
  snow lane; body and surface regressions pass.
- **Spray and audio** (2026-09-11, ARCHITECTURE 6a). No Niagara systems or sound assets exist
  and neither can be authored headless, so both are greybox C++ with the rules that carry over
  to the art pass. `UGTSprayComponent`: three CPU particle pools (mud, dust, snow; 120 each)
  drawn as instanced engine spheres, mud with an opaque `M_GT_Prop` instance, dust and snow with
  translucent `M_GT_Glass` instances (both masters carry the instanced-static-mesh usage flag,
  set by their scripts, or a real render falls back to the default material). A wheel in
  contact emits by surface tag at 40 / 25 / 30 particles a second times spray (speed / 5 m/s
  plus wheelspin) from its contact point, backwards and up relative to the car: mud blobs fall
  at 1 g and die in under a second, dust rises slowly, grows and drifts for two seconds, snow
  puffs sit between; a full pool recycles its oldest. `UGTVehicleAudioComponent`: a mono 22 kHz
  synth (`FGTVehicleSynth`) rendered on the audio thread through a `USoundWaveProcedural`
  subclass and a non-spatial audio component: engine tone at the firing frequency (rpm / 60 x 4
  for the V8; four harmonics plus a half-rate sub), gain 0.12 idle to 0.42 at full throttle,
  gated by misfires and an empty tank; tyre noise low-passed by surface (tarmac 4000 Hz at half
  level, dirt 1500, sand 1200, snow 900, mud 600 at full level) scaled by speed over 20 m/s;
  skid noise from wheel slip; a decaying noise thud on impacts by severity. Parameters cross to
  the audio thread as atomics. Needs the AudioExtensions module (sound wave subclass). Every
  headless test now runs with `-nosound` so the synth never plays through the speakers; the
  spray test renders a block of the mix on the game thread instead. Verified:
  `Art/spray_test.bat` (`-GTSprayTest`, 16 s down the lanes) PASS: no spray on tarmac, dust up
  to the pool in the dirt lane, 88 mud blobs live in mud, 92 snow puffs in snow, 972 spawned,
  tyre cutoff 4000 Hz on tarmac and 600 Hz in mud, rendered RMS 0.13 in both, engine 59 Hz at
  idle rising with rpm. Trap: a test flag that the built binary does not know starts the game
  and never exits (a failed build followed by a test run hung for ten minutes); chains stop on a
  failed build now.
- **Master materials** (2026-09-11, ARCHITECTURE 6d): six masters exist and every one ends in
  `MF_Weather`: M_GT_Environment (BaseColor, Roughness, TrackStrength, Porosity; the track-paint
  normal and displacement), M_GT_Prop (BaseColor, Roughness, EmissiveColor x EmissiveStrength),
  M_GT_Vehicle (Grime and MF_Dents as above), M_GT_Glass (translucent, Crack, Dirt), M_GT_Foliage
  (two-sided, a wind sway World Position Offset from MPC_Weather's WindStrength and
  WindDirection) and M_GT_Character (usable on skeletal meshes for the arms). `Art/setup_m1_masters.bat`
  creates the last two, inserts the MF_Weather call (tagged "Weather:") between whatever feeds
  BaseColor / Roughness and the pins on every master except the vehicle (already routed by
  setup_m1_body), adds a Porosity parameter per master and sets it on the environment instances
  (tarmac 0.3, dirt 0.9, mud 1.0, snow 0.6), then asserts that all six BaseColor pins are fed
  by MF_Weather ("masters through MF_Weather: 6/6"). M_GT_Prop and M_GT_Glass carry the
  instanced-static-mesh usage flag for the spray. Still open from the backlog item: the
  Substrate clear coat on the vehicle master (its pins are not reachable from Python) and the
  puddle mask / rain ripples / occlusion in MF_Weather (M3). Verified: an off-screen spray test
  run with `-GTProbeMaterial=` foliage and character compiled all six masters (no "Failed to
  compile") and still passed.
- **After the fourth drive** (2026-09-11): the user wants no windscreen sheet in view
  (`bBuildWindscreen` now defaults off; `M_GT_Glass` and the crack plumbing wait for real
  glass), calls the deformation "very basic, good for now", and asked for left-hand drive (seat,
  cluster, binnacle and wheel moved to Y -40). Added with it: bonnet steam (a fourth spray kind
  from `SteamOrigin` (170, 0, 105) at up to 25 puffs a second once the radiator is below half
  health, rising and drifting with the car; the body test now requires steam after the wall),
  driving input assets (`Art/setup_m1_input.bat` writes IA_Throttle / Brake / Steer / Handbrake
  / Look and IMC_Driving under Content/GrandTour/Input through `CreateDrivingInputAssets`, with
  exactly the runtime mapping; the pawn loads them when present and logs "driving input from
  assets", so keys are rebindable in the editor; delete them to get the built-in mapping back;
  the flat test requires 15 mappings), and the clear coat on `M_GT_Vehicle` (shading model
  ClearCoat; ClearCoat 0.8 x (1 - dirt mask) and ClearCoatRoughness 0.1 through
  `ConnectMaterialCustomData`, a C++ helper for the pins Python hides; compiled off-screen by the
  body test). Editor-only helpers in `UGTVehicleSetupLibrary` are guarded by WITH_EDITOR and the
  MaterialEditor module is an editor-only private dependency. Trap: UBT refuses to build while
  the editor has Live Coding active; the editor must be closed for the .bat pipeline. More traps
  from the same batch: `delete_all_material_expressions_in_function` deletes every other node
  (delete while iterating), so the function scripts now clear with a loop (`clear_function`) and
  fail if anything survives; a stale node had reached an output and broke M_GT_Vehicle. Any
  material a constructor finder loads roots everything it references, so once M_GT_Prop went
  through MF_Weather the weather script crashed until the dashboard loaded its material lazily
  too: no constructor finders for project materials, anywhere. Python cannot see 5.8's key
  mapping storage on an input mapping context (its arrays read empty), so the input script
  counts through `GetMappingCount`.
- **Input**: gamepad axes carry a 0.2 dead zone; without it a resting stick steered the car
  (found when a controller stayed plugged in during a headless run). The headless tests disable
  the car's player input at start and zero the driving inputs, so results no longer depend on
  attached devices.
- **Tests** in `AGTDriveTestGameMode`: `-GTDriveTest` (flat), `-GTSurfaceTest`, `-GTMudTest`
  (parked in mud, then pull away), `-GTRoughTest` (ridges at full throttle: jolt and float
  numbers), `-GTTrackTest` (tyre tracks; `track_test.bat gpu` adds the render-target read
  back), `-GTBodyTest` (wall hit: dent texture, region death, panel detach; `body_test.bat gpu`
  compiles the body materials), `-GTBodyStateTest` (dirt, wet, snow down the lanes;
  `bodystate_test.bat gpu` compiles the weathered body material), `-GTSprayTest` (spray by
  lane and the synth); one .bat each in `Art/`, all silent (`-nosound`). The surface test also logs the dashboard every 4 s and requires the engine
  light after the wall. `-GTSurfaceTest`: full throttle down the straight, per
  segment entry/exit speed and sinkage, then the wall. Result 2026-09-11: PASS; mud slows the
  car, the wall destroys the radiator and drops the engine to 0.37.
- **Traps**: `unreal.Rotator(a, b, c)` is roll, pitch, yaw, not pitch, yaw, roll; the track
  script uses keywords after the ridges came out as posts. Skeletal-mesh hit events need `bNotifyRigidBodyCollision` on the physics asset
  bodies (`setup_m0.py` sets it) and the component; `FGameplayTag` cannot be set from Python
  (`UGTVehicleSetupLibrary::SetSurfaceTag`).


## 14. M2 on foot + tools (2026-09-12)

Everything below is C++ under `Source/GrandTour` in the ARCHITECTURE 2 folders (Character/,
Interaction/, Inventory/, Tools/, Harvest/, Hazards/, Core/, winch in Vehicle/), greybox where art
is needed, and verified by two new headless runs: `Art/onfoot_test.bat` (`-GTOnFootTest`) and
`Art/winch_test.bat` (`-GTWinchTest`), both on L_DriveTest and both PASS (the on-foot one also
passes on L_OnFootTest). `FGTM2TestRunner` (Core/) scripts them step by step from the game mode's
Tick; every step logs a `GTDRIVETEST m2` line. The user has not yet felt any of it: movement,
camera, head bob and the swap all need the hand test before any tuning.

- **Player character** (`AGTPlayerCharacter`, ARCHITECTURE 9a). `ACharacter` with a 34 x 96
  capsule, no full-body mesh (the inherited one stays empty: no shadow body), a `CameraRoot`
  scene component at eye height 64 cm above the capsule centre (eyes at 160 cm) carrying the
  camera, which follows the control rotation (FOV 90 like the seat). Walk 300, sprint 550 cm/s,
  no jump at first; a jump was added on 2026-09-13 at the user's request (`JumpVelocity` 420 cm/s, a measured 90 cm rise, Space or gamepad B, off while collapsed; the on-foot test jumps after the boot transfer). The arms are Epic's mannequin `SKM_Manny_Simple` drawn as a first-person primitive
  (`FirstPersonPrimitiveType::FirstPerson`, only-owner-see, no shadows, first-person FOV 70 at
  scale 0.6 as in the 5.8 template) attached to the camera, playing `MF_Pistol_Idle_ADS` in a loop
  because that pose holds both hands up in view; head, thigh_l and thigh_r are hidden with their
  children so what remains reads as arms and a torso, and the mesh is placed so the head bone sits
  `ArmsHeadOffset` (-12, 0, 4) from the eye (computed from the reference skeleton at BeginPlay;
  the mannequin faces +Y so it is yawed -90). 5.8 ships no arms-only mesh; this is the template's
  own approach minus its control rig. `Art/setup_m2_character.bat` copies the 17 mannequin files
  (mesh, skeleton, physics asset, control rig, materials, textures, two anims, 62 MB) from
  `Templates/TemplateResources/High/Characters` into `Content/Characters/Mannequins`, keeping
  Epic's `/Game/Characters` paths so the package references resolve (the one folder outside
  `Content/GrandTour`, by design); without them the character logs a warning and plays armless.
  The tool in hand is a coloured box (`M_GT_Prop` instance) on the `hand_r` socket, or 45 cm in
  front of the camera when there are no arms; `ToolOffsetInHand` / `ToolRotationInHand` are the
  knobs. Head bob is procedural on `CameraRoot`: one lateral sway per stride and one vertical dip
  per footfall (2 cm vertical, 1 cm lateral, 0.9 strides a second at walking speed, scaling with
  speed), eased out over a few frames when stopping; the sprint FOV kick is +8 degrees. Both have
  toggles (`bHeadBobEnabled`, `bSprintFovKickEnabled`; H flips head bob while playing so the user
  can compare). Collapsed (exposure zero): speed x0.3, the eye drops 45 cm, tools grant nothing.
  Look: mouse 1 degree per unit like the car, stick 120 degrees a second; legacy input scales are
  on in DefaultInput.ini (yaw 2.5, pitch -2.5) so the character multiplies by 0.4 and negates
  pitch. Input: `IMC_OnFoot` with IA_Move (WASD via swizzle/negate modifiers, left stick with the
  0.2 dead zone), IA_LookMouse, IA_LookStick, IA_Sprint (Shift / stick click), IA_Interact (E /
  A), IA_ToolNext / Prev (scroll, d-pad), IA_Inventory (Tab / back), IA_DropHook (G / X),
  IA_ToggleHeadBob (H), IA_Transfer (T / Y, boot screen only); assets from
  `setup_m2_character.bat` (22 mappings) or the identical runtime fallback. E always goes to the
  interaction component (first hand test: the boot screen had taken E over and nothing else
  could be used until Tab; now looking at the boot and pressing E closes it).
- **Possession swap** (`AGTPlayerController`, ARCHITECTURE 5 Enter / exit). The game mode now
  uses this controller and `AGTHUD`. The controller spawns the character the first time it
  possesses a car and keeps it hidden, collision-less, movement disabled and attached to the car
  (`SetInCar`), so inventory and exposure persist across swaps and the character rides along.
  `ExitCar` (F in the seat, refused above 3 m/s): zero the driving inputs, handbrake on, find a
  clear capsule spot with `AGTCarPawn::FindExitLocation` (driver's door at car-space (40, -175),
  then the other door, then behind, then ahead: ground trace plus a capsule overlap test), put the
  character there facing the seat camera's yaw, `SetViewTargetWithBlend` 0.35 s ease-in-out then
  `Possess` (the camera manager keeps a pending blend to the same target, so the blend survives
  the possess), control rotation = seat view. `EnterCar` (look at the car, E) reverses it. Each
  pawn adds its own mapping context in SetupPlayerInputComponent and the controller removes the
  other pawn's in OnPossess; `HasDrivingContext` / `HasOnFootContext` let the tests check the
  swap. The car survives the swap untouched (same actor, still simulating).
- **Interaction** (`IGTInteractable`, `UGTInteractionComponent`, ARCHITECTURE 5). One C++
  interface: `GetInteractionOffer(query)` returns available + prompt + hold time, or a reason;
  `Interact(query)`. The component traces from the eyes (300 cm, Visibility) every tick, keeps
  the target and offer, and drives hold-to-use: progress climbs over the hold time, fires once,
  and needs a release before the next; instant offers fire on the press; a target change resets.
  Tool requirements are a tag check in the offer (`AGTPlayerCharacter::HasToolTag`). The car is
  an interactable: repair kit on a damaged region -> "Repair front (2 scrap)" (2.5 s), nose with
  bare hands -> "Take winch hook", tail -> "Open boot", else "Get in"; hook in hand -> nothing.
- **Tools** (`UGTToolDefinition`, a primary data asset: id, name, granted tag, use-time scale,
  greybox box size and colour). Three: Cutter (Tool.Cut), Pry bar (Tool.Pry), Repair kit
  (Tool.Repair), from `Content/GrandTour/Tools/DA_Tool_*` (written by `setup_m2_character.bat`
  through `CreateToolAssets`, since FGameplayTag cannot be set from Python) or the same defaults
  built at runtime. Scroll cycles hands -> cutter -> pry bar -> kit -> hands. Native tags
  `Tool.Cut/Pry/Repair` and `Hazard.Weather/Radiation` are in GTGameplayTags.
- **Harvest nodes** (`AGTHarvestNode`, `AGTWreck`). A node needs a tool tag, takes HarvestTime
  (x the tool's scale) per use, pays a fixed yield into the harvester's inventory (what does not
  fit is dropped and logged; dropped-item actors are an M3 item) and shrinks when its uses run
  out. Cable bundle: cutter, 2 s, 2 wire, 3 uses. Wreck: pry bar, 3 s, 3 scrap + a radiator, 2
  uses, 320 x 160 x 110 cm, and it carries a winch anchor component (30 kN) so the hook can go on
  it. Loot tables replace the fixed yield with the hand-placed nodes of M3.
- **Field repair**: `UGTConditionComponent::RepairRegion` gives every part the region protects
  +0.5 health, sets the region's own health to 1 and clears the dents resolved to that region
  (the body texture rebuilds); `IsRegionDamaged` decides whether the kit is offered. Costs 2
  scrap. Detached panels stay off until the lift (M4). The winch is a new car part (`Winch`, hit
  by frontal impacts at 0.3).
- **Winch** (`UGTWinchComponent`, `AGTWinchAnchor` + `UGTWinchAnchorComponent`, ARCHITECTURE 6e).
  Mount at car-space (240, 0, 55), cable 25 m, rated pull 40 kN scaled by winch health, reel 150
  cm/s. States stowed / hookCarried / attached / snapped. Hook carried: the cable end follows the
  character and the tether clamps the capsule to the cable length from the mount (position pulled
  back onto the circle, outward velocity removed, `TetherClamps` counts). Attached: the cable is
  a clamped spring, never a constraint: tension = clamp(2000 N/cm x stretch + 60 N s/cm x
  stretch rate, 0, rated pull), applied with `AddForceAtLocation` at the mount toward the anchor
  (x100 for kg cm/s^2); reeling shortens the rest length at 150 cm/s scaled by (1 - tension /
  rated) so the motor stalls at the cap. Anchor failure: tension above the anchor's strength for
  0.3 s tears it out (`Fail`: the post simulates and topples toward the car), the cable goes
  slack, state back to stowed. Snap: tension at or above 36 kN while the mount closes slower than
  20 cm/s for 1.5 s (pulling flat out at something that will not come): winch part -0.5, a 1 m/s
  recoil impulse, state snapped; the hook can be taken again with whatever pull is left. R in
  the seat reels; G on foot drops the hook; the hook is dropped on entering the car. Visual:
  a `UCableComponent` (module added to Build.cs; the plugin is on by default) from the mount to
  the capsule or the anchor, with particle collision on (`bEnableCollision`, friction 0.2) and
  half gravity so the rope lies on the ground instead of through it (first hand test), drawn
  taut while the winch holds tension and slack only when the car has come closer than the drum
  paid out. The winch becomes a gadget-slot part when the
  part system lands (M4); until then every car has one.
- **Inventory** (`UGTInventoryComponent`): named item stacks with a weight limit (character 40
  kg, boot 250 kg); `Add` returns what fitted, `TransferTo` moves what fits. Item weights are a
  table in GTInventoryComponent.cpp (scrap 2 kg, wire 0.5, bolts 0.2, fuel can 10, radiator 8,
  tyre 12; unknown 1) until the item data assets of ARCHITECTURE 4. Boot transfer is a greybox
  HUD screen: E at the tail opens it, scroll selects a stack on either side, T moves the whole
  stack across, E on the boot or Tab closes; walking 6 m away closes it.
- **Exposure** (`UGTExposureComponent`, ARCHITECTURE 9a): 0..100, drained by `AGTHazardVolume`
  (a box that overlaps pawns; Hazard.Weather, 10 points a second by default, ignores a character
  in the car), recovers 10 a second in the car and 1 a second outside after 5 s without a
  hazard. Zero = collapsed until back above 25. The weather front and radiation zone of M3 derive
  from the volume and add car damage.
- **HUD** (`AGTHUD`): canvas text and bars, no UMG: crosshair, prompt with hold bar, tool line
  and key hints, hook warning, COLLAPSED banner, exposure bar, inventory / boot lists, and in the
  seat the winch state (attached distance and kN) and the F / R hints. CommonUI replaces it in M7.
- **Map**: `Art/setup_m2_onfoot.bat` builds `L_OnFootTest` (run setup_m1_track first for the
  materials): 300 m tarmac floor, a 40 m mud lane 20 m ahead of the start, two cable bundles, a
  wreck, a steel post (200 kN) past the mud, a rotten post (3 kN), a hazard volume on a red slab
  15 m to the left, and a wall past the post to snap the cable on. The car spawns at the start;
  press F. Idempotent: props are rebuilt, floor and lights kept. The startup map is still
  L_TestTrack; F works there too, it just has nothing to use.
- **Tests**. `-GTOnFootTest` (14 s): exit (character possessed 180 cm from the car's centre at
  the driver's door, on-foot context in, driving out, car still there), walk 1.5 s (4.3 m,
  bob peak 2.0 cm) then with the bob off (0.00 cm), look at a cable bundle bare-handed
  ("needs a cutter"), with the cutter (offered, 2 s hold, 2 wire in the bag), radiator damaged to
  0.4 and 4 scrap given, repair kit at the nose ("Repair front (2 scrap)", 2.5 s hold, radiator
  0.9, 2 scrap left), wire moved to the boot, 100 scrap offered and 18 accepted at the 40 kg
  limit, 2 s in a 20/s hazard (100 -> 60), back in (driving context, character hidden, same car),
  2 s in the seat (60 -> 80). `-GTWinchTest` (15 s): hook offered and taken at the nose, sprint
  away from 20 m out for 3 s and never past 25.0 m (3096 clamps), attach offered and done at the
  post, in the seat, reel 6 s: the car comes 8.6 m at 147 cm/s with a 27 kN start-up peak; a wall
  in front: tension sits at 39.6 kN with the car still and the cable snaps after 1.5 s (winch
  health 0.49, the wall hit took a little too); a rotten post to the side tears out at 7.4 kN
  within 0.3 s of reeling. Regressions: drive (19 mappings now), body and spray still pass.
- **Traps**. A local named `Mesh` in an `ACharacter` subclass shadows the inherited member
  (warning-as-error C4458). `Cast<AGTCarPawn>` needs the full header in every cpp that uses it
  (Casts.h static-asserts on incomplete types). Bash-tool heredocs over about 5 KB still fail to
  parse: patch scripts go through the Write tool. `unreal.Rotator` positional order is (roll,
  pitch, yaw) as before. FGameplayTag prints as an empty struct from Python; the on-foot test's
  "tools=assets" line proves the saved tags load. Legacy input scales (2.5 / -2.5) apply to
  `AddControllerYawInput` / `AddControllerPitchInput`; compensate or the stick spins.

## 15. M3 run loop: legs, weather, hazards, loot, conditions (2026-09-12)

Everything below is C++ under `Source/GrandTour` in the ARCHITECTURE 2 folders (Run/, Weather/,
Hazards/, Harvest/, Environment/, Core/), greybox where art is needed, and verified by five new
headless runs on L_DriveTest that spawn what they need: `Art/leg_test.bat` (`-GTLegTest`),
`Art/weather_test.bat` (`-GTWeatherTest`, `gpu` reads the occlusion capture back and compiles
M_GT_Environment), `Art/hazard_test.bat` (`-GTHazardTest`), `Art/loot_test.bat` (`-GTLootTest`)
and `Art/env_test.bat` (`-GTEnvTest`), all PASS. `FGTM3TestRunner` (Core/) scripts them from
`AGTRunGameMode::Tick`; every step logs a `GTDRIVETEST m3` line. Two setup bats write the
content: `Art/setup_m3_weather.bat` (weather states, the occlusion target, MF_Weather and the
masters) and `Art/setup_m3_leg.bat` (loot tables, DA_Leg_01, the greybox leg L_Leg01). The
user has not driven any of it yet; fun test #3 is theirs.

- **Game mode.** `AGTRunGameMode` (Run/) derives from `AGTDriveTestGameMode` so every headless
  self-test keeps working on any map, and is now the project's `GlobalDefaultGameMode`
  (DefaultEngine.ini). Its game state is `AGTRunGameState`. On the first tick it resolves the
  leg: the run subsystem's pending leg (the base sets it before OpenLevel in M4), else the
  map's `AGTLegStart` (an asset reference or a path such as `/Game/GrandTour/Legs/DA_Leg_01`),
  else nothing (the test tracks: the leg phase stays None and nothing changes). Its own test
  flags come first in Tick; M2's and M1's fall through to the base.
- **Run subsystem.** `UGTRunSubsystem` (Core/, a game instance subsystem: no custom game
  instance needed) holds `FGTCampaignState` (leg index, results, currency placeholder, total
  time) and the pending leg across level loads, and `RecordResult` appends an `FGTLegResult`
  (leg id, time, par, overtime, checkpoints, the haul as merged stacks with weight and value at
  base prices, rank against the rivals). This closes the M0 backlog line for the skeleton.
- **Leg definition.** `UGTLegDefinition` (Run/, primary data asset): id, name, number, map path,
  par and time limit (0 = none; past it the HUD warns and the result is marked overtime, the
  leg keeps running), the start weather (asset or a state name), the conditions profile
  (`FGTConditionCurve`: an `Env.*` tag with an `FRuntimeFloatCurve` of intensity against leg
  progress 0..1) and the rivals' times. `ApplyDefaultLeg01` is what the setup writes as
  DA_Leg_01 and what the tests build at runtime: par 300 s, limit 600 s, overcast, `Env.Cold`
  0 -> 0.8 over the second half, `Env.Dust` 0.7 through 0.35..0.6, `Env.Heat` 0.6 on the last
  quarter, rivals 250 / 280 / 320 / 400 s.
- **Checkpoints and extraction.** `AGTCheckpoint` and `AGTExtractionZone` (Run/) are volumes
  with a flat greybox slab on the ground (yellow, green). The game state polls the player's
  car against them with an oriented box test (the vehicle's skeletal mesh needs no overlap
  events). Checkpoints clear in Index order only. The leg timer starts when the car first moves
  faster than 0.5 m/s (`StartSpeed`) and counts up. Extraction: with every checkpoint cleared,
  the car driven and stopped (under 1 m/s) inside the zone for 2 s (`HoldSeconds`, the HUD
  shows the hold bar) fires `OnExtractionReady`; without the checkpoints the visit is refused
  once and the HUD says which checkpoint is next. Progress along the leg is the car's
  projection onto the current segment of start -> checkpoints -> extraction, so the profile is
  sampled by where you are on the route, not by time. The HUD shows leg number, clock, par and
  limit, the next objective's distance and bearing, and the hold.
- **Results screen.** `AGTRunGameMode::FinishLeg` builds the result from the state and both
  inventories (boot + bag), records it, freezes the car (input off, handbrake) and the HUD draws
  the panel: time against par, overtime, checkpoints, leg standing "2nd of 5" against the
  rivals' times (M5 replaces it with the simulated standings), the haul with weight and value,
  and "Enter / Start: continue", which reloads the leg map for now (the base takes over in M4).
  The key is a plain `BindKey` on the controller beside the pawns' enhanced input contexts.
- **Weather subsystem.** `UGTWeatherSubsystem` (Weather/, a tickable world subsystem) runs a
  state machine over `UGTWeatherStateDefinition` assets (Clear, Overcast, Rain, Storm, Snow;
  `Art/setup_m3_weather.bat` writes DA_Weather_* under `Content/GrandTour/Weather`, and the C++
  defaults stand in when they are missing). `SetState` blends the state's values (precipitation,
  cloud, fog density, sun and sky scale, wind strength and yaw, temperature, two ambience
  gains) from the current ones with a smoothstep over the state's transition time (20 s clear
  and overcast, 15 s rain, 10 s storm). A weather front layers its storm on top by pressure
  (below). From the blended values it simulates the two slow quantities, ground wetness (up at
  0.2/s times rain, dries at 0.01/s faster when warm) and snow cover (falls below zero, melts
  above and wets the ground), writes Wetness, RainIntensity, SnowAmount, WindStrength,
  Temperature, WindDirection, OcclusionBounds and OcclusionEnabled into `MPC_Weather` every
  frame through the collection instance (names are checked once, so an older collection is
  fine), scales the map's directional light and sky light and sets the height fog density, and
  drives the rain emitter. Nothing else in the game writes the collection. Wet traction:
  `AGTCarPawn` copies the subsystem's wetness into `UGTTractionComponent::Wetness` every tick,
  and the surfaces gained `WetRollingResistanceScale` and `WetSinkageScale` (dirt 1.6 / 3.0:
  wet dirt drives like shallow mud; mud 1.2 / 1.3; tarmac and snow 1 / 1; the table in
  `Art/Unreal/setup_m1_track.py` carries them) on top of the existing wet grip. The body's own
  wetness already floors at the traction wetness, so a car in the rain never dries.
- **Rain.** `AGTRainEmitter` (Weather/, spawned by the subsystem, transient) is the greybox rain
  until the Niagara pass of M6: a pool of 600 instanced streaks (3 cm flakes below zero) spawned
  in a 12 m cylinder 8..12 m above the player's camera, falling at 9 m/s (1.5 snow) with the
  wind's drift, each with a downward trace at spawn for where it dies and an upward one that
  rejects the spawn under cover; a landing leaves a 0.2 s splash disc. Drops land on roofs and
  never enter the space under them. It also plays the ambience: `FGTWeatherSynth` (rain hiss, a
  gusting wind rumble and Geiger clicks) through a `USoundWaveProcedural` like the vehicle's;
  `-nosound` leaves it silent and `RenderTestBlock` still proves signal.
- **Rain occlusion capture.** The emitter carries an orthographic `USceneCaptureComponent2D`
  looking straight down from 30 m above the player over a 60 m square, capturing scene depth
  into `RT_RainOcclusion` (512 px RGBA16F, `Content/GrandTour/Materials`) whenever the window
  moves a texel or 0.25 s pass, with the window snapped to whole texels. `MF_Weather` now takes
  the collection's OcclusionBounds (centre x, y, top z, half extent) and OcclusionEnabled and a
  `RainOcclusion` texture object parameter defaulting to the target, maps world XY to the image
  (looking down with pitch -90, image up is world +X and image right is world +Y), reads the
  depth, and masks the global wetness and snow to zero where something sits more than 20 cm
  above the surface. Local wetness (the car's own spray) is not masked. Under -NullRHI the
  capture is skipped and OcclusionEnabled stays 0, so materials show the uncovered result. The
  `gpu` weather run reads the target back at the roof and beside it and requires the roof to
  be at least 2 m nearer the capture than the open ground: it read 2666 against 3144, which
  puts the roof about 80 cm higher than it was placed, so the capture's depth scale is a little
  off; the mask only needs "nearer than the ground" and holds, but calibrate the scale before
  trusting absolute heights (M6, with real geometry).
- **Puddles.** `MF_Weather` gained a `CanPool` input (0 by default; `setup_m1_masters.py` feeds
  the environment master a `CanPool` scalar parameter of 1 and nothing else) and a `Puddle`
  output: a low-frequency value noise on world XY, thresholded by the global wetness (masked by
  the occlusion) so puddles appear in the same dips every time and grow as it rains, on
  upward-facing pooling ground only; a puddle darkens the base colour and drops roughness to
  0.03. Ripple normals wait for real ground materials (M6).
- **Exposure in the weather.** On foot the character drains its meter by the rain intensity
  (1.5 points a second at full rain, none under cover: an upward trace every 0.25 s), by the
  cold (0.08 a second per degree below zero), and by the leg's conditions at its own progress
  on the route (`Env.Cold` 1.0, `Env.Heat` 0.8, `Env.Dust` 0.3 a second at full intensity).
  Any drain blocks the open-air recovery, as before. The HUD shows the rate and "sheltered".
- **Hazard volumes.** `AGTHazardVolume` (Hazards/) still drains exposure on foot by tag and now
  also damages the car: `CarDamage` is a list of part rates per second, resisted through
  `UGTConditionComponent::ApplyHazardDamage` by `HazardResistance[tag]` (0 until parts fill it
  in M4; `HazardDamageTaken` counts), and it tells the car it is inside (`NotifyHazardContact`,
  a 0.25 s grace) so the dash and HUD can show it. The car is detected with the same oriented
  box test as the checkpoints.
- **Weather front.** `AGTWeatherFront` derives from the volume: an 80 x 300 x 40 m box with a
  dark 2 m slab on its leading face that travels along its yaw at 4 m/s (`SpeedCmPerSec`; that
  sweeps the 1.2 km leg in about six minutes). It owns no weather: every tick it reports its
  pressure at the player (1 inside, fading to 0 over `InfluenceCm` = 150 m ahead of the box) to
  the subsystem, which blends toward the storm state by that pressure, and that is what drops
  visibility (fog 0.12) and turns the rain on before the wall arrives. Inside: exposure 8/s on
  foot, glass 0.010, body 0.008 and radiator 0.004 health a second. The HUD shows STORM n%.
- **Radiation zone.** `AGTRadiationZone` is the static one: a 50 x 50 m box with a green slab,
  exposure 6/s on foot, engine 0.004 and radiator 0.003 a second in the car, the dash's
  RADIATION lamp (new light), a Geiger click rate into the ambience that rises toward the
  centre, and the rare nodes hand-placed inside it.
- **Loot tables.** `UGTLootTable` (Harvest/, a primary data asset rather than a data table so
  the picks per harvest live with the rows and the defaults can be written headless): weighted
  entries with a count range, guaranteed stacks, and picks min..max per harvest with
  replacement. `AGTHarvestNode` rolls its `LootTable` (or loads `LootTablePath`) instead of the
  fixed yield when it has one, from a random stream seeded by the node's name so a node pays
  the same every run. Three defaults from `Art/setup_m3_leg.bat` under `Content/GrandTour/
  Harvest`: CableBundle (wire 2..4 or bolts 1..3), Wreck (1 scrap guaranteed plus 1..2 picks of
  scrap 2..4, a radiator, a tyre or a fuel can) and RadiationCache (1 rare alloy guaranteed plus
  alloy 1..2 or scrap). The item table gained `RareAlloy` (4 kg) and a base price per item
  (scrap 5, wire 4, bolts 2, fuel can 30, radiator 80, tyre 60, alloy 150) for the haul value.
- **Environment stage.** `UGTEnvironmentComponent` (Environment/, on the car) samples the leg's
  profile at the car's progress every tick and applies the Tier 1 conditions in the tuning
  pipeline, now base -> traction -> environment -> condition -> Chaos. Three conditions, two
  small continuous models and one multiplier, each ramping performance (0.2) -> warning (0.5)
  -> damage (0.8), so no part goes from healthy to dead without a readable window:
  `Env.Heat` is coolant heat, up at 0.05/s at full intensity and full load and down at rest in
  a cool environment, costing up to 25 % torque, driving the new temperature dial, lighting
  COOLANT from the warning level and cooking the engine at 0.01/s past the damage level (ease
  off is the behaviour answer, a big radiator the part answer); `Env.Dust` is the air filter
  clog, growing with intensity x distance driven (0.5 per km at full intensity) and never
  clearing on the leg, costing up to 30 % torque, FILTER from the warning level, scoring the
  engine at 0.005/s past the damage level (slow down; a filter); `Env.Cold` is a 10 % torque
  multiplier and the COLD lamp, no car damage, the player's exposure is what it attacks (keep
  moving; a heater). `Resistance` per tag is the hook for M4's parts and consumables.
- **Dash and cabin cues.** The cluster gained a coolant temperature dial next to the fuel dial
  (same sweep) and three lamps, FILTER, COLD and RADIATION (eight in the row now); `Describe`
  lists them and `CheckDialVisibility` covers the new dial. The canvas HUD adds, in the seat,
  the weather line (state, rain or snow %, wetness, temperature, storm pressure), RADIATION and
  STORM FRONT while inside, and a line per condition at warning or damage ("OVERHEATING - ease
  off", "FILTER CLOGGING - slow down", "COLD - engine down on power", then "ENGINE COOKING",
  "FILTER CHOKED"); on foot the exposure drain rate and its cause.
- **The greybox leg.** `Art/setup_m3_leg.bat` builds `L_Leg01` under `Content/GrandTour/Legs`:
  a 1.5 km tarmac floor, the start with `AGTLegStart` naming DA_Leg_01, a 12 x 12 m roof on
  posts at 250 m (drive under it in the rain and watch the ground stay dry), a dirt section
  300..600 m and a mud crossing at 700 m with a steel post beside it, checkpoints at 400 and
  800 m, the extraction zone at 1200 m, the radiation pocket 80 m off the road at 600 m with
  two alloy caches, three cable bundles and two wrecks on their tables, and the weather front
  starting 300 m behind the start. The leg starts overcast. Startup map is still L_TestTrack.
- **Tests.** `-GTLegTest` (11 s): a runtime leg with checkpoints 30 and 90 m ahead and the
  zone at 150 m; staging with the timer at 0, the timer starts on the move, checkpoint 1 clears
  by driving through, the zone refuses the car before checkpoint 2, checkpoint 2 by teleport,
  a 2 s stop in the zone finishes the leg at 9.7 s with 3 scrap and 2 wire hauled (7 kg, value
  23), rank 2 of 4, recorded in the subsystem. `-GTWeatherTest`: clear to rain in 2 s; after
  4 s rain 0.70, wetness 0.42 mirrored in the collection and the traction, tarmac grip 0.89,
  383 drops live and none in the space under the roof, ambience RMS 0.082;
  3 s on foot in the rain 100 -> 96.9 at 1.05/s, 3 s under the roof no loss; snow: -5 C,
  cover 0.072 after 3 s; a front parked 50 m ahead with 100 m of influence: pressure
  0.50, rain 0.50 with the state still Clear. `-GTHazardTest`: the front 90 m out at 10 m/s:
  pressure 0.06 -> 0.50 -> inside at 6 s with the car flagged; 2.5 s on foot inside 100 ->
  76.2, glass 0.965, body 0.972; the zone: 3 s in the car engine 0.988, lamp on, 32 clicks/s;
  2 s on foot 88.0; the alloy cache offered with the cutter and one harvest pays alloy.
  `-GTLootTest`: 200 wreck rolls: scrap 1..9, radiator 47, tyre 25, none empty; a node on the
  cache table pays 2 alloy. `-GTEnvTest` (20 s flat out, teleported back to the start every
  7 s on the 400 m floor, then out): heat 1.00 (damage stage, COOLANT lamp from 11 s,
  dial at 38 deg), clog 0.71 (warning, FILTER from 18 s), torque scale 0.53,
  engine 0.960 after 0.070 of condition damage; on foot with all three conditions at 1 the meter
  drains at 2.10/s (1.0 cold + 0.8 heat + 0.3 dust). Regressions: drive, on-foot, winch, surface and body state still pass
  under the run game mode.
- **Traps.** A local named `Zone` in a class with a `Zone` member and an anonymous-namespace
  array named `Defaults` are both errors (C4458 / C4459: the engine has a `Defaults` parameter
  in UnrealType.h). A modulo-of-time check misses ticks at 400 fps: use a threshold that
  advances. A car left rolling on the 400 m flat map drives off the edge in 20 s and then
  "moves" at 90 m/s downward, which the exit refuses. A drop dying on a roof sits 1 cm above it
  for a frame, so a "nothing under the roof" box must stop below the underside. A game state's
  tick flags go in its constructor. The delegate macro goes outside the UCLASS body. Rebuilding
  MF_Weather (clear + update) severs every master's call to it: the property inputs come back
  empty (or, for the glass, on the pre-weather node). `setup_m3_weather.bat` therefore runs
  weather, body and masters in that order, and `setup_m1_masters.py` repairs a severed
  BaseColor / Roughness from the master's own parameter nodes and refreshes an existing call
  instead of deleting it. Wind-blown drops drift about a metre in under an open roof edge.

## 16. Car doors (2026-09-12)

Asked for by the user while M4 was still unverified (its base and loop tests had not run). C++ on the
existing body and car, verified by `Art/door_test.bat` (`-GTDoorTest` on L_DriveTest; `gpu` adds two
pictures in Saved/Screenshots/Doors), PASS. The on-foot, winch, body and drive regressions still pass. Not hand-tested yet.

- **What opens.** The blockout's four door objects (frontDoors and passengerDoors, mirrored left and
  right) were already separate panels, so nothing was modelled. They are the lower door skins only,
  sill (z 39) to belt line (z 115): the window openings above belong to the Pillars object, so an
  open door has no window frame on it. Full-height doors would need the frames split per door in
  rangerover.blend, which is the user's modelling call.
- **Hinges.** Every panel was exported about the car origin, so `UGTBodyComponent` computes a hinge
  per door from the mesh bounds: the front edge (max X) on the outer skin (min Y on the left, max Y on
  the right) at mid height, vertical axis. A hinge scene component sits there on the car mesh and the
  panel hangs off it at minus the hinge offset, so a shut door is exactly where it was. Front doors
  hinge at X 91.6, rear doors at X -9.5, all at |Y| 91.2. The swing is 65 degrees outward (left doors
  +yaw, right doors -yaw) over 0.45 s with a smoothstep ease (`DoorOpenAngle`, `DoorSwingSeconds`); a
  doorway counts as clear from 40 degrees (`DoorwayClearAngle`). Door panels block the Visibility
  channel, query only (`bDoorsTargetable`): the look trace finds them even swung out, and nothing
  physical touches them, so an open door passes through walls and people.
- **On foot.** The car's interaction resolves doors before the winch hook and the boot. Looking at a
  door panel toggles it ("Open front-left door" / "Close front-left door", 0.15 s hold). A hit on the
  body inside a door's shut outline means the door (still shut) or the doorway (open, or the door is
  gone): a front doorway offers "Get in", a rear doorway "Close". With `bEnterNeedsOpenDoor` on, the
  default, the rest of the car answers "Open a front door to get in"; off restores "Get in" anywhere,
  with the driver's door swinging open and shut for you. The repair kit on a damaged side still wins.
- **Getting out and in.** F opens the driver's door and it stays open. The exit spot moved from beside
  the door (car space 40, -175, exactly where the open door now swings) to just behind its trailing
  edge, computed from the door (`GetExitSpotBehindDoor`): car space (-34.5, -175.2), 179 cm from the
  car's centre; `ExitOffsets` are the fallbacks. Getting in shuts the door you used 0.2 s after the
  swap (`EnterCloseDelay`, plus the swing if it was still opening). In the seat the HUD lists open doors.
- **Damage and repair.** A dead side region still throws its doors off as physics props, and the doorway
  then stays clear. `ReattachAll`, the lift's repair, hangs a door back on its hinge, shut and targetable.
- **Test.** Four doors with hinges at their bounds and the driver's door front-left; all four open to
  65.0 degrees with every trailing edge within 0.00 cm of the hinge maths (the driver's at car space
  48.9, -182.8); shut again within 0.5 cm; out at (-34.5, -175.2) with the door opening; prompts: the
  doorway "Get in", the open door "Close front-left door", the shut door "Open front-left door", the
  rear arch "Open a front door to get in"; closed and opened by hand; in through the doorway and shut
  behind; the left side killed: both left doors off and "Get in" with no door; back on the hinge.
- **Not done.** Open doors do not break the cabin's exposure seal yet (ARCHITECTURE 6b: hazards leak in
  faster); doors do not swing or slam with the car's motion; they collide with nothing; dents on doors
  are unchecked on screen and are not expected to read correctly on the blockout's mesh density.
- **Traps.** A screenshot request is served on the next frame drawn, so changing the view target in the
  same tick captures the new view (the first outside door picture came out as the character's view).
- **Changed with M4's review (2026-09-13, section 17).** An open doorway's zone reaches the roof line (Z 175), so looking in
  above the door skin still offers "Get in"; an exit spot blocked at ground level by a low step (the lift's 20 cm edge,
  anything up to 45 cm at the contact) stands you on the step instead of moving you to the other door.

## 17. M4 base + crafting (2026-09-12, first run 2026-09-13)

Everything below is C++ under `Source/GrandTour` in the ARCHITECTURE 2 folders (Parts/, Crafting/, Economy/,
Base/, Core/), greybox where art is needed. Written on 2026-09-12 and first run on 2026-09-13 by two headless
tests: `Art/base_test.bat` (`-GTBaseTest` on L_DriveTest: the five stations spawned beside the car) and
`Art/loop_test.bat` (`-GTLoopTest -GTNoLoad`, starting on L_Leg01: leg -> base -> leg across two level loads).
The loop test passed first time; the base test failed one check (the lift put the part it replaced into the
bag, not the boot) and passed after the fix. A review then found sixteen more defects, fixed the same day (below).
`FGTM4TestRunner` (Core/) scripts both tests from `AGTRunGameMode::Tick` or `AGTBaseGameMode::Tick` and logs a
`GTDRIVETEST m4` line per step; the loop test keeps its place in `UGTRunSubsystem::TestStage` across OpenLevel.
`Art/setup_m4_base.bat` writes the content and L_Base; `Art/base_shots.bat` renders pictures of it. Nobody has
played it by hand yet.

- **Items.** `UGTItemDefinition` (Parts/, a primary data asset: id, name, kind, weight, base price, whether the
  trader stocks it), with `UGTPartDefinition` and `UGTConsumableDefinition` deriving from it (ARCHITECTURE 4).
  `UGTItemRegistry` (a game instance subsystem) loads DA_Item_* from `Content/GrandTour/Items`, DA_Recipe_* from
  `Crafting` and DA_Upgrade_* from `Economy`, and builds anything missing from the C++ defaults (`GTItemDefaults`,
  `DefaultRecipes`, `DefaultUpgrades`), so a fresh checkout and a headless run behave the same; the M2 item
  table's weights and prices (`GTItems`) now answer through it. `setup_m4_base.bat` writes the assets from the
  same defaults: 24 items (4 resources, 15 parts, 5 consumables), 7 recipes, 7 upgrades. Resources: scrap 2 kg /
  5 credits, wire 0.5 / 4, bolts 0.2 / 2, rare alloy 4 / 150 (not stocked).
- **Parts.** The Tier 1 shape of sections 3 and 7: one part per named slot, no socket graph. A part has its
  slot, a tier, tuning contributions (torque, drag, grip and rolling scales, tank litres, winch pull),
  resistances by tag (0..1), the condition entries it owns (installing it sets them to full health), a tag
  dependency (`RequiresTag` / `ProvidesTags`), a `DamageScale` nothing reads yet, and a greybox box at a
  car-space socket, so the hands-on install of a later tier only adds the interaction. The fifteen: engine (M)
  150 kg / 300 and (L) torque x1.25 / 650; radiator 80 and big radiator (Env.Heat 0.5) 180; air filter (Env.Dust
  0.6) 60; cabin heater (Env.Cold 0.7) 120; suspension stock 200 and heavy duty (damage scale 0.6) 450; road tyres
  240 and knobbly (grip x1.10, rolling x1.2) 400; fuel tank 81 L 150 and long-range 120 L 350; winch 40 kN 350
  (gadget slot); sealed cabin (Hazard.Weather 0.5) 250 and lead lining (Hazard.Radiation 0.6) 400 (shielding
  slot). Tyres and suspension draw no box.
- **Part slots.** `UGTPartSlotsComponent` (Parts/, on the car, ticked by it): nine slots in display order
  (Engine, Radiator, AirFilter, Heater, Suspension, Tyres, FuelTank, Gadget, Shielding) and a default loadout of
  six (engine M, radiator, stock suspension, road tyres, the 81 L tank, the winch). `CanInstall` says why not
  (unknown item, not a part, no such slot, needs a provider) and what it would replace; `Install` swaps,
  `Remove` empties. `RequiredSlots` (engine, radiator, suspension, tyres, tank) are the slots the car cannot run
  without, and the lift only swaps their parts. Every change pushes the installed set out (`ApplyEffects`):
  resistances summed per tag and clamped to 1 into `UGTConditionComponent::HazardResistance` (Hazard.*) and
  `UGTEnvironmentComponent::Resistance` (Env.*), which closes both M3 hooks; the tank capacity from the tank part
  (with no tank the fuel stays where it is, so refitting a tank does not empty it); the winch enabled only by a
  gadget with a pull, at that pull (the M2 line: the winch is now a gadget-slot part); the greybox boxes rebuilt.
  The parts are the first stage of the tuning, base -> parts -> traction -> environment -> condition -> Chaos,
  multiplying torque, grip and rolling in; no engine or no tank means no torque. Consumables add temporary
  resistances that tick down in `Update`.
- **Recipes.** `UGTRecipeDefinition` (Crafting/): the station tag, the workbench crew tier needed, inputs, an
  output and a craft time (shown on the row; crafting is instant for now). Seven at the workbench: radiator
  (6 scrap, 2 bolts), air filter (3 scrap, 2 wire), cabin heater (4 scrap, 3 wire, 2 bolts), coolant flush
  (1 scrap, 1 wire), filter cleaner (1 wire), and from Workbench I the big radiator (10 scrap, 4 bolts, 1 alloy)
  and the lead lining (8 scrap, 2 alloy).
- **Crew upgrades.** `UGTUpgradeDefinition` (Economy/): four tracks as gameplay tags, tiers bought in order, the
  effect read by the station that cares, tiers kept in the campaign. Mechanic I 200 (lift repairs half price)
  and II 500 (free); Trader I 200 (pays 70 % of base) and II 500 (80 %); Scout I 200 (the briefing shows peak
  intensities) and II 500 (the curves); Workbench I 300 (tier-2 recipes).
- **Stations.** `AGTCraftingStation` (Crafting/, ARCHITECTURE 5): an interactable greybox box. Look at it and
  press E ("Use workbench", 0.2 s) to open its screen on the character; E on it again or Tab closes it, and so do
  walking 6 m away, getting in the car and opening the boot. Scroll (d-pad left / right) moves the selection one
  row, never onto a caption and never past either end; T (gamepad Y) acts on the selected row. The rows are
  rebuilt from the station after every act (`BuildRows` / `Act`; `ActOnRow` for the tests) and the cursor stays on
  the row it acted on, not its index, since a purchase can add a sell row above it; when that row is gone (a stack
  sold out) the cursor lands nearby and T waits for a scroll. E is never captured by a screen, and the crosshair
  and the interaction prompt stay on, the prompt beside the panel. Nothing is used up or taken off unless it has
  somewhere to go: costs come out of the bag first, then the boot; what is made or bought goes into the bag first,
  then the boot; parts taken off the car go to the boot first. The canvas HUD draws the name, a window of rows that
  scrolls with the cursor ("more above / below"), the selected row's hint, the last message and the key line; UMG
  replaces it in M7 and the rows carry over.
  - *Workbench:* each recipe with its inputs, and the craft time, what is missing, the tier it needs, or that its
    result would not fit.
  - *Car lift* (a 5 x 2.6 m slab): works on the player's car within 12 m (`LiftRadius`), else it says to park on
    the lift. Rows: the nine slots with the installed part and its health (T takes an optional part off to the
    boot; a required slot says to install a replacement, and a part with no room in the boot or the bag stays on);
    every part in the bag or the boot with its slot and whether it fits or what it replaces (T installs; the old
    part goes to the boot, or the bag when the boot is full, and the install is refused when it has nowhere to go);
    repair everything, offered whenever a part is below full health or a panel is off, at 4 scrap per whole point
    of missing part health plus 0.5 a detached panel, times the mechanic factor, rounded up ("free" at Mechanic II;
    every part to full, panels back on their hinges shut, dents out); wash (dirt, wetness and snow). Tuning at the
    lift waits for runtime suspension setters.
  - *Trader:* sells anything in the bag or the boot, one at a time, at 60 / 70 / 80 % of base price by the trader
    tier (at least 1 credit); buys any stocked item at base price and refunds when neither the bag nor the boot
    has room. The header shows the credits.
  - *Crew tent:* the seven upgrades with owned or cost and the effect; a tier is refused before the one below it
    or without the credits.
  - *Briefing board:* read only. The next leg's name, par and limit, the weather at the start, the conditions at
    the scout tier's precision (names only, peak % at I, an eleven-step curve with start / middle / end % at II),
    the rivals' times and how to depart.
- **Consumables.** Fuel can (20 L into the tank), coolant flush (coolant heat to 0), filter cleaner (clog to 0),
  rad pills (Hazard.Radiation 0.5 for 120 s, 40 exposure back), thermal blanket (Env.Cold 0.6 for 300 s). Used on
  foot from the Tab inventory with T (the list marks what is usable and shows what the last use did). One is used
  up only when it changes something: a flush on a cool engine or a can on a full tank (or with no tank) stays in the
  bag, "would do nothing right now". A resistance goes to both the car's part slots and the character's own
  (`AGTPlayerCharacter::GetResistance`) and keeps running through a level change.
- **Campaign, carry and save.** `FGTCampaignState` gained credits (300 at the start), crew tiers by track and the
  next leg's path; `FGTCarrySnapshot` is what travels between levels: the bag, the boot, the loadout, every
  part's health, the fuel, and the consumables' running resistances on the car and on the character.
  `AGTRunGameMode::FinishLeg` captures it, records the result and saves; Enter / Start on the results screen now
  opens L_Base (or reloads the leg when L_Base is missing). A leg applies a held snapshot when it starts, and a leg
  started on its own map (Play in the editor) loads the save first, so its extraction continues the campaign
  instead of saving a fresh one over it. `UGTSaveGame` (version 1) holds the campaign and the snapshot in slot
  `GrandTour0`. Runs with a self-test switch (any `-GT...Test`, or `-GTBaseShots`; `UGTRunSubsystem::IsSelfTestRun`)
  save to `GrandTourTest0` instead and never load a save on their own, and the base and loop tests empty that slot
  when they finish. Before that fix (2026-09-13) the tests deleted `GrandTour0`, left their own campaigns in it, and
  every leg a test finished saved over it, so the first hand test of the base would have loaded a test's loadout.
- **Base game mode and gate.** `AGTBaseGameMode` (Base/, derives from the test game mode so the headless flags
  work): on the first tick it applies the snapshot (a fresh start loads the save first, unless `-GTNoLoad`),
  saves, and gets you out beside the car with no camera blend. `AGTDepartGate` (Base/): a 4 x 12 x 8 m volume
  with a red slab; the player's car driven into it with you in the seat departs once: capture, the campaign's
  next leg set pending, save, open the leg's map.
- **L_Base.** `Art/setup_m4_base.bat` (run setup_m1_track and setup_m3_leg first) builds
  `Content/GrandTour/Base/L_Base`: a 120 x 80 m tarmac floor with a 60 x 60 m walled yard (x -20..40 m, y
  -30..30 m) open in a 14 m gateway at the front; the lift at the PlayerStart, so the car spawns parked on it facing
  the gate road; on the driver's side (-Y, where you get out) the workbench at (3, -8) m, the trader at (-5, -8) m
  and the briefing board at (11, -6.5) m; the crew tent across the yard at (-12, 10) m; a 40 m road to the gate at
  x = 40 m between two posts. The map's game mode override is AGTBaseGameMode; every other map keeps
  AGTRunGameMode. GameDefaultMap is L_Base; the editor still opens L_TestTrack. On the way the stations were moved
  off the gate road (the briefing board stood in the car's path) and the checkpoint, extraction and gate marker
  slabs now trace down to the ground (since M3 they had sat under the floor).
- **Tests.** `-GTBaseTest` (L_DriveTest) waits for the car to land and stop, then: the stations beside the car, 12
  scrap, 4 bolts and 5 wire in the bag, engine 0.5, radiator 0.4, wetness 0.7; craft a radiator (6 scrap left);
  install it (radiator 1.00, the old one in the boot); repair for 2 scrap (engine 1.00); wash (wetness 0.00); sell 5
  wire (300 -> 310 credits); buy a heater (190) and install it (Env.Cold resistance 0.70 on the parts and in the
  environment); Scout I refused at 190 credits, bought after 100 more (tier 1), and the briefing shows peaks (cold
  80 %, dust 70 %, heat 60 %); a coolant flush takes heat 0.8 to 0; a thermal blanket takes the car's cold resistance
  to 1.00 and the character's to 0.60; a step of checks for the review fixes (below); save, add 1000 credits, load:
  130 -> 130 with the heater in the loaded loadout and the blanket's resistance for the car and the character; the
  registry came from the assets (24 / 7 / 7). `-GTLoopTest -GTNoLoad` (L_Leg01): 3 scrap and 1 wire in the boot, the
  checkpoints by teleport, a 2 s stop in the zone finishes the leg (rank 1 of 5, saved), continue -> L_Base: on foot,
  the boot's 3 scrap and 1 wire, one result, a save, the trader, lift and gate found; buy and install a heater (180
  credits) and use a thermal blanket; back in the car and teleported into the gate -> L_Leg01 staging with the heater
  installed, car cold resistance 1.00 (0.7 plus the blanket), the character's own 0.60, the 3 scrap, 180 credits and
  leg index 1. Regressions, run one after another on the build before the review fixes and again after them: drive
  (19 mappings), on-foot (out 179 cm from the car, jump 90 cm), winch (snap, winch health 0.49, the rotten post out),
  body (20 panels, 4 off), surface, body state, leg (9.7 s, 2nd of 4), weather (rain 0.70, wetness 0.42, 383 drops
  and none under the roof), hazard, loot (200 rolls), env (heat 1.00, clog 0.71, torque x0.53) and door (every
  check) all PASS (body on its rerun the second time, see Traps). Pictures: `Art/base_shots.bat` (`-GTBaseShots
  -GTNoLoad`, off-screen) wrote all six to Saved/Screenshots/M4. The overview and the top-down view show the walled
  yard, the car on the lift at the foot of the road to the gate, the workbench, trader and briefing board on the
  driver's side and the crew tent across the yard; at eye level from the road the HUD shows the weather line, the
  credits, the tool line and the exposure bar; all four doors open from outside; looking into the open driver's
  doorway offers "[E] Get in". Retaken after the review fixes, the lift screen shows the required slots greyed with
  the selected engine's hint "the car needs one: install a replacement to swap it", the winch row still available,
  install, repair for 2 scrap and wash rows, and the crosshair and the "[E] Get in" prompt beside the panel instead
  of hidden under it.
- **Review (2026-09-13).** With both tests passing, a read-only review in five areas (stations and screens, parts
  and items, save and loop, doors and jump, the base level), each checked by a second reader trying to refute it,
  confirmed sixteen findings and refuted two. Fixed the same day: the lift took a part off, or swapped one out, and
  destroyed it when neither the boot nor the bag had room, while saying it had worked, and the workbench used up
  inputs for an output with nowhere to go (both now check room first and say why not); after Mechanic II the repair
  row read "nothing to repair" because damage was judged by the price; the station cursor kept a row number, so a
  second T after buying or selling could buy something else; scrolling up at the top parked the cursor on a caption;
  the screen hid the crosshair and prompt while E still worked, and survived getting in or opening the boot; long
  lists ran off the screen with the cursor still reaching the hidden rows; taking the tank off and putting it back
  emptied it; an empty tyre, suspension or radiator slot changed nothing; a leg started on its own map saved a fresh
  campaign over the player's at extraction; looking into an open doorway above the door skin said "Open a front door
  to get in"; parked off-centre on the lift, getting out went to the passenger side because the lift's 20 cm edge
  blocked the spot; consumables were used up when they did nothing, and timed ones were lost at the gate. Left on
  the backlog: carrying region health, dents, detached panels and dirt between levels, and per-part wear. Refuted: a
  passenger-side entry leaving the driver's door open (intended, harmless) and an exit spot overlapping an open rear
  door (doors collide with nothing). The base test gained a step for every fix, driven the way the keys drive it
  where it matters, and each one passes: getting out beside a 20 cm slab stands you on its edge on the driver's side
  (capsule centre 105.8 cm above the floor, against 98 at ground level); the engine's remove row reads "the car needs
  one: install a replacement to swap it"; at Mechanic II "Repair everything (free)" takes the engine from 0.5 to 1.00
  for no scrap; with the bag and the boot packed (38 and 1210 bolts) the lead lining is refused ("no room for it
  (60 kg)") without using its inputs and the winch stays on ("no room for it (30 kg)"); on the trader, T twice on Buy
  Wire buys two wire although the first adds a sell row above it, selling the only radiator leaves the next T doing
  nothing, and sixty notches up leave the cursor on the first row; a coolant flush on a cool engine stays in the bag;
  looking into the open doorway 30 cm above the door skin offers "Get in"; the save carries the blanket's resistance
  for the car and the character. The loop test carries that blanket from the base to the next leg. A second read-only
  pass over the fixes themselves (four areas, each checked by a refuting reader) confirmed one more: the exit step-up
  only tested that the raised capsule was clear, so its rounded foot could settle on the edge of something about 70 cm
  tall; the step is now taken only when the contact is at most 45 cm above the ground. It also noticed that the test
  slab reached under the rear-left wheel's ground sweep and could lift that corner, so the slab is now 30 cm wide
  (car-space Y -150..-120). Base, loop, on-foot, winch and door PASS again on that build. Its other points were
  refuted or already on the backlog (a spare swapped in returns the worn part whole, per-part wear).
- **Not done.** Region health, body dirt, dents, detached panels and the character's exposure are not carried
  between levels (the lift's repair and wash cover them at the base; a leg starts clean). Items carry no wear, so a
  worn part taken off and refitted, or swapped out for a spare of the same kind, comes back whole. Consumables cannot be used from the seat. Crafting is
  instant. No tuning at the lift. Hands-on installation stays a later tier; the lift and a physical install must write
  the same slots. `DamageScale` is not read, so the heavy-duty suspension does nothing yet. Tools are not items the
  trader sells. Open doors do not break the cabin seal. The trader has unlimited stock. The M3 note stands: harvesting
  is a placeholder and resources are item ids any source can pay.
- **Traps.** A headless test must never touch the player's save slot (above). A car spawns above the floor and is
  still dropping 0.5 s in, when the base test used to run its first steps: anything that reads the car's pose (the
  exit spot, a look into the doorway) waits for it to land and stop, or the look is aimed at where the car was. A
  capsule resting its rounded foot on a step's edge sits lower than on the step's top: 105.8 cm above the floor for a
  20 cm slab whose edge is 25 cm in from the capsule's axis, against 98 cm when placed on the ground. Chaos reports the
  same square wall hit as one, two or three hit events with different speeds between identical runs of the body test
  (deltaV 1546; 206..220 in two events; once three events after a bounce at 22 degrees that left the front at 0.15 with
  no panel off, a FAIL on unchanged code that passed on the rerun): rerun it once before suspecting a change. Steps
  that act through a station's rows directly can pass while the same thing through the keys fails (the cursor bug), so
  the base test drives the trader through the character's own selection and T calls. A lift repair (`ReattachAll`)
  shuts every door.

## 18. M5 tour: leg sequence, mission types, rival standings, ending (2026-09-14)

Everything below is C++ under `Source/GrandTour` in Race/ (new, the ARCHITECTURE 2 folder for the leg sequence,
the standings simulation and the ending), Run/ and Core/, greybox where art is needed, and verified headless by
`Art/tour_test.bat` (`-GTTourTest -GTNoLoad` on L_DriveTest with a runtime tour, so no assets are needed) on
2026-09-14, PASS first run. `Art/setup_m5_legs.bat` writes the assets and builds the four new leg maps. The three
decisions of 2026-09-14 (PROJECT_PLAN 6) shape it: legs are named challenges in the style of the TV specials, the
base is a camp per tour, and the tour is the sequence.

- **Tour.** `UGTTourDefinition` (Race/, a primary data asset): id, name, region, the camp map, the legs in order as
  asset paths, the rivals, the starting credits, points and prize credits by placing, and three ending lines (win,
  podium, the rest). `ApplyDefaultTour01` is Tour 1, "The Altiplano" (Bolivia): the five default legs, four rivals
  (Ines Varga in a lowered Impreza, quick and fragile, skill x0.88, spread 10 %, grit 0.70; Teodor Balan, a tidy
  Pajero, x0.97 / 5 % / 0.90; Marisol Quispe, a tired Hilux, x1.06 / 6 % / 0.98; Wendell Price, something with a
  snorkel, x1.22 / 12 % / 0.80), 300 credits, points 10 / 8 / 6 / 5 / 4 and prizes 200 / 150 / 100 / 60 / 40 for
  1st to 5th. DA_Tour_01 lives under `Content/GrandTour/Race`; the run subsystem builds a runtime copy when the
  asset is missing, the way the item registry does.
- **Campaign.** `FGTCampaignState` lost `NextLegPath` and gained `TourPath` (DA_Tour_01), `Seed` (drawn at
  `ResetCampaign`) and keeps `CurrentLegIndex` as the index into the tour's legs. `UGTRunSubsystem::ResolveTour`,
  `ResolveLeg(Index)` (the asset at the tour's path, else the default leg of that index built at runtime) and
  `ResolveNextLeg` (null once the tour is over: `IsTourComplete`). `RecordResult` banks the prize and always moves
  the index on, a did-not-finish included. `UGTSaveGame` is version 2; a version 1 save gets the default tour path.
  `ResetCampaign` keeps the tour, takes its starting credits and draws a new seed.
- **Mission types.** `UGTLegDefinition` gained `Mission` (`EGTMissionType`: TimeTrial, Endurance, Photograph),
  `MissionBrief` (the briefing's words, in the show's voice), `PhotoSubjectName` and `PhotosRequired`, and
  `MissionObjective()` for one line of what the leg wants. Every kind is scored by the leg time and placed against
  the rivals; what differs is what the zone accepts and what counts as a finish. Time trial: the checkpoints in
  order, past the limit the result is marked overtime but counts. Endurance: the same, but past the limit the leg
  is failed (`AGTRunGameState::IsMissionFailed`, the HUD says OVER THE LIMIT: no result) and the zone still ends it,
  as a did-not-finish worth no points and no prize. Photograph: the zone refuses the car until `PhotosTaken`
  reaches the requirement ("photograph the spectacled bear first"; `GetExtractionRefusal` and `LastRefusal` feed
  the HUD), and the HUD carries "Photograph the spectacled bear  0 / 1" under the checkpoint line.
- **Photo subject.** `AGTPhotoSubject` (Run/): an interactable greybox animal, a body box on four leg posts. On foot,
  look at it from up to `PhotoRange` (25 m) and hold E for 1.5 s ("Photograph the spectacled bear (hold still)");
  `Interact` counts it in the run state. Come within `FleeRadius` (8 m on foot; 15 m in the car) before the picture
  and it moves off `FleeDistance` (40 m) away from you, landing on whatever is under the new spot, up to `MaxFlees`
  (3) times; then it is too tired to care. The interaction component now traces to `LongRange` (30 m) and accepts
  a hit beyond arm's length only when the interactable's own `GetInteractionRange` (new on `IGTInteractable`,
  0 by default) allows it, so nothing else changes.
- **The five legs.** `UGTLegDefinition::ApplyDefault(Index)` (Leg 01 unchanged as `ApplyDefaultLeg01`): 1 "The
  Flats", time trial, 1.2 km, par 300 s, limit 600, overcast; 2 "The Washout", endurance, 1.6 km, par 420, limit
  720, rain, three mud crossings with a front 200 m behind at 5 m/s; 3 "The Hide", photograph, 1.4 km, par 480,
  limit 900, clear, the bear in a hide of posts 150 m off the road past the first checkpoint beside a radiation
  pocket ("get closer and so does your skin"); 4 "The Pass", time trial, 2 km, par 540, limit 1000, snow, cold
  all the way; 5 "The Salt", endurance, 2.4 km, par 600, limit 1080, clear, heat and dust rising to full. Each has
  a brief and fallback rival times (par x 0.83 / 0.93 / 1.07 / 1.33) for a leg run outside a tour.
  `UGTVehicleSetupLibrary::CreateLegAssets` now writes all five (StartWeather by name) and `CreateTourAssets`
  writes DA_Tour_01. `Art/setup_m5_legs.bat` (after setup_m1_track, setup_m3_weather and setup_m3_leg) writes both
  and builds `L_Leg02`..`L_Leg05` from a table in `Art/Unreal/setup_m5_legs.py`: a tarmac floor 400 m wide,
  surface lanes (dirt, mud, snow) with marker posts, a zigzag route (the checkpoints sit up to 80 m off the axis)
  marked by posts every 100 m, checkpoints, the extraction zone, radiation pockets with alloy caches, cable
  bundles, wrecks and steel posts, weather fronts, a shelter roof on the pass, and on leg 3 the subject in its
  hide. Nobody has looked at them yet.
- **Rival standings.** `GTStandings` (Race/): `SimulateRival` draws a rival's leg once from the campaign seed, the
  leg index and the rival index (an `FRandomStream`), so a save replays the same table and the briefing can quote
  expectations without spoiling the draw: time = par x skill x (1 + consistency x a normal clamped to 2.5 sigma); a
  did-not-finish by (1 - grit) x the mission's hardness (time trial 0.25, photograph 0.7, endurance 1.0) and, on an
  endurance leg, by a time past the limit. `PlaceLeg` places the player among the finishers by time (ties to the
  player), everyone who dropped out after them, and gives points by placing (a DNF scores 0). `Build` sums the
  recorded results into `FGTStandingRow`s (points, then legs finished, then total time) and `EndingLine` picks the
  tour's line for the player's final place. `UGTRunSubsystem::ScoreResult` does the draw at extraction and fills the
  result's `Rivals` (name, time, finished, place, points), `Rank`, `Points` and `PrizeCredits`; `BuildStandings` and
  `EndingLine` serve the HUD and the board. Outside a tour the leg's fallback times rank as before.
- **Results and ending.** `FGTLegResult` carries the mission, its verdict in words (`MissionText`: "Photographed the
  spectacled bear", "Over the limit: did not finish", "Extracted inside par"), the photographs, the rivals'
  outcomes, points and prize. The canvas results screen is two columns: the leg on the left (LEG COMPLETE or DID
  NOT FINISH, the verdict, time against par, checkpoints and photographs, the haul), the placings on the right
  (everyone on the leg quickest first with DNFs at the bottom, the points and credits earned, then the tour table:
  place, name, points, legs finished / run, total time). After the last leg the title is TOUR OVER, the table is
  final and the ending line sits under it; Enter still goes to the camp. There the gate refuses (the log says why)
  and the briefing board shows the final table, the ending and a "Start a new tour" row: T resets the campaign on
  the same tour (leg 1, the starting credits, a fresh seed and table) and saves; the car keeps whatever is on it.
- **Briefing board.** The tour and leg number, the mission in brackets, the brief wrapped to the screen, the
  objective line, par and limit (an endurance limit says "past it: no result"), the weather, the conditions at the
  scout tier as before, then each rival with their car, their usual pace on this leg (par x skill) and their points,
  and the player's own place in the table.
- **Economy and difficulty.** Pars rise 300 -> 600 s and limits 600 -> 1080 s down the tour; prize money by placing
  is the second income beside the trader (a clean tour pays 200 a leg for a win). The tables live on the tour
  asset. This is the first pass of the curve, not the tuning: nobody has driven legs 2 to 5.
- **Tests.** `-GTTourTest` (11 s): the runtime tour resolves five legs with their missions and four rivals; the draw
  is identical for the same inputs, differs across seeds (20 of 20), stays within 0.6..1.9 of the expected time over
  4000 draws, drops the low-grit rival on an endurance leg about one time in five (0.20) and the steady one on a
  time trial almost never (0.01); placings: quicker than all is 1st with 10 points, slower than all is last of the
  finishers, a DNF scores 0, the rivals' places are distinct from 1. Then in the world: a photograph leg (a
  checkpoint 30 m ahead, the zone at 90 m, two bears 40 m off either side) stages with "Photograph the spectacled
  bear  0 / 1"; through the checkpoint and stopped in the zone the extraction is refused ("photograph the spectacled
  bear first"); on foot 20 m from the first bear the offer reads "Photograph the spectacled bear (hold still)" and
  the hold takes the picture; 5 m from the second it moves off 40 m; back in the car the leg finishes: completed,
  "Photographed the spectacled bear", 1st of 5, +10 points, +200 credits (300 -> 500), leg index 1, a five-row table
  with the player on 10. An endurance leg with a 2 s limit: past it the line reads OVER THE LIMIT, the zone ends it as
  a did-not-finish, 0 points, 0 prize, leg index 2. Legs 3 to 5 scored straight into the campaign: the tour is over,
  the table is sorted (the player 40 points, Balan 27, Quispe 21, Price 20, Varga 16), credits 1100, the ending
  line "You won the Altiplano. ..."; save, reset, load brings the same table, seed and ending back; a briefing board
  spawned beside the car shows "is over" and "Start a new tour", and T on it resets to leg 1 of 5 with 300 credits
  and a new seed, saved. The leg test's rank check and the loop test's credit check were updated for the tour's
  scoring (rank 1 of 5 with points; credits 300 + the first leg's prize - 120). Regressions on the build: base,
  body, body state, door, drive, env, hazard, loop, loot, mud, on-foot, rough, spray, surface, track, weather and
  winch PASS; the leg test failed once (below, the cold-scoring trap) and passed with tour and loop after the fix.
  `Art/setup_m5_legs.bat` then wrote the five leg assets, DA_Tour_01 and L_Leg02..05, and the loop test passed
  again departing to L_Leg02 with DA_Leg_02.
- **Not done.** The difficulty and economy curve is a first pass, untuned (BACKLOG). Bailing out of a leg early at
  a cost (the core loop's "or bail out early") does not exist: a leg ends only at the zone. Photo subjects are
  static greybox boxes that teleport when spooked; no animation, no sound. A photograph leg cannot end without the
  picture. Only three mission kinds. The new tour from the board keeps the car's loadout and both inventories (the
  snapshot is cleared, the pawns are not). The camp is still L_Base for every tour (one camp per tour is M6).
  Legs 2 to 5 have not been driven or looked at. The rivals' table ignores the haul.
- **Traps.** A leg's `RivalTimesSeconds` no longer decides the rank inside a tour: `ScoreResult` overwrites `Rank`
  with the tour placing, so a test that expects the fallback rank (the leg test did) must expect the draw. The
  runtime tour only exists once something resolves it: the first `ScoreResult` read a null runtime tour on a leg run
  cold (no base, no reset) and fell back to the leg's own times, rank 2 of 4 and no points; it now calls
  `ResolveTour` itself. A `/Game/...` map argument in a chained Bash call is mangled into a Git path even with
  `MSYS_NO_PATHCONV` exported in the same chain, and the run then loads the default map (L_Base) and sits there; run
  the tests from a bash script file. An
  absurd endurance limit drops every rival too (their times pass it), so a player DNF can read "1 of 5" with no
  finishers.

## 19. M6 terrain first: The Hide gets real ground (2026-09-14)

The greybox phase ended with the user's verdict on the M5 legs ("fine as a base systems test", nothing more to judge
on flat maps), so M6 starts with shape, not textures: one leg with real ground as the proof. C++ under
`Source/GrandTour/Terrain` (the generator) and the setup library, greybox where art is needed, verified by
`Art/terrain_test.bat` (`-GTTerrainTest` on L_Leg03) and looked at through `Art/hide_shots.bat` (`-GTHideShots`,
five pictures in Saved/Screenshots/M6), both PASS on 2026-09-14. `Art/setup_m6_hide.bat` builds it. Nobody has
driven it yet.

- **Generator.** `FGTTerrainSpec` (Terrain/GTTerrainGenerator.h) is one leg's ground: the landscape grid (8 x 8
  components of 2 x 63 quads, 2 m quads, 2 km square, origin and Z scale), the land (a seed, four octaves of Perlin
  noise at 14 m / 320 m, a tilt of 22 m per km along +X, and landforms: hills, bowls, ridges and channels with a
  smooth falloff), the road (the route as a polyline in metres, a 6 m half width, a 14 m shoulder, a 13 % grade
  limit and an 80 m smoothing length), what the road is paved with by arc length (`FGTSurfaceSpan`), the ground
  layer away from it, a snow line and the channel depth that turns to mud. `GTTerrain` is pure: `BaseHeightM` is
  the land, `BuildRouteProfile` samples it along the route every 5 m, smooths it and limits the grade forwards and
  back, `HeightM` carves the road in (the profile's height inside the half width, blending to the land across the
  shoulder), `LayerWeights` paints five layers (tarmac, dirt, mud, snow, scrub: the road from its spans, scrub off
  it, mud where a channel digs deeper than the threshold, snow above the line), `Generate` fills the landscape
  height values and the weight bytes for the whole grid, and `SampleHeightCm` / `RouteAtCm` place things on it.
  `HideSpec()` is The Hide: a valley start between two ridges, a swing left onto a plateau (a hill with the bear's
  dell as a bowl beside the radiation pocket), a channel crossing the road about 1115 m along the route, the last
  stretch under a big hillside, the checkpoints at (500, 0) and (1100, 40) and the zone at (1400, 0) as before. The
  one spec is what the setup script, the tests and the pictures all use (`UGTVehicleSetupLibrary::MakeHideTerrainSpec`).
- **Import.** `UGTVehicleSetupLibrary::BuildLegLandscape` (editor only) writes five `ULandscapeLayerInfoObject`
  assets under `Content/GrandTour/Terrain/Layers` pointing at the surface physical materials (scrub reads as dirt),
  generates the data, spawns an `ALandscape` and calls `Import` the way the editor's New Landscape button does, then
  registers the target layers. Two things the button gets from the editor that a commandlet does not (Traps): the
  final weightmaps are written on the CPU through `FLandscapeEditDataInterface` with no edit layer and the textures
  finalised with `PostEditChange`, and the per-component material instances are built by
  `UpdateAllComponentMaterialInstances`. The log line after it lists the material's layer names, one component's
  allocations, a weightmap texel and the instance's static layer parameters, so a black or one-colour landscape can
  be traced.
- **Material.** `M_GT_Landscape` is a copy of `M_GT_Environment` made by `Art/Unreal/setup_m6_hide.py` each run, so
  it keeps the MF_Weather call (wetness, snow, puddles through CanPool), the porosity and the MF_TrackPaint ruts; its
  BaseColor, Roughness and Porosity come from three Landscape Layer Blend nodes over the five layers (constants per
  layer: tarmac 0.16 grey, dirt road a warm 0.52 / 0.38 / 0.22, mud dark, snow white, scrub a dull 0.30 / 0.29 /
  0.19), the scalar ones through a component mask. After any MF_Weather rebuild run setup_m3_weather.bat, then this.
- **L_Leg03.** The flat floor and the old props go; the landscape comes in; the leg's actors are placed on the
  generated heights: the start on the road 20 m in, the checkpoints turned to the road's yaw, the zone, the leg
  start, the pocket with one alloy cache, the bear in its dell ringed by nine boulders with a way in from the road
  side, two cable bundles and a wreck beside the road, a steel post by the crossing, sixty boulders scattered off
  the road, and a 20 km skirt 22 m down so the horizon ends in ground rather than the sky's sea. Boulders are
  greybox spheres. The landscape's height range is -16.7 m to 73.9 m.
- **Tests.** `-GTTerrainTest`: a landscape actor under the leg (DA_Leg_03, two checkpoints, the zone, the bear), every
  leg actor and the car standing on it (the ground trace hits the landscape within their extents), the surfaces by
  traces reading the physical material: tarmac on the valley road, dirt on the climb, dirt off the road, dirt on
  the last stretch, mud at the deepest point of the crossing; the road's steepest grade over 25 m samples 11.8 %
  against a 13 % limit and 28 m of rise, and the land 120 m off the road has a 7.9 m spread of heights; the car
  driven flat out from the start for 8 s covers 84 m, stays within the road and on its wheels. `-GTHideShots`:
  from the road at the start looking down the valley, on the road at the top of the valley looking up the climb,
  the dell from its rim, the crossing from the road above it, an overview from 220 m up. Looked at: the valley
  reads as a grey road between two olive walls with the car on it; the climb as a lighter dirt track winding over
  scrub toward the plateau; the dell as a ring of boulders beside the pocket's green slab (the bear is behind the
  nearest boulder); the crossing as the track dipping into a darker mud band; the overview shows the whole route,
  the tarmac dark, the track light. The relief is gentle: dunes rather than mountains, the user's call whether to
  raise it. Regressions after it: terrain, drive, leg and on-foot PASS (the others were unaffected by the change).
- **The spec as an asset, and the button (later the same day).** The user drove The Hide ("Not bad") and said they
  intend to build levels in earnest themselves, so the spec moved out of C++: `UGTTerrainSpecAsset` (Terrain/) is a
  data asset holding a name and an `FGTTerrainSpec`, every field editable in the Details panel (the route as a list
  of metre points, the spans, the landforms, the noise, the grade limit). `Art/setup_m6_hide.bat` writes
  `Content/GrandTour/Terrain/DA_Terrain_Hide` from `HideSpec()` once and then leaves it alone, so the user's edits
  survive a re-run (`CreateTerrainSpecAssets(Folder, bOverwrite)`). `AGTTerrainBuilder` (Terrain/, editor-only,
  one placed in L_Leg03 as "TerrainBuilder") points at the asset and has three buttons in its Details panel:
  *Rebuild Landscape* throws away the map's landscape, builds a new one from the asset through `BuildLegLandscape`
  and drops the leg's actors back onto the new ground at the height each had above the old one (checkpoints, the
  zone, the leg start, nodes, wrecks, posts, the bear, the player start, and static meshes whose labels start with
  Rock_, Hide_, Roof_, Marker_ or Post_; the horizon skirt is left alone); *Reground Actors* does the dropping on
  its own after the user moves things; *Show Route* draws the route coloured by its spans, the route points, and
  the landforms (green up, red down) in the viewport for a minute. The material path, the layer folder and the
  prefixes are properties. The setup script drives the same functions (it spawns the builder if the map has none,
  points it at the asset, calls the rebuild, places the props, then rebuilds a second time and checks the bear
  came back within a centimetre and about eighty actors were re-grounded), so the headless build and the button
  share one path; the terrain test reads the asset for its spec and checks it resolves. The editor must still be
  closed for the .bat scripts; the button is for inside it.
- **The generator features (the same evening, "Go, generator features next").** The spec gained what the
  MudRunner / SnowRunner reference with rally stretches (PROJECT_PLAN 6) needs, and The Hide got all of them:
  - *Route sections* (`FGTRouteSection`: an arc range and a kind): Road (as before); Track (`TrackWidthScale`
    0.55 of the width); Rally (1.3 x the width, the land smoothed over `RallySmoothM` 30 m instead of 80 so crests
    and dips stay, grades to `RallyGradePercent` 20, and camber); Mud (a bog: 1.6 x the width, the road sunk
    `MudSinkM` 0.4 m into a trough fading in over 10 m, mud across it); Ford (a water crossing: the road drops into
    the ground's channel following it over 10 m at up to `FordGradePercent` 25, mud in the bed, water `DepthM`
    above the road's lowest point through it). Width, smoothing, grade and surface come from the section; the
    profile builder limits the grade per sample by its section.
  - *Camber* on rally stretches: the route's heading smoothed over +-20 m gives a curvature (radians per metre,
    positive to the left); camber = curvature x `CamberGainDegrees` (500) clamped to `CamberMaxDegrees` (7); the
    road surface tilts across its width so a left bend has its left side lower, the tilt carried out to the shoulder.
  - *Alternative lines* (`FGTAltRoute`: points, a half width, a layer): carved like narrow roads with their own
    profile; where lines overlap the one with the stronger presence wins. The Hide's detour leaves the first
    checkpoint south round the plateau and rejoins before the bog, 724 m of 3.5 m track.
  - *Paving in proportion*: the surface layer stops soon after the road's edge, over half its width (at least
    1.5 m), instead of over the fixed shoulder, so a narrow track stays narrow; the cut and fill still blend over
    the full 14 m shoulder.
  - *Water*: `M_GT_Water`, a translucent blue master of its own (water does not get wet, so it stays outside
    MF_Weather); the setup lays a sheet over each ford at the water level (`TerrainFordWaterLevelCm`), 30 m wide,
    with no collision at all so the car drives into the bed and traces reach it.
  - *Winch posts and rocks*: the setup puts a steel post either side of a bog's far end and one at the ford's exit;
    boulders (140) are scattered on the scrub only, thicker where the ground is steep (`TerrainSlopeDegrees`;
    a 12 % chance on the flat rising to 100 % at 25 degrees).
  - *The Hide's spec*: steeper (noise 20 m, the valley walls 40 / 34 m, the plateau 20 m, the hillside 50 m; the
    landscape spans -22 to 92 m), a rally stretch 560-1030 m over the plateau with two bends, the bog 1035-1085,
    the ford 1090-1140 through the stream (water at 25.1 m, the bed 60 cm under it), the narrow track 1145-1500
    under the hillside, the detour. DA_Terrain_Hide was reset to it (`setup_m6_hide.bat reset`; without the word
    the asset is kept).
  - *Test*: the terrain test's grade check is per section (a 20 % rally grade passes, the road's 13 % holds
    elsewhere) and it checks each feature by trace and by the generator: the bog's axis and 8 m off it mud, the
    road 88 cm below its shoulder; the ford's bed mud and 60 cm under a water sheet that exists; the rally
    stretch's sharpest bend at 695 m banks 7 degrees, 99 cm across 8 m (98 expected); the detour's middle dirt with
    scrub 8 m off and no cross-slope; the track's axis dirt with scrub 6 m off; 140 rocks and 3 posts. PASS, with
    the pictures retaken. The builder re-grounded 162 actors on the second rebuild.
- **Not done.** One leg only; legs 1, 2, 4 and 5 keep their flat floors until each gets a spec. No textures, rocks
  from Fab, or vegetation: greybox colours per layer and sphere boulders. The route is edited as a list of points,
  not a spline. Water is a sheet: it does not slow, float or flood the car, and it is not in the weather. Nobody
  has driven the sections or pressed the builder's buttons; the script exercised the rebuild twice per run. No landscape LOD or streaming tuning. The
  camp is still L_Base. The ruts and the weather front's mud painting work through the copied master but have not
  been driven on the landscape. The bear's dell is a bowl the car can drive into.
- **Traps.** UE 5.8 landscapes always have edit layers: `Import` writes the height and weight data into the default
  edit layer and asks for a GPU merge to produce the final weightmaps, which never runs under -NullRHI, so the
  components end up with no final weight allocations (the heights survive: Import writes those directly) and the
  shader blends nothing (black, roughness 0: a mirror). Writing the final weightmaps on the CPU with
  `FLandscapeEditDataInterface(Info, FGuid(), false)` fixes the allocations, but the textures it allocates still need
  `PostEditChange` or they load with no platform data. A commandlet never ticks, so the component material instances
  must be built with `UpdateAllComponentMaterialInstances`. `FWeightmapLayerAllocationInfo::GetLayerName` is not
  exported; read the layer info's name. `LandscapeEdit.h` pulls in the Foliage module. Under -NullRHI no texture has
  platform data (heightmaps included), so a "PF_Unknown, 0 mips" probe in a NullRHI run means nothing. Judging a
  picture by eye is not enough: the "uniform beige" landscape was a grey road seen from its own edge, settled by
  sampling pixels (PowerShell System.Drawing GetPixel) and by a run with red and green diagnostic colours; sample
  before believing the eye. The dirt road on dirt ground was invisible until the ground got its own scrub layer.
  A static mesh actor spawned by the setup keeps its collision unless the component's collision is disabled, its
  profile set to NoCollision and the actor's collision turned off, all three; with any of them on, the ford's
  water sheet stopped the ground trace (and would carry the car). A paving fade tied to the shoulder's fixed width
  makes a 3.3 m track read as a 6 m road: tie it to the road's own width. Checkpoint probes in the test compare
  against the section's grade, not the road's, or a rally stretch fails it.
 `SetLeg` resets the checkpoints' `bCleared` (it did not before, which only mattered once a test ran two
  legs on one map). A photo subject registers with the run state in BeginPlay and `SetLeg` gathers them too, so
  either order works. The interaction trace is now 30 m long: a hit beyond 3 m is rejected unless the actor asks
  for more, so the doors, nodes and stations behave as before, but a new interactable that should work at range has
  to override `GetInteractionRange`.

## 20. Driving feel stage 1: grip that can be lost (2026-09-14)

The user drove The Hide's sections and called the driving generic: the rally stretch easy with no sense of risk,
the bog and the 4WD roughness absent. `docs/DRIVING_FEEL_PLAN.md` holds the diagnosis and five stages, each gated
by a feel test. This is stage 1, built and headless-verified the same evening (`Art/grip_test.bat`, the bend runs
in `Art/terrain_test.bat`), not yet felt.

- **What was wrong** (read from the Chaos 5.8 source, not guessed). Grip per wheel is load x the surface's Friction
  x the wheel's FrictionForceMultiplier, which the project never set, so the Chaos default 2.0 applied: dirt at 0.62
  was 1.24 g and nothing could make the car slide. No LateralSlipGraph was set, so lateral force was slip angle x
  CorneringStiffness clipped by the friction circle: on rails, then sliding with the same force. A third fault came
  out of the grip test: Chaos 5.8 holds the car up with a per-wheel suspension *constraint* (PBD, a quarter of the
  spring rate as its stiffness, `CreateVehicle` about line 1266) and never applies the force model's spring
  (`ApplySuspensionForces` only adds that force under DisableConstraintSuspension, whose console variable is
  commented out). The virtual spring, rate x displacement, is what Chaos presses the tyre in with (through
  WheelLoadRatio) and reports as SpringForce; the constraint settles where it reads 65-72 % of the weight at rest and
  49 % mid-corner (the body lifts as it rolls), so the tyres have had 70-85 % of their real load since M1.
- **Tyre** (`GTVehicleWheel.cpp`). FrictionForceMultiplier 1.0; the surface table in `Art/Unreal/setup_m1_track.py`
  is now real coefficients (tarmac 0.95, dirt 0.62, mud 0.38, snow 0.28; dirt's sinkage grip loss 0.2 -> 0.1 so
  gravel at speed keeps 0.56); a LateralSlipGraph in fractions of the grip available (0 at 0 deg, 0.42 at 2, 0.76
  at 4, 0.95 at 6, 1.0 at 8, 0.97 at 10, 0.9 at 14, 0.82 at 20, 0.74 at 30, 0.68 at 40; Chaos samples 20 points
  over the curve's range, so it stops at 40 and the last value holds beyond); SideSlipModifier 0.9 (both forces
  trimmed while the friction circle clips: throttle or brake in a bend); WheelLoadRatio 1.0; no ABS, no traction
  control.
- **Load** (`UGTTractionComponent`, `UGTVehicleTuningComponent`). Each tick the four spring forces (smoothed at
  LoadFilterRate 16/s) are summed over the wheels in contact and `LoadCorrection` = weight / sum (clamped 0.5..3;
  1.54 at rest, 2.04 mid-corner) turns them into true loads with the transfer kept: mid-corner on tarmac at 0.84 g
  the outside wheels carry 166 % of a quarter and the inside 36 %, the 66/34 a 60 cm mass centre over a 157 cm track
  predicts. The correction rides in the friction multiplier Chaos gets (`SetWheelFrictionMultiplier`), so its
  friction circle is true load x friction x the tyre's state; the slip graph multiplier
  (`SetWheelSlipGraphMultiplier`) is true load x surface friction x the tyre's state / 10000, so the graph's 1.0 is
  the friction circle. `FGTWheelTuning` carries `SlipGraphScale` and `LoadCorrection`; `FGTWheelTraction` carries
  `SpringForce`, `Load` and `SurfaceFriction`.
- **Steering** (`GTCarPawn.cpp`). `SteeringSetup.SteeringCurve`, in mph: full lock (35 deg) at rest, 25 at
  20 km/h, 17.5 at 40, 12 at 60, 9 at 80, 7 at 100, 6 at 120, 5 at 160, so a keyboard tap at speed asks the front
  tyres for a slide rather than a spin.
- **Tests.** `Art/grip_test.bat` (`-GTGripTest`, L_DriveTest): two 200 m pads with PM_Tarmac and PM_Dirt, the car
  run up to 60 km/h then full lock left for 5 s, the mean of yaw rate x speed over the last 4 s: tarmac 0.84 g (peak
  1.04, front slip 15 deg), dirt 0.47 g (peak 0.71, slip 19 deg); pass bands 0.75..1.15 and 0.42..0.75 with dirt
  under 0.85 x tarmac and both fronts past 8 deg of slip: PASS. The log also prints the springs at rest against the
  weight and the four wheels mid-corner. `Art/terrain_test.bat` gained two runs after its drive: the rally stretch's
  sharpest bend (710 m, radius 45 m, camber 7 deg, half width 7.8 m) entered 100 m before it at 90 km/h flat out,
  following the route (steer = the angle to the point a second ahead / 20 deg) leaves the road (32.8 m off the
  route, 25 m past the edge); the same at 43 km/h held stays 3.3 m inside the edge (peak 0.82 g): PASS. Before the
  load correction the held run was 0.3 m over the edge on 0.24 g of grip. The runs steer through
  `AGTCarPawn::SetRawSteer` (player input disabled); `FGTM6TestRunner::Drive` is throttle without the handbrake.
- **Regressions.** All 19 other headless tests PASS after two test adjustments that the honest tyres forced: the body
  test's run-up is the snow lane, and at snow's real 0.28 (0.20 sunk) the car reached the wall at 7 m/s instead of 13
  and dented nothing, so it now starts at 50 km/h (`SetPhysicsLinearVelocity` at the teleport); the winch test's weak
  anchor sat 15 m to the side, and a car pulled sideways from its bumper now pivots and rolls toward the anchor at
  2.5 m/s so the tension spikes and drops instead of holding 3 kN for the 0.3 s tear-out delay, so the anchor is ahead
  with the handbrake on (it tears at 9.2 kN). Neither was a physics fault: both tests assumed a car that cannot move.
  Numbers that moved: the drive test's top speed 71 km/h in 8 s (unchanged launch: engine-limited), the mud start
  28 km/h after 8 s, the surface test's mud slowing 22.5 -> 19.6 m/s.
- **Not done.** Not felt: the user drives the valley road and the rally stretch next. Stages 2-5 of the plan
  (ground with texture, mud and water that take the car, a drivetrain you operate, feedback) follow the feel test.
- **Traps.** The Chaos slip graph is absolute force (Y x 10000), so it has to be scaled per wheel every tick or it
  is a fixed cap that ignores load and surface. FWheelStatus::SpringForce is the force model's virtual spring, not the
  support: under the constraint suspension it reads 65-72 % of the weight at rest and about half mid-corner, and
  Chaos's own tyre load is built from it, so any grip number taken from it is short unless normalised to the weight.
  `p.Vehicle.DisableSuspensionConstraint` does not exist in 5.8 (commented out) and `GWheeledVehicleDebugParams` is
  not exported, so the force suspension cannot be chosen from project code. Steering curve keys are mph. Untagged
  ground counts as friction 1.0 in the slip graph scale (Chaos keeps its last surface friction there). The surface
  coefficients reach the landscape through the same PM assets: a table change needs `setup_m1_track.bat`, no
  landscape rebuild.

## 21. Chase camera for testing (2026-09-14)

Asked for while the driving feel work is judged from outside the car ("for testing for now"; the backlog still holds
the accessibility chase camera as a Tier 2 item with mirrors).

- **Camera.** `AGTCarPawn` carries a `USpringArmComponent` (ChaseArm) on the mesh root, its pivot 120 cm over the
  car's origin, pitched -10 deg, 700 cm long, with a `UCameraComponent` (ChaseCamera, FOV 80) on its socket. The arm
  follows the car's yaw only (pitch and roll not inherited: a level horizon), lags the position at 10/s up to 250 cm
  and the rotation at 6/s, and probes with a 20 cm sphere on the Camera channel so it pulls in against the ground
  and walls. The numbers are EditAnywhere under GT|Camera|Chase. The chase camera starts inactive; `SetChaseCamera`
  activates one camera component and deactivates the other, which is the whole switch (a pawn's view is its first
  active camera component). The driver camera keeps being placed every tick either way, so switching back is instant.
- **Input.** `IA_CameraToggle` (C, gamepad right stick click) is written by `Art/setup_m1_input.bat` into IMC_Driving
  (21 mappings now) through `BuildDrivingMappings`; the runtime fallback builds it too, and an IMC_Driving asset
  from before this change gets the two keys mapped at runtime so the key works without re-running the setup.
- **Test.** The flat drive test toggles the chase camera at 4 s, reads the player camera's location half a second
  later (805 cm behind the car, 242 cm above), toggles back and finds the view 2 cm from the driver camera: PASS; the
  mapping count check moved from 15 to 17. The on-foot test (exit, re-enter with the rewritten context) PASS.
- **Not done.** No look input on the chase arm (the mouse still turns the driver's head only), no free orbit, no
  remembering the choice across a level load. The dashboard and the leg HUD draw as before.

## 22. Driving feel stage 4: a drivetrain you operate (2026-09-14)

"Go, drivetrain first" after the stage 1 feel test ("much better for the rally stage, not perfect, on the right
path"). The drivetrain is ours now; Chaos's engine and gearbox are off on the car. Built and headless-verified
(`Art/drivetrain_test.bat`), not yet felt.

- **`UGTDrivetrainComponent`** (Vehicle/), driven by `AGTCarPawn::Tick` after the tuning. Engine: torque = drive
  pedal x MaxEngineTorque x TorqueScale (both from the tuning, so parts, damage, fuel, heat and bogging still act) x
  the normalised TorqueCurve at the engine speed; idle 800, the limiter at MaxRPM, engine braking EngineBrakeEffect x
  MaxTorque x speed fraction off the pedal. The engine turns with the wheels (no clutch or converter model, as
  Chaos's engine also had none): its speed is the wheels' mean speed through the ratios, idle at the least, so the
  launch push is the 208 Nm at 800 rpm it was in M1 (0.28 g). Gearbox: automatic on the engine speed from
  `TransmissionSetup` (ratios, change-up 4200 / change-down 1800, 0.4 s change with a torque cut, 0.6 s between
  changes). Transfer case: `LowRangeRatio` 2.5. Differentials: centre (`CentreSplitFront` 0.5) then front and
  rear. Open: a side gets at most what the other side can react, its cap = true load x surface friction x the tyre's
  state x radius (UGTTractionComponent's numbers) + `OpenSpinAllowanceNm` 40, so a wheel in the air or on ice
  starves its partner. Locked: the cap is lifted and a coupling of `LockCouplingNmPerRadS` 120 (at most 400 Nm)
  hands torque from the faster side to the slower until their speeds match. One diff lock locks all three
  (`CentreLockWhenOn`, `AxleLockWhenOn`; parts can later restrict a car to a centre lock). Brakes per wheel: the
  brake pedal x MaxBrakeTorque, the handbrake x MaxHandBrakeTorque on the wheels that take it.
- **Chaos.** The wheel classes carry `ExternalTorqueCombineMethod Override` (the component also sets it), so
  `SetDriveTorque` / `SetBrakeTorque` are the whole story per wheel; `bMechanicalSimEnabled` and `bReverseAsBrake`
  are off on the movement component. Reverse is ours, from the smoothed pedals: the brake pedal held alone under
  30 cm/s puts the car in reverse (then it drives backward and the throttle brakes), the throttle held alone under
  30 cm/s takes it out, the same feel ReverseAsBrake gave. The tacho, the audio, the condition's misfire and heat and
  the environment read the drivetrain's engine speed and drive pedal (new parameters on UpdateFromVehicle and
  Update). Two Chaos hacks are off because they falsify hills: the suspension constraint swaps the ground normal for
  straight-up at low speed on slopes flatter than `p.Chaos.Suspension.SlopeThreshold` (cos 45 deg; set to 1.0 in
  BeginPlay), which parked a car for free and pushed it uphill (a 35 % slope was climbed from a standing start on
  5.8 kN against 6.8 kN of grade); and `SleepSlopeLimit` (cos 30 deg -> 0.9995), since a sleeping body is not
  integrated and Chaos slept a stopped car on any slope under 30 degrees. A parked car now rolls unless held; the
  exit path already sets the handbrake. The drivetrain wakes the body when it applies torque (releasing a pedal
  does not wake anything).
- **Controls.** X / D-pad right toggles the diff lock, V / D-pad down low range (`IA_DiffLock`, `IA_LowRange` in
  IMC_Driving, 25 mappings; the runtime patch maps them on an older context). LOCK and LOW lamps on the dash
  (ELight gained Lock and Low: warm white and green).
- **Test.** `Art/drivetrain_test.bat` (`-GTDrivetrainTest`, L_DriveTest): an ice strip (a runtime physical material,
  friction 0.01) under the left wheels, full throttle 4 s: open 194 cm, locked 1359 cm (open under 400, locked over
  1000 and over twice open); a coast released on a 35 % ramp with nothing holding it: -660 cm/s after 2 s (gravity
  alone -650); a standing start on the slope held by the handbrake: high range 0.0 m (rolls back), low range 10.6 m
  in 8 s (high under 3, low over 8 and 5 more than high); the brake pedal held from rest: -968 cm/s after 3 s in
  reverse; the gearbox reached 2nd or 3rd. PASS. The flat drive test PASS (70 km/h in 8 s, unchanged launch).
- **Regressions.** All 21 other headless tests PASS first time on the new drivetrain and the honest hills (the flat
  drive 70 km/h in 8 s, the mud start 27 km/h, the grip pads 0.87 / 0.46 g, the leg 9.6 s, the terrain drive and
  bend runs unchanged).
- **Not done.** No clutch or engine inertia, so the engine speed never sags under load (the SnowRunner bog-down
  sound needs it: a small model on top of this one, later). No manual gearbox (a toggle away). The lock is all
  three diffs at once. Nothing in the parts system yet (lockers, low range as upgrades). The lock on the rally stage
  makes the car scrub and understeer, which is right; tell the user. Not felt.
- **Traps.** `UChaosVehicleWheel::GetRotationAngularVelocity` is negated: a forward-rolling wheel reads negative
  (the lock's coupling ran backwards until this was undone). A diff test on ice with a run-up proves nothing: with
  the torque curve rising with speed the car climbs 35 % in high range once rolling, as the real one would; the
  standing start is the discriminating case. Chaos's slope hack and slope sleep must both be off for any hill test
  to mean anything; both are engine-wide settings. `SetDriveTorque` is set-and-forget (Override): a stale value
  keeps driving if the component stops updating.

## 23. Driving feel stage 3: mud and water that take the car (2026-09-14)

"Solid. Lets move on" after the drivetrain, so the mud. Built and headless-verified (the terrain test's four new
runs, the mud start test, a picture), not yet felt.

- **The bog you can read.** A sixth landscape layer, Bog (`GTTerrain::LayerCount` 6, `LI_Bog`, `PM_Bog`,
  `Surface.Bog`): deep mud down a bog section's middle in a band `BogCoreFraction` 0.45 of the half width plus up
  to `BogPocketFraction` 0.3 more where a Perlin noise of `BogPocketWavelengthM` 25 peaks, so it widens and narrows
  along the bog; the rest of the trough is Mud, the shallow line. Spec fields on `FGTTerrainSpec`; the layer's
  colour in `Art/Unreal/setup_m6_hide.py` (darker, wetter); the bog reads as mud to the spray, the body dirt and the
  tyre audio. Surface numbers (`setup_m1_track.py`): Mud 0.42 grip, sinks to 22 cm at 0.08 m/s, drag 0.06 x (1 +
  1.0 x sink), plough 0.25, grip loss 0.3; Bog 0.30, sinks to 45 cm at 0.14 m/s, drag 0.09 x (1 + 2 x sink), plough
  0.45, grip loss 0.5.
- **The tyre sinks, and the car with it.** `UGTTractionComponent` hands the sinkage to the tuning (`SinkageCm`) and
  `UGTVehicleTuningComponent` shrinks the Chaos wheel radius by it (`SetWheelRadius`, at most
  `MaxVisibleSinkFraction` 0.6 of the radius: sunk to the rims). Chaos sweeps with the effective radius, so the
  contact drops, the suspension droops and then the body follows into the mud, while the drawn wheel keeps its size
  and buries itself: in the bog the radius goes 38 -> 15 cm and the body sits 14 cm below the mud's surface, 19 cm
  lower than on firm ground (measured by the terrain test). The drivetrain reads the shrunk radius too.
- **The axles on the mud.** Chaos has no unsprung parts, so a belly collision box cannot do it (the body only drops
  once the suspension has fully drooped). Past `AxleClearanceM` 0.19 the traction adds `BellyDragPerMetre` 1.5 of
  the load per metre sunk beyond it and takes `BellyGripLoss` 0.4 off the tyre at a further 19 cm: in the deep band
  drag 0.67 against grip 0.30 of the load, the car stops; on the mud edge drag 0.20 against 0.66 x 0.42, a
  low-range crawl gets through. Wheelspin digs three times the surface rate now, recovery on firm ground is
  0.08 m/s, and the drag cap is 0.9.
- **Your own ruts.** The track paint's CPU grid (`UGTTrackPaintSubsystem::SampleDepth`) is read `RutLookAheadCm` 60
  ahead of each wheel (so a wheel does not read the stamp it is laying): a full rut eases the ploughing by `RutEase`
  0.6 (sinkage growth and plough drag) and the wheel drops into it (sinkage at least 0.8 x the rut x the surface's
  depth). Re-driving your track is easier than fresh mud.
- **Water.** `AGTWaterSheet` (Terrain/, an AStaticMeshActor with the engine cube, no collision, movable) replaces
  the plain slab over each ford (`setup_m6_hide.py` spawns it with `BaseLevelCm`); its level is the placed height
  plus `RiseWithWetnessCm` 80 x the weather's ground wetness plus `ExtraRiseCm` (events, tests), and it moves
  itself. `DepthCmAt` gives the water over any ground point inside a sheet. Per wheel: `WaterDragPerMetre` 2.4 of
  the load per metre of depth at 10 m/s (with speed squared), `WaterBuoyancyGripLoss` 0.4 at `WaterBuoyancyDepthM`
  0.8. `UGTConditionComponent::UpdateFlooding`: water over the front wheels past `IntakeHeightM` 0.85 floods the
  engine (`bFlooded`: no torque, the engine lamp, the engine audio off) until `FloodDrainSeconds` 5 out of it; a
  snorkel part would raise the intake.
- **Tests.** `Art/terrain_test.bat` gained four runs after the bend: the bog down its middle at 30 km/h with open
  diffs in high range stops 25 m in (1060 of 1035-1085), sinkage 1.00, the body 19 cm lower; the edge (8.5 m off
  the axis) crawled from a stop in low range with the lock at under 15 km/h gets through (1090 m, on mud all the
  way, sunk 22 cm); the ford at 20 km/h in low range gets through in 0.60 m of water with the engine running; the
  ford with the water raised 70 cm floods the engine in 1.30 m and the car stops at 1116 m. The section check reads
  Surface.Bog on the bog's axis and Surface.Mud 8 m off. The mud start test on L_TestTrack PASS (19 km/h after 8 s
  on the new mud). `Art/hide_shots.bat` takes two more pictures: hide_6_bog, the car driven into the bog in low range
  and left spinning until it has sunk, from behind and to the right, and hide_7_bog_top, the bog from 70 m straight
  above. Looked at and pixel-sampled: from above the deep band is plain, a darker brown (RGB sum ~400) down the
  middle against the mud edge (~475) and the dirt road (~534), widening and narrowing along the bog, the car in it;
  from behind the car at 2.6 m the ground is one colour (red 176-187 everywhere), the wet low-roughness layers
  reflecting the sky at that angle. In hide_6_bog the body sits low with only the lower part of the wheels showing.
- **Regressions.** The 19 other tests PASS; two needed the old mud's assumptions removed: the surface test's dash
  check no longer wants the engine lamp lit by the wall (the car now reaches it at 3 m/s after the mud and the snow
  lane), and the track-paint test runs 18 s instead of 16 so the snow sample is reached (20 s overshot its window).
- **Not done.** No terrain deformation (the ruts stay paint). Depth within the bog is two levels (mud, bog), not a
  field. The water does not push the car or float it; only drag, buoyancy on the tyres and the intake. The weather's
  rise is wired but not driven by a front yet. Not felt.
- **Traps.** A test's follower must hold a crawl at crawl speed: left at full throttle in low range the car reached
  40 km/h, wandered off the road edge and cut back into the deep band. A car below the mud's surface has a negative
  clearance: do not clamp it away. A .bat launched from Bash as `cmd //c "C:\GrandTour\Art\${T}_test.bat"` never
  runs: the backslash before the `$` escapes it and cmd gets a literal `${T}` (the log stays stale and looks like a
  rerun); build the path with `cygpath -w` and check the log's time. From the driver's seat the deep band is hard to
  tell from the mud edge (the wet look at grazing angles): a darker or rougher look or a texture in the art pass.
- **Felt, and retuned (later the same evening).** "Looking pretty good", with two things named. The car got
  completely stuck and could not move: the deep band's drag (0.66 of the load) was above anything the tyres could
  push (0.30), so no lever helped, which is wrong for the reference (deep mud is slow and dangerous, not a wall). Now
  Bog is 0.36 grip, sinks to 40 cm, drag 0.05 x (1 + 1.0 x sink), grip loss 0.35, `BellyDragPerMetre` 0.3 and
  `BellyGripLoss` 0.25, and your own rut cuts the axle drag too: at full sinkage grip 0.18 against drag 0.16, so a
  locked low-range crawl creeps at walking pace with the wheels churning, and a stop is the danger. The terrain test's
  middle run now asserts the momentum loss (30 km/h in, under 3 km/h inside: 13 cm/s measured, the car 16 cm lower)
  and lets it creep on. The second thing named, shape in the ground, is section 24.

## 24. Driving feel stage 2, first part: relief (2026-09-14)

"I would like the mud and all the ground for that matter to have some shape, rather than flat." The shape a wheel
feels first: bumps per surface on a landscape fine enough to carry them. The rest of stage 2 (stones, water bars,
rut pairs, crests, a narrower rally road with verges and posts) follows.

- **A 1 m landscape.** `FGTTerrainSpec` defaults are now 16 components a side at 100 cm quads (the same 2 km; 2017 x
  2017 verts, 256 components). `Art/Unreal/setup_m6_hide.py` upgrades an asset written at 2 m in place (quad 100,
  components 16, every other field kept; it logs "spec upgraded to 1 m quads"). The import, the two rebuilds and
  the save take about twenty seconds.
- **Relief per surface.** Spec fields under GT|Terrain|Relief: `RoughnessWavelengthM` 4 (a second octave at 2 m) and
  bump heights `RoadRoughnessM` 0.02, `RallyRoughnessM` 0.06, `TrackRoughnessM` 0.15, `MudRoughnessM` 0.12
  (hummocks), `FordRoughnessM` 0.08, `ScrubRoughnessM` 0.25 (the ground away from any road). `GTTerrain::HeightM`
  adds the bumps after the road carve, the amplitude blended from the scrub's to the section's across the paving's
  fade; an alternative line carries a track's bumps. The route profile is still built from the land alone, so the
  bumps never fight the grade limits. `SlopeDegrees` measures over 4 m now (the landform), or the bumps would have
  put rocks everywhere.
- **Test.** The terrain test's track check reads 21 heights a metre apart along the track's axis and the tarmac
  road's, fits a line and takes the spread about it: track 4.9 cm, road 0.3 (thresholds 4 and 3). Every other check
  holds on the new ground (the bend runs, the bog, the ford, the camber 97 cm against 98 expected, the detour's
  cross-slope 3 cm). PASS. Pictures retaken: the relief is physically there but reads faintly in the flat-coloured
  pictures under a high sun; hide_6_bog shows the car's own ruts as two dark lines into the bog. Not judged "shaped"
  by eye: the user drives it. The full suite after the relief and the mud retune: 21 of 21 PASS.
- **Not done.** Stones in the track with collision, water bars across tracks, rut pairs as heightfield features,
  rally crests and compressions as spec features, `RallyWidthScale` 1.3 -> about 0.75 with a verge profile (ditch and
  bank) and posts or greybox trees along the edge; textures and normal maps, which is where the shape becomes
  visible. Not felt.
- **Traps.** A local named like a runner member (`bRelief`) is C4458, an error here. Relief belongs in `HeightM`
  only; put it in `BaseHeightM` and the grade limiter fights it. Rock placement by slope must use a coarse step.


## 25. Driving feel stage 2, the rest: stones, water bars, ruts, crests, verges and posts; the chassis never sleeps (2026-09-14)

The remainder of stage 2 after the relief (section 24), built and headless-verified in one evening (`Art/terrain_test.bat`
gained three runs and five checks, `Art/hide_shots.bat` two pictures), not yet felt. Also found on the way: the drivetrain
test had been failing since stage 3 unseen, because Chaos put the chassis to sleep.

- **The chassis never sleeps** (`AGTCarPawn::BeginPlay`). The suite script of stages 3 and 2a listed 21 tests and left the
  drivetrain test out, so its failure went unnoticed: the low-range standing start on the 35 % ramp climbed 0.0 m (10.6
  before) with 1061 Nm on every wheel and the wheels not turning for 8 s, and the gearbox never left first. The car had
  slid back on the handbrake, the throttle stopped it, and at rest Chaos's island sleep took the body; the drivetrain's
  wake (`WakeAllRigidBodies` when `!IsAnyRigidBodyAwake`) is a game-thread call against a physics-thread sleep and never
  landed, and a sleeping body is not integrated, so the torque did nothing. Proven by running the test with
  `p.Chaos.Solver.Sleep.Enabled 0`: PASS. The fix is per body: the mesh's root body gets `SleepFamily Custom` with a
  `CustomSleepThresholdMultiplier` of 0, pushed to the particle with `SetSleepThresholdMultiplier_AssumesLocked`, which
  Chaos reads as never sleep ("all zeroes means never sleep", IslandManager.cpp). The vehicle's own explicit sleep on
  level ground with no input (`SleepSlopeLimit`) still applies. Drivetrain test PASS (low range 11.7 m, gears to 3rd).
  The same sleep could have held a car stopped dead in the bog with the throttle down; whether the user's "completely
  stuck" of stage 3 had this in it as well as the drag is not known.
- **Crests and compressions as spec features.** `FGTRouteSection` gained `Bumps` (`FGTProfileBump`: ArcM along the
  route, HeightM up or down, LengthM foot to foot); the profile copies them (`FGTRouteProfile::Bumps`) and
  `HeightAt` adds each as a raised cosine after the lerp of the 5 m samples, so a crest is smooth at any step and never
  fights the grade limiter. The Hide's rally section (560-1030) has a crest of 0.9 m over 24 m at 810 (the straight
  after the first bend), a compression of 0.5 m over 18 m at 862 (into the second bend) and a crest of 0.8 m over 22 m
  at 960. The arithmetic: a raised cosine of height H over half-length a has curvature H/2 (pi/a)^2 at its top; the car
  leaves the ground when v^2 times that exceeds g, so 0.9 m over 24 m flies at 25 m/s (30 m/s^2 of drop against 9.8)
  and not at 12 m/s (7.1). Measured: taken at 87 km/h flat out, all four wheels off the ground for 0.44 s.
- **Water bars.** Across a Track section, a ridge every `WaterBarSpacingM` 100 (each moved up to 30 % by a hash of its
  number), `WaterBarHeightM` 0.25, `WaterBarLengthM` 3 foot to foot, skewed `WaterBarSkewDegrees` 25 from square so it
  drains to one side; added on the paving (times PaveWeight) in `SampleRoad`. `GTTerrain::WaterBarArcs` lists a
  section's bars for the test and the dressing. The Hide's track has four; traced, all four stand 12 cm or more over
  the axis 3 m either side (the tallest 30 cm).
- **Rut pairs.** Two grooves `RutOffsetM` 0.8 either side of a centre that wanders `RutWanderM` 0.4 over
  `RutWanderWavelengthM` 25 (`GTTerrain::RutWanderAt`, Perlin), each a raised cosine `RutHalfWidthM` 0.75 wide,
  `TrackRutDepthM` 0.10 on a track and `MudRutDepthM` 0.18 in a bog, on the paving. Traced at 1322 m: 4 and 6 cm below
  the crown and the ground outside (a 1 m grid rotated to the road keeps about half the depth; the wheels ride the
  vertex mesh, so that is what they feel).
- **Stones and posts: `AGTTerrainDressing`** (Terrain/), a runtime actor with two hierarchical instanced mesh
  components, `Stones` (the engine cube, `TrackStoneSpacingM` 4 along every Track section, `TrackStoneMinM` 0.15 to
  `TrackStoneMaxM` 0.4 long, turned and tilted up to 15 deg, 30 % sunk) and `Posts` (the engine cylinder,
  `RallyPostWidthM` 0.2 by `RallyPostHeightM` 1.3, one a side every `RallyPostSpacingM` 30 along a Rally section clear
  of its ends by 20 m, `VergeWidthM` + 0.5 m beyond the paved edge), both BlockAll so the wheels sweep against them
  and the body dents on them; materials MI_Env_Greybox and MI_Env_Marker by path at rebuild time. The lists come from
  `GTTerrain::TrackStones` and `GTTerrain::RallyPosts`, deterministic from the spec by an integer hash.
  `AGTTerrainBuilder::RebuildDressing` (a button, and called by Rebuild Landscape and Reground Actors) finds or spawns
  the one dressing actor in the map and rebuilds it, so the script and the buttons share the path; `Dressing` on the
  builder. The Hide: 88 stones, 30 posts.
- **The rally road narrowed, with verges.** `RallyWidthScale` 1.3 -> 0.75 (a 9 m road). Beyond the paved edge for
  `VergeWidthM` 3 the road sample carries a half sine, `VergeDitchM` 0.4 down where the road is on fill or level ground
  and `VergeBankM` 0.5 up where it is in cut; cut is read once per side from the land 2 m beyond the verge against the
  road's height (read at the point itself it flipped along a shallow cut and the bank came out 11 cm). Traced at 640 m,
  1.5 m past the edge: the bank side +29 cm, the ditch side -34 cm. The car dropped with its outer wheels in the ditch
  and its inner on the edge rolls 11.5 deg toward the ditch with the outer wheels 31 cm lower.
- **Spec upgrade in place** (`setup_m6_hide.py`). A rally section of DA_Terrain_Hide with no bumps gets the C++
  default's for the section at the same start; logged "spec upgraded: 3 crests/compressions". RallyWidthScale needed
  nothing: a field the user never changed is not stored in the asset (delta against the class default), so it follows
  the C++ default. The new Track and Rally fields arrive the same way.
- **Tests.** The terrain test's section check gained the bars, the ruts, the rally width (half width 4.5 m, dirt 3.5 m
  off, scrub 7 m off), the verge and the dressing (88 stones, 30 posts, a trace straight down onto the first stone lands
  on the dressing). Three runs between the bend runs and the bog: the first crest at 90 km/h flat out (all four wheels
  off the ground for at least 0.3 s: 0.44), the track from 1180 to 1330 m held at 40 km/h (vertical acceleration over
  50 ms windows, RMS at least 0.15 g: 0.45 g, peak 1.59 g), the verge drop (roll at least 5 deg, the outer wheels at
  least 20 cm lower). The bend runs on the narrower road: flat out still leaves it by 25 m; held at 43 km/h stays 1.0 m
  inside the edge (3.3 m before). `Ground()` ignores the dressing so a probe reads the ground, not a stone. Pictures
  hide_10_rally (from the verge 60 m before the first bend: the posts stand along the road; the ditch does not read at
  that angle) and hide_11_track (the track from 2 m up: the stones as dark blocks down it; the ruts and the bar do not
  read at that angle). Looked at; the ground shape is not judged by eye.
- **Regressions.** All 22 headless tests PASS (the suite script now lists every one, the drivetrain test included) after
  one test fix that the never-sleeping chassis forced: the hazard test spawned its radiation zone 6 m above the car's
  origin with a 6 m half height, so the origin sat exactly on the box's bottom face and counted as inside only while
  Chaos held the body asleep; awake, the car settled a centimetre and was out (engine 0.997, no lamp). The zone now
  spawns 3 m up. The same arithmetic holds in the levels: `setup_m6_hide.py` places the pocket at ground + 6 m with a
  6 m half height and the car's origin rides about 30 cm above the ground, so a dip of more than that inside a 25 m
  pocket puts the car outside it; `AGTHazardVolume::ContainsPoint` tests the origin. Not changed; noted for the level
  work. Numbers that moved with the narrower rally road: the held bend at 43 km/h is 1.0 m inside the edge (3.3 before),
  the bend's camber check 94 cm of 98 (the probes at 4 m now sit near the edge).
- **Not done.** Not felt. No stones or bars on the alternative lines. The verge is one profile for the whole stretch (no
  culverts, no gaps at junctions). The posts are cylinders, not trees. Textures, which is where the shape becomes
  visible. Stage 5 (feedback) waits for what the user names.
- **Traps.** A test not in the suite script is a test not run: the script now lists all 22. Chaos island sleep is on the
  physics thread; a game-thread wake each tick does not beat it, and a sleeping body ignores every force. The
  generator's "+ side" (SignedM positive, the comments' "left") is +Y of the heading, the car'


## 26. The second bog: a dead stop you can drive out of (2026-09-15)

The stage 2 feel test's first report: "that mud patch on leg 3 brings the car to a stop, and you cannot drive out."
The stage 3 retune (section 23) had put deep mud at grip 0.18 against drag 0.16 of the load and called that a walking-pace
creep; the terrain test measured 13 cm/s and its middle run counted a dead stop as a pass, so nothing ever proved the
car could leave the deep band. Built and headless-verified, not yet felt.

- **Why it stopped dead.** Three things stacked. The plough drag was `plough x sinkage x (speed / 10 m/s)^2`, so the crawl
  speed a surface allows, where the tyres' push equals the drag, was sqrt((grip - drag at rest) / plough) x 10 m/s: with
  0.0155 of the load to spare and plough 0.45 that is 0.19 m/s, a tenth of walking pace on the flat. Stage 2's relief then
  put 12 cm hummocks and an 18 cm rut pair into the bog, and 0.0155 of the load climbs 0.9 degrees, so the car stopped on
  the first rise and had nothing to pull away with. And the rut of your own that eases the ploughing was read 60 cm ahead
  along the velocity, which at rest is no direction at all, so a stopped car read no rut and reversing into its own
  channel gained nothing.
- **The plough law** (`UGTTractionComponent::Update`). Linear with speed under 10 m/s, squared above: `SpeedRatio x
  max(1, SpeedRatio)`. The momentum-eating at 30 km/h is unchanged (the squared regime), and the crawl speed is now
  (grip - drag at rest) / plough x 10 m/s, so the mud's numbers say what a crawl does without a second formula.
- **The numbers.** Bog (`setup_m1_track.py`): rolling 0.040, drag scale 0.8, grip loss 0.25 (plough 0.45 and the rest
  unchanged); `BellyGripLoss` 0.25 -> 0.15. At full sinkage: grip 0.36 x 0.75 x 0.85 = 0.23 of the load, drag at rest
  0.072 + 0.063 (the axles) = 0.135, so a dead stop pulls away with 0.095 of the load (about 5 degrees of climb) and the
  crawl runs out at 2.1 m/s. Mud, the shallow line, keeps its row; its drag at a crawl dropped with the law (net push 0.2).
- **The rut at rest.** Under `RutReadSpeed` 20 cm/s the rut is read 60 cm along the car's heading, backward when the
  drivetrain is in reverse, so backing out of a dead stop reads the channel the car cut coming in (drag and growth eased
  by `RutEase` 0.6 of the rut's depth) while forward reads fresh mud: the rocking a stuck truck does.
- **Test.** `Art/terrain_test.bat` gained a step after the middle run (steps renumbered, 13 now). The middle run ends
  once the car has been under 3 m/s in the band for 2 s and asserts the momentum loss (slowest under 300 cm/s from 830 in):
  slowed to a crawl at 1066 m, slowest 159 cm/s, sunk 1.00, the body 17 cm lower. The escape then holds the car on the
  handbrake for 3 s in the deep band with the lock and low range, drives forward at full throttle following the axis
  (at least 8 m and 100 cm/s: 15.0 m in 9.9 s, fastest 211 cm/s), then holds the brake pedal alone, which brakes, drops
  into reverse and drives backward (at least 2 m: 6.0 m in 4.2 s, fastest 235 cm/s, the rut making reverse the faster
  way). The edge crawl is through at 295 cm/s slowest. PASS; the mud start (22 km/h after 8 s), the surface test (mud
  lane 21.9 -> 12.4 m/s) and the drivetrain test PASS on the new build, and the other 18 tests PASS unchanged: 22 of 22.
- **Tools.** `Art/suite.sh [names]` runs any set of the 22 tests in one call and prints one result line each (a FAIL
  prints the last GTDRIVETEST lines); `Art/build.sh` builds the editor target after checking the editor is closed and
  prints only errors and the result. Both exist so a build-and-test round is two tool calls instead of a dozen.
- **Not done.** Not felt. The lock and low range do not change a uniform bog's crawl (the tyres are grip-limited either
  way; the levers matter on split grip and slopes, which the drivetrain test covers), and nothing yet makes a spinning
  tyre push less than a gripping one in mud, so a keyboard full throttle costs only the dig-in. No terrain deformation
  (the ruts stay paint); the user has asked to look at it next.
- **Traps.** A test that counts a dead stop as a pass proves nothing about getting out; the escape is the assertion the
  bog needed from the start. A squared drag law has no crawl regime: any surface under it is either a wall or nothing.
  The rut read needs a direction at rest or a stopped car reads no rut at all.


## 27. Mud deformation stage A: the mud field (2026-09-15)

"Go, start with stage A" of `docs/MUD_DEFORMATION_PLAN.md`, the MudRunner split: a CPU mud surface per bog that the
wheels and the belly draw primitives into, a texture built from it for the mesh of stage B, the physics untouched
until stage C. Built and headless-verified in the terrain test; nothing to see yet (no mesh reads the texture).

- **`FGTMudField`** (Terrain/, a plain struct): a grid at 12.5 cm over a bog's footprint holding the mud's height in cm
  relative to the ground (negative in a rut, positive on a ridge), a horizontal slide-away offset and a tracks factor,
  with bilinear samples, a gradient, and a dirty rectangle for the upload. `StampWheel(From, To, Width, Depth)` lowers a
  capsule of the tyre's width to -Depth (only ever lower: the deeper of what is there and the wheel), sums the volume
  it removed and puts `RidgeReturn` 0.6 of it back as a hump beside the capsule (a sine over `RidgeWidthCm` 40, capped
  at `MaxRidgeCm` 25; mud compacts, so not all of it comes back), pushes the offset of cells within `SlideWidthCm` 60
  outward by `SlideCmPerMetre` 4 per metre the wheel travelled (capped at 20 cm), and sets the tracks factor under the
  tyre and across the ridge. `StampBelly(Centre, Forward, Length, Width, Depth)` flattens a box to -Depth with no
  ridges. Both return the volume lowered; `LoweredCm3` accumulates it. Because a stamp only lowers, a second tyre down
  the same line removes nothing: compaction for free.
- **`AGTMudPatch`** (Terrain/), one per Mud route section, spawned at BeginPlay by **`UGTMudSubsystem`** (game and PIE
  worlds only) from the terrain builder's spec: the section's route sampled every 2 m, its half width (the paving,
  `RoadHalfWidthM` x `MudWidthScale` = 9.6 m on The Hide) plus `MarginCm` 200 either side, the axis-aligned box of
  that. The Hide's bog gets one patch. The patch keeps the field and a transient `PF_FloatRGBA` texture (R height in
  metres, GB offset in metres, A tracks) that it updates each tick the field changed, the dirty rectangle only, with
  `UpdateTextureRegions` (no render-target readback anywhere). `PatchAt(XY)` and `TotalLoweredCm3()` on the subsystem.
- **The stamps** (`UGTTractionComponent::StampMud`, after the sinkage each tick, `bStampMud`). A wheel in contact on
  Surface.Mud or Surface.Bog with any sinkage stamps the patch under it: a capsule from where it last stamped to its
  contact now (a jump over 3 m is a teleport, not a stroke), the Chaos wheel's width (25 cm), its sinkage in cm; the
  volume goes into the wheel's `MudLoweredCm3`. With three or more wheels on mud and the deepest past `AxleClearanceM`,
  the belly stamps a box between the contacts inset `BellyStampInsetCm` 40 at each end and side (so it does not flatten
  the ruts) to the depth past the clearance. `FGTWheelTraction` gained `ContactPoint` and `MudLoweredCm3`. Dirt and snow
  still go to the paint window; the paint keeps stamping bogs too until stage C.
- **Test** (`Art/terrain_test.bat`, a step after the bog escape, 14 steps now). During the escape's forward pass the
  wheel contacts are sampled every half second (92 samples); then, for each, the field under the contact is at most
  -0.6 x the wheel's sinkage (mean -34.5 cm against 40 of sinkage, 91 of 92), the highest point 5 to 40 cm outward of
  the tyre's edge is a ridge of 3 cm or more (mean 7.9 cm, 79 of 92: the misses where a later pass cut it), the tracks
  factor is 0.9 or more under the tyre (92) and 0.05 or less 6 m off (92); a tyre run twice down one 4 m line at a
  clear spot lowers 309,375 cm^3 then 0 and leaves a 6.7 cm ridge (the field's own compaction); one patch, over the
  bog. A profile across the track at the middle sample, 12.5 cm steps, the car's right positive: `-38 -1 -10 -19 -21
  -21 -21 -21 -21 -20 4 -26 -38 -2 11 7 1 0 0 0 0 0 0 0 0`: the other wheel's rut at -150, the belly's smear at -21
  between the wheels, this wheel's rut at 0, its outer ridge at +25, untouched mud beyond. Logged, not gated: the
  fronts lowered 230,802 cm^3 per metre of the forward pass and the rears 146,464 (the rears do not sit in the fronts'
  ruts on a curving line: stage C's business), and the reverse pass, steered to retrace the recorded path, lowered as
  much as the forward pass (621,120 against 611,822 per metre), so the retrace is not retracing; the escape checks
  still pass (14.3 m forward, 6.0 m back). PASS; the other 21 tests PASS unchanged: 22 of 22.
- **Not done.** Nothing visible: stage B (the grid mesh per patch displacing by the texture, the landscape pushed back
  under it, a top-down picture with a diagnostic height colour) is next. The physics does not read the field (stage
  C). No drying, no weather writing into a patch, patches only where the spec has a Mud section. Not felt.
- **Traps.** The runner's `World` is a weak pointer: `World.IsValid()`, not `World ?`. A stamp that could raise as well
  as lower would undo compaction; ridges are the only raise, and they never land under the tyre. Reversing with the
  wheel turned right takes the rear to the right: the retrace steer keeps the forward sign of the cross product, and it
  still did not retrace; measure compaction on the field, not on the driver.

## 28. Mud deformation stage B: the mud mesh, its material, and a picture (2026-09-15)

Stage B of `docs/MUD_DEFORMATION_PLAN.md`: the field of stage A drawn. A fine flat mesh per patch that the field's
texture displaces in the vertex shader, a material for it, the landscape pushed back under the patch so a rut can dip
below it, a top-down diagnostic picture judged by pixel, and the terrain test checking the mesh. Built and
headless-verified; the look is the layer colours until the texture pass; not looked at by the user; the physics does
not read the field yet (stage C).

- **The mesh** (`AGTMudPatch::BuildMesh`, called by `Init` at BeginPlay). A `UProceduralMeshComponent` grid at
  `MeshCellCm` 25 over the field's footprint (The Hide's patch is 69 x 36 m, an axis-aligned box round a curving
  section: 278 x 144 = 40,032 vertices, 79,222 triangles), each vertex on the landscape's collision heightfield
  (`ALandscapeProxy::GetHeightAtLocation`, a trace where no landscape answers) plus `MeshLiftCm` 2, so it coincides
  with the ground at rest and never z-fights it. Vertex normals from the neighbours' heights (the ground's slope; the
  material adds the mud's), UV0 the patch's 0..1, no collision, no shadow, `BoundsScale` 1.5 for the displacement.
  `MeshRestZAt(XY)` reads the rest surface back (the test). It wears a dynamic instance of `M_GT_Mud` (by path at
  runtime, a warning and the default material when `Art/setup_m6_mud.bat` has not run) carrying the patch's texture
  and `PatchMin` / `PatchSize` / `PatchTexels`.
- **`M_GT_Mud`** (`Art/setup_m6_mud.bat`, `Art/Unreal/setup_m6_mud.py`, rebuilt every run). Masked, two-sided,
  world-space normal, two Custom nodes. The vertex one samples the field texture at the vertex's world XY inside the
  patch and returns (offset.x, offset.y, height) x 100 as the world position offset. The pixel one derives the
  normal from the height by central differences over a texel on top of the ground's vertex normal, blends
  `MudColor` / `MudRoughness` over `GroundColor` / `GroundRoughness` (the Mud layer's numbers) by the tracks factor,
  darkens and lowers the roughness toward `WetRoughness` by `MPC_Weather`'s Wetness and in the rut floors (water
  collects), and clips where the field is untouched (tracks under 0.02 and |height| under 5 mm), so the landscape shows
  through until a wheel has been there: an opaque rectangle over the bog would show its edges against the layer
  blend. `MudDiagnostic` 1 draws everything as an emissive ramp: R the mud height (0.5 flat, 0 at -40 cm, 1 at +40),
  G the ground's Z from `DiagZ0` over `DiagZRange`, B the tracks, scaled to 0.3 for the tonemapper.
- **The landscape under a patch** (`setup_m6_hide.py`, `M_GT_Landscape`). The Mud and Bog layers' weight, inside any
  of the patch boxes `Patch0..Patch3` that `UGTMudSubsystem` writes into `MPC_TrackPaint` at BeginPlay, becomes a
  pixel depth offset of `MudDepthOffsetCm` 100, so the mesh wins the depth test where a rut dips below the landscape
  (a 40 cm rut wins down to about 24 degrees of view). The boxes ride in the track-paint collection because a material
  may reference two collections and the landscape already has weather and track paint. `MP_PixelDepthOffset` is
  hidden from Python: `UGTVehicleSetupLibrary::ConnectMaterialPixelDepthOffset`. Run `setup_m6_mud.bat` before
  `setup_m6_hide.bat` (the landscape material needs the boxes; `setup_m1_trackpaint` keeps them on a rerun).
- **The picture** (`Art/hide_shots.bat`, step 12, `hide_12_mud_diag.png`, twelve pictures now). The car is put
  20 m into the deep band, held 3 s on the handbrake with the lock and low range, driven 10 s (0.9-2.3 m: the crawl
  varies run to run), its wheel contacts recorded, then taken to arc 60 so its roof does not hide its ruts; the
  diagnostic goes on with a 3 m green window about the crawl's ground and the camera looks straight down from 40 m,
  the route up the picture. The runner projects and logs a set of world points to screen pixels (`diag <name> px x
  y`): each wheel's rut centre, the ridge 20 and 40 cm outward of the tyre's edge, clear mud 3 m out, a 12.5 cm
  profile across the last wheel's track halfway back along the crawl, and a 1 m line across the bog 8 m ahead of the
  stop. `Art/tools/sample_mud_diag.ps1` reads the picture at those pixels (a 3 x 3 mean) beside the field and ground
  numbers. The final run (a 2.4 m crawl): the rut centres R 94-102 against clear mud R 169 (4 of 4 lower, field
  -38 to -40 cm); the ridge 20 cm out R 171-174 (3 of 4 higher, field +3 to +4 cm; the fourth point fell in a
  neighbouring rut at -3 cm and read 166; 40 cm out the field is back near 0 and so is R); the profile halfway back
  along the crawl: the rut at -36 cm reads R 96, its ridge at +8 cm R 175-176, clear mud beyond R 169; the tracks
  B 202-203 under the tyres against 48 clear; across the bog, the fixed rut pair's two grooves read G 155 and 158
  against 162-165 beside them (ground 15 and 10 cm lower), the hummocks 2-3 levels higher (8 cm). So the rut band
  is lower than the surface, the ridges higher, the fixed rut pair visible as shape; the hummocks only just. The
  auto exposure normalises the picture (an emissive of 0.15 reads 169), so only differences within one picture
  count. Seen, not sampled: the earlier picture `hide_6_bog` now shows deformed mud round the sunk car's wheels with
  dark patches in the rut floors that are the wheels' shadows or something else, unchecked; the mesh's mud reads
  lighter than the bog around it (the layer blend goes through `MF_Weather`, the mesh does not).
- **Test** (terrain test step 10, `mud mesh:` line). The patch over the bog has a vertex per 25 cm cell corner over
  the footprint (40,032, 278 x 144 as expected) and the grid's triangles, its bounds are the footprint's in X and Y
  with a Z range under 30 m, no vertex missed the ground, the material loaded, and the rest surface sits 2.0 cm over
  the traced ground at the middle and two more points (within 5 allowed). PASS; the rest of the suite unchanged.
  The material compiles under `-RenderOffScreen` (the shots run, and `terrain_test.bat gpu` carries
  `-GTProbeMaterial=M_GT_Mud`); the first two off-screen runs found what NullRHI cannot, below.
- **Traps.** `UTexture2D::CreateTransient` does not zero its first mip: the mesh displaced by garbage wherever no
  stamp had uploaded and every picture near the bog was one giant triangle (zero the mip and upload the whole field
  once at Init). A vector parameter's main pin is RGB: `.w` fails to compile (a second parameter for the texel
  counts). A material may reference two parameter collections; a third fails at translation with "too many
  MaterialParameterCollections". A top-down shot with the car in it hides its own ruts. The escape test's crawl
  distance from the same spot varies between runs (0.9 and 2.3 m seen). Judging the picture by eye would have
  passed the garbage run's flat colour as "mud".
- **Not done.** The physics does not read the field (stage C, on the go). No drying, no weather writing into a
  patch, no spray from the field. The mud's look is the two layer colours: textures come with the texture pass. Not
  felt, not looked at by the user.

## 29. Mud deformation stage C: the physics reads the field (2026-09-15)

Stage C of `docs/MUD_DEFORMATION_PLAN.md`: inside a mud patch the traction reads the field of stage A instead of the
paint window, the field's slope holds a tyre in its rut, the belly reads the channel it cut, and bogs no longer stamp
the paint. Built and headless-verified in a new terrain test step; not felt.

- **The rut ahead** (`UGTTractionComponent::Update`). A wheel in contact on Surface.Mud or Bog with a patch under its
  contact (`UGTMudSubsystem::PatchAt`, `bInMudPatch` on the wheel) reads `FGTMudField::HeightAt` at `RutLookAheadCm`
  60 ahead along where the tyre is heading: the chassis heading turned by the Chaos wheel's steer angle, flipped when
  the car travels backward (the velocity above `RutReadSpeed` 20 cm/s, the drivetrain's reverse under it). The deepest
  of three probes across the tyre's width (the centre and the two edges), so a tyre half over a rut reads it; a single
  probe read nothing when the car sat a yaw off its own ruts, where the paint's smear had read a full rut. `RutDepth` is
  that depth over the surface's MaxSinkage (0..1); the rut ease and the drop-in are section 26's, unchanged. Outside a
  patch the paint's `SampleDepth` along the car's heading as before.
- **The hold.** At the centre probe the field's gradient (`GradientAt`, cm per cm) is split about the tyre's heading.
  Along it is the climb (`RutClimb`, clamped to `RutHoldMaxSlope` 0.5, weighted by the tracks factor there so untouched
  mud never holds; a stamp's wall reads 1.5 or more over one cell), which adds `RutHoldDrag` 0.3 x climb to the wheel's
  rolling resistance: 0.15 of the load at most, inside the 0.9 cap. Across it is the wall (`RutCrossSlope`, positive
  rising to the car's right), which pushes the tyre back down into its rut: `RutHoldLateral` 0.3 x the wheel's true
  load x the slope at the contact point (`AddForceAtLocation`), fading in over `RutReadSpeed` so a parked car with a
  turned wheel is not shoved. Both are zero down a rut and on untouched mud. In reverse the climb counts backward and
  the push is the same. The gradient under the tyre is always zero (the tyre's own stamp flattens it every tick), so the
  hold has to read ahead.
- **The belly's channel** (`ReadBellyChannel`, once per tick). The box StampMud flattens (between the tyres in contact,
  inset `BellyStampInsetCm`), from the contacts and last tick's deepest sinkage; three points across its inner width
  just ahead of its leading end, the way the car is going, `RutLookAheadCm` on. `BellyChannel` is the mean depth there
  over the depth the belly would cut to (sinkage - clearance), 0..1. Inside a patch the belly drag is scaled by
  1 - `BellyChannelEase` 0.6 x BellyChannel instead of by the wheel's rut factor; outside as before.
- **The paint** (`AGTCarPawn::PaintTracks`). A wheel whose contact lies in a mud patch does not stamp the paint window;
  dirt, snow and mud outside patches as before. The picture's landscape under a patch is pushed back anyway (section 28).
- **Test** (terrain test step 11, `ruts [...]` in the result line; 15 steps). It follows the field check of step 10 so
  the stage A checks cannot be eroded: the ridge beside each sample is now read when the forward pass ends (the reverse
  and the passes cut across them; 86 of 88 ridges in the last run against 76-81 read after the reverse). The car goes
  back to the escape's start (the location and yaw recorded when its forward pass began), 3 s on the handbrake with
  the lock and low range, then 12 s or 15 m at full throttle steered at the recorded path point 4 m ahead (the
  reverse's retrace, forward, `SteerAlongEscapePath`); then the same from the start steered to a heading 30 degrees
  left of the ruts (a gain of 45 degrees per full lock: full lock at a locked crawl overshot to 62 degrees and left
  the deep band); then, logged and not gated, the same exit from the recorded path point 8 m along with `RutHoldDrag`
  and `RutHoldLateral` zeroed. Per pass: metres from its start, time, the time to 6 m (3 m across at 30 degrees, inside
  the deep band's 4.3 m half width), the fastest speed, time-weighted means of the rut read, the climb, the belly
  channel and the unsigned heading off the ruts. Gates: the pass down the ruts reaches 6 m in at most 1/1.05 of the
  first pass's time; the held exit reaches 6 m at least 1.05 x later than the pass down the ruts (or never in 12 s) and
  still gets 3 m. Two runs after the build (the crawl varies run to run): the first pass reached 6 m in 5.9 and 5.5 s,
  the pass down its ruts in 4.8 and 4.8 (rut read 0.61 and 0.79 against 0.33 and 0.34, belly channel 0.93 and 0.95
  against 0.03 and 0.06, 15 m in 9.8 and 9.9 s against 11.8 and 11.3; the wheels' drag 0.137-0.155 against
  0.188-0.206 on fresh mud); the held exit 5.5 and 8.1 s to 6 m, the unheld exit 5.2 and 6.0 (the held one 0.3 and
  2.1 s later: the same direction both runs, the size varies). The hold shows most in the heading: in the first run at
  9 s the held exit sat 14 degrees off the ruts with one rear tyre still in its rut (climb 0.50, drag 0.303) while the
  unheld one was 48-70 degrees off; the second run's means 36 against 22 degrees (the unheld one starts where the path
  had curved, so its start yaw is rougher). The reverse, reading the exact field instead of the paint's blur, went
  6.0 m in 5.9 s and 4.8 m in 8.0 s (6.0 in 4.4 with the paint): the test's retrace still wanders (it lowered 57 % and
  122 % of the forward pass's volume per metre) and a tyre beside its rut reads a wall. PASS; the other 21 PASS (the
  winch test failed once on its weak-anchor step, "timed out waiting for the anchor failure", and passed on the rerun;
  it has no mud in it).
- **Not done / unchecked.** Not felt: the hold's numbers are first guesses for the user to name. `hide_shots` not
  rerun (the physics change alters picture 12's crawl, not what its sampler checks). No hold outside patches (dirt and
  snow keep the paint's ease only). The test's retrace driver still cuts beside the ruts. No drying, no weather writing
  into a patch, no spray from the field.
- **Traps.** A field read at one point is exact to a cell: a car a yaw off its ruts reads nothing where the paint read
  a full rut (three probes across the tyre). Full lock at a locked low-range crawl overshoots a 30-degree heading by
  30 more. Later passes cut the ridges the field check counts: read them when the pass that made them ends. A step
  that teleports the car to a recorded path point needs a ground trace for Z (the bog is a trough). The winch test
  can flake on the weak anchor (rerun once).

## 30. The rut band on foot: the black under the ruts, the mud's look matched to the ground (2026-09-15)

The user drove stage C ("working well") and stood beside the bog: the rut band showed black strips along its near
edge and black blobs in it, "like you can see underneath the ruts" (the dark rut floors section 28 left unchecked, now
named). Found by pictures and fixed in the mud material and the patch; the slide-away's cap fixed on the way; the mesh
at the field's 12.5 cm; two questions answered in the backlog (resolution, tunables).

- **The pictures** (`Art/hide_shots.bat` step 13, four more, 16 now; `Art/tools/sample_rut_low.ps1`). After step 12's
  crawl the diagnostic ramp goes off and the camera stands at eye height 5 m back from the band's middle and 3.5 m to
  its side, looking at the middle on the ground (19 degrees down, the user's view on foot): `hide_13_rut_low` as
  shipped, `hide_14_rut_noslide` with the slide-away offset off (a new `SlideScale` scalar on M_GT_Mud, 1 in play),
  `hide_15_rut_nomesh` with the mud meshes hidden, `hide_16_rut_noshadow` with the landscape's shadow casting off on
  its 256 components. The runner logs the band's screen box (`rutbox`, the crawl's ends 130 cm either side, projected);
  the sampler counts, inside it, the pixels whose brightest channel is under 40 (their mean colour) and a histogram in
  six bands, so a dark strip is put down to its cause by numbers.
- **What the numbers said** (the same framing, a 4.4-4.6 m crawl). With the mesh hidden every pixel of the box sits in
  the 160-200 band: the lit ground. As shipped 387 pixels were under 40, with the slide off 384, with the landscape's
  shadow off 396: neither folded triangles nor the landscape's shadow on floors under its surface (the two suspects
  from section 28's "unchecked"). Their mean colour was 33 28 24: the mud colour under the sky alone. The posts' shadows
  in the picture fall toward the camera, so the sun is ahead, and every rut wall and ridge front facing the camera faces
  away from the sun: sky-lit, dark. What made them read as holes under a floating sheet was the spread around them:
  10,550 pixels (11.6 %) in 40-100 and 12,325 (13.6 %) in 200-235 brighter than the ground, the tops mirror-glossy
  because the rut-floor gloss (`0.5 x depth` toward `WetRoughness` 0.12) and the floor darkening (`0.25 x depth`)
  applied in dry weather, over a `MudColor` and `GroundColor` that were not the ground's (the Mud row over the Bog band,
  section 28's other unchecked thing: the halo lighter than the bog).
- **The fix** (`Art/Unreal/setup_m6_mud.py`, `AGTMudPatch::BakeLayers`). The patch bakes which landscape layer lies
  under each cell into a `PF_G8` texture (`LayerTexture`, `BogCells`): the generator's `GTTerrain::LayerAt` at the
  landscape's own vertices (`Spec.QuadSizeCm`), 1 for the Bog layer and 0 for Mud, bilinear into the cells as the
  landscape blends its weightmap, once, after `Init` (`UGTMudSubsystem::BuildPatches`). M_GT_Mud reads it as
  `MudLayer`: the ground colour and roughness are `lerp(GroundColor, BogColor, bog)` and `lerp(GroundRoughness,
  BogRoughness, bog)` with the four numbers the landscape's Mud and Bog rows (0.28 0.20 0.12 / 0.55 and 0.18 0.13
  0.08 / 0.45), churned by `TrackDarken` 0.85 where the tracks are; the water's darkening and gloss are multiplied by
  the wetness (`(0.35 + 0.25 x depth) x wet`, `wet x (0.6 + 0.4 x tracks + 0.5 x depth)`), so a dry rut is matte mud
  of the ground's colour. `MudColor` and `MudRoughness` are gone. After: 345 pixels under 40 (the shaded walls stay,
  as they should), 4,545 in 40-100 (from 10,550), 1,080 in 200-235 (from 12,325), none at 235 or more (from 31),
  64,580 of 85,440 in the ground's own band (from 52,441); the box's mean brightest channel 171 against 188 with no
  mesh (was 165). Seen in the picture: ruts cut into the same tan ground, matte, with shaded walls; no sheet.
- **The mesh at 12.5 cm** (`MeshCellCm` 25 to 12.5, the field's cell). At 25 cm the ridges drew as lumps (a 40 cm hump
  sampled by two vertices). The Hide's patch is 553 x 289 vertices (about 160,000, 319,000 triangles), one draw call,
  built once at BeginPlay. Seen, not measured: the crests are now jagged (each stamp segment adds its own sine hump;
  between segments the sum is uneven), which the lumps had hidden. Left as is until named.
- **The slide-away's cap** (`FGTMudField::StampWheel`). The cap on the offset was a flat `MaxSlideCm` 20 at any distance
  while the push falls off linearly to `SlideWidthCm` 60: a long drive pushed the cells 40 cm out to 20 as well, so
  the last 20 cm held a 20 cm drop, a slope of 1 that folds the mesh's triangles (their backs would draw black). The
  pictures showed the fold was not the black seen (384 against 387), but the cap now falls off like the push
  (`MaxSlideCm x (1 - Out / SlideWidthCm)`, a slope of a third) and never undoes a nearer stamp's slide.
- **Not done / unchecked.** The mesh's look in rain against the landscape's `MF_Weather` path (both darken by the
  wetness, not by the same law). The jagged crests. The lighting itself: the level's sky light makes sun-away faces
  about a sixth of the sunlit ground, on the car as on the mud. Whether the user's view reads right now: not felt.
- **Traps.** A dark patch in a picture is not a hole until the histogram says so: hide the suspect, switch each cause
  off, count. Auto exposure lifts a 0.18 albedo bog to a pale tan, so the mud's own colour is not what is dark; the
  sky-lit faces are. A chained bash step must check the build by build.sh's own stdout line, not by the log file
  (the first chain skipped the shots and reported a failed build that had succeeded).
- **Still there (the user, the same evening, two more screenshots): "you can see the bottom of the rut underneath the
  top edges".** My next reading was the slide-away folding the sheet where two stamps push a strip from both sides (the
  rears' ruts beside the fronts'). Checked: step 13 now crawls a second line 35 cm beside the first before its pictures,
  `SlideScale` defaults to 0 (the offset stays in the field for a texture shift; a sheet moved only up and down cannot
  fold) and picture 14 puts it back to 1. The count did not move: 1,071 dark pixels with the sheet a pure heightfield,
  1,095 with the slide displacing it, 0 with the mesh hidden, 1,058 with the landscape's shadow off; and their mean
  colour is now 14 8 4, black, not the sky-lit 33 28 24 of the single line. So: not folds, not shadow, not sky-lit
  faces. What fits every number is the depth offset itself, and the user named it from the game: the ruts float in
  front of the dirt plane. The landscape under the bog is pushed back 100 cm in depth so a rut can dip below it, so
  wherever the ground should hide the inside of a rut (behind the near rim, from eye height) the mesh wins the depth
  test within 100 cm along the ray (33 cm below the rim at 19 degrees) and you see that inside instead: the shadowed
  floor and walls under the rim's edge (the shadow-off picture proves nothing, the shadow maps may have been cached
  and the sky light's occlusion was never switched). Two lines double the near walls, which is why the count tripled.
  The fix is not a number: the ground must be the ground where it should occlude. Planned: the landscape material
  masked out (a hole) exactly where the mud mesh draws, from the patches' own textures, no depth offset at all, so
  the mesh is the ground there and nothing floats; the mesh one-sided; needs the landscape's dynamic material
  instances and a level rebuild. Awaiting the go.
- **Done (the same night): the hole instead of the depth offset.** `M_GT_Landscape` is Masked: a `Landscape:hole`
  custom node (`MUD_HOLE_HLSL` in `setup_m6_hide.py`) finds which patch box `Patch0..3` (MPC_TrackPaint) the pixel is
  in, samples that patch's own field texture (`MudField0..3`, texture object parameters defaulting to
  `/Engine/EngineResources/Black`, which is sRGB, so the sampler type is Color) at `(WorldPos.xy - box.xy) / (box.zw -
  box.xy)` and returns 0 where the mesh's own mask condition holds (tracks over 0.02 or |height| over 5 mm), 1
  everywhere else, into Opacity Mask (clip 0.333). `MudDepthOffsetCm`, the depth custom node and the Pixel Depth Offset
  link are gone (`ConnectMaterialPixelDepthOffset` stays in the library, unused). The textures reach the landscape
  through its dynamic material instances: `BuildLegLandscape` sets `bUseDynamicMaterialInstance` before `Import`
  (saved in the level, so The Hide was rebuilt), the components create their MIDs in `OnRegister` at runtime, and
  `UGTMudSubsystem::BuildPatches` calls `ALandscapeProxy::SetLandscapeMaterialTextureParameterValue("MudField<i>",
  Patch->Texture)` on every proxy once the patches exist (the log says "field textures bound on 1 of 1
  landscape(s); boxes written"). A proxy without the flag (a level built before this) gets a warning and the boxes
  stay unwritten, so there the mesh clips at the ground instead of the world opening. The mud mesh is one-sided.
- **The numbers** (`hide_shots.bat` step 13, `sample_rut_low.ps1`, the same eye). Before: 1,071 dark pixels as
  shipped, 1,095 with the slide displacing, 0 with the mesh hidden, 1,058 with the landscape's shadow off, of 85,440
  in the box (a 4.4-4.6 m crawl), mean colour 14 8 4. After: 12 as shipped (0.04 %, mean colour 35 35 39; the box's
  mean brightest channel 177.9; bands 40-100: 185, 100-160: 3,125, 160-200: 24,004, 200-235: 1,154, none at 235), 1
  with the slide displacing, 0 with the shadow off, of 28,480: this run's step 12 crawl came to 1.8 m and the second
  line to 2.4 m (the crawl from a dead stop varies run to run; nothing in the physics changed), so the box is a third
  the size, 1.25 % of it dark before against 0.04 % after. The mesh-hidden picture now shows the landscape's holes
  where the mesh drew (26,118 of 28,480 pixels in 40-100, mean colour 21 29 39: the sky below the horizon through
  the ground), so its count means nothing from here on. My look at `hide_13_rut_low` (a look, not a measurement):
  the ruts are cut into the same ground and the near rim hides their inside; along the deformed region's near
  edges runs a thin dark line. The likely cause is `MeshLiftCm` 2: at the mask's boundary the mesh's edge rests 2 cm
  above the landscape, and from 19 degrees a ray passing under that edge lands about 6 cm inside the hole, on
  nothing. Not changed (the terrain test checks the 2.0 cm lift; a 0 lift is a build, the shots and that number);
  named for the user's look.
- **Suite after the change.** 21 of 22 pass. The terrain test failed twice on the stage C ruts gate of step 11: the 30-degree exit with the hold on reached 6 m in 4.7 s against 4.8 s down the ruts, then on the rerun 4.4 s against 5.6 s (the gate wants the exit 1.05x slower). Nothing in this change touches the physics (the mesh has no collision; the hole, the flag and the one-sided mesh are rendering only; the terrain checks report the same numbers as before), and the terrain logs of the day show the same gate marginal on its own: it failed at 19:18 before any of this (4.6 against 4.5 s), passed at 19:25 (5.5 against 4.8), 19:38 (8.1 against 4.8) and 21:22 (4.9 against 4.5, 1.09x). Exits 4.4-8.1 s against passes 4.5-5.6 s over six runs: a chaotic crawl behind a thin gate. Not tuned (movement); reported for the user to call.


## 31. Mud one surface, stage D: the mesh is the ground over its whole box (2026-09-15)

Stage D of `docs/MUD_ONE_SURFACE_PLAN.md`, after the user's verdict on the hole ("better, but it is not
MudRunner/Spintires; there is a gap between the edge of the ruts and the flat mud"). The boundary the user named was
the edge of the *touched* region: the mud mesh drew only where a wheel had been, the landscape's hole followed the same
condition, and where the two met the mesh sat 2 cm up and a ray under its edge landed inside the hole on nothing. Stage
D removes the boundary by removing the condition: the mesh draws over its whole patch box and the hole is the whole box.
Built and headless-verified; the pictures are numbers, not a verdict; not looked at by the user, not felt (nothing in
the physics, the camera or the mud's shape numbers was touched).

- **The mesh draws everywhere** (`Art/Unreal/setup_m6_mud.py`, `SURFACE_HLSL`). `mask = 1.0`. The `Mask` output and the
  diagnostic stay. No draw-cost change: the triangles were all drawn before, only their pixels discarded.
- **The hole is the box** (`Art/Unreal/setup_m6_hide.py`, `MUD_HOLE_HLSL` and `build_landscape_material`). The landscape
  masks itself out over each patch box `Patch0..3` (MPC_TrackPaint) shrunk by a new scalar parameter `HoleInsetCm`
  (12.5, one mesh cell) on every side, with no texture sampling at all: the `MudField0..3` texture object parameters are
  gone, and with them the per-patch binding loop in `UGTMudSubsystem::BuildPatches`
  (`SetLandscapeMaterialTextureParameterValue`) and its dependence on the landscape's dynamic material instances.
  `bUseDynamicMaterialInstance` stays set in `BuildLegLandscape` (one line; stage E may want a parameter per patch back)
  and the boxes are still written into the collection. A patch over a flat map is unaffected: only the landscape reads
  the boxes. The material logs `mud hole: the patch boxes shrunk by HoleInsetCm 12.5 cm (one mesh cell), no field
  textures, the material masked at clip 0.333`; 24 expressions, no compile errors.
- **The mesh sits on the ground** (`AGTMudPatch`). `MeshLiftCm` 2 -> 0: the mesh *is* the ground inside the box, so it
  rests on it. The outermost vertex ring gets `EdgeLipCm` 1.0 fading to 0 at the second ring (`LiftAt` in `BuildMesh`,
  the ring index from the four edges), so the 12.5 cm overlap strip between the hole's inset edge and the box edge sits
  0-1 cm over the landscape: no z-fight, and anything the landscape's LOD morphing opens at the border shows mud, not
  sky. The mesh casts shadows now (`SetCastShadow(true)`: the landscape casts none where the hole is). `BoundsScale`
  1.5 is gone in favour of the section's own box, expanded by `DisplaceDownCm` 40 and `DisplaceUpCm` 25
  (`GetProcMeshSection` / `SetProcMeshSection`, which recomputes the component's local bounds), so the displacement can
  never be culled; `MeshBounds` stays the rest box (the test and the diagnostic's Z window read it).
- **The test** (terrain step 10, the `mud mesh:` line). The lift check now reads three interior probes and expects
  `MeshLiftCm`, and the edge ring's lip is measured at the middle of the box's -X edge and logged only. This run:
  `158730 vertices (555 x 286, expected 555 x 286), 315780 triangles, bounds x 91953..98878 y 3582..7144 z 2609..3035
  over the footprint, 0 ground misses, material M_GT_Mud, interior lift over the traced ground 0.0 / 0.0 / -0.0 cm
  (asked 0.0), edge ring lip 1.0 cm (asked 1.0) -> 1`. The mud field's own checks are unchanged (92 samples, rut mean
  -36.1 cm, ridge mean 9.7 cm ok 90, compaction 309,375 then 0 cm^3).
- **The border pictures** (`hide_shots.bat` step 14, two more, 18 now; `Art/tools/sample_border.ps1`). After step 13 the
  runner takes the patch's box (x 91953..98878, y 3582..7144), picks the side nearest the crawl (the +Y side at
  94937 6744), takes 6 m of it, and shoots it twice: `hide_17_border_low` from eye height 170 cm, 3 m outside the box
  and 3.92 m back along the border (19.7 degrees down), and `hide_18_border_far` from 40 m on the same bearing at eye
  height (6.5 degrees down: the landscape's LOD at distance). It logs a `borderbox` per picture (the border's two ends
  60 cm either side, projected) and, for the near one, a `mudstrip` and a `landstrip` (3 x 1 m of ground 1.5 m inside
  and 1.5 m outside the box). The sampler counts inside each box the dark pixels (brightest channel under 40) and the
  sky-coloured ones (blue the brightest channel by 15 or more: the sky through a crack read 21 29 39 in section 30).
  **Both runs: `hide_18_border_far` 0 dark and 0 sky of 814 (every pixel in the 160-200 band); `hide_17_border_low`
  0 dark and 0 sky of 189,864 in the first run, 16 dark (0.008 %, mean colour 25 25 25) and 0 sky in the second.** No
  crack, so `HoleInsetCm` stays 12.5 (25 was the fallback).
- **The rut band** (step 13's four pictures, `sample_rut_low.ps1`, the same eye). The count is not comparable with
  section 30's: the crawl from a dead stop varies run to run and in both of today's runs the car did not move (step
  12's crawl 0.1 m, step 13's second line 0.0 m, against 1.8 m and 2.4 m for the "12 of 28,480" run and 4.4-4.6 m for
  the 1,071 one), so the band's box is a third the size (9,389 and 9,945 pixels against 28,480 and 85,440) and nearly
  all of it is the two 40 cm pits a stationary wheel digs rather than a long shallow rut. As shipped: 1,986 of 9,389
  dark (21.2 %, mean colour 29 27 26, box mean brightest channel 128.4) and 1,709 of 9,945 (17.2 %, mean colour
  33 32 33, mean 141.2); with the slide displacing 1,938 and 1,550; with the landscape's shadow off 1,993 and 1,537
  (so not the landscape's shadow, as in section 30); with the mesh hidden 0 dark both times, the box now entirely the
  hole (all 9,945 pixels in 100-160 in the second run: auto exposure opens up when the ground is missing, so that
  picture means nothing from here on). **What is not there**: the thin dark line along the deformed region's near
  edges that section 30 named. What is there, by the numbers, is the inside of the pits. My look at
  `hide_13_rut_low` (a look, not a measurement): one continuous tan surface with the pits cut into it, no seam and no
  sheet, the pits' interiors black and their walls jagged.
- **The mud against the landscape** (the stage's trap, reported not fixed). In `hide_17_border_low` the mud mesh 1.5 m
  inside the box reads a mean brightest channel of 181.0 against 205.9 for the landscape 1.5 m outside it: **-24.9**
  (-25.1 in the first run). The mesh now covers flat mud the landscape used to draw, and it does not go through
  `MF_Weather` (no puddles, no paint ruts) and knows only two layers (the baked `LayerTexture` is 1 for Bog and 0 for
  everything else, so a box corner that is really Dirt or Scrub draws as the Mud row). Stage E's shared texture is
  where that closes; nothing was done about it here.
- **Not done / unchecked.** Not looked at by the user (the gate) and not felt. The mesh's new shadow casting was not
  isolated by a picture: with the car's pits this deep the dark pixels are their interiors either way, and no picture
  switches the mesh's own shadow off. The jagged crests are still there and still unnamed. Nothing in `MF_Weather`
  reaches the mesh. The 40 m picture is one framing of one border on one leg.
- **Traps.** A procedural mesh's render bounds come from the section's own box: `BoundsScale` inflates a 69 x 36 m
  footprint sideways to buy 40 cm of Z, so the box is expanded directly (copy the section, move Min.Z / Max.Z, set it
  back; `UpdateLocalBounds` is private but `SetProcMeshSection` calls it). Auto exposure normalises each picture, so
  the mud-against-landscape number only means anything because both strips are in the same picture. And the band's
  dark count is a function of how far the car crawled: compare the crawl lengths before comparing the counts.
- **Suite after the change.** 21 of 22 pass (body and winch passed first time). The terrain test failed on the stage C
  ruts gate of step 11 again, both runs of the day: the 30-degree exit with the hold on reached 6 m in 4.4 s against
  4.7 s down the ruts, then 4.5 s against 5.0 s (the gate wants the exit at least 1.05x slower; the unheld exit took
  5.7 s and 5.5 s, so the hold still shows, and the second run's held exit sat 44 degrees off the ruts). Section 30
  recorded the same gate failing and passing on its own before any of this (exits 4.4-8.1 s against passes 4.5-5.6 s
  over six runs), and nothing here touches the physics: the mesh has no collision, the mask, the hole, the lift, the
  lip and the shadow are rendering only, and the bog's own checks read as before (escape 14.0 m forward in 12.0 s,
  6.0 m back, mud field 92 of 92 ruts). Not tuned (movement); reported for the user to call.


## 32. Mud one surface, stage E: a real mud look (2026-09-15)

Stage E of `docs/MUD_ONE_SURFACE_PLAN.md`, after stage D made the mud mesh the ground over its whole box and left it
reading 24.9 darker than the landscape beside it. E1 (the sourcing, its own session) plus E2 and E3: one CC0 texture
set, sampled the same way by the mud mesh and by the landscape's Mud and Bog rows, so the box border has nothing left
to show. Built and headless-verified; the pictures are numbers and a look; not looked at by the user, not felt
(nothing in the physics, the camera or the mud's shape numbers was touched).

- **The texture** (`Art/Textures/Mud/muddy_tracks`, `Art/Unreal/setup_m6_textures.py`, `Art/setup_m6_textures.bat`,
  written in the E1 session and first run today). **"Muddy Tracks" (muddy_tracks) by Amal Kumar, Poly Haven, licence
  CC0 (public domain, no attribution required)**, 2K, picked as the thumbnail nearest a churned wet dirt track.
  Imported into `/Game/GrandTour/Textures/Mud`, all four 2048 x 2048: `T_GT_Mud_Diffuse` (source 2.83 MB, TC_DEFAULT,
  sRGB on), `T_GT_Mud_Normal` (the `_nor_dx` file, 25.97 MB, TC_NORMALMAP, sRGB off, no green flip: it is already
  DirectX), `T_GT_Mud_Rough` (7.30 MB) and `T_GT_Mud_Disp` (6.38 MB), both TC_MASKS, sRGB off. The `.bat` measures the
  diffuse map's mean colour in linear space first with a PowerShell System.Drawing pass (Unreal's Python has no PIL and
  cannot decode a JPG) into `muddy_tracks_mean.json`: **mean colour 0.080993 0.029794 0.011753** over 65,536 samples
  (sRGB 79.8 47.5 27.5). Nothing painted, nothing generated. Run it before the two material setups; both now stop with
  a message if the assets are missing.
- **The mud mesh wears it** (E2, `Art/Unreal/setup_m6_mud.py`: a new `TRIPLANAR_HLSL` block spliced into
  `SURFACE_HLSL`; `M_GT_Mud` 28 expressions). Three texture object parameters, `MudDiffuse` (Color), `MudNormal`
  (Normal) and `MudRough` (LinearColor), each sampler type matched to the asset's sRGB. Tri-planar by the field-derived
  normal: the XY projection for the floor, XZ and YZ for the walls, weights `pow(abs(n), 4)` normalised, three taps per
  map at `MudTileCm` **150 cm**, with `Texture2DSample` outside every branch so the hardware takes the gradients from
  the world-space UVs (the field's own taps stay `Texture2DSampleLevel`). The albedo is tinted by the layer row over
  the map's mean, `saturate(tex * lerp(GroundColor, BogColor, bog) / TextureMeanColor)`, so the texture's average still
  reads as the landscape's Mud or Bog row; the normal map is unpacked by hand (`rg * 2 - 1`, z rebuilt) and its XY
  added to the field's normal at `MudNormalScale` 1.0, renormalised; the roughness map swings the row's roughness by
  `MudRoughVary` 0.35 either way. Inside the tracks the detail normal flattens by `TrackFlatten` **0.6** and the colour
  still darkens by `TrackDarken` 0.85. The wetness and rut-depth darkening and gloss sit over the texture unchanged,
  and the diagnostic ramp is untouched.
- **The landscape wears the same** (E3, `build_landscape_material` in `Art/Unreal/setup_m6_hide.py`; `M_GT_Landscape`
  **40 expressions**, 24 before). The same `TRIPLANAR_HLSL`, word for word in the second script (both copies carry a
  note to keep them in step; the five numbers above are duplicated as constants), inside a `Landscape:mudtex` Custom
  node with five outputs: the Mud row's albedo, the Bog row's albedo, those two rows' roughness and one world-space
  detail normal over the landscape's vertex normal. The Mud and Bog rows of the `LAYERS` table take them on their layer
  blends' `Layer Mud` and `Layer Bog` pins (`LayerBlendInput.layer_input`, weight blend as the rest); every other row
  keeps its constant. **MF_Weather takes no normal**: its pins are BaseColor, Roughness, Porosity, LocalWetness,
  LocalSnow and CanPool, logged with what feeds them every run, so the plan's fallback applies. A sixth layer blend
  carries the normal (the Mud and Bog rows the detail normal, every other row `VertexNormalWS`) through a small
  normalise custom node straight into `MP_NORMAL`, and the material's normal is **world space**
  (`tangent_space_normal` off) exactly as the mud mesh's is. The hole, the layer colours, the roughness and porosity
  paths and the weather call are otherwise untouched.
- **The border** (`hide_shots.bat` step 14, `Art/tools/sample_border.ps1`, stage D's framing). The mud mesh 1.5 m
  inside the box against the landscape 1.5 m outside it in `hide_17_border_low`: **184.8 against 196.5, a difference of
  -11.8** (mean brightest channel), where stage D read 181.0 against 205.9, **-24.9**. The plan asked for the two means
  within 15 of each other. `hide_18_border_far` from 40 m (the LOD crack check): **0 dark and 0 sky of 814**, every
  pixel in the 160-200 band, as in both stage D runs. `hide_17_border_low` now has 137 dark pixels of 193,104 (0.07 %,
  mean colour 30 28 25) against 0 and 16 in stage D: the detail normal makes sun-away micro-facets, scattered over the
  frame rather than along a line.
- **The rut band** (step 13, `Art/tools/sample_rut_low.ps1`). This run's step 12 crawl was 2.0 m and the second line
  2.6 m, so its box (31,635 px) compares with section 30's 1.8 / 2.4 m run (28,480 px), not with stage D's stalled
  ones. As shipped: **119 dark of 31,635 (0.4 %, mean colour 34 29 24, box mean brightest channel 172.3)** against 12
  of 28,480 (0.04 %, mean 177.9). The bands moved the way the plan expected a texture to move them: 40-100 **1,371**
  (185 before), 100-160 4,166 (3,125), 160-200 24,052 (24,004), 200-235 **1,927** (1,154), none at 235 or more. With
  the slide displacing 87, with the landscape's shadow off 120 (so neither is the cause), with the mesh hidden 0 (the
  box is then the hole and means nothing, as since stage D).
- **My look** (a look, not a measurement). `hide_17_border_low`: one continuous churned surface running from the mud
  mesh in the foreground out over the landscape, the same fine smeared-track detail on both sides of the border, and no
  line where the border runs. `hide_13_rut_low`: the pits are cut into that surface, their crests still jagged, the
  texture visibly stretched down the steep rut walls (the tri-planar's wall projections), the deepest pit's inside
  dark. Under auto exposure the ground still reads as a pale tan, as it did before the texture: the tint keeps the
  row's colour and only the detail is new.
- **Test.** Terrain **PASS** (191 s): the mud mesh check is unchanged (158,730 vertices 555 x 286, 315,780 triangles,
  0 ground misses, interior lift 0.0 / 0.0 / -0.0 cm asked 0.0, edge ring lip 1.0 asked 1.0), and step 11's ruts gate
  passed this time (6 m down the ruts in 4.3 s, the first pass 5.4 s, the held exit at 30 degrees 5.0 s = 1.16x, the
  unheld exit 5.0 s with the heading 35 degrees off against the held one's 16).
- **Suite after the change.** 21 of 22 pass (body and winch passed first time). The terrain test passed on its own run
  twenty minutes earlier (above) and failed inside the suite on the stage C ruts gate of step 11 again: the 30-degree
  exit with the hold on reached 6 m in **4.5 s against 4.4 s** down the ruts, where the gate wants at least 1.05x
  (4.62 s); the unheld exit took 5.8 s, so the hold is still there, and the held exit's heading sat 42 degrees off the
  ruts against the unheld one's 28. Sections 30 and 31 record the same gate failing and passing on its own before any
  of this (exits 4.4-8.1 s against passes 4.3-5.6 s over eight runs now) and nothing in stage E touches the physics:
  the change is three textures, two materials and a normal, all of it rendering. Not tuned (movement); reported for the
  user to call.
- **Not done / unchecked.** Not looked at by the user (the gate) and not felt. `T_GT_Mud_Disp` is imported and unused
  (stage F or H may want it). The mud mesh still does not go through `MF_Weather`, so rain's puddles and the paint ruts
  live on the landscape only; in the dry the two surfaces now agree to 11.8. The mesh's baked layer still knows only
  Bog against everything else, so a box corner that is really Dirt or Scrub draws as the Mud row wearing mud, which is
  part of that 11.8. No tread in the rut floors (stage F), no water in them (G). One framing of one border on one leg,
  in dry weather: the wet path over the texture is unchecked.
- **Traps.** `unreal.Texture2D` has no `post_edit_change` in 5.8's Python (`set_editor_property` fires
  PostEditChangeProperty anyway; the call is wrapped and logs a note). A Custom node's `Texture2DSample` returns the
  raw sample and not `UnpackNormalMap`, so a TC_Normalmap asset (BC5, blue 0) needs its z rebuilt by hand. A
  LandscapeLayerBlend's pins are named `Layer <row>`, and `setup_m6_hide.py`'s `connect()` falls back to any other pin
  when a name misses, which would silently wire the wrong row: the per-row wiring uses a new `connect_exact()` and logs
  every pin it wired. NullRHI compiles no HLSL, so the setup scripts' `recompile_material` proves nothing about the
  shader; the off-screen shots run is the real compile check. The two copies of `TRIPLANAR_HLSL` and the five numbers
  beside them are the whole of "both materials match": nothing checks it but the border picture.


## 33. Mud one surface, stage F: the tyre's tread in the ruts (2026-09-16)

Stage F of `docs/MUD_ONE_SURFACE_PLAN.md`, after stages D and E made the mud mesh the ground over its whole box and
gave it a sourced texture ("Much much better", the user). The rut floor now carries the tyre's lug pattern, as
Spintires stamps the tread: the field remembers, per cell, which way the wheel was going and where in its lug cycle it
was, and the material draws the lugs as a normal tilt. Nothing of the tread is in the height field. Built and
headless-verified; the picture is numbers and a look; not looked at by the user, not felt (nothing in the physics, the
camera or the mud's shape numbers was touched).

- **The field remembers the tread** (`Source/GrandTour/Terrain/GTMudField.h/.cpp`). Two more per-cell arrays:
  `HeadingTurns` (the stamping wheel's heading, 0..1 of a circle) and `PhaseTurns` (the lug phase in turns of
  `LugPeriodCm` **9**, -1 where no wheel has been). `StampWheel` takes two new arguments, the heading the tyre is going
  and how far it has rolled in all, and writes both into **every cell of the tyre's capsule** (not only the cells it
  lowers: a second pass down a compacted rut lowers nothing and must still lay its own tread):
  `phase = frac((rolled + (cell centre - the contact) . heading) / LugPeriodCm)`. `TreadPhaseAt(XY)` reads it back the
  way the material draws it - the nearest cell's phase carried across that cell along its heading, never interpolated,
  because a wrapping phase and a wrapping angle cannot be filtered.
- **The traction measures the rolling** (`GTTractionComponent`). `FGTWheelTraction` gains `RolledCm` (accumulated
  `|angular speed| x radius` per tick, unsigned: the heading carries the direction, so reverse needs no sign) and
  `TyreHeading` (the heading the rut is already read along inside a patch, the way the car travels elsewhere).
  `StampMud` passes both. Chaos asserts inside `GetRotationAngularVelocity` when the async output is missing, so the
  output is checked first, as `UGTDrivetrainComponent` does. Nothing else in the traction changed.
- **The patch carries a second texture** (`AGTMudPatch`). `TreadTexture`, PF_FloatRGBA like the field's, the same size,
  zeroed the same way and uploaded with the **same dirty rects** in the same `Upload` (R heading turns, G lug phase).
  It is bound to the mesh's material instance as `MudTread`, and the patch's own `LugPeriodCm` UPROPERTY (9) goes both
  into the field and onto the instance, so the two can never disagree.
- **The material draws the lug** (`Art/Unreal/setup_m6_mud.py`, `SURFACE_HLSL`; `M_GT_Mud` **35 expressions**, 28
  before). The uv is snapped to the texel centre (point sampling), the cell's phase is carried to the pixel along the
  cell's heading, and `p = frac(phase + (WorldPos.xy - cellCentre) . heading / LugPeriodCm)`. The lug is a plateau
  `LugWidth` **0.45** of the period wide with a smoothstep flank; the flank's analytic slope (-1..1, no finite
  difference) tilts the normal about the axis across the heading by `LugTiltDeg` **25**. It shows only where the rut is
  deeper than `LugDepthMin` **0.05** (of 30 cm) and the tracks over `LugTracksMin` **0.5**, and fades with the field's
  cross-slope, a smoothstep from half of `LugWallFade` to it, so the walls stay smooth. Every number is a material
  parameter and all of them are logged each run.
- **`LugWallFade` is 3.0, not the 0.6 of the first cut.** The first build's picture read **4 brightness peaks against
  the 23.4 lugs the field held**: a 25 cm tyre's rut is only two 12.5 cm cells wide, so the central difference the
  surface normal is already built from reads a cross-slope of **1.0-1.4 across the rut's own floor** and 2.8 on its
  wall (the profile of section 27 gives the same: -38 between -26 and -2). At 0.6 the fade erased the lugs everywhere.
  At 3.0 (the knee 1.5-3.0) the floor keeps them and a real wall loses them.
- **The test** (terrain step 10, a new `tread:` line, gated in the terrain result). The step already stamps a tyre
  twice down one clean 4 m line to measure compaction; both passes now carry a heading and a rolled distance (0, then
  400 cm), and the phase is read back along that line at 2 cm steps and its wraps counted: **45 against the 44.4 asked
  (400 cm / LugPeriodCm 9), 201 of 201 samples stamped -> PASS**. It is read there and not along the escape's own crawl
  because the rears and the reverse pass cross that one and each writes its own phase, which is right for the look and
  useless for a count; 2 cm advances the phase by 0.22 turns, so only a wrap can jump half a turn.
- **The picture** (`hide_shots.bat` step 15, **19 pictures now**, `hide_19_tread_top`, `Art/tools/sample_tread.ps1`).
  Straight down from 3 m over one of step 12's ruts with the diagnostic off; the runner shrinks the axis until both its
  ends sit 30 px inside the frame and logs `treadaxis` with the span and the lugs the field says lie along it. The
  sampler walks that line one pixel at a time, averages 3 px either side, subtracts a **local** mean (a moving average
  over two and a half lug periods: a rut's own shape swings the brightness 150 levels over tens of pixels, so a lug
  riding on it never crosses the picture's global mean - the first cut counted 8 where 23.4 were asked for that reason
  alone), counts the peaks, and reports the strongest repeat between half and twice the lug period.
- **What the picture gave.** This run's step 12 crawl came to **0.7 m** (it was 2.1 m on the run before; the crawl from
  a dead stop varies run to run and nothing in the physics changed), so the axis is 66 cm and the field holds 7.3 lugs
  along it. **12 peaks against 7.3, a difference of 4.7 where 2 was asked**, the mean swing about the local mean 16.5
  levels; the strongest repeat is at **25 px, and 25 px is the field's 12.5 cm cell (26.7 px here), not the 9 cm lug
  (19.2 px)**. Both numbers have the same cause, and it is not a bug: in a low-range bog crawl the wheels turn metres
  for every centimetre the car moves, so `rolled` jumps far more between two ticks than the ground does, and two
  neighbouring cells written by two different ticks hold phases that have nothing to do with each other. Inside one
  cell the pattern is exactly 9 cm and joins its neighbour perfectly **when one stamp wrote both**; under heavy slip it
  does not, so the 12.5 cm cell edge shows and there are more bright bands than lugs. Where a wheel rolls rather than
  spins the pattern is continuous by construction (the terrain test's 45 wraps are that case).
- **My look** at `hide_19_tread_top` (a look, not a measurement): the whole churned band is covered in fine parallel
  ribs running across the direction of travel, in patches that change direction with each stamp's heading, and they
  read as a brushed streaking rather than as chunky tyre lugs from this height; the untouched mud to the side keeps the
  muddy_tracks texture with no ribs, so the gates hold. The crests are still jagged (stage H).
- **The other pictures, unchanged in kind** (the same run). `hide_13_rut_low`: 346 dark of 18,216 (1.9 %, mean colour
  36 34 30, box mean brightest channel 164.3; bands 40-100: 1,465, 100-160: 3,297, 160-200: 11,454, 200-235: 1,654),
  against 119 of 31,635 in stage E - the box is 18,216 px against 31,635 because this crawl was 0.7 m against 2.0, so
  it is mostly the pits a stationary wheel digs, as in stage D. `hide_17_border_low`: the mud inside the box 185.0
  against the landscape outside it 196.7, **-11.7** (stage E read -11.8), 300 dark of 191,512 and 0 sky;
  `hide_18_border_far` **0 dark and 0 sky of 814**, every pixel in the 160-200 band, as in every run since stage D.
- **Test and suite.** Terrain **FAIL**, on the stage C ruts gate of step 11 and nothing else: the 30-degree exit with
  the hold on reached 6 m in **4.7 s against 4.5 s** down the ruts where the gate wants 1.05x (4.73 s), a hair short;
  the unheld exit took 4.8 s. Everything else in the run passed, including the new tread gate and the mesh check
  (158,730 vertices, interior lift 0.0, edge ring lip 1.0). **The suite: 21 of 22 pass**, terrain the only failure and
  the same gate inside it (the held exit 5.2 s against 5.5 s down the ruts, wanting 5.78; the unheld exit 5.2 s, so the
  hold shows only in the heading, 16 degrees off against 32); body and winch passed first time, and the tread gate read
  45 wraps again. Sections 30, 31 and 32 record the same gate failing and
  passing on its own over ten runs now (exits 4.4-8.1 s against passes 4.3-5.6 s), and nothing in stage F touches the
  physics: the change is two arrays, one texture and a normal tilt. Not tuned (movement); reported for the user to
  call.
- **Not done / unchecked.** Not looked at by the user (the gate) and not felt. The cell edge showing under heavy slip
  (above) is named, not fixed: the cheap fix, if the user wants it, is to blend the lug slope over the four
  neighbouring cells so disagreeing cells cancel into mush instead of a grid, which costs three more taps. No tread in
  the belly's smear (`StampBelly` writes no heading or phase, so the flattened box between the wheels stays smooth).
  `T_GT_Mud_Disp` is still imported and unused. The wet path over the lugs is unchecked. One framing of one rut on one
  leg, and that rut was 0.7 m long.
- **Traps.** A wrapping phase and a wrapping heading cannot be filtered: the material must snap the uv to the texel
  centre and carry the phase itself, and a bilinear read would smear every lug away. Storing the phase at the cell
  centre and adding the pixel's offset along the same heading is what makes neighbouring cells of one stamp join
  exactly - store it at the contact instead and every cell would step. The finite-difference normal on a 12.5 cm grid
  reads a 25 cm rut's floor as a 1.0-1.4 slope, so any gate written against "flat" erases itself. And a 1D peak count
  down a rut needs a local mean: the rut's own shading is ten times the lug's.


## 34. Mud one surface, stage H: less spiky ruts, more randomness (2026-09-16)

Stage H of `docs/MUD_ONE_SURFACE_PLAN.md`, the user's two words after stages D and E ("make the ruts less spiky, and
to increase randomness"), plus H0, a follow-up from stage F. Nothing here is new machinery: the field's stamp learns to
smooth and to vary what it draws, and both materials read it bicubic and break up the texture's tile. Built and
headless-verified; the pictures are numbers and a look; not looked at by the user, not felt. No camera, no surfaces
table, no traction constant was touched - but the field's shape feeds the traction's rut read, so the physics does read
different mud (the numbers are below).

- **H0, the tread phase follows the ground** (`GTTractionComponent`). `FGTWheelTraction::RolledCm` was the wheel's own
  rolled distance (`|angular speed| x radius` per tick), so under the slip of a low-range bog crawl it ran metres for
  every centimetre of ground and two cells written by two ticks held phases with nothing to do with each other: stage 33
  recorded the tread picture repeating at the field's 12.5 cm cell (12 peaks) instead of the 9 cm lug. It is now the
  contact patch's ground travel - the chassis' velocity at the contact, along the tyre's heading, times the tick, never
  negative and zero while the wheel is not turning (over 1 degree a second) or out of contact. Nothing else in the
  traction changed; no force reads it.
- **H1a, the field is read bicubic** (`Art/Unreal/setup_m6_mud.py`, `WPO_HLSL` and `SURFACE_HLSL`). Catmull-Rom, 16
  taps, in the vertex shader (the displacement) and in the surface shader, where the slope that builds the normal is now
  the interpolant's **own derivative over those same 16 taps** rather than a central difference of four more samples: it
  is what a finite difference of bicubic samples converges to, at a fifth of the taps, and it is continuous across a
  cell edge. The vertex node takes `PatchTexels` for it. A 12.5 cm grid therefore draws a smooth surface instead of
  linear ramps with a crease at every cell.
- **H1b/c, the stamp smooths what it draws** (`FGTMudField::StampWheel`). A hump is blended into a ridge cell that
  already carries one by `RidgeBlend` **0.9** - max plus that fraction of the lesser, not the sum of stage F (1.0 is
  that sum exactly, and is how the test measures "before"). Then the cells the stamp touched are pulled toward a 3-tap
  mean **along the stamp's own direction**: crest cells toward the crest cells of the same stamp, floor cells toward the
  floor cells, by `RidgeSmooth` **0.7** scaled by how far the stroke rolled over the tyre's width. The floor's result may
  not come out above the depth this stamp cut it to, so a second pass down the same line still finds nothing to remove
  (compaction: 310,853 cm^3 then 0).
- **H2, the randomness** (`FGTMudField`, both materials). In the field, a hashed lattice noise of the cell index alone
  (`NoiseSeed` 1, no state, so the same clumps grow pass after pass): the ridge's return varies by `RidgeNoise` **0.7**
  either way in clumps of `RidgeNoiseCells` **4** (half a metre of crest), the same noise ragged-edges the tracks factor
  across the tyre's edge at 3 cells, and the rut floor's target varies by `FloorNoiseCm` **1.5** at 5 cells (only ever
  lowered to, and never above the ground). In `TRIPLANAR_HLSL` - still word for word the same block in
  `setup_m6_mud.py` and `setup_m6_hide.py` - two octaves of world-space value noise at `MudNoiseFineCm` **60** and
  `MudNoiseCoarseCm` **250** warp the tri-planar uv by `MudNoiseWarp` **0.15** tiles per octave (so the 150 cm tile does
  not read as a tile), swing the tint by `MudNoiseTint` **0.08** and the roughness by `MudNoiseRough` **0.1** on the mud
  mesh and on the landscape's Mud and Bog rows alike. `M_GT_Mud` **40** expressions (35 before), `M_GT_Landscape` **45**
  (40), no compile errors.
- **Three numbers had to be measured rather than taken from the plan, and two of them are the plan's own defaults.**
  `RidgeBlend` 0.8 took a fifth off the crest (6.58 -> 5.12 cm) where the plan asks for the height to stay, so 0.9.
  `RidgeSmooth` 0.5 and `RidgeNoise` 0.35 at a 2-3 cell wavelength cancel each other: the 3-tap smoothing that takes the
  spikes out is the same filter as a 2-3 cell noise, and with both on the crest's coefficient of variation came out
  **0.07 against the 0.12 the field had with all of stage H off** - less random, not more. So the clumps are at 4 cells,
  where the smoothing passes them, and `RidgeNoise` is 0.7 (measured: 0.22).
- **Two things had to be got right before any of it worked, and both showed only in the driven bog.** (1) A crest cell
  smoothed against *whatever* lay beside it drags the mud the wheel is about to drive into down toward the rut behind
  it, tick after tick (a cell 40 cm ahead is a crest cell of every stamp until the tyre reaches it): the escape's ridges
  came out at **-1.6 cm with 0 of 92 samples over 3** and the fronts lowered **68,917 cm^3 per metre against 230,901**,
  because the wheel kept meeting ground it had already dug. Hence "the same kind, in this same stamp". (2) Keeping the
  old rule that a stamp may never raise what a wheel cut, as a `min()` on the smoothed value, makes the smoothing a
  ratchet: at a hundred stamps a second every cell falls to the deepest one in reach, and the rut came out **75 cm wide
  at -41 cm with its crest inside it** (ridge mean -12.4, 2 of 92). The mean is a plain mean now and compaction is kept
  by the floor's target bound instead.
- **And one crash, worth the line.** The first cut of H2 pulled each crest cell toward a *noised* mean
  (`mean x (1 + RidgeNoise x noise)`). A clump of cells whose noise is positive then pulls itself up by
  `1 + RidgeSmooth x RidgeNoise` every stamp, which is geometric: inside ten seconds of crawling the crest reached
  infinity, the field's gradient came out NaN, the traction pushed a NaN at the chassis and Chaos died indexing its slip
  table with it (`Array index out of bounds: -2147483648 into an array of size 21`, twice, reproducible). The noise
  lives in each hump's volume, where it cannot compound, and the smoothing has a `MaxRidgeCm` ceiling as insurance.
- **The test** (terrain step 10, a new `along-crest:` line, gated). A 3.6 m line is stamped at a clean spot in **18
  uneven strokes** (a crawling wheel's ticks are 0.1-3 cm of ground; even strokes lay a smooth hump by construction and
  would show nothing), and the crest beside it is read station by station over 3 m - one along-cell at a time, the
  highest cell across the hump's band. Three spots in one run, so before and after come off the same ground: **A** the
  field as it ships, **B** H1 alone (the noise off), **C** stage H off (`RidgeBlend` 1, no smoothing, no noise) - which
  is exactly the field of stage F. Gates: B's cell-to-cell difference sd at most 0.55 of C's, and A's mean within 20 %
  of C's. The coefficient of variation, the rut floor and the whole profile are logged.
- **What it read.** C (stage F's field): mean **6.66 cm**, cv **0.10**, difference sd **0.88 cm**, rut floor -28.2.
  B (H1 alone): mean 6.16, cv **0.08**, difference sd **0.47** - a fall of **47 %**. A (shipped): mean **6.96 cm**
  (+4.5 % on C), sd 1.45, cv **0.21** (the plan asked 0.2-0.4 with H2 and under 0.1 without: both hold), difference sd
  0.89, rut floor **-28.0** (C -28.2: 0.7 %). The plan asked the difference sd to halve and it fell 47 %: the last 5 %
  is the sampler's own, because the crest's top lies between cells and the highest cell across a 40 cm hump reads it up
  to half a centimetre low at a random phase from station to station - white noise that sits in both numbers. The gate
  is 0.55 for that reason, stated in the test.
- **The escape's own field, unchanged in kind**: 92 samples, rut mean **-33.5 cm** ok 90, ridge mean **7.7 cm** ok 87
  (stage F: -35.6 and 10.4, ok 92 and 90), tracks 92, clear 6 m off 92, the fronts lowering **228,208 cm^3 per metre**
  (230,901), compaction 310,853 then 0, the mesh 158,730 vertices with interior lift 0.0 and the edge ring 1.0.
- **The tread picture** (`hide_19_tread_top`, `Art/tools/sample_tread.ps1`, and a new `treadfield:` line beside
  `treadaxis` so the picture can be told from the field). This run's crawl was **1.8 m**, the axis 177 cm - but a
  straight axis over a wandering crawl only lies on stamped rut for part of its length: **38 of 89 samples**, about
  76 cm, which holds **8.4 lugs** at `LugPeriodCm` 9. The field wrapped its phase **7** times along it and the picture
  read **10 peaks**; both within 2 of 8.4, where stage F read 12 against 7.3. **The cell signature is gone**: the
  strongest repeat is no longer the field's 12.5 cm cell (26.3 px) but 9 px at a correlation of 0.11, which is noise.
  The sampler's own "expected 19.7" is the whole axis over 9 cm and means nothing while half the axis is off the rut.
  The terrain test's phase-wrap gate (its own clean 4 m line, unaffected by H0) reads **45 against 44.4, PASS**.
- **The other pictures.** `hide_13_rut_low` **266 dark of 28,302** (0.9 %, mean colour 33 28 22, box mean brightest
  channel 170.9; bands 40-100: 987, 100-160: 4,337, 160-200: 21,470, **200-235: 1,242**, none at 235), on a 1.8 m crawl
  against stage E's 119 of 31,635 on a 2.0 m one and stage F's 346 of 18,216 on a 0.7 m one. The plan expected the
  200-235 band (specular spikes on the crests) to fall and it did, as a share: **4.4 %** of the box against 6.1 % at
  stage E and 9.1 % at stage F. With the slide displacing 245, with the landscape's shadow off 260 (neither is the
  cause), with the mesh hidden 0. `hide_17_border_low`: mud inside the box 185.4 against landscape 196.3, **-10.9**
  (stage F -11.7, stage E -11.8), 118 dark of 193,104 and 0 sky; `hide_18_border_far` **0 dark and 0 sky of 814**, every
  pixel in the 160-200 band, as in every run since stage D. The 40 m diagnostic: the four rut centres read R 49-84
  against clear mud R 168 (field -39 to -41), their ridges 20 cm out R 171-176 (field +2.9 to +6.9).
- **My look** (a look, not a measurement). `hide_13_rut_low`: one continuous tan ground with the pits and ruts cut into
  it, their rims now rounded and wavy rather than saw-toothed, and fine ribs across the direction of travel down the
  whole floor. `hide_19_tread_top` from 3 m: the ribs are regular and parallel over the churned band and the crest
  along its edge has broken into clumps with dark pockets between them - the clumping H2 was asked for. The mud still
  reads pale tan under auto exposure and the texture still streaks down the steepest rut walls (the tri-planar's wall
  projections, named at stage E).
- **Test and suite.** Terrain **FAIL**, on the stage C ruts gates of step 11 and nothing else: the pass down the ruts reached 6 m in **5.2 s against the first pass's 5.3** (the gate wants 5.05) and the 30-degree held exit in **4.8 s against 5.2** (it wants 5.46); the unheld exit took 4.1 s and ended 30 degrees off the ruts against the held one's 16, so the hold still shows in the heading. Everything else in the run passed, including the new along-crest gate (0.88 -> 0.47 with 0.48 asked, the mean 6.66 -> 6.96), the tread's 45 wraps and the mesh check (158,730 vertices, interior lift 0.0, edge ring 1.0). **The suite: 21 of 22**, terrain the only failure; body and winch passed first time. Sections 30-33 record the same crawl gates failing and passing on their own over a dozen runs, and the field's own checks in this run read rut mean -33.1 cm ok 85 of 92 and ridge mean 7.3 cm ok 87 - but stage H does change the mud the traction reads, so this is not the usual 'nothing here touches the physics'. Reported as it comes, not tuned (movement).
- **Not done / unchecked.** Not looked at by the user (the gate) and not felt, and this stage does move what the
  traction reads. `T_GT_Mud_Disp` is still imported and unused. The wet path over the noise is unchecked. The bicubic
  read costs 16 taps a vertex and 16 a pixel against 1 and 5: nothing measures the frame time here, and the off-screen
  runs are the only evidence it compiles and runs at all. The mud mesh still has no `MF_Weather`. One framing of one
  rut and one border on one leg.
- **Traps.** A smoothing that may only lower is a ratchet, not a smoothing. A noise that multiplies a value the
  smoothing then averages is a feedback loop with a gain over 1. A smoothing applied per stamp is applied at the
  physics tick rate, so it must be scaled by how far the stroke rolled or a crawling wheel diffuses its own mud away a
  hundred times a second. A 3-tap smoothing and a 2-3 cell noise are the same filter, and the smoothing wins. And a
  profile read at a fixed offset along a diagonal line measures the sampler's quantisation, not the mud: read the
  crest's own maximum per station instead.


## 35. Mud one surface, stage I: a mud-like shape (2026-09-16)

Stage I of `docs/MUD_ONE_SURFACE_PLAN.md`, the user on foot after F and H: "pretty solid, but it is still very sharp
and uniform. It needs to be more mudlike." Tall knife-edged banks the whole length of the ruts, the same height end to
end, the sun on the crests. So the field's shape numbers were theirs to change: the bank is now a low wide plateau
that varies along the rut, one side of a tyre throws more than the other, stretches of it slump back in, and there are
clods; and in the materials the rut floor reads as worked slurry and the crests lost their gloss. Built and
headless-verified; the pictures are numbers and a look; not looked at by the user, not felt - and this stage moves
what the traction reads (the numbers are below).

- **I1, the bank is a plateau** (`FGTMudField::StampWheel`). `RidgeWidthCm` **40 -> 90**, `MaxRidgeCm` **25 -> 12**,
  and the sine hump is a plateau: smoothstep up over `RidgeFootCm` **30**, a flat middle, the outer foot fading over
  the last 30. `RidgeReturn` stays 0.6, so the same volume makes a bank about twice as wide and less than half as
  tall. Measured across the crawl at three stations: the width at half height **18.0 -> 67.2 cm** (the plan asked
  45-70) and the crest **5.83 -> 2.38 cm**.
- **The crest's height could not be what the plan asked, and the arithmetic says why.** The plan expected 4-8 cm. The
  same returned volume over a 90 cm plateau instead of a 40 cm sine hump is **0.43** of the height by conservation
  alone (40 x 2/pi against 90 x 2/3), so 5.83 becomes 2.4 and 4 cm would need `RidgeReturn` raised, which stage I
  holds at 0.6. The test's gate is **2.0-8.0 cm**, stated in the code with that arithmetic.
- **I2, variation along the rut** (the same function, all of it in each hump's *weight*, never in the height, so the
  volume is conserved and nothing can compound - stage H's crash). Two hashed noises read at the cell's foot on the
  stroke (so they vary along the rut, not across it) swing the height by `RidgeWave`, one swings the width by
  `RidgeWidthWave` **0.5**; `RidgeSideBias` **0.3** makes one side of each tyre heavier, which side chosen by a 1 m
  noise; `RidgeSlump` **0.25** of the length, in stretches of 40-80 cm from a 1 m noise thresholded at 1 - 2 x that,
  loses half its bank, and `RidgeSlumpFloor` **0.333** of what falls settles on the rut floor there (never more than
  `RidgeSlumpRiseMaxCm` **1** - the volume-based rise reached 3.6 cm on a deep fresh stamp, which half of a 2.4 cm
  bank cannot deliver - and written as the cut depth plus that rise, so it cannot walk upward tick by tick);
  `ClodChance` **0.15** of the band's cells carry a lump half the local bank again, `ClodMinCm` 8 to `ClodMaxCm` 15
  across.
- **Two of I2's numbers had to move, measured, and the reason is stage H's smoothing.** `RidgeSmooth`'s 3-tap mean is
  applied to a cell by every stroke whose band reaches it - about **13 times** over a 90 cm band - which is a low-pass
  of **sigma 27 cm**: it keeps 96 % of a 600 cm wave, 79 % of 250 cm, **35 % of 120 cm** and **1.6 % of 60 cm**. With
  the plan's `RidgeWaveCm` 120 / `RidgeWaveLongCm` 300 / `RidgeWave` 0.5 the crest's coefficient of variation measured
  **0.20**, against 0.24 before stage I: less varied, not more. At **250 / 600 / 1.0** (the short wave weighted 0.7 and
  the long one 0.5) it reads **0.25**, and the 40-80 cm slump stretches survive only through their floor rise. The
  plan's 0.35-0.6 is out of reach with this smoothing in front of the field, and buying more costs the crest its
  height: at `RidgeWave` 0.5 the shipped crest sat 11 % under the unvaried one, at 1.0 it sits **21 %** under. The cv
  gate is **0.22** (a regression gate on what stage I won) and stage H's own "the crest keeps its height" band is
  **30 %** instead of 20 %, because stage I's slump takes about an eighth of the bank away on purpose.
- **`RidgeFillShare` 0.35, the one number this stage added that is not in the plan.** A 90-135 cm band reaches across
  the *next* pass's rut - the wheels and the two crawl lines are under a metre apart - and at first every bank filled
  the rut beside it: the escape's rut mean went **-32.1 -> -27.3 cm** with only **59 of 88** samples still past 0.6 of
  their sinkage, and the bog's own sink check went with it. A cell that is already a rut (under -1 cm) now takes only
  this share of a deposit (slurry swallows what falls in); fresh ground takes all of it, or every bank would lose two
  thirds. With it: rut mean **-30.6**, 77 of 92.
- **I3, the walls and the floor** (`Art/Unreal/setup_m6_mud.py`, and the shared `TRIPLANAR_HLSL` in
  `setup_m6_hide.py`). The tri-planar weights are `pow(abs(n), MudTriSharp 6)`, 4 before, so a steep wall takes its own
  projection instead of the floor's streaked down it. Inside the tracks the roughness falls toward `WetRoughness` by
  `TrackWetLook` **0.25** even in the dry, the tint goes `TrackSlurryDarken` **0.12** darker on top of `TrackDarken`,
  and the fine octave of the world noise doubles (`nFine` is the shared block's own local), so the floor reads worked.
  Last of all `CrestRoughUp` **0.1** takes the gloss off any cell standing above the ground. `M_GT_Mud` **44**
  expressions (40 before), `M_GT_Landscape` **46** (45), no compile errors, and the off-screen shots run is the proof
  they compile.
- **The test** (terrain step 10, a new `ridge shape (stage I...)` line beside the along-crest one, gated, plus a
  `station by station` line). The along-crest profile is read over **6 m** now and stamped over 6.6 m in 33 strokes
  (3 m and 18 before: the variation asked for is at 1-3 m and a 3 m window holds one wave of it), the spots are 4 m
  apart across the route and 9 m along it, and stage I's variation is off at the B and C spots so that stage H's own
  before-and-after still measures the smoothing. **Before -> after: width at half height 18.0 -> 67.2 cm, crest
  5.83 -> 2.38 cm, crest curvature 20.86 -> 0.85 cm, cv 0.24 -> 0.25, the dominant wavelength's argmax 0.50 m at
  r 0.14 -> 0.50 m at r 0.53 with the scale it stays correlated over 1.25 m, left/right ridge 1.01 -> 0.95, the
  profile's rut floor -28.0 -> -29.5 cm** (the plan asked within 15 % of -28). The gates are the width, the crest and
  the cv, and they pass.
- **The curvature's 20.86 is not a fair "before".** The first cut of the cross profile stepped a fixed 12.5 cm along a
  diagonal (which reads one cell twice and skips the next) and measured every station, including one where the wave
  had taken the bank away and the highest cell was a crumb on the rut's rim: that station read **20.40 cm** and took
  the mean of three from 0.85 to 7.37. The profile now walks cell by cell and the curvature is only read where a bank
  stands clear of the rut with a cell either side of its top. The three stations after: **-2 m peak 3.31 cm at 44 cm
  out, width 65, curvature 1.04 | 0 m peak 2.03 cm at 22 cm out, width 66, no bank clear of the rut | +2 m peak
  1.82 cm at 72 cm out, width 70, curvature 0.66.** The plan expected under 1 cm and the two real banks read 1.04 and
  0.66.
- **The escape's own field**: 92 samples, rut mean **-30.6 cm** ok **77** (before -32.1 ok 80; stage H -33.1 ok 85),
  ridge mean **4.2 cm** ok 92, tracks 92, clear 6 m off 92, compaction 310,853 then 2,288 cm^3 with a 1.4 cm ridge,
  the mesh unchanged (158,730 vertices, interior lift 0.0, edge ring lip 1.0), the tread's 45 phase wraps against 44.4.
  The escape's profile across the track is the shape change in one line:
  `-30 -19 -19 -20 -20 -20 -19 -20 -20 -23 -27 -32 -38 -20 2 4 4 3 2 1 0 0 0 0 0` - a 38 cm rut and a 4 cm bank 60 cm
  wide, where stage A's read `... 4 -26 -38 -2 11 7 1 0 ...`, an 11 cm spike two cells wide.
- **A fourth gate moved with the profile.** The escape's "a ridge of at least 3 cm beside each sample" was
  written against the old hump; at 0.43 of the height it measures nothing, so it is **1.0 cm** now (92 of 92 pass it,
  ridge mean 4.2). The search window follows `RidgeBandCm()` (135 cm) instead of the old 40.
- **Pictures** (`hide_shots.bat`, **20** now: `hide_20_rut_side`, 1.5 m over the ground, 2 m to the side of one rut,
  yawed down it and pitched a fixed 10 degrees - the user's own view on foot - with its own `sidebox` logged and
  sampled by `Art/tools/sample_rut_low.ps1`). Taken again on the shipped field after the re-gating below; this run's
  crawl was **4.0 m**, the longest since section 30's 4.4-4.6 m, so its boxes are three times the earlier ones and the
  counts are comparable with that run rather than with stage H's 1.8 m. `hide_13_rut_low` **1,888 dark of 74,034**
  (2.6 %, mean colour 30 29 26, box mean brightest channel 159.3; bands 40-100: 6,064, 100-160: 16,193, 160-200:
  47,485, **200-235: 2,400 = 3.2 % of the box**, against 4.4 % at stage H, 6.1 % at E and 9.1 % at F - the crest
  highlights I3 went after). With the slide displacing 2,047, with the landscape's shadow off 1,826 (so neither), with
  the mesh hidden 0. `hide_20_rut_side` **2,217 dark of 163,928** (1.4 %, mean 161.5, **200-235: 2,440 = 1.5 %**).
  Two earlier runs of the day, at 1.0 m and 1.7 m of crawl, read 698 of 21,409 and 117 of 27,632 in the band's box:
  the dark count is a function of how far the car crawled, as since stage D. Border: mud inside the box 184.6 against
  the landscape outside it 195.2, **-10.6** (stage H -10.9, F -11.7, E -11.8), `hide_17_border_low` 323 dark of
  195,394 and 0 sky, `hide_18_border_far` **0 dark and 0 sky of 814**, every pixel in the 160-200 band, as in every
  run since stage D.
- **My look** at `hide_20_rut_side` (a look, not a measurement): one continuous tan churned ground with the crawl's
  pits cut into it in the foreground, their rims rounded and wavy and their floors worked; the banks are low and wide
  enough that they read as swellings in the ground rather than as edges. The texture still streaks down the steepest
  pit walls even at `MudTriSharp` 6 (those walls are near vertical and the side projections stretch too), named and
  not chased.
- **The three gates stage I broke, taken apart.** All three were written for a 40 cm bank and none of them measures
  the rut a wheel cuts any more; the clean single-pass rut floor on the along-crest line went **-28.0 -> -29.6 cm**,
  *deeper*, so nothing was lost where one pass runs on untouched ground.
  (1) **The mud field's rut check**: for each wheel contact sampled every half second of the escape's forward pass
  (80-92 of them), the field's height under it when step 10 reads it, gated at "9 of 10 past 0.6 of that wheel's own
  sinkage" (-24 cm at the escape's 40) since stage A. A 90-135 cm bank reaches into the next pass's rut - the rears'
  and the reverse pass's - and the count read **80 of 92 before stage I** (already under its own gate) against 77, 64,
  86, 75, 69 after. Re-gated to what it is really asking: the **mean** depth against the mean sinkage (0.6 of it,
  -24 cm; read **-32.0, -31.9, -28.4, -29.6**) and **three quarters** of the contacts past **half** their own sinkage
  (read 90 of 92, 82 of 88, 79 of 88, 77 of 80); the old 0.6 count stays in the line, logged, because what it now
  measures is the spill between passes.
  (2) **The bog's middle sink**: driving the deep band at 30 km/h, the body's clearance drop against its firm-ground
  clearance, at least 8 cm with max sinkage 0.7 - written at section 23 on 2026-09-14, before any mud field. Stage I
  does not touch the sinkage model, but it does change what a wheel reads 60 cm ahead of itself: a 4 cm bank is less
  of a climb than a 25 cm spike, so the car keeps more speed through the band (**slowest 91-104 cm/s against 85**) and
  has less time to settle. **9 cm before, 8 / 11 / 8 / 8 / 8 after**, with max sinkage 1.00 and the belly below the
  mud's surface (clearance 6-7 -> -1 or -2) every time. Reducing the spill was tried first and does not move it: the
  slump's floor cap **3 -> 1 cm** read 8 on both sides (it is kept at 1 anyway, being what half of a 2.4 cm bank can
  deliver). So the threshold is **7 cm**, with that measurement in the comment.
  (3) **"Clear 6 m off"** (found on the way): the tracks factor 6 m outward of every sample had to be under 0.05. A
  pass used to touch half a metre either side of itself and now touches 1.5 m, and the escape wanders across an 8.6 m
  deep band, so a point 6 m out can land on another pass: **86 of 88** in one run against 88 and 92 of 92 in others.
  Gated at 0.95 of the samples, which still catches a field smeared everywhere.
- **Test and suite.** With those three re-gated, terrain's mud checks all pass: **mud field 1** (rut mean -29.6 against
  -24 asked, 77 of 80 past half their sinkage, the 0.6 count 69 logged, ridge mean 3.2 cm over 1.0, tracks 80, clear
  6 m off), **mesh 1**, **tread 1** (45 wraps against 44.4), **along-crest 1** (0.21 -> 0.09 with 0.11 asked, mean
  3.27 -> 2.57 inside the 30 % band), **ridge shape 1** (the six numbers above), **bog 1** (body 8 cm, gate 7). The run
  still **FAILs**, and now on nothing but **step 11's two stage C crawl gates**: 6 m down the ruts in **4.9 s against
  the first pass's 5.0** where 4.76 is wanted, and the 30-degree held exit in **4.5 s** where it must be slower than
  the pass down the ruts (the unheld exit took 4.1 s and the held one's rut read was 0.56 against 0.48, so the hold is
  there). Sections 30-34 record that same pair failing and passing on its own over a dozen runs; it is movement and it
  is not tuned here. **The full suite before the re-gating: 20 of 22, 21 after one rerun** - `loot` flaked once on
  "the node was not offered", nothing to do with the mud, and passed on the rerun in 15 s; body and winch passed first
  time; terrain was the only real failure there too.
- **Not done / unchecked.** Not looked at by the user (the gate) and not felt. The cv is 0.25 where the plan asked
  0.35-0.6 and the mechanism is understood, not fixed: the way to more variation without losing the crest is to make
  stage H's smoothing scale-aware (smooth across the bank, not along it), which is a change to stage H's own
  machinery. The slump's 40-80 cm stretches are erased by that same smoothing except through their floor rise. The
  wet path over the slurry floor is unchecked (`TrackWetLook` only shows in the dry here). `T_GT_Mud_Disp` is still
  imported and unused. One framing of one rut and one border on one leg, and that rut was 4.0 m long.
- **Traps.** A profile stepped at a fixed distance along a diagonal reads one cell twice and skips the next, and a
  second difference of that measures the sampler. A curvature read at the highest cell is the rut's wall wherever
  there is no bank. A stamp's band is also its reach along the stroke, so widening it from 40 to 90 cm quadruples the
  cells per stamp and lets one pass write into the next pass's rut. And a low-pass applied once per physics tick is a
  filter whose sigma grows with the band: check what wavelength survives it before choosing a noise's wavelength -
  this is the second stage running to catch stage H's smoothing eating the randomness it was given.


## 36. Mud one surface, stage G: water in the ruts (2026-09-16)

Stage G of `docs/MUD_ONE_SURFACE_PLAN.md`, after stage I gave the mud its shape. A bog now has a water table, and a
rut cut below it holds water: a second grid per patch at the ground plus the table, translucent, masked off wherever
the mud stands at or above it, so the water is in the ruts and only in the ruts and its surface follows the ground
cell by cell instead of being one plane over the bog. Built and headless-verified; the pictures are numbers and a
look; not looked at by the user, not felt. **The physics half is built and off** (`UGTMudSubsystem::bRutWaterPhysics`
false): nothing in the driving reads the water yet, and nothing in the mud's shape, the camera or the traction's
constants was touched.

- **The spec** (`FGTRouteSection::WaterTableCm`, `Source/GrandTour/Terrain/GTTerrainGenerator.h`). A Mud section
  carries where its water stands, cm relative to the **undisturbed ground under each point**: **-20** by default, so a
  30 cm rut holds 10 cm and untouched mud holds none. `UGTMudSubsystem::BuildPatches` hands it to the patch before
  `Init`. A field never edited in `DA_Terrain_Hide` takes the C++ default, so The Hide is at -20 without touching the
  spec asset.
- **The weather lifts it** (`AGTMudPatch::WetTableLiftCm` **15**, `Tick`). Ground wetness 0..1 from
  `UGTWeatherSubsystem::GetWetness` raises the table by that much at wetness 1, exactly as `AGTWaterSheet::Tick` lifts
  a ford by its `RiseWithWetnessCm` 80 (a bog's table is a hand's width, not a river's). The grid is built at the
  still table and the lift moves the whole component, with the material told where the table is now:
  `CurrentWaterTableCm()` is the sum and is what everything reads.
- **The water grid** (`AGTMudPatch::WaterMesh`, `BuildWaterMesh`, called at the end of `BuildMesh`). The same
  vertices as the mud mesh, each `WaterTableCm` over that mesh's rest height, normals up (a water facet is level
  whatever the ground does; the sheet still follows the ground from vertex to vertex), no collision, no shadow,
  `SetTranslucentSortPriority(1)` so it sorts after the mud. **158,730 vertices and 315,780 triangles, the mud
  mesh's own**, one draw. With `M_GT_MudWater` missing the grid is not built at all and the component is hidden: a
  white default sheet over a bog would be worse than no water.
- **The material** (`M_GT_MudWater`, `Art/Unreal/setup_m6_water.py` + `Art/setup_m6_water.bat`, **17 expressions**,
  no compile errors). Translucent, two-sided, its own master outside `MF_Weather` as the ford's `M_GT_Water` is. It
  reads the patch's own field texture (`MudField`, R the height in metres) inside `PatchMin`/`PatchSize` the way
  `M_GT_Mud` does, and the water at a pixel is `WaterTableCm - height`: `EdgeFadeCm` **1.0** cm of depth fades it in,
  so a pixel whose mud stands at or above the table is fully transparent and **that is the whole mask**. The tint runs
  `ShallowColor` **0.100 0.085 0.060** to `DeepColor` **0.018 0.014 0.010** over `WaterDeepCm` **12** cm, the opacity
  `ShallowOpacity` **0.35** to `DeepOpacity` **0.92** with `FresnelOpacity` **0.35** more at a grazing angle, and the
  roughness `WaterRoughness` **0.06** falling to `GlossRoughness` **0.02** there (the sky). Brown, not the ford's
  blue-green: this is the water that stands in a wheel rut.
- **5.8's Python has no `TLM_SURFACE_FORWARD_SHADING`.** The plan's translucency lighting mode is the editor's label
  for the C++ enumerator `TLM_SurfacePerPixelLighting`, and Python offers `TLM_SURFACE`,
  **`TLM_SURFACE_PER_PIXEL_LIGHTING`** and the four volumetric modes. The script tries them by name in that order and
  logs which it set (`TLM_SURFACE_PER_PIXEL_LIGHTING`); without one of them a translucent surface takes no specular at
  all and there would be no sky in the water.
- **The physics half, off** (`UGTMudSubsystem::bRutWaterPhysics` **false**, `UGTTractionComponent::Update`). With it
  on, a wheel in contact inside a patch takes `AGTMudPatch::WaterDepthCmAt` (the table over the field's height there)
  as its `WaterDepthM`, the **deeper** of that and the ford sheet's, never the sum: it then feeds the water drag, the
  buoyancy grip loss and the engine flood that were already there. Off, the line is one branch on a bool and the
  numbers below are the same driving as stage I's.
- **The test** (terrain step 10, a new `rut water (stage G)` line, gated in the terrain result). It reads the deepest
  cell of the along-crest line's own rut - a clean single-pass rut this step stamps at a clean spot, whose floor has
  read -29.6 cm since stage I - through the patch's own `WaterDepthCmAt`, the call the traction will make, and gates
  it against the arithmetic within 2 cm; and it reads a point a metre and a half beyond the ridge band, which must be
  dry, or the table is being treated as a plane over the bog instead of an offset from the ground. **Table -20.0 cm
  (section -20.0 + a weather lift of 0.0 of 15.0 at wetness 1); the deepest cell -30.8 cm -> asked 10.8 cm, the patch
  reports 10.8 cm; that line's rut mean -29.6 cm -> 9.6 cm of water; untouched mud 0.00 cm; the water grid 158,730
  vertices against the mud mesh's 158,730, 315,780 triangles, M_GT_MudWater, drawn -> 1.**
- **The picture** (`hide_shots.bat` step 17, **21 pictures now**: `hide_21_rut_wet`, hide_13's eye and hide_13's box,
  with the table lifted by a wetness of 1 and the weather's own wetness put back after the shot; `wetbox` in the log,
  `Art/tools/sample_rut_low.ps1` samples it). The collection cannot be set directly - `UGTWeatherSubsystem`
  overwrites `MPC_Weather`'s Wetness from its own number every tick - so the runner sets that number
  (`SetWetnessForTest`, a test hook) and the collection, the mud material's wet path and the patch's lift all follow
  it. At the shot the weather read **0.97-0.98** (it dries at 1 % a second) and the patch's table **-5.3 cm**
  (-20.0 + a lift of 14.7).
- **Both picture runs stalled the crawl**, which is what makes the band numbers hard to read. Step 12's crawl from a
  dead stop ran **0.0 m then 0.1 m** (the second line 0.1 m then 0.7 m) against **4.0 m** for stage I's run, so the
  band's box is 9,184-10,293 px against 74,034 and is nearly all pit. Named, not chased (section 31 recorded the same
  stall, and nothing in stage G touches the physics). The two runs' numbers, in that light:
  **`hide_13_rut_low`** 16 dark of 10,293 (0.2 %, mean brightest channel 153.6; 40-100 **996 = 9.7 %**, 200-235
  **381 = 3.7 %**) and 444 of 9,184 (4.8 %, mean 138.6; 40-100 **1,237 = 13.5 %**, 200-235 **115 = 1.25 %**), against
  stage I's 3.2 % in the 200-235 band on its 4.0 m crawl. **`hide_20_rut_side`** 860 of 99,386 (0.9 %, mean 164.4,
  200-235 **4.5 %**) and 1,247 of 109,242 (1.1 %, mean 167.9, 200-235 **3.9 %**), against stage I's 1.5 %. The two
  runs disagree by a factor of three on the same gate with the same build, so **the band moves are the crawl's, not
  the water's** - and the look below says why: at the -20 table this hollow holds almost no water.
  **`hide_21_rut_wet`**, the lifted table: 0 dark both runs, 40-100 **143 = 1.4 %** then **140 = 1.5 %**, 200-235
  **44 = 0.43 %** then **8 = 0.09 %**, and **90-95 % of the box in the 100-160 band** with the mean brightest channel
  **123.5 / 119.5 against the dry picture's 153.6 / 138.6**. The plan expected the 200-235 band to rise with the sky
  standing in the water; it fell, and the water reads as a dark fill. That is the stage's one open question, and it
  is the user's to call.
- **Border and tread, unchanged** (the water is not at the box border). `hide_17_border_low`: the mud inside the box
  against the landscape outside it **-10.6 then -10.7** (stage I -10.6, H -10.9, F -11.7, E -11.8), 0 dark and 0 sky
  of 189,864. `hide_18_border_far` **0 dark and 0 sky of 814**, every pixel in the 160-200 band, as in every run
  since stage D. The tread axis (50 cm of rut off a 0.1 m crawl): 4 peaks against the field's 5.6, inside the 2 asked.
- **My look** (a look, not a measurement). `hide_21_rut_wet`: one dark brown pool standing in the hollow the spinning
  wheels dug, with a clean water line against the banks around it and a second small pool off to the left; the pool
  is a flat dark sheet with a faint lighter sheen at its far edge, not a mirror of the sky. `hide_13_rut_low`, the
  same eye and the dry table: the same hollow with its ribbed floor and **no pool at all**. That is the two numbers
  agreeing: the hollow a sinking car digs is mostly the belly's smear, 10-20 cm deep, which sits above the -20 table,
  while a driven rut's floor (the test's -30.8 cm) is below it. The water is where the plan put it; there is just
  very little of it in the dry at this spot.
- **Test and suite.** Terrain **FAIL**, and on nothing but **step 11's held-exit gate**, the pair marginal since
  section 30: 6 m down the ruts in **5.4 s** against the first pass's 6.8 (that gate passes), and the 30-degree held
  exit in **5.1 s** where it must be 1.05x the pass down the ruts, 5.67 (the unheld exit took 4.1 s, so the hold is
  still there). Every mud check passes: mud field 1 (92 samples, rut mean -33.1 cm, 92 of 92 past half their sinkage,
  ridge mean 4.6 cm, compaction 310,853 then 763 cm^3), mesh 1, tread 1 (45 wraps against 44.4), along-crest 1
  (shipped mean 2.57 cm cv 0.25 difference sd 0.23, H1 alone 2.46/0.15/0.09, stage H off 3.27/0.14), ridge shape 1
  (width 67.2 cm, crest 2.38 cm, cv 0.25, rut floor -29.6 cm), rut water 1, bog 1. **The full suite: 21 of 22**, terrain the only failure and the same pair inside it (6 m down the ruts in 5.4 s against the first pass's own 5.4, and the held exit in 4.4 s; the unheld exit 4.8 s), with the rut water gate reading the same 10.8 cm asked and 10.8 read; body, winch and loot passed first time. Not tuned (movement).
- **Not done / unchecked.** Not looked at by the user (the gate), not felt, and the drag is off. The dark water is
  named and not chased: the opacity reaches 0.92 by 12 cm and the tint is near black there, so a deep pool hides its
  own floor, and the sky's reflection through `TLM_SURFACE_PER_PIXEL_LIGHTING` measured 8-44 pixels in the 200-235
  band. Nothing measures the second grid's frame cost (158,730 more vertices and a translucent pass over the box);
  the shots run stalled its crawl twice, which it also did at stage D with no water in the build, so the two cannot
  be told apart from here. The water is flat: no ripples, no normal, no flow, and nothing of the rain falls in it.
  `T_GT_Mud_Disp` is still imported and unused. One framing of one hollow on one leg, at two wetnesses.
- **Traps.** `MPC_Weather`'s Wetness cannot be set from a test: the weather subsystem writes it from its own number
  every tick, so the number is what a test sets. A translucent material's default lighting mode is volumetric and
  takes no specular, so a water sheet built without touching it has no sky in it and no gloss; and the enumerator's
  Python name is not the editor's label. A mask on a translucent surface is its opacity, not an opacity mask - there
  is no clip - so the "only ruts draw" rule is `saturate(depth / EdgeFadeCm)` and nothing else. And the water grid
  must be built after the mud mesh, because it is the mud mesh's own rest heights plus the table.


## 37. Mud one surface, stage J: matte mud, no tread lines, a lower waterline (2026-09-16)

Stage J of `docs/MUD_ONE_SURFACE_PLAN.md`, the user on foot after stages I and G ("pretty happy with it at the
moment"): "Mud is too shiny, and there are these lines that appear after mud has been deformed, which doesn't look
good at all. The waterline needs to be lowered a bit, maybe by half." Three named changes, three numbers, nothing
else: no shape, no physics, no camera, no water look beyond where the level puts it. Built and headless-verified; the
pictures are numbers and a look; not looked at by the user, not felt.

- **J1, the shine** (the shared `TRIPLANAR_HLSL`, word for word in `Art/Unreal/setup_m6_mud.py` and
  `Art/Unreal/setup_m6_hide.py`). The sourced roughness map reads wet, so its sample is remapped into
  `MudRoughMin` **0.70** - `MudRoughMax` **0.90** inside the shared block, and from there on `texRough` **is** the
  roughness: the mud mesh takes it (plus stage H2's `MudNoiseRough` 0.1) and so do the landscape's Mud and Bog rows,
  the same band on both sides of the patch box. What no longer reaches the mud is the pair of row constants the
  roughness used to come from (`GroundRoughness` **0.55** / `BogRoughness` **0.45**, and `MudRough` / `BogRough` on
  the landscape) swung by `MudRoughVary` **0.35** - all four read wet themselves, which is what the user was seeing.
  They are still parameters and still wired, so one line brings the row swing back. `TrackWetLook` **0.25 -> 0**: a
  worked floor keeps stage I's darker tint and doubled noise but takes no wet gloss in the dry. The wetness path
  (MPC_Weather's Wetness toward `WetRoughness` 0.12, and the rut-depth darkening) and `CrestRoughUp` 0.1 are
  untouched. `M_GT_Mud` **46** expressions (44 before), `M_GT_Landscape` **48** (46), no compile errors.
- **J2, the lines** (`LugTiltDeg` **25 -> 0**). The user's screenshot was stage F's tread: regular stripes across the
  rut floor and up its near walls. The tilt is the only place the lugs reach the picture (`tan(radians(0))` is 0), and
  **the material parameter is the only default there is** - `grep -rn LugTilt Source/` finds nothing, `AGTMudPatch`
  pushes only its `LugPeriodCm` onto the instance - so one number turns them off. Everything else of stage F stays:
  the field still writes a heading and a lug phase per cell, the patch still uploads `TreadTexture`, and terrain step
  10's phase gate still reads **45 wraps against 44.4 asked, 201 of 201 samples stamped -> PASS**. Bringing them back
  subtler and broken is a separate ask.
- **J3, the waterline** (`FGTRouteSection::WaterTableCm` **-20 -> -25**, `Source/GrandTour/Terrain/GTTerrainGenerator.h`).
  `AGTMudPatch::WaterTableCm`'s own fallback default and `setup_m6_water.py`'s `WATER_TABLE_CM` (what the master shows
  before a patch pushes the section's number) follow it to -25. The spec asset could have carried the old number, so
  `setup_m6_hide.py` now logs every Mud section's table and moves any still reading the old -20 to the C++ default:
  The Hide's one mud section at 1035 m read **-25.0 cm** straight off the C++ default and nothing was written, which
  is the memory's "a spec-asset field never edited follows the C++ default" measured again. `WetTableLiftCm` stays 15.
- **The water gate followed the arithmetic** (terrain step 10, the `rut water` line). Table **-25.0 cm** (section
  -25.0 + a weather lift of 0.0 of 15.0 at wetness 1); the crawl line's deepest cell **-30.8 cm** -> asked **5.8 cm**,
  the patch reports **5.8 cm** through the call the traction will make (gate: within 2), that line's rut mean -29.6 ->
  **4.6 cm** of water, untouched mud **0.00 cm**, the water grid 158,730 vertices and drawn -> **1**. Stage G read
  10.8 / 10.8 at the -20 table, so the water in a driven rut is a little over half what it was, which is the ask.
- **The shine, measured** (`hide_13_rut_low` and `hide_20_rut_side`, `Art/tools/sample_rut_low.ps1`). This run's crawl
  was **4.1 m**, the longest since stage I's 4.0 m, so the boxes compare with that run and not with stage G's stalled
  ones. `hide_13`: **1,878 of 77,024 in the 200-235 band = 2.44 %** against stage I's 2,400 of 74,034 = **3.2 %**
  (stage H 4.4 %, E 6.1 %, F 9.1 %), the box's mean brightest channel **162.6 against 159.3** (the plan asked within
  8), 2,265 dark (2.9 %) against 1,888 (2.6 %). `hide_20_rut_side`: **1,995 of 164,255 = 1.21 %** against stage I's
  2,440 of 163,928 = **1.5 %**, mean **160.2 against 161.5**, 2,487 dark (1.5 %) against 2,217 (1.4 %).
- **The band did not reach the 1 % the plan asked, and the wet picture says why.** 2.44 % is a quarter off, not a
  collapse. If those pixels were gloss, the glossiest the material gets should have more of them - and it has fewer:
  `hide_21_rut_wet`, the same eye and box with the wetness forced to 1 (roughness pulled toward `WetRoughness` 0.12
  everywhere, which is what the wet path is for), reads **288 of 77,024 = 0.37 %** in that band with 18 pixels at 235
  or more and 47 % of the box in 100-160, mean brightest channel **138.8**. The wet path darkens the albedo by
  35-60 %, so what the band is counting in the dry picture is **sunlit pale ground, not a specular highlight**; auto
  exposure normalises each picture separately, so that is a read across two pictures and weaker than a number inside
  one. Reported, not chased: chasing it would mean roughness past 0.90 (flat mud) or the albedo, and neither is what
  the user named.
- **The border closed with it** (`hide_17_border_low`, `Art/tools/sample_border.ps1`). The mud mesh 1.5 m inside the
  box **185.2** against the landscape 1.5 m outside it **189.7**: **-4.5**, against -10.6 at stage I, -10.7 at G,
  -10.9 at H, -11.7 at F and -11.8 at E. Both sides now take their roughness from the same band, where before the
  mesh blended the two row constants by the baked layer and the landscape used each row's own. `hide_18_border_far`
  **0 dark and 0 sky of 825**, every pixel in the 160-200 band, as in every run since stage D.
- **The lines, measured** (`hide_19_tread_top`, `Art/tools/sample_tread.ps1`). The 4.1 m crawl gave a **400 cm axis**
  with 884 pixel samples, of which the field says **38 of 201** lie on stamped rut (the axis is straight and the crawl
  wanders, as at stage H). It read **30 peaks above a local mean** with a mean swing of **10.6 levels**, and the
  strongest repeat between 10 and 40 px at lag 29 px with a correlation of **0.07** - the noise floor (stage H called
  0.11 noise; stage F, with the lugs on and the phase broken, read a clear repeat at the field's 12.5 cm cell). **There
  is no peak at the 19.9 px lug period.** The raw count did not fall to stage H/I's 8-10 because those axes were 177 cm
  and this one is 400: per metre it is 7.5 against 5.6, and with no period behind it. The periodicity is what the
  stripe was, and it is gone, so the plan's "switch each candidate off and count" hunt was not needed.
- **My look** (a look, not a measurement). `hide_19_tread_top` from 3 m straight down: the fine parallel ribs that ran
  across the direction of travel over the whole churned band at stages F and H are **not there**; what is left inside
  the ruts is the texture's own smeared streaking running *along* the travel direction. `hide_13_rut_low` at eye
  height: one continuous pale tan ground with the crawl's furrows cut into it, matte, no sheen or bright speculars
  anywhere in the frame, the walls combed. One thing worth naming that is not the tread: the rut **rims** carry
  regular saw-tooth notches, clearest along the far rut from above - the field's own shape at cell scale, not the
  material. Unnamed by the user, not chased (it is a shape number).
- **Test and suite.** Terrain **FAIL**, and on nothing but step 11's stage C held-exit gate, marginal since section 30:
  6 m down the ruts in **4.7 s** against the first pass's 5.1, and the 30-degree held exit in **4.6 s** where the gate
  wants 1.05x the pass down the ruts (**4.94**); the unheld exit took 5.5 s and ended 14 degrees off the ruts against
  the held one's 17, so the hold is still there. Every mud check passes: mud field 1 (88 samples, rut mean **-30.0 cm**
  against -24 asked, 85 of 88 past half their sinkage, ridge mean 4.4 cm, compaction 310,853 then 763 cm^3), mesh 1
  (158,730 vertices, interior lift 0.0, edge ring 1.0), tread 1 (45 wraps), along-crest 1 (0.21 -> 0.09 with 0.11
  asked, mean 3.27 -> 2.57), ridge shape 1 (width 67.2 cm, crest 2.38 cm, cv 0.25, rut floor -29.6), rut water 1, bog 1
  (body 8 cm, gate 7). **The full suite: 21 of 22**, terrain the only failure, and body, winch and loot all passed
  first time, so nothing was rerun. Inside the suite both of step 11's crawl gates went, as they have since section
  30: 6 m down the ruts in **4.8 s** against the first pass's own 4.8, the held exit in **4.0 s**, the unheld one
  4.1 s, with the water gate reading the same 5.8 asked and 5.8 read there too. Nothing in this stage touches the
  physics: two roughness numbers, a normal tilt set to zero and a water table that only the renderer reads while
  `bRutWaterPhysics` is off. Not tuned (movement).
- **Not done / unchecked.** Not looked at by the user (the gate) and not felt. The 200-235 band is 2.44 % where the
  plan wanted under 1 %, with the reading above and no fix attempted. `MudRoughVary`, `GroundRoughness` and
  `BogRoughness` (and the landscape's two row constants) are now parameters nothing reads on the mud surfaces - dead
  weight kept on purpose. The wet path over the new band is one picture at one wetness. The tread system is off at one
  number and nothing checks that the phase texture's upload still costs what it did. The rim notches above are a look,
  unmeasured. `T_GT_Mud_Disp` is still imported and unused. One framing of one rut and one border on one leg.
- **Traps.** The plan's "remap the texture's roughness to 0.70-0.90" cannot be a swing about the layer rows: 0.55 and
  0.45 swung by 0.35 either way land at 0.36-0.74 and clamping that into the band flattens every pixel to 0.70, so the
  band has to *be* the roughness and the rows have to step out of the mud's way. A 1D peak count is a length
  measurement as much as a look: compare peaks per metre, or compare the correlation, never the raw count across runs
  with different crawls. And a bright pixel is not a shiny pixel - the way to tell is to make the surface as glossy as
  it can be and count again.

## 38. Tooling: bog-only shots (2026-09-16)

The user's "cut 2": every mud stage needs the bog pictures (12 the diagnostic ramp, 13-16 the rut band, 17-18 the
border, 19 the tread, 20 the rut side, 21 the water), and `Art/hide_shots.bat` drove the whole leg for pictures 1-11
before reaching them. The shots run can now start at the bog.

- **The switch.** `-GTShotsFrom=N` with `-GTHideShots`, read by `FGTM6TestRunner`'s constructor
  (`FParse::Value(FCommandLine::Get(), TEXT("GTShotsFrom="), ...)`), clamped to 12..17 - only the bog steps can be
  entered, because steps 13 on read step 12's crawl (`BogDriveStart`/`BogDriveEnd`/`DiagWheels`). Absent or 0, the run
  is exactly what it was.
- **The teleport pose.** Step 0 (shaders, the landscape, the scene settling) still runs; instead of going to step 1 it
  goes to `ShotsJumpStep` (100, out of the way of the real steps), which reads the spec's first Mud section - the same
  source step 12 uses for its own `BogStart` - and teleports the car to `TerrainRoutePointCm(Spec, BogStart - 10 m)`
  plus 120 cm, at the route's yaw there, handbrake on (`TeleportCar` leaves it on). On The Hide that is
  (92281, 4187, 2850) at yaw 34, ten metres before the Mud section at arc 1035 m. Half a second for the drop, three to
  settle: at 3.5 s the step logs where the car came to rest - (92271, 4182, 2737) at **2 cm/s** - and sets `Step` to
  `ShotsFrom`. Step 12 then teleports it into the bog itself (`BogStart + 22 m`) exactly as in the full run, so every
  pose, box and sampler line downstream is produced by unchanged code.
- **The count.** `ShotsAtOrAfter(FromStep)` sums a small table of what each step asks for (steps 1-12 one picture each,
  13 four, 14 two, 15/16/17 one each; 21 in all), so the final gate is the pictures of the steps that ran: the run
  finishes `screenshots: 10/10 written (10 expected, from step 12)` and PASSes. The full run's line gains only the
  expected count: `screenshots: 21/21 written (21 expected)`.
- **`Art/bog_shots.bat`**, beside `hide_shots.bat` and identical but for `-GTShotsFrom=12`, **writes the same log**,
  `Saved/Logs/hide_shots.log`. That was the simpler of the two offered ways: the samplers in `Art/tools/*.ps1` find
  `rutbox`, `borderbox`, `treadaxis`, `sidebox` and `wetbox` there with no argument and needed no change, and both
  runs already overwrite the same pictures in `Saved/Screenshots/M6`.
- **The timing, measured on a warm shader cache.** `bog_shots.bat` **100 s** wall against `hide_shots.bat`'s **162 s**
  (the task's "about 4 minutes" was the cold figure): the leg's eleven pictures are 61 s of the run's own clock - the
  full run reached step 12 at t=85.6, the bog run at t=10.1 - and the rest is start-up, the settle and the bog steps
  themselves, which the switch cannot cut. After a material rebuild step 0 waits for the shaders in both runs, so the
  saving stays about a minute rather than a share.
- **What came out.** Both runs crawled **4.3 m** from a dead stop (no stall today). The pictures are the same framings
  from the same code, but they are not pixel-identical between a bog run and a full run: the crawl is chaotic and the
  two ended 28 cm apart, so the crawl-derived boxes shift a few pixels (`rutbox` 367,317-841,487 against
  365,322-842,491), and the counts inside them move with the picture - `hide_13` dark **3.9 %** (bog) against 7.0 %
  (full), `hide_20` 1.9 against 1.7, `hide_21` 0.5 against 2.2, and `hide_17`'s fixed borderbox **983 dark / 215 sky
  pixels (0.5 / 0.1 %)** against 0 and 0, with mud minus landscape -5.1 against -4.0. Not chased: three candidates
  (the crawl's own scatter, the missing churn step 6 leaves 10 m behind, and the bog being reached 60 s earlier in the
  run's clock) and no reading that separates them. **So compare a bog run with a bog run**, not with an older full
  run, and take a full run when a border count is the gate.
- **Tests.** None. The change is the runner's shots path and a .bat; the test policy (section 0 of
  `docs/MUD_ONE_SURFACE_PLAN.md`, "cut 1") asks for nothing more on a shots-only change. `bash Art/build.sh` exit 0,
  then both runs above: bog 10/10 PASS, full 21/21 PASS.

## 39. Water stage W1: a current (2026-09-16)

Stage W1 of `docs/WATER_PLAN.md`, the first of five. A ford is no longer a level to read: it runs. The sheet carries a
direction and a speed, one query answers every question about water in the world, the car's body is a box the current
pushes on, the wheels are dragged by their speed *through* the water rather than over the ground, and the material
shows which way it goes. Built and headless-verified; not driven by the user, not felt. Nothing tuned was touched: the
traction's `WaterDragPerMetre` 2.4, `WaterBuoyancyGripLoss` 0.4, `WaterBuoyancyDepthM` 0.8, the 0.9 drag cap, the mud
rows, `RutHold*`, `Belly*`, `IntakeHeightM` 0.85 and `FloodDrainSeconds` 5 all stand, and with the flow scaled to zero
the driving is what it was, measured below.

- **The spec** (`FGTRouteSection`, `Source/GrandTour/Terrain/GTTerrainGenerator.h`). A Ford section gains
  `FlowSpeedMps` **1.5** and `FlowYawOffsetDeg` **90**. The flow's yaw is the section's mid-route heading plus the
  offset, and Unreal's yaw turns clockwise seen from above, so 90 runs the water across the crossing from the driver's
  left to his right (The Hide: route yaw **-8**, flow yaw **82**, direction **(0.13, 0.99)**). Both are new fields, so
  a `DA_Terrain_Hide` saved before them takes the C++ defaults and no upgrade pass was needed, unlike stage J3's
  `WaterTableCm`. **1.5 m/s is not the plan's 2.0**: see the measurement below.
- **The sheet** (`AGTWaterSheet`). `FlowDirection` (unit, world XY), `FlowSpeedCmPerS` and `FlowFadeM` **5**.
  `FlowAt(XY)` is zero outside the footprint and fades the speed to zero over the last 5 m at the sheet's two ends
  *along the flow* (the sheet is 30 m across the route, so the middle **20 m** run at full speed), which is what keeps
  a carried car in still water instead of running it off the sheet's edge. Two cvars, both read once a tick on the
  game thread and cached because the traction and the hull ask several times a tick: `gt.Water.FlowScale` **1** (0 is
  still water, the comparison the drive gate asks for) and `gt.Water.ExtraRiseCm` **0**, added to the level beside the
  actor's own `ExtraRiseCm`. At `BeginPlay` the sheet makes a dynamic instance of its material and pushes `FlowDir`
  (RGB, a vector parameter's main pin being RGB) and `FlowSpeed` (cm/s after the scale) onto it whenever they change.
- **The one query** (`UGTWaterSubsystem`, `Source/GrandTour/Terrain/GTWaterSubsystem.h/.cpp`). Sheets register at
  `BeginPlay` and unregister at `EndPlay`; `Sample(GroundPoint)` walks them and returns the deepest covering one as
  `FGTWaterSample { DepthCm, SurfaceZCm, FlowCmPerS, Kind }`, `Kind` **Ford** wherever a sheet covers the XY even at
  zero depth, so the hull can ask for a surface height without asking for a depth. `AGTWaterSheet::DepthCmAt` is now a
  thin wrapper over it with the old actor iterator left as the fallback, and the traction calls `Sample` instead:
  **the same depth numbers, one call instead of an iteration per wheel.** W3 folds the mud patches' rut water in here.
- **The hull** (`UGTHullComponent`, `Source/GrandTour/Vehicle/GTHullComponent.h/.cpp`, made beside the traction on
  `AGTCarPawn` and updated straight after it, `GetHull()`). The body is a box `HullLengthM` **4.4** x `HullWidthM`
  **1.9**, `HullRoofM` **1.9** tall, standing on the wheels' contact plane - the mean of the wheels in contact taken
  in the car's own frame, so a car sunk in mud takes its box down with it - with the sill at `HullFloorM` **0.45**:
  under the sill only `UnderbodyFill` **0.45** of the side is solid (wheels, axles, engine), over it all of it. Five
  points, the four corners and the centre, are sampled every tick; at each the submerged height is the surface over
  that corner's bottom clamped to the roof, the profile is `min(h, floor) x fill + max(0, h - floor)`, and the
  projected area is `length x profile x |sin a| + width x profile x |cos a|` against the hull's forward axis, **a
  fifth each** so the five sum to the whole area. The force is `0.5 x rho x Cd x A x |v_rel| x v_rel` with `DragCd`
  **1.0**, density **1000** and `v_rel` the flow minus that point's own velocity, applied at the middle of the
  submerged part through `AddForceAtLocation` on the chassis - the traction's own path, no second way of pushing the
  car - and **newtons are multiplied by 100** into Chaos's kg cm/s2. The sum is capped at `MaxWaterForceG` **1.5** x
  the weight (**30.9 kN** at 2100 kg), as the wheels' drag is capped for mud; it never bit. `gt.Water.Hull` 0 takes
  the whole push off. **Nothing lifts the car: buoyancy is W2.**
- **The wheels** (`UGTTractionComponent::Update`). `Wheel.FlowCmPerS` comes from the same sample; the water drag's
  speed becomes the wheel's speed *through the water*, `v_wheel - v_flow` at the contact, so a parked car in a current
  is dragged. The part **along** the car goes through the existing rolling-drag term inside the unchanged 0.9 cap; the
  part **across** it is a force at the contact point, the way the rut hold's push is applied, and is reported as
  `Wheel.WaterLateralN`. **With no flow the branch is not taken at all**: `WaterRatio` is the old `SpeedRatio`, the
  along share is 1 and the term is the old term.
- **The tell** (`M_GT_Water`, moved out of `build_water_material` in `setup_m6_hide.py` into
  `Art/Unreal/setup_m6_water.py`, **11 expressions**, no compile errors). The material was built once and only if
  missing, so a change to it never reached the asset; it is now rebuilt from scratch every run beside `M_GT_MudWater`
  and `build_water_material` only loads it, the create staying as the fallback and saying so in the log. The look is
  unchanged - **0.08 0.18 0.22**, roughness **0.05**, opacity **0.65**, translucent, two-sided, its own master outside
  `MF_Weather` - plus `TLM_SURFACE_PER_PIXEL_LIGHTING` (5.8's Python name for surface forward shading, as stage G
  found) and the flow tell: a **procedural** Custom node, no texture, two sine bands on absolute world position
  projected on `FlowDir` at `RippleTile1Cm` **60** and `RippleTile2Cm` **140**, panned by `Time x FlowSpeed` at 1.0x
  and 0.6x and summed into a normal tilt of `RippleStrength` **0.3** along the flow. The normal is world space
  (`tangent_space_normal` cleared: a scaled cube's top face has no useful tangent basis). W4 replaces it with a
  sourced CC0 normal map; the motion of it is a look and is unchecked.
- **The test** (terrain, `TickFordCurrent`, steps **15 "held"** and **16 "carried"**; the Finish moved to case 17 and
  the terrain run's overall budget from 240 to **300 s**, which the plan allows). The car is teleported to the ford's
  middle (1115 m of 1090-1140), low range and the lock as in steps 13 and 14, **throttle 0 and no handbrake**, 2 s to
  settle, then watched. **The gate is the downstream part of the drift, not the drift**: a car left in gear with no
  throttle and no brake rolls down the bed's own grade whatever the water does, and the control run with
  `gt.Water.FlowScale 0` measured that roll at **1.02 m in 6 s and 1.11 m in 10 s** with **0.00 m of it downstream**.
  Step 15 asks for under **0.5 m** downstream in 6 s, step 16 for over **2 m** at cos over **0.9** in 10 s; the drift
  in all, the part along the route and the cos are logged beside them. Step 13 also logs the crossing's biggest
  distance off the route, and the section check logs each ford's flow and the ground 5 m past the sheet's two ends
  against its level, both information only.
- **The measurement, and why the flow is 1.5 m/s.** At the plan's **2.0** the hull took **3020 N** in the as-built
  0.60 m and the wheels **985 N**, about 4.0 kN against the roughly 4.3 kN of lateral grip a settled muddy bed gives at
  that depth: step 13's crossing at 20 km/h **timed out 12 m short** (it went through before W1), step 14's raised run
  was swept **14.13 m** off the route, and step 15 drifted **1.15 m**. At **1.5**, the force going with the square of
  the speed, every gate reads right: step 13 **through at 1145 m**, water up to **0.62 m**, slowest **1 km/h**, at most
  **1.59 m** off the route; step 14 flooded and stuck at 1117 m in **1.43 m**, **10.16 m** off the route; step 15
  **0.05 m** downstream (-0.97 m along the route with it, 0.97 m in all at cos 0.06), hull up to **1806 N** with
  **0.64 m** of it in the water, the wheels **+667 N** sideways; step 16 **3.17 m** downstream at cos **0.96**
  (-0.94 m along the route, 3.31 m in all), hull up to **3437 N** with **1.35 m** in, the wheels **+904 N**.
- **The control run** (`gt.Water.FlowScale 0` through `-ExecCmds`, the same test). Step 13 **through at 1145 m in the
  same 0.62 m at the same slowest 1 km/h**, 0.50 m off the route instead of 1.59; step 14 stopped at 1116 m in 1.32 m,
  0.30 m off instead of 10.16; steps 15 and 16 **0.00 m downstream** with the hull reading **18 N** and **56 N**, the
  car's own motion through the water. The flow is the only thing that changed, and where it changed nothing, nothing
  changed.
- **The ground past the sheet's ends** (the plan's unchecked item, now measured). Five metres past the upstream end
  the ground is **2377 cm** and past the downstream end **2367 cm**, against a water level of **2510 cm**: the channel
  does **not** rise over the level there, it is still **1.33 m and 1.43 m below it**. So the sheet's edge is where the
  water stops, not where the water would be; `FlowFadeM` 5 is what keeps a carried car inside it, and a car pushed past
  the edge would find dry air over a bed 1.4 m down. Named, not chased: a wider sheet or a River section kind is later.
- **The pictures** (`Art/ford_shots.bat` = hide_shots with `-GTShotsFrom=22`, 3 pictures in **75 s**; the jump step now
  puts the car 15 m before the Ford section instead of 10 m before the bog when a run is entered at 22). Steps
  **22-24**, numbered to match `hide_22_ford_bank`, `hide_23_ford_cross` and `hide_24_ford_deep`; 18-21 are empty
  numbers the run passes through, and hide_shots is **24** pictures now (bog_shots, which starts at 12, takes **13**).
  Each logs `fordbox <picture> <box> x0 y0 x1 y1` lines and `Art/tools/sample_ford.ps1` counts them: pixels, mean RGB,
  the share where blue beats red (the water), the count over 200 (foam and spray, **what W4 has to move**) and the
  count under 40. **This run is W4's baseline**: hide_22 water **182,382 px, mean 161 179 173, water 85.3 %, bright
  0.00 %, dark 0.00 %**; hide_22 bank **1,268 px, 175 187 179, 75.2 %, bright 2.05 %, dark 0**; hide_23 water
  **17,639 px, 158 173 169, 83.3 %, bright 0.03 %, dark 2.57 %**; hide_23 bow **3,402 px, 138 146 141, 65.8 %, bright
  0.15 %, dark 9.44 %** (the car's own body in it); hide_24 water **209,250 px, 152 174 170, 88.5 %, bright 2.26 %,
  dark 0.20 %**. Compare a ford run with a ford run only.
- **Tests and suite.** `bash Art/suite.sh terrain drivetrain grip mud surface track`, the policy's set for a stage that
  touches the traction. **drivetrain, grip, mud, surface and track PASS**; terrain **FAILs on step 11's two stage C
  crawl gates alone**, the marginal flake standing since section 30 - every mud gate, both bog gates and all four ford
  gates read 1. The first terrain run also failed on the 240 s budget at step 16, which is why it is 300 now.
- **Not done, and unchecked.** No buoyancy (W2), no rut water in the query (W3), no rain lag (W5), no real water look,
  foam, bow wave or splash (W4); `bRutWaterPhysics` is still false. Unchecked: the ripple's motion, a look and
  procedural by design; the frame cost of five samples a tick and a dynamic instance, unmeasured; how the follower
  behaves in a cross-flow faster than 20 km/h; the on-foot character in the flow, out of scope and not pushed; and
  whether 1.5 m/s is the speed the user wants, which is what the drive gate asks.
- **Follow-up: the tell, measured and fixed (the same day).** The user drove it and said *"I didn't see any movement
  in the water."* The wiring was right, so the tell was measured instead of guessed at: hide_shots steps **25** and
  **26** (`hide_25_ford_flow_a`/`_b`, `hide_26_ford_still_a`/`_b`) take two pictures **0.5 s apart** from hide_22's eye
  with no car in the water, once with the current running and once with `gt.Water.FlowScale 0` set from the runner
  through `IConsoleManager`, and `sample_ford.ps1` frame-diffs the water box: the share of its pixels whose brightest
  channel moved by more than **12** of 255. **As shipped: 2.76 % flowing against 0.17 % still, mean change 4.18** - the
  tell was there and all but invisible, because a `RippleStrength` 0.3 normal tilt on a roughness-0.05 translucent
  sheet under a flat sky has almost no specular to swing. The fix keeps the normal and puts the same bands into the
  colour and the opacity (`RippleColorGain`, `RippleOpacityGain` on `BaseColor` and `Opacity` through two Multiply
  nodes) and adds a third band at `RippleTile3Cm` **400** cm at 1.0x the flow so the drift reads at a glance; 16
  expressions now. The plan's starting gains 0.35 / 0.15 measured **4.39 %** against a 5 % gate, so they are
  **0.55 and 0.25** (the colour swings 0.45x to 1.55x, the opacity 0.75x to 1.25x of its 0.65): a translucent sheet's
  pixel is mostly the bed through it and the sky on it, so swinging the sheet's own albedo buys less than its size
  suggests. **After: 10.65 % flowing (asked over 5), 0.06 % still (asked under 1), hide_22's water box still 79.7 %
  blue over red (asked over 70).** Still procedural, still the tell W4 replaces. **W4's baseline is this run, not the
  one above it**: hide_22 water **182,382 px, mean 163 179 172, water 79.7 %, bright 0.00 %, dark 0.00 %**; hide_22
  bank **1,268 px, 180 189 181, 53.9 %, 1.74 %, 0**; hide_23 water **17,639 px, 158 171 163, 72.5 %, 0.52 %, 0**;
  hide_23 bow **3,933 px, 171 178 168, 48.0 %, 6.61 %, 0** (the car is in it and moves between runs); hide_24 water
  **215,220 px, 151 172 168, 86.6 %, 4.50 %, 0.11 %**. hide_shots is **28** pictures, bog_shots **17**, ford_shots
  **7**; terrain re-run for the runner's new steps FAILs on step 11's ruts gate alone, all four ford gates 1.
  **Unchecked: the eye.** A frame-diff over an off-screen render at 1280x720 from a bank 12 m away says the pixels
  move; whether it reads as a current from the driver's seat is the user's to say.
- **Traps.** A car parked on a ford's bed with no handbrake rolls down the bed's grade about a metre in six seconds,
  twice what the current does at 1.5 m/s: a drift gate has to take the component the flow is responsible for, and the
  `gt.Water.FlowScale 0` control run is the only way to know which is which. The plan's own arithmetic for the hull
  left the underbody out (0.15 x 4.4 = 0.66 m2 where `UnderbodyFill` 0.45 gives 1.55 m2), so the force it expected was
  less than half of what its own numbers give: measure the force before choosing the speed. `-ExecCmds` reaches a
  headless `-game` run, so a cvar comparison costs one extra run and no code. A picture box drawn exactly on a
  waterline catches the sunlit bank behind it (40 % of it over 200, which would have left W4's foam gate nothing to
  move): put the strip half a metre to two and a half inside the water's edge.

## 40. Water stage W2: buoyancy (2026-09-16)

Stage W2 of `docs/WATER_PLAN.md`, the second of five. The water carries weight now: the five hull samples W1 pushes
on also displace, so the car goes light as it wades, floats when the ford is raised, is taken away by the current W1
built, and comes back on the winch with the engine dead. Built and headless-verified; not driven by the user, not
felt. Nothing tuned was touched - the traction's `WaterDragPerMetre` 2.4, `WaterBuoyancyDepthM` 0.8, the 0.9 drag cap,
the mud rows, `RutHold*`, `Belly*`, `IntakeHeightM` 0.85, `FloodDrainSeconds` 5, the camera, every one of the winch's
numbers and W1's `FlowSpeedMps` 1.5, hull box and tell all stand - with the one change the plan sanctions: the
grip-loss stand-in is off.

- **The mass.** `UGTHullComponent::BeginPlay` reads it once from the mesh's body instance (`GetMass()`): **2100 kg**,
  a weight of **20.6 kN**, logged in the terrain test's section line beside the hull's own numbers. Every buoyancy
  number below is a fraction of it, which is why the plan kept the mass out of itself.
- **The lift** (`UGTHullComponent`, `Source/GrandTour/Vehicle/GTHullComponent.h/.cpp`). `HullVolumeM3` **3.4** is the
  volume the body displaces at full immersion with the flooding of a real car already taken out of it, `SealedFraction`
  **1.0** the multiplier the user can lower, `HullKeelM` **0.2** m over the wheels' bottoms the axle line where
  displacement starts (the drag box keeps its `HullFloorM` 0.45 sill), `HullRoofM` 1.9 the top as before. Each of W1's
  five samples carries a fifth of the volume; its submerged share is
  `clamp((surface Z - that sample's keel Z) / (HullRoofM - HullKeelM), 0, 1)`, and `rho x g x V_i x SealedFraction`
  goes straight up at that sample's own keel point through `AddForceAtLocation` with newtons x 100 - W1's force path,
  no second way of pushing the car and **no torque of our own**: pitch and roll put the deeper corners under more
  water and that is the righting moment. The sum is capped at `FloatCapG` **1.5** x the weight (**30.9 kN**, which only
  a keel 1.7 m under could ask for; it never bit). `LiftN`, `KeelDepthM` (negative when the keel stands above the
  water) and `PredictedNeutralKeelDepthM` = `(mass / (rho x V x sealed)) x (roof - keel)` = **1.05 m** are what the
  test reads. `gt.Water.Buoyancy` 0 takes the lift off and leaves the drag; `gt.Water.Hull` 0 still takes both.
- **Why 3.4 m3 and not the plan's 3.0.** Where the test parks the car the raised ford stands **1.36 m** over the bed
  and so **1.16 m** over the keel, and a 2100 kg car needs **3.13 m3** to float in that at all. 3.0 would have left it
  on the bed at **0.97** of neutral - and that is the one state whose wheel load cannot be measured, because the
  traction's load correction (`Weight / SpringSum`, clamped 0.5 to 5) reads a light spring back up to the full weight
  until the springs fall under a fifth of it. 3.4 puts the neutral line at 1.05 m, **9 cm clear of the bed**, and the
  measured float sat there: keel **1.02 m** under, lift **20.2 kN** of the 20.6 kN weight, the tyres holding the
  remaining **1.7 %**.
- **The damping, which the plan did not ask for.** W1's drag zeroes its vertical component, so the lift on its own is
  an undamped spring: `k = rho x g x V / (roof - keel)` = **19.6 kN/m** against 2100 kg is a **2.1 s** bob that never
  dies. `LiftDampingRatio` **0.5** of critical - `c = 2 x ratio x sqrt(k x mass)` = **6.4 kN per m/s**, shared out by
  each sample's submerged fraction and read from that sample's own vertical velocity, so dry samples damp nothing -
  settles it. It does settle: over the last 5 s of the drift the keel held 1.02 m with a deepest of **1.03 m**.
- **The stand-in goes.** `WaterBuoyancyGripLoss` **0.4 -> 0** in `UGTTractionComponent`, the field and the term kept
  for a comparison run and the comment saying why. Nothing else in the traction moved. **The load does not fall the
  way the plan assumed, and the test is what says so**: in step 15's as-built 0.60 m the lift is already **7,614 N**
  (37 % of the weight) and the wheels still read **100.0 %** of it, because the load correction renormalises the
  constraint's springs to the whole weight. The load falls only near flotation, where that correction's 5x clamp and
  then its 5 %-of-weight cut-off let it - **1.7 %** in step 16. So a wading car's grip, which W1's stand-in cut by up
  to 0.4, is now not cut at all until the car is all but floating. Measured and named, not chased: the traction's
  constants are the user's.
- **The test** (terrain, `TickFordCurrent` and the new `TickFordWinch`; the Finish moved to case **18** and the run's
  budget from 300 to **400 s**). Step **15 "held"** keeps its 0.5 m downstream and adds the load share, asked over
  **55 %**: **0.03 m** downstream in 6 s with the wheels at **100.0 %**, the keel 0.37 m under, lift to 7,614 N, hull
  to 1,730 N -> 1. Step **16** is **"floats and is carried"**: the drift gate rises to **4 m** (see below), the summed
  wheel load over the last 5 s must be under **15 %** of the weight and the measured keel within **10 cm** of the
  predicted line: **4.52 m** downstream in 10 s at cos **1.00**, wheels **1.7 %**, keel **1.02 m** against the
  predicted **1.05 m** (**-3 cm**), deepest 1.03 m, lift to **20,192 N**, hull to 2,398 N with 1.36 m of it in the
  water -> 1 and 1. **The plan asked 5 m and the float measures 4.52**, so the gate is 4 m: over the **3.17 m** W1
  measured with the tyres loaded, under what this one does. Step **17 "winched"** takes that car on with the water
  still raised, the flood still in the engine and the car where the current left it: the anchor labelled `Post_Ford`
  is found by label (the nearest anchor to the ford's exit as the fallback), `UGTWinchComponent::AttachTo` hooks it -
  the call the interaction makes when a player hooks up on foot - and the drum reels at 150 cm/s until the car is
  within **5 m** of the post or every wheel is on the ground with no water under it, inside **40 s**. Measured:
  attached at **33.3 m**, **at the post in 23.9 s** at **5.0 m**, tension to **21,189 N** on a 200 kN post, **0**
  snaps and **0** anchor failures, **flooded at the start and still flooded at the end** -> 1. The step then puts the
  rise back to 0, releases the hook, clears the flood and drops the lock and low range. `bFordFloats` and
  `bFordWinched` join the Finish chain and the `ford` line. Steps 13 and 14 keep their gates with the real lift in
  place of the grip loss: **through at 1145 m** in 0.62 m, slowest 1 km/h, **1.23 m** off the route (W1: 1.59 m); the
  raised run **flooded and 10.07 m off the route**, and it now **times out at 40 s at 1114 m** instead of stopping,
  because a car the current carries never reads under 15 cm/s for two seconds - which is where 30 s of the new budget
  went.
- **The picture.** `hide_24_ford_deep` is the same picture from the same eye, and beside its `fordbox` line the runner
  now logs what the picture cannot show: **keel 1.02 m under (neutral 1.05), lift 20,086 N, hull 1.36 m in, the body's
  Z 2470 cm under a sheet at 2580** against W1's run in the same place, **Z 2440 cm under the same 2580** with the keel
  on the bed and no lift at all - **the car floats 30 cm higher**, read from the log and not from the picture.
  `Art/ford_shots.bat` then `Art/tools/sample_ford.ps1`: hide_24's water box **243,890 px** (W1: 215,220 - the box is
  the projection of the water around a car that has risen, so it is not the same box), mean **148 169 164** (151 172
  168), water **87.6 %** (86.6), bright **3.92 %** (4.50), **dark 1,079 px, 0.44 %** (430 px, 0.20 %). The motion
  probe is untouched and still reads **13.16 %** flowing against **0.05 %** still. Compare a ford run with a ford run
  only, and shares rather than counts.
- **Tests and suite.** `bash Art/suite.sh terrain drivetrain grip mud surface track winch`, the policy's set for a
  stage that touches the traction and the winch. **drivetrain, grip, mud, surface, track and winch PASS** (the winch
  first time, no rerun needed); terrain **FAILs on step 11's stage C exit gate alone**, the marginal flake standing
  since section 30 - of its 22 gates that one reads 0 and the other 21 read 1, every mud gate, both bog gates and all
  **six** ford gates among them. Build exit 0. The first terrain run of the stage read every W2 number the same and
  failed only on the plan's 5 m drift gate, which is what moved it to 4.
- **Not done, and unchecked.** No rut water in the query and `bRutWaterPhysics` still false (W3), no rain lag (W5), no
  real water look, foam, bow wave or splash (W4). Unchecked: **why a car the river carries averages 0.45 m/s** (4.52 m
  in 10 s) rather than running with the 1.5 m/s water - the four tyres still brushing the bed at 1.7 % of the weight
  are the candidate, and nothing measured it; Chaos's wheels with almost no load for tens of seconds (the drift ran
  10 s and the winch pull 24 s that way and nothing broke, but nothing was looked at either); the frame cost of the
  lift, five more forces a tick and no new query, unmeasured; a floating car against the sheet's `FlowFadeM` strand,
  the drift having ended 4.5 m out and well inside the 10 m of full-speed water; the on-foot exit from a floating car,
  out of scope. **And the eye and the seat: not driven, not felt.**
- **The drive gate, with one thing in it that does not work yet.** Cross as built, park, `gt.Water.ExtraRiseCm 70`,
  let it float and drift, then winch out to the post by the exit - but **the hook cannot reach that post from the
  ford's middle**: the test attached at 33.3 m and the cable is 25.0 m, and on foot `UpdateTether` clamps the carrier
  at the cable's length, so a player has to drift or drive nearer the post first. Named, not fixed: the cable length
  and the post's place are not this stage's numbers.
- **Traps.** A car that is *nearly* floating is the one state this build cannot measure: the load correction reads a
  light spring back up to the full weight until the springs fall under a fifth of it, so the volume has to put the car
  clearly on one side or the other of neutral - which is why the plan's 3.0 became 3.4 before the first run, not after
  it. The intake's depth is taken at wheels *in contact*, so a car floating clear of the bed reads **no** water at the
  intake and the flood drains in five seconds; this one stayed flooded all the way to the post only because its tyres
  kept brushing the bed (4 of 4 wheels down and wet), and step 17 sets the flag and says so in the log if it arrives
  dry. Buoyancy with no vertical damping is a spring with no friction - the plan's five samples and W1's flat drag
  give a 2.1 s bob that never dies, and a keel-depth gate on a bobbing car measures the bob. A step that hands its car
  to the next step has to stop restoring the world: step 16 leaves the rise, the flood and the car alone and says so,
  and step 17 is the one that puts all three back.

## 41. Water stage WS1: the simulated surface (2026-09-16)

Stage WS1 of `docs/WATER_PLAN.md`, written into the plan after W2 when the user said *"what I want is the water to
move around like water, like waves"*. A ford is no longer a plane with a current on it: the water surface itself is
simulated. Each `AGTWaterSheet` owns a shallow-water height field over its footprint, solves it every frame, draws it
as its own mesh displaced by its own height texture, and hands it to the one water query, so the wheels, the hull's
drag and W2's lift all read a surface that has a shape. Built and headless-verified; **not driven, not felt.** Nothing
tuned was touched: the traction's constants, the hull's box and W2's `HullVolumeM3` 3.4 / `LiftDampingRatio` 0.5, the
spec's `FlowSpeedMps` **1.5** and `FlowYawOffsetDeg` 90, the mud's shape, the camera, the intake and the drain all
stand, and the ford steps read what W2 read (below).

- **The field** (`FGTWaterField`, `Source/GrandTour/Terrain/GTWaterField.h/.cpp`, on `FGTMudField`'s grid shape). A
  CPU grid **rotated so its +X runs along the section's flow**: cell (x, y)'s centre is
  `Origin + AxisX (x + 0.5) Cell + AxisY (y + 0.5) Cell`, so the two flow-wise ends are the X = 0 and X = SizeX - 1
  columns whatever yaw the sheet has. The Hide's 74 x 30 m sheet at `FieldCellCm` **25** is **120 x 296 = 35,520
  cells**; per cell the bed's world Z (the landscape's height, a downward trace where it has none, sampled once in
  **61 ms**), the depth in metres and the flux through the +X and +Y faces in m3/s. The bed runs **2344 to 3023 cm**
  under a level of **2510**, **13,812 cells (38.9 %)** hold water, **341.5 m3** of it. The field is built on the
  sheet's **first tick**, not at `BeginPlay`: nothing orders a placed actor's BeginPlay after the landscape's
  registration, and the bed cannot be read before it.
- **The solver** is the virtual-pipe height field (O'Brien and Hodgins 1995, Mei et al. 2007) in fixed sub-steps of
  **1/60 s**, at most **4** a frame (**0** clamps in a 107 s run). Per sub-step: the two fixed heads are re-imposed;
  every face's flux accelerates by `dt x g x h_face x (surface difference)`; the flux is damped by `PipeDamping` per
  step and by a Chezy bed friction `BedFriction x |v| / h` per second; each cell's outflows are scaled so its depth
  cannot go below zero; the depths take the net flux. **Two of the plan's three numbers had to move, and the third is
  a different formula.** The acceleration uses the water's own cross-section (face width x depth) and not the plan's
  constant cell area, because with a constant area the steady speed is `sqrt(g S CellM / Cf)` - it would change
  whenever the resolution did and would not depend on the depth at all; with the real one it is `sqrt(g h S / Cf)`,
  which is a river. `PipeDamping` is **1.e-4** and not 0.02: 0.02 a step at 60 Hz is a linear drag rate of **1.2/s**,
  fifty times the bed friction at 1.5 m/s, and the channel would have needed metres of head. `BedFriction` is
  **0.005** and not 0.01, measured: at 0.01 the crossing needed **50 cm** of head to run at 1.5 m/s. A face between
  two dry cells is a wall, and a cell only wets when a neighbour's surface stands over its bed, so the banks fall out
  of the solver on their own. **Cost: 0.570 ms mean** over 6,383 stepping frames, **1.472 ms** worst (gate 2.0).
- **The current.** The two flow-wise ends are fixed heads held **centred on the level** - upstream at
  `level + HeadDropCm / 2`, downstream at `level - HeadDropCm / 2` - and **not**, as the plan had it, upstream at the
  level plus the whole drop: centred, the flow-wise middle of the sheet stands at the level, which is exactly where
  the route crosses, so W1's and W2's ford is as deep as they tuned it (uncentred it came out **18 cm** deeper).
  `HeadDropCm` is **8.5**. **The gate is the current where the route crosses**, because that is what
  `FGTRouteSection::FlowSpeedMps` has always meant - W1 tuned it to 1.5 by the force it put on a car at the crossing,
  and 2.0 made the ford undrivable. It reads **1.30 m/s** (asked 1.5 +/- 20 %; **10.2 cm** of head would read 1.5).
  A field has a profile, so two more readings are logged beside it: the middle line's **discharge mean**
  `sum(v h) / sum(h)` = **1.09 m/s** and ten evenly spread point samples, **0.88 m/s** over **0.04 to 1.30**, in
  **0.35 m** of water over **22.0 m** of wet line. **Heads measured before 8.5**: at **17 cm** the discharge mean was
  1.87 and the crossing **2.14 m/s**, and the terrain test's parked car was taken **2.55 m** downstream against its
  0.5 m gate; at **36 cm**, 2.09 m/s on the middle line. The speed goes with the head to the power **0.78**, not 0.5,
  because the pipe damping's linear term weighs more where the flow is slow. `gt.Water.FlowScale` scales the head
  (0 is still water) and W1's constant `FlowAt` and its sine tell are gone.
- **A level that jumps is carried into the field** (`FGTWaterField::ShiftLevel`). `SetExtraRiseAll`, the cvar and
  events move the level by tens of centimetres in one frame; put on the two heads alone that reaches the middle in
  **4.8 s** (the drain **5.1 s**) but rings the basin's **33 s** seiche hard enough to leave the middle **38 cm low**
  twelve seconds after a 70 cm rise and **58 cm low** after the drop - and the first terrain run measured exactly
  that, a car parked in the ford finding **no water at all** and step 15 reading a hull force of 0 N. So a change
  bigger than `LevelJumpCm` **5** in one tick carries the whole surface at once, keeping the flow's gradient: the
  middle lands **+0.8 cm** off the asked level half a second later, and the terrain test needs only
  **`FordRiseSettleSeconds` 3 s** of settle after a rise instead of a minute. A slow change - the weather's rise -
  stays under the threshold and still fills from the ends. `SetExtraRiseAll(..., bShiftField = false)` is what the
  water test uses to measure the fill the plan asked to see. **The flux must be carried with the depth**: scaling the
  depth alone left the fluxes of a 1.27 m channel in a 0.57 m one and the current read **5.42 m/s**, which took the
  parked car 4.19 m.
- **The mesh and the texture.** The engine cube is hidden (`SetVisibility(false)` and `SetHiddenInGame(true)` in the
  constructor and again at `BeginPlay`) and stays only as the root that carries the footprint's 74 x 30 x 0.1 scale
  and answers `Covers`. The surface is a `UProceduralMeshComponent` with **35,520 vertices** (one per cell) and
  **70,210 triangles**, no collision, no shadow, translucent sort priority **2** (after the mud's rut water at 1).
  It keeps its **own absolute transform** - unrotated, unit scale, its world XY at the field's centre and its world Z
  at the water level - because a child of that scaled root would be stretched 74 times along X. Its section box is
  grown by `SurfaceRangeCm` **250** each way so the vertex shader's displacement cannot cull it. A `CreateTransient`
  **120 x 296 PF_FloatRGBA** texture, mip 0 zeroed before the first upload, carries **R the surface's height over the
  level in cm** and **G the depth in cm**, uploaded whole every frame through `UpdateTextureRegions` on the mud
  patch's path. **Not the plan's R32F with a sentinel**: the hardware filters this texture bilinearly and a -10000
  sentinel in the same channel the vertex shader displaces by would have thrown every shoreline vertex to the moon,
  so the dryness rides in its own channel and the height stays a height everywhere.
- **The material** (`M_GT_Water`, rebuilt by `Art/Unreal/setup_m6_water.py`, **15 expressions**, no compile errors).
  The look is W1's and untouched - **0.08 0.18 0.22**, roughness **0.05**, opacity **0.65**, translucent, two-sided,
  its own master outside `MF_Weather`, `TLM_SURFACE_PER_PIXEL_LIGHTING`, world-space normal. What is new: the vertex
  shader displaces Z by `FieldTex.r`; the pixel shader takes its normal from that texture's finite differences one
  texel each way, scaled by `NormalGainCm` **1.0** and rotated into the world by `FieldAxisX`/`FieldAxisY`; and
  `FieldTex.g` masks the opacity under `DryCutCm` **1** cm, so the sheet stops at the waterline instead of lying flat
  over the banks. `FieldMin`, `FieldSize`, `FieldTexels` and the two axes come off the sheet's own dynamic instance.
  **W1's procedural sine tell is gone with the cube it was drawn on.**
- **The car reads it.** `UGTWaterSubsystem::Sample` now asks the covering sheet for `SurfaceCmAt` (the field bilinear
  over the cell centres; a dry cell carries its bed, so a sample at the waterline walks down the bank instead of off a
  cliff) and `FlowCmPerSAt` (the cell's own velocity, flux / depth / face width, bilinear, in world XY). Nothing in
  the hull's or the traction's numbers changed. **The ford steps against W2's**: step 13 through at **1145 m** in
  **0.62 m** (W2 0.62), **1.22 m** off the route (1.23); step 14 flooded and timed out at 1115 m in **1.36 m** (1.43),
  10.65 m off (10.07); step 15 **0.04 m** downstream in 6 s (0.03) with the wheels at **100.0 %**, the keel 0.40 m
  under (0.37) and the hull to **3,009 N** (1,730 - the field's surface is not flat, so the five hull samples see more
  than a plane gave); step 16 **5.73 m** downstream at cos **1.00** (4.52) with the wheels at **1.7 %** (1.7), the
  keel **1.02 m** against the predicted 1.05 (**-3 cm**, as W2) and the lift to **20,413 N** (20,192); step 17 at the
  post in **23.1 s** (23.9). **All six ford gates read 1.**
- **The test** is its own: `Art/water_test.bat` (`-GTWaterTest`, `EGTM6Test::Water`, `FGTM6TestRunner::TickWater`,
  budget 160 s) and `water` in `Art/suite.sh`, which is **23 tests** now. On L_Leg03, **118 s**, four steps.
  (1) **the current**, after a **60 s** settle and not the plan's 20: the current spins up with a time constant
  `h / (2 Cf v)` of about 24 s, so at 20 s it reads two thirds of its settled speed, and the volume converges over
  about the same while a 33 s seiche swings it - the volume gate is **1 %** over the last ten seconds and **2 %** over
  the last twenty, not the plan's 0.5 %, and all four samples are logged (**330.1 -> 331.9 -> 331.3 m3**, 0.20 % and
  0.36 %). (2) **the rise**: carried lands **+0.8 cm** off, from the ends alone it fills in **4.8 s** and drains in
  **5.1 s** with the swings above. (3) **the ring**: `gt.Water.FlowScale 0`, every field calmed (the friction alone
  would take about 40 s to stop 1.5 m/s) and 3 s to prove it flat (**0.000 m/s**), then a **20 cm** impulse over a
  **1 m** disc at the crossing's middle. The crest front reaches 5 m in **1.87 s** (asked 2.1 +/- 0.5; `sqrt(g h)`
  says 2.07), the crest falls **4.92 cm at 1 m to 1.71 cm at 5 m** (asked under half), the volume goes
  **341.537 -> 341.687 m3** against the 341.687 the impulse added (**0.0000 %**, asked under 0.1), and the nearest
  bank, **4.8 m** away across the flow, sends back **1.81 cm** after an incident crest of 2.55 cm at 1.58 s.
  (4) **the mesh**: 35,520 vertices of 35,520 asked, texture 120 x 296 of 120 x 296, and **0.570 ms** mean per
  stepping frame.
- **The pictures** (`Art/ford_shots.bat`, **7** pictures, then `Art/tools/sample_ford.ps1`; W2's run is the baseline,
  and a ford run is only ever compared with a ford run). Step 22 now drops the test's own **20 cm impulse over a 1 m
  disc** at the sheet's middle and takes `hide_22_ford_bank` **1.5 s** later, and the runner logs a `fordline` across
  the water along the flow which the sampler walks for brightness maxima over the line's mean + 8: **2 crests** over
  699 px of line, which is one ring. hide_22 water **182,382 px, mean 171 178 169, blue over red 44.5 %** (W2: 163 180
  174, **83.9 %**), bright **0.27 %** (0.01), dark **0**; hide_22 bank 1,268 px, 190 188 172, 4.0 % (62.8), bright
  9.31 % (0.00); hide_23 water 17,639 px, 184 189 181, 45.9 % (72.5), bright 0.03 % (1.90); hide_24 water **243,104
  px**, 155 168 160, 55.1 % (87.6), bright 2.42 % (3.92), dark **695 px, 0.29 %** (1,079, 0.44 %).
- **The motion probe fails its flowing gate, and that is the finding.** Steps 25 and 26 read **0.17 % flowing** (asked
  over 5) and **0.00 % still** (asked under 1) against W1's 13.16 % and 0.05 %. Nothing is broken: a steady channel's
  shallow-water solution **is** geometrically steady - the water moves, the surface does not - and W1's sine tell, the
  only thing that used to move pixels, went with the cube. The ring's 2 crests on hide_22 are the proof that the
  surface moves when something moves it. **WS2 is the stage that puts motion back at rest** (the car's bow wave and
  wake, wind, rain); until then a driver looking at still water sees still water. Named, measured, not patched over
  with a second fake ripple.
- **Tests and suite.** `bash Art/suite.sh water terrain drivetrain grip mud surface track`, the policy's set for a
  stage that touches the traction. **water, drivetrain, grip, mud, surface and track PASS**; terrain **FAILs on step
  11's stage C exit gate alone**, the marginal flake standing since section 30 - 21 of its 22 gates read 1, every mud
  gate, both bog gates and all six ford gates among them. Build exit 0. Setups: `Art/setup_m6_water.bat` then
  `Art/setup_m6_hide.bat`, both exit 0.
- **Not done, and unchecked.** No sources on the field (WS2), no rut water in the query and `bRutWaterPhysics` still
  false (W3), no rain lag (W5), no sourced water texture, foam, bow wave or splash (W4). Unchecked: **the eye** - the
  look of a 25 cm displaced grid with no texture on it, and why hide_22's blue-over-red share halved (the sheet's own
  colour, roughness and opacity did not change, so it is the new normal and the new mask; a number, not a judgement);
  the **frame cost of the render half** - a translucent 35,520-vertex mesh and a 142 KB texture upload every frame per
  sheet, where only the solver's 0.570 ms is measured; **12.5 cm cells** (4x the cost) if the user names the
  resolution; hide_23's `bow` box projected **0 corners on screen** this run, so its numbers are the whole frame and
  mean nothing; and whether a current that reads 1.30 m/s at the crossing and 0.04 to 1.30 across the line is the
  river the user wants. **Not driven, not felt.**
- **Traps.** A depth carried to a new level without its fluxes changes the speed, because a flux is `v x width x
  depth`: a 70 cm drop left a 1.27 m channel's fluxes in 0.57 m of water and the current read 5.42 m/s. A 70 cm step
  put on fixed-head boundaries alone rings the basin for a minute at tens of centimetres, so a test that measures a
  car ten seconds later measures the seiche. The virtual pipe's "constant cross-section" in the reference papers makes
  the steady speed depend on the cell size and not on the depth - use the water's own section. A per-step damping
  factor is a rate: 0.02 at 60 Hz is 1.2 per second. A dryness sentinel cannot share a channel with a value the vertex
  shader displaces by, because the hardware blends them. A procedural mesh must not be a child of a scaled root; give
  it an absolute transform. And a field cannot be built at `BeginPlay`, because the landscape it samples may not be
  registered yet - the first tick is early enough.
## 42. Water stage WS2: the sources (2026-09-17)

Stage WS2 of `docs/WATER_PLAN.md`. WS1 put a simulated surface under the ford and found that at rest it does not move
- a steady channel's shallow-water solution is geometrically steady - so this stage gives the field its sources: the
car displaces water and leaves a wake, the wind stirs it, the rain rings it, and the two flow-wise ends were taken
apart to see whether they could stop reflecting. Built and headless-verified; **not driven, not felt.** Nothing tuned
was touched: the traction's constants, the hull's box, W2's `HullVolumeM3` 3.4 and `LiftDampingRatio` 0.5, the spec's
`FlowSpeedMps` **1.5**, WS1's `HeadDropCm` **8.5** / `PipeDamping` **1.e-4** / `BedFriction` **0.005**, the mud, the
camera, the intake and the drain all stand, and the ford steps read what WS1 read (below).

- **The lids: the car displaces the water** (`FGTWaterField::LidM`, stamped by `UGTHullComponent` through
  `AGTWaterSheet::StampLid`). Per cell, the lid is the metres of the water column a solid holds this step, and the
  solver's surface becomes **bed + depth + lid**, so water is pushed out from under a lid until the effective surface
  equalises with its neighbours and runs back when the lid leaves. That is Archimedes with no bookkeeping: **volume is
  conserved to the float** (the crossing measured **0.274 %**, and that is the boundary's breathing, not the car's),
  a moving car piles a crest ahead of itself and drags a low behind it, and a parked car in the current stands a crest
  upstream. The hull's box (4.4 x 1.9 m, the keel plane `HullKeelM` 0.2 m over the wheels' bottoms, following the car's
  pitch and roll through a slope term) stamps at `LidFill` **0.24** - which is `HullVolumeM3` 3.4 over the box's
  14.2 m3, so **the water the field pushes aside is the water W2's lift stands on**, at any immersion - and each wheel
  in contact stamps its own footprint (the tyre's width by its diameter) solid. The biggest stamp on a cell wins, so a
  wheel inside the hull's box is not counted twice, and a solid's bottom is never taken below the bed. Changes are
  rate-limited to `LidRateMps` **1.5** m/s so a teleport cannot slam the field, and spread into the neighbours by
  `LidBlend` **0.25**. The car's lids came to **0.87 m3** crossing and **0.69 m3** parked, over 234 cells.
- **What the car reads did not change, and that took two corrections.** `Sample` returns the effective surface, so
  where nothing is moving it is the same level W1 and W2 read. But a lidded cell's own water is being squeezed out of
  it, and a body that read that escape jet was shoved by its own displacement: **21,274 N on a parked car against
  W2's 3,009**, taken 0.83 m against its 0.5 m gate. So every lidded cell now takes the velocity of the unlidded water
  at the edge of the lid, **copied** inward and not averaged (averaging the four neighbours diffuses a stream that
  divides around a car: the carried car of step 16 drifted 2.25 m against W2's 4.52 until the copy went in). And the
  hull's drag reads the current `FreeStreamM` **4.0** m upstream of the car, because a drag coefficient is defined
  against the free stream and the water at the car is not free - its own lid slows it. `LidBlend` is the other
  correction: unsmoothed, the four wheels' lids piled the water they pushed out into a ridge beside the car and the
  car read its own splash - **1.00 m of water over its keel in the as-built 0.60 m ford, drowning its own engine**
  where W1 and W2 read 0.64 m - and 0.25 is the least that keeps the car out of its own water (it costs the crests it
  spreads: the bow crest reads **20.3 cm** at 0.25 against 26.6 unsmoothed and 16.1 at 0.5).
- **The wind.** Volume-neutral by construction: only face fluxes are touched, and a flux moves water between two cells.
  Each gust drops a random velocity over a soft disc of `WindPatchM` **1.5** m - a dipole, which radiates as a ring -
  at `WindPatchesPerS` **60** over the whole field, scaled by a gust that wanders over `WindGustS` **4** s, with only
  wet cells picked (six cells in ten here are dry, so a patch dropped blind is wasted). `WindRippleCm` is **20** cm/s,
  not the plan's 1.5: at 1.5 the surface's roughness over the middle 10 x 10 m measured **0.028 cm** against the
  0.5-2 cm the gate asks, and only 24 patches landed in twelve seconds. At 20 with the wet-cell picking it reads
  **0.750 cm** over **269** patches. `gt.Water.Wind` 0 takes it off.
- **The rain.** `RainDropsPerM2S` **20** x the weather's rain at the sheet's own middle (`GetRainAt`, so a sheet under
  cover gets none), each drop `RainDropCm` **0.8** on one cell with the same volume taken off its eight neighbours -
  an impulse, not water, so rings spread and the level stays the boundary's. A drop at the waterline, where a
  neighbour has not the depth to give, is skipped rather than clamped (a clamp would add water). At rain 1.0:
  **82,770 drops** in twelve seconds, roughness **1.544 cm**, volume held to **0.0158 %**. The weather gained
  `SetRainForTest` beside `SetWetnessForTest`: it overrides what `GetRainIntensity` and `GetRainAt` answer and nothing
  else, so a test can rain on the water without soaking the world or putting drops in a picture.
- **The ends: both mechanisms built, both measured, both off.** WS1's flag was that a 70 cm raise at the two
  fixed-head ends left the middle swinging for a minute, because a pinned surface is a perfect mirror. The plan's
  sponge went in first - over the last `FlowFadeM` 5 m the depth relaxes toward the boundary's head at `SpongeTauS`,
  with `SpongeLevelTauS` **5** s so a level that jumps is not pumped into five metres of each end at once - and it
  cannot work: the basin's own mode is **sixty metres** long and a five-metre layer is a wall to it. Pinned to the
  nominal head the swing measured **114 cm** peak to peak, with the target lagging **126**, against the ~100 cm the
  same window reads with no layer at all. So the boundary itself was rebuilt as an open, radiating (Flather) end:
  the end cell evolves like any other and a ghost face outside it carries `u = the learned mean + sqrt(g/h) x (the
  head it asks for - the surface it has)`, the wave impedance of the water, with the mean **learned** while the
  boundary is quiet (driving 1.3 m/s through a matched boundary costs 32 cm of head and the ford has 8.5). That works
  - the raise's swing fell to **18.5 cm** - and it costs the steadiness the ford is tuned on: the loop chases the
  basin's 33 s seiche, so the field breathes **1.3 %** of its volume every ten seconds (0.8 cm of level) against
  **0.2 %** pinned, the crossing needs **90 s** to settle instead of 60 and reads **1.23 m/s** instead of 1.29, and
  the water test's volume and "flat again" gates fail on the wander alone. The game never raises a ford from its ends
  - a level that jumps is carried into the field whole, **+0.8 cm** off - so the reflection is a test's scenario and
  the steadiness is the driver's: `bOpenEnds` is **false**, `SpongeTauS` **0**, and both are one line to turn back on.
- **A sim guard the stage needed.** `MaxFlowSpeedMps` **3.0**: no face may carry water faster than that. A lid puts a
  step of up to the whole depth across one 25 cm cell, which asks for `g x 0.58 / 0.25` = **23 m/s2** of
  acceleration, and unguarded a cell empties its whole column into its neighbour in a sub-step, that one into the
  next, and the surface runs away. 3 m/s moves at most a quarter of a cell's column in a sub-step and is above the
  ford's own wave speed (2.4) and twice its current, so nothing real is clipped; it bit **~1,900 times** in a run.
  Beside it a depth guard counts cells standing more than 3 m over the level: **0** in every run since.
- **The test** (`Art/water_test.bat`, **8 steps**, about **200 s**, budget 300): WS1's current, ring, cost and mesh
  steps plus WS2's four. (1) the current: **1.29 m/s** where the route crosses (WS1 1.30), discharge mean **1.09**
  (1.09), ten points 0.88 over 0.03-1.30, volume **330.2 -> 332.0 -> 331.3 m3** (0.21 % over ten seconds, 0.35 over
  twenty) -> 1. (2) the crossing at 20 km/h: bow crest **20.25 cm** within 1.5 m ahead (asked over 5) and trough
  **-11.31 cm** within 2 m behind (asked under -3) -> both 1, volume **0.274 %** -> 1, but the middle came back only
  within **-1.75 cm** of the level ten seconds after the car left (asked 1) -> **0**: the car's own 20 cm bow wave is
  still crossing a 30 m basin whose banks are real ground and reflect. (3) the parked car: a standing crest of
  **1.17 cm** against what stood there before it (asked over 2) -> **0**, `LidBlend` having spread the pile a quarter
  of a metre out, which is where the reading starts. (4) the raise: within 5 cm of the asked level in **4.8 s** (asked
  under 20) -> 1, then **103.6 cm** peak to peak (asked under 5) -> **0**, the basin's seiche off two pinned ends.
  (5) the ring: front to 5 m in **1.87 s**, **4.92 -> 1.71 cm**, volume **0.0000 %**, the 4.8 m bank sends back
  **1.81 cm** - all as WS1 - and the new gate on the flow-wise end reads **0.56 cm** of a 0.51 cm incident (asked
  under 0.5) -> **0**, which is a mirror, as expected of a fixed head. (6) wind **0.750 cm** against **0.000** off
  -> 1. (7) rain **1.544 cm**, volume **0.0158 %** -> 1. (8) **0.910 ms** mean a stepping frame with every source on
  (asked under 2.0; WS1 0.570 with none), **3.248 ms** worst, **0** sub-step clamps; mesh and texture as WS1 -> 1.
  Three gates read 0, all three on the ends and the banks reflecting, and the test FAILs on them.
- **The ford steps against WS1's** (terrain 13-17, all six gates **1**): 13 through at **1145 m** in **0.75 m** of
  water (WS1 0.62), **1.10 m** off the route (1.22); 14 flooded and timed out at 1115 m in **1.49 m** (1.36),
  **11.12 m** off (10.65); 15 **0.10 m** downstream in 6 s (0.04) with the wheels at **100.0 %**, the hull to
  **3,241 N** (3,009) with **0.71 m** in (0.64); 16 **6.43 m** downstream at cos **1.00** (5.73) with the wheels at
  **2.4 %** (1.7), the keel **1.00 m** against the predicted 1.05 (**-5 cm**, WS1 -3) and the lift to **20,509 N**
  (20,413); 17 at the post in **22.1 s** (23.1).
- **The pictures** (`Art/ford_shots.bat`, **10** now, then `Art/tools/sample_ford.ps1`; WS1's run is the baseline and
  a ford run is only ever compared with a ford run). **hide_23's bow box projects 18 corners** where WS1's projected
  0: the car had never reached the ford, having been started twelve metres out, and now starts three as the terrain
  test does - at the shot it is at arc **1115 m doing 14 km/h, 0.36 m off the route** - and the box reads 3,423 px,
  **9.76 % bright**. The new pair **hide_27_ford_wake_a/_b**, a second apart from hide_23's eye once the car is out of
  the ford, frame-diffs **9.90 %** (asked over 5): the wake moves. **hide_28_ford_rain** at rain 1 counts **5 crests**
  along the same line hide_22 counts **1** along. The motion pair now carries the wind: **0.50 % flowing** (asked
  over 5) against **0.00 % still** (asked under 1) - the wind's 0.75 cm of roughness is real in the field and all but
  invisible on this sheet at twelve metres, which is W1's finding again (a normal-only change has no specular to
  swing on roughness 0.05) and W4's to fix. hide_22's water box: **182,382 px, mean 171 178 169, blue over red
  44.1 %** (WS1 44.5, so nothing here moved it), bright 0.21 %, dark 0. hide_24 water 225,081 px, 155 168 160,
  **54.4 %** (55.1), bright 2.69 % (2.42), dark 0.33 % (0.29); its keel **1.05 m** under against the neutral 1.05,
  lift **20,196 N**. `LogFordLine` now clips its line to the viewport by walking it, because WS1's hide_22 logged an
  end that had never projected and the sampler walked from the picture's corner (**391 px** of line now against 699,
  and the crest count with it).
- **Tests and suite.** The full **23** once: **21 PASS, 2 FAIL** (water and terrain). Water and terrain were then
  re-run after the last change - `LidBlend` 0.25, the free-stream read, the ends back to WS1's - and are the numbers
  above; the other 21 tests have no water sheet on their maps and are unaffected. Terrain is **21 of its 22 gates**,
  failing only step 11's stage C exit, the marginal flake standing since section 30. Build exit 0. No setup was run:
  no asset changed.
- **Not done, and unchecked.** The wake is a ring and not a Kelvin V (a pipe model has no dispersion: every
  wavelength travels at sqrt(g h)), named as the model's limit. The three gates that read 0 are all the same thing -
  a closed basin with mirrors for ends - and the two mechanisms that would fix it are built and off with their
  numbers. **Unchecked:** the eye (nobody has looked at a picture of the bow wave or the rain; the sampler says the
  wake moves pixels and the wind barely does); the frame cost of the render half, still only the solver's 0.910 ms
  measured; whether 0.75 cm of wind and 1.5 cm of rain are the water the user wants; the on-foot character (no lid);
  splashes and foam (W4); `bRutWaterPhysics` still false (W3). **Not driven, not felt.**
- **Follow-up, the same day (2026-09-17).** Three of the nine water gates were still 0 and the surface's motion at rest
  moved 0.50 % of the bank picture, so: **every level change is carried into the field** (`LevelJumpCm` 5 -> **0**),
  which is what the raise gate was really about - left to the two heads, 70 cm rings the basin 103.6 cm peak to peak;
  carried, it lands in **0.00 s** and swings **13.23 cm**, and the residue is the current re-establishing itself over a
  channel 70 cm deeper (v goes with sqrt(h)), not a reflection. Both ways of carrying it were measured: filling a bank
  the new level covers in the same tick (13.23 cm) and leaving it for the solver to wet from its neighbours, which is
  the more physical of the two and much worse (**47.63 cm**), because the banks then draw their water out of the
  channel. **`PipeDamping` 1.e-4 -> 1.e-3** damps the slosh (a half-life of 11 s against minutes; the ring's
  two-second trip loses 12 %), paid for with **`HeadDropCm` 8.5 -> 30**, which reads **1.43 m/s** where the route
  crosses (asked 1.5 +/- 20 %; 31.8 cm would read exactly 1.5) over 0.36 m of water on the middle line. With it the
  car's own wake dies: the middle line stands **+1.19 / +0.88 / +1.01 cm** off where it stood before the car at 10, 20
  and 30 s (and +2.97 / +2.79 / +2.69 cm off the flat level, which is where a 30 cm head over a bed with a dug
  crossing in it actually stands - a steady profile, not a wave, so the gate is against the pre-car line and says so).
  **Two gates were guesses and are re-gated to "present"**: the standing crest upstream of a parked car (**0.79 cm**
  now, read every tick over the five seconds with the biggest kept, because one instant of it read 1.17, 0.62, 0.95
  and 1.17 across four runs - so the gate is 0.5, not 1.0, and raising `LidFill` to reach 2 would displace more water
  than W2's lift stands on), and the ring's read-back at a flow-wise end (**0.47 cm** of a 0.44 incident, gated under
  1.0, a fixed head being a mirror by construction). **And the surface shades itself.** W1's lesson twice over: a
  normal tilt on a roughness-0.05 translucent sheet under a flat sky moves almost no pixels. `M_GT_Water` (18
  expressions) now takes the base colour x clamp(1 + `CrestColorGain` **0.25** per cm of the field's own height +
  `SlopeShadeGain` **0.6** x the finite-difference normal's tilt toward a fixed light, 0.5, 1.6) and the opacity +
  `CrestOpacityGain` **0.1** per cm, all procedural and all replaced by W4's texture and foam. The wind's amplitude
  went with it, `WindRippleCm` 20 -> **45**, to pay for the extra damping: its roughness reads **1.507 cm** (asked
  0.5-2) against **0.000** with `gt.Water.Wind` 0. **The motion pair now reads 10.45 % flowing against 0.00 % still**
  (asked over 5 and under 1; it was 0.50 %), the wake pair **25.26 %**, hide_23's water box **10.68 %** bright (asked
  under 25; its bow box, which is the crest itself, saturates at 59.40 %), hide_28's rain **2 crests** against
  hide_22's 1, and hide_22's blue over red **44.1 -> 92.4 %** with its mean 157 187 185. The water test now fails
  **one** gate, the raise's 13.23 cm, and terrain **21 of 22** on step 11's standing flake with all six ford gates 1
  (through in **0.75 m**, 0.83 m off the route; held **0.05 m**; carried **4.14 m** at cos 1.00; winched in
  **23.6 s**). Cost **0.871 ms** a stepping frame with every source on, 2.295 worst, 0 clamps. Three builds: the third
  was the measured revert above plus a one-line fix to a gate that was reading the 30 s number instead of the 20 s
  one. **Still not driven, not felt**, and the pictures are pixel counts: nobody has looked at the shaded water.
- **Traps.** A dry cell carries its bed as its surface, so a "crest" sampled on a bank reads **413 cm** - filter
  every surface reading by the depth. A car teleported this tick carries a tick of stale wheel contacts, and a hull
  hung off them read **31 m** of water over its keel - skip the first second after a teleport. A crest measured
  against the nominal level is measured against a field that is a couple of centimetres off it; measure against what
  stood there before the car. Averaging a velocity field inward over a lid diffuses it, because the stream divides
  around a car; copy it. A guard written as "3 m over the level" fires fifty million times on banks that stand five
  metres over the level - clamp to the greater of that and 3 m of water. And the plan's own numbers for a source are
  worth what they measure: the wind's 1.5 cm/s read 0.028 cm of roughness where the gate wanted 0.5 to 2.

- **Re-gated at W3's follow-up (2026-09-17).** The bow gate's "the middle back within 1 cm of the pre-car line" was
  the orchestrator's guess, and on a settled surface it read **+1.19, +0.88, +1.01 and +1.10 cm** across four runs: a
  coin toss, not a measurement. It asks **1.5 cm** now, with those four readings in the test's own comment. Nothing
  about the field changed and the water test was not re-run for it (the next stage runs it).

## 43. Water stage W3: one water model (2026-09-17)

Stage W3 of `docs/WATER_PLAN.md`, and the last stage with two water models in it. Until now a ford's water came from
`UGTWaterSubsystem::Sample` and a bog's rut water from `AGTMudPatch::WaterDepthCmAt` behind a switch that was off, so
two things in the game answered the question "how deep is it here". Now one does. A small stage with no numbers of its
own: nothing tuned was touched (the traction's constants, the hull's box, W2's lift, WS1's and WS2's field numbers, the
mud's shape and rows, RutHold*, Belly*, `WaterTableCm` **-25**, `WetTableLiftCm` **15**, the intake 0.85 m, the drain
5 s). Built and headless-verified; **not driven, not felt.**

- **The patches joined the query.** `EGTWaterKind` gains **`Rut`**. Each `AGTMudPatch` registers with
  `UGTWaterSubsystem` at `UGTMudSubsystem::BuildPatches` and comes out again there (the previous build's patches) and at
  `Deinitialize`. `Sample(GroundPoint)` answers the sheets as before, then the patches: inside a patch's box the depth
  is the patch's own `WaterDepthCmAt` - the section's `WaterTableCm` -25 plus `WetTableLiftCm` 15 x wetness, over the
  mud field's height at that XY - with `SurfaceZCm` = the ground point + that depth, **flow zero** (rut water stands:
  no current, no waves, nothing to solve) and `Kind` **Rut** anywhere in the box, even at zero depth, exactly as a sheet
  answers `Ford` at zero depth. **Where both answer, the deeper wins and the two are never summed**: a ford and a bog
  are different stretches of route and their water is different water.
- **The switch is gone.** `UGTMudSubsystem::bRutWaterPhysics` is **removed**, and with it the traction's own
  max-of-two branch: one `Sample` call per wheel at its contact point is every kind of water there is, and the rut
  water feeds the wheels' existing water drag (`WaterDragPerMetre` 2.4 on the wheel's speed *through* the water),
  `WaterBuoyancyGripLoss` (0 since W2) and `FrontWaterDepthM` for `UpdateFlooding` as any water does - and 5-10 cm of
  it never comes near the 0.85 m intake.
- **The hull skips ruts.** `UGTHullComponent` takes a sample only when its kind is `Ford` (one predicate,
  `bHullWater`, at the five body samples and at the free-stream read), so rut water gives it no drag, no lift, no
  submerged height and no lid. The reason is in the comment: a rut is narrower than a 1.9 m hull and its water lies
  under the axle line, so a drag box reading it would be a new force on the bog's already marginal crawl, not a hull in
  water. The wheels do read it; the hull does not.
- **The rises are unchanged.** The sheet's `RiseWithWetnessCm` 80 x wetness (until W5) and the patch's
  `WetTableLiftCm` 15 x wetness both stand; they are simply read through the subsystem now.
- **The test** (terrain, step 10). The `rut water` line reads its depth through `UGTWaterSubsystem::Sample` instead of
  the patch and asserts the kind: table **-25.0** cm (section -25.0 + a weather lift of 0.0 of 15.0), the crawl line's
  deepest cell **-30.8** cm -> **asked 5.8 cm, the query reports 5.8 cm, kind 2 = Rut** (surface Z 2845, ground traced),
  untouched mud **0.00** cm, the water grid 158,730 vertices of the mud mesh's 158,730, drawn -> **1**. A new **`sources`**
  line reads the whole model in one place: the ford's middle at 1115 m **kind Ford, 61.4 cm**; this step's own rut
  **kind Rut, 5.8 cm**; the road at 100 m (no section, tarmac, no patch, no sheet) **kind None, 0.0 cm**; and
  `UGTHullComponent::SubmergedHeightM` **0.000 m** with the car standing inside the patch box (box 1) -> **1**. Its flag
  is in the Finish chain, so terrain is **23 gates** now.
- **Tests and suite.** `terrain water drivetrain grip mud surface track weather` - the traction, the mud subsystem and
  the water query are what this stage touched. **6 PASS, 2 FAIL** (terrain, water). **Terrain 22 of its 23 gates**,
  failing only step 11's held exit, the flake standing since section 30 - and step 11's *other* gate, the pass down the
  ruts being faster, read **1** this run where the last run read 0 (15.0 m in 8.5 s, 6 m in 4.5 s, fastest 267 cm/s,
  against the first pass's 14.0 m in 12.0 s). All six ford gates **1**: through at 1145 m in 0.78 m of water 0.88 m off
  the route; raised 70 cm, flooded, timed out at 1115 m in 1.39 m; held **0.04 m** downstream with 1996 N of hull force;
  the wheels carrying **100.0 %** with the keel 0.45 m under and 9222 N of lift; carried **4.02 m** at cos 0.99; winched
  to 5.0 m of the post, 19,373 N, drained at 15.8 s. Water **7 of its 9**: the raise's **12.64 cm** peak to peak (asked
  5), the open gate named at WS2, and the bow's "the middle back within **+1.10 cm** of where it stood before the car"
  (asked 1), which read +0.88 at WS2's follow-up - a marginal centimetre on a gate nothing in W3 can reach (there is no
  mud patch at the ford, so `Sample` returns exactly what it returned). Drivetrain, grip, mud, surface, track and
  weather **PASS**. One build, exit 0. No setup was run and no picture taken: nothing visual changed.
- **What moved in the bog, reported and not tuned.** All four bog gates read 1 before and after. Two numbers moved
  further than the others: the middle crawl's body sink **10 -> 26 cm** lower than on firm ground (7 -> -4 against
  6 -> -19) and the mud field's rut mean **-30.7 -> -34.9** cm (the gate asks -24.0), with the contacts past half their
  own sinkage 86 -> 90 of 92 and the ridge mean 4.4 -> 4.1 cm. The crawl took a different line through the bog (1.0 m
  off the axis before, **0.3 m** after, slowest **105 cm/s** in both), which is what chooses the mud it cuts, and 5.8 cm
  of water at `WaterDragPerMetre` 2.4 is 0.014 of the load at 1 m/s: the cause is **unmeasured** either way. The escape
  is inside its day range (forward 14.6 -> **14.0 m** in 12.0 s, fastest 168 cm/s both; reverse 6.0 m back in 6.1 ->
  **6.9 s**), and the edge crawl came out faster (143 -> **264 cm/s**).
- **Not done, and unchecked.** The frame cost of the patch loop in `Sample` is **unmeasured** (a `Contains` and a
  bicubic `HeightAt` per patch per wheel per tick, and the hull's seven samples, on top of the sheets). The weather's
  lift through the query is unexercised: the terrain run reads a lift of 0.0 at wetness 0, and the 15 cm at wetness 1
  has only ever been read off the patch. Whether 5-10 cm of rut water can be felt at all is the user's to say. No
  picture: the water grid, the mud and the ford all draw what they drew. **Not driven, not felt.**
- **Follow-up, the same day: is it the rut water?** The bog's numbers moved at W3 and "unmeasured" was not good
  enough before the user drives, so the rut water got a switch and four runs settled it. **`gt.Water.RutWater`**
  (default **1**; at **0** `Sample` skips the mud patches, so the wheels read no rut water and the driving is what it
  was before W3) with **`-GTRutWater=0`** read off the command line once at `UGTWaterSubsystem::Initialize`, which is
  how a headless run sets it; the user has the cvar for the comparison while driving. With it off the `sources` line
  logs the rut reading as **kind 0, 0.0 cm** and does not gate it ("rut water off"), and step 10's rut water gate falls
  back to the patch's own call, so an OFF run is an ordinary run. Then **OFF, ON, OFF, ON** on The Hide, terrain each
  time, the same 22 of 23 gates every run:

  | | OFF | OFF | ON | ON | verdict |
  |---|---|---|---|---|---|
  | the middle crawl's body sink, cm lower | 8 | 10 | **26** | **25** | the rut water |
  | where it slowed, m / off the axis, m | 1064 / 0.8 | 1064 / 1.0 | **1060 / 0.3** | **1060 / 0.3** | the rut water |
  | slowest in the bog, cm/s | 100 | 104 | 103 | 102 | run-to-run |
  | the mud field's rut mean, cm | -28.8 | -31.8 | **-34.1** | **-35.3** | the rut water |
  | contacts past half their sinkage, of 92 | 83 | 90 | 87 | 92 | run-to-run |
  | ridge mean, cm / ridges ok | 2.7 / 83 | 3.7 / 90 | **4.0 / 92** | **4.0 / 91** | the rut water (3.7 against 4.0) |
  | escape forward, m / fastest cm/s | 13.7 / 198 | 13.8 / 188 | 13.8 / **162** | 14.3 / **167** | distance run-to-run, speed the rut water |
  | escape reverse, m in s / fastest | 6.0 in 6.5 / 174 | 6.0 in 5.1 / 183 | **4.2 in 8.0 / 149** | **4.4 in 8.0 / 139** | the rut water |
  | the edge crawl's slowest, cm/s | 138 | 144 | 147 | 264 | no overlap, but ON spans 117: run-to-run |
  | step 11, 6 m down the ruts, s | 5.8 | 5.4 | 5.7 | 5.6 | run-to-run |
  | step 11, 6 m on the first pass, s | 5.2 | 5.2 | **6.4** | **6.3** | the rut water |
  | step 11, 6 m on the held exit, s | 5.0 | 4.4 | **5.6** | **5.8** | the rut water |
  | step 11, 6 m on the unheld exit, s | 3.8 | 5.5 | 4.5 | 4.0 | run-to-run |

  So **it is the rut water, and it is a bias and not noise**: both OFF runs sit together and both ON runs sit together
  on the body's sink, the rut mean, the escape's speeds and two of step 11's three times. What it is *not* is the drag's
  arithmetic: 5.8 cm at `WaterDragPerMetre` 2.4 and 1 m/s is **0.0014 of the load** (`SpeedRatio` is the car's own speed
  per 10 m/s, squared), which cannot push a body 18 cm deeper by itself. A bog crawl at 1 m/s with the sinkage already
  at its cap amplifies a small steady force: the car goes slower (fastest 190 -> 165 cm/s), so it stamps more field per
  metre and cuts 5 cm deeper, and sits 16 cm lower in what it cut. **Nothing was tuned.** The mechanism past "the crawl
  amplifies it" is **unmeasured**, and whether 5-10 cm of standing water should cost a bog crawl that much is the
  user's to say - the switch is there to feel both ways.

## 44. Water stage W5: rivers rise with rain (2026-09-17)

Stage W5 of `docs/WATER_PLAN.md`. Until now a ford's level followed the ground's wetness, 80 cm at wetness 1, which
puts a river on the same clock as a puddle: it rises while the rain falls and drops as the ground dries. A river
answers its catchment hours later. Now it follows the **rain**, with a lag, and the ground's wetness is out of it.
Nothing tuned was touched (the traction's constants, the hull's box, W2's lift, WS1's and WS2's field numbers,
`HeadDropCm` 30, `PipeDamping` 1.e-3, `LidFill`/`LidBlend`, the mud's shape and rows, `WaterTableCm` -25,
`WetTableLiftCm` **15**, which stays on ground wetness because a bog's puddle *is* ground wetness, the intake 0.85 m,
the drain 5 s). Built and headless-verified; **not driven, not felt.**

- **The stage.** `UGTWaterSubsystem` holds one `RiverStageCm` for every sheet in a world and advances it **once a
  frame**, by the first sheet that ticks (a `UWorldSubsystem` does not tick, and every ford on a leg stands in the same
  weather). The target is `RiverRiseCmAtFullRain` **80** cm x the weather's **`GetRainIntensity`** - the global one,
  not `GetRainAt`, because a river answers its catchment and not the cover over the ford - relaxed toward with a
  first-order lag, `stage += (target - stage) x (1 - e^(-dt / lag))`, exact for a target held over the frame so the
  reading does not depend on the frame rate: `RiseLagS` **180** s while the target is above the stage and `FallLagS`
  **600** s while it is below. Rivers rise fast and fall slow.
- **What a sheet's level is now.** base + `RiseWithWetnessCm` x wetness + **the river stage** + `ExtraRiseCm` + the
  cvar's extra. `RiseWithWetnessCm` defaults to **0** (80 before; the field is kept and its term stays in the sum, for
  a pond or a sheet that should follow the ground). The rise reaches the surface the way every level change has since
  section 42's follow-up - carried into the field whole, `LevelJumpCm` 0 - so a rise is **many tiny lifts** and there
  is no bore and no wave: at `RiseLagS` 180 the first tick of full rain asks **0.007 cm**.
- **One line of WS2's had to move with it.** The sheet remembered the level every tick whether its change had been
  carried or not, and with the carry threshold's 0.01 cm floor that throws a river's rise away 0.007 cm at a time,
  for ever. `FieldLevelCm` is now remembered **only when the change was taken** - carried, or deliberately left to the
  ends by `bSuppressNextShift` - so small changes accumulate until they cross the floor and are then carried like any
  other. Nothing a jump does changes.
- **The driver's tools.** `gt.Water.RiverLagScale` (default **1**; 0.2 puts a three-minute rise inside a minute) scales
  both lags, and `gt.Weather.Rain` (default **-1**, no override; 0..1) forces the intensity. It drives **the numbers
  only** - the drops in the air, the ambience, the wetness the ground gains and MPC_Weather all go on reading the state
  blend's own intensity, as `SetRainForTest` has since WS2 - so `gt.Weather.Rain 1` with `gt.Water.RiverLagScale 0.2`
  raises a ford in a minute without wetting the world. For tests: `SetLagScaleForTest` (multiplies both lags),
  `ResetRiverStageForTest`, and `SetRiverFrozenForTest`, because WS2's rain step and the `hide_28` rain picture rain on
  a ford to **stir** it, not to raise it, and their volume gates are half a percent while a twelfth of 80 cm would
  arrive in their twelve seconds.
- **The test** (`water` step 10, `river [...]`, about 41 s). Lags x**0.05** (rise 9 s, fall 30 s), the wind off, the
  field calmed and `gt.Water.FlowScale` 0, because the rain step before it leaves the current switched back on and a
  current spinning up with a 24 s time constant would drift the middle by more than the rise being measured; the
  question the gate asks - does the surface follow a level that moves - is the same with the head on or off. **Rain
  1.0 for 9 s: the stage read 50.57 cm of the 50.57 asked** (80 x (1 - e^-1)), within 2. While it rose, the surface at
  the ford's middle was read every half second and stood **at worst 3.36 cm** off base + stage over 17 readings (asked
  under 5), **swinging 3.37 cm** peak to peak about that moving line (asked under 5). **Rain 0 for 30 s: 18.60 cm of
  the 18.60 asked**, within 2. The middle is the **mean of the middle 10 x 10 m**, not one cell: the rain that drives
  the step falls on the field as well as in the catchment and stirs it 1.3-1.5 cm sd, and a drop is an impulse whose
  mean over a patch is zero by construction.
- **The step raise is a surge number now.** `SetExtraRiseAll`'s 70 cm in one tick is a test and event device - an
  upstream dam, a cutscene - and **the river stage is how water rises in play**, so the gated rise is the river's path
  and the jump keeps a looser sanity gate of **25 cm** (it read **15.01** this run against 13.23 and 12.64 before),
  which still catches a regression toward the ~104 cm the same 70 cm rings when it goes on the two fixed heads alone.
  The water run's budget went 300 -> **360 s** for the new step.
- **Tests and suite** (`water terrain weather`). **water PASS** - all ten gates, the first time the water test has
  passed since WS2 gave it its sources, the raise's swing having been the one failure. **terrain FAIL on step 11's
  stage C held exit alone**, the flake standing since section 30 (the held exit reached 6 m in 5.7 s against the pass
  down the ruts' 5.5), with **all six ford gates 1** and the ford as built read **0.75 m** of water, 0.76 m off the
  route, through at 1145 m - unchanged by `RiseWithWetnessCm` 0, the test weather being Clear at wetness 0. **weather
  PASS.** Build exit 0. No setup was run: no asset changed. The sheets take the new default because nothing ever wrote
  that property into the level.
- **Unchecked.** How a front's own intensity and duration over a leg sit against 180 / 600 s (the user drives a leg
  with a front and crosses twice) - nothing in play has been watched raising a ford. The **fall's** surface lag:
  6.40 cm off base + stage at worst, against the rise's gated 3.36, logged and ungated and unexplained (the banks
  drying back is the candidate). The advance's own cost (one exp a frame) is not measured. **Not driven, not felt.**


## 45. Water stage W4: the look (2026-09-17)

Stage W4 of `docs/WATER_PLAN.md`, the plan's last, and the one the user asked for by name after driving WS2 ("I'm
really happy with it. The one thing to take note of that we will fix later is getting the color/opacity of the water
correct"). The ford's surface had W1's flat blue-green with WS2's procedural height and slope shading on top; it now
has a colour and an opacity that come from the field's own depth, a sourced ripple normal that the field's own current
carries, foam off the same field, and thrown water from the spray. Built and headless-verified; **not driven, not
felt, and nobody has looked at a picture** - every number below is the test's or the pixel sampler's. Nothing tuned
was touched: the traction's constants, the hull's box, W2's lift, WS1's and WS2's solver numbers (`HeadDropCm` 30,
`PipeDamping` 1.e-3, `BedFriction` 0.005, `LidFill` 0.24, `LidBlend` 0.25, `WindRippleCm` 45, `MaxFlowSpeedMps` 3.0),
W5's lags, the mud, the camera, the intake and the drain, and the spray's own `MudRate` 40 / `DustRate` 25 /
`SnowRate` 30 / `SteamRate` 25 all stand.

- **The field texture carries what the material needs** (`AGTWaterSheet::FieldTexel`, one function now, which both
  `UploadField` and the test call). The per-frame PF_FloatRGBA texture was **R** the surface over the water level in
  cm and **G** the water column in cm (the depth plus WS2's lid, so the mesh is not cut away under a car that has
  pushed its own cells dry). It now also carries **B** and **A**: the cell's depth-averaged flow in the **field's own
  axes**, cm/s - the frame the material already maps world XY into, so the ripple pans with the current without a
  second rotation - and **zero on a dry cell**, because the solver leaves its last velocity in a cell that has just
  dried and a ripple panned by it would ride over dry ground. The alpha channel had been a constant 1 and nothing
  read it.
- **Colour and opacity by depth**, `M_GT_MudWater`'s pattern (section 36) with its own numbers and the depth read
  **per pixel out of G** rather than from a `DepthFade` node: the field knows how deep it is, while the scene depth
  only knows how far away the bed is, and a shallow-water field is the one place in this project where that
  difference is free. A silty upland river and not a pool. **WS2's height and slope shading is kept on top as
  multipliers**, because it is what makes the motion at rest visible at all (a normal tilt alone moved 0.50 % of the
  bank picture's pixels before it went in), and its two gates still hold below.
- **Every material parameter of `M_GT_Water`, with its default** (the list the user tunes by name;
  `Art/Unreal/setup_m6_water.py`, rebuilt by `Art/setup_m6_water.bat`, **39 expressions**, no compile errors):
  the depth look `ShallowColor` **0.10 0.13 0.10**, `DeepColor` **0.02 0.035 0.03**, `WaterDeepCm` **120**,
  `ShallowOpacity` **0.25**, `DeepOpacity` **0.85**, `FresnelOpacity` **0.30**, `WaterRoughness` **0.08**,
  `GlossRoughness` **0.03**; the ripple `WaterTileCm` **200**, `WaterTileCm2` **450**, `NormalStrength` **0.6** (the
  second layer's weight), `RippleGain` **1.0** (the master on both; 0 leaves the field's own slope alone),
  `FlowTexScale` **1.0**, `FlowTexScale2` **0.6**, `FlowPeriodS` **2.0**, `StillDriftCmPerS` **8**; the foam
  `FoamDepthCm` **12**, `FoamSlope` **0.6**, `FoamSpeedCmPerS` **250**, `FoamNoiseCm` **80**, `FoamColor`
  **0.7 0.7 0.68**, `FoamRoughness` **0.6**; and WS1/WS2's, unchanged: `NormalGainCm` **1.0**, `DryCutCm` **1.0**,
  `CrestColorGain` **0.25**, `SlopeShadeGain` **0.6**, `CrestOpacityGain` **0.1**. `BaseColor`, `Roughness` and
  `Opacity` are **gone**: the colour, the roughness and the opacity all leave the one pixel-shader node finished.
  `AGTWaterSheet` sets only what it always set (`FieldTex`, `FieldMin`, `FieldSize`, `FieldAxisX`, `FieldAxisY`,
  `FieldTexels`, `NormalGainCm`, `DryCutCm`), so every W4 number is the master's and the user edits it in the editor.
- **The ripple normal carried by the flow.** The flow-map technique: per layer the sourced normal is sampled **twice**
  along the local velocity with the two phases half a period apart and cross-faded on a sawtooth of `FlowPeriodS`, so
  no sample is ever panned more than a second's worth and the ripples ride the current instead of stretching with it.
  Two layers at 200 and 450 cm, the second at `NormalStrength` and `FlowTexScale2`. Where the water stands the pair
  drifts at `StillDriftCmPerS` so still water is not a frozen photograph. Only the texture's **RG** is read and used
  as a slope, added to the field's finite differences before the world normal is built: a normal-compressed texture
  has no usable B in a Custom node, and a slope is exactly what the field's own differences already are. The source's
  green is DirectX convention (down) and is flipped in the shader. The ripple is masked off the dry cells.
- **Foam from the simulated surface**, the largest of three, broken up by two octaves of hashed value noise at
  `FoamNoiseCm` that drift with the flow (procedural, which the plan allows here), taking the colour to `FoamColor`,
  the opacity to 1 and the roughness to `FoamRoughness`: the **shallows** (G under `FoamDepthCm`: the banks and the
  ring around anything standing in the water), the **steep surface** (the field's own slope over `FoamSlope`) and the
  **fast water** (B/A over `FoamSpeedCmPerS`). **Two of the three thresholds are not the plan's and both were
  measured.** At the plan's `FoamSlope` **0.15** and `FoamSpeedCmPerS` **120** the foam painted the whole channel:
  hide_25's water box read **41.19 %** of its pixels over 200 in the brightest channel against **1.88 %** in the same
  box with the flow and the wind off, and hide_24's **42.26 %**. Both numbers are the ford doing what it always does -
  this ford's current is **143 cm/s** where the route crosses, over the plan's 120, and WS2's wind puts **1.5 cm** of
  roughness on 25 cm cells, which is a finite-difference slope of about **0.04 cm/cm** against a threshold of 0.15.
  So both were set above what a drivable crossing does on its own (**0.6** and **250**: a 20 cm bow crest over a 25 cm
  cell is 0.8 cm/cm, and white water is faster than a ford you can drive through), and the same two boxes then read
  **15.32 %** and **31.98 %**. The user lowers them by name to get rapids.
- **The spray's water state** (`UGTSprayComponent`, a fifth kind `EGTSprayKind::Water` with its own emitter, so it can
  take a water colour: the existing translucent droplet at **0.55 0.64 0.62**, opacity **0.55**, roughness **0.15**,
  falling at 980 cm/s2 as mud does). **Additive**: the mud, dust and snow branches are untouched, so a wheel on a
  ford's muddy bed still throws what it threw before and the spray test's lane counts do not move - a ford's bed is a
  Mud surface, so the two overlap by design rather than by accident. A wheel in contact whose own water (the one
  query's depth, since W3) is over `SplashDepthM` **0.10 m**, with the car over `SplashSpeedMps` **2 m/s**, throws
  `SplashRate` **60** droplets a second x speed/`SplashFullSpeedMps` **6** x depth/`SplashFullDepthM` **0.4**, from
  the waterline over its contact. The hull, whose `SubmergedHeightM` the spray now takes as a new argument, throws a
  bow spray from `BowSprayOrigin` **(220, 0, 20) cm** when it is over `BowSprayHeightM` **0.05 m** and the car over
  `BowSprayMps` **3 m/s**, at `BowSprayRate` **50** x speed/`BowSprayFullSpeedMps` **6** x
  submersion/`BowSprayFullHeightM` **0.5**. The speed both read is the car's whole 2D velocity and not its forward
  component: a car the river is carrying sideways is still throwing water. Nothing on the on-foot character.
- **The test.** The `water` test's texture step checked only the texture's size; it now reads the channels through
  `FieldTexelAt`, which is the texel that goes into the upload, so a NullRHI run that can sample nothing can still
  check the layout: **wet cell 0 G 36.85 cm** (asked over 0), **dry cell 20 G 0.00** (asked 0) and, at the cell the
  route crosses, **the texel carried 142.7 cm/s of flow against the cell's own 142.7** (asked within 30 %). Two things
  had to be measured rather than assumed. A cell the solver calls dry still carries the film it was left with - the
  first cell under `DryDepthM` held **0.43 cm**, which is what `DryCutCm` 1.0 exists to cut - so "G is 0 on a dry
  cell" is asked of a cell that has **never** held water, and a bank cell is that. And the flow is read at **step 1**,
  where the current runs, not at step 8: by then the wind, rain and river steps have calmed the water to **0.3 cm/s**,
  and at 0.3 cm/s a reading cannot tell cm/s from m/s (a hundredfold unit error would have passed). The spray's own
  test runs on `L_TestTrack`, which has no water sheet on it, so **the spray check is logged from the terrain ford
  steps instead**, as the plan allowed: crossing as built, **4 wheels at once, the deepest in 0.79 m, 213 droplets/s,
  the bow spraying with 0.79 m submerged at 50/s, 120 live**; raised 70 cm, **4 wheels, 1.17 m, 222/s, bow 1.41 m,
  50/s, 118 live**. Information, not a gate: a particle count on a chaotic crossing is not a number to fail a suite on.
- **The pictures** (`Art/ford_shots.bat`, **11** now, then `Art/tools/sample_ford.ps1`; a ford run is only ever
  compared with a ford run, and the baseline is WS2's follow-up run). Water box **mean RGB, blue over red, the count
  over 200**. **hide_22_ford_bank** water 182,382 px **157 187 185 / 92.4 % / 3.90 %** -> **166 175 163 / 66.1 % /
  8.41 %**; its bank box (which is 1,268 px of the **sunlit far ground** and not water - 0.0 % blue over red - so the
  plan's "foam takes it over 2 %" gate is met by the ground it frames) **21.21 % -> 62.70 %**. **hide_23_ford_cross**
  water **10.68 % -> 8.53 %** bright (asked under 25), its bow box **59.40 % -> 14.68 %** (asked over 1: WS2's crest
  shading had saturated that box and the depth tint is darker). **The motion pair holds under the new shading:
  34.34 % flowing against 0.00 % still** (asked over 5 and under 1; WS2 read 10.45 and 0.00). **hide_24_ford_deep**
  water 235,478 px **153 167 154 / 9.82 % / 1.67 % dark** -> **184 178 161 / 31.98 % / 0.14 % dark**.
  **hide_27** wake pair **25.26 % -> 16.86 %**, **hide_28_ford_rain** **2 -> 5 crests** along the line hide_22 counts
  **1** along. And the new **hide_29_ford_shallow**, the eye 1.6 m over the near bank looking down the route into the
  water, for the user's own colour judgement: its **edge** box (the first 2 m past the waterline, 75,603 px) **mean
  176 167 137, 0.40 % over 200**, its **shallow** box (3 to 8 m past it, 52,734 px) **mean 169 166 143, 7.0 % blue
  over red, 0.54 % over 200**, with the field reading **21.3 cm** of water 1 m past the waterline and **62.5 cm** 5 m
  past it, flowing **81 cm/s** there - so at `WaterDeepCm` 120 both boxes are still mostly the bed seen through the
  water, which is what a shallow edge is and what the user is being asked to judge. The waterline is found by walking
  the route until the field has water in it (**1110.5 m**), not taken from the Ford section's start (**1090 m**),
  where the field reads 0.0 cm: the first run of this picture framed fifty metres of dry bank.
- **Tests and suite.** Per the cut policy, `water terrain spray` between builds; then the full **23**: **22 PASS, 1 FAIL**, the failure `terrain` on step 11's stage C held exit alone - the exit at 30 degrees ran 12.8 m in 12.0 s against the pass down the ruts' 14.5 m, so "slower than down the ruts" read 0 - the marginal flake standing since section 30, and the same test PASSED outright on this stage's own iteration run an hour earlier, which is what marginal means.
  On the iteration run `terrain` **PASSED outright** - all 23 of its gates, including step 11's standing ruts flake,
  with all six ford gates 1 - and `spray` PASSED with the new kind in it (`tarmacClean=1 poolExceeded=0
  maxDustInDirt=120 maxMudInMud=95 maxSnowInSnow=91`), while `water` failed its new channel gate once and passes all
  ten after the two corrections above. Three builds, all exit 0, and
  three setups: `setup_m6_textures` (the mud set still imports 4 of 4 with the same mean colour 0.080993 0.029794
  0.011753, plus the water normal), `setup_m6_water`, and no `setup_m6_mud` or `setup_m6_hide` - nothing they build
  changed.
- **The normal is sourced, CC0** (`Art/Textures/Water/SOURCE.txt` carries the whole provenance and why the usual
  places did not have one): **"Rain Ripples on Puddle" (others_0028) by TextureCan.com, licence CC0 1.0 Universal**,
  https://www.texturecan.com/details/531/, the 2K set's DirectX normal, imported by `Art/setup_m6_textures.bat` as
  `T_GT_Water_N` (TC_Normalmap, sRGB off, no green flip). Measured before importing: **2048 x 2048, mean 127.7 127.8
  255.0** over 65,536 samples with R over 86-164, a tangent-space normal about flat with slopes to roughly +/- 0.3.
  ambientCG's API answers **no** water material at all (twelve hits for "water", all ice, ground and surface
  imperfections) and Poly Haven's texture list has none either (four hits, all "waterproof tiles" tags);
  3dtextures.me's Water 001/002 are behind Google Drive links whose pages do not state CC0, and OpenGameArt's
  fifteen-texture water pack with normals is **CC-BY 3.0**, not CC0. `M_GT_Water` refuses to build without the
  texture rather than falling back, because a normal-compressed texture parameter cannot take a linear-colour default.
- **Not done, and unchecked.** **Nobody has looked at any of this**: the numbers above are pixel counts and the user
  judges the colour, the opacity, the ripple's motion, the foam's break-up and the thrown water on foot. The **frame
  cost of the render half is still unmeasured** - the solver's 0.949 ms a stepping frame is all there is, and W4 adds
  six texture samples and two octaves of noise per water pixel over a 30 x 74 m sheet, plus up to 120 more instanced
  spheres. The **water pool saturates**: 213 droplets/s against `PoolPerKind` 120 and lives of 0.45-0.85 s means the
  oldest slot is recycled while it is still alive (the count read 120 and 118 of 120). The **bow spray leaves
  backwards**, sharing the wheels' spawn direction, which is a look nobody has checked. The foam's **shallow** term is
  the only one this ford can reach now (the edge box reads 0.40 % over 200, and the field says the foam band is under
  half a metre wide at this bed's slope), so the foam's break-up has not really been seen by anything. `RippleGain`
  1.0 puts up to 0.5 cm/cm of tilt on the surface and that is **not** measured against anything - the still picture's
  2.00 % bright against WS2's 0.00 % is all it moved. And the two-sided sheet seen **from under the water** (a
  floating car's camera dips) has not been looked at, as the plan flagged.
- **Traps.** A dry cell is not an empty cell: the field's `DryDepthM` is 0.01 m and the cells under it still carry
  their film into the texture, so a channel gate written as "= 0" has to pick a cell that has never been wet. A flow
  reading taken where the water has been calmed cannot check a unit: 0.3 cm/s and 0.3 m/s both read "about zero".
  The Ford **section** is not the ford: 50 m of route with a dug channel in the middle of it, and the water starts
  20 m in. A Custom node may not read a normal-compressed texture's blue - use RG as a slope. A `VectorParameter`
  wired into a Custom node's input arrives as float3, so `.rgb` is the whole of it. And the plan's own numbers for a
  threshold are worth what they measure: 0.15 and 120 were both under what this ford does at rest, and foamed it end
  to end.
- **Follow-up: refraction and the shallows (2026-09-18) - BUILT, THEN REVERTED THE SAME DAY.** The user drove it and
  said: *"Revert it, that seems to have messed up the physics of the water."* **Everything in this bullet is out of
  the build**; `M_GT_Water` is back to W4's shipped state (39 expressions, `ShallowOpacity` **0.25**, `WaterDeepCm`
  **120**, `FresnelOpacity` **0.30**, no `MP_REFRACTION` connection, the refraction method at its default, no
  `RefractionIOR` / `RefractionStrength` / `RefractionEdgeFadeCm` / `WetBedDarken` / `WetBedCm`), the
  `gt.Water.Refraction` cvar and `AGTWaterSheet::AppliedRefraction` are gone, the hide_30 picture pair is gone from
  the runner and the sampler, and `Art/ford_shots.bat` writes **11** pictures again. `CalmField` / `CalmAll` /
  `FGTWaterField::Calm` were **kept**: they pre-date this follow-up and the water test uses them in four places and
  shots step 26 in one - hide_30 was only another caller. **The finding is kept because it is why refraction does not
  come back** (the refraction sub-bullet below), and the rest is kept only as the record of what was tried.
  **Why it was reverted is not proven.** The follow-up touched no solver, hull, traction or subsystem file; the
  suspect is frame time, because the field takes at most **4 sub-steps a frame** and a distortion pass over a
  35,520-vertex translucent sheet lengthens frames. The rendered shots run logs **no clamp count and no StepMs** (the
  water test logs both, but it runs under NullRHI where there is no distortion pass at all, so that test can never
  see this). The only proxy in the logs is game seconds per real second over shots steps 22-28, and it is **bimodal
  and does not separate the two builds**: W4-main read **0.996** and **0.272** on two runs of the same build, the
  three follow-up runs **0.420 / 0.375 / 0.249**, and the reverted build **0.996**. Reported, not claimed. What that
  ratio does say is that **the ford pictures are frame-rate dependent** - at 0.27 the field gets a quarter of the
  sub-steps per game second that it gets at 1.0 - which is the likeliest reason the picture numbers below swing as
  far as they do, and it is worth its own measurement before anyone trusts a ford picture to a few per cent again.
  - **The picture numbers, W4-main / after the revert**, same material, same script: hide_22 water box mean
    **166 175 163 / 171 179 166**, blue over red **66.1 / 34.7 %**, over 200 **8.41 / 4.44 %**; hide_23 water bright
    **8.53 / 5.40 %**, its bow box **14.68 / 14.92 %**; the motion pair **34.34 / 13.42 %** flowing against
    **0.00 / 0.00 %** still (the gates are over 5 and under 1, and both runs pass them); hide_24 **31.98 / 7.34 %**.
    The two runs of the *same* build disagree by more than the follow-up ever moved them, which is the frame-rate
    point above and the same instability section 45 already recorded for hide_29 (37.3, 25.8, 6.4 across three runs).
  - **The tests after the revert.** `water` **PASS**, all ten gates. `terrain` **FAIL on step 11's stage C held exit
    alone** - the exit at 30 degrees ran 14.3 m against the pass down the ruts' 13.2 m - the standing flake, with
    **all six ford gates 1** (through at 1145 m in 0.76 m; flooded and timed out at 1115 m in 1.37 m; held 0.03 m
    downstream; carried; floating with the wheels at 100.0 % of the weight; winched to the post in 23.6 s). Two
    builds, both exit 0; `Art/setup_m6_water.bat` only.

  What follows is the record of the reverted work.

  The user, on foot after W4: *"That looks better. but the
  water is still too transparent, or there is no refraction so in the clear parts of the water you cant really tell it
  is there."* Both causes he names were addressed, and the honest answer was that **one of them is built and measures
  nothing, and the other is what actually moved the picture.**
  - **Refraction is in and is invisible here, measured both ways.** `MP_REFRACTION` is connected and the material's
    `refraction_method` is **`RM_PIXEL_NORMAL_OFFSET`** (5.8 offers `RM_2D_OFFSET`, `RM_INDEX_OF_REFRACTION`,
    `RM_INDEX_OF_REFRACTION_FROM_F0`, `RM_NONE`, `RM_PIXEL_NORMAL_OFFSET`; the property and the enumerator were both
    looked up by name and the one that took is logged, the same dance the translucency lighting mode needed). It
    **coexists with `TLM_SURFACE_PER_PIXEL_LIGHTING`**: nothing had to be given up, the sheet still takes the sky.
    The pin is fed `lerp(1.0, RefractionIOR, RefractionStrength x the edge fade x the dry mask)`, so 1.0 is "no
    bending" in either mode and **`RefractionStrength` 0 is a clean off switch** - which is what `gt.Water.Refraction`
    pushes onto every sheet's own instance, and what the new picture pair uses. And the pair says it does not show:
    with the surface **frozen** for it (the wind off, the flow off, the field calmed, so the two frames differ by the
    refraction alone - hide_26's own still pair frame-diffs 0.00 %), `hide_30_ford_refract_on` against `_off` moved
    **0.00 %** of the shallow box by more than 12 of 255 (mean change **1.15**, biggest **6**) against a gate of
    **5 %**. `RM_INDEX_OF_REFRACTION` was then built and measured on the same pair and is no better: **0.02 %**, mean
    **2.01**, biggest **17**. **The mechanism is the depth gap.** The engine's distortion offset is bounded by how far
    the refracting surface stands in front of what is behind it, and over a ford's bed that gap is the depth of the
    water - **18 cm** a metre past the waterline in the run that shipped - so the bend is a fraction of a pixel
    whatever the mode. Pixel Normal Offset ships because it is the right mode for a sheet whose vertex normals are all
    up and whose shape is all in the pixel normal, and because it does not carry Index of Refraction's shoreline halo;
    **not** because it measured better. What would make refraction visible is deeper water or a hand-rolled
    screen-space offset, and neither is in this follow-up.
  - **The shallows are the part that moved**, through the opacity and the tint and not through the refraction:
    `ShallowOpacity` **0.25 -> 0.45**, `WaterDeepCm` **120 -> 70** (120 put the tint's ramp out past anything a ford
    holds; at 70 a fordable depth is already most of the way to `DeepColor`), `FresnelOpacity` **0.30 -> 0.45**, and a
    new **wet bed**: over the first `WetBedCm` **5 cm** of depth the tint is multiplied toward a darker one by
    `WetBedDarken` **0.35** and the opacity is lifted by the same ramp, so the waterline reads as a wet line on the
    bank. The lift is not decoration: a translucent surface **cannot** multiply what is behind it (that is
    `BLEND_MODULATE`, which takes no specular and would cost the sky), so darkening a tint at an opacity of 0.25
    darkens nothing.
  - **The gate this was meant to be judged on does not work, and that is the follow-up's other finding.**
    hide_29's "colour distance between the shallow box and the dry edge box" read **37.3, 25.8 and 6.4 across three
    runs of the same material** (asked over 30, and 9 before this stage), with the two box means swapping which is the
    brighter one between runs. Two reasons, both in the instrument and not in the water. **The "edge" box is not dry
    ground**: it is the water 0.5 to 2 m past the waterline, so the number differences shallow water against
    slightly shallower water - and the 9 it is compared against was measured the same way. And **the eye moves**: it
    is placed against the waterline found by walking the route, which the field puts at **1110.0, 1110.5 and 1111.5 m**
    on three runs, so the boxes frame different ground each time. Fixing it means putting the edge box on the bank
    *before* the waterline and pinning the eye to a fixed arc, which is a runner change this follow-up had no build
    left for. **Nothing about the water was tuned to chase it.**
  - **The one stable instrument this follow-up did produce** is hide_30's own box, because its surface is frozen: it
    read **129 136 128** with the refraction on in all three runs (and 130-131 137 128-129 with it off), to within a
    unit. That is the baseline the next pass on the shallows should be judged against, not hide_29's.
  - **The standing gates hold.** The motion pair **26.38 % flowing against 0.00 % still** (asked over 5 and under 1).
    hide_23's water box bright **7.10 %** (asked under 25). hide_22's water box mean **155 168 161** with blue over red
    **79.5 %** (W4 read 166 175 163 and 66.1 %). Reported and **not** gated here: hide_23's bow box fell from
    **14.68 % to 0.39 %** over 200 - the box is the bow wave's crest, and a more opaque, darker, less blown-out water
    is exactly what the user asked for, so the W4 gate that box carried (over 1 %) no longer means what it meant.
  - **Tests and setups.** C++ changed (the cvar and the picture step), so `bash Art/suite.sh water`: **PASS**, all ten
    gates, the current 1.44 m/s. One build, exit 0. `Art/setup_m6_water.bat` only - no other asset changed.
  - **The parameter list this follow-up shipped - NONE OF IT IS IN THE BUILD** (the live list is the main stage's,
    above; this is only what was reverted): `ShallowColor` **0.10 0.13 0.10**, `DeepColor` **0.02 0.035 0.03**,
    `WaterDeepCm` **70**, `ShallowOpacity`
    **0.45**, `DeepOpacity` **0.85**, `FresnelOpacity` **0.45**, `WaterRoughness` **0.08**, `GlossRoughness` **0.03**;
    `WetBedDarken` **0.35**, `WetBedCm` **5**; `RefractionIOR` **1.33**, `RefractionStrength` **1.0** (0 off, and
    `gt.Water.Refraction` pushes it onto every sheet's instance), `RefractionEdgeFadeCm` **8**; `WaterTileCm` **200**,
    `WaterTileCm2` **450**, `NormalStrength` **0.6**, `RippleGain` **1.0**, `FlowTexScale` **1.0**, `FlowTexScale2`
    **0.6**, `FlowPeriodS` **2.0**, `StillDriftCmPerS` **8**; `FoamDepthCm` **12**, `FoamSlope` **0.6**,
    `FoamSpeedCmPerS` **250**, `FoamNoiseCm` **80**, `FoamColor` **0.7 0.7 0.68**, `FoamRoughness` **0.6**;
    `NormalGainCm` **1.0**, `DryCutCm` **1.0**, `CrestColorGain` **0.25**, `SlopeShadeGain` **0.6**,
    `CrestOpacityGain` **0.1**. **44 expressions**, no compile errors.
  - **Unchecked.** Nobody has looked at any of it - whether the wet line at the bank reads as wet, whether 0.45 is too
    opaque, and whether the user's "you can't tell it is there" is answered at all, since the thing he named by name
    (refraction) measures nothing and the thing that moved is the opacity he also named. The frame cost of the
    distortion pass over a 30 x 74 m sheet is not measured. hide_29's gate is broken as described. And **13 pictures**
    now come out of `Art/ford_shots.bat`, two of them a frozen pair, which lengthens the run by about ten seconds.

## 46. Water stage R1: instrumentation and rocks in the ford (2026-09-18)

Stage R1 of `docs/WATER_PLAN.md` section 6, the first of the river stages, built against that section's **standing
finding**: a look change once changed what the user felt with no physics touched, because the solver takes at most
four sub-steps of 1/60 s a frame and a slow frame runs the water in slow motion. So the stage begins with a
measurement, fixes what the measurement found, and only then puts stones in the bed. Nothing tuned was touched.

- **Every run now says what the water cost it.** `AGTWaterSheet` keeps two windows of `FGTWaterRunStats` - frame ms
  (mean, worst), the field's `StepMs` (mean, worst), sub-steps **asked** against **run**, the clamp count and the
  **simulated time it dropped in seconds**. One window is logged once a second as `GTWATERSTATS ...` while a camera or
  a pawn is within 100 m; the other is taken by the runner at the end of **every shots and water-test step** (in
  `Next()`, so the line carries that step's number). `gt.Water.Stats 1` draws the same line on screen.
  `Art/tools/sample_ford.ps1` prints it beside each picture and marks a picture **VOID** when its step clamped.
- **The measurement, before any rock went in.** Over the eight ford picture steps: frame **10.0-12.5 ms** mean
  (80-100 fps) but **143-400 ms** worst, the solver **0.74-0.92 ms** mean and up to **4.34 ms**, and **seven of the
  eight steps clamped** - 1 to 2 frames each, dropping **0.083 to 0.333 s** of water. Every ford picture but one had
  been taken in a run whose water had just run slow.
- **The clamp fix** (the plan's, made exact by the measurement). Unsimulated time is carried across frames instead of
  being thrown away, bounded at **0.25 s**; a frame may burst to **8** sub-steps while the *mean* cost of a sub-step
  (`StepMsSum / SubStepsRun`, not one frame's `StepMs / Steps`, which counts the per-frame work eight times over)
  keeps the burst under **6 ms**; past that the frame takes **1/30 s** steps while the Courant number at the deepest
  cell stays under **0.9** (it logs **0.51** at 25 cm cells here, the plan's 2.5 m of water being the limit), and a
  frame on that fallback may take eight of them. After it: **eight of the nine** picture steps clamp **0** and drop
  **0.000 s**; the one that does not is step 22, whose **400 ms** first frame after the level load exceeds the 0.25 s
  bound and costs **0.153 s**, so hide_22 alone comes out VOID.
- **A stone in the channel is bed.** `AGTWaterSheet::BedZAt` takes the **higher** of the landscape's height and a
  downward trace against **WorldStatic** geometry, with the landscape actors ignored (their collision mesh is not
  their heightmap, and taking it would move a crossing tuned to the centimetre) and everything movable out of the
  query by construction. Only cells whose bed is within 2 m of the level are traced: **24,164** of 35,520, **28 ms**
  at level start, **99** of them taking their bed from a rock.
- **The rocks.** `FGTTerrainSpec` gains `FordRockCount` **14**, `FordRockMinM` **0.6**, `FordRockMaxM` **1.6**,
  `FordLaneM` **4** and R1's own `FordRockClearM` **6**; `GTTerrain::FordRocks` places them on `TrackStones`' pattern
  and `AGTTerrainDressing` instances them with the stone mesh, turned, tilted 6 degrees and sunk a quarter, each one
  placed so the top of the cube **over its own centre** stands `FordRockExposedCm` (52.5 cm per metre of size) over
  the bed whatever its tilt - which is the height the water test reads back. **12 of the 14 were placed, 7 of them
  standing over the water**; the terrain test's dressing line carries the count.
- **Three things the crossing's own gates taught the placement, each measured.** (1) With rocks 2 m from the middle
  the raised crossing's current fell **1.25 -> 1.01 m/s** and the floating car was carried **2.11 m** in ten seconds
  against the gate's 4 (terrain step 16), because the current runs *across* the route and a rock beside the middle is
  upstream of it: hence `FordRockClearM` 6 m. (2) With rocks anywhere in the **downstream half** the winch tow stalled
  after 3.1 m and the cable snapped at **40 kN** three runs running, where a clear half takes the car to the post in
  **23.6 s** - the new tow log shows the car leaving the crossing sideways and reaching 12 m downstream within 7 m of
  route, so the whole half is left clear and the rocks lie upstream. (3) A role a spot cannot take (too deep to break
  the surface, too shallow to drown a 0.6 m rock) is swapped for the other rather than passed over; without that the
  upstream shallows placed **5 of 14**. The proud share is therefore **7 of 12**, not the plan's third.
- **A frame-rate bug the rocks uncovered, and its fix.** The water test's river gate started failing at **9.1 cm** off
  a rising level against W5's 3.4. It was not the rocks: `AGTWaterSheet` carried a level change from the level
  `Step` was last handed rather than from the level the field was last **carried** to, so every frame whose change was
  too small to cross the 0.01 cm threshold was thrown away - at the river's 5 cm/s and a thousand frames a second the
  field gained **81 %** of a 49 cm rise. `FGTWaterField::ShiftLevel` takes the base level as an argument now and the
  sheet passes `FieldLevelCm`. The gate reads **3.2 cm** again. Same water, a different frame time: exactly the
  standing finding.
- **The water test's new step 11, `rocks`** (the wind off, **45 s** for the current to settle - at 15 s the crossing
  still read 0.87 m/s of its 1.26): the tallest rock's cell stands **47.5 cm** over the mean of its ring 1 m out
  against the **47.4 cm** it was placed at (asked within 10); beside the **proudest** rock (0.90 m, standing 12.6 cm over the
  level - a geometric choice, because choosing it by the speed of the water it stood in picked a different stone every
  run) the flank cell reads **1.32 m/s** against the **1.10 m/s** the same streamline runs 2.5 m upstream of it, and
  **0.52 m/s** in its slack **25 cm** behind it. Three things about those two gates are measured, not the plan's:
  they are read against the rock's own streamline and not the crossing's mean of 1.27 (a proud rock is outside the
  crossing's flow tube by construction, and one side of a rock can sit in another's lee reading 0.10 m/s, so the
  faster of the two sides is the reference); the flank is the first cell clear of the rock, since at 0.75 m off a
  0.74 m stone the squeeze has already spread and read 0.87 against the water's own 1.01; and the gates are **1.05 x**
  and **0.8 x** rather than 1.1 x and 0.5 x, because over four placements a 0.7-0.9 m stone on a 27-42 cm shoal
  squeezes by 9 to 20 % and its slack is **one cell** wide (0.52, 0.84, 1.04 m/s at 0.25, 0.50, 0.75 m). A 20 cm ring
  3 m upstream reaches it in **0.65 s** and comes back **2.09 cm** on the near side (asked over 0.3). `StepMs`
  **0.780 ms** with the rocks in.
- **Tests.** `water` **PASS**, all eleven gates. `terrain` **FAIL on two gates, neither this stage's**: the mud step's
  `difference sd 0.21`, which fails identically in the pre-rock baseline run of the same day, and step 11's standing
  ruts flake, which passed on two of this stage's four terrain runs and failed on the other two. **All six ford gates
  read 1** (through at 1145 m in 0.76 m; raised, flooded; held 0.03 m; **carried 4.09-4.40 m** over three runs against
  a gate of 4; floats at 3.1 % of the weight; **winched to the post in 23.6 s**, no snaps).
- **The pictures**, `Art/ford_shots.bat`, **12** now. The new **hide_31_ford_rock**: the eye 1.6 m over the nearest
  dry ground, **5.0 m** from the nearest surface-breaking rock (0.90 m, standing 12.6 cm over the level), a ring round
  its waterline against the same ring of open water 3 m to the side - **5.78 % over 200 against 0.00 %**, which is
  W4's foam finding the shallows at the stone. hide_22's water box reads 171 179 166, 33.7 % blue over red, **4.11 %**
  over 200, and is **VOID** by its own rule (the level-load frame).
- **Unchecked.** Nobody has driven or walked it: whether 12 rocks are too many or too few, whether the lane is wide
  enough to drive, and whether a rock reads as a rock in greybox. The burst and coarse paths have only been exercised
  by screenshot hitches, never by a real slow machine. The bed trace's 28 ms is paid at every level start. The two
  rocks on the lane's edges are both on the upstream side now, the downstream half being kept clear.

## 47. The Proving Ground (2026-09-19)

A second generated map, **L_Proving**, so water, mud and the car can be felt without driving a leg. Built by
`Art/setup_m6_proving.bat` from **DA_Terrain_Proving** (`GTTerrain::ProvingSpec`, beside `HideSpec`) through the same
code as The Hide: `setup_m6_hide.py` now splits into `place_ford_sheet`, `upgrade_hide_spec`, `place_hide` and a
parameterised `build_level(material, level_path, spec_name, write_spec, place, builder_xyz)`; `setup_m6_proving.py`
imports that module (`GT_M6_AS_MODULE=1`), makes the level when missing as `setup_m5_legs.py` makes a leg map (sun, sky
light, atmosphere, fog, player start; **no AGTLegStart**, so `AGTRunGameMode::ResolveLeg` finds no leg and the run is
free roam: no mission, checkpoints, par time or rivals) and places its own actors. The Hide rebuilt through the shared
path is unchanged (12 of 14 ford rocks, 88 stones, 30 rally posts, bear z 2300.0 -> 2300.0).

**The ground.** 3 x 3 components of 2 x 63 one-metre quads = **378 m square** (the import takes any whole number of
components; three is the fewest that hold the loop, its shoulders and the ramps), 379 x 379 verts, heights
-3.8..10.0 m, gentle relief (2.5 m over 150 m, no tilt). Two new spec fields carry what a leg has no use for and every
leg spec leaves empty, so no leg's ground moves: **`FGTTerrainSpec::Planes`** (`FGTTerrainPlane`: a rectangle with a
start, a yaw, a length, a half width, a base height, a grade, a cross slope, a blend, its own roughness and a layer,
laid over the land *after* the roads and fading into what is under it over `BlendM`) and **`Stations`**
(`FGTTerrainStation`: a name, the landing point, a heading, an arc, what lies ahead). `FGTRouteSection` gains
**`FordRockCountOverride`** (-1 takes the spec's `FordRockCount`, as before; 0 leaves a ford clear).

**The loop**: 250 x 120 m with 25 m corners, **697 m**, anticlockwise from the pad at the map's middle. Stations, by
arc (the GTGoto landing point is 10 m before each):

| station | arc | what | the test read there |
| --- | --- | --- | --- |
| pad | 0 (and 697) | 60 x 60 m flat tarmac plane round the start | on the pad, `Surface.Tarmac` |
| forda | 55-85 | ford, DepthM 0.6, 14 of 14 R1 rocks | deepest 61.4 cm within 30 m |
| fordb | 141-177 | ford, DepthM 1.4, no rocks, 4 winch posts | deepest 139.9 cm |
| bog | 236-296 | 60 m Mud, 4 winch posts (both ends, 11 m out) | inside the mud patch |
| (shallow mud) | - | **skipped**: `BogCoreFraction` is the spec's, not a section's, so a second Mud section would have a bog core too | - |
| rally | 356-476 | 120 m, crest +0.9 m / 24 m, compression -0.5 m / 18 m, the banked third corner | section Rally, car on the route |
| track | 480-560 | 80 m, 20 stones, water bars at 30 m, the rut pair | section Track |
| climbs | off route, feet at (-110, -8), (-80, -8), (-50, -8) | three 30 m ramp planes at 15 / 25 / 35 %, each with an 18 x 14 m flat top | grades 15.0 / 25.0 / 35.0 % |
| slope | off route, (-20..20, -58) | 40 m across an 18 degree cross slope | 18.0 degrees |

Ford B's four posts: one on each bank 14 m from mid-channel and 8 m upstream (16.1 m out, ground 1.04 m and 0.31 m over
the water), and one 20 m downstream of each (18.4 m out). **Minimum gap between footprints 13.0 m** (ford A's sheet to
ford B's); every other pair is 15 m or more, and two stretches of the same road meeting (rally into track) is not
counted.

**Getting around.** `GTGoto <station>` (`UFUNCTION(Exec)` on `AGTPlayerController` -> `GTProving::Goto`) puts the car
10 m before the station, upright, at rest, handbrake on, and the player beside it when not seated; `GTGoto list` names
them: pad forda fordb bog rally track climbs climbs25 climbs35 slope. At BeginPlay, on a map whose spec has stations
only, `GTProving::ShowHelp` prints the names and `gt.Water.ExtraRiseCm / FlowScale / Wind / RutWater / RiverLagScale /
Stats` and `gt.Weather.Rain` on screen for 15 s. `FGTM6TestRunner` now takes the level builder's spec asset first and
the `DA_Terrain_Hide` path only as a fallback, so nothing is keyed to a map by name.

**Launch**: `Art/play_proving.bat` (windowed 1600x900, `Saved/Logs/play_proving.log`); the map also opens in the editor
and plays.

**The test**: `proving` (`Art/proving_test.bat`, `-GTProvingTest`, `FGTProvingTestRunner`), 24th in `Art/suite.sh`,
**PASS in 38 s**: 1 landscape, sheets 2/2 fords, patches 1/1 bog, ford rocks 14/14, track stones 20/20, rally posts
6/6, winch posts 8/8 (four per bog, four per ford of 1.0 m or deeper), the car at rest on the pad 3 s after it spawned,
and every station landed at rest (0-1 cm/s, up 0.99-1.00, 8-10 cm over the ground) with the reading above. `terrain`
and `water` on The Hide both PASS after the change (279 s and 304 s) - including the two gates that had been failing on
the unmodified build, which passed this run.

**Unchecked**: nobody has driven or walked it. The stations' spacing, the pad's size, the ramp grades and the slope are
numbers from the brief, not felt ones. The ramps, the tops, the pad and the slope are landscape (they carry the Dirt or
Tarmac surface); their blends stand at up to 60 degrees on the tall ramps' flanks. The deep ford was never driven into,
so "floats and floods" is the depth asked and read, not seen.

## 48. Painterly ground textures (2026-09-20)

The user, 2026-09-20: "bring some painterly textures in". Two sourced CC0 sets on the two rows that cover the most
ground, the mud left as it was (the user: "leave the mud alone"). Nothing painted or generated, nothing tuned touched:
no traction, mud, water, weather or camera number, no terrain spec. Built 2026-09-20, measured 2026-09-22.

- **The sets and the licence.** Both from 3dtextures.me (Katsukagi), whose F.A.Q. page (https://3dtextures.me/about/)
  says "All textures on this site are licensed as CC0."; downloaded 2026-09-20 from each asset's Google Drive folder.
  **Stylized Grass 002** -> `T_GT_Grass_D / _R / _N`, **Stylized Dry Mud 001** -> `T_GT_Dirt_D / _R / _N`, each map
  1024 x 1024, imported by `Art/setup_m6_textures.bat` under `/Game/GrandTour/Textures/Stylised`. The normals are
  imported with the green channel flipped (OpenGL assumed: the site does not say) and **not sampled**; the height and
  AO maps are on disk, not imported. Provenance, pages and file sizes: `Art/Textures/Stylised/SOURCE.txt`.
- **The node.** `M_GT_Landscape` (`build_landscape_material` in `Art/Unreal/setup_m6_hide.py`) gains a second
  tri-planar custom node, `Landscape:groundtex`, beside the mud's: world-position planes weighted by the vertex normal
  at `GroundTriSharp` 6.0 (the mud's), albedo and roughness only, roughness clamped 0.05-1.0. Its parameters:
  **GrassTileCm 350**, **DirtTileCm 250**, **GrassTint / DirtTint (1, 1, 1)** - the texture as its author made it.
  **12** texture samples a pixel (two sets x two maps x three planes) on top of the mud node's **9**: **21**.
- **The rows.** Scrub (the ground away from any road) takes the grass, Dirt (every leg's road and the Proving Ground's
  tracks) the dry mud; Mud and Bog keep the photoreal muddy_tracks set of section 32; Tarmac and Snow
  keep their flat colour and roughness. The build logs `SETUP_M6_HIDE painterly ground: T_GT_Grass_D tri-planar on the
  Scrub row at GrassTileCm 350 cm ...`. Order: `setup_m6_textures`, `setup_m6_hide` (recreates the material asset),
  then `setup_m6_proving` (re-points L_Proving at it); both maps were rebuilt on 2026-09-20.
- **The shots' count gate.** The 2026-09-20 `Art/hide_shots.bat` wrote **33** pictures against **32** expected, a
  default stale since R1 added hide_31: `ExpectedShots` in `GTM6TestRunner.h` 32 -> **33**, `== build exit 0 in 27s`.
  Re-run 2026-09-22: **PASS 33/33**.
- **Tests (2026-09-22).** `terrain` **PASS (316 s)**, `proving` **PASS (36 s)**, `suite: 2 PASS, 0 FAIL`; terrain's
  two flaky gates (step 11 ruts, mud difference sd) passed this run.
- **What the pictures read.** A look, the 2026-09-20 session's, at hide_1_valley, hide_10_rally and hide_6_bog: the
  scrub a vivid painterly green, the rally road orange-tan with dark speckle, the bog's mud pale sandy beside it.
  Pixel means over the lower half of the 2026-09-22 pictures (every fourth pixel), with the share of pixels whose
  green is the largest channel: hide_1_valley **161 176 147, 37.5 %**; hide_10_rally **146 169 98, 68.9 %**; hide_6_bog
  **180 157 117, 0.0 %**. No picture from before the textures is on disk (each run overwrites them), so these are a
  baseline for the next pass, not a before and after.
- **The frame cost**, from the runner's per-step `GTWATERSTATS` lines. **Before**: R1's last ford run (2026-09-18,
  `Saved/Logs/hide_shots-backup-2026.09.19-04.37.24.log`, the run behind section 46), ford steps 22-30: frame
  **11.01-14.61 ms** mean, mean of the means **12.91 ms**, worst **53.03-175.37 ms** plus the **400 ms** level-load
  frame at step 22. **After**: the 2026-09-20 textured full run (`hide_shots-backup-2026.09.20-08.46.01.log`), the same
  steps: **12.59-15.28 ms** mean, mean of the means **14.16 ms** (**+1.25 ms**; every step higher, by 0.43 to 2.15 ms),
  worst **16.04-177.74 ms** (**+2.37 ms** on the worst of the worsts, the load frame left out); the whole run's 32
  step lines **10.06-16.75 ms** mean (**12.77**), one clamp (step 2, 0.159 s). Not like with like: a ford run against
  a full run (the ford run's step 22 holds the load, the full run has 22 steps of play before it) and no full run
  with these lines exists from before the textures, so the +1.25 ms is not the material's alone. **The clean
  2026-09-22 full run** (the day's first run was VOID, `FarCry6.exe` on the same GPU), the same steps: **14.05-16.09
  ms** mean, mean of the means **15.25 ms** (**+2.35** on R1's ford run, **+1.09** on the 09-20 run; every ford step
  above 09-20's, by 0.72 to 1.46 ms), worst **17.39-183.44 ms** (**+8.07** / **+5.70** on the worst of the worsts, no
  load frame in these steps); the whole run's 32 step lines **10.33-16.83 ms** mean (**13.92**, **+1.16** on 09-20),
  one clamp (step 2, the 400 ms load frame, 0.155 s). Steps 0-21, away from the ford, read 12.02 -> **13.45 ms**
  (+1.43) against 09-20 on a build that differs only in `ExpectedShots`: two runs of one build differ by 1.1-1.4 ms,
  the size of the +1.25 ms, so the textures' own cost is inside the run-to-run spread. `sample_ford.ps1` reads the
  ford pictures again (flow frame-diff **13.08 %** on, **0.00 %** off; wake **7.61 %**).

**Unchecked**: the normals' convention (flipped green assumed, nothing samples them); the owner's look at The Hide and
at L_Proving (no picture of L_Proving exists); the photoreal mud beside the painterly grass; the 21 samples' cost on
their own (no run with the node off); why two full runs of one build differ by 1.1-1.4 ms a frame.


## 49. Ford bed, sinkage recovery and buoyant grip (2026-09-22)

The owner, driving L_Proving on 2026-09-22: (1) "in the water or near it the car is super slow, no wheelspin, down on
power"; (2) "climbs up a small invisible ledge when leaving a water area". This was a fix stage, decided by the
orchestrating session from a measured diagnosis: three changes. No tuned number was touched (traction, hull,
drivetrain, water, mud field and rows, weather, camera, either terrain spec's values, materials).

- **The tool (built 2026-09-22 for the diagnosis; documented here).** `-GTFordDiag` (`FGTFordDiagRunner`,
  `Source/GrandTour/Core/GTFordDiagRunner.cpp`, run with `-GTNoLoad`) opens L_Proving headless. It first surveys forda
  and fordb: waterlines, 25 cm profiles (`GTFORDPROF`), the surface changes along three lines at 0 and +-0.78 m, the
  rows and the rocks. Then it drives a dry 30 m on the pad and each ford at full throttle, in high range with open
  diffs, from a standing start 15 m before the water to 15 m past it: the base run, `gt.Water.Hull 0`,
  `gt.Water.Buoyancy 0`, and a repeat of forda. **`Art/ford_diag.bat`** runs it (2 min 20 s on this run) and writes
  `Saved/Logs/ford_diag.log`. **`python Art/tools/ford_diag.py [log] [--rows DIR]`** prints for each run:
  - the entry and exit, and the minimum speed;
  - the force budget at the slowest point and every 2 m;
  - the peak slip ratio;
  - the exit-bank dynamics, the front wheels' sinkage and radius, and the bow wave.
  It then prints the terrain profiles and the rocks. `--rows` writes each run's exit-bank rows to DIR.
  The logger is **`gt.Water.Diag`**: at 1 it writes a `GTWATERDIAG` line every 0.1 s, at 2 every tick; the runner sets
  2 within 6 m of a waterline, so the one-tick numbers below come from that window. The logging code is
  **`Source/GrandTour/Vehicle/GTWaterDiag.h/.cpp`** (`GTWaterDiag::Measure / Format / TickCar`). `TickCar` is called
  last in `AGTCarPawn::Tick` and only reads. The traction component gains the **Diag fields** on `FGTWheelTraction`:
  `DiagSurfaceDrag`, `DiagPloughDrag`, `DiagBellyDrag`, `DiagRutDrag`, `DiagWaterDrag`, `DiagSinkRate`,
  `DiagMaxSink`. They are the terms of RollingResistance's sum; Update writes them and nothing reads them. The result
  line is `GTDRIVETEST_RESULT PASS ford diagnostic (off the gates)`: it gates nothing and is not in the suite.
- **The diagnosis.** forda: 0.6 m deep, 22.45 m of water, a 2100 kg car in high range with open diffs.
  - **Speed.** The crossing took **13.16 s**, with a minimum of **0.85 m/s** 2.2 m before the exit and **1.03 m/s** at
    the exit. The dry pad reaches **14.3 m/s** in 30 m.
  - **The budget at the slowest point.** Tractive force **5846 N** (engine at idle, 1st gear) against:
    - mud rolling **2894** (surface 2470 + plough 293 + belly 129);
    - grade **1933**;
    - tyre water drag **270**;
    - hull drag **162**;
    - about **590** unexplained.
  - **At 6.24 m/s, 2.6 m in.** Tyre water drag **5590**, hull drag **4442** and mud **4576** against **6843** tractive.
    `gt.Water.Hull 0` halved the crossing (**6.76 s**).
  - **No wheelspin.** The peak slip ratio was 0.06-0.20.
  - **Lift did not reach the tyres.** The wheel loads summed to **20580 N**, the dry weight, although the hull lifted
    **2478 N**. The load correction (Weight / SpringSum) normalised the lift away, so buoyancy never cut grip; W2
    flagged this as "no grip cut when wading".
  - **The bed was mud.** The Mud row (SinkageRate 0.08, MaxSinkage 0.22, WetSinkageScale 1.3) covered the bed from
    6.1 m before the entry waterline to 2.4 m past the exit. The banks are Dirt (0.01 / 0.05).
  - **The ground has no step.** The biggest rise is 6.9 cm per 50 cm, the bank's grade, and no rock stands on the line
    near the exit.
  - **The ledge.** It is 2.45 m past the exit waterline, where Mud meets Dirt. There the front sinkage fell from
    **0.220 to 0.050 m in one tick**: the old clamp to the new row's MaxSink. In that tick the wheel radius went from
    16.2 to 33.0 cm and the front load from 4.3 to 14.0 kN (peak 15.2). Over the next 0.18 s the chassis rose 10 cm
    and pitched from 6.4 to 10.0 deg. The rear axle repeated it 2.75 m later (17.5 cm in 0.3 s). The same pop happens
    at every Mud/Bog -> Dirt edge.
- **F1, a firm ford bed.** A new spec field, **`FGTTerrainSpec::bFordBedMud = false`**: with it false, a Ford section's
  paving is painted with the Dirt row (1) over the span that was Mud (2); true restores M6 stage 3's muddy bed. Neither
  spec asset was edited, so both maps follow the C++ default.
  - **It took two builds.** With only the section's paint changed, forda's bed still read Mud from **60.05 to 81.00 m**
    and fordb's from 148.16 to 171.16 m. The mud came from the channel paint in `LayerWeights`, "mud in the bottoms of
    channels, on and off the road". With `MudChannelDepthM` 1.5 that paints mud wherever the stream is dug deeper than
    0.75 m.
  - **The fix to the channel paint.** `FRoadSample::bFirmFordBed` is set on a Ford section when `bFordBedMud` is false.
    The channel's mud is then multiplied by 1 minus the road's paving weight, so it stays off the paving. The stream
    banks beside the road keep their mud. The survey now reads Dirt the whole way (`forda ... 40.00:Dirt/L`,
    `fordb ... 126.16:Dirt/L`).
  - **Tests and maps.** Terrain's two bed checks (the Hide's `crossing(dig ...)` and `ford@...`) expected
    `Surface.Mud`. They now expect whatever `bFordBedMud` asks for and read **Surface.Dirt**. Both maps were rebuilt,
    hide then proving, twice.
- **F2, sinkage recovers at a row change.** In `UGTTractionComponent::Update`'s sinking branch, when `Sinkage >
  MaxSink` the sinkage now comes down at the existing `SinkageRecoveryRate` (0.08 m/s) instead of being clamped to the
  new row's MaxSink. No new number.
  - **Seen in the water.** The first diag run, with the channel mud still in the bed, crossed a Mud -> Dirt line at
    81.00 m inside the water. All four wheels came down **0.219 -> 0.052 m in 2.08 s (126 ticks)**, at most 0.13 cm a
    tick.
  - **The wheel radius** (`GTVehicleTuningComponent`, from the raw sinkage) grew **16.0-16.4 -> 32.1-32.5 cm** over
    those 2.08 s.
  - **The belly term** (`Sinkage - AxleClearanceM`, raw, clearance 0.19 m) stays live only while the sinkage is over
    0.19 m, the first 0.36 s. Its drag fraction went **0.003-0.009 -> 0**.
  - **The drag terms** read `SinkageFraction`, which is clamped to 1. So during the decay they read no more than a Dirt
    wheel at its own MaxSinkage (sd 0.060).
  - **At the exit.** The biggest one-tick load change was **971 N** (9621 before), and the chassis's biggest rise in
    any 0.18 s was **2.1 cm** (10.8 before).
- **F3, the hull's lift takes load off the tyres.** The load correction's target is now **Weight - LiftN**, where
  `LiftN` is `UGTHullComponent::LiftN` in newtons, times 100 to Chaos units. The hull is looked up once on the owner and
  null-safe (no hull, no lift), and the clamp [0.5, 5] and the 5 % guard are kept. The hull ticks after the traction,
  so the target uses last tick's lift. On land LiftN is 0 and nothing changes.
- **Numbers (forda, `Art/ford_diag.bat`, before -> after):**

  | forda | before | after | gate | |
  |---|---|---|---|---|
  | crossing, base run | 13.16 s | **6.92 s** | < 8 s | PASS |
  | min speed in the water, base run | 0.85 m/s | **1.71 m/s** (exit climb, 6.22 m before the exit) | > 2.5 m/s | **FAIL** |
  | biggest one-tick sinkage change, exit -6..+10 m | 17.0 cm | **0.00 cm** | < 2 cm | PASS |
  | biggest one-tick load change, same window | 9621 N | **804 N** | < 3 kN | PASS |
  | chassis ride height (z - mean contact z): biggest rise in 0.18 s | 10.8 cm | **2.4 cm**; the whole rise 4.0 cm over **2.48 s** (10-90 %) | spread > 0.5 s | PASS |
  | wheel loads / (weight - lift) in the water, all four in contact | 1.226 mean (loads = weight) | **1.000** mean, p5 0.982, p95 1.016 | within 5 % | PASS |
  | peak slip ratio in the water | 0.175 | **0.726** per tick (0.684 at 0.1 s); Chaos slipping 243 of 1660 wheel-ticks (34 of 3156) | reported | |
  | max water over the front contacts | 0.759 m | **0.846 m** (the intake is 0.85) | | |
  | repeat run | 12.08 s, 0.69 m/s | **11.94 s, -0.14 m/s**: engine flooded at 72.72 m, front water 0.866 m | as base | **FAIL** |
  | `gt.Water.Buoyancy 0` | 12.45 s, 0.90 m/s | 11.67 s, -0.19 m/s: flooded at 73.34 m, 0.877 m | | |
  | `gt.Water.Hull 0` | 6.76 s, 2.18 m/s | 3.53 s, 4.97 m/s | | |
  | dry pad | 10.18 m/s at 15 m, 14.31 at 30 | 10.18 / 14.31 | | |

  **The budget at the slowest point after** (base run: 1.71 m/s, 16.23 m in, 1st gear, 800 rpm, engine 208 Nm):
  - tractive **5206 N** (grip cap 7984);
  - rolling **3193** (tyre water 1894, surface 1235, plough 62, belly 0);
  - hull drag **1161**;
  - grade **1274**;
  - m*a **-494**;
  - unexplained **71**.
  The hull lifted **6854 N**; the springs read 6430 and the loads sum 13451 against 13726 (weight - lift). The minimum
  is on the exit climb, after the car slows from 9.37 m/s at entry. At 3.6 m in, at 8.12 m/s, the tyres' water drag is
  11798 N and the hull's 9048 N.
- **New: the intake floods at forda.** With a firm bed the car keeps its speed, and the bow wave puts **0.846-0.877 m**
  of water over the front contacts; before the change it was 0.68-0.77 m. That is on the 0.85 m intake. Two of the three
  lift-on runs of the same ford flooded and stalled, 2 cm apart: the repeat and buoy0 flooded and the base run did not.
  So forda's run is no longer the same run to run. The intake was not touched.
- **A cost of F3 on a muddy bed** (the first diag run, bed still Mud from 60 to 81 m): forda_base took **27.12 s**
  (min 0.25 m/s) against 11.03 s for the same run with `gt.Water.Buoyancy 0`. The slowest point was the rear axle in
  the Mud, sunk 0.22 m, loads 3377 and 2740 N, slip 0.878. This bears on whether any ford should get `bFordBedMud`
  back.
- **fordb (1.4 m) floods by design**, as before. The base run flooded at 152.25 m and stuck 6.75 m in, with 1.433 m of
  water over the front and loads 1734 N against weight - lift 1721 N (before: flooded at 152.16 m, stuck 5.78 m in,
  1.285 m).
- **The Hide's ford** (terrain test): its bed reads Surface.Dirt, 61 cm under the water. Every ford step passed:
  - as built, through at 1145 m with water up to 0.74 m;
  - raised 70 cm, flooded;
  - held, 0.07 m in 6 s;
  - the wheels carry **57.7 %** of the weight (asked over 55);
  - carried 5.89 m in 10 s;
  - floats and winched.
- **Tests (2026-09-22).** Build `== build exit 0 in 42s`, then `in 5s` after the channel fix. The partial suite
  `terrain proving water grip mud`:
  - `PASS terrain (261s)`: the bog escape **13.4 m in 12.0 s** from a dead stop (band 13.0-15.0), reverse **5.7 m in
    8.0 s**, "clear 6 m off" **92 of 92** (asked 88, 0.95), the edge crawl through at 294 cm/s. Terrain's two flaky
    gates passed this run (step 11 ruts faster 1 / slower 1; mud difference sd 0.23 cm).
  - `PASS proving (32s)`, `PASS grip (38s)`, `PASS mud (21s)`.
  - **`FAIL water (288s)`** on one gate, the bow step's "the middle back within **+1.54 cm** of where it stood before
    the car 20 s after (asked 1.5 ...)". Every other water gate passed.
  - `== suite: 4 PASS, 1 FAIL (failed: water)`.
- **The full suite.** **`== suite: 22 PASS, 2 FAIL (failed: terrain water)`**; the body, winch and loot tests passed, so
  nothing was rerun. `FarCry6.exe` started at 19:42:27 local, during this run (19:38-19:57), and was left running.
  The ford diag and the partial suite ran before it.
  - **`FAIL terrain (264s)`** is the known step 11 ruts flake: "exit at 30 deg, the hold on: 15.0 m in 8.6 s ... ->
    slower than down the ruts 0". Every other terrain gate passed. The bog escape read **13.1 m** forward, **5.8 m**
    reverse, and clear 6 m off **92 of 92**.
  - **`FAIL water (292s)`** is the same bow gate, **+1.97 cm**. The cause shows in the gate's own line: the test's car
    now passes mid-ford at **6 km/h** where it went **3 km/h** (bow 11.05-12.56 / -13.03 to -15.74 cm, against 20.60 /
    -6.70). That is the firm bed. The day's run before the change (`water_test-backup-2026.09.23-01.10.20.log`) read
    **+1.19 cm at 3 km/h**, PASS, and 2026-09-19's read +0.97. The gate was not re-gated or tuned; that decision
    belongs to the orchestrator or the owner.
- **Unchecked.**
  - The owner's feel at either ford.
  - The Hide's ford is undriven.
  - The unexplained force: 71 N at the slowest point after, but **-820 to +1390 N** along the 2 m table (about 590
    before). Its cause is unmeasured.
  - The crossing speed with a firm bed is the number for the owner to name; `WaterDragPerMetre` 2.4 and `DragCd` 1.0
    are the knobs and were not touched.
  - Whether the new intake flooding at forda is wanted.
  - The bog exits' rise with F2 is unmeasured by the diag. Terrain's bog numbers hold.
  - Whether the water test's bow gate should be re-gated for a 6 km/h pass. Its speed doubling follows the firm bed,
    but whether F3 plays a part is unmeasured.
  - No picture was taken: the look of the Dirt bed under the water is unchecked.

## 50. Housekeeping: the water settle gate and the intake decision (2026-09-22)

Stage S0 of `docs/RIVERBED_PLAN.md`. It changed one test step and recorded one decision. No tuned number was touched.

- **The problem.** The water test's bow step has failed on one gate since section 49: "the middle back within 1.5 cm
  of where it stood before the car 20 s after". It read **+1.54** and **+1.97 cm**. With the firm Dirt bed the test
  car crosses mid-ford at **6 km/h** on full throttle. On the Mud bed it went through at 3 km/h and read +1.19 cm
  (2026-09-22) and +0.97 (2026-09-19).
- **What was done: a speed hold, not a re-gate.** The gate asks whether a 3 km/h wake dies, and the runner already
  holds speeds (the track run's bang-bang at 40 km/h, `GTM6TestRunner.cpp:2374`). So the crossing now holds 3 km/h
  where the gate reads, and the gate keeps its meaning and its 1.5 cm.
  - **The change.** `FGTM6TestRunner::TickWater`, the bow step's phase 0 (`GTM6TestRunner.cpp:3812-3833`). Within
    10 m of mid-ford (arc 1105-1125 m of 1090-1140, the stretch the settle line covers) the throttle comes from a PI
    on the measured speed: target **83 cm/s**, gain 1/60 per cm/s, integral 1/60 per cm, both clamped to 0-1.
    Outside that stretch the car runs full throttle, as before (in at 20 km/h, low range, locked).
  - **New members** (`GTM6TestRunner.h`): `WaterHoldIntegral`, `WaterHoldSeconds`, `WaterHoldMinCms`,
    `WaterHoldMaxCms` and `WaterHoldBandSeconds`, reset at the step's start.
  - **Logging.** The "out of the ford" line now reports the held stretch: its time, the mean over the 20 m, min, max,
    and the share of the time spent in 2.0-4.0 km/h. The gate's text adds "the middle 20 m held at 3 km/h since
    section 50".
- **Two runs.** The first try was the track run's bang-bang, with a 75-90 cm/s band and 0.3 throttle inside it. The PI
  replaced it because the bang-bang run took 17.0 s for the whole step, too short for a true 3 km/h over 20 m (24 s).
  The held-stretch readings were added with the PI, so the bang-bang run has none.

  | | bang-bang (first try) | PI (kept) |
  |---|---|---|
  | out of the ford | 17.0 s | 17.8 s |
  | speed at mid-ford (the gate's own reading) | 3 km/h | 3 km/h |
  | bow crest / trough, at mid-ford | 19.38 / -9.32 cm | 19.87 / -9.99 cm |
  | the held 20 m | unlogged | **11.2 s**: mean 6.43 km/h, min 2.05, max 45.90, **83 %** of the time in 2.0-4.0 km/h |
  | the middle vs before the car, 10 / 20 / 30 s | +1.14 / **+1.45** / +1.02 cm | +0.87 / **+1.22** / +1.19 cm |
  | volume change | | 0.181 % (asked under 0.5) |

  - **The held 20 m are not all at 3 km/h.** The car comes into the stretch at speed, and the mean of 6.43 km/h with
    83 % of the time in band means most of the distance went by in the first couple of seconds.
  - **The 45.90 km/h maximum** is a single reading. Its cause is unmeasured.
  - **The whole step** took 17.8 s against 24.0 s for the old mud-slowed crossing. The profile differs, but the
    reading at mid-ford is the same.
- **Tests (2026-09-22).** Build `== build exit 0 in 46s`, then `in 38s` and `in 16s`. The machine was checked before
  every run: no editor, no GrandTour process, no FarCry6.exe.
  - `PASS water (294s): water: current 1.44 m/s where the route crosses (asked 1.5 +/- 20 %, 31.6 cm of head would read 1.5); the middle line's discharge mean 1.30 m/s, ten points 1.17 (0.57-1.44) over 0.36 m of water, 23.0 m`
    - Every sub-line of the result reads `-> 1` (13 of 13).
    - The bow gate: `the middle back within +1.22 cm of where it stood before the car 20 s after (asked 1.5, ...; the middle 20 m held at 3 km/h since section 50; ...)`.
    - The bang-bang run also passed, at +1.45.
  - `FAIL terrain (263s)` on step 11's ruts flake only, left alone as the plan says. It read `exit at 30 deg, the hold on: 15.0 m in 10.6 s ... -> slower than down the ruts 0`
    against the first pass's 13.4 m in 12.0 s. The other 22 verdicts read `-> 1`, including the Hide's ford
    "winched: at the post in 22.5 s".
  - **The full suite** ran after both stages were built, in the foreground in six calls (the tool's limit is 10
    minutes a call): **23 PASS, 1 FAIL** (terrain, the ruts flake). The 20 lines not quoted here are in section 51.
- **The intake decision (plan section 4, item 1).** The owner, 2026-09-22: "Keep it as 'drive fords slowly'". Section
  49 found that forda at full throttle floods the intake, with 0.846-0.877 m of water over the front against
  `IntakeHeightM` 0.85 (`GTConditionComponent.h:208`). That stays: fords are driven slowly. Nothing was changed.
- **Unchecked.**
  - Only two runs: the gate's margin (0.28 cm on the PI run) is unmeasured across runs.
  - The held stretch's speed trace is logged only as time, mean, min, max and share in band.
  - What the 45.90 km/h reading is.

## 51. Winch release (2026-09-22)

Stage S1 of `docs/RIVERBED_PLAN.md`, with the owner's decision on its item 4 (2026-09-22): "stow the hook, rewind
visibly". Before this, once the hook was on an anchor nothing reached `UGTWinchComponent::Release()` but a lost or
failed anchor. No winch number changed apart from the new `RewindSpeed`.

- **The keys, as the plan's S1 entry names them.** The brief asked for G on foot; the plan names E, and the plan was
  followed. On foot, G still only drops a carried hook.
  - **On foot, at the anchor.** Empty-handed at the anchor a winch holds, E offers **"Detach winch hook from <name>"**,
    hold 0.5 s, the same as attaching.
  - **On foot, at the nose.** At the front (car-local X over 150 cm) while the hook is on an anchor and no tool is in
    hand, E offers **"Release winch"**, hold 0.3 s, the same as taking the hook. Before this change it fell through
    to "Get in".
  - **In the seat.** **G** or **DPad Up**, through a new action, IA_ReleaseWinch. It acts only while the hook is on an
    anchor.
- **The release.** `Release()` (`GTWinchComponent.cpp:143`) first reads where the hook is: the anchor, or the
  carrier's hand 70 cm down, as `TakeHook` draws it. Then, as before, it forgets the anchor and the carrier, sets
  Stowed, zeroes TensionN and stops the reel.
  - **The pull ends at once.** `Update` applies no force while Stowed, so the force is gone on the tick `Release()`
    runs. The cable is still a force, never a constraint.
  - **The visible rewind** (`StartRewind` `:204`, `UpdateRewind` `:222`, called from `Update`'s stowed branch
    `:256`). The cable's end is held in the body's space at the hook's position, so it rides with the car. The drawn
    length starts at the larger of the drawn length and the straight run to the hook. Each tick takes
    `RewindSpeed` x dt off it, so any slack comes in first and then the end walks down the straight line to the
    drum. At 0 the cable hides.
  - **`RewindSpeed` = 500 cm/s** (`GTWinchComponent.h:121`), a full 25 m in 5 s. It is proposed and unmeasured by
    eye; the owner names it.
  - **What cancels a rewind.** `TakeHook` and `AttachTo` cancel one in progress. `Snap` still hides the cable at once.
    Dropping a carried hook and getting in with it also rewind now, from the hand.
  - **New calls:** `GetDrawnCableCm()`, `IsRewinding()` and `IsReeling()`. `Describe()` gains `drawn=`.
- **The anchor knows its winch.** `UGTWinchAnchorComponent::HeldBy` (`GTWinchAnchor.h:38`) is set by `AttachTo`
  (`GTWinchComponent.cpp:124`). `ForgetAnchor` (`:193`) clears it in `Release`, `Snap`, `TakeHook` and a re-attach.
  - **Offer and action.** `GTGreybox::AnchorOffer` gives the detach offer (`GTWinchAnchor.cpp:59`), and `AttachHook`
    calls that winch's `Release()` (`:74`).
  - **Harvest nodes** share these two functions (`GTHarvestNode.cpp:168,178`), so they get the detach too. This is
    untested; harvesting is a placeholder and nothing was built on it.
- **The car** (`GTCarPawn`).
  - **On foot:** `ECarInteraction::ReleaseWinch` (`.h:335`), resolved at `.cpp:356`, offered at `:390`, acting at
    `:426`.
  - **In the seat:** `ReleaseWinchAction` (`.h:271`) is loaded as `IA_ReleaseWinch` (`.cpp:658`) or made at run time
    (`:675`).
  - **Mapping:** G and `Gamepad_DPad_Up` in `BuildDrivingMappings` (`:632`), and `EnsureMapped` (`:701`) adds them to
    the existing IMC_Driving asset for the run. That asset was not rewritten.
  - **Binding:** on Started (`:745`), to `OnReleaseWinch` (`:794`).
  - **Setup:** `UGTVehicleSetupLibrary::CreateDrivingInputAssets` writes an IA_ReleaseWinch asset the next time
    `Art/setup_m1_input.bat` runs (`GTVehicleSetupLibrary.cpp:104`). It was not run.
  - **HUD:** the attached line reads "Winch attached  x m  y kN   G  release" (`GTHUD.cpp:360`).
- **The test** (the winch test, `FGTM2TestRunner::TickWinch`, `GTM2TestRunner.cpp`). The old steps 3-6 are now
  4, 5, 7 and 8, unchanged.
  - **Step 2**, after the attach, reads the post's offer; nothing is pressed.
  - **New step 3** (`:463`) stands at the nose and reads its offer; nothing is pressed.
  - **New step 6** (`:514`), the release:
    - It reads the car's driving context for the action's keys.
    - It loads the cable (handbrake on, reeling until 2000 N).
    - It presses IA_ReleaseWinch through `UEnhancedInputLocalPlayerSubsystem::InjectInputForAction`, with the car's
      input on for the step. This goes through the binding a key press reaches.
    - It reads the state and the tension, then the drawn length every tick until it is 0, then re-attaches with
      `AttachTo` and reads both AttachCounts.
  - **The gate** (`:691`) takes all of these:
    - both offers;
    - G and DPad Up mapped;
    - attached -> stowed -> attached;
    - tension above 0 before and 0 at and after the release;
    - a rewind over 0.2 s that ends hidden and never lengthens;
    - two attaches on the winch and two on the post.
  - **The first version** pressed at the end of the reel, on a slack cable (0 N before the release), which proves
    nothing about the force. The load phase was added and the test rebuilt.
- **Numbers (winch test, 2026-09-22):**

  | | read |
  |---|---|
  | offers | post "Detach winch hook from strong post" 1, nose "Release winch" 1 |
  | IA_ReleaseWinch mapped | G 1, DPad Up 1 |
  | pressed | 0.02 s into the step, under **2133 N** |
  | released | 0.001 s after the press, attached -> stowed |
  | tension | **2133 -> 0 N**; the highest after the release **0 N** |
  | drawn cable | **1275 cm -> 0 in 2.55 s** over 4137 ticks (1025 at 0.5 s, 775 at 1.0, 275 at 2.0, 25 at 2.5), never lengthening, hidden at the end |
  | re-attached | stowed -> attached; AttachCount winch **1 -> 2**, post **1 -> 2** |

  - **The car kept rolling toward the post** after the release: the distance went from 1275 to 955 cm by the
    re-attach, with 0 N on the cable. Its speed at the release was not logged.
  - **Then** the wall step snapped the re-attached cable (winch health 0.49), and the rotten post tore out.
- **Tests (2026-09-22).** Build `== build exit 0 in 46s`, then `in 38s` (the load phase).
  - **The first test run** (slack release: 1278 cm in 2.56 s, attaches 2 / 2) also passed winch and onfoot.
  - **The second test run:**
    - `PASS winch (27s): winch: release ok=1 (offered post=1 nose=1, keys G=1 DPadUp=1, by the action=1, tension 2133 -> 0/0 N, rewind 1275 cm in 2.55 s at 500 cm/s, 4137 ticks, monotone=1 hidden=1, attaches winch 2 post 2) hoo`
    - `PASS onfoot (23s): on foot: exit=1 contexts=1 exitDist=179 walked=427 bobMax=1.97 bobOff=0.00 bareRefused=1 cutterOffered=1 wire=2 repairOffered=1 radiator=0.90 scrap=2 bootWire=2 overfill=18 weightOk=1 exposureHazard=60`
  - **The full result line** from the log: `GTDRIVETEST_RESULT PASS winch: release ok=1 (...) hookOffered=1 taken=1 tether maxDist=2500 clamps=2651 ok=1 attachOffered=1 attached=1 pulled=882 cm maxTension=17871 N reelOk=1 snapped=1 winchHealth=0.49 weakFailed=1`.
    The winch test did not flake, so it was not rerun.
  - **The rest of the full suite**, run after both stages, all PASS: base 12 s, body 17, bodystate 25, door 18,
    drive 18 (`mappings=27`), drivetrain 46, env 33, grip 38, hazard 26, leg 21, loop 13, loot 12, mud 21,
    proving 33, rough 21, spray 25, surface 32, tour 19, track 27, weather 24. Water and terrain are in section 50.
  - **A pre-existing log line.** Every run ends on `LogPawn: Error: DisableInput can only be specified on a Pawn for
    its Controller`; it is in logs from 2026-09-19 too.
- **Docs.** `ARCHITECTURE.md` 6e gains the release, and section 7's key lists are brought to the code. They were
  stale: they named Recentre, Headlights, Pause and an IMC_UI, none of them built.
- **Unchecked.**
  - The owner's try, at fordb's posts on L_Proving: E on the post, E at the nose, G / DPad Up in the seat.
  - The rewind's look and its speed. No picture was taken; a NullRHI run draws nothing.
  - During the rewind the end rides with the car, straight at the drum; it does not fall or drag on the ground. How
    that looks is unchecked.
  - The test reads the two on-foot offers but does not press them.
  - The car's keys are checked as mappings, and the press is an injected action, not a key event.
  - The detach on harvest-node anchors.

## 52. No sinking without deformation (2026-09-23)

Stage S2 of `docs/RIVERBED_PLAN.md`, with the orchestrator's three additions: a ramp at the box's edge, the decisions for
the plan's section 4 (items 2, 3 and 7), and before/after numbers for every test the change could move. The owner drove
S1 ("winch works fine") and said "go ahead with S2". No tuned number moved; the two new numbers are marked proposed.

- **The owner's report and picture 1** (section 1 of the plan): "The wheels clip into the ground in riverbeds." In the
  picture every visible wheel of the estate car sits deep in flat, pale, undeformed ground beside a water body (the
  orchestrator's look, not a measurement).
- **M1 as found** (plan section 2): the Chaos radius shrinks by the traction's whole sinkage everywhere
  (`GTVehicleTuningComponent.cpp:112-119`, at most 0.6 x 38 cm), but only a mud patch deforms. Outside the patches the
  shrink came from the channel paint (Mud wherever a channel is dug past 0.75 m, `GTTerrainGenerator.cpp` LayerWeights),
  from wet Dirt (15 cm) and from L_TestTrack's Mud and Snow lanes, so wheels sank into ground that never moved.
  `GTDrivetrainComponent.cpp:79-84` scales the grip torque cap by the Chaos radius, so the radius is a movement lever.
- **(a) No Mud or Bog outside a patch box.**
  - **The box moved into GTTerrain.** `GTTerrain::MudPatchBoxCm` (`GTTerrainGenerator.cpp:540`, declared `.h:637-639`
    with `MudPatchMarginCm` 200) is `UGTMudSubsystem::BuildPatches`' old loop unchanged: the section's route points every
    2 m, each +- the half width there + 200 cm, as one axis-aligned box. `BuildPatches` calls it
    (`GTMudSubsystem.cpp:103`); the subsystem's own `MarginCm` is gone. `BuildProfiles` keeps every box in
    `FGTTerrainProfiles::MudBoxesCm` (`.h:600-601`).
  - **The paint.** At the end of LayerWeights (`GTTerrainGenerator.cpp:708-731`), before snow, any Mud (layer 2) or Bog
    (layer 5) weight at a point outside every box goes to Dirt (layer 1). The channel bottoms, the edge of a bog's paving
    past its box, a Mud span, line or plane all become Dirt; inside a box nothing changes. `bFordBedMud` (off on both
    maps) can no longer paint a ford bed Mud unless the ford lies in a box.
  - **The survey** (`GTProving::SurveyMud`, `GTProvingGround.cpp`): one WorldStatic trace down per grid point over the
    whole landscape, a stone, post or sheet in the way ignored and the trace repeated; it counts the Surface.Mud and
    Surface.Bog hits inside and outside the patches' boxes and puts the outside ones down to a channel (its line + radius
    + 5 m) or a box's 10 m fringe. The ford diag logs it on L_Proving every 1 m; the terrain test logs it on the Hide
    every 2 m and **gates it at 0** (new, `GTM6TestRunner.cpp:2862`, `bMudSurveyOk` in the terrain test's final gate).
  - **Counts, before (the old maps) and after (both rebuilt, hide then proving):**

    | map | step | samples | Mud / Bog inside the box | Mud outside every box | Bog outside |
    |---|---|---|---|---|---|
    | L_Proving | 1 m | 143,641 | 752 / 699 | **2,511 -> 0** (forda's channel 1,166, fordb's 1,296, the bog's fringe 49) | 0 -> 0 |
    | L_Leg03 (the Hide) | 2 m | 1,018,081 | 145 / 143 | **2,750 -> 0** (the stream's channel 2,749, the bog's fringe 1) | 0 -> 0 |

    Forda's channel had 1,166 m2 of Mud-dominant ground outside any patch; picture 1's pale ground beside the water fits
    it, which is as far as a count goes (the plan's item 3).
- **(b) The visible shrink only inside a patch box.**
  - **Where it lives.** `UGTTractionComponent::Update` (`GTTractionComponent.cpp:261-289`), after the sinkage and the F2
    decay. `bInPatchBox` is `PatchAt(contact)` (the box, not `bInMudPatch`, which also wants the Mud or Bog tag), kept
    from the last tick in contact. The shrink the tuning applies is the new `VisibleSinkage` (`ModifyTuning`, `:489`).
    Drag, grip, the belly and the F2 decay keep the raw `Sinkage`; the bog's physics is unchanged (the bog is a patch).
  - **The cap: `OutsidePatchSinkCapM` 0.05 m** (`GTTractionComponent.h:176`; Dirt's MaxSinkage; proposed 2026-09-23,
    unmeasured by the owner). Outside every box the shrink target is min(Sinkage, cap). Wet Dirt's 15 cm is capped.
  - **The ramp: `VisibleSinkRiseRate` 0.3 m per m** (`.h:184`; proposed 2026-09-23, unmeasured by the owner). The applied
    shrink is max(target, min(previous - rate x ground travelled, Sinkage)): no limit sinking in, at most 0.3 m back per
    metre of the contact's horizontal travel, never deeper than the raw sinkage (so a wheel standing still still comes
    up by F2's 0.08 m/s). Inside a box it equals the raw sinkage exactly, as before.
  - **Console variables:** `gt.Mud.SinkCap` (1; 0 lets the shrink follow the raw sinkage everywhere, as before this
    section) and `gt.Mud.SinkRiseRate` (-1 the property; the diag sets 1000 to measure the ledge the ramp removes).
    `GTWATERDIAG` wheel segments gain `vs=` (the visible sinkage, m) and `pb=` (in a box).
- **The box's edge (the orchestrator's addition 1).** The ford diag gained four bog runs on L_Proving
  (`GTFordDiagRunner.cpp`, `BeginBogRun`/`TickBogRun`/`EndBogRun`): low range, locked, full throttle from a dead stop
  after 3 s on the handbrake, logging every tick within 3 m of the box's edge (`edge` lines: each wheel's distance past
  the nearest side, visible and raw sinkage, radius, box, tag; the chassis Z). The distance is measured square to the
  side; the side runs cross it at 35 degrees, so 1 m past is about 1.7 m of travel. The per-tick load and radius steps
  below come from the `GTWATERDIAG` lines of the same runs.

  | run (after) | wheels at the edge (visible / raw cm, m/s) | visible at the cap | biggest one-tick chassis rise | biggest one-tick radius rise, load rise |
  |---|---|---|---|---|
  | bog_right: out of the side where the Mud reaches it | 21.9/22.0 0.24, 21.9/22.0 0.23, 21.8/22.0 0.34, 21.0/22.0 1.93 | **+0.24 to +0.31 m** past | **0.42 cm** | 1.10 cm, +1,596 N |
  | bog_right_noramp (rate 1000) | 5.0/22.0 on crossing, all four | +0.00 m | 0.81 cm | **17.30 cm (15.7 -> 33.0), +12,404 N (1,136 -> 13,540)** |
  | bog_left: out of the side past the bend's scrub | one wheel 8.5/11.5 at 6.14 m/s, three at the cap | +0.13 m | 0.73 cm | 3.40 cm, +4,096 N |
  | bog_end: along the route past the section's end | all four at the cap (8 m of Dirt inside the box first) | on crossing | 0.05 cm | 0.00 cm, +529 N |

  - **Gates:** chassis rise under 2 cm, **0.42 cm**; the shrink at the cap within 1.0 m past the edge, **0.31 m**. Both
    pass. Without the ramp the chassis still rose only 0.81 cm in one tick at crawl speed, but the wheel grew 17.3 cm
    and its load 12.4 kN in one tick: section 49's ledge (16.2 -> 33.0 cm, 4.3 -> 14.0 kN). With it, 1.1 cm and 1.6 kN.
  - **Before** (the old map, `gt.Mud.SinkCap 0`): the left run's deepest wheel crossed at 9.6 cm and came up to 5 cm
    2.00 m past by F2; chassis 0.62 cm. The right and no-ramp runs did not exist yet.
  - **Unmeasured:** a wheel leaving a box deep at speed. The deep crossings above were crawls (0.2-1.9 m/s); at 6 m/s the
    ramp gave 3.4 cm of radius per 16.7 ms tick.
- **The ford diag, before (old map, cap off) / after** (`Art/ford_diag.bat`, `python Art/tools/ford_diag.py`):
  - **forda_base:** waterline to waterline **6.97 -> 6.95 s** (the gate: under 8 s), min 1.72 -> 1.71 m/s, not flooded
    (front 0.831 m).
  - **forda's exit bank, per tick:** radius step **0.0 -> 0.0 cm**, contact step 1.1 -> 1.1 cm, load step +780 -> +763 N.
    The applied radius on the bank **33.4 cm** both times: the route's banks have been Dirt since section 49, and Dirt's
    raw 4.6 cm there is under the cap. The channel's bank off the road is the picture's.
  - **forda_base_repeat:** 11.93 -> 11.93 s, flooded at arc 72.70 (front 0.874 m over the 0.85 m intake): the
    bow-wave flood of section 4 item 1, not S2. The crossing time is two-valued on it.
  - fordb's three runs stay stuck (1.4 m, the car floats and floods), as before.
- **The picture** (the orchestrator's addition 2, item 7): `Art/proving_shots.bat`, a new picture mode for L_Proving
  (`Core/GTProvingShotsRunner.cpp`, `-GTProvingShots` with `-RenderOffScreen`, log `Saved/Logs/proving_shots.log`,
  pictures in `Saved/Screenshots/Proving`, `-GTShotsFrom=N` through the .bat's first argument; later stages add steps
  after step 1). Step 1 parks the car on forda's channel bank: 19 m south of the crossing along the channel at
  (70, -19) m, where the dig is 2.0 m or more under every wheel (Mud-dominant before this section), dry, 5 cm across the
  wheels, outside every box; it settles on the handbrake (raw and visible sinkage 5.00 cm after 18 s, Chaos radius
  33.5 cm, Surface.Dirt). Then a picture from each side at 70 cm eye height 4.5 m out, and a control: the same car on a
  climb's flat Dirt top (2 cm of relief) from its sunlit side. The runner logs, per wheel on the camera's side, a box
  round the drawn tyre's lower half, the drawn tyre's lowest point (the bone - 38 cm) and the ground under its outer
  face; `Art/tools/sample_wheels.ps1` finds each column's lowest tyre pixel.
  - **The tyres are grey, not dark**, so the sampler tells the tyre from the ground by colour (the Dirt is brown, red
    over blue by 35 or more). On the shade side a grey tyre reads like the car's shadow around it, so that picture is
    not measured.

    | picture | wheel | lowest tyre pixel vs the ground line at the face | the drawn lowest point vs the line |
    |---|---|---|---|
    | proving_01_bank_left (sunlit) | w0 | **7.8 px above** | 8.3 px below |
    | proving_01_bank_left (sunlit) | w2 | **6.5 px above** | 8.7 px below |
    | proving_02_bank_right (shade) | w1, w3 | not measured | 8.6, 7.5 px below |
    | proving_03_flat_sunlit (control) | w0, w2 | **9.1, 9.7 px above** | 8.8, 8.6 px below |

  - **Read:** 38 cm of drawn radius projects to 66 px there (1.74 px per cm). The geometry puts the drawn tyre 4.6-4.8 cm
    under the bank; the picture shows the tyre ending 6.5-7.8 px (about 4 cm) above the ground line, and the same
    offset, 9.1-9.7 px, on the flat control. So the offset is not the bank's relief; it lies between the runner's model
    of the drawn tyre and what renders (the tyre mesh's radius against 38 cm, or where the wheel bone sits in it).
    Unchecked; the owner looks.
- **The six movement tests, before (old build) / after** (`bash Art/suite.sh drivetrain grip mud surface track spray`;
  a first "before" run was void, FarCry6 started during it; the after column is the stage's run, then the full suite's):

  | test | before | after | full suite |
  |---|---|---|---|
  | drivetrain: split-mu open / locked, ramp low, reverse | 193 / 1333 cm, 11.9 m, -899 cm/s | 193 / 1328, 11.9, -896 | 193 / 1327, 12.0, -897 |
  | grip: tarmac / dirt mean | 0.87 / 0.48 g | 0.87 / 0.47 | 0.87 / 0.47 |
  | **mud** (L_TestTrack's Mud lane, pull-away) | **593 cm/s, 2877 cm** | **538, 2771** | **536, 2750** |
  | **surface**: speed into / out of the Mud lane | 2187 / **1299** cm/s | 2188 / **1164** | 2188 / **1164** |
  | track: Mud ruts L/R, Snow L/R | 1.75/1.78, 1.55/1.60 | 1.73/1.76, 1.58/1.59 | 1.75/1.75, 1.59/1.59 |
  | spray: dust / mud / snow | 120 / 94 / 94 | 120 / 88 / 94 | 120 / 92 / 94 |

  - **A movement change, reported, not re-gated:** the Mud lane is patchless, so the wheels there now sink 22 cm raw but
    shrink 5 cm. The pull-away is **9 % slower** (593 -> 538/536 cm/s; the void run read 598) and the car leaves the Mud
    lane **10 % slower** (1299 -> 1164 cm/s; the void run 1235). The likely lever (unmeasured): a 16 cm Chaos radius turns the
    drivetrain's torque into about twice the tyre force a 33 cm one does, like a lower gear. Every gate still passes (mud: 400 cm/s and 8 m), so
    nothing was re-gated. The track, grip, drivetrain and spray numbers moved within their run-to-run spread.
- **Terrain** (`bash Art/suite.sh terrain`), before (old map, cap off) / after / full suite:
  - Survey gate: Mud outside 2,750 (FAIL) -> 0 -> 0.
  - The bog's middle at 30 km/h: body 27 -> 28 -> 29 cm lower (asked 7); escape forward from a dead stop 13.4 -> 13.3
    -> 13.6 m (asked 13.0-15.0); reverse 5.2 -> 6.0 -> 6.0 m; clear 6 m off 92 of 92 each time (asked 88, 0.95); the
    edge crawl through, body 23 cm lower each time. The rut field: rut mean -35.0 -> -34.7 cm.
  - The edge crawl starts outside the box with 16 cm of raw sinkage carried from the step before: Chaos radius 21-22 cm
    before, 33 cm after (the cap working); inside the box 16 cm (22 cm raw) in both.
  - All three runs failed only step 11's ruts flake ("exit at 30 deg, the hold on ... -> slower than down the ruts 0").
- **Proving:** `PASS proving (33s)`, and `(34s)` in the full suite.
- **The full suite**, in three foreground batches after the stage: 10 PASS, 12 PASS, then `PASS water (319s)` and
  `FAIL terrain (260s)` on the ruts flake: **23 PASS, 1 FAIL**. `FarCry6.exe` started at 12:10:12, 27 s before the
  water test ended: its last steps' timing numbers are void. The ruts flake was rerun once on its own at 13:15 (`bash Art/suite.sh terrain`): PASS (the stage agent was interrupted before it could write this line; the orchestrator read the log).
- **Builds:** `== build exit 0 in 55s`, then 18, 17, 10 and 21 s (the survey's regions, the right and no-ramp runs,
  the occluder and sun side, the flat control). The machine: no editor or GrandTour process at any run; FarCry6 from
  09:25 to 11:05 (no build or run in that time after the void "before" suite) and again from 12:10.
- **Decisions recorded in the plan's section 4:** item 2, the 5 cm cap is the starting number; item 3, yes, channel
  floors go Mud -> Dirt; item 7, a picture mode for L_Proving, built here.
- **Unchecked.**
  - The owner's look at the wheels on forda's channel bank, and the tyre's 4-5 cm offset in the pictures.
  - The feel of the ramp out of a box, of the cap on wet Dirt, and of L_TestTrack's Mud and Snow lanes, now 9-10 %
    slower in the tests.
  - The cap (5 cm) and the rise rate (0.3 m per m): proposed, for the owner to name.
  - A deep wheel leaving a box at speed; the Snow lane's numbers (the tests read its ruts, not its speed).

## 53. The water fills its basin (2026-09-23)

Stage S3 of `docs/RIVERBED_PLAN.md`, with the owner's decision (plan section 4 item 5, "let the ponds stand still") and
the orchestrator's four notes. The owner looked at S2 ("wheels look fine") and said "go ahead with S3". The code was
written while FarCry6.exe held the machine (13:55-14:12, no run); the coordinator reported it closed at 14:20 and every
build and run below is from 14:20 on, each after a clean `tasklist` (no FarCry6, editor or GrandTour at any run).
No tuned water, mud or traction number moved; the new numbers (margin, cap, still-water threshold) are proposed.

- **The owner's report and picture 2** (plan section 1): "The water only covers a square of the pond." The
  orchestrator's look: a rectangular pale-blue sheet with a straight far edge inside a larger pale hollow.
- **M2 as found.** The box was the placed actor's (section + 24) x 30 m (`setup_m6_hide.py` `place_ford_sheet`), X
  along the flow = the 30 m. `FGTWaterField::Init` gave water to every cell under the level; **so did `Calm` and
  `ShiftLevel`** ("a dry cell fills to the new level"), and `ApplyBoundary` held its head on every end-column cell.
  `AGTWaterSheet::Covers` was the actor's cube, so the car read no water past the straight edges, and **a covered dry
  cell answers its bed as the surface**: a point sunk under the bed inside the box read "ford water" (found below).
- **The survey, `GTFORDFILL`** (`FGTWaterBasin`, `GTWaterField.h:420`, `GTWaterField.cpp:1295`; logged by
  `AGTWaterSheet::LogBasin`, `GTWaterSheet.cpp:62`, at every sheet's first tick, `:313`): a 4-connected flood fill over
  `BedZAt` at `GetLevelCm()` on a 25 cm lattice in the field's axes (X along the flow), 200 m a side (`GTBasinSearchCm`,
  `:59`), from the lowest bed cell in the placed box. Read from the before runs; the ford diag's and the water test's
  logs after carry the same lines (distances from the sheet's centre; "left" is +Y of the flow):

  | ford | level | the wet region along the flow | across it | cells / m2 | the placed box | past it | hollows in the box | search edge |
  |---|---|---|---|---|---|---|---|---|
  | forda (L_Proving, Water_0) | -87.2 cm | -44.00 to +32.25 m (76.25 m) | -16.00 to +12.75 m (28.75 m) | 26,979 / 1,686 m2 | 30 x 54 m, 25,920 cells | upstream 29.00, downstream 17.25, sides 0 | 0 | no |
  | fordb (L_Proving, Water_1) | -162.2 cm | -44.00 to +35.00 m (79.00 m) | -12.50 to +10.75 m (23.25 m) | 24,686 / 1,543 m2 | 30 x 60 m, 28,800 | upstream 29.00, downstream 20.00, sides 0 | 0 | no |
  | the Hide (L_Leg03, Water_2) | 2510.0 cm | -37.50 to +100.00 m (137.50 m) | -100.00 to +11.25 m (111.25 m) | 125,134 / 7,821 m2 | 30 x 74 m, 35,520 | upstream 22.50, downstream 85.00+, right 63.00+ | 0 | **YES** |

  Every cell under the level inside the three placed boxes is in the region: **no disconnected hollows** on either map.
  The Hide's region reaches the 200 m search square's edge downstream and to the right: its stream (R3a's river) and
  the low ground beside it. Beds sampled 42,433 / 43,648 / 148,286 in 36 / 37 / 142 ms.
- **The change:**
  - **The box** (`BuildField`, `GTWaterSheet.cpp:326-397`): the region's bounds plus **`BasinMarginM` 2.0 m**
    (`GTWaterSheet.h:184`, proposed), on the survey's lattice. A sheet with a current keeps the placed 30 m along the
    flow: its ends are the source and sink and HeadDropCm is set over that length, so the Hide's current is not moved
    (the water test's current 1.44 m/s both before and after). Across the flow it takes the union of the placed box and
    the region, symmetric about the crossing. Still water takes the region both ways. `-GTWaterPlacedBox` keeps the
    pre-S3 box and fill (the before pictures). Logged as **`GTFORDBOX`**.
  - **The cap `MaxSimCells` 57,000** (`GTWaterSheet.h:194`, proposed): 1.14 ms at the 19.9 ns a cell measured before
    (the Hide in the water test). A still basin past it is clipped along the flow about the crossing; a current's box
    across only. `-GTWaterSimCellCap=N` overrides it for a run.
  - **Water only in the basin** (`FGTWaterField::Basin`, `GTWaterField.h:264`; `SetBasinFrom` `GTWaterField.cpp:606`,
    called at `GTWaterSheet.cpp:395` from the survey's seed at the level + half the head drop; `GrowBasin` `:653`):
    `ApplyBoundary` holds a head only on a basin cell (`:593`), `Calm` (`:233`) and a rising `ShiftLevel` (`:505`) grow
    the basin over every cell under the new level that touches it and fill only the basin. The solver is unchanged.
  - **The footprint** (`Covers`, `GTWaterSheet.cpp:723`, with `InPlacedBox`, `NearFieldWater`, `NearStaticBasin`): the
    field's rectangle, all of it inside the placed box as before, and past the placed box only within one cell of the
    basin or of water. **Found by the first terrain run:** with the whole rectangle covered, the Hide's capped field
    (+-59.4 m across) reached the bog 55 m up the route, and the terrain test's car parked there read **0.129 m** of
    "ford water" (its sunk hull under the dry cells' bed; the W3 check asks 0: FAIL). After the fix: **0.000 m** (PASS).
  - **The static part** (`BuildStaticPart` `:1006`, `UploadStatic` `:1145`), only for a still basin past the cap: the
    rest of the basin + margin as section 1 of the same surface mesh on the same lattice (a quad wherever the field
    draws none: the two share the field's edge vertices), its own instance of M_GT_Water with its own flat field
    texture (R 0 on water, the bed over the level on a dry cell, G the depth at the level, no flow), no solver; the
    level there for the car, no current; re-uploaded when the level moves 0.25 cm (W5), the basin grown to it first.
    Logged as **`GTFORDSTATIC`**. No sheet reaches the cap on either map, so it runs only under `-GTWaterSimCellCap`.
  - **`GTFORDSEAM`** (`SeamLine`, `:839`), 5 s and 30 s after a field is built: the mean and largest step of the wet
    cells of each end column and side row against a flat sheet at the level.
- **The boxes and the cost** (`GTWATERSTATS`, NullRHI, a quiet machine; before from the logs of 11:42 and 12:05):

  | sheet | cells before -> after | box after | wet after | step ms mean before -> after | ns a cell after |
  |---|---|---|---|---|---|
  | forda | 25,920 -> **42,051** (321 x 131) | 80.2 x 32.8 m | 26,657 (63.4 %) | 0.501 -> **0.867** (ford diag, 6,883 stepping frames, worst 5.24) | 20.6 |
  | fordb | 28,800 -> **36,188** (332 x 109) | 83.0 x 27.2 m | 24,556 (67.9 %) | 0.517 -> **0.743** (ford diag, 13,260 frames, worst 1.60) | 20.5 |
  | the Hide | 35,520 -> **57,000** (120 x 475, **CAPPED**; the region + 2 m wanted 96,000) | 30.0 x 118.8 m | 15,796 (27.7 %) | 0.707 -> **1.129** (water test, 13,644 frames, worst 2.34; 1.079 in the first run) | 19.8 |

  **The cap holds: no sheet over 1.14 ms**, the Hide at 1.129 (99 % of it). The water test's own step gate (under 2.0)
  passes. Both L_Proving fields' four edges hold **0 wet cells** (the ponds are closed inside their boxes).
- **The seam step** (`GTFORDSEAM`): **L_Proving 0.00 cm** - no seam as built (the whole basin simulated, the edges dry);
  with `-GTWaterSimCellCap=20000` (forda clipped to 152 x 131, fordb 183 x 109, the static parts 321 x 131 and 332 x 109
  lattice cells, 21,970 and 16,092 quads, built in 19 and 14 ms) the ends meeting the static part stood at **mean
  0.00 cm, largest 0.00 cm** on both (95 and 94, 77 and 81 wet cells: still water held at the level, head 0). **The
  Hide +15.00 cm upstream, -15.00 cm downstream** (170 and 234 wet cells), as before: its ends are the current's heads
  and it gets no static part; **S3 stops at the Hide's flow-wise ends**, 15 m either side of the crossing along the
  stream, where the region goes on 22.5 m upstream and 85 m+ downstream (R3a's river). Its capped sides hold 0 wet cells.
- **The still ponds** (the owner's decision): `setup_m6_proving.py:237` sets each proving sheet's `head_drop_cm` and
  `flow_speed_cm_per_s` to 0 (the flow direction stays: the field's axis and the posts' upstream side);
  `Art/setup_m6_proving.bat` rebuilt L_Proving (10 s, saved 14:26:54). The Hide needed no rebuild (the box is set at
  runtime; `setup_m6_hide.py` is unchanged).
- **The proving test** asserted no flow; its ford check now also asserts still water (`GTProvingTestRunner.cpp:31`,
  `:249`): the mean current along the flow axis over the points within 30 m with more than 5 cm of water, under
  `StillWaterCmPerS` 20 cm/s (proposed). Read: **forda +0.3 cm/s over 14 points (fastest 15.3), fordb -2.8 cm/s over 12
  (fastest 27.1), head drop 0.0 -> still**. forda's "first wet" moved 1 m -> 11 m ahead of the station: the 1 m was the
  dry-cell artefact above (a covered bank reading its bed), fordb 2 -> 18 m; deepest 61.5 -> 61.7 cm and 139.9 -> 138.5.
- **The picture** (`Art/proving_shots.bat 2`, step 2, `GTProvingShotsRunner.cpp:487-627`): the car back on the pad;
  **the camera at the forda station, (45, 0) m heading 0 (east, along the route, across the pond), eye 5 m over the
  ground** (474 cm world, pitch -12.7 at forda's middle on the water); the first run at a standing 1.7 m saw the pond at
  3-10 degrees as a sliver, so the eye went up before the before picture that counts. Pairs of points on the water
  plane 1 m either side of the placed box's flow-wise ends, where the bed under both is under the level: 84 pairs kept
  each run. `Art/tools/sample_basin.ps1` (new), 5 x 5 px round each point, water = blue over red:

  | run | upstream end: inside / outside the old edge (mean R, B) | downstream end | all: inside / outside, step | the depth the car reads inside / outside |
  |---|---|---|---|---|
  | before (`-GTWaterPlacedBox`, the old map) | **70.9 % (179, 183) / 0.0 % (162, 94)** | 0.0 % (178, 115) / 0.0 % (169, 100) | 33.8 % / 0.0 %, **33.8 points** | 64.0 / 0.0 cm, 30.3 / 0.0 cm |
  | after | 0.1 % (161, 143) / 7.7 % (160, 149) | 24.5 % (169, 161) / 18.0 % (163, 155) | 12.9 % / 13.1 %, **-0.2 points** | 47.1 / 47.0 cm, 45.4 / 46.0 cm |
  | after, cap 20,000 (both old edges still inside the simulated window) | 20.1 % (166, 156) / 2.6 % (161, 143) | 43.5 % (174, 169) / 23.5 % (167, 155) | 32.3 % / 13.5 %, 18.8 points | 48.1 / 45.9 cm, 46.0 / 45.7 cm |

  - **Read:** before, the upstream end is a step (water inside, brown ground outside: blue 183 against 94); after, the
    two sides read the same colour within 6 of blue and the car reads 47 cm both sides. The blue-over-red share is a
    weak rule on this water: the still pond reads pale grey-brown (the bed through translucent water), the before
    picture's downstream water read brown on both sides (the end held 15 cm under the level), and the cap run - the same
    water at the old edge, both points simulated - read an 18.8-point step: **the rule's run-to-run spread on this
    water is about 20 points**, so the after run's -0.2 is inside it and the mean colours and depths carry the result.
    The orchestrator's look at proving_04 after (a look): the water spans the channel from bank to bank with a foam
    line along both shores, R1's rocks standing out of it; before, a pale sheet with a straight left edge.
  - Pictures: `Saved/Screenshots/Proving/proving_04_forda_basin_before.png`, `_after.png`, `_cap20000.png`; logs
    `Saved/Logs/proving_shots_s3_before.log`, `_after.log`, `_cap20000.log`.
- **The Hide's pictures** (`Art/ford_shots.bat`, hide_22-31, `sample_ford.ps1`; before with `-GTWaterPlacedBox`,
  logs `Saved/Logs/hide_shots_s3_before.log` / `_after.log`): **unchanged within their spread** - hide_22 water 43.5 ->
  39.9 %, hide_23 bow 68.3 -> 61.6 %, hide_24 11.9 -> 12.2 %, hide_28 32.2 -> 31.9 %, frame-diff flow+wind 17.40 ->
  16.05 %, still 0.00 -> 0.00 %, wake 11.17 -> 10.75 %, crests 4/2/4 -> 3/2/4. hide_22 is VOID in both runs (one
  clamped frame, 0.163 / 0.160 s). **Changed boxes:** hide_29's shallow boxes and hide_31's rock boxes moved (the runner
  picks them from the field; hide_31's "open" box projected nowhere after and fell back to the whole frame), so those
  two are not comparable.
- **The ford diag** (`Art/ford_diag.bat` + `python Art/tools/ford_diag.py --rows Saved/Logs/ford_diag_rows`; before =
  11:42's log, current on): **forda_base waterline to waterline 6.96 -> 5.72 s** (gate under 8 s), minimum 1.71 ->
  2.74 m/s, not flooded; forda_hull0 3.53 -> 3.53 s; forda_buoy0 11.52 s flooded -> **5.40 s, not flooded**;
  forda_base_repeat 11.93 s flooded -> **5.63 s, not flooded**; fordb's three runs stuck as before (156.9 / 160.8 /
  159.4 m, flooded). The still pond is the change: forda without its current across the road (1.5 m/s nominal before) is crossed
  faster and the bow-wave flood of section 4 item 1 did not happen in these runs (a movement change, the owner's
  decision, reported here).
- **Tests** (`bash Art/suite.sh water terrain proving`, twice: the first run found the covered-dry-cell bug, the second
  is on the final code):
  - `PASS water (294s): water: current 1.44 m/s where the route crosses (asked 1.5 +/- 20 %, 31.5 cm of head would read 1.5); the middle line's discharge mean 1.30 m/s, ten points 1.17 (0.55-1.44) over 0.36 m of water, 23.0 m`
    (both runs). Every water gate passes: river **50.57 cm of 50.57 asked**, rain 0 for 30 s 18.60 of 18.60, raise
    13.58 cm peak to peak, bow crest 18.59 cm, the middle back within +1.42 cm (asked 1.5), step 1.129 ms, still water
    0.000 m/s, ring front 1.88 s, mesh 57,000 vertices.
  - Run 1: `FAIL terrain (264s): FAIL terrain: landscape under the leg, ...` on the W3 check (the hull's submerged height
    0.129 m at the bog, asked 0); fixed in `Covers`.
  - Run 2: `FAIL terrain (264s): FAIL terrain: landscape under the leg, actors on it, surfaces [valley road=Surface.Tarmac climb=Surface.Dirt off the road=Surface.Dirt last stretch=Surface.Dirt crossing(dig 3.2 m)=Surface.Dirt outside the mud boxes Mud 0 Bog 0 of 1018081 (every 2 m)], road max grade 20.1% rise `
    - **only step 11's ruts flake** ("exit at 30 deg, the hold on: 15.0 m in 10.0 s ... -> slower than down the ruts
    0"); the W3 check now 0.000 m -> 1. **The ford steps all pass:** through (water up to 0.75 m, 3 km/h slowest);
    raised 70 cm, flooded; **held 0.05 m in 6 s** (13:15's run 0.04, 12:05's 0.05); **carried 7.28 m in 10 s** (run 1
    7.21; before 5.75 at 13:15 and 5.65 at 12:05: **+1.5 m, a movement change on the Hide**, reported, not re-gated -
    the gate asks over 4 m; the likely cause, unmeasured, is the Hide's field 118.8 m across instead of 74 m, which the
    70 cm raise floods wider); floats 3.4 % of the weight on the wheels, keel 0.97 m (asked within 10 cm of 1.05);
    winched to the post in 22.1 s (22.3 before).
  - `PASS proving (33s): proving: all stations | sheets 2 patches 1 rocks 14 stones 20 rallyposts 6 winchposts 8 | pad: on the pad yes, surface Surface.Tarmac | pad: on the pad yes, surface Surface.Tarmac | forda: water depth`
    (both runs).
  - `== suite: 2 PASS, 1 FAIL (failed: terrain)` (both runs). The full suite was not run (it ran earlier today).
- **Builds:** `== build exit 0 in 50s`, then 16 s (the step-2 eye), 26 s (the `Covers` fix). Warnings only in
  `GTM6TestRunner.cpp` (C4996, C4701), not S3's code.
- **Found while running:** step 1 of the proving shots (S2's bank picture) looks for a dry spot along forda's channel;
  the channel floor at (70, -19) m is now under the pond, so its spot will move (unchecked: step 1 was not run).
  `setup_m6_proving.py`'s gap log still measures the placed (length + 24) x 30 m sheets.
- **Unchecked.** The owner's look at forda and fordb from the bank and at the Hide's ford; the margin (2 m) and the cap
  (57,000), proposed; the static part's look (it only runs under the cap override) and the seam's look; the still
  ponds' feel; the Hide's "carried" change; the Hide past its flow-wise ends (R3a); a W5 rise past the 2 m margin on
  L_Proving's banks; the picture rule's spread on still water (measured once, 18.8 points).

## 54. Deformable riverbeds (2026-09-23)

Stage S4 of `docs/RIVERBED_PLAN.md`, the plan's last, with the orchestrator's decisions (plan section 4 item 6: both
maps' fords get a bed patch, the profile on the Ford kind's default) and notes. The owner looked at S3 ("ponds look
good") and said "go ahead with S4". Every build and run below was after a clean `tasklist` (no FarCry6, editor or
GrandTour at any run, 15:16-16:30). No tuned number moved: the bog's rows, field and ridge numbers, the traction's
constants, the water and the hull are as they were; the profile's numbers are new and PROPOSED, UNMEASURED.

- **The owner's question** (plan section 1, M4): the ford's bed should deform like the bog - the wheel goes down into
  it and leaves ruts under the water - instead of the capped 5 cm of S2 on a bed that keeps no mark.
- **M4 as found** (plan section 2): a patch reads nothing from the row itself - its depth is the wheel's Sinkage, its
  look the generator's layer baked per cell; the ridge numbers were already per patch (`AGTMudPatch` UPROPERTYs) and
  `BuildPatches` set only `WaterTableCm` from the section; patches only over Mud sections; the traction read and
  stamped a patch only on the Surface.Mud/Bog tags; 4 hole slots (MPC_TrackPaint Patch0..3). All as the plan wrote it.
  One more found here: **on the Hide the ford section starts 5 m after the bog ends, and the bog's box reaches 11.6 m
  past its section** (half width 9.6 + 2 m), so a ford box on the same rule overlapped the bog's by 15.8 m: two meshes
  on one ground.
- **The profile** (`FGTDeformProfile`, `Terrain/GTTerrainGenerator.h:118`, on `FGTRouteSection::Deform` `:237`, mode
  enum `EGTDeformProfileMode` `:98`): `Mode` (ByKind, the default: a Ford's bed takes the profile, a Mud section keeps
  its rows; On; Off), `SinkageRate`, `MaxSinkageM` and the nineteen ridge numbers of `AGTMudPatch` (stage H/I, the
  bog's values as defaults). `GTTerrain::DeformProfileFor` (`GTTerrainGenerator.cpp:577`) says whether a section has
  one, `DeformPatchBoxCm` (`:587`) is the box on the bog's rule (the route points every 2 m +- the half width + 2 m,
  the rule `MudPatchBoxCm` keeps; the generator's paint boxes stay Mud-only, so a ford's bed stays Dirt),
  `DeformPatchCount` the patches a spec gets (the proving test asserts it). A spec asset never edited follows the
  default: DA_Terrain_Hide's ford took it with no asset change.
- **The patches** (`UGTMudSubsystem::BuildPatches`, `Terrain/GTMudSubsystem.cpp:108`): two passes, the Mud sections
  first in section order exactly as before (a bog keeps its list place, its hole slot, its rows and its ridge numbers:
  no profile is applied to it), then every profiled section. A later box is cut back off an earlier patch's box on the
  side that keeps the most of it, 25 cm short (two field cells; the field rounds its size up). `AGTMudPatch::ApplyProfile`
  (`GTMudPatch.cpp:43`) copies the sinkage and ridge numbers in before `Init`, the `WaterTableCm` pattern. **The
  rut-water grid** of a profiled patch leaves out every quad a water sheet covers (`GTMudPatch.cpp:526`; the sheets
  have not begun play then, so `Covers` answers the placed box); a bog keeps its whole grid (the Hide's placed sheet
  box reaches over the bog's far end, and that stays as it was). `HoleSlot` is the patch's MPC slot, -1 past four.
  `-GTNoBedPatch` builds no profiled patch (the pre-S4 answer, for control runs).
- **The traction** (`Vehicle/GTTractionComponent.cpp:157-160, 203, 453`): the patch is looked up first, at the
  contact; inside a profiled patch's box on ground that sinks at all (the row's MaxSinkage over 0: tarmac stays firm)
  the profile's SinkageRate and MaxSinkage stand in for the row's, the row's wet scale and everything else of the row
  still apply (so the ford bed is 10 cm dry and 30 cm at wetness 1 on Dirt's WetSinkageScale 3.0: unmeasured). The
  field read and the stamp take "a patch with a profile" as well as the Mud/Bog tag; `bInPatchBox` (S2's cap) comes
  from the same lookup, so inside the box the whole 10 cm shows. A bog wheel runs the same lines to the same values.
- **The patches per map** (the subsystem's log, both maps rebuilt, `setup_m6_hide.log` 15:29:31, `setup_m6_proving.log`
  15:29:46):

  | map | patch | section | box | cells | hole slot | profile | rut-water grid |
  |---|---|---|---|---|---|---|---|
  | L_Proving | 0 | 2, the bog (Mud 236-296 m) | 82.7 x 26.2 m | 662 x 210 | 0 | none (the rows) | 139,893 vertices, 0 quads cut (as before) |
  | L_Proving | 1 | 0, forda (Ford 55-85 m) | 48.5 x 18.5 m | 388 x 148 | 1 | 10 cm, 0.02 m/s | off: all 57,424 quads under the sheet |
  | L_Proving | 2 | 1, fordb (Ford 141-177 m) | 18.5 x 54.5 m | 148 x 436 | 2 | 10 cm, 0.02 m/s | off: all 64,528 quads under the sheet |
  | the Hide | 0 | 1, the bog (Mud 1035-1085 m) | 69.2 x 35.6 m | 554 x 285 | 0 | none (the rows) | 158,730 vertices, 0 cut (as before) |
  | the Hide | 1 | 2, the ford (Ford 1090-1140 m) | 51.9 x 25.1 m (cut from 68.0 x 25.0 off the bog's +X side) | 415 x 201 | 1 | 10 cm, 0.02 m/s | 1,840 triangles left, 82,495 quads under the sheet |

  **L_Proving 3 patches, the Hide 2; every patch holds a hole, no slot short** (the log: "patch count 3 (2 with a
  deformation profile), 3 with a landscape hole, 0 without"). The Hide's cut leaves the ford section's first ~7 m (arc
  1090-1097, x 982-989 m, the route's own geometry) inside the bog's box, where the bog's patch (no profile, the Dirt row,
  S2's full shrink of Dirt's 5 cm) answers; whether water stands there is unchecked.
- **The starting profile, PROPOSED and UNMEASURED:** MaxSinkage **10 cm**, SinkageRate **0.02 m/s** (Dirt's 5 cm and
  0.01 x 2), the bog's ridge numbers (RidgeWidthCm 90, MaxRidgeCm 12 and the other seventeen as `AGTMudPatch` has
  them). The owner names them after driving.
- **The ford diag** (`Art/ford_diag.bat` + `python Art/tools/ford_diag.py`; before = S3's 14:54 log, kept as
  `Saved/Logs/ford_diag_s4_before.log`; after = 15:46 and 16:04, the second with the "under the water" filter below):

  | run | before | after (15:46 / 16:04) |
  |---|---|---|
  | forda_base waterline to waterline (gate under 8 s) | 5.72 s, min 2.73 m/s | **5.57 / 5.57 s**, min 2.68 / 2.69 m/s, not flooded (front 0.761 / 0.763 m) |
  | forda_base exit bank radius step per tick (gate under 2 cm) | 0.0 cm | **0.0 / 0.0 cm** (contact step 1.5 cm, load step +768 / +708 N) |
  | forda_base entry bank radius step | 0.5 cm | 0.6 cm |
  | forda_base peak slip ratio | 0.717 | 0.458 / 0.444 |
  | forda_hull0 / buoy0 / base_repeat | 3.53 / 5.40 / 5.63 s | 3.42 / 4.92 / 5.52 s (16:04: 3.42 / 4.92 / 5.50) |
  | fordb base / hull0 / buoy0 | stuck at 156.89 / 160.75 / 159.44 m | stuck at 156.90 / 160.76 / 159.43 m (floats and floods, as before) |
  | the Proving bog's four box-edge runs | through / timeout 4.21 m / through / through | through / **through** / through / through (bog_right_noramp, the gt.Mud.SinkRiseRate 1000 control) |

  - **The sinkage in the water** (new `end ... sinkage in the water` line): every wheel **10.0 cm raw and 10.0 cm
    visible**, MaxSink read 10.0 cm, the smallest Chaos radius **28.0 cm** (38 - 10), the profile on 1336 of 1336
    wheel-ticks in contact (fordb's runs the same, radius 28.4 cm). Before: Dirt's 4.6 cm raw under the 5 cm cap,
    radius 33.4 cm on the bank (section 52).
  - **Found: the box's edge on the far approach.** The run now goes on past the bed patch's box (it leaves the box at
    arc 94.35, 10.75 m past the exit waterline) and logs the biggest per-tick step anywhere: **a 4.0 cm radius step in
    one tick at +10.90 m, load step +3459 / +3192 N**, at about 9 m/s. It is S2's ramp (VisibleSinkRiseRate 0.3 m per m,
    proposed) meeting the bed's 10 cm at speed: 0.15 m of ground a tick lets the shrink fall 4.5 cm, 10 -> 5 cm in two
    ticks (section 52's "unmeasured: a wheel leaving a box deep at speed", now measured). The exit bank's own window
    (+-4 m of the waterline) reads 0.0. Not tuned: the rise rate is the owner's to name.
  - The crossing is faster (5.72 -> 5.57 s, buoy0 5.40 -> 4.92) with a smaller wheel: the drivetrain scales each
    wheel's grip torque cap by the Chaos radius (M1's lever) and a 28 cm wheel turns the same torque into more push;
    the peak slip fell 0.72 -> 0.45. A movement change, reported.
- **The ruts under the water** (`GTFORDRUT`, `FGTFordDiagRunner::LogFordRuts`, `GTFordDiagRunner.cpp:637`; the field's
  own cells a wheel touched whose ground lies under more than 2 cm of the sheet's water - the first run's "more than 0"
  also counted dry cells inside the placed box, whose bed stands millimetres off the landscape):
  - After forda_base (16:04): **5,562 touched cells under the water, 776 cut past 1 cm, mean -9.76 cm, 757 past 5 cm,
    the deepest -11.27 cm**, the banks beside them up to +2.41 cm; after all four forda crossings 834 cut, mean -9.87,
    deepest -11.34 cm. The rut floor is the wheel's 10 cm plus FloorNoiseCm's 1.5.
  - Proving shots step 3's crossing: the left wheels' path 0.5-5 m into the water, **93 points, the field under them
    mean -9.82 cm (min -10.50) under 28.1 cm of water read**; 722 cells cut past 1 cm under the water, mean -9.89.
- **The water depth the car reads** (the sheet's surface over the landscape contact; the ruts never reach the solver's
  bed): across forda's middle (arc 72.38, the centre line and both wheel lines), **before the crossing 57.8 / 58.1 /
  60.2 cm; after it with the water calmed 57.8 / 58.1 / 60.2 cm** - unchanged to the millimetre while the field under
  the lines reads -2.4 / +1.0 / -6.5 cm (the surface over the rut floor would be 60.3 / 57.1 / 66.7 cm). Straight
  after the crossing, with its waves: 57.0 / 57.4 / 62.1 cm.
- **The picture of the ruts** (new `Art/proving_shots.bat 3`, `GTProvingShotsRunner.cpp:731`; the camera on forda's
  entry bank 3 m up, 3 m left of the road 3 m before the entry waterline, pitched 29.7 degrees down at the left wheel
  line 2.75 m in, 28.0 cm of water there; one picture before the crossing and one after it, the car back on the pad
  and the water calmed both times; new `Art/tools/sample_ford_ruts.ps1`: discs of 12 cm either side of the left
  wheels' recorded path, and the same path 2.5 m further left over untouched wet bed, 0 of 93 control points touched,
  0 dry):

  | set | pixels | before: mean brightest channel | after | after minus before, mean | changed by more than 12 |
  |---|---|---|---|---|---|
  | the ruts | 5,457 | 195.1 (RGB 195 181 148) | **185.8** (186 173 143) | **-9.3** | **1,808 (33.1 %)** |
  | untouched wet bed | 7,362 | 193.1 (193 177 143) | 193.3 (193 178 143) | +0.3 | **0 (0.0 %)** |

  In the after picture the rut band reads 7.5 below the untouched bed beside it. Pictures
  `Saved/Screenshots/Proving/proving_05_forda_ruts_before.png`, `proving_06_forda_ruts_after.png`; log
  `Saved/Logs/proving_shots.log` (the first run, whose waterline scan used "more than 0" and put the ruts on the dry
  approach, is `proving_shots_s4_run1_drywaterline.log`). **My look at proving_06** (a look, not a number): two dark
  lines run from the near bank through the water and up the far bank; the bed patch's box reads as a pale rectangle
  across the pond, its two sides straight lines in the water against the darker bed outside it - the mesh's Mud row
  against the landscape seen through the water, the look the box-edge number below measures on the dry approach. The
  owner's look: unchecked.
- **The box edge on a Dirt bed** (`proving_07_forda_box_edge`, hide_17's view of forda's box on the approach road:
  eye 1.7 m, 3 m outside, 19.2 degrees down; `sample_border.ps1 -LogName proving_shots.log -Folder Proving -Step 3
  -Names proving_07_forda_box_edge`, the sampler's new arguments, defaults as before): **dark 0 of 190,743, sky 0**;
  the mud mesh 1.5 m inside the box reads **211.9** against the landscape 1.5 m outside **181.1: +30.8** (the bog's
  border read -4.5 at stage J, -10.6 in a bog run). **What the mesh does on a Dirt cell:** `AGTMudPatch::BakeLayers`
  writes 1 where the generator's layer is the Bog and 0 everywhere else, so a Dirt (or Scrub, or road) cell is drawn
  with M_GT_Mud's Mud row - muddy_tracks tinted to the Mud row's colour and roughness - over the whole box, road and
  bank alike, and under the water. The +30.8 is that mismatch in numbers; the look is unchecked.
- **The Hide's pictures** (`Art/ford_shots.bat`, hide_22-31, `sample_ford.ps1`; with the bed patch 15:56, log
  `hide_shots_s4_after.log`; a control with `-GTNoBedPatch` on the same build 15:58, `hide_shots_s4_nobed.log`,
  pictures in `Saved/Screenshots/M6_s4_nobed`; S3's after for the spread):

  | picture | S3 after | S4, no bed patch | S4, bed patch |
  |---|---|---|---|
  | hide_22 water (VOID all three: one clamped frame) | 39.9 % | 39.7 % | 38.3 % |
  | hide_23 bow water / bright | 61.6 % / - | 62.0 % / 54.7 % | 54.4 % / 1.2 % |
  | hide_24 water | 12.2 % | 12.5 % | 12.7 % |
  | hide_28 rain water | 31.9 % | 28.5 % | 38.0 % |
  | frame-diff flow+wind / still / wake | 16.05 / 0.00 / 10.75 % | 13.58 / 0.00 / 15.99 % | 11.20 / 0.00 / 8.67 % |
  | crests ring / bow / rain | 3 / 2 / 4 | 3 / 2 / 5 | 5 / 4 / 3 |

  The pair on one build parts by more than S3's before/after did on the bow's bright share (54.7 -> 1.2 %) and the wake
  (15.99 -> 8.67 %). Under the Hide's water the bed is now the mud mesh (the landscape has its hole there) and the car
  sinks 10 cm; which of the two moves the pixels is unmeasured. The look under the water: unchecked.
- **Tests** (`bash Art/suite.sh terrain proving water mud`, 15:29-15:40):
  - `PASS proving (33s): proving: all stations | sheets 2 patches 3 rocks 14 stones 20 rallyposts 6 winchposts 8 | ...`
    (the patch check is now `DeformPatchCount`: 3 of 3).
  - `PASS mud (22s): mud start: speed=538 cm/s (19 km/h) distance=2772 cm maxspeed=538 maxSink=1.00 boggedEver=0 boggedNow=0`
    (section 52's 538: L_TestTrack has no spec and no patch).
  - `FAIL terrain (...): FAIL terrain: landscape under the leg, actors on it, surfaces [...]` - **only step 11's ruts
    flake** ("exit at 30 deg, the hold on: 15.0 m in 8.5 s ... -> slower than down the ruts 0"). **The bog, before (S3's
    14:48 run) -> after:** middle slowest 111 -> 104 cm/s, body 28 -> 28 cm lower (asked 7 or more); **escape forward
    13.5 -> 13.7 m** in 12 s (13.0-15.0); reverse 6.0 -> 5.4 m; the rut field's rut mean -35.1 -> -36.2 cm, past half
    their sinkage 90 -> 90 of 92, past 0.6 81 -> 88 (logged), ridge mean 4.5 -> 4.5 cm, **clear 6 m off 92 of 92 both**
    (1.00, asked 0.95); mesh 158,730 vertices both; the along-crest check's numbers identical (a clean spot, no car).
    A bog wheel runs the same code to the same values; the crawls are chaotic run to run. **The Hide's ford** (now on
    its bed patch): through, water up to 0.74 m (0.75); held 0.05 m in 6 s (0.05); **carried 7.28 -> 6.11 m** in 10 s
    (asked over 4; a movement change on the Hide, reported); floats 3.4 -> 4.5 % on the wheels (asked under 15);
    winched 22.1 s both.
  - `FAIL water (...): FAIL water: current 1.44 m/s where the route crosses ...` - **one gate: the bow's settle, the middle
    back within +1.54 cm (asked 1.5)**; every other water gate passes (river, rain, ring front 1.88 s, bow crest 19.26
    cm, step 1.077 ms, still water 0.000 m/s). **Control on the same build with `-GTNoBedPatch`: PASS, +1.40 cm**
    (`water_test_nobed.log`; S3's two runs +1.42). The Hide's ford bed patch moves this gate by about +0.14 cm; the car
    held at 3 km/h over the middle 20 m now sits 10 cm lower. Not re-gated; the full suite's run read +1.47 (PASS).
- **Found while building:** the waterline scan of a picture step, and any "under the water" count, must ask for more
  than a couple of centimetres: a dry cell inside a sheet's placed box answers its bed as the surface (section 53), a
  few millimetres off the landscape at a point, so "depth over 0" put forda's waterline 5.6 m up the dry approach.
- **Builds:** `== build exit 0 in 59s`, then 6 s (`-GTNoBedPatch`) and 9 s (the 2 cm filter). Warnings only in
  `GTM6TestRunner.cpp` (C4996, C4701), not S4's code.
- **The full suite** (`bash Art/suite.sh`, 16:02-16:22, the plan's last stage; log `Saved/Logs/suite_s4_full.txt`):
  `== suite: 23 PASS, 1 FAIL (failed: terrain)`. The one FAIL line:
  `FAIL terrain (263s): FAIL terrain: landscape under the leg, actors on it, surfaces [valley road=Surface.Tarmac climb=Surface.Dirt off the road=Surface.Dirt last stretch=Surface.Dirt crossing(dig 3.2 m)=Surface.Dirt outside the mud boxes Mud 0 Bog 0 of 1018081 (every 2 m)], ...`
  - again **only step 11's ruts flake**: "exit at 30 deg, the hold on: 15.0 m in 11.2 s (6 m in 5.3 s), fastest 209
    cm/s, rut read 0.87, climb 0.072 peak 0.49, belly channel 0.97, heading 14 deg off the ruts -> slower than down the
    ruts 0". It failed the same way in both of today's terrain runs (and in S2's and S3's): the known flake, not rerun a
    third time. The bog in this run: escape forward **13.5 m** (13.0-15.0), reverse 6.0 m, body 27 cm lower, clear 6 m
    off 92 of 92, rut mean -36.2 cm, past 0.6 88; the Hide's ford held 0.06 m, **carried 6.65 m** (6.11 in the first
    run, 7.28 in S3's), winched 22.2 s.
  - `PASS water (296s): water: current 1.44 m/s where the route crosses (asked 1.5 +/- 20 %, 31.5 cm of head would read 1.5); the middle line's discharge mean 1.30 m/s, ten points 1.17 (0.55-1.44) over 0.36 m of water, 23.0 m`
    - the bow's settle **+1.47 cm** (asked 1.5), bow crest 18.63 cm: with the bed patch the gate read +1.54 (FAIL)
    and +1.47 (PASS), without it +1.40; S3 +1.42. It sits on its gate now.
  - `PASS proving (34s)` (patches 3), `PASS mud (22s): mud start: speed=537 cm/s` (538 in the first run), `PASS winch
    (27s)` and `PASS body (17s)` first time (no flake rerun needed), grip, surface, track, spray and drivetrain PASS.
- **Unchecked.** The water test's bow settle (+1.54 and +1.47 with the bed patch against 1.5); the owner's drive of forda on L_Proving and of the Hide's ford; every profile number (10 cm, 0.02 m/s,
  the ridge numbers); the wet bed (30 cm at wetness 1 through Dirt's wet scale: never run); the look of the ruts under
  the water and of the mud mesh on the Dirt bed (+30.8 at the box edge) and at the box edges generally; the 4.0 cm
  one-tick step at the far edge of forda's box at speed (S2's rise rate, the owner's); the Hide's ford's first 7 m under
  the bog's box; the rut water a profiled patch still answers in the water query where its grid is cut (only past the
  table, -25 cm, so never in a 10 cm rut at wetness 0); the frame cost of the two new L_Proving meshes (57,961 and
  65,113 vertices) and the Hide's (84,032), unmeasured.

## 55. Look stage L1: the GT Paint addon (2026-09-23)

Stage L1 of `docs/LOOK_PLAN.md`, from the owner's brief (the L1 prompt): the Blender addon that paints, bakes and
exports the owner's models in one preset, and the Unreal material that receives the bake. Every build and run below was
after a clean `tasklist` (no FarCry6, editor or GrandTour at any run). No tuned number moved: traction, hull,
drivetrain, water, mud, weather, camera, terrain specs and the landscape material are as they were; nothing in the
post-process, the water, the mud or the landscape was touched. Every preset number is new, PROPOSED and UNMEASURED
against a look; the owner names them. No texture was sourced.

- **The references, looked at** (ref_01..05, a look, not a measurement): big walls in one flat saturated colour with a
  few lighter horizontal brush drags, hard cast shadows in the wall's own hue, pale chipped patches and scuffs on the
  blue and yellow walls, trim as flat pale bands, the figure and the boombox in two or three greys each. The plan's
  section 1 reading stands.
- **The addon** (`Art/Blender/gt_paint/`: `__init__.py` with `bl_info` for 5.1, the panel and the three operators;
  `core.py`, the functions the panel and the test share). The "GT Paint" tab of the 3D view's N sidebar: Preset
  (empty = `Art/Blender/gt_paint_preset.json`), Asset (empty = the active object's name, cleaned to `RearBumper001`
  style), Size (Preset / 1K / 2K), Export (empty = `Art/Export`), a line of the preset's main numbers, and the buttons.
  Install: zip the `gt_paint` folder and Install from Disk, or copy it into the 5.1 `scripts\addons` folder (unchecked,
  see below). Rules kept: nodes found by type; every enum value picked from RNA's list (`core.pick`); the render engine
  read, then set inside `try/except TypeError` and put back.
  - **Apply Style** (`gt_paint.apply_style`, the selected meshes): creates or refreshes the shared `GT_Paint` node group,
    then one material per object (`GT_<Object>`; per slot, `GT_<Object>_<n>`, when an object has more than one slot).
    The base colour: a colour attribute on the mesh when the preset's `base_source` is `auto` or `vertex` (hand paint
    = Vertex Paint on it); otherwise the ID colour - the slot's own material's Principled base colour (the owner's flat
    ID colour), else the palette entry the first matching `name_rules` needle picks (`wheel` -> tyre, `interior`,
    `bumper`/`pillar` -> trim, else body: the naming `export_rangerover.py` already uses for its slots). A refresh keeps
    each GT material's base colour as it stands on its group node. Preview: Principled BSDF (albedo + roughness); the
    wear, grime and pointiness nodes are Cycles nodes, so EEVEE shows base and grain only (unchecked).
  - **The group** (`core.build_group`): grain = world-position noise (scale `grain_scale_m`, Z stretched by
    `grain_stretch` so strokes run level), its 0.3-0.7 range mapped to -1..1, x `grain_strength`; wear = the Bevel
    node's normal (radius `wear_width_m`) against the shading normal, 1 - dot mapped 0.01-0.12, or pointiness mapped
    0.55-0.75 x `wear_pointiness`, whichever is larger, x (a second noise + 0.5), mapped `wear_breakup`..+0.2; grime =
    1 - the object's own AO (`only_local`, distance `grime_distance_m`) mapped 0.05-0.45 x (the grain noise + 0.5);
    highlight = the normal's Z past `highlight_up` x `highlight`. Shade v = 1 + grain + `wear_lighten` x wear -
    `grime_strength` x grime + highlight, **posterised** to levels 1 + k s, s = (hi - lo) / (tones - 1) over the
    preset's darkest (1 - grain - grime) to lightest (1 + grain + wear + highlight), k clamped so there are exactly
    `tones` levels and k = 0 - the base colour itself - is one of them. Albedo = base x min(v, 1), mixed toward
    `wear_colour` by v - 1 above 1; roughness = `roughness` + (`roughness_wear` - it) x wear + (`roughness_grime` - it) x
    grime; Mask = (wear, grime, roughness). The ranges written as numbers above (0.3-0.7, 0.01-0.12, 0.55-0.75, 0.2,
    0.05-0.45, 0.05) are constants in `core.py`, not preset keys: unchecked, and the owner's to move into the preset.
  - **Bake** (`gt_paint.bake`, the selected meshes as ONE asset): a world-space copy of every source's evaluated mesh
    (modifiers applied), joined, with their materials: `<Asset>_GTBake` in a `GT Paint Bake` collection, hidden and off
    in renders afterwards. A single source with a UV map keeps its render UV; otherwise one smart-project UV (`GT_UV`,
    `uv_angle_deg` 66, `uv_island_margin` 0.01) over the whole asset, so several parts share one atlas. Cycles, EMIT,
    `bake_samples` 1, no clear and no Cycles margin: the albedo (`T_GT_<Asset>_D`, sRGB, RGBA) then the mask
    (`T_GT_<Asset>_M`, Non-Color, R wear, G grime, B roughness), 1024 or 2048 px, PNG, into `Art/Export/<Asset>/`. The
    margin (`bake_margin_px` 8) is grown afterwards by `core.fill_margin`, copying the nearest baked texel; the albedo's
    alpha marks painted texels (baked + margin). The scene's engine, samples and dither are put back.
  - **Export** (`gt_paint.export`): the last bake's mesh (the UVs the textures were baked on) as
    `Art/Export/<Asset>/SM_<Asset>.fbx`: pivot at the active object's origin, turned by `export_yaw_deg` 90 (a model
    built front -Y, like the car, faces +X in Unreal), written in centimetres with `export_rangerover.py`'s FBX settings
    (the scene's `scale_length` 0.01 for the call, put back), one material slot `M_<Asset>`. No bake -> an error, not a
    guess.
- **The preset** (`Art/Blender/gt_paint_preset.json`, sRGB hex colours, keys starting `_` are notes; the same values
  are `core.DEFAULT_PRESET` for an install away from the repo), all PROPOSED, UNMEASURED: `tones` **4**,
  `grain_scale_m` **0.35**, `grain_strength` **0.15**, `grain_stretch` **5**, `wear_width_m` **0.02**, `wear_lighten`
  **0.25**, `wear_colour` **#F2EDE4**, `wear_breakup` **0.5**, `wear_pointiness` **0.5**, `grime_strength` **0.3**,
  `grime_distance_m` **0.3**, `highlight` **0** (off), `highlight_up` **0.7**, `roughness` **0.85** / `_wear` **0.6** /
  `_grime` **0.95**, `base_source` **auto**, palette body **#D9772E**, trim **#B8B2A6**, tyre **#2C2C30**, interior
  **#46423C**, `bake_size` **1024**, `bake_samples` **1**, `bake_margin_px` **8**, `uv_angle_deg` **66**,
  `uv_island_margin` **0.01**, `ao_samples` **16**, `bevel_samples` **8**, `export_yaw_deg` **90**. The first seven
  are the plan's.
- **Found and fixed on the way** (each measured by the test): (1) Blender's EXTEND margin averages its neighbours:
  **2,922 distinct colours** on the car's 1K albedo against 14 tones over 0.5 % -> the addon's own nearest-copy
  margin: **12**. (2) Recreating the group's interface on every Apply Style reset the group node inputs in EVERY
  material: the test's refresh step read the ochre cube back as **0.0 0.0 0.0** -> the interface is rebuilt only
  when its socket list changes (values kept by name if it ever does); the refresh reads **kept**. (3)
  `unit_settings.length_unit` is a dynamic enum RNA lists as `DEFAULT` only -> not set (the FBX never reads it).
- **The test** (`Art/Blender/tests/test_gt_paint.py` via `bash Art/blender_test.sh`: a copy of `Art/rangerover.blend`
  in `%TEMP%\gt_paint_test`, `blender -b --factory-startup`, never saved, refuses the owner's file; the panel's own
  operators; FAILs on a missing or empty file, an operator error or a refresh that changes a material). Two runs give
  byte-identical PNGs (md5). Numbers (1K, 1 sample; tones = 8-bit colours over 0.5 % of the painted texels; ceiling =
  4 tones x the asset's base colours):

  | asset | bake (D+M) | files D / M / FBX | painted | tones (ceiling), all colours | mean albedo sRGB | mask R / G / B |
  |---|---|---|---|---|---|---|
  | TestCube, 1 m, ochre #E3B04B owner material | 0.88 s | 47.6 / 50.0 / 15.3 KB | 67.3 % | **3** (4), 3 | 226.9 176.8 78.1 | 0.045 / 0.000 / 0.838 |
  | TestBox, 1.2 x 0.8 x 0.8 m, bevel 5 cm x 3 | 0.91 s | 30.7 / 32.2 / 18.7 KB | 87.0 % | **2** (4), 3 | 217.0 119.5 47.0 | 0.004 / 0.000 / 0.854 |
  | TestCar, 17 parts of the blockout copy | 0.72 s | 160.5 / 413.2 / 122.3 KB | 68.9 % | **10** (16), 12 | 159.1 107.3 68.5 | 0.272 / 0.476 / 0.827 |

  The cube's tones: #E3B04B 94.4 %, the wear tone #E7C48E 4.8 %, one shade darker #C4973F 0.8 %. The car's: body
  #D9772E 36.3 % and #BB6626 14.1 %, trim #B8B2A6 / #9E998F / #CBC5BA, tyre #2C2C30 / #242428, interior #46423C /
  #3B3832, wear #E0A486 4.7 %; the fourth, darkest level reaches 0.5 % nowhere. Read, not tuned: the bevelled box
  shows almost no wear (**0.004**) - a 5 cm bevel in 3 segments turns 30 degrees a facet, which the 2 cm Bevel node
  reads as about 0.03 of edge, far under the 0.5 breakup - and the cube and box no grime (a convex object has no AO of
  its own), while the car carries **0.476** of grime, the joined body's inner faces occluding each other. Skipped as
  `export_rangerover.py` skips them: `frontDoors.001` (1 face), `pillars.001` (3). The car's two textures and FBX are
  written into `Art/Export/TestCar/`, which is NOT the Range Rover's export (`Art/Export/SK_RangeRover.fbx` and
  `Static/`, untouched).
- **The Unreal side.** `Art/setup_look_l1.bat` + `Art/Unreal/setup_look_l1.py` (log prefix `SETUP_LOOK_L1`) import
  every `Art/Export/<Asset>/` holding all three files (`Static/` is reported and skipped): the FBX as a static mesh
  into `/Game/GrandTour/Props/Painted` with `import_rangerover.py`'s `make_task` settings generalised
  (`destination_name` SM_<Asset>); the bake into `/Game/GrandTour/Textures/Painted` on `setup_m6_textures.py`'s
  pattern, `_D` TC_Default sRGB on with `compression_no_alpha`, `_M` TC_Masks sRGB off; `M_GT_Painted` in
  `/Game/GrandTour/Materials`: BaseColor = lerp(`Albedo`, white, `Masks`.R x `WearLighten`) x (1 - `Masks`.G x
  `GrimeDarken`), Roughness = `Masks`.B, nothing else (no specular, normal or emissive: lighting is L2's).
  `WearLighten` and `GrimeDarken` default to **0**: the bake already carries wear and grime as paint, so these add on
  top and are the owner's to name. `M_GT_PaintedGrey` (BaseColor 0.214 linear = sRGB 128, Roughness 0.85) is the
  plain "before". `MI_GT_Painted_<Asset>` in `/Game/GrandTour/Materials/Painted` on every slot of its mesh. The run:
  3 of 3 assets, SM_TestBox **80 x 120 x 80 cm** 188 triangles, SM_TestCar **461 x 186 x 179 cm** 4,594 triangles
  (facing +X like the driven car), SM_TestCube 100 cm 12 triangles, lowest points at z 0, both materials compiled.
  **THE DRIVEN CAR KEEPS `M_GT_Vehicle`** (runtime dirt, MF_Weather wetness, dents, clear coat): whether it takes a
  bake is **OPEN, the owner's decision**.
- **The pictures.** `Art/proving_shots.bat 4`, a new step 4 in `FGTProvingShotsRunner` (`LastStep` 3 -> 4, two
  pictures more expected): the car on step 1's flat Dirt top (-11000, -4700, yaw -90, 18 x 14 m) on the handbrake,
  SM_TestBox 3.8 m ahead, SM_TestCar 5.2 m behind, spawned movable and without collision; the camera 9 m out on the
  sunlit side, 1.6 m over the top's height (the first try stood 11 m out on the falling slope and saw only the
  roofs over the crest); `proving_08_painted_before` in M_GT_PaintedGrey, then `proving_09_painted_after` in the
  instances, the shaders' compile jobs waited out (0 left) and `StreamAllResources` asked. `Art/tools/sample_tones.ps1`
  (new; `sample_border.ps1`'s box format; 5 bits a channel, tones over 0.5 % of a box, the top tones, a 16-bin
  luminance histogram) on the camera-facing side of each prop (25-75 % along, 30-60 % up) and on the parked car's side
  (`control_car`, M_GT_Vehicle in both):

  | box | before: mean, tones | after: mean, tones | after - before |
  |---|---|---|---|
  | TestBox (608 px) | 206.4 201.4 193.0, **2** | 255.0 197.1 97.0, **2** | +48.6 -4.4 -96.0 |
  | TestCar (7,912 px) | 205.1 200.2 191.5, **6** (55 in all) | 244.2 190.3 96.8, **12** (144 in all) | +39.1 -9.9 -94.7 |
  | control_car (2,560 px) | 235.3 227.5 208.5, 2 | 235.5 227.9 209.0, 2 | +0.2 +0.4 +0.4 |

  The control moves under half a level, so the change is the paint's, not the exposure's. The painted box's red
  **clips at 255** in the sun (the bake's #D9772E reads #FCC464 there), and the car's box reads 12 tones in the
  picture where the bake has 3 body and 2 tyre tones: the rest are the lighting's gradients across its panels, which
  L2's band pass is for. My look at the pair: before, two near-white cars and a near-white box; after, the copy reads as a light orange
  car with pale flecks along its edges, dark tyres and pale bumpers, the box one flat orange.
- **Tests.** `bash Art/build.sh`: `== build exit 0` three times (29 s, 26 s, 22 s). `bash Art/suite.sh base body
  proving`, run after the runner change and again at the end: **3 PASS** both times (base 12 s, body 20 s, proving
  34 s in the last); no flake met. Blender test PASS.
- **Unchecked.** The owner's look at everything; every preset number and the group's constants; the panel drawn in a
  live Blender UI and the zip install (the test runs the operators headless); the vertex-colour (hand paint) path,
  objects with several material slots, a single object keeping its own UV, 2K bakes, the highlight on; the EEVEE
  preview; the FBX pivot and yaw on a model other than the car and the test boxes; the bake's cost on a dense model
  (these three bake under a second); the albedo's alpha into Unreal (ignored by `compression_no_alpha`); M_GT_Painted's
  WearLighten/GrimeDarken above 0; the car taking a bake (open).

### Follow-up 2026-09-23: wear gated to edges, grain as strokes

- **The owner's gate** (their own blockout in a live Blender, Apply Style with the shipped preset): "It just looks
  rusty, not like the references." The orchestrator's look at their screenshot: one flat orange, no brush drags, small
  pale specks evenly over every panel (the middle of the bonnet and doors too) and on the pale trim. The references
  want one flat wall colour, a few long level drags one shade lighter or darker, and scuffs only as a few large ragged
  patches near edges and bases. No game number moved; nothing in Unreal changed (no C++, no material).
- **The two faults as handed over, and what the measurements say.** (1) Wear not gated to edges: `edge =
  max(bevel, pointiness x wear_pointiness)` cut into centimetre chips. MEASURED on the test's copy of the blockout,
  flat as saved and with a scratch Subdivision Surface (level 2, smooth shading, scratchpad only): the old group gives
  the SAME wear share with `wear_pointiness` 0.5 and 0 (0.0576 flat, 0.0304 subdivided, every part equal) and the same
  share of texels lighter than their colour's commonest outside wear (0.0041): x 0.5 caps the term at 0.5, which the 0.5
  breakup keeps under R 0.25. So on this copy the pointiness painted nothing; the owner's live model may differ
  (unchecked). (2) The grain posterised away: true for most of it, but its tail was not: with the old step s = 0.283
  a grain peak over about half a step (about 0.4-0.5 % of each asset, the "lighter outside wear" column) rounded UP
  into the top tone, and the top tone was the wear tone. My look at a scratch unlit Cycles render of the subdivided
  copy under the old group: small pale specks over roof, bonnet and doors, as in the owner's screenshot; the same copy
  with only edge wear (strokes, scuffs and grime at 0): clean panels, pale lines along seams and edges. So the specks
  were the grain's tail painted in the wear colour, not the pointiness. The new mechanism removes both.
- **The new mechanism** (`core.build_group`; operators, files, names and the other keys as they were):
  - **Wear** = the Bevel term only by default (`wear_pointiness` **0**, the input kept), chipped as before, plus
    **scuffs**: a world-aligned noise (`scuff_scale_m`, detail 2) made uniform (`Graph.uniform`: the noise's measured
    spread `NOISE_SIGMA` through Bowling's logistic fit of the normal CDF) and cut at cover = `scuff_cover` x weight,
    weight = max(edge, 1 - height fraction); the height fraction runs over the world-Z bounds of the whole Apply Style
    selection (two new per-material group inputs, Scuff Low / Scuff High, set by `apply_style`; the bake copy is in
    world space, so the preview and the bake agree when a model is styled in one go). Ragged edges: a 4x finer noise,
    made uniform, moves the threshold by +-0.5 x the cover, which keeps the covered share. Wear = max(edge wear, scuff)
    = the mask's R, as before.
  - **Tones**: the shade v loses the grain: lo = 1 - grime, hi = 1 + `wear_lighten` + highlight, s = (hi - lo) /
    (tones - 1) (0.183 at the preset). The dark side is capped at tones - 3 levels so the top two stay free; the TOP
    level is the **wear tone**: wear > 0.5 takes it, mix(base, `wear_colour`, `wear_tint`); the light levels under it
    step toward the wear colour in equal parts (tones 4: base, +1 = 0.175 of the way, wear = 0.35); the dark levels are
    base x (1 + k s). Each base colour still paints at most `tones` colours.
  - **Strokes**: the stretched grain noise (world-aligned, `grain_stretch`, unchanged) made uniform; its top
    `grain_strength` / 2 are light strokes, its bottom `grain_strength` / 2 dark strokes, ragged at the ends by a 4x
    finer noise moving the threshold; they move the ROUNDED k by +1 / -1 AFTER the rounding, never on wear, never into
    the wear tone, clamped to the dark end. **On walls only** (my choice, from a picture): the cover is scaled by 1 at
    |normal z| <= 0.6 to 0 at >= 0.8, because the first pass laid round blobs on the roof (a level drag has no
    direction on a horizontal face).
  - **Found on the way** (the first pass, measured and looked at): with the light strokes on the top tone at tones 4,
    a light stroke WAS the scuff colour; my look at its unlit render of the subdivided copy: pale patches over the
    roof, bonnet and doors, worse than the old specks. Hence the tone split (a light level under the wear tone) and
    the wall gate. And the noise's spread depends on the slice: detail 2 / 3 / 4 read 0.0843 / 0.0781 / 0.0750 on two
    tilted 40 m planes (used), 0.0793 / 0.0735 / 0.0706 on a plane on the noise's integer lattice (the first
    calibration, which over-cut the scuffs 40 %: 0.0697 on a 20 m floor asked 0.05). With the tilted spreads, a 20 x
    20 m floor (weight 1) reads scuffs **0.0572** (asked 0.05) and a 20 m wall **0.0278** (0.025 expected from the
    height falloff); a single flat face's cover can read about 0.8-1.2 x the asked one.
- **The keys** (core `DEFAULT_PRESET` and `Art/Blender/gt_paint_preset.json` together, `_` notes on each), all
  PROPOSED, UNMEASURED against a look: `wear_pointiness` **0** (was 0.5), `grain_strength` **0.15** now the stroke cover
  (half light, half dark, of the walls), new `wear_tint` **0.35**, `scuff_scale_m` **0.3**, `scuff_cover` **0.05**.
  Constants in `core.py` (not preset keys, unchecked): `NOISE_SIGMA` (measured above), `RAGGED` 0.5, `WARP_FREQ` 4,
  `WALL_FULL` 0.6 / `WALL_NONE` 0.8, two decorrelating offsets. The group gains five inputs (Wear Tint, Scuff Scale,
  Scuff Cover, Scuff Low, Scuff High): an owner's file styled before this re-runs `build_group`'s interface rebuild,
  which keeps values by name. The panel's number line reads tones, strokes %, wear, scuffs %, grime.
- **The test** (`test_gt_paint.py`, extended; tone count still reported against its ceiling): per asset the
  **surface** = texels rasterised from the bake mesh's UV triangles (the rasterised count matches the UV area within
  0.2 %, 0 rasterised texels uncovered), the **wear share** (mask R > 0.5 over the surface, by the lower and upper half
  of the asset's height), the **stroke share** (surface texels not the commonest colour of their base colour's family,
  the family from each triangle's material; wear and grime texels count, so the share outside wear is beside it, and
  the share LIGHTER than the commonest colour outside wear), the **largest 4-connected wear patch** in texels (cut at
  UV seams, under 0.1 s), and for a multi-part asset the same per part. A second argument names another preset (the
  scratch runs). Found: the car's covered texels are **59 % margin** (295,873 surface of 722,096), so section 55's mask
  R mean 0.272 was margin-weighted: the surface wear share was 0.0576. Numbers (1K, 1 sample):

  | asset | tones (ceiling) | wear share, low / high half | stroke share (outside wear) | lighter outside wear | largest wear patch |
  |---|---|---|---|---|---|
  | TestCube before | 3 (4) | 0.0186, 0.0182 / 0.0191 | 0.0308 (0.0134) | 0.0050 | 152 |
  | TestCube after | **4** (4) | **0.0526**, 0.0808 / 0.0245 | **0.1753** (0.1295) | 0.0547 | 6,468 |
  | TestBox before | 2 (4) | 0.0012, 0.0011 / 0.0013 | 0.0114 (0.0105) | 0.0088 | 5 |
  | TestBox after | **4** (4) | **0.0288**, 0.0420 / 0.0156 | **0.1079** (0.0815) | 0.0420 | 4,254 |
  | TestCar before | 10 (16) | 0.0576, 0.0505 / 0.0687 | 0.3109 (0.3101) | 0.0041 | 215 |
  | TestCar after | **13** (16) | **0.0873**, 0.0919 / 0.0802 | **0.4401** (0.3865) | 0.0266 | 283 |
  | car subdivided (scratch) before | - | 0.0304, 0.0281 / 0.0338 | 0.2858 (0.2825) | 0.0041 | 377 |
  | car subdivided (scratch) after | - | 0.0602, 0.0698 / 0.0455 | 0.3983 (0.3597) | 0.0268 | 388 |

  The cube's tones after: #E3B04B 80.2 %, wear #E8C899 7.9 %, dark stroke #CFA144 6.9 %, light stroke #E6BD7A 5.0 %;
  the box's #D9772E 88.9 %, light #DE956F 4.1 %, dark #C66C29 3.8 %, wear #E2AD92 3.1 %. Per part on the flat copy,
  wear before -> after: roof 0.019 -> 0.019, bonnet 0.062 -> 0.086, front doors 0.085 -> 0.110, passenger doors 0.098
  -> 0.111; lighter outside wear: roof 0.008 -> 0.003, bonnet 0.003 -> 0.004, front doors 0.004 -> 0.042 (strokes are
  on walls). The car's stroke share carries its grime (G mean 0.476 on the inner faces), not only the strokes. The car
  after: mean albedo 169.9 124.1 91.2 (was 159.1 107.3 68.5), mask R mean 0.297 (0.272), 16 distinct colours in all =
  the ceiling. The wear rises on the flat copy because the scuffs add to an unchanged edge term; on the subdivided
  copy the edge term alone reads 0.0304 (scuffs off), the scuffs take it to 0.0602, lower half over upper.
- **Unreal** (`tasklist` clean before each run): `Art/setup_look_l1.bat` 19:46: "done: 3 of 3 asset(s) imported,
  textured and given their instance", both materials compiled. Its log also names three folders it skipped with an
  error: `Art/Export/FrontDoors/`, `PassengerDoors/`, `RearPanel/` hold `_D`/`_M` PNGs written 19:12 and no FBX - not
  written by this follow-up's runs (the owner's own bakes at the gate, I guess); left untouched. `proving_shots.bat 4`:
  2/2 written. `sample_tones.ps1`, section 55's "after" beside this one's:

  | box | 55 after: mean, tones (all) | follow-up after: mean, tones (all) | follow-up after - before |
  |---|---|---|---|
  | TestBox (608 px) | 255.0 197.1 97.0, 2 | 254.4 197.5 101.7, **12** (16) | +48.0 -4.0 -91.3 |
  | TestCar (7,912 px) | 244.2 190.3 96.8, 12 (144) | 243.9 193.7 111.2, **28** (169) | +38.8 -6.5 -80.3 |
  | control_car (2,560 px) | 235.5 227.9 209.0, 2 | 235.5 227.9 209.0, 2 | +0.2 +0.4 +0.5 |

  The before picture reads as before (TestBox 206.4 201.5 193.0, TestCar 205.1 200.3 191.5) and the control moves
  under half a level. The red still clips at 252-255 in the sun. **My look at `proving_09_painted_after`**: the copy
  reads light orange; pale patches gather on its lower half, along the door and sill edges and on the tyres
  (grey-white patches there), with a few pale level drags along the side; the darker strokes hardly show at this
  distance; the roof line is clean; the box is orange with one pale patch at a lower corner. Beside section 55's
  picture (a near-flat orange side with a few small flecks and clean dark tyres) the new one carries MORE and LARGER
  pale patches, low and on the tyres: the scuffs are as proposed (5 % where the weight is 1) and may read as more
  worn. My looks at the scratch unlit renders of the subdivided copy (the owner's gate is a subdivided model): old,
  even small specks; new, a clean roof and bonnet top apart from a few scuff patches, level light and dark drags on
  the doors and sides, scuffs and edge lines low.
- **Tests.** `bash Art/blender_test.sh` **PASS** (5 s). `bash Art/suite.sh proving` **PASS** (34 s). No flake met.
- **Unchecked.** The owner's look (the gate: they re-look); every number above (`wear_tint`, `scuff_scale_m`,
  `scuff_cover`, the stroke cover, the wall gate, the ragged and warp constants); the pointiness on the owner's live
  model; the preview in EEVEE (scuffs, walls and strokes are plain math and noise, the Bevel term is Cycles-only);
  Apply Style on a subset (the height bounds become that subset's); grey scuffs on the tyres; no strokes on
  horizontal faces; at tones 4 the light stroke (0.175 of the way to the wear colour) and the wear tone (0.35) are
  both pale steps; the stroke and scuff covers on a single flat face (0.8-1.2 x); the frame/bake cost of the extra
  noises (the car's bake 0.72 s, as before).

### Follow-up 2, 2026-09-24: painted normals from the owner's OW Painterly Normal Baker; scuffs and strokes off by default

- **The owner's direction** (after the first follow-up): "I don't want heaps of those wear marks / scuffs. I want the
  lights and darks to be 'painted' using normal maps." Their reference: a painted apple where every brush stroke is a
  flat facet tilted in the normal map. **The technique in two lines:** each brush dab commits the surface under it to
  ONE flat, slightly tilted normal, so the sun lights each dab as its own plane and the lighting paints the lights and
  darks; the albedo under it stays a few flat tones. No game number moved; no C++ change; nothing in the post-process,
  water, mud, landscape or physics touched.
- **How GT Paint calls the extension** (the owner's `ow_painterly_normal_baker` 0.5.0 in
  `%APPDATA%\Blender Foundation\Blender\5.1\extensions\user_default\`, not modified; GT Paint does not paint dab
  normals itself). `core.bake`, after `_D` and `_M` are saved and before the bake copy is hidden, calls
  `core.bake_normal`: `ensure_normal_baker` uses the extension when it is registered (`bpy.types.PNB_OT_generate` and
  `Scene.pnb_settings`, the owner's live Blender); otherwise it imports the package from its folder under its own id
  (`importlib` with `submodule_search_locations`, `sys.dont_write_bytecode` on, so nothing is written there: checked,
  no file in the folder newer than 2026-07-12) and calls its `register()`; a missing folder is a `GTPaintError` naming
  the path, which fails the Bake (and the test) loudly. Then: the scene's `pnb_settings` are snapshotted, the preset's
  `normal` block is written into them with `resolution` = the bake size and `output_dir` = a temp folder,
  `bpy.ops.pnb.generate()` runs on the bake copy (its one UV: `GT_UV`, or a single source's own kept UV), the settings
  are put back, and the extension's **`T_<Asset>_GTBake_Painterly_Normal_DX.png`** (found from `last_gl` with `_GL`
  -> `_DX`) is moved to **`Art/Export/<Asset>/T_GT_<Asset>_N.png`**; its OpenGL twin and report JSON go with the temp
  folder. The file is a **16-bit RGBA PNG** (the extension saves a float image).
- **Found and fixed on the way** (both measured): (1) the extension's `restore_guard` puts the materials back with
  `materials.clear()` + append, which **reset the bake copy's face material indices** (the judge run's bake reported
  "put back"): `bake_normal` saves the indices and restores them, so Export and the test's per-part numbers see the
  parts as before (the per-part wear shares are the first follow-up's flat-copy 'before' values again: roof 0.019,
  bonnet 0.062, front doors 0.085, passenger doors 0.098; with the indices reset every texel would be one part). (2) Blender loads a
  16-bit PNG into a float buffer, which an sRGB colour space linearises: the test first read the normal's mean as
  **55 55 255** (0.5 -> 0.214); read as Non-Color it is **127.6 127.5 254**. The preview sets Non-Color too.
- **Handedness**: `_N` is the extension's **DirectX** file (its `directx_flip` = 1 - green of the OpenGL bake), per its
  own docstring's "UE 5.8 round trip"; imported with no green flip, the project's convention. NOT re-verified here.
- **The preview** (Apply Style and Bake): `core.attach_normal` adds UV Map (the bake's UV) -> the `_N` image
  (Non-Color) -> Separate Color, 1 - G, Combine (DirectX back to the OpenGL a Blender Normal Map node reads) -> Normal
  Map, tangent space, on that UV -> the Principled BSDF's Normal, in every GT material of the asset (nodes named
  `GT_N_*`, our own names). Bake loads it straight after writing `_N`; Apply Style loads it when
  `<Export>/<Asset>/T_GT_<Asset>_N.png` exists and `normal_enable` is on. **The catch, measured:** the dabs are baked
  on the bake copy's UV. On the blockout every body part has a Mirror modifier and no UV (15 parts; the 4 wheels have
  `UVMap`), so the copy is smart-projected (`GT_UV`) and **0 of 17 sources carry that UV**: the preview can only show
  on the copy. Hence a new button, **Show Bake** (`gt_paint.show_bake`): it swaps the viewport between the sources and
  `<Asset>_GTBake` (viewport hiding only; the copy records its sources in `gt_sources`). A single source that keeps its
  own UV shows the dabs on itself (unchecked: no such asset in the test). On a source without the UV the chain is
  harmless in Cycles: the scratch render of the sources with the chain against without it differs by **0.000** (max
  0.0) over 129,600 pixels; EEVEE unchecked. The panel gains two lines: "Normal: T_GT_<Asset>_N.png loaded in k of n GT
  material(s), shows on ..." (or "no _N yet" / "on disk, NOT loaded" / "off in the preset") and "Baker: enabled in this
  Blender / found, Bake imports it / MISSING at <path>".
- **The preset** (core `DEFAULT_PRESET` and `Art/Blender/gt_paint_preset.json` together, `_` notes on each; a partial
  `normal` block in the JSON keeps the other defaults), all PROPOSED, UNMEASURED for this use: `scuff_cover` **0.0**
  (was 0.05), `grain_strength` **0.0** (was 0.15; the strokes live in the normal now); `wear_lighten` 0.25 and edge
  wear kept, `wear_pointiness` 0, `tones` 4; every layer still available. New: `normal_enable` **true**,
  `normal_baker_path` **""** (= the path above), and `normal` = the baker's own defaults: `dab_length_cm` **4.4**,
  `length_min` **0.7**, `length_max` **2.4**, `aspect` **1.5**, `coverage` **3.0**, `normal_jitter` **4.0** deg,
  `rot_jitter` **20.0** deg, `detail_enable` **true**, `detail_length_cm` **1.8**, `seed` **7**, `brush_path` **""**
  (its bundled `oil_knife.png`). The baker's other settings (detail coverage 1.5 / jitter 6.5, palette 20 x 0.6, flow
  axis Z, ink features off, painted colour off) stay as the scene holds them: the defaults in the test.
- **The test** (`bash Art/blender_test.sh` **PASS**, 92 s, `--factory-startup` kept: the baker is imported by path).
  New per asset: the `_N` file and size (a missing `_N` fails like any file), over the surface texels the normal's
  mean (8-bit scale), the RMS tilt of the decoded normals from straight up, the dab coverage (share tilted > 2 deg),
  the preview check (every GT material carries the `_N` on the bake's UV), and at the end Apply Style keeping the
  cube's `_N` and Show Bake swapping and back. Bake now takes about 30 s an asset (the car's `_N` 28.8 s; `_D` + `_M`
  about 1 s as before):

  | asset | `_N` | mean 8-bit | RMS tilt (mean, 95 %, max) | dab coverage > 2 deg (> 5, > 10) | dabs main / detail |
  |---|---|---|---|---|---|
  | TestCube | 3,084 KB | 127.7 127.5 254.7 | **4.17** deg (3.40, 7.66, 14.9) | **0.610** (0.276, 0.005) | 17,757 / 40,000 |
  | TestBox | 3,721 KB | 127.6 127.5 254.2 | **6.46** deg (3.88, 13.63, 75.5) | **0.521** (0.212, 0.082) | 14,401 / 40,000 |
  | TestCar | 4,648 KB | 127.6 127.5 253.9 | **7.79** deg (4.25, 14.25, 88.9) | **0.540** (0.269, 0.098) | 40,000 / 40,000 |

  The car's two passes hit the extension's 40,000-dab cap (`sample_dab_frames` `max_count`), so its coverage 3.0 is
  not reached (read from the code and the counts; how far short, unmeasured). The albedo with the new defaults, first
  follow-up -> now: TestCube tones 4 -> **2** (#E3B04B 95.4 %, wear #E8C899 4.5 %), wear share 0.0526 -> **0.0186**,
  stroke share 0.1753 -> **0.0190** (outside wear 0.1295 -> 0.0004); TestBox 4 -> **1** (#D9772E 99.5 %), wear 0.0288 ->
  **0.0012**, strokes 0.1079 -> **0.0015** (0.0815 -> 0.0004); TestCar 13 -> **12** (ceiling 16), wear 0.0873 ->
  **0.0576**, strokes 0.4401 -> **0.3822** (0.3865 -> 0.3445, lighter outside wear 0.0266 -> 0.0005: what is left is
  the car's grime, G mean 0.476, not strokes). The wear shares are section 55's first numbers again (edge term only).
- **The judge picture** (scratch, `judge/judge_after.png` and `judge_before.png` in the session scratchpad): a copy of
  the blockout with a scratch Subdivision Surface (level 2, smooth) on its 17 parts, styled and baked through
  `core.bake` (36,536 faces, `_N` 28.4 s, 40,000 / 40,000 dabs), the bake copy rendered lit in Cycles (64 samples, no
  denoise, Standard view) under one sun (4.0, from -0.55 -0.45 0.70) and a 0.05 grey world, the same view with the
  `_N` and with it detached. Over 312,876 car pixels: mean 107.3 78.7 62.2 -> 106.7 78.3 61.8, 5-bit tones over 0.5 %
  23 -> 22 (699 -> 695 colours), mean |after - before| 5.11 (three 8-bit channels summed), 21.8 % of the car's pixels
  changed by more than 6. **My look at it** (and a 2x crop of the doors): the dabs show as short vertical strokes a few
  centimetres long, lighter where they face the sun and darker where they turn away, dense over every panel, gathering
  darker along the lower door edges and sills, dark flecks on the pale bumpers, mottling on the tyres; at this size it
  reads as a fine dry-brush texture over the whole car, not the apple's few large facets. Before: smooth orange
  panels with soft gradients and pale seam lines.
- **Unreal** (`tasklist` before each run: no editor, no GrandTour; **FarCry6.exe was running** through all three runs,
  not a stop condition in this brief, so the rendered run shared the GPU with it). `Art/Unreal/setup_look_l1.py`:
  `_N` imported as `T_GT_<Asset>_N` (TC_Normalmap, sRGB off, `flip_green_channel` False set explicitly); an asset
  without `_N` gets `/Engine/EngineMaterials/FlatNormal` (logged; not met); `M_GT_Painted` gains `Normal`
  (SAMPLERTYPE_NORMAL) and `NormalStrength` **1** (proposed): Normal = normalize(lerp((0,0,1), sampled, NormalStrength)),
  no specular change; each `MI_GT_Painted_<Asset>` gets its `_N`. A folder without `SM_<Asset>.fbx` is now ONE log line,
  not an error: `SETUP_LOOK_L1 skip Art/Export/FrontDoors/: no SM_FrontDoors.fbx (bakes without an export: ...)`, the
  same for `PassengerDoors/` and `RearPanel/` (the owner's, untouched). `Art/setup_look_l1.bat` 10:41: "done: 3 of 3
  asset(s) imported, textured and given their instance", both materials compiled. `Art/proving_shots.bat 4`: 2/2
  written (232 s). `sample_tones.ps1`:

  | box | before (grey) | 55 after | first follow-up after | now after | now after - before |
  |---|---|---|---|---|---|
  | TestBox (608 px) | 206.5 201.4 192.8, 2 | 255.0 197.1 97.0, 2 | 254.4 197.5 101.7, 12 (16) | 255.0 197.2 97.1, **2** (2) | +48.5 -4.1 -95.7 |
  | TestCar (7,998 px) | 205.0 199.9 191.1, 6 (65) | 244.2 190.3 96.8, 12 (144) | 243.9 193.7 111.2, 28 (169) | 243.9 190.6 98.0, **12** (144) | +38.9 -9.3 -93.1 |
  | control_car (2,560 / 2,592 px) | 235.2 227.0 207.8, 2 | 235.5 227.9 209.0, 2 | 235.5 227.9 209.0, 2 | 235.5 227.6 208.7, 2 | +0.2 +0.6 +0.8 |

  **The expected sign did not show**: the lit picture's tones are section 55's (box 2, car 12), fewer than the first
  follow-up's albedo strokes gave (12 / 28). Two readings, neither measured: at 9 m a 4.4 cm dab is about 4 x 2.5
  pixels on the car (461 cm over about 400 px), so the normal's mips average it toward flat; and the red channel
  clips at 255 in the sun (the box reads #FCC464 at 98.4 %), so a few degrees of tilt barely moves the colour.
  **My look at `proving_09_painted_after`** (and a 3x crop of the painted car): the copy reads as one bright light
  orange side with faint, soft, low-contrast mottling (slightly darker smudges low on the doors and bonnet), thin pale
  dashed edge-wear lines along the panel seams and arches, pale bumpers, dark tyres with pale rims around the wheel
  holes; no distinct dab facets at this distance; the pale scuff patches of the first follow-up are gone; the box is
  one flat orange.
- **Tests.** `bash Art/blender_test.sh` **PASS** (92 s). `bash Art/suite.sh proving` **PASS** (36 s). No flake met.
- **Unchecked.** The owner's look (the gate: they re-look); every number above, above all `dab_length_cm` 4.4 (the
  baker's default from a character, the hedgeknight, now on a 4.6 m car; the proving camera does not resolve it) and
  `NormalStrength` 1; the handedness in Unreal (the extension's claim, not re-verified); the preview in EEVEE and in a
  live Blender UI (panel lines and Show Bake drawn), the extension used as registered in the owner's Blender (the test
  only covers the import-by-path route); a single source keeping its own UV; the FBX's tangents against Blender's bake
  tangents in Unreal (MikkTSpace on both sides expected, not compared); the 16-bit `_N` import's memory and the
  bake cost on a dense model (about 30 s an asset here, most of it the extension's per-dab painting); a stale `_N` is
  left in place when `normal_enable` is turned off (Unreal would still import it).

- **Defaults re-proposed after the variant pictures (2026-09-24, the orchestrator).** Two judge renders of the TestCar copy
  (the follow-up's camera and sun): A `dab_length_cm` 35 / `normal_jitter` 14 / `coverage` 2.0 (RMS tilt 19.97 deg, 0.897 tilted
  > 2 deg, 1,549 main dabs) and B 20 / 10 / 2.5 (17.58 deg, 0.924, 5,929). The orchestrator's look: A = lit and shaded patches
  tens of centimetres across with ragged edges on the roof, bonnet and doors, the closest to the owner's apple reference; B =
  busier, streaky vertical strokes; the shipped 4.4 cm = fine dry-brush grain. The preset and `DEFAULT_PRESET` now carry A's
  three numbers (PROPOSED, UNMEASURED against the owner's look; the rest of the block unchanged; the 1.8 cm edge-detail pass
  still hits the 40,000 cap). `bash Art/blender_test.sh` PASS in 302 s: TestCube RMS tilt 6.62 deg / 0.675 tilted > 2 deg,
  bake 91.5 s; TestBox 10.36 / 0.642, 133.6 s; TestCar 17.68 / 0.885, 71.9 s (a max tilt of 107.7 deg on the car = a few
  texels decoded past the surface, unexplained). Not re-imported into Unreal and no new picture: the Test assets in
  /Game/GrandTour/Textures/Painted still hold the 4.4 cm bake.
- **Second re-proposal (2026-09-24, the orchestrator; the owner on variant A: "much better; increase brush size and stroke
  length, and reduce colour jitter").** Two more judge renders: C `dab_length_cm` 55 / `aspect` 2.0 / `normal_jitter` 8
  (RMS tilt 20.47 deg, 0.879 tilted > 2 deg, 837 main dabs, 109 s) and D 75 / 2.5 / 6 (21.70 deg, 0.891, 563, 168 s). The
  orchestrator's look: C = dabs a third to half a door across, strokes along the roof and bonnet, a soft light/dark
  difference, a few hard dark blocks at the bonnet front; D = the largest and longest, half a bonnet, with hard dark shards at
  the front and roof corners (the dabs decoded past 90 deg, max 107.7 on the car, are the likely cause: a flat dab across a
  curve). C's three numbers are now the defaults (PROPOSED, UNMEASURED). The measured tilt did not fall with the jitter (14 ->
  8 -> 6 deg gave 20.0 -> 20.5 -> 21.7 deg RMS): the jitter is the hand wobble, the dab's own flattening sets the light/dark
  strength. So a new top-level preset key `normal_strength` 0.7 (PROPOSED) drives the preview's Normal Map Strength
  (`attach_normal(..., strength)`), and `NORMAL_STRENGTH` in `Art/Unreal/setup_look_l1.py` mirrors it by hand at 0.7; 1 = as
  baked. `bash Art/blender_test.sh` PASS in 571 s (the bake time grows with the dab size: TestCube 169.5 s, RMS tilt 5.42 deg,
  0.724 tilted > 2 deg; TestBox 287.0 s, 8.46, 0.651; TestCar 109.9 s, 17.09, 0.864, max 90.7 deg). Not re-imported into
  Unreal and no new picture. Unchecked: the owner's look at C on their own model; every number; the preview at 0.7.
- **`normal_strength` 0.7 -> 0.5 (2026-09-24, the orchestrator; the owner on C: "the colour jitter / colour difference in
  strokes is still too big").** The C bake re-rendered at Normal Map Strength 1.0 / 0.5 / 0.3 (no re-bake): the whole-body
  luminance sd 34.51 / 34.19 / 34.00 does not separate them (lit vs shaded panels dominate); the local spread (luminance minus
  its 15 x 15 px mean over 55,049 orange-body pixels, hue 10-45 deg, saturation > 0.45) 6.02 / 5.05 / 4.61 does. The
  orchestrator's look: 0.5 = soft dabs that still read as strokes; 0.3 = faint mottling, nearly smooth-shaded. 0.5 is the
  default now (preset, DEFAULT_PRESET, NORMAL_STRENGTH in setup_look_l1.py; PROPOSED, UNMEASURED on the owner's model). No
  re-bake was needed and the Blender test was not re-run for this scalar (JSON and Python parse checked); Unreal not
  re-imported.
- **Unreal import of the C bake (2026-09-24, the orchestrator; the owner: "Nice. Import to unreal").** `Art/setup_look_l1.bat`
  at 11:30 with FarCry6 running (no editor): 3 GT Paint exports (TestBox, TestCar, TestCube) with _D / _M / _N (TC_NORMALMAP,
  sRGB off, flip green off), the owner's FrontDoors / PassengerDoors / RearPanel folders skipped as bakes without an FBX,
  M_GT_PaintedGrey and M_GT_Painted compiled (NormalStrength 0.5), MI_GT_Painted_<Asset> x 3. `proving_shots.bat 4` at 11:34 +
  `sample_tones.ps1`: TestBox 206.5 201.3 192.8 (2 tones) -> 255.0 197.3 97.2 (2); TestCar 205.0 199.9 191.2 (6) -> 244.1
  191.3 99.0 (13; 12 in the 4.4 cm follow-up 2 run); control_car +0.2 +0.7 +1.1. The lit orange side clips: the top tones
  are #FCC45C / #FCCC64 (red 252), so the dabs cannot show as tones in that box. The orchestrator's look: a flat bright orange
  car copy with faint darker mottling on the side and pale flecks along the edges; the dabs barely read at 9 m in this sun,
  where the Blender judge render (an oblique sun, no clipping) shows them plainly. Exposure and sun angle are L2's; the
  strength is the owner's. `bash Art/suite.sh proving` PASS (35 s).

### L1 follow-up 3 (2026-09-24): the owner's panel bakes on the driven car

The owner: "just apply the new paint in game" (the prompt: docs/prompts/LOOK_L1_car_paint.md). `tasklist` clean before
every build and run (no FarCry6, editor or GrandTour process). No tuned number moved; the water, the mud, the landscape
material, the L2 post layer, the physics and Art/Blender were not touched. **Blocked at the crux**: the car's panels have
no UV, so the bakes cannot lie on them; everything else is built and the switch is at its safe default (UsePaint 0).

- **M_GT_Vehicle takes a bake** (`Art/Unreal/setup_m1_body.py`). New parameters: PaintAlbedo (Color sampler, default
  /Engine/EngineResources/DefaultTexture), PaintMask (Masks, DefaultDiffuse_TC_Masks), PaintNormal (Normal, FlatNormal),
  UsePaint 0, WearLighten 0, GrimeDarken 0 and NormalStrength 0.50, read at build time from setup_look_l1.py's
  NORMAL_STRENGTH (M_GT_Painted's number, not a new one). The painted colour is M_GT_Painted's, lerp(PaintAlbedo, white,
  PaintMask.R x WearLighten) x (1 - PaintMask.G x GrimeDarken); roughness PaintMask.B; normal normalize(lerp((0,0,1),
  PaintNormal, NormalStrength)) with the dent normal whiteout-blended over it (normalize(dent.xy + paint.xy, dent.z x
  paint.z)). Each insertion is lerp(today's input, painted, UsePaint) at the Grime node's BaseColor and Roughness inputs
  and at the Normal pin, so UsePaint 0 hands on today's values and the Grime node (runtime Dirt), MF_Weather (wetness,
  snow), MF_Dents (WPO and normal) and the clear coat stay wired as they were, acting on top of the paint with UsePaint 1.
  Plain nodes, no HLSL; the MPC count is unchanged (MF_Weather's only); no Substrate fallback was needed. The defaults
  load with `load_object`: the commandlet's asset registry does not list /Engine/EngineMaterials/FlatNormal
  (EditorAssetLibrary.load_asset fails), so setup_look_l1.py's prop path for a bake without an _N
  (`eal.load_asset(FLAT_NORMAL)`) would fail too; not fixed here (every prop has an _N today). Rebuilt with
  setup_m1_body.bat ("M_GT_Vehicle compiled (painted path behind UsePaint 0 ...)") then setup_m1_masters.bat (masters
  through MF_Weather 6/6).
- **The importer** (`Art/Unreal/setup_look_l1.py`, a second pass after the props). Art/Export/<Asset>/ with
  T_GT_<Asset>_D.png, no SM_<Asset>.fbx and a car panel of that name (SM_RR_<Asset>_L/_R or SM_RR_<Asset>; Wheel skipped
  as in the body component) -> _D (TC_Default, sRGB), _M (TC_Masks, linear), _N (TC_Normalmap, no green flip, if
  present) into /Game/GrandTour/Vehicles/Bodies/RangeRover/Paint as T_GT_<Asset>_D/_M/_N, over the earlier import; a
  stale _N goes when the new bake has none. No mesh import. One line per panel: painted / no bake / no such panel / no
  UV. The UV gate (added after the painted picture below): a panel mesh whose UV0 has no area gets nothing and loses an
  earlier import. In the commandlet `delete_asset` logs "Force Deleting" but leaves the .uasset on disk, so the pass
  removes the file too. The last run (19:03): FrontDoors, PassengerDoors, RearPanel "no UV - SM_RR_<Asset>_L UV0 area
  0.0000, 1 distinct UV(s), ..._R ... the earlier import's T_GT_<Asset>_D, T_GT_<Asset>_M removed (UsePaint stays 0)",
  12 panels "no bake", "panel pass done: 0 painted"; the props pass as before (3 of 3).
- **The body component** (`Source/GrandTour/Vehicle/GTBodyComponent.h/.cpp`). PaintFolder (UPROPERTY, the Paint folder,
  read through the asset registry once per car); after MakePanelMaterial the panel's name with a trailing _L/_R
  stripped is the asset; with T_GT_<Asset>_D and _M found the panel's instance gets PaintAlbedo, PaintMask (PaintNormal
  when an _N exists) and UsePaint 1. One line per car: "UGTBodyComponent: N panels painted from <folder> (UsePaint 1):
  FrontDoors_L=FrontDoors, ...". The instance is the panel's for life: the hinge swing, Detach and ReattachAll move the
  same component and never call SetMaterial (code), and the doors-open picture below shows the paint going along.
- **The runner** (`Source/GrandTour/Core/GTProvingShotsRunner.h/.cpp`, step 4) logs two more boxes on the car,
  car_FrontDoors and car_RearPanel (the camera-side half, 25-75 % along and 30-60 % up the panel's bounds on its
  camera face, as the props), with the panel's material and UsePaint; `Art/tools/sample_tones.ps1` reads them by default.
- **The bakes** (PowerShell over the PNGs, texels with alpha > 0): T_GT_FrontDoors_D mean 209.8 118.8 52.1 (70.5 % of
  1024 x 1024 painted; 3 tones #DC742C 64.5 %, #BC6424 26.1 %, #E4A484 9.4 %), PassengerDoors 210.1 119.1 52.7 (81.2 %,
  the same 3 tones), RearPanel 215.9 124.0 57.5 (51.6 %; #DC742C 79.5 %). No _N: they predate the painted-normal bake.
- **The painted picture and the crux** (`proving_shots.bat 4`, the L2 layer on in every picture; before 18:40, painted
  18:56). Picture 08 puts the car on the same pixels in both runs (control_car 541 344 620 375 in each), so the new
  boxes read the before picture too: car_FrontDoors 214.7 206.9 183.6 (5 tones) -> 143.8 74.9 38.2 (4 tones: #944C24
  72.0 %, #8C4C24 25.0 %), car_RearPanel 215.4 208.0 184.2 (6) -> 200.2 155.5 124.2 (2: #CC9C7C 95.8 %), control_car
  214.5 206.6 183.1 -> 101.0 59.1 37.3; the bakes' own means are 210 119 52 and 216 124 58 with three tones each. My
  look (a crop of the car at 3x): each painted panel is one flat colour, front doors brown-orange, passenger doors near
  black, rear panel pale salmon, with not one strip, edge band or fleck of the bake: the paint does not lie on the
  panels. The cause, measured: every car panel in Unreal has UV0 (0,0) on every vertex (a mesh-description probe:
  SM_RR_FrontDoors_L/_R, PassengerDoors_L, RearPanel_L and Bonnet each 1 distinct UV, UV area 0.0000; the 2026-09-11
  export carried none), and a copy of Art/rangerover.blend (saved 2026-09-23 19:06, six minutes before the bakes) has no
  UV layer on frontDoors, passengerDoors, rearPanel or any other body object (only the four wheels carry UVMap). So GT
  Paint's build_bake_mesh gave each bake a fresh smart-project UV that lives only on its bake copy; nothing in the car
  carries it and each panel samples the bake's wrapped corner texels. Stopped there, no UV hacks; the UV gate went in.
  The three pictures 08 (before, painted, final) and their boxes: Saved/Screenshots/Proving/carpaint/ and
  Saved/Logs/carpaint_compare.log (`sample_tones.ps1 -LogName carpaint_compare.log -Folder Proving\carpaint -Names
  carpaint_before,carpaint_painted -Boxes control_car,car_FrontDoors,car_RearPanel`).
- **The final picture** (19:06, the gate's run: nothing imported): "UGTBodyComponent: 0 panels painted", UsePaint 0 on
  the logged panels; against before, car_FrontDoors +0.6 +0.7 +0.9 (5 tones), car_RearPanel +0.2 +0.0 +0.7 (4),
  control_car +0.5 +0.6 +0.9 (5): the run-to-run drift (the control read +0.2 +0.7 +1.1 in the import above), so
  UsePaint 0 is today's car within it. My look: the car cream all over, as before.
- **The door swing** (`base_shots.bat` 19:01, the three imports still in): base_5_doors_open, my look: the swung front
  door keeps the brown-orange and the passenger door the black of the painted picture, so the instance swings with it.
- **Tests.** `bash Art/build.sh` == build exit 0 (81 s). `bash Art/suite.sh body proving` 2 PASS (body 21 s, 20 panels,
  4 detached; proving 35 s). No flake met. No "Failed to compile" in the three rendered logs.
- **Unchecked.** The bake on the car at all (blocked); a dent over paint (no shots step); a detached painted panel in a
  picture (the body test detaches 4, no picture); PaintNormal with a real _N and the whiteout blend's look; the painted
  path's frame cost (three more samples per car pixel, taken at UsePaint 0 too); whether export_rangerover.py carries a
  UV map into the FBX; what a mirrored object's shared UV (both halves on the same islands) does to its bake.
- **The way on (the owner's).** Give frontDoors, passengerDoors and rearPanel (any panel to paint) a UV map in Blender
  and save; Art/export_rangerover.bat, then Art/import_rangerover.bat; bake them again with the current addon (dabs; a
  single object with a UV keeps it, so the bake lands on the panel's own UV); rerun Art/setup_look_l1.bat; the car's
  panels then take UsePaint 1 by themselves. Then the look gate: the owner drives and looks at the doors and the rear
  panel.

### L1 follow-up 4 (2026-09-25): unwrap on Bake, the car painted

The owner: "just apply the new paint in game", then, told the car's panels have no UV maps, "yep, add unwrapping" (the
prompt: docs/prompts/LOOK_L1_unwrap.md). `tasklist` clean before every .bat, Unreal and Blender run (no FarCry6, editor,
GrandTour process or Blender at any run). No tuned number moved: the preset, the water, the mud, the landscape material,
the L2 post layer, the physics and M_GT_Vehicle are as they were. No C++ changed, so no build. **The car wears the
paint**: the three panels carry a UV from Blender to Unreal, the gate imports their bakes and the body component paints
both halves of each.

- **Unwrap in the addon** (`Art/Blender/gt_paint/core.py`, `__init__.py`, bl_info 0.3.0). `unwrap_object`: a mesh object
  with no UV map gets a new map GT_UV (the bake copy's name) by `smart_project`, now GT Paint's one projection, shared
  by the bake copy of several sources and the unwrap: the preset's uv_angle_deg 66 and uv_island_margin 0.01, area
  weight 0, aspect corrected, not scaled to bounds - the parameters the bake copy used before, no new number. It
  projects the object's own mesh with its modifiers not applied (Tab, select all, Smart UV Project, Tab), so a Mirror's
  two halves share the islands, as the car exporter and the game see them; the view layer's selection, the active
  object, the object's hiding and the mesh's element selection and hiding are put back, so only the UV changes. One
  console line per object: "GT Paint: unwrapped frontDoors -> UV map 'GT_UV' (new): smart project (angle 66.0 deg,
  island margin 0.010, area weight 0, aspect corrected, not scaled to bounds) over its own 59 faces, modifiers not
  applied; UV area 0.5988". `build_bake_mesh`: ONE source with no UV is unwrapped first, then the keep-UV path takes
  over (the bake copy inherits GT_UV, the bake lands on it, Export and export_rangerover.py carry it, a second Bake
  keeps it); several sources, or a source with a UV: unchanged. The panel: an "Unwrap for Paint" button (every selected
  mesh with no UV map; one with a map is left alone unless the "Replace" tick is on, default off, which re-projects its
  render-active map in place, name kept) and a line saying what Bake will do ("UV: no UV: Bake unwraps it (smart project
  -> GT_UV)", "UV: Bake keeps its UV map 'GT_UV'", "UV: N objects: Bake joins them on one fresh smart-project atlas").
  `uv_area` sums a map's face area in 0-1 UV space (the areas below). A side effect, measured: TestCube and TestBox are
  made with no UV, so their own Bake now unwraps the source. TestCube's numbers are unchanged (67.3 % baked, 2 tones,
  mean 227.2 177.1 78.6); TestBox's moved a little (87.0 -> 89.2 % baked, 1 tone, 4 colours for 3, mean B 46.5 -> 46.3):
  its UV is now projected before its Bevel modifier, which interpolates it over the bevel.
- **The test** (`Art/Blender/tests/test_gt_paint.py`, `nouv_case`). TestNoUV, a copy of TestCube with its GT_UV removed,
  through the panel's Bake: the source comes out with 1 map, GT_UV, area 0.6510; the albedo 67.3 % baked, 2 tones
  (#E3B04B 95.4 %, #E8C899 4.5 %, counted as run_asset counts), mean 227.2 177.1 78.6. A second Bake: 1 map, the same
  name, the UVs unchanged, the bake copy on GT_UV. Unwrap for Paint on a second UV-less copy and TestCube: the copy gets
  GT_UV, area 0.6510 (= the Bake's), TestCube's map is left alone. The case bakes into a temp folder beside the blend
  copy with a temp preset that differs only in normal_enable false (the _N is not what it checks, and it costs 170-350 s
  a bake). `bash Art/blender_test.sh` RESULT PASS, exit 0, 618 s. The addon copied to the owner's Blender as before
  (`%APPDATA%\Blender Foundation\Blender\5.1\scripts\addons\gt_paint\`, __init__.py and core.py, byte-identical to
  Art/Blender/gt_paint).
- **The owner's car** (`Art/rangerover.blend`, the one repo file this stage wrote). The backup first:
  `Art/rangerover_backup_20260925_121018.blend` (139029 bytes, byte-identical to the file as the owner saved it on
  2026-09-23 at 19:06). Headless, the blender_test way (Blender 5.1 -b --factory-startup, the addon from Art/Blender, a
  scratch script) on the owner's file: its signature (objects, collections, per object the transform, the modifiers with
  every setting, the material slots, the mesh counts, vertex, loop and edge hashes, attributes, UV maps with their area,
  selection and hiding); Unwrap for Paint on frontDoors, passengerDoors and rearPanel only; the signature again, only
  those three UV maps differing; that UV-only state written as a stage copy beside the file, before Apply Style or a
  bake touched the session (the file has 0 materials, so Bake needs Apply Style's GT materials, which are not the
  owner's to keep); Apply Style + Bake as FrontDoors, PassengerDoors and RearPanel into Art/Export; only after all three
  wrote a new _D, _M and _N was the stage copy re-opened, compared with the file as opened (only the three UV maps
  differ) and moved over Art/rangerover.blend (143403 bytes), which read back the same. Objects 23 before and 23 after
  (19 meshes, 0 materials, 6 images, 2 collections both times); no bake copy, material or GT Paint setting in the saved
  file. Log: Saved/Logs/paint_owner_car.log.
  - UV (GT_UV, 1 map each, area in 0-1 UV space): frontDoors 0.5988 (59 faces), passengerDoors 0.5007 (63), rearPanel
    0.6461 (59). Each is its Mirror half's projection, which the game's _L and _R share.
  - Bakes (1024 px, over the texels with alpha): FrontDoors 68.1 % baked, 3 tones #D9772E 57.1 %, #C66C29 26.8 %,
    #E2AD92 16.0 % (4 colours in all), mean 213.4 124.7 60.7, _N 3061 KB (346 s, dabs 86/40000); PassengerDoors 57.0 %,
    the same 3 tones at 55.0/28.3/16.6 %, mean 213.1 124.9 61.3, _N 2572 KB (307 s, 71/40000); RearPanel 73.0 %, #D9772E
    76.2 %, #E2AD92 16.7 %, #C66C29 6.9 %, mean 217.2 127.3 62.5, _N 2841 KB (289 s, 36/25136). The _N means over the
    baked texels (8-bit scale) 128.1 128.5 253.7, 127.2 127.3 254.3, 128.6 126.7 253.8.
- **Export, import, apply.** `export_rangerover.bat` (12:26): 19 static meshes, SK_RangeRover 17 parts 4590 tris, the
  warnings the owner's meshes already gave (frontDoors 18 and passengerDoors 10 doubled verts merged, 26 edges on 3+
  faces each; frontDoors.001 skipped, 1 face). `import_rangerover.bat` (12:27): "IMPORT_DONE: 24 assets". A read-only
  Unreal probe of the imported panels (their mesh descriptions, summed as the gate sums them): SM_RR_FrontDoors_L and _R
  UV0 area 0.5988 each (139 distinct UVs), PassengerDoors_L/_R 0.5007 (173), RearPanel_L/_R 0.6461 (154) - the Blender
  areas to four places, _L and _R alike; SM_RR_Bonnet 0.0000 (1 UV), as before. So export_rangerover.py carries the UV
  into the FBX. `setup_look_l1.bat` (12:28), the gate's lines: "panel pass: 17 car panel name(s) in
  /Game/GrandTour/Vehicles/Bodies/RangeRover/Panels, 3 panel bake folder(s) (a _D and no FBX): FrontDoors,
  PassengerDoors, RearPanel"; "panel FrontDoors (SM_RR_FrontDoors_L, SM_RR_FrontDoors_R): painted - T_GT_FrontDoors_D,
  T_GT_FrontDoors_M, T_GT_FrontDoors_N"; the same for PassengerDoors and RearPanel; "panel pass done: 3 painted
  (FrontDoors, PassengerDoors, RearPanel)"; the props pass 3 of 3 as before.
- **Tests.** `bash Art/suite.sh body proving base` 3 PASS (body 25 s, panels=22 detached=4; proving 36 s; base 16 s). No
  flake met.
- **The pictures** (a quiet machine, the L2 layer on). `proving_shots.bat 4` (12:31-12:38): "UGTBodyComponent: 6 panels
  painted from /Game/GrandTour/Vehicles/Bodies/RangeRover/Paint (UsePaint 1): FrontDoors_L=FrontDoors+N,
  FrontDoors_R=FrontDoors+N, PassengerDoors_L=PassengerDoors+N, PassengerDoors_R=PassengerDoors+N,
  RearPanel_L=RearPanel+N, RearPanel_R=RearPanel+N". Picture 08 puts the car on the pixels of 09-24's final picture
  (control_car 545 344 624 375 in both), so the boxes compare like with like. Picture 08 is copied to
  Saved/Screenshots/Proving/carpaint/carpaint_uv.png and its box lines appended to Saved/Logs/carpaint_compare.log
  (`sample_tones.ps1 -LogName carpaint_compare.log -Folder Proving\carpaint -Names
  carpaint_before,carpaint_painted,carpaint_final,carpaint_uv -Boxes control_car,car_FrontDoors,car_RearPanel`).
  car_FrontDoors: unpainted (final, 09-24) 215.3 207.6 184.5, 5 tones; painted without a UV (09-24) 143.8 74.9 38.2, 4
  tones; now 236.4 161.9 72.5, 13 tones of 18 colours (#ECA444 56.1 %, #EC9C44 24.9 %, then the paler #ECAC6C 3.1 %,
  #ECB47C 2.3 %, ...), against the bake's 213.4 124.7 60.7. car_RearPanel: 215.6 208.0 185.0, 4 tones; 200.2 155.5
  124.2, 2 tones; now 237.3 160.4 66.0, 2 tones of 9 colours (#ECA444 94.4 %), against the bake's 217.2 127.3 62.5. The
  screen means sit above the bake means in every channel (sunlit, the fixed EV100, the L2 layer), G most (x 1.30 on the
  doors, x 1.26 on the rear panel). control_car lies on the painted doors now (236.4 161.3 71.5): no longer a control.
  No "Failed to compile" in either rendered log.
- **Looks** (mine, crops at 3x). carpaint_uv: the front doors, passenger doors and rear panel orange, each with thin
  pale lines along its edges, its seams and its horizontal creases, straight and even along the panel: no smear, no
  stretch, no flat corner colour; the front panel, wheel arches, rear arches and roof stay cream (no bake).
  `base_shots.bat` (12:39-12:45, the same 6 panels painted): base_5_doors_open, the swung left front door and left
  passenger door keep the paint and its edge lines, so the instance swings with them; base_4_lift_screen the same from
  the driver's place. Left against right: the right half's outer face is in no picture; its inner faces, seen through
  the cabin in base_5, are orange with a pale line on the top edge, as the left. The painted dabs (_N) do not resolve at
  these sizes to my eye.
- **Found, not fixed.** (1) Art/Export/Static holds four FBX the exporter no longer writes (SM_RR_Bonnet2,
  SM_RR_RearPanel2, SM_RR_Vert from 2026-09-11 13:48, SM_RR_Trunk 16:37); import_rangerover.py imports every FBX there,
  so the car still carries them, as it did. The import also brought the owner's current blockout in: 17 panel names
  against 15 on 09-24 and 22 body panels against 20 (the exporter writes SM_RR_BaseInterior and SM_RR_Boot today; which
  two were new is not in the logs kept: unchecked); whether Boot and the old Trunk overlap: unchecked. (2)
  export_rangerover.py skips only Reference and Jig: a .blend saved after a Bake holds the bake copies (<Asset>_GTBake
  in "GT Paint Bake"), which the exporter would take as car parts ("hidden in viewport but exported anyway"). Delete
  that collection, or do not save it, before Art/export_rangerover.bat.
- **Unchecked.** The right half's outer face in a picture (the probe says both halves carry the same UV); the dabs at
  driving distance; the owner driving it; the mirrored bake (both halves bake onto the same texels, so where grime or
  occlusion differ side to side the last half written wins); a dent over paint; a detached painted panel in a picture;
  the painted path's frame cost.
- **Files.** Art/Blender/gt_paint/core.py, Art/Blender/gt_paint/__init__.py, Art/Blender/tests/test_gt_paint.py;
  Art/rangerover.blend (UV maps only) and its backup Art/rangerover_backup_20260925_121018.blend; Art/Export/FrontDoors,
  PassengerDoors, RearPanel (T_GT_<Asset>_D/_M/_N); Art/Export/Static, SK_RangeRover.fbx and manifest.json (the
  re-export); the RangeRover Panels and Paint assets in Content (the re-import and the panel pass);
  Saved/Screenshots/Proving/carpaint/carpaint_uv.png, Saved/Logs/carpaint_compare.log; docs/LOOK_PLAN.md,
  docs/BACKLOG.md, docs/devlog/2026-09-25.md.
- **The gate (the owner's).** Drive the car and look at the painted front doors, passenger doors and rear panel; re-bake
  any panel from the GT Paint panel as liked (select it, Apply Style, Bake: it keeps the UV now), then
  Art/setup_look_l1.bat (the mesh already carries the UV, so a re-bake alone needs no export or import). Any other
  panel: Unwrap for Paint and save, then Art/export_rangerover.bat, Art/import_rangerover.bat, Bake (and do not save
  after it, or delete the GT Paint Bake collection first: Found (2)), Art/setup_look_l1.bat.

- **Stale panels removed (2026-09-25, the orchestrator, the owner: "delete the stale panels too").** Art/Export/Static/SM_RR_Bonnet2, RearPanel2, Trunk and Vert .fbx (2026-09-11, no longer in rangerover.blend: the manifest lists Boot and RearBumper instead) and their /Game/GrandTour/Vehicles/Bodies/RangeRover/Panels .uasset deleted; UGTBodyComponent's damage-region map: Trunk -> Boot (Rear), Vert -> RearBumper (Rear). `== build exit 0`, `bash Art/suite.sh body` PASS (panels=18, was 22). Not changed: the exporter still keeps stale FBX and would export a bake copy left in the file (open).

### L1 follow-up 5 (2026-09-25): the rest of the panels

The owner: "bake the rest of the panels too". The follow-up 4 chain on the ten remaining non-wheel parts of
Art/Export/manifest.json, as their manifest names: BaseInterior, Bonnet, Boot, Bumper, FrontPanel, FrontWheelArch,
Pillars, RearArches, RearBumper, Roof. `tasklist` clean before every .bat, build, Unreal and Blender run. No tuned
number moved; the addon, the preset, the water, the mud, the landscape material, the L2 post layer, the physics and
M_GT_Vehicle are as they were. The four stale panels the orchestrator removed (Bonnet2, RearPanel2, Trunk, Vert) were
not recreated: the exporter writes 19 static meshes, the import has 19 panel assets.

- **The owner's file.** Backup `Art/rangerover_backup_20260925_142717.blend` (143403 bytes, byte-identical to the file
  follow-up 4 saved). The same headless script as follow-up 4 (now taking the part list), on Art/rangerover.blend: its
  signature; Unwrap for Paint on the ten (each had no UV map; pillars.001 and frontDoors.001, 3 and 1 faces, which the
  exporter skips, left alone); the signature again, only the ten UV maps differing; the UV-only state written as the
  stage copy; Apply Style + Bake per part into Art/Export/<Part>/; after all ten wrote a new _D, _M and _N, the stage
  copy re-opened, compared with the file as opened (only the ten UV maps differ) and moved over the file (156584 bytes),
  which read back the same. Objects 23 before and 23 after (19 meshes, 0 materials, 6 images, 2 collections both times);
  the saved file holds no bake copy (no *_GTBake object), no "GT Paint Bake" collection and 0 materials. 1465 s. Log:
  Saved/Logs/paint_owner_car.log (follow-up 4's kept as paint_owner_car_fu4.log).
- **Per part** (UV: GT_UV, 1 map each, area in 0-1 UV space; bake: 1024 px, over the texels with alpha, tones as
  blender_test counts them; every _N written):

  | Part | UV area | baked | tones (share) | mean sRGB | _N mean (8-bit) | bake s (dabs) |
  |---|---|---|---|---|---|---|
  | BaseInterior | 0.7538 | 80.4 % | 3: #46423C 84.2, #3F3C36 12.8, #A09C95 3.0 | 71.8 67.9 61.9 | 128.3 127.2 251.0 | 117 (181/40000) |
  | Bonnet | 0.3480 | 41.6 % | 3: #D9772E 77.3, #E2AD92 15.8, #C66C29 6.7 | 217.2 126.8 61.6 | 125.3 128.8 252.3 | 145 (84/40000) |
  | Boot | 0.4840 | 56.3 % | 3: #D9772E 69.5, #E2AD92 18.7, #C66C29 11.6 | 216.5 127.9 64.2 | 126.2 127.1 254.0 | 210 (43/29588) |
  | Bumper | 0.4637 | 56.8 % | 3: #B8B2A6 54.8, #CFC9BF 22.6, #A8A297 22.4 | 185.6 179.6 168.3 | 129.7 128.8 253.2 | 219 (31/21686) |
  | FrontPanel | 0.3149 | 36.1 % | 3: #D9772E 52.7, #C66C29 36.3, #E2AD92 11.1 | 211.1 121.0 55.3 | 129.4 126.7 254.5 | 56 (28/19189) |
  | FrontWheelArch | 0.4973 | 58.1 % | 3: #2C2C30 68.1, #9B9893 16.0, #27272B 15.7 | 61.1 60.7 63.2 | 126.7 125.1 252.2 | 183 (31/21124) |
  | Pillars | 0.5727 | 67.0 % | 2: #B8B2A6 74.5, #CFC9BF 25.1 | 189.8 183.8 172.3 | 126.0 128.1 253.1 | 55 (15/10014) |
  | RearArches | 0.4107 | 46.5 % | 2: #D9772E 88.6, #E2AD92 11.0 | 217.9 124.9 57.0 | 129.4 119.5 251.8 | 80 (17/11469) |
  | RearBumper | 0.5355 | 59.8 % | 3: #B8B2A6 74.7, #A8A297 15.1, #CFC9BF 10.1 | 183.9 177.9 166.3 | 128.1 131.1 252.8 | 261 (62/40000) |
  | Roof | 0.5881 | 62.3 % | 3: #D9772E 93.4, #E2AD92 5.4, #C66C29 1.1 | 217.3 121.8 51.4 | 127.2 127.2 253.5 | 135 (128/40000) |

- **FrontWheelArch baked in the tyre colour.** The file has no materials, so Apply Style picks each part's base colour
  by the preset's name_rules, first match wins: [["wheel", "tyre"], ["interior", "interior"], ["bumper", "trim"],
  ["pillar", "trim"], ["", "body"]]. "frontWheelArch" contains "wheel", so it took the tyre #2C2C30, not the body
  #D9772E; rearArches has no "wheel" and took the body. Not changed here (the preset is the owner's): a name rule
  ["arch", "body"] ahead of "wheel", or renaming the object, then a re-bake of FrontWheelArch and Art/setup_look_l1.bat,
  would make it body orange. The owner names it. Bumper, RearBumper and Pillars took the trim grey and BaseInterior the
  interior colour by the same rules, as the manifest's M_Trim and M_Interior slots have them.
- **Build, export, import, apply.** The runner logs two more boxes (next item): `bash Art/build.sh` == build exit 0 in
  22s. `export_rangerover.bat` (14:52): 19 static meshes, SK_RangeRover 17 parts 4590 tris; warnings the owner's meshes
  give (frontDoors.001 and pillars.001 skipped; doubled verts merged on bumper 1, frontDoors 18, passengerDoors 10, Roof
  5; internal-face edges on seven parts; the vehicle origin 22.6 cm behind the axle midpoint). `import_rangerover.bat`
  (14:52): "IMPORT_DONE: 20 assets". `setup_look_l1.bat` (14:52): "panel pass: 13 car panel name(s) in
  /Game/GrandTour/Vehicles/Bodies/RangeRover/Panels, 13 panel bake folder(s) (a _D and no FBX): BaseInterior, Bonnet,
  Boot, Bumper, FrontDoors, FrontPanel, FrontWheelArch, PassengerDoors, Pillars, RearArches, RearBumper, RearPanel,
  Roof", a "painted - T_GT_<Part>_D, T_GT_<Part>_M, T_GT_<Part>_N" line for each, and "panel pass done: 13 painted
  (BaseInterior, Bonnet, Boot, Bumper, FrontDoors, FrontPanel, FrontWheelArch, PassengerDoors, Pillars, RearArches,
  RearBumper, RearPanel, Roof)"; the props pass 3 of 3.
- **Tests.** `bash Art/suite.sh body proving base` 3 PASS (body 21 s, panels=18 detached=3; proving 34 s; base 13 s). No
  flake met.
- **The boxes** (`Source/GrandTour/Core/GTProvingShotsRunner.cpp/.h`: step 4's car-panel list is FrontDoors, RearPanel,
  Bonnet, Roof; Bonnet and Roof are one mesh each across the car, boxed by the same rule, 25-75 % along and 30-60 % up
  the bounds on the camera face; `Art/tools/sample_tones.ps1`'s default box list gains car_Bonnet and car_Roof). The
  runner: "car panel Bonnet: Panel_Bonnet, mesh 135 x 182 x 24 cm, -Y face, ..., UsePaint 1", box 434 330 488 335 (330
  px); "car panel Roof: Panel_Roof, mesh 250 x 144 x 13 cm, -Y face, ..., UsePaint 1", box 585 280 682 283 (392 px): the
  car's top is in frame only as the roof's and the bonnet's side edges, a 4-6 px strip each.
- **The pictures** (a quiet machine, the L2 layer on). `proving_shots.bat 4` (14:54): "UGTBodyComponent: 18 panels
  painted ... (UsePaint 1)" (13 assets, five of them _L/_R pairs). Picture 08 copied to
  Saved/Screenshots/Proving/carpaint/carpaint_all.png, its box lines appended to Saved/Logs/carpaint_compare.log. The
  car sits 5 px lower on screen than in 09-24's and 12:31's pictures (the doors' and rear panel's boxes moved from y 345
  and 338 to 350 and 343, x unchanged; control_car is ground-based and did not move), so the bonnet and roof boxes read
  the earlier pictures moved up 5 px (appended as such; unmoved, the roof box read the window and the grass behind it).
  Means (before = carpaint_final, 09-24, unpainted -> after 3 panels, carpaint_uv, 12:31 -> now, carpaint_all), tones in
  brackets, against the bake means:
  - car_FrontDoors 215.3 207.6 184.5 (5) -> 236.4 161.9 72.5 (13) -> 236.5 161.8 71.9 (10); bake 213.4 124.7 60.7.
  - car_RearPanel 215.6 208.0 185.0 (4) -> 237.3 160.4 66.0 (2) -> 237.6 160.6 66.1 (1, #ECA444 99.3 %); bake 217.2
    127.3 62.5.
  - car_Bonnet 219.7 213.7 192.4 (6) -> the same (6) -> 236.6 168.1 77.5 (20, #F4A444 32.1 %, #ECA444 21.8 %); bake
    217.2 126.8 61.6.
  - car_Roof 215.9 208.2 185.3 (5) -> the same (5) -> 235.4 170.3 94.3 (20, #ECAC64 27.3 %, #F4A444 16.3 %); bake 217.3
    121.8 51.4.
  - control_car 215.0 207.2 184.1 -> 236.4 161.3 71.5 -> 236.5 161.6 71.5 (it lies on the painted doors: no longer a
    control).
  The doors and the rear panel read what they read at 12:31 (within 0.6 a channel), so the new panels did not move them.
  The bonnet and the roof, sampled on 4-6 px edge strips, sit 6-22 above the doors in G and B: their edge bands are the
  bakes' pale #E2AD92 wear tone mixing in (a strip that thin is mostly edge), my reading, not measured apart.
- **Looks** (mine; carpaint_all at 3x, and `base_shots.bat` 14:55-14:56, base_5_doors_open at 3x, the same 18 panels
  painted). The side: the front panel, the front wing, both doors, the rear panel, the rear arch and the roof all one
  orange, the doors' orange, with the pale lines along the edges, seams and creases as on the doors; no step of colour
  between two orange panels. The front bumper, the rear bumper and the pillars pale grey-white (trim); the front wheel
  arch's lip dark grey round the front wheel (the tyre colour, above); the interior dark. base_5: the bonnet top orange,
  the doors' tone, with pale lines on its creases and along its edge to the wing; the roof orange; the swung doors keep
  the paint. Seams between panels: a pale line on each panel's edge, so a seam reads as a thin pale double line; no dark
  gap, no mismatch in orange across a seam that I can see. The dabs (_N) do not resolve at these sizes to my eye.
- **Unchecked.** The right side's outer faces, the rear and the boot in a picture; the dabs at driving distance; the
  owner driving it; the mirrored bakes' side-to-side differences (both halves on the same texels); the painted path's
  frame cost with 18 painted panels; FrontWheelArch in the body colour (the owner's call).
- **Line endings.** Every repo text file this follow-up touched was written by a byte-level patch and counted by bytes
  afterwards (lines ending in CR of all lines): CRLF throughout.
- **Files.** Art/rangerover.blend (UV maps of the ten parts) and its backup Art/rangerover_backup_20260925_142717.blend;
  Art/Export/<Part>/T_GT_<Part>_D/_M/_N for the ten; Art/Export/Static, SK_RangeRover.fbx and manifest.json (the
  re-export); the RangeRover Panels and Paint assets in Content; Source/GrandTour/Core/GTProvingShotsRunner.cpp/.h;
  Art/tools/sample_tones.ps1; Saved/Screenshots/Proving/carpaint/carpaint_all.png, Saved/Logs/carpaint_compare.log;
  docs/BACKLOG.md, docs/devlog/2026-09-25.md.
- **The gate (the owner's).** Drive the car and look at the whole painted body; name FrontWheelArch's colour (tyre as
  now, or body by a name rule and a re-bake); re-bake any part from the GT Paint panel as liked (it keeps its UV), then
  Art/setup_look_l1.bat.

## 56. Look stage L2: the post-process lighting layer (2026-09-24)

Stage L2 of `docs/LOOK_PLAN.md`, from the owner's brief (`docs/prompts/LOOK_L2_post_layer.md`): one post-process layer
over the frame - the band pass, a stroke-noise warp, a grade, a fixed exposure, hard sun shadows, an anisotropic
Kuwahara filter behind a cvar - on every level, driven by the weather. Every build and Unreal run below was after a clean
`tasklist` (no FarCry6, editor or GrandTour process at any run). No tuned number moved: traction, hull, drivetrain,
water, mud, weather states, camera, terrain specs, the landscape material, the GT Paint preset and M_GT_Painted's
NormalStrength 0.5 are as they were; the water solver, the mud, the landscape material, physics and Art/Blender were not
touched. The weather code gained one getter (`UGTWeatherSubsystem::GetBlendAlpha`). Nothing was sourced. Every L2 number
below is PROPOSED and UNMEASURED against a look; the owner names them.

- **The references, looked at** (ref_01..05, a look): big walls in one flat colour, hard branch shadows in the wall's
  own hue a step darker, the road's shadows a cool blue-grey, a flat cobalt sky paling to the horizon, figures and
  distant houses as two-tone blocks. The plan's section 1 reading stands.
- **The route: C++, one subsystem, no level asset changed.** `UGTLookSubsystem` (`Source/GrandTour/Look/`, a
  UTickableWorldSubsystem for Game and PIE worlds) spawns at BeginPlay one transient, unbound `APostProcessVolume`
  (priority 100) carrying a dynamic instance of `MI_GT_PostLook` and, while `gt.Look.Kuwahara` is 1, one of
  `MI_GT_PostKuwahara`. Chosen over a volume spawned beside each level's sun because seven setup scripts spawn suns
  (setup_m0, m1_track, m2_onfoot, m3_leg, m4_base, m5_legs, m6_proving; The Hide is m5_legs' L_Leg03) and re-running them
  rebuilds their levels; the subsystem misses no level, re-saves none, lets a cvar flip the layer in place and reads the
  weather without a collection. The volume's settings: bloom 0, lens flare 0, film grain 0, vignette 0, local exposure
  contrast scales 1 (off: the project's 0.8 would re-shade the flat bands), auto exposure histogram with min = max
  brightness = the weather set's EV100 (fixed). Every `ADirectionalLight`'s LightSourceAngle goes to **0.05 deg** (the
  engine default 0.5357; hard virtual shadow maps) while the layer is on and back to its own value when it is off.
- **The materials** (`Art/Unreal/setup_look_l2.py` + `Art/setup_look_l2.bat`, /Game/GrandTour/Materials, instances in
  /Game/GrandTour/Materials/Look; NullRHI compiles no HLSL, so the shaders compile on the next rendered run and every
  check below is a rendered picture). `M_GT_PostLook`, Post Process domain, Scene Color Before DOF, priority 0, one
  Custom node fed by SceneTexture PostProcessInput0 / BaseColor / SceneDepth / CustomStencil and the EyeAdaptation node.
  Per pixel: the lookup warped by two value noises stretched into strokes (**WarpPx 1.5** at 1080p, strokes
  **StrokeLenPx 24 x StrokeWidthPx 5** along a direction from a 180 px noise; screen-anchored); the light amount
  **X = luma(SceneColor) / PreExposure / max(luma(BaseColor), BaseGuard 0.02) / SunRef**, SunRef = the sun's current
  lux / pi, pushed every frame, so X is 1 on a surface square to the sun and does not follow the exposure (measured
  below); **Bands** 2 or 3 cut at **T1** (and **T2**) with a smoothstep **Soft** wide; recomposed as BaseColor x
  ShadowTint / MidTint (lerp(Shadow, Lit, **MidMix 0.6**)) / LitTint, times (X / the band's typical X) ^ **InBand 0.25**
  clamped 0.7-1.3 (a quarter of the light variation kept inside a band, so painted-normal dabs can read), times
  **LitX 0.75** x SunRef (the radiance of a surface at X = 0.75 under this sun: the exposure then shows the bands and the
  sky alike, so EV100 is one brightness knob); then the lifted blacks, Lift + (1 - Lift) x colour. The sky
  (SceneDepth > **SkyDepthCm 5e6**) passes through with the warp and the lift; stencilled pixels pass through untouched.
  `gt.Look.Debug` views: 1 BaseColor, 2 X in log2 colour classes, 3 the exclusions (stencil 1 blue, 2 magenta, sky cyan),
  4 the plain picture with the exposure left automatic, 5 X in linear 0.1 classes; 2-5 draw the exposure bars (log2 of
  PreExposure and of the EyeAdaptation value, (v + 16) / 32 of the width, top rows) and three calibration patches.
- **The Substrate probe (first thing, as asked): BaseColor exists.** With `r.Substrate.ProjectGBufferFormat=0` the
  engine's SceneTextureLookup reads BaseColor through `SubstratePublic_GetSubstrateGBufferFromFirstBSDF`
  (MaterialTemplate.ush); `proving_shots.bat 4 -GTLookDebug=1`: one flat colour per surface, the sky black (a look;
  cream car 57 51 35, orange copy 63 20 2 under the then-wrong scale below). No fallback was needed; Substrate stays on.
- **Two engine facts, measured on the way.** (1) A post material before the tonemapper has its output multiplied by
  View.PreExposure (PostProcessMaterialShaders.usf, unless the material disables the pre-exposure scale) and is then
  shown x Exposure / PreExposure: the first pictures came out a stop dark and every pass-through darkened by the
  exposure (the sky 75 114 151 with the layer's volume alone, 64 96 131 with the band pass, 47 74 104 with Kuwahara as
  well). Measured with the calibration patches (0.5 written x PreExposure / Exposure, / Exposure and raw: at EV100 3 and
  under the automatic exposure only "/ Exposure" read the same, 190 and 190), so colours made from BaseColor are written
  / Exposure and the scene passes through / PreExposure; after that the sky with the band pass reads 82 118 155 against
  75 114 151 without it (the lift) and Kuwahara keeps a flat panel at 213 124 51. (2) The automatic exposure cannot run
  under the band pass: the histogram meters the pass's own output, which is written / Exposure, and it ran away to
  log2 -6.8 in one picture. So the layer fixes the exposure. The automatic exposure picked log2(PreExposure) +0.42 on
  L_Proving (debug 4 bar, 0.513 of the width).
- **X measured, then the cuts** (`-GTLookDebug=5` over a full hide_shots and proving_shots 4, linear bins of 0.1, the
  share of each frame): hide_1 >= 0.7 49.2 %, 0.6-0.7 7.9, 0.5-0.6 2.6, < 0.1 2.9; hide_6 66.9 / 5.2 / 1.9 / 0.9;
  hide_10 45.9 / 11.5 / 2.4 / 0.0; hide_13 62.1 / 14.1 / 2.9 / 0.5; proving_09 56.6 / 1.7 / 0.3 / 2.0. Lit ground is
  X 0.5 and up, cast shadows under 0.1, little between; the log2 view put the cars' shadows at 1/16-1/4. X is the same
  at EV100 3 and at an exposure 7 stops off (99.0 % of proving_09's pixels in the same log2 class). Hence Clear's
  **T1 0.2** (shadow/mid) and **T2 0.45** (mid/lit): the mid band is grazing light, not the flat ground.
- **Kuwahara** (`M_GT_PostKuwahara`, Before DOF, priority 10 - lower priorities run first - so it filters the band
  pass's output): the structure tensor from central differences over a 5 x 5 luma window, Gaussian weighted; an
  ellipse **RadiusPx 4** at 1080p (2.67 px at the pictures' 720p) stretched by (Alpha + A) / Alpha, **Alpha 1**, capped
  at 12 px a side; 8 sectors with polynomial weights, **Zeta 0.33**, sharpness **Q 8**; filtered in displayed units so Q
  means the same at any exposure; stencilled pixels pass through. **Off by default** (`gt.Look.Kuwahara 0`).
- **Exclusions: this stage turned custom depth-stencil on** (`r.CustomDepth=3` in Config/DefaultEngine.ini, with a
  comment). Stencil 1: every primitive of each AGTWaterSheet and each AGTMudPatch's WaterMesh; stencil 2: every
  primitive under UGTDashboardComponent - logged `GTLOOK stencil`: 4 water and 26 dashboard primitives on The Hide, 7
  and 26 on L_Proving. FOUND: translucent M_GT_Water and M_GT_MudWater write no stencil (a translucent material writes
  custom depth only with its Allow Custom Depth Writes flag, which is theirs, L4's, and was left off); debug view 3 of
  hide_22 has no stencil pixel. The water is kept out of the band pass anyway: it is After-DOF translucency (the engine
  default; PostProcessing.cpp runs the Before-DOF chain first and composites that translucency after it), so the ford's
  sheet is laid over a band-passed bed. The dashboard's stencil is not in any gate picture: unchecked.
- **Weather sets** (C++ `UGTLookSubsystem::DefaultSet`; blended the weather's way: the target state through its blend
  alpha and the same smoothstep, then the storm pressure towards Storm; logged `GTLOOK weather target`):

  | set | bands | T1 | T2 | soft | InBand | lit tint | shadow tint | lift | warp px | EV100 |
  |---|---|---|---|---|---|---|---|---|---|---|
  | Clear | 3 | 0.20 | 0.45 | 0.08 | 0.25 | 1.00 0.96 0.88 | 0.55 0.62 0.80 | .012 .014 .020 | 1.5 | 0.25 |
  | Overcast | 2 | 0.30 | - | 0.35 | 0.25 | 0.92 0.93 0.95 | 0.72 0.76 0.84 | .020 .021 .024 | 1.5 | -0.45 |
  | Rain | 2 | 0.30 | - | 0.35 | 0.25 | 0.84 0.86 0.90 | 0.66 0.70 0.79 | .018 .020 .024 | 1.5 | -1.05 |
  | Storm | 2 | 0.30 | - | 0.40 | 0.25 | 0.74 0.77 0.82 | 0.58 0.62 0.72 | .016 .018 .022 | 1.5 | -2.00 |
  | Snow | 3 | 0.20 | 0.45 | 0.15 | 0.25 | 1.00 1.00 1.02 | 0.62 0.70 0.92 | .014 .016 .024 | 1.5 | -0.25 |

  Clear's EV100 0.25 keeps the painted car copy's sunlit orange under clipping (below); the others move with log2 of the
  weather's SunScale (0.6, 0.4, 0.2, 0.5) so the lit band keeps its brightness. Only Clear has been rendered; Overcast,
  Rain, Storm and Snow are unchecked.
- **Console and command line.** `gt.Look.Post` 0 off (no volume, the suns' own angle), **1 on (default)**, 2 the
  volume without the band pass (the exposure, no bloom/flare/grain/vignette/local exposure, the hard sun);
  `gt.Look.Kuwahara` 0/1; `gt.Look.Debug` 0-5. `-GTLook=N`, `-GTLookKuwahara=N`, `-GTLookDebug=N` set them at start, and
  hide_shots.bat, bog_shots.bat and ford_shots.bat pass their arguments to the game, proving_shots.bat those after the
  step (`proving_shots.bat 4 -GTLook=0`). **The layer is on in every picture .bat now: a comparison with any picture
  taken before this stage (sample_border's baselines, sample_rut_low, sample_ford, sample_tones) wants `-GTLook=0`.**
- **Frame cost** (`ford_shots.bat` at 1280 x 720, the mean of the steps' GTWATERSTATS frame ms over steps 22-30, the
  three set-ups interleaved and repeated once, a clean tasklist before each, every run 96-110 s = real time; step 22
  clamped once in every run, the level-load frame): off (`-GTLook=0`) **17.15 / 18.63 ms**; on **18.05 / 18.76**; on with
  Kuwahara **21.18 / 21.47**. Pairwise the band pass costs +0.90 / +0.13 ms, inside the 1.5 ms the two "off" runs differ
  by; Kuwahara +3.13 / +2.71 ms over "on". At 1080p the Kuwahara's taps and pixels both grow (radius x 1.5, pixels x
  2.25): unmeasured. Per step (off / on / Kuwahara, first run): 22 15.30/17.37/20.52, 23 15.22/16.14/19.07,
  24 17.42/17.82/21.19, 25 18.08/18.50/21.56, 26 17.90/18.67/22.21, 27 16.56/16.98/20.08, 28 17.41/18.59/21.44,
  29 18.25/19.36/22.29, 30 18.20/18.99/22.28.
- **Pictures and gates.** Before: a full `hide_shots.bat` and `proving_shots.bat 4` taken before anything was built
  (Saved/Screenshots/L2_before, logs Saved/Logs/L2/*_before.log); after: the same two with the layer at its defaults
  (Saved/Screenshots/L2_after; Kuwahara's in L2_after/Kuwahara, the exposure alone in L2_after/ExposureOnly). New
  `Art/tools/sample_bands.ps1` on sample_tones.ps1's pattern: per picture a sky, a car-panel and a ground box (the
  Hide's as fixed rectangles from a look at the before pictures; proving_09's car box the runner's logged TestCar line;
  plus the ford's water in hide_22 and the rally road in hide_10), the distinct tones (5-bit colours over 0.5 % of the
  box) with all 5-bit colours beside them, the top tones and a 16-bin luma histogram, before and after. Tones (colours):

  | picture | sky | car panel | ground | extra |
  |---|---|---|---|---|
  | hide_1_valley | 11 (15) -> 9 (13) | 8 (54) -> 7 (9) | road 6 (8) -> 2 (4) | |
  | hide_6_bog | 16 (26) -> 14 (21) | 6 (61) -> 7 (24) | 33 (138) -> 21 (97) | |
  | hide_10_rally | 12 (20) -> 11 (16) | no car | grass 38 (153) -> 28 (122) | road 37 (301) -> 33 (237) |
  | hide_13_rut_low | 18 (31) -> 13 (23) | no car | 30 (162) -> 24 (123) | |
  | hide_22_ford_bank | 16 (24) -> 17 (25) | no car | bank 20 (96) -> 18 (75) | water 19 (48) -> 23 (43) |
  | proving_09 | 15 (22) -> 13 (20) | TestCar 13 (138) -> 11 (125) | 47 (388) -> 35 (254) | |

  With Kuwahara on: proving_09 TestCar 11 (81), ground 24 (123); hide_22 bank 10 (50), water 20 (52). The histograms
  narrow and shift down: hide_1's road from bins 10-11 (4665, 21696) to bin 9 alone (26358), its sky from bins 8-9 to
  5-7; proving_09's ground mean 181 131 86 -> 120 78 49 and sky 135 176 204 -> 90 130 166 (EV100 0.25 is 0.67 stop
  under the automatic exposure's +0.42 there); hide_22's bank 175 154 119 -> 174 153 118.
  **The car copy's top tones** (proving_09, TestCar): before #FCC45C 34.3 % #FCCC64 27.4 % (red 252, clipped); the
  exposure alone (`-GTLook=2`, EV100 0.25) #F4A444 24.1 % #F4A43C 17.2 % #EC9C3C 14.1 % #F49C3C 12.8 % #F4AC44 11.2 %
  (red 244, 13 tones: the dabs read as tones once nothing clips); the layer on #ECA444 76.8 % then #34343C 3.7 % (a
  tyre) #EC9C44 3.5 % #F4A444 2.9 % (red 236, one main tone, the dabs down to a few per cent); Kuwahara on #ECA444
  79.0 %. TestBox 255.0 197.3 97.1 -> 237.0 154.2 61.4 (exposure alone) -> 237.1 160.0 65.2 (layer on); the parked
  car's control box 235.6 227.9 209.1 -> 215.5 207.6 184.5. The shadow under the cars (5 x 5 px under the sills) 29 24 22
  beside lit dirt at 185 126 80 before, 76 53 40 beside 117 71 43 after: lifted, and cooler than the lit dirt (R 0.65,
  G 0.75, B 0.93 of it) - the shadow tint's hue shift.
- **The looks** (the after pictures, looked at with the Read tool; looks, not measurements). proving_09: flat colours;
  the car copy one flat orange with faint lighter and darker patches where the dabs were; the dirt keeps its albedo
  texture; ragged silhouettes from the warp; a deep blue sky. **Whether the
  dabs read: faintly** - with the sun square on the side every dab sits in the lit band and only InBand 0.25 carries
  them (one tone at 77 %); they read plainly as tones with the exposure alone. hide_1: the hills one flat green with no
  shading, the road one flat grey, the car's rear flat cream, the floating box's cast shadow a hard blue-violet shape.
  hide_10: flat green grass with its painted leaf albedo, the rally road red-brown, a hard post shadow. hide_22: the
  ford's water as before (composited after the pass), the banks flat. **hide_6 and hide_13: a wide darker stripe across
  the bog that the before pictures do not have**: sampled in hide_13, the stripe reads 151 130 96 at X >= 0.7 beside
  180 158 120 at X 0.6-0.7 outside it, where the before picture reads 198 179 145 and 196 175 137 - so the stripe is the
  mud patch (M_GT_Mud) showing a darker BaseColor than the landscape's Mud row it was matched to by rendered colour in
  mud stage E (section 32); the band pass shows base colours. L4's (the mud's look), not tuned here.
- **Tests.** `bash Art/suite.sh terrain` PASS (267 s) after the first working build (the later builds changed the
  layer's numbers and HLSL only, which NullRHI does not run); the full suite once at the end: **23 PASS, 1 FAIL** - `loot` (16 s): "the node was not offered", its interaction target none at t = 1.0; not a listed
  flake; `bash Art/suite.sh loot` alone then PASSED (15 s, nodeOffered=1) on the same build; cause unmeasured, not tuned.
  terrain PASSED in the suite as well (269 s; the step 11 ruts flake did not fire), water 297 s, body and winch first time.
  Builds: every `bash Art/build.sh` printed `== build exit 0`.
- **Unchecked.** The owner's look and every number above; Overcast, Rain, Storm and Snow sets (none rendered); the
  warp in motion (screen-anchored strokes: whether they swim on a moving camera); the dashboard's stencil in a picture;
  Kuwahara's cost at 1080p; the stripe's cause past the base-colour reading; the sun angle 0.05's shadow aliasing up
  close. **THE GATE:** the owner drives The Hide and L_Proving with `gt.Look.Post` on and off (and 2), looks at the
  painted props and the driven car, and names the band count, the two tints, the terminator, the warp, the exposure
  and whether Kuwahara stays.
- **Follow-up 2026-09-24: the black strip on hide_10's ridgelines (the orchestrator's gate finding).** The orchestrator's
  look: with the layer on, a black jagged strip along the far ridgeline (about x 470-570, y 305-320) and dark scribbles
  along the near hill's crest (x 850-1000, y 255-270), in neither before picture. Measured (a GetPixel box, mean and the
  share of pixels with luma under 20): the ridge box 139.5 176.9 174.7 / 0.0 % before, 63.2 96.6 70.0 / **23.6 %** with the
  layer; the crest box 157.2 196.1 171.1 / 0.0 % before, 99.0 145.2 104.3 / 0.0 % with the layer (the scribbles are
  thin). Parts switched off one at a time, one full hide_shots run each on a clean tasklist: the warp off (new cvar
  `gt.Look.WarpScale`, `-GTLookWarp=0`) 63.1 96.3 70.1 / 23.5 % - not the warp; the volume without the band pass
  (`-GTLook=2`: the fixed EV100 0.25 and the 0.05 deg sun, no material) 74.4 110.9 110.7 / 0.0 % - not the exposure and
  not the sun angle. A new probe view `gt.Look.Debug 6` (flags at the warped lookup: red BaseColor luma under BaseGuard,
  green the sky by depth, blue a lit scene) reads, in the ridge box, **28.6 % base-less, not sky, lit**, 27.7 % sky and
  43.7 % ordinary ground; in the crest box 3.8 % base-less, 36.7 % sky; the whole frame 0.1 % base-less. **The cause**:
  something nearer than SkyDepthCm with no BaseColor - it shows blue in the before picture, a band at the horizon behind
  the far hill and a thin line behind the near crest; what it is (the atmosphere's ground, a far mesh with an unlit or
  black-based material, the landscape's far LOD) was not identified - so the recomposition wrote BaseColor x tint = black.
  The candidates asked about were tested, not assumed: the warp across the sky/ground edge (off: the same 23.5 %), a
  base-less silhouette (yes, 28.6 %), the sun's 0.05 deg angle (mode 2: 0.0 %). **The fix, in M_GT_PostLook only**: a
  pixel whose BaseColor luma is under BaseGuard (0.02, unchanged) passes through unbanded like the sky (the warp and the
  lift, no bands) - chosen over a depth clamp on the warp because the warp is not the cause, and over a raised floor
  because a floor still multiplies an absent colour; a surface with no base colour carries nothing the bands can use.
  Re-shot (`Art/setup_look_l2.bat`, then a full hide_shots at the defaults; the run took 588 s, the slow mode, clean
  tasklist): the ridge box **78.7 119.5 100.9 / 0.0 %**, the crest box 100.5 147.0 107.3 / 0.0 %. My look at the re-shot
  hide_10 (the Read tool, a look): the far strip is the blue band of the before picture again with ragged warp edges,
  the crest carries the before picture's thin blue line instead of dark scribbles, no black. sample_bands on the re-shot
  set (Saved/Screenshots/L2_after_fix): hide_10 sky 11 (16), grass 28 (114), road 33 (234); hide_13 ground 25 (124);
  hide_22 bank 16 (70), water 19 (41); hide_1's and hide_6's car boxes moved (hide_1 7 (9) -> 9 (91)) because the slow run
  left the car elsewhere in the frame (a look: smaller and lower), not because of the fix. proving_shots 4 not re-shot.
- **The post's cast shadow on the grass (measured, not tuned).** The box right of the post (730-780 x 385-400) against
  a lit box beside it (800-850 x 385-400): before 114.9 164.2 103.9 against 146.0 198.0 121.3; with the layer 70.4 123.7
  60.9 against 75.7 132.4 59.2; after the fix 70.4 123.7 60.8 against 75.7 132.3 59.3. The shadow's own pixels (the 217
  of 816 darker than 0.7 x the lit box in the before picture): before 40.2 81.1 64.3 against the lit box's 146.0 198.0
  121.3, with the layer 59.9 105.6 66.4 against 75.7 132.4 59.2, and with the volume alone (no band pass) 7.7 26.1 20.9
  against 77.1 130.3 59.8. The debug-5 view puts 35 % of those pixels at X < 0.1 and 46 % at 0.1-0.2, so the terminator
  does put them in the shadow band: **the shadow survives as a distinct tone, cooler (B 66 against 59) and only a
  little darker (G 106 against 132)**, because the shadow tint 0.55 0.62 0.80 on a green whose base is mostly G takes a
  quarter off; the before picture's shadow was 2.4 times darker than the lit grass in G. The shadow tint and the lift are
  the owner's to name.
- **Tests after the fix.** `bash Art/build.sh` `== build exit 0`; `bash Art/suite.sh terrain` FAIL twice, each on step
  11's ruts gate alone (the first run "faster 0" and "slower than down the ruts 0", the rerun "slower than down the ruts
  0"), the known flake, not tuned; the terrain test is NullRHI and the change is the material's HLSL and a cvar.
  Unchecked: what the base-less surface at the horizon is; proving_09 with the fix.

## 57. Look stage L6: the runtime painterly surface material (2026-09-25)

Stage L6 of `docs/LOOK_PLAN.md`, from the owner's brief (`docs/prompts/LOOK_L6_runtime_paint.md`): one master material
that gives an UNBAKED mesh the painted surface at runtime from the mesh alone, and the instances the terrain dressing
wears. The plan went into LOOK_PLAN L6 before any build. **God of War (GoW.exe, started 16:08) was running when the stage
began**: the first baseline hide run under it took 1030 s at 2-5 fps and is VOID; the tasklist grep of the brief
(UnrealEditor|GrandTour|FarCry) does not see it. It closed at about 16:55 and every number below was taken after, with
GoW, FarCry, the editor and GrandTour absent at every build and run. No tuned number moved: traction, hull, drivetrain,
water, mud, weather, camera, terrain specs, the landscape material, the GT Paint preset, M_GT_Painted, M_GT_Vehicle and
L2's numbers are as they were; nothing in Art/Blender changed (the preset and the addon were used, not edited). Nothing
was sourced. Every L6 number is PROPOSED and UNMEASURED against a look unless it is marked as the bake's; the owner
names them.

- **The references, looked at** (ref_01..05, a look): big walls in one flat colour with a few horizontal brush drags and
  pale chipped patches; ref_04's rubble in pale planes, cream lit and lavender-blue shadow, two or three values each, hard
  edges between the planes. The plan's section 1 reading stands.
- **Found: the dressing never wore its material in the game.** `M_GT_Environment` has no InstancedStaticMeshes usage
  flag, so on the dressing's HISM components the engine drew its default material (the grey checker) wherever
  `MI_Env_Greybox` / `MI_Env_Marker` were assigned - "Material ... missing usage flag InstancedStaticMeshes! Default
  Material will be used in game" in every hide_shots log, the pre-L6 baseline included. So the "before" of this stage is
  the checker, and gt.Look.Surface 0 is the plain graph those instances meant (0.55 grey, 0.9 0.35 0.1 orange), not what
  the game drew. `M_GT_Environment` was NOT given the flag (not this stage's material; the owner decides).
- **The material** (`Art/Unreal/setup_look_l6.py` + `Art/setup_look_l6.bat`): `M_GT_Painterly` (/Game/GrandTour/Materials)
  is a fresh copy of `M_GT_Environment` every run (as setup_m6_hide copies it for the landscape), so MF_Weather still wets
  it and its plain graph is the environment master's own (BaseColor / Roughness through MF_Weather with Porosity and
  CanPool, the track-paint normal and WPO behind TrackStrength). One Custom node sits between the parameters and
  MF_Weather and in front of the Normal pin; its colour, roughness and world normal meet the plain values in three lerps on
  a `Surface` scalar, and the node returns at once on 0. The InstancedStaticMeshes usage is set on it. Per pixel:
  (a) **tones**: the instance's BaseColor (its plain instance's colour), per-instance jittered, cut into three tones of value by a
  3D world value noise at **35 cm** (the bake's grain_scale) at its 25th/75th percentiles (**0.366**, simulated): dark =
  tint x (1 - **0.183**) (the bake's level spacing, (1 + wear_lighten - (1 - grime)) / (tones - 1)), base, light = tint
  **0.175** of the way to the wear colour (the bake's light level, wear_tint x 1/2); never the lighting.
  (b) **grain**: value noise on the dominant world plane (a hard pick by the vertex normal: a flat face keeps one plane),
  **60 cm** along x 12 cm across (the bake's grain_stretch 5), its 15 % tails (**0.256**) light and dark strokes: albedo x
  (1 +- **0.08**), roughness -+ **0.1**.
  (c) **edge wear** from the mesh's own local bounds: per instance-space axis the face does not face, the distance to that
  bounds plane x the instance's scale on it, in cm (`MeshHalfCm` 50 50 50 from the engine meshes' bounds; `EdgeRound` 1 on
  the post: the cylinder's rims, the cap by its radius); within max(**2 cm** (the bake's wear_width), **1.5 px** at the
  pixel's depth) of an edge, broken by the bake's wear_breakup **0.5**, the bake's wear tone (0.35 of the way to #F2EDE4).
  Chosen over the screen-space change of the world normal: the cube's faces carry split normals, constant per triangle,
  and pixel-quad derivatives never cross a triangle (reasoned, not measured). **Measured on the way**: "Local Space" on a
  HISM is the component's, not the instance's - the first dressing run put every face in the wear tone (the stone's
  BaseColor view #CCCCCC on 98.2 % of its box, the post's 220 196 172); the transforms are now "Instance & Particle
  Space" and the footprint takes the View Property node's Tan(0.5 x Field Of View) (a first build had a 90 deg constant).
  (d) **the dab normal**: `DabTile` 0 (shipped) the procedural dab - an oriented ellipse per cell of a **55 x 27.5 cm**
  brick grid (the bake's dab 55 cm and aspect 2), jittered, 3 x 3 cells searched, the ellipse **1.3** x its cell, each
  dab a flat facet tilted up to **8 deg** (the bake's normal_jitter) at +- **20 deg** of direction (rot_jitter), the top
  one by a random order wins; `DabTile` 1 the baked tile below at **200 cm**. Both at **NormalStrength 0.5**
  (M_GT_Painted's), normalize(lerp(n, dab, 0.5 x fade)), the fade linear to nothing at **40 m**.
  (e) roughness floored at **0.75**; metallic and clear coat as the plain graph (none). (f) PerInstanceRandom: value
  **+- 0.04**, hue **+- 3 deg** about the grey axis, before the tones. Every number is a scalar parameter in the
  "Painterly" group (the log's SETUP_LOOK_L6 table lists each with where it came from).
- **The dab tile** (`bash Art/make_dab_tile.sh` -> `Art/tools/make_dab_tile.py`; `Art/Textures/Painted/T_GT_DabTile_N.png`
  with `SOURCE.txt`; /Game/GrandTour/Textures/Painted/T_GT_DabTile_N, TC_Normalmap, sRGB off, no green flip): a flat 2 x 2 m
  plane (tooling) through GT Paint's Apply Style and Bake at the preset as it is, so the owner's OW Painterly Normal Baker
  laid the dabs (285 s). **Seam**: the mean |difference| across the wrapped edge against the mean between neighbouring
  texels inside, **0.0264 / 0.0061 = 4.31 x** (vertical edge) and **0.0329 / 0.0095 = 3.47 x** (horizontal): it does not
  tile, so the procedural dab ships. My look at the tile (a look): mostly small detail-pass dabs a few cm long, with larger
  soft 50 cm patches of a slightly different tilt; no seam line stands out to the eye, but the numbers say it is there.
- **The switch**: `gt.Look.Surface` 1/0 and `-GTLookSurface=N` in `UGTLookSubsystem`. Not a parameter collection: the copy
  already holds MPC_Weather and MPC_TrackPaint and a material takes two. At BeginPlay and once a second (with the
  stencil pass) every mesh slot whose base material is M_GT_Painterly gets a dynamic instance and its Surface follows the
  cvar (log "GTLOOK surface: 3 mesh slot(s) ... given a dynamic instance", then the probe cube: 4). **0 is the plain graph
  pixel for pixel, measured**: the stone's twin (a non-instanced engine cube with the stone's rotation and scale, 1 m to
  its side, where M_GT_Environment does render) in the Surface 0 instance and then in MI_Env_Greybox, same frame: mean
  |difference| **0.30** a channel, **0.00 %** of the pixels over 8.
- **What wears it**: `MI_GT_Painterly_Stone`, `_Rock` (both from MI_Env_Greybox: 0.55 grey, roughness 0.85, porosity 0.2,
  CanPool 1, TrackStrength 0) and `_Post` (from MI_Env_Marker: 0.9 0.35 0.1, EdgeRound 1) in /Game/GrandTour/Materials/
  Painterly. `AGTTerrainDressing`: the ford rocks moved from the Stones component into their own `Rocks` (the same mesh
  and collision; FordRockCount counts them); the C++ default paths point at the three instances, with PlainStone/
  PlainPostMaterialPath (the MI_Env_* paths) as the fallback when a path does not load. The paths live in C++ (DA_Terrain_
  Hide holds none): setup_look_l6.py calls The Hide's builder `RebuildDressing` (the button's path) and saves L_Leg03 -
  88 stones, 30 posts, 12 rocks, each component in its instance. The water bars are landscape ridges (WaterBarArcs, by
  trace) and wear the landscape material, untouched. L_Proving's dressing is not rebuilt (setup_m6_proving will).
- **The pictures** (`Art/dressing_shots.bat`, -GTShotsFrom=40, the bog run's jump; steps 40-42, never reached by a full
  run; 17 pictures, 81 s; L2 on in every one): a 0.39 m track stone 7.1 m off near 1322 m, the post nearest 640 m at
  7.0 m, the ford rock standing highest over its water (only **12 cm** over the level of 2510 cm) at 7.2 m; 25 deg field
  of view, the eye on the sun's side turned 40 deg; per object Surface 0 and 1, both again under gt.Look.Debug 1, and the
  MI_Env_* put back (what the game drew before). `sample_bands.ps1 -Dressing` (tones = 5-bit colours over 0.5 % of the
  box's middle 60 %; grain = tone steps, the luma moved over 3 of 255 from the last counted tone, per 100 px on three rows):
  stone off / on **3 / 8 tones** (48 / 55 colours), histogram peaks 1 / 1, grain **0.0 / 7.2**,
  mean 214.6 212.8 209.7 / 207.6 205.9 202.9, its BaseColor view 1 / 4 tones; post **2 / 10 tones**, peaks 1 / 1, grain
  **0.0 / 8.8**, mean 243.0 201.7 127.3 / 234.7 188.5 110.3; rock **22 / 29 tones** (the box holds water: the rock is
  mostly under it), peaks 2 / 2, grain 11.9 / 16.0. The checker the game drew (the _plain picture): stone 7 tones, grain
  16.5, mean 109.5 108.0 105.4 (|difference| 104.7 a channel against Surface 0); post 11 tones, 105.5 104.7 102.9.
- **The compose check** (per pixel log2(luma look / luma BaseColor view), clusters of 0.05 bins over 1 %, counted over
  5 %; the same object, the same frame): stone **1 / 1** band (x1.09 on 98 % / x1.11 on 98 %), post **1 / 1** (x1.17 /
  x1.14), rock **1 / 1** (x1.06). The painted surface is lit into the same bands as the plain one: no second terminator.
  Every object in these frames sits in the lit band (the eye is on the sun's side), so the count is L2's lit side, 1.
- **My looks** (the Read tool on crops at 3 x; looks, not measurements): Surface 0 - the stone a flat near-white block,
  its faces barely apart; the post a flat light orange. Surface 1 - the stone reads painted, not like a noisy photo: a
  pale ragged band along every edge of the block (the wear sits on the edges: the top's outline and the vertical corner),
  two or three large soft grey patches and a horizontal streak on the faces, no pixel noise; the band reads heavy at
  this zoom (about 8 px at 25 deg). The post: a long darker orange patch down its side, faint blocky strokes near the
  top and a pale rim on the cap. In hide_10_rally (the near post about 10 px wide) the painted post reads two-coloured, an
  orange top and a cream lower part: the light tone (0.175 toward the wear colour) desaturates orange hard under L2. The
  rock is a white slab barely out of the water with a grey side band. The 0.55 grey reads near-white under L2's lit
  band with or without L6 (L2's numbers, not this stage's).
- **Before and after, full runs** (`Art/hide_shots.bat`, quiet machine): hide_10_rally's near post (a fixed box, x 722-731,
  y 322-392, added to sample_bands.ps1): before (the checker) 16 tones, mean 96.0 97.0 97.3; Surface 0 6 / 5 tones, 241.0
  199.6 124.6; Surface 1 23 / 21 tones, 232.8 200.9 152.6; sky, grass and road unchanged to a unit. hide_22_ford_bank: no
  rock stands visibly over the water in it (a look); its boxes are the water's own (water 103.8 before, 104.4 / 104.5 in
  the second pair; the first Surface 1 run 117.7, the ring caught at another moment - a look).
- **Frame cost** (`Art/ford_shots.bat` GTWATERSTATS frame ms, steps 22-30, the 12 rocks in frame, two runs each, all 12/12
  pictures): Surface 0 **16.54 / 16.69 ms** mean over the steps, Surface 1 **16.64 / 16.77 ms** (+0.10 / +0.08, inside the
  0.15 ms between two runs of the same switch); per step off -> on (first pair) 22 15.69 -> 16.09, 23 15.16 -> 15.08, 24
  16.65 -> 16.66, 25 16.91 -> 17.02, 26 16.50 -> 16.97, 27 15.46 -> 15.80, 28 17.06 -> 16.87, 29 17.82 -> 17.57, 30 17.63
  -> 17.68. Surface 0 runs the same shader with the early return, so "off" is not the plain material's cost (the plain was
  never drawn: the checker). **Full hide run**: before (the checker) 234 s; Surface 0 229 / 232 s; Surface 1 229 / 244 s
  (the last game time 213.1 / 226.7 s against 212.8-212.9 for every other run: one slower step, not the frame rate). The
  edge term's own share is not separated.
- **Tests**: builds `== build exit 0` (three times). `bash Art/suite.sh terrain` after the first setup and after the second:
  FAIL both times on step 11's ruts gate alone ("slower than down the ruts 0", the known flake: 5 of the 9 backed-up
  terrain logs of 2026-09-23/24 read the same), dressing **88 stones 30 rally posts 12 ford rocks, solid=1** each time.
  The full suite once at the end: **24 PASS, 0 FAIL** (terrain passed, its ruts gate 1). Line endings: WATER_PLAN.md
  (642 lines) and GTTerrainDressing.h/.cpp (84 / 159) were LF-only before this stage and are CRLF now (a third build, exit
  0, after that); Art/make_dab_tile.sh is LF like every .sh (bash needs it); every other touched file CRLF throughout.
- **Unchecked**: the owner's look and every number above (tone count and step, grain amount and tile, the edge width
  and the 1.5 px floor, the dab choice and its strength, the jitter, the roughness floor, the 40 m fade); a shadow-side
  face in a dressing picture (the compose check saw the lit band only); the dab normals' own effect (not separated from
  the tones in any picture); rain on the painted surface; Lumen's surface cache after a flip; L_Proving and every level
  not re-dressed; the probe cube and any mesh the owner drops in (wrapped, not pictured).
- **Owner's look (2026-09-25, the gate)**: with gt.Look.Surface 0 and 1 on The Hide's dressing, the owner: "can't really
  tell any difference between the two. However, I am happy to move on, it will do for now." So L6 stands as built with
  the switch on and no number named; the difference the samplers measured (stone 3 -> 8 tones, grain 0 -> 7.2 steps per
  100 px, the edge line) does not read to the owner at driving distance under the L2 bands. If more is wanted later the
  dials to raise are the tone step 0.183, the grain 0.08 / 0.1, the wear lighten, NormalStrength 0.5 and the 40 m fade
  (all still proposed). L_Proving is not re-dressed: adding it to setup_look_l6.py's level loop is a five-line change,
  offered and not asked for.

## 58. Look stage L3: sky, foliage and atmosphere (2026-09-26)

Stage L3 of `docs/LOOK_PLAN.md`, from the owner's brief (`docs/prompts/LOOK_L3_sky_foliage_haze.md`), as the plan block
amended by Fable (the dome static at the origin, the frame budget and cut order, the far water, the sun disc). The
backdrop (a painted sky that is not lit), the distance (a haze on what is already lit and banded) and PLACEHOLDER
foliage cards in the terrain dressing. **God of War (GoW.exe) was running when the stage began**: the plan was written,
nothing was built or run until it closed (a 15-minute wait, then PARTIAL, then resumed); every build and Unreal run below
was after a clean `tasklist | grep -i -E "UnrealEditor|GrandTour|FarCry|GoW"`. No tuned number moved: traction, hull,
drivetrain, water, mud, the weather states and their CloudCover/FogDensity/SunScale/SkyScale, camera, terrain specs,
the landscape material, the GT Paint preset, M_GT_Painted, M_GT_Vehicle's painted path, M_GT_Painterly and L2's
bands, tints, terminator, warp, exposure, Kuwahara and BaseGuard are as they were; nothing in Art/Blender changed;
nothing was sourced. Every L3 number is PROPOSED and UNMEASURED against a look unless marked as reused (L2's LitX 0.75,
L6's tone step 0.183, jitter and dab, M_GT_Foliage's wind); the owner names them.

- **The references, looked at** (ref_01..05, a look): ref_03's sky a flat cobalt paling toward the horizon, ref_04's
  clouds white blobs with a blue-grey shadow side; the distant town and hills paler and bluer with distance, low
  contrast (ref_04, ref_05); foliage as flat dark-green blade shapes in two or three values (ref_01, ref_02's clump,
  ref_04's fronds). The plan's section 1 reading stands.
- **The sky** (`Art/Unreal/setup_look_l3.py` + `Art/setup_look_l3.bat`): `M_GT_Sky` + `MI_GT_Sky`, unlit, TRANSLUCENT in
  the Before-DOF pass (standard translucency renders into scene colour before the post chain), two-sided, Apply Fogging
  off, not IsSky. One Custom node on the view direction d: horizon weight (1 - max(d.z, 0))^**1.5** (the first build;
  the owner's set 3.0, 'Dials applied' below) between zenith **0.10 0.22 0.55** (the first build; now 0.04 0.10 0.45) and horizon **0.62 0.72 0.86**; clouds where a 3D value noise at a **0.333** cell plus **0.12** x a
  second at a fifth of it, at d + CloudOffset, passes a cut taken from the noise's own quantiles (2 million samples:
  CloudCover 0 / 0.1 / 0.5 / 0.9 / 1 -> 1.10 / 0.747 / 0.500 / 0.252 / -0.10), light **0.92 0.92 0.90**, underside **0.70
  0.74 0.84** where the point **0.08** below is clear; the whole x LitX 0.75 x SunRef x SkyScale. `UGTLookSubsystem`
  spawns the dome ONCE at the world origin (the engine sphere at a **10 km** radius, never moved), pushes CloudCover,
  SkyScale, SunRef and LitX every tick from `UGTWeatherSubsystem::GetCurrent()` and the sun, and advances CloudOffset
  **0.002** a second along the state's WindYaw. Kept out of every lighting path: no shadow, not in the real-time sky
  capture, reflection captures, ray tracing, Lumen or distance fields, hidden in scene captures (the rain's top-down
  occlusion capture), sort priority **-1000**, no collision. No painted sun disc: the atmosphere's own is covered.
- **Found and fixed: the first build's dome collided.** SetCollisionEnabled(NoCollision) before the mesh was not enough
  on the spawned AStaticMeshActor (BlockAll): the car in L_Base spawned 185 m up at t = 0.5 s and the first half of the
  suite read 1 PASS / 11 FAIL. The NoCollision profile, before and after the mesh, and the actor's collision off: the log
  now reads "collision 0, a physics body 0, actor collision 0", base PASS, the suite below. The Hide runs taken with the
  first build started the car where the pre-L3 run did (Z -191.7 vs -192.4 cm) and the final build's full run matches
  them (hide_10 mean |difference| 0.30 a channel), so their numbers stand.
- **The lighting check** (`Art/sky_shots.bat` spot s, the camera held; L2 and L6 on): the ground box (a 2 x 2 m road
  patch 7 m ahead of the car) Sky 1 against Sky 0 **0.42** mean |difference| a channel (0.2 % of pixels over 8; signed
  +0.09 +0.06 +0.05) against **0.34** (0.2 %; +0.09 +0.04 +0.05) for the same picture taken again; at hide_10's frame the
  ground 0.41 / 0.35, the road 0.35 / 0.30, the ridge 0.42 / 0.44. The car's tailgate (500,632-770,704): Clear 231.8
  153.9 66.7 with the dome, 231.7 153.9 66.9 without, taken 3.5 s apart; the same box DRIFTS in every configuration (to
  228.4 160.2 83.8 in the repeat 14 s later; Overcast 212.7 -> 196.5 red over the sequence), cause unchecked (the
  clear coat's reflections settling after the teleport is the candidate); the Sky pair is inside that drift. gt.Look.Debug
  6: the sky box's flags identical with the dome and without (sky by depth, no BaseColor, lit: 100 % each): the band
  pass meets the dome as the sky it covers, warp and lift, unbanded. **Chosen: the dome; the post-composite alternative
  was not needed.**
- **The haze** (M_GT_PostLook, the one change to `Art/Unreal/setup_look_l2.py`; `setup_look_l3.py` runs it first so either
  script builds the same material; the master's Haze 0): a = saturate((depth - **60 m**) / (**600 m** - 60 m)); on the
  displayed colour after the recomposition (banded and base-less pixels) and before the lift, the saturation to
  lerp(1, **0.5**, a) of itself, then HazeTint **0.70 0.78 0.90** x LitX x SunRef mixed in to **0.35** x a (the first
  build's 600 m and 0.35; the owner's set 1200 m and 0.15, 'Dials applied' below). Not the sky;
  not stencilled pixels, so the far water stays unhazed (L4's). Ridge box (hide_10's frame, 220,315-420,324): Haze 0
  74.5 131.0 60.9, saturation **0.541**, blue - red **-13.6**; Haze 1 185.2 194.5 193.8, **0.054**, **+8.6** (Overcast
  0.505 / -9.7 -> 0.056 / +8.6); histogram peaks 1 and 1: no band added. The near boxes: ground 0.40-0.47 against their
  0.34-0.39 noise. hide_22's far hill 78.2 134.5 63.4 (saturation 0.536) before, 161.9 179.0 168.9 (0.099) after.
- **The card** `M_GT_FoliageCard` + `MI_GT_FoliageCard_Scrub` (/Game/GrandTour/Materials/Foliage): a fresh copy of
  M_GT_Foliage each run (two-sided, its wind WPO on MPC_Weather and its MF_Weather call as they were), Masked (clip
  **0.5**), InstancedStaticMeshes usage; one Custom node in front of MF_Weather: the PLACEHOLDER mask, a fan of **5**
  blades from the foot, each an ellipse tapered to the top (lengths **0.7-1.0**, half-width **0.09** of the card, leaning
  **+-30 deg**), from the instance-local position (the up sign from the instance's Y axis); UseCardMask 1 takes the
  CardMask texture (R mask, G tone) for the owner's card; the tint **0.18 0.32 0.12** (the first build; now 0.08 0.20 0.06), L6's jitter (+-0.04, +-3 deg), one
  of three tones per blade tint x (1 + k x 0.183) at 25/50/25 %; the normal lerped **0.7** toward world up; roughness
  **0.9**, specular 0, default lit. **DabNormal ships 0 (none)**: the clump box on / DabNormal 1 3.30 mean |difference|
  against 3.92 for the same picture again (the wind sways the cards): no difference over the noise.
- **The placement** (`AGTTerrainDressing`, a `Foliage` HISM beside Stones/Posts/Rocks, no collision, casting shadows):
  FoliageMeshPath `/Engine/BasicShapes/Plane.Plane` (the PLACEHOLDER, stood up by roll -90), FoliageMaterialPath
  `MI_GT_FoliageCard_Scrub`; rows outward from the road's edge on both sides at FoliageDensity **0.025** a m2 (6.3 m
  cells, jittered 40 %), kept on the Scrub layer, off any dug channel, at least **6 m** outside the main road's and every
  alt route's edge and nearest their own stretch; nearest first up to **3000** clumps; **2** cards crossed per clump,
  random yaw, **0.8-1.3** of **1.2 x 1.5 m**, the foot 10 cm sunk. The Hide re-dressed through RebuildDressing and saved:
  **3000 clumps, 6000 cards, placed in 0.01 s**. L_Proving not re-dressed.
- **The switches**: gt.Look.Sky, gt.Look.Haze, gt.Look.Foliage (1 by default; -GTLookSky= / -GTLookHaze= /
  -GTLookFoliage=), and gt.Look.Weather <Id> (-GTWeather=), which holds a state through SetState(instant) while it names
  one (added: nothing forced a state from outside before; the states' numbers untouched). **All three 0 = today**: a
  full run with them 0 against the pre-L3 run, hide_10 mean |difference| **0.31** a channel (0.01 % over 8), hide_1 0.20;
  hide_22 1.96 (6.2 %: the water moves between runs; its box 106.9 before, 106.0).
- **Pictures** (`Art/sky_shots.bat`, -GTShotsFrom=50, 30 pictures sky_<s|r|c>_<weather>_<switch> in Saved/Screenshots/M6,
  kept in Saved/Screenshots/L3_sky; `Art/tools/sample_bands.ps1 -Sky`): the sky box (spot s, 40,20-1240,260) Clear
  187.8 205.3 223.8, **12 tones** (24 colours), cloud **4.0 %, 4 clouds**; Overcast 227.2 227.8 227.8, 4 tones, cloud
  97.3 %, one lid; the engine's sky there 63.1 97.7 139.1, 15 tones. The clump box (534,179-758,572): **28 tones** (168
  colours, the ground between the blades in the box), 3 histogram peaks, grain **23.8** tone steps / 100 px (the ground
  there with Foliage 0: 58.5). hide_10 before -> after: sky 80.6 118.5 156.8 -> 204.8 214.8 226.3, grass 75.2 131.6 59.1
  and road 118.2 78.7 48.4 unchanged, ridge 72.4 129.6 58.4 -> 185.2 194.5 193.9; hide_22 sky 100.2 138.4 170.4 -> 209.8
  217.7 227.3. **My looks** (the Read tool; looks): the sky reads as a flat painted gradient with flat, ragged-edged blobs,
  not a texture - but PALE: a hazy light blue much lighter than the engine's sky and the references' cobalt, the horizon
  tint dominating 15-45 degrees up (HorizonPow is the first dial); Overcast a flat pale lid with blue holes rimmed in
  the underside tone. The distance reads as a cool painted haze stepping back in layers rather than as fog (hide_22's far
  hills now separate from the near bank), strong: the far ridge nearly the sky's value. The clumps read as flat blade
  shapes in two or three values (a sage and a yellow-green, the dark tone rarely seen), lighter than the ground, their
  hard shadows on the grass.
- **Frame cost** (`Art/ford_shots.bat` GTWATERSTATS frame ms, steps 22-30, 12/12 pictures every run; clumps in the view
  frustum at the step ends 46 / 89 / ~280 / 46 / 46 / 89 / 46 / 938 / 2029, 46-122 within 100 m): the machine warmed
  across the session (the first run after a pause 12.8-12.9 ms, the next 14.9, then 15.4-16.5), so only neighbours
  compare: all on / all three 0 **16.34 / 16.24** and **16.54 / 16.47** (on first), **16.01 / 15.41** (off first); from the
  three pairs about **+0.1 to +0.3 ms** for the whole stage, under the proposed **1.0 ms** budget: **nothing cut** (card
  shadows, the second noise octave and the 3000 cap stand). Per switch, warm: Sky 0 16.09, Haze 0 16.38, Foliage 0 16.44
  against all on 16.34 / 16.54: inside the drift, not separated. **Full hide run**: before 270 s (the session's first
  run), after 229 s and 229 s (the final build), all three 0 231 s; the last game time 212.7-212.9 s in every run.
- **Tests**: builds `== build exit 0` (three: 39 s, 18 s, 8 s). `bash Art/suite.sh terrain` after the setup: FAIL on
  step 11's ruts gate alone ("slower than down the ruts 0", the known flake), dressing **88 stones 30 rally posts 12 ford
  rocks 3000 foliage clumps (6000 cards), solid=1**. The full suite once at the end (in two calls): **23 PASS, 1 FAIL**
  (terrain, the ruts flake alone; the same dressing line). Line endings: every touched repo file CRLF throughout,
  counted with Python.
- **Unchecked**: the owner's look and every number above (the sky tints and the horizon power, the cloud cell, edge,
  cut, tones, drift; the haze start, end, strength and tint; the card tint, tone count, normal blend, density, size and
  the 3000 cap); whether the sky reads as cobalt at any power (not tried); the car tailgate's drift; rain, snow and storm
  skies (Clear and Overcast only); snow on the up-blended cards; the cards in rain (MF_Weather); every level other than
  The Hide (the sky and the haze are on all of them through the subsystem; unpictured); L_Proving's foliage (not
  re-dressed); Lumen at the terrain's silhouette against the dome (no difference measured in the boxes); TSR on the drift.
- **Dials applied (2026-09-26)**: the owner, "apply the proposed dials": five numbers, nothing else; the first build's
  values stand above as the 2026-09-26 first build, these are the owner's first named set (still the owner's to move).
  **HazeMix 0.35 -> 0.15, HazeEndCm 60000 -> 120000** (setup_look_l2.py's M_GT_PostLook defaults and, since the look
  subsystem pushes its own haze numbers over them every frame, UGTLookSubsystem's HazeMix / HazeEndCm set to the same:
  one build, `== build exit 0`); **HorizonPow 1.5 -> 3.0, Zenith 0.10 0.22 0.55 -> 0.04 0.10 0.45** (M_GT_Sky, Horizon
  0.62 0.72 0.86 unchanged); **MI_GT_FoliageCard_Scrub's tint 0.18 0.32 0.12 -> 0.08 0.20 0.06**. `Art/setup_look_l3.bat`
  logged HorizonPow 3.000, Zenith 0.04 0.10 0.45, BaseColor 0.080 0.200 0.060 and The Hide re-dressed (3000 clumps, 6000
  cards). Pictures: the first build's set copied to Saved/Screenshots/L3_first before shooting (also L3_sky); the dials'
  set in Saved/Screenshots/M6 and L3_dials (the same steps 50-52 and switches; log Saved/Logs/L3/sky_shots_dials.log).
  Before -> after (`sample_bands.ps1 -Sky`, Clear): sky box (spot s) 187.8 205.3 223.8 -> **133.5 164.6 214.7**,
  saturation 0.161 -> 0.380, tones 12 -> 19, cloud 4.0 % / 4 clouds -> 3.5 % / 2; the top rows (0-40) 169.9 196.2 221.7
  -> **99.0 141.0 211.0**, row 250 197.5 210.6 224.8 -> 156.9 180.4 217.1, row 450 (near the horizon) 215.9 222.0 228.7 ->
  208.7 215.9 226.4 (the engine's sky at the top 63.1 97.7 139.1). Overcast sky box 227.2 227.8 227.8 -> 225.5 226.4
  227.5, 4 -> 3 tones, cloud 97.3 -> 97.2 %. Ridge box (Haze 0 / 1): saturation 0.541 / 0.054 -> **0.547 / 0.208**, blue -
  red -13.6 / +8.6 -> **-13.2 / +1.7**, mean 185.2 194.5 193.8 -> 118.9 149.6 120.6; Overcast 0.509 / 0.205, -9.3 / +2.6;
  histogram peaks 1 / 1 as before. The far hill in the sky picture (740,480-940,505), Haze 0 / 1: saturation 0.533 /
  0.047 -> 0.540 / 0.209, blue - red -14.7 / +8.7 -> -15.1 / +0.2. The clump against the grass beside it in the same
  picture (grass box 950,380-1250,650: 73.8 129.3 57.8): the clump box 110.1 156.7 99.4 -> **75.7 133.5 72.5**, luma
  ratio 1.27 -> **1.04**; the blades alone (the pixels Foliage 0 changes by over 8) 128.3 170.0 120.1 -> **76.4 135.0 79.8**,
  ratio 1.40 -> **1.06** (Overcast 1.48 -> 1.15): still a little LIGHTER than the grass, not darker; the clump box's
  histogram peaks 3 -> 1 (the blades now sit at the grass's value). Lighting pair with the dials: ground Sky 1 / 0 0.99
  against 0.97 for a repeat. **My looks** (the Read tool; looks): the sky now reads cobalt at the top, a flat mid blue
  fading to a pale band in the lowest fifth, a painted gradient with flat blobs; the far hills read green-grey and near
  (the ridge keeps its green, a light cool veil rather than a wash); the blades read as flat green shapes close to the
  grass's value, the lighter blades still lighter than the grass, the darker ones about its value. No frame-cost run:
  the instruction counts did not change (the same graphs, other constants). Tests: `bash Art/suite.sh terrain` **PASS**
  (dressing 88 stones 30 rally posts 12 ford rocks 3000 foliage clumps (6000 cards), solid=1; the ruts gate 1 this run).
  No full suite (terrain only, by instruction). Line endings (Python, lines / CRLF): setup_look_l2.py 390 / 390,
  setup_look_l3.py 534 / 534, GTLookSubsystem.h 220 / 220, VEHICLE_BUILD_SYSTEM.md, LOOK_PLAN.md, BACKLOG.md and the devlog
  as counted in the report. Unchecked: the owner's look at the new set; the blades against the grass on other ground and
  light; rain, storm and snow skies; every level other than The Hide.

## 59. OW landscape toolkit port and its test map (2026-09-27)

The landscape dressing toolkit from OWGameUE, water left out, per `docs/LandscapeMigrationManifest.md` section 9
(stages A, D, B, C). The full guide, every command and the owner's checklist: `docs/LandscapeToolkit.md`.
- **Code:** `UOWRoadBedComponent` + the `-GTDressingTest` runner (runtime), the `GrandTourEditor` module (biome PCG,
  tree variant and verge commandlets, bed stamp, `UOWToolkitSetupLibrary`). One CoreRedirect for the road bed.
- **Content:** 334 packages byte-copied (SHA-1 335/335 files), audit 0 missing, 0 water, 0 `/Script/OWGameUE`; the 6
  graphs `PCG_OW*` regenerated and tuned.
- **Test map** `/Game/GrandTour/Test/L_OWToolkitTest`: 505 x 505 vertices over 504 m, 3 x 3 biome cells, scree and
  alpine hills, 3 roads, a cliff wall, 6 `OWBiome.*` PCG volumes, one RVT volume. Painted vertices per layer 3817
  (Snow) to 60531 (Bare); verge 5969 vertices over 3 roads, read-back 255.
- **Ticking pass** (`Art/dressing/tick_harness.ps1`, full editor, 45 s warm): the bed carve at half each road's
  length 27.5 -> -52.2, 49.7 -> 3.3, 9.8 -> 11.1 cm; ISM instances Forest 1108, Meadow 128, Scree 163, Road 1624,
  Cliff 78, Alpine 58.
- **Tests:** `dressing_toolkit` PASS (14 s), in `Art/suite.sh`'s default list (25 tests); `terrain` PASS.
- **Paid:** a commandlet is NullRHI unless `-AllowCommandletRendering` (the verge merge); `delete_asset` leaves the
  map for `new_level`; a spline `set_editor_property` reruns the construction script. Details in the guide.
- **Unchecked:** the look. The owner runs the 9.E checklist in the guide (layers, biomes, borders, grass, trees,
  roads, cliff, RVT, Substrate, perf).

## 62. Leg dressing LD1-LD7: The Hide dressed (2026-09-27)

The OW toolkit's biome dressing on a GrandTour leg, per `docs/LEG_DRESSING_PLAN.md`; the guide, the dials and the
rebuild order: `docs/LandscapeToolkit.md` ("Leg dressing"). Only The Hide (L_Leg03). Commits 650e0cd..aaffd17 and after.
- **LD1 + LD3 (650e0cd), LD1b (c615b17):** biome rules split the off-road byte into layers 6+; the no-biome hashes
  pinned (Hide 0x977AF3A498E07815, Proving 0x7DBDFB11F2FD2CE1); `AGTDressingExclusion`; `MPC_GlobalWind` (Clear 0.1 ->
  0.5); `gt.Look.Dressing`; a route-section band on rules. D2 revised: forest 27.3 %, Thicket 5.6 % of the off-road land.
- **LD2 (2412dd1):** 11 biome rows on `M_GT_Landscape`, the OW grass output (12 pins + ThicketGrass), an RVT output;
  texture samples 21, parameter collections 2.
- **LD4 (1328375):** riparian Thicket before the forest (7002 riparian-dominant vertices); trunk capsules on 21/21 trees,
  none on 4/4 bushes; `PCG_GT_*` (size classes, physical classes, understorey, the Thicket brush). Scratch map: 8,040
  instances in 0.52 s, tree Z scale 0.25-1.70 (x the variants' prescale 0.25-4.06).
- **LD5 v2 (8ca3c40, 5b6804d):** `UGTVegetationSubsystem` (proxy-swap bend, speed-scaled resist with class caps, impact or
  sustained-push snap); `veg` PASS; case 6 +4.09 ms GPU pushing, +2.21 parked; scratch probe 100 m in 17.2 s.
- **LD6:** backup `Saved/Backup/ld6_20260927_173233` (15 files, `SHA1SUMS.txt`). `GTTerrain::HideSpec()` carries the
  palette (one source; the biome test clears it before hashing: both hashes unchanged); `DA_Terrain_Hide` pushed.
  `setup_dress_hide`: 263 exclusion boxes (route 164, alt 73, sections 2, patches 3, gameplay 21, largest the ford sheet
  at 87 m), one RVT volume over the 2016 m landscape, five 2018 x 2018 x 214 m `GTHIDE_PCG_*` volumes. First generation
  (LD4 densities, forest 0.70): 130,495 instances (Solid 9,370, Sapling 8,211, Young 2,051, Brush 110,290, None 573) in
  113 s on a cold editor, the map 35 -> 90 MB. After the cuts: 68,458 (Solid 8,752, Sapling 7,786, Young 1,860, Brush
  49,444, None 616) in 4.4 s warm, 81 MB; tree Z scale Sapling 0.25-0.52, Young 0.45-0.92, Mature 0.71-1.70 (400-440 a
  0.1 bin from 1.0 to 1.6), x prescale 0.25-4.14.
- **Paid on the real leg (all fixed):** the ford sheet's exclusion box was 1055 x 82 m (its absolute-location
  `SurfaceMesh` has empty bounds at the world origin); checkpoints, the zone and the nodes were boxed at their editor
  size (1 m, sized at BeginPlay); `RebuildLandscape`'s ground trace hit a PCG volume's brush and sank every leg actor
  140 m; the volume brushes and the exclusion boxes answered game traces (terrain "on the ground 0", an empty ford in
  the water test); a regenerate over old output saved it half replaced. A bog post comes back +25.3 cm on every rebuild
  (the setup puts it back).
- **LD7 tests:** `route_clear` (new, in the suite, 28 tests): 1178 swept 3 x 4 x 2 m boxes, 0 Solid, 0 Soft; nearest
  Solid 8.15 m, Soft 5.96 m (its circle's edge), unclassed 11.70 m from a centreline, 0 within 2 m of the corridor's
  edge; the 12 gameplay points clear by 5 m (nearest 5.4 m). The sky shots' spot 2 aims at the nearest biome plant; four
  biome views (steps 53-56). The terrain test runs with `-GTLookDressing=0` (step 3's flat-out bend rolled the car on
  the trees, and the damaged car then failed the bog escape and the raised ford). Full suite 28 PASS.
- **Perf** (`hide_shots`, 1280x720, the mean of the steps 1-30 step means, 3 dressing off/on pairs a row; ms):

  | after cut step | off frame | on frame | frame + | off GPU | on GPU | GPU + |
  |---|---|---|---|---|---|---|
  | none | 17.12 | 26.85 | +9.72 | 15.56 | 25.05 | +9.49 |
  | 1 Nanite copies of the soft pack meshes | 17.49 | 22.94 | +5.45 | 15.96 | 21.29 | +5.33 |
  | 2 tree shadow distance | not taken: no per-primitive shadow distance on a 5.8 ISM descriptor | | | | | |
  | 3 `grass.CullDistanceScale` 0.6 | 16.81 | 21.94 | +5.12 | 15.46 | 20.29 | +4.83 |
  | 4 `grass.DensityScale` 0.5 | 17.49 | 21.89 | +4.40 | 16.02 | 20.13 | +4.12 |
  | 5 GT brush density x 0.5 | 17.01 | 21.45 | +4.43 | 15.54 | 19.82 | +4.28 |
  | 6 forest from 0.75 | 15.98 | 20.40 | +4.42 | 14.63 | 18.82 | +4.19 |
  | 7 `r.Nanite.AllowVoxels` 0 | 16.08 | 20.15 | +4.07 | 14.80 | 18.72 | +3.92 |

  **Over the +2.0 ms budget after every step: the list ran out.** The HISM A/B was moot (PCG turns HISM into ISM for
  Nanite meshes). Water after step 7: field step 1.90 -> 2.10 ms, the worst step 42 fps dressed (30 before the cuts).
  Thicket nearest the route, 100 m at 30 km/h: before the cuts +14.26 ms frame / +14.16 GPU, the vegetation's work
  0.052 ms mean, 0.689 max; after step 7 +4.99 / +5.04, 0.046 mean, 1.879 max (4 sapling snaps).
- **Pictures:** `Saved/Screenshots/LD7_cut7/p3_d0` and `p3_d1` (33 each, off and on), `LD7_final/sky_and_views` (44).
  Unchecked: the look. Gate: the owner drives The Hide (plan section 9) and decides the budget.
- **LD8a (0a0faaf, 2026-09-28):** the no-gain cuts 5-7 undone (`GTBrushDensityScale` 1, the forest from 0.70,
  `r.Nanite.AllowVoxels=1`; grass cull 0.6 / density 0.5 and the Nanite pack copies kept): 130,495 instances (the LD6
  first generation), Forest + ForestFir 27.1 %, Thicket 5.8 %. Summer leaves on the GT graphs only: 15
  `MI_GT_Leaf_*_Summer` (`Art/dressing/retint_summer.py`), 506 spawner slots; the OW and pack content SHA-1 unchanged.
  `-GTProfileGPU` (ProfileGPU after a picture, `Art/dressing/ld8_profile.ps1` / `.py`, `docs/landscape_migration/
  ld8_profile*`). Pairs 1-2 (pair 3 cut): graphics frame 10.90 -> 15.79 ms (+4.88), async compute +2.55; the growth:
  Lumen DiffuseIndirectAndAO (async) +2.46, ShadowDepths +1.55, Nanite::VisBuffer +0.80, LumenSceneLighting +0.65,
  BasePass +0.64. hide_shots GTPERF (2 runs a state): off 14.11 / on 18.06 frame (+3.95), GPU +3.85. The laptop GPU
  throttles within each run (86-87 C, SW thermal slowdown, 1680-2235 MHz at the hide captures).
- **LD8b (2026-09-28):** GT grass copies `LGT_GT_*` on `M_GT_Landscape` (the OW types already had dynamic shadow off,
  contact shadow on and distance-field lighting off on all 43 varieties, so the copies change no flag); Soft.Brush,
  Soft.Sapling and unclassed descriptors out of Lumen and the distance fields (`bAffectDistanceFieldLighting`,
  `bAffectDynamicIndirectLighting` false); bushes and cover plants `WorldPositionOffsetDisableDistance` 5000 cm;
  view_thicket 12 m from a Thicket edge. Four launches (the cool-down guard capped at 3 min: every run started at
  61-69 C): hide_shots off 16.19 / on 21.04 frame (+4.85), GPU 14.74 / 19.37 (+4.63). **Over the +2.0 ms budget**;
  stopped there (no further fixes), the owner drives. Profile deltas LD8a -> LD8b (6 views): frame +4.88 -> +6.59,
  DiffuseIndirectAndAO +2.46 -> +2.46, ShadowDepths +1.55 -> +3.06, Nanite::VisBuffer +0.80 -> +1.14,
  LumenSceneLighting +0.65 -> +0.64, BasePass +0.64 -> +0.62; the hide captures ran at 1665-1920 MHz, 86-88 C (one
  capture a state), so the two series are not at the same clocks. Pictures `Saved/Screenshots/LD8b` (dressing on).
- **LD8c (2026-09-28):** the LD8b pictures showed default-checker bushes. The `-game` logs said why: "Material
  .../MI_GT_Leaf_Bush_PackBirch_Summer missing usage flag Voxels! Default Material will be used in game" and the same
  for the vendor `MI_BirchTree_Bark_01_Summer` - the Nanite pack copies of the birch bushes on the pack masters
  `M_Tree_Leaf` / `M_Tree_Bark`, which lack the Voxels usage, while `r.Nanite.AllowVoxels=1` (the LD7-era logs show the
  vendor `MI_BirchTree_Leaf_01_Summer` falling back the same way before cut 7 turned voxels off). Fix: GrandTour master
  copies `M_GT_Tree_Leaf` / `M_GT_Tree_Bark` (Voxels, Nanite, ISM usage) under `/Game/GrandTour/Dressing/Materials/Masters`,
  the four pack-derived `MI_GT_Leaf_*` reparented, `MI_GT_BirchTree_Bark_01_Summer` for the Nanite copies' bark (556
  GT slots); the pack albedo moves only when warm (the birch bushes and oaks back to the vendor Base Albedo Color).
  Vendor and OW content SHA-1 unchanged. The two hide_shots runs log no "missing usage flag" / "Default Material" line.
  hide_shots GTPERF off 15.62 / on 20.01 frame (+4.39), GPU 14.26 / 18.58 (+4.32) (LD8b +4.85 / +4.63); every
  capture at 86-87 C, SW thermal slowdown, 1665-2115 MHz. Reported as measured, no more cuts; the owner drives.
  **Note:** LD7's cut 1 (Nanite pack copies, -4.3 ms) was probably measured with those bushes on the default material
  (voxels were on then), so its gain is suspect. Pictures `Saved/Screenshots/LD8c` (dressing on).

## 63. Approved painterly clay on live deformation (2026-09-29)

The approved MudStyleStudy/03 color and normal bakes now shade `M_GT_Mud` and the Mud/Bog rows of
`M_GT_Landscape`. `Art/Unreal/live_mud_style.py` shares the triplanar sampling block, samples displaced
height on rut walls and blends compressed tracks toward the worked-clay bake. The existing field sampling,
WPO, holes, traction, ridge shape and water tables are retained. Backups of both masters are under
`/Game/GrandTour/ArtTests/MudStyle/BeforeLive_*`.

`Art/setup_live_mud_drive.ps1` creates `/Game/GrandTour/ArtTests/LiveMudDrive/L_MudDrive`: 140 m of gravel,
mud (32-60 m) and ford (88-100 m), with approved tussocks and winch anchors. Its landscape material is a map-specific
copy with gravel/clay transitions. The setup clears the builder's legacy foliage from this map.
`Art/check_live_mud_drive.ps1` drives the real car in PIE twice, retaining the ruts for the wet replay, and records
completion, field volume, wheel sinkage and water contact. The existing steering and test-wetness setters and
field-volume getter were exposed to Python; their implementations did not change. Build passed.

Full validation and performance results, screenshots, reproduction, and remaining visual limitations are in
`docs/LIVE_MUD_DRIVE.md`. Reapply the live setup after running the legacy mud/landscape material builders.
The static art studies were preserved; the new live strip is ready for the owner's visual and driving review.

## 64. Softer mud shoulders and boundary continuity (2026-09-29)

User requested less sharp/uniform deformation and removal of the live/non-live ground seam. The shared CPU field
now makes sloped, width-varying shoulders, coherent shallower pockets and a rounded belly feather. Later banks and
trailing feathers preserve earlier compacted cuts. The L_MudDrive landscape apron now matches clay normal detail
and roughness as well as color; the patch overlap lip went from 1 cm to 1 mm. Rut walls retain more clay detail.
Build and GrandTour.Mud.SoftShoulders passed; dry route completed and the boundary/long-rut images were inspected.
God of War started during the wet capture, which timed out near 61.8 m at roughly 14 fps; the editor subsequently
exited with an access-violation status after writing its failed report. Final wet/repeated-drive validation and
regressions are deferred at the user's explicit request: "Save changes and previews; test later".
Details and reproduction: docs/LIVE_MUD_SHOULDERS.md. No current-revision performance result is claimed.

## 65. Living mud LM1: the living field (2026-10-05)

docs/LIVING_MUD_PLAN.md stage LM1 (its italic note has every number). `FGTMudField` gains a time step for the cells a
wheel has recently touched: `Settle(DeltaSeconds)`, fixed 1/30 s sub-steps from an accumulator (at most 2 a frame),
over tiles of 16 cells (2 m) with an awake flag and a one-cell border. Per neighbour pair: slump of the step above
tan(ReposeDeg) x CellCm, and ooze of the whole step while either cell's set timer `SetS` runs; the flux goes through a
delta buffer, so volume is conserved and the outer edge is closed. The receiving cell's `OffsetCm` smears the way the
mud went; a per-cell `Fresh` is 1 where the surface moved over 0.01 cm and fades over FreshFadeS. The stamps set
`SetS`, mark `Fresh` and wake their tiles, and write nothing else new: with `gt.Mud.Settle 0` the field is LM0's.

- Numbers (`AGTMudPatch` UPROPERTYs, copied from `FGTDeformProfile` by `ApplyProfile` in `BuildPatches`): bog ReposeDeg
  38, SlumpRate 2.0, **OozeRate 1.2** (proposed 0.6; 0.6 gave 8.3 % back at 5 s, 1.2 gives 17.7 % of the asked 15-25),
  SetSeconds 4.0, SmearCmPerCm 0.5, FreshFadeS 6.0, SleepCmPerS 0.05; the ford bed 45 / 0.1 / 1.5.
- `AGTMudPatch::Tick` settles before `TakeDirty`/`Upload`; `TreadTexture` B carries `Fresh` (0 while the switch is off).
  The traction stamps from `AGTCarPawn::Tick`; both on the game thread. Cycle stats `STAT_GTMudSettle` and
  `STAT_GTMudUpload`, CSV timers `GTMud/GameThread/Settle` and `/Upload`, and `UGTMudSubsystem` readouts
  (`GetSettleMeanMs`/`MaxMs`/`AwakePeak`/`Frames`, `GetUploadMeanMs`/`MaxMs`, `ResetSettleStats`, `MudHeightCmAt`,
  `MudFreshAt`, `ResetFieldsForTest`).
- Material (`Art/Unreal/live_mud_style.py`, the live block): `SlideUV` 1.0 drags the clay's sample position by the
  field's offset (vertices unchanged, SlideScale 0), `FreshWet` 0.6 takes roughness toward 0.5 and albedo x 0.85 by
  Fresh, read from MudTread B (the live code had not sampled MudTread before; it is now wired to the surface node).
- Tests: `GrandTour.Mud.Settle`, every row of the plan's table, PASS (volume error 0.1 cm^3 of 3.47 m^3 lowered, steepest
  step 7.57 cm, 17.7 % back at 5 s, ford 0.20 %, crest 8.90 -> 5.71 cm and 66.1 -> 68.1 cm wide, asleep at 10.40 s,
  frame rates identical, deterministic, Settle 0 = LM0). `Art/mud_shape_test.ps1` runs all of `GrandTour.Mud`.
- Housekeeping: the terrain test's raised-ford flood is latched over the run and counted (PASS in three runs, flooded
  once each); the stage I floor gate is re-based to -28.0 x 0.825 x (1 - 0) = -23.1 cm +-15 % (PASS at -23.6); the
  stage H crest gate's re-derivation leaves its band where it was and it still FAILS (4.45 against 5.35-9.94: the
  stage H smoothing under section L's shoulders, not the pockets or the ooze). Step 11's held exit failed three of four
  runs (4.4-5.1 s against a 5.4-5.6 s pass; it passed the fourth, 5.7 s against 4.5; LM0 passed both): the shallower
  settled ruts, reported, not tuned.
- The drive check (`Art/Unreal/check_live_mud_drive.py`) now plays in a new 1440x900 window (client 1440x868,
  `UGTPlayWindowLibrary::RequestPlayInNewWindow` in GrandTourEditor; the first window comes up 1274x682 and is asked
  for again) and, in one session, profiles a dry crossing with Settle 0, the same crossing on reset fields with Settle
  1 (the cost readout), the settle pair on a fresh rut (`Mud_Settle_0s/5s.png`, `settle_profile.csv`), the old
  pictures, the wet replay and a last dry crossing with Settle 0 (A/B/A). The wrapper judges by a fresh `ok: true`
  report and prints the editor's -1073741819 exit as the known shutdown fault.
- Cost on the dry crossing: Settle mean 0.100 / 0.138 ms, max 0.620 / 3.62 ms, awake peak 50 / 48 over two runs (gate
  0.3 / 1.0): the max passed once and failed once, in a session other apps slowed by 40-90 %. Frame times in the same
  viewport drift run over run by more than the switch moves them (the GPU rose after switching back to 0); Settle's
  own share is 0.1 ms. The strip completes dry and wet; dry it lowers about 7 % more volume with Settle on (22.3
  against 20.8-20.9 M cm^3 in the same sessions; the ooze raises floors that later wheels cut again, not measured apart).
- Full suite: `bash Art/suite.sh` 27 PASS, 1 FAIL (terrain, on the stage H crest mean alone: 7.65 -> 4.45, asked 5.35-9.94; its step 11 passed, held exit 5.7 s against a 4.5 s pass; the raised ford flooded once -> PASS). Body and winch passed first time.
- Unchecked: the look of SlideUV, FreshWet and the settle pair (pictures written, not judged); the feel. Owner gate:
  drive the strip, watch the ruts settle behind the car, drive back down them; name ReposeDeg, the recovery share,
  SetSeconds, SlideUV, FreshWet.

## 66. Living mud LM1b: recovery that keeps the detail (2026-10-05)

docs/LIVING_MUD_PLAN.md stage LM1b (its italic note has every number). The owner drove LM1 and found it "too smooth":
LM1's ooze is a diffusion, a blur that took half the field's fine detail in 4 s (D 0.48 of its stamped value) and barely
moved the strip's broad 15 cm rut. `FGTMudField::SettleStep` gains a **shape-keeping relax** in its place: while a cell's
set timer runs, its own height moves toward the ground by K = 1 - exp(-a dt), a = -ln(1 - RecoverShare) / SetSeconds, so
a rut cell rises and a bank cell sinks in proportion to its own height. Per sub-step the rises asked by every set cell
below 0 (V_up) and the falls asked above 0 (V_down) are summed over the patch and the larger side is scaled to the
smaller, so the rut rises only by what the banks give up and the volume is kept exactly. HeightCm only (LM2a's lumps
will ride on it). Each moved cell's OffsetCm creeps down the surface's slope by CreepCmPerCm per cm moved, capped at
MaxSlideCm. Talus, Fresh, the set timer, tiles, sleep and the 2-sub-step cap are LM1's; `OozeRate` stays as a code path,
0 by default.

- Numbers (`AGTMudPatch` UPROPERTYs, `FGTDeformProfile` fields copied by `ApplyProfile`): bog **RecoverShare 0.4**
  (the plan's 0.2 gave 7.6 % back: the banks hold about 35 % of a rut's volume, so the rut comes back about 0.38 x
  RecoverShare; the main session revised it), ford 0.02; CreepCmPerCm 3; OozeRate 0 (bog and ford).
- `GrandTour.Mud.Settle`, every row PASS: 15.2 % (narrow 40 cm stroke) and 15.5 % (broad 15 cm) of the core back at 5 s
  (asked at least 14), ford 0.8 %; detail kept D10/D0 0.918 / 0.978 (asked 0.9-1.1) against LM1's diffusion 0.484 / 0.479;
  crest 40.6 % / 40.3 % lower at 5 s; volume error 0.0 cm^3; steepest step 9.30 cm; asleep at 10.40 s; frame-rate and
  determinism identical; Settle 0 = LM0's field. `FGTMudField::DetailRatio` is the D measure.
- Check script (`Art/Unreal/check_live_mud_drive.py`): the settle pair writes D (`detail_d`, over the cells within 1 m x
  1.5 m of the spot, from `UGTMudSubsystem::MudCellHeightsCm` / `MudCellsAcross`), a per-tick trace of the core cell
  (`MudSetSecondsAt`, the sheen, the patch's awake tiles and sub-steps), and after the third crossing drives the pair
  again with gt.Mud.Settle 0 from the very same camera (`Mud_Settle_0s_Off.png` / `Mud_Settle_5s_Off.png`). The report's
  `dark_line` projects the patch's box edge, the hole's inset edge (HoleInsetCm from the landscape material) and the lip's
  inner ring into the pair camera's 1440x900 shot (a pinhole; the engine's own projection agrees in x and differs by the
  viewport's letterbox in y).
- Strip, the clean run: dry and wet complete (62.6 s / 58.5 s; LM1 61.6-61.8 / 54.4-56.2), lateral 0.27 / 0.33 m.
  Settle cost on the dry crossing mean 0.134 ms, max 1.34 ms (three frames over 1 ms, on 20-26 ms game frames), awake
  peak 44: the max gate fails once more. The settle pair moves little between 0.3 s and 5 s (core -17.48 -> -17.10 cm,
  D 0.0593 -> 0.0597) because with Settle 1 the car takes 14.6 s to clear the spot from its first wheel (1.8 s with
  Settle 0) and most of the relax is done before t0: 9.4 % back from the rear wheel's last cut. Not investigated.
- The thin dark line along the left of the settle pictures sits on the patch's box edge (the mesh's outer ring), not on
  the hole's inset edge, and shows with gt.Mud.Settle 0: not new. Not fixed.
- Terrain, two runs: step 11's held exit 5.4 / 5.4 s against 5.6 / 5.9 s down the ruts -> FAIL both (LM1 failed 3 of
  4); escape forward 10.8 / 10.6 m, reverse 6.0 m in 7.9 / 6.4 s; rut mean -30.1 / -30.6 cm (LM1 -27.0..-27.2); stage H
  crest still FAIL. drivetrain, grip, mud, surface and track PASS.
- During the session the OpenAI Codex app ran Unreal imports and renders of its own in this project; two drive checks
  overlapped them (one stalled in the wet bog) and were repeated. Unchecked: every look; the feel. Owner gate as LM1's,
  with RecoverShare and CreepCmPerCm added to the numbers to name.

## 67. Living mud LM2a + LM2b: lumps, the wheelspin throw, clay clods (2026-10-05)

docs/LIVING_MUD_PLAN.md stages LM2a and LM2b (their italic notes have every number). Phase A (code, tests, headless
Blender, the clod import, the live setup) ran with the owner's God of War running. Phase B's drive check also started
with it running, by the owner's override; the game had exited before the suite. The cost gates are unjudged until a
clean run.

- **Lumps.** `FGTMudField::LumpCm` rides on `HeightCm`. `SurfaceCm` is what everything reads: `HeightAt`, `GradientAt`,
  `CellHeightCm`, the upload, the water depth, the talus, `DetailRatio`, the check script's cells. Each stamp holds back
  `LumpShare` 0.35 of what the bank's cells would take and spreads it by a static weight W, with exact volume. W is a
  set of smooth domes round hashed jittered sites, `LumpSpacingCells` **4** (landed; 3 gave 1.15x crest variation
  against at least 1.5x) and `LumpRadiusCells` 1.6 +-40 %. A cell holds at most `LumpMaxCm` 10; the excess goes into the
  same cell's `HeightCm`. A capsule (and the belly) flattens the lumps under its bowl into its displaced volume. The
  talus runs on the surface and takes outflow from the lumps first; the relax touches `HeightCm` only (the main
  session's decision). Stage I's `ClodChance` is 0. With lumps on, the rut gets about 10 % back at 5 s (15 % off): the
  lumps keep about 35 % of the bank out of the relax's balance.
- **The throw.** `StampWheel(..., ThrowShare, OutThrownCm3)`; the old call forwards 0, and LM0's field reproduces to the
  bit. The traction maps slip to a throw share. `SlipMagnitude` is Chaos's tyre surface speed less the ground's at the
  contact, in cm/s. The spin is that times the drive's sign, so a locked wheel never throws. The share rises from the
  wheel's `SlipThreshold` (20) to `ThrowMax` 0.5 at `SlipSaturation` (300); `FGTWheelTraction::ThrownCm3` accumulates
  it. `UGTSprayComponent` spends it on 6-14 cm blobs carrying 4/3 pi r^3 x 0.6. A blob that comes down on a patch's
  surface calls `AGTMudPatch::DepositThrown`: a 1.5 x radius dome into the lumps, at least one cell, volume exact,
  fresh, its tile woken. Blobs off every patch are lost: 1-3 % over a crossing.
- **Clods.** `Art/Blender/build_mud_clods.py` (headless) writes five procedural clods (328-332 triangles, 10 x 6 cm,
  pivot on the flat face) to `Art/Export/MudClods`. `Art/import_mud_clods.ps1` imports them as
  `/Game/GrandTour/Mud/Clods/SM_GT_Clod_0..4` (no collision, Nanite off), and `live_mud_style.py` builds `M_GT_Clod`:
  clay bakes tri-planar at 1.5 m, wet roughness and darkening, a +-6 % instance tint. `AGTMudPatch` keeps one HISM per
  mesh and a 1,200-slot ring, fed by bank lump sites and throw landings. Clods re-snap on dirty tiles, are squashed
  under a new capsule and sink in the wet, all in 5 Hz batches. `gt.Mud.Clods` switches them; with no mesh there are
  no clods.
- **Housekeeping.** `FreshMinCm` 0.002 (the pair's core reads Fresh 1.0 at 0.3 s). Per-feature mean / p99 / max with the
  gate mean <= 0.3 / p99 <= 0.7 (`UGTMudSubsystem` keeps every frame's sample). The stage H crest gate is a report;
  it reads 7.65 -> 6.12 cm with lumps, back inside its old band. The crawl log, `crawl.csv`: Settle 1 takes 5.77 s
  for 2.3 m against 2.03 s with Settle 0. The wall just ahead of a slow tyre reads about 0.6 cm higher, RutClimb and
  the hold drag double, and the wheels never spin up. Diagnosed, not fixed. The drive check's wrapper now turns off the
  editor's background throttle: with a game in front the hidden editor ran under 1 frame a second and the car never
  moved.
- Tests: `GrandTour.Mud.Lumps` and `.Throw`, every table row PASS. `GrandTour.Mud.Settle` asserts LM1b's rows with lumps
  off and the lumps-on rows (recovery at least 9 %, asleep by 12.5 s, D kept 0.9-1.1, step, volume). SoftShoulders PASS.
  `Art/mud_shape_test.ps1` asks for all four.
- Strip: dry and wet complete (64.3 s / 58.9 s; LM1b 62.6 / 58.5); spin test, clod counts, the GPU at the cap: see the
  plan's notes. Terrain: one run PASS, two FAIL on step 11's held exit alone (needs 1.05x: 5.4 vs 5.4 s, 5.8 vs 5.6 s);
  the escape, rut mean -31.0 cm, stage I shape and the fords PASS. drivetrain, grip, mud, surface, track PASS. Full
  suite: `bash Art/suite.sh` 27 PASS, 1 FAIL (terrain, on step 11's held exit alone: 5.9 vs 5.6 s; escape 10.4 m, reverse 6.0 m in 5.6 s), so step 11 passed 1 of 4 terrain runs; spray, water, body, winch and the rest PASS.
- Unchecked: the feel; the look beyond one glance at `Mud_Clods_Dry.png` and `Mud_Spin_Dry.png`. The spin crept 1 m
  rather than digging in place, and the lane has no Bog layer. Owner gate: drive, spin up, look at the banks and the
  mound; name `LumpShare`, the lump size, the clod rates and sizes, `ThrowMax`, `RecoverShare`.

## 68. Living mud LM2c: non-uniform lumps and clods (2026-10-05)

docs/LIVING_MUD_PLAN.md stage LM2c (its italic note has every number), the owner's "They are very uniform. Fix that and
then move on." No game and no foreign Unreal ran at any step, so the cost numbers are judged.

- **Lumps.** `FGTMudField::bLumpVariety` (true; the patch's `bLumpVariety` pushes it) switches `EnsureLumpWeights` to
  LM2c; false is LM2a's path to the bit (the Variety test's comparison). Sites jitter over their whole grid cell. A
  smoothed value noise (`LumpClusterCm` 150) leaves out the sites under its `LumpAbsentShare` 0.35 quantile, in patches.
  Each site gets an amplitude of 0.3 + 1.3 u^2 and an elliptical dome (aspect 1-2.2, a random angle, radius +-60 %, each
  semi-axis at least one cell). 20 % of sites take a smaller satellite 0.6-0.9 of the radius away. `LumpShare`,
  `LumpMaxCm` and the normalisation are unchanged, so the held volume lands on fewer, taller domes.
- **Bank clods.** These come from the lip, not the site tops: the eligible band cells beside the stroke's line, the band's
  inner 40 % measured square to it. Each stamp gives each cell a chance of `ClodBankPerCm` (landed 0.014) x what the cell
  took (bank + lump, cm) x the cluster weight, from a hash of the cell and the stamp counter. Sizes run 3 + 15 u^2.5 cm.
  LM2b's site roll is the `bLumpVariety` 0 path.
- **Throw.** Blobs are 4 + 12 u^2.5 cm across, each with its own heading (+-25 deg) and throw speed (x 0.5-1.5). They leave
  as a Poisson stream in the thrown volume whose rate follows what waits at the wheel (`ThrowReserveBlobs` 3), so the
  waiting mud stays near three mean blobs and the mean rate is unchanged. `ClodThrowChance` is 0.2.
- **Meshes.** `Art/Blender/build_mud_clods.py` (headless) now writes ten clods in four families by number: 0-1 blobs, 2-4
  pancakes and a slab, 5-7 broken chunks (one or two planar cuts, flat faces), 8-9 smears (aspect 1.87 / 2.37).
  They range from 254 to 328 triangles, 10 cm across and 2.4-7.0 cm tall. The patch reads each mesh's height from its
  bounds and the family from its number.
- **Placement and pools.** Each instance gets XY scale 0.7-1.4, Z 0.5-1.2, a random yaw and the local normal (field +
  ground) tilted +-35 deg. It sinks 0.35-0.75 of its own height. The mesh comes from its source's family odds: banks
  favour pancakes and chunks, throws blobs and smears. The slot no longer fixes the mesh: each HISM keeps a pool (1,200 /
  10 to start, growing by half when it runs out) and a free list. Pushes go per dirty instance, not over a range, and the
  wet sinking re-pushes at 0.2 cm.
- **Material.** `M_GT_Clod` has a +-12 % value tint and a static freshness from PerInstanceCustomData 0 (throw 1, bank
  0.3; `FreshDarken` 0.2, `FreshRough` 0.5, proposed).
- Tests: `GrandTour.Mud.Variety` (new). Lumps and Throw PASS; Settle, SoftShoulders and Variety FAIL. Variety fails one
  row: the peak-spacing CV is 0.355 against at least 0.45 (LM2 0.258). Settle fails the narrow stroke's detail kept with
  lumps on, 0.893 against 0.9-1.1 (LM2 1.009). SoftShoulders fails its cross-step, 25.15 cm against under 24 (LM2 17.34).
  An ablation in the Variety test traces both old-gate breaks to the absent sites (without them: 18.72 cm, 0.938). The
  satellites add nothing to the spacing CV (0.351 without them): at 1-1.4 cells from the parent's top they make a
  lopsided lump, not a second peak. Reported for the main session, not relaxed.
- Strip: dry and wet complete (61.0 s / 57.5 s; LM2 64.3 / 58.9). The dry crossing ends with 768 clods live, 122 from the
  bank and 746 from the throw (LM2 1,023 / 389 / 1,911); the asked 300-350 live is not met, and the throw is the bulk.
  Clods p99 is 0.296 ms dry and 0.248 ms wet (LM2b 0.594 / 0.884); the GPU at the cap is +0.305 ms (asked <= 0.3; LM2b +0.34).
- Suite `terrain drivetrain grip mud surface track`: 5 PASS, 1 FAIL. The terrain fails on stage I's ridge shape alone (crest cv 0.85 against 0.22-0.60). Step 11's held exit, the escape (10.6 m forward, 6.0 m back) and the rut mean (-30.9 cm) pass. drivetrain, grip, mud, surface and track PASS. No full suite this stage.
- Unchecked: the look beyond one glance at Mud_Clods_Dry.png, Mud_Spin_Dry.png and the new Mud_OnFoot_Dry.png (the
  owner's eye-level view along the settle pair's rut), and the feel. No owner gate here: the owner sees the clods at
  LM3's gate.

**Follow-up (2026-10-05, the main session's "Follow-up decisions after LM2c").**
- **The bank keeps the absent sites' share.** An absent site's share of the held lump volume now stays in the bank: the
  held share is LumpShare x the existing / full-set lump weight over the stamp's cells (`LumpWFull`), so the existing
  domes keep a full set's heights. That brings SoftShoulders back (18.68 cm) and Settle's narrow D kept (0.975).
- **The absent share.** Tried 0.35-0.55; only 0.50 and 0.55 land the spacing cv (0.509 / 0.650). The terrain test's
  stage I crest cv reads 0.62-0.64 at every share (LM2 0.46), so no share keeps it.
- **Shipped.** `LumpAbsentShare` 0.5, `ClodBankPerCm` 0.017 (a third of LM2b's bank clods per metre again) and
  `ClodThrowChance` 0.065 (the dry crossing: 352 live, bank 106, throw 309).
- **Results.** All five mud tests pass. Wet clod p99 0.183 ms; the GPU at the cap +0.246 ms. The suite is 5 PASS,
  1 FAIL: terrain, on stage I's cv 0.64 and step 11's held exit (the known flake).

## 69. Living mud LM3a: snow sections, compaction, the plough, refill, L_SnowDrive (2026-10-05)

docs/LIVING_MUD_PLAN.md stage LM3a (its italic note has every number), docs/LIVE_SNOW_DRIVE.md (the strip). No game and
no foreign Unreal ran at any step, so the cost numbers are judged.

- **Housekeeping.** Terrain stage I's crest-cv band is 0.22-0.75 (`GTM6TestRunner.cpp`, the reason in a comment).
  `FGTDeformProfile` owns the LM2c variety (`LumpAbsentShare`, `LumpClusterCm`, `LumpAmpMin/Max`, `LumpAspectMax`,
  `LumpVarietyRadiusJitter`, `LumpSatelliteChance`), `ClodBankPerCm`, `ClodThrowChance`, and the field's own
  `RidgeReturn`, `RutShoulderCm`, `RutDepthVariation` and a new `RutShoulderMinCells` (the field's hard-coded 2-cell wall
  floor until now). The patch has each as a UPROPERTY, `ApplyProfile` copies them and `Init` pushes them into the field.
  Every default is the value in force before, so the bog and the ford are unchanged (the five mud tests read LM2c's
  numbers to the digit, field CRC 8e0aad06). The mud check also takes `Mud_Clods_Dry_NoShadow.png` (the patch meshes'
  shadow casting off): the black patches beside the near lumps stay, so they are not the mesh's cast shadows.
- **The section.** `EGTRouteSectionKind::Snow` (appended after Ford): `SnowWidthScale` 1.4 of the road, no sink, the
  Snow layer (3) across the paving. Its profile on ByKind is `FGTTerrainSpec::SnowProfile`
  (`FGTDeformProfile::SnowDefaults()`), through `GTTerrain::DeformProfileFor(Spec, Section)`; the one-argument form is
  unchanged, and a section's own Deform with Mode On overrides it. `FGTRouteSection::SnowDrifts` deepen stretches of it
  (a depth curve by the arc of the nearest route point, `GTTerrain::SnowDepthCmAt`), baked per cell when the patch is
  built. The Hide and the Proving Ground have no Snow sections: their grids and hashes do not move.
- **The field.** `FGTMudField::bSnow`, `SnowDepthCm`, `SnowEdgeCm`; per cell `SnowDepthCell` and `SnowTopCm` (the depth
  x a smoothstep taper over 300 cm in from the box's border). The heights stay relative to the snow's top;
  `GroundRelativeAt` adds the top back. `StampWheel` in snow cuts each capsule cell to the tyre's own bottom, -(sinkage +
  the snow top), with no sinkage needed. Snow alone hands the whole return to the lip (the band's eligible cells beside the
  stroke's line, normalised over their weight), leaves its floor unsmoothed, and lets the ridge smoothing keep a cell that
  already stands over the cap. `PloughBelly` cuts the belly's box to its underside where the snow stands above it and puts
  `PloughReturn` 0.3 of the cut into a 40 cm sine band beside each long side. `Refill` raises every cell under the snow
  top by `RefillCmPerMin` x the time, fades the tracks by the same share of the depth and softens the lumps by the same cm.
- **The patch.** `Medium` Snow: the mesh rests on the snow top (MeshRestZ carries it, so the clods and the spray land on
  the snow); no rut water (no water grid, `WaterDepthCmAt` 0); `M_GT_Snow` and `M_GT_Clod_Snow` (from
  `Art/Unreal/live_snow_style.py`; the mud materials with a warning when they are missing); `DisplaceDownCm` covers the
  deepest cut. The refill runs at 1 Hz while the weather snows (precipitation below freezing, the weather subsystem's own
  rule for its snow amount); `gt.Snow.Refill` -1 / 0 / 1. Readouts: `PloughedCm3`, `PloughBermCm3`, `RefilledCm3`,
  `RefillPasses`; `UGTMudSubsystem::SnowTopCmAt`, `SnowPloughedCm3`, `SnowPloughBermCm3`.
- **The traction.** In a snow patch: the profile's MaxSinkage 5 cm and SinkageRate 0.05; a tyre stamps whatever its
  sinkage; the rut read is against the ground; the plough term is `SnowPlough` x the snow ahead over the tyre's bottom
  (the mean of the three rut probes) / the wheel's radius x the bog's speed law, in place of the row's plough; the belly
  drags `BellyDragPerMetre` x the snow standing over its underside (AxleClearanceM over the deepest tyre's bottom) just
  ahead of its box, on every wheel in the patch; the belly's plough box spans the car out to the tyres' outer edges.
  `FGTWheelTraction::bInSnowPatch`, `SnowAheadCm`; `UGTTractionComponent::BellySnowCm`, `bBellyInSnow`,
  `BellyPloughedCm3`; the Diag surface, plough and belly terms are readable from Python. The mud path is the same
  arithmetic as before.
- **Materials.** `M_GT_Snow`: a fresh copy of the live M_GT_Mud graph each setup (the same WPO and field sampling) with flat
  values, fresh albedo 0.85 / roughness 0.7, packed (tracks) 0.72 / 0.45, as `SnowFreshAlbedo`, `SnowFreshRough`,
  `SnowPackedAlbedo`, `SnowPackedRough`. LM3b replaces its surface block. `M_GT_Clod_Snow`: near-white (0.85 / 0.86 /
  0.88), roughness 0.7, the instance tint (0.05) and the freshness path kept with no darkening.
- **Tests.** `GrandTour.Snow.Compact` (`Source/GrandTour/Terrain/GTSnowTests.cpp`), every row PASS: volume gone 0.8021 of
  the cut (asked 0.8 within 1 %; 0.8154 at the bog's RidgeBlend 0.9); the wall below the lip mean 67.4 deg, min 63.1, just
  cut and after 10 s; the taper 0.00000 at the border and 1.00000 at 300 cm in; refill 6.00 cm in 3 min (asked 6 within
  10 %); the plough's berms exactly 0.3 of its cut. `Art/mud_shape_test.ps1` runs `GrandTour.Mud+GrandTour.Snow`: 6 of 6.
- **Strip.** `L_SnowDrive` (`& Art/setup_live_snow_drive.ps1`, `& Art/check_live_snow_drive.ps1`): both passes complete
  (257.9 s fresh, 36.6 s in its own trench); the drift at 0.219 then 2.870 m/s, 13.1x (asked at least 1.15); the belly
  ploughed 26.4 m^3 on pass 1; the trench walls 69-70 deg, the berms 17-22 cm over 35 cm of snow and 33-34 cm over the
  drift's 60. Settle mean 0.029-0.054 / p99 0.105-0.247 ms, clods 0.005-0.007 / 0.093-0.149 ms: PASS. In fresh snow the
  car crawls (0.39 m/s in 35 cm): the drag at full sinkage (the Snow row's rolling 0.120 + the belly 0.066 + the plough
  0.009) equals the row's grip there (0.196). Not tuned; the main session decides.
- **Regressions.** The mud strip completes dry (62.1 s) and wet (59.1 s), its cost gates PASS. Suite: `bash Art/suite.sh terrain drivetrain grip mud surface track biome` 6 PASS, 1 FAIL: terrain, on step 11's held exit alone (5.9 s against 5.8 s down the ruts, asked 1.05x slower: the known flake); stage I's ridge shape passes in its new band (cv 0.64), the escape went 10.6 m forward and 6.0 m back, the rut mean read -30.8 cm. The biome test's hashes are unchanged (The Hide 0x977AF3A498E07815, the Proving Ground 0x7DBDFB11F2FD2CE1). No full suite this stage.
- **Unchecked.** Every look; the feel. The snow throw draws in the spray's mud pool. The mud strip's black patches beside
  the near lumps: not the mesh's cast shadows, cause unchecked.

## 70. Living mud LM3b: the God of War look on snow, the snow feel, the snow throw (2026-10-06)

docs/LIVING_MUD_PLAN.md stage LM3b (its italic note has every number), docs/LIVE_SNOW_DRIVE.md (how to see it). No game
and no foreign Unreal ran at any step, so the cost and the frame numbers are judged.

- **The snow feel (housekeeping 1).** `UGTTractionComponent::SnowBaseRow` (the Dirt row, `PM_Dirt`): inside a snow patch
  a tyre's own sinkage rolls at that row's `RollingResistance x (1 + SinkageDragScale x the sinkage fraction)` (0.06 at
  full sinkage) in place of the Snow row's (0.12); the surfaces table is untouched and the Snow row still applies
  outside snow patches. `FGTDeformProfile::SnowBellyDrag` (and the patch's copy) scales the belly's drag in snow (1 is
  LM3a's). Two tuning switches: `gt.Snow.Plough` and `gt.Snow.BellyDrag` (-1, the patch's own). Tuned at full throttle
  by the drive check's trials (each a pass 1 on a reset field): **SnowPlough 0.78, SnowBellyDrag 0** (LM3a: 0.35, 1.0).
  Every trial with any belly drag fell into a 1.7-1.9 km/h crawl through the drift (and stayed in it after); with none
  the drift runs 5.5 km/h. Pass 1: 9.3 km/h on the 35 cm outside the drift (A 40-66 m 10.4, B 85-110 m 8.4), 5.6 km/h
  through the drift, never stopped; pass 2 through the drift 28.4 km/h (5.10x).
- **Snow throw (housekeeping 2).** `UGTSprayComponent::SpawnThrown` takes the kind: a wheel in a snow patch throws through
  the Snow pool (white, the Snow kind's lighter fall), still carrying its volume onto the patch, whose clods are
  `M_GT_Clod_Snow`. Pass 1: 2,362 blobs, all through the Snow kind; 254 thrown clods live at the end.
- **M_GT_Snow** (`Art/Unreal/live_snow_style.py`), still a fresh copy of the live M_GT_Mud graph each setup (the WPO,
  the bicubic field read, the masked root and the hole untouched), all procedural: fresh snow albedo 0.85 with a blue
  shade tint where N.L falls, a normal from world-space value noise at 2, 12 and 60 cm (PCG hashes), roughness 0.7
  swung by the 12 cm octave; the glint (1 cm hashed world cells, a facet within 5 degrees of the sun's half-vector turns
  the normal to it and dips the roughness to 0.12; the sun is the Sky Atmosphere Light Direction node, light 0); packed
  snow (tracks 1) 0.72 x a grey-blue tint, roughness 0.45, the grain at 0.3, stage F's lugs at `LugTiltDeg` 30; walls
  (the field's slope 0.8-2.0 cm/cm) 0.64 x a blue-grey tint, roughness 0.55. **Substrate is on** (`r.Substrate=True`,
  the blendable GBuffer `ProjectGBufferFormat=0`): the surface feeds a Substrate Slab on the Front Material with
  Sub-Surface Type **Wrap** (a Diffusion slab exports as Default Lit in the blendable GBuffer; Wrap exports as the legacy
  Subsurface model) and an SSS MFP from `SnowSubsurfaceColor` (0.55, 0.70, 0.90): MFP = -0.01 / ln(colour) cm, since
  Substrate rescales the MFP by its 100 cm simple volume over the Slab's default 0.01 cm thickness. The first run took
  100 cm as the thickness (a near-white subsurface colour at any amount and a 10-16 level step at the patch's edge);
  fixed. The SSS fades in over the patch's 3 m taper.
- **The border.** `M_SnowLandscape` takes the same fresh-snow response (the same HLSL and numbers) at the patch box's
  border, fading over 3 m outside it and wherever its Snow layer lies (`SnowApron` and three wrappers on its Base Color,
  Normal and Roughness). The check: 0 dark and 0 sky-coloured pixels in the border box; 10-30 cm either side of the edge
  differ by +1.6 / +2.0 / +2.4 levels (R/G/B; the same with the patch's SSS off).
- **Pictures and samplers** (`check_live_snow_drive.py`): the LM3a three, `Snow_Glint.png` with `Snow_Glint_NoGlint.png`
  (846 pixels over 245 in the fresh-snow box against 0), `Snow_Border.png` with two diagnostics, and the cost.
- **Cost of the look** (one camera over the snow at 50 m; the patch wears M_GT_Snow, a M_GT_Mud instance with the same
  field parameters, or M_GT_Snow with SnowSSS 0; 5 s CSV profiles in the order snow, clay, no-SSS, no-SSS, clay,
  snow): GPU/Basepass 1.280 ms snow against 1.336 clay (-0.056 ms); the whole GPU +0.85 ms (frame +0.59), of which
  deferred lighting +0.39 ms with the snow material on whether its SSS is on or off, Lumen reflections +0.10, and Lights
  +0.12 / TranslucentLighting +0.13 with the SSS on only. M_GT_Snow 991 pixel instructions against M_GT_Mud's 462, 3
  samplers against 8. Settle and the clods on the strip PASS (pass 1 Settle 0.074 / 0.321 ms, clods 0.010 / 0.195).
- **Tests.** The six `GrandTour.Mud` and `GrandTour.Snow` tests PASS (the compaction row 0.8021, unchanged).
  Suite `terrain drivetrain grip mud surface track` (the final build): 5 PASS, 1 FAIL: terrain, on step 11's held exit alone (6 m in 5.9 s against 5.6 s down the ruts; asked 1.05x slower), the known flake, in the bog, which the snow changes do not reach; stage I's ridge PASSES (cv 0.64, width 50.5 cm, crest 6.00 cm), the rut mean -30.8 cm, the fords pass. drivetrain, grip, mud, surface (reachedSnow 1), track PASS. The full suite (`bash Art/suite.sh`, in the background): 27 PASS, 1 FAIL: terrain again on step 11's held exit alone (6 m in 5.4 s against 5.6 s down the ruts); biome's hashes unchanged (The Hide 0x977AF3A498E07815, the Proving Ground 0x7DBDFB11F2FD2CE1); spray PASS (maxSnowInSnow 95).
- **Unchecked.** Every look (the owner's gate). The feel. Why the snow material costs +0.39 ms in deferred lighting with
  its SSS off. The drift's bistable crawl (1.7-1.9 km/h or 5.5 km/h; nothing between seen).

## 71. Living mud LM3c: snow tread only in tyre paths, a crumbly plough berm, white snow clods (2026-10-06)

docs/LIVING_MUD_PLAN.md stage LM3c (its italic note has every number), docs/LIVE_SNOW_DRIVE.md (how to see it). No game
and no foreign Unreal ran at any step, so the cost numbers are judged. Nothing in the feel was retuned.

- **Tread only in tyre paths** (`FGTMudField`, snow only). `StampWheel` records the tick it wrote each capsule cell's tread
  (`TreadTickOf`); `PloughBelly` clears `PhaseTurns` to -1 on the cells it cuts that no tyre covered since the last plough,
  writes the belly's heading there and marks them scraped (`SnowMark`), then advances the tick. `AGTMudPatch::Upload`
  writes the tread texture's A on snow patches (`FGTMudField::TreadAlpha`): the lug strength where a tyre's phase is set,
  -1 where the belly scraped (0 on mud, as before). `M_GT_Snow` draws lugs only where A is over 0 and, where it is -1,
  faint scrape streaks along the heading (stretched world value noise 55 x 3 cm, `ScrapeLengthCm`, `ScrapeWidthCm`,
  `ScrapeSlope` 0.15, `ScrapeAlbedo` 0.03), the direction binned to 5 degrees so the streaks do not break at cell borders.
  Test: no phase in the 343 channel cells beyond any capsule's reach.
- **Broken lugs.** `FGTMudField::LugStrength` (snow only, static): value noise at 55 cm ranked into 0.25-1.0, and 20 % of
  the cells at 0 in patches (a second noise at 60 cm under its quantile). `LugTiltDeg` 30 is the peak.
- **The plough berm through the bank path** (`FGTMudField::bPloughBankPath`, on; off is LM3b's sine hump). A tyre's bank
  weight read at the cell's foot on the box's side: stage I's plateau with the width swing, the two along-stroke waves,
  `RidgeSideBias`, `RidgeNoise`'s clumps, and `LumpShare` of the deposit into the lump domes; no cap; the berm cells are
  marked and the tyres' stage H ridge smoothing leaves them alone. Snow's `RidgeWave` 0.6 and `RidgeNoise` 0.5
  (`SnowDefaults()`; the lips take them too). GrandTour.Snow.Compact's new car row (four tyres then the belly each 5 cm
  tick): the crest cv along the trench **0.779** against LM3b's 0.160 (asked at least 0.35), but through the lumps alone
  (0.215 with `LumpShare` 0), whose overflow over `LumpMaxCm` stacks single cells up to 93 cm over the snow top (59 cm on
  the strip after the talus); the far berm reads as a row of sharp peaks in `Snow_Trench_Close.png`. Open for the main
  session. The volume rows unchanged in substance (compaction 0.8022, LM3b 0.8021; the plough 0.3000); the mud CRC
  8e0aad06.
- **White snow clods.** `M_GT_Clod_Snow`: albedo 0.82, roughness 0.7, tint +-5 %, no freshness darkening, on M_GT_Snow's
  Substrate Slab (Wrap SSS from the snow's subsurface colour). The check measures it against the snow in
  `Snow_Trench_Close.png` (the clods' projected boxes, against the same frame with the clods hidden): 16 sunlit clods at
  0.916 of the snow round them (asked within 15 %).
- **The deferred lighting, diagnosed.** `UGTSubstrateInfoLibrary` (GrandTourEditor, new; the module now lists `RHI`)
  prints a material's compiled Substrate output. M_GT_Snow compiles as Single (SSS | MFPPluggedIn), M_GT_Mud as Simple on
  the legacy GBuffer pass-through. At run time the snow's pixels are Single only while its SSS is on (33 % of the frame);
  at `SnowSSS` 0 they are Simple like the clay's, yet RenderDeferredLighting is still +0.31-0.36 ms over the clay. The
  classification costs the sun's light pass about +0.09 ms with the SSS on; it is not the excess. Cause unchecked.
- **The check** (`check_live_snow_drive.py`, `TRIALS` False): the passes at the patch's own numbers, the berm's crest
  along the strip, the clod boxes and `Snow_Trench_Close_NoClods.png`, `Snow_Floor_Close.png`, `Snow_Classify_*.png`
  (`r.Substrate.ViewMode 4`) and a ProfileGPU dump per material between `LM3C_PROFILEGPU` log markers. Feel gates: pass 1
  9.8 km/h on the 35 cm, 5.5 km/h through the drift, no stop; pass 2 5.21x through the drift.
- **Tests.** The six `GrandTour.Mud` and `GrandTour.Snow` tests PASS. Suite `terrain drivetrain grip mud surface track`: 5 PASS, 1 FAIL: terrain, on step 11's held exit alone (6 m in 5.4 s against 5.5 s down the ruts; asked slower), the known flake in the bog, which the snow changes do not reach; stage I's ridge passes (cv 0.64, width 50.5 cm, crest 6.00 cm), the rut mean -30.8 cm; surface reachedSnow 1.
- **Unchecked.** Every look (the owner's gate). The berm's peaks (open for the main session). Why the snow material costs
  ~0.3 ms more in RenderDeferredLighting with its pixels classified Simple.
- **Follow-up (the main session's decision on the berm's peaks).** A lump's overflow over `LumpMaxCm` goes back into the
  stroke's bank, spread over the band cells that took the deposit by its plain weights (`FGTMudField::bLumpOverflowToBand`,
  every medium; the berm the same over its band; `DepositLump` keeps the same-cell rule), the volume exact. The berm's own
  `PloughLumpShare` 0.25 (`FGTDeformProfile`, the patch, the field) and, not a plan number, `PloughBankVariation` 0.4, its
  share of the bank's height swings. The car row: the crest cv 0.175 (LM3c first 0.779, LM3b 0.160), its 90th percentile
  1.40x its median (asked at most 1.3: FAIL, left failing), its highest 1.53x (asked at most 1.6: PASS), highest 29.5 cm
  against 93.7. The 90th-percentile row holds at no berm number: the lips' own lumps (0.5) under the berm read 1.32x on a
  uniform berm. On the strip the crest's highest is 31-32 cm (LM3c first 56-59), 1.79-1.80x its median. Mud: the Settle CRC
  row (no lumps) is 8e0aad06; with lumps the bog's banks change where a lump overflows (the Lumps test's narrow stroke
  27,627 cm^3; SoftShoulders cross-step 18.68 -> 18.83 cm; the five mud tests PASS; the live mud check OK). The dashes along
  the tyre slot in `Snow_Floor_Close.png` repeat at 8.5-9.5 cm along the travel: the tyre's lugs (`LugPeriodCm` 9), not
  cell steps. Feel gates hold (9.6 / 5.5 km/h, no stop, 5.19x).
  Tests: the five mud tests PASS; Snow.Compact FAILS on the 90th-percentile row alone. Suite `terrain drivetrain grip mud surface track` after the follow-up: 5 PASS, 1 FAIL: terrain, on step 11's held exit alone (6 m in 5.8 s against 5.6 s down the ruts; asked 1.05x slower), the known flake in the bog; stage I's ridge passes at cv 0.58 (0.64 before; asked 0.22-0.75), width 50.5 cm, crest 6.01 cm, the rut mean -30.9 cm; surface reachedSnow 1.

## 72. Living mud LM4: God of War snow - a 6.25 cm snow grid, crust plates, stepped walls, shards, a granular material, an uneven snow top (2026-10-06)

docs/LIVING_MUD_PLAN.md stage LM4 (its italic note has every number and the cell-unit table), docs/LIVE_SNOW_DRIVE.md (the
switch and the dials). God of War Ragnarok ran through the session: the build, the tests, headless Blender, the shard import and the
strip's setup ran; the drive check (the feel gates, the pictures, the FineGrid cost) and the targeted suite are OWED. The
snow's feel numbers are untouched (SnowPlough 0.78, SnowBellyDrag 0, sinkage 0.05 m at 0.05 m/s).

- **A grid per profile.** `FGTDeformProfile::CellCm` (12.5; snow 6.25) is the field's and the mesh's cell
  (`AGTMudPatch::MeshCellCm` follows the field). StampWheel's own cell-unit numbers are the profile's (`RidgeNoiseCells`,
  `SettleTileCells`, `FloorNoiseCells`, `PocketNoiseCells`, `TracksEdgeCells`), mud's by default; snow states each at
  6.25 cm to keep its cm (clumps 50 cm, the tile 2 m, the floor noise 62.5, the pockets 150, the tracks' edge 37.5), the
  lump sites 20 cm apart, the wall's fewest cells 1 (6.25 cm, so `RutShoulderCm` 10 is the wall). The bank clods' chance is
  per 12.5 cm cell's area (`FGTMudField::ClodAreaScale`, 1 on mud). `gt.Snow.FineGrid` 0 builds a snow patch at 12.5 with
  the cell numbers rescaled (`ScaleCellUnits`); read when the patches are built (restart Play, or the check's
  `UGTMudSubsystem::RebuildPatchesForTest`). Not a plan number: snow's `RidgeSmooth` 0 (stage H's 3-cell mean is not
  volume-conserving on the stepped lip: the compaction row 0.8115 with it, 0.8000 without). The mud field's CRC 8e0aad06.
- **Crust plates** (`FGTMudField::bLumpPlates`, snow): each lump site owns its Voronoi cell over the whole jittered site set
  (absent sites' cells are gaps); the held share lands flat on the plates by LM2a's normalisation and `ReshapePlates`
  re-levels each touched plate to a plane tilted 5-25 deg toward a hashed azimuth, clamped 0..LumpMaxCm, its volume kept
  (bisection); the berm's lumps the same. The tread texture's B carries the plate mask on snow (`PlateAlpha`).
- **A stepped wall line** (`WallStepMinCm` 3, `WallStepMaxCm` 8 over 15-30 cm segments): the capsule's half-width steps by
  a hash of the segment (the world axis nearer the stroke, the side, a 60 cm lane; three magnitude levels), read at the
  cell's own place along the line; inward the tyre's width still cuts to full depth. `WallDropShare` 0.15 of the segments
  drop their lip plate onto the trench floor beside the wall (exact; the cells marked `SnowMarkDropped`) with
  `FloorChunkChance` 0.18 of them leaving a floor chunk (a clod spawn, Source 3).
- **Snow shards** (`Art/Blender/build_snow_chunks.py`, `Art/Unreal/import_snow_chunks.py`, `Art/import_snow_chunks.ps1`):
  eight Voronoi cells of a 4-8 cm slab, 7.6-21.6 cm across, 144-252 triangles, flat shaded,
  `/Game/GrandTour/Mud/SnowChunks/SM_GT_SnowChunk_0..7`. A snow patch draws them in place of the clods
  (`AGTMudPatch::bShards`): the lip's at plate edges only, power-law 4-25 cm, yaw along the lip +-30, tilt 10-40, sunk 20-50 %;
  the floor's where a plate fell. `ClodsFromFloor`, `WallDrops`, `LipChunksQueued`, `FloorChunksQueued` readouts.
- **M_GT_Snow** (`live_snow_style.py`): cellular clumps at 1.5 and 6 cm with crisp creases and darkened gaps (fresh and
  packed, shared with the landscape apron), faceted walls and plates (3D Voronoi facets, the grain at 0.3), the plates'
  tops 0.76, and the shade dial `SnowShadeSaturation` 0.5 (half LM3b's on the four tints and the subsurface colour). 1,542
  pixel instructions (LM3c 1,056).
- **An uneven snow top** (`FGTMudField::SnowTopNoiseCm`, sd `SnowTopUndulationCm` 2.5 at 0.6-3 m) inside `SnowTopAt`, so
  the mesh's rest, the stamps' cut and the traction's snow ahead read one top; snow `FloorNoiseCm` 1.5.
- Tests: `& Art/mud_shape_test.ps1`'s run (7 of 7 Success; the wrapper expects the new GrandTour.Snow.GoW). GoW (LM3c ->
  LM4): plate edges 15.75 -> 41.50 steps of 2 cm per metre of lip; 74 plates at 5.1-25.0 deg (median 15.2), azimuths in
  all eight octants (resultant 0.147); the wall line's outline sd 2.70 / 1.65 -> 6.97 / 5.81 cm, 0 -> 21 % of stations
  stepping; no autocorrelation peak above 0.3 at lags 2-8 (a 36 m stroke less its 1 m moving average; the raw series shows a
  0.42 wiggle at lag 5 on the crest's slow decay, reported); chunks 48 = LM3c's 48 over a 30 m car, 33 % on the floor, sizes
  cv 0.574; the snow top's sd 2.53 cm over 20 m. Compact at 6.25: compaction 0.8000, walls 76.3 / 69.8 deg, taper, refill
  6.00 cm, plough 0.3000, the berm 1.15 / 1.28x (asked 1.5 / 1.6).
- The check (`check_live_snow_drive.py`) reads the patch's cell, adds `Snow_GoW_View.png` and `Snow_OnFoot.png` and the
  FineGrid pair (0, then 1) after the main session, each its two passes and two cost-camera profiles; not yet run.

## 73. Living mud LM4b: soft snow shape, crumbly per-pixel detail - continuous wall line, soft domes, rounded clumps, a snow-clump height map, an edge mask, a parallax experiment (2026-10-06)

docs/LIVING_MUD_PLAN.md stage LM4b (its italic note has every number and the sweeps), docs/LIVE_SNOW_DRIVE.md (the switch,
the dials, the texture). The owner's "the snow is a bit blocky": the shape soft and irregular, the crumbly detail moved into
the surface as God of War's is. God of War Ragnarok ran from 14:25: the builds, the bake, the imports, headless Blender, the
tests and the strip's setup ran; the drive check (the feel gates, the pictures, the parallax pictures), the FineGrid and
parallax cost and the targeted suite are OWED (LM4's owed items with them). The 6.25 cm grid and every snow feel number
stay; the mud field's CRC 8e0aad06.

- **A continuous wall line** (`FGTMudField::WallOffsetAt`): with `WallStepMaxCm` 0 the cut's half-width wanders by two
  octaves of smoothed value noise along the line, `WallWaveAmpCm` 1.0 at `WallWaveCm` 25 plus `WallWaveLongAmpCm` 2.0 at
  `WallWaveLongCm` 70 (a lattice row per wall side and 60 cm lane). LM4's segments carry only the drops now. The wall line's
  sd 3.19 / 2.52 cm, its largest station step 1.28 / 1.03 cm (LM4 16.57 / 14.99).
- **Soft domes** (`FGTMudField::bLumpSoftDomes`, the profile's; LM4's `bLumpPlates` off on snow): LM2c's domes on LM4's
  sites, radius 8.5 cm +-41 %, a skew of 2-10 deg (`LumpSkewMinDeg`/`MaxDeg`: the dome's W leans by tan(skew) per cm along a
  hashed azimuth over its height cap), and `ReshapeDomes` (the plates' `ReshapePlates` counterpart, through `ReshapeLumps`)
  re-shapes every dome a stamp or the plough touched to T x its kernel, volume exact, its peak at most
  `LumpHeightPerRadius` 0.30 x its radius (not a plan number: the softness; caps 1.9-3.6 cm). `LumpCapAmpPower` and
  `LumpCapRadiusPower` (0) scale the cap by the site's amplitude or radius (tried, not landed). The notch's ends feather over
  `WallDropFeatherCells` 2 (a 0-1 drop share per lip cell, `LipDropShare`). A drop-marked berm cell's lump share goes to the
  berm's band on the soft domes (it built a 41 cm tower in one cell). Lip chunks from the domes' edges, `ClodBankPerCm` 0.031.
  The tread texture's B on snow is the lumps' mask (`PlateAlpha` on either shaped mode).
- **Rounded clumps** (`Art/Blender/build_snow_chunks.py`): icosphere ellipsoids with 2-4 fracture planes pulled in,
  Laplacian rounding, three noise octaves, a flat bottom, smooth shaded; 5-18 cm across, 320 triangles each; the same
  `SM_GT_SnowChunk_0..7` names and import.
- **The snow-clump height map** (`Art/tools/bake_snow_detail.py`, numpy only): `Art/Textures/Snow/T_GT_SnowDetail.png`, a
  tileable 1024 x 1024 16-bit map of a 100 cm tile, R crumbs (1-4 cm clumps), G clods (6-15 cm), B both; soft blobs joined by
  a smooth maximum, clumped by a periodic density field (seam ratio 0.94-1.01), with a preview PNG and a JSON of its numbers.
  `Art/Unreal/import_snow_detail.py` / `Art/import_snow_detail.ps1`: `/Game/GrandTour/Textures/Snow/T_GT_SnowDetail`, linear
  (sRGB off), BC7, wrapped. The PNG is gitignored (`*.png`): the script regenerates it bit for bit (a fixed seed).
- **M_GT_Snow** (`live_snow_style.py`): the map tri-planar on the field's normal at 100 and 113 cm (`SnowDetailTileCm`; the
  60 cm grain octave picks between them), its layers' gradients bending the normal by `SnowDetailCm` 0.8 / 2.0 cm, the
  crevices darkening; the edge mask E (slope `SnowEdgeSlope` 0.35-1.2, the tracks' boundary, the lip band `SnowEdgeLipCm` 2
  or a lump) sets the gains: fresh `SnowDetailFresh` 0.35 / `SnowCavityFresh` 0.05, packed `SnowDetailPacked` 0.2 /
  `SnowCavityPacked` 0.04, E 1 both layers and `SnowCavityEdge` 0.3. LM4's cellular grain off (`SnowCellGrain` 0), its facets
  and plate albedo gone; `SnowEdgeDebug` 1 draws E. The apron (`M_SnowLandscape`) reads the map's fresh crumbs too
  (`APRON_DETAIL`), on the shared wrap sampler. 1,641 pixel instructions (LM4 1,542), 4 samplers.
- **Parallax, an experiment** (`gt.Snow.Parallax` -1/0/1, `AGTMudPatch` pushes it to `SnowParallax` when it changes): POM
  over B where E > 0.2 and a pixel spans under `SnowParallaxNearCm` 1.2, in a frame from the field's normal, 10 steps over
  2.5 cm, a linear refine; the slide moves every detail lookup. Off by default: no picture or cost could be taken.
- Tests (`GrandTour.Snow`; the Mud tests and CRC unchanged): 6 of 7 Success; GoW fails the lip crest cv row (0.297 / 0.192,
  asked 0.3; LM4 0.307 / 0.299; with no lumps the +Y side reads 0.153) - the softness row (steps over 3 cm 3.33 %, at most half
  LM4's 7.81 %) and it do not hold together at any setting the sweep tried. LM4's two blocky rows retired, its plate tilt rows
  reported. Compact: compaction 0.8001, the berm 1.27 / 1.41x.
- The check (`check_live_snow_drive.py`): `Snow_GoW_View`, `Snow_OnFoot` and the new `Snow_Edge_Close` (60 cm out from the
  -Y trench's outer lip, 30 cm up, along it) each with `_Parallax1`, `Snow_Edge_Mask.png`, and the parallax cost (the strip
  and the edge view, 0 / 1 / 1 / 0) before LM4's FineGrid pair; not yet run.

## 74. Living mud LM4c: snow piles, not walls - the talus per cell, delayed wall collapses, the berm in piles (2026-10-06)

docs/LIVING_MUD_PLAN.md stage LM4c (its italic note has every number and the sweeps), docs/LIVE_SNOW_DRIVE.md (the numbers, the
collapse pair). The owner's "the form of the snow is too uniform, and it sticks up way too much, those tall edges need to fall down
into piles". God of War Ragnarok ran through the session (and the Codex app ran two Unreal renders, waited out): the builds, the
tests and the strip's setup ran; the drive check (the feel gates, every picture, the collapse pair, LM4b's parallax pairs), the cost
and the targeted suite are OWED. The snow's feel numbers stay; the mud field's CRC 8e0aad06.

- **The talus per cell** (`FGTMudField::bCellRepose`, in Settle's pair): a pair takes the higher cell's talus - `LooseReposeDeg`
  **50** above the snow top (the berm, the lip) and on a collapse's pile (`SnowMarkDebris`), else the cell's static wall repose,
  `WallReposeDeg` **64** +- `WallReposeRangeDeg` 20 by two rotated octaves of world value noise at 40 / 80 cm ranked over the field
  (`EnsureSnowPiles`, built once per patch by `PrepareSnowPiles`). Snow's SetSeconds stays 0. Mud keeps ReposeDeg, bit for bit.
- **Delayed wall collapses** (`CollapseSegmentAt`, `ArmCollapse`, `FireCollapses`, `Collapse`): the wall in 30-80 cm segments (LM4's
  scheme: a hash of the segment, side and 60 cm lane); `CollapseChance` **0.2** of them collapse 0.5-3 s after the last stamp that cut
  them (a cell of the cut's outer 40 % beside the line lowered by 1 cm or more re-arms the timer; `SettleClockS`, the settle sub-steps,
  drives it, so the same stamps and dt give the same collapses). The top 30-60 % of the wall above the floor beside it, the lip
  included, comes off above a plane rising back at the loose repose from where the face crosses the cut level, the ends feathered
  over 2 cells, and lands exactly as a cone on the trench floor at the wall's foot (marked loose), with 1-2 clumps (Source 3).
  Readouts on the patch (`CollapsesFired`, `CollapseCm3`, `CollapseSegsArmed`, `CollapseClumpsQueued`) and the field's `CollapseLog`.
- **The berm in piles**: `PloughBandCm` **85**, `bPloughFallingProfile` (the plough's bank weight (1 - u)^`PloughFallPower` 0.5 from the
  wall out), and the plough's and the lips' bank weights times a cluster factor at the cell's foot on its line: `PileClusterMin` **0.08**
  .. `PileClusterMax` 1.8 by two rotated octaves at 100 / 250 cm, ranked and mapped by smoothstep (`PileContrast` 1). Volume exact.
- Profile, patch and test plumbing for every number (`FGTDeformProfile`, `AGTMudPatch::ApplyProfile` / `Init`, `ScaleCellUnits` scales
  `CollapseFeatherCells`); off by default, so a bog and a ford's bed are unchanged. `gt.Mud.Settle 0` stops the talus and the collapses.
- Landed against the block's numbers (35 / 60 / 0.25 / 0.2 / 70) on `GrandTour.Snow.Piles`' sweeps: the block's read the floor's
  debris 56 % and the crest cv 0.23 / 0.26. The floor and wall rows pull against each other through the wall's repose; the landing
  sits inside both, near both edges, and other noise (seeds 2-4) moves rows across their limits.
- Tests: `GrandTour.Snow.Piles` (new): the edge (berm crest) median / 90th percentile 10.56 / 16.20 cm against LM4b's 19.01 / 28.67
  (x0.56 / x0.57), piles 5.6 / 4.7 per 10 m (spacing cv 0.474), crest cv 0.356 / 0.360 (LM4b 0.266 / 0.293), the outer walls' cells
  57.2 % steeper than 55 deg (LM4b 100 %), the floor 29.4 % raised 2 cm (LM4b 0), 3.54 collapses per 10 m of wall 0.60-2.77 s after the
  cut (piles to 12.5 litres, 11.2 cm), the volume kept (0.16 cm^3), lip steps 6.16 % (at most 7.81), no pattern, deterministic.
  Compact's settled-wall row retired (reported 64.5 deg mean); its no-spike berm rows hold at 1.47 / 1.58x (asked 1.5 / 1.6); GoW's
  wall-line step 1.49 cm (asked 1.5) and lip steps 3.83 % (asked 3.94) - both moved by the lips' piles. **8 of 8 GrandTour.Mud +
  GrandTour.Snow Success.** The mud shape wrapper expects 8.
- The check (`check_live_snow_drive.py` / `.ps1`): the berm crest out to 250 cm, the collapses per pass, and the collapse pair
  (`UGTMudSubsystem::CutSnowTrenchForTest`: a fresh single-tyre cut at 90-99 m, 2.9 m to +Y; `Snow_Collapse_0s.png` and
  `Snow_Collapse_4s.png` from across its trench); not yet run.

## 75. Living mud LM4d: the belly's channel isn't flat - an undulating scrape, smear ridges, spill (2026-10-06)

docs/LIVING_MUD_PLAN.md stage LM4d (its italic note has every number), docs/LIVE_SNOW_DRIVE.md. The owner, driving LM4c: "the edges
look great, but the middle is still very perfectly flat". LM4c's edges are unchanged. No game ran: the drive check (the first since
LM3c, so it reads LM4, LM4b and LM4c too) and the targeted suite ran. The snow's feel numbers stay; the mud field's CRC 8e0aad06.

- **The undulating scrape** (`FGTMudField::BellyOffsetCm`): the plough's target over the ground +-`BellyUndulationCm` 2.5 by two
  value-noise octaves at `BellyWaveMinCm` 20 / `BellyWaveMaxCm` 60 cm across, `BellyStretch` 2.5x along the world axis nearer the
  heading (world-anchored: a heading-frame noise would swing with the yaw and the lowering-only cut would keep the deepest of each);
  under the belly's full width only.
- **Smear ridges** (`SmearRidgeCm`, `DepositChannel`): 20 cm world lanes cut into 30-80 cm segments (each lane its own phase),
  `SmearChance` 0.25 x 2 x a 120 cm bunching noise, 8-15 cm wide, 1-3 cm high; laid on the channel's cells as they leave the box
  (a 25 cm band behind it, each cell once: `SnowMarkSmeared`), out of the plough's return.
- **Spill** (`DepositChannel`): `PloughSpillShare` 0.15 of the side deposit back into the channel on the lump sites 30-55 cm behind
  the box, by kernel x cluster weight: LM4b's capped soft dome in LumpCm on a soft mound in HeightCm; `SpillClumpChance` 0.15 of
  the sites a snow clump (Source 4; the patch's `ClodsFromChannel`). The channel: scraped, never tyre-covered, between the innermost
  tyre-covered cells in the plough's reach. `PloughBermCm3` books the whole return. Readouts `SmearCm3`, `SpillCm3`,
  `SpillClumpsQueued` (field and patch).
- **M_GT_Snow** (`live_snow_style.py`): the edge mask at least `BellyDetail` 0.35 in the belly's channel; scrape streaks
  `ScrapeSlope` 0.3, `ScrapeAlbedo` 0.06 (LM3c 0.15 / 0.03). 1,642 pixel instructions.
- Profile, patch and test plumbing for every number (off by default: a bog's and a ford's bed unchanged).
- Tests: `GrandTour.Snow.Channel` (new): the channel floor's sd per 1 x 3 m window median 2.35 cm (LM4c 0), 2.89 smear ridges per
  metre (spacing cv 1.68), 11.2 % of the channel's cells raised 2 cm or more by the spill, the return whole (0.3000), the volume
  kept, no pattern. `Lm3cProfile` / `Lm4Profile` switch LM4c and LM4d off (GoW's LM4 lip baseline back to 7.81 %). **8 of 9
  Success: GoW's "LM4 chunks 20-40 % on the trench floor" reads 42 %** (21 lip + 15 floor; LM4c 29 + 15): the tyres roll 13 more
  cutting stamps with the ridges or the spill on, and the lip chunks' rolls hash that count. Piles' +Y crest cv at its limit
  (0.350). The mud shape wrapper expects 9.
- The check: `Snow_Channel_Close.png`, the channel's readouts per pass. Its results (the first check since LM3c): the drift pass
  2 / pass 1 4.31x (PASS); **pass 1 at 6.25 cm B 3.7 km/h, the 35 cm outside the drift 5.6 (asked 8-15: FAIL)**, at 12.5 cm 8.8;
  **Settle 1.51 / 5.67 ms mean / p99 at 6.25 cm (gate 0.3 / 0.7: FAIL)**, 0.40 / 1.46 at 12.5; LM4b's parallax base pass +0.11 ms;
  every picture written (the collapse pair, the parallax pairs, the edge mask among them). The targeted suite: 6 PASS, 0 FAIL.

## 76. Living mud LM4e: the snow's cost - quiet sleep, a fast sweep, per-tile uploads, a chunked LOD mesh, an opaque snow material (2026-10-06)

docs/LIVING_MUD_PLAN.md stage LM4e (its italic note has every number), docs/LIVE_SNOW_DRIVE.md (the switches, the owner's test
list, the cost table). The owner: "We need to optimize the snow A LOT", and the look and the feel must not change. Two profiles
ran (ABBA; Blender ran through parts of both), then the owner stopped timing runs: the later cuts are unmeasured.

- **Tools.** `Art/profile_live_snow.ps1` / `Art/Unreal/profile_live_snow.py`: pass 1 and 2 profiled (CSV: frame, threads, GPU by
  pass; Settle, upload, stamps, clods mean / p99 / max), each feature toggled alone standing and on pass 1, ABBA; the field's
  record and replay (`FGTMudField::FEvent`, `AGTMudPatch::SetRecording` / `StartReplay`, `UGTMudSubsystem::SetRecordingForTest`,
  `SaveRecordForTest`, `LoadRecordForTest`, `StartReplayForTest`): every outside call into the field (the traction's stamps and
  plough, the throw's landings, the patch's clock, settle and frame end) recorded as plain data and replayed frame by frame (the
  same work in any build) or all at once (the same snow for the before/after pictures; the replay's CRC matched the record's
  end). `Art/profile_live_mud.ps1`: the clay reference. `Art/tools/summarise_snow_profile.py` prints a run and compares its
  pictures with `Art/Export/LiveSnowDrive/BeforeLM4e`; `Art/tools/compare_test_rows.py` diffs two shape-test logs. New readouts:
  the stamp time (`GTMud/Stamp`, `GT Mud Stamp ms`), swept tiles, uploaded cells, drawn triangles.
- **Cut 1, `gt.Snow.QuietSleep`** (`FGTMudField::bSnowQuietSleep`): snow keeps no fresh sheen (M_GT_Snow draws none: the tread
  texture's B is the lumps' mask), so a still tile sleeps after its 0.5 s quiet instead of the sheen's 6 s fade, nothing is marked
  dirty for a fading sheen, and a sleeping tile that flux reaches takes a still tile's test.
- **Cut 2, `gt.Snow.UploadTiles`** (`TakeDirtyRects`, `AGTMudPatch::UploadRects`, `FGTMudField::EncodeTexels`): the dirty cells
  kept per settle tile and uploaded as one region per tile in one update per texture (not one box round them all); the texels
  encoded a row at a time with the per-cell checks hoisted (the same values).
- **Cut 3, `gt.Snow.FastSweep`**: a pair under the smallest talus any pair can take is passed over before its talus is looked up
  (exact without the ooze), four cells at a time with SSE as a conservative pre-filter (`Pair` still decides, in the scalar
  order); the apply passes over a listed tile no flux reached (snow has no set timers); no smear on snow (OffsetCm is not drawn
  there and nothing reads it back).
- **Cut 4, `gt.Snow.MeshLod`** (read when the patches are built): `AGTMudPatch::BuildChunks` / `UpdateChunkLods`: the snow mesh in
  24 chunks of 128 cells (8 m), each a component (culled on its own) with three sections, every vertex / every 2nd / every 4th of
  the grid (a chunk's last row and column kept), LOD 0 within `LodNearCm` 2000, 1 within `LodFarCm` 4000, else 2,
  `LodHysteresisCm` 150; `SkirtCm` 40 skirts on the inner chunk edges, facing out. `SetSurfaceMaterialForTest`,
  `SetSurfaceCastShadowForTest`, `SetSurfaceVisibleForTest`, `ForceChunkLodForTest` act on every chunk (the checks use them).
- **Cut 5**: M_GT_Snow opaque (`live_snow_style.SNOW_OPAQUE`; the copied mud root was masked with a mask of 1 since mud stage D);
  `MI_GT_Snow_Masked` overrides it back for an A/B.
- **Cut 6, `gt.Snow.FastMaterial`** (M_GT_Snow's `SnowFastPath` 1): the scrape streaks' noise only where their amount is over 0.
- **Measured** (in-session ABBA, before the stop): the pass-1 record replayed, cuts 1-3 off -> on: Settle 1.38 -> 0.84 ms mean
  (p99 4.79 -> 3.04), upload 1.52 -> 0.53 (p99 4.15 -> 1.62; 63,048 -> 14,044 cells a frame); alone QuietSleep -0.28 Settle /
  -0.21 upload, FastSweep -0.39 Settle, UploadTiles -0.61 upload; MeshLod on foot -1.29 ms GPU (shadow depths -0.75); opaque
  inconclusive. Pass 1 after cuts 1-5: Settle 0.381 / 1.735 ms (target 0.3 / 0.7: not met), upload 0.370 (0.2: not met), frame
  19.57 against the mud strip's dry crossing 18.76 (+2 allowed); the snow patch hidden -7.73 ms GPU against the clay bog's -3.69
  (+1 allowed: not met; the views don't cover the same pixels). Unmeasured: 2b, 3b, 6 and the final state.
- **Parity**: GrandTour.Mud + GrandTour.Snow 8 of 9, as before (GoW's chunk row, 42 %, failed before any cut); the mud CRC
  8e0aad06 and 126 of 127 rows to the digit; Piles' "the drive twice" CRC 7ad7b091 -> 30de74f6 (equal both times; cut 1). The
  pictures below the sky differ by 0.28-0.44 of 255; chunk seams add no dark or sky pixels; the feel: pass 1 9.3 km/h outside the
  drift, 5.1 in it, pass 2 3.86x.
- **Not done**: half-rate talus, a coarser quiet threshold, a fresh-cut band, ParallelFor (each changes the simulation or its
  sums), a shadow proxy (moves the trenches' shadow edges), the plan's look-changing material cuts, the stamps.

## 77. Living mud LM4f: the bigger snow cuts behind switches - a shadow proxy, a cheaper material, a fast settle, the stamps' noise from arrays (2026-10-06)

docs/LIVING_MUD_PLAN.md stage LM4f (its italic note has the rows), docs/LIVE_SNOW_DRIVE.md (the switches, and "How to test the
optimisation": each switch's look risk and its estimated saving). The owner: "dont do any timing runs. Do the optimization and I
will do the testing." So no timing, profile, drive or suite run: the build, the GrandTour.Mud + GrandTour.Snow tests and the
strip's setup only. Each cut LM4e left out (it can move the look or the settle) is in, behind a console switch, on by default; 0
gives LM4e's behaviour.

- **Item 1, `gt.Snow.ShadowProxy`** (`AGTMudPatch::BuildChunks` / `ApplySurfaceShadows` / `DestroyShadowMeshes`): per chunk a
  `SnowShadow_i_j` procedural mesh, the patch's grid every `ShadowProxyCm` 25 (every 4th vertex at 6.25 cm, the chunk's last row
  and column kept, no skirts: one spacing everywhere), hidden (`SetVisibility(false)`, `bCastHiddenShadow`), out of ray tracing and
  distance-field lighting, with the surface's MID (so the same WPO displacement from the field texture: updated with the chunks
  every frame). On: the chunks' `CastShadow` off, the shadow meshes' on; off: the chunks cast as LM4e's and the shadow meshes are
  not in the scene. The switch is read every tick; `SetSurfaceCastShadowForTest` / `SetSurfaceVisibleForTest` /
  `SetSurfaceMaterialForTest` act on both. `ShadowProxyTriangles` reads the shadow meshes' triangles. Only with `gt.Snow.MeshLod 1`.
- **Item 2, `gt.Snow.FastMaterial 2`** (M_GT_Snow's `SnowFastPath`, default now 2; `-1` takes it; 1 is LM4e's, 0 the full
  material; `live_snow_style.FAST_DETAIL_HLSL` and SNOW_HLSL): the detail map's projection top-down only where the surface's normal is
  within 30 deg of up (tri-planar on walls); its weights scaled by `saturate((E - 0.05) / 0.05)` (none at E 0.05 or under: the loop's
  existing 0.01 branch skips them); the second tiling's mix scaled by `saturate((E - 0.2) / 0.1)` (one tiling under E 0.2); the glint's
  gain faded by `1 - smoothstep(1200, 2000, depth)` and the glint block skipped where its gain is 0; the SSS amount faded by
  `1 - smoothstep(2000, 3500, depth)` (no SSS MFP: Substrate Simple). The depth is a new `SnowCamDepth` input from a PixelDepth node.
  The two fades in E (0.05-0.10, 0.2-0.3) are the agent's, so neither cut draws a line where it starts.
- **Item 3, `gt.Snow.FastSettle`** (`FGTMudField::SnowFastSettle`; the console variable lives in GTMudField.cpp and a new field
  takes it as its default, so the CPU tests follow it; the patch pushes it every tick): 1 = the talus's sub-step `1/FastSettleHz`
  (15 Hz) instead of `SettleStepS` (1/30; SlumpK doubles, under its 0.2 cap at snow's SlumpRate 2); band-only wake (`WakeTiles` stamps
  `TileWriteS` on every tile within `FastSettleBandCm` 200 of the cells any write touched; each sub-step an awake tile older than
  `FastSettleBandS` 3 s and not by a pending collapse - a box round each pending segment's line point, its face and half its length,
  plus the band - sleeps as a quiet tile does; flux still reaches it); the parallel sweep and apply (`SweepTile` /
  `ApplyTile`: every swept tile's pairs in a ParallelFor, `PairQ` reading only heights, lumps, set timers and the static talus, each
  tile logging its flux and wakes in its own serial order (`FFluxLog`), the logs then added in the work list's order - the serial
  sweep's exact sequence of additions - and each tile's apply at once, its dirty box marked in the list's order). 2 = the parallel
  part alone; 3 = parallel + 15 Hz, 4 = parallel + the band (each half alone, for the A/B). Mud: always the serial path.
- **Item 4, the stamps' static noises** (no switch: exact): `FGTMudField::NoiseCells` / `NoiseAt` / `PrepareStampNoise` - eleven
  slots (the station's wave, long wave, side and slump noise; the floor's pocket and floor noise; the band's clumps, clods, clod
  sizes and tracks' edge; the lip chunks' cluster noise), each `CellNoise(X, Y, wavelength, salt)` per cell for the field's size and
  seed, keyed on every input (compared exactly; a stale slot rebuilds), built in a ParallelFor over rows when the patch starts
  (`AGTMudPatch::Init`, after `PrepareSnowPiles`). StampWheel and PloughBelly read them (a foot cell off the grid computes as
  before); the piles' `EnsureSnowPiles` (an 18-number key compare) once per stamp instead of per lip or berm cell
  (`PileFactorReady`). Reading the stamp loop: per stamp some 500-800 lattice noises (the station's 4 at every change of foot cell,
  one to three a row; 2 per floor cell; 3-4 per lip cell), each 4 integer hashes and a smoothstep blend; what is left is
  WallOffsetAt per lip cell (its foot moves with the stroke, so not a per-cell static), the dome re-shapes and the clod rolls.
- **Item 5**: GrandTour.Snow.GoW's chunk floor share re-based 20-40 % -> 20-45 % (42 % failed identically at LM4e's own baseline:
  13 extra cuts shift the hash rolls), the reason in the test's comment.
- **Tests** (no game ran; a foreign UnrealEditor - the Codex app's Benmore setup - came and went and every run waited for it):
  FastSettle 0: 9 of 9 Success, 125 of 127 rows identical to LM4e's final log to the digit, CRCs included
  (mud 8e0aad06; Piles' drive twice 30de74f6 / 30de74f6), the two moved rows item 5's (GoW Fail -> Success, its chunk row's "asked
  20-40 -> 0" -> "20-45 -> 1" at the same 42 %): item 4 and the restructured serial settle are exact. FastSettle 2: all 127 rows as
  FastSettle 0's (the parallel half is bit-identical). FastSettle 1, the default: 8 of 9 - GrandTour.Snow.Piles FAILS its outer-wall
  row (62.3 % of the outer walls' cells over 55 deg, asked 15-60; LM4e 57.2), 29 rows moved (the plan's LM4f note has each, before and
  after; e.g. the floor raised 28.0 -> 26.5 %, piles 5.3 -> 4.7 per 10 m, smear ridges 2.89 -> 2.53 per m, the drive twice CRC
  cf3cf299 / cf3cf299, equal). Diagnostic values 3 (15 Hz alone) and 4 (the band alone): 4 fails the same row (62.7 %), 3 keeps it
  but tips the berm crest cv to 0.361 / 0.350 (asked at least 0.35; LM4e 0.362 / 0.350). Nothing retuned; the main session decides.
- **Setup**: `& Art/setup_live_snow_drive.ps1` LIVE_SNOW_SETUP_OK: M_GT_Snow and M_GT_Clod_Snow 0 compile errors, M_GT_Snow 1,673
  pixel instructions (static, every branch), Substrate Single [SSS|MFPPluggedIn] as before; the editor's known shutdown fault
  (-1073741819) after a fresh ok report.
- **Unchecked**: every cost (no timing ran: the savings in docs/LIVE_SNOW_DRIVE.md are estimates from LM4e's before profile), every
  look (no picture ran: the shadow proxy's shadow edges, the level-2 material, the patch's edge against the apron), the feel with
  FastSettle 1 (the traction reads the field).

## 78. Living mud LM5b phase B: four churned-bog variants per route section - texture arrays, one-layer mud, L_MudVariants (2026-10-06)

docs/LIVING_MUD_PLAN.md stage LM5b (its italic note), docs/MUD_VARIANTS.md (how to pick, the looks and numbers, the strip,
re-importing), docs/LIVE_MUD_DRIVE.md ("The one-layer mud"). The owner: the ruts the same colour and texture as the rest of the
mud, only a little wetter; four variants of the approved wet churned bog, each with its own look and feel, per route section.
Phase A (commit 268b811) baked the sets; this is phase B. It replaces LM5's original phase B: no churn channel, no clay/churn
layers. No game and no foreign Unreal ran at any step; no cost or timing was measured (the owner tests performance).

- **Data** (`GTTerrainGenerator.h/.cpp`): `EGTMudVariant` {Standard, Firm, Deep, Stony} (the arrays' slice order);
  `FGTRouteSection::MudVariant` (default Standard); `FGTDeformProfile` gains `bScalesRows`, `MaxSinkageScale`,
  `SinkageRateScale`, `FrictionScale`, `WaterTableOffsetCm` (identity defaults) and `MudVariantDefaults(v)` on the
  SnowDefaults pattern (the table: Firm sinkage x0.6, RecoverShare 0.25, LumpShare 0.25, ThrowMax 0.3, friction x1.1; Deep
  x1.5, 0.55, 0.35, 0.6, water table +10 cm, x0.9; Stony x0.8, 0.3, 0.2, friction x1.15; the three shares start from
  `AGTMudPatch`'s defaults, so Stony's ThrowMax is the bog's 0.5). `GTTerrain::MudVariantProfile(v)` (built once; null for
  Standard) and `DeformProfileFor`: a Mud section on ByKind takes its variant's profile, Standard none ("today's path
  exactly"); Mode On is the section's own full profile, Off none.
- **The patch** (`GTMudPatch.h/.cpp`): `ApplySection(Spec, Section)` - the water table, the variant (Mud only), the profile, in
  BuildPatches' order (the subsystem calls it). `ApplyProfile` copies the scales and adds the water-table offset on every
  profile (identity on a ford's and snow's); with `bScalesRows` it sets RecoverShare, LumpShare and ThrowMax and returns, so
  a variant's patch stays a bog's (bHasProfile false: the rows and the Mud/Bog tag gate, the 12.5 cm grid, every other bog
  number). `MudVariant`, the three scales and `ClodMaterialInstance` are BlueprintReadOnly. The mesh's `M_GT_Mud` instance
  takes `MudVariant`; off Standard (and off snow) the clods get one `M_GT_Clod` instance per patch with it, bank and thrown alike.
- **The subsystem** (`GTMudSubsystem.cpp`): `ApplySection` in BuildPatches; a variant's patch keeps the subsystem's cell;
  the log names the variant and its numbers; `MPC_TrackPaint` `PatchVariant<slot>` (written only where the collection has
  it) beside each `Patch<slot>` box - the boxes' four components are all used, so the variants are four new scalars.
- **The traction** (`GTTractionComponent.cpp`): inside a patch, for a wheel on the Mud or Bog row of a bog's patch or on a
  profiled patch, the sinkage cap and rate x the patch's scales and the wheel's `FrictionScale` x its friction scale. The
  friction goes on FrictionScale, not SurfaceFriction: the Chaos friction circle (via the wheel multiplier), the slip graph
  (SlipGraphScale x FrictionScale) and the drive cap (SurfaceFriction x FrictionScale) all move by exactly the scale, as for
  a row with that much more Friction; on SurfaceFriction the drive cap would have taken it twice. Every scale is 1.0f off a
  variant, an exact multiply.
- **The arrays** (`Art/Unreal/import_mud_variants.py`, `& Art/import_mud_variants.ps1`, new): the sixteen PNGs into
  `/Game/GrandTour/ArtTests/MudStyle/Variants/` and four `Texture2DArray`s `TA_MS_Bog{Color,Normal,Rough,Height}` (Color sRGB
  BC1, Normal BC5, Rough and Height linear TC_Masks; wrap; World group; 2048). **Route: arrays, no fallback.** Python makes
  them (Texture2DArrayFactory) and its `set_editor_property('source_textures', ...)` alone gave 4 slices of 2048 x 2048 each;
  `UGTMudArtLibrary::BuildTextureArray` (`Terrain/GTMudArtLibrary.h/.cpp`, new, editor-only body) then rebuilds the source
  from the slices on every run, so a re-import of revised bakes is never stale, and `TextureArraySourceSlices` checks it.
- **The live material** (`Art/Unreal/live_mud_style.py`): `M_GT_Mud` one layer - the variant's slice (input `MudVariant`)
  tri-planar (pow 6), the top face at two tilings that share no repeat (300 cm square, 430 cm turned 37 deg) height-blended
  (`BogBlendSharp` 0.2) by two octaves of world value noise (`BogMixCm` 260), the walls one tiling; unwrapped uvs with
  explicit gradients (SampleGrad). A rut differs only by its shape, `FreshWet` **0.3** (was 0.6; only ever glossier), the
  weather's wetness (the old terms) and the rut water. Gone from the mesh: the worked-clay bake, the 0.88 matte crests, the
  Bog row's 15 % darkening. The far gloss fade (static switch `FarGlossFade`, on): roughness toward 0.65 from 6 to 12 m. The
  landscape's mud block: the clay outside (bit for bit where the apron is 0); round each live patch's box (`Patch0..3`) its
  slice (`PatchVariant0..3`) over a 300 cm apron, the bog samples behind a branch (gradients from outside it), new outputs
  Apron / ApronColor / ApronNormal / ApronRough. `live_landscape(path)` builds a strip's own landscape material (L_MudDrive's
  `M_LiveLandscape`, L_MudVariants' `M_VariantsLandscape`): its apron follows the live boxes (it was the clay in two boxes
  measured on L_MudDrive), in the variant's colour, normal and roughness. `M_GT_Clod`: the arrays' colour and normal at its
  150 cm scale, the slice from `MudVariant`. `ensure_patch_variants` adds `PatchVariant0..3` to `MPC_TrackPaint`.
- **The strip** (`Art/Unreal/setup_mud_variants.py` + `.ps1`, `check_mud_variants.py` + `.ps1`, new): `L_MudVariants`,
  0-215 m along +X, Firm 30-55, Standard 75-100, Deep 120-145, Stony 165-190 m, 20 m gravel gaps (box gaps 6.4 m, so the 3 m
  aprons never meet), no ford, the car at 5 m, winch posts past each section, 13,681 tussocks. The check: one dry crossing at
  full throttle in low range with the diff lock, completion, per section the mean speed and the largest and mean sinkage, then
  per section an on-foot picture and a close-up; no CSV profile, no stat readout.
- **Runs**: build exit 0 (93 s, no warning in the changed files); 10 of 10 GrandTour.Mud + GrandTour.Snow tests Success, mud
  CRC **8e0aad06**; GrandTour.Mud.Variants (new) - each variant's profile reached its patch as written (the plan's note
  has the rows); the import OK; `& Art/setup_live_mud_drive.ps1` failed once - `M_GT_Clod` sampled the arrays with `.Sample`,
  which a ray-tracing hit shader rejects ("Opcode Sample not valid in shader model lib_6_6(closesthit)"); `Texture2DArraySample`
  (Common.ush: mip 0 there) fixed it - then OK, every material 0 compile errors; `& Art/setup_mud_variants.ps1` OK;
  `& Art/check_mud_variants.ps1` OK.
- **The drive**: completed, 200.06 m in 84.6 s, lateral 0.51 m. Firm 32.2 km/h, sinkage max / mean 24.0 / 18.8 cm; Standard
  24.4 km/h, 40.0 / 32.8; Deep 1.8 km/h (slowest 0.04 m/s), 60.0 / 59.4; Stony 22.6 km/h, 32.0 / 26.7.
- **Suite** `terrain drivetrain grip mud surface track`: 5 PASS, 1 FAIL - terrain on its bog escape (forward 6.9 m in 12 s,
  asked at least 8 m; fastest 103 cm/s); the one rerun PASSED (8.3 m, 115 cm/s; LM4d's run read 8.5 m). The Hide's bog is
  Standard, whose numbers are multiplied by exactly 1.0f, so the change cannot move it; the gate sits at its edge.
- **Unchecked**: every cost; the far gloss fade on/off; the apron in a border or top-down picture; L_MudDrive and The Hide in
  pictures (they wear the Standard bog everywhere in the patch now); the wet look.

## 79. MudRunner MR1: mud leaves the bog - carried tracks, splats, muddy grass (2026-10-08)

docs/MUDRUNNER_LESSONS_PLAN.md MR1 (its italic note), docs/MUD_VARIANTS.md ("Carried mud, splats, muddy grass"). The owner:
lessons from MudRunner, the world reacting to mud first. Wheels carry mud out of the bogs as broken, thinning tracks; thrown
mud splats the ground and rocks and posts instead of vanishing; grass by the tracks gets muddy at its foot. No cost or timing
was measured (the owner tests performance); every feature has a switch, on by default.

- **The load** (`GTTractionComponent.h/.cpp`): `FGTWheelTraction::MudLoad` 0..1 and `UGTTractionComponent::StepMudLoad` (static,
  `FGTMudLoadStep`, so the tests drive it without a car). On the Mud or Bog row inside a mud patch it rises at `MudLoadRate` 0.6/s
  x (0.5 + sinkage fraction) x (1 + slip share); in a snow patch it is 0; in water over `MudWashDepthM` 5 cm it halves every
  `MudWashHalfM` 2 m of ground; elsewhere every `MudShedHalfM` 15 m. The ground covered is the chassis's own speed x the tick,
  under 20 cm/s counting as standing: the contact point's movement, then the velocity at the contact, both shed a parked car's
  load (0.7 -> 0.4 over the check's 45 s of pictures). Nothing in the physics reads it.
- **The track paint** (`GTTrackPaintSubsystem.h/.cpp`): **RT_TrackPaint stays RGBA16f**; R is the ruts exactly as before; G is
  mud coverage, B its wetness. Until MR1 a rut stamp added its amount to R, G and B alike (G and B unread copies) and the decay
  multiplied all three by R's factor; now a rut stamp adds to R alone and the decay is one modulate draw (R's factor, G's, B's),
  R's clock and factor bit for bit as before. A blot sets G toward its coverage and B toward its wetness under the atlas mask:
  a modulate pass by (1, 1 - mask, 1 - mask) then an additive pass of (0, mask x coverage, mask x wet), so neither passes 1
  (both from brush textures built at load from `GTMudBlots.inl`, 4 x 4 tiles of 32 px). G fades with a 600 s time constant
  (`MudFadeSeconds`, every `CoverDecayInterval` 4 s, so each half-float step is several units), B with 90 s (`MudDrySeconds`,
  every 1 s). A 512-cell CPU grid (25 cm) mirrors G and B, shifts with every recentre, and stops its clocks when it is empty.
  `AddCarriedMud(State, Start, End, Width, Load)`: a blot every 0.45-1.0 tyre widths at a full load (x 1/sqrt(load) as it falls,
  at most x 3.3), its square 1.8-2.8 widths across x (0.55 + 0.45 load) (1.1-1.9 read as two thin dotted lines in the first
  pictures: the atlas blots fill about half their square), turned at random, a random tile, jittered 0.3 widths across; G toward
  0.8 x load, B toward 1; nothing at or under 0.02. `AddSplat(Point, Radius, Seed)`: a random tile reaching Radius, G toward
  0.9. `SampleCoverage`/`SampleWetness`, `ReadRenderTargetMud` (the GPU's G and B, the check's mirror test). MPC_TrackPaint's
  `MudCover` (gt.Mud.Carry or gt.Mud.Splats) and `GrassMud` written when they change. The pawn (`GTCarPawn.cpp`
  `PaintTracks`) lays each wheel's carried mud outside every patch with its own stroke state (seeded per wheel).
- **Splats** (`GTMudSplatSubsystem.h/.cpp`, new; `GTSprayComponent.cpp`): a volume-carrying throw blob's path is line-traced
  (world static and dynamic, the owner ignored) from where it was last traced, at most `MaxTracesPerFrame` 64 a frame across
  every car (a refused blob traces the longer path next frame). Outside every patch: a landscape hit is a track paint splat
  (2-3 x the blob's radius), a hit inside a patch's box after all lands there as before, a static mesh hit is a pooled deferred
  decal. **Inside a patch's box too** (beyond the plan's "path leaves every patch", 2026-10-08): only a static mesh takes it
  there, the ground being the field's, because the box reaches 2 m past the mud and every post or rock beside a section - the
  winch posts included - stands inside one. Decals: at most `MaxDecals` 96, the oldest out, each with its own instance of
  `M_GT_MudSplatDecal` (Tile, SpawnTime, SizeCm), projected along -normal and turned at random, hidden after 600 s; not on a pawn,
  a simulating body, a water sheet or a patch's own mesh and clods. The blob still counts as lost to the fields (LM2a's books)
  and as splatted (`GetThrowSplattedCm3`, `GetThrowBlobsSplatted`). `TraceSplat` is the check's synthetic blob path.
- **The atlas** (`Art/Blender/build_mud_splats.py`, new, headless numpy + one Cycles preview, 11 s): 16 tiles, 2048, 4 x 4 of
  512: 7 lumpy blots (a drawn-out or kidney core with 3-6 lobes and a few droplets clustered on one or two sides), 5 splatters (a
  smaller core, thick arms and 22-44 droplets flung in 2-3 sectors, smaller and sparser outward), 4 drag smears (overlapping
  lumps on a path bending under 15 degrees, thick at the head, breaking into beads at the tail). Outlines from a few random
  harmonics and a light warp (under 3 % of the tile, so nothing flows); domes with lumps and a crumb grain; every blot inside
  0.88 of its tile's half size (outermost 0.589-0.878). Mask (8-bit), height (16-bit, one scale), DirectX normal, a 2048
  tileable car-space splatter for MR2 (2,299 droplets in clusters, 105 short drips, 16.8 % covered), the manifest (the Standard
  bog's mean linear colour 0.0705 0.0401 0.0186) and `Source/GrandTour/Terrain/GTMudBlots.inl` (the mask at 32 px a tile: re-bake,
  then rebuild).
- **Materials** (`Art/Unreal/mud_cover.py` + `setup_mud_carry.py` + `Art/setup_mud_carry.ps1`, new): the four PNGs into
  `/Game/GrandTour/Mud/Splats` (TC_Masks / TC_NormalMap); `MF_MudCover`: where G is over 0 on up-facing ground (`MudCover` on),
  the Standard bog slice (TA_MS_Bog* slice 0, top-down at 300 cm) by `smoothstep(0.15, 0.35, G x (0.25 + 1.5 bog height))` (0.30
  / 0.50 hid a 0.4 load's track), B from dried (x1.45, matte 0.88) to wet (x0.78, glossy 0.32); the inputs pass through
  unchanged where it is 0. It sits in front of the MF_Weather call's BaseColor and Roughness (so every master still ends in
  MF_Weather and rain wets the mud) and on MP_NORMAL (`TangentNormal`, a static bool, picks the space): in `M_GT_Environment`
  (tangent), `M_GT_Landscape`, `M_LiveLandscape`, `M_VariantsLandscape` (world); `live_mud_style.py` re-splices it whenever it
  rebuilds a landscape. `M_GT_MudSplatDecal` (deferred decal, translucent - Substrate's grey transmittance; the blend set before
  the domain). Grass: `GrassMud:surface` behind the static switch `GrassMud` in `M_TS_Grass` (the strips' tussocks; base and
  subsurface) and `M_GT_FoliageCard` (The Hide's L3 cards, before its weather call): G at the blade's own XY (the tussocks are
  1-2.5 m clumps, so the instance's centre would mud a whole clump or none), the lower 18-30 cm by instance (about 30-50 % of
  the 60 cm mean tussock) x (0.55 + 0.45 G) with a ragged line and a speckle above, toward dried mud (the Standard mean x 1.6).
  The Hide's other grass is the OW vendor grass under the LGT_GT types (left alone: the OW content stays untouched), and the
  landscape's RVT output takes its colour before the cover, so grass tinted from the RVT does not see the mud.
- **Found and fixed (LM5b)**: the strips' `LiveApronRoughness` read the weather call's first output (BaseColor) as `Old`, so
  their ground roughness outside the aprons was the colour's red channel (about 0.1-0.3): tussocks mirrored in the gravel
  (Carry_Grass and Splat_Post of the first run; a T3D export showed the pin). `live_landscape` now wires the weather's Roughness
  (on a rerun too); after it the ground showed no reflections. Possibly the cause of LM5b's unchecked "pale bluish ground".
- **Switches**: `gt.Mud.Carry`, `gt.Mud.Splats` (also every trace), `gt.Mud.GrassMud` (1 by default), the material static
  switch `GrassMud`.
- **The test** `GrandTour.Mud.Carry` (new, `GTMudCarryTests.cpp`, CPU): the rise 0.600 / 0.600 asked (1 s at sinkage 0.5; 0.5 s
  at full slip); the shed 0.498 at 15 m, 0.248 at 30 m; the wash 0.500 after 2 m in 10 cm of water, 3 cm sheds as firm ground
  (0.912); snow 0, airborne kept; a 50 m exit at 8 m/s from a full load: 157 blots, G by 10 m bin 0.567 / 0.179 / 0.086 / 0.045
  / 0.028, gaps (G under 0.02) 45.0 % of 200 cells (0 / 17 / 22 / 24 / 27 of 40 by bin), the ruts' R untouched; a 60 cm splat: 7
  cells inside, 0 outside, the farthest 53.0 cm; G to 1/e at 598.0 s (600), B at 90.0 s (90); gt.Mud.Carry 0 lays nothing.
- **Runs**: the bake OK; build exit 0 (no warning in the changed files); 11 of 11 GrandTour.Mud + GrandTour.Snow tests Success,
  mud CRC **8e0aad06** (after each change); `& Art/setup_mud_carry.ps1`, `& Art/setup_live_mud_drive.ps1`, `& Art/setup_mud_variants.ps1`
  OK, no compile failure but LM5b's known intermediate M_GT_Clod warning. L_MudVariants gains `SplatPost_Deep` (a pale 1.6 m
  post at 121.6 m, 4.2 m left, Deep's left edge). The check (`check_mud_variants.py`, an MR1 phase after its pictures):
  - **clean run** (no game, carried blots 1.1-1.9): completed, 200.1 m in 82.3 s. Loads 0.48 / 0.47 / 0.55 / 0.52 at the stop
    (1.0 through Stony, shedding from the section's end); the track paint from 197 to 221 m per side, per 5 m: left 0.299 /
    0.162 / 0.052 / 0.015 / 0.018 (gaps 59.8 %), right 0.162 / 0.243 / 0.026 / 0.030 / 0.063 (57.7 %); the GPU's G at the CPU's
    best cell of each 5 m 0.457 / 0.195 / 0.277 / 0 / 0 (CPU 0.557 / 0.442 / 0.277 / 0.226 / 0.163) and 0.505 / 0.238 / 0.274 /
    0.176 / 0.181 (CPU 0.501 / 0.420 / 0.284 / 0.202 / 0.181); the verge drive reached it, 8 of 17 wheel points with mud, mean G
    0.169 (GPU 0.267); the spin-up threw 484 blobs, 2 splatted SplatPost_Deep (2 decals); the whole run 1,248 carried blots, 213
    landscape splats, 208,959 traces, 77,370 refused by the cap.
  - **with GoWR running** (the owner's override; carried blots 1.8-2.8): the drive crawled (Firm 27.4 s, then 65.6 s, against
    2.9 s) and timed out in Standard at 98.96 m, then at 97.35 m on the one rerun; the MR1 pictures of those runs are not the
    carried mud's; the first's spin-up made 30 landscape splats and no decal, and its 24 synthetic paths all splatted the post;
    the rerun's 2 natural decals drew as one black, hard-edged square on the post.
- **Pictures** (`Art/Export/MudVariants`, the clean run): `Carry_Exit.png` - from 3 m behind the parked car at 223 m looking
  back: the dark Stony patch and its ruts mid-frame, and from it two thin dotted tracks of small dark specks running toward the
  camera over the pale gravel, thinning out by mid-frame, a few lone specks nearer; `Carry_Grass.png` - tussock clumps filling
  the frame and Stony's pebbled bog bottom right: no mud on blade feet or between the clumps that I can point to; `Splat_Post.png`
  - the pale post at Deep's edge with two dark-brown irregular splats on its face toward the car (a lumpy blot about 60 % down
  with a droplet above it; a small speck higher at its right edge), the glossy lumpy Deep bog round its foot.
- **Suite** `terrain drivetrain grip mud surface track` (GoWR running; a foreign Unreal - the Benmore import and review - ran
  beside it unseen, my mistake): 5 PASS, 1 FAIL - terrain's bog escape (forward 7.2 m in 12 s, asked 8 m; LM5b's 6.9 then 8.3 m).
  The terrain rerun alone (GoWR running, no foreign Unreal): PASS, escape forward 9.0 m in 12 s, the held 30-degree exit slower than down the ruts.
- **Unchecked / owed**: the carried tracks at 1.8-2.8 and the close grass camera in a clean picture (the GoWR runs never reached
  Stony); muddy grass in any picture; the black decal square; The Hide (M_GT_Landscape, M_GT_FoliageCard) and L_MudDrive in
  pictures; the wet-to-dry look over time; every cost (the trace count is high: the cap refused 77,370 in one run).

## 80. MudRunner MR2: a muddy vehicle - tyres, mud line, spin fling, splats, wet/dry, wash; MR1 polish (2026-10-08)

docs/MUDRUNNER_LESSONS_PLAN.md MR2 (its italic notes), docs/MUD_VARIANTS.md ("The muddy car (MudRunner MR2)"). The owner: the car
gets muddy as MudRunner trucks do, after MR1's carried mud is polished. No cost or timing was measured (the owner tests
performance; the per-second trace counts below are functional readouts, not timings); every feature has a switch, on by default.

### MR1 housekeeping

- **No beads.** `UGTTrackPaintSubsystem::AddCarriedMud` stamps by distance with overlapping blots: a blot every `CarrySpacingMin..Max`
  0.3-0.6 x the smallest blot's reach at the load (so at most 0.6 of any blot's radius; MR1: 0.45-1.0 tyre widths x 1/sqrt(load)),
  its size, turn, tile and across offset jittered as before; the strength along the track follows the stroke's own noise
  (`CarryStrengthAt`: two hashed value-noise octaves at `CarryNoiseLongCm` 230 and `CarryNoiseShortCm` 110, features of about
  1-3 m, through a soft threshold rising from `CarryGapAtFull` 0.15 to `CarryGapAtEmpty` 0.5 as the load runs out, `CarryGapSoft`
  0.15); under it no blot is laid (a gap place, `GetCarriedGapCount`). `FGTMudCarryState` keeps the stroke's ground and noise key
  (the pawn per wheel). The dotted look had a second cause in the ground material: `MF_MudCover`'s edge was
  `g x (0.25 + 1.5 x the bog's height)`, so a track's moderate G passed only on the bog's lumps - rows of small dark specks however
  continuous G was. Now `g x (0.5 + the height three mips down + 0.3 x (the height - 0.5))` (`mud_cover.py`): ragged in
  metre-scale patches. The Carry test's 50 m row now asks the track to thin (no 10 m bin over the first, the last 20 m under a third
  of the first 20 m, the last bin under half the first; MR1's strict bin-by-bin fall is reported as "monotone"), since a smear after
  a gap may hold more than the bin before it; and a new row: along a 30 m exit G's autocorrelation at lags of 1-10 blot spacings
  has no peak over 0.3 (MR1's stamping had one: 0.40 at 75 cm in a Python model of the same grid).
- **Muddy grass.** The close camera (1.4 m from the verge point with the most mud, 0.6 m up) and a diagnosis: with the tussocks'
  mud line raised to 4 m and the mud blue, the blades over the carried mud turned blue and the rest did not (the coverage reaches
  the grass); with the coverage texture white, every blade turned blue (the block runs). Two causes, both fixed in
  `mud_cover.wire_grass_mud`: (1) in a pixel shader `ObjectPositionWS` is the ISM component's origin, not the instance's
  (MaterialTemplate.ush: the pixel parameters take the primitive's position, the vertex parameters the instance's), so on the
  strips (the component at the world origin, the ground about 34 cm up) every blade stood above its 18-30 cm mud line; the origin
  now reaches the pixel shader through a vertex interpolator. (2) The mud colour was the Standard bog's mean x 1.6, the straw
  tussocks' own brown in the sun; now the mean itself (x 0.6 toward wet). Carry_Grass_Off.png (the same camera with
  gt.Mud.GrassMud 0) is the pair.
- **The black square.** A deferred decal whose material has no compiled shaders is drawn with the engine's fallback
  (DecalRenderingShared.cpp's TryGetDeferredDecalMaterial walks GetFallback to DefaultDeferredDecalMaterial: unlit, a constant,
  opaque over its box) - a black, hard-edged square whose top edge followed the decal box round the post. In the editor a
  material's shader jobs are submitted when a primitive first draws with it; with GoWR holding the CPU (and after a setup rerun had
  rebuilt the decal material) the splats came before the shaders. `UGTMudSplatSubsystem` now places a decal hidden while
  `M_GT_MudSplatDecal`'s shader map is not complete for the world's platform (`IsDecalMaterialReady`), shows it when it is (its spawn
  time kept), and in the editor asks for the jobs itself (`SubmitCompileJobs_GameThread`, from Initialize and every tick until
  ready: a decal held hidden never draws, so nothing else would ask - the first fix alone left 24 decals waiting all run).
- **The trace budget.** A blob is traced only while it is descending and within `TraceBandCm` 100 of the surface under it (a
  patch's field surface inside a box; outside, the landscape's height from `LandscapeHeightAt`, a heightfield lookup through
  `ALandscapeProxy::GetHeightAtLocation`, no trace); a blob outside every patch that goes under the landscape's height splats
  there without a trace (`SplatGround`). The cap stays 64 a frame.

### MR2: the muddy vehicle

- **The state** (`GTBodyStateComponent.h/.cpp`): the per-region **Dirt carries MudCoat** (one coat per region, as the plan
  allowed; dust still adds to it and reads as dried mud). New: `TyreCoat` per wheel, `MudLineCm` (the most over `MudLineWindowS` 10 s
  of the deeper of the sinkage and the water at a wheel, plus `MudLineBaseCm` 20, plus `MudLineSpinCm` 30 while a wheel spins over
  `MudLineSpinShare` 0.2), `CoatLineCm` (the coat's own line: MudLineCm's high mark while mud is laid, lowered only by `Wash()`),
  `MudWet` (1 with fresh mud, falling to 0 over `MudDrySeconds` 90, never under the weather's wetness), `WashCm` / `WashAmount`
  (the last waterline and how clean below it), `Rain` (set by the pawn from the weather). `GetCoatAt(Region, HeightCm)` is the
  material's coat before its breakup (the tests' mirror); `RegionSpanCm` the regions' heights above the wheel bottoms.
- **Sources**: a wheel on the Mud or Bog surface (a bog's patch or an old mud lane; not a ford's riverbed, a profiled patch on its
  Dirt bed that the traction flags too) and not washing cakes its tyre (`TyreCoatSeconds` 0.8: 0.9
  in about 1.8 s; MR1's `MudLoad` keeps it at least that), and by speed (`MudFullSpeed` 300 cm/s) x sinkage (0.3 + 0.7 x the
  fraction) coats its side's sill (`SillMudRate` 0.3 shared by two wheels), its end's bumper (`BumperMudRate` 0.15) and its arch
  (`ArchMudRate` 0.35, plus spin); spin flings mud by axle onto its end and arch (`FlingRate` 0.4: front - the front bumper and front
  wings; rear - the rear and rear arches); the belly past `AxleClearanceM` coats the sills (`BellyMudRate` 0.4); a thrown blob hitting
  the body coats the region it hits (`AddThrowHit`: its volume x `BlobHitCoatPerCm3`, 0.003-0.05, MudWet 1; the region from
  `ResolveRegion` with the hit face's normal; the only source for the windscreen).
- **Blob hits** (`GTSprayComponent`): a rising mud blob inside the body's local bounds (plus `BodyTraceMarginCm` 30) is traced
  against the car's own collision (one component, `LineTraceComponent`), at most `MaxBodyTracesPerFrame` 32 a frame for this car (a
  refused blob traces the longer path next frame). On a face it sticks (the region coated, the blob gone, counted
  `GetThrowBlobsOnCar`); on the underside it coats and drops back (`GetThrowBlobsUnderCar`), its mud still landing in the field -
  consumed there, 56 % of a spin-up's blobs never reached the bog in the first run.
- **Removal**: a wheel in water over `WashDepthCm` 5 (a ford's; a bog's rut water is slurry and does not wash) washes below its
  waterline: the band (`WashCm` rises to the deepest water, `WashAmount` by `WashMovingRate` 0.3/s over `WashMovingSpeed` 50 cm/s
  or `WashStillRate` 0.1/s), a region wholly under the water loses its coat at that rate, the tyre at `TyreWashRate` 0.5/s; fresh
  mud thrown at speed or by spin fills a washed band back (`WashRefillRate` 0.5/s x the strongest wheel's speed x sinkage + spin);
  rain at `RainWashRate` 0.01/s x rain on every region and tyre. Nothing else removes mud. To make the ford wash, two pieces of
  MR1 moved: `FGTWheelTraction::bRutWater` (the water at the contact is a bog's rut water) and, in `StepMudLoad`, a ford's water
  over its riverbed patch now washes the load (it rose there before: in the ford the load and so the tyre stayed caked).
- **The material** (`setup_m1_body.py`): `M_GT_Vehicle`'s Grime node is a custom node with a `CarMud` scalar (0: the pre-MR2 node
  exactly). MR2: the coat across the body from three vectors (`CoatEnds` front / rear / roof / glass, `CoatArches`, `CoatSides`)
  blended smoothly in car space round the wheels (`WheelGeom`: the axles' X 160.2 / -114.9, hub Z 37.9, radius 38, from the
  skeleton's rest pose; `MudBaseZ` -0.1 the wheel bottoms), so no panel seam shows; the Standard bog slice (`MudSlice` 0) tri-planar
  in car space at `MudTileCm` 100, its colour, roughness and normal `MudBlurMips` 3 mips down (sharp, the bake's lumps read as a
  mosaic of glued pebbles on the tailgate in the first two runs - the rejection list), its normal at `MudNormalStrength` 0.3 through
  a Local -> Tangent transform; the line at `MudLineCm` (the state's CoatLineCm) above `MudBaseZ`, broken by the bog's sharp height,
  the splatter (`T_MudSplat_Splatter`, `SplatterTileCm` 100, image down = car down), a 7 m-tile sample of the bog's height
  (`LineWaveCm` 22: tongues of 0.3-1 m; blurred three mips it sat low and a few highs stood up as vertical columns, the sixth run)
  and `ArchLiftCm` 18 round the wheels; below it the coat thick at the sills and thinner toward
  the line; above it the splatter's droplets thinning over `AboveCm` 80; below the last waterline clean by `WashAmount`, the
  waterline ragged too; MudWet from wet (x `WetDarken` 0.78, `WetRough` 0.3) to dried (x `DryLighten` 1.45, `DryRough` 0.9). The
  clear coat thins under it (1 - DirtMask) and MF_Weather takes it as porosity, as before; both paths (UsePaint 0 and 1) pass
  through it. `M_GT_Tyre` (new, skeletal mesh usage) on the skeletal mesh's `M_Wheel` slot (it drew the engine's
  WorldGridMaterial): rubber and a rim by the radius from the hub (`RimShare` 0.62), caked by `TyreCoat` (FL, FR, RL, RR) treads
  first, then the sidewall inward, the rim last, in the wheel's rest-pose space (PreSkinnedPosition / Normal through vertex
  interpolators - a pixel shader cannot read them) so the mud turns with the wheel. `M_GT_Glass`: Dirt as splats (three layers of
  the splatter appearing at Dirt 0.02 / 0.35 / 0.7), not a film; the windscreen is not built on the driven car (bBuildWindscreen off
  since 2026-09-11), so it is unseen. `UGTBodyComponent` pushes the values when one moves (`PushMud`) and dresses the tyres
  (`DressTyres`).
- **Switch**: `gt.Mud.CarMud` (1).
- **The test** `GrandTour.Mud.CarMud` (new, `GTCarMudTests.cpp`, CPU, on the state with a traction component set by hand): 3 s in
  a bog at 3 m/s, sinkage 15 cm (fraction 0.5): tyres 0.976 (asked 0.9), sills 0.585 / 0.585 (asked 0.5), roof 0, the windscreen 0,
  mud and coat line 35 cm; 11 s on firm ground after: the mud line 20.0 (its base), the coat line 35.0 kept, the sills kept; spin 2 s
  standing at full slip: front axle F / aFL / aFR 1.00 and R / aRL / aRR 0, rear axle the reverse, the line 65 (15 + 20 + 30);
  4 s through 50 cm of water at 2 m/s with the coat line 110: the band 50 cm at 1.00, the coat at 30 cm 0.000 and at 80 cm 1.000,
  every region kept at 1, tyres 0; 5 s standing in 50 cm: the band 0.500; 2 s through 120 cm: front and arches (wholly under) 0.40,
  the rest 1; a ford's riverbed (a profiled patch on Dirt): tyre 0, MudWet 0, sill 0.042 (dust); drying: 0.5 at 45.0 s, dry at 90.0 s;
  rain 1 for 10 s: 0.100 off a region and a tyre, MudWet held at the weather's 0.6; two 600 cm^3 blobs: the glass 0.03, aFL 0.03,
  MudWet 1, hits 2 (glass 1); gt.Mud.CarMud 0: the rule before MR2 (aFL 0.15, glass 0.03 a second at full spray, no hits, no tyres).
- **Runs** (the process state at each: GoWR open from 10:06 to about 12:15 and again from about 13:30; the OpenAI Codex app's
  Unreal ran Benmore reviews at 12:16, 12:26, 12:45, 12:51, 13:26 and 13:37, waited for each time with a background wait loop): the
  build exit 0 (no warning in the changed files) after each change; `& Art/mud_shape_test.ps1 -AllowGame` (GoWR open, no foreign
  Unreal): 12 of 12 GrandTour.Mud and GrandTour.Snow tests Success, CRC 8e0aad06; `Art/setup_m1_body.bat` then
  `Art/setup_m1_masters.bat` (6/6), `& Art/setup_mud_carry.ps1`'s command line (the strips' cover kept, the grass "kept"); the
  strip setups (setup_live_mud_drive, setup_mud_variants) not rerun: nothing they build changed. The first GPU run of the body
  test (GoWR open) showed two compile faults, fixed: a vector parameter reaches a custom node as RGB (`.w` out of bounds: the
  vectors are appended to float4 now), and PreSkinnedPosition cannot be read in a pixel shader (vertex interpolators).
- **The checks.** `check_mud_variants.py` gains a scripted pass (FAST) for a drive that does not get through (the car set 2 m
  before each section it missed and driven 6 m in; Stony's leg driven on out for the carried tracks, the section pictures held
  until after MR2; the verge run from 2 m before Stony through 11 m of its mud; the spin-up ended by its blobs; every placement
  waits for the car to come to rest - at a game's 1-2 frames a second a fixed wait left the car in the air and the first
  Car_Muddy_Side looked up at its underside), the trace counts per second and per frame, Carry_Grass_Off, and MR2's pictures
  from the car's sunlit right side and from behind it at 212 m. `check_car_washed.py` / `& Art/check_car_washed.ps1` (new):
  L_MudDrive, the L_MudDrive check's own drive through the mud to 74 m (Car_PreFord.png) and through the ford to 109 m
  (Car_Washed.png), the body state before and after. The wrappers take `-AllowGame` (an editor still refuses).
- **Runs of the checks**: L_MudVariants eight times. Clean (no game; run 6, 56 frames a second): completed 200 m in 78.9 s (Firm
  31.0 km/h 19.6 cm, Standard 23.1 km/h 33.3 cm, Deep 2.2 km/h 58.9 cm, Stony 20.6 km/h 27.2 cm); the exit's G per 5 m left 0.430 /
  0.333 / 0.221 / 0.149 / 0.117, right 0.371 / 0.257 / 0.198 / 0.172 / 0.113, gaps 4.1 % each side; the verge 16 of 17 points with
  mud, mean G 0.394; the spin-up 817 blobs, 815 landed (the floor's hits drop back), 24 synthetic paths splatted the post; the
  car at 212 m: every region 1.00 but the roof and glass 0, mud line 83, coat line 110, MudWet 0.95, tyres 1.00, 5,341 hits
  (underside), 3 blobs stuck. Traces: 134,097, refused 17,674 (112 a second over 157.7 s of play, 2.3 a frame), 63,744 blob-frames
  skipped by the band, 12 splats by the height test; the body's 52,352 traces, 7,085 refused (32 a frame). MR1's clean run had
  208,959 and 77,370 refused (no play time recorded; about 480 a second at this flow's length). With GoWR open (runs 1, 2, 8:
  1.3-1.7 frames a second) the drive stopped at 90-97 m every time; run 1's 25 s legs moved 0.2 m (real-time caps at those frame
  rates; now distance-ended, 240-300 s caps); run 8's scripted pass got 6 m into Standard, Deep and Stony, the exit to 210 m, the
  verge 15 of 15 points with mud. L_MudDrive's ford: GoWR open, the mud leg stuck in the bog at 57.2 m after 900 s (real), the
  ford leg through to 109.0 m (water up to 0.55 m, 45 s over 5 cm): before, every region 1.00, coat line 90, MudWet 1.00, tyres
  1.00; after, the washed band 55.2 cm at 1.00, tyres 0.00, the regions kept (none wholly under 55 cm), MudWet 0.74; the check's
  verdict FAIL (its mud leg's reach), the pictures written. The run before the riverbed fix: band 58.9 cm at 0.00, tyres 1.00.
- **Suite** `terrain drivetrain grip mud surface track body bodystate` (GoWR open, no foreign Unreal at its start): 7 PASS
  (drivetrain, grip, mud, surface, track, body, bodystate: glass dirt 0.00, asked only with gt.Mud.CarMud 0), terrain FAIL at
  step 11's held 30-degree exit (6 m in 6.4 s against 6.7 s down the ruts; escape forward 9.0 m); the one rerun FAIL the same
  (5.8 against 5.9 s; escape 11.1 m); a diagnosis run with gt.Mud.CarMud 0 FAIL the same (6.4 against 6.7 s; escape 9.3 m): not
  MR2's body; the gate this step has failed on before (BACKLOG: 3 of 4 runs).
- **Unchecked / owed**: a clean picture set in one run (the files on disk are run 8's, GoWR open: Carry_Exit's trail there is
  separate blots, the grass camera stood in a clump the car had flattened, Splat_Post took one natural decal off its face);
  the windscreen's splats (no windscreen is built); The Hide's cards' muddy feet; MudWet's dry look over 90 s in a picture;
  every cost (the body's traces: 330-580 a second on the strip drive, 32 a frame refused often).
- **Pictures** (`Art/Export/MudVariants`, `Art/Export/LiveMudDrive`): `Car_Muddy_Side.png` (run 8; run 7 the same) - the car's
  sunlit right side on the gravel: below the line a dark-brown mottled coat (no pebbles since the blur), its top edge rising and
  falling in rounded tongues to the window line in places and lower between them, clusters of droplets with short drips above it
  over the doors and pillars, the tyres caked brown over tread and sidewall, the rims grey with brown at their edges; it reads
  splattered, not a smooth band; for the owner's list: the droplets above are dense and fairly evenly spread over both doors, and
  the tongues have soft vertical sides. `Car_Muddy_Rear.png` - the bumper and lower tailgate solid brown, tongues up the tailgate,
  droplets and drips above on it and the pillars, the right side the same, the tyres brown. `Car_Washed.png` - a clean orange
  band along the lower doors to about 55 cm above the wheel bottoms with the coat, tongues and droplets above it; the tyres clean
  dark rubber, the rims grey; the band's top edge is a nearly level line, a little ragged (a waterline; it may read as a regular
  line). `Car_PreFord.png` - taken in the bog at 57 m (the leg's stop), the car sunk in it, coated and caked. The first runs'
  lessons are in the text above: the pebble mosaic (runs 1-2), the vertical columns (run 6), the underside (run 1).
  `Carry_Exit.png` - run 4 (clean, the final ground material): from Stony's exit two continuous dark smears for the first metres,
  fading into faint ragged traces, no rows of specks (MR1's: rows of small dark specks); run 8 (on disk, GoWR, the scripted pass
  driving out of Stony at full throttle): two loose trails of separate irregular dark blots of varied size with gaps, which at a
  distance read as broken dotted lines. `Carry_Grass.png` / `Carry_Grass_Off.png` - run 6 (clean): the clump's lower blades
  darker brown with GrassMud on (mean 78.5 vs 86.9 of 255 over the feet; 12 % of pixels darker by over 25 levels, 1 % lighter;
  above the feet even); run 8 (on disk): the camera stood in a clump the car had just flattened, the pair barely differs.
  `Splat_Post.png` - run 2 (the shaders asked for): irregular dark-brown splats on the post's face, lumpy edges, a few droplets;
  no black square in any run since; run 8 (on disk): one natural decal, not on the face the camera sees.

## 81. Benmore water: bounded foam/sediment and cached river stepping (2026-10-08)

The opt-in Benmore water domain uses one moving 96 x 96 field. Its reference-wave kernel now visits wet cells and caches fixed mean velocities and absorbing-band coefficients; physical timestep remains 60 Hz. Separate passive foam/suspended-sediment concentrations update at most 30 Hz, driven by changing immersed-solid occupancy, transported by current and retained through window relocation. They do not write water volume, flux, terrain or vehicle forces. The default combined height/flow and detail texture upload cap is 30 Hz; detail uses 36 KiB, the existing half-float water texture 72 KiB. Existing sourced water normals supply visual breakup. No new car, traction, buoyancy, mud/snow tuning or generated art textures.

Build succeeded. All three `GrandTour.Water.*` native tests passed: a 0.6 m/s current transported the foam centre 240.01 cm in four seconds, retained 0.36788 of its amount on the four-second decay timescale, and left physical heights bit-for-bit identical to the no-detail control. Dry-bank, finite/bounded concentration, solid-source, reset and window-handoff checks passed. Existing river-reference stability/volume and whole-water query tests still pass. No native performance threshold is inferred from those correctness tests.

The rest/wake/+4 s screenshots, runtime counters, on/off/off/on comparison, regression results and remaining art gates are recorded in `docs/BENMORE_RIVER_LIFE.md`. `gt.Water.Domain.Detail` is the visual comparison control; `gt.Water.Domain.UploadHz` is capped 15–60 (default 30). The former only affects the Benmore opt-in domain. The owner still needs to drive the crossing; a scripted immersed footprint is a material/transport preview, not a vehicle handling result. River-mouth geometry, new splash/wet-bank effects and full-scene Lumen/vegetation optimization remain separate work.

Final local DomainTick at 1274 x 682: ford 0.651 ms median, coastal lake 0.866 ms, fully wet open lake 1.718 ms (2.432 ms p95). Sixteen 10 m shifts peaked at 4.246 ms. Full-grid detail ABBA added approximately 0.141 ms CPU by paired medians; GPU variation did not resolve its incremental cost. Dedicated water regression PASS; terrain FAIL at its standing step-11 rut-exit gate, with terrain's water/flood/float/recovery checks passing. The wider scene is still GPU-limited, particularly Lumen scene updates; no whole-game FPS gain or complete-suite pass is claimed.

## 82. MudRunner MR2b: car mud splatter with structure - wheel fans, a jagged sloped mud line; the clean picture set (2026-10-08)

docs/MUDRUNNER_LESSONS_PLAN.md MR2b (its italic note), docs/MUD_VARIANTS.md ("The muddy car", MR2b). The main session's look at
MR2's Car_Muddy_Side: the coat's top edge was rounded tongues with vertical sides (a skyline: blocky) and the droplets above it
were spread evenly over the doors and pillars (polka dots: very uniform). Kept: the caked tyres and the mottled coat. No cost or
timing was measured (the owner tests performance); the switch stays `gt.Mud.CarMud`.

- **The spray fans** (`GTBodyStateComponent.h/.cpp`): per wheel `FanCoat` (0..1), fed in mud by the wheel's spin
  (`FanSpinRate` 0.8 a second x the tread's speed over the car's, / 300 cm/s) and by its speed x sinkage (`FanRollRate` 0.3 x
  MR2's Rolled); washed like the coat (its arch wholly under a ford's water at the coat's rate, rain at 0.01/s, `Wash()`).
  `FanDir` (+1: the fan opens behind the arch) is the sign of `FanSide`, a memory of where the wheel's mud went (-1..1, moved by
  `FanSideRate` 2 x the fan's feed a second toward the way the tread moves: a full spin turns it over in about 1.25 s). The
  tread's speed is new on the traction: `FGTWheelTraction::TreadCmPerS`, Chaos's omega x the wheel radius (forward positive, 0
  braked). Strip runs 1-4 ended with every fan forward. The cause was the check: it parked the car with the brake pedal held,
  which is reverse at a stop (UGTDrivetrainComponent), so after the spin-up the wheels spun backward in Deep for the 4 s wait
  and the fans followed them, rightly (a trace of the fans' sides through the run's phases showed the turn in that wait). Two
  rules went before that was found: the slip's own sign (wrong for a braking wheel, whose slip is negative while its tread still
  moves forward: now a test row) and the car's speed plus the slip; the tread's own omega x radius stays. The checks now let the
  pedal go once the parked car is slow (the handbrake holds it): `check_mud_variants.py` and `check_car_washed.py`.
- **The material** (`setup_m1_body.py`, M_GT_Vehicle's Grime node; `UGTBodyComponent::PushMud` sends `FanCoat` and `FanDir`,
  FL FR RL RR, to every panel as it does the coats):
  - the mud line is a curve along the body, never a top-down sample (MR2's 7 m sample of the bog's height was constant up a
    side, so its tongues had vertical sides): `s = x - y` runs along car X on each side and across the ends, continuous at the
    corners; the line is the coat line x (1 - `LineDropShare` 0.35), two value-noise octaves along s (`LineLongCm` 80 at
    `LineLongAmpCm` 12, `LineShortCm` 25 at `LineShortAmpCm` 4) and `ArchRiseCm` 15 over each arch (full within the wheel's
    radius of its axle, smooth-stepped down over `ArchRampCm` 40): its slope at most 3 x 12 / 80 + 3 x 4 / 25 + 1.5 x 15 / 40 =
    1.49; the edge broken at two scales by a fine value noise (`EdgeNoiseCm` 9 and a third of it, turned off the axes,
    `EdgeNoiseAmpCm` 3) and the splatter's own droplets (`EdgeSplatCm` 8). The noise is a sin-free hash in a struct in the
    custom node. `LineDropShare` 0.25 at first kept the coat to the belt behind the rear arch (no paint above it for a fan to
    show on); 0.35 brings the solid coat back to about where MR2's thinning left it. The coat's thinning toward the line
    follows the line (its rise is the height over the line), its mottle a 40 cm noise on the side in place of the 7 m sample.
  - the droplets show by a density: per arch an annular sector in the side plane from the arch centre, `FanLowDeg` -20 to
    `FanHighDeg` 105 from straight back (back = away from the wheel's throw, `FanDir`), its density (1 - t)^`FanFalloff` 1.5
    with t the distance past the wheel's radius over `FanReachCm` 120, its radius and angle broken by a `FanNoiseCm` 25 noise
    (+-`FanNoiseAmpCm` 15 cm, +-0.35 rad), x the wheel's FanCoat; plus `FanBase` 0.1 x the coat elsewhere, thinning over
    `AboveCm` above the line. They show in the paint the coat leaves too (the thinned clusters near the line).
  - `T_MudSplat_Splatter` gained a G channel: each droplet's rank 0..1 (`build_mud_splats.py`: its own random stream, so the
    coverage R is the MR2 bake's byte for byte - checked; the atlas, its header GTMudBlots.inl and the masks unchanged; a drip
    carries its droplet's rank, overlaps take the lower, the background a neighbour's grown 24 px for filtering and mips; 0.6 a
    cluster's key + 0.4 its own, made uniform over the 2,299 droplets). The material shows a droplet where its rank is under
    the density (soft over 0.04), so a thin fan is fewer whole droplets, not smaller ones (density 0.1 keeps 10.9 % of the
    covered pixels, 0.3 36.7 %, 0.6 68.9 %). The rank is weighted by the three projections' coverage so a droplet keeps its own.
    Imported by `& Art/setup_mud_carry.ps1` (TC_Masks, wrap); the tyre and glass read R only, unchanged.
  - Gone: `LineWaveCm`, `ArchLiftCm`, the 7 m sample (`lowH` / `wave`).
- **Tests** (`GTCarMudTests.cpp`, GrandTour.Mud.CarMud): the right rear alone spinning forward 2 s standing in mud: FanCoat FL
  0 / FR 0 / RL 0 / RR 1.000, its side behind; spinning backward: still behind after 0.5 s, in front after 1.5 s, the others 0;
  rolling 1 s at 2 m/s then braking 1 s (slip -150 cm/s): all four behind; 2 s at 3 m/s, sinkage fraction 0.5: 0.390 each; a fan
  washes like the coat: from 1.00, 4 s through 50 cm of water 1.000 (the arch 1.000), 2 s through 120 cm 0.400 (the arch 0.400),
  10 s of rain 0.900 (a region 0.900), Wash 0. `& Art/mud_shape_test.ps1 -AllowGame`: 12 of 12 GrandTour.Mud and GrandTour.Snow
  Success, field CRC 8e0aad06.
- **The droplet-density row** (`Art/count_car_droplets.py`, system Python with numpy and Pillow, run by
  `check_mud_variants.ps1`): two boxes on the car's right side in the same band, 92-114 cm above the wheel bottoms (under the
  belt), behind the right rear arch (5-50 cm behind its edge) and mid-door (50 cm about the middle between the arches' inner
  edges); `check_mud_variants.py` writes their world corners and the camera into the report, the counter projects them (the
  camera's horizontal FOV over the picture's width) and counts 8-connected dark spots (under 0.6 x the box's 95th-percentile
  luminance, 3-1,500 px, not touching the box's border) and writes Car_Muddy_Side_Boxes.png.
- **The checks.** `check_mud_variants.py`: Car_Muddy_Side from 6.4 m (MR2 4.7 m: the whole car, both arches' fans), the boxes,
  the fans in the body report and a trace of their sides through the MR1 phases, Carry_Grass's camera on a verge point the car
  crossed and did not park on (none within 4 m of where it stopped), the parked brake let go. `check_car_washed.py`: the fans in
  its report, the parked brake let go.
- **Runs** (no game open at any of them; the OpenAI Codex app's Unreal ran Benmore water installs and validations at 15:19,
  15:22, 15:25, 15:34, 15:57 and 16:07, waited for each time with a background wait loop; once, at 15:25, a chained command of
  mine ran `setup_m1_body` and `setup_m1_masters` while its install ran - the build's own guard refused, the chain went on -
  so both were run again alone at 15:28): the build exit 0 after each change (no warning in the changed files);
  `& Art/mud_shape_test.ps1 -AllowGame` four times, the last: 12 of 12 GrandTour.Mud and GrandTour.Snow Success, CRC 8e0aad06;
  the bake (`build_mud_splats.py`, headless Blender 5.1); `& Art/setup_mud_carry.ps1` (the splatter's G imported; the strips'
  cover and the grass "kept"); `Art/setup_m1_body.bat` and `Art/setup_m1_masters.bat` (6/6) after each material change;
  `Art/body_test.bat gpu` once (PASS, no compile error); `& Art/check_mud_variants.ps1 -AllowGame` five times (all completed
  the drive, 200 m in 80-83 s; Firm 30-31 km/h, Standard 22-24, Deep 2.0, Stony 21-24; the fans forward in runs 1-4, see
  above; run 5 the set below); `& Art/check_car_washed.ps1 -AllowGame` once (the mud leg to 74 m in 50.7 s, the ford to 109 m;
  before: every region 1.00, coat line 90, fans 1.00 behind, tyres 1.00; after: the washed band 50.4 cm at 0.983, tyres 0.005,
  fans 1.00 (no arch wholly under 50 cm), MudWet 0.97).
- **The droplet-density row** (run 5): behind the rear arch 26 dark spots (2.63 per 100 cm2, median 7 px), mid-door 2 (0.18
  per 100 cm2): 14.6x the density (asked 3x). The runs with every fan forward: 13 / 8, 5 / 3, 4 / 3, 10 / 3 (1.5-3.7x).
- **Pictures** (run 5 and the ford run; all from runs with no game open; `Art/Export/MudVariants`, `Art/Export/LiveMudDrive`):
  `Car_Muddy_Side.png` - the whole car from its sunlit right side: the coat a smooth dark brown (MR2's three-mip blur), its top
  a sloped curve, low mid-door (about 40 % of the door's height), rising over the rear arch almost to the belt and toward the
  front over the front wheel; jagged at small scale with droplet-shaped bumps and drips; no vertical-sided tongues, not a
  skyline. The droplets and drips stand in two patches: dense over the rear quarter behind the rear arch up to the belt and
  the D-pillar's foot, thinning forward over the rear door; and behind and above the front arch over the front door's front
  half and the wing; the middle of the doors is nearly clean. They read as spray round and behind each wheel, not an even
  spread; within a patch they are scattered round droplets (no directional streaks), and the fans' outer edges are not a
  visible shape. Tyres caked, rims grey with brown. `Car_Muddy_Side_Boxes.png` - the two boxes and the counted spots.
  `Car_Muddy_Rear.png` - the coat low on the rear face (the line about 50-55 cm there): the bumper's right half and the lower
  right corner coated, the bumper's top on the left pale; droplets scattered over the tailgate, densest at its lower right
  near the right rear wheel; the right side's rear quarter densely spattered behind its arch. Less coated than MR2's rear
  (whose line was the full coat line plus its waves). `Car_Washed.png` - after the ford: tyres clean dark rubber, the sills
  clean to the waterline, above it only a thin ragged strip of coat (the line about 58 cm: 0.65 x the 90 cm coat line)
  widening into a wedge behind the front arch, and the two fans of droplets above; the strip may read as a stripe.
  `Car_PreFord.png` - at 74 m after the mud: the coat low mid-door rising to the arches, the fans behind them, tyres caked,
  carried blots on the ground behind the rear wheel. `Carry_Exit.png` - faint: two short dark marks at Stony's exit and two
  thin broken trails over the first few metres of gravel; nothing visible nearer the camera (the exit's G per 5 m 0.39 / 0.23
  / 0.21 / 0.19 / 0.09 left). `Carry_Grass.png` / `Carry_Grass_Off.png` - the camera at a verge point the car crossed (193.4 m,
  8.1 m left; it parked 16.5 m on at 209.9 m), filled with the tussock's blades: the lower blades darker with GrassMud on
  (mean luminance of the middle band 90.0 against 97.1, 10 % of pixels darker by over 25 levels, 0.5 % lighter); subtle by
  eye. `Splat_Post.png` - irregular dark-brown splats with lumpy edges on the post's shaded side from about 30 cm to 1.4 m (the
  24 synthetic paths; the spin-up's own blobs reached no mesh), one or two with a straight cut edge; no black square.
- **Suite** `terrain drivetrain grip mud surface track body bodystate` (no game, no foreign Unreal at its start, 16:25): 7 PASS (drivetrain, grip, mud, surface, track, body, bodystate: glass dirt 0.00), terrain FAIL at step 11's held 30-degree exit (6 m in 5.9 s, the same as down the ruts); the one rerun PASS (5.9 against 5.6 s): the known flake (MR2: FAIL twice there, also with gt.Mud.CarMud 0).
- **Unchecked / owed**: the owner's look and drive; the fans' look under reverse spin (the tests only); every cost (the Grime
  node now evaluates seven value noises and a two-fan loop per pixel); the windscreen's splats (no windscreen is built).

## 83. Benmore water: cloudier optics and readable surface motion (2026-10-08)

**Subsequent user review rejected this appearance.** Source/code audit completed against both Spintires articles and their wave/simulation diagrams. The replacement stages and validation gates are recorded in `docs/BENMORE_RIVER_LIFE.md`, "Spintires reference audit and corrected implementation order". Existing bounded disturbances, foam/silt transport and wheel/bow spray are useful baselines; the missing coordinated ambient waves and the visible lake coverage defect remain implementation work. The audit changes documentation only and makes no new build, render or performance claim.

Further scope correction: the user rejects the river surface outline, bed shape and bed texture too. A read-only native-bed/mean-water survey now runs via `Art/tools/audit_benmore_channel_shape.py`; saved native wet-area median depth is 12.81 cm and 64.55% is below 20 cm. Three section plots and a footprint map expose the current geometry for review; height input remains byte-identical. The first replacement stage now includes a 100–150 m native-terrain morphology/material pilot and coupled flow rebake before wave shading. Preserve low banks, deformability, roads and ford access, and re-seat affected instances deliberately. See the morphology addendum in `docs/BENMORE_RIVER_LIFE.md`. This is a completed diagnostic, not new installed terrain or an in-engine visual result.

The user's "too clear and still" follow-up changes the review-owned river/lake masters only: a mineral-bearing base, stronger sourced ripple normals, current-driven broad detail and restrained moving facing highlights. No native physics, car/mud tuning, terrain, placements, texture sample count or simulation resolution changed. Controls `WaterTurbidity=1`, `SurfaceMotion=1`; comparison value 0 retains the previous look. `WaterTimeOverride=-1` uses normal time; positive values are capture-only. The source rain normal's RG standard deviation is only about 0.019, so the first gain increase remained too subtle; final gain 2.0–5.0 is slope-capped at +/-0.32 and paired with the facing response.

Material compile/save/reload passed with no final shader errors. Fixed Ford/Upstream/Lake images and sixteen sampled material-clock phases were captured. Ford water ROI mean RGB change 9.43/255, 19.47% of pixels over 20; 0.75-second motion change 2.04/255 versus 0.54 in the first attempt. The GIF is a sampled material preview, not driving or runtime frame-rate evidence. God of War was active, so the new appearance has no measured GPU timing; the harness preserves an ABBA option for a quiet run. An existing local/static lake coverage/join defect was exposed by both comparison settings and remains unresolved. Details, sources, controls, backups and evidence are in docs/BENMORE_RIVER_LIFE.md, "Water clarity and visible current". No native retest was claimed for a material-only revision.

## 84. MudRunner MR3: muddy rut pools - turbidity per cell, brown churn and froth, settling (2026-10-08)

docs/MUDRUNNER_LESSONS_PLAN.md MR3 item 1 (its italic note; rut pools only, the owner's scope: the ford's water is being reworked
separately, and GTWaterField, GTWaterSheet, M_GT_Water, the river and setup_m6_water.py are untouched), docs/MUD_VARIANTS.md
("Muddy rut water"). No cost or timing was measured (the owner tests performance). Switch: `gt.Mud.MuddyWater`.

- **The field** (`GTMudField.h/.cpp`): per cell `Turbidity` (0..1; mud only, empty on snow), with its own per-tile flags
  `TileTurbid` over the settle's tiles. `ChurnWater` sets it to 1 where the water over the cell - `RutWaterTableCm` (the patch's
  `CurrentWaterTableCm`, pushed every tick and when the water grid is built) over the surface, the lower of before and after -
  is over `TurbidMinWaterCm` 1 cm. Called from `TouchCell` where it sets Fresh (a stamp that moved the cell: a parked wheel that
  does not move the mud does not churn) and from `DepositLump` (a throw's landing). `SettleTurbidity(dt)`: a fixed sub-step
  (`TurbidStepS` 0.1 s, at most `TurbidMaxSteps` 10 a call, its own accumulator) over the turbid tiles: (1) a sleeping neighbour
  tile joins when a wet edge cell at `TurbidSleepBelow` 0.02 or more faces a wet cell of it; (2) each wet cell takes
  K x (neighbour - itself) from each wet 4-neighbour in a listed tile (K = `TurbidMixRate` 0.15/s x dt, at most 0.2, so every
  new value is a weighted mean of old ones: never above 1, and both sides of a pair computed from the old values, so the
  exchange conserves), then the decay 0.5^(dt / `RutSettleS` 45); a dry cell holds 0; (3) a cell whose value crossed a 32nd is
  dirty (uploaded); (4) a tile under 0.02 everywhere sleeps and its remainder goes to 0, unless a turbid neighbour's wet edge
  faces it (it would only join again). It runs in the patch's Tick on its own clock, whatever `gt.Mud.Settle` says, before the
  upload. Heights, lumps, slide, tracks, tread, fresh, the set timers and the settle's own tiles are never written by it (the
  test's state CRC and awake tile counts are equal with the switch on and off). `SetMuddyWater(false)` clears every turbid
  tile (marked dirty) and nothing is set after. `TurbidityAt`, `TurbidTileCount`.
- **The upload**: TreadTexture A on mud is the turbidity (`TreadAlpha` and `EncodeTexels`; A was 0 on mud since LM3c, only
  snow writes it, and no mud material read it: LM5b dropped the churn channel). B stays Fresh.
- **The patch** (`GTMudPatch.h/.cpp`): `gt.Mud.MuddyWater` (default 1); each tick (mud only) it pushes the table and the switch
  (on only where its rut water is drawn, `IsWaterDrawn`) and, when the switch moves, the water material's `MuddyWater`;
  `BuildWaterMesh` gives the water's instance `MudTread` and `MuddyWater`. Readouts: `LastTurbidSteps`, `TurbidityAt`,
  `TurbidTileCount`, `DescribeMuddyWater(centre, radius)` (wet cells, turbid over 0.5, the max and wet mean, froth cells, turbid
  tiles, the table, the switch) for the checks.
- **The material** (`live_mud_style.py` `muddy_water`, run by `apply_existing` after its rut-water defaults, so both strip
  setups put it back after `setup_m6_water` rebuilds M_GT_MudWater): a custom node `Muddy water (MR3)` between setup_m6_water's
  `Mud water (PS)` and the colour, opacity and roughness, reading that node's own field, table, rim, patch box and position
  parameters. `MuddyWater` 0 (or turbidity 0) returns its inputs untouched. Else the colour goes by turbidity toward the
  Standard bog slice top-down at `TurbidTileCm` 300 and `TurbidMip` 5 (soft mottling, no grain), pulled toward its mean
  (`TurbidMean`, the splat manifest's 0.0705 0.0401 0.0186) by `TurbidMottle` 0.55, x `TurbidLighten` 1.9; the opacity to
  `TurbidOpacity` 0.96 past `TurbidOpaqueCm` 3 of water (`TurbidRimOpacity` 0.7 at the rim, x the rim fade); roughness to
  `TurbidRough` 0.32. Froth where Fresh (B) x smoothstep(`FrothTurbidLo` 0.5, `FrothTurbidHi` 0.85, turbidity): the splatter
  bake's droplets (T_MudSplat_Splatter, `MuddySplatter`) at `FrothTileCm` 140 and a second tiling turned 37 degrees at 1.37 x,
  a droplet shown when its rank (G) is under the density (the second layer's at 0.7 x), the density x a two-octave value noise
  (`FrothClusterCm` 40, a sin-free hash) through a threshold, so the specks come in clusters of whole droplets of their own
  sizes; their colour the mean x `FrothLighten` 3.6 (x 0.85-1.15 by the droplet's coverage), opaque within the pool, roughness
  `FrothRough` 0.75. All proposals.
- **The check** (`check_mud_variants.py`, after MR2's pictures): the car set 2.5 m into Deep on the drive's ruts, full throttle
  for 4 s of game time, then moved to the gravel (a parked car keeps stamping as it sinks) and hidden; the most churned spot (the
  most turbidity in a 60 cm box over a 20 x 10 cm scan of the stretch); `Rut_Muddy.png` from 3.4 m (1.9 m up, the +Y side)
  looking down at it, `Rut_Settled.png` from the same camera 60 s of game time later; the patch's readout at each.
  `check_mud_variants.ps1` prints the MR3 lines; `mud_shape_test.ps1` expects 13 tests and prints the MuddyWater rows.
- **Tests** (`GTMudWaterTests.cpp`, GrandTour.Mud.MuddyWater, CPU on the field; the Settle test's 40 cm stroke under a -25 cm
  table):
  - set: 403 cells over 1 cm of water, 403 turbid at the stamps (0 of them left dry by a later stamp), 433 after one sub-step
    (the mix into the shallower wet cells), 0 dry; no table 0, a 15 cm rut (above the table) 0; a throw in the pool (14.0 cm of
    water) 1.00, on the dry mud beside it 0.00;
  - settle: the pool's sum 402.4 halves in 45.00 s, its middle cell in 42.70 s (asked 45 s, 10 %); at 90 s 0.250 of the start;
  - mix: one churned cell (14.6 cm of water) at a tile's last column, 20 s: never above 1.000, never in a dry cell, the sum never
    rose; across the tile edge 0.021, two back 0.016, the seed 0.023; the sum 0.7268 against the settle alone's 0.7349 (the
    1e-5 floor at the spreading front); 2 turbid tiles;
  - switch: the Settle test's LM0 CRC under the -25 cm table 8e0aad06 with the switch on and off; after 30 s of Settle and
    SettleTurbidity the state CRC (heights, lumps, slide, tracks, tread, fresh, set timers) 8d64be62 both, the awake tile count
    equal every frame, off: no turbidity, the tread texels' A all 0, every other texel equal to on's;
  - sleep: 7 turbid tiles, all asleep at 251.8 s (asked log2(50) x 45 = 254.0 s, 10 %), no turbid cell after.
  13 of 13 GrandTour.Mud and GrandTour.Snow tests, CRC 8e0aad06 (`& Art/mud_shape_test.ps1 -AllowGame`, GoWR open).
- **The run** (`& Art/check_mud_variants.ps1 -AllowGame`; GoWR open at every Unreal run of this stage, so every picture is from a
  game run): the drive timed out at 99.27 m (300 s at about 2 frames a second); the scripted pass did Standard, Deep and Stony;
  MUD_VARIANTS_DRIVE_OK. MR3: the car set at 122.5 m, 4.21 s of game time at full throttle (sinkage 60 cm on all four, slip
  270 / 83 / 171 / 0), it moved 0.66 m; the spot 123.9 m, -0.05 m (between the tracks: at 60 cm the belly cuts the middle too),
  the mud 41 cm under Deep's -15 cm table; at Rut_Muddy within 60 cm: 74 wet cells, 63 over 0.5, max 0.997, the wet mean 0.850,
  60 froth cells, 15 turbid tiles in the patch; at Rut_Settled (60.2 s of game time later, 141.8 s real): 74 wet, none over
  0.5, max 0.304, the wet mean 0.265 (the settle alone from 0.85: 0.34), no froth, the spot's cell 0.287.
  - `Rut_Muddy.png`: the churned pool fills most of the frame, opaque mid-brown with soft, even mottling (smooth); pale tan froth
    specks lie in two loose diagonal bands of irregular clusters (blots of many sizes, round droplets, some elongated drip-like
    streaks) - not a grid, no rings or swirls - but flat and crisp, reading more like spilt paint than foam; the floor's lumps
    show faintly at the far edge; lower right a nearly black shadowed bank.
  - `Rut_Settled.png`: the same camera; the froth is gone; the pool is still brown and a little more see-through (the floor's
    lumps show over more of it); the change from the churned picture is small, since the clear rut water was already brown.
- **Suite** `terrain drivetrain grip mud surface track` (GoWR open): 5 PASS (drivetrain, grip, mud, surface, track); terrain FAIL
  at step 11's held exit (6 m in 6.4 s against 6.1 s down the ruts), FAIL again on the one rerun (5.9 s against 5.7 s) - the
  standing failure MR2 and MR2b met; nothing in MR3 reaches the traction or the field's shape.
- **Open**: the main session and the owner look at Rut_Muddy / Rut_Settled. As seen: the froth reads as flat paint splatter
  (crisp tan blots and drip streaks) rather than foam, the churned surface is smooth and even, and the settled pool is barely
  clearer than the churned one because the clear rut water was already brown (the numbers to move are above; all proposed).

## 85. Benmore channel pilot: sourced bed aggregate and bounded surface refinement (2026-10-08)

- Installed in `L_Benmore_GaeaReview`, owned assets under `Gaea/ChannelPilot`. Native heights, depth baseline, ford/approach profiles and vehicle constants retained. Original driving map hash unchanged.
- Unmodified CC0 Poly Haven river-small-rocks maps at 2.9 m repeat, geographic coarse/fine/damp zones; same appearance wrapper on the existing deformation field. Detail fades 35–100 m. 550 embedded 7–19 cm stones in four groups, no collision/shadows/distance fields, cull 50–110 m, excluded from the live crossing/path. Greatest sampled bottom gap −0.70 cm.
- Water surface refined only in X −725…−550, Y 105…310 m, against the unchanged native bed/query: 21,460 → 69,961 triangles. Original vertices outside bounds unchanged. No new ambient wave renderer.
- `BENMORE_CHANNEL_PILOT_OK`: material compile, save/reload, eight matched stills, four water queries and eight native collision supports passed. All 90,353 existing instance transforms retain their prior signature. Python syntax, source hashes and offline geometry checks passed. No C++ rebuild, driving suite or GPU timings for this visual/material pass.
- Pixel sampler: bare-bed luma standard deviation 0.04336 → 0.07001, adjacent horizontal difference 0.00746 → 0.01573. Reviewed pixels show more grain relief and embedded aggregate. The larger shoreline scallops, old ring normals and lake coverage defect remain; morphology/flow gates are still open. Next requires native-bank contours with matching rebake; another shared mud session currently occupies Unreal. See `docs/BENMORE_RIVER_LIFE.md` for evidence and limits.

## 86. MudRunner MR3b: soft bubbly froth and clearer settled rut water (2026-10-08)

docs/MUDRUNNER_LESSONS_PLAN.md MR3 (the MR3b line under its note), docs/MUD_VARIANTS.md ("Muddy rut water"). The main session's
look at MR3's Rut_Muddy / Rut_Settled: the froth read as spilt paint (crisp tan splatters with drip streaks), and settled and
churned water read as the same flat opaque brown. Material only (`live_mud_style.py` `muddy_water`, the `Muddy water (MR3)`
node on M_GT_MudWater); no C++; no cost or timing measured; GoWR open at every Unreal run.

- **Settled and churned** (all proposals): with `MuddyWater` on, turbidity 0 is now water - the old tint x `SettledDarken` 0.8,
  opacity `SettledRimOpacity` 0.3 at the rim to `SettledOpacity` 0.6 past `SettledDeepCm` 8 (x the rim fade), plus
  `SettledFresnel` 0.45 x the fresnel at a grazing angle; roughness `SettledRough` 0.07 to `SettledGlossRough` 0.03 at a
  grazing angle - and turbidity 1 an opaque lighter mid-brown (`TurbidLighten` 2.3, `TurbidMottle` 0.45, `TurbidOpacity` 0.95
  past 3 cm, `TurbidRimOpacity` 0.75, `TurbidRough` 0.35), lerped by turbidity. `MuddyWater` 0 still returns the node's inputs
  untouched (the water before MR3); with it on, every rut pool takes the settled look, churned or not. LM5b's far gloss fade is
  the mud's and the landscape's, not this material's (the setup reports no FarGloss parameter on M_GT_MudWater).
- **The froth**, procedural (MR3's splatter froth and its `FrothTileCm`, `FrothLighten` and `MuddySplatter` parameters are
  removed from the graph on a rerun): two jittered cellular layers, `FrothBubbleCm` 1.6 cm and 0.45 x that turned 37 degrees;
  each cell's bubble a soft disc (full to 0.45 of its radius, fading to its edge) at a random point, radius 0.22-0.5 of a cell
  (x 0.65-1 by the local density), shown when its own random number is under the density (the small layer at 0.8 x), so the
  bubbles thin toward the clumps' edges; the density is Fresh x smoothstep(0.5, 0.85, turbidity) x smoothstep(`FrothClumpLo`
  0.35, `FrothClumpHi` 0.75) of a two-octave value noise at `FrothClusterCm` 25 cm. Colour `FrothColor` 0.28 0.23 0.15 (creamy
  beige-tan) x 0.88-1.12 toward the bubble's centre, plus a glint (`FrothGlint` 0.35) in a small disc up-left of each centre;
  roughness `FrothRough` 0.3; opaque within the pool. Between `FrothNearCm` 400 and `FrothFarCm` 900 from the camera the bubbles
  fade into a flat tone (`FrothFarCover` 0.55 x the density), so far froth does not shimmer.
- **The check**: the grazing pair from eye level, 1.65 m over the ground 3 m from the spot on the +Y side (`Rut_Muddy_Low.png`
  after Rut_Muddy, `Rut_Settled_Low.png` after Rut_Settled), each waiting for the last picture to be on disk. Found on the way:
  under GoWR (about 2 frames a second) a picture taken 1.5 s after its camera moved was only 3 frames later and showed the
  camera as it was before (the first grazing run's Rut_Muddy, Rut_Muddy_Low and Rut_Settled_Low share one framing). Every
  picture of the check now also waits 10 ticks after its camera moves, and the phases hold while a picture is pending and for 3
  ticks after its command. In the third run each camera's two pictures share one framing (checked by eye on a contact sheet).
- **The run** (`& Art/check_mud_variants.ps1 -AllowGame`, GoWR open: every picture from a game run; MUD_VARIANTS_DRIVE_OK; the
  drive timed out at 84.65 m, the scripted pass took Standard, Deep (7.9 of 8 m in 240 s) and Stony): the car spun 4.17 s in
  Deep's pools; the spot 123.92 m, -0.05 m, 41 cm deep; at Rut_Muddy 59 of 74 wet cells over 0.5 turbid, 58 froth cells; at
  Rut_Muddy_Low (2.5 s of game time later) 61 / 59; at Rut_Settled (60.0 s later) none over 0.5, max 0.305, the spot 0.276.
  - `Rut_Muddy.png`: the churned pool brown and opaque, with clumps of small pale soft-edged bubbles, lighter in the middle,
    thinning toward the clumps' edges; no grid, no drips, no crisp blots. They read as scattered bubbles on the water, not
    paint, but sparse and fine (from 3.4 m most are a few pixels: a pale speckle more than a foam head).
  - `Rut_Muddy_Low.png`: the same froth from eye level, the clumps foreshortened into bands of speckle; the brown surface has
    no visible sky reflection.
  - `Rut_Settled.png`: the froth gone; the pool a translucent brown film with the floor's lumps and the tracks showing through
    it and a faint sheen: murky water, clearly different from the churned picture, though still brown (turbidity about 0.28 at
    60 s: the half-life is 45 s).
  - `Rut_Settled_Low.png`: the same from eye level: the floor's lumps visible through the water, a soft sheen, no sky
    reflection seen at this angle (about 35 degrees down). No swirls, rings or grids in any of the four.
- **Tests**: `& Art/mud_shape_test.ps1 -AllowGame`: 13 of 13 GrandTour.Mud and GrandTour.Snow Success, CRC 8e0aad06 (the
  MuddyWater switch row unchanged).
- **Open**: the main session and the owner look at the four. As seen: the bubbles may be too fine and sparse to read as a foam
  head from standing height (`FrothBubbleCm`, `FrothAmount`, `FrothClumpLo`/`Hi` to raise); the settled water shows no sky
  reflection at 35 degrees (`SettledFresnel`, `SettledOpacity` to raise).

## 87. Benmore continuous native channel: removing point-stamp banks (2026-10-08)

- **Problem/change:** old native incision used isolated drainage samples, creating repeated disc banks. Recovered its exact sampling phase and verified reconstruction, then replaced point distance/nearest floor selection with continuous segment distance/interpolated original floor targets. No deeper profile targets or raised berms. Original ford/footbridge cross-sections and roads retained; 5,733 native samples changed. Short-scale incision-width ripple RMS 0.73353 → 0.04190 m (94.29% reduction).
- **Matched water/placement:** converged conservative offline rebake, 0.8 m³/s original inflow, mean/depth/current and geographic masks updated together. Ford surface −2.657 cm, depth 7.543 cm over unchanged ground. River/outlet meshes 50,248 / 30,356 triangles. Re-seated 700 supports vertically; all 90,903 authored XY placements and road transforms retained. Existing deformation profiles and WPO remain; no C++ or movement tuning.
- **Result/evidence:** `BENMORE_CHANNEL_SHAPE_OK`, saved/reloaded `L_Benmore_GaeaReview`, backup `L_Benmore_BeforeChannelShape`. All 4,068,289 packed native samples match candidate hash `d2706ef14458f2915a8357a76d78effde2647bcf0d549693a9f9f6cc08e59fa5`; 33 collision checks max error 0.0811 cm; four coverage queries passed. Twelve Unreal comparisons and sampler passed: Plan RGB change 18.93/255, bare bed 16.82/255 (exposure/vegetation not frozen). Actual overhead/bare views show continuous banks. Reports/renders: `Art/Export/BenmoreGaea/ChannelShape`; full controls/scripts in `docs/BENMORE_RIVER_LIFE.md`.
- **Tests/open:** required `terrain` ran once before import: FAIL forward bog escape and step-11 held-rut exit on the independent test map; ford/water gates passed. No C++ rebuild/module change or duplicate shared-owner full suite. Native terrain/flow/install checks passed; Benmore driving, quiet-machine timings and accepted realism remain unchecked. Pre-existing shading seam, circular water normals and lake coverage/joins remain; coordinated ambient-wave rendering and natural channel variety are subsequent work. No FPS/speedup claim. Shared editor sessions were allowed to finish; one editor at a time.

## 88. Benmore river provenance: rejected canal morphology and corrected plan (2026-10-08)

The user rejects the stage-87 straight channel as neither a river nor a stream and requires understanding the Gaea/system workflow before another solution claim. Stopped the proposed lateral bend patch before any map, height, asset or bake changes.

Read-only `Art/tools/audit_benmore_river_provenance.py` confirms the current carve largely replaces Gaea's river network with separately calculated priority-flood paths: only 3.581% of added >10 cm cut overlaps the selected Gaea footprint, and main-path median distance to it is 22.45 m. Gaea's Rivers bed is blended/protected afterward, while water exports come from before the blend; median raw surface clearance against imported ground is 0.721 m, p90 4.492 m. The exact same archived Gaea build has a paired raw bed/surface with median 0.00480 m clearance, not a ready gameplay water model. Crossing reach sinuosity 1.00125, grade 6.80%; fixed-bed water simulation cannot generate natural bank morphology.

All four source/candidate/map hashes unchanged; audit passes and a data figure was inspected. Reports/plot: `Art/Export/BenmoreGaea/review/RiverProvenance`. No Unreal render/run, rebuild, regression or timings for this read-only diagnosis. Replacement gates in `docs/BENMORE_RIVER_LIFE.md`: reference/course/bankfull corridor, coherent final Gaea output pair, one native deformable dry/wet creek study with reconciled crossings, matched flow/render/query data, then bounded interaction and scale/profile. Morphology remains unaccepted; no implementation/realism/performance success claim.

## 89. Benmore Gaea creek course and native gravel banks (2026-10-08)

Regional direction is shallow runs, an uneven grey gravel corridor and inside bars, with a single channel and tributary joins in narrow hillside reaches. References: [DOC Project River Recovery](https://www.doc.govt.nz/documents/conservation/land-and-freshwater/Freshwater/PRR/prr-strategic-plan-2006-2012.pdf), [DOC upper Waitaki vegetation study](https://www.doc.govt.nz/documents/conservation/land-and-freshwater/Freshwater/braided-river-vegetation.pdf), and [ORC Manuherekia instream habitat assessment](https://orc.govt.nz/media/15449/instream-habitat-and-minimum-flow-requirements-in-the-manuherekia-river-2016.pdf). This is a regional art interpretation, not a surveyed watercourse reconstruction.

The separate `review/CoherentCreek/Benmore_PairedCreek.terrain` applies protected erosion before Rivers and exports bed/surface/depth/mask from the same final Rivers node. Gaea 2.3.0.1 Swarm built successfully. Its raw Rivers Out raises some ground by about 9 m and was rejected for direct import. Mask-confined extraction instead restores Gaea's upper course, resampled at 2 m with about 4 m raster smoothing. Native cross-sections refine the protected original terrain with asymmetric inside shelves, tighter outside banks and no raised berm. The retired upper trench is restored. The tested lower outlet remains west of X=-875 m and joins near X=-843 m, where course separation is under 3 m, through a 65 m transition. This avoids forcing raw Gaea channels across protected road/shoreline grades. Earlier full-Gaea lower-route trials were rejected and never imported. This is authored bank geometry, not sediment transport or bank migration.

**Installed and verified:** `BENMORE_GAEA_CREEK_OK`, clean save/reload in `L_Benmore_GaeaReview`; all 4,068,289 packed native heights match, 33 collision supports max error 0.07391 cm, four water coverage/query checks, road transforms/original drive hash and tuned deformation/WPO preserved. Re-seated 1,654 supports, relocated 4,721 bank instances, reconciled ford/bridge. Sourced CC0 grey gravel and geographic masks retained. Temporary preview water materials are cleaned before saving, fresh-load asset parents/rendering verified; local optics fade to the bake over 6 m.

The existing conservative fixed-bed solver was rebaked on the exact quantized native bed with the existing authored 0.8 m3/s total discharge. At 4,200 simulated seconds the visible channel is stable over a 200 s window: maximum depth drift 0.001964 m and velocity drift 0.004610 m/s, conservation residual -3.73e-11 m3, positivity correction zero, connected to the lake, no artificial wet corridor edge. **Discharge is not fully converged:** final outflow 0.73927 m3/s versus inflow 0.8 m3/s, with storage continuing outside the visible channel. `flow-report.json` deliberately retains `converged:false`. The installed time-averaged fixed-bed bake is a stable visual reference, not catchment hydrologic equilibrium or a calibrated regional river. Offline pruning retains 50 m around wet water/course, removed only 1.056e-9 m3 and leaves 268,362 offline cells; runtime interaction remains 9,216 cells, 60 m span, 0.625 m spacing. River/outlet static surfaces contain 56,753 / 29,791 triangles, sampled at 0.625 / 1.25 m, with finite geometry, positive areas and zero stored mean-surface/query error.

Twelve same-camera Unreal before/after stills were captured, including wet/bare overhead, reach, bed and ford. Inspected overhead views show the winding course in place of the straight trench; bank views show the broader uneven gravel shelves. The river/gravel are still an owner-review candidate, not accepted realism. A fresh-load render exposed black water from serialized editor-preview dynamic material overrides whose field/detail textures are transient. The installer now restores asset parents and clears preview sections before saving; VerifyOnly saves clean parents, reloads, verifies those parents, then captures and discards transient preview overrides. Final clean-load parent checks and wet renders passed. A 6 m optical blend between baked and local depth/current, with local foam/sediment faded at the same boundary, provides a gradual optical transition at the local-window perimeter; remaining shading changes are still visible in the bank views. Geometry/query/physical solver are unchanged. No added texture samples. Still sampler passes: mean absolute RGB changes Plan 14.04/255, Plan_Bare 10.17/255, Reach 19.76/255, Bed_Bare 28.49/255, Ford 18.79/255. Cameras and water clock match; exposure/vegetation are not completely frozen, so pixel differences do not isolate shape or measure realism. `Gaea_Bank_Comparison.png` is the compact actual-render comparison; `Gaea_Creek_Comparison.png` contains five view pairs.

Required `bash Art/suite.sh terrain` ran once: **FAIL on held-rut exit (step 11)** on its independent test map; ford/water/float/carry/winch gates passed. Result retained in `GaeaCreek/terrain-regression.txt`; tuned physics were not altered to get a pass. No native C++ change or additional module rebuild/tests for this asset/material stage. Shared editor tests were allowed to finish; no second Unreal process or duplicate shared full suite. Owner-driven crossing/bridge approaches, Gaea/outlet join inspection, discharge equilibrium, regional art acceptance, inherited circular ripple normals, lake/shading defects and quiet-machine FPS/GPU profiling remain open. No driving-feel, runtime performance or measured speedup claim.

Controls/scripts and detailed evidence: `docs/BENMORE_RIVER_LIFE.md` stage 89, `Art/Export/BenmoreGaea/GaeaCreek`.

## 90. Whole-course correction after shape rejection (2026-10-08)

The user rejected stage 89's straighter course; its artistic status remains unaccepted. Stage 90 replaces the roughly 600 m retained lower route plus the middle course with larger unequal authored bends, broader shallow floors and asymmetric native gravel shelves. Gaea headwaters/junctions retained; this is an authored regional interpretation, not simulated channel migration or a surveyed river. 26,501 native samples changed, maximum terrain cut 2.50 m; water depth was not the goal. The outside-native scenery mouth bed and masks now join the same solver bed. Roads and original drive map are unchanged.

**Installed/checked:** clean native hash `a89e743fe49a971afe77545fa075a6b2d0390ecb9b706b9fc78b51b6c02f2812`, 33 native plus 2 exterior collision supports, matching baked/render/query water, re-seated supports and bank dressing, reconciled crossings, preserved deformation profile/WPO and clean saved water parents. At 4400 simulated seconds, 200 s maximum visible depth/velocity drift is 0.000024 m / 0.000085 m/s; conservation residual -9.64e-11 m3, positivity correction zero, lake-connected and zero artificial wet-edge cells. Final outflow 0.79926 against authored inflow 0.8 m3/s; `converged:true`. This is a conservative fixed-bed bake, not regional hydrologic calibration, erosion or sediment transport.

Actual whole-course/lower wet and bare captures and pixel sampler pass. The required terrain regression **PASS** (270 s), independent test map. Runtime cell/span settings and tuned physics are unchanged. Artistic acceptance, owner-driven crossings, inherited water shading/ripple defects and quiet-machine profiling remain open. Controls/evidence: `docs/BENMORE_RIVER_LIFE.md` stage 90 and `Art/Export/BenmoreGaea/CourseRevision`.


### Benmore morphology research after stage 90 rejection (2026-10-08)

The owner rejected the installed stage-90 shape as unnatural. Its import,
conservation and regression results remain valid; visual acceptance failed.
The audit found both banks tied to one spline, a flat central floor and forced
monotone bed grade. The fixed-bed bake cannot form bars or migrate banks.
Pre-incision native grades along successive reaches are 14.53%, 8.11%, 4.78%,
1.89%, 1.07% and 0.86%; one smooth gravel-river shape is inappropriate throughout.

Regional ORC Lindis/Cardrona/Kauru aerials and cross sections were inspected.
The correction method uses terrain-constrained reaches, independent gravel-bed
boundaries, discrete tapered bars, separate low-flow grooves and local bedform
relief, followed by a bake over the exact quantized native floor. Gaea supplies
the drainage/erosion/sediment scaffold; retaining only a line discards useful
morphology. See `docs/BENMORE_RIVER_LIFE.md`, "Shape research after stage 90
rejection", for sources, construction steps, assumptions and acceptance gates.

An isolated 240 m geometry experiment now works numerically: independent banks,
three bar bodies, a split/rejoin and shallow bedform relief, at 1.240079 m spacing
and 1/64 m quantization. At 1200 s, inflow/outflow 0.8/0.799975 m3/s; 200 s
depth/velocity drift 0.00004087 m/0.00015617 m/s; conservation residual
-6.82e-13 m3, no positivity correction, connected outlet and no wet side boundary.
Finite-volume face fluxes verify a flowing secondary thread (about 0.08 m3/s
beside the primary about 0.72 m3/s at x=30 m). These are experiment values.
Its dimensions are authoring choices; the Lindis source figure has no scale.
This is a fixed-bed geometry study, not simulated sediment/bank migration,
an installed Benmore correction or accepted realism.

`Art/tools/study_benmore_river_morphology.py --audit --study-seconds 1200` writes
only `Art/Export/BenmoreGaea/review/MorphologyResearch`; inspected diagnostic
figures are `Reach_Diagnosis.png` and `Channel_Anatomy_Study.png`. Reports retain
quantitative/provenance data and unchanged installed-course input hashes.
No binary/map asset or tuned/runtime physics change, Unreal launch, engine
regression run or performance claim. Applying the method to native Landscape,
rebaking, reconciliations and actual level/drive validation remain to be done.


## 91. MudRunner MRP: physically based mud (all surfaces), ORH packed arrays with baked AO, parallax occlusion on the mud ground (2026-10-08)

docs/MUDRUNNER_LESSONS_PLAN.md MRP, docs/MUD_VARIANTS.md ("Physically based mud, parallax occlusion"). The owner at the
world-reacts gate: "That is far too glossy, we need pbr and occlusion mapping for detail. ensure it is optimised." No cost or
timing measured (the owner's); static shader stats only. No game was open at any MRP run; a foreign Unreal (a Codex Benmore script, then a terrain test) was waited out twice with a background wait loop.

- **The ORH maps** (`Art/bake_mud_orh.py`, system Python, about 5 s a variant): from each variant's 16-bit height (the 0-1 height
  over `height_range_cm`, 2048 px over 3 m: 0.146 cm a pixel), horizon AO - 16 directions, 11 integer steps to 6 cm (41 px,
  wrapped: the tiles are tileable), per direction the largest sin of the horizon's elevation above level ground x (1 - (r/R)^2),
  AO = 1 - their mean - written as `T_MS_Bog<V>AO.png` beside the bakes; then `T_MS_Bog<V>ORH.png`: R the AO, G the roughness
  remapped `r' = 0.45 + (r - 0.14) x 0.5 / 0.77` clamped 0.45-0.95 (exactly invertible over the bakes' 0.149-0.902; the PBR 0 paths
  use `r = 0.14 + (r' - 0.45) x 1.54`), B the 0-1 height. `bog-orh.json`: AO mean / p5 Standard 0.868 / 0.608, Firm 0.859 /
  0.695, Deep 0.966 / 0.893, Stony 0.898 / 0.722; roughness p5/50/95 Standard 0.22/0.38/0.86 -> 0.50/0.61/0.92, Firm
  0.58/0.75/0.90 -> 0.74/0.85/0.95, Deep 0.15/0.25/0.62 -> 0.46/0.52/0.76, Stony as Standard; the colours' linear luminance means
  Standard 0.045, Firm 0.063, Deep 0.032, Stony 0.048 (linear RGB 0.071 0.040 0.019 / 0.088 0.058 0.033 / 0.049 0.029 0.014 /
  0.070 0.044 0.023): wet mud's band (0.65-0.8 x the dry soil's 0.05-0.25: 0.0325-0.2) holds Standard, Stony and Firm (Firm in
  the dry band too); Deep sits at its dark edge (0.032). Not changed: the owner approved the colours.
- **The array**: `import_mud_variants.py` gains the channel `ORH` (linear, TC_BC7: three uncorrelated channels, where BC1's
  5:6:5 endpoints would step the parallax's height), `TA_MS_BogORH`, 4 slices of 2048; Rough and Height stay imported (M_GT_Snow
  is a copy of the older mud graph and still names them). One BC7 array (1 byte a texel) in place of two BC1 arrays (0.5 each):
  the same memory, one sample a tiling fewer, the AO added.
- **The switches** (C++, `UGTTrackPaintSubsystem`): `gt.Mud.PBR` (1), `gt.Mud.POM` (2; 0/1/2) and `gt.Mud.POMShadow` (1) written
  into MPC_TrackPaint's new `MudPBR`, `MudPOM`, `MudPOMShadow` (live_mud_style.py and mud_cover.py add them; defaults 1 / 2 / 1)
  by WriteSwitches when they change, as MR1's switches. `AGTMudPatch::Tick` pushes the rut water's table (CurrentWaterTableCm,
  -10000 when no water is drawn) onto the mud's own instance as `MudWaterTableCm`, so the parallax can skip the pixels under it.
- **The value pass** (old -> new; gt.Mud.PBR 0 gives the old values back):
  - **mud ground** (M_GT_Mud, live_mud_style.py): roughness the bake's (Standard slurry 0.22-0.38, Deep 0.15-0.28) -> the ORH's
    remapped (slurry 0.46-0.61, lump tops 0.89-0.95); the weather's wetness took it to min(r, 0.48) on worked ground -> toward
    the saturated surface `wetR = lerp(MudWetRoughLo 0.45, MudWetRoughHi 0.65, (r' - 0.45) / 0.5)` by wet x (0.5 + 0.5 worked);
    the fresh sheen took it to min(r, 0.5) -> toward wetR; floor 0.4; the darkening unchanged (wet 0.65-0.82x, fresh 0.85x); the
    far gloss fade (toward 0.65 from 6-12 m) -> off (the static switch `FarGlossFade` now defaults off; PBR 0 applies it as
    before); AO (ORH R x `MudAOStrength` 1) -> the Ambient Occlusion pin (the surface's new `Occl` output through a OneMinus: 0
    where a copy of the graph does not write it, so M_GT_Snow keeps AO 1) and a cavity tint `MudCavityTint` 0.15 (the colour x (1
    - 0.15 (1 - AO))). The landscapes' apron round each patch (M_GT_Landscape, M_LiveLandscape, M_VariantsLandscape): the same
    ORH roughness and cavity tint (no AO pin: it feathers into the clay), PBR 0 the bake's own.
  - **rut water** (M_GT_MudWater, MR3's wrapper): Specular default 0.5 (F0 0.04) -> `WaterSpecular` 0.25 (F0 0.02); settled
    `SettledRough` 0.07 falling to `SettledGlossRough` 0.03 at a grazing angle -> `SettledRoughPBR` 0.15 flat, with a ripple
    normal (tangent space: the analytic gradient of two value-noise octaves at `RippleCm` 6 and 0.43 x it, turned, drifting
    `RippleSpeedCm` 0.6 a second, slope `RippleSlope` 0.05); `SettledFresnel` 0.45 extra opacity at a grazing angle -> none;
    churned `TurbidRough` 0.35 -> `TurbidRoughPBR` 0.5 (opaque 0.95 as before); froth `FrothRough` 0.3 plus a `FrothGlint` 0.35
    highlight -> `FrothRoughPBR` 0.6, no glint. With gt.Mud.MuddyWater 0 and PBR 1 the pools take the settled PBR water (before:
    the base node's water untouched, roughness 0.12 -> 0.08 at a grazing angle, FresnelOpacity).
  - **car mud** (M_GT_Vehicle's Grime, setup_m1_body.py): `WetRough` 0.3 -> `WetRoughPBR` 0.5, dry `DryRough` 0.9, the bake's
    roughness swinging it +-0.07 -> +-0.025, held in the bands (wet 0.45-0.55, dry 0.85-0.95); the clear coat already ClearCoat x
    (1 - DirtMask): 0 under full mud; cavity tint `CavityTint` 0.15 and the AO on the Ambient Occlusion pin (`MudAO`, 1 off mud);
    after MF_Weather a floor node (`Mud roughness floor (MRP)`): lerp(R, max(R, 0.45), DirtMask) - the weather's wet path takes
    porous surfaces toward 0.15 (rain on the mud, or the car's local wetness). **Tyres** (M_GT_Tyre): wet 0.3 -> 0.5, the cavity
    tint and AO, the same floor after the weather. **Glass** (M_GT_Glass): mud splats drew the pane's roughness 0.05 -> wet 0.5 to
    dry 0.9 under the splats (the static stats did not move: the glass's default translucency lighting takes no specular).
  - **carried mud** (MF_MudCover, mud_cover.py): dried max(r, `MudDryRough` 0.88), wet min(r, `MudWetRough` 0.32) with r the bake's
    -> dried clamp(max(r', 0.88), 0.85, 0.95), wet the saturated surface (0.45-0.65); the cavity tint; a new function output
    `AmbientOcclusion` (1 off the cover) wired to a ground material's Ambient Occlusion pin where it was free (all four:
    M_GT_Environment, M_GT_Landscape, M_LiveLandscape, M_VariantsLandscape). The rerun now keeps the function's inputs and outputs
    (their nodes, so every call keeps its links) and rebuilds what lies between (MR1's rerun changed only the code). **Splat
    decals** (M_GT_MudSplatDecal): wet `MudWetRough` 0.30 -> 0.45-0.65 by the ORH, dried 0.88 -> 0.85-0.95, the cavity tint (no AO
    pin on a translucent deferred decal).
  - **clods** (M_GT_Clod): already in the bands (dry 0.85, wet 0.45, fresh 0.5): unchanged.
  - **Removed** (each behind gt.Mud.PBR 0 now): the rut water's grazing-angle gloss (0.07 -> 0.03) and its Fresnel opacity boost
    (0.45), the froth's glint highlight, the slurry's 0.15-0.38 roughness, the fresh sheen's and the weather's falls to 0.48 / 0.5,
    the car's and the carried mud's 0.30-0.32 wet roughness, the glass splats' 0.05, the weather's 0.15 on mud (the floors). No
    mud surface had an emissive (M_GT_Mud's is its diagnostic only).
- **Parallax occlusion** (M_GT_Mud only, `POM_HLSL`): after the uv setup and before the samples; a struct `GTMudPom` reads the height
  (ORH B) in the field normal's dominant projection - the top face as the sample blends its two tilings (the tiling the mix noise
  leaves out is not read: one sample where the mix is 0 or 1), a wall at tiling A - with SampleGrad and the un-slid uv's
  derivatives. The ray: V from the eye to the displaced surface point, its descent dot(V, n) clamped to -0.2 (grazing), its slide
  the tangent-plane part / -dot x `MudPomDepthCm` 3 x the fade. Steps: POM 1 `MudPomMinSteps` 8; POM 2 from `MudPomMaxSteps` 16
  at a grazing angle to 8 looking straight down; both toward the minimum over the fade; a linear refine between the last two. The
  fade: 1 inside `MudPomNearM` 6 m to 0 at `MudPomFarM` 14 m, x 0 where the rut water stands over the pixel (fading over its last
  1.25 cm); `[branch]` on POM > 0.5 and the fade, so nothing is marched past 14 m. The hit's slide moves every lookup: both top
  tilings (B by its turn) and the two walls. The self-shadow (POMShadow, within `MudPomShadowM` 4 m, faded over its last
  quarter): 4 steps from the hit toward the sun (Sky Atmosphere Light Direction 0) at 0.8 / 0.6 / 0.4 / 0.2 of the hit's depth;
  shadowed by 6 x how far the surface stands above the ray; the colour x (1 - `MudPomShadowStrength` 0.45 x it).
- **Shader stats** (`Art/Unreal/mud_pbr_stats.py`, get_statistics at PCD3D_SM6, before -> after; pixel / vertex instructions,
  samplers): M_GT_Mud 503 -> 742 / 264, 7 -> 6; M_GT_MudWater 2515 -> 2602 / 339, 8 -> 8; M_GT_Vehicle 731 -> 750 / 245, 11 -> 10; M_GT_Tyre 321 -> 341 / 314, 5 -> 5; M_GT_Glass 443 -> 443 / 339, 3 -> 3; M_GT_Landscape 305 -> 319 / 155, 7 -> 6; M_GT_Environment 357 -> 371 / 155, 8 -> 7; M_LiveLandscape 477 -> 493 / 155, 10 -> 8; M_VariantsLandscape 477 -> 493 / 155, 10 -> 8; M_GT_MudSplatDecal 405 -> 415 / 344, 5 -> 6; M_GT_Clod 262 -> 262 / 148, 3 -> 3.
- **The check** (`check_mud_variants.py`, an MRP phase after MR3; `check_car_washed.py` at 74 m): the look pictures and the buffer
  dumps (HighResShot's `0 0 0 0 0 1 1` arguments: the overview buffers `r.BufferVisualizationOverviewTargets
  BaseColor,Roughness,MaterialAO` dumped as uncompressed EXR, `r.SaveEXR.CompressionQuality 0`, `r.PostProcessingColorFormat 1`),
  read by `Art/sample_mud_pbr.py` (a numpy EXR reader; the gravel's known 0.9 checks the encoding).
- **The runs** (each alone; no game open; the process state checked before each): the AO bake; the before stats; the import
  (5 arrays, ORH created; the known shutdown fault after a fresh report); `bash Art/build.sh` (Succeeded, 48 s); the mud tests;
  `& Art/setup_mud_carry.ps1` (MPC +MudPBR/MudPOM/MudPOMShadow; MF_MudCover rebuilt between its pins, 31 expressions; AO wired on
  all four ground materials); `& Art/setup_live_mud_drive.ps1` (M_GT_Mud, M_GT_Landscape, M_GT_MudWater, M_GT_Clod, L_MudDrive,
  M_LiveLandscape; BogR/BogH and their parameters retired); `& Art/setup_mud_variants.ps1`; the car (`run_body_masters_gpu.py`:
  setup_m1_body + setup_m1_masters in one editor run with a real RHI, so the HLSL compiles; 6/6 masters through MF_Weather); the
  after stats (every listed material compiled); `& Art/check_mud_variants.ps1 -AllowGame` twice (the first run's close-up looked
  into the +Y rut's shadow, 74 % of it under 20 of 255: the camera moved 3.2 m right onto sunlit untouched mud and the check was
  rerun); `& Art/check_car_washed.ps1 -AllowGame` (the wet car's captures); the suite. Every setup log's "Failed to compile" lines
  are the custom nodes' transient "missing input" while the graphs were being wired; none after.
- **PBR rows** (`pbr-rows.json` in Art/Export/MudVariants and Art/Export/LiveMudDrive; the dumps linear, the gravel 0.898 against
  0.9): ground roughness p5 / median / p95 - Firm 0.741 / 0.886 / 0.945, Standard 0.502 / 0.643 / 0.918, Deep 0.455 / 0.510 /
  0.682, Stony 0.502 / 0.608 / 0.918, L_MudDrive's Standard 0.502 / 0.671 / 0.918, none under 0.40 (PASS); AO mean / p5 0.864 /
  0.725, 0.874 / 0.659, 0.975 / 0.918, 0.898 / 0.737, 0.857 / 0.612; base colour luminance 0.063, 0.045, 0.032 (Deep, just under
  the 0.0325 wet-soil floor), 0.048, 0.046. Car mud wet (L_MudDrive at 74 m, MudWet 0.89) 0.451 in every pixel of the sill band -
  the weather's wet path (the car's local wetness) took it lower and the floor holds it at 0.45 (PASS); dry (MudWet 0, L_MudVariants)
  0.886 / 0.898 / 0.910. Rut water (a model: translucent, not in the GBuffer) median 0.272, lowest 0.15 over 121 cells (PASS).
- **Pictures** (no game): Mud_PBR_OnFoot / _POM0 - matte mud, no sheen on the slurry or the rut floors, the parallax visible only
  in the near metres (mean difference 6.6 of 255), no crosswise far bands with the far fade off (so it stays off); Mud_PBR_Close /
  _POM0 (60 cm, 25 cm up) - POM 0 flat plates, POM 2 lumps standing up out of the mud, hiding what is behind them, dark shadowed
  fronts (mean difference 14.3); at full size fine stair-stepping on the steep flanks of the largest lumps, serrated silhouettes
  in places, near-black undersides that push Standard's lumps toward stones set in mud; Rut_Settled_PBR - a murky see-through
  brown film, a faint soft sheen, no mirror, the ripple not visible at 3.4 m; Car_Muddy_PBR - the dried coat matte; L_MudDrive's
  Car_PreFord (wet) - a darker matte coat, no highlights. Nothing reads as glossy.
- **Tests**: `& Art/mud_shape_test.ps1 -AllowGame` 13 of 13 GrandTour.Mud and GrandTour.Snow Success, CRC 8e0aad06. Suite `terrain drivetrain grip mud surface track body bodystate`: 7 PASS, terrain FAIL at step 11's held exit (6 m in 6.3 s against 4.7 s unheld: "slower than down the ruts 0"), FAIL again on the one rerun (5.9 against 3.9 s) - the standing failure since MR2 (MRP changes no physics).
- **Open**: the owner A/Bs gt.Mud.PBR / POM / POMShadow and measures the cost. As seen: the parallax's stair-stepping on steep lump
  flanks at a grazing camera (`MudPomMaxSteps`, `MudPomDepthCm`), the shadowed undersides' darkness (`MudPomShadowStrength`,
  `MudAOStrength`); Deep's colour at the dark edge of the soil range; the landscapes' carried mud and apron under rain still go
  through MF_Weather's shared wet path (toward 0.15: no floor there; the checks run dry); the glass's splat roughness is compiled
  out of its default translucency lighting.
- **Follow-up** (the main session's look at Mud_PBR_Close: step bands on the larger lumps' flanks; the owner's rain question):
  POM_HLSL's step search reads the height one mip up (`GTMudPom::H`'s derivative scale 2), then `MudPomRefine` 5 binary halvings
  at full resolution and a secant between the bracket's ends; `MudPomGrazingMinSteps` 12, the steps' floor at a grazing angle (8
  looking down, 16 at most), the fade cannot take them under it; `MudPomSteepCap` (0) shrinks the depth where the relief's slope
  (full-resolution differences over 5 mm) runs 0.75-2.5, four more samples when on. Tried at 0.6: Mud_PBR_Close_Steep (the
  close-up's spot from 80 cm back, 29 cm up, about 20 degrees) kept the same band pattern on the steepest flank with and without
  it and with gt.Mud.POMShadow 0 (Mud_PBR_Close_Steep_NoShadow, 0.27 of 255 apart), so it is left off; Mud_PBR_Close is 0.62 of 255
  from MRP's. The bands look like the packed height's BC7 steps (at most 16 levels of a 4 x 4 block's range), untested. M_GT_Mud
  742 -> 917 pixel instructions. MF_MudCover's new `FloorMask` (its cover with gt.Mud.PBR) feeds `MudCover rain floor (MRP)` after
  each ground material's MF_Weather call: max(R, 0.45) x FloorMask x (1 - Puddle) (`mud_cover.rain_floor`, found by desc on a
  rerun; it takes over whatever read the weather's Roughness: the Roughness pin, or the strips' LiveApronRoughness Old); MF_Weather
  unchanged. The ground materials +3 / +4 pixel instructions. Carry_Wet_PBR (the check now drives fresh tracks out of Stony to 215
  m - MR1's tracks are dropped when the track paint's window follows the car to Deep - and holds the test wetness at 1): carried
  mud median 0.451, p5 0.259 (the feathered edges), wet gravel 0.129, a puddle 0.03. 13 of 13 Mud and Snow, CRC 8e0aad06. One check
  run crashed out of video memory during MR3 (no other GPU user found); the one rerun passed.
- **Follow-up 2** (the main session's test of the BC7 theory): the parallax's height in TA_MS_BogHeightPOM (BC4, TC_Alpha, from
  the 16-bit bakes; the old TA_MS_BogHeight stays for M_GravelLandscape), the AO and roughness in TA_MS_BogOR (BC5, TC_Normalmap,
  read raw); every former ORH reader reads OR (+ the height array where it needs a height); ORH no longer built. M_GT_Mud 917 ->
  919 pixel instructions, 6 -> 7 samplers. Memory (4 x 2048 with mips): ORH 22.4 MB; OR 22.4 MB (the engine's figure 22.41 MB) +
  HeightPOM 11.2 MB (arithmetic; the engine reported 4 KB, not resident in that run). Mud_PBR_Close_Steep's flank bands: the same
  with BC7, BC4 and an uncompressed G8 test array (0.48 / 0.74 of 255 from BC7's picture) - not the compression: the bakes' lump rims
  are near vertical (up to 8 % of the height range per texel) and the parallax stretches those few texels over the flank. Stopped as
  asked; BC4 kept. 13 of 13 Mud and Snow, CRC 8e0aad06.
- **Follow-up 3** (soft parallax height, one ORH pack): ORH's B is a soft-rimmed parallax height (`soft_rims`: slope cap 1.5 % of the range per texel from the mean of the two cone envelopes, then a 1.5 texel Gaussian; max slope per texel Standard 23.6 -> 1.5 %; Firm 23.1 -> 1.5 %; Deep 22.1 -> 1.5 %; Stony 17.7 -> 1.5 %); the readers are back on ORH (follow-up 2's split undone; M_GT_Mud 917 / 6 samplers); OR, HeightPOM, HeightPOM8 left unreferenced on disk. Mud_PBR_Close_Steep: flank bands gone; dotted dark lines along some lump feet and serrated shadowed edges remain; the lumps still stand up with occlusion, lower and softer. New `UGTMudArtLibrary::TextureAllMipsBytes` (CalcTextureMemorySizeEnum(TMC_AllMips) after BlockOnAnyAsyncBuild): bog arrays 53.4 MiB, all mud material textures 135.9 MiB, snow 62.2 MiB. Two check runs ended out of video memory (one with r.Streaming.PoolSize 1500, `check_mud_variants.ps1 -PoolSize`): D3D12 held 26.7 GB of UAV buffers at the crash, textures 253 MB - not the textures; cause unchecked. 13 of 13 Mud and Snow, CRC 8e0aad06.


## 92. Native bed-first morphology installed (2026-10-09)

Owner authorized applying the morphology study after rejecting stage 90's
regular ribbon. Target: `/Game/GrandTour/Demo/BenmoreRoads/Gaea/L_Benmore_GaeaReview`;
assets and exports in `Gaea/Morphology` and `Art/Export/BenmoreGaea/Morphology`.
Backup: `/Game/GrandTour/Demo/BenmoreRoads/Gaea/L_Benmore_BeforeMorphology`.
This is an authored regional interpretation using Gaea's drainage, not a surveyed
Otago reconstruction or a sediment/bank-migration simulation. Owner visual and
driving acceptance remain open.

- Bed: retire the stage 90 middle/lower S-bend controls; retain Gaea's valley and
  tributary topology. Gravel margins use separate controls from the low-flow
  groove. Five tapered bar bodies, two unequal short split/rejoin grooves,
  attached point bars, narrowing reaches and shallow local riffle/scour relief.
  Native 2017-square Landscape at 1.240079 m spacing,
  1/64 m height quantization. Maximum incision below pre-incision terrain
  1.90625 m; 31134 samples changed
  relative to stage 90. This is bed seating, not a deeper-water target.
- Bake: final terrain is quantized first. A **cold start**, initially dry native
  creek with only the lake wet, receives 0.36/0.22/0.22 m3/s at three sources.
  6000 simulated seconds; outflow
  0.79989274 against inflow 0.8 m3/s. Mass residual
  5.09e-11 m3, positivity correction zero. Last 200 s visible
  depth/velocity drift 6.86e-07 m /
  8.48e-05 m/s. Lake connected, zero artificial
  boundary cells over 5 cm; maximum boundary film 0.00999 m.
  Offline grid 155760 cells, 35 m valley radius and at least 19 m
  beyond the widest gravel bank. This is a bounded creek bake, not hillside runoff.
- Water depth (native river wet cells): median 0.11898 m, p95
  0.33213 m, maximum 0.45312 m. Stage 90 was 0.14935 / 0.36507 /
  0.53497 m. Sampled sections include actual flowing splits. Their interpolated
  discharge estimates are diagnostics, not conservative face flux measurements.
- Exact bed match: 0.0 m error between baked
  floor and native triangle interpolation. Saved/reloaded Landscape checksum
  `eb27dbd5a904d44f0a27e0dba032d114d465387f8c856f45892df518f79efae6`. Geometry, wetness, materials, water queries and
  crossing placement share this bed. No static native riverbed replacement.
  The existing scenery apron alone is rebuilt outside X=-1250 m.
- Materials/placements: retain sourced CC0 mineral textures; geographic bar and
  rocky-reach masks keep coarse gravel on dry deposits. Place review-owned bank
  vegetation outside the active gravel bed. Re-seat 3310 supports and relocate
  4721 review-owned bank instances; remove
  28 ordinary plants from water. Rebuild the
  bridge and approaches. Ford query depth 0.22011 m.
  Road transforms/count, original Drive map checksum and all tuned crossing
  deformation values pass preservation checks. Deform WPO remains connected.
- Runtime: existing 9216-cell / 60 m / 0.625 m local interaction field retained.
  No runtime C++/vehicle/mud/snow tuning or new map-wide live fluid simulation.
  Native water mesh 59923 triangles; outlet
  21893. These counts are not a frame-time claim.

**Visual check:** Inspected actual Unreal Ford, Reach, Lower, Lower_Bare, Bars, BarGround and FullCourse captures. The whole-course view shows Gaea-aligned narrow headwaters and tributaries, then wider lower reaches with unequal split/rejoin sections. The lower wet and bare views show an elongated exposed gravel bar separating two grooves; the ground view shows water rejoining around its tip. Remaining visible issues: the grey gravel border is still too uniform in places, shore edges show native-grid stepping from overhead, and the inherited reflective surface / circular ripple pattern still needs a water-rendering pass. These are visual observations, not a claim of finished naturalism, animation quality, driving feel or performance.

Actual Unreal images are `FullCourse_After.png`, `Lower_After.png`,
`Bars_After.png`, `Bars_Bare_After.png`, `BarGround_After.png`, plus the same
before cameras and Ford/Bed/Reach/Plan views. `pixel-report.json` and
`Gaea_Creek_Comparison.png` compare those captures at a fixed water clock.
Bars mean absolute RGB change 17.23/255;
BarGround 24.47/255.
These establish image changes, not aesthetic acceptance or animation quality.

**Validation:** Python compile, conservative solver gates, exact-floor check,
Unreal import/save/reload, native collision supports, outlet collision,
water coverage/query agreement, WPO and preservation checks passed.
`bash Art/suite.sh terrain` ran once (296 s): **FAIL**, documented step 11 rut-exit
gate: held 6 m in 5.8 s vs down-ruts 5.6 s; "slower than down the ruts 0".
No tuned physics changed or attempted fix for that standing failure. Evidence
in `terrain-regression.json` / `Saved/Logs/terrain_test.log`. No extra module
tests/build: no C++ modules changed. No Benmore driven acceptance or FPS profile.

**Implementation:** `Art/tools/build_benmore_morphology.py`,
`check_benmore_morphology.py`; `--morphology` in the existing packer, Blender
exporter and sampler; `-Morphology` in `Art/benmore_gaea_creek.ps1` / installer.
Fresh build: generator `--prepare --cold-start --seconds 6000`, checker, packer,
Blender exporter, installer, then sampler. A failed settle must resume and pass
before packing. After successful installation use `-VerifyOnly`, not a second
normal install that would re-seat placements again.

**Lessons:** numerical convergence did not establish natural shape. Early
analytic/warm starts and weak junction/turn transitions created off-channel
puddles and films. Correct endpoint extents, terrain seating and final cold-start
validation replaced those attempts; rejected reports are retained. Rendered
water is clipped from solved occupancy, never a bank-width ribbon. Existing
ambient water shading/animation and final owner look/drive review remain open.


## 93. Benmore shoreline and sediment refinement (2026-10-09)

Owner said stage 92 was looking better and authorized continuing. Preserve that
accepted native morphology; this stage changes shoreline rendering and material
transitions in `/Game/GrandTour/Demo/BenmoreRoads/Gaea/L_Benmore_GaeaReview`.
Owned outputs/assets: `Art/Export/BenmoreGaea/ShoreRefinement`, `Gaea/ShoreRefinement`.
Backup: `Gaea/L_Benmore_BeforeShoreRefinement`.

- A 0.625 m signed coverage atlas and matching clipped render meshes reconstruct
  the existing hydraulic occupancy against the native triangle floor. The
  smoothed coverage is bounded to preserve narrow channels. At the validation
  sample spacing the offline mask removes 6.23% of old coverage,
  maximum retreat 0.884 m; added coverage is zero.
  It does not deepen the river or alter the native heights. Surface vertex means
  still use the accepted wet-weighted baked height, with no height offset.
- The local surface uses the same shore atlas, with a bounded visual rim to avoid
  reproducing its 0.625 m occupancy-cell edges. Interior live wet/dry clipping,
  wakes and field WPO remain. This is render reconstruction, not higher-resolution
  physical wetness: vehicle depth/current queries and the serialized domain asset
  are unchanged. The rim is not a new shoreline flooding/erosion simulation.
- Sediment data separates low wet gravel, dry bar cores and higher soil margins
  using height above water, current speed and the existing bar/rock masks. The
  uniform 78% grey mix/gain is replaced with a 42–76% mineral-neutral tint,
  lighter clean gravel and stronger wet darkening. Existing sourced CC0 mineral
  albedo/normal/roughness remain;
  no generated art textures. Ecology path/vegetation channels remain identical.
- Native Landscape R16 SHA after save/reload:
  `eb27dbd5a904d44f0a27e0dba032d114d465387f8c856f45892df518f79efae6`.
  All authored instance transforms/counts, road transforms, tracked deformation
  settings, water-domain asset bytes, fixed-point queries, local solver settings
  and original Drive map SHA compare equal before/after. Deformation WPO stays
  connected. No C++ or tuned physics edits; no new native static bed overlay.
- Runtime simulation remains 9216 cells / 60 m / 0.625 m. Static native surface is
  68183 triangles (stage 92: 59923); outlet
  21893 (unchanged). This visual pass is not a measured
  performance improvement. No FPS or Benmore driven acceptance claim.

**Actual visual inspection:** Inspected the final actual Unreal Ford, Bars, BarGround and FullCourse captures against the pre-pass views, plus the first-iteration Lower view. The large cell-shaped steps along the near water edge are reduced; the grey border is less continuous, the dry bar is lighter than the damp shore, and the higher margins return toward the surrounding warm soil. Both lower branches and their rejoin remain visible, with the accepted whole-course route retained. Some angular shoreline segments remain at distant bends/bar tips. Broad sky reflections and the inherited circular rain-ripple normal still make parts of the water read too much like a quiet pond. Sourced mineral grain remains visible close up but is not a finished large-stone bed treatment. Sky/cloud and vegetation wind animation were not frozen, so changes to lighting/leaf silhouettes in the paired captures are not evidence of asset edits. Still renders do not establish animation, vehicle interaction or FPS quality.

**Validation:** source hashes and reconstruction bounds, Python compilation,
Unreal material compilation/import/save/reload, native/apron collision support,
unchanged native R16, unchanged placement/query/domain/physics checks passed.
Fixed-camera Before/After images use the same water clock. Pixel differences:
Bars 5.64/255; BarGround
12.27/255. These quantify changes,
not artistic acceptance; sky/cloud animation was not frozen and can affect pixel
comparisons away from the river. `bash Art/suite.sh terrain` ran once (268 s),
**FAIL** at the documented step 11 held rut-exit gate (5.7 s vs 5.5 s down-ruts;
"slower than down the ruts 0"). The run preceded importing this visual-only pass.
No physics adjustment or repeated run to chase that standing failure.

**Reproduction:** `Art/tools/prepare_benmore_shore.py`, Blender background
`Art/Blender/export_benmore_shore.py`, `Art/benmore_shore.ps1`, then
`Art/tools/sample_benmore_shore.py`. The installer reuses guarded library helpers
from `install_benmore_gaea_creek.py`, whose direct-run entry point is now guarded.
After installation, use `-ReviewOnly` for a material/capture retry. Never rerun the
stage 92 normal terrain installer on this revision. Evidence: prepare/install/
pixel/terrain-regression reports, nine paired engine renders, visual-review.txt.

**Remaining:** ambient flow-normal choice and specular/riffle response, visually
reviewed moving-water sequences, Benmore driving and actual frame-time profiling.
Current owner acknowledgement applies to stage 92; this pass awaits their review.


## 94. Benmore current-aligned waves and river surface relief (2026-10-09)

Installed in `/Game/GrandTour/Demo/BenmoreRoads/Gaea/L_Benmore_GaeaReview`.
The owner rejected the old circular ripple motion and perfectly flat surface.
This pass replaces the rain-ring/reset animation with current-aligned numerical
waves and actual vertex displacement. It is a render change, not a new fluid
solver or a deeper river. Owner artistic acceptance is still pending.

`GTWaterAmbient.cpp` and hooks in `GTWaterSheet.h` / `GTWaterDomainSheet.cpp`
produce one shared 256-square RGBA16F height/slope/foam target at 30 Hz for the
Benmore domain. Four surfaces share its texture and absolute clock. Six geometry
bands and eight finer normal-only bands are sampled in four fixed neighbouring
direction/speed bases without periodic UV reset. Procedural numerical data is
the wave plan's approved exception; no new painted texture was made.

The shortest geometry wavelength is 2.91 m on a 0.625 m grid. Amplitude follows
current and depth, stays below 22% of optical depth, fades over the final 10–75 cm
to shore and between 55–180 m viewing distance. Numerical sampled maxima are
5.16 cm on the river and 4.49 cm on the outlet (before distance fade); these are
sampled values, not a physical wave-height guarantee. The absolute bound is
8.235 cm before the depth/shore fades. Fine ripples stay in the lighting.

The outlet render mesh was subdivided on its original triangle planes: 21,893
to 87,572 triangles, with original vertices, footprint and mean surface
preserved. The native river remains 68,183 triangles. Interaction displacement
now samples the existing live field on that continuous river mesh, fading in
through the existing 6 m edge region. It no longer swaps to the offset local
grid in the river; the lake retains its local replacement. This removes the
river grid seam exposed by the first boundary captures. This adds rendering work;
it is not a measured speedup. The background lake remains a coarse engine plane
with normal-only ambient waves. A bounded lake render grid is still needed for
lake geometric relief; this pass does not claim all water is now displaced.

**Validation:** full editor C++ build passed. SM6 material creation and actual
GPU readback passed at two clocks (worst channel error <0.000475), including the
foam alpha convention. One shared target, disable/enable physics independence,
asset parents and save/reload checks passed. All 90,872 authored instances,
57,808 road instances, deformation profiles, physical water-domain asset,
fixed-point water queries, runtime solver settings and original Drive map hash
remain equal. Physical source binary and native height source hashes also match.
The interaction field remains 9,216 cells / 60 m / 0.625 m.

Three CPU regressions passed: `GrandTour.Water.RiverReference`, `MovingDomain`,
`PassiveDetail`. The fixed-step 24-frame impulse comparison is numerically
unchanged. The effect does not alter buoyancy/depth queries. No driven crossing,
runtime frame cadence, FPS or GPU-cost result is claimed. Previous stage 93's
terrain suite had the existing step-11 held-rut-exit failure; tuned traction was
not changed or retuned. The user requested work without timing claims.

Actual engine captures include 60 ambient frames at 12 sampled frames/second,
the impulse, window recenter/join pairs, shallow-angle relief off/on, reach,
bar and lake. The GIF's five-second wrap is a preview loop, not a runtime wave
reset. Clouds and vegetation were not frozen. See `visual-review.txt` for the
image inspection and remaining appearance limits; pixels do not establish
artistic acceptance or vehicle feel.

**Reproduction:** `Art/tools/prepare_benmore_flow_mesh.py`, Blender
`Art/Blender/export_benmore_flow_mesh.py`, `Art/tools/check_benmore_wave_geometry.py`,
`Art/benmore_waves.ps1 -Mode Install`, `-Mode After`,
`Art/water_domain_test.ps1`, `Art/tools/sample_benmore_wave_motion.py`.
Shared Unreal runs must finish before builds or another editor is launched.
The previous blocked attempts made no level change; a later free interval
allowed this build and installation. Backup: `L_Benmore_BeforeFlowWaves`.

Owner comparisons: `gt.Water.Domain.Ambient 0` / `1` toggle only this rendering;
`gt.Water.Domain.AmbientHz` defaults 30, clamped 15–60. Use `stat unit`, `stat gpu`
and `gt.Water.Stats 1` for a future owner profiling pass. Solver statistics alone
do not include the new render-target/material/mesh cost.

Evidence: `Art/Export/BenmoreGaea/FlowWaves/` contains install, geometry, motion,
comparison and current status reports, captures and `Ambient_After.gif`.
Build/test logs are `Saved/Logs/build_benmore_waves.txt`,
`BenmoreWavesInstall.log`, `BenmoreWavesAfter.log`, `water_domain_test.log`.

## 95. Benmore vehicle spray and visible wakes (2026-10-09)

The owner asked for stronger bow waves and more realistic spray. The vehicle's
water emitter now uses its speed relative to the local current, water depth and
excess wheel slip. Both incoming hull corners are sampled independently, including
reverse and sideways travel. A dry corner does not throw water. Emission starts
at 0.35 m/s / 2.5 cm for tyres and 0.6 m/s / 10 cm for the bow. Full rates are
80/s per wet wheel and 100/s across both bow corners, scaled by activity.

`GTSprayWater.cpp` reuses the existing 120-slot water pool. Thin, short-lived
spray fans, smaller ballistic droplets and sparse mist use flight-aligned,
camera-facing engine planes. A dedicated lit material uses numerical feathered
masks, depth fading and individual lifetime opacity; no painted bitmap was made.
Mist gets more drag and less gravity. Water has its own random stream, leaving
the mud/snow stream untouched. Dry dust is suppressed at submerged wheels;
the existing dry-ground dust appearance is otherwise unchanged. The rejected
ellipsoid prototype produced shiny disks; the installed card revision replaces it.

Wheel and bow foam/silt sources feed the existing transported detail field.
Its previously unused B channel holds extra visual wake height, signed around
exact byte 128, at quarter-centimetre precision. Gain defaults to 1.5, bounded
to 18 cm and 35% of reference depth. This amplifies existing physical surface
disturbances only; it does not add mass or change buoyancy, traction or the bed.
Matching finite-difference normals and brighter aeration use the same field.
The saved material already admits the continuous native river into the transported
detail branch; the older generator's local-only condition was not the live cause.
Stage 95 explicitly reconnects the matching normal/roughness/opacity outputs and
gives crest aeration more coverage, opacity and roughness to separate it from the
broad reflected sky. No particle-count increase is involved.
There is no new simulation grid or render target. The 96-square / 60 m interaction
window and stage 94 ambient-wave budget remain in place. This is a bounded visual
effect, not resolved three-dimensional fluid breakup or a measured speedup.

The owner's follow-up asked for more prominent surface waves. The same B upload
now also reconstructs a curved pressure ridge ahead of the immersed hull and
two widening wake crests. Relative travel determines direction, including reverse;
speed and immersion determine strength. At most four source records are retained,
and inactive sources fade within 1.2 seconds. The upload only rasterizes the near-car
region onto existing wet cells. Combined extra height is bounded to +28 cm / -18 cm,
with tighter depth limits and shore fading. This is explicitly a render model
over the physical field, not additional simulated displacement or fluid mass.

**Controls:** `gt.Water.InteractionSpray 0/1` stops/starts new spray;
`gt.Water.InteractionTrails 0/1` controls the extra foam/silt sources;
`gt.Water.WakeRelief 0` removes the extra height, default `1.5` restores it.
`gt.Water.VehicleWaves 0/1` controls the reconstructed bow/wake crests separately
(strength is clamped to 0–2). Disable both height controls for physical-only relief.
Existing particles and transported trails fade after their sources are disabled.

**Installation:** `/Game/GrandTour/Demo/BenmoreRoads/Gaea/L_Benmore_GaeaReview`,
water materials under `Gaea/WaterInteraction`, and
`/Game/GrandTour/Materials/M_GT_WaterSpray`. The spray renderer applies to all
vehicles using `GTSprayComponent`; the extra wake material is installed on Benmore's
four domain surfaces. Backup: `Gaea/L_Benmore_BeforeWaterInteraction`.

**Reproduction:** build with Unreal closed; run
`Art/benmore_water_interaction.ps1 -Mode Install`, then `-Mode Review`, then
`-Mode Tests`, sequentially with no other Unreal process. Summarize with
`Art/tools/summarize_benmore_water_interaction.py`. Capture harness uses the real
GT car and existing physics, a one-time starting velocity, then throttle/brake
inputs. It covers crawl, faster crossing, reverse and dry ground. Sampled GIF
cadence is not runtime FPS. Evidence is in
`Art/Export/BenmoreGaea/WaterInteraction`; final card captures are in `RealismFinal`.

**Validation:** editor build and the four water CPU tests passed (RiverReference,
MovingDomain, PassiveDetail, InteractionVisuals). Install/save/reload comparison
preserves 90,872 authored instances, 57,808 road instances, deformation profiles,
domain asset bytes, physical query samples, solver settings and the original
Drive map hash. Real vehicle captures pass crawl, crossing, reverse, dry ground,
chase view and travel along the river, with no water particles on dry ground and
no water pool overflow. The rendering upload reports nonzero near-car sources and
bounded extra height; this is not a physical-wave-height measurement.

`bash Art/suite.sh terrain spray` ran once on the final C++ behavior. Spray/audio
PASS, including pool bounds and other surface effects. Terrain FAIL at the
documented held-rut-exit comparison: 6 m in 5.3 s with the hold versus 5.8 s down
the ruts, failing the expected slower exit. Ford, raised-water/flooding, held and
carried current, floating and winch gates passed. No traction retuning or repeated
terrain run to chase that result. Logs: `water_interaction_suite.txt`,
`terrain_test.log`, `spraytest.log`, `water_interaction_test.log` in Saved/Logs.

The last material-only adjustment breaks broad aeration patches into smaller
numerical flecks; the persistent detail field carries their large-scale transport.
Fine breakup drifts uniformly and slowly. Applying absolute time to varying local
velocity stretched the trial mask into stripes, so that version was rejected.
The final breakup retains the same height/physics.
Its focused actual-car review uses `-Mode Review -WaveFinish` and writes
`WaterInteraction/WakeFinish`; the six-case functional run remains in RealismFinal.
The final evidence summary selects WakeFinish for along-river images and the
frozen height/normal off/on comparison (foam/spray remain on). Owner visual
acceptance and performance are open.

The first final-material capture hit a D3D device removal/GPU crash. Its diagnostic
reported 4,605 MB local use against a 1,822 MB local budget; this is crash evidence,
not a performance benchmark or proof of the sole cause. The log is retained as
`WaterInteraction/capture-gpu-crash.log`. The focused retry uses a shorter four-second
along-river case and 960 x 600 capture resolution. No persistent renderer settings
or other applications were changed for it.

The shorter retry completed successfully: eight actual-car states plus the frozen
comparison. The final upload spans -7.50 to +17.75 cm in that case. Reviewed captures
show conspicuous patchy aeration and soft wheel spray without the rejected stripes
or shiny disks. Some foam patches remain broad, and the car/shadow hides some
surface relief. See `visual-review.txt` for limits; no finished-realism claim.

## 96. MudRunner MR4: readable soft spots (2026-10-09)

docs/MUDRUNNER_LESSONS_PLAN.md MR4 (the execution block of 2026-10-09; its rim and share lines revised by the main session the same
day), docs/MUD_VARIANTS.md ("Readable soft spots"). What you see is what you feel: one static softness S (0..1) per cell of a bog's
patch, read by the traction and drawn by M_GT_Mud. No field height changes (the mud field CRC stays 8e0aad06). No cost or timing
measured (the owner's); static shader stats only. Foreign Unreal (the Codex app's runs: a UnrealEditor-Cmd, its Benmore water install,
-GTMorphology editors) was waited out six times; Unreal was paused for the Codex app mid-stage (the check then running was ended at its
map load, nothing written); GoWR was open for every run after the pause (the build, both test runs, the terrain test, the check).

- **Scope** (`AGTMudPatch::HasSoftSpots`): `!bHasProfile && Medium == EGTDeformMedium::Mud` - an unprofiled bog's patch or an LM5b
  variant's (bScalesRows keeps bHasProfile false). A ford's or riverbed's profiled patch, snow and any other medium have none.
- **The field** (`AGTMudPatch::BuildSoftness`, at Init; seed `SoftSpotSeed(SectionIndex)` = 104729 (i + 1) + 17): two octaves of
  hashed value noise at 7 m and 3 m (0.65 / 0.35, the lattices turned 0.6 and 1.9 rad), domain-warped by a 9 m noise of 1.5 m;
  remapped piecewise-linear by the percentiles of the patch's interior (cells 2 m or more from the edge): min 0, p5 0.15, p75 0.6,
  p95 0.9, max 1; S = 0.5 + (S0 - 0.5) x the amplitude (`FGTDeformProfile::SoftSpotAmplitude`: Standard 1 with no profile, Firm 0.5,
  Deep 0.6, Stony 0.6, proposed); the rim S = lerp(0.4, S, smoothstep(0.5 m, 2.0 m, d)), d the distance to the nearest edge (the
  outer 0.5 m exactly 0.4, under the look's threshold even in the hollows). A float array on the patch, outside the field and its CRC.
- **The feel** (`UGTTractionComponent::Update`, the LM5b bVariantScaled branch): `AGTMudPatch::SoftScalesAt(contact)` reads S
  bilinearly - SinkScale = lerp(0.75, 1.5, S) / M_s on the sinkage's cap and rate, FrictionScale = lerp(1.05, 0.9, S) / M_f on the
  variant's friction, M_s and M_f the patch's means over its cells (Init), so its mean scale is 1. The arithmetic is
  `UGTTractionComponent::PatchSinkage` (base x wet x variant x soft, in that order: scales of 1 change no bit), which the test calls
  too; every cap after it still applies.
- **The look** (`Art/Unreal/live_mud_style.py` SOFT_HLSL, M_GT_Mud only): LayerTexture PF_G8 -> PF_R8G8, R the bog layer as before,
  G S x 255, uploaded in BakeLayers as before. w = smoothstep(0.55, 0.68, S - 0.25 (h - 0.5)), h the base slice's ORH B (the top
  face's two tilings blended as the colour is): lump tops stay the base mud, the hollows fill first. Off Deep, inside a dynamic branch
  on w > 0.01, the bog block again on slice 2 at the same parallax-slid uvs (no second march): colour, normal and AO lerp by w,
  roughness to max(0.45, Deep's). Off Deep the colour x lerp(1, 0.85, w) (Deep keeps its colour since the follow-up below); every
  variant's roughness toward 0.45 by 0.5 w.
- **Switch** `gt.Mud.SoftSpots` (1): 0 makes both scales exactly 1 and uploads G as 0; the patch notices a flip on its tick
  (`ApplySoftSwitch`) and re-uploads its layer.
- **Shader stats** (static, `Art/Unreal/mud_pbr_stats.py` tag mr4, `Art/Export/MudVariants/shader-stats-mr4.json`; accepted by the main
  session): M_GT_Mud 917 -> 991 pixel instructions, 6 -> 7 samplers, vertex 264. The seventh sampler is MudLayer itself: its R read in
  the legacy prefix has been dead code since LM5b's one layer, so the compiler had dropped the texture; reading G brings it back.
- **The terrain test** (`FGTM6TestRunner::TickBog` step 8, `TickBogEscape` step 9; since the follow-up below): the bog run's and the
  escape's gates test the tuned bog, so steps 8-9 run with gt.Mud.SoftSpots forced to 0 (`SetSoftSpotsForTest`, applied to the patches
  at once) and the value saved at step 8's start restored at the end of step 9's reverse leg; a report line gives
  the mean static S under the forward pass's wheel cells.
- **Tests** (`GrandTour.Mud.SoftSpots`, new, on DA_MudVariants' own spec: L_MudVariants' patches, 309 x 109 cells, 38.6 x 13.6 m):

  | Patch (amplitude) | soft share whole / interior | blobs | median eq. diameter | median shape P^2/4piA | NN CV | outer 0.5 m max S | at amplitude 1: whole / interior, blobs, diameter, shape |
  |---|---|---|---|---|---|---|---|
  | Firm (0.5) | 11.8 / 16.8 % | 6 | 3.39 m | 1.80 | 0.29 | 0.400 | 18.4 / 25.0 %, 5, 5.86 m, 1.87 |
  | Standard (1) | 20.5 / 25.0 % | 4 | 3.90 m | 2.01 | 0.44 | 0.400 | the same |
  | Deep (0.6) | 16.7 / 20.6 % | 2 | 6.93 m | 3.33 | 0.00 | 0.400 | 20.9 / 25.0 %, 4, 3.30 m, 2.20 |
  | Stony (0.6) | 13.0 / 19.1 % | 3 | 5.44 m | 1.93 | 0.36 | 0.400 | 17.7 / 25.0 %, 4, 4.43 m, 2.21 |

  Gates, amplitude 1 pooled over the four: the interior's soft share 25.0 % (20-30; the whole patches' 19.4 %), 17 blobs, median
  diameter 4.82 m (2-6), median shape 2.04 (at least 1.6). Mean SinkScale and FrictionScale 1.0000 / 1.0000 on every patch (the lerps'
  means Firm 1.1046 / 0.9791, Standard 1.1029 / 0.9794, Deep 1.1061 / 0.9788, Stony 1.1072 / 0.9786). The same seed gives the same S
  byte for byte. Stroke (Standard, PM_Mud's MaxSinkage 0.22 m through PatchSinkage, the field's floor noise and pockets off): S 0.800
  SinkScale 1.2241 -> 26.93 cm, S 0.200 SinkScale 0.8160 -> 17.95 cm: rut ratio 1.5000 = SinkScale ratio 1.5000 (with the field's
  noise and pockets on, 17.47 / 16.71 cm, 1.05: its own +-35 % depth pockets at 1.5 m outweigh S there). Switch 0: both scales exactly
  1 at every cell, G all 0, R unchanged; back at 1 the layer as before.
- **14 of 14 Mud and Snow tests** Success at gt.Mud.SoftSpots 1 and again at 0 (`-ExecCmds="gt.Mud.SoftSpots 0,..."`), CRC 8e0aad06
  both times; no other test's output moves (the two logs identical outside SoftSpots). GoWR open.
- **Before the revision** (the block's 1.5 m smoothstep rim and the whole-patch remap): the outer-0.5 m gate failed on every patch (most
  0.463-0.516: a cell 0.44 m in kept 21 % of its inner S) and the share at amplitude 1 was 19.7-21.6 % per patch.
- **Terrain** (L_Leg03; its bog's patch has soft spots at amplitude 1, 554 x 285 cells): with the step at 0, FAIL - escape forward
  6.1 m in 12 s (8 asked), reverse 6.0 m PASS; the escape path's mean S 0.559 under 179 wheel cells, 49 % of them soft; step 11's held
  exit FAIL (6 m in 8.9 s against 11.0 s unheld; "slower than down the ruts" 0). GoWR open (the escape's 3-second samples went missing:
  irregular frames). Step 8 (the middle run into the bog) still runs at 1, so the escape starts in ruts dug with soft spots. Before the
  in-step switch (no game): 7.0 m at 1 twice, 9.6 m with the whole test at 0 (the test PASS then). Suite mud PASS.
- **The check** (`& Art/check_mud_variants.ps1 -AllowGame`, GoWR open: 1.13 frames a second): the drive timed out at 76.28 m after
  300 s (Firm crossed in 54.2 s of real time; physics samples in Firm at least 4.43 m/s; sinkage max 28.47 cm, mean 24.66 cm against
  the committed 24.0 / 19.46 cm, i.e. over Firm's 24 cm cap by its SinkScale), then the scripted pass 6-8 m into Standard, Deep and
  Stony. Mean speeds against the committed drive-report (git HEAD): Firm 0.461 m/s of real time against 8.648 m/s - not comparable at
  1.1 frames a second (the crossing is timed on the real clock); the other three not crossed. Wheel path (route line +-1 m) soft share
  in each section: Firm 29.1 %, Standard 18.6 %, Deep 18.0 %, Stony 14.3 % (in the whole box 22.7 / 15.8 / 15.0 / 18.8 %). The Standard
  camera's blob: 78.2 m2 at (80.33, -0.75 m); Firm's 23.5 m2 at (35.66, 0.29 m). Pictures and maps (Art/Export/MudVariants):
  `soft-Firm.png`, `soft-Standard.png`, `soft-Deep.png`, `soft-Stony.png`, `Soft_Standard_Before.png`, `Soft_Firm_Before.png`,
  `Soft_Top.png`, `Soft_Standard_After.png` (after the scripted pass's 8 m into Standard), and the existing set retaken. The PBR rows
  (`Art/sample_mud_pbr.py`): Deep's ground base colour luminance 0.0286, under its soil band (MRP: 0.0322 at the dark edge) - MR4's
  wet darkening x0.85 applies on Deep's soft spots too; PBR_CarryWet FAIL (no carried mud in view after the scripted pass). Unjudged
  here: the pictures are for the main session's look.
- **Owed / open**: the owner's A/B of gt.Mud.SoftSpots on L_MudVariants and the amplitudes to name; the bog escape (6.1 m with the step
  at 0 under GoWR; 7.0 m at 1 and 9.6 m at 0 without a game) as a feel call; a check and a terrain run without a game for clean speeds.
- **Follow-up (2026-10-09, the main session)**: Deep keeps its colour under soft spots (the x0.85 darkening only off Deep; a Deep
  patch's soft spots get the roughness pull alone), for its soil band (the sampler had Deep's ground at luminance 0.0286); the terrain
  test forces gt.Mud.SoftSpots 0 from step 8's start (the run into the bog) to step 9's end, so the escape starts in ruts the tuned bog
  dug. `& Art/setup_mud_variants.ps1`'s command line re-applied M_GT_Mud (GoWR open; compiled, no errors); 14 of 14 Mud and Snow at 1
  and at 0, CRC 8e0aad06. Owed without a game: the terrain test (escape forward and reverse, step 11, the mean-S line) and the check
  (section speeds against the committed report, the Soft_* pictures, the PBR rows with Deep's luminance, PBR_CarryWet).

## 97. MudRunner MR5: breakable mud chunks (2026-10-09)

docs/MUDRUNNER_LESSONS_PLAN.md MR5 (the execution block of 2026-10-09), docs/MUD_VARIANTS.md ("Breakable mud chunks"). Chunks are the
firm crust and soft spots the soup: loose clods of dry crust on a bog's untouched ground where MR4's S is low, rigid bodies the
wheels never ride up on (a wheel that reaches one breaks it) and the body bumps and pushes. No cost or timing measured (the owner's).
No game and no foreign Unreal was running at any run (GoW, GoWR, FarCry6, Ace7Game, UnrealEditor, UnrealEditor-Cmd and UBT checked
before each); the MR4 runs (commit 3915f3c) had finished before the first.

- **Scope** as MR4: `HasSoftSpots()` - `!bHasProfile && Medium == EGTDeformMedium::Mud` with S built. No snow, ford, riverbed or Gravel.
- **The channel**: `ECC_Destructible` (`AGTMudPatch::MudChunkChannel`). Nothing else in the project uses it: no source, config, plugin
  or Art/Unreal script names it, and no content package serialises `ECC_Destructible`. The name "Destructible" sits in the name
  tables of L_Leg03, L_GTDressScratch, L_OWToolkitTest and the four ANGRY_MESH plank meshes; a pythonscript scan found no component in
  the three maps (1217 / 324 / 593 components) with that object type or profile, and the planks are Custom profiles of WorldStatic
  type (a response list naming the channel). Components that do not block the channel (269 / 83 / 8 in those maps, NoCollision and
  custom responses among them) will not stop a chunk. No ini change. `AGTCarPawn` sets `WheelTraceCollisionResponses` to ignore it (`SetWheelTraceResponseToChannel`), so the suspension's
  sphere sweeps pass through chunks. A chunk is its own object type and blocks WorldStatic, WorldDynamic, Vehicle, Pawn and
  Destructible; everything else (Visibility, Camera, PhysicsBody) is ignored.
- **Meshes** (`Art/Blender/build_mud_chunks.py`, headless; `Art/import_mud_chunks.ps1` -> `/Game/GrandTour/Mud/Chunks/SM_GT_MudChunk_0..5`):
  build_mud_clods.py's recipe at 30 cm across on a cube-sphere (the finest whose finished chunk stays within 600-1,000 triangles),
  three octaves of noise (stronger than the clods' two), 2-4 crack grooves (a wavy plane through the body, the surface pulled in along
  it, tapered at its ends), the family's planar cuts, a flat bottom. One convex hull each (UCX_, the mesh above an embed line at 18 % of
  its height plus where its edges cross the line, thinned to 64 vertices by farthest-point sampling); the pivot is the hull's bottom
  (its face's area centroid), the render mesh goes on below it by the embed.

  | Mesh | family | triangles | size cm | volume cm^3 | above the line | hull cm^3 (vertices) | embed cm |
  |---|---|---|---|---|---|---|---|
  | 0 | rounded | 996 | 30.0 x 27.5 x 16.5 | 5585.8 | 4347.9 | 5188.5 (64) | 2.97 |
  | 1 | rounded | 952 | 30.0 x 29.8 x 14.4 | 5169.7 | 3953.2 | 4730.8 (64) | 2.59 |
  | 2 | slab | 872 | 30.0 x 29.2 x 9.0 | 3629.6 | 2658.4 | 2920.9 (64) | 1.62 |
  | 3 | slab (broken side) | 962 | 24.8 x 30.0 x 10.2 | 3461.9 | 2563.9 | 2760.3 (62) | 1.84 |
  | 4 | broken (two cuts) | 806 | 28.8 x 30.0 x 17.4 | 5189.1 | 3595.4 | 3798.6 (59) | 3.13 |
  | 5 | smear (aspect 2.1) | 904 | 30.0 x 14.0 x 7.8 | 1537.8 | 1180.1 | 1309.0 (64) | 1.40 |

  `Art/Export/MudChunks/manifest.json` lists them; the import puts each one's numbers on the mesh as a `UGTMudChunkData` (asset user
  data: family, volume, hull volume, embed, across), which the patch reads. Under Interchange (5.8's FBX path) the import must keep
  `auto_generate_collision` on: off drops the UCX_ hull as well. In Unreal the imported hull's lowest vertex sits 0.27 cm under the
  pivot at scale 1 (Chaos's own hull of the UCX_ points); the spawn lifts by the hull's vertices, so a resting chunk still sits on it.
  Material `M_GT_MudChunk` (`live_mud_style.build_clod_material(CHUNK_MATERIAL, chunk=True)`): M_GT_Clod's graph and numbers, the
  slice through MudVariant (the patch's instance on a variant), freshness a constant 0, the tint from custom primitive data 0
  (`ChunkRand`, set per chunk). Preview renders: `Art/Export/MudChunks/MudChunks_Preview.png`, `MudChunks_Hulls.png`.
- **Placement** (`AGTMudPatch::PlanMudChunks`, at Init after S; seed `MudChunkSeed` = 7919 (i + 1) + 3301; the route line from
  `SetRouteLine`, UGTMudSubsystem::BuildPatches, the main route every 2 m from the section's start to its end): candidate cells within
  6 m of the line, 1.5 m from the rim, S <= 0.55 (each chunk's centre checked again); the target = their area x 1/25 m^2 x the
  variant's `FGTDeformProfile::ChunkDensityScale` (Firm 0.5, Deep 1.5, Stony 1; Standard 1 with no profile; at most 48); a hashed 4 m
  value noise's top 35 % of the candidates is cluster ground, x2.5 there and x0.2 elsewhere, drawn by those weights (so the mean is
  the target); sizes 20 + 30 u^2.2 cm with u stratified over the patch's chunks (one per 1/N of 0..1, hashed jitter), placed largest
  first, 60 tries each; centres at least r1 + r2 + 5 cm apart (r half the size); families by 0.3 / 0.35 / 0.2 / 0.15; yaw random, tilt
  up to 12 degrees off the rest mesh's normal; on the landscape by a trace, lifted along the normal until the hull's lowest point
  touches.
- **Physics**: one pooled `UStaticMeshComponent` per chunk, owned by the patch (not attached), simulating; mass clamp(1.6 kg/L x
  volume, 10, 40); put to sleep after its spawn. The awake cap (`UGTMudSubsystem::EnforceMudChunkAwakeCap`, once a frame from the
  patches' ticks): at most `MaxAwakeMudChunks` 64 in the world, the longest-awake put to sleep first. A chunk more than 1 m under the
  landscape at its XY (the rest mesh inside the box, a trace outside it) is removed and its volume logged as lost.
- **Breaking** (`BreakMudChunk`): removed, its exact volume (`UGTMudChunkData::VolumeCm3` x scale^3) into the field as a dome of 0.5 x
  its size through `DepositLumpDome` (DepositThrown's dome, factored out; recorded as the new `FGTMudField::EventChunk`, which the
  replay deposits without clods), and 3-5 LM2c clods (Source 5, freshness 0) of 0.25-0.45 x its size within 0.6 x its size, from the
  chunks' own random stream. Triggers: (a) `UGTTractionComponent::StampMud`, per wheel in contact inside a patch (stamping or not),
  before its stamp: the capsule from last frame's contact to this one, the tyre's half width, against the chunks' 2 m grid and each
  footprint circle (0.4 x size); (b) `OnMudChunkHit` from a Vehicle-type component with a normal impulse over `ChunkBreakImpulse`
  50,000 kg cm/s (500 N s); (c) from a WorldStatic component at an impulse over the chunk's mass above 400 cm/s. A chunk pinned under
  the body would also read as (c) (the car's weight in one step's impulse); not seen in the check.
- **Switch** `gt.Mud.Chunks` (1): 0 removes every chunk at once (nothing deposited: the field CRC is untouched); 1 again places them
  anew on the cells the field still has at 0. The terrain test forces it to 0 across steps 8-9 with gt.Mud.SoftSpots (`SetChunksForTest`)
  and restores it after.
- **Tests** (`GrandTour.Mud.Chunks`, new; DA_MudVariants' patches over a static ground box, -NullRHI, Chaos stepping the world): Success.

  | Patch | live / target | candidate m^2 | in cluster ground | sizes cm (CV) | nearest neighbour mean (CV) | max S | min rim | min edge gap | masses kg |
  |---|---|---|---|---|---|---|---|---|---|
  | Firm (x0.5) | 6 / 6 | 282.6 | 1 | 20.0-45.3 (0.318) | 480 cm (0.410) | 0.503 | 162 cm | 300.3 cm | 10.0-28.6 |
  | Standard | 10 / 10 | 240.9 | 10 | 20.0-43.9 (0.279) | 365 cm (1.138) | 0.536 | 224 cm | 64.4 cm | 10.0-25.9 |
  | Deep (x1.5) | 16 / 16 | 266.8 | 14 | 20.0-46.8 (0.293) | 233 cm (0.580) | 0.546 | 162 cm | 65.4 cm | 10.0-23.8 |
  | Stony | 11 / 11 | 267.3 | 11 | 20.1-48.3 (0.310) | 338 cm (1.408) | 0.500 | 153 cm | 46.6 cm | 10.0-37.4 |

  The plan is deterministic and the live chunks are its; 0 violations of S, the rim, the route's reach or the gap on every patch; all
  asleep after spawn, every hull's lowest point on the ground (0.000 cm). The meshes' volumes are the manifest's. Wheel: a stroke 2 cm
  clear of a 43.9 cm chunk's footprint broke nothing, 2 cm into it broke it: the field took 16182.2 cm^3 for its 16182.2 (0.0000 %;
  LumpCm +8192.1, the rest over LumpMaxCm into HeightCm in the same cell, DepositLump's rule), 5 clods. Impulse: 0.9x pushed, 1.1x
  broken; landing (23.8 kg) 0.9x held, 1.1x broken. Awake cap: 100 more on Firm's rim band, 140 woken, 76 put to sleep, 64 awake.
  Drop: all six meshes dropped 5 cm at 30 cm asleep at 0.37 s, hull bottoms 0.00 cm. Switch: 0 -> 0 live, the four fields' CRCs
  unchanged; 1 -> 43 on untouched ground. (The world ticks inside one engine frame, so the test moves GFrameCounter with each tick: a
  tick function runs once per frame.)
- **15 of 15 Mud and Snow tests** Success at gt.Mud.Chunks 1 and again at 0 (`-ExecCmds="gt.Mud.Chunks 0,..."`), CRC 8e0aad06 both
  times. **The full suite** (`bash Art/suite.sh -q`): 28 PASS, 0 FAIL.
- **Terrain** (L_Leg03, in the suite): the bog line had 17 chunks at gt.Mud.Chunks 1 (target 17 on 435 m^2, 6 meshes), 0 for steps 8-9,
  15 placed again on untouched ground after; escape forward 8.4 m in 12.0 s (PASS), reverse 6.0 m (PASS); the escape path's mean S 0.605
  under 258 wheel cells, 58 % soft; step 11 down the ruts 10.9 m (6 m in 5.8 s) against the first pass's 8.4 m (6 m in 7.5 s), faster 1.
- **The check** (`& Art/check_mud_variants.ps1 -AllowGame`, no game open): the drive reached 200 m in 81.48 s at 38.98 frames a second
  (Firm 8.70, Standard 6.48, Deep 0.56, Stony 6.23 m/s). Per section at the end (before driving: 6 / 10 / 16 / 11 live):

  | Section | live | breaks wheel / impulse / landing | deposited cm^3 | lost | awake peak | clods | max chassis impulse | max landing |
  |---|---|---|---|---|---|---|---|---|
  | Firm | 5 | 1 / 0 / 0 | 3667.3 | 0 | 0 | 3 | 0 | 0 |
  | Standard | 10 | 0 / 0 / 0 | 0 | 0 | 0 | 0 | 0 | 0 |
  | Deep | 13 | 3 / 0 / 0 | 21035.8 | 0 | 1 | 10 | 0 | 67.4 cm/s |
  | Stony | 8 | 2 / 0 / 1 | 17618.6 | 0 | 1 | 13 | 11274.3 kg cm/s | 573.3 cm/s |

  World-wide awake peak 1, none capped. Pictures (for the main session's look): `Chunks_Before.png`, `Chunks_After.png` (2.5 m up at 73 m,
  7.5 m to -Y, across Standard's start), `Chunks_Close.png` (1.7 m eye height, 3.5 m from Standard's biggest cluster: 4 chunks at
  90.8 m, +2.8 m), `Chunks_Firm.png`; the variants' and MR1-MR4 pictures retaken. Deep's ground base colour luminance 0.0323 (soil OUT,
  under the 0.0325 floor); the same check at gt.Mud.Chunks 0 read 0.0324, the other grounds moving by up to 0.0002 between the two
  runs: run-to-run churn, not the chunks. The committed drive-report and pbr-rows are the Chunks 1 run's.
- **Owner's test list**: gt.Mud.Chunks 0/1 on L_MudVariants; `ChunkBreakImpulse`; the density multipliers
  (`FGTDeformProfile::ChunkDensityScale`); the size range (`MudChunkSizeMinCm` / `MaxCm`); the cost (a simulated component per chunk:
  6 / 10 / 16 / 11 on L_MudVariants' patches, 17 on L_Leg03's bog; at most 48 a patch, 64 awake).

## 98. Deformable gravel DG0-DG1: the Codex study taken over, revision-04 bakes with PBR and parallax, loose stones, windrow heaps (2026-10-09)

docs/DEFORMABLE_GRAVEL_PLAN.md DG0 and DG1 (with its "Decisions after the phase A bakes" and "After the phase A2 Close.png"),
docs/DEFORMABLE_GRAVEL.md. No cost or timing measured (the owner's). No game and no foreign Unreal was running at any run (GoW, GoWR,
FarCry6, Ace7Game, GrandTour, UnrealEditor and UnrealEditor-Cmd checked before each; the Codex app was open, its Unreal was not).

- **DG0** (commit 30b4703): the Codex study's C++ hunks (the Gravel medium, `FGTDeformProfile::SurfaceMaterialPath`, the patch's
  `ProfileSurfaceMaterialPath`), its scripts, docs, reports, the gravel road study and import, and the Poly Haven provenance. The asset
  registry's dependency list (`Art/Unreal/dg0_gravel_dependencies.py` -> `Art/Export/DeformableGravel/dg0-dependencies.json`): 33 study
  packages, 42 shared (MudStyle arrays and clay bakes, RoadFordStyle textures, the tussock straw, MF_Weather, MPC_Weather, MPC_TrackPaint,
  RT_TrackPaint, RT_RainOcclusion, the stylised and mud textures), none Benmore-named, none moved. Verified on MR5's code: build, 15/15
  Mud and Snow tests (CRC 8e0aad06), the study's ten checks.
- **Bakes** (`Art/Blender/bake_gravel_dg1.py`, headless Blender 5.1; `Art/bake_gravel_orh.py`): revision 04's own node graph with every
  procedural input made periodic in numpy (Voronoi 26 / 68 cells wrapped, noise values matched to Blender's own), a 2 m tile at 2048.
  Seams: edge z within +-2.02 on every channel. Direction: the parallax height's coherence 0.013 / 0.087 (whole / 10 cm). Loose
  luminance 0.257, Packed 0.248 (x0.967, the study's wheel path). ORH G: Loose p5/50/95 0.761 / 0.902 / 0.902, Packed 0.808 / 0.851 /
  0.851. B: per stone a centre (Loose 0.35-1.0, 33.4 % at 0.35-0.55; Packed 0.25-0.7) and a tilted top (rise 0.15-0.45), 6 %/texel sides,
  chips 0.05-0.3, a 0-0.1 matrix, soft rims 6 %/texel and a 1-texel Gaussian; per-stone top median 0.647 (gate 0.6), maximum 1.0.
  Depth 0.8 cm Loose, 0.5 cm Packed; mean(hL) 0.2959. `TA_GV_{Color,Normal,ORH}` (`Art/Unreal/import_gravel_dg1.py`, the mud's array
  builder): 2 slices of 2048, Color BC1 sRGB, Normal BC5, ORH BC7.
- **M_GT_Gravel** (`Art/Unreal/gravel_dg1_material.py`, the profile's SurfaceMaterialPath): the study's displacement and Catmull-Rom field
  normal; the arrays on a 2 m world tile (uv (x, -y) / 2 m, the bake's DirectX green toward -y); the track blend; the windrow (AO x1.15,
  parallax x1.2 over 0-2 cm); M_GT_Mud's parallax march on the surface the pixel shows (lerp(Loose B x 0.8, Packed B x 0.5, p), Packed's
  sample only where T > 0.13) with the 4-step sun self-shadow within 4 m, gt.Gravel.POM (MPC_TrackPaint GravelPOM, UGTTrackPaintSubsystem);
  PBR (roughness from ORH, wet x0.75 and 0.4, default specular), the AO and a 0.15 cavity tint; the study's x0.82 albedo and grass verge.
  M_GravelLandscape on slice 0 of the same arrays (no parallax). M_GT_GravelStone for the stones. Shader counts
  (`Art/gravel_shader_stats.ps1`): M_GravelField 410 pixel / 263 vertex instructions, 6 samplers; M_GT_Gravel 666 / 263, 5 samplers;
  M_GravelLandscape 201 / 155, 3; M_GT_GravelStone 197 / 201, 1 (M_GR_Stone 191 / 153, 1).
- **The pale edge line**: the field normal's sun-lit rut wall (an even 25 cm, ~15 deg wall under a low sun, squeezed into a line by the
  grazing view). gt.Gravel.Debug 1 (flat normal) and 4 (flat lighting normal) remove it; 2 (no slide), 3 (no detail normal), 5 (no
  specular), 6 (fully rough), the parallax off and a B-spline slope all keep it. Fixed by varying the wall's lighting slope along the rut
  (45 cm noise, x0.25-1.25) and by stone (x0.8-1.2), soft-capped at ~8 deg (`GravelWallTiltCap` 0.14).
- **Loose stones** (`UGTGravelStones`, GTGravelStones.h/.cpp; the patch's `InitGravelStones` after BuildMesh; the traction's chunk-break
  footprint calls `PushUnderWheel`): 2772 Firm (12 per m^2 over 231 m^2) and 7980 Loose (30 over 266 m^2), four HISMs a patch, culled and
  faded 25-35 m; gt.Gravel.Stones, gt.Gravel.StoneDensity. A pressed stone stays pressed under later strokes (the first check had 0.6 %
  pressed: the next tick's capsule pushed them out).
- **Windrow heaps**: the gravel profiles' lumps (LumpShare 0.3, LumpMaxCm 2.5, radius 1.5 x (1 +- 0.33) cells, absent 0.5, cluster 150 cm).
- **Tests**: GrandTour.Gravel.Stones (new; `Art/mud_shape_test.ps1` runs it with the Mud and Snow tests): placement deterministic, Firm
  11.89 and Loose 30.08 per m^2 over the interior; a 6 m stroke 38 -> 4 inside (10.5 %), pushed 34, the band +34 exactly, spacing cv 0.600;
  slip 0.5: 65 of 129 flicked (0.504), landing 51-299 cm back; heaps: 66 peaks, spacing cv 0.608, highest 2.50 cm; gt.Gravel.Stones 0 leaves
  0 instances. 16/16 GrandTour.Mud / Snow / Gravel, CRC 8e0aad06. The full suite (`bash Art/suite.sh -q`): 27 PASS, 1 FAIL - terrain, the same twice (a rerun): step 11's exit at 30 deg with the hold on was not slower than down the ruts (the car stayed 9 deg off them; the gate MR2-MR3 also failed). L_Leg03 has no gravel patch, so none of DG1's code runs there (the patch's GravelStones is null off gravel); not proven by an A/B run.
- **The check** (`& Art/deformable_gravel.ps1 -Mode Check`): 9 of the study's 10 pass. **small_positive_ridges fails**: the loose windrow
  stands 5.50 / 5.53 / 5.51 cm after the three passes (the check asks under 4; before the heaps 3.0) - the heaps' 2.5 cm domes on the
  study's 3 cm ridge cap. Not relaxed: the main session decides (the check's limit or the heaps' cap). The repeat pass now lowers
  577,249 cm^3 (before the heaps 111,479; the first 2,455,786): the heaps sit on the rut lips. Stones after the passes: Firm 198 pushed,
  33 pressed; Loose 1062 pushed, 174 pressed, 8 flicked. PBR rows (`python Art/sample_gravel_pbr.py`): dry base colour luminance p5/50/95
  0.154 / 0.195 / 0.277 (0.05-0.35 PASS), roughness p5 0.777 (>= 0.5 PASS); wet roughness 0.400 (>= 0.4 PASS), luminance x0.753.
  Pictures in `Art/Export/DeformableGravel/`: Gravel_Before, FirstPass, RepeatedPass, ShoulderPass, Close, Close_POM0, Low, Wet,
  RepeatedPass_Debug1-6, RepeatedPass_POM0, PBR_Gravel_Dry / Wet (+ EXR buffers).
- **Owner's test list**: drive L_GravelDeform (first pass, repeat, shoulder); gt.Gravel.POM 0/1, gt.Gravel.Stones 0/1; the stone
  densities (gt.Gravel.StoneDensity; 12 / 30 per m^2); the feel numbers (unchanged: caps 2.5 / 5 cm, rates 0.4 / 0.9 cm/s, friction 0.68,
  rolling 0.035, plough 0.012, sinkage drag 0.35); the heaps' height.

### 98b. DG1b, after the main session's look (2026-10-09)

- **The stones' colour**: `M_GT_GravelStone` had no instanced-static-mesh usage, so the HISMs drew the engine's default material (DG1's
  near-black specks; the check log's "missing usage flag InstancedStaticMeshes"). The material now has it and takes, per instance
  (PerInstanceRandom), a stone face of the Loose bake (ORH B over 0.45, up to eight hashed tries, the colour one mip up) through the
  ground's x0.82 colour path with a x0.92-1.06 tint; roughness 0.75-0.85 per instance, 0.4 wet. (Its fade read PerInstanceFadeAmount
  inverted - 1 is shown - so with the usage on the stones were dithered out until that was fixed.) PBR sampler (PBR_Gravel_Stones: the
  field, the landscape and the grass hidden): the stones' median base-colour luminance 0.2163 against the ground's p50 0.1971 (x1.097,
  within 25 %), the least 0.1467 (none under 0.08), roughness p5/50/95 0.757 / 0.804 / 0.847.
- **Clustering**: two octaves of value noise (1.5 m and 4 m, the second weighted 0.45), sharpened by a smoothstep over 0.4-0.6
  (`ClusterSharpen` 0.1: without it the two octaves average out, cv 0.56-0.59), x0.1-2.5, the edge and crown rule kept; the target is
  now renormalised over the section's span and the margins separately (12.00 and 30.00 per m^2 over the sections). 1 m^2 quadrat count
  cv over the sections: Firm 0.730, Loose 0.784 (DG1's one octave x0.3-1.8: 0.443, 0.366); a new GrandTour.Gravel.Stones row (>= 0.6).
- **The streaks** on the windrow walls (Gravel_Close): the texture slide - gt.Gravel.Debug 2 (no slide) removes them, 1 and 3 do not.
  `FGTDeformProfile::TextureSlideScale` (default 1; the gravel profiles 0.25) sets M_GT_Gravel's GravelSlideUV (the patch's material
  instance); the mud materials have no such parameter.
- **The heap gate**: the study check's `small_positive_ridges` is Loose under 6 cm (3 cm ridges + 2.5 cm heaps, by design) and Firm
  under 4 cm. The check: ten of ten (loose 5.24 / 5.24 / 5.60 cm, firm 3.25 / 3.90 / 3.90 after the three passes).
- **Tests**: 16/16 Mud / Snow / Gravel, CRC 8e0aad06. Pictures retaken in `Art/Export/DeformableGravel/` (the study's four, Close,
  Close_POM0, Low, Wet, RepeatedPass_Debug1-6, RepeatedPass_POM0, Close_Debug1-3, PBR_Gravel_Dry / Wet / Stones).

## 99. Wheel spray P1-P2: painterly mud and gravel spray (Niagara droplets, grit, dust; clump-drawn mud blobs) (2026-10-10)

docs/WHEEL_SPRAY_PLAN.md P0-P2. No cost or timing measured (the owner's). No game and no foreign Unreal was running at any run
(GoW, GoWR, FarCry6, Ace7Game, GrandTour, UnrealEditor and UnrealEditor-Cmd checked before each). Water, Benmore, GTSprayWater.cpp
and the Water / Steam / Snow drawing untouched; the foreign water hunks in GTSprayComponent.h/.cpp stay out of this commit.

- **P0** (report only): Niagara is authored headless through UE 5.8's `UNiagaraExternalEditUtilities` (experimental, C++ statics,
  not script-exposed): CreateNiagaraSystem, AddEmitter (engine templates), GetEmitterTopology, AddUserVariable, SetStackInputData
  (local, enum, linked, HLSL expression), SetRendererData / SetEmitterData (JSON), AddModule, SetModuleEnabled,
  GetSystemCompileState. A link to a static switch (the probe's `Color Mode`) crashed the editor (CastChecked in Casts.cpp).
- **P1 / P1b** (`Art/Blender/build_spray_assets.py`, headless Blender 5.1, ~15 s; `Art/Export/WheelSpray/`): eight clumps
  `SM_GT_SprayClump_0..7` from the clod recipe, P1b after the look (P1's planar cuts read as rocks): torn lobes pulled out, drooping
  rims, three strings tapering into a sagging tail; decimated to 46 triangles, one Catmull-Clark level, fine noise along the
  normals, all smooth: 276 triangles each, longest side 1.6 / 1.9 / 2.2 / 2.6 / 3.1 / 3.8 / 4.7 / 6.0 cm. Atlases, 1024, 4 x 4 frames of
  256: `T_GT_SprayMud` (RGBA: R soft height, A coverage), `T_GT_SprayGrit` (RGBA: R facet shade, G per-chip random, A mask),
  `T_GT_SprayDust` (grey coverage, the puff over its life). Renders `Assets_Clumps.png` (the Standard bog bake tri-planar at a 25 cm
  tile, wet x0.8, roughness 0.5) and `Atlas_Sheets.png`. `manifest.json` holds the palette (the bog slices' means, DG1b's stone
  tints and matrix x1.15).
- **Setup library** (`Source/GrandTourEditor/Private/FX/GTNiagaraSetupLibrary.h/.cpp`, the P0 probe renamed; GrandTourEditor depends on
  Niagara, NiagaraCore, NiagaraEditor; GrandTour on Niagara): `BuildWheelSpray` and `DescribeEmitterTemplate` (every input of a
  template plus modules, with types, switch / visible / editable and enum values, and the emitter and renderer JSON). **The guard**:
  before every SetStackInputData it reads GetEmitterTopology afresh and asserts the script and the module exist by their exact names,
  the input exists by its exact name, its type is exactly the one given (any enum for an enum write), it is visible and editable,
  and for links and expressions it is not a static switch; a link also asserts the User parameter exists with the same type. Any miss
  is a FAIL naming it, and nothing after it is written. After a static switch the edit context is rebuilt so the next topology sees the
  inputs it reveals.
- **NS_GT_WheelSpray** (`Art/setup_wheel_spray.ps1` -> `Art/Unreal/setup_wheel_spray.py`, a full editor with -RenderOffScreen):
  User MudRate, GritRate, DustRate, BaseVelocity, MudTint, GritTintA, GritTintB, DustTint, SizeScale; three Fountain-template emitters.
  MudDroplets (GPU, fixed bounds +-25 m): 1-6 cm x SizeScale by `1 + 5 rand^2.5`, BaseVelocity's direction +-35 deg at its length
  x0.6-1.4, gravity 980, drag 0.3, 0.6-1.4 s, depth-buffer collision killing at the first hit, colour MudTint. GravelGrit (GPU): 0.5-2
  cm, +-40 deg, a random point between GritTintA and GritTintB per particle, restitution 0.3, killed at the second hit, 0.8-1.5 s.
  GravelDust (CPU): 30-120 cm growing x2.5 (ScaleSpriteSize, 1 + 1.5 NormalizedAge), 0.25 of BaseVelocity in a 60 deg cone, a 30 cm/s2
  lift over drag 1.5 (about 20 cm/s), 1.5-3 s, DustTint, sorted by view distance. Random sprite rotation and Material Random on all
  three; their template colour-over-life off. Sprite materials `M_GT_SprayMud` (masked 0.33, lit, roughness 0.5, the frame from
  Particle Random, a normal from R), `M_GT_SprayGrit` (masked, lit, particle colour x facet shade x 0.9-1.1 by G, roughness 0.75),
  `M_GT_SprayDust` (translucent, lit, the flipbook by Particle Relative Time with frames blended, at most 0.35, a 60 cm depth fade).
  `M_GT_SprayClump` on the clods' builder (`live_mud_style.build_clod_material(spray=True)`): wet (freshness 1, roughness
  min(lerp(0.85, 0.45, wetness), 0.5)), the slice from per-instance custom data 0, ClodScaleCm 25. The system is rebuilt from nothing
  each run: the launcher removes the old file first (built over an existing package in one session, the saved system crashed every
  later load, -game included). The setup editor exits with an access violation after it has saved; the system reloads cleanly.
- **Runtime** (`Source/GrandTour/Vehicle/GTSprayArt.cpp`; hooks in GTSprayComponent.h/.cpp; GTTractionComponent): the wheel gets
  `bInGravelPatch` (the contact in a profiled patch of medium Gravel, by `UGTTractionComponent::PatchMediumFlags`, the rule
  bInSnowPatch now uses too) and `PatchVariant` (the slice of the patch at the contact, 0 outside). One UNiagaraComponent per wheel,
  world-aligned, 45 cm behind the contact (back from the spin) and 25 cm up. Each tick: MudRate = 6 x the Mud kind's CPU rate on the
  wheel (Mud or Bog tag), GritRate = 10 x max(speed factor, slip factor), DustRate = 2.5 x the same x saturate(1 - wetness / 0.6), all x
  b(t) x gt.Spray.FineScale; b(t) = (0.3 + 1.4 n)^2 over its long-run mean, n a per-wheel smooth noise at 3 Hz from shuffled
  stratified levels; BaseVelocity = SpawnThrown's mean (back from the spin, up 250 + ThrowUpPerSpin x spin, 0.2 of the car's
  velocity); MudTint = the slice's bog mean x0.8. At gt.Spray.Art 1 a gravel patch's grey Dust spheres stop, and the Mud kind (spray
  and thrown blobs) draws as the eight clumps: one ISM each, the clump by particle id, the blob's size as the clump's longest side, the
  strings stretched x1.5 along their velocity, the others tumbling 2-8 rev/s about a random axis, the slice in custom data 0. The pools,
  their random stream, the emission and the thrown volumes are untouched (particles only gain an id and a slice). Under -NullRHI the
  art layer stays off (nothing would draw).
- **Switches**: `gt.Spray.Art` (1; 0 the greybox exactly: Niagara deactivated, spheres, grey dust on gravel), `gt.Spray.Fine` (1; 0 the
  Niagara layers off), `gt.Spray.FineScale` (1). UPROPERTYs on UGTSprayComponent: FineMudPerRate 6, FineGritPerFactor 10,
  FineDustPerFactor 2.5, BurstHz 3. Owner tests: A/B each switch, `stat Niagara`, FineScale 2-4 on gravel (the plan's gravel rates are
  sparse: 10 grit and 2.5 dust a second a wheel at full).
- **Tests**: 17/17 GrandTour.Spray, Mud, Snow and Gravel (CRC 8e0aad06 in Settle). GrandTour.Spray.Art: the gravel flag on gravel only
  (not mud, snow, off-contact or unprofiled); bursts over 60 s mean 0.981 / 1.015 / 0.986 / 0.990 on four wheels (min 0.08, max 2.58);
  every rate 0 at Fine 0; dust 0 at wetness 0.7 (grit 10); the clump per id deterministic, all eight used (476-523 of 4000). The spray
  drive test (-GTSprayTest, L_TestTrack) passes: headless at Art 1 three times and Art 0 twice, spawned 990 and maxDustInDirt 120
  every run, maxMudInMud 91 / 88 / 89 at Art 1 and 88 / 88 at Art 0, maxSnowInSnow 92-93 (run-to-run spread at one setting); with a GPU
  at Art 1 (spawned 880) and Art 0 twice (920, 918), the Art 1 car about 0.4 s behind from its start.
- **Pictures** (`Art/check_wheel_spray.ps1` -> `Art/Unreal/check_wheel_spray.py`; `Art/Export/WheelSpray/`, live counts per emitter
  at the capture in `check-report.json`): Spray_Mud_Spin (MudDroplets 66, clumps 110, Deep slice 2), Spray_Mud_Spin_Greybox (0, 0; CPU
  Mud 111), Spray_Mud_Drive (392, clumps 111; 4.4 m/s, Standard slows the car below 25 km/h), Spray_Gravel_Drive (grit 10, dust 14),
  Spray_Gravel_Launch (grit 6, dust 3; 1.2 s in), Spray_Gravel_Wet (grit 17, dust 0), and, not in the plan, Spray_Gravel_Drive_FineScale4
  (grit 72, dust 83) and Spray_Gravel_Launch_FineScale4 (grit 28, dust 18). Owner gate: drive mud and gravel with each switch.
- **P2b** (the main session's look, 2026-10-10). **The white blots** in Spray_Mud_Drive were not the droplets: in the BaseColor buffer
  the droplets' pixels (the custom-depth mask of the car's Niagara components alone, `Art/sample_spray_pbr.py`, the GBuffer at the
  87 % render resolution) read MudTint exactly (Standard 0.0562 / 0.032 / 0.0144, luminance 0.0359; Deep 0.0324), and a green
  MudTint drew green. They are the CPU Water kind's pale spray (M_GT_WaterSpray): 29-53 alive at every mud capture, most likely fired in the
  muddy ruts by the uncommitted water work's thresholds (SplashDepthM 0.025 m); water is off limits here, so it is reported, not
  changed. **Fixed**: the Collision module killed occluded and offscreen droplets (Kill Occluded / Kill Offscreen Particles now
  false): a stuck spin kept 17-54 of about 1100 a second alive, now 466-541; the emitters sit 50 cm behind the contact at 40 cm (hub
  height); the dust is lit per pixel (TLM surface; volumetric lighting read it darker than the sunlit gravel). **Gravel**: grit 30 x
  the factor (1-3 cm), dust 8 x (60-200 cm, opacity 0.5); FineScale stays. **Camera rule** (`check_wheel_spray.py`): a 3/4 rear view
  of the rear wheel whose view puts the level's sun nearest behind the camera (both levels' sun travels (0.47, -0.76, -0.45)), eye
  1.15 m up, 4.0 m back and 2.5 m out (4.85 m from the wheel; the close pictures 2.4 / 1.8 m, 3.21 m), looking 1.2 m behind the wheel;
  sun angles 6.7-23.5 deg. **Gate**: Spray_Mud_Close 0.0324 (2574 px) and Spray_Mud_Drive 0.0359 (3087 px) in 0.03-0.25; grit 0.1952
  (721 px), 0.99 of the gravel p50 0.197. **Kill On Collision**: a still system 60 cm above the flat road, a 0.06 s burst from rest,
  the live counts every frame: MudDroplets (1) half gone at 0.43 s, all at 0.46 s (first hit due 0.35 s, life at least 0.6);
  GravelGrit (2) half gone at 0.56 s (second hit due 0.56 s, life at least 0.8). Live counts per emitter at each capture in
  check-report.json. Tests 17/17 (Spray, Mud, Snow, Gravel; CRC 8e0aad06).
- **P2c** (the main session's look, 2026-10-10). **Dust in shadow**: M_GT_SprayDust takes its light from the new
  `MPC_GT_Spray` - base colour DustTint x DustLit (0.7) and an emissive sky floor DustTint x DustFloor (1.4), blended by the opacity.
  The gate (`Art/sample_spray_pbr.py`, Spray_Gravel_Close's final image; the dust mask is the difference from the same paused frame
  with the car's Niagara components hidden, less the grit; a dust pixel is in shadow where that frame is under 0.4 x its sunlit
  ground): dust in shadow 0.3839, in sun 0.4951, ratio 0.775 (asked 0.5). The asked floor 0.3 (lit 1.0) gave 0.264 in the first run.
  The same frame swept (lit / floor -> ratio): 1.0 / 0.3 0.746, 1.0 / 1.0 0.779, 0.7 / 1.0 0.757, 0.7 / 1.4 0.775, 0.5 / 1.4 0.759,
  0.7 / 2.0 0.812 - this frame's shadowed dust is mostly sunlit dust in front of the car's shadow on the ground, so the floor matters
  less here than under the bumper. **The dark streak** (P2b's Spray_Gravel_Drive) did not recur in three runs. A same-frame hide of the
  CPU Dust kind changed 0 pixels (its 17-19 grey spheres are behind the camera). A flipbook frame, the depth fade and sorting cannot
  darken: the frames are coverage only, the depth fade only lowers the opacity, and every puff has one colour. What darkens a lit puff
  is a sun shadow on the per-pixel lit dust (P2b's lighting; the same mechanism as the dust under the bumper), which the floor lifts.
  **Droplets**: 2-8 cm; their cone axis and speed from BaseVelocity with its upward part x1.3 (MudDroplets only). Gate: 43 % of the
  visible droplet pixels in Spray_Mud_Close above the rear wheel's arch-top line (its contact + 2 x 38 cm + 10 cm, projected; asked 25 %).
  The visible sprites are the custom-depth pixels whose BaseColor differs from the same frame's dump with the components hidden: custom
  depth also holds sprites behind the body (P2b's Spray_Mud_Close base colour had mixed the car's paint in). With that mask Deep's
  droplets read 0.0258 (Deep's bake mean x 0.8, under the 0.03 band edge by the bake), Standard's 0.0359, the grit 0.1597 (38 px).
  **Captures**: every capture of a scenario is one paused frame; `Spray_Mud_Close_NoWater` hides the CPU Water spray's ISM (18298 px
  differ). Live counts in check-report.json.
- **P2d** (the main session's look, 2026-10-10). **Rooster tail**: MudDroplets leave in clumps - those born in one window of
  Emitter.Age (MudRate / 10 windows a second, so about ten each) share hashes of that window and the new User.ClumpSeed (the wheel's
  number): a direction within 15 deg of BaseVelocity with its upward part x1.3, a speed x0.8-1.2; each droplet then a 4.6 deg cone and
  x0.92-1.08; the speed capped at 700 / the direction's z, so the upward launch is at most 700 cm/s. Gate: droplet height above the
  ground p95 1.37 m (p50 0.86, apex p95 1.53, apex max 1.88; asked 2.5 m) - a CPU estimate from the launch velocities, not the GPU's
  particles (`check_wheel_spray.py` droplet_heights: the four wheels' BaseVelocity and rates at the capture through the same
  distribution, 40 cm above the contact, gravity and the 0.3 drag, each droplet at a uniform moment of its flight; this capture's
  upward parts were 252-325 cm/s, under the cap). Clumping, the visible droplets in 32 px cells of Spray_Mud_Drive, CV over the 1260
  cells: 3.376 before (P2c), 3.817 after. **Deep**: MudTintFor exempts Deep from the wet x0.8 (luminance 0.0321; Standard 0.0360,
  Firm 0.0502, Stony 0.0383); the visible Deep droplets in Spray_Mud_Close read 0.0319. **Muddy rut splash** (the owner approved;
  Codex's SplashDepthM and water hunks untouched): UGTSprayComponent::StampWaterMud gives each new Water particle (SpawnWater leaves
  its id 0) the mud of the nearest wheel contact within 1.2 m when that contact is in a Mud patch - the patch's TurbidityAt there,
  the weight max(0.6, sqrt(turbidity)), the variant's MudTint - and PushWaterMud writes them after the Water kind's own transforms as
  its ISM's custom data 2 (weight), 3-5 (colour), 6 (turbidity) (the ISM raised to 7 floats in BeginArt). `setup_wheel_spray.py`
  adds the path onto M_GT_WaterSpray (built by benmore_water_interaction.py, not touched): base colour lerp(BaseColor, the colour,
  weight), the coverage's Alpha lerp(Opacity, 0.85, turbidity); roughness stays 0.7. Zeros outside a Mud patch and at gt.Spray.Art 0:
  the splash exactly as before. Gate (final image: the spray is translucent and writes no BaseColor; its pixels are where
  Spray_Mud_Close and _NoWater differ): 4386 px, median luminance 0.1011, R 0.1651 > G 0.0887 > B 0.0296. 33-53 tinted particles
  alive in the mud pictures. Tests 17/17 (CRC 8e0aad06).

## 100. Ground relief GR0-GR1: rolling strips, hummocks, pre-churned bogs, grass variation (2026-10-10)

docs/GROUND_RELIEF_PLAN.md GR0 (report only) and GR1. The owner: "The ground is too flat. the mud, the grass all of it is too
flat and smooth". No cost, timing or profiling measured (L_MudDrive's check ran with the new `GT_CHECK_NO_PROFILE=1`: no CSV
profile, no clod-cap timing phases). God of War Ragnarok (GoWR) was open at every Unreal run; no foreign Unreal ran. Water, Benmore
and river files and the Codex app's hunks untouched; the Snow strip, The Hide and the legs unchanged (every new number defaults to
the ground before GR1).

**GR0, Nanite tessellation on the landscape** (time-boxed, report only; probe files uncommitted: `Art/Unreal/probe_gr0_nanite.py`,
`/Game/GrandTour/ArtTests/GRProbe/L_GR_Probe` + `M_GR_ProbeLandscape`, `Art/Export/GRProbe/`):
- Copy of L_MudVariants: worked headless (`EditorLoadingAndSavingUtils.save_map`; `duplicate_asset` of a World left a standalone
  copy the next `load_level` could not collect: fatal "Old world ... not cleaned up by garbage collection").
- Nanite on the landscape: worked. `bEnableNanite` set by Python; the build happens in `ALandscapeProxy::PreSave`
  (`LandscapeInfo->UpdateNanite`) when the level is saved: 1 `LandscapeNaniteComponent`, its mesh's LOD0 4,589 triangles (the
  fallback). With `landscape.Nanite.LiveRebuildOnModification 1` the property change asked for a build while the proxy was not
  registered: "Assertion failed: Proxies.Contains(LandscapeProxy) [LandscapeSubsystem.cpp:1443]" (twice, also 10 s after the load).
- Tessellation + displacement on the material copy: BLOCKED headless. `MP_Displacement` is `UMETA(Hidden)` in `EMaterialProperty`
  (SceneTypes.h), so Python has no `MaterialProperty.MP_DISPLACEMENT` and `MaterialProperty.cast(32)` fails ("Cannot cast type
  'int' to 'MaterialProperty'"); `enable_tessellation` and `displacement_scaling` (Magnitude 8 cm, Center 0.5 = +-4 cm) are
  settable. A C++ editor helper (`UMaterialEditingLibrary` does not take the hidden pin either) would be the way.
- Settings: UE 5.8 has no `r.Nanite.AllowTessellation`; tessellation runs when `r.Nanite.Tessellation` (1), `r.Nanite.ProgrammableRaster`
  (1) and `r.Nanite.ComputeRasterization` (1) are on (`UseNaniteTessellation`, RenderUtils.cpp); `r.Nanite.DicingRate` and
  `r.Nanite.MaxPixelsPerEdge` set the density; `landscape.RenderNanite` (1) draws the Nanite landscape.
- Counts (`NaniteStats Primary`, on foot over the Standard patch, Nanite landscape without displacement): 242 clusters, about 90,500
  triangles, 20,649 vertices; diced (tessellated) clusters 0, patches 0.
- The patch hole: with the Nanite landscape on, the pictures show the Standard patch's area as dark ground with thin lit lines in
  step patterns (`GR0_Edge_Tess1.png`, `GR0_OnFoot_Tess1.png`); with `landscape.RenderNanite 0` the lit mud meets the landscape at
  the box edge as before (`GR0_Edge_NoNanite.png`). The masked hole (MPC_TrackPaint boxes) did not read as before under the Nanite
  landscape; cause unchecked.

**GR1** (C++: `GTTerrainGenerator`, `GTMudPatch`, new `GTReliefLibrary`; Python: new `Art/Unreal/ground_relief.py` holds every strip
number, the three setups apply it, new `Art/Unreal/relief_pictures.py`):
1. **Land** (`ground_relief.LAND`): base_amplitude_m 3.5 at 60 m, 4 octaves, persistence 0.5 on L_MudVariants and L_GravelDeform;
   **L_MudDrive 2.75 m** (the plan's rule: its route grade p95 away from the ford was 11.02 % at 3.5 m; the test's sweep 10.49 at 3.25,
   10.02 at 3.0, 9.76 at 2.75).
2. **Relief octaves**: `FGTTerrainSpec::RoughnessOctaves` (2 = the stage-2 relief exactly); 3 adds an octave at a third of
   `RoughnessWavelengthM`, weights 1 / 0.55 / 0.3 over 1.85; the strips 3 at 6 m (6, 3, 2 m), ScrubRoughnessM 0.45, MudRoughnessM 0.22.
3. **Hummocks** (`FGTHummockField`, `Density` 0 = none; `GTTerrain::HummockHeightM / HummockMask / HummockAtM / HummockCentres`):
   a Poisson count per 4 m cell (renormalised hashed 12 m value noise, x0.1-2.2 over its mean), radius 1.0-2.8 m truncated power law
   (exponent 2), height 0.15-0.5 m by the radius's place x0.8-1.2, a (1 - u^2)^2 dome whose rim is warped by three angular harmonics
   (k 2-3, 4-7, 8-15; +-25 %) and whose crest sits up to 30 % off centre (the ray from the crest to the warped rim), overlaps as
   sqrt(sum h^2); masked by (1 - the strongest road's presence)^3, the planes and the channels (a ford's channel stays clear). One
   addition the gate needed: each mound's height is capped so its radial flank stays at tan 30 deg over its shortest crest-to-rim
   reach (the field alone was 35.65 deg at 0.25 m without it).
4. **Pre-churn** (`FGTDeformProfile::PreChurnScale`, 0 = the flat field; `AGTMudPatch::ApplySection` reads the section's own
   `Deform.PreChurnScale` whatever its Mode, so a ByKind bog takes it; `gt.Mud.PreChurn` 1/0, read at Init): after the soft spots,
   before the mesh: hummocks in HeightCm (2.5 m and 1.2 m value-noise octaves, the amplitude 5-20 cm by a 5 m cluster noise squared),
   2-4 old rut pairs along the route line carried through the whole box (gauge 1.5-1.8 m, tyre 25-32 cm, centre +-1 m, wander +-1.5 m
   as two sines of 20-40 m and 1.6-2.1x that, depth 6-18 cm by knots every 2.5 m, x1.4 where S > 0.6) by the field's own
   `StampWheel` in 25 cm strokes (its own banks), 10 s of the field's own `Settle`, the rim faded over 1.5 m (heights, lumps and the
   base), the tread and the fresh sheen cleared, the render bounds widened. MR5's chunks sit only where the pre-churned surface is
   within 3 cm of the hummocked ground before the tracks ("the base": the hummock tops and the flats, never a rut or its bank), and
   "untouched" for `gt.Mud.Chunks` 1 again is against the pre-churned surface.
5. **Grass** (`FGTGrassVariation`, every number 0 / CrestTussockWeight 1 = the placement as given; `GTTerrain::VaryGrass`,
   `UGTReliefLibrary::VaryGrassTransforms`): height x1 +- 0.45 from 3 m and 0.8 m Perlin octaves (uniformised), the width x its
   root; bare gaps where a 2 m noise is under a local share moved 10-25 % by a 12 m noise; a lean of half the ground's slope plus
   a 1.5 m noise lean, clamped to 12 deg; tussocks on a crest (the hummock field at least 60 % of its mound's peak) get one companion
   0.3-0.7 m off (x2). The strips' setups pass every tussock kind through it (Fine grass without the crest weight).

**Numbers** (setup reports `relief`, `GrandTour.Relief.Strips`):

| Strip | Grade p95 (away from fords) | Cross p95 | Before GR1 grade / cross | Hummocks (in grid, stamped) | NN CV | g(r) peak beyond NN | Field slope max | Ground on hummocks at 1 m max / p99 |
|---|---|---|---|---|---|---|---|---|
| L_MudVariants | 7.32 % | 3.96 % | 5.54 / 2.55 | 5,146 / 4,774 (8.10 per 100 m^2) | 0.559 | 1.157 at 2.25 m | 33.6 deg | 38.2 / 27.1 deg |
| L_GravelDeform | 5.25 % | 0.38 % | 0.54 / 0.48 | 2,938 / 2,710 (8.22) | 0.566 | 1.150 at 2.75 m | 34.0 deg | 32.7 / 19.6 deg |
| L_MudDrive (2.75 m) | 9.76 % (whole route 13.91 %) | 2.96 % | 4.10 / 2.10 (whole route 10.82: the ford) | 2,938 / 2,613 | 0.566 | 1.150 at 2.75 m | 34.0 deg | 42.2 / 26.5 deg |

Pre-churn per L_MudVariants bog (`GrandTour.Mud.PreChurn`, the strip's CRCs as the new strip baseline):

| Bog | CRC | Pairs | Depth asked | Hummocks | Surface | Water cells | Rim | Chunks planned (without; of those kept / moved) |
|---|---|---|---|---|---|---|---|---|
| Firm | ee8ffa80 | 2 | 6.0-22.9 cm | +-19.9 cm | -21.1..17.7 cm | 0 of 33,681 | 0.101 cm | 4 (6; 3 / 3) |
| Standard | ce21021c | 4 | 6.0-24.9 cm | +-19.9 cm | -24.0..19.9 cm | 0 | 0.088 cm | 5 (10; 5 / 5) |
| Deep | 027d22e5 | 3 | 6.1-23.3 cm | +-20.0 cm | -20.7..20.0 cm | 244 (0.72 %) | 0.101 cm | 10 (16; 11 / 5) |
| Stony | 8981a1c7 | 2 | 6.3-23.8 cm | +-20.0 cm | -22.5..20.0 cm | 0 | 0.070 cm | 8 (11; 8 / 3) |

The old ruts reach at most 25 cm (18 x 1.4) against Standard's -25 cm table, so only Deep's (-15 cm) holds rut water. The mean
|surface| within 25 cm of the rim is 0.09-0.13 cm against 4.7-6.5 cm 1.5 m in.

Grass (setup reports): height scale x0.550-1.450 on every kind and strip, bare share 16.9-20.3 % per kind (L_MudVariants Straw 16.9,
Rust 19.4, Weathered 19.6, Fine 18.7; L_GravelDeform straw 18.9; L_MudDrive 17.9-20.3), lean at most 12.0 deg, crest companions
L_MudVariants 200 / 168 / 51, L_GravelDeform 28, L_MudDrive 94 / 99 / 22.

**Tests**: 17 of 17 GrandTour.Mud, Snow and Gravel (with the new GrandTour.Mud.PreChurn), GrandTour.Spray.Art and the new
GrandTour.Relief.Strips PASS; the mud CRC 8e0aad06 unchanged (Settle, MuddyWater on/off); GrandTour.Mud.SoftSpots and Chunks keep
the flat field (their copy of DA_MudVariants zeroes PreChurnScale). Full suite once (GoWR open): 27 PASS, 1 FAIL - terrain at the bog escape (7.0 m forward in 12 s, 8 asked: the standing gate under GoWR since MR4); its one rerun: the escape 9.0 m PASS, step 11's held exit FAIL (10.3 m against 10.5 m down the ruts: the standing flake). Nothing of GR1 reaches The Hide: the biome test's The Hide and L_Proving hashes are unchanged. The rerun's pre-check listed an Unreal process and the run went on in the same command (a slip); a foreign Codex capture (capture_benmore_fleet_driving.py) started at 14:41, at the rerun's end.

**Drive checks** (sections against today's reports): GoWR held the editor to a fraction of real time (4-10x more samples per metre than today's), so each check hit its real-time cap and none completed: L_MudVariants timed out at 140.77 m, inside Deep, after 300 s (today's report, no game: completed in 81.5 s; the MR2 scripted pass then took Deep and Stony); L_GravelDeform "stalled" at 65.9 m at its 100 s pass cap while doing 16.1 km/h; L_MudDrive's first two dry runs reached 36.6 and 19.5 m in their 110 s. Completion is owed a run without a game. Section speeds (the mean of the sampled instantaneous speed, game time; today's from its report): L_MudVariants Firm 27.0 km/h (31.3), Standard 23.2 (23.3), Deep 2.6 over its first 20.8 m (2.0), Stony not reached by the drive (22.4); L_GravelDeform 0-30 m 14.2 (14.7), Firm 16.1 (16.1), 55-80 m 16.1 (16.1), Loose not reached (16.2); L_MudDrive gravel 5-32 m 15.7 (15.8), the bog 12.0 over its first 4.6 m (2.9 over all of it), the ford not reached (13.6). L_MudDrive's check ran with `GT_CHECK_NO_PROFILE=1` (new; no CSV profile, no clod-cap timing phases). The checks' drive reports stay uncommitted (the committed MudVariants report is the check's own baseline).

**Pictures** (same cameras before (`GR1_Before/`) and after, the sun behind the camera, yaw -58): `Art/Export/MudVariants/Relief_Overview.png`,
`Relief_OnFoot.png`, `Relief_Bog.png`; `Art/Export/DeformableGravel/Relief_Overview.png`, `Relief_OnFoot.png`;
`Art/Export/LiveMudDrive/Relief_Overview.png`, `Relief_OnFoot.png`, `Relief_Bog.png`; and the checks' own pictures. Not described
from code: the owner looks.

**The owner's list** (proposals in `Art/Unreal/ground_relief.py`): land 3.5 m at 60 m, 4 octaves, 0.5 (L_MudDrive 2.75 m); relief 3
octaves at 6 m, scrub 0.45 m, bog 0.22 m; hummock density 8 per 100 m^2 (cluster 12 m x0.1-2.2, radius 1.0-2.8 m, height 0.15-0.5 m,
rim 25 %, crest 30 %); PreChurnScale 1 (depth 6-18 cm, 2-4 pairs, hummocks 5-20 cm, 10 s settle); grass x0.55-1.45, bare 10-25 %,
lean 12 deg, crest weight 2. Switches: `gt.Mud.PreChurn`; spec numbers at 0 for the rest.

## 101. Ground relief GR1b: old tracks without crease lines; the pale rectangle identified (2026-10-10)

docs/GROUND_RELIEF_PLAN.md GR1b items 1-2 (the main session's look at GR1). No cost or timing measured; GoWR open at every run; every
Unreal and UBT run started only after `Art/wait_unreal_free.ps1` (new, committed here) printed UNREAL FREE in its own command.

- **The cause** (`gt.Mud.PreChurnDebug`, new, read at Init: 1 the tracks factor cleared, 2 the field smoothed, 4 the lumps cleared;
  `Art/Unreal/crease_debug.py` shoots the Relief_Bog camera with each and with runtime switches; `Art/Export/GroundRelief/CreaseDebug/`).
  Near-black pixels (luminance under 12) in the picture's lower half on GR1's tracks: as built 0.391 %, no mesh shadow 0.084 %, smoothed
  0.182 %, gt.Mud.POM 0 0.312 %, gt.Mud.POMShadow 0 0.404 %, SSAO off 0.383 %, tracks cleared 0.425 %, lumps cleared 0.356 %. The lines
  were the bog mesh's own shadow inside the wheel stamp's trough (a tyre-wide flat floor between near-vertical two-cell walls).
- **The fix** (`AGTMudPatch::PreChurn`): old tracks drawn as cosine troughs instead of stamped - half width max(2.6 x depth, tyre / 2 +
  20 cm) x (1 +- 0.2 on 2-4 m knots), a cosine bank beside (PreChurnBankReturn 0.5 of the section), depth on 1-3 m knots (6-18 cm, x1.4
  where S > 0.6), 20-40 % of each line filled back to 30-60 % in 0.8-3 m segments with irregular gaps (0.4 m ramps inside them),
  LM2's lumps re-seeded over troughs and banks (LumpShare x the disturbance x the field's lump-dome weight, at most LumpMaxCm), the
  tracks factor at half the trough's shape, the cells woken for the 10 s settle (`FGTMudField::WakeEdited`, new). New numbers:
  PreChurnWallPerDepth 2.6, PreChurnWidthWander 0.2, PreChurnDepthKnotMin/MaxCm 100/300, PreChurnFillShareMin/Max 0.2/0.4,
  PreChurnFillDepthMin/Max 0.3/0.6, PreChurnBankReturn 0.5. On the new tracks the mesh shadow no longer moves the dark share (0.420 ->
  0.410 %); the dark marks left along the troughs' far walls fall with gt.Mud.POM 0 (0.276 %): MRP's parallax there, not changed
  (`Art/Export/GroundRelief/CreaseDebugGR1b/`).
- **The pale rectangle**: the strip's gravel road (the landscape's Dirt layer) in the 6.4 m between Standard's box (to 106.8 m) and
  Deep's (from 113.2 m), its ends softened by the two 3 m patch-slice aprons (`CreaseDebug/Gap_TopDown.png`); present in GR1_Before,
  so LM5b's layout, not GR1's: reported, not changed.
- **GrandTour.Mud.PreChurn** (new rows: the filled share 15-45 %, filled no shallower than 40 % of the shallowest depth, no trough cell
  at 60 degrees or more):

| Bog | CRC | Pairs | Depth | Filled to / share | Trough cells | Steepest | Surface | Water cells | Chunks (without; kept / moved) |
|---|---|---|---|---|---|---|---|---|---|
| Firm | 4a20b9b2 | 2 | 6.0-24.5 cm | 3.0 cm / 28.4 % | 5,957 | 35.0 deg | -23.9..18.5 cm | 0 | 4 (6; 5 / 1) |
| Standard | 44371c3f | 4 | 6.0-25.1 cm | 2.9 cm / 25.2 % | 9,114 | 33.1 deg | -25.6..19.9 cm | 4 | 6 (10; 7 / 3) |
| Deep | 10a17173 | 3 | 6.1-22.4 cm | 2.9 cm / 30.1 % | 7,368 | 23.8 deg | -14.7..20.0 cm | 0 | 11 (16; 13 / 3) |
| Stony | 587ccf09 | 2 | 6.1-19.8 cm | 2.5 cm / 34.6 % | 5,038 | 33.4 deg | -20.0..20.0 cm | 0 | 8 (11; 8 / 3) |

  The troughs now cut below the hummocked ground rather than to an absolute depth, so Deep's rut water (244 cells in GR1) is gone:
  its deepest cell sits at -14.7 cm against its -15 cm table. Rims at most 0.10 cm. 17/17 Mud, Snow and Gravel; the fixture CRC 8e0aad06.
- **Pictures** (GR1's cameras exactly, `GT_RELIEF_CAMERAS`; GR1's set kept in `GR1/`): `Art/Export/MudVariants/Relief_Overview.png`,
  `Relief_OnFoot.png`, `Relief_Bog.png`; `Art/Export/LiveMudDrive/Relief_Overview.png`, `Relief_OnFoot.png`, `Relief_Bog.png`.
- Owed: the strips' drive checks with no game open; the suite was not rerun (only the bog field changed).

## 102. Checks under a running game: fixed time step, render only for captures, game-time limits (2026-10-10)

docs/CHECKS_UNDER_GAME_PLAN.md items 1-6 (the owner: "make it run whilst gow is running then. Optimise it properly"), for
check_mud_variants.py, check_deformable_gravel.py, check_live_mud_drive.py and check_wheel_spray.py. Wall-clock duration and the check
runs' frame rate are reported as a pipeline measure only; no game performance numbers. Every run started after
`Art/wait_unreal_free.ps1` printed UNREAL FREE in its own command.

- **Why they crawled:** under GoWR / Ace7Game the rendered checks ran at 1-3 frames a second, and at that rate the world's clamped
  delta (up to 0.1 s) outran the physics (at most 1/30 s a frame): a first fix that only counted game seconds still timed out
  (L_MudVariants at 142.6 m in Deep after 300 game s, 1.9 frames a second; L_MudDrive at its 40 min cap after two of four runs).
- **1. Fixed time step:** the wrappers pass `-UseFixedTimeStep -FPS=60`; it takes in editor Play In Editor (FEngineLoop::PreInit sets
  FApp's fixed delta, UEngine::UpdateTimeAndHandleMaxTickRate steps every frame by it). Verified per run over 300 frames of the drive
  (`check_run.fixed_dt`): every world delta 0.016667 s (min = max = 0.016667) in all eight fixed-step runs; the two real-step
  comparison runs read 0.0167-0.4 and 0.0167-0.051.
- **2. Game-time limits:** the drive caps, leg caps, stall timers and the phases' waits count game seconds (`gt()`, a physics clock
  that equals the world's time at the fixed step); the only wall-clock limit is a 40 min safety cap per check. The reports' drive
  times and speeds were in WALL seconds before (section times, `elapsed_s`, the samples' `t`); they are game seconds now (`time_base`).
- **3. No rendering while driving:** `Art/Unreal/check_render.py` (`Gate`) drives `ShowFlag.Rendering` (it works headless): off by
  default; on from a picture's request, 30 frames of warm-up, the capture, and until its file is newer than the request. GPU reads
  inside rendered windows only: L_MudVariants' two track-paint readbacks (MR1's exit profile, the verge points) now wait for the gate;
  the spray check renders the kill check (30 frames before its burst, then throughout), a spin or launch's act, a drive's last 2 game s
  (its capture waits 90 rendered frames) and the paused captures; L_MudDrive renders the settle pair's watch and takes its cockpit
  pictures 30 frames after the mark. No other gate reads the GPU while driving (the track paint's CPU grid, the mud field and the
  spray pools are CPU). `GT_CHECK_RENDER_ALWAYS=1` renders every frame; `check_live_mud_drive.ps1 -Profile` is the owner's cost run as
  before (real step, every frame, -csvGpuStats); the default is fixed step, no CSV profile (`GT_CHECK_NO_PROFILE=1`).
- **4. GPU wait only while rendering** (VRAM_SOAK's per-tick readback, where the check has one).
- **5. Correctness.** All runs fixed step unless said:

| Check | No game: wall / fps | GoWR open: wall / fps | Gates |
|---|---|---|---|
| L_MudVariants | 362 s / 83 (drive 96) | 1,420 s / 19 (drive 47) | completed both; PBR_CarryWet FAIL (below) |
| L_GravelDeform | 268 s / 73 (passes 93-96) | 392 s / 26 (passes 54-68) | 10/10 both |
| L_MudDrive | 372 s / 90 (runs 89-94) | owed (no game open at that point) | completed, four runs |
| Wheel spray | 191 s / 79 | owed | report ok; two P2c/P2d rows FAIL (below) |

  Before the pipeline the with-game L_MudVariants and L_MudDrive checks ran 40+ min and did not finish their drives.
  Section speeds, L_MudVariants (km/h): fixed step no game Firm 31.95, Standard 29.19, Deep 1.73, Stony 21.86 (89.7 game s); with GoWR
  31.03 / 28.27 / 1.71 / 22.13 (91.3 s, within 3 % of no game); the old way on the same GR1b ground (real step, rendered every frame,
  no game) 30.04 / 27.66 / 1.55 / 19.81 (102.5 s): the fixed 1/60 s step drives 5-12 % faster than the real step (at 40 frames a
  second), over the plan's 5 %. Against the committed baseline (2026-10-09, pre-GR1 ground) the comparison mixes in GR1/GR1b's ground:
  31.3 / 23.3 / 2.0 / 22.4. L_GravelDeform's sampled speeds match the baseline within 0.1 km/h past the start (0-30 m 13.1 / 14.7).
  **Gates that moved under the fixed step:** L_MudVariants PBR_CarryWet FAIL (no game: the carried mud's median roughness 0.439,
  62.5 % under 0.45; with GoWR 0.231) where the real-step run on the same ground PASSes (0.451); the spray check's Spray_Mud_Close
  "droplets above the arch" FAIL (0.099, asked 0.25; real step 0.452: at the 3 s capture of the Deep spin the right rear's rate was 65
  against 257, the live droplets 142 against 253). Its "muddy splash" row fails both ways (60 / 1 water pixels): GR1b's Deep has no rut
  water now. Causes unchecked. The baselines are re-based to the fixed-step no-game runs (the committed reports).

## 103. Ground relief GR1c: old tracks fade, merge and hold puddles (2026-10-10)

docs/GROUND_RELIEF_PLAN.md, decisions after phase A, "GR1c, old tracks as a layout" (the main session's look at GR1b: from above, a
bundle of long, narrow, parallel grooves). No game was open at any run; every run started after `Art/wait_unreal_free.ps1` printed
UNREAL FREE in its own command (the Codex app's Benmore profiling held Unreal several times in between). No timing.

- **Count and wander (AGTMudPatch::PreChurn):** `PreChurnPairs` 1, `PreChurnPairsLong` 2 where the route runs more than
  `PreChurnLongPatchCm` 40 m through the patch's box (L_MudVariants' four boxes: 38.2 m, 1 pair; L_MudDrive's: 41.2 m, 2 pairs).
  Each pair keeps its own centre and two-sine wander (GR1's), so two pairs cross, merge and split; the random 2-4 is gone.
- **Width and depth:** each wheel line's width at half depth is `PreChurnWidthMin-Max` 1.4-1.9 x its tyre (knots 2-4 m apart; the
  trough still at least `PreChurnWallPerDepth` 2.6 x its depth wide); depth `PreChurnDepthMin-MaxCm` 5-14 cm on knots 1-3 m apart, the
  soft spots' x1.4 kept inside the range. GR1b's fills (20-40 % of the length back to 30-60 %), banks and lumps stay.
- **Fading:** each pair's presence fades in and out over `PreChurnFadeMin-MaxCm` 3-8 m at random points (holds from a 16-28 m
  cycle), drawn until 35-60 % of the route's stretch in the box is present and the stretch inside the rim has both an absent and a
  present place; the two wheel lines' fades sit up to 0.75 m apart. The depth, the bank, the tracks factor and the lumps follow it.
- **Puddles (step 3b, after the settle):** cut before the settle, a puddle came out 10-15 cm shallower and above the table (the
  settle's relax gives a set cell `RecoverShare` of its depth back), so the puddles are cut into the settled field: along each wheel
  line the lowest-lying 20-30 % of its present length in the box (the settled floor under its centre) makes the runs, each run's floor
  2-5 cm under the patch's `WaterTableCm` (Standard -25, Deep -15), ramped over 1.5 m either side, lumps cleared under it, a cosine
  trough at least the track's width and `PreChurnPuddleWallPerDepth` 4.5 x the extra cut wide with a bank beside it, not woken (no
  relax takes it back before a wheel works it). Every bog here has a table, so all four get puddles.
- **POM self-shadow (M_GT_Mud, Art/Unreal/live_mud_style.py):** x a slope factor of the field's own normal - 1 to
  `MudPomShadowSlopeLo` 15 deg, linear to `MudPomShadowSlopeMin` 0.3 at `MudPomShadowSlopeHi` 30 deg, held beyond; rebuilt by the strip
  setups (compile errors none).
- **Numbers (GrandTour.Mud.PreChurn, the strip as play builds it):**

| Patch | CRC | pairs | present | depth asked | filled | puddles (of present) | cut into the settled floor | water cells (table) | steepest trough cell |
|---|---|---|---|---|---|---|---|---|---|
| Firm | d23d3b51 | 1 | 42.3 % | 5.0-14.0 cm | 28.2 % to 2.4 cm | 26.2 % | 19.7 cm at most | 198 of 33,681 (-25) | 42.6 deg |
| Standard | 1e549040 | 1 | 45.2 % | 5.1-14.0 cm | 33.1 % to 2.7 cm | 27.9 % | 27.0 cm | 237 (-25) | 43.5 deg |
| Deep | eefac94d | 1 | 53.4 % | 5.9-14.0 cm | 31.2 % to 2.6 cm | 29.3 % | 15.9 cm | 287 (-15) | 42.8 deg |
| Stony | 58be0a5c | 1 | 54.6 % | 5.3-14.0 cm | 20.1 % to 4.1 cm | 27.4 % | 22.0 cm | 188 (-25) | 42.6 deg |
| L_MudDrive | (play log) | 2 | 45 %, 58 % | | | 26 % | 21.7 cm | 522 of 36,297 (-25) | 41.6 deg |

- **Gates:** water-holding cells in Deep (287) and Standard (237) over 0 (GR1b: 0 and 4); the fixtures' CRC 8e0aad06 unchanged
  (GrandTour.Mud.Settle and MuddyWater); tests 18/18 PASS (GrandTour.Mud, Snow, Gravel, Relief; PreChurn's new rows: 1 pair under 40 m,
  each pair 35-60 % present, depths 5-14 cm, puddles 15-35 % of the present length, water in Standard and Deep). The steepest trough
  cell rose from GR1b's 23.8-35.0 deg to 41.6-43.5 deg (the post-settle puddle cut on the settled walls; the test's no-wall gate is 60 deg).
  From above, "no more than 2 long grooves per patch" is the main session's look.
- **Pictures** (the GR1b cameras, `GT_RELIEF_CAMERAS=Art/Export/GroundRelief/pictures-gr1b.json`): Art/Export/MudVariants/Relief_Overview.png,
  Relief_OnFoot.png, Relief_Bog.png and Art/Export/LiveMudDrive/ the same three; copies in each strip's GR1c/, GR1b's kept in GR1b/.

## 104. Checks after the fixed step: spray rendered through its scenarios, the carried-wet gate, the frame-rate finding (2026-10-10)

docs/GROUND_RELIEF_PLAN.md, decisions after phase A, "Checks after the fixed step". No game was open at any run; every run started after
`Art/wait_unreal_free.ps1` printed UNREAL FREE in its own command. Wall-clock duration and frame rate of the check runs only as a
pipeline measure.

- **Spray (Art/Unreal/check_wheel_spray.py):** every spray scenario renders from its throttle-on to its capture (the drives rendered only
  their last 2 game seconds before, so Niagara's GPU particles had a shorter life than under the real step); the kill check and the
  captures as before; the other checks keep their windows. Run (no game, fixed 60 Hz): 191.9 s, 13,842 frames of which 4,695 rendered.
  Spray_Mud_Close droplets above the arch PASS again: 992 droplet pixels, 66.4 % above (fixed step before: 426 and 9.9 %, FAIL; real
  step 1,735 and 45.2 %). Base colours, dust in shadow, droplet height and clumping PASS.
- **Muddy splash: still FAIL.** The spin at 132.4-133.1 m stands in no water: the CPU Water spray's live count 0 and the muddy-splash
  count 0 at both captures; the 235 changed pixels between Spray_Mud_Close and _NoWater are scattered over the bright background (median
  luminance 0.533 with water, 0.518 without). GR1c's Deep puddles (287 cells) lie where the old track's floor is lowest, not under the
  car at 132 m. Note: the build included the Codex app's uncommitted GTSprayComponent.cpp, whose wheel splash now comes from
  "water-only emitters" fed by the local relative water speed (`WaterSpeedMps = 0` in the wheel loop) - a car spinning in place has none.
  Not changed here.
- **PBR_CarryWet - the cause is not the track paint.** The check now reads the CPU mirror against RT_TrackPaint over the carried spot's
  grid (200-206 m, +-1.5 m, 25 cm cells): with the scene not rendered, mean G 0.322 / 0.309 and B 0.813 / 0.784 (CPU / GPU), with it
  rendered every frame 0.348 / 0.333 and 0.816 / 0.790; the per-cell differences are blob edges (a texel against a 25 cm cell). Writes
  and decays run on the subsystem's Tick DeltaTime (game time) and canvas draws that do not depend on the viewport's ShowFlag.Rendering.
  MF_Weather's inputs there: MPC wetness 0.9998, the occlusion open 1.0 everywhere (cover within 2 cm of the ground), fill 1.0.
- **What moves it:** the gate's median over the brown, dark pixels. The floor (MF_MudCover's FloorMask = the cover c) encodes as 114 or
  115 of 255 in the GBuffer (0.447 or 0.451) around the 0.45 threshold; the trail's partly covered edges sit between the weather's value
  and the floor by design; MF_Weather's standing water (0.03, the floor off by design) covers 31-41 % of the gravel in view at test
  wetness 1, a world-fixed patch the trail runs into or not depending on its lateral line (y 0.5 / 0.75 / 1.0 m across today's runs).
  Today: fixed 60 Hz 0.447 (51 % at the floor, 47 % edges, 2 % in water), the same rendering every frame 0.451 (y 0.5), fixed 85 Hz 0.031
  (y 1.0: the whole trail in standing water), the final run 0.439 (47 % at the floor, 6 % in water).
- **The fix (Art/sample_mud_pbr.py):** the carried-mud pixels in the weather's standing water (roughness under 0.06) are left out and
  counted, the floor is read on the fully covered mud (p75) against 0.446 (one 8-bit step under 0.45), at least 5,000 unpuddled pixels;
  the median stays reported. Final run: 12,549 unpuddled, p5/25/50/75/95 0.129 / 0.365 / 0.443 / 0.451 / 0.451 -> PASS; the 85 Hz run
  would read FAIL (no unpuddled mud in view). A broken floor (the weather glossing the mud to about 0.15-0.3) fails it.
- **The frame-rate finding (report only):** no per-frame term without dt in the traction, sinkage or stamping. UGTTractionComponent::Update
  grows and recovers sinkage x DeltaSeconds, loads mud by distance, rolls the tread x DeltaSeconds, and its drags are forces
  (UGTVehicleTuningComponent::ApplyRollingResistance, AddForce); the drivetrain sets torques; FGTMudField::StampWheel cuts to the tyre's
  sinkage along the stroke since the last tick (a target, not an accumulation; its smoothing already per stroke length), Settle runs fixed
  1/30 s sub-steps from an accumulator, the track paint stamps by distance plus StationaryDigRate x DeltaSeconds. The one frame-weighted
  filter is the tyre load's FInterpTo (alpha = 16 x dt a frame: an effective 18.6/s at 60 Hz, 17.7/s at 85 Hz; it feeds LoadCorrection,
  Chaos's friction multiplier). Measured on the same GR1c strip (the check's new per-section traction means): fixed 85 Hz against fixed
  60 Hz Firm 30.36 against 30.00 / 29.67 km/h, Standard 28.54 against 28.27 / 28.12, rolling resistance 0.326 / 0.319, plough 0.232 /
  0.228, mean sinkage 21.0 / 21.7 cm; Deep at 85 Hz stalled at 144.0 m (60 Hz crossed at 1.81 / 1.71 km/h). Two identical fixed-60 runs
  differ by 1.1 % (Firm), 0.5 % (Standard), 6 % (Deep), 14 % (Stony): the drive is not deterministic run to run. Rendering every frame
  (fixed 60): Firm 29.83, Standard 27.55. So the step's size moves Firm and Standard within that spread. The real step's 6.0 % (Firm)
  and 5.2 % (Standard) slower (GR1b strip) lie outside it, its Deep 10.4 % and Stony 9.4 % near or inside it; that difference goes with
  the step varying frame to frame (80-90 Hz) and with every frame rendered, which no term in this code integrates differently - Chaos's
  own per-step wheel and suspension solve was not audited. Not fixed (the owner's call).
- **Pipeline:** Art/check_mud_variants.ps1 -Fps <n> (another fixed step for a comparison run; 60 is the check's own); the MV report's
  sections carry `traction_means` and MRP's `wet_mirror` (CPU / GPU paint, MPC_Weather, the occlusion's open and fill). L_MudVariants
  (no game, fixed 60): 348.7 s, 28,987 frames, 3,884 rendered. The committed reports are the final no-game runs.

## 105. Ground relief GR2 phase B: soil detail with anti-tiling and parallax, ground scatter (strips only) (2026-10-11)

docs/GROUND_RELIEF_PLAN.md GR2 phase B, items 0-7 (the main session's design after its look at phase A2). Every Unreal or UBT run
started after `Art/wait_unreal_free.ps1` printed UNREAL FREE in its own command (the Codex app's Benmore profiling held it for long
stretches); no game was open at any run. No timing or cost measurement; instruction, sampler and instance counts only. Strips only: The Hide's
M_GT_Landscape, the legs, the snow strip and L_Proving are untouched (the biome test PASS: The Hide 0x977AF3A498E07815 and L_Proving 0x7DBDFB11F2FD2CE1 unchanged; M_GT_Landscape's counts unchanged).

- **Item 0, the bake fix (Art/Blender/bake_ground_detail_gr2.py, `stage=bake`; the rng stream is A2's, so clods, pebbles, litter, wash
  and dabs are A2's exactly):** the cracks' colour darkening 0.35 -> 0.1225 (0.35 of A2's); the crack presence noise 6-30 cm -> 4-18 cm
  and its smoothstep 0.55-0.72 -> 0.74-0.86, so 36.5 % -> 20.0 % of the tile keeps cracks; and no crack within 1-2.5 cm of a Voronoi
  vertex (F3 - F1), so runs no longer join at the cells' corners. Measured on the crack mask over 0.3 (8-connected, periodic): 6,770 ->
  2,913 runs (235 -> 88 of 20 px or more), extents p50 / p95 / max 2.05 / 4.49 / 6.64 -> 1.95 / 2.83 / 5.57 cm, 26,423 -> 10,133
  pixels, the largest run 309 -> 127 px; the crack pixels' luminance against the rest 0.630 -> 0.769 (the albedo's horizon-AO term alone
  0.83). Manifest block `phase_b_item0`. Re-render `Art/Export/GroundDetailGR2/ScrubSoil_AntiTile.png` (A2's kept as
  `ScrubSoil_AntiTile_A2.png`; `ScrubSoil_AntiTile_Single.png` the one-sample reference). SoilUnderGrass: its root fibres are 0.886 of
  the rest's luminance and its own anti-tile view (`SoilUnderGrass_AntiTile.png`) was rendered for the look; the roots were not changed.
- **Finding (contradicts the plan's premise, report only):** the 4 cm-blurred luminance contrast of the tile (its mid-distance read) is
  0.0781 before and 0.0780 after the fix. A scratch decomposition of the bake's colour terms (each frozen at its mean in turn; the
  contrast after a 5 / 10 / 20 cm Gaussian): full 0.068 / 0.034 / 0.009; the colour wash (`band_noise` 20-80 cm + 5-20 cm, weight 0.6)
  frozen 0.023 / 0.011 / 0.005; the crack paint off 0.068 / 0.034 / 0.009 even at A2's darkening; the AO term, dabs, clod tops,
  pebbles and litter each change it by under 0.002. So the rows of darker patches at mid distance come from the 2 m tile's own colour
  wash (two thirds of the mid-distance contrast), not the crack paint; the crack fix does not remove them (the re-render is for the
  main session's look). Not changed beyond the plan's item.
- **Item 1, import (`Art/ground_detail_gr2.ps1 -Step import` -> `Art/Unreal/import_ground_detail.py`):** `/Game/GrandTour/ArtTests/
  GroundDetail/TA_GD_{Color,Normal,ORH}` (slice 0 ScrubSoil, 1 SoilUnderGrass; 2048, BC1 sRGB / BC5 / BC7 linear, wrapped) by the mud's
  array builder; the 20 scatter meshes SM_GD_* from their FBX (vertex colour replaced, imported normals, no collision, no Nanite; the
  sizes checked against the manifest to 0.5 cm); MPC_TrackPaint's `GroundDetail` scalar (default 1; 14 scalars, no vector shift).
- **Item 2, the landscape (`Art/Unreal/ground_detail.py`):** *fact against the plan:* the strips have no shared parent - each has its
  own copy of M_GT_Landscape (M_VariantsLandscape, M_LiveLandscape, M_GravelLandscape; The Hide's M_GT_Landscape is not touched). So
  each copy takes the static switch `GroundDetail` (off: its default) and each strip folder an `MI_GT_Landscape_Strips` with it on, which
  the strip's landscape wears (the plan's name, one per strip). Where: M_VariantsLandscape and M_LiveLandscape on the Scrub row's
  colour, roughness and normal inputs of their layer blends (the row's mud apron, groundtex's ClayBlend, keeps the mud's colour);
  M_GravelLandscape - whose whole ground is its gravel surface - on its outputs, weighted by the surface's own grass verge (3.75-5.9 m
  off the line). Slice 1 where the grass is dense: `T_GD_Grass_<strip>`, a 50 cm map of every grass instance's root footprint (tussocks
  0.55 m x their XY scale, the fine undergrass 0.40 m; from the tussock style study's lobes and roots), blurred 1 m, smoothstep 0.2-0.5
  of the cover (dense on 2.2 % of L_MudVariants, 2.7 % of L_MudDrive, 0 % of L_GravelDeform's 320 scattered tussocks); it and its
  bounds are the parameters' defaults on each copy. Colour = layer x (detail luminance / the slice's mean: 0.101, 0.0622) at 70 %, the
  bake's own colour at the layer's luminance at 30 %; the 13 m tint's ends divided by their midpoint so the mean palette stays.
  Roughness the bake's ORH G; the normal the bake's (uv (x, -y) / 2 m, A's (x, -y) as the gravel's, B's turned back by its rotation and
  scaled by its tile). Anti-tile: sample B at 2.7 m, turned 37 deg, offset (0.37, 0.61), blended by a 7 m gradient-noise fBm (3
  octaves) through smoothstep 0.45-0.55. POM: the gravel's code (adaptive 8-16 steps, 3 bisections, a 4-step sun self-shadow within
  4 m x0.5) over ORH B at 1.5 cm, full to 15 m, none past 25 m; the whole detail fades into the old look over 25-40 m. All numbers are
  material parameters (GD*). `gt.Ground.Detail` (UGTTrackPaintSubsystem -> MPC GroundDetail) 0 = the old look.
- **Shader counts (`Art/ground_detail_gr2.ps1 -Step stats`, MaterialEditingLibrary.get_statistics; Art/Export/GroundDetailGR2/
  shader-stats-{baseline,after}.json):** today -> the parent with the switch off: M_VariantsLandscape 496 -> 496 pixel instructions,
  155 -> 155 vertex, 8 -> 8 samplers, 3 -> 3 pixel texture samples; M_LiveLandscape the same; M_GravelLandscape 201 -> 201, 155, 3 -> 3,
  3 -> 3 (the off path is the old wiring, so the same shader). With the switch on: M_GravelLandscape 591 pixel instructions, 6 samplers.
  The live copies' static counts hold no layer row at all (the stats compile the layer blends without a landscape: 496 / 8 for their MI
  too, a Scrub preview weight or the Dirt row fed the Scrub input changed nothing), so a probe copy of each with the Scrub row's input
  bypassing the three blends was counted (GroundDetail/Probe/, uncommitted content): off 520 / 8 samplers, on 1,232 / 12. The Hide's
  M_GT_Landscape 323 / 155 / 6 / 12, as before. M_GT_GroundScatter 283 pixel, 206 vertex, 3 samplers.
- **Item 3, the scatter (`AGTGroundScatter`, Source/GrandTour/Terrain/GTGroundScatter.h; placed by `ground_detail.apply_strip` at each
  strip's setup, deterministic, one hierarchical instance component per mesh, saved with the level):** open ground = the off-road
  layer's weight at least 0.9 (`GTTerrain::OffRoadWeight`, new), outside every section's patch box (`DeformPatchBoxCm`: mud, gravel, a
  ford's bed) grown 3 m, and off every channel. Densities per m^2: clods 0.6, pebbles 1.5, twigs 0.05; litter 0.25 within 1.5 m of a
  tussock; a mound under every tussock whose root footprint is 25 cm or more (tussocks 0.55 m x their scale), the nearest of the three
  scaled to it. Clustered: 3 m value noise sharpened by a smoothstep over 0.25-0.75 (as DG1b's) mapped to x0.1-2.5 and renormalised
  (unsharpened it spanned only x0.33-1.67 at p5-p95; sharpened x0.08 at p10, x1.88 at p90). Clods and pebbles by a power law (3-12 cm,
  1-5 cm, alpha 1.5) to the nearest mesh, scaled x0.8-1.25; twigs and litter any mesh x0.85-1.15; a random yaw; dropped by a trace
  onto the landscape, aligned to its normal; A2's clods, litter and mounds carry their own embed, the pebbles and twigs sink 30 % of
  their height. Cull 30-40 m (twigs and litter 18-25 m), dithered by PerInstanceFadeAmount. M_GT_GroundScatter: vertex colour x the
  strip's palette (live_mud_style.GROUND_HLSL's n); the soil families (clods, mounds) the ground's own path (palette x the ScrubSoil
  luminance, box-projected at 2 m) x A2's tints, the others their A2 tint x the palette's local swing; the ScrubSoil normal box-projected
  as a 1.5 cm bump; wet x0.75, rough to 0.45; litter two-sided. `gt.Ground.Scatter` 0/1, `gt.Ground.ScatterDensity` 0-1 (a stable
  hashed subset).
- **Instances per strip (setup reports, `ground_detail.scatter`):**
  - L_MudVariants 130,784 over 58,568 m^2 open: clods 35,282 (Clod0-5 10,637 / 11,984 / 6,156 / 3,680 / 2,092 / 733), pebbles 88,102
    (49,861 / 25,934 / 9,643 / 2,664), litter 1,378 (363 / 332 / 325 / 358) over 5,097 m^2, twigs 2,997 (1,014 / 970 / 1,013), mounds
    3,025 under 3,824 tussocks (4 / 722 / 2,299).
  - L_MudDrive 69,497 over 31,385 m^2: clods 18,641 (5,532 / 6,402 / 3,297 / 1,911 / 1,125 / 374), pebbles 46,552 (26,452 / 13,711 /
    5,018 / 1,371), litter 857 (216 / 206 / 228 / 207), twigs 1,555 (526 / 488 / 541), mounds 1,892 under 2,288 (4 / 453 / 1,435).
  - L_GravelDeform 71,284 over 32,971 m^2: clods 19,711 (5,863 / 6,746 / 3,471 / 2,030 / 1,204 / 397), pebbles 49,257 (28,017 /
    14,480 / 5,320 / 1,440), litter 397 (107 / 86 / 109 / 95), twigs 1,639 (550 / 513 / 576), mounds 280 under 320 (9 / 96 / 175).
  - Achieved per open m^2: clods 0.60, pebbles 1.49-1.50, twigs 0.050-0.051, litter 0.26-0.27; no trace missed the landscape.
- **Item 7, puddles as basins (AGTMudPatch step 3b):** each puddle run is one cosine basin inside the track: an ellipse on the run's
  lowest step, along the line over the run (+ half the 1.5 m ramp each end), across the track's half width; a quarter cosine from a flat
  floor to the wall limit `PreChurnPuddleWallMaxDeg` 30 at the edge, the field taken down to it where higher (min: the basin never adds
  to the track's walls); the floor the run's 2-5 cm under the table, raised until the basin reaches the ground round its edge (no step);
  lumps cleared under it. *Fact against the plan:* a 30 deg wall inside the track's half width reaches only 0.37 of that width (13-22
  cm), and Standard's table lies 25 cm under the base: inside the footprint alone the basins held water in Deep only (Firm 0, Standard
  0, Deep 11, Stony 0 water cells; the PreChurn test's water gate failed for Standard), and without the edge rule (a first build) the
  basins' own walls were 26-28 deg but their edges stepped up to 51.7 deg. So the wall goes on at 30 deg over a skirt of half the
  track's half width more (`PreChurnPuddleSkirt` 0.5; the basin reaches up to 1.5x the half width where the floor must go deep), then
  the floor rises (a dry dip) if still short. Result per patch (basins, with a floor under the table; water cells, GR1c's in brackets;
  the steepest basin cell, edges included; the steepest old-track cell, GR1c 41.6-43.5): Firm 9, 8; 123 (198); 30.0; 28.8 deg.
  Standard 11, 6; 41 (237); 30.0; 29.0. Deep 11, 11; 227 (287); 29.7; 28.6. Stony 7, 5; 80 (188); 29.9; 28.8. New strip CRCs Firm
  5687584a, Standard de3e99d8, Deep 2b85214e, Stony 5c567e0a; the fixtures' 8e0aad06 unchanged. GrandTour.Mud.PreChurn gains the basin
  rows (basins over 0, their walls at most 30 deg). `AGTMudPatch::NearestPuddleCm` (new) finds the nearest water cell.
- **Item 7, the spray check:** its two Deep spins (Spray_Mud_Spin, _Greybox, _Close) put a rear wheel on the puddle cell (2 cm of water
  or more) nearest the old spot's rear wheels: the cells lay 2.7-5.4 m from the old spot, 2.5-4.1 cm of water under the wheel (report `puddle_spin`). The muddy-splash count at the three captures 0 / 0 / 0, the CPU Water spray's live count 0 / 22 / 0: still FAIL with water under the wheel. The splash counts Water particles with a mud share (GTSprayArt.cpp PushWaterMud), and the build carries the Codex app's uncommitted GTSprayComponent.cpp, whose water emitters follow the local relative water speed (a spin in place has little). Not changed here (GTSprayArt.cpp is MW1's).
- **Item 4, tests and checks:** GrandTour.Mud (12), Snow (4), Gravel (1), Spray (2) and Relief (2, with the new Relief.Scatter: open
  ground only, determinism, the densities within 20-30 %, litter within 1.5 m of a tussock, mounds, the cluster multiplier's spread
  and the count CV 0.54-0.55 against a Poisson's 0.27-0.28) - 21/21 PASS, the fixtures' CRC 8e0aad06. Drive checks (no game was open at any run):
  L_MudVariants completed (200 m in 94.2 game s; before 102.6): Firm 29.8 km/h (29.7), Standard 27.6 (28.1), Deep 1.7 (1.7), Stony 16.3
  (9.4); its MRP sampler: every row PASS but PBR_Deep_Ground's soil range, base luminance 0.0323 against the 0.0325 floor (before
  exactly 0.0325). L_MudDrive: all four runs reach 119.0 m, 59.9 / 59.8 / 62.1 / 58.6 game s (before 57.1 / 59.6 / 60.9 / 55.1).
  L_GravelDeform: all ten checks true; its passes 27.43 / 27.37 / 11.32 game s (before 27.43 / 27.38 / 11.32).
- **Item 5, pictures** (`Art/ground_detail_gr2.ps1 -Step pictures` -> relief_pictures.py with GT_RELIEF_GR2=1; GR1c's cameras, the sun
  behind): Art/Export/MudVariants/ and Art/Export/LiveMudDrive/: Relief_Overview.png, Relief_OnFoot.png, Relief_Bog.png, Ground_Close.png, Ground_Close_Detail0.png, Ground_Far.png; Art/Export/DeformableGravel/: Relief_Overview.png, Relief_OnFoot.png, Ground_Close.png, Ground_Close_Detail0.png, Ground_Far.png (copies in each strip's GR2/; GR1c's in GR1c/). Ground_Close aims at the first spot 10-18 m off the line with no tussock within 1.5 m and two or more within 4 m (MudVariants (115, 10) m, gravel (46, 10), LiveMudDrive (40, 10)); Ground_Far from 24 m off the line aimed 50 m on. Art/Export/GroundRelief/pictures-gr2.json. Not described here.
- **Owner's list:** gt.Ground.Detail 0/1, gt.Ground.Scatter 0/1, gt.Ground.ScatterDensity 0-1; the densities (clods 0.6, pebbles 1.5,
  twigs 0.05, litter 0.25 per m^2 within 1.5 m of tussocks, a mound under each tussock of 25 cm or more; cluster 3 m x0.1-2.5, sharpen
  0.25); the POM range (full to 15 m, none past 25 m, 1.5 cm) and the detail's fade (25-40 m); the puddles' wall limit 30 deg and skirt
  0.5.
- **Pipeline:** `Art/ground_detail_gr2.ps1 -Step import|stats|pictures`; the three setups apply GR2 last (`ground_detail.apply_strip`;
  L_GravelDeform's strips the GroundDetail nodes first, as its gravel builders remake the nodes the switches read). Probe content left
  in /Game/GrandTour/ArtTests/GroundDetail/Probe/ (the stats' copies).

## 106. Mud and water MW1: crisp deformed mud, moving rut water, rings (2026-10-12)

The owner (2026-10-11, an on-foot screenshot along a water-filled old track): "mud and water are reading way too smooth - the water
is too static." Plan: docs/MUD_WATER_SURFACE_PLAN.md MW1. Built 2026-10-11/12 beside GR2 phase B (its section 0 split the files).
No timing or cost measured. GoWR was open for the after check and the tests (named, not closed).

**The check** (new): `& Art/check_mud_water.ps1 -Tag before|after [-Cameras <check-before.json>]` runs
Art/Unreal/check_mud_water.py on L_MudVariants (fixed 1/60 s step, verified over 300 frames; rendered only for the pictures),
then `python Art/sample_mud_water.py` (numbers in Art/Export/MudWater/mw-numbers-<tag>.json). The frame: Deep's old track,
its biggest puddle at 137.0 m, +0.26 m (2.3 cm of water over 0.75 m; Deep holds 169 cells over 1 cm at the start, Standard 18),
the eye 1.6 m over the mud 4.5 m behind it, looking along the track, the sun turned to 22 deg up and 30 deg off the view. Water
masks are the rut water's cells projected with the camera (a picture-difference mask caught the grass and the capture noise).

**Diagnosis (item 1)**: mean absolute difference (0-255, RGB) of each debug picture against the same frame, in the old track's mud
outside the water; then the same on a fresh Deep bank after the car's drive, water hidden:
| Debug | Owner frame | Fresh bank |
|---|---|---|
| the same frame again (the capture floor) | 0.49 | 0.53-0.71 |
| SlideUV 0 | 1.05 (1.9 % of pixels over 8) | 0.54 |
| FreshWet 0 | 1.10 | 0.58 |
| gt.Mud.POM 0 | 9.9 (41 %) | 9.6 (37 %) |
In the owner set a global shift of 10.85 came between the first two pictures and the rest, in both runs, toggles or not; those
rows are taken against the post-shift water-hidden picture. So in these frames the parallax is the term that changes the walls;
the slide and the sheen are at the capture floor. Item 2a's condition held: **SlideUV stays 1.0** (reported, not changed). The
roughness buffer on the track: p5/50/95 0.455 / 0.522 / 0.749 (dry), highlights (luminance over 0.8) 0.2 %. The field's 12.5 cm
bicubic geometry has no switch to isolate it. POM was not changed (not in the plan).

**Mud (M_GT_Mud, Art/Unreal/live_mud_style.py)**:
- 2b, the deformation detail (`gt.Mud.DeformDetail`, MPC_TrackPaint MudDeformDetail): the variant slice's normal and ORH AO at
  2.6x the tiling (1.15 m) turned 29 deg, from the un-slid surface point, tri-planar by the field normal's weights, laid in the
  field normal's tangent plane; strength 0.8 x max(the tracks or the Fresh history, smoothstep(12, 25 deg) of the field's slope);
  SampleGrad inside a branch (derivatives outside). MW1_MUD_SCALARS.
- 2c, FreshWet 0.3 -> 0.12.
- 2d, broken highlights: on wet mud outside the rut water, roughness +- 0.08 of two value-noise octaves (8 and 25 cm) by the wet
  share, and the wet floor 0.5 (from 0.4, reached at a wet share of 0.5).

**Water (M_GT_MudWater, `gt.Mud.WaterMotion`, MPC_TrackPaint MudWaterMotion; 0 is the MRP water exactly)**: the wind ruffle (25 and
11 cm octaves, slopes 0.12 / 0.08, crests across MPC_Weather's WindDirection with a slow wander, drifting 10 / 16 cm/s), gusts
(a 2.5 m noise moving 60 cm/s, x0.3-x1.6), calm under 2 cm (x0.4); settled roughness 0.2 up to 0.3 in the gusts (churned and froth
unchanged, F0 0.02); the mottle, the froth and a fleck layer (2-6 mm dark or light specks, 3-20 % of 3 cm cells by turbidity,
faded 2.5-6 m and under a pixel) drift 3-6 cm/s down the field's slope over +-60 cm (the patch's long axis where flat), two
phases 6 s apart cross-faded. MW1_WATER_SCALARS. The material's second collection is MPC_Weather (the limit is two).

**Rings (`gt.Mud.WaterRings`)**: UGTMudWaterSubsystem (new, Source/GrandTour/Terrain/GTMudWaterSubsystem.*) feeds
NS_GT_WaterRings (UGTNiagaraSetupLibrary::BuildWaterRings: one CPU emitter, every input guarded, SpawnRate from User.RingRate,
the template's shape, velocity, gravity, drag and colour modules off, Particles.SpriteFacing (0,0,1) from a SetParameters module,
CustomFacingVector, 10 cm growing to 1.2 m over 1.2-2 s) with M_GT_WaterRing (translucent, lit per pixel, 2 x 2 painted atlas
cell by Particle Random, opacity 0.9 x the fade in/out, 4 cm depth fade) and T_GT_WaterRings (Art/Blender/build_water_rings.py,
headless: dabs along wobbling circles, broken, two with a second ring). Wheels: every car's in-contact wheels in rut water over
1 cm, 1-6 rings/s by its ground speed (30 cm/s to 7 m/s). Footsteps: the character has no step event (its head bob is camera
only), so a 0.45 s cadence while moving on the ground in rut water over 1 cm, the first at once, 12 cm either side in turn. The
subsystem reads the wheels from the traction component, so GTSprayArt.cpp (it carries the Codex app's uncommitted hunks) is
untouched. 3e: the weather has no rain ripples on other surfaces (the rain emitter draws splash cylinders), so none were added.
Setup: `& Art/setup_mud_water.ps1` (the atlas, M_GT_Mud, M_GT_MudWater, MPC_TrackPaint's two scalars, the ring material and system;
not the landscapes, clods or strips).

**Gates**:
- Motion (the puddle, a fixed camera 1.8 m over it, frames 30 fixed steps apart): gt.Mud.WaterMotion 1 mean |dL| 2.29 / 2.26 of
  255, 18.4 % / 19.6 % of the water over 4/255 - **pass**; 0: 0.36, 0 %. On the car's fresh churned pool (MW_Water2): 0.92 / 1.06,
  1.7 % / 3.0 % - **fail** (0: 0.28): churned water is opaque slurry at roughness 0.5.
- Glare (owner frame, water pixels over 0.95): 0 % before (MW_Before_OnFoot; and gt.Mud.WaterMotion 0 in the after run, the water's
  mean luminance 0.261) and 0 % after (0.277). The owner's white blow-out did not reproduce at this frame.
- Mud PBR (the fresh Deep bank at test wetness 1, outside the water; EXR dumps, the encoding linear on the gravel, 0.898): roughness
  p5 0.451 before -> **0.498** after (the 0.5 floor is stored as 127/255: one 8-bit step under the 0.5 asked; the carry gate's
  precedent); dry p5 0.455 unchanged. Base colour luminance dry 0.0318 / wet 0.0220, as before (0.0319 / 0.0220): Deep's slice sits
  under the sampler's 0.0325 band floor at this frame before and after.
- Regression: 22 GrandTour.Mud, Snow, Gravel, Spray and Relief tests Success (the new GrandTour.Mud.WaterRings among them; GoWR
  open); the field CRC 8e0aad06 and the strip CRCs 5687584a / de3e99d8 / 2b85214e / 5c567e0a, as e68eb79.
- Static shader numbers (no timing): M_GT_Mud 999 -> 1129 pixel instructions (samplers 7, texture samples 3, unchanged);
  M_GT_MudWater 2602 -> 3486 (8, 3); M_GT_WaterRing 1842 (7, 1).
- Rings: the drive left 40 wheel rings (MW_Rings is at 1.7 km/h: Deep bogs the car - 13.2 km/h at most on the 20 m run-up - and no
  ring was alive at that frame); the walk 3 footstep rings in 1.3 s in water; MW_Rings_Test (three test rings on the settled
  puddle, then gt.Mud.WaterRings 0, the same frame): 4,067 water pixels changed by over 8/255 (214 outside the water).
- Detail (the mean absolute Laplacian of the luminance, 0-255): the owner frame's track 6.55 before -> 7.26 after
  (gt.Mud.DeformDetail 0: 6.16); the fresh bank 4.29 -> 7.55 (0: 4.54).

**Pictures** (Art/Export/MudWater/; the owner looks): MW_Before_OnFoot, MW_After_OnFoot; the debug set MW_Before_Dbg_* and MW_Dbg_*
(Repeat, SlideUV0, FreshWet0, POM0, AllOff, NoWater, after also DeformDetail0 and WaterMotion0; Buffers with _Roughness_view and
_WorldNormal_view); MW_Water_t0 / _t05 / _t10, MW_Water_Motion0_t0 / _t05, MW_Water2_* (the fresh pool); MW_Rings, MW_Rings_Foot,
MW_Rings_Test / _Off; MW_Mud_Close (+ _NoWater, _Wet), MW_Dbg_Close_* and the before ones; MW_PBR_Close_Dry / _Wet views.

Open: the owner's look and numbers; a 10 km/h rings frame needs puddles on firmer ground; the fresh-pool motion.

## 107. Mud and water MW1b: no parallax on deformed mud, matte toward the sun, Deep softened, no water swirls (2026-10-12)

The main session's look at MW1 (106): the owner frame nearly unchanged - the walls still smeared, the right half of the mud
glaring white, Deep's crater-like ring blisters, fingerprint-like swirls in the churned pool. Seven items, sent as messages (no
plan section; the Done note is in docs/MUD_WATER_SURFACE_PLAN.md). GoWR was open for the capture runs (named, not closed). No
timing. Tests: one run of the 22 GrandTour.Mud/Snow/Gravel/Spray/Relief tests before the owner's "dont worry about test runs"
(all Success, field CRC 8e0aad06, strip CRCs as e68eb79); none after (owner).

**Mud (M_GT_Mud, Art/Unreal/live_mud_style.py MW1_MUD_SCALARS)**:
1. No parallax on deformed mud: the parallax's fade (its depth, its steps and the branch that skips it) x (1 - the moved-mud mask)
   x (1 - smoothstep(PomFlatLo 10, PomFlatHi 22 deg, the field's slope)); a copy of POM_HLSL (POM_MUD_HLSL), the shared one is
   unchanged. The deformation detail (106) carries the walls.
2. Matte toward a low sun: the ORH band remapped dry to MudDryRoughLo..Hi 0.8-0.95 and wet to MudWetBandLo..Hi 0.62-0.8, every
   variant; the floor WetRoughFloor 0.62; specular occlusion from the baked AO (Specular 0.5 x lerp(1, AO^2, MudSpecOcclusion 1),
   a new Spec output on the Specular pin).
3. Deep softened: its normal x DeepNormalScale 0.5, its AO's strength x DeepAOScale 0.5 (the height-made shading), its parallax
   x DeepPomScale 0.5.

**Rut water (M_GT_MudWater; no river water touched)**:
4. The swirl cause, from a layer-by-layer run on the churned pool (check_mud_water.ps1 -Tag diag; each layer off against the
   picture right before it, the frame's middle, 0-255): the wind ruffle 14.5 (it drew long diagonal bands: its crests were stretched
   x1.8 across the wind), the drift 7.4 (the curved arc marks: the drift's direction came per pixel from the field's slope, so the
   moving offsets warped the froth's bubbles and the mottle into arcs; with the drift off the arcs went and the detail rose 5.7 ->
   7.8), the froth 5.5, the mottle 4.4, the flecks 3.7, the MRP ripple 4.2. Fixed: the drift is one direction per patch (its long
   axis, 4.5 cm/s, two phases cross-faded: a pure translation; DriftGradCm no longer read) and the ruffle isotropic. The mottle
   stays the bake's blotches.
5. Churned water ripples too: ChurnRippleSlope 0.15 x turbidity (the finer octave weighted), with the froth's drift.

**Rings frame (6)**: the Standard / Firm search found Firm's puddle at 37.6 m, +0.64 m (2.0 cm); the car crosses it at about
10 km/h and the shot waits for a live ring.

**The check** (Art/Unreal/check_mud_water.py): the owner set now waits for game time 15 s; the walls are the field's cells over
22 deg projected with the camera; the mud's own pixels come from a MudDiagnostic picture; the rings drive runs on Firm before
Deep's churning drive. Found: a scalar set on the patches' mud instances from Python never came back on its restore (every later
picture stayed shifted, 3.5-10.6 of 255), which made 106's SlideUV and FreshWet rows on the owner frame unreliable (the earlier
"shift"); those toggles now run last, after every measured picture. POM 0, DeformDetail 0 and WaterMotion 0 are console switches
and were never affected.

**Gates** ("MW1" = the committed 106 look, the same frames; MW1b after):
| Gate | MW1 | MW1b |
|---|---|---|
| walls, POM on against off (mean, 0-255; <= 3) | 11.18 | **0.69** (flat mud 8.75 -> 1.89) |
| mud pixels over 0.9 luminance (<= 3 %) | 10.3 % (right half 20.7 %) | **0.0 %** (over 0.8: 18.5 % -> 0.01 %) |
| wet mud roughness p5 / 50 / 95 (close bank) | 0.498 / 0.498 / 0.596 | 0.639 / 0.671 / 0.749 |
| dry mud roughness p5 / 50 / 95 | 0.455 / 0.529 / 0.765 | 0.800 / 0.820 / 0.886 |
| base colour luminance dry / wet | 0.0318 / 0.0220 | 0.0316 / 0.0219 |
| motion, old-track puddle (>= 2, >= 15 %) | 0.83-3.20, 0.1-29 % by the gust's phase | **2.07 / 2.39, 19.0 / 21.7 %** (WaterMotion 0: 0.28) |
| motion, the car's fresh pool (>= 2, >= 15 %) | 0.92-1.63, 1.2-8.4 % | **0.65 / 0.82, 0.9 / 1.8 % - fail** |
| water glare over 0.95 | 0 % | 0 % |
| rings frame | Deep, 1.7 km/h, none alive | **Firm, 7.1 km/h, 1 alive** (7 wheel rings in the pass) |
The owner frame's detail measure (mean absolute Laplacian, 0-255) 7.39 -> 3.45; DeformDetail 0 takes it to 2.75. Static shader
numbers: M_GT_Mud 1129 -> 1146 pixel instructions, M_GT_MudWater 3486 -> 3467 (samplers unchanged).

**Not met / open**: the fresh-pool motion gate (its camera looks almost straight down at a deep pool that has settled by then, the
sky's reflection there is nearly uniform; turbidity at that moment was not recorded); in MW_After_OnFoot the ring blisters on Deep
are still visible, fainter - a Deep rebake is the owner's call; a small bright patch shows on the right rut's puddle in
MW_After_OnFoot (not in MW1_OnFoot).

**Pictures** (Art/Export/MudWater/): MW1_OnFoot and MW_After_OnFoot (the owner frame, MW1 and MW1b); MW_Dbg_PomRef / MW_Dbg_POM0
(the walls gate) and MW1_Dbg_PomRef / MW1_Dbg_POM0; MW_Dbg_MudMask, MW_After_OnFoot_mudmask.png, MW_After_OnFoot_walls.png;
MW_Water_t0 / _t05 / _t10 and MW_Water_Motion0_t0 / _t05 (the puddle), MW_Water2_* (the fresh pool); MW_Rings (Firm),
MW_Rings_Deep, MW_Rings_Test / _Off; MW_Mud_Close (+ _NoWater, _Wet), MW_PBR_Close_Dry / _Wet views; the swirl run MW1b_Pool_Ref0-6
and MW1b_Pool_Mottle0 / Ruffle0 / Froth0 / Flecks0 / Drift0 / Ripple0.

## 108. Benmore integration B1: ground detail, soil scatter as landscape grass, surface types (2026-10-12)

docs/BENMORE_INTEGRATION_PLAN.md B1 on `/Game/GrandTour/Demo/BenmoreRoads/Gaea/L_Benmore_GaeaReview`. Every Unreal or UBT run started after
`Art/wait_unreal_free.ps1` printed UNREAL FREE in its own command (the MW1 agent's checks held it for long stretches); God of War
Ragnarok (GoWR) was open at every run and was left alone. No timing or cost measurement: instruction, sampler and instance counts only.
The river water is untouched (rivers, creek, lake, their materials and meshes, M_GT_Water, GTWaterField/Sheet); the detail and the
scatter stay off the creek and river beds, the banks and the lake.

- **Item 1, the inventory (`Art/benmore_b1.ps1 -Step inspect`, `Art/Export/BenmoreB1/inventory.json`):**
  - The landscape (2017², 124.0079 cm, Z 200, 256 components) wears `Gaea/ShoreRefinement/M_GC_Terrain`, a plain material (no
    instance chain) at the end of a clone chain: L_Benmore_Drive's M_Benmore_FullCover -> Gaea/M_Gaea_Terrain
    (benmore_gaea_materials.ground) -> RiverLife/M_RL_Terrain -> RiverScale/M_RS_Terrain -> ChannelPilot/M_CP_Terrain ->
    GaeaCreek/M_GC_Terrain -> ShoreRefinement/M_GC_Terrain (install_benmore_shore.copy_material). Masked (the RiverLifeHole patch
    cut), tangent-space normal, 101 nodes, no layer blends: every region comes from textures (T_Benmore_RoadMask R running surface /
    G shoulder band / B branch, T_Benmore_RoadCoordinates lateral and half width, T_RL_Ecology banks, T_RL_Vegetation grass
    densities, T_Benmore_CompositionZones rock and shelter, T_GC_ExtendedBedZones the bed, T_Benmore_Landform/HillStructure).
  - **Paint layers:** Tarmac, Dirt, Mud, Snow, Scrub, Bog (BenmoreFullSite layer infos; Dirt and Scrub re-pointed to
    PM_Benmore_FirmGround by fix_benmore_firm_ground). Blend method NONE on all six. On a 16 x 16 grid Scrub weighs 1.0 at all 256
    samples, the rest 0. The material samples none of them. So B1's "layers" are the material's mask regions (below).
  - **Grass:** five painterly types (`BenmoreRoads/Painterly/LGT_Painterly_*`, one SM_TS_* variety each, all from T_RL_Vegetation:
    LowGrass R 350 / 10 m² cull 65-110 m; CrownTussock G 70, 180-320 m; ShaggyTussock G 55, 210-380 m; TallClumps B 35, 220-450 m;
    DistantTussock G 6, 650-950 m, min LOD 2), lock-XY scales, no dynamic shadow, contact shadow on, no distance-field lighting.
    Project grass.DensityScale 0.5, grass.CullDistanceScale 0.6.
  - **Roads:** no splines; `Art/Export/BenmoreRoads/road-manifest.json` holds the two centrelines (Terrace loop 1,260 points,
    6.4 m, closed; Hillside branch 596 points, 4.4 m; x_m, y_m, z_m, yaw) and the masks above. Road dressing: 5,704 aggregate and
    52,104 verge instances.
  - **Gaea masks:** T_Gaea_Flow, T_Gaea_Banks, T_Gaea_VegetationMask (integration), T_RL_Ecology / Vegetation / Flow / WaterMask,
    T_GC_ExtendedBedZones, T_SR_Shore. No slope texture (the material reads the normal), the lake by local z under 48 cm.
  - **Contradicts the plan:** there is a GTTerrainBuilder, `Benmore_RL_CrossingProfiles` (DA_GC_CrossingProfiles, 2 sections, the
    ford crossing profiles). The review cameras: Benmore_Gaea_Camera_Creek_Close, _Creek_Reach, _Long_Vista (and 9 others).
  - Today's counts: pixel 1,090, vertex 148, samplers 24, pixel texture samples 19; collections MPC_TrackPaint and
    MPC_Benmore_GravelPOM.
- **Item 2, `MF_GT_GroundDetail` (/Game/GrandTour/Terrain/GroundDetail):** GR2's GD_HLSL as a function (four swaps, asserted against
  the source: the weights in, the strips' grass map and apron out, the POM toggle). Inputs Base, ScrubW, GrassW, WorldPos, PomEnable
  (1), and optional Rough (0.85), Normal (0,0,1), AO (1); outputs Colour, Normal, Roughness, AO. Every number from
  `/Game/GrandTour/Terrain/MPC_GT_GroundDetail` (GR2's 20 GD scalars, 5 vectors, GroundDetail, ScatterScale, the cluster numbers,
  BenmoreGravelPOM; 27 scalars, 5 vectors). **The strips were not re-pointed:** a material may reference two parameter collections
  (ParameterCollection.h MaxNumParameterCollectionsPerMaterial = 2); the strips already reference MPC_Weather (in MF_Weather) and
  MPC_TrackPaint. A probe copy of M_VariantsLandscape with the function wired fails: "Material references too many
  MaterialParameterCollections! A material may only reference 2 different collections." The strips keep GR2's nodes.
- **Item 3, the review material (`Art/Unreal/benmore_gt_ground.py attach`, hooked into install_benmore_shore.copy_material):**
  - The function sits between the river-life pass (the CP_Source pass-throughs) and the ChannelPilot bed node.
  - Its weights come from the material's own masks: off the running surface (RoadMask R), the banks (Ecology R/G), the bed (bed zones
    alpha, smoothstep 0-0.25), the exposed rock (CompositionZones G + slope, the hill pass's own term) and the lake. The verge soil
    keeps it. GrassW = tussock ground (Vegetation G + B, smoothstep 0.2-0.5).
  - The gravel road layers are Codex's, unchanged.
  - The material had two collections, so Codex's gravel parallax switch moved from MPC_Benmore_GravelPOM.Enabled to
    MPC_GT_GroundDetail.BenmoreGravelPOM (profile_benmore_game.py's `gravel_pom` flag follows it).
  - Counts: pixel 1,090 -> 1,827, vertex 148 -> 148, samplers 24 -> 28, pixel texture samples 19 -> 44 (the POM loop's and the
    four detail samples counted once each); collections MPC_GT_GroundDetail + MPC_TrackPaint.
  - Switch `gt.Ground.Detail` (UGTTrackPaintSubsystem writes MPC_GT_GroundDetail GroundDetail as well as MPC_TrackPaint's).
- **Item 4, scatter as landscape grass (/Game/GrandTour/Terrain/GroundDetail):**
  - `LGT_GT_SoilScatter`: the 6 clods, 4 pebbles, 3 twigs; `LGT_GT_GrassLitter`: the 4 litter mats. One variety per mesh, GR2's
    per-m² densities split by size^-1.2 (most small), times the cluster's peak over its mean (2.5 / 1.3): clods 0.6, pebbles 1.5,
    twigs 0.05, litter 0.25 per m² on average where the weight is 1.
  - Weights (a second custom node that only the grass and physical-material outputs read): open ground as above, off the running
    surface and 0.6-1.4 m past its edge, off the bed (smoothstep 0-0.1), banks and lake; litter only on tussock ground; times GR2's
    3 m value-noise cluster sharpened by 0.25 (ScatterClusterCm, ScatterSharpen, ScatterMin, ScatterMax) and ScatterScale.
  - Align to surface, random yaw, uniform scale ranges (clods 0.8-1.25, pebbles 0.8-1.3, twigs 0.75-1.2, litter 0.8-1.2).
  - **No Z offset in FGrassVariety (5.8):** the pebbles and twigs are `SM_GD_*_LG` copies imported with GR2's 30 % sink in their
    pivot (min z = -0.3 of their height, checked); the clods and litter carry their own embed.
  - Culls as seen: clods 20-35 m, pebbles, twigs and litter 15-25 m (the assets carry them over grass.CullDistanceScale 0.6).
    Density scaling off (the project's grass.DensityScale 0.5 is the tussocks' setting; the scatter has its own).
  - Lighting: no distance-field lighting, the meshes' Support Ray Tracing off (out of the ray-tracing and hardware Lumen scenes);
    dynamic shadows only for clods. FGrassVariety has no ray-tracing or indirect-lighting flags.
  - Tussock bases skipped (grass types cannot sit them under the tussocks).
  - Switches `gt.Ground.Scatter` and `gt.Ground.ScatterDensity`. **Contradicts the plan (an MPC scale on the grass weight):** the
    landscape's grass weight render does not see a changed collection value. With ScatterScale 0 written to the editor world and
    the grass maps flushed (also 4 s after the write), every scatter build came out the same: 6,432 / 5,127 / 10,752 instances at the
    three on-foot spots, on and off. So UGTTrackPaintSubsystem scales the two grass types' variety densities (authored x the scale,
    restored on Deinitialize) and runs grass.FlushCachePIE (instances only, the maps stay); this works in cooked builds too.
    ScatterScale stays in the weight at its default 1.
- **Item 5, surface types:**
  - `UGTSurfacePhysMaterial` gains bGravelSpray (false) and SprayTintA, SprayTintB, DustTint (zero = the code's defaults). B1b reads
    them.
  - No paint layers to carry them, so the material has a **Landscape Physical Material Output**. The landscape renders it per
    collision sample and the wheels' heightfield carries it; the map was saved after the rebuild.
  - The Benmore surfaces (Gaea/Surfaces, copies of PM_Benmore_FirmGround, Surface.Dirt):
    - running surface, wheel paths (Codex's loose share under 0.5) -> PM_Benmore_GravelFirm: Dirt's numbers (no gravel row), no
      unprofiled sinkage, gravel spray, tints A (0.180, 0.177, 0.166), B (0.215, 0.211, 0.198), dust (0.200, 0.196, 0.184);
    - running surface, crown and edges (loose share over 0.5) -> PM_Benmore_GravelLoose: the same numbers, tints A (0.073, 0.072,
      0.069), B (0.330, 0.325, 0.310), dust (0.218, 0.215, 0.205);
    - bed, silt banks, lake -> PM_Benmore_WetGround: wet Dirt (friction 0.62 x 0.8 = 0.496, rolling 0.03 x 1.6 = 0.048, no
      unprofiled sinkage, MaxSinkage 0.05 kept for the crossing profiles);
    - verge, grass, scrub, rock -> PM_Benmore_FirmGround (today's).
    The tints are the review material's packed and aggregate grading over gravel_floor_04 / _02, their 15-35 % and 65-85 %
    luminance bands and mean.
  - Traces (`UGTSurfaceQueryLibrary::TraceLandscapeSurface`: the Kismet traces return no physical material): Terrace loop
    centre GravelFirm 124 / GravelLoose 86 of 210, edge - 0.3 m Loose 92 / Firm 49 / FirmGround 69, verge + 1.5 m FirmGround 205 of
    210, + 8 m FirmGround 209; Hillside branch centre Firm 54 / Loose 46 of 100, verge FirmGround 98; a 64 x 64 site grid FirmGround
    4,027, WetGround 56, GravelLoose 8, GravelFirm 5.
- **Item 6, checks (`Art/benmore_b1.ps1 -Step check`, check.json):**
  - Scatter instances near the camera (the engine's own grass build log, LogGrass Verbose, the last build per component,
    subsection and mesh after a flush at the camera):
    - on foot at CreekClose 6,432 (clods 2,666, pebbles 3,137, twigs 121, litter 508; the painterly grass 291,818);
    - CreekReach 5,127 (1,275 / 3,158 / 139 / 555; 271,157);
    - LongVista 10,752 (2,604 / 6,712 / 265 / 1,171; 243,958);
    - the verge views 11,176 / 23,215 / 11,460;
    - the off pictures (the grass types' densities at 0, as gt.Ground.Scatter 0 sets them): 0 scatter at all three, the painterly
      grass unchanged (291,818 / 271,157 / 243,958).
  - Tests: the owner waived test runs during the stage ("dont worry about test runs"). Before that message the automation tests
    had run once: GrandTour.Mud, Snow, Gravel, Spray and Relief 22 / 22 Success, fixtures 8e0aad06, strips 5687584a / de3e99d8 /
    2b85214e / 5c567e0a (unchanged); biome PASS (The Hide 0x977AF3A498E07815, L_Proving 0x7DBDFB11F2FD2CE1 unchanged). They were not
    rerun after the last C++ change (the scatter switch on the grass densities).
- **Pictures** (Art/Export/BenmoreB1, sun behind every camera, open ground found by traces near each review camera):
  BI_OnFoot_<loc>.png and BI_OnFoot_<loc>_Off.png (gt.Ground.Detail 0, scatter 0), BI_Verge_<loc>.png, BI_Far_<loc>.png for
  CreekClose, CreekReach, LongVista.
- **Owner's list:** gt.Ground.Detail, gt.Ground.Scatter, gt.Ground.ScatterDensity; the densities and culls above; the POM range (GR2's
  15-25 m, faded out 25-40 m); MPC_GT_GroundDetail BenmoreGravelPOM (Codex's gravel parallax).

## 109. Mud roads MRD1 and MRD1b: braided old tracks, pools along the runs, silt surface, opaque rut water (2026-10-12)

docs/MUD_ROADS_PLAN.md, from the owner's five reference pictures (Art/Reference/MudRoads, local only). Tests not run (owner); GoWR
open during MRD1b's runs (named, never closed); no timing.
- **The profile** (FGTDeformProfile, read whatever the Mode): PreChurnStyle Braided, RoadDebrisPerM2 0.05, RoadSiltTileMul 2,
  RoadSiltStrength 0.4, MudRoadSprayScale 2 (the number only; Benmore B1b's spray reads it). Art/Unreal/mud_roads.py road_deform();
  the MudRoad sections stand at a -10 cm water table (the bog's -25 cm lay under every road track).
- **AGTMudPatch::PreChurnBraided** (after the hummocks, x0.4 on a road): 6-14 tracks across the road (7 on the strips' 6 m), each a
  cosine trough 1.2-2.0 x its tyre wide on two sines (15-35 m and 30-60 m, swing 0.4-1.5 m), its stretch (50-90 % of the road) placed
  in a shuffled even slot; power-law depths 2-25 cm (a 0.4); the layout redrawn until every 20 m window has 2 crossings and a 4 deg
  heading sd. Banks of 0.7 of the cut, lumps at 0.5 heavier on the ridges, 10 s of the field's settle; deep tracks' walls stepped
  4-7 cm and their lips broken into one-cell blocks (30 % of lip segments leaning in); churn zones (1-3 per 40 m at crossings or deep
  spots) with clod fields (2-6 a m^2 over 2-4 m, clod Source 6: old, dry, no wet sinking) and 2-4 MR5 chunks; pools along the tracks
  (runs of 2-8 m, 3 m apart, 1-4 cm under the table, stray water lifted to it) until 8-15 % of the road; the partial old tread on the
  2-3 freshest tracks (TreadTex G 2 + phase, R heading + strength in eighths; M_GT_Mud, gt.Mud.OldTread, MPC MudOldTread).
  DescribeMudRoad() returns the gates.
- **Debris:** GR2's twigs and SM_MRD_Branch0-1 (Art/Blender/build_road_branches.py, the twig recipe, 60 / 105 cm), flat, pitched to the
  ground, sunk 25-60 %, clustered; pressed down with the ground under a wheel.
- **M_GT_Mud:** 12 field taps give the wet/dry term (x0.72 and roughness 0.5-0.6 near water and in troughs, x1.08 and 0.85-0.95 on
  crowns), the deep walls' AO (x1.0 past 15 cm after MRD1b) and the silt mask (the bake 2x finer, lump normal, AO and parallax x0.4
  on the running surface); deformation detail 1.0. **M_GT_MudWater:** settled roughness 0.06-0.1; MRD1b's opaque turbid body (the
  variant's bog mean, saturated, 0.85-0.95 from 1 cm, faded over the outer 1 cm).
- **Numbers (MRD1b, L_MudVariants / L_MudDrive):** puddles 13.5 / 14.3 % (pass), pools in 5 m of a track at most 3 / 4 (fail: the
  count includes the other tracks' pools a line crosses), crossings 2.0 / 2.0 in the fewest window, heading sd 6.0 / 5.7 deg, width
  1.21-2.00 x tyre; puddle look in MRD_Ref4 fails (water 0.216 under wet mud 0.252, R > G > B passes); water motion 0.88 / 0.78 (fail);
  mud glare 0.01 %.
- **Capture:** Art/check_mud_water.ps1 -Tag mrd (GT_MRD_CAMERAS, GT_MRD_CHASE), Art/sample_mud_roads.py -> Art/Export/MudRoads.
