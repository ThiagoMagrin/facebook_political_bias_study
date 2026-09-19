"""
Rebuttal analysis - Step 2
Independent, rule-based ideological coding of publishers, used to validate the
data-driven publisher bias score b_p (Reviewer 4).

Coding protocol (fixed in advance, applied mechanically to the page title):

  Tier 1 - NOMINAL.   The page title names a political actor (politician, party,
                      organised movement) or an established media organisation.
                      Politicians/parties are matched by regular expression and
                      coded by their documented position in the Brazilian party
                      system. Media organisations are NOT rule-matched: they are
                      a hand-assembled lookup (MEDIA below), one editorial-line
                      judgement per outlet, and it is consulted before any regex.
                      This is case-by-case discretion and is reported as such --
                      it is also the weakest tier of the validation, so the
                      per-tier agreement is printed separately below.
  Tier 2 - AVOWED.    The page title contains an explicit ideological or
                      partisan self-declaration without naming an actor
                      ("Esquerda", "Conservador", "Direita", "Patriotas",
                      "Intervenção Militar").
  Not coded.          Everything else (regional pages, universities, hobby and
                      entertainment pages, ambiguous titles). These are reported
                      as non-identifiable and excluded from the agreement test.

One disambiguation is applied: "Movimento Brasil LIVRE E SOBERANO-Rede
Internacional da Legalidade" is a distinct organisation from the right-wing
"Movimento Brasil Livre" (MBL) whose name it partially contains. It is left
uncoded as a name collision. The exclusion concerns the identity of the
organisation, not its score.

This one exclusion is load-bearing and must not be buried: the page matches the
RIGHT_ACTOR pattern but has b_p = -0.833 (Left), so including it would turn the
headline "zero Left<->Right sign reversals" into one reversal and drop exact
agreement from 62/66 = 93.9% to 62/67 = 92.5%. 03_descriptives.py therefore
reports the agreement statistics BOTH with and without it, as claimed here.
The membership test is an exact string match, so a title that drifts by one
character would silently stop excluding; the assertion below fails loudly
instead.

Frame: every publisher in the analytical sample with >= 15 links in its sharing
history, i.e. enough history for b_p to be estimable. The frame is coded
exhaustively; no page is dropped after seeing its b_p.

Output: rebuttal/data/publisher_labels.csv
"""
import os
import re
import polars as pl
from pathlib import Path

# Repository root: PROJECT_ROOT if set, otherwise derived from this file's own
# location (scripts live in <root>/rebuttal/scripts/). Mirrors the resolution in
# _common.R so the Python and R halves of the pipeline relocate together.
ROOT = Path(os.environ.get("PROJECT_ROOT") or Path(__file__).resolve().parents[2])
assert (ROOT / "rebuttal" / "scripts").is_dir(), f"not a repository root: {ROOT}"
OUT = ROOT / "rebuttal" / "data"

MIN_LINKS = 15

# ---------------------------------------------------------------------------
# Tier 1 - named actors and media organisations
# ---------------------------------------------------------------------------
LEFT_ACTOR = r"(lula|lulista|petista|\bpt\b|partido dos trabalhadores|haddad|dilma|ciro gomes|psol|boulos|margarida salomão|david miranda|privataria tucana)"
RIGHT_ACTOR = r"(bolsonaro|olavo de carvalho|sergio moro|sérgio moro|lava jato|movimento brasil livre|\bmbl\b|terça livre|partido militar)"

# distinct organisations whose titles collide with a pattern above
NAME_COLLISIONS = {"Movimento Brasil LIVRE E SOBERANO-Rede Internacional da Legalidade"}
ANTI_LEFT = r"(contra o pt|contra o lula|anti[- ]?pt)"
ANTI_RIGHT = r"(contra (jair )?bolsonaro|fora bolsonaro|anti[- ]?bolsonaro|bolsonaro:? aqui não|ele não|contra o coiso)"

# Hand-assigned, one judgement per outlet, and consulted BEFORE the regexes
# below. This is the discretionary part of the protocol -- see the docstring.
MEDIA = {
    # mainstream general-interest press -> Center
    "UOL": "Center", "UOL Notícias": "Center", "Terra": "Center",
    "Poder360": "Center", "Correio Braziliense": "Center", "O Povo": "Center",
    "iG": "Center", "Jornal O Dia": "Center", "BBC News Brasil": "Center",
    "O Globo": "Center", "Blog do Josias": "Center",
    # documented left / progressive outlets
    "Mídia NINJA": "Left", "Catraca Livre": "Left",
    "Catraca Livre Entretenimento": "Left", "Quebrando o Tabu": "Left",
    "The Intercept glenn greenwald vazajato": "Left",
    "Blog da Maria Frô": "Left",
    # documented right / conservative outlets
    "Gazeta do Povo": "Right", "Gazeta do Povo - Paraná": "Right",
    "O Antagonista": "Right",
}

