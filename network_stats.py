"""
network_stats.py
----------------
Compute and store every statistic for the PLDB creator co-creation network,
with the 7 confirmed duplicate-creator pairs merged (name resolution).

Writes network_stats.json (before and after the merges) and prints a summary.

Usage:
    python3 network_stats.py
"""

from __future__ import annotations
import json
import os
from collections import Counter

import networkx as nx

from load_pldb import load_pldb
from creator_network_d3 import build_creator_projection, _is_language
from build_corrected_graph import NAME_MERGES

HERE = os.path.dirname(os.path.abspath(__file__))
CONCEPTS = os.path.join(HERE, "pldb", "concepts")
OUT = os.path.join(HERE, "network_stats.json")


def language_stats(df, name_map=None):
    """Count language concepts that name creators, and how many name one."""
    n = 0
    single = 0
    for _, row in df.iterrows():
        if not _is_language(row.get("tags")):
            continue
        raw = row.get("creators")
        if not isinstance(raw, str) or not raw.strip():
            continue
        creators = []
        for person in raw.split(" and "):
            person = person.strip()
            if name_map:
                person = name_map.get(person, person)
            if person and person not in creators:
                creators.append(person)
        n += 1
        if len(creators) == 1:
            single += 1
    return {
        "languages_with_creators": n,
        "single_author_languages": single,
        "single_author_pct": round(100 * single / n, 1) if n else 0.0,
    }


def graph_stats(G):
    n_all = G.number_of_nodes()
    n_edges = G.number_of_edges()
    n_iso = sum(1 for n in G if G.degree(n) == 0)
    n_conn = n_all - n_iso

    comps = [c for c in nx.connected_components(G) if len(c) >= 2]
    n_components = len(comps)
    n_complete = 0
    clique_hist = Counter()
    largest = 0
    for comp in comps:
        k = len(comp)
        m = G.subgraph(comp).number_of_edges()
        if m == k * (k - 1) // 2:
            n_complete += 1
            clique_hist[k] += 1
        largest = max(largest, k)

    # Density over ALL creators (isolated included), so solo authors pull
    # the denominator down and the whole-network density is what's reported.
    density = (2 * n_edges / (n_all * (n_all - 1))) if n_all > 1 else 0.0
    return {
        "creators_total": n_all,
        "creators_isolated": n_iso,
        "creators_isolated_pct": round(100 * n_iso / n_all, 1) if n_all else 0.0,
        "creators_connected": n_conn,
        "edges": n_edges,
        "connected_components": n_components,
        "complete_components": n_complete,
        "complete_components_pct": round(100 * n_complete / n_components, 1) if n_components else 0.0,
        "non_complete_components": n_components - n_complete,
        "density_pct": round(100 * density, 2),
        "largest_component": largest,
        "largest_component_pct": round(100 * largest / n_all, 1) if n_all else 0.0,
        "total_components_with_isolated": n_components + n_iso,
        "clique_size_histogram": dict(sorted(clique_hist.items())),
    }


def _teams(df, name_map=None):
    """Languages with two or more creators (merged, deduped), as name lists."""
    teams = []
    for _, row in df.iterrows():
        if not _is_language(row.get("tags")):
            continue
        raw = row.get("creators")
        if not isinstance(raw, str) or not raw.strip():
            continue
        creators = []
        for person in raw.split(" and "):
            person = person.strip()
            if name_map:
                person = name_map.get(person, person)
            if person and person not in creators:
                creators.append(person)
        if len(creators) >= 2:
            teams.append(creators)
    return teams


def structure_stats(df, name_map=None):
    """Team sizes, within-team pair accounting, and creator language spread.

    `pair_instances` sums C(s, 2) over every team of size s: each pair of
    co-creators counted once per language they share. `unique_edges` dedupes
    those pairs, so the difference is exactly the pairs that share two or more
    languages (reported in `pairs_sharing_multiple_languages`).
    """
    teams = _teams(df, name_map)
    sizes = [len(t) for t in teams]

    pair_shared = Counter()
    for t in teams:
        for i in range(len(t)):
            for j in range(i + 1, len(t)):
                a, b = sorted((t[i], t[j]))
                pair_shared[(a, b)] += 1

    lang_count = Counter()
    for _, row in df.iterrows():
        if not _is_language(row.get("tags")):
            continue
        raw = row.get("creators")
        if not isinstance(raw, str) or not raw.strip():
            continue
        seen = []
        for person in raw.split(" and "):
            person = person.strip()
            if name_map:
                person = name_map.get(person, person)
            if person and person not in seen:
                seen.append(person)
        for p in seen:
            lang_count[p] += 1

    n_creators = len(lang_count)
    n_one = sum(1 for v in lang_count.values() if v == 1)
    multi_hist = Counter(v for v in pair_shared.values() if v >= 2)
    return {
        "multi_author_languages": len(teams),
        "max_team_size": max(sizes) if sizes else 0,
        "team_size_histogram": dict(sorted(Counter(sizes).items())),
        "pair_instances": sum(pair_shared.values()),
        "unique_edges": len(pair_shared),
        "pairs_sharing_multiple_languages": sum(multi_hist.values()),
        "multi_language_pair_histogram": dict(sorted(multi_hist.items())),
        "creators_total": n_creators,
        "creators_in_one_language": n_one,
        "creators_in_one_language_pct": round(100 * n_one / n_creators, 1) if n_creators else 0.0,
    }


