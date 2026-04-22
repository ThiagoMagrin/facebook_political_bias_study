import marimo

__generated_with = "0.17.0"
app = marimo.App(width="full")


@app.cell
def _():
    import marimo as mo
    import pymongo
    import polars as pl
    import pandas as pd
    import numpy as np
    from newspaper import Article
    from time import sleep
    import os
    from googleapiclient import discovery
    import json
    from urllib.parse import urlparse
    from sklearn.metrics import precision_recall_curve, f1_score, precision_score, recall_score, r2_score
    import matplotlib.pyplot as plt
    from sklearn.linear_model import LinearRegression
    return (
        Article,
        LinearRegression,
        discovery,
        f1_score,
        mo,
        np,
        os,
        pd,
        pl,
        plt,
        precision_recall_curve,
        precision_score,
        pymongo,
        r2_score,
        recall_score,
        sleep,
        urlparse,
    )


@app.cell(hide_code=True)
def _(mo):
    mo.md(r"""## Collecting Facebook data from MongoDB""")
    return


@app.cell
def _(pl, pymongo):
    client = pymongo.MongoClient("mongodb://localhost:27017/")
    db = client["crowd_tangle"]
    df_rph = pl.read_csv("../data/links_rph_brazil.csv", columns=["collection_name", "RP(H)", "retweeted_url"])
    return db, df_rph


@app.cell
def _(db, pl, urlparse):
    def get_link_info(df_rph, collection_name):
        _df_rph_filtered = df_rph.filter(pl.col("collection_name") == collection_name)

        if not _df_rph_filtered.is_empty():
            return _df_rph_filtered.select(
                "RP(H)", 
                "retweeted_url"
            ).to_dicts()[0]
        else: 
            return None

    def get_documents_data(collection_name):
        pipeline = [
            {
                "$match": {
                    "platform": "Facebook",
                    "message": {"$exists": True}
                }
            },
            {
                "$project": {
                    "_id": 0,
                    "message": 1,
                    "account_name": {"$ifNull": ["$account.name", None]},
                    "subscriberCount": {"$ifNull": ["$account.subscriberCount", None]},
                    "likeCount": {"$ifNull": ["$statistics.actual.likeCount", None]},
                    "shareCount": {"$ifNull": ["$statistics.actual.shareCount", None]},
                    "commentCount": {"$ifNull": ["$statistics.actual.commentCount", None]},
                    "loveCount": {"$ifNull": ["$statistics.actual.loveCount", None]},
                    "wowCount": {"$ifNull": ["$statistics.actual.wowCount", None]},
                    "hahaCount": {"$ifNull": ["$statistics.actual.hahaCount", None]},
                    "sadCount": {"$ifNull": ["$statistics.actual.sadCount", None]},
                    "angryCount": {"$ifNull": ["$statistics.actual.angryCount", None]},
                    "thankfulCount": {"$ifNull": ["$statistics.actual.thankfulCount", None]},
                    "careCount": {"$ifNull": ["$statistics.actual.careCount", None]},
                }
            }
        ]
        return db[collection_name].aggregate(pipeline)

    def get_domain(link: str) -> str:
        if not link.startswith(('http://', 'https://')):
            link = 'http://' + link

        parsed = urlparse(link)
        domain = parsed.netloc

        if domain.startswith("www."):
            domain = domain[4:]

        return domain
    return get_documents_data, get_domain, get_link_info


@app.cell
def _(mo):
    posts_button = mo.ui.run_button()
    posts_button
    return (posts_button,)