# ---------------------------------------------------------------------------
# Tier 2 - avowed ideological identity, no actor named
# ---------------------------------------------------------------------------
LEFT_AVOWED = r"(esquerdas?\b|esquerdista|siga à esquerda)"
RIGHT_AVOWED = r"(à direita|de direita|direita e liberdade|conservador|patriotas?\b|intervenção militar|brasil direita)"


def code(name: str, honour_collisions: bool = True):
    """Return (label, tier, basis) or (None, None, reason).

    honour_collisions=False bypasses NAME_COLLISIONS, giving the label the rest
    of the protocol would assign on its own. Used to report the sensitivity of
    the agreement statistics to that single hand exclusion.
    """
    if honour_collisions and name in NAME_COLLISIONS:
        return None, None, "name collides with a different organisation - not coded"
    if name in MEDIA:
        return MEDIA[name], "Tier 1 (media)", "documented editorial line"

    low = name.lower()
    l1 = bool(re.search(LEFT_ACTOR, low)) or bool(re.search(ANTI_RIGHT, low))
    r1 = bool(re.search(RIGHT_ACTOR, low)) or bool(re.search(ANTI_LEFT, low))

    # an anti-X page is coded against X, so resolve the polarity explicitly
    if re.search(ANTI_RIGHT, low):
        r1 = False
    if re.search(ANTI_LEFT, low):
        l1 = False

    if l1 and not r1:
        return "Left", "Tier 1 (actor)", "names a left actor / opposes a right actor"
    if r1 and not l1:
        return "Right", "Tier 1 (actor)", "names a right actor / opposes a left actor"
    if l1 and r1:
        return None, None, "names actors on both sides - ambiguous"

    l2 = bool(re.search(LEFT_AVOWED, low))
    r2 = bool(re.search(RIGHT_AVOWED, low))
    if l2 and not r2:
        return "Left", "Tier 2 (avowed)", "avowed left identity in page title"
    if r2 and not l2:
        return "Right", "Tier 2 (avowed)", "avowed right identity in page title"

    return None, None, "no identifiable political actor or avowed identity"


d = pl.read_csv(OUT / "analysis_dataset.csv")
frame = (
    d.group_by("account_name")
    .agg(
        pl.col("rph_user").first().alias("bp"),
        pl.col("author_links_history").first().alias("links_history"),
        pl.col("author_posts_history").first().alias("posts_history"),
        pl.len().alias("posts_in_sample"),
    )
    .filter(pl.col("links_history") >= MIN_LINKS)
    # account_name breaks ties in links_history. Without it polars leaves tied
    # rows in an unspecified order and this CSV is rewritten differently on
    # every run, producing diffs that look like real changes but are not.
    .sort(["links_history", "account_name"], descending=[True, False])
)

_in_frame = set(frame["account_name"])
_missing = NAME_COLLISIONS - _in_frame
assert not _missing, (
    f"NAME_COLLISIONS entries absent from the frame: {_missing}. The membership "
    "test is an exact string match, so a retitled page would silently stop being "
    "excluded and the agreement statistics would change without warning."
)

rows = []
for name, bp, links, posts, n in frame.iter_rows():
    label, tier, basis = code(name)
    # the label the protocol would give with the one hand exclusion removed
    label_nc, _, _ = code(name, honour_collisions=False)
    bp_side = "Left" if bp <= -0.3 else ("Right" if bp >= 0.3 else "Center")
    rows.append({
        "account_name": name,
        "manual_label": label,
        "manual_label_no_collision_rule": label_nc,
        "tier": tier,
        "coding_basis": basis,
        "bp": bp,
        "bp_side": bp_side,
        "links_history": links,
        "posts_history": posts,
        "posts_in_sample": n,
    })

lab = pl.DataFrame(rows)
lab.write_csv(OUT / "publisher_labels.csv")

coded = lab.filter(pl.col("manual_label").is_not_null())
print(f"frame (>= {MIN_LINKS} links): {lab.height} publishers")
print(f"coded: {coded.height}  |  not identifiable: {lab.height - coded.height}")
print()
print(coded.group_by(["tier", "manual_label"]).len().sort(["tier", "manual_label"]))
print()
print("--- every coded publisher ---")
for r in coded.sort(["manual_label", "bp"]).iter_rows(named=True):
    hit = "OK " if r["manual_label"] == r["bp_side"] else ">> "
    print(f'{hit}{r["account_name"][:50]:<52} manual={r["manual_label"]:<6} bp={r["bp"]:+.3f} -> {r["bp_side"]:<6} ({r["tier"]}, {r["links_history"]} links)')
print()
print("--- not identifiable ---")
for r in lab.filter(pl.col("manual_label").is_null()).iter_rows(named=True):
    print(f'   {r["account_name"][:50]:<52} bp={r["bp"]:+.3f} ({r["links_history"]} links)')