def component_structure(G):
    """Split each connected component (>=2 creators) into three kinds.

    * single-language: every member is credited on exactly one language, the
      same one (the union of the members' languages has size 1).
    * umbrella: a complete graph, but the members collectively span two or
      more languages, so no single language covers everyone.
    * partial overlap: not complete; held together only indirectly.
    """
    single = umbrella = partial = 0
    for comp in nx.connected_components(G):
        if len(comp) < 2:
            continue
        langs = set()
        for n in comp:
            langs.update(G.nodes[n].get("languages", []))
        k = len(comp)
        m = G.subgraph(comp).number_of_edges()
        complete = m == k * (k - 1) // 2
        if len(langs) == 1:
            single += 1
        elif complete:
            umbrella += 1
        else:
            partial += 1
    total = single + umbrella + partial
    return {
        "single_language_components": single,
        "single_language_pct": round(100 * single / total, 1) if total else 0.0,
        "umbrella_components": umbrella,
        "umbrella_pct": round(100 * umbrella / total, 1) if total else 0.0,
        "partial_overlap_components": partial,
        "partial_overlap_pct": round(100 * partial / total, 1) if total else 0.0,
    }


def main():
    df = load_pldb(CONCEPTS)

    lang_before = language_stats(df)
    lang_after = language_stats(df, NAME_MERGES)

    G_before = build_creator_projection(df, drop_isolated=False)
    G_after = build_creator_projection(df, drop_isolated=False, name_map=NAME_MERGES)

    before_nodes = set(G_before.nodes)
    merges_applied = [
        {"variant": v, "canonical": c}
        for v, c in NAME_MERGES.items()
        if v in before_nodes and c in before_nodes
    ]

    result = {
        "name_merges": NAME_MERGES,
        "merges_applied": merges_applied,
        "n_merges_applied": len(merges_applied),
        "structure": structure_stats(df, NAME_MERGES),
        "component_structure": component_structure(G_after),
        "before": {
            "graph": graph_stats(G_before),
            "languages": lang_before,
        },
        "after": {
            "graph": graph_stats(G_after),
            "languages": lang_after,
        },
    }

    with open(OUT, "w", encoding="utf-8") as f:
        json.dump(result, f, ensure_ascii=False, indent=2)

    print(f"Merges applied: {len(merges_applied)} of {len(NAME_MERGES)}")
    for m in merges_applied:
        print(f"  {m['variant']:<24} -> {m['canonical']}")
    for variant, canon in NAME_MERGES.items():
        if variant not in before_nodes or canon not in before_nodes:
            print(f"  (no-op: '{variant}' / '{canon}' not both in filtered graph)")

    gb, ga = result["before"]["graph"], result["after"]["graph"]
    lb, la = result["before"]["languages"], result["after"]["languages"]

    print()
    print(f"{'graph':<24}{'before':>10}{'after':>10}")
    rows = [
        ("creators total", gb["creators_total"], ga["creators_total"]),
        ("creators isolated", gb["creators_isolated"], ga["creators_isolated"]),
        ("isolated %", gb["creators_isolated_pct"], ga["creators_isolated_pct"]),
        ("creators connected", gb["creators_connected"], ga["creators_connected"]),
        ("edges", gb["edges"], ga["edges"]),
        ("components", gb["connected_components"], ga["connected_components"]),
        ("complete components", gb["complete_components"], ga["complete_components"]),
        ("complete %", gb["complete_components_pct"], ga["complete_components_pct"]),
        ("non-complete", gb["non_complete_components"], ga["non_complete_components"]),
        ("density %", gb["density_pct"], ga["density_pct"]),
        ("largest component", gb["largest_component"], ga["largest_component"]),
        ("largest %", gb["largest_component_pct"], ga["largest_component_pct"]),
        ("components + isolated", gb["total_components_with_isolated"], ga["total_components_with_isolated"]),
    ]
    for label, b, a in rows:
        print(f"{label:<24}{str(b):>10}{str(a):>10}")

    print()
    print(f"{'languages':<24}{'before':>10}{'after':>10}")
    for label in ["languages_with_creators", "single_author_languages", "single_author_pct"]:
        print(f"{label:<24}{str(lb[label]):>10}{str(la[label]):>10}")

    print()
    print("clique histogram (size -> count):")
    print(f"  before: {gb['clique_size_histogram']}")
    print(f"  after:  {ga['clique_size_histogram']}")

    st = result["structure"]
    cs = result["component_structure"]

    print()
    print("component structure (after merges):")
    print(f"  single-language: {cs['single_language_components']} ({cs['single_language_pct']}%)")
    print(f"  umbrella:        {cs['umbrella_components']} ({cs['umbrella_pct']}%)")
    print(f"  partial overlap: {cs['partial_overlap_components']} ({cs['partial_overlap_pct']}%)")

    print()
    print("team structure (after merges):")
    print(f"  multi-author languages: {st['multi_author_languages']}  max team size {st['max_team_size']}")
    print(f"  team size histogram: {st['team_size_histogram']}")
    print(f"  pair instances (sum C(s,2)): {st['pair_instances']}  unique edges: {st['unique_edges']}")
    print(f"  pairs sharing >=2 languages: {st['pairs_sharing_multiple_languages']} {st['multi_language_pair_histogram']}")
    print(f"  creators in exactly one language: {st['creators_in_one_language']} / {st['creators_total']} ({st['creators_in_one_language_pct']}%)")

    print(f"\nWrote {OUT}")


if __name__ == "__main__":
    main()
