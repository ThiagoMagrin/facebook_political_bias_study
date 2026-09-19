"""
Rebuttal analysis - Step 3
Descriptive statistics requested by the reviewers.

  Q1b : composition of reactions (all-positive / mixed / negative-containing)
        and the arithmetic relation between reaction negativity and the
        Consensus Index.
  Q3  : distribution of ideological discrepancy across the four levels and the
        degree to which each level is dominated by a few authors.
  Q4  : agreement between the data-driven b_p and the rule-based manual coding.

Writes: rebuttal/results/descriptives.txt and the CSV tables used by the figures.
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
DATA = ROOT / "rebuttal" / "data"
RES = ROOT / "rebuttal" / "results"
RES.mkdir(parents=True, exist_ok=True)

d = pl.read_csv(DATA / "analysis_dataset.csv")
N = d.height
lines = []

def say(s=""):
    print(s)
    lines.append(str(s))

def pct(x, tot=N):
    return f"{x} ({100*x/tot:.2f}%)"

say("=" * 78)
say("ANALYTICAL SAMPLE")
say("=" * 78)
say(f"posts        : {N}")
say(f"publishers   : {d['account_name'].n_unique()}")
say(f"content items: {d['collection_name'].n_unique()}")

# =============================================================== Q1b ==========
say()
say("=" * 78)
say("Q1b - COMPOSITION OF REACTIONS")
say("=" * 78)

react_cols = ["likeCount", "loveCount", "hahaCount", "wowCount",
              "sadCount", "angryCount", "careCount", "thankfulCount"]
tot_all = {c: int(d[c].sum()) for c in react_cols}
grand = sum(tot_all.values())
say(f"\n-- share of every reaction actually cast in the corpus (n = {grand:,}) --")
for c, v in sorted(tot_all.items(), key=lambda kv: -kv[1]):
    say(f"   {c.replace('Count',''):<10} {v:>10,}  {100*v/grand:6.2f}%")

say(f"\n   Like alone accounts for {100*tot_all['likeCount']/grand:.2f}% of all reactions cast.")
say(f"   Valence-bearing reactions used by the metrics (Like+Love+Sad+Angry): "
    f"{100*(tot_all['likeCount']+tot_all['loveCount']+tot_all['sadCount']+tot_all['angryCount'])/grand:.2f}%")

say("\n-- per-post composition over the valence set (Like+Love vs Sad+Angry) --")
allpos = int(d["all_positive"].sum())
allneg = int(d["all_negative"].sum())
mixed = N - allpos - allneg
hasneg = int(d["has_negative"].sum())
say(f"   all-positive (zero Sad+Angry)      : {pct(allpos)}")
say(f"   mixed (both signs present)         : {pct(mixed)}")
say(f"   all-negative (zero Like+Love)      : {pct(allneg)}")
say(f"   containing at least one negative   : {pct(hasneg)}")
say(f"   majority-negative (share > 0.50)   : {pct(int((d['share_negative'] > 0.5).sum()))}")

fn = d["share_negative"].to_numpy()
say("\n-- distribution of the negative share f_neg = (Sad+Angry)/(Like+Love+Sad+Angry) --")
say(f"   mean {fn.mean():.4f} | median {np.median(fn):.4f} | sd {fn.std(ddof=1):.4f}")
for q in [0.10, 0.25, 0.50, 0.75, 0.90, 0.95, 0.99]:
    say(f"   p{int(q*100):<3} {np.quantile(fn, q):.4f}")
for t in [0.0, 0.01, 0.05, 0.10, 0.25, 0.50]:
    say(f"   posts with f_neg <= {t:<5}: {pct(int((fn <= t).sum()))}")

# Also over the full 8-reaction set, to show the default-Like dominance
say("\n-- per-post share of Like over ALL reactions received --")
share_like = (d["likeCount"] / d["totalReactions"]).to_numpy()
say(f"   mean {share_like.mean():.4f} | median {np.median(share_like):.4f}")
say(f"   posts where Like is the modal reaction: "
    f"{pct(int((d['likeCount'] >= d[react_cols].max_horizontal()).sum()))}")

say("\n-- arithmetic relation between negativity and the Consensus Index --")
ci = d["consensus_index"].to_numpy()
identity = np.abs(1 - 2 * fn)
say(f"   CI_i == |1 - 2 * f_neg,i| holds exactly (max |deviation| = {np.abs(ci - identity).max():.2e})")
say(f"   for the {100*(fn <= 0.5).mean():.2f}% of posts with f_neg <= 0.5 this reduces to CI = 1 - 2*f_neg,")
say("   i.e. CI is a strictly decreasing LINEAR function of the post's own negativity.")
say(f"   Spearman(CI, f_neg) = {stats.spearmanr(ci, fn).statistic:.4f}")
say(f"   Pearson (CI, f_neg) = {stats.pearsonr(ci, fn).statistic:.4f}")
say("   => at the level of a single post, 'negativity' and 'heterogeneity' are the")
say("      same quantity measured twice. The reviewer's concern is correct here.")

# How often does the fold in CI = |1 - 2*f_neg| actually engage? CI differs from
# plain negativity only above f_neg = 0.5, so this bounds the conceptual case for
# keeping CI as a separate construct.
say("\n-- how often the fold in CI = |1 - 2*f_neg| engages --")
for t in [0.5, 0.7, 0.9]:
    say(f"   f_neg > {t:<4}: {pct(int((fn > t).sum()))}")
say(f"   majority-negative AND CI > 0.5: {pct(int(((fn > 0.5) & (ci > 0.5)).sum()))}")
say(f"   maximum observed f_neg = {fn.max():.3f}")
say(f"   Pearson(CI, 1 - 2*f_neg) over the whole sample = "
    f"{stats.pearsonr(ci, 1 - 2*fn).statistic:+.3f}")
say(f"   below the fold (f_neg <= 0.5) Pearson(CI, f_neg) = "
    f"{stats.pearsonr(ci[fn <= 0.5], fn[fn <= 0.5]).statistic:+.3f}")

say("\n-- but the model's predictor is the LEAVE-ONE-OUT content-level score RS --")
rs = d["reaction_score"].to_numpy()
fn_loo = 1 - rs
say(f"   RS is computed from the OTHER posts sharing the same link; 1-RS is the")
say("   negative share of those other posts.")
say(f"   Pearson (CI, RS)                 = {stats.pearsonr(ci, rs).statistic:.4f}")
say(f"   Pearson (f_neg_own, f_neg_others)= {stats.pearsonr(fn, fn_loo).statistic:.4f}")
say(f"   Spearman(f_neg_own, f_neg_others)= {stats.spearmanr(fn, fn_loo).statistic:.4f}")
say("   The CI-RS association is therefore NOT definitional: it is the empirical")
say("   fact that the same news item draws a similar reaction mix from different")
say("   audiences. Its size is bounded by that content-level reproducibility.")

# RS leaves out the focal POST, not the focal PUBLISHER. Where a publisher
# shared the same link more than once, its own other posts are inside its RS,
# so "a different audience" does not hold for those rows. Measure it instead of
# asserting it.
#
# Measure it on the frame RS was BUILT on, which is not this one. 01 computes RS
# over the 25,473-post frame that precedes the step-3 listwise deletion, so a
# post's RS can include same-publisher posts that never entered the analytical
# sample. Counting inside these 4,584 rows described a frame RS was not computed
# on: it undercounted the general case (549 rather than 720) and overcounted the
# worst one (97 rather than 60). rs_n_contrib and rs_n_self_contrib are carried
# from that frame by 01 for exactly this reason -- a post contributes to its
# link's RS iff it drew at least one valence-bearing reaction.
_self_in_rs = pl.col("rs_n_self_contrib") > 1          # >1 counts the focal post
_all_self   = pl.col("rs_n_contrib") == pl.col("rs_n_self_contrib")
_contam_n   = d.filter(_self_in_rs).height
_selfonly_n = d.filter(_all_self).height
_pairs_n    = d.filter(_self_in_rs).select(["collection_name", "account_name"]).unique().height
say("\n-- how often is RS really 'a different audience'? --")
say("   (measured on the pre-deletion frame RS is computed over, not on the 4,584)")
say(f"   (content, publisher) pairs contributing more than one post to an RS : {_pairs_n}")
say(f"   posts whose RS includes another post by the SAME publisher: "
    f"{pct(_contam_n)}")
say(f"   posts whose RS comes ENTIRELY from the same publisher     : "
    f"{pct(_selfonly_n)}")
say("   RS is leave-one-POST-out over the content item, not leave-one-PUBLISHER-out.")
say(f"   The 'different audience' reading therefore holds for "
    f"{100*(N-_contam_n)/N:.1f}% of the sample, not all of it. For the rest")
say("   part of RS is the same page's own audience reacting to the same link, so")
say("   the reviewer's definitional-artefact concern is only partly answered there.")

# one-way ICC across content items
def icc_by_content(col: str) -> float:
    g = d.select(["collection_name", col]).to_pandas()
    grp = g.groupby("collection_name")[col]
    k, means, gm = grp.size(), grp.mean(), g[col].mean()
    ssb = float((k * (means - gm) ** 2).sum())
    ssw = float(((g[col] - g["collection_name"].map(means)) ** 2).sum())
    dfb, dfw = len(k) - 1, len(g) - len(k)
    msb, msw = ssb / dfb, ssw / dfw
    k0 = (len(g) - (k ** 2).sum() / len(g)) / dfb
    return (msb - msw) / (msb + (k0 - 1) * msw)

icc = icc_by_content("share_negative")
say(f"\n   ICC of f_neg across content items (one-way ANOVA) = {icc:.3f}")
say(f"   -> {100*icc:.1f}% of the variance in a post's negativity is attributable to")
say("      which news item is being shared, which is what RS picks up.")

# RS itself is very nearly one constant per link; the response document cites
# this against the content random intercept, so compute it here rather than
# leaving it as a number with no script behind it.
icc_rs = icc_by_content("reaction_score")
say(f"\n   ICC of RS across content items (one-way ANOVA) = {icc_rs:.3f}")
say("   -> RS is very nearly one constant per link, which is what the content")
say("      random intercept already absorbs.")

say("\n-- the association survives inside the mixed-reaction subsample --")
mx = d.filter(pl.col("reaction_composition") == "Mixed")
say(f"   mixed posts n = {mx.height}")
say(f"   Pearson (CI, RS) among mixed posts  = "
    f"{stats.pearsonr(mx['consensus_index'].to_numpy(), mx['reaction_score'].to_numpy()).statistic:.4f}")
say(f"   Spearman(CI, RS) among mixed posts  = "
    f"{stats.spearmanr(mx['consensus_index'].to_numpy(), mx['reaction_score'].to_numpy()).statistic:.4f}")
say("   Among all-positive posts CI is constant at 1.00, so they carry no")
say("   information about the CI-RS slope; the association is estimated entirely")
say("   on the mixed posts.")

d.select(["consensus_index", "share_negative", "reaction_score",
          "reaction_composition", "totalReactions"]).write_csv(RES / "fig_reaction_composition.csv")

# ================================================================ Q3 ==========
say()
say("=" * 78)
say("Q3 - DISTRIBUTION OF IDEOLOGICAL DISCREPANCY")
say("=" * 78)

order = ["Very Low", "Low", "High", "Very High"]
cuts = [d["rph_delta"].quantile(q) for q in (0.25, 0.50, 0.75)]
say(f"\nquartile cut points of Delta_b: "
    f"Q1={cuts[0]:.4f}  Q2(median)={cuts[1]:.4f}  Q3={cuts[2]:.4f}  max={d['rph_delta'].max():.4f}")

rows = []
for lev in order:
    s = d.filter(pl.col("discrepancy_level") == lev)
    n = s.height
    # account_name breaks ties: polars leaves tied groups in an unspecified
    # order, so without it top_author and the top-k shares move between runs.
    per_author = s.group_by("account_name").len().sort(
        ["len", "account_name"], descending=[True, False])
    cnt = per_author["len"].to_numpy().astype(float)
    p = cnt / cnt.sum()
    hhi = float((p ** 2).sum())
    srt = np.sort(cnt)
    gini = float((2 * np.arange(1, len(srt) + 1) - len(srt) - 1).dot(srt) / (len(srt) * srt.sum()))
    top1 = 100 * cnt[0] / n
    top5 = 100 * cnt[:5].sum() / n
    top10 = 100 * cnt[:10].sum() / n
    n_top10pct = max(1, int(np.ceil(0.10 * len(cnt))))
    share_top10pct = 100 * cnt[:n_top10pct].sum() / n
    rows.append({
        "level": lev,
        "n_posts": n,
        "pct_posts": round(100 * n / N, 2),
        "delta_min": round(s["rph_delta"].min(), 3),
        "delta_max": round(s["rph_delta"].max(), 3),
        "delta_mean": round(s["rph_delta"].mean(), 3),
        "n_authors": per_author.height,
        "n_content": s["collection_name"].n_unique(),
        "posts_per_author_median": float(np.median(cnt)),
        "posts_per_author_max": int(cnt.max()),
        "top1_author_pct": round(top1, 2),
        "top5_authors_pct": round(top5, 2),
        "top10_authors_pct": round(top10, 2),
        "top10pct_authors_pct": round(share_top10pct, 2),
        "gini_authors": round(gini, 3),
        "hhi_authors": round(hhi, 4),
        "eff_n_authors": round(1 / hhi, 1),
        "single_link_author_posts": int((s["author_links_history"] == 1).sum()),
        "mean_CI": round(s["consensus_index"].mean(), 3),
        "mean_toxicity": round(s["toxicity"].mean(), 4),
        "top_author": per_author["account_name"][0],
    })
tab = pl.DataFrame(rows)
tab.write_csv(RES / "table_discrepancy_levels.csv")
say()
with pl.Config(tbl_cols=-1, tbl_width_chars=400, fmt_str_lengths=40):
    say(str(tab.select(["level", "n_posts", "pct_posts", "delta_min", "delta_max",
                        "n_authors", "n_content", "posts_per_author_median",
                        "posts_per_author_max"])))
    say(str(tab.select(["level", "top1_author_pct", "top5_authors_pct", "top10_authors_pct",
                        "top10pct_authors_pct", "gini_authors", "hhi_authors",
                        "eff_n_authors", "top_author"])))

say("\n-- how many discrepancy levels does a publisher appear in? --")
spread = d.group_by("account_name").agg(pl.col("discrepancy_level").n_unique().alias("levels"))
say(str(spread["levels"].value_counts().sort("levels")))
say(f"   publishers present in all four levels: {int((spread['levels'] == 4).sum())}")

say("\n-- the ten publishers contributing most posts, by level --")
for lev in order:
    s = (d.filter(pl.col("discrepancy_level") == lev).group_by("account_name").len()
         .sort(["len", "account_name"], descending=[True, False]).head(10))
    say(f"\n   [{lev}]")
    for nm, c in s.iter_rows():
        say(f"      {nm[:48]:<50} {c:>4} posts ({100*c/tab.filter(pl.col('level')==lev)['n_posts'][0]:.1f}%)")

# author-concentration curve data for the figure
curve = []
for lev in order:
    s = d.filter(pl.col("discrepancy_level") == lev)
    cnt = np.sort(s.group_by("account_name").len()["len"].to_numpy())[::-1].astype(float)
    cum = np.cumsum(cnt) / cnt.sum()
    x = np.arange(1, len(cnt) + 1) / len(cnt)
    for xi, yi in zip(x, cum):
        curve.append({"level": lev, "author_frac": float(xi), "post_frac": float(yi)})
pl.DataFrame(curve).write_csv(RES / "fig_author_concentration.csv")
d.select(["rph_delta", "discrepancy_level", "account_name", "consensus_index",
          "toxicity", "author_links_history"]).write_csv(RES / "fig_discrepancy.csv")

# orientation distribution (paper Table 2 replication)
say("\n-- orientation distribution (replicates paper Table 2) --")
# value_counts() does not fix its row order, so sort before printing
say(str(d["content_side"].value_counts().with_columns((100*pl.col("count")/N).round(2).alias("pct"))
        .sort("count", descending=True)))
pub = d.group_by("account_name").agg(pl.col("publisher_side").first())
say(str(pub["publisher_side"].value_counts().with_columns((100*pl.col("count")/pub.height).round(2).alias("pct"))
        .sort("count", descending=True)))

# ================================================================ Q4 ==========
say()
say("=" * 78)
say("Q4 - FACE VALIDITY OF THE PUBLISHER BIAS SCORE")
say("=" * 78)
lab = pl.read_csv(DATA / "publisher_labels.csv")
coded = lab.filter(pl.col("manual_label").is_not_null())
say(f"\nframe: {lab.height} publishers with >= 15 links in their sharing history")
say(f"coded by the protocol: {coded.height}   not identifiable: {lab.height - coded.height}")

num = {"Left": -1, "Center": 0, "Right": 1}
man = np.array([num[x] for x in coded["manual_label"]])
auto = np.array([num[x] for x in coded["bp_side"]])
bpv = coded["bp"].to_numpy()

agree = int((man == auto).sum())
say(f"\nexact three-way agreement : {agree}/{coded.height} = {100*agree/coded.height:.1f}%")
say(f"sign reversals (L<->R)    : {int(((man*auto) == -1).sum())}")

# The protocol carries one hand exclusion (NAME_COLLISIONS in 02). It is
# load-bearing, so report the same two statistics with it removed rather than
# only under the exclusion. 02 writes the label the rest of the protocol would
# assign on its own.
_nc = lab.filter(pl.col("manual_label_no_collision_rule").is_not_null())
_nc_man = np.array([num[x] for x in _nc["manual_label_no_collision_rule"]])
_nc_auto = np.array([num[x] for x in _nc["bp_side"]])
_nc_agree = int((_nc_man == _nc_auto).sum())
_extra = _nc.height - coded.height
say(f"\nsensitivity to the one hand exclusion (NAME_COLLISIONS):")
say(f"   with the exclusion    : {agree}/{coded.height} = {100*agree/coded.height:.1f}%"
    f"   sign reversals {int(((man*auto) == -1).sum())}")
say(f"   without the exclusion : {_nc_agree}/{_nc.height} = {100*_nc_agree/_nc.height:.1f}%"
    f"   sign reversals {int(((_nc_man*_nc_auto) == -1).sum())}")
say(f"   ({_extra} page(s) re-enter; the headline 'no sign reversal' depends on this)")
for _r in lab.filter(pl.col("manual_label").is_null()
                     & pl.col("manual_label_no_collision_rule").is_not_null()).iter_rows(named=True):
    say(f"   -> {_r['account_name'][:46]:<48} would be coded "
        f"{_r['manual_label_no_collision_rule']:<6} vs b_p={_r['bp']:+.3f} -> {_r['bp_side']}")
say(f"Spearman(manual, b_p)     : rho = {stats.spearmanr(man, bpv).statistic:.3f} "
    f"(p = {stats.spearmanr(man, bpv).pvalue:.2e})")
say(f"Kendall tau-b(manual, b_p): tau = {stats.kendalltau(man, bpv).statistic:.3f} "
    f"(p = {stats.kendalltau(man, bpv).pvalue:.2e})")
say(f"Pearson (manual, b_p)     : r   = {stats.pearsonr(man, bpv).statistic:.3f}")

# Cohen's kappa (linear weights)
cats = ["Left", "Center", "Right"]
cm = np.zeros((3, 3), dtype=int)
for a, b in zip(coded["manual_label"], coded["bp_side"]):
    cm[cats.index(a), cats.index(b)] += 1
n_ = cm.sum()
po = np.trace(cm) / n_
pe = (cm.sum(0) * cm.sum(1)).sum() / n_ ** 2
kappa = (po - pe) / (1 - pe)
w = 1 - np.abs(np.subtract.outer(np.arange(3), np.arange(3))) / 2
po_w = (w * cm).sum() / n_
pe_w = (w * np.outer(cm.sum(1), cm.sum(0)) / n_).sum() / n_
kappa_w = (po_w - pe_w) / (1 - pe_w)
say(f"Cohen's kappa             : {kappa:.3f}   (linearly weighted: {kappa_w:.3f})")

say("\nconfusion matrix (rows = manual coding, columns = b_p at the +/-0.3 cut)")
say(f"{'':>10}" + "".join(f"{c:>10}" for c in cats))
for i, c in enumerate(cats):
    say(f"{c:>10}" + "".join(f"{cm[i, j]:>10}" for j in range(3)))

say("\nmean b_p by manual label")
for c in cats:
    s = coded.filter(pl.col("manual_label") == c)["bp"].to_numpy()
    if len(s):
        say(f"   {c:<7} n={len(s):>3}  mean={s.mean():+.3f}  sd={s.std(ddof=1):.3f}  "
            f"range=[{s.min():+.3f}, {s.max():+.3f}]")

say("\nby tier")
for t in sorted(coded["tier"].unique()):
    s = coded.filter(pl.col("tier") == t)
    a = int((np.array([num[x] for x in s["manual_label"]]) == np.array([num[x] for x in s["bp_side"]])).sum())
    say(f"   {t:<18} {a}/{s.height} = {100*a/s.height:.1f}%")

part = coded.filter(pl.col("manual_label") != "Center")
pm = np.array([num[x] for x in part["manual_label"]])
pa = np.array([num[x] for x in part["bp_side"]])
say(f"\nrestricted to the {part.height} publishers coded Left or Right:")
say(f"   exact agreement  : {int((pm==pa).sum())}/{part.height} = {100*(pm==pa).mean():.1f}%")
say(f"   correct side of 0: {int((np.sign(part['bp'].to_numpy())==pm).sum())}/{part.height} = "
    f"{100*(np.sign(part['bp'].to_numpy())==pm).mean():.1f}%")
say(f"   sign reversals   : {int(((pm*pa)==-1).sum())}")

say("\ndisagreements")
for r in coded.filter(pl.col("manual_label") != pl.col("bp_side")).sort("bp").iter_rows(named=True):
    say(f"   {r['account_name'][:46]:<48} manual={r['manual_label']:<7} b_p={r['bp']:+.3f} -> {r['bp_side']:<7} ({r['links_history']} links)")

coded.write_csv(RES / "fig_face_validity.csv")



# ============================================ PREMISE CHECKS (appended) =======
lines2 = []
def say2(s=""):
    print(s); lines2.append(str(s))

say2("=" * 78)
say2("PREMISE CHECKS - are the two proposed confounders related as the reviewer expects?")
say2("=" * 78)

ltr = d["log_total_reactions"].to_numpy()
lal = d["log_author_links"].to_numpy()
dlt = d["rph_delta"].to_numpy()
tox = d["toxicity"].to_numpy()

say2("\n(i) 'a wider audience makes different reactions more likely'")
_rho_ci = stats.spearmanr(ltr, ci).statistic
say2(f"    Spearman(log total reactions, CI)       = {_rho_ci:+.3f} "
     f"(p = {stats.spearmanr(ltr, ci).pvalue:.2e})")
say2(f"    Spearman(log total reactions, f_neg)    = {stats.spearmanr(ltr, fn).statistic:+.3f}")
# state the direction the sign actually shows, and grade the size from the value
say2(f"    -> {'correct in direction' if _rho_ci < 0 else 'OPPOSITE to the expectation'}: "
     f"bigger audiences are {'more' if _rho_ci < 0 else 'less'} heterogeneous, and the")
say2(f"       association is {'weak' if abs(_rho_ci) < 0.3 else 'substantial'} "
     f"(|rho| = {abs(_rho_ci):.3f}).")
say2("    median CI by decile of total reactions:")
dec = d.with_columns(((pl.col("totalReactions").rank("ordinal") - 1) * 10 // N).alias("dec"))
for r in dec.group_by("dec").agg(
        pl.col("totalReactions").median().alias("med_reactions"),
        pl.col("consensus_index").median().alias("med_CI"),
        pl.col("share_negative").median().alias("med_fneg"),
        pl.len()).sort("dec").iter_rows():
    say2(f"      D{r[0]+1:<2} median reactions {r[1]:>8.0f}   median CI {r[2]:.3f}   median f_neg {r[3]:.3f}   n={r[4]}")

say2("\n(ii) 'an author who shared only one link cannot be misaligned'")
say2(f"    Spearman(log links shared by author, Delta_b) = "
     f"{stats.spearmanr(lal, dlt).statistic:+.3f} (p = {stats.spearmanr(lal, dlt).pvalue:.2e})")
au = d.group_by("account_name").agg(pl.col("author_links_history").first())
_auh = au["author_links_history"].to_numpy()
_poh = d["author_links_history"].to_numpy()
say2("    size of the sharing history b_p is estimated from:")
say2(f"      per PUBLISHER: mean {_auh.mean():.1f} links, median {np.median(_auh):.0f}, "
     f"max {int(_auh.max())}")
say2(f"      per POST     : mean {_poh.mean():.1f} links, median {np.median(_poh):.0f}")
say2(f"      posts from publishers with fewer than 5 links: "
     f"{int((_poh < 5).sum())} ({100*(_poh < 5).mean():.1f}% of the sample)")
say2(f"    publishers with a single link in their history: "
     f"{int((au['author_links_history']==1).sum())}/{au.height} "
     f"({100*(au['author_links_history']==1).mean():.1f}%), contributing "
     f"{int((d['author_links_history']==1).sum())} posts "
     f"({100*(d['author_links_history']==1).mean():.1f}% of the sample)")
say2("    Delta_b and |b_p| by size of the sharing history:")
b = d.with_columns(
    pl.when(pl.col("author_links_history") == 1).then(pl.lit("1"))
    .when(pl.col("author_links_history") == 2).then(pl.lit("2"))
    .when(pl.col("author_links_history") <= 5).then(pl.lit("3-5"))
    .when(pl.col("author_links_history") <= 20).then(pl.lit("6-20"))
    .otherwise(pl.lit(">20")).alias("bin"))
for r in b.group_by("bin").agg(
        pl.len().alias("n"), pl.col("rph_delta").mean().alias("delta"),
        pl.col("publisher_extremity").mean().alias("pub_ext"),
        pl.col("consensus_index").mean().alias("CI")).sort("n", descending=True).iter_rows():
    say2(f"      history = {r[0]:<5} n={r[1]:>5}   mean Delta_b {r[2]:.3f}   mean |b_p| {r[3]:.3f}   mean CI {r[4]:.3f}")
say2("    NOTE the direction of the artefact. With one shared link the estimator")
say2("    returns b_p in {-1, 0, +1} by construction, so such publishers are pinned")
say2("    to the extremes of the scale rather than to zero discrepancy:")
sl = d.filter(pl.col("author_links_history") == 1)
say2(f"      among single-link publishers, |b_p| = 1 for "
     f"{100*(sl['publisher_extremity'] > 0.99).mean():.1f}% of posts and b_p = 0 for "
     f"{100*(sl['publisher_extremity'] < 0.01).mean():.1f}%")
say2("    This is why model A5 re-estimates the model without them.")

# Describe the number that comes out, do not assert one in advance: the heading
# used to read "barely correlated with each other" above a Spearman of +0.370.
_rho_controls = stats.spearmanr(ltr, lal).statistic
_strength = ("negligibly" if abs(_rho_controls) < 0.1 else
             "weakly" if abs(_rho_controls) < 0.3 else
             "moderately" if abs(_rho_controls) < 0.5 else "strongly")
say2(f"\n(iii) how the two proposed controls relate to each other and to the outcome")
say2(f"    Spearman(log total reactions, log author links) = {_rho_controls:+.3f}")
say2(f"    Spearman(log total reactions, Delta_b)          = {stats.spearmanr(ltr, dlt).statistic:+.3f}")
say2(f"    Spearman(log author links, CI)                  = {stats.spearmanr(lal, ci).statistic:+.3f}")
say2(f"    -> the two controls are {_strength} correlated with each other; the")
say2("       collinearity that matters for the fit is reported as VIF in models.txt.")



# ------------------------------- CI by decile of RS (support check, appended) --
lines3 = []
def say3(s=""):
    print(s); lines3.append(str(s))

say3("=" * 78)
say3("CI BY BIN OF THE REACTION SCORE - how well is the negative end sampled?")
say3("=" * 78)
say3(f"{'RS bin':<14}{'n':>7}{'mean CI':>10}{'median CI':>12}")
# Bins are left-closed [lo, hi), matching 05_figures.R, which now passes
# right = FALSE to cut() so the figure and this table describe the same bins.
BIG_BIN = 100
edges = np.arange(0, 1.0001, 0.1)
# How many posts the bin convention actually decides. 05_figures.R passes
# right = FALSE to cut() to match; the response document cites this count as the
# reason the two sides must agree, so it is computed here rather than asserted.
_on_edge = int(sum(np.isclose(rs, e).sum() for e in edges))
say3(f"posts whose RS falls exactly on a decile boundary: {_on_edge} "
     f"(left-closed bins [lo, hi), matching 05_figures.R)")
_bins = []
for lo, hi in zip(edges[:-1], edges[1:]):
    m = (rs >= lo) & (rs < hi if hi < 1 else rs <= 1.0)
    if m.sum() == 0:
        say3(f"[{lo:.1f},{hi:.1f})      0         -           -")
        continue
    say3(f"[{lo:.1f},{hi:.1f}){m.sum():>10}{ci[m].mean():>10.3f}{np.median(ci[m]):>12.3f}")
    _bins.append({"lo": lo, "n": int(m.sum()), "mean_ci": float(ci[m].mean())})
say3(f"\nposts with RS < 0.2: {int((rs < 0.2).sum())}  |  RS < 0.3: {int((rs < 0.3).sum())}  "
     f"|  RS < 0.4: {int((rs < 0.4).sum())} ({100*(rs < 0.4).mean():.1f}% of the sample)")

# Check the monotonicity claim instead of asserting it, and read the bin sizes
# off the table rather than restating remembered numbers.
_big = [b for b in _bins if b["n"] > BIG_BIN]
_small = [b for b in _bins if b["n"] <= BIG_BIN]
_mono = all(a["mean_ci"] < b["mean_ci"] for a, b in zip(_big, _big[1:]))
_cut = _big[0]["lo"]
_share_big = 100 * sum(b["n"] for b in _big) / N
say3(f"Across every bin holding more than {BIG_BIN} posts (RS >= {_cut:.1f}, "
     f"{_share_big:.1f}% of the sample) mean CI")
say3(f"{'increases monotonically' if _mono else 'does NOT increase monotonically'} with RS, "
     f"from {_big[0]['mean_ci']:.2f} to {_big[-1]['mean_ci']:.2f}.")
say3(f"The {len(_small)} bin(s) below RS = {_cut:.1f} hold "
     f"{', '.join(str(b['n']) for b in _small)} posts and are too noisy to order.")
say3("The strongly negative end of RS is too sparse to test for a reversal, so no")
say3("claim is made about it; a smoother fitted there would extrapolate from the")
say3(f"{_bins[0]['n']} post(s) in the lowest populated bin.")

# One write, at the end. Writing this file in three passes meant a crash
# between them left a truncated descriptives.txt that still looked complete --
# and the response document quotes numbers from every section of it.
(RES / "descriptives.txt").write_text(
    "\n".join(lines) + "\n\n" + "\n".join(lines2) + "\n\n" + "\n".join(lines3) + "\n",
    encoding="utf-8")
print(f"\n\nwritten: {RES / 'descriptives.txt'}")
