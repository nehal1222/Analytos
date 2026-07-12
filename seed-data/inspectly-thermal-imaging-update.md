# Inspectly — Product Overview

**Product:** Inspectly
**Category:** AI visual inspection and compliance documentation for regulated manufacturers
**Owner:** GroundTruth, Regulated Manufacturing Vertical

## Summary

Inspectly is a computer-vision inspection layer for manufacturers who operate
under heavy regulatory scrutiny — medical device makers, aerospace component
suppliers, and precision electronics. It sits at the end of a production
line, inspects units against a trained defect model, and automatically
generates the audit-ready documentation that FDA / ISO 13485 / AS9100
auditors expect.

## Features

- **Automated Defect Detection** — Vision models trained per part number
  flag surface defects, dimensional deviations, and assembly errors in real
  time on the line.
- **Compliance Audit Trail** — Every inspection decision (pass/fail/escalate)
  is logged with the image, model version, and operator override (if any),
  producing a chain-of-custody record auditors can pull on demand.
- **Batch Traceability** — Links every inspected unit back to its
  manufacturing batch, supplier lot, and machine/operator, so a recall can be
  scoped precisely instead of pulling an entire production run.
- **Root-Cause Clustering** — Groups recurring defect types by machine,
  shift, and supplier lot to surface systemic causes instead of one-off
  outliers.
- **Thermal Imaging Defect Detection** — Adds a thermal camera pass alongside
  the visual model to catch subsurface defects (voids, delamination, cold
  solder joints) that a visible-light camera alone can't see, without
  slowing down the line.

## Proof Points

- Manual inspection time **dropped 47%** per unit after Inspectly took the
  first pass and routed only ambiguous cases to human reviewers.
- Defect escape rate (bad units that reach the next stage undetected)
  **fell from 1.8% to 0.3%** in our first regulated-manufacturing pilot.
- Audit preparation time **dropped from roughly 3 weeks to 2 days**, since
  the compliance audit trail is generated continuously instead of
  reconstructed after the fact.
- The defect-detection model reached **99.2% detection accuracy** on the
  held-out calibration test set, benchmarked against the customer's existing
  human-inspector baseline of 94.5%.
- Root-Cause Clustering identified a single miscalibrated machine as the
  source of **61% of one customer's Q1 defect volume**, letting them fix one
  machine instead of auditing the whole line.
- Thermal Imaging Defect Detection caught **subsurface defects in 2.1% of
  units** that the visual-only model had passed, in the first pilot batch on
  a precision electronics line.

## Roadmap Decision Log

- **2026-03-20** — Decided to build Batch Traceability before expanding
  Root-Cause Clustering to multi-site deployments, after our medical device
  pilot customer flagged traceability as a blocking requirement for their
  next FDA audit.
- **2026-06-01** — Decided to keep human-in-the-loop override mandatory for
  any "fail" decision on Class II/III medical device parts, rather than
  allowing fully autonomous rejection, based on regulatory risk discussed
  with the pilot customer's quality team.
- **2026-07-05** — Decided to ship Thermal Imaging Defect Detection as an
  add-on module for precision electronics customers first, before offering
  it to medical device or aerospace lines, since subsurface solder/void
  defects are the dominant failure mode in electronics but a smaller share
  of defects in the other two verticals.
