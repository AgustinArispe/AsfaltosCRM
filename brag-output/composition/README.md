# PULSE CRM — review composition

30 seconds · 900 frames · 30 fps · 1920×1080 · light mode · silent.

## Review locally

Run from this directory:

```sh
npm run check
npx --yes hyperframes@0.8.74 preview --background
```

Use the Studio URL printed by preview. No live CRM, login, database, Meta or network asset is needed by the composition. Every visual resource is local. The review server is local; nothing is published.

The root `data-duration="30"` and `data-fps="30"` govern the future frame count.
No final MP4 has been generated. Final rendering requires the user's next instruction.

## Editable source

- `index.html`: standalone Hyperframes composition, one paused GSAP timeline.
- `build-composition.py`: reproducible authoring source; regenerates index.html, timing.json and motion assertions. Update this when changing the source so regeneration preserves edits.
- `prepare-assets.py`: lossless rectangular crop recipe from real captures, using FFmpeg. Does not alter the application.
- `capture-manifest.json`: exact source/crop coordinates.
- `timing.json`: approved overlay timings and narrative boundaries.
- `verify-assets.mjs`: dimensions, duration, local asset integrity and silent/no-network checks.

Only crop layers are rearranged as permitted by the storyboard. No labels, metrics or controls are repainted. The logo and Manrope are original local brand assets.

## Review notes

- Actual source label is **Manual**, while the storyboard said Referido. This was reported during capture. The composition preserves the authentic UI label.
- Pipeline appears at 4.2s inside the lead-arrival beat, then carries through the 6–11s Pipeline beat, as described by the storyboard's match cut.
- The opening logo crossfade lasts until 2.7s and notification entrance begins at 2.5s. Later scenes overlap by 0.2–0.3s during their planned transition windows (10.7–11, 15.7–16, 21.8–22.1, 26.7–27). Narrative boundaries and overlay timings remain fixed.
- Source content is fictional demo data. Inspect full-size frames for fine UI text; the contact sheets are thumbnails.
- Hyperframes may advise extracting the monolithic scene layers into sub-compositions and flag reuse of identical logo/badge sources. Those are authoring advisories, not evidence of duplicate onscreen brands; inspect the preview.

Uncropped local screenshots are ignored by Git because they contain internal demo fields excluded from the advertisement. The portable composition ships only approved crops. Re-cropping requires those local source captures; normal playback/recomposition does not.
