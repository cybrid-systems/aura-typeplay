"""Progressive kids levels — bilingual EN + 中文 hints (ASCII targets for Latin keyboards).

Levels map to Soft scene themes. Typed text stays age-friendly ASCII (English /
pinyin); Chinese is a display hint only (IME-safe for the TUI).
No scary / violent content.
"""

from __future__ import annotations

from dataclasses import dataclass, field


@dataclass(frozen=True)
class Line:
    """One typing target + optional Chinese gloss (not typed)."""

    text: str
    hint_zh: str = ""


@dataclass(frozen=True)
class Level:
    id: str
    title_en: str
    title_zh: str
    theme_scene: str  # Soft scene id this level prefers
    blurb: str
    lines: tuple[Line, ...]


# Progressive ladder: home row → animals → meadow → ocean → space → celebrate
LEVELS: tuple[Level, ...] = (
    Level(
        id="home",
        title_en="Home Row",
        title_zh="基准键",
        theme_scene="focus",
        blurb="Fingers rest on asdf jkl; — slow and steady",
        lines=(
            Line("asdf", "基准键左边"),
            Line("jkl;", "基准键右边"),
            Line("asdf jkl;", "左右一起"),
            Line("aaa sss ddd", "重复练习"),
            Line("fff jjj", "食指回家"),
            Line("all fall", "小词"),
            Line("salad", "沙拉"),
            Line("flask", "小瓶"),
            Line("dad sad", "爸爸难过？不，练习！"),
            Line("ask dad", "问爸爸"),
        ),
    ),
    Level(
        id="animals",
        title_en="Friendly Animals",
        title_zh="可爱动物",
        theme_scene="forest",
        blurb="Meet kind forest friends",
        lines=(
            Line("cat", "猫"),
            Line("dog", "狗"),
            Line("bird", "鸟"),
            Line("bunny", "兔子"),
            Line("fox", "狐狸"),
            Line("a soft cat", "软软的猫"),
            Line("happy dog", "开心的狗"),
            Line("little bird", "小鸟"),
            Line("bunny hops", "兔子跳跳"),
            Line("fox peeks", "狐狸偷看"),
            Line("mao is cat", "猫 mao"),
            Line("gou is dog", "狗 gou"),
        ),
    ),
    Level(
        id="meadow",
        title_en="Sunny Meadow",
        title_zh="阳光草地",
        theme_scene="meadow",
        blurb="Sun, flowers, and kind colors",
        lines=(
            Line("sun", "太阳"),
            Line("flower", "花"),
            Line("bee", "蜜蜂"),
            Line("green grass", "绿草"),
            Line("yellow sun", "黄太阳"),
            Line("soft wind", "软风"),
            Line("i see a bee", "我看见蜜蜂"),
            Line("flowers smile", "花在笑"),
            Line("tai yang", "太阳 pinyin"),
            Line("hua duo", "花朵 pinyin"),
            Line("red blue green", "红蓝绿"),
            Line("be kind today", "今天要善良"),
        ),
    ),
    Level(
        id="ocean",
        title_en="Calm Ocean",
        title_zh="平静大海",
        theme_scene="ocean",
        blurb="Waves, fish, and gentle swimming",
        lines=(
            Line("fish", "鱼"),
            Line("wave", "波浪"),
            Line("boat", "小船"),
            Line("blue sea", "蓝海"),
            Line("soft wave", "轻柔的浪"),
            Line("happy fish", "开心的鱼"),
            Line("dolphin swims", "海豚游泳"),
            Line("cloud and sea", "云和海"),
            Line("yu is fish", "鱼 yu"),
            Line("hai shui", "海水 pinyin"),
            Line("we float slow", "我们慢慢漂"),
            Line("calm blue day", "平静的蓝天"),
        ),
    ),
    Level(
        id="space",
        title_en="Star Garden",
        title_zh="星星花园",
        theme_scene="space",
        blurb="Moon, stars, and friendly rockets",
        lines=(
            Line("star", "星星"),
            Line("moon", "月亮"),
            Line("rocket", "火箭"),
            Line("bright star", "亮晶晶的星"),
            Line("soft moon", "软软的月亮"),
            Line("i love stars", "我爱星星"),
            Line("rocket flies", "火箭飞呀飞"),
            Line("planet smile", "行星微笑"),
            Line("xing xing", "星星 pinyin"),
            Line("yue liang", "月亮 pinyin"),
            Line("space is big", "太空好大"),
            Line("count the stars", "数一数星星"),
        ),
    ),
    Level(
        id="celebrate",
        title_en="Streak Party",
        title_zh="连击派对",
        theme_scene="party",
        blurb="Longer kind phrases — you earned it!",
        lines=(
            Line("you did great", "你真棒"),
            Line("keep the streak", "保持连击"),
            Line("fingers dance", "手指跳舞"),
            Line("type with care", "认真打字"),
            Line("friends help friends", "朋友帮朋友"),
            Line("music and typing", "音乐和打字"),
            Line("ni zhen bang", "你真棒 pinyin"),
            Line("we learn together", "我们一起学"),
            Line("smile and try again", "笑一笑再试"),
            Line("practice every day", "每天练习"),
            Line("soft colors make me smile", "柔和颜色让我笑"),
            Line("thank you for playing", "谢谢你来玩"),
        ),
    ),
)

