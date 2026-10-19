# Action-by-action help

The public [How To gallery](https://ethansk.github.io/magic-wand/how-to/) has twelve short
illustrated guides. They show the buttons, wand movement and screen result, with ElevenLabs
narration, captions and transcripts. Opus authored the initial storyboards and renderer;
the videos are illustrations, not recordings or proof of physical behaviour.

## Answering “How do I…?”

1. Run `node tutorials/find.mjs "scroll sideways"`, or read the public
   [`tutorials.json`](https://ethansk.github.io/magic-wand/how-to/tutorials.json) index.
2. Match the user's intended action, not just a button name. Return the matching guide's
   `url` and one short instruction. Its `video` URL is the direct MP4.
3. Check the user's selected control version and options when available. These videos show
   Control V2. Review changes and Stage files show the default clockwise/anticlockwise quarter-turns. With
   **Review with nods and shakes** enabled, use the guide's `optionNote`: vertical turns go
   next, horizontal turns go previous. Do not tell that user to use the default circles.
4. If the version or option differs, explain the difference. If the action is not covered,
   answer from current source; do not invent a clip or pass off a different action as the answer.

Ethan's request: “individual actions that the user can ask, how do I do this? And then we
just show the video for that action.” Keep each guide focused on one question.

## Maintaining the videos

`tutorials/tutorials.json` is the authored list. It contains each question, aliases, search
keywords, steps and timed animation actions. Each beat's timing derives from the actual
narration duration. `narration` and `render` blocks are written by their respective tools.

```sh
python3 -m pip install pillow numpy
# Use the existing configured ElevenLabs helper; never put credentials in this repository.
python3 tutorials/narrate.py --session-id "$CODEX_THREAD_ID"
python3 tutorials/render/render.py --workers 2 --scratch /path/to/verified/scratch
python3 scripts/build.py
npm run check
node tutorials/find.mjs "How do I drag?"
```

Run narration from the current Codex task, with `CODEX_THREAD_ID` set and the local voice helper configured. Use an isolated Python environment if the system package manager requires it. The renderer
also needs `ffmpeg` and `ffprobe` on PATH. `--frames /path/to/previews` creates stills without
encoding; a tutorial ID restricts either operation to that guide. Rendering reuses the existing
audio. Narration uses the configured ElevenLabs helper and never plays speech during production.

Final MP4s, posters, captions and transcripts live in `docs/how-to/`; unique narration stays
under `tutorials/narration/`. Large disposable output belongs on verified scratch storage.
Never hand-edit the generated gallery cards, public index, hash records or cache keys.

When controls change, update `wand.json` and the affected storyboard. Checks compare referenced
controls and storyboard fingerprints, narration text, media hashes, captions and transcripts.
They deliberately fail instead of silently publishing a stale video. Re-render the affected
guide, inspect actual encoded frames from every scene, check audio/video streams, then rebuild.
Use real-time offsets (`atS`) for quick taps; stretching tap-to-hold timing to narration length
can teach a gesture the receiver will not recognise. Keep default and optional controls distinct.

Before publication, test gallery search, keyboard focus, opening/closing a player, captions,
direct guide links, narrow layouts and reduced motion in the authorised browser. Record any
blocked checks honestly. Preserve the existing device installation: website work never flashes
the Puck or restarts the receiver, Agentic Mouse or Agent Flow.
