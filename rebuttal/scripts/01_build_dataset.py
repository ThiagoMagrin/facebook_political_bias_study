"""
Rebuttal analysis - Step 1
Rebuilds the analytical dataset from the raw sources, reproducing the pipeline of
notebooks/data_collection.py, and adds the variables required by the reviewers:

  * post popularity            -> totalReactions (all reaction types) and log transform
  * author activity            -> number of posts / unique links shared by the author
                                  (plus author_bp_links, the subset of those links
                                   that actually carry a bias score and so enter b_p)
  * reaction composition       -> positive / negative / mixed classification
  * leaning vs. extremity      -> signed bias and |bias| for content and publisher
  * categorical orientation    -> Left / Center / Right
  * discrepancy quartiles      -> Very Low / Low / High / Very High

Output: rebuttal/data/analysis_dataset.csv
"""
import os
import polars as pl
from pathlib import Path

# Repository root: PROJECT_ROOT if set, otherwise derived from this file's own
# location (scripts live in <root>/rebuttal/scripts/). Mirrors the resolution in
# _common.R so the Python and R halves of the pipeline relocate together.
ROOT = Path(os.environ.get("PROJECT_ROOT") or Path(__file__).resolve().parents[2])
assert (ROOT / "rebuttal" / "scripts").is_dir(), f"not a repository root: {ROOT}"
DATA = ROOT / "data"
OUT = ROOT / "rebuttal" / "data"
OUT.mkdir(parents=True, exist_ok=True)

EPS = 1e-6

RES = ROOT / "rebuttal" / "results"
RES.mkdir(parents=True, exist_ok=True)

# The Table 1 ladder and the reproduction check are quoted in the response
# document, which claims every number can be read out of a file the pipeline
# writes. Console output does not satisfy that, so collect and write it, the
# way 03_descriptives.py and 07_bp_reliability.py already do.
_log = []
def say(s=""):
    print(s)
    _log.append(str(s))

# ---------------------------------------------------------------- 1. raw posts
posts = pl.read_csv(DATA / "data_mongodb.csv")
say(f"[1] deduplicated posts (paper Table 1, step 2): {posts.height}")

# ------------------------------------------------- 2. publisher bias b_p (rph_user)
# Computed over the FULL deduplicated history, exactly as in the original pipeline.
counts = posts.group_by("account_name").agg(
    pl.col("rph_link").filter(pl.col("rph_link") >= 0.3).count().alias("blue_count"),
    pl.col("rph_link").filter(pl.col("rph_link") <= -0.3).count().alias("red_count"),
    pl.col("rph_link").filter((pl.col("rph_link") > -0.3) & (pl.col("rph_link") < 0.3)).count().alias("gray_count"),
)
metrics = (
    counts.with_columns(total_count=pl.col("blue_count") + pl.col("red_count") + pl.col("gray_count"))
    .with_columns(
        W_L=(pl.col("red_count") + pl.col("gray_count")) / (pl.col("total_count") + EPS),
        W_N=(pl.col("red_count") + pl.col("blue_count")) / (pl.col("total_count") + EPS),
        W_R=(pl.col("blue_count") + pl.col("gray_count")) / (pl.col("total_count") + EPS),
    )
    .with_columns(
        numerator=(pl.col("blue_count") * pl.col("W_R") - pl.col("red_count") * pl.col("W_L")),
        denominator=(pl.col("red_count") * pl.col("W_L")
                     + pl.col("gray_count") * pl.col("W_N")
                     + pl.col("blue_count") * pl.col("W_R") + EPS),
    )
    .with_columns(rph_user=pl.col("numerator") / pl.col("denominator"))
    .select(["account_name", "rph_user"])
)

# --------------------------------------------- 3. AUTHOR ACTIVITY (reviewer 1)
# "total number of links shared by the author" -- measured on the same history
# that produces b_p, i.e. the full deduplicated corpus.
#
# Two different counts are needed and they are NOT the same variable:
#   author_links_history -- every distinct link the publisher shared. This is
#       literally the quantity reviewer 1 asked to control for, so it is the one
#       that enters the models as log_author_links.
#   author_bp_links      -- distinct links carrying a non-null rph_link, i.e.
#       the links b_p is actually estimated from. The b_p formula counts
#       categories with .count(), which drops nulls, so a link with no bias
#       score contributes nothing to b_p.
# They differ for 36 publishers. 08_threshold_models.R thresholds on
# author_links_history and describes it as "the links b_p rests on"; carrying
# both makes that gap visible instead of leaving the two scripts disagreeing
# about what the same number means.
activity_history = posts.group_by("account_name").agg(
    pl.len().alias("author_posts_history"),
    pl.col("collection_name").n_unique().alias("author_links_history"),
    pl.col("collection_name").filter(pl.col("rph_link").is_not_null())
      .n_unique().alias("author_bp_links"),
)

