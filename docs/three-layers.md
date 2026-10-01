# Three-layer note

## 1. Soft runtime

- Binary **only**: `AURA_BIN=/workspace/aura-grok/build/aura` (ld-linux shim over aura.real + image_libs)
- Owns: `query:*` observe faces, `--serve` / oneshot eval, scene evolve in `aura/*.aura`
- Soft observe ≠ Hard — counter guidance is not proof

## 2. This product

- Kids typing UX: Textual host, lines, ANSI scenes
- Thin bridge: `host/soft_bridge.py` starts Soft serve, writes observe.json, reads scene.json
- Offline / DeepSeek copy+words when Soft down; Soft alone mutates `.aura`

## 3. No Soft language hacks

- Do not invent soft_* helpers; Soft gaps → Aura issues (one symbol)
- Prefer Soft-native `std/io`, `json-parse` / `json-encode`, `engine:metrics`
