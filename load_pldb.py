"""
load_pldb.py
------------
Parses PLDB's raw "concepts/*.scroll" files (from the breck7/pldb repo)
into a single pandas DataFrame, one row per concept.

PLDB's own site builds pldb.csv from these same files, but that build
artifact isn't checked into the repo (it's generated at deploy time and
served from pldb.io), so we parse the source files directly instead.
This is actually nice: it's simpler, always in sync with `main`, and
doesn't depend on the website being up.

Scroll format refresher (see concepts/python.scroll for a real example):
    id python
    name Python
    appeared 1991
    creators Guido van Rossum
    writtenIn python restructuredtext c xml ...
    repoStats
     firstCommit 1990
     commits 156324

- Top-level keys start at column 0: `key value`.
- Nested/indented lines (like the `repoStats` block above) are metadata
  we don't need for graph-building, so we skip anything indented.
- Multi-value fields (creators, writtenIn, influencedBy, tags, ...) are
  space-separated on one line. A few creator names contain spaces
  themselves, joined with the literal word " and " per PLDB's own
  schema notes -- we leave those as raw strings and let the caller
  decide how to split a given field.
"""

from __future__ import annotations
import os
import glob
import pandas as pd

# Fields we care about for graph-building + light metadata. Add more
# freely -- any top-level scalar/list field in the .scroll files works.
RELEVANT_FIELDS = [
    "id", "name", "appeared", "tags", "creators", "country", "rank",
    "numberOfUsersEstimate", "isOpenSource",
    # relational / edge-bearing fields
    "writtenIn", "influencedBy", "dialectOf", "subsetOf", "supersetOf",
    "extensionOf", "forkOf", "implementationOf", "successorOf",
    "renamedTo", "compilesTo", "inputLanguages", "runsOnVm", "related",
    "wikipedia_related",
]


def parse_scroll_file(path: str) -> dict:
    """Extract top-level key/value pairs from one .scroll concept file."""
    row = {}
    with open(path, "r", encoding="utf-8", errors="replace") as f:
        for line in f:
            if not line.strip():
                continue
            if line[0] in (" ", "\t"):
                continue  # nested/indented sub-field, skip
            parts = line.rstrip("\n").split(" ", 1)
            key = parts[0]
            value = parts[1] if len(parts) > 1 else ""
            if key in RELEVANT_FIELDS:
                row[key] = value
    return row


def load_pldb(concepts_dir: str) -> pd.DataFrame:
    """Build a DataFrame with one row per PLDB concept."""
    files = glob.glob(os.path.join(concepts_dir, "*.scroll"))
    if not files:
        raise FileNotFoundError(
            f"No .scroll files found in {concepts_dir}. "
            "Did you clone the repo? See README for the git clone step."
        )
    rows = [parse_scroll_file(fp) for fp in files]
    # A concept must have an `id`; a few .scroll files aren't concepts
    # (empty files, site helpers like conceptsSitemap.scroll) and would
    # otherwise become spurious all-NaN rows sharing a NaN index.
    rows = [r for r in rows if r.get("id")]
    df = pd.DataFrame(rows).set_index("id", drop=False)

    # Normalize types
    df["appeared"] = pd.to_numeric(df.get("appeared"), errors="coerce")
    df["rank"] = pd.to_numeric(df.get("rank"), errors="coerce")
    df["numberOfUsersEstimate"] = pd.to_numeric(
        df.get("numberOfUsersEstimate"), errors="coerce"
    )
    return df


if __name__ == "__main__":
    import sys
    concepts_dir = sys.argv[1] if len(sys.argv) > 1 else "pldb/concepts"
    df = load_pldb(concepts_dir)
    print(f"Loaded {len(df)} concepts, {df.shape[1]} columns")
    print(df[["name", "appeared", "tags"]].head(10))