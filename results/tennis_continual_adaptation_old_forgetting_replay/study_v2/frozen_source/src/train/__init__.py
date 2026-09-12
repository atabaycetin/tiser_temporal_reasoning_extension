from __future__ import annotations

__all__ = ["build_trainer", "run_training"]


def build_trainer(*args, **kwargs):
    from .trainer import build_trainer as implementation
    return implementation(*args, **kwargs)


def run_training(*args, **kwargs):
    from .trainer import run_training as implementation
    return implementation(*args, **kwargs)
