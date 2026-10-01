# Three-layer note

aura-typeplay sits on Soft without becoming Soft.

## 1. Soft runtime

- Binary: `AURA_BIN=/workspace/aura-grok/build/aura` (comment / later wire-up)
- Owns: observe fitness, mutate candidates, select-best, honesty (`incr_proven` / `fiber_live` never faked)
- Product brains live in Soft / aura-build — **do not fork them here**

## 2. This product

- Kids typing UX: target line, keystrokes, live accuracy / WPM / streak
- Textual host + ANSI/emoji scene panel
- Offline rule-based scene swap and thin MiniMax propose client
- Stubs under `aura/*.aura` document sockets Soft will serve

## 3. No Soft language hacks

- Do not invent Soft string/list helpers (`soft_*`) in this repo
- When Soft gold-binds a primitive, prefer Soft-native — defense-in-depth only if Soft asks
- Host Python stays thin: I/O, TUI, env keys, JSON sockets

```
 Soft runtime          this product           forbid
 ┌─────────────┐      ┌──────────────┐      ┌──────────────────┐
 │ aura binary │◄────►│ Textual host │      │ Soft lang hacks  │
 │ select-best │ sock │ scenes/UX    │      │ gold scene fixes │
 └─────────────┘      └──────────────┘      └──────────────────┘
```
