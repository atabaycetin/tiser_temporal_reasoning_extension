"""Deterministic fixed-budget schedules and actual consumed-token accounting."""
from __future__ import annotations

import random
from dataclasses import dataclass, field


def schedule_batches(n, batch_size, count, seed=42):
    if min(n, batch_size) < 1 or count < 0:
        raise ValueError("Invalid schedule dimensions")
    rng, pool, index = random.Random(seed), [], 0
    for _ in range(count):
        batch = []
        for _ in range(batch_size):
            if index == len(pool):
                pool = list(range(n))
                rng.shuffle(pool)
                index = 0
            batch.append(pool[index])
            index += 1
        yield batch


def planned_exposure(metadata, steps, batch_size=4, accumulation=4, seed=42):
    counter = Exposure()
    for index, batch in enumerate(schedule_batches(len(metadata), batch_size, steps * accumulation, seed), 1):
        counter.observe([metadata[i]["input_tokens"] for i in batch],
                        [metadata[i]["supervised_tokens"] for i in batch])
        if index % accumulation == 0:
            counter.update(index // accumulation)
    return counter.to_dict()


def closest_token_steps(metadata, target, batch_size=4, accumulation=4, seed=42):
    if target <= 0 or not metadata or any(r["supervised_tokens"] <= 0 for r in metadata):
        raise ValueError("Token target and training target lengths must be positive")
    # An upper bound using the shortest example; only iterate until crossing.
    maximum = target // (min(r["supervised_tokens"] for r in metadata) * batch_size * accumulation) + 2
    total, previous = 0, 0
    for i, batch in enumerate(schedule_batches(len(metadata), batch_size, maximum * accumulation, seed), 1):
        total += sum(metadata[j]["supervised_tokens"] for j in batch)
        if i % accumulation == 0:
            step = i // accumulation
            if total >= target:
                use_previous = step > 1 and target - previous <= total - target
                chosen, actual = (step - 1, previous) if use_previous else (step, total)
                return {"max_steps": chosen, "target_supervised_tokens": target,
                        "planned_supervised_tokens": actual, "residual_tokens": actual - target,
                        "relative_residual": (actual - target) / target}
            previous = total
    raise RuntimeError("Token schedule did not reach target")


@dataclass
class Exposure:
    examples: int = 0
    input_tokens: int = 0
    supervised_tokens: int = 0
    microbatches: int = 0
    updates: list = field(default_factory=list)

    def observe(self, input_lengths, supervised_lengths):
        if len(input_lengths) != len(supervised_lengths) or any(s < 0 or s > n for n, s in zip(input_lengths, supervised_lengths)):
            raise ValueError("Invalid token counts")
        self.examples += len(input_lengths)
        self.input_tokens += sum(input_lengths)
        self.supervised_tokens += sum(supervised_lengths)
        self.microbatches += 1

    def update(self, step):
        if step != len(self.updates) + 1:
            raise ValueError("Optimizer-step sequence differs from exposure ledger")
        self.updates.append({"step": step, "examples": self.examples, "input_tokens": self.input_tokens,
                             "supervised_tokens": self.supervised_tokens, "microbatches": self.microbatches})

    def to_dict(self):
        return {"examples": self.examples, "input_tokens": self.input_tokens,
                "supervised_tokens": self.supervised_tokens, "microbatches": self.microbatches,
                "optimizer_steps": len(self.updates), "updates": self.updates}

    @classmethod
    def restore(cls, value, step):
        if value["optimizer_steps"] != step or len(value["updates"]) != step:
            raise ValueError("Checkpoint/exposure optimizer-step mismatch")
        result = cls(**{k: value[k] for k in ("examples", "input_tokens", "supervised_tokens", "microbatches", "updates")})
        if step and any(value[k] != value["updates"][-1][k] for k in ("examples", "input_tokens", "supervised_tokens", "microbatches")):
            raise ValueError("Checkpoint token totals differ from last completed update")
        return result
