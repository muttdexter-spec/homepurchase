# Detecting manipulated listing photos

Written 2026-09-06 after the 2450 Overton failure, where the photo pass called a gut-job "genuinely
renovated." Supersedes the staging guidance in section 6 of the analysis spec.

---

## 1. The hard technical limit, stated first

**No forensic analysis is possible on these images.** The media server sends no CORS headers, so the
page cannot fetch the bytes, and drawing them to a canvas taints it. That rules out, permanently:

- EXIF and metadata inspection (which software touched the file)
- Error Level Analysis, noise residual, or JPEG ghost analysis
- Any pixel-level or frequency-domain test
- Any automated AI-detection model

Everything below is **visual judgment at full resolution**. It produces false positives and false
negatives. Treat it as evidence that shifts confidence, never as proof.

---

## 2. What is actually happening on 2450 Overton

I re-examined the photos at 760px looking specifically for manipulation. The finding is more useful
than a yes or no.

**Not found: fabricated surfaces.** Kitchen photos 11 and 12 are mutually consistent across two
angles: same backsplash pattern, same counter, same cabinet profile, same floor. Per-image AI
re-skinning almost always breaks multi-angle consistency, and it does not break here. The kitchen
refresh appears to be **real but cheap** — painted or refaced doors, laminate counter with a rolled
edge and a topmount sink, mosaic backsplash, dated appliances. Photo 30's bathroom is a genuine 1987
corner garden tub, not a fabrication.

**Found, and decisive: virtual staging.** Photo 7 is the clearest case:

- The sofa at left has **no contact shadow** and does not compress the rug pile. It floats.
- The rug edge meets the hardwood with a hard, unnaturally clean line and no edge shadow.
- The sofa's perspective lines do not converge with the room's vanishing point, which the staircase
  and floorboards establish clearly.
- The barrel chair's legs do not meet the floor convincingly and cast nothing.
- The drum table's shadow is soft and directionless despite a chandelier directly above it.

Furniture also appears and disappears between shots of the same room, which is the giveaway across
the set rather than within one image.

**Found: aggressive HDR and exposure blowout.** Every interior is pushed to near-white. This is not
AI, it is ordinary editing, and it is **the single most effective concealment in the set** because
it flattens exactly the information that reveals condition: scuffs, stains, colour variation, wear
patterns, grout discolouration, patchy stain, drywall waviness.

**Found: wide-angle distortion** making rooms read substantially larger than they are.

The one thing that survived all of it is the **heavy stipple ceiling**, plainly visible in photo 7,
along with the original oak staircase and orange 1987 hardwood.

**Conclusion for this listing:** the deception was real and it worked, but the mechanism was virtual
staging plus heavy processing plus selective concealment, not AI-generated rooms. That distinction
matters because the countermeasures differ.

---

## 3. The tells that actually work

Ordered by reliability.

### Tier 1: cross-photo consistency (strongest, and cheap)

Per-image editing breaks between angles. Any room photographed more than once gets checked:

- Counter colour, pattern and edge profile identical across angles?
- Backsplash pattern continuous and consistent?
- Cabinet count, door profile and hardware the same?
- Flooring tone and direction consistent?
- **Does furniture appear in one shot of a room and vanish in another?** That is virtual staging,
  near-conclusively.

A mismatch here is the closest thing to hard evidence available.

### Tier 2: physics failures (reliable when present)

- **Contact shadows.** Real furniture darkens the floor where it meets it and compresses carpet pile.
  Inserted furniture floats.
- **Shadow direction** must agree with the windows and fixtures in frame.
- **Reflections.** Mirrors, glass and stainless are where insertion fails. A mirrored closet that
  does not reflect the inserted sofa is conclusive.
- **Perspective agreement.** Inserted objects' lines should converge to the room's vanishing point.
- **Rug and object edges** should show soft contact, not a clean cut.

### Tier 3: detail collapse (only visible at full resolution)