@app.cell
def _(
    db,
    df_rph,
    get_documents_data,
    get_domain,
    get_link_info,
    mo,
    pl,
    posts_button,
):
    mo.stop(not posts_button.value)

    all_dfs = []

    reaction_cols = [
        "likeCount", "loveCount", "wowCount", "hahaCount", "sadCount", "angryCount", "thankfulCount", "careCount"
    ]

    for collection_name in db.list_collection_names():
        link_info = get_link_info(df_rph, collection_name)
        if link_info is None:
            continue

        _documents_data = get_documents_data(collection_name)

        df_collection = pl.DataFrame(_documents_data)

        if df_collection.is_empty():
            continue

        df_collection = df_collection.with_columns(
            pl.lit(link_info["RP(H)"]).alias("rph_link"),
            pl.lit(link_info["retweeted_url"]).alias("link"),
            pl.lit(collection_name).alias("collection_name"),
            pl.sum_horizontal(reaction_cols).alias("totalReactions"),
        )

        all_dfs.append(df_collection)

    df_posts_duplicated = pl.concat(all_dfs).with_columns([pl.col("link").map_elements(get_domain, return_dtype=pl.String).alias("dominio")])
    df_posts_duplicated.write_csv("../data/data_mongodb_duplicated.csv")
    df_posts_duplicated
    return


@app.cell
def _(pl):
    df_posts_duplicated_file = pl.read_csv("../data/data_mongodb_duplicated.csv")
    _df_posts = df_posts_duplicated_file.sort("totalReactions", descending=True).unique(subset=["account_name", "message"], maintain_order=True, keep="first")
    _df_posts.write_csv("../data/data_mongodb.csv")
    return


@app.cell
def _(pl):
    #df_posts.write_csv("../data/data_mongodb.csv")
    df_posts = pl.read_csv("../data/data_mongodb.csv")
    df_posts
    return (df_posts,)


@app.cell(hide_code=True)
def _(mo):
    mo.md(r"""## Calculating publisher political bias""")
    return


@app.cell
def _(df_posts, pl):
    _counts_df = df_posts.group_by('account_name').agg(
        pl.col('rph_link').filter(pl.col('rph_link') >= 0.3).count().alias('blue_count'),
        pl.col('rph_link').filter(pl.col('rph_link') <= -0.3).count().alias('red_count'),
        pl.col('rph_link').filter((pl.col('rph_link') > -0.3) & (pl.col('rph_link') < 0.3)).count().alias('gray_count')
    )

    epsilon = 1e-6

    metrics_df = _counts_df.with_columns(
        total_count = pl.col('blue_count') + pl.col('red_count') + pl.col('gray_count')
    ).with_columns(
        W_L = (pl.col('red_count') + pl.col('gray_count')) / (pl.col('total_count') + epsilon),
        W_N = (pl.col('red_count') + pl.col('blue_count')) / (pl.col('total_count') + epsilon),
        W_R = (pl.col('blue_count') + pl.col('gray_count')) / (pl.col('total_count') + epsilon)
    ).with_columns(
        numerator = (pl.col('blue_count') * pl.col('W_R') - pl.col('red_count') * pl.col('W_L')),
        denominator = (pl.col('red_count') * pl.col('W_L') + pl.col('gray_count') * pl.col('W_N') + pl.col('blue_count') * pl.col('W_R') + epsilon)
    ).with_columns(
        rph_user = pl.col('numerator') / pl.col('denominator')
    ).select(['account_name', 'rph_user'])

    df_posts_with_rph_metrics = df_posts.join(metrics_df, on='account_name', how='left').with_columns(
        abs(pl.col("rph_link") - pl.col("rph_user")).alias("rph_delta")
    )
    return df_posts_with_rph_metrics, epsilon


@app.cell(hide_code=True)
def _(mo):
    mo.md(r"""## Collecting news text""")
    return


@app.cell
def _(mo):
    news_collection = mo.ui.run_button()
    news_collection
    return (news_collection,)


