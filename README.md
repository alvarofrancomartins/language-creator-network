# PLDB Creator Co-authorship Network

One-mode projection of the Programming Language Database (PLDB): two creators
are linked when they co-created at least one computer language.

![Creator co-authorship network](featured.png)

It produces four artifacts:

- `creator_network_corrected.json`: nodes, links, and connected components
- `creator_network_d3.html`: single-file interactive graph, components laid out in a grid
- `network_stats.json`: the statistics
- `creator_network_report.md`: the written findings

## Data

PLDB (github.com/breck7/pldb) stores each concept (languages, editors, file
formats, OSes) as one `.scroll` file under `concepts/`. Clone it:

```bash
git clone --depth 1 https://github.com/breck7/pldb.git
```

Only concepts tagged as computer languages (`LANGUAGE_TAGS` in
`creator_network_d3.py`) that also name their `creators` enter the graph.

## Pipeline

| step | file | what it does |
|---|---|---|
| parse | `load_pldb.py` | reads `pldb/concepts/*.scroll` into a pandas DataFrame |
| project | `creator_network_d3.py` | defines the creator projection and the D3 page renderer |
| correct | `build_corrected_graph.py` | applies `NAME_MERGES`, writes the JSON graph and the HTML page |
| count | `network_stats.py` | computes the statistics into `network_stats.json` |
| report | `creator_network_report.md` | the written findings |
| audit | `name_dedup/` | the duplicate-creator audit behind `NAME_MERGES` |

## Run

```bash
pip install pandas networkx

python3 build_corrected_graph.py        # corrected graph → JSON + HTML
python3 network_stats.py                # statistics → network_stats.json
```

Open `creator_network_d3.html` in a browser. The page needs an internet
connection: it loads d3 and the Inter/Oswald fonts from a CDN. Click a node
to see its languages and co-creators, search for a creator, filter by minimum
shared languages, or tune the force layout from the panels in the top bar and
bottom-right corner.

## How the graph is built

`build_creator_projection` turns each language's creator list into a clique:
every pair of co-creators gets an edge, weighted by how many languages they
share. Isolated creators (the sole credited author of their language) are
dropped from the rendered graph. The connected components that remain are
ranked by size and laid out in a grid, largest at the top-left.

Creator names come from each language's `creators` field, which
`load_pldb.py` reads as a raw string. `build_creator_projection` splits it
on `" and "`, the field's delimiter in PLDB's schema (`creatorsParser`:
`listDelimiter and`). There is no richer structured source: the
`creators/creators.scroll` file is a profile list with no per-language
link, so it only canonicalizes names after the fact (`NAME_MERGES`). The
split is exact in this data: 177 of the 1,182 language creator fields use
`" and "`, and none use any other separator.

One data-quality fix is baked in:

- **Creator names are merged.** `NAME_MERGES` folds 7 duplicate spellings of
  the same person onto one canonical name.

## Name resolution

`name_dedup/` is the audit behind `NAME_MERGES`. `prep.py` generates
deterministic leads (fuzzy matches, missing-edge cliques); a swarm of review
agents examines every connected component, and a verifier web-checks each
candidate. Of the 7 confirmed pairs, 3 change the graph (both spellings
appear as language creators); the other 4 do not. Full write-up in
`name_dedup/DUPLICATE_CREATORS_REPORT.md`.

`prep.py` is a one-off, already-run step (its outputs sit in `name_dedup/`).
`python3 name_dedup/prep.py` regenerates `manifest.json`, `all_leads.json`,
and `batches/`; re-run only to redo the audit, not as part of the normal
build.

Note: the audit's own figures (689 creators, 976 links, 220 components, as
reported in `DUPLICATE_CREATORS_REPORT.md` and `manifest.json`) predate the
language filter; they describe a graph with no language filter. The current
pipeline yields 475 connected creators, 715 links, 148 components before the
merges. The 7 merges are unaffected.

## Findings

85% of the 1,182 languages that name a creator have a single author. The
472 connected co-authors form 148 components, 136 of them (92%) complete
graphs. The 12 that aren't complete are held together only indirectly, by
creators who bridge languages, since no single language credits them all.
The network is sparse (712 links, 0.64%
density) and has no center (the largest component holds 16 people). Full
details in `creator_network_report.md`.
