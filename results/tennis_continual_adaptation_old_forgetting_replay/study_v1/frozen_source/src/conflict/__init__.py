"""Context-memory conflict probe (extension E6).

Inference-only behavioural probe over the frozen TISER baseline: feed a
counterfactual context that contradicts the model's parametric memory and
measure context-faithfulness and whether <reflection> notices the conflict.

Pipeline modules (see config/conflict.yaml and the experiment plan):
  M0 subset.py       - parse in-scope records, structure-parse context, tag classes
  M1 memory.py       - closed-book parametric-belief elicitation (self-consistency)
  M2 eligibility.py  - strict eligibility filter + GO/NO-GO yield gate
"""
