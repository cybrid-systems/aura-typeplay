"""ANSI/emoji scene panel — evolves from Soft/host params (no gold hardcoded fixes)."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class Scene:
    id: str
    title: str
    art: str
    # evolve params Soft/host may mutate
    hue: str = "cyan"
    energy: float = 0.5  # 0..1


# Base scene library — rule-based offline picker selects among these.
# MiniMax proposes new Scene dicts; Soft/host selects — never gold-fix patches.
SCENES: dict[str, Scene] = {
    "meadow": Scene(
        id="meadow",
        title="Sunny Meadow",
        hue="green",
        energy=0.4,
        art="""
   \\|/  ☀️
  --🌻--
   /|\\   🐝
  ~~~~🌿~~~~
  bunny 🐰 hops
""",
    ),
    "ocean": Scene(
        id="ocean",
        title="Calm Ocean",
        hue="blue",
        energy=0.35,
        art="""
     ☁️    ☁️
  ~~~~🌊~~~~🌊~~
   🐠    🐡
  ~~~~🐙~~~~~~~~
   dolphin 🐬
""",
    ),
    "space": Scene(
        id="space",
        title="Star Garden",
        hue="magenta",
        energy=0.7,
        art="""
   ✦  🚀  ✧
  ★   🪐   ★
   ✧  🌕  ✦
  comet ☄️ trails
""",
    ),
    "forest": Scene(
        id="forest",
        title="Quiet Forest",
        hue="green",
        energy=0.3,
        art="""
    🌲  🦉  🌲
   🌲🌲   🌲🌲
  fox 🦊 peeks
   🍄  🐛  🍄
""",
    ),
    "party": Scene(
        id="party",
        title="Streak Party!",
        hue="yellow",
        energy=0.95,
        art="""
  🎉 ✨ 🎊 ✨ 🎉
   YOU DID IT!
  🎈 🏆 🎈
  keep the streak!
""",
    ),
    "focus": Scene(
        id="focus",
        title="Focus Cave",
        hue="white",
        energy=0.2,
        art="""
   ┌─────────┐
   │  ·  ·   │
   │ slow &  │
   │ steady  │
   └─────────┘
""",
    ),
}


def rule_based_scene(signals: dict) -> Scene:
    """Offline evolve: map accuracy/rhythm/streak → scene (local metrics→scene)."""
    acc = float(signals.get("accuracy", 1.0))
    streak = int(signals.get("streak", 0))
    rhythm_cv = float(signals.get("rhythm_cv", 0.0))
    wpm = float(signals.get("wpm", 0.0))

    if streak >= 20:
        return SCENES["party"]
    if acc < 0.7:
        return SCENES["focus"]
    if rhythm_cv > 0.8 and acc >= 0.85:
        return SCENES["ocean"]  # calm the jagged rhythm
    if wpm >= 25 and acc >= 0.9:
        return SCENES["space"]
    if acc >= 0.95 and streak >= 10:
        return SCENES["meadow"]
    return SCENES["forest"]


def scene_from_proposal(data: dict) -> Scene | None:
    """Accept MiniMax/Soft proposal dict → Scene (host selects; no hardcoded gold)."""
    try:
        sid = str(data.get("id") or data.get("scene_id") or "custom")
        title = str(data.get("title") or sid)
        art = str(data.get("art") or "")
        if not art.strip():
            return None
        hue = str(data.get("hue") or "cyan")
        energy = float(data.get("energy", 0.5))
        return Scene(id=sid, title=title, art=art, hue=hue, energy=energy)
    except (TypeError, ValueError):
        return None


def apply_soft_scene(data: dict | None, signals: dict) -> tuple[Scene, str] | None:
    """Map Soft scene.json → host Scene. None → caller uses offline fallback."""
    if not data or not isinstance(data, dict):
        return None
    if data.get("source") not in ("soft", "soft-probe"):
        # still accept if Soft wrote id we know
        if not data.get("id"):
            return None
    sid = str(data.get("id") or "")
    if sid in SCENES:
        base = SCENES[sid]
        hue = str(data.get("hue") or base.hue)
        try:
            energy = float(data.get("energy", base.energy))
        except (TypeError, ValueError):
            energy = base.energy
        title = str(data.get("title") or base.title)
        return Scene(id=sid, title=title, art=base.art, hue=hue, energy=energy), "soft"
    # custom Soft/MiniMax art payload
    custom = scene_from_proposal(data)
    if custom:
        return custom, "soft"
    return None