@app.cell
def _(Article, df_posts_with_rph_user, mo, news_collection, pl, sleep):
    mo.stop(not news_collection.value)

    def news_text(url):
        if not isinstance(url, str) or not url.startswith(('http://', 'https://')):
            print("It isn't a link")
            return None

        print("Waiting 5 seconds...")
        sleep(5)

        print(f"Getting data from: {url}")
        try:
            article = Article(url)
            article.download()
            article.parse()
            return article.text
        except Exception as e:
            print(f"Error: {e}")
            return None

    df_unique_links = df_posts_with_rph_user.unique("link").select("link")

    df_scraped_text = df_unique_links.with_columns(
        pl.col("link").map_elements(
            news_text, 
            return_dtype=pl.String
        ).alias("news_text")
    )

    df_posts_with_link_text = df_posts_with_rph_user.join(df_scraped_text, on="link", how="left").rename({"text": "link_text", "message": "post_text"})
    return (df_posts_with_link_text,)


@app.cell
def _(df_posts_with_rph_metrics, pl):
    links_test = pl.read_csv("../data/urls_text.csv")
    df_posts_with_content_text = df_posts_with_rph_metrics.join(links_test.select("collection_name", "text"), on="collection_name").rename({"text": "link_text", "message": "post_text"})
    return (df_posts_with_content_text,)


@app.cell(hide_code=True)
def _(mo):
    mo.md(r"""## Perspective API to measure toxicity in posts data""")
    return


@app.cell
def _(sleep):
    def get_perspective_api_score(text, perspective_client):
        sleep(1.01)
        if not isinstance(text, str) or not text.strip():
            return {
                'toxicity': None,
                'severe_toxicity': None,
                'identity_attack': None,
                'insult': None,
                'profanity': None,
                'threat': None
            }

        analyze_request = {
            'comment': { 'text': text },
            'languages': ['pt'],
            'requestedAttributes': {
                'TOXICITY': {}, 
                'SEVERE_TOXICITY': {}, 
                'IDENTITY_ATTACK': {}, 
                'INSULT': {}, 
                'PROFANITY': {}, 
                'THREAT': {}
            }
        }

        try:
            print("Getting data...")
            response = perspective_client.comments().analyze(body=analyze_request).execute()
            scores = response.get('attributeScores', {})
            organized_scores = {
                attr.lower(): score_data.get('summaryScore', {}).get('value')
                for attr, score_data in scores.items()
            }

            return organized_scores

        except Exception as e:
            print(f"Error: {e}")
            return {
                'toxicity': None,
                'severe_toxicity': None,
                'identity_attack': None,
                'insult': None,
                'profanity': None,
                'threat': None
            }
    return (get_perspective_api_score,)


@app.cell
def _(mo):
    perspective_button = mo.ui.run_button()
    perspective_button
    return (perspective_button,)


@app.cell
def _(
    df_posts_with_link_text,
    discovery,
    get_perspective_api_score,
    mo,
    os,
    perspective_button,
    pl,
):
    mo.stop(not perspective_button.value)

    API_KEY = os.environ["PERSPECTIVE_API_KEY"]

    perspective_client = discovery.build(
      "commentanalyzer",
      "v1alpha1",
      developerKey=API_KEY,
      discoveryServiceUrl="https://commentanalyzer.googleapis.com/$discovery/rest?version=v1alpha1",
      static_discovery=False,
    )

    df_with_scores = df_posts_with_link_text.select(
        "collection_name", "account_name", "post_text"
    ).with_columns(
        pl.col("post_text").map_elements(
            lambda text: get_perspective_api_score(text, perspective_client),
            return_dtype=pl.Struct([
                pl.Field("toxicity", pl.Float64),
                pl.Field("severe_toxicity", pl.Float64),
                pl.Field("identity_attack", pl.Float64),
                pl.Field("insult", pl.Float64),
                pl.Field("profanity", pl.Float64),
                pl.Field("threat", pl.Float64)
            ])
        ).alias("perspective_scores")
    ).unnest("perspective_scores")
    return


