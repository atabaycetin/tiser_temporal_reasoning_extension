"""M4 - build run-input prompts per style (CPU).

Two prompt styles inject the perturbed context c' (M3) for the run matrix:

  tiser    - the verbatim 4-tag TISER prompt: take the item's own closed-book prompt
             (real preamble + question + '### Answer:', context removed in M0) and inject
             c' before '### Answer:' (context_parse.inject_context). Byte-identical preamble
             to training -> the #1 baseline-reproduction guard.
  standard - a plain direct-answer prompt with no 4-tag instruction (D-STD, the H1 baseline
             arm). Template is config-driven (conflict.prompts.standard_template), wording
             OPEN to match the TISER paper's baseline framing.

Only validity_ok conflict rows are emitted. Each row carries (id, conflict_type, style,
prompt) so M5/M6 join back on (id, conflict_type). The chat-template wrap (apply_chat_template)
is applied identically for both styles downstream in M5 - M4 emits only the raw prompt body.

Output: 'outputs/conflict/run_inputs/<style>.jsonl' (+ 'run_inputs_report.json', 'run_meta.json').
"""

from __future__ import annotations

import os

from src.conflict.context_parse import inject_context
from src.conflict.io import read_jsonl, stage_dir, write_jsonl, write_run_meta
from src.utils.io import write_json


def build_tiser_prompt(prompt_no_context: str, ctx_prime: str) -> str:
    """Inject c' into the verbatim 4-tag closed-book prompt."""
    return inject_context(prompt_no_context, ctx_prime)


def build_standard_prompt(q: str, ctx_prime: str, template: str) -> str:
    """Render the plain direct-answer prompt (D-STD) from the config template."""
    return template.format(q=q, ctx=ctx_prime)


def build_run_inputs(cfg) -> dict:
    pcfg = cfg.conflict.prompts
    styles = list(pcfg.styles)

    conflicts = read_jsonl(os.path.join(stage_dir(cfg, "conflicts"), "conflict_set.jsonl"))
    valid = [r for r in conflicts if r.get("validity_ok")]

    # The tiser style needs each item's closed-book prompt, which lives on the eligible set.
    eligible = read_jsonl(os.path.join(stage_dir(cfg, "eligible"), "eligible.jsonl"))
    pnc = {it["id"]: it["prompt_no_context"] for it in eligible}

    out_dir = stage_dir(cfg, "run_inputs")
    counts: dict[str, int] = {}
    for style in styles:
        rows: list[dict] = []
        for r in valid:
            if style == "tiser":
                if r["id"] not in pnc:
                    continue  # no closed-book prompt to wrap (should not happen post-join)
                prompt = build_tiser_prompt(pnc[r["id"]], r["ctx_prime"])
            elif style == "standard":
                prompt = build_standard_prompt(r["q"], r["ctx_prime"], pcfg.standard_template)
            else:
                raise ValueError(f"unknown prompt style {style!r}")
            rows.append({"id": r["id"], "conflict_type": r["conflict_type"],
                         "style": style, "prompt": prompt})
        write_jsonl(os.path.join(out_dir, f"{style}.jsonl"), rows)
        counts[style] = len(rows)

    report = {"styles": styles, "n_valid_conflicts": len(valid), "per_style": counts}
    write_json(os.path.join(out_dir, "run_inputs_report.json"), report)
    write_run_meta(out_dir, cfg, extra={"styles": styles})

    print(f"[M4] built run inputs for styles {styles}: {counts} -> {out_dir}")
    return report
