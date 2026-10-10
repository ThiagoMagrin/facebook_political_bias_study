"""Render the verified final-model robustness table and manuscript insertions."""
import json
import os
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(os.environ.get("PROJECT_ROOT") or Path(__file__).resolve().parents[2])
OUT = ROOT / "rebuttal/results/consolidated_robustness"


def main():
    d = pd.read_csv(OUT / "consolidated_robustness.csv")
    fits = pd.read_csv(OUT / "model_diagnostics.csv")
    expected_ids = ["final", "no_crp", "bp2", "bp5", "window", "linkout", "min25", "min100"]
    assert list(d.id) == expected_ids and list(fits.id) == expected_ids
    assert (d.optimizer_code == 0).all() and d.pdHess.all()
    assert fits.finite_coefficients_and_CIs.all()
    assert np.isfinite(d[["beta_delta", "delta_low", "delta_high",
                             "beta_tox", "tox_low", "tox_high"]]).all().all()
    delta_negative = (d.delta_high < 0).all()
    tox_negative = (d.tox_high < 0).all()
    # Do not auto-write favorable interpretation if the fitted results differ.
    assert delta_negative and tox_negative, "Interpretation needs manual revision for changed signs/CIs"
    checks = json.loads((OUT / "preparation_checks.json").read_text())
    base = pd.read_csv(OUT / "baseline_reproduction.csv")
    max_repro = float(np.abs(base[["estimate_difference", "low_difference", "high_difference"]]).max().max())
    assert max_repro < .001
    labels = {
        "final": "Final model", "no_crp": "CRP omitted",
        "bp2": r"Pages with $\geq 2$ bias-scored links",
        "bp5": r"Pages with $\geq 5$ bias-scored links",
        "window": "Twitter-window posts only", "linkout": "Leave-link-out page bias",
        "min25": "Minimum 25 reactions", "min100": "Minimum 100 reactions"}
    rows = []
    mdrows = []
    for r in d.itertuples():
        rows.append(labels[r.id] + f" & ${r.beta_delta:.3f}$ & $[{r.delta_low:.3f}, {r.delta_high:.3f}]$"
                    + f" & ${r.beta_tox:.3f}$ & $[{r.tox_low:.3f}, {r.tox_high:.3f}]$ & {r.N:,} " + r"\\")
        mdrows.append(f"| {r.specification} | {r.beta_delta:.3f} | [{r.delta_low:.3f}, {r.delta_high:.3f}] "
                      f"| {r.beta_tox:.3f} | [{r.tox_low:.3f}, {r.tox_high:.3f}] | {r.N:,} |")
    table = r"""\begin{table}[htb]
\centering
\footnotesize
\setlength{\tabcolsep}{3pt}
\caption{Sensitivity analyses using the final mixed beta model for the
Reaction Homogeneity Index. Except for the stated modification, each model
retains the fixed- and random-effects specification in
Table~\ref{tab:beta_results}. Continuous predictors are standardized within
each fitted sample. Coefficients are on the logit scale and intervals are
two-sided 95\% Wald confidence intervals.}
\label{tab:robustness_final}
\begin{tabular}{p{3.7cm}ccccc}
\toprule
\textbf{Specification} & $\beta_{\Delta_b}$ & \textbf{95\% CI}
& $\beta_{\mathrm{Tox}}$ & \textbf{95\% CI} & \textbf{N} \\
\midrule
""" + "\n".join(rows) + r"""
\bottomrule
\end{tabular}
\end{table}
"""
    (OUT / "robustness_table.tex").write_text(table)
    preamble = r"""We next assessed the sensitivity of the key associations while retaining
the final mixed beta specification as the reference model.
Table~\ref{tab:robustness_final} reports standardized coefficients for Bias
Discrepancy and Toxicity after omitting Content Reaction Positivity,
restricting pages by the number of distinct bias-scored links in their
observed sharing histories, restricting posts to the Twitter collection
window (October 1--December 11, 2018), reconstructing page bias without the
focal link, and varying the minimum-reaction criterion.

For the sharing-history restrictions, we counted only distinct links with
available ideological scores, which are the links that contribute to $b_p$.
The page-activity control retained its original definition based on all
distinct shared links. In the leave-link-out analysis, we removed all posts
by a page sharing the focal news link from that page's full observed history,
then recalculated page leaning, page extremity, and Bias Discrepancy together.
This excluded 371 posts from pages with no remaining bias-scored history,
leaving 4,213 posts; an all-centrist remaining history was assigned $b_p=0$,
consistent with the original calculation. Other predictors retained their
original definitions. The 25-reaction sample was rebuilt from the source
data using the same preprocessing and metric-construction procedures before
applying the lower engagement cutoff. In every fitted sample, continuous
predictors were standardized and the boundary adjustment of $RHI$ was
recomputed using that sample's size.

"""
    postamble = r"""Across all eight specifications, Bias Discrepancy and Toxicity had
negative coefficients, with all 95\% confidence intervals excluding zero.
The Bias Discrepancy association persisted after removing the focal link
from the page-bias calculation, after restricting the sample to posts
within the Twitter measurement window, and under alternative engagement
cutoffs. These checks support the robustness of the reported association
to these specific analytical choices. They do not remove the limitations
of estimating page ideology from observed sharing behavior or establish a
causal effect. Because standardization was performed within each sample,
coefficient magnitudes reflect the predictor distributions in those samples.
"""
    r2_text = ""
    r2_report = ""
    if "R2_valid" in fits.columns and fits.R2_valid.all():
        rf = fits.loc[fits.id == "final"].iloc[0]
        rn = fits.loc[fits.id == "no_crp"].iloc[0]
        r2_text = (f"\nOmitting $CRP$ from the final specification reduced marginal $R^2$\n"
                   f"from ${rf.R2_marginal:.3f}$ to ${rn.R2_marginal:.3f}$, while conditional\n"
                   f"$R^2$ remained similar (${rf.R2_conditional:.3f}$ versus ${rn.R2_conditional:.3f}$).\n"
                   "Marginal and conditional $R^2$ were calculated using the Nakagawa\n"
                   "method implemented in \\texttt{performance::r2\\_nakagawa()}, with the\n"
                   "lognormal approximation. This indicates that $CRP$ accounts for substantial\n"
                   "fixed-effect variation, while the Bias Discrepancy association persists\n"
                   "when this same-link reaction covariate is omitted.\n")
        r2_report = (f"\n## CRP and model R2\n\nFor the exact final specification, marginal R2 decreases from "
                     f"{rf.R2_marginal:.3f} to {rn.R2_marginal:.3f} after CRP omission. "
                     f"Conditional R2 is {rf.R2_conditional:.3f} versus {rn.R2_conditional:.3f}.\n"
                     "These replace the earlier signed-bias comparison (0.760 to 0.121)\n"
                     "in the consolidated S5 discussion. If the response letter uses the\n"
                     "earlier numbers, either explicitly retain their signed-bias-model\n"
                     "context or update the comparison to the final model.\n\n"
                     "The old installed R2 utility produced negative distribution-specific\n"
                     "variance warnings and conditional R2 above 1. Those calculations are\n"
                     "retained only in `model_diagnostics_before_metric_refresh.csv` for\n"
                     "audit. Supplementary metrics were recomputed from the unchanged saved\n"
                     "fits with updated performance/insight dependencies; coefficient\n"
                     "estimates and CIs were not refitted. All refreshed R2 values passed\n"
                     "range and warning checks. See `metric_refresh_sessionInfo.txt` for\n"
                     "versions and `metric_refresh_warnings.csv` for the warning log.\n")
    appendix = preamble + table + "\n" + postamble + r2_text
    (OUT / "s5_robustness_replacement.tex").write_text(appendix)
    maintext = r"""The negative association between Bias Discrepancy and $RHI$ persisted
when $CRP$ was omitted, when pages were restricted to longer bias-scored
sharing histories, when posts were restricted to the Twitter collection
window, when page bias was recalculated without the focal shared link,
and under alternative minimum-reaction cutoffs (see
\nameref{app:r27_checks}, Table~\ref{tab:robustness_final}).
The negative-reaction-share analysis provides an alternative representation
of the same reaction-composition pattern, as explained in
\nameref{app:r27_checks}.
"""
    (OUT / "main_results_replacement.tex").write_text(maintext)
    report = f"""# Consolidated final-model robustness analyses

All eight models were fitted from the uploaded source data. Both Bias Discrepancy
and Toxicity remain negative, with every 95% Wald confidence interval excluding zero.

| Specification | Beta discrepancy | 95% CI | Beta toxicity | 95% CI | N |
|---|---:|---:|---:|---:|---:|
""" + "\n".join(mdrows) + f"""

## Exact manuscript insertion

1. In **S5 Appendix → Model specification and robustness checks**, keep the
   first paragraph comparing the signed-bias, leaning/extremity and categorical
   models, ending **“page links as activity controls (AIC $=-15046.2$).”**
2. Replace everything from **“Table~\\ref{{tab:r27_robustness}} reports additional
   checks...”** through the paragraph ending **“single observed link.”** with
   the full contents of `s5_robustness_replacement.tex`. This replaces the
   existing Table 6 and its surrounding discussion. Leave the following
   **Categorical bias specification** subsection in place. Use the table's
   automatic numbering rather than hard-coding “Table 6”.
3. In the main Results, replace the paragraph beginning **“Alternative model
   specifications produced substantively consistent results.”** and ending
   **“in \\nameref{{app:r27_checks}}.”** with `main_results_replacement.tex`.
4. `robustness_table.tex` is the table alone, if you prefer to insert the text
   separately. The new label is `tab:robustness_final`.

## Important distinctions from the existing results

- The earlier A4 “No CRP” model omits extremity terms. This new row removes only
  CRP from final model C; its discrepancy coefficient is
  {d.loc[d.id == 'no_crp', 'beta_delta'].iloc[0]:.3f}.
- History restrictions use `author_bp_links`, not `author_links_history`.
  The >=2 subset is unchanged at 4,213 posts. The >=5 subset has 3,405 posts,
  seven fewer than the earlier all-links threshold. Existing threshold results
  are retained rather than silently relabeled.
- Leave-link-out excludes **all shares of the focal content by the page**,
  rather than just the focal post. All three page-bias quantities are updated.
  {checks['leave_link_out_excluded_posts']} posts from
  {checks['leave_link_out_excluded_pages']} pages lack remaining scored history.
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
  {checks['full_bp_max_abs_error']:.2e}.
- All model variables in the >=50 subset of the rebuilt >=25 dataset match the
  reference data. Timestamp joins are unique and complete; window N = 4,099.
- All eight optimizer codes are zero; every Hessian is positive definite and
  all fixed-effect estimates, SEs and confidence intervals are finite.
- All 20 final-model coefficients and interval endpoints reproduce the stored
  model C within {max_repro:.2e}; the script permits differences below 0.001.
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
"""
    (OUT / "ROBUSTNESS_REPORT.md").write_text(report + r2_report)
    # Standalone table preview, with enough space to assess layout.
    preview = r"""\documentclass[10pt]{article}
\usepackage[margin=1in]{geometry}
\usepackage{amsmath,booktabs,array}
\begin{document}
\section*{Final-model robustness checks}
""" + table.replace(r"Table~\ref{tab:beta_results}", "the final model") + r"""
\end{document}
"""
    (OUT / "robustness_table_preview.tex").write_text(preview)
    print("Rendered verified table, S5 text, main Results text, and report.")


if __name__ == "__main__":
    main()
