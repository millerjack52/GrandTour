# Benmore environment refinement

Scope: the existing Benmore driving map and its owned assets. Preserve the approved TussockStyle vegetation, willow family, surveyed terrain reference, and other contributors' shared assets.

1. **Ground rocks.** Sample the actual underside and terrain over each large rock footprint; embed the base into slopes. Correct small aggregate placement against the triangulated landscape. Check support across footprints and retain road clearance.
2. **Separate banks from flats.** Blend dry taupe soil into exposed banks and layered grey rock on steeper faces. Break boundaries with world-space variation; keep straw vegetation on gentler terrain. Use projected rock detail to avoid stretching on cliffs.
3. **Distant hills.** Add broad slope/aspect variation, reduce small-scale contrast with distance, and introduce restrained blue-grey atmospheric separation. Keep close roads clear.
4. **Background.** Extend scenery using available LINZ DEM coverage with a matching inner boundary. Background meshes are scenery only. Record their geographic extent and any coverage limitations.
5. **Gravel and bumps.** Increase loose-gravel scale consistently across colour, normal and POM height. Add shallow, broad physical road undulations appropriate to the 1.24 m landscape grid; keep fine corrugation in shading. Re-seat dressing after terrain changes.

Validation: save a pre-pass map backup; verify shader compilation, height import, rock support, background seams, grass preservation, road collision, and vehicle driving cases. Capture close road, bank/rocks, and distant landscape views. Report measured results and any remaining limitations; unattended editor timing is not a performance benchmark.

All five passes are implemented. See [implementation and measured validation](BENMORE_ENVIRONMENT_REFINEMENT.md). The six driving cases passed; final imagery and machine-readable reports are in `Art/Export/BenmoreEnvironment`.