df = (
    posts.join(metrics, on="account_name", how="left")
    .with_columns((pl.col("rph_link") - pl.col("rph_user")).abs().alias("rph_delta"))
    .join(activity_history, on="account_name", how="left")
)

# ------------------------------------------------------- 4. news text + toxicity
links_text = pl.read_csv(DATA / "urls_text.csv").select("collection_name", "text")
df = df.join(links_text, on="collection_name").rename({"text": "link_text", "message": "post_text"})
# This is NOT Table 1 step 3. The join is on collection_name and every post has
# a collection, so it drops nothing: a post whose article could not be scraped
# keeps its row with a null link_text and is removed further down, in the
# listwise deletion. That deletion is the real step 3 and is reported there.
say(f"[2] after joining news text (join drops nothing; nulls removed at step 3): {df.height}")

tox = pl.read_csv(DATA / "data_toxicity.csv")
df = df.join(tox, on=["collection_name", "account_name", "post_text"])

# ------------------------------------------- 5. reaction score & consensus index
df = (
    df.with_columns([
        (pl.col("likeCount") + pl.col("loveCount")).alias("positive_reactions"),
        (pl.col("sadCount") + pl.col("angryCount")).alias("negative_reactions"),
    ])
    .with_columns([
        (pl.col("positive_reactions") + pl.col("negative_reactions")).alias("four_reactions"),
        pl.col("positive_reactions").sum().over("collection_name").alias("pos_coll"),
        pl.col("negative_reactions").sum().over("collection_name").alias("neg_coll"),
    ])
    .with_columns([
        (pl.col("pos_coll") - pl.col("positive_reactions")).alias("loo_pos"),
        (pl.col("neg_coll") - pl.col("negative_reactions")).alias("loo_neg"),
        # RS is built on THIS frame -- the one before the step-3 listwise
        # deletion -- so the posts feeding a post's RS include ones that never
        # reach the analytical sample. Count them while that frame still exists.
        # 03_descriptives.py reports the leave-one-out contamination of section
        # 3.3 and cannot measure it from the 4,584-row output: doing so there
        # described a frame RS was not computed on, undercounting the general
        # case and overcounting the worst one.
        pl.len().over("collection_name").alias("link_n_posts"),
        (pl.col("four_reactions") > 0).sum()
          .over("collection_name").alias("rs_n_contrib"),
        (pl.col("four_reactions") > 0).sum()
          .over(["collection_name", "account_name"]).alias("rs_n_self_contrib"),
    ])
    .with_columns([
        # Leave-one-POST-out over the content item, not leave-one-PUBLISHER-out:
        # the focal post is excluded, but other posts by the SAME publisher on
        # the same link are not. So RS is not always "a different audience" --
        # where a publisher shared a link more than once it partly reflects that
        # publisher's own audience. 03_descriptives.py quantifies how often.
        (pl.col("loo_pos") / (pl.col("loo_pos") + pl.col("loo_neg"))).alias("reaction_score").fill_nan(None),
        ((pl.col("positive_reactions") - pl.col("negative_reactions")).abs()
         / pl.col("four_reactions")).alias("consensus_index"),
    ])
    .drop(["pos_coll", "neg_coll", "loo_pos", "loo_neg"])
)

# The listwise deletion below IS the manuscript's Table 1 step 3, and it is not
# only "inaccessible text": four distinct conditions remove rows here, and two
# of them condition the analytical sample in ways the paper does not state.
# link_text in particular is dropped from the output and enters no model, so its
# nulls are a listwise deletion on a variable with no analytic role. Report every
# condition rather than folding them into one unexplained count.
_before = df.height
_rs_null = pl.col("reaction_score").is_null()
_reasons = {
    "no scraped article text (link_text null)": df["link_text"].null_count(),
    "no link bias score (rph_link null)": df["rph_link"].null_count(),
    "zero Like+Love+Sad+Angry -> CI undefined": df.filter(pl.col("four_reactions") == 0).height,
    # RS is undefined in two distinct ways and they are not the same statement
    # about the sample. Reporting both as "shared only once" overstated the
    # first and hid the second: the condition the analytical sample actually
    # imposes is that the link carries at least one OTHER post with a valence
    # reaction, which is stricter than "shared at least twice".
    "no other post shares the link -> leave-one-out RS undefined":
        df.filter(_rs_null & (pl.col("link_n_posts") == 1)).height,
    "other posts on the link drew no valence reaction -> RS undefined":
        df.filter(_rs_null & (pl.col("link_n_posts") > 1)).height,
}
df = df.drop_nulls().drop_nans()
say(f"[3] after listwise deletion (paper Table 1, step 3): {df.height}  (-{_before - df.height})")
for _why, _n in _reasons.items():
    say(f"      {_why:<64} {_n}")
