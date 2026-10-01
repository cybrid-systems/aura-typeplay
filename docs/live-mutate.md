# Soft live-mutate (Aura-native)

Product brain is **Soft**, not Python scene swap.

## What happens each observe tick

1. Host writes typing signals → `observe.json` (thin I/O).
2. Persistent `aura --serve` runs `run-typeplay-live-tick`:
   - **6 fiber worldlines** each `mutate:rebind` a distinct `cand-*` AST slot
     (Unique / MutationBoundary Guard — Soft warn on join is expected).
   - Soft **select-best** by accuracy / rhythm / streak / theme.
   - Winner **lands** into live `scene-id` / `scene-hue` / `scene-energy` /
     `scene-title` / `feedback-*` / `burst` / `glyph-scale` via more
     `mutate:rebind` + `eval-current`.
   - Soft writes `scene.json` with `soft_mutate=true`, `compile_epoch`,
     `live_tick`, `select=fiber-select-best`.
3. Host TUI **displays** Soft landing: morph sparkles, **epoch/tick** badge,
   Soft feedback until MiniMax overlays copy.

## What the player sees

| UI | Soft AST live? |
|----|----------------|
| Scene badge `🧬 Soft live-mutate AST epoch=N tick=M` | Yes — epoch climbs as Soft mutates |
| Top bar Soft epoch/tick | Same |
| Title / hue / energy / Soft 中文鼓励 | Soft-landed attributes |
| Morph counter bumps | When Soft epoch or art/id changes |

Offline Soft-down: badge idle; host shows library art honestly as
`offline(soft_down)` — not pretending Soft mutated.

## MiniMax connectivity chip（小星星说）

| Chip | Meaning |
|------|---------|
| `MiniMax 未接 KEY` | No key via env / KEY_FILE / aura-build `minimax.env` — Soft still mutates |
| `MiniMax probing…` | API call in flight |
| `MiniMax OK Nms #hash` | Propose succeeded; 「小星星说」refreshed |
| `MiniMax FAIL (…)` | API/filter fail — Soft AST still live; missing KEY_FILE → `密钥文件不存在`; `401` → `密钥无效` |

MiniMax only proposes **copy** (title/blurb/art/cheers). Soft owns mutate.

```bash
export AURA_BIN=/workspace/aura-grok/build/aura
make soft
# optional copy — export KEY, or share ~/.config/aura-build/minimax.env
```
