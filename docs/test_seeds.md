# Test seeds

The test seeds were kept out of the repository until the results were published (docs/hypotheses.md). The results of
v0.1 and v1.0 are published, so the first seed of each range is given here. Each line uses consecutive seeds, starting at
the first seed of its range: `first, first + 1, ...`, up to its number of instances.

| Run | First seed | Seeds per line | Instances | Conditions |
|---|---|---|---|---|
| v0.1 | 714002 | the whole line (`V01_LINES`) | 61 | B, C |
| v1.0 | 893483 | at most 5 (`V10_LINES`) | 79 (34 played in condition A: levels 1 and 2) | A, B, C |

The v1.0 twins and canaries use the same first seed (`TWIN_LINES`, `CANARY_LINES`, 5 seeds per line at most), and are
reported apart.

Regenerate the instances of v1.0:

```
python -m orbitbench.harness run --condition B --suite v10 --first-seed 893483 --per-line 5 --model <model> --log-dir <dir>
```

(suites `v10`, `twins` and `canary`; `--max-level 2` is applied automatically in condition A).

These ranges are **spent**: they served once, each for the report that quotes them, and must not be reused to evaluate a
model, to train one, or to tune anything. Any later evaluation (new lines, the lunar line, a training study) draws a new
range kept private until its own results are published. The lunar line has its own range, still private.
