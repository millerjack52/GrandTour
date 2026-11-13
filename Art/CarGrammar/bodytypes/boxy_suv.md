# Body type: boxy SUV

The boxy SUV column of every rule in `rules/`, collected (Land Cruiser 80 style). `grammar.py` checks that
each value here equals the Boxy SUV cell of the same ID in the rules files; change both in one edit.

| ID | Subsystem | Rule | Boxy SUV | Src | Conf |
|---|---|---|---|---|---|
| GH-01 | Greenhouse | The windscreen is one sheet with a plan bow sag across its width that varies linearly from the glass base to the roof round tangent (base, top); no curvature up the glass | base 0.060, top 0.030 | P | A |
| GH-02 | Greenhouse | Windscreen rake from vertical | RAKE_WS 32 (28 to 38) | P | A, measure on sheet |
| GH-03 | Greenhouse | A-pillars are straight in side view at the windscreen rake; width seen from the side | 0.090 | P | A |
| GH-04 | Greenhouse | The roof is flat with a crown: sag across W_ROOF and along its length | 0.020 across, 0.015 along | P | A |
| GH-05 | Greenhouse | Roof rail round radius (roof to side glass plane) | 0.035 | P | A |
| GH-06 | Greenhouse | Roof front edge round (roof to windscreen) and rear edge round | 0.040, 0.040 | P | A |
| GH-07 | Greenhouse | Side glass is flat, leaning in by TUMBLEHOME | 6 (4 to 9) | P | A, measure |
| GH-08 | Greenhouse | Rear screen is flat, raked RAKE_RS; on a tailgate its base sits at the tailgate top | 8 (3 to 15) | P | A |
| GH-09 | Greenhouse | B, C, D pillars are vertical in side view; widths at the belt | 0.090, 0.110, 0.150 | P | A, measure |
| GH-10 | Greenhouse | The belt is a straight horizontal line from the A-pillar base to the tail | H_BELT | S | measure |
| GH-11 | Greenhouse | Side glass top edge = roof rail round bottom minus a header; glass corner radius | header 0.040, r 0.040 | P | A |
| GH-12 | Greenhouse | Front door glass has a fixed quarter light ahead of the drop glass only if the A-pillar base is ahead of the door line by more than this | 0.120 | P | A |
| GH-13 | Greenhouse | Greenhouse plan corner radius at the A-pillars (windscreen edge to side glass) | 0.080 | P | A |
| GH-14 | Greenhouse | Greenhouse plan corner radius at the rear (side glass to rear screen) | 0.120 | P | A |
| BS-01 | Bodyside | Below the belt the side is one near-flat plane leaning in above the waist; waist at the belt | lean 3 | P | A |
| BS-02 | Bodyside | Belt edge: the top of the lower body rounds into a ledge under the glass | r 0.015, ledge 0.030 | P | A |
| BS-03 | Bodyside | Sill: the side tucks under over the bottom part of its height, at an angle | tuck 0.060 high at 30 | P | A |
| BS-04 | Bodyside | Shoulder crease line on the bodyside at a height above the sill, depth | none | P | A |
| BS-05 | Bodyside | Arch opening: circle about the hub, radius ARCH_R = TYRE_R + margin; squared style flattens the top over ARCH_TOP_FLAT | margin 0.080, flat 0.35 x dia | P/S | A, measure |
| BS-06 | Bodyside | Flare: a lip around the arch, width out from the body and height, with a lower cladding strip along the sill of the same material | 0.070 out, 0.060 tall; cladding 0.120 tall | S | measure |
| BS-07 | Bodyside | Door bottoms sit above the sill line by | 0.040 | P | A |
| FR-01 | Front and rear | The front face is upright, leaning forward at the top by RAKE_FRONT; the grille and lamp panel is one plane | 5 (0 to 10) | P | A, measure |
| FR-02 | Front and rear | Bonnet: flat with a crown across; falls from the cowl to the leading edge | crown 0.025; fall 0.040 | P | A, measure |
| FR-03 | Front and rear | Bonnet leading edge round; front face vertical corner radius in plan | 0.035; 0.120 | P | A |
| FR-04 | Front and rear | Bumper bar: a box across the face at H_BUMPER, protruding, wrapping round the corner along the side | 0.180 tall, 0.100 out, wraps 0.250 | P | A, measure |
| FR-05 | Front and rear | Headlamps: rectangles on the lamp panel, outboard, centred at H_LAMP | 0.200 x 0.120 | S | measure |
| RR-01 | Front and rear | Tail face vertical to RAKE_REAR; tailgate spans the full width between the quarter panels | 3 (0 to 6) | P | A, measure |
| RR-02 | Front and rear | Roof rear edge round; tail vertical corner radius in plan | 0.040; 0.100 | P | A |
| RR-03 | Front and rear | Rear bumper as FR-04 | same | P | A |
| LAY-01 | Layout | Front door leading edge continues the A-pillar base line down to the sill, raked back slightly | 5 from vertical | P | A |
| LAY-02 | Layout | B-pillar centre as a fraction of the wheelbase behind the front axle | 0.48 | P | A, measure |
| LAY-03 | Layout | Rear door trailing edge is vertical, ahead of the rear arch by | 0.060 | P/S | measure |
| LAY-04 | Layout | Bonnet shut lines: along the fender top at a set distance inboard of the body side; rear edge at the cowl | 0.060 | P | A |
| LAY-05 | Layout | Panel gap; edge round; return depth | 0.006; 0.004; 0.015 | O | defaults |
| LAY-06 | Layout | Tailgate split: upper glass hatch and lower drop gate, split at | H_BELT | S | measure |
| LAY-07 | Layout | Door bottom edge above the sill line (BS-07); the rocker strip below belongs to the body | 0.040 | P | A |
| LAY-08 | Layout | Door window frames: the door carries its frame up to the header band; frame width round the glass | 0.035 | P | A |
| LAY-09 | Layout | Cowl strip between the bonnet rear edge and the windscreen base | 0.040 | P | A |
| LAY-10 | Layout | Front panel seam: a vertical seam at the end of the front plan corner arc (fender to grille panel); the rear quarter runs to the end of the rear corner arc | at the arc end | P | A |
| LAY-11 | Layout | Lower tailgate bottom edge above the rear bumper top | 0.010 | P | A |
| LAY-12 | Layout | Hinges: doors on a vertical axis at the leading edge; bonnet on a transverse axis at its rear edge; lower tailgate on a transverse axis at its bottom edge; upper hatch on a transverse axis at the roof rear round tangent | as rule | P | A |
