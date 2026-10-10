# Consolidated final-model robustness analyses

All eight models were fitted from the uploaded source data. Both Bias Discrepancy
and Toxicity remain negative, with every 95% Wald confidence interval excluding zero.

| Specification | Beta discrepancy | 95% CI | Beta toxicity | 95% CI | N |
|---|---:|---:|---:|---:|---:|
| Final model | -0.173 | [-0.211, -0.135] | -0.149 | [-0.196, -0.102] | 4,584 |
| CRP omitted | -0.178 | [-0.219, -0.138] | -0.133 | [-0.180, -0.086] | 4,584 |
| At least 2 bias-scored links | -0.201 | [-0.241, -0.160] | -0.162 | [-0.211, -0.113] | 4,213 |
| At least 5 bias-scored links | -0.219 | [-0.264, -0.175] | -0.170 | [-0.226, -0.113] | 3,405 |
| Twitter-window posts only | -0.173 | [-0.214, -0.132] | -0.144 | [-0.192, -0.096] | 4,099 |
| Leave-link-out page bias | -0.192 | [-0.234, -0.150] | -0.165 | [-0.214, -0.116] | 4,213 |
| Minimum 25 reactions | -0.171 | [-0.206, -0.135] | -0.133 | [-0.179, -0.088] | 5,774 |
| Minimum 100 reactions | -0.167 | [-0.209, -0.126] | -0.177 | [-0.229, -0.126] | 3,558 |

## Exact manuscript insertion

1. In **S5 Appendix → Model specification and robustness checks**, keep the
   first paragraph comparing the signed-bias, leaning/extremity and categorical
   models, ending **“page links as activity controls (AIC $=-15046.2$).”**
2. Replace everything from **“Table~\ref{tab:r27_robustness} reports additional
   checks...”** through the paragraph ending **“single observed link.”** with
   the full contents of `s5_robustness_replacement.tex`. This replaces the
   existing Table 6 and its surrounding discussion. Leave the following
   **Categorical bias specification** subsection in place. Use the table's
   automatic numbering rather than hard-coding “Table 6”.
3. In the main Results, replace the paragraph beginning **“Alternative model
   specifications produced substantively consistent results.”** and ending
   **“in \nameref{app:r27_checks}.”** with `main_results_replacement.tex`.
4. `robustness_table.tex` is the table alone, if you prefer to insert the text
   separately. The new label is `tab:robustness_final`.

## Important distinctions from the existing results

- The earlier A4 “No CRP” model omits extremity terms. This new row removes only
  CRP from final model C; its discrepancy coefficient is
  -0.178.
- History restrictions use `author_bp_links`, not `author_links_history`.
  The >=2 subset is unchanged at 4,213 posts. The >=5 subset has 3,405 posts,
  seven fewer than the earlier all-links threshold. Existing threshold results
  are retained rather than silently relabeled.
- Leave-link-out excludes **all shares of the focal content by the page**,
  rather than just the focal post. All three page-bias quantities are updated.
  371 posts from
  364 pages lack remaining scored history.
  Although its N matches the >=2 subset, its page scores and discrepancies differ.
- The engagement cutoff uses total reactions across all reaction categories,
  as in the original builder. CRP/RHI use Like, Love, Sad and Angry. CRP is
  constructed before the cutoff, consistently with the reference analysis.
- Coefficients are standardized within each sample. Predictor SDs and raw-unit
  coefficients are included in the CSV; standardized magnitudes should not be
  treated as effects for identical raw changes across different samples.
- Original ideological cutoffs and post weighting are unchanged. Eight analytical
  posts have link scores exactly at +/-0.3; changing boundary conventions would
  be a separate methodological change and would require rerunning analyses.

## Verification and diagnostics

- The original builder reproduced 4,584 posts and all 25 shared original columns
  with zero numerical differences.
- Rebuilt full-history page bias matches to within
  1.11e-16.
- All model variables in the >=50 subset of the rebuilt >=25 dataset match the
  reference data. Timestamp joins are unique and complete; window N = 4,099.
- All eight optimizer codes are zero; every Hessian is positive definite and
  all fixed-effect estimates, SEs and confidence intervals are finite.
- All 20 final-model coefficients and interval endpoints reproduce the stored
  model C within 7.30e-06; the script permits differences below 0.001.
- `model_diagnostics.csv`, `random_effects.csv`, `vif.csv`, `warnings.csv`,
  model summaries, and session information provide further audit details.
  Small optimizer gradients are recorded rather than equated with exact zeros.
- VIF maxima range from 4.59 to 5.10 across the specifications. The
  Twitter-window Politics term (5.104) and >=25 Culture term (5.003) slightly
  exceed 5; no blanket claim that all sensitivity-model VIFs are below 5 is made.
- Pearson residual summaries are descriptive. No simulation-based residual
  or dispersion test was performed in this consolidation.

## Changed files and reproduction

`01_build_dataset.py` now accepts `MIN_REACTIONS` (default 50), names alternate
outputs separately, and retains the original-sample reproduction check at 50.
Scripts 11--13 prepare validated samples, fit the eight models, and render these
deliverables. Script 14 refreshes supplemental metrics from the saved fits. See `rebuttal/CONSOLIDATED_ROBUSTNESS.md` for the commands.
The original modeling scripts and their result tables are retained.

## CRP and model R2

For the exact final specification, marginal R2 decreases from 0.762 to 0.154 after CRP omission. Conditional R2 is 0.977 versus 0.979.
These replace the earlier signed-bias comparison (0.760 to 0.121)
in the consolidated S5 discussion. If the response letter uses the
earlier numbers, either explicitly retain their signed-bias-model
context or update the comparison to the final model.

The old installed R2 utility produced negative distribution-specific
variance warnings and conditional R2 above 1. Those calculations are
retained only in `model_diagnostics_before_metric_refresh.csv` for
audit. Supplementary metrics were recomputed from the unchanged saved
fits with updated performance/insight dependencies; coefficient
estimates and CIs were not refitted. All refreshed R2 values passed
range and warning checks. See `metric_refresh_sessionInfo.txt` for
versions and `metric_refresh_warnings.csv` for the warning log.
