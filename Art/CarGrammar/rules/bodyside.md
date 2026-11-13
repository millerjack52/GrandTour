# Bodyside (BS)

Values are metres or degrees unless marked. Src: R real-car data, S approved sheet, P design
practice, O owner. Conf: M measured, D derived, A assumed. Transcribed from
`docs/CAR_GRAMMAR_PLAN.md` section 3.

| ID | Rule | Boxy SUV | Sedan | Src | Conf |
|---|---|---|---|---|---|
| BS-01 | Below the belt the side is one near-flat plane leaning in above the waist; waist at the belt | lean 3 | 8 to 12 | P | A |
| BS-02 | Belt edge: the top of the lower body rounds into a ledge under the glass | r 0.015, ledge 0.030 | 0.025, 0.030 | P | A |
| BS-03 | Sill: the side tucks under over the bottom part of its height, at an angle | tuck 0.060 high at 30 | 0.080 at 35 | P | A |
| BS-04 | Shoulder crease line on the bodyside at a height above the sill, depth | none | at 0.55 H, 0.004 | P | A |
| BS-05 | Arch opening: circle about the hub, radius ARCH_R = TYRE_R + margin; squared style flattens the top over ARCH_TOP_FLAT | margin 0.080, flat 0.35 x dia | 0.070, round | P/S | A, measure |
| BS-06 | Flare: a lip around the arch, width out from the body and height, with a lower cladding strip along the sill of the same material | 0.070 out, 0.060 tall; cladding 0.120 tall | lip 0.015 | S | measure |
| BS-07 | Door bottoms sit above the sill line by | 0.040 | 0.040 | P | A |
