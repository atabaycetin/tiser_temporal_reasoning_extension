from __future__ import annotations

import torch
from tqdm import tqdm


def generate_batch(
    model,
    tokenizer,
    prompts: list[str],
    gen_cfg,
    *,
    temperature: float | None = None,
    top_p: float | None = None,
    num_return_sequences: int = 1,
) -> list[str]:
    """Batched generation. Greedy by default (baseline path).

    The keyword-only 'temperature'/'top_p'/'num_return_sequences' enable
    self-consistency sampling (M1) without changing the default greedy behaviour:
    when 'temperature is None' and 'num_return_sequences == 1', the call is
    byte-identical to the original. With 'num_return_sequences=k', the k samples for
    prompt *i* are returned as the contiguous block 'outputs[i*k : (i+1)*k]'.
    """
    # Wrap each prompt in the SAME chat template used at training time so the model
    # sees the context it was fine-tuned in. 'add_generation_prompt=True' ends the
    # text at the assistant header, exactly where the gold trace began in training.
    wrapped = [
        tokenizer.apply_chat_template(
            [{"role": "user", "content": p}], tokenize=False, add_generation_prompt=True
        )
        for p in prompts
    ]
    sampling = temperature is not None
    do_sample = sampling or gen_cfg.do_sample
    outputs: list[str] = []
    for start in tqdm(range(0, len(wrapped), gen_cfg.batch_size), desc="generate"):
        batch = wrapped[start : start + gen_cfg.batch_size]
        enc = tokenizer(
            batch, return_tensors="pt", padding=True, add_special_tokens=False
        ).to(model.device)

        gen_kwargs = dict(
            max_new_tokens=gen_cfg.max_new_tokens,
            do_sample=do_sample,
            num_return_sequences=num_return_sequences,
            pad_token_id=tokenizer.pad_token_id,
            eos_token_id=tokenizer.eos_token_id,
        )
        if sampling:
            gen_kwargs["temperature"] = temperature
            if top_p is not None:
                gen_kwargs["top_p"] = top_p

        with torch.no_grad():
            generated = model.generate(**enc, **gen_kwargs)

        # Left-padded batch -> the prompt occupies a fixed width; new tokens follow it.
        # With num_return_sequences=k the rows are grouped k-per-input, in input order.
        new_tokens = generated[:, enc["input_ids"].shape[1] :]
        outputs.extend(tokenizer.batch_decode(new_tokens, skip_special_tokens=True))
    return outputs