@app.cell
def _(df_posts_with_content_text, pl):
    #df_with_scores.write_csv("../data/data_toxicity.csv")
    _df_toxicity = pl.read_csv("../data/data_toxicity.csv")
    df_toxicity = df_posts_with_content_text.join(_df_toxicity, on=["collection_name", "account_name", "post_text"])
    return (df_toxicity,)


@app.cell(hide_code=True)
def _(mo):
    mo.md(r"""## Calculating Reaction Score and Consenso Index""")
    return


@app.cell
def _(df_toxicity, pl):
    df_with_all_metrics = (
        df_toxicity
        .with_columns([
            (pl.col("likeCount") + pl.col("loveCount")).alias("positive_reactions"),
            (pl.col("sadCount") + pl.col("angryCount")).alias("negative_reactions"),
        ])
        .with_columns([
            (pl.col("positive_reactions") + pl.col("negative_reactions")).alias("total_reactions"),
            pl.col("positive_reactions").sum().over("collection_name").alias("total_pos_over_collection"),
            pl.col("negative_reactions").sum().over("collection_name").alias("total_neg_over_collection"),
        ])
        .with_columns([
            (pl.col("total_pos_over_collection") - pl.col("positive_reactions")).alias("loo_pos_sum"),
            (pl.col("total_neg_over_collection") - pl.col("negative_reactions")).alias("loo_neg_sum"),
            (pl.col("positive_reactions") > pl.col("negative_reactions")).cast(pl.Int8).alias("is_post_positive"),
        ])
        .with_columns([
            (pl.col("loo_pos_sum") / (pl.col("loo_pos_sum") + pl.col("loo_neg_sum")))
            .alias("reaction_score")
            .fill_nan(None),

            (abs(pl.col("positive_reactions") - pl.col("negative_reactions")) / pl.col("total_reactions"))
            .alias("consensus_index")
        ])
        .drop(["total_pos_over_collection", "total_neg_over_collection", "loo_pos_sum", "loo_neg_sum"])
        .drop_nulls()
        .drop_nans()
    )
    return (df_with_all_metrics,)


@app.cell
def _(df_with_all_metrics, pl):
    # Calculate std of reaction_score per collection_name
    df_reaction_std = df_with_all_metrics.group_by("collection_name").agg(
        pl.col("reaction_score").std().alias("reaction_score_std"),
        pl.len().alias("posts_count")
    )

    # Calculate mean std for each minimum posts threshold
    std_results = []

    for min_posts in range(1, 200):
        df_filtered = df_reaction_std.filter(pl.col("posts_count") >= min_posts)

        if df_filtered.is_empty():
            continue

        mean_std = df_filtered["reaction_score_std"].mean()
        collections_count = df_filtered.height

        # Calculate total posts remaining
        total_posts = df_filtered["posts_count"].sum()

        std_results.append({
            "min_posts_threshold": min_posts,
            "mean_reaction_score_std": mean_std,
            "collections_count": collections_count,
            "total_posts": total_posts
        })

    std_results_df = pl.DataFrame(std_results)
    return (std_results_df,)


@app.cell
def _(plt, std_results_df):
    fig, (ax1, ax2) = plt.subplots(2, 1, figsize=(10, 10), sharex=True)

    # Top plot: Mean reaction score std
    ax1.plot(
        std_results_df["min_posts_threshold"],
        std_results_df["mean_reaction_score_std"],
        marker="o",
        linewidth=2,
        color="steelblue"
    )

    ax1.set_ylabel("Mean reaction score std")
    ax1.set_title("Mean reaction score std by minimum posts per collection")
    ax1.grid(True)

    # Bottom plot: Total posts remaining
    ax2.plot(
        std_results_df["min_posts_threshold"],
        std_results_df["total_posts"],
        marker="o",
        linewidth=2,
        color="darkorange"
    )

    ax2.set_xlabel("Minimum posts per collection")
    ax2.set_ylabel("Total posts")
    ax2.set_title("Total posts remaining by minimum posts per collection")
    ax2.grid(True)

    plt.tight_layout()
    plt.gca()
    return


