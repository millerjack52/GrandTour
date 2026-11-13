# Car grammar

A library of car-modelling knowledge, written so a person can read it and a program can use it. The
plan is `docs/CAR_GRAMMAR_PLAN.md`. The first car is a Land Cruiser 80.

## What is in it

| Path | What it holds |
|---|---|
| `schema/hardpoints.md` | The named hard points that fix a car's architecture (wheelbase, overhangs, belt, cowl, roof, rakes, ...), one row each |
| `rules/greenhouse.md` | Greenhouse rules (GH): windscreen, pillars, roof, side glass, rear screen |
| `rules/bodyside.md` | Bodyside rules (BS): side plane, belt edge, sill, arches, flares, doors |
| `rules/front_rear.md` | Front (FR) and rear (RR) rules: face, bonnet, bumpers, lamps, tail |
| `rules/layout.md` | Layout rules (LAY): where panels split and openings sit |
| `bodytypes/boxy_suv.md` | The boxy SUV column of every rule, collected in one table |
| `cars/landcruiser80.md` | The Land Cruiser 80 car sheet: every hard point with value, source, confidence and evidence, and the rule rows measured on the approved sheet |
| `grammar.py` | Parses all the tables into Python dictionaries and fails loudly on a malformed row |
| `tools/` | The G0 measurement and drawing scripts for the Land Cruiser sheet |

## The tables are the source of truth

Every number lives in a Markdown table. Code reads the tables through `grammar.py`; nothing copies a
number into code. The body-type file repeats the boxy SUV column of the rules files, and
`grammar.py` fails if the two disagree, so a change is made in the rules file and then copied to the
body-type file (or the other way round) in the same edit.

## Rule rows

Columns: **ID | Rule | Boxy SUV | Sedan | Src | Conf**.

- **ID**: subsystem prefix and number (`GH-01`). IDs never change meaning; a retired rule keeps its ID.
- **Rule**: one sentence saying what the fact is.
- **Boxy SUV / Sedan**: the value for that body type, metres or degrees unless marked. The sedan
  column is filled only where known (G5 completes it); `n/a` means it does not apply.
- **Src**: R real-car data, S approved sheet, P design practice (Fable), O owner. Two sources are
  written `P/S`.
- **Conf**: A assumed, D derived, M measured. `measure` means the value is to be measured on the
  car's sheet; the measured value is written in the car sheet, not here.

## How to change a rule

1. Find the row by its ID in `rules/<subsystem>.md`.
2. Change the number (or the sentence). Set **Src** to `O` if the owner gave the number and **Conf**
   to `M` if it was measured.
3. Make the same change in the boxy SUV column of `bodytypes/boxy_suv.md` when the boxy SUV value
   changed.
4. Run `python Art/CarGrammar/grammar.py`. It lists every table it read and exits with an error
   naming the file and line of any malformed row or mismatch.
5. Rebuild the car. Corrections go into the library, not into the car's build.

## Car sheets

A car sheet lists every hard point of `schema/hardpoints.md` with **Value | Unit | Source |
Confidence | Real car | Evidence**, where Source is sheet pixels, real-car data, rule default or
owner, and Confidence is measured, derived or assumed. The sheet's second table holds the rule rows
measured on the car's approved reference, with the rule default beside the measured value. Where the
approved sheet and the real car disagree, the sheet wins and the difference is written in the
Real car column.
