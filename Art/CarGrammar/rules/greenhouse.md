# Greenhouse (GH)

Values are metres or degrees unless marked. Src: R real-car data, S approved sheet, P design
practice, O owner. Conf: M measured, D derived, A assumed. Transcribed from
`docs/CAR_GRAMMAR_PLAN.md` section 3.

| ID | Rule | Boxy SUV | Sedan | Src | Conf |
|---|---|---|---|---|---|
| GH-01 | The windscreen is one sheet with a plan bow sag across its width that varies linearly from the glass base to the roof round tangent (base, top); no curvature up the glass | base 0.060, top 0.030 | base 0.080, top 0.050 | P | A |
| GH-02 | Windscreen rake from vertical | RAKE_WS 32 (28 to 38) | 60 to 65 | P | A, measure on sheet |
| GH-03 | A-pillars are straight in side view at the windscreen rake; width seen from the side | 0.090 | 0.080 | P | A |
| GH-04 | The roof is flat with a crown: sag across W_ROOF and along its length | 0.020 across, 0.015 along | 0.035, 0.030 | P | A |
| GH-05 | Roof rail round radius (roof to side glass plane) | 0.035 | 0.080 | P | A |
| GH-06 | Roof front edge round (roof to windscreen) and rear edge round | 0.040, 0.040 | 0.120, 0.100 | P | A |
| GH-07 | Side glass is flat, leaning in by TUMBLEHOME | 6 (4 to 9) | 20 to 25 | P | A, measure |
| GH-08 | Rear screen is flat, raked RAKE_RS; on a tailgate its base sits at the tailgate top | 8 (3 to 15) | 55 to 62 | P | A |
| GH-09 | B, C, D pillars are vertical in side view; widths at the belt | 0.090, 0.110, 0.150 | B 0.100 | P | A, measure |
| GH-10 | The belt is a straight horizontal line from the A-pillar base to the tail | H_BELT | rises 0.03 to the rear | S | measure |
| GH-11 | Side glass top edge = roof rail round bottom minus a header; glass corner radius | header 0.040, r 0.040 | 0.050, 0.060 | P | A |
| GH-12 | Front door glass has a fixed quarter light ahead of the drop glass only if the A-pillar base is ahead of the door line by more than this | 0.120 | 0.120 | P | A |
| GH-13 | Greenhouse plan corner radius at the A-pillars (windscreen edge to side glass) | 0.080 |  | P | A |
| GH-14 | Greenhouse plan corner radius at the rear (side glass to rear screen) | 0.120 |  | P | A |
