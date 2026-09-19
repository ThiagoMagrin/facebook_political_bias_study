# post_timestamps.csv

Post-level timestamps for the 4,584 posts of the analytical sample, joinable
one-to-one to `analysis_dataset.csv` on `(account_name, post_text)`.

| Column | Meaning |
|---|---|
| `collection_name`, `account_name`, `link`, `post_text` | join keys to `rebuttal/data/analysis_dataset.csv` |
| `mongo_post_id` | CrowdTangle post identifier (`accountId\|postId`) |
| `post_datetime` | when the post was published |
| `updated_datetime` | when CrowdTangle last refreshed the post's metrics |
| `temporal_period` | position relative to the 2018 election and the Twitter collection window |
| `within_twitter_window` | post falls inside the window used to derive the link bias scores |

## Provenance

These fields exist nowhere else in the repository: `data/data_mongodb.csv`
carries reaction counts but no dates. They come from the MongoDB `crowd_tangle`
snapshot and were extracted by `rebuttal/scripts/06_extract_timestamps.py`,
which reproduces the document projection and the `(account_name, message)`
de-duplication rule of `notebooks/data_collection.py`. The join to the
analytical sample is exact: 4,584 rows in, 4,584 out, zero unmatched.

To re-run it, mount the snapshot and start MongoDB 6.0.5 (the version that
wrote the data files — WiredTiger 10.0.2):

```bash
docker run -d --name pbs-mongo -p 27017:27017 \
  -v "$PWD/mongodb/var/lib/mongodb":/data/db \
  --entrypoint mongod mongo:6.0.5 --dbpath /data/db --bind_ip_all
```

`--entrypoint mongod` is required under rootless Docker: the image's default
entrypoint drops to the `mongodb` user, which cannot read files owned by the
host user through the bind mount. Copy the data directory before mounting it —
mongod writes to the dbpath on startup.

## Temporal coverage

Range 2018-01-08 to 2022-11-03. Not every post is from the election period:

| Period | Posts |
|---|---:|
| Twitter window: between rounds | 3,031 |
| Twitter window: after second round | 700 |
| Twitter window: through first round | 368 |
| 2019-2022 | 243 |
| Before Twitter window | 222 |
| After Twitter window, still 2018 | 20 |

Relevant if a later review round asks about temporal alignment between the
Twitter-derived bias scores and the Facebook posts. Nothing in
`REVIEWER_RESPONSE.md` currently depends on this file.
