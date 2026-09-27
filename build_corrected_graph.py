"""
build_corrected_graph.py
------------------------
Build the final, corrected creator co-creation graph and write it out.

Applies name resolution: the 7 confirmed duplicate-creator pairs are merged
onto one canonical spelling via NAME_MERGES.

Writes:
  creator_network_corrected.json   nodes / links / components
  creator_network_d3.html          the D3 visualization (regenerated)

Usage:
  python3 build_corrected_graph.py
"""

from __future__ import annotations
import json
import os

from load_pldb import load_pldb
from creator_network_d3 import build_creator_projection, graph_to_data, write_html

HERE = os.path.dirname(os.path.abspath(__file__))
CONCEPTS = os.path.join(HERE, "pldb", "concepts")
JSON_OUT = os.path.join(HERE, "creator_network_corrected.json")
HTML_OUT = os.path.join(HERE, "creator_network_d3.html")

# Confirmed same-person pairs (name_dedup/DUPLICATE_CREATORS_REPORT.md),
# mapped variant spelling -> canonical spelling.
NAME_MERGES = {
    "John George Kemeny": "John G. Kemeny",
    "Daniel Weinreb": "Dan Weinreb",
    "Dave Moon": "David A. Moon",
    "Mary Fernandez": "Mary Fernández",
    "Leon Bottou": "Léon Bottou",
    "Yann Le Cun": "Yann LeCun",
    "John Cowan": "John W. Cowan",
}


def main():
    df = load_pldb(CONCEPTS)
    G = build_creator_projection(df, drop_isolated=True, name_map=NAME_MERGES)

    data = graph_to_data(G)
    with open(JSON_OUT, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=1)

    write_html(G, HTML_OUT)

    print(f"creators: {G.number_of_nodes()}  links: {G.number_of_edges()}")
    comps = sorted({d["component"] for _, d in G.nodes(data=True)})
    print(f"connected components: {len(comps)}")
    print(f"Wrote {JSON_OUT}")
    print(f"Wrote {HTML_OUT}")


if __name__ == "__main__":
    main()
