"""Back-compat shim — scene copy lives in ``host.llm_copy``.

Default provider is DeepSeek Flash. ``TYPEPLAY_LLM=minimax`` (or
``TYPEPLAY_MODE=minimax``) selects MiniMax.
"""

from __future__ import annotations

from host.llm_copy import (  # noqa: F401
    DEEPSEEK,
    MINIMAX,
    LlmResolved,
    _HINT_KEY_INVALID,
    _HINT_KEY_MISSING_FILE,
    _HTTP_401_HINT,
    _friendly_http_error,
    _sanitize_api_key,
    active_provider,
    apply_copy,
    continuous_enrich,
    has_api_key,
    kid_safe_copy,
    kid_safe_hit,
    propose_copy,
    propose_copy_multi,
    provider_label,
    provider_spec,
    resolve_api_key,
    resolve_base_and_model,
    resolve_deepseek,
    resolve_llm,
    resolve_minimax,
    rule_based_copy,
    select_best_copy,
    select_copy,
)

# Older name used in some docs / smoke
MiniMaxResolved = LlmResolved
