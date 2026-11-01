# Hypotheses and primary comparison

Recorded on 2 November 2026, before any model has been run on the benchmark. A change made after
calibration is added to "Amendments" below with its date and its reason; the text above is never edited.

## Questions, in priority order

1. **Training.** Does RL training of a small open-source model on this reward reduce the gap to the optimum
   on task families held out of training?
2. **Reliability.** How often does a model claim a verification it never did, or present a failure as a success?
3. **Value of the tool.** By how much does GMAT-MCP raise the success rate compared with Python alone (condition C minus B)?

## Primary comparison

Gap to the optimum on the held-out families, trained model against the same model before training, paired on
the same instances, with a bootstrap confidence interval (resampling families first, then instances within a
family). Questions 2 and 3 are reported separately, with their own intervals.

## Hypotheses

- **H1 (exploratory).** The tool helps mostly at levels 3 and 4 (multi-step, targeting); at levels 1 and 2 Python
  alone is enough. The split by level lacks the power of a confirmatory test, so H1 is reported per family
  without a firm conclusion.
- **H2.** Without GMAT, errors of units, frames and conventions dominate. Tested at levels 1 and 2, on
  conditions A (no tool) and B (Python only).
- **H3.** The gap between models grows with difficulty.
- **H4.** Reliability (succeeding k times out of k) is clearly lower than the success rate of a single attempt.
- **H5.** Models present a measurable share of failures as successes, including when the result signals the
  failure (a targeting run with `converged` false).
- **H6.** Training reduces the gap to the optimum on the held-out families.

## Amendments

None yet.
