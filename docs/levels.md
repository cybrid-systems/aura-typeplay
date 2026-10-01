# Kids levels (bilingual)

Typed targets are **ASCII** (English + pinyin) so Latin keyboards work without IME.
Chinese appears as a **hint** only (`中文 …`).

| # | id | Theme (Soft scene) | Content |
|---|-----|--------------------|---------|
| 1 | `home` | `focus` | Home row `asdf jkl;` |
| 2 | `animals` | `forest` | Friendly animals + pinyin (`mao`/`gou`) |
| 3 | `meadow` | `meadow` | Sun, flowers, kind colors |
| 4 | `ocean` | `ocean` | Calm sea, fish, dolphin |
| 5 | `space` | `space` | Stars, moon, rocket |
| 6 | `celebrate` | `party` | Longer kind phrases |

## Advance rules

- Complete a line with **line accuracy ≥ 0.85** → counts toward unlock
- **3** good lines in a row (ok streak) → unlock next level
- Skip (`Ctrl+N`) resets the ok streak (does not demote)
- Soft/MiniMax scene id can **hint forward** to a matching theme (never demotes)

## Soft

`observe.json` includes `level_id`, `level_idx`, `theme_scene`. Soft prefers
`theme_scene` when accuracy is healthy (Soft observe ≠ Hard).

## DeepSeek target words

When DeepSeek is OK, it proposes kid-safe ASCII targets for the current level/theme.
The host queues them for typing (kid-safe filter only — no gold rewrite).
If DeepSeek is down or the queue is empty, the built-in level lists above are used.
Soft mutate does **not** come from these words.
