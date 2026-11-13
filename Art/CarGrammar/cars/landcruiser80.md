# Land Cruiser 80 car sheet

Hard points of `schema/hardpoints.md` for the Land Cruiser 80, measured on the approved sheet
`Art/References/Vehicles/LandCruiser80_v01/01_exterior_proportions_v2.png` by `tools/measure_lc80_sheet.py` (G0, 2026-10-02). Car frame: metres,
front = -Y, Z up, origin mid-wheelbase on the ground; angles in degrees. Pixel coordinates are sheet pixels
(x right, y down; a boundary between rows k-1 and k is written k - 0.5). The sheet wins over the real car;
differences are in the Real car column. The drawing of every line is
`Art/Export/VehicleTools/landcruiser-grammar-g0-v01/hardpoints-drawing.png`.

## Registration

- Side view (authority): hub centres (429.38, 279.62) and (983.86, 279.98) px, rim circle fits rms 0.62 / 0.54 px; wheelbase 554.47 px = 2.850 m, so 194.552 px/m; ground (Z = 0) at y 349.79 px; mid-wheelbase (Y = 0) at x 706.62 px.
- Roof clipped in the side view: no (15.0 px of background above the roof outline).
- Front view 170.014 px/m (0.874 x side), rear view 170.594 px/m (0.877 x side), from their roof height against the side view's H_ROOF; both differ from the side view by more than 3 %, so heights come from the side view and the front and rear views are used at their own registered scale for widths only.
- Top view 191.87 px/m (0.986 x side) from the length; within 3 %. Widths in the top view are 17 % narrower than in the front view at the same scale (W/L = 0.312 against the front view's W/H x side H/L = 0.374): the top view is not used for widths.

## Hard points

| Name | Value | Unit | Source | Confidence | Real car | Evidence |
|---|---|---|---|---|---|---|
| WB | 2.850 | m | real-car data (registration) | measured | 2.850 verified (toyota-global vehicle lineage id60013935: 2850 mm); sheet - real +0.000 | hub centres x 429.38 / 983.86 px (rim circle fits, rms 0.62 / 0.54 px) -> 554.47 px = 2.850 m; side scale 194.552 px/m; hub rows differ by +0.36 px |
| TRACK_F | 1.595 | m | owner (real car) | assumed | 1.595 unverified (Fable's recollection); sheet 1.653 | owner decision at gate G0 (2026-10-02): heights and lengths from the sheet, widths from the real car; sheet front view measured 1.653 (tyre centres 281.0 px apart) |
| TRACK_R | 1.615 | m | owner (real car) | assumed | 1.615 unverified (Fable's recollection); sheet 1.545 | owner decision at gate G0 (2026-10-02): heights and lengths from the sheet, widths from the real car; sheet rear view measured 1.545 (263.5 px) |
| TYRE_R | 0.383 | m | owner (sheet value, hub at this height) | measured | 0.396 unverified (275/70R16, Fable's recollection); sheet - real -0.013 | owner decision at gate G0 (2026-10-02): heights and lengths from the sheet, widths from the real car; radius as measured on the sheet's tyre sides (rays 12-48 and 132-168 deg, 75.4 / 73.6 px); the hub sits at Z = TYRE_R (the sheet's tyre is drawn squashed, hub 0.360); arch centres move up with the hub |
| TYRE_W | 0.280 | m | owner (real car) | assumed | 0.275 unverified (275/70R16); sheet 0.359 | owner decision at gate G0 (2026-10-02): heights and lengths from the sheet, widths from the real car; G1 wheel width (plan 6e); sheet front view measured 0.359 incl. the sidewall bulge |
| OH_F | 0.791 | m | sheet pixels | measured | - | front bumper face x 275.5 px (left-most object pixel over rows 200-271, at row 215); front hub x 429.38 |
| OH_R | 1.206 | m | sheet pixels | measured | - | rear bumper face x 1218.5 px (right-most object pixel over rows 200-271, at row 239); rear hub x 983.86 |
| W_BODY | 1.830 | m | owner (real car) | derived | 1.830 verified (toyota-global id60013935: HZJ81V body without flares 1830 mm); sheet 1.812 | owner decision at gate G0 (2026-10-02): heights and lengths from the sheet, widths from the real car; sheet front view measured 1.812 (rows 792-808, x 304.5-612.5 px) |
| W_FLARE | 1.900 | m | owner (real car) | measured | 1.900 verified (toyota-global id60013935: width 1900 mm); sheet 2.029 | owner decision at gate G0 (2026-10-02): heights and lengths from the sheet, widths from the real car; sheet front view measured 2.029 (rows 818-858, x 285.5-630.5 px) |
| W_ROOF | 1.270 | m | owner (real-car width scale) | derived | - | owner decision at gate G0 (2026-10-02): heights and lengths from the sheet, widths from the real car: the front view's roof width 1.258 (213.9 px, sharp corners at the roof top row) scaled by W_BODY real / sheet = 1.830 / 1.812; half width 0.635 (plan 6b) |
| H_SILL | 0.392 | m | sheet pixels | measured | - | body lower edge at the doors (first bright row under the dark rocker, x 585-889 minus the B-pillar shut line): median y 273.5 px (IQR 273.5-275.5); the running board below (to about y 289) is a separate part |
| H_BELT | 1.155 | m | sheet pixels | measured | - | top of the body-colour door skin under the side glass, 473 columns x 600-1125: y = 131.14 + -0.00710 x (rms 0.41 px), 125.0 px at mid-doors; the glass itself ends 121.0 px (black belt moulding between, 21 mm); glass_bottom_m 1.176 |
| H_COWL | 1.231 | m | sheet pixels | derived | - | windscreen line meets the bonnet top line (y = 155.5 + -0.0811 x over x 350-530, rms 0.95) at (558.1, 110.3) px; the side silhouette of a plan-bowed windscreen is its centre line |
| H_BONNET_F | 1.121 | m | sheet pixels | derived | - | bonnet top line meets the front face line at (294.0, 131.7) px (sharp-corner point; the drawn edge is rounded) |
| H_ROOF | 1.723 | m | sheet pixels | measured | 1.900 verified (toyota-global id60013935: height 1900 mm (Fable's note said 1.86)); sheet - real -0.177 | roof top outline y 14.5 px at x 853 (top-most object pixel over x 660-1129); ground y 349.79 |
| H_BUMPER_T | 0.706 | m | sheet pixels | measured | - | front bumper bar top: first row of a mostly dark 10-row run in columns 279-314, median y 212.5 px; rear bar 0.654 m (y 222.5); rear_m 0.654 |
| H_BUMPER_B | 0.467 | m | sheet pixels | measured | - | front bumper bar bottom (end of that dark run, tow hooks excluded by the column range), median y 259.0 px; rear bar 0.438 m (y 264.5); rear_m 0.438 |
| H_LAMP | 0.906 | m | sheet pixels | measured | - | front view headlamp housing rows 812.5-848.5 px (first non-body-colour row under the bonnet front and first body-colour row under the housing, median over columns 318-375) -> centre, front-view scale |
| Y_COWL | -0.764 | m | sheet pixels | derived | - | same point, x 558.1 px |
| Y_A_BASE | -0.669 | m | sheet pixels | derived | - | A-pillar body-colour strip centre over rows 50-105: x = 701.3 + -0.9980 y (rms 0.46, n 56), at the belt row 125.0: x 576.5 px (the mirror hides the pillar base itself) |
| Y_ROOF_F | -0.191 | m | sheet pixels | derived | - | windscreen line meets the roof top line (y = 23.37 + -0.00844 x over x 700-1110, rms 1.24) at (669.5, 17.7) px |
| Y_ROOF_R | 2.293 | m | sheet pixels | derived | - | roof top line meets the upper tail line at (1152.8, 13.6) px |
| Y_RS_BASE | 2.523 | m | sheet pixels | derived | - | rear view: rear screen (glass with its black frame) rows 703.5-786.5 px at the centre +-90 px -> base Z 1.161 m; side view upper tail line at that height x 1197.5 px; z_m 1.161 |
| Y_B | 0.336 | m | sheet pixels | measured | - | B-pillar = columns with glass in under 25 % of rows 50-110: x 760.5-783.5 px (width 0.118 m); width_m 0.118 |
| Y_C | 1.171 | m | sheet pixels | measured | - | C-pillar = columns with glass in under 25 % of rows 50-110: x 923.5-945.5 px (width 0.113 m); width_m 0.113 |
| Y_D | 2.351 | m | sheet pixels | measured | - | D-pillar = columns with glass in under 25 % of rows 50-110: x 1128.5-1199.5 px (width 0.365 m); the D pillar's rear edge is the tail silhouette at row 117; width_m 0.365 |
| RAKE_WS | 50.3 | deg | sheet pixels | measured | - | windscreen silhouette (centre line) left edge over rows 44-96, x = 690.8 + -1.2031 y (rms 1.54 px, n 53); positive = top rearward Checked 2026-10-02 (plan 7a): 50.3 is from vertical; the silhouette moves 1.203 px horizontally per 1 px vertically, cowl (-0.764, 1.231) to roof front (-0.191, 1.707) is 0.573 m along over 0.476 m up |
| RAKE_RS | 22.1 | deg | sheet pixels | measured | - | tail silhouette above the belt (D-pillar / tailgate glass frame) rows 44-112, x = 1147.2 + 0.4054 y (rms 1.38, n 69); positive = top forward |
| RAKE_FRONT | -1.8 | deg | sheet pixels | measured | - | front face (lamp and grille panel) left silhouette over rows 160-204, x = 289.8 + 0.0318 y (rms 1.23, n 43); positive = top rearward |
| RAKE_REAR | 5.9 | deg | sheet pixels | measured | - | tail silhouette below the belt rows 128-199 (tail lamp side included), x = 1188.0 + 0.1026 y (rms 1.56, n 72); positive = top forward |
| TUMBLEHOME | 21.1 | deg | sheet pixels | measured | - | greenhouse silhouette above the mirrors, front view rows 705-750: left x = 620.9 + -0.3898 y (rms 0.50), right x = 292.9 + 0.3938 y (rms 0.42) -> 21.4 deg; rear view rows 704-750 -> 20.8 deg; front_deg 21.4, rear_deg 20.8 |
| ARCH_R | 0.474 | m | sheet pixels | measured | - | arch opening = inner edge of the flare (dark wheel well -> flare face, luminance 45 crossing) on rays every 3 deg from 195 to 345 deg about each hub: median radius front 93.7 px, rear 90.6 px; sides only 92.4 / 90.0, top 92.1 / 87.2 |
| ARCH_TOP_FLAT | 0.153 | m | sheet pixels | measured | - | equivalent flat: chord of the side-radius circle at the opening's top height (rays 245-295 deg), 2 sqrt(r_side^2 - r_top^2) when the top sits lower than the side circle, else 0: front 15.6 px, rear 44.0 px (radius sides/top front 92.4/92.1, rear 90.0/87.2 px) |
| GROUND_CLEAR | 0.224 | m | sheet pixels | measured | 0.220 unverified (Fable's recollection; not on the Toyota pages); sheet - real +0.004 | front view: lowest dark underbody pixel between the front tyres (x 354-562) at (379, 946.5) px; side view lowest underbody between the wheels (running board / tank) 0.284 m at (826, 294.5); side_underbody_m 0.284 |

## Owner decisions at gate G0 (2026-10-02)

Owner: "Yes, sheet height and real-car width, go ahead with G1." Heights and lengths stay as measured on the sheet;
W_BODY, W_FLARE, TYRE_W, the tracks and the roof width (scaled) come from the real car; TYRE_R keeps the sheet value
with the hub at that height. The rule rows measured in G0 replace the boxy SUV defaults for this car (table "Rule
values used for this car" below); rules not listed there use the boxy SUV default in `rules/`.

## Overall against the real car

| Quantity | Sheet | Real car | Status | Difference | Source |
|---|---|---|---|---|---|
| length | 4.847 | 4.820 | verified | +0.027 | toyota-global id60013935 (4820 mm HDJ81V and HZJ81V; FJ80G 4970) |
| height | 1.723 | 1.900 | verified | -0.177 | toyota-global id60013935 (1900 mm; Fable's note said 1.86) |
| width | 2.029 | 1.900 | verified | +0.129 | toyota-global id60013935 (1900 mm; HZJ81V narrow body 1830; Fable's note said 1.93); sheet = W_FLARE |
| wheelbase | 2.850 | 2.850 | verified | 0 (registration) | toyota-global id60013935 (2850 mm); used for registration |

Not on the Toyota pages, so unverified: tracks 1.595 / 1.615, tyre 275/70R16 (radius 0.396), ground clearance 0.22 (Fable's recollection).

## Rule rows measured on the sheet

The rule default is the boxy SUV value in `rules/`; the measured value is the Land Cruiser on the approved sheet.
Rows after LAY-06 are rules not marked measure that were measured on the way.

| ID | Default (boxy SUV) | Measured | Unit | Evidence |
|---|---|---|---|---|
| GH-02 | RAKE_WS 32 (28 to 38) | 50.3 | deg | = RAKE_WS (side silhouette of the windscreen) |
| GH-07 | 6 (4 to 9) | 21.1 | deg | = TUMBLEHOME; front view 21.4, rear view 20.8; left/right front 21.3/21.5 |
| GH-09 | 0.090, 0.110, 0.150 | B 0.118, C 0.113, D 0.365 | m | visible pillar between glass areas (body colour plus black frames), side view; D = last glass to the tail silhouette |
| GH-10 | H_BELT | H_BELT 1.155, rise_to_rear_m 0.019, over_m 2.699, rms_m 0.0021 | m | belt line fit over x 600-1125 px: slope -0.00710 px/px (negative = rises to the rear) |
| BS-05 | margin 0.080, flat 0.35 x dia | ARCH_R 0.474, margin 0.091, flat_m 0.153, flat_over_arch_dia 0.16, radius_side_vs_top_m front 0.475/0.473, rear 0.462/0.448 | m | margin = ARCH_R - TYRE_R; flat as ARCH_TOP_FLAT; a squared top would show a smaller radius at the top than at the sides |
| BS-06 | 0.070 out, 0.060 tall; cladding 0.120 tall | flare_out 0.109, flare_band_side 0.128, cladding_tall 0.283 | m | out = (W_FLARE - W_BODY) / 2 in the front view; flare band = radial width of the flare seen from the side (opening edge to the body-colour edge, median front 24.2 / rear 25.5 px); cladding = dark band from y 218.5 to the sill 273.5 px at the doors (includes the darker rocker strip) |
| FR-01 | 5 (0 to 10) | -1.8 | deg | = RAKE_FRONT, positive = top rearward (leans back) |
| FR-02 | crown 0.025; fall 0.040 | crown 0.007, fall 0.11 | m | crown = sag of a parabola through the bonnet top edge in the front view over x 352-567 (half width 108 px, 1.2 px); fall = bonnet top line height at the cowl minus at the leading edge, side view |
| FR-04 | 0.180 tall, 0.100 out, wraps 0.250 | tall 0.239, out 0.108, side_length 0.386, rear_tall 0.216 | m | side view: bar rows 212.5-259.0; out = front face line at the bar top (x 296.5) minus the bar face (x 275.5); side length = bar face to the black wheel-well gap at mid-height (x 350.5); rear bar side length not separable: the bar runs into the dark flare at the same luminance |
| FR-05 | 0.200 x 0.120 | housing_w 0.459, housing_h 0.212, lamps_only_w 0.388, H_LAMP 0.906, centre_x_from_cl 0.694 | m | front view left housing (side marker + two round lenses in one dark frame) x 301.5-379.5, y 812.5-848.5 px; lamps only = marker's inner edge x 313.5 to the frame's outer edge |
| RR-01 | 3 (0 to 6) | 5.9 | deg | = RAKE_REAR, positive = top forward |
| LAY-02 | 0.48 | 0.618 | fraction of WB | (Y_B - front axle Y) / WB |
| LAY-03 | 0.060 | to_flare_outer_edge -0.453, to_opening_front -0.293, trailing_edge_rake_deg 6.4 | m | rear door trailing edge line x = 931.7 + 0.1128 y (rows 135-170, rms 0.56); flare outer edge's front-most point x 862.9; opening front (hub - side radius) x 893.9; negative = the edge is behind that point (the door is cut round the arch) |
| LAY-06 | H_BELT | split_z 0.999, H_BELT 1.155, difference -0.156 | m | rear view: thin horizontal line across the tailgate below the rear screen at median y 814.0 px (77 columns); rear screen frame bottom y 786.5 (1.161 m) |
| GH-03 | 0.090 | 0.123 | m | extra, GH-03 A-pillar width seen from the side: rows 50-99: windscreen silhouette edge to the door glass front edge, median |
| GH-08 | 8 (3 to 15) | 22.1 | deg | extra, GH-08 rear screen rake: = RAKE_RS |
| LAY-01 | 5 from vertical | 7.4 | deg | extra, LAY-01 front door leading edge rake: x = 591.3 + -0.1291 y over rows 135-205; positive = top rearward |
| FR-03 | 0.035; 0.120 | 0.215 | m | extra, FR-03 bonnet leading edge round: gap 21.0 px from the sharp corner to the silhouette along the bisector |

## Rule values used for this car

The value each build reads for this car. Src: S approved sheet (G0 measurement), O owner, P design practice (Fable),
R real car; Conf: M measured, D derived, A assumed. Rules not listed use the boxy SUV default in `rules/`.

| ID | Value | Unit | Src | Conf | Note |
|---|---|---|---|---|---|
| GH-01 | base 0.185, top 0.073 | m | S | M | plan 7a: the windscreen centre line is 0.185 ahead of the A-pillar side edge at the belt row (Z 1.155) and 0.073 at the roof row (Z 1.707), G0 side view; replaces the v01 dial 0.010 |
| GH-02 | rake 50.3 | deg | S | M | = RAKE_WS |
| GH-03 | width 0.123 | m | S | M | A-pillar width seen from the side (G0 extra) |
| GH-07 | lean 21.1 | deg | S | M | = TUMBLEHOME on the sheet; G1 derives the lean from W_ROOF and reports it beside this |
| GH-08 | rake 22.1 | deg | S | M | = RAKE_RS |
| GH-09 | B 0.118, C 0.113, D 0.365 | m | S | M | visible pillar widths at the belt (body colour plus black frames) |
| GH-10 | rise 0.019, over 2.699 | m | S | M | the belt rises 0.019 over 2.699 from the A-pillar base |
| BS-02 | r 0.030, ledge 0.030 | m | P | A | G1 spec (plan 6a: wall-to-top round 0.030 everywhere; 6b: ledge 0.030); the boxy row reads r 0.015 |
| BS-05 | margin 0.091, flat 0.153 | m | S | M | ARCH_R = TYRE_R(sheet) + margin; flat = ARCH_TOP_FLAT |
| BS-06 | out 0.109, band 0.128, cladding 0.283 | m | S | M | flare and cladding, for G3 |
| FR-01 | lean -1.8 | deg | S | M | = RAKE_FRONT: the top is 1.8 deg forward |
| FR-02 | crown 0.007, fall 0.110 | m | S | M | bonnet crown at the leading edge and fall from the cowl |
| FR-03 | edge 0.200, corner 0.150 | m | P | A | edge: plan 7 (G1 v02; v01 dial 0.100, G0 measured 0.215); corner: G1 spec (plan 6a front plan corner 0.150; the boxy row reads 0.120) |
| FR-04 | tall 0.239, out 0.108, side 0.386, edge 0.030, corner 0.060 | m | S/P | M | tall, out and side length measured; edge round and plan corner radius G1 spec (plan 6c) |
| FR-05 | housing_w 0.459, housing_h 0.212 | m | S | M | headlamp housing (marker and two round lamps), for G3 |
| RR-01 | lean 5.9 | deg | S | M | = RAKE_REAR: the top is 5.9 deg forward |
| RR-03 | tall 0.216, side 0.386, edge 0.030, corner 0.060 | m | S/P | M | rear bar height measured; side length as the front bar (not separable on the sheet); rounds G1 spec (plan 6c) |
| LAY-01 | rake 7.4 | deg | S | M | used (plan 9a): front door leading edge through the A-pillar foot, bottom forward, 7.4 from vertical (G0) |
| LAY-02 | fraction 0.618, y 0.336 | - | S | M | used (plan 9a): front and rear doors split at the B-pillar centre line Y_B = 0.336 (fraction of WB behind the front axle 0.618) |
| LAY-03 | behind 0.293, rake 6.4 | m | S | M | used (plan 9a): rear door trailing edge at the belt 0.293 behind the rear arch opening's front edge, 6.4 deg from vertical, bottom forward; the lower rear corner is cut by the arch opening (G0: flare -0.453, opening -0.293) |
| LAY-06 | split 0.999, half_width 0.660 | m | S | M | used (plan 9a): tailgate split height (G0 rear view) and tailgate half-width (rear view) |
| LAY-04 | inboard 0.060 | m | P | A | used (plan 9a): bonnet shut line along the fender top, inboard of the body side |
| LAY-05 | gap 0.006, chamfer 0.004, return 0.015 | m | O | A | used (plan 9a): panel gap, edge chamfer, return depth |

## Construction values (G1)

Numbers the G1 construction needs that are not a hard point or a rule row. Src as above.

| Name | Value | Unit | Src | Note |
|---|---|---|---|---|
| BONNET_EDGE_Y | -2.121 | m | S | Y of the bonnet edge point (bonnet top line meets the front face line, G0; H_BONNET_F is its height) |
| RS_BASE_Z | 1.161 | m | S | height of the rear screen base point (G0; Y_RS_BASE is its Y) |
| GLASS_BELT_BAND | 0.030 | m | P | body-colour band above the greenhouse base before the glass starts (plan 6d) |
| REAR_BUMPER_T | 0.654 | m | S | rear bumper bar top (G0, H_BUMPER_T evidence rear_m) |
| REAR_BUMPER_B | 0.438 | m | S | rear bumper bar bottom (G0, H_BUMPER_B evidence rear_m) |
| BELT_ANCHOR_Y | 0.750 | m | P/S | plan 7: the belt ledge equals H_BELT here (mid-doors, where G0 quoted H_BELT) |
| REAR_SCREEN_BOW | 0.030 | m | P | plan 7a: constant plan bow of the rear screen |
| TUCK_ROUND | 0.015 | m | P | plan 7: round on the sill tuck edge (BS-03) |
| GLASS_INSET | 0.006 | m | P | plan 9b: glass panes sit this far inward along the surface normal |
