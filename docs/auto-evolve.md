# How auto-evolve feels in play

You **just type**. There is no Ctrl+E evolve key.

## While you play

1. **Instant cute feedback** (host, every key): big spaced glyphs, emoji reactions,
   EN + 中文 micro lines (`Nice! / 真棒！`), color bursts on streaks / soft cloud on typos.
2. **Background Soft chat** (every ~5s, and sooner after bursts of keys): Soft
   **multi-proposes** scene candidates (`focus`…`party`) and **select-best** from
   accuracy / rhythm / streak / theme. Soft owns `id` / `hue` / `energy` / style knobs.
3. **Background DeepSeek** (when a DeepSeek key is resolved (env / KEY_FILE / `deepseek.env`; default provider)): multi-proposes scene
   **copy** (title / blurb / ASCII art), style flavor, and bilingual feedback /
   next-line vibe. Host thin **select-best** among candidates (kid-safe filter —
   no gold rewrite of LLM text). Soft params stay locked.
4. **Scene morphs** quietly: sparkle on the art, title/blurb swap, glyph scale
   grows with Soft `glyph_scale`, reaction panel shows Soft/DeepSeek whispers.

## Offline / no key

Soft down or no DeepSeek key → rule-based scene + library art + local emoji feedback.
Play never blocks on the network.

## Modes

| Command | Feel |
|---------|------|
| `make soft` | Soft serve select-best + DeepSeek copy (key optional; default on if key set) |
| `make soft / make deepseek` | Soft oneshot select when available + continuous DeepSeek multi-propose |
| `make offline` | Local rules + cute feedback only |

Env: `TYPEPLAY_EVOLVE_INTERVAL` (seconds, default 5), `TYPEPLAY_MINIMAX_COPY=0` to
disable DeepSeek during `make soft`.

## DeepSeek 生成什么？Soft 选什么？

| 角色 | 做什么 | 你在屏幕哪里看到 |
|------|--------|------------------|
| **Soft** | 根据准确率 / 节奏 / 连击 **多候选选优** 场景 `id`、颜色 `hue`、能量 `energy`、风格旋钮 | 右侧场景徽章「🌿 Soft 场景」；顶栏 `📡 进化来源` |
| **DeepSeek** | 为 Soft 锁定的场景 **写文案**：标题、简介、ASCII/emoji 画、中英鼓励话、下一句味道 | 「🌟 小星星说」条；场景徽章「🎨 AI 画画」；标题/简介/画会换 |
| **本机（无）** | 每个按键的表情反馈、打错时的黄色大字提示 | 粉框表情区；打字区闪烁 `>>> X <<<` |

没有可用 DeepSeek 密钥时：小星星条会提示等待钥匙，场景用内置图库文案（offline）。

## Typing feel

- **打对**：前进一格，绿色字。
- **打错**：不前进；黄色/`>>> 字母 <<<` 大提示「请按这个」；再乱按只刷新可爱 oops（限频），**直到按对**才继续。
- **Backspace**：退一格（撤销一个已对的字）。
- 空格 / Enter 只有目标里真有才需要。

