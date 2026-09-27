"""
prep.py — stage data for the creator-name dedup swarm.

Splits the co-creation network's 220 connected components into batches and
computes deterministic "leads": candidate pairs flagged by cheap pattern
checks. The swarm agents take each batch (components + leads), apply the
graph-pattern investigation guideline, and return probable duplicates.

Lead types:
  NORM         names identical after normalization (lowercase, punctuation
               and honorifics stripped) — e.g. "John G. Kemeny" vs
               "John G Kemeny"
  INIT         one name has a single-letter token where the other has a
               longer token with the same initial ("John G Kemeny" vs
               "John George Kemeny"); surname-initial variants need
               corroboration (shared language or neighbor)
  FUZZY        edit-similar names (ratio >= 0.85) with corroboration
  MISSING_EDGE non-adjacent nodes that share neighbor(s) — if the two were
               one person, the subgraph would be a clique (the Kemeny tell)
  ADJACENT     adjacent nodes (co-created a language) with similar names —
               same person listed twice
  RARE_LANG    non-adjacent, similar names both credited with the same
               language (rarity noted in the lead)
"""

from __future__ import annotations
import json
import os
import sys
from collections import defaultdict
from difflib import SequenceMatcher

import networkx as nx

HERE = os.path.dirname(os.path.abspath(__file__))
BATCHES_DIR = os.path.join(HERE, "batches")
HONORIFICS = {"dr", "mr", "mrs", "ms", "prof", "professor"}
ROOT = os.path.dirname(HERE)
if ROOT not in sys.path:
    sys.path.insert(0, ROOT)

from load_pldb import load_pldb  # noqa: E402
from creator_network_d3 import build_creator_projection  # noqa: E402


def norm(name: str) -> str:
    """Lowercase, keep only alphanumerics, drop honorifics."""
    s = "".join(ch if ch.isalnum() else " " for ch in name.lower())
    toks = [t for t in s.split() if t not in HONORIFICS]
    return " ".join(toks)


def initial_diff_pos(a: str, b: str):
    """If a/b differ only by single-letter tokens being expanded to
    same-initial longer tokens, return the differing token position;
    otherwise None. Requires equal token counts and >= 2 tokens."""
    ta, tb = norm(a).split(), norm(b).split()
    if len(ta) != len(tb) or len(ta) < 2:
        return None
    pos = None
    for i, (x, y) in enumerate(zip(ta, tb)):
        if x == y:
            continue
        if len(x) == 1 and y.startswith(x):
            pos = i
            continue
        if len(y) == 1 and x.startswith(y):
            pos = i
            continue
        return None
    return pos


