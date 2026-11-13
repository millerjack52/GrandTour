# Cockpit workshop

Current revision: `C:/GrandTour/Art/Export/VehicleTools/cockpit-workshop-v04/`.

Open `RangeRover_Cockpit_Workshop.blend` for the complete assembly or append collections from `Cockpit_Components.blend`. The original `Art/rangerover.blend` and previous exterior deliverables remain separate.

## Components

Twelve independent collections add the dashboard carrier, instrument cassette, steering and pedals, centre stack and tunnel, two front seats, rear bench, four door cards, and cabin floor/lining. The assembly retains the 34 earlier workshop collections.

The dashboard has real vent, glovebox and instrument openings. The instrument cassette has separate recessed faces, scale marks, numerals, needles, clear covers and a deep hood. Controls include a three-spoke wheel, column, stalks, three pedals, radio, ventilation controls, gear lever, transfer lever and handbrake.

Front seats use shaped cushion and backrest grids, contrasting fabric inserts, seams, separate headrests, recline wheels, buckles, fixed feet and sliding runners. The rear bench sits above hollow wheel tubs. Door cards include fitted backing, padded trim, pull handles, recessed releases, manual winders and front speaker grilles/open storage pockets. Lining includes fitted floor sections, mats, pillar trims, static belt representations, headliner, visors and a rear-view mirror.

The dark graphite and oatmeal interior is a proposed continuation of the stylized exterior. It is not a factory-correct reconstruction or a newly approved style reference.

## Editing and reuse

Install `GrandTour_Cockpit_Addon.zip`, or run the saved Blender text `START HERE - cockpit workshop.py`. In the **GT Parts** sidebar:

- Select a front-seat component and set **Front seat offset** between −35 and +35 mm. Upholstery and runners move together while the floor mounts stay fixed.
- Select the steering component and set **Steering radius** between 165 and 185 mm. The rim and spokes update together.
- Click **Rebuild selected cockpit part**. Other cockpit kinds can be rebuilt at their stored specification.

Manual geometry, transforms and relevant material changes trigger a refusal to rebuild. Keep those edits as a variant or deliberately migrate them into the builder. A staged build failure leaves the previous collection intact. Do not clear fingerprints to bypass protection.

The `rr-cabin-v1` interface uses metres and the existing assembly origin: +X left, +Y rear, +Z up. The original steering position at X = −0.410 m is retained. Parts are fitted to this body; independently appending one to a differently proportioned vehicle does not automatically fit it.

## Review and evidence

The revision contains matched before/after driver and exterior renders, dashboard/instrument/seat/door-card close-ups, front and side checks, an interior cutaway, top view and clay render. The cutaway hides the body, glazing and roof lining for inspection; exposed trim ends in that image are normally covered by the exterior.

Source files under `Art/VehicleTools/`:

- `cockpit_workshop.py`: component builders and optional sidebar.
- `build_cockpit_workshop.py`: loads the rear-body-v05 assembly, replaces interior placeholders, renders and packages a fresh revision.
- `test_cockpit_workshop.py`: 17 checks for selected closed meshes, finite geometry, nominal/limit seat clearance, non-overlapping floor faces, seated mounting feet, actual parameter-driven geometry, unchanged neighbours, invalid input, manual edit protection, rollback, registration and save/reopen persistence.
- `verify_cockpit_assembly.py`: reopens the delivery, verifies all 46 workshop fingerprints, checks cockpit meshes against the 34 protected exterior collections and retained body/roof/windscreen, and registers the packaged ZIP.

Reports are `fit-report.json`, `tests.json` and `assembly-reopen-check.json`. Check those files and Blender's log: a Python assertion may still produce process exit code zero. Surface-intersection tests do not detect every possible containment or movement problem.

## Limits and next work

This is a static modelling milestone. Gauges, pedals, belts, steering, windows and levers are not operational; the driver camera is an artistic review position rather than a validated human eye box. Door cards are independently grouped but are not yet parented to animated doors. UVs, LODs, simplified collision, suspension/steering sweeps and Unreal export remain unvalidated.

The next useful step is an assembly and articulation pass: component pivots, door/card relationships, steering and wheel movement, and a simple inspection rig. Validate moving clearances before adding more accessories.
