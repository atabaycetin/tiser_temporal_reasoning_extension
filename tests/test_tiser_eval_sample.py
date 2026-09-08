from scripts.tennis.build_tiser_eval_sample import build_complement, sample_records


def _rows() -> list[dict]:
    return [
        {
            "dataset_name": split,
            "question_id": f"{split}-{index}",
            "question": f"Question {split} {index}?",
            "prompt": f"Prompt {split} {index}",
            "answer": str(index),
        }
        for split in ("split_a", "split_b")
        for index in range(4)
    ]


def test_sample_and_complement_are_complete_disjoint_evaluator_records() -> None:
    rows = _rows()
    sampled, summary = sample_records(rows, per_split=2, seed=42)
    complement = build_complement(rows, sampled)

    required = {"dataset_name", "question_id", "question", "prompt", "answer"}
    assert len(sampled) == 4
    assert len(complement) == 4
    assert summary["fields"] == [
        "prompt",
        "question",
        "answer",
        "dataset_name",
        "question_id",
    ]
    assert all(required <= set(row) for row in sampled + complement)

    sampled_ids = {(row["dataset_name"], row["question_id"]) for row in sampled}
    complement_ids = {
        (row["dataset_name"], row["question_id"]) for row in complement
    }
    source_ids = {(row["dataset_name"], row["question_id"]) for row in rows}
    assert sampled_ids.isdisjoint(complement_ids)
    assert sampled_ids | complement_ids == source_ids

