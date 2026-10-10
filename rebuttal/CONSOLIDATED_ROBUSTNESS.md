# Consolidated robustness analyses

These analyses start from model C in `_common.R`. The original scripts and
results for the earlier signed-bias models are retained for provenance.

## Run from the repository root

Python packages: `polars` (validated with 1.34.0), `pandas`, `numpy`.
R packages: `readr`, `dplyr`, `glmmTMB`, `broom.mixed`, `performance` (and `reformulas` for recent `insight` versions).

```bash
python rebuttal/scripts/01_build_dataset.py
MIN_REACTIONS=25 python rebuttal/scripts/01_build_dataset.py
python rebuttal/scripts/11_prepare_robustness.py
Rscript rebuttal/scripts/12_consolidated_robustness.R
# Optional: refresh supplementary metrics from saved fits after package updates
Rscript rebuttal/scripts/14_refresh_fit_metrics.R
python rebuttal/scripts/13_robustness_deliverables.py
```

Use an environment with the Python dependencies installed. If using `uv`,
replace `python` with `uv run python`; the existing project environment
contains the other research dependencies as well. R is a separate runtime.
`PROJECT_ROOT` is optional; paths otherwise resolve relative to the scripts.

## Definitions

- The reference is the exact final model C: signed content/page bias, content/page
  extremity, Bias Discrepancy, Toxicity, CRP, log total reactions, log page links,
  ten topic scores, and `(toxicity|account_name) + (toxicity|collection_name)`.
- CRP omission removes only CRP; other covariates and the random structure remain.
- History restrictions use `author_bp_links`: distinct bias-scored links in the
  full deduplicated corpus, rather than all shared links. The activity control
  continues to use the original `log_author_links`.
- The Twitter-window subset uses the exact one-to-one timestamp mapping.
- Leave-link-out removes all posts by the page sharing the focal content ID
  before recomputing its page bias. Page leaning, page extremity, and discrepancy
  are replaced together. Pages without remaining bias-scored history are omitted;
  an all-center remaining history receives zero as in the original EPS formula.
  All other covariates, including CRP and the activity control, retain their
  original definitions.
- The original bias category rule is retained: Left <= -0.3, Right >= 0.3, and
  Center strictly between them. The history remains post-weighted and uses EPS
  = 1e-6. This analysis does not change those original methodological choices.
- The >=25 sample is rebuilt before the original >=50 filter. Metric construction
  and domain exclusions remain identical. CRP is computed before the engagement
  filter, as in the original pipeline, rather than recomputed on each subset.
- Continuous predictors are standardized within each fitted sample; the outcome
  uses `(RHI * (N - 1) + 0.5) / N` within that sample. The CSV also includes
  predictor SDs and raw-unit coefficients for comparability. Coefficient CIs
  are two-sided 95% Wald intervals on the logit scale.

## Checks and outputs

`results/consolidated_robustness/` contains the completed table, all coefficients,
model summaries, optimizer codes, positive-definite Hessian checks, gradients,
VIFs, random-effect SDs/correlations, sample manifests, input hashes, and R
session information. Serialized fits are checkpointed under `fits/`.

The preparation script verifies reproduction of page bias, unique post joins,
the 4,099-window count, and exact matching of every model variable in the >=50
subset of the expanded >=25 sample. The R script checks all 20 final-model
estimates and CI endpoints against the repository's stored model C, allowing
a maximum numerical difference of 0.001 for runtime differences.

Model estimates are released only if the optimizer code is zero, the Hessian
is positive definite, and all fixed-effect estimates, standard errors, and CI
endpoints are finite. `pdHess` alone is not called convergence. R2 uses
`performance::r2_nakagawa(..., approximation="lognormal")`; version information
is recorded because R2 values can depend on package implementation. Invalid
R2 values or calculations carrying an unreliability warning are stored as NA;
they are not used in the coefficient table or interpretation.
Pearson residual summaries are descriptive and are not a substitute for
simulation-based residual diagnostics. These checks do not establish absence
of all misspecification or identify causal effects.

See `results/consolidated_robustness/ROBUSTNESS_REPORT.md` for estimates,
interpretation, and exact manuscript insertion instructions.
