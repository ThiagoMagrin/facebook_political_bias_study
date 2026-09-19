"""
Rebuttal analysis - Step 7
How reliable is the publisher bias score b_p when a publisher has a short
sharing history, and does that instability reach the results?

Part 1: leave-one-post-out stability of b_p, by size of the sharing history.
Part 2: the sample that survives increasing history thresholds (models fitted
        by 08_threshold_models.R).
"""
import os
import numpy as np
import polars as pl
from pathlib import Path
from scipy import stats

# Repository root: PROJECT_ROOT if set, otherwise derived from this file's own
# location (scripts live in <root>/rebuttal/scripts/). Mirrors the resolution in
# _common.R so the Python and R halves of the pipeline relocate together.
ROOT = Path(os.environ.get("PROJECT_ROOT") or Path(__file__).resolve().parents[2])
assert (ROOT / "rebuttal" / "scripts").is_dir(), f"not a repository root: {ROOT}"
DATA, RES = ROOT / "data", ROOT / "rebuttal" / "results"
OUT = ROOT / "rebuttal" / "data"
EPS = 1e-6

# The sharing-history cut-offs, read from thresholds.txt rather than hardcoded:
# 08_threshold_models.R reads the same file. Tables 2.3 and 2.4 of the response
# share column headers, so if the two scripts kept private copies of the ladder
# they could silently come to describe different subsets.
THRESHOLDS = [
    int(line) for line in (Path(__file__).resolve().parent / "thresholds.txt")
    .read_text().splitlines() if line.strip() and not line.lstrip().startswith("#")
]

def bp(blue, red, gray):
    """Publisher bias, exactly as notebooks/data_collection.py computes it."""
    total = blue + red + gray
    W_L = (red + gray) / (total + EPS)
    W_N = (red + blue) / (total + EPS)
    W_R = (blue + gray) / (total + EPS)
    num = blue * W_R - red * W_L
    den = red * W_L + gray * W_N + blue * W_R + EPS
    return num / den

posts = pl.read_csv(DATA / "data_mongodb.csv")
# notebooks/data_collection.py counts categories with .count(), which DROPS
# null rph_link. A bare .otherwise() would sweep those posts into "gray" and
# silently produce a different b_p, so nulls are excluded explicitly here.
n_null = posts["rph_link"].null_count()
posts = posts.filter(pl.col("rph_link").is_not_null())
print(f"dropped {n_null} posts with null rph_link, as the original pipeline does")

cat = (
    pl.when(pl.col("rph_link") >= 0.3).then(pl.lit("blue"))
    .when(pl.col("rph_link") <= -0.3).then(pl.lit("red"))
    .otherwise(pl.lit("gray"))
)
posts = posts.with_columns(cat.alias("cat"))
counts = posts.group_by("account_name").agg(
    (pl.col("cat") == "blue").sum().alias("blue"),
    (pl.col("cat") == "red").sum().alias("red"),
    (pl.col("cat") == "gray").sum().alias("gray"),
    pl.len().alias("n_posts_history"),
    pl.col("collection_name").n_unique().alias("n_links_history"),
)

# leave-one-post-out: drop the focal post's own contribution
loo = (
    posts.join(counts, on="account_name", how="left")
    .with_columns([
        (pl.col("blue") - (pl.col("cat") == "blue").cast(pl.Int64)).alias("b_loo"),
        (pl.col("red") - (pl.col("cat") == "red").cast(pl.Int64)).alias("r_loo"),
        (pl.col("gray") - (pl.col("cat") == "gray").cast(pl.Int64)).alias("g_loo"),
    ])
)
b = loo["blue"].to_numpy(); r = loo["red"].to_numpy(); g = loo["gray"].to_numpy()
bl = loo["b_loo"].to_numpy(); rl = loo["r_loo"].to_numpy(); gl = loo["g_loo"].to_numpy()
loo = loo.with_columns([
    pl.Series("bp_full", bp(b, r, g)),
    pl.Series("bp_loo", np.where((bl + rl + gl) == 0, np.nan, bp(bl, rl, gl))),
])

def _check_join(joined, source, key_cols, col):
    """Every analysis row must find its match; the binning below drops nulls
    silently, so an incomplete join would shrink the table without warning."""
    n_null = joined[col].is_null().sum()
    assert joined.height == source.height, (
        f"join changed the row count: {source.height} -> {joined.height}")
    assert n_null == 0, f"{n_null} analysis rows found no match on {key_cols}"
    print(f"join check: {joined.height} rows in, {joined.height} out, 0 unmatched")


analysis = pl.read_csv(OUT / "analysis_dataset.csv").select(
    ["collection_name", "account_name", "post_text",
     "author_links_history", "author_bp_links", "rph_user"]
)

