"""
Rebuttal analysis - Step 6 (one-off recovery)
Extracts post-level timestamps from the MongoDB `crowd_tangle` database and
attaches them to the analytical sample.

These fields exist nowhere else in the repository: data/data_mongodb.csv carries
reaction counts but no dates. Run this only when the MongoDB snapshot is mounted;
its output, rebuttal/data/post_timestamps.csv, is the durable artefact.

The document projection and the de-duplication rule reproduce
notebooks/data_collection.py exactly, so the rows line up one-to-one with
rebuttal/data/analysis_dataset.csv on (account_name, post_text).

    docker run -d --name pbs-mongo -p 27017:27017 \
      -v /path/to/mongodb/var/lib/mongodb:/data/db \
      --entrypoint mongod mongo:6.0.5 --dbpath /data/db --bind_ip_all
"""
import polars as pl
from pathlib import Path
from pymongo import MongoClient

ROOT = Path(__file__).resolve().parents[2]
OUT = ROOT / "rebuttal" / "data"

REACTIONS = ["likeCount", "loveCount", "wowCount", "hahaCount",
             "sadCount", "angryCount", "thankfulCount", "careCount"]

client = MongoClient("mongodb://localhost:27017/", serverSelectionTimeoutMS=15000)
db = client["crowd_tangle"]
print(f"mongod {client.server_info()['version']}  |  collections: {len(db.list_collection_names())}")

pipeline = [
    {"$match": {"platform": "Facebook", "message": {"$exists": True}}},
    {"$project": {
        "_id": 0,
        "message": 1,
        "account_name": {"$ifNull": ["$account.name", None]},
        "mongo_post_id": {"$ifNull": ["$id", None]},
        "post_datetime": {"$ifNull": ["$date", None]},
        "updated_datetime": {"$ifNull": ["$updated", None]},
        **{c: {"$ifNull": [f"$statistics.actual.{c}", None]} for c in REACTIONS},
    }},
]

rows = []
names = sorted(db.list_collection_names())
for i, coll in enumerate(names, 1):
    for d in db[coll].aggregate(pipeline):
        d["collection_name"] = coll
        rows.append(d)
    if i % 400 == 0 or i == len(names):
        print(f"  {i}/{len(names)} collections -> {len(rows)} documents")

raw = pl.DataFrame(rows).with_columns(
    pl.sum_horizontal([pl.col(c).fill_null(0) for c in REACTIONS]).alias("totalReactions")
)

# same de-duplication as notebooks/data_collection.py: keep the highest-reaction
# copy of each (account_name, message) pair
dedup = (
    raw.sort("totalReactions", descending=True)
       .unique(subset=["account_name", "message"], maintain_order=True, keep="first")
       .select(["collection_name", "account_name", "message", "mongo_post_id",
                "post_datetime", "updated_datetime"])
       .rename({"message": "post_text"})
)
print(f"\ndocuments: {raw.height}  ->  after de-duplication: {dedup.height}")

analysis = pl.read_csv(OUT / "analysis_dataset.csv").select(
    ["collection_name", "account_name", "link", "post_text"]
)
joined = analysis.join(dedup.drop("collection_name"),
                       on=["account_name", "post_text"], how="left")

print(f"analysis rows: {analysis.height}  |  after join: {joined.height}  "
      f"|  unmatched: {joined['post_datetime'].null_count()}")
assert joined.height == analysis.height, "join changed the row count"
assert joined["post_datetime"].null_count() == 0, "some posts have no timestamp"

# derived temporal fields: 2018 Brazilian general election and the window of the
# Twitter collection from which the link bias scores were derived
R1 = pl.datetime(2018, 10, 7, 23, 59, 59)
R2 = pl.datetime(2018, 10, 28, 23, 59, 59)
WIN_START, WIN_END = pl.datetime(2018, 10, 1), pl.datetime(2018, 12, 11, 23, 59, 59)

out = (
    joined.with_columns(pl.col("post_datetime").str.to_datetime().alias("dt"))
    .with_columns([
        pl.when(pl.col("dt") < WIN_START).then(pl.lit("Before Twitter window"))
        .when(pl.col("dt") <= R1).then(pl.lit("Twitter window: through first round"))
        .when(pl.col("dt") <= R2).then(pl.lit("Twitter window: between rounds"))
        .when(pl.col("dt") <= WIN_END).then(pl.lit("Twitter window: after second round"))
        .when(pl.col("dt") <= pl.datetime(2018, 12, 31, 23, 59, 59))
        .then(pl.lit("After Twitter window, still 2018"))
        .otherwise(pl.lit("2019-2022")).alias("temporal_period"),
        ((pl.col("dt") >= WIN_START) & (pl.col("dt") <= WIN_END)).alias("within_twitter_window"),
    ])
    .with_columns([
        pl.col("dt").dt.strftime("%Y-%m-%dT%H:%M:%S%.6f").alias("post_datetime"),
        pl.col("updated_datetime").str.to_datetime()
          .dt.strftime("%Y-%m-%dT%H:%M:%S%.6f").alias("updated_datetime"),
    ])
    .drop("dt")
)

out.write_csv(OUT / "post_timestamps.csv")
print(f"\nwritten: {OUT / 'post_timestamps.csv'}  ({out.height} rows)")
print(f"date range: {out['post_datetime'].min()}  ->  {out['post_datetime'].max()}")
print()
print(out["temporal_period"].value_counts().sort("count", descending=True))