@app.cell(hide_code=True)
def _(mo):
    mo.md(r"""## Calculating news's topics""")
    return


@app.cell
def _(df_with_all_metrics, pl):
    df_topics_aux = pl.read_csv("../data/zero_shot_results/resultado_zero_shot_MoritzLaurer_mDeBERTa-v3-base-xnli-multilingual-nli-2mil7.csv")
    df_topics = df_with_all_metrics.join(df_topics_aux, on="collection_name")
    return (df_topics,)


@app.cell(hide_code=True)
def _(mo):
    mo.md(r"""## Final dataframe""")
    return


@app.cell
def _(df_topics, pl):
    df_posts_filtered = df_topics.select(
        "collection_name", 
        "dominio",
        "link", 
        "link_text",
        "account_name", 
        "rph_link", 
        "rph_user",
        "rph_delta",
        "toxicity",
        "profanity",
        "identity_attack",
        "threat",
        "severe_toxicity",
        "insult",
        "economia", 
        "educação", 
        "saúde", 
        "segurança", 
        "cultura", 
        "religião", 
        "desinformação", 
        "eleição", 
        "politica", 
        "corrupção",
        "likeCount", 
        "loveCount", 
        "wowCount", 
        "hahaCount", 
        "sadCount", 
        "angryCount", 
        "thankfulCount", 
        "careCount",
        "totalReactions",
        "positive_reactions",
        "negative_reactions",
        "reaction_score",
        "consensus_index"
    ).filter(~(
        pl.col("link").str.contains("g1\\.globo\\.com") |
        pl.col("link").str.contains("jota\\.info") |
        pl.col("link").str.contains("epoca\\.globo\\.com") |
        pl.col("link").str.contains("https://band\\.uol\\.com\\.br/eleicoes/") |
        pl.col("link").str.contains("https://redetv\\.uol\\.com\\.br/aovivo")
    ))
    return (df_posts_filtered,)


@app.cell
def _(
    df_posts_filtered,
    epsilon,
    f1_score,
    np,
    pl,
    precision_recall_curve,
    precision_score,
    recall_score,
):
    df_topics_thiago = pl.read_csv("../data/zero_shot_results/avaliacao_topicos_thiago.csv")
    df_topics_validation = df_posts_filtered.select("link", "economia", "educação", "saúde", "segurança", "cultura", "religião", "desinformação", "eleição", "politica", "corrupção").join(df_topics_thiago, on="link").to_pandas()

    best_thresholds = {}

    topics = ["educação", "saúde", "segurança", "cultura", "religião", "desinformação", "eleição", "politica", "corrupção"]

    for t in topics:
        y_true = df_topics_validation[f"{t}_right"]
        y_pred_probs = df_topics_validation[t]

        prec, rec, thresh = precision_recall_curve(y_true, y_pred_probs)

        f1 = 2 * prec * rec / (prec + rec + epsilon)

        best_thresh = thresh[np.argmax(f1)]

        best_thresholds[t] = best_thresh

    best_thresholds

    metrics_by_topic = {}

    for t2 in topics:
        y_true2 = df_topics_validation[f"{t2}_right"]
        y_pred_probs2 = df_topics_validation[t2]

        y_pred2 = (y_pred_probs2 >= best_thresholds[t2]).astype(int)

        precision2 = precision_score(y_true2, y_pred2, zero_division=0)
        recall2 = recall_score(y_true2, y_pred2, zero_division=0)
        f12 = f1_score(y_true2, y_pred2, zero_division=0)

        metrics_by_topic[t2] = {
            "threshold": best_thresholds[t2],
            "precision": precision2,
            "recall": recall2,
            "f1": f12
        }

    metrics_by_topic
    return