# The two link counts are not the same thing: author_links_history counts every
# distinct link the publisher shared (reviewer 1's "author activity"), while
# author_bp_links counts only those carrying a bias score, i.e. the links b_p is
# actually estimated from. The bins below and the subsets in 08 threshold on the
# former, so say how far the two diverge instead of letting the scripts disagree
# silently about what the number means.
_gap = analysis.select(["account_name", "author_links_history", "author_bp_links"]).unique()
_gap = _gap.filter(pl.col("author_links_history") != pl.col("author_bp_links"))
_gap_posts = analysis.join(_gap.select("account_name"), on="account_name", how="inner").height
print(f"link-count gap: {_gap.height} publishers ({_gap_posts} posts) shared links with no "
      f"bias score, so b_p rests on fewer links than author_links_history reports")

# This script re-implements the b_p formula that lives in the original pipeline.
# Duplicated formulas drift, so verify the recomputation against the b_p that
# actually entered the regressions before using it for anything.
_chk = (
    analysis.select(["account_name", "rph_user"]).unique()
    .join(loo.select(["account_name", "bp_full"]).unique(subset=["account_name"]),
          on="account_name", how="inner")
)
_maxdiff = float((_chk["rph_user"] - _chk["bp_full"]).abs().max())
print(f"check: max |recomputed b_p - b_p used in the models| = {_maxdiff:.3e}")
assert _maxdiff < 1e-9, (
    f"recomputed b_p does not match the b_p in the models (max diff {_maxdiff:.4f}); "
    "the formula here has drifted from notebooks/data_collection.py"
)
_key = ["collection_name", "account_name", "post_text"]
m = analysis.join(
    loo.select(["collection_name", "account_name", "message", "bp_full", "bp_loo",
                "n_posts_history", "n_links_history"]).rename({"message": "post_text"}),
    on=_key, how="left",
)
_check_join(m, analysis, _key, "bp_full")

lines = []
def say(s=""):
    print(s); lines.append(str(s))

say("=" * 78)
say("b_p RELIABILITY: leave-one-post-out stability by size of sharing history")
say("=" * 78)
say("\nIf b_p is a stable property of a publisher, removing one of its posts should")
say("barely move it. If the history is short, it moves a lot.\n")
say("r is scale-free and flatters short histories: at 2 links r = 0.85 while the")
say("mean shift is 0.29 on a b_p scale that spans [-1, +1]. Read both columns.\n")
say(f"{'history (links)':<18}{'posts':>7}{'r(full, LOO)':>15}{'mean |shift|':>15}{'median |shift|':>16}")
bins = [(1, 1), (2, 2), (3, 5), (6, 10), (11, 20), (21, 50), (51, 10**9)]
rows = []
for lo, hi in bins:
    s = m.filter((pl.col("author_links_history") >= lo) & (pl.col("author_links_history") <= hi))
    s = s.filter(pl.col("bp_loo").is_not_nan() & pl.col("bp_loo").is_not_null())
    label = f"{lo}" if lo == hi else (f"{lo}+" if hi > 10**8 else f"{lo}-{hi}")
    if lo == 1:
        # b_p is degenerate here, not merely noisy: with one distinct link the
        # estimator can only return -1, 0 or +1. Reporting a correlation for this
        # group would be misleading, so it is carried with nulls and flagged.
        n_all = int(m.filter(pl.col("author_links_history") == 1).height)
        say(f"{label:<18}{n_all:>7}{'degenerate':>15}{'-':>15}{'-':>16}")
        rows.append({"history_bin": label, "n_posts": n_all, "r_full_loo": None,
                     "mean_abs_shift": None, "median_abs_shift": None,
                     "degenerate": True})
        continue
    if s.height < 2:
        say(f"{label:<18}{s.height:>7}{'n/a':>15}{'-':>15}{'-':>16}")
        continue
    f_, l_ = s["bp_full"].to_numpy(), s["bp_loo"].to_numpy()
    shift = np.abs(f_ - l_)
    rr = stats.pearsonr(f_, l_).statistic if np.std(l_) > 0 else float("nan")
    say(f"{label:<18}{s.height:>7}{rr:>15.3f}{shift.mean():>15.3f}{np.median(shift):>16.3f}")
    rows.append({"history_bin": label, "n_posts": s.height, "r_full_loo": rr,
                 "mean_abs_shift": float(shift.mean()),
                 "median_abs_shift": float(np.median(shift)), "degenerate": False})

allp = m.filter(pl.col("bp_loo").is_not_nan() & pl.col("bp_loo").is_not_null())
say(f"\noverall r(full, LOO) = {stats.pearsonr(allp['bp_full'].to_numpy(), allp['bp_loo'].to_numpy()).statistic:.3f} "
    f"over {allp.height} posts")