# Soft scene id → preferred level id (hint only; host may sync)
SCENE_TO_LEVEL: dict[str, str] = {
    "focus": "home",
    "forest": "animals",
    "meadow": "meadow",
    "ocean": "ocean",
    "space": "space",
    "party": "celebrate",
}

# Lines completed at ≥ this accuracy promote progress within a level
LINE_OK_ACCURACY = 0.85
# Perfect-ish lines needed to unlock next level
LINES_TO_ADVANCE = 3


def level_by_id(level_id: str) -> Level | None:
    for lv in LEVELS:
        if lv.id == level_id:
            return lv
    return None


def level_index(level_id: str) -> int:
    for i, lv in enumerate(LEVELS):
        if lv.id == level_id:
            return i
    return 0


@dataclass
class LevelProgress:
    """Tracks current level and line; advances on accuracy streak of completed lines.

    Optional ``llm_queue``: DeepSeek-proposed kid-safe targets (ASCII). When
    non-empty, typing pulls from the queue first; Soft mutate still owns scene
    AST — the queue is host-only words, never writes ``.aura``.
    """

    level_idx: int = 0
    line_idx: int = 0
    ok_lines: int = 0  # consecutive good completions in this level
    total_completed: int = 0
    last_line_accuracy: float = 1.0
    llm_queue: list[Line] = field(default_factory=list)
    llm_source: str = ""  # e.g. deepseek / empty = library

    @property
    def level(self) -> Level:
        return LEVELS[self.level_idx % len(LEVELS)]

    @property
    def using_llm_targets(self) -> bool:
        return bool(self.llm_queue)

    def current_line(self) -> Line:
        if self.llm_queue:
            return self.llm_queue[0]
        lines = self.level.lines
        return lines[self.line_idx % len(lines)]

    def target_text(self) -> str:
        return self.current_line().text

    def hint_zh(self) -> str:
        return self.current_line().hint_zh

    def offer_llm_targets(
        self,
        items: list[dict] | list[Line],
        *,
        source: str = "deepseek",
        replace: bool = True,
    ) -> int:
        """Accept already-filtered targets into the queue. Returns count kept."""
        lines: list[Line] = []
        for it in items or []:
            if isinstance(it, Line):
                lines.append(it)
                continue
            if not isinstance(it, dict):
                continue
            text = str(it.get("text") or it.get("target") or "").strip()
            hint = str(it.get("hint_zh") or it.get("hint") or "").strip()
            if text:
                lines.append(Line(text=text, hint_zh=hint))
        if not lines:
            return 0
        if replace:
            self.llm_queue = lines
        else:
            self.llm_queue.extend(lines)
        self.llm_source = source
        return len(lines)

    def clear_llm_targets(self) -> None:
        self.llm_queue.clear()
        self.llm_source = ""

    def status(self) -> dict:
        lv = self.level
        return {
            "level_id": lv.id,
            "level_idx": self.level_idx,
            "level_title_en": lv.title_en,
            "level_title_zh": lv.title_zh,
            "theme_scene": lv.theme_scene,
            "line_idx": self.line_idx,
            "ok_lines": self.ok_lines,
            "lines_to_advance": LINES_TO_ADVANCE,
            "total_completed": self.total_completed,
            "hint_zh": self.hint_zh(),
            "target_source": self.llm_source if self.llm_queue else "library",
            "llm_queue_len": len(self.llm_queue),
        }

    def _advance_cursor(self) -> None:
        """Consume current target (LLM queue or library index)."""
        if self.llm_queue:
            self.llm_queue.pop(0)
            if not self.llm_queue:
                self.llm_source = ""
            return
        self.line_idx = (self.line_idx + 1) % len(self.level.lines)

    def complete_line(self, line_accuracy: float) -> dict:
        """Finish current line; maybe advance level. Returns event dict."""
        self.total_completed += 1
        self.last_line_accuracy = line_accuracy
        advanced = False
        prev_id = self.level.id
        if line_accuracy >= LINE_OK_ACCURACY:
            self.ok_lines += 1
        else:
            self.ok_lines = 0
        self._advance_cursor()
        if self.ok_lines >= LINES_TO_ADVANCE and self.level_idx < len(LEVELS) - 1:
            self.level_idx += 1
            self.line_idx = 0
            self.ok_lines = 0
            self.clear_llm_targets()  # new level → wait for fresh DeepSeek words
            advanced = True
        return {
            "advanced": advanced,
            "from_level": prev_id,
            "to_level": self.level.id,
            "line_accuracy": line_accuracy,
            **self.status(),
        }

    def skip_line(self) -> None:
        """Skip without counting as ok (breaks ok streak)."""
        self.ok_lines = 0
        self._advance_cursor()

    def hint_from_scene(self, scene_id: str) -> bool:
        """If Soft scene suggests a higher/matching theme, gently sync level.

        Only moves forward (never demotes). Returns True if level changed.
        """
        want_id = SCENE_TO_LEVEL.get(scene_id)
        if not want_id:
            return False
        want_idx = level_index(want_id)
        if want_idx > self.level_idx:
            self.level_idx = want_idx
            self.line_idx = 0
            self.ok_lines = 0
            self.clear_llm_targets()
            return True
        return False


# Back-compat for anything still importing next_line
def next_line(index: int) -> str:
    flat = [ln.text for lv in LEVELS for ln in lv.lines]
    return flat[index % len(flat)]
