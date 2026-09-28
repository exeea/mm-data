# Pre-build checklist for a new modular Mek

Run this before modelling anything. You name the unit and share the art; I work through the questions below with
you, then build. Every answer here came from a correction on an earlier chassis, so each one saves a round of
rework.

The build itself is described in [NEW_CHASSIS_BRIEF.md](NEW_CHASSIS_BRIEF.md), and the review loop and its rules in
[UNIT_REVIEW_PROCESS.md](UNIT_REVIEW_PROCESS.md). This is the step before both.

## 1. What I gather first, without asking

- The unit's weight class and tonnage, and its **height band** (UNIT_REVIEW_PROCESS.md section 9).
- Every variant's unit file, from the Mek catalog: which locations carry weapons, which carry slotted heat sinks,
  which arms have hands or lower arm actuators, and any head weapons.
- The heaviest-armed variant, because it sets how much of the 5,000-triangle budget the body can take.
- The chassis's existing body and recipe, if it has one, so the old version can be archived.
- The three reference renders of the current state (section 4 below).

## 2. Questions for you

**Only once the art has arrived.** I share the facts from section 1, ask for the references, look at them, and
then ask. Many questions are answered by the pictures, and the rest are sharper for them.

**The art**
1. Which picture is the authority when they disagree: the miniature, the line drawing, or a record sheet?
2. Is there a front view? A side view? If not, which angle should I trust for proportions?
3. Is anything on the miniature a sculpting quirk rather than the design, and should be ignored?

**The body**
4. Where is the cockpit, and what does it look like: a head, a canopy blister, windows in a nose, a visor? (The
   Locust's is in its nose, not on the roof.)
5. What two or three features make it read as this Mek at a glance? Those get the detail budget first.
6. Is the body symmetric? Is anything on one side only, like the Atlas's dish?
7. Leg type: forward knee, reverse (bird) knee, or no legs? How bent should they stand?
8. Arms: hands, gun pods, weapon arms, or none? Do they sit flush against the torso?
9. Should it have a simpler LOD1 body for when it is small on screen, as the Phoenix Hawk has? Worth it for a
   detailed body; unnecessary for a plain one.

**The weapons**
10. For each location, where do its weapons sit: on a front face, hanging under something, in a turret, held in the
    hand? (The Locust fires its centre weapons from a chin turret.)
11. Do weapons sharing a socket sit side by side or over and under?
12. Missile launchers: upright and stacked, or lying flat? On the shoulders, in the torso, in a bay?
13. Any special rule for this chassis, like the Atlas drawing every LRM 20 as an upright LRM 5 on its waist?
14. Should head weapons share another location's face?

**Surface detail**
15. Where should vents go when no heat sinks are slotted in a torso?
16. Any detail to add or leave off: antennas, dishes, spines, searchlight position?

**Sign-off**
17. Which two or three variants should I check closely? One with the fewest weapons, one with the most and one with
    an unusual loadout covers most problems.
18. Should the old version be archived before the new one replaces it?

## 3. Rules I check on every build

- **Budget:** the whole unit, body plus weapons, within 5,000 triangles at LOD0 (2,000 at LOD1 when there is one).
  The body aims for about 4,000. No `Weapon review:` line from the export goes unexplained.
- **Height:** inside the class band, measured to the top of the armour.
- **Sockets:** on the surface of their own location, measured against the body rather than judged from a render.
- **Mirroring:** left and right mirror across the centre line, never copied.
- **Flush:** weapons sit on their surface, not floating off it or buried in it.
- **Faces the right way:** panels and windows face outward, since the game draws one side only.
- **Attached:** every part touches what it hangs from, legs to hips especially.
- **Vents after weapons:** no weapon drawn over a vent.
- **Every variant builds:** the assembled review passes with every weapon drawn.

## 4. The three renders you get at every step

1. **Six views** of the bare chassis: Front, Back, Left, Right, Above, Three-quarter, with the chassis named at the
   top right.
2. **Variant sheet:** every variant as the game builds it, with its real loadout and triangle count, framed to the
   chassis's size, plus close-ups of the variants chosen in question 17.
3. **Weight lineup:** the chassis beside neighbours of similar tonnage, on one ground line at one scale.

## 5. Finishing a unit

- **The final review includes a close look at the head.** I send an enlarged front and three-quarter crop of the
  head beside the reference art: its outline, eyes or visor, ears and fins, and how it sits in the collar. At sheet
  scale the head is only a few pixels across, and it is what makes a Mek read as itself (the Panther's snout, ears
  and collar each took a round to get right).
- I zip the old version into `archive/` under the next plain numbered name (`a1.zip`, `a2.zip` and so on), with a
  README inside.
- I update `UNIT_REVIEW_PROCESS.md` with any new rule the unit taught us.
- You decide whether and when the work is committed. I never push.
