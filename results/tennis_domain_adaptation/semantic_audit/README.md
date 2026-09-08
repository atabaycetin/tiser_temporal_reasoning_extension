# Tennis Training-Set Semantic Spot-Check

## Result

A targeted AI-assisted review inspected 302 of the 785 training records and
flagged ten records whose gold answer is wrong or not uniquely entailed by the
context. Seven flagged records are inside the reported 600-record training
artifact and three are in the ungenerated tail; none is in the 50-record
pilot. Semantic defects therefore exist, but they cannot explain why the
reported artifact stops at 600.

The detailed decisions are in `semantic_review_findings.json`. They are review
flags pending human adjudication, not silent corrections; the underlying data
and reported results remain unchanged.

## Scope

The union included:

- all 50 pilot IDs;
- up to six evenly spaced examples per category within each of the
  inside/outside-600 groups;
- all 103 `duration_minutes` records;
- all 81 `overlap_while_during` records;
- date/day-risk ordering records; and
- traced outputs containing language suggestive of uncertainty.

After overlaps, this produced 302 unique IDs in training-file order: 193 from
the reported 600 and 109 absent from it (the 50 pilot plus 59 of the 135-item
ungenerated tail). Category coverage was 103 duration, 81 overlap, 54 yes/no,
25 which-first/last, 19 immediate-before/after, 11 other, 8 tournament, and 1
medical-primary record.

The SHA-256 of the reviewed IDs encoded as UTF-8, one ID per line with a final
newline, is:

```text
816cf11d2d12201cec0216f394b4dcd392c4a1dfa0ab201e03dbd8d799697dd1
```

## Reproducing the reviewed set

```python
import hashlib
import json
import re
from collections import defaultdict
from pathlib import Path

train = json.loads(Path("data/tennis/tennis_train.json").read_text())
full_rows = json.loads(Path("data/tennis/tennis_train_traced_full.json").read_text())
full = {row["question_id"] for row in full_rows}
pilot = json.loads(Path("data/tennis/tennis_train_traced_50.json").read_text())
review = {row["question_id"] for row in pilot}

stratified = set()
for status in ("IN", "OUT"):
    groups = defaultdict(list)
    for row in train:
        membership = "IN" if row["question_id"] in full else "OUT"
        if membership == status:
            groups[row["category"]].append(row)
    for items in groups.values():
        n = min(6, len(items))
        indexes = sorted(
            {
                round(k * (len(items) - 1) / (n - 1)) if n > 1 else 0
                for k in range(n)
            }
        )
        stratified.update(items[index]["question_id"] for index in indexes)
review |= stratified

review |= {
    row["question_id"]
    for row in train
    if row["category"] in {"duration_minutes", "overlap_while_during"}
}

days = (
    "morning", "afternoon", "evening", "monday", "tuesday", "wednesday",
    "thursday", "friday", "saturday", "sunday", "same day",
)
for row in train:
    context = row["prompt"].split("Temporal context:\n", 1)[1].split(
        "\n\nQuestion:", 1
    )[0]
    if row["category"] in {
        "yes_no_before_after", "which_first_last", "immediate_before_after"
    } and any(term in context.lower() for term in days):
        review.add(row["question_id"])

doubt = re.compile(
    r"(?i)(strictly speaking|not explicitly|not stated|no elapsed|"
    r"accepting gold|assum|presum|unclear|ambiguous|or maybe|maybe it means|"
    r"both events happen|unless stated)"
)
review |= {
    row["question_id"] for row in full_rows if doubt.search(row["output"])
}

ids = [row["question_id"] for row in train if row["question_id"] in review]
assert len(ids) == 302
digest = hashlib.sha256(("\n".join(ids) + "\n").encode()).hexdigest()
assert digest == "816cf11d2d12201cec0216f394b4dcd392c4a1dfa0ab201e03dbd8d799697dd1"
```

## Interpretation limit

This was a targeted risk-oriented review, not a random sample. The ratio
10/302 must not be reported as a dataset-wide error rate, and the remaining
483 unreviewed records are not certified. The existing schema and trace
validators likewise do not test semantic entailment.
