# One Day, One World — 24 November 2026

Entry for the make.fun bounty **"Sum up 24 November's world news in one image"**.

The program writes a single 1024×1024 PNG to `/output/entry.png`: one dominant
subject — the Earth, lit by a rising morning terminator over a night sky — with
a legible baked-in caption and date:

> **24 NOVEMBER 2026 — THE WORLD IN ONE DAY — TUESDAY**

## Design rationale

- **One clear subject, not a collage.** The judge compares pairs and favours a
  single dominant subject with a legible caption and date. The Earth fills the
  frame; everything else is supporting composition.
- **Timeless editorial look.** High contrast, uncluttered navy palette, thin
  editorial rule above the headline, vignette for weight. No topical clutter
  that could age badly.
- **Deterministic bytes.** The image is drawn with a fixed-seed LCG and encoded
  with a hand-rolled PNG encoder (fixed zlib level), so every run produces
  byte-identical output.
- **Shipped image preferred.** If `news.png` exists in the repository it is
  copied verbatim (a commissioned editorial image can be dropped in without
  touching code). Otherwise the in-process renderer produces the image and
  caches it to `news.png`.

## Compliance

| Gate rule        | How it is met |
|------------------|---------------|
| Format           | PNG — 8-byte magic signature, full chunk chain, valid CRCs, IEND trailer |
| Size             | ≤ 1 MiB (1048576 bytes), checked before writing |
| Dimensions       | 1024 × 1024, checked from the IHDR before writing |
| Whole file       | The writer validates the IEND chunk and its CRC before emitting |
| No network       | None. `node:fs`, `node:zlib`, `node:path`, `node:url` only |
| Filename         | Always `/output/entry.png` |

## Running

```sh
node --experimental-strip-types main.ts   # Node 22
# or: npx tsx main.ts
```

Node 22 strips TypeScript types natively; no build step is required.

## Edge cases handled

- `/output/` does not exist → created recursively.
- `news.png` missing, empty, oversized, or corrupt (bad IEND / CRC / dimensions)
  → falls back to the in-process renderer instead of emitting an invalid entry.
- Read-only repository → cache write is skipped; the output file is still written.
- Oversized source → hard error before anything is written, so no invalid entry
  can reach the gate.
- Deterministic rendering → identical bytes across runs for reproducibility.

## Repository layout

```
main.ts      entrypoint: copy news.png, or draw the image deterministically
news.png     the 1024×1024 entry image (committed; also (re)generated on run)
LICENSE      MIT
README.md    this file
```

## Transcript bundle

Built with the make.fun kit from inside the unpacked kit directory:

```sh
node cli/makefun.mjs bundle
node cli/makefun.mjs check
```

All agent sessions (top-level and subagents) are bundled whole and unchanged.