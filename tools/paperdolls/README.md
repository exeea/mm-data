# Paperdoll sources

- `src/*.svg`: the editable source of the HUD paperdolls, copies of MekBay's location cut set (provenance, licence
  and the converter's rules in `data/images/paperdolls/README.md`). Location regions are elements with
  `class="armor unitLocation"` or `"structure unitLocation"` and `data-loc` (rear armor adds `data-rear="1"`); shield
  parts are `class="shield unitLocation"` with `data-loc="DC{arm}"` / `"DA{arm}"`. Keep every drawn part of a
  location, hands included, inside an element of its code.
- `review/`: one PNG per family (each view and shield variant; every region in its own colour with its code, a sample
  number and its anchor circle; the unassigned hull hatched grey; Mek art outside every region in red) and
  `validation.txt`, written by `./gradlew :megamek:convertPaperdolls` from the MegaMek checkout. Look at every PNG
  after a change.
