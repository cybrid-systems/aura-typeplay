#!/usr/bin/env python3
"""Back-compat: run smoke_llm_copy."""
from __future__ import annotations
import runpy
from pathlib import Path
p = Path(__file__).with_name("smoke_llm_copy.py")
ns = runpy.run_path(str(p))
raise SystemExit(ns["main"]())
