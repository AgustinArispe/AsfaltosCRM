# PULSE CRM — composition review

Status: READY FOR FINAL RENDER technically, as a silent composition, pending visual review/user instruction. No final MP4 or draft MP4 was generated. No video was published.

## A–C. Composition and format

Created `../composition/index.html` from the approved 30-second plan. One seekable paused GSAP timeline, Hyperframes 0.8.74 pinned, local GSAP 3.14.2.

Root: 30.000 seconds, data-fps 30, width 1920, height 1080. Therefore 900 output frames, indexed 0–899, final frame at 29.966667 seconds. Verified root metadata, timing.json, asset-verification.json and CLI info.json. This is composition/frame-budget verification, not ffprobe verification of an MP4: no MP4 exists.

## D. Real UI captures

Ten 1920×1080 source captures, light mode, isolated local demo:

- `/pipeline`: Nueva 3 / Cotizada 3 / Negociación 2; Nexo and Delta.
- `/notifications`: Ramiro Serra / Delta Digital, Nueva, active, unread; badge 1.
- `/pipeline/opportunities/5`: Nexo / Paula Luna; source WhatsApp; Sofía Fernández; Plan Business; activity and notes captured separately.
- `/whatsapp/conversations/1`: Paula, existing incoming/outgoing messages and Leído.
- `/whatsapp/conversations/2`: Ramiro, loaded workflow.png.
- `/whatsapp/conversations/3`: Lara, loaded 0:00 / 0:02 audio player, not played.
- `/dashboard?period=three-months&from=2026-07-01&to=2026-09-30`: overview, evolution and origins captures.

28 crop recipes; 27 UI crops used plus the original logo. Originals remain local under ../captures/ and are ignored by Git. Only approved crops are shipped. No application screenshot is repainted. The native light theme was selected; no app code changed.

## E–F. Motion and overlays

Implemented controlled pan/zoom, Nexo elevation, cursor travel/click rings, notification badge pulse, Delta focus, recorded activity→notes panel transition, message entrances, image reveal, audio-player hover, KPI/chart emphasis and short crossfades. Camera scale changes remain at or below 1.12; no bounce, rotation, glow, fake playback/progress or invented message statuses.

Seven approved overlay strings and exact entry/hold/exit times are recorded in ../composition/timing.json. Local Manrope, navy on light canvas, safe margins; final logo/tagline remain visible through frame 899. Reviewed full-size representative frames and contact sheets. No overlay overflow or contrast findings.

## G–H. Validation

`check-final.json`: Hyperframes check **PASS**, 0 errors. Runtime, layout, motion and contrast each have 0 errors and 0 warnings. Layout sampled 25 timestamps including boundaries/transitions; motion assertions sampled 300 times. The lint stage has 15 non-blocking advisories: 14 recommendations to extract nested elements into sub-compositions, plus reused-image-source discovery advice. Identical logo/badge assets are deliberately reused in different intervals; stills confirm their correct appearance. No failed requests or missing/broken assets found.

`asset-verification.json`: 30 referenced local assets (28 PNGs including logo, Manrope and GSAP), all nonempty; PNG headers/dimensions and SHA-256 recorded. HTML has no audio/video elements or external URL dependency. The original logo is copied unchanged.

`keyframes.json` and `nexo-motion.png`: seekable trajectory/elevation evidence. `timeline.json` and `info.json`: timing metadata.

Review covers first frame, the twelve requested representative times, extra settled message/KPI poses, scene boundaries, four crossfade midpoints and final frame. No blank sampled frame, broken image, unexpected theme change, browser chrome, kg, IDs, demo email, demo footer or administrative controls in the composition crops. This is sampled visual validation, not a claim to have exported/inspected all 900 frames.

## I. Review materials

- Live local Studio: http://localhost:3002/#project/composition (HTTP 200 confirmed).
- `frames/`: 24 representative PNGs, including all requested timestamps and frame 899.
- `frames/contact-sheet-1.jpg`, `contact-sheet-2.jpg`, `contact-sheet-3.jpg`.
- `transitions/`: four mid-transition PNGs and contact-sheet.jpg.
- `nexo-motion.png`: focused motion strip.

## J. Deviations and limitations

1. Source label: the plan says Referido, but the real UI says Manual. Reported before composition, then work continued after the user's “segui”. Authentic Manual is preserved; no UI label or dataset modification.
2. Opening: notification enters at 2.5 instead of 2.7, while the logo exits through 2.7. This small transition overlap prevents an empty boundary frame. Total duration and overlay timings are unchanged.
3. Actual seller is shown in detail, not on the pipeline card, as explicitly allowed in the plan.
4. UI capture crops are scaled for the approved panel layout; animated camera zoom remains ≤1.12. Small native UI labels are softer than vector overlays at enlargement; the source UI and official 180px logo are deliberately not redrawn.
5. The notification-to-pipeline handoff reveals the existing board and emphasizes Delta. It does not fabricate a prior empty board, increase the unread count or create an opportunity.

## K–L. Readiness and audio

READY FOR FINAL RENDER: yes, technically, with silence and the above documented source-label correction. Review the Studio composition before authorizing final rendering. Music/voice/SFX absent; the unverified brag music track was not copied or used. No provider authentication required.

## M–P. Files and safety

All task files are under brag-output/: composition brief, composition source/build helpers, local cropped assets/font/runtime, capture manifest, timing/motion assertions, and review material. The approved storyboard is unchanged. No frontend/backend functionality changes and no seed reset.

Branch: demo/pulse-video. Main and origin/main retain 52d29b160f13d5b4636d91f578d30648aa950ba5. Only the demo branch is committed/pushed; see Git history for the delivery commit.

Runtime isolation verified via the demo wrapper: database host db, database pulse_demo, WhatsApp provider fake. No production connection, Railway action, production DB mutation or real Meta request was made. Opening demo chats may update their local read state; no messages were sent or commercial data changed.
