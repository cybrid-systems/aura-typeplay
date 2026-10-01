# How auto-evolve feels in play

You **just type**. There is no Ctrl+E evolve key.

## While you play

1. **Instant cute feedback** (host, every key): big spaced glyphs, emoji reactions,
   EN + 中文 micro lines (`Nice! / 真棒！`), color bursts on streaks / soft cloud on typos.
2. **Background Soft chat** (every ~5s, and sooner after bursts of keys): Soft
   **multi-proposes** scene candidates (`focus`…`party`) and **select-best** from
   accuracy / rhythm / streak / theme. Soft owns `id` / `hue` / `energy` / style knobs.
3. **Background MiniMax** (when `MINIMAX_API_KEY` is set): multi-proposes scene
   **copy** (title / blurb / ASCII art), style flavor, and bilingual feedback /
   next-line vibe. Host thin **select-best** among candidates (kid-safe filter —
   no gold rewrite of LLM text). Soft params stay locked.
4. **Scene morphs** quietly: sparkle on the art, title/blurb swap, glyph scale
   grows with Soft `glyph_scale`, reaction panel shows Soft/MiniMax whispers.

## Offline / no key

Soft down or no MiniMax key → rule-based scene + library art + local emoji feedback.
Play never blocks on the network.

## Modes

| Command | Feel |
|---------|------|
| `make soft` | Soft serve select-best + MiniMax copy (key optional; default on if key set) |
| `make minimax` | Soft oneshot select when available + continuous MiniMax multi-propose |
| `make offline` | Local rules + cute feedback only |

Env: `TYPEPLAY_EVOLVE_INTERVAL` (seconds, default 5), `TYPEPLAY_MINIMAX_COPY=0` to
disable MiniMax during `make soft`.