say("      (conditions overlap, so they do not sum to the total removed)")

# ------------------------------------------------------------------ 6. topics
topics = pl.read_csv(DATA / "zero_shot_results/resultado_zero_shot_MoritzLaurer_mDeBERTa-v3-base-xnli-multilingual-nli-2mil7.csv")
df = df.join(topics.drop(["text", "clean_text", "topic"]), on="collection_name")
df = df.rename({
    "economia": "Economy", "educação": "Education", "saúde": "Health",
    "segurança": "Security", "cultura": "Culture", "religião": "Religion",
    "desinformação": "Disinformation", "eleição": "Election",
    "politica": "Politics", "corrupção": "Corruption",
})

# -------------------------------------------------- 7. domain + popularity filter
# The manuscript's Table 1 lists three filtering steps and does not mention this
# domain exclusion; it is folded into the step-4 count. Applied to the step-3
# frame, the >= 50 reactions cut alone leaves 6,983 posts, so this filter removes
# the other 2,399. Printed separately below so the ladder reconciles.
# Printed, not left to be worked out by hand: the response document reports
# what the >= 50 cut removes on its own, so the two filters can be separated.
_only50 = df.filter(pl.col("totalReactions") >= 50).height
say(f"[3b] step-3 frame with the >= 50 reactions cut ALONE: {_only50}")
df = df.filter(~(
    pl.col("link").str.contains(r"g1\.globo\.com")
    | pl.col("link").str.contains(r"jota\.info")
    | pl.col("link").str.contains(r"epoca\.globo\.com")
    | pl.col("link").str.contains(r"https://band\.uol\.com\.br/eleicoes/")
    | pl.col("link").str.contains(r"https://redetv\.uol\.com\.br/aovivo")
))
say(f"[4] after excluding the five hand-listed domains: {df.height}")
df = df.filter(pl.col("totalReactions") >= 50)
say(f"[5] final analytical sample (paper Table 1, step 4): {df.height}")
say(f"      of the {_only50} posts the >= 50 cut alone leaves, "
      f"the domain exclusion removes {_only50 - df.height}")

# ============================== REVIEWER-REQUESTED DERIVED VARIABLES ==========
df = df.with_columns([
    # --- post popularity -----------------------------------------------------
    pl.col("totalReactions").log().alias("log_total_reactions"),
    pl.col("four_reactions").log().alias("log_four_reactions"),

    # --- author activity -----------------------------------------------------
    pl.col("author_links_history").log().alias("log_author_links"),
    pl.col("author_posts_history").log().alias("log_author_posts"),

    # --- reaction composition ------------------------------------------------
    (pl.col("negative_reactions") / pl.col("four_reactions")).alias("share_negative"),
    (pl.col("negative_reactions") == 0).alias("all_positive"),
    (pl.col("positive_reactions") == 0).alias("all_negative"),
    (pl.col("negative_reactions") > 0).alias("has_negative"),

    # --- leaning / extremity decomposition -----------------------------------
    pl.col("rph_link").alias("content_leaning"),
    pl.col("rph_link").abs().alias("content_extremity"),
    pl.col("rph_user").alias("publisher_leaning"),
    pl.col("rph_user").abs().alias("publisher_extremity"),
])

# strictly-positive share of the full reaction set (8 reaction types)
df = df.with_columns(
    (pl.col("negative_reactions") / pl.col("totalReactions")).alias("share_negative_all")
)

def side(col: str) -> pl.Expr:
    return (
        pl.when(pl.col(col) <= -0.3).then(pl.lit("Left"))
        .when(pl.col(col) >= 0.3).then(pl.lit("Right"))
        .otherwise(pl.lit("Center"))
    )