say("\n-- what the single-link publishers look like --")
one = m.filter(pl.col("author_links_history") == 1)
_vals = sorted({round(float(v), 3) for v in one["bp_full"]})
say(f"   posts {one.height}; their b_p takes only the values "
    f"{', '.join(f'{v:g}' for v in _vals)}")
_one_post = int(one.filter(pl.col("n_posts_history") == 1).height)
_many_posts = int(one.filter(pl.col("n_posts_history") > 1).height)
assert _one_post + _many_posts == one.height, "single-link posts do not partition"
say(f"   They are excluded from the table above. For the {_one_post} that posted their")
say("   one link once, leave-one-post-out is undefined - nothing remains. For the")
say(f"   {_many_posts} that posted it more than once, dropping a post leaves the same")
say("   single category, so the score trivially does not move; that stability is an")
say("   artefact of the degeneracy, not evidence of reliability. With one distinct")
say("   link b_p is not an estimate, it is a label forced by a single observation.")

pl.DataFrame(rows).write_csv(RES / "bp_reliability.csv")

say("\n" + "=" * 78)
say("SAMPLE REMAINING AT EACH HISTORY THRESHOLD")
say("=" * 78)
d = pl.read_csv(OUT / "analysis_dataset.csv")
say("\nThe threshold is applied to author_links_history (every distinct link the")
say("publisher shared). The last column counts publishers admitted by that cut")
say("whose b_p in fact rests on fewer links, because some of the links they")
say("shared carry no bias score.")
say(f"\n{'threshold':<22}{'posts':>8}{'publishers':>13}{'content':>10}{'b_p under cut':>22}")
_under_detail = []
for t in THRESHOLDS:
    s = d.filter(pl.col("author_links_history") >= t)
    _u = s.filter(pl.col("author_bp_links") < t)
    _under, _under_posts = _u["account_name"].n_unique(), _u.height
    # The response document quotes the posts as well as the publishers, so print
    # both here rather than leaving the post count to be worked out by hand.
    _cell = f"{_under}" if _under == 0 else f"{_under} ({_under_posts} posts)"
    say(f"{'>= ' + str(t) + ' links':<22}{s.height:>8}{s['account_name'].n_unique():>13}"
        f"{s['collection_name'].n_unique():>10}{_cell:>22}")
    if _under:
        _under_detail.append((t, sorted(set(_u["author_bp_links"].to_list()))))
for _t, _links in _under_detail:
    say(f"   at >= {_t}: b_p there rests on "
        f"{', '.join(str(x) for x in _links)} scored link(s), not {_t}")

with open(RES / "bp_reliability.txt", "w", encoding="utf-8") as fh:
    fh.write("\n".join(lines) + "\n")
print(f"\nwritten: {RES / 'bp_reliability.txt'}")

# ------------------------------- composition of the thresholded subsamples ----
lines2 = []
def say2(s=""):
    print(s); lines2.append(str(s))

say2("=" * 78)
say2("WHAT THE THRESHOLD ACTUALLY SELECTS (Table 2.4)")
say2("=" * 78)
say2("\nRequiring a longer sharing history does not only reduce noise in b_p; it")
say2("also selects larger, more institutional publishers. If it were a clean")
say2("measurement-error correction, the sample composition would not move.\n")
say2("Publisher-level quantities are computed over DISTINCT PUBLISHERS, not over")
say2("posts. Weighting publisher attributes by post count lets one high-volume page")
say2("enter the average dozens of times and reverses the centrist trend, so both")
say2("weightings are reported.\n")
say2(f"{'threshold':<11}{'posts':>7}{'pubs':>6}{'med react':>11}"
     f"{'subs/post':>11}{'subs/pub':>10}{'mean tox':>10}{'ctr/post':>10}{'ctr/pub':>9}")
