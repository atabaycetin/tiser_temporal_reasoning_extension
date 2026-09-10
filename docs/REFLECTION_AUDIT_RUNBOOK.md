# Reflection Audit: Follow These Steps Exactly

This audit uses two primary Codex tasks. Judge A processes all 2,295 reflections
in one task. Judge B independently processes the same 2,295 reflections in a
second task. You do not need an API key, Colab, or 92 separate tasks.

## Step 1: prepare the files

Open Terminal and run exactly:

```bash
cd "/Users/atabay/Desktop/Folders/Documents n Stuff/Polito/DNLP/Project/tiser_temporal_reasoning_extension"
python3 scripts/audit.py prepare \
  --kind reflection \
  --output-dir results/reflection_audit \
  --requested-model gpt-5.6-sol
```

This command only prepares files. It does not run a judge.

Check that no judgments have been imported:

```bash
cat results/reflection_audit/progress.json
```

Before Judge A, `primary_completed` must be `0`.

## Step 2: run Judge A

1. In the Codex desktop app, create a new **projectless task**.
2. Select **GPT-5.6 Sol**.
3. Select **high** reasoning.
4. Attach this one file:

   ```text
   /Users/atabay/Desktop/Folders/Documents n Stuff/Polito/DNLP/Project/tiser_temporal_reasoning_extension/results/reflection_audit/task_bundles/reflection-judge_a-primary.json
   ```

5. Open this file on your Mac:

   ```text
   /Users/atabay/Desktop/Folders/Documents n Stuff/Polito/DNLP/Project/tiser_temporal_reasoning_extension/results/reflection_audit/task_bundles/JUDGE_PROMPT.txt
   ```

6. Copy the entire contents of `JUDGE_PROMPT.txt`.
7. Paste the copied text into the Judge A task and send it.
8. Wait until the task reports that it created all 46 response files and gives
   you the absolute path of the response directory.
9. Copy that absolute directory path.

If the task stops before producing all 46 files, send this message in the same
Judge A task:

```text
Continue from the next unfinished batch. Preserve the completed response files and finish all remaining batches. Then verify that the response directory contains 46 JSON files and give me its absolute path.
```

Do not attach any Judge B file to the Judge A task.

## Step 3: import Judge A

In Terminal, run the following command. Replace
`/ABSOLUTE/PATH/REPORTED/BY/JUDGE_A` with the directory path copied in step 2:

```bash
cd "/Users/atabay/Desktop/Folders/Documents n Stuff/Polito/DNLP/Project/tiser_temporal_reasoning_extension"
python3 scripts/audit.py import \
  --output-dir results/reflection_audit \
  --response "/ABSOLUTE/PATH/REPORTED/BY/JUDGE_A" \
  --task-id "reflection-judge-a"
```

The output must show:

```text
"files": 46
"accepted": 2295
"errors": []
```

Then run:

```bash
cat results/reflection_audit/progress.json
```

`primary_completed` must be `2295`.

If the import reports an error, do not edit the response manually. Give the
error to the same Judge A task, ask it to replace only the invalid response
file, and run the same import command again.

## Step 4: run Judge B

1. Create another new **projectless task**. Do not reuse the Judge A task.
2. Select **GPT-5.6 Sol**.
3. Select **high** reasoning.
4. Attach this one file:

   ```text
   /Users/atabay/Desktop/Folders/Documents n Stuff/Polito/DNLP/Project/tiser_temporal_reasoning_extension/results/reflection_audit/task_bundles/reflection-judge_b-primary.json
   ```

5. Copy the entire contents of the same `JUDGE_PROMPT.txt` used for Judge A.
6. Paste the text into the Judge B task and send it.
7. Wait until the task reports 46 response files and gives their directory's
   absolute path.
8. Copy that path.

Do not give Judge B any Judge A file, response, result, or conversation.

If Judge B stops early, use the same continuation message from step 2 in the
same Judge B task.

## Step 5: import Judge B

Replace `/ABSOLUTE/PATH/REPORTED/BY/JUDGE_B` below:

```bash
cd "/Users/atabay/Desktop/Folders/Documents n Stuff/Polito/DNLP/Project/tiser_temporal_reasoning_extension"
python3 scripts/audit.py import \
  --output-dir results/reflection_audit \
  --response "/ABSOLUTE/PATH/REPORTED/BY/JUDGE_B" \
  --task-id "reflection-judge-b"
```

The output must show `files: 46`, `accepted: 2295`, and `errors: []`.

Run:

```bash
cat results/reflection_audit/progress.json
```

`primary_completed` must be `4590`.

## Step 6: adjudicate disagreements

Run:

```bash
python3 scripts/audit.py adjudicate \
  --output-dir results/reflection_audit
find results/reflection_audit/task_bundles \
  -type f -name 'reflection-adjudicator-pending-*.json' | sort
```

If the `find` command prints nothing, continue to step 7.

If it prints a bundle path:

1. Create one new projectless GPT-5.6 Sol task with high reasoning.
2. Attach only the newest adjudicator bundle printed by `find`.
3. Paste the complete contents of `JUDGE_PROMPT.txt` and send it.
4. Wait for the response-directory path.
5. Import that directory:

```bash
python3 scripts/audit.py import \
  --output-dir results/reflection_audit \
  --response "/ABSOLUTE/PATH/REPORTED/BY/ADJUDICATOR" \
  --task-id "reflection-adjudicator"
python3 scripts/audit.py adjudicate \
  --output-dir results/reflection_audit
```

Afterward, `results/reflection_audit/pending_batches.json` must contain `[]`.

## Step 7: create and verify the final audit result

Run:

```bash
python3 scripts/audit.py summarize \
  --output-dir results/reflection_audit
python3 -c "import json,pathlib; p=pathlib.Path('results/reflection_audit'); s=json.loads((p/'summary.json').read_text()); g=json.loads((p/'progress.json').read_text()); assert s['status']=='complete'; assert g['status']=='complete'; assert s['completed']=={'reflection':2295}; assert all(s['reflection_cells'][c]['all_rows']==1176 for c in ('base__tiser','tiser__tiser')); print(json.dumps(s['reflection_cells'],indent=2))"
```

If this command finishes without an assertion error, the reflection audit is
complete. The report must not use the replacement reflection rates before this
final verification succeeds.
