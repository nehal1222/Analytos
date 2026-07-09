**Product:** Inspectly
**Category:** AI visual inspection and compliance documentation for regulated manufacturers

## Summary

Inspectly is a computer-vision inspection layer for manufacturers who operate under
heavy regulatory scrutiny.

## Features

- **Multi-Line Simultaneous Inspection** — Runs inspection models across multiple
  production lines from a single control station, instead of requiring one dedicated
  inspection station per line.

## Proof Points

- Multi-Line Simultaneous Inspection let one customer **cut inspection station
  hardware costs by 52%** across a four-line facility, without slowing down any
  individual line.

## Roadmap Decision Log

- **2026-07-09** — Decided to cap Multi-Line Simultaneous Inspection at four
  concurrent lines per station in this release, since compute load testing showed
  latency degrading noticeably beyond that on the current hardware profile.
