from __future__ import annotations

__all__ = ["run_eval"]


def run_eval(*args, **kwargs):
    """Lazily dispatch to the canonical evaluator.

    Keeping package import lightweight lets the dedicated vLLM environment import
    evaluation metrics without requiring the PEFT/TRL training stack.
    """
    from .run_eval import run_eval as _run_eval

    return _run_eval(*args, **kwargs)
