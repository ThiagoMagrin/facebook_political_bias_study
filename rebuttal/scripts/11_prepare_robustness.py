"""Validate samples and prepare leave-link-out page bias for final-model checks.

Run 01_build_dataset.py at MIN_REACTIONS=25 first. No model estimates are made
here. The full deduplicated history, post weighting, EPS and +/-0.3 cutoffs
are exactly those of the original builder. All posts sharing the focal
collection_name are removed, including repeat shares by the same page.
"""
import hashlib
import json
import os
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(os.environ.get("PROJECT_ROOT") or Path(__file__).resolve().parents[2])
DATA = ROOT / "rebuttal/data"
RES = ROOT / "rebuttal/results/consolidated_robustness"
RES.mkdir(parents=True, exist_ok=True)
KEY = ["collection_name", "account_name", "link", "post_text"]
EPS = 1e-6


def bp(blue, red, gray):
    total = blue + red + gray
    wl = (red + gray) / (total + EPS)
    wn = (red + blue) / (total + EPS)
    wr = (blue + gray) / (total + EPS)
    return (blue * wr - red * wl) / (red * wl + gray * wn + blue * wr + EPS)


def main():
    d = pd.read_csv(DATA / "analysis_dataset.csv", keep_default_na=False)
    d25 = pd.read_csv(DATA / "analysis_dataset_min25.csv", keep_default_na=False)
    dates = pd.read_csv(DATA / "post_timestamps.csv", keep_default_na=False)
    assert len(d) == 4584
    assert not d.duplicated(KEY).any(), "Nonunique analytical post key"
    assert not d25.duplicated(KEY).any(), "Nonunique alternate-sample post key"
    assert not dates.duplicated(KEY).any(), "Nonunique timestamp key"
    # At cutoff >=50 the expanded sample must reproduce every model variable,
    # not the sample-specific quartile labels or sample activity counts.
    shared = ["rph_link", "rph_user", "rph_delta", "toxicity", "reaction_score",
              "consensus_index", "totalReactions", "log_total_reactions",
              "log_author_links", "author_bp_links", "content_leaning",
              "content_extremity", "publisher_leaning", "publisher_extremity",
              "Economy", "Education", "Health", "Security", "Culture",
              "Religion", "Disinformation", "Election", "Politics", "Corruption"]
    expanded50 = d25.loc[d25.totalReactions >= 50, KEY + shared]
    assert len(expanded50) == len(d)
    check = d[KEY + shared].merge(expanded50, on=KEY, validate="one_to_one",
                                  suffixes=("_main", "_alt"), how="outer", indicator=True)
    assert (check._merge == "both").all()
    for v in shared:
        np.testing.assert_allclose(check[v + "_main"], check[v + "_alt"], rtol=0, atol=1e-9)
    timed = d.merge(dates[KEY + ["within_twitter_window"]], on=KEY,
                    validate="one_to_one", how="left")
    assert timed.within_twitter_window.notna().all()
    assert timed.within_twitter_window.dtype == bool
    assert int(timed.within_twitter_window.sum()) == 4099

    raw = pd.read_csv(ROOT / "data/data_mongodb.csv")
    scored = raw.loc[raw.rph_link.notna()].copy()
    scored["blue"] = (scored.rph_link >= .3).astype(int)
    scored["red"] = (scored.rph_link <= -.3).astype(int)
    scored["gray"] = ((scored.rph_link > -.3) & (scored.rph_link < .3)).astype(int)
    assert (scored[["blue", "red", "gray"]].sum(axis=1) == 1).all()
    full = scored.groupby("account_name")[["blue", "red", "gray"]].sum()
    full["bp_full"] = bp(full.blue, full.red, full.gray)
    verify = d[["account_name", "rph_user"]].drop_duplicates().merge(
        full[["bp_full"]], on="account_name", validate="one_to_one")
    assert len(verify) == d.account_name.nunique()
    max_error = float(np.max(np.abs(verify.rph_user - verify.bp_full)))
    assert max_error < 1e-9, "Page-bias reconstruction differs from the final model"
    counts = scored.groupby(["account_name", "collection_name"])[["blue", "red", "gray"]].sum()
    counts = counts.rename(columns={c: "focal_" + c for c in counts.columns}).reset_index()
    counts = counts.merge(full.reset_index(), on="account_name", validate="many_to_one")
    for c in ["blue", "red", "gray"]:
        counts["rem_" + c] = counts[c] - counts["focal_" + c]
        assert (counts["rem_" + c] >= 0).all()
    counts["remaining_scored_posts"] = counts[["rem_blue", "rem_red", "rem_gray"]].sum(axis=1)
    counts["bp_linkout"] = bp(counts.rem_blue, counts.rem_red, counts.rem_gray)
    # No remaining scored history is missing, rather than an invented center.
    # Remaining all-center history retains bp=0, matching the original EPS rule.
    counts.loc[counts.remaining_scored_posts == 0, "bp_linkout"] = np.nan
    mapping = counts[["account_name", "collection_name", "bp_linkout", "remaining_scored_posts",
                      "rem_blue", "rem_red", "rem_gray"]]
    linkout = d.merge(mapping, on=["account_name", "collection_name"], how="left",
                      validate="many_to_one", indicator=True)
    assert len(linkout) == len(d) and (linkout._merge == "both").all()
    excluded = int(linkout.bp_linkout.isna().sum())
    audit = linkout[KEY + ["rph_user", "bp_linkout", "remaining_scored_posts",
                           "rem_blue", "rem_red", "rem_gray"]].copy()
    audit["excluded_no_remaining_scored_history"] = audit.bp_linkout.isna()
    audit.to_csv(RES / "leave_link_out_audit.csv", index=False)
    linkout = linkout.loc[linkout.bp_linkout.notna()].drop(columns="_merge").copy()
    linkout["rph_user"] = linkout.bp_linkout
    linkout["publisher_leaning"] = linkout.bp_linkout
    linkout["publisher_extremity"] = linkout.bp_linkout.abs()
    linkout["rph_delta"] = (linkout.rph_link - linkout.bp_linkout).abs()
    linkout.to_csv(DATA / "analysis_dataset_linkout.csv", index=False)
    timed.to_csv(DATA / "analysis_dataset_timed.csv", index=False)

    samples = [("final", "Final model", d), ("no_crp", "CRP omitted", d),
               ("bp2", "At least 2 bias-scored links", d.loc[d.author_bp_links >= 2]),
               ("bp5", "At least 5 bias-scored links", d.loc[d.author_bp_links >= 5]),
               ("window", "Twitter-window posts only", timed.loc[timed.within_twitter_window]),
               ("linkout", "Leave-link-out page bias", linkout),
               ("min25", "Minimum 25 reactions", d25),
               ("min100", "Minimum 100 reactions", d.loc[d.totalReactions >= 100])]
    summary = pd.DataFrame([dict(id=k, specification=label, N=len(s),
                                pages=s.account_name.nunique(), links=s.collection_name.nunique())
                            for k, label, s in samples])
    summary.to_csv(RES / "sample_manifest.csv", index=False)
    paths = [ROOT / "data/data_mongodb.csv", DATA / "analysis_dataset.csv",
             DATA / "analysis_dataset_min25.csv", DATA / "post_timestamps.csv"]
    report = dict(full_bp_max_abs_error=max_error, alternate50_exact_match=True,
                  timestamp_unmatched=0, twitter_window_N=4099,
                  leave_link_out_excluded_posts=excluded,
                  leave_link_out_excluded_pages=int(audit.loc[audit.excluded_no_remaining_scored_history,
                                                              "account_name"].nunique()),
                  all_center_remaining_posts=int(((linkout.rem_gray > 0)
                                                  & (linkout.rem_blue == 0)
                                                  & (linkout.rem_red == 0)).sum()),
                  category_rule="Left <= -0.3; Center -0.3 < b < 0.3; Right >= 0.3",
                  history_unit="Post-weighted, full deduplicated corpus",
                  input_sha256={str(p.relative_to(ROOT)): hashlib.sha256(p.read_bytes()).hexdigest()
                                for p in paths})
    (RES / "preparation_checks.json").write_text(json.dumps(report, indent=2) + "\n")
    print(summary.to_string(index=False))
    print(json.dumps(report, indent=2))


if __name__ == "__main__":
    main()