- Garbled text on appliance badges or control panels
- Melted or asymmetric hardware, missing hinges
- Outlets and switch plates with wrong geometry, or missing where they should be
- Cabinet doors with no reveal gaps, counters passing into walls, missing toe kicks
- Repeating texture in wood grain, tile or backsplash that cannot occur physically
- Halos or soft mush where an edited surface meets an unedited one

### Tier 4: processing signature (not manipulation, but conceals like it)

- Whites clipped to pure white, no texture in bright areas
- Every room the same colour temperature regardless of window orientation
- No visible wear anywhere in a house over 20 years old, which is itself implausible
- Windows blown out to solid white, or conversely perfectly exposed exterior and interior at once

---

## 4. The strategic answer: detection is the second line, not the first

Detection is worth doing, but it is fragile and it will keep improving against you. The robust fix
does not depend on catching the manipulation at all.

**Photos may demote a listing. Photos may never promote one.**

Adopt this as a hard asymmetry:

- A photo showing a problem is **evidence**. Efflorescence, a fuse panel, a garden tub, a soffit
  above the uppers, a drop ceiling. Act on it, downgrade on it.
- A photo showing something nice is **not evidence**. It is a marketing asset produced by someone
  paid to sell the house, and it may be staged, processed, virtually furnished, or out of date.
- Therefore **no listing's condition score may rise above "unverified" on photographic evidence
  alone.** A house that looks immaculate in fifty photos scores exactly the same as a house with no
  interior photos: unknown, pending eyes on it.

This is robust whether the manipulation is AI, a wide lens, or a well-timed throw blanket over a tub.

The corollary is that **the photo pass is a screening-out tool, not a shortlisting tool.** Its job is
to eliminate listings cheaply and to generate a targeted list of what to verify in person. It is not
capable of telling you a house is good, and the Overton run is the proof.

---

## 5. Virtual staging is itself a negative signal

Sellers virtually stage when the house is empty and the real interior does not sell itself. It is
legal and common, and in Ontario it is generally expected to be disclosed, but the decision to use it
carries information:

- The property is vacant, so no one is living with its condition
- The rooms did not photograph well unfurnished
- Budget went to presentation rather than to the house

**Score `staging: virtually_staged` as a mild negative and a confidence reducer, never as neutral.**
Same for a listing that is vacant with heavy HDR.

---

## 6. Schema and rule changes

Add to the section 6 observation record:

```
staging:              professionally_staged | virtually_staged | lived_in | vacant | mixed
virtual_staging_tells: [no_contact_shadow, perspective_mismatch, furniture_inconsistent_across_shots,
                        reflection_failure, clean_rug_edge, none_observed]
hdr_blowout:          none | moderate | severe          # severe = finish condition unassessable
cross_angle_check:    consistent | minor_variance | inconsistent | single_angle_only
manipulation_risk:    low | medium | high
concealed_surfaces:   [list every surface a staged object covers]
```

Three new rules:

**Rule A. Anything a staged object covers is `not_shown`, not fine.** A throw over a tub, a rug over
a floor, a plant in front of a cabinet run. Overton's main bathroom had a blanket draped over the tub
basin, and I read it as decor. It was concealment, and it worked.

**Rule B. `hdr_blowout: severe` forces every finish-condition field to `not_shown`.** If the exposure
has removed the texture, you cannot assess wear, and pretending otherwise is how a gut job scores
a B.

**Rule C. `manipulation_risk: high` or `cross_angle_check: inconsistent` caps the listing at
INCONCLUSIVE regardless of everything else**, and routes it to a showing rather than a grade.

---

## 7. What to actually do about it

1. **Ask the agent.** "Are any photos in this listing virtually staged or digitally enhanced?" In
   Ontario this is generally expected to be disclosed, and asking costs one line in an email. Add it
   to `agent_questions.md` as a standing question on every listing.
2. **Ask when the photos were taken.** Stale photos are a separate and equally common problem.
3. **Compare against Street View.** Exterior only, but it is unedited and it is the one image in the
   process that nobody is trying to sell you.
4. **Treat any listing that clears the photo pass as unproven, not good.** The output of the pass is
   a shortlist to go look at, and a list of what to look at when you get there.
