| Arm | Model | n | Parse/JSON fail % | Template acc % | Side acc % | Plays with any issue % | Legal play from phrasing % | Mean issues/play | out_of_bounds % | overlap % | too_fast % | ball_orphan % | missing_player % | p50 s | p95 s |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| rules | none (keyword rules) | 40 | 15.0 | 75.0 | 85.0 | 0.0 | 85.0 | 0.0 | 0.0 | 0.0 | 0.0 | 0.0 | 0.0 | 0.0 | 0.06 |
| template | qwen2.5-3b-instruct (Modal, llama.cpp) + rules fallback | 40 | 0.0 | 92.5 | 95.0 | 0.0 | 100.0 | 0.0 | 0.0 | 0.0 | 0.0 | 0.0 | 0.0 | 3.3 | 7.33 |
| freehand_hosted | qwen2.5-3b-instruct (Modal, llama.cpp) | 40 | 0.0 | 65.0 | 92.5 | 97.5 | 2.5 | 13.07 | 2.5 | 97.5 | 0.0 | 0.0 | 0.0 | 41.11 | 63.51 |
