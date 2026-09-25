# PULSE CRM v1 — actual MP4 validation

Output: ../pulse-crm-demo-v1.mp4

- Size: 4,210,504 bytes (4.21 MB / 4.02 MiB).
- Codec/container: H.264 / MP4.
- Duration: 30.000000 seconds.
- Resolution: 1920×1080.
- Frame rate: 30/1 fps.
- Frame count: 900, both declared and actually decoded by ffprobe.
- Streams: one video stream, no audio stream.

Command, from brag-output/composition:

```sh
HYPERFRAMES_NO_TELEMETRY=1 npx --yes hyperframes@0.8.74 render --quality looks --fps 30 --format mp4 --output ../pulse-crm-demo-v1.mp4
```

Official `looks` review-quality profile. Render completed in 19 seconds, drawelement capture, hardware GPU. No cloud/HeyGen/paid service, music, voice or SFX.

Validation was performed on the encoded MP4: ffprobe counted 900 decoded frames; FFmpeg decoded the whole file without warnings/errors. A grayscale scan of every frame found zero near-uniform/empty frames, and blackdetect found zero black intervals. Fifteen representative encoded frames, including frames 0 and 899, were extracted and visually reviewed. First frame is valid; final frame preserves the official logo and tagline. No missing images, incorrect scaling, clipped overlays or obvious render-only cursor/transition defect was found in the reviewed samples.

Freezedetect reported low-motion intervals around 0.3–2.4, 8.33–10.7 and the closing hold after 27.4. These correspond to the current composition's brand holds and settled pipeline, not a frozen entire video. Small highlights/cursor movements can fall below the whole-frame detector threshold. No aesthetic changes were made to those authored holds.

No rendering defect required correction or rerender. Composition files, storyboard, captures and demo data were not changed. Render completed from existing commit 8717222.

Evidence: mp4-v1-probe.json, mp4-v1-decode.log, mp4-v1-motion-scan.log, render-v1.log, mp4-v1-frames/contact-sheet.jpg, boundary-01.png and boundary-02.png. Video also opened in the Codex file preview.

Safety: only demo/pulse-video. Main and origin/main remain at 52d29b160f13d5b4636d91f578d30648aa950ba5. No Railway, production frontend/backend, production DB, production environment variables or real Meta services were touched.