@app.cell
def _(LinearRegression, df_posts_filtered, pd, pl, plt, r2_score):
    def get_orientation_expr(col_name):
        return (pl.when(pl.col(col_name) >= 0.3)
                .then(pl.lit("right"))
                .when(pl.col(col_name) <= -0.3)
                .then(pl.lit("left"))
                .otherwise(pl.lit("center")))

    results = []
    thresholds = [5, 10, 20, 30, 40, 50, 75, 100, 125, 150, 175, 200]

    for thr in thresholds:
        df_f = df_posts_filtered.filter(pl.col("totalReactions") >= thr)
        posts_count = df_f.height

        if posts_count < 30:
            continue

        df_f = df_f.with_columns([
            get_orientation_expr("rph_link").alias("link_orientation"),
            get_orientation_expr("rph_user").alias("user_orientation")
        ])

        left_posts = df_f.filter(pl.col("link_orientation") == "left").height
        center_posts = df_f.filter(pl.col("link_orientation") == "center").height
        right_posts = df_f.filter(pl.col("link_orientation") == "right").height

        left_users = df_f.filter(pl.col("user_orientation") == "left").height
        center_users = df_f.filter(pl.col("user_orientation") == "center").height
        right_users = df_f.filter(pl.col("user_orientation") == "right").height

        # Unique users count
        unique_users_count = df_f.select("account_name").n_unique()

        reaction_score_std = df_f["reaction_score"].std()
        consensus_index_std = df_f["consensus_index"].std()

        features = [
            "reaction_score", "rph_delta", "rph_link", "rph_user",
            "economia", "educação", "saúde", "segurança", "cultura",
            "religião", "desinformação", "eleição", "politica",
            "corrupção", "toxicity"
        ]

        df_pandas = df_f.select(features + ["consensus_index"]).to_pandas()
        X = df_pandas[features]
        y = df_pandas["consensus_index"]

        model = LinearRegression()
        model.fit(X, y)
        y_pred = model.predict(X)
        r2 = r2_score(y, y_pred)

        results.append({
            "num_reactions_threshold": thr,
            "posts_count": posts_count,
            "unique_users_count": unique_users_count,
            "left_posts_count": left_posts,
            "center_posts_count": center_posts,
            "right_posts_count": right_posts,
            "left_users_count": left_users,
            "center_users_count": center_users,
            "right_users_count": right_users,
            "reaction_score_std": reaction_score_std,
            "consensus_index_std": consensus_index_std,
            "r2_score": r2,
        })

    results_df = pd.DataFrame(results)

    # ========================
    # Plotting
    # ========================

    fig_test, axs = plt.subplots(3, 2, figsize=(15, 15))
    fig_test.suptitle("Statistics by Reaction Threshold", fontsize=16)

    # (0,0) Total posts
    axs[0, 0].plot(results_df["num_reactions_threshold"],
                   results_df["posts_count"], marker="o")
    axs[0, 0].set_title("Total number of posts")
    axs[0, 0].set_xlabel("Reaction threshold")
    axs[0, 0].set_ylabel("Number of posts")
    axs[0, 0].grid(True)

    # (0,1) Total unique users
    axs[0, 1].plot(results_df["num_reactions_threshold"],
                   results_df["unique_users_count"], marker="o", color="orange")
    axs[0, 1].set_title("Total number of unique users")
    axs[0, 1].set_xlabel("Reaction threshold")
    axs[0, 1].set_ylabel("Number of unique users")
    axs[0, 1].grid(True)

    # (1,0) Post distribution by orientation
    axs[1, 0].plot(results_df["num_reactions_threshold"],
                   results_df["left_posts_count"], marker="o", label="Left")
    axs[1, 0].plot(results_df["num_reactions_threshold"],
                   results_df["center_posts_count"], marker="o", label="Center")
    axs[1, 0].plot(results_df["num_reactions_threshold"],
                   results_df["right_posts_count"], marker="o", label="Right")
    axs[1, 0].set_title("Post distribution by orientation")
    axs[1, 0].set_xlabel("Reaction threshold")
    axs[1, 0].set_ylabel("Count")
    axs[1, 0].legend()
    axs[1, 0].grid(True)

    # (1,1) Unique users by orientation
    axs[1, 1].plot(results_df["num_reactions_threshold"],
                   results_df["left_users_count"], marker="o", label="Left users")
    axs[1, 1].plot(results_df["num_reactions_threshold"],
                   results_df["center_users_count"], marker="o", label="Center users")
    axs[1, 1].plot(results_df["num_reactions_threshold"],
                   results_df["right_users_count"], marker="o", label="Right users")
    axs[1, 1].set_title("Unique users by orientation")
    axs[1, 1].set_xlabel("Reaction threshold")
    axs[1, 1].set_ylabel("Count")
    axs[1, 1].legend()
    axs[1, 1].grid(True)

    # (2,0) Standard deviation of reaction score
    axs[2, 0].plot(results_df["num_reactions_threshold"],
                   results_df["reaction_score_std"], marker="o")
    axs[2, 0].set_title("Reaction score standard deviation vs threshold")
    axs[2, 0].set_xlabel("Reaction threshold")
    axs[2, 0].set_ylabel("Std. dev. of reaction_score")
    axs[2, 0].grid(True)

    # (2,1) R² variation
    axs[2, 1].plot(results_df["num_reactions_threshold"],
                   results_df["r2_score"], marker="o")
    axs[2, 1].set_title("Linear regression R² vs threshold")
    axs[2, 1].set_xlabel("Reaction threshold")
    axs[2, 1].set_ylabel("R²")
    axs[2, 1].grid(True)

    plt.tight_layout(rect=[0, 0.03, 1, 0.95])
    plt.gca()
    return (results_df,)


