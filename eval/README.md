# eval: freehand LLM vs template engine

Measures whether an LLM can draw a legal play by itself (freehand coordinates), compared with
Chalk Talk's path (LLM picks a template, the engine builds it, the validator checks it).
Results and method: [RESULTS.md](RESULTS.md).

## Run

```
python3 eval/run_eval.py --limit 20                       # quick check, about 5 minutes cold
python3 eval/run_eval.py --workers 8 --gemma-limit 100    # full run (300 phrasings; gemma arm on the first 100)
python3 eval/run_eval.py --arms rules,template            # just the cheap arms
```

Needs `httpx`, the engine in `../engine` (imported from the path, nothing to install), the hosted
LLM at `https://m-simakhov--chalk-talk-llm.us-east.modal.run/v1` (503 while cold: the harness
waits and retries) and, for the `freehand_gemma` arm, Ollama on `localhost:11434` with
`gemma4:12b-nvfp4`.

Every LLM reply is cached in `eval/.cache/<arm>/` (key: hash of arm, model, messages, schema), so
re-running or resuming after a crash only pays for what is missing. Delete a folder there to
re-measure that arm. Outputs: `eval/results/<arm>.jsonl` (one row per phrasing, with raw replies),
`eval/results/summary.json`, `eval/results/table.md`.

## Files

- `seeds.json`: 40 hand-written coach phrasings with labels.
- `gen_phrasings.py`: grows the seeds to 300 with a local Ollama model (`phrasings.json`).
- `llmcall.py`: the one cached, retrying OpenAI-compatible call.
- `run_eval.py`: the four arms and the metrics.