df = df.with_columns([
    side("rph_link").alias("content_side"),
    side("rph_user").alias("publisher_side"),
    pl.when(pl.col("negative_reactions") == 0).then(pl.lit("All-positive"))
      .when(pl.col("positive_reactions") == 0).then(pl.lit("All-negative"))
      .otherwise(pl.lit("Mixed")).alias("reaction_composition"),
])

# --- discrepancy quartiles ---------------------------------------------------
q = df["rph_delta"].quantile
cuts = [q(0.25), q(0.50), q(0.75)]
say(f"[6] rph_delta quartile cut points: {[round(c, 4) for c in cuts]}")
df = df.with_columns(
    pl.when(pl.col("rph_delta") <= cuts[0]).then(pl.lit("Very Low"))
    .when(pl.col("rph_delta") <= cuts[1]).then(pl.lit("Low"))
    .when(pl.col("rph_delta") <= cuts[2]).then(pl.lit("High"))
    .otherwise(pl.lit("Very High")).alias("discrepancy_level")
)

# --- author activity inside the analytical sample ----------------------------
sample_activity = df.group_by("account_name").agg(
    pl.len().alias("author_posts_sample"),
    pl.col("collection_name").n_unique().alias("author_links_sample"),
)
df = df.join(sample_activity, on="account_name", how="left")

# ============================== VALIDATION AGAINST data_final.csv =============
ref = pl.read_csv(DATA / "data_final.csv")
say("\n--- reproduction check against data/data_final.csv ---")
say(f"reference rows: {ref.height} | rebuilt rows: {df.height}")
assert ref.height == df.height, f"row count differs: {ref.height} vs {df.height}"

# data_final.csv has no unique row key -- (collection_name, account_name, link)
# repeats for publishers that shared the same link more than once -- so rows are
# matched by sorting BOTH frames on every shared column. Comparing each column's
# sorted values separately would only prove the marginals agree, which is weaker:
# it would pass even if the values were reshuffled across rows.
shared = [c for c in ref.columns if c in df.columns]
key = [c for c in shared if ref[c].dtype == pl.String]
num = [c for c in shared if c not in key]
ref_s = ref.select(shared).sort(shared)
df_s = df.select(shared).sort(shared)

for c in key:
    assert ref_s[c].to_list() == df_s[c].to_list(), f"row-aligned mismatch in {c}"
max_dev = 0.0
for c in num:
    dev = float((ref_s[c] - df_s[c]).abs().max())
    max_dev = max(max_dev, dev)
    assert dev < 1e-9, f"row-aligned mismatch in {c}: max |diff| = {dev}"
say(f"  rows match as a multiset over all {len(shared)} shared columns")
say(f"  {len(key)} text columns identical after row alignment")
say(f"  {len(num)} numeric columns agree to max |diff| = {max_dev:.2e}")
say(f"  n publishers  reference={ref['account_name'].n_unique()} rebuilt={df['account_name'].n_unique()}")
say(f"  n content     reference={ref['collection_name'].n_unique()} rebuilt={df['collection_name'].n_unique()}")

keep = [
    "collection_name", "link", "account_name", "post_text",
    "rph_link", "rph_user", "rph_delta",
    "content_leaning", "content_extremity", "publisher_leaning", "publisher_extremity",
    "content_side", "publisher_side", "discrepancy_level",
    "toxicity", "reaction_score", "consensus_index",
    "likeCount", "loveCount", "wowCount", "hahaCount", "sadCount", "angryCount",
    "thankfulCount", "careCount", "totalReactions", "subscriberCount",
    "positive_reactions", "negative_reactions", "four_reactions",
    "rs_n_contrib", "rs_n_self_contrib",
    "share_negative", "share_negative_all", "reaction_composition",
    "all_positive", "all_negative", "has_negative",
    "log_total_reactions", "log_four_reactions",
    "author_posts_history", "author_links_history", "author_bp_links",
    "log_author_links", "log_author_posts",
    "author_posts_sample", "author_links_sample",
    "Economy", "Education", "Health", "Security", "Culture", "Religion",
    "Disinformation", "Election", "Politics", "Corruption",
]
df.select(keep).write_csv(OUT / "analysis_dataset.csv")
say(f"\nwritten: {OUT / 'analysis_dataset.csv'}  ({df.height} rows)")

(RES / "build_log.txt").write_text("\n".join(_log) + "\n", encoding="utf-8")
print(f"written: {RES / 'build_log.txt'}")
