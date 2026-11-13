# Lamp and grille workshop

September 30, 2026. Second component-authoring milestone, following the wheel/fender workshop. The scope is the Range Rover study's front lamps, indicators, grille and fitted nose openings. Existing wheel/fender collections and the original user model are preserved.

## Files and controls

Source: `Art/VehicleTools/lamp_grille_workshop.py`. Build: `build_lamp_grille_workshop.py`. Tests: `test_lamp_grille_workshop.py`. These reuse the earlier wheel workshop's mesh construction, fingerprint and staged rebuild helpers.

Review: `Art/Export/VehicleTools/lamp-grille-workshop-v02/RangeRover_Lamp_Grille_Workshop.blend`. The neighbouring `Lamp_Grille_Components.blend` contains independently appendable lamp, indicator and grille collections. `GrandTour_Lamp_Grille_Addon.zip` contains both the lighting module and its helper dependency.

Install the ZIP through Blender's Install from Disk control and enable it, or run the review blend's `START HERE - lighting workshop.py` text to load the project module once. The latter uses the source at `C:/GrandTour/Art/VehicleTools`. Neither the file nor the source automatically changes preferences or executes at load.

The **GT Parts** sidebar has a lighting section. Select a lamp mesh and adjust **Lens crown** or **Glass flute pitch**, then rebuild the selected part. Select a grille mesh to choose four, five or six slats. Rebuilding refuses hand-edited geometry, transforms, modifiers or materials. Save manual variants rather than forcing a rebuild. **Check nose cassette fit** writes its findings into the Blender Text `Lights fit report`.

## Construction

Each headlamp has a closed rear shell, shaped reflector, rubber seat, rolled retaining bezel, lens gasket, bulb/socket geometry, retaining screws, rear mounting tabs and a closed curved glass lens. Vertical fluting is modelled into the lens surface. The review uses unlit lamps so geometry and materials can be judged without emission masking the shape.

The front carrier has real circular lamp apertures and a central grille opening. The grille has shaped slats, side returns, rear braces and recessed radiator fins. Indicator clusters use separate beds, fluted amber/clear lenses, a separator and fasteners. A vehicle-specific adapter creates matching openings in the old flat nose panel, allowing the housings to occupy real recesses.

Local X is outward along the lamp axis, local Y is lateral and local Z is up. Mounted components rotate into the vehicle's front -Y convention. The fixed lamp interface is `rr-lamp-286-v1` with a .143 m aperture radius and .119 m lens radius. Adjustable lens crown is .008–.023 m and flute pitch .009–.018 m. This first interface is tied to the Range Rover study; arbitrary openings are not silently resized.

## Review and evidence

The build saves matched before/after front and whole-car renders, a lamp closeup, a clay front, a straight front view and an exploded lamp view. Materials, camera and studio lights are held constant between comparison images. The rest of the vehicle is still the earlier body/cabin study.

Independent checks cover actual lens geometry propagation, grille variants, preservation of neighbouring components, a deliberate mounting error and collision, incompatible opening refusal, manual-edit refusal, a staged construction failure, sidebar registration and save/reopen. Reports are in `Art/Export/VehicleTools/lamp-grille-tests-v02/tests.json`. The build also compares all six earlier wheel/fender fingerprints with the source revision.

The first lens render was too cloudy and its fluting was poorly resolved. Revision 2 lowers glass roughness and samples the curved lens across the flute direction, giving the narrow ribs enough geometry without relying on dense radial rings. The small bonnet lettering is also repositioned within the remaining painted band above the carrier.

Fit reporting covers lamp mount positions, glass radial containment and lamp-to-carrier surface intersections. Tabs and fastening contacts are intentional. These are authoring assets; optical beam behaviour, weather sealing, movement, UV/LOD/export and game performance are not validated.

The final saved assembly was independently reopened. All five lighting and six earlier wheel/fender collection fingerprints matched, both lens shells had closed manifold topology, the checked lighting surfaces did not intersect the nose cap, and the packaged add-on registered successfully. Results are saved in `assembly-reopen-check.json` beside the model.