def main() -> None:
    df = load_pldb(os.path.join(HERE, "..", "pldb", "concepts"))
    G = build_creator_projection(df, drop_isolated=True)
    names = sorted(G.nodes)
    n = len(names)

    langs_of = {x: set(G.nodes[x].get("languages", [])) for x in names}
    neigh_of = {x: set(G.neighbors(x)) for x in names}

    # language -> creator count (for rarity notes)
    lang_count = defaultdict(int)
    for x in names:
        for l in langs_of[x]:
            lang_count[l] += 1

    leads = {}  # (sorted name pair) -> lead dict

    def add(key, **lead):
        k = tuple(sorted(key))
        leads[k] = {"a": k[0], "b": k[1], **lead}

    def corrob(a, b):
        return list(langs_of[a] & langs_of[b]), list(neigh_of[a] & neigh_of[b])

    # ── P1: identical after normalization ─────────────────────────────
    norm_groups = defaultdict(list)
    for x in names:
        norm_groups[norm(x)].append(x)
    for grp in norm_groups.values():
        for i in range(len(grp)):
            for j in range(i + 1, len(grp)):
                a, b = grp[i], grp[j]
                if a == b:
                    continue
                add((a, b), type="NORM", why=f"identical after normalization: '{norm(a)}'")

    # ── P2/P5/P6: initial-expansion + fuzzy, with corroboration ────────
    toks = {x: norm(x).split() for x in names}
    for i in range(n):
        for j in range(i + 1, n):
            a, b = names[i], names[j]
            key = (a, b)
            if key in leads:
                continue
            pos = initial_diff_pos(a, b)
            if pos is not None:
                langs, neigh = corrob(a, b)
                # surname-initial ("John K." vs "John Kemeny") is risky
                # without corroboration.
                surname_pos = len(toks[a]) - 1
                if pos == surname_pos and not (langs or neigh):
                    continue
                why = f"initial expansion: '{norm(a)}' vs '{norm(b)}'"
                if langs:
                    why += f"; both credited with {langs}"
                if neigh:
                    why += f"; share neighbor(s) {neigh}"
                add(key, type="INIT", why=why)
                continue
            # fuzzy: cheap prefilter, then ratio
            if abs(len(toks[a]) - len(toks[b])) > 2:
                continue
            ratio = SequenceMatcher(None, norm(a), norm(b)).ratio()
            if ratio >= 0.85:
                langs, neigh = corrob(a, b)
                if not (langs or neigh):
                    continue
                why = f"fuzzy similarity {ratio:.2f}: '{norm(a)}' vs '{norm(b)}'"
                if langs:
                    why += f"; both credited with {langs}"
                if neigh:
                    why += f"; share neighbor(s) {neigh}"
                add(key, type="FUZZY", why=why)

    # ── P3/P4/P6: structural, per connected component ─────────────────
    for comp in nx.connected_components(G):
        comp = sorted(comp)
        adj = {x: set(G.neighbors(x)) for x in comp}
        for i in range(len(comp)):
            for j in range(i + 1, len(comp)):
                a, b = comp[i], comp[j]
                key = (a, b)
                similar = key in leads  # NORM/INIT/FUZZY already
                shared = adj[a] & adj[b]
                if b in adj[a]:  # adjacent
                    if similar:
                        leads[key]["type"] += "+ADJACENT"
                        leads[key]["why"] += "; ADJACENT: directly co-created " + str(sorted(G[a][b].get("shared", [])))
                    elif _name_similar(a, b, norm):
                        add(key, type="ADJACENT",
                            why=f"co-created {sorted(G[a][b].get('shared', []))} and names similar: '{norm(a)}' vs '{norm(b)}'")
                    continue
                if not shared:
                    continue
                jac = len(shared) / len(adj[a] | adj[b])
                if jac >= 0.5 and min(len(adj[a]), len(adj[b])) <= 3:
                    if key in leads:
                        leads[key]["type"] += "+MISSING_EDGE"
                        leads[key]["why"] += f"; MISSING_EDGE: not adjacent but share neighbor(s) {sorted(shared)[:4]} (jaccard {jac:.2f})"
                    else:
                        add(key, type="MISSING_EDGE",
                            why=f"not adjacent but share neighbor(s) {sorted(shared)[:4]} (jaccard {jac:.2f})")

    # ── P5: non-adjacent, similar, sharing a language ─────────────────
    for i in range(n):
        for j in range(i + 1, n):
            a, b = names[i], names[j]
            key = (a, b)
            if key in leads:
                continue
            if not _name_similar(a, b, norm):
                continue
            shared_langs = langs_of[a] & langs_of[b]
            if not shared_langs:
                continue
            # skip if adjacent (ADJACENT would have caught it)
            if G.has_edge(a, b):
                continue
            rarities = ", ".join(f"{l} ({lang_count[l]} creators)" for l in sorted(shared_langs)[:4])
            add(key, type="RARE_LANG",
                why=f"similar names both credited with: {rarities}")

    # ── assign leads to batches, write files ──────────────────────────
    comps = sorted(nx.connected_components(G), key=len, reverse=True)
    comp_of = {}
    for rank, comp in enumerate(comps, start=1):
        for x in comp:
            comp_of[x] = rank

    # Batching: 3 batches for comps >= 6, 4 for the tail (< 6)
    big = [r for r in range(1, 22)]
    small = [r for r in range(22, len(comps) + 1)]
    groups = [
        big[0:7], big[7:14], big[14:21],
        small[0:50], small[50:100], small[100:150], small[150:200],
    ]

    os.makedirs(BATCHES_DIR, exist_ok=True)
    manifest = {"total_nodes": n, "total_components": len(comps),
                "total_leads": len(leads), "batches": []}

    for bi, ranks in enumerate(groups, start=1):
        batch_comps = []
        batch_lead_list = []
        for r in ranks:
            comp = sorted(comps[r - 1])
            batch_comps.append({
                "rank": r,
                "size": len(comp),
                "nodes": [
                    {"id": x, "languages": sorted(langs_of[x]), "deg": len(neigh_of[x])}
                    for x in comp
                ],
                "links": [
                    {"source": a, "target": b, "shared": sorted(G[a][b].get("shared", []))}
                    for a, b in G.edges(comp)
                ],
            })
        for key, lead in leads.items():
            if comp_of.get(key[0]) in ranks:
                batch_lead_list.append(lead)
        path = os.path.join(BATCHES_DIR, f"batch_{bi:02d}.json")
        with open(path, "w", encoding="utf-8") as f:
            json.dump({
                "batch": f"b{bi}",
                "components": batch_comps,
                "leads": batch_lead_list,
            }, f, ensure_ascii=False, indent=1)
        manifest["batches"].append({
            "id": f"b{bi}", "path": path,
            "ranks": f"{ranks[0]}-{ranks[-1]}",
            "components": len(batch_comps),
            "nodes": sum(c["size"] for c in batch_comps),
            "leads": len(batch_lead_list),
        })

    with open(os.path.join(HERE, "manifest.json"), "w", encoding="utf-8") as f:
        json.dump(manifest, f, ensure_ascii=False, indent=1)

    # All leads dumped too, for the final report / cross-checking.
    with open(os.path.join(HERE, "all_leads.json"), "w", encoding="utf-8") as f:
        json.dump(sorted(leads.values(), key=lambda l: l["type"]), f,
                  ensure_ascii=False, indent=1)

    print(json.dumps(manifest, indent=1))
    print("leads by type:", {t: sum(1 for l in leads.values() if l["type"].startswith(t))
                             for t in ["NORM", "INIT", "FUZZY", "MISSING_EDGE", "ADJACENT", "RARE_LANG"]})


def _name_similar(a: str, b: str, normfn) -> bool:
    """NORM-equal, initial-expansion, or fuzzy ratio >= 0.8."""
    if normfn(a) == normfn(b):
        return True
    if initial_diff_pos(a, b) is not None:
        return True
    return SequenceMatcher(None, normfn(a), normfn(b)).ratio() >= 0.8


if __name__ == "__main__":
    main()