comp = []
for t in THRESHOLDS:
    sub = d.filter(pl.col("author_links_history") >= t)
    # nothing downstream needs a mean over this group-by, which is important:
    # polars does not fix the group order, so averaging a float column here made
    # the written CSV differ in the last ULP between runs.
    # publisher_side is constant within a publisher, so .first() is safe there.
    # subscriberCount is NOT: it is a per-post snapshot and 485 of the 1,243
    # publishers carry more than one value (one spans 11,030-381,918). Since
    # polars does not fix the group order, .first() would pick an arbitrary
    # snapshot and move this column between runs. Reduce it explicitly.
    pubs = sub.group_by("account_name").agg(
        pl.col("publisher_side").first(),
        pl.col("subscriberCount").median(),
    )
    row = {
        "threshold": t, "posts": sub.height, "publishers": pubs.height,
        "median_reactions": float(sub["totalReactions"].median()),
        "median_subscribers_per_post": float(sub["subscriberCount"].median()),
        "median_subscribers_per_publisher": float(pubs["subscriberCount"].median()),
        "mean_toxicity": float(sub["toxicity"].mean()),
        "pct_center_by_post": float(100 * (sub["publisher_side"] == "Center").mean()),
        "pct_center_by_publisher": float(100 * (pubs["publisher_side"] == "Center").mean()),
    }
    comp.append(row)
    say2(f"{'>= ' + str(t):<11}{row['posts']:>7}{row['publishers']:>6}"
         f"{row['median_reactions']:>11.0f}{row['median_subscribers_per_post']:>11.0f}"
         f"{row['median_subscribers_per_publisher']:>10.0f}{row['mean_toxicity']:>10.4f}"
         f"{row['pct_center_by_post']:>9.1f}%{row['pct_center_by_publisher']:>8.1f}%")
pl.DataFrame(comp).write_csv(RES / "threshold_composition.csv")

c0, c1 = comp[0], comp[-1]
say2(f"\nfull sample -> >= 15 links:")
say2(f"   median reactions per post      {c0['median_reactions']:.0f} -> {c1['median_reactions']:.0f}"
     f"   ({c1['median_reactions']/c0['median_reactions']:.1f}x)")
say2(f"   median subscribers, per POST   {c0['median_subscribers_per_post']:.0f} -> "
     f"{c1['median_subscribers_per_post']:.0f}   ({c1['median_subscribers_per_post']/c0['median_subscribers_per_post']:.1f}x)")
say2(f"   median subscribers, per PUBLISHER {c0['median_subscribers_per_publisher']:.0f} -> "
     f"{c1['median_subscribers_per_publisher']:.0f}   ({c1['median_subscribers_per_publisher']/c0['median_subscribers_per_publisher']:.1f}x)")
say2(f"   mean toxicity                  {c0['mean_toxicity']:.4f} -> {c1['mean_toxicity']:.4f}"
     f"   ({100*(c1['mean_toxicity']/c0['mean_toxicity']-1):+.0f}%)")
say2(f"   centrist share, per POST       {c0['pct_center_by_post']:.1f}% -> {c1['pct_center_by_post']:.1f}%   (RISES)")
say2(f"   centrist share, per PUBLISHER  {c0['pct_center_by_publisher']:.1f}% -> {c1['pct_center_by_publisher']:.1f}%   (FALLS)")
say2("")
say2("The two weightings disagree on direction. Restricting keeps a few very")
say2("high-volume centrist outlets whose posts dominate the post-weighted share,")
say2("while removing proportionally more centrist publishers than partisan ones.")
say2("What both agree on is that the surviving sample is larger and less toxic,")
say2("i.e. a different population rather than the same one measured better.")

say2("\n-- predictor SDs by subset (each model standardises within its own subset) --")
say2("Every predictor reported in Table 2.3 is listed, not only the stable ones:")
cols = ["content_leaning", "content_extremity", "publisher_leaning", "publisher_extremity",
        "rph_delta", "toxicity", "reaction_score", "log_total_reactions", "log_author_links"]
say2(f"{'threshold':<12}" + "".join(f"{c[:18]:>20}" for c in cols))
for t in THRESHOLDS:
    s = d.filter(pl.col("author_links_history") >= t)
    say2(f"{'>= ' + str(t):<12}" + "".join(f"{float(s[c].std()):>20.4f}" for c in cols))
say2("\n-- ratio of each SD at >= 15 links to the full sample --")
_full = {c: float(d[c].std()) for c in cols}
_r15 = {c: float(d.filter(pl.col("author_links_history") >= 15)[c].std()) / _full[c] for c in cols}
for c in sorted(_r15, key=lambda k: _r15[k]):
    flag = "  <-- NOT comparable across columns" if abs(_r15[c] - 1) > 0.10 else ""
    say2(f"   {c:<22} {_r15[c]:.3f}{flag}")
say2("")
say2("Seven of the nine predictors keep their scale to within 10%, so their")
say2("standardised coefficients in Table 2.3 are comparable across columns.")
say2("Two are not:")
say2("  log_author_links  SD falls 41% - the subsets are defined BY this variable,")
say2("                    so its coefficient must be read in raw units and the sign")
say2("                    change across Table 2.3 is not an effect change.")
say2("  publisher_leaning SD falls 15% - its standardised rise across Table 2.3")
say2("                    understates the raw one (+0.165 -> +0.287 per unit), so")
say2("                    the direction holds but the magnitude is not comparable.")

with open(RES / "bp_reliability.txt", "a", encoding="utf-8") as fh:
    fh.write("\n\n" + "\n".join(lines2) + "\n")
