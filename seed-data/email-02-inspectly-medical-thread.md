# Email Thread: Inspectly Pilot — Meridian MedTech FDA Audit Prep

**Thread:** inspectly-pilot-meridian-2026
**Participants:** Jonas Fielder (Analytos, Solutions Engineer), Dr. Anita
Kessler (Meridian MedTech, VP Quality Assurance), Priya Nandakumar (Analytos,
VP Product)
**Status:** Internal + customer thread — contains customer name and
regulatory specifics, internal-only, must not be surfaced externally.

---

**From:** Dr. Anita Kessler <a.kessler@meridianmedtech.com>
**To:** Jonas Fielder <jonas.fielder@analytos.ai>
**Date:** 2026-05-18**
**Subject:** Inspectly pilot — pre-audit readiness

Jonas,

Our FDA recertification audit is scheduled for early Q3. I need to know
whether Inspectly's audit trail is going to hold up under scrutiny before I
commit to using it as our system of record for the Class II line. Historically
audit prep has taken us about three weeks of pulling paper records together.

Also — we had a defect escape reach a downstream station last month before
your system was live. Once it's on all lines, what's the expected drop in
escape rate?

Anita

---

**From:** Jonas Fielder <jonas.fielder@analytos.ai>
**To:** Dr. Anita Kessler <a.kessler@meridianmedtech.com>
**Cc:** Priya Nandakumar <priya.nandakumar@analytos.ai>
**Date:** 2026-05-20
**Subject:** RE: Inspectly pilot — pre-audit readiness

Anita,

On audit prep: our other pilot customer went from roughly 3 weeks to 2 days
once the compliance audit trail was running continuously instead of being
reconstructed after the fact. I'd expect something similar for you given a
comparable inspection volume.

On escape rate: across our first regulated-manufacturing pilot we saw
defect escape rate fall from 1.8% to 0.3%. Detection accuracy on the
calibration set was 99.2%, versus a 94.5% baseline for manual inspection
alone.

One thing to flag given the Class II line: we're keeping human-in-the-loop
override mandatory for any "fail" decision on Class II/III parts — no fully
autonomous rejection. That was a deliberate call based on regulatory risk,
not a current model-confidence limitation.

Jonas

---

**From:** Dr. Anita Kessler <a.kessler@meridianmedtech.com>
**To:** Jonas Fielder <jonas.fielder@analytos.ai>
**Cc:** Priya Nandakumar <priya.nandakumar@analytos.ai>
**Date:** 2026-05-22
**Subject:** RE: Inspectly pilot — pre-audit readiness

That mandatory human-in-the-loop point actually helps our case with the
auditor, not hurts it. Please make sure that's documented clearly in
whatever compliance materials ship with the product — I plan to reference it
directly in our audit response.

One more ask, and this is important: nothing about Meridian's name, our
defect rates, or this audit timeline can appear in any of your public
marketing or case studies without written sign-off from our legal team.
This thread is confidential.

Anita

---

**From:** Priya Nandakumar <priya.nandakumar@analytos.ai>
**To:** Dr. Anita Kessler <a.kessler@meridianmedtech.com>
**Cc:** Jonas Fielder <jonas.fielder@analytos.ai>
**Date:** 2026-05-23
**Subject:** RE: Inspectly pilot — pre-audit readiness

Understood and confirmed — Meridian's name and any pilot-specific numbers
stay internal-only, no public use without your legal sign-off. We decided
in-quarter to prioritize finishing Batch Traceability before expanding
Root-Cause Clustering to multi-site, specifically because your team flagged
traceability as a blocking requirement for the Q3 audit. That'll ship ahead
of your audit date.

Priya
