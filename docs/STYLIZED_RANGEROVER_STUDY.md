# Range Rover Classic — stylized Blender study

September 30, 2026. After accepting the new wagon and Land Cruiser studies, the user requested a Range Rover in the same style. This is a separate four-door Classic interpretation. The user's existing hand-modelled `Art/rangerover.blend`, its backups, exports and Unreal assets remain unchanged.

## Files

- Model: `Art/Export/VehicleTools/stylized-rangerover-v02/Stylized_RangeRoverClassic.blend`.
- Source: `Art/VehicleTools/build_stylized_rangerover.py`; a source snapshot accompanies the model.
- Review images: `three-quarter.png`, `side.png`, `front.png`, `top.png`, `rear-quarter.png`, `arch-joint.png` in the model folder.
- Artistic dimensions and reference URL: `spec.json`.
- Limited geometry checks: `static-fit-report.json`.

The script creates an empty Blender scene and requires a new empty output directory. It never loads the existing Range Rover. Both accepted vehicle renders are packed into the blend as hidden style references.

## Shape decisions

Muted green body; nearly flat bonnet; low continuous waist; deep glazing and black pillars under a body-coloured roof; close faceted semicircular arches with narrow body-colour lips; round headlights; vertical grille; thin wraparound bumpers; three-spoke wheels; split tailgate. These distinguish the Classic from the taller ivory Land Cruiser while keeping the same broad surfaces and restrained detail.

Body length 4.27 m, width 1.84 m, roof height 1.79 m, axle spacing 2.63 m and tyre radius 0.38 m are artistic modelling choices, not verified factory specifications or replacements for existing game tuning.

Identity references: [JLR Classic design history](https://media.jlr.com/classic/en-gb/news/2010/06/range-rover-celebrates-its-40th-birthday) and [official Classic image pack](https://media.jlr.com/corporate/image-packs/classic-range-rover-0). Photography is reference only and is not used in materials.

## Scope and verification

Actual Blender Cycles renders provide front/side/top and both three-quarter views plus the arch/door/sill join. The first close-up exposed a seam where the lower side tuck crossed the arch lip; revision 02 removes the tuck for a continuous planar join. Static checks passed for finite mesh coordinates and tyre-shell triangle intersections against the body/arch meshes and sill trims. This check excludes containment, wheel steering, suspension travel and all other component pairs.

This is an exterior style study with simple cabin and underbody masses. It has no new rig, functional cockpit, UV preparation, collision, FBX export or Unreal integration. User approval of the new Range Rover's style is pending.