@app.cell
def _(plt, results_df):
    plt.rcParams.update({
        'font.size': 10,
        'axes.titlesize': 16,
        'axes.labelsize': 16,
        'xtick.labelsize': 16,
        'ytick.labelsize': 16,
        'figure.titlesize': 16
    })

    plt.figure(figsize=(8, 6))

    plt.plot(
        results_df["num_reactions_threshold"],
        results_df["posts_count"],
        marker="o",
        linewidth=2
    )

    plt.title("Number of posts vs reaction threshold")
    plt.xlabel("Reaction threshold")
    plt.ylabel("Number of posts")
    plt.grid(True)

    plt.tight_layout()
    plt.show()
    return


@app.cell
def _(plt, results_df):
    plt.figure(figsize=(8, 6))

    plt.plot(
        results_df["num_reactions_threshold"],
        results_df["reaction_score_std"],
        marker="o"
    )

    plt.title("Reaction score standard deviation vs threshold")
    plt.xlabel("Reaction threshold")
    plt.ylabel("Standard deviation of reaction_score")
    plt.grid(True)

    plt.tight_layout()
    plt.show()
    return


@app.cell
def _(df_posts_filtered):
    topic_translations = {
        'economia': 'Economy',
        'educação': 'Education',
        'saúde': 'Health',
        'segurança': 'Security',
        'cultura': 'Culture',
        'religião': 'Religion',
        'desinformação': 'Disinformation',
        'eleição': 'Election',
        'politica': 'Politics',
        'corrupção': 'Corruption'
    }

    df_posts_final = df_posts_filtered.rename(topic_translations)
    return (df_posts_final,)


@app.cell
def _(df_posts_final, pl):
    columns_to_drop = [
        "dominio", "likeCount", "loveCount", 
        "hahaCount", "sadCount", "angryCount", "wowCount", 
        "thankfulCount", "careCount", "positive_reactions",
        "negative_reactions", "totalReactions"
    ]

    final_df = df_posts_final.filter(pl.col("totalReactions") >= 50).drop(columns_to_drop)
    final_df.write_csv("../data/data_final.csv")
    return


@app.cell
def _():
    return


if __name__ == "__main__":
    app.run()
