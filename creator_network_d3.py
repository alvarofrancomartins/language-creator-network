"""creator_network_d3.py
---------------------
One-mode projection of PLDB's creator -> language network, rendered as an
interactive D3 graph laid out in a grid.

Two creators are connected when they co-created at least one computer
language, and the edge weight is the number of languages they share. The
page draws the graph as an inline <svg>: connected components are arranged
in a grid (largest at the top-left, reading left-to-right, top-to-bottom),
while link + charge forces still lay out the nodes inside each component.
A "grid" force pins each component's centroid to its cell and a "confine"
force keeps each component compact.

Produces a single HTML file (creator_network_d3.html) that loads d3 and the
Inter/Oswald fonts from a CDN.
"""

from __future__ import annotations
from collections import defaultdict
import json
import networkx as nx

# PLDB indexes *concepts*, not just computer languages: it also has entries
# for operating systems, hardware standards, file/data formats, protocols,
# libraries, editors, etc. (each with a `tags` value like `os`, `standard`,
# `dataNotation`). The `pl` tag is PLDB's canonical programming-language
# marker, so the creator graph is built from `pl` concepts only.
LANGUAGE_TAGS = {"pl"}


def _is_language(tags) -> bool:
    """True if a concept's `tags` mark it as a computer language."""
    if not isinstance(tags, str) or not tags.strip():
        return False
    return bool(set(tags.split()) & LANGUAGE_TAGS)


def build_creator_projection(df, drop_isolated: bool = True, name_map: dict | None = None) -> nx.Graph:
    """
    Build an undirected graph of creators.

    Nodes are creators (a person's name), edges connect two creators who
    share at least one language. Each edge carries:
        weight  -- how many languages the two co-created
        shared  -- the names of those languages

    name_map (optional) canonicalizes creator names before nodes are built,
    e.g. to merge known duplicate spellings into one person.
    """
    # concept id -> (display name, [creator names])  (deduplicated per concept)
    lang_creators = {}       # id -> (name, [creators])
    for cid, row in df.iterrows():
        if not _is_language(row.get("tags")):
            continue
        raw = row.get("creators")
        if not isinstance(raw, str) or not raw.strip():
            continue
        name = row.get("name")
        if not isinstance(name, str) or not name.strip():
            continue
        lang_id = row.get("id")
        if not isinstance(lang_id, str) or not lang_id.strip():
            continue
        creators = []
        for person in raw.split(" and "):
            person = person.strip()
            if name_map:
                person = name_map.get(person, person)
            if person and person not in creators:
                creators.append(person)
        if creators:
            lang_creators[lang_id] = (name, creators)

    creator_langs = defaultdict(set)      # creator -> {language names}
    pair_langs = defaultdict(set)         # (a, b) -> {shared language names}
    for _lang_id, (name, creators) in lang_creators.items():
        for c in creators:
            creator_langs[c].add(name)
        for i in range(len(creators)):
            for j in range(i + 1, len(creators)):
                a, b = sorted((creators[i], creators[j]))
                pair_langs[(a, b)].add(name)

    G = nx.Graph()
    for c, langs in creator_langs.items():
        G.add_node(c, label=c, node_type="creator", languages=sorted(langs))
    for (a, b), langs in pair_langs.items():
        G.add_edge(a, b, weight=len(langs), shared=sorted(langs), relation="coCreated")

    if drop_isolated:
        G.remove_nodes_from([n for n in G if G.degree(n) == 0])

    # Rank connected components by size (1 = largest) so the page can let
    # the user jump to the biggest component, the second-biggest, and so on.
    comps = sorted(nx.connected_components(G), key=len, reverse=True)
    for rank, comp in enumerate(comps, start=1):
        for n in comp:
            G.nodes[n]["component"] = rank
            G.nodes[n]["compSize"] = len(comp)
    return G


def graph_to_data(G: nx.Graph) -> dict:
    """Convert the creator graph to {nodes:[...], links:[...]} for the D3 page."""
    nodes = []
    for n, d in G.nodes(data=True):
        nodes.append({
            "id": n,
            "label": d.get("label", n),
            "type": "creator",
            "languages": d.get("languages", []),
            "langCount": len(d.get("languages", [])),
            "deg": int(G.degree(n)),
            "component": int(d.get("component", 0)),
            "compSize": int(d.get("compSize", 0)),
        })
    links = [
        {"source": u, "target": v, "weight": int(d.get("weight", 1)),
         "shared": d.get("shared", []), "relation": "coCreated"}
        for u, v, d in G.edges(data=True)
    ]
    # Component summary for the dropdown (rank 1 = largest, size = #creators).
    sizes = {}
    for _, d in G.nodes(data=True):
        r = d.get("component")
        if r is not None:
            sizes[r] = max(sizes.get(r, 0), d.get("compSize", 0))
    components = [
        {"rank": r, "size": sizes[r]}
        for r in sorted(sizes)
    ]
    return {"nodes": nodes, "links": links, "components": components}


# HTML/JS/CSS template. `__PLDB_CREATOR_DATA__` is replaced with the JSON
# above. Raw string so the JS backticks/backslashes pass through untouched.
TEMPLATE = r'''<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>PLDB · Creator Network (D3)</title>
<link href="https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700&family=Oswald:wght@500;700&display=swap" rel="stylesheet">
<script src="https://cdn.jsdelivr.net/npm/d3@7"></script>

<style>
:root {
  --bg:#07080a; --s1:#0d1117; --s2:#111820; --s3:#161e2c;
  --b1:#1a2535; --b2:#243347; --b3:#2e4060;
  --amber:#e8a020; --amber2:#b87818; --accent-rgb:232,160,32;
  --text:#bdd0e8; --text2:#56708a; --text3:#2c3f58;
  --body:'Inter',sans-serif; --disp:'Oswald',sans-serif;
  --panel:500px;
}
*{box-sizing:border-box;margin:0;padding:0}
html,body{height:100%;overflow:hidden;background:var(--bg);color:var(--text);font-family:var(--body);font-size:20px}

body::before{content:'';position:fixed;inset:0;pointer-events:none;z-index:9000;
  background:repeating-linear-gradient(0deg,transparent,transparent 2px,rgba(0,0,0,.04) 2px,rgba(0,0,0,.04) 4px)}

#topbar{
  position:fixed;top:0;left:0;right:0;height:90px;z-index:400;
  background:rgba(7,8,10,.94);backdrop-filter:blur(8px);
  border-bottom:1px solid var(--b1);
  display:flex;align-items:stretch;
}
.tb-logo{display:flex;flex-direction:column;justify-content:center;padding:0 24px;border-right:1px solid var(--b1);flex-shrink:0}
.tb-mark{font-family:var(--disp);font-size:42px;letter-spacing:2px;line-height:1;color:var(--amber);text-shadow:0 0 18px rgba(var(--accent-rgb),.3);text-transform:uppercase}
.tb-sub{font-size:17px;letter-spacing:1px;font-weight:600;color:var(--text);text-transform:uppercase;margin-top:3px}

.tb-stats{display:flex}
.tb-stat{display:flex;flex-direction:column;justify-content:center;padding:0 24px;border-right:1px solid var(--b1)}
.tb-val{font-family:var(--disp);font-size:42px;color:var(--amber);line-height:1}
.tb-lbl{font-size:17px;font-weight:600;letter-spacing:1px;color:var(--text);text-transform:uppercase;margin-top:3px}

.tb-weight{display:flex;flex-direction:column;justify-content:center;gap:4px;padding:0 24px;border-right:1px solid var(--b1);flex-shrink:0}
.tb-weight .lbl{font-size:12px;font-weight:700;letter-spacing:1px;color:var(--text3);text-transform:uppercase}
.tb-weight .row{display:flex;align-items:center;gap:10px}
.tb-weight input[type=range]{width:150px;accent-color:var(--amber);cursor:pointer}
.tb-weight .val{font-family:var(--disp);font-size:20px;color:var(--amber);min-width:22px;text-align:center}

.tb-right{display:flex;align-items:center;gap:12px;padding:0 20px;border-left:1px solid var(--b1);flex-shrink:0;margin-left:auto}
.tb-btn{padding:8px 18px;background:none;border:1px solid var(--b1);color:var(--text2);font-family:var(--body);font-weight:600;font-size:16px;letter-spacing:1px;cursor:pointer;border-radius:4px;transition:all .12s;text-transform:uppercase;white-space:nowrap}
.tb-btn:hover{color:var(--text);border-color:var(--b2)}

#graph-wrap{position:fixed;inset:0;top:90px;outline:none}
#graph-wrap svg{cursor:grab}
#graph-wrap svg:active{cursor:grabbing}
#graph-wrap line{pointer-events:stroke}

#node-panel{
  position:fixed;top:90px;right:0;bottom:0;width:var(--panel);
  background:var(--s1);border-left:1px solid var(--b1);
  z-index:300;transform:translateX(100%);transition:transform .25s cubic-bezier(.2,.8,.3,1);
  display:flex;flex-direction:column;overflow:hidden;
}
#node-panel.open{transform:translateX(0)}
.np-close{position:absolute;top:16px;right:16px;background:none;border:none;color:var(--text2);cursor:pointer;font-size:26px;z-index:1;padding:4px 8px;border-radius:2px;transition:color .12s;font-family:var(--body)}
.np-close:hover{color:var(--text)}
.np-head{padding:26px 26px 18px;border-bottom:1px solid var(--b1);flex-shrink:0}
.np-name{font-family:var(--disp);font-size:44px;color:var(--amber);letter-spacing:1px;line-height:1.1;text-transform:uppercase;word-break:break-word}
.np-type{display:inline-block;padding:4px 12px;border-radius:4px;font-size:15px;font-weight:600;letter-spacing:1px;text-transform:uppercase;border:1px solid var(--b2);margin-top:14px}
.np-meta{font-size:16px;color:var(--text);margin-top:8px;line-height:1.5}
.np-meta-lbl{font-weight:700;letter-spacing:1px;text-transform:uppercase;color:var(--text3);font-size:14px}

.np-rels{flex:1;overflow-y:auto;padding:16px 0}
.np-sec{border-bottom:1px solid var(--b1)}
.np-sec:last-child{border-bottom:none}
.np-sec-hdr{padding:12px 24px;cursor:pointer;display:flex;align-items:center;justify-content:space-between;transition:background .08s;user-select:none}
.np-sec-hdr:hover{background:rgba(255,255,255,.02)}
.np-sec-title{font-size:16px;font-weight:600;letter-spacing:1px;text-transform:uppercase}
.np-sec-n{font-size:18px;font-weight:600;color:var(--text3)}
.np-items{display:none}
.np-sec.open .np-items{display:block}
.np-item{padding:12px 20px 12px 32px;border-top:1px solid var(--b1);transition:background .08s;cursor:pointer}
.np-item.plain{cursor:default}
.np-item:hover{background:rgba(var(--accent-rgb),.03)}
.np-item-name{color:var(--text);font-size:17px;font-weight:600;font-family:var(--disp);letter-spacing:0.5px;word-break:break-word}
.np-item:hover .np-item-name{color:var(--amber)}
.np-item-sub{color:var(--text3);font-size:14px;font-weight:600;margin-top:2px}

::-webkit-scrollbar{width:5px}
::-webkit-scrollbar-track{background:transparent}
::-webkit-scrollbar-thumb{background:var(--b2);border-radius:3px}

#loader{position:fixed;inset:0;background:var(--bg);display:flex;flex-direction:column;align-items:center;justify-content:center;z-index:999;gap:20px}
.ld-logo{font-family:var(--disp);font-size:96px;letter-spacing:8px;color:var(--amber);text-shadow:0 0 40px rgba(var(--accent-rgb),.4)}
.ld-msg{font-size:16px;font-weight:600;letter-spacing:2px;color:var(--text2);text-transform:uppercase}
.ld-bar{width:280px;height:3px;background:var(--b1);border-radius:2px;overflow:hidden}
.ld-fill{height:100%;background:var(--amber);width:0;transition:width .3s}

#tooltip{
  display:none;position:fixed;z-index:600;pointer-events:none;
  background:var(--s2);border:1px solid var(--b2);border-radius:4px;
  padding:12px 16px;box-shadow:0 6px 20px rgba(0,0,0,.5);color:var(--text);
  max-width:360px;
}
.tt-name{font-family:var(--disp);font-size:30px;color:var(--amber);letter-spacing:1px;line-height:1.1;text-transform:uppercase}
.tt-type{font-size:14px;font-weight:600;letter-spacing:1px;color:var(--text3);text-transform:uppercase;margin-top:5px}
.tt-sub{font-size:14px;color:var(--text2);margin-top:5px;max-width:340px}

.clabel{font-family:var(--disp);paint-order:stroke;stroke:var(--bg);stroke-linejoin:round}
.clabel-primary{font-size:30px;font-weight:700;letter-spacing:1px;fill:var(--amber);stroke-width:5px}
.clabel-secondary{font-size:20px;font-weight:500;letter-spacing:.5px;fill:var(--text);fill-opacity:.62;stroke-width:4px}
</style>
</head>
<body>

<div id="loader">
  <div class="ld-logo">CREATORS</div>
  <div class="ld-msg" id="ld-msg">Loading…</div>
  <div class="ld-bar"><div class="ld-fill" id="ld-fill"></div></div>
</div>

<div id="topbar">
  <div class="tb-logo">
    <div>
      <div class="tb-mark">Computer Languages</div>
      <div class="tb-sub">Nodes are creators · edges link co-creators</div>
    </div>
  </div>

  <div class="tb-stats">
    <div class="tb-stat"><div class="tb-val" id="s-nodes">—</div><div class="tb-lbl">Creators</div></div>
    <div class="tb-stat"><div class="tb-val" id="s-edges">—</div><div class="tb-lbl">Links</div></div>
  </div>

  <div class="tb-weight">
    <span class="lbl">Min shared</span>
    <div class="row">
      <input type="range" id="weight-filter" min="1" max="3" step="1" value="1">
      <span class="val" id="weight-val">1</span>
    </div>
  </div>

  <div style="position:relative;display:flex;align-items:center;padding:0 18px;border-left:1px solid var(--b1);flex-shrink:0">
    <input type="text" id="node-search" placeholder="Search creators…" autocomplete="off"
      style="width:260px;padding:10px 14px;background:var(--s2);border:1px solid var(--b1);border-radius:4px;color:var(--text);font-family:var(--body);font-size:16px;outline:none;transition:border-color .15s"
      onfocus="this.style.borderColor='var(--amber)'" onblur="this.style.borderColor='var(--b1)'">
    <div id="search-results" style="display:none;position:absolute;top:100%;left:18px;width:320px;max-height:420px;overflow-y:auto;background:var(--s2);border:1px solid var(--b2);border-radius:4px;z-index:400;box-shadow:0 8px 24px rgba(0,0,0,.5)"></div>
  </div>

  <div class="tb-right">
    <button class="tb-btn" id="btn-fit" style="color:var(--amber);border-color:var(--amber)">Fit</button>
  </div>
</div>

<div id="graph-wrap"></div>

<div id="node-panel">
  <button class="np-close" id="np-close">✕</button>
  <div class="np-head" id="np-head"></div>
  <div class="np-rels" id="np-rels"></div>
</div>

<div id="tune-panel" style="position:fixed;bottom:18px;right:18px;z-index:200;background:rgba(13,17,23,.94);border:1px solid var(--b1);border-radius:4px;font-family:var(--body);width:300px">
  <div id="tune-toggle" style="padding:10px 14px;cursor:pointer;display:flex;align-items:center;justify-content:space-between;font-size:14px;font-weight:600;letter-spacing:1px;color:var(--text3);text-transform:uppercase;user-select:none" onclick="document.getElementById('tune-body').style.display=document.getElementById('tune-body').style.display==='none'?'block':'none'">
    <span>⚙ Force Tuning</span><span id="tune-arrow">▸</span>
  </div>
  <div id="tune-body" style="display:none;padding:6px 14px 14px;border-top:1px solid var(--b1)"></div>
</div>

<div id="tooltip"></div>

<script>
// ═══════════════════════════════════════════════════════════════════════
//  COLOR  —  one line, no palette tables
//
//  Components are ordered by size (rank 1 = largest), so the colour is
//  sampled from a D3 ramp: t = 0 for the biggest component, t = 1 for the
//  smallest. Any d3.interpolate* works.
//
//  d3.interpolateViridis    d3.interpolateInferno   d3.interpolateMagma
//  d3.interpolatePlasma     d3.interpolateCividis   d3.interpolateTurbo
//  d3.interpolateRainbow    d3.interpolateSinebow   d3.interpolateWarm
//  d3.interpolateCool       d3.interpolateCubehelixDefault
//
//  Append "-1" to reverse: d3.interpolateViridis is dark→bright, so
//  [...].reverse() (see below) is the same as viridis_r. Swap in any
//  d3.scheme* array instead (d3.schemeTableau10, d3.schemeCategory10,
//  d3.schemeSet3, d3.schemePaired, ...) and it wraps around.
// ═══════════════════════════════════════════════════════════════════════
const palette = d3.interpolateMagma;
const REVERSE = true;   // true → smallest components get the bright end
// ═══════════════════════════════════════════════════════════════════════

// ═══════════════════════════════════════════
// DATA (embedded at build time)
// ═══════════════════════════════════════════
const DATA = __PLDB_CREATOR_DATA__;
const allNodes = (DATA && DATA.nodes) || [];
const allLinks = (DATA && DATA.links) || [];

// UI accents are derived from the same d3 ramp as the nodes (see applyTheme
// in init) so the whole page moves together. Read them back from CSS:
const NODE_COLOR = 'var(--amber)';
const EDGE_COLOR = 'var(--amber2)';
const HIGHLIGHT = '#FFFFFF';

const NODE_BY_ID = {};
allNodes.forEach(n => { n.visDeg = n.deg || 0; NODE_BY_ID[n.id] = n; });
const MAX_WEIGHT = Math.max(1, ...allLinks.map(l => l.weight || 1));
const COMPONENTS = (DATA && DATA.components) || [];
const COMP_COLOR = {};
const DEFAULT_COLOR = '#95A5A6';
const compColor = r => COMP_COLOR[r] || DEFAULT_COLOR;

// ── Component labels ────────────────────────────────────────────────
// Stack the languages with the most creators above each component. A label
// appears only when one of those languages is well known (in FAMOUS), so
// ALGOL, SQL, Go, Common Lisp get called out and Aardvark, EverParse3D,
// XML-GL stay silent. Capped at 2 and shared by ≥2 creators.
const FAMOUS = new Set([
  'ALGOL 60', 'ALGOL 68', 'SQL', 'QUEL',
  'B', 'C', 'C++', 'C#', 'D', 'JAVA', 'JAVASCRIPT', 'TYPESCRIPT', 'PYTHON',
  'RUBY', 'RUST', 'GO', 'SWIFT', 'KOTLIN', 'SCALA', 'CLOJURE', 'DART',
  'PHP', 'PERL', 'R', 'LUA', 'JULIA', 'MATLAB', 'HACK', 'CRYSTAL',
  'SOLIDITY', 'CARBON',
  'COMMON LISP', 'LISP', 'INTERLISP', 'MACLISP', 'SCHEME', 'RACKET', 'GUILE',
  'ML', 'CAML', 'OCAML', 'HASKELL', 'AGDA', 'ERLANG', 'ELIXIR',
  'BASIC', 'FORTRAN', 'COBOL', 'PASCAL', 'SIMULA', 'SNOBOL', 'PROLOG',
  'SMALLTALK', 'APL',
  'AWK', 'UNIX', 'SHELL', 'BASH', 'LEX', 'M4', 'ASSEMBLY', 'VERILOG', 'SCRATCH',
  'HTML', 'CSS', 'DOT', 'JQ', 'GRAPHQL', 'SPARQL',
]);
const compLabels = {};
COMPONENTS.forEach(c => {
  const counts = {};
  for (const n of allNodes) {
    if (n.component !== c.rank) continue;
    for (const l of n.languages) counts[l] = (counts[l] || 0) + 1;
  }
  const names = Object.entries(counts)
    .sort((a, b) => b[1] - a[1])
    .filter(e => e[1] >= 2 && FAMOUS.has(e[0].trim().toUpperCase()))
    .slice(0, 2)
    .map(e => e[0]);
  // Break each name into one line per word, but keep a trailing number on
  // the same line as its word ("SEQUEL 2" stays together, "COMMON LISP" splits).
  const lines = [];
  names.forEach((name, i) => {
    const parts = [];
    for (const w of name.split(' ')) {
      if (/^\d/.test(w) && parts.length) parts[parts.length - 1] += ' ' + w;
      else parts.push(w);
    }
    parts.forEach(p => lines.push({ text: p.toUpperCase(), primary: i === 0 }));
  });
  compLabels[c.rank] = lines;
});

// Edges are intentionally NOT palette-driven: they stay a light neutral so
// they read against the dark background no matter which ramp the nodes use.
const LINK_COLOR = '#F2F6FF';

function buildCompColors() {
  const n = COMPONENTS.length;
  COMPONENTS.forEach((c, i) => {
    // `palette` is either a d3.interpolate* function or a d3.scheme* array.
    const c_ = (typeof palette === 'function')
      ? palette(n > 1 ? (REVERSE ? 1 - i / (n - 1) : i / (n - 1)) : 0)
      : palette[(REVERSE ? n - 1 - i : i) % palette.length];
    COMP_COLOR[c.rank] = c_;
  });
}

// Paint the page chrome (headings, numbers, sliders, hovers) with the same
// ramp as the nodes. Note this deliberately ignores REVERSE: that flag only
// decides which end the *largest component* gets, while the UI always needs
// the bright end or it would vanish into the dark background.
function applyTheme() {
  const root = document.documentElement.style;
  const isFn = typeof palette === 'function';
  const at = t => isFn
    ? palette(t)
    : palette[Math.round(t * (palette.length - 1))];
  // Headline accent: brightest step of the ramp.
  const primary = d3.rgb(at(1));
  // Secondary: a step back down the ramp so it reads as related-but-dimmer.
  const secondary = d3.rgb(at(0.6));
  root.setProperty('--amber', primary.formatHex());
  root.setProperty('--amber2', secondary.formatHex());
  root.setProperty('--accent-rgb', [primary.r, primary.g, primary.b].join(','));
}

let wrapEl = null;
let svg = null, g = null, zoom = null, simulation = null, linkSel = null, nodeSel = null;
let minWeight = 1;
let selectedNode = null;
let labelTopY = null; // top of the first-row labels, for fitView bounding

const fmt = n => Number(n).toLocaleString();
const escHtml = s => String(s == null ? '' : s).replace(/&/g,'&amp;').replace(/</g,'&lt;').replace(/>/g,'&gt;').replace(/"/g,'&quot;').replace(/'/g,'&#39;');
const nodeIdOf = ref => (ref && typeof ref === 'object') ? ref.id : ref;
const ordinal = n => {
  const s = ['th', 'st', 'nd', 'rd'];
  const v = n % 100;
  return n + (s[(v - 20) % 10] || s[v] || s[0]);
};

function hexToRgba(hex, alpha) {
  let h = (hex || '#ffffff').replace('#', '');
  if (h.length === 3) h = h.split('').map(c => c + c).join('');
  const r = parseInt(h.substring(0, 2), 16) || 0;
  const g = parseInt(h.substring(2, 4), 16) || 0;
  const b = parseInt(h.substring(4, 6), 16) || 0;
  return 'rgba(' + r + ',' + g + ',' + b + ',' + alpha + ')';
}

const radiusOf = d => 3 + 1.6 * Math.log2((d.visDeg || 0) + 1);
const weightAlpha = l => Math.min(0.9, 0.25 + (l.weight || 1) * 0.2);
const weightWidth = l => 2 + (l.weight || 1) * 0.7;

// ═══════════════════════════════════════════
// INIT
// ═══════════════════════════════════════════
function init() {
  const setLD = (t, p) => {
    document.getElementById('ld-msg').textContent = t;
    document.getElementById('ld-fill').style.width = p + '%';
  };
  setLD('Building graph…', 40);
  applyTheme();
  const wf = document.getElementById('weight-filter');
  wf.max = MAX_WEIGHT;
  wf.value = 1;
  buildCompColors();
  buildGraph();
  buildTunePanel();
  buildSearch();
  setLD('Rendering…', 90);
  setTimeout(() => { document.getElementById('loader').style.display = 'none'; }, 700);
}

// ═══════════════════════════════════════════
// COMPONENT GRID + FORCE
// ═══════════════════════════════════════════
function buildGraph() {
  wrapEl = document.getElementById('graph-wrap');
  const width = wrapEl.clientWidth, height = wrapEl.clientHeight;

  // Create the SVG container (origin at the center, like the example's
  // viewBox: [-width / 2, -height / 2, width, height]).
  svg = d3.select(wrapEl).append('svg')
    .attr('width', width)
    .attr('height', height)
    .attr('viewBox', [-width / 2, -height / 2, width, height])
    .attr('style', 'max-width:100%;height:100%;');

  g = svg.append('g');

  // Pan/zoom (the 2D analogue of the 3D camera). Dragging a node still
  // wins over panning because d3.drag stops the mousedown's propagation.
  zoom = d3.zoom()
    .scaleExtent([0.05, 20])
    .on('zoom', event => g.attr('transform', event.transform));
  svg.call(zoom);

  const linkG = g.append('g').attr('fill', 'none').attr('stroke-linecap', 'round');
  const nodeG = g.append('g').attr('stroke', '#fff').attr('stroke-width', 1.5);

  // ── Component grid ─────────────────────────────────────────────────
  // Components are laid out in a grid (gridN per row), rank 1 (the largest)
  // at the top-left, reading left → right, top → bottom. Each column's gap
  // to the next grows with the largest components in those two columns, so
  // the biggest components get the most room while every row keeps the same
  // width (columns stay aligned). Link and charge physics are untouched —
  // the grid force (below) pins each component's centroid to its anchor, and
  // the confinement force keeps each component's shape compact.
  // ───────────────────────────────────────────────────────────────────
  const nComps = COMPONENTS.length || 1;
  // Match the grid's aspect ratio to the viewport so it fills the page's
  // width and height instead of always forming a square.
  const gridN = Math.min(nComps, Math.max(1, Math.ceil(Math.sqrt(nComps * (width / height)))));
  const gridRows = Math.ceil(nComps / gridN);
  const BASE = 120;    // px between two smallest components
  const PER_NODE = 2;  // extra px per node shared by two neighbouring columns
  const dist = (a, b) => BASE + PER_NODE * (a + b);
  const ROW_GAP = 240; // vertical gap between rows

  // Column x positions: the gap between column j and j+1 uses the largest
  // component in each (row 0 holds the biggest of every column).
  const colX = [];
  let acc = 0;
  for (let j = 0; j < gridN; j++) {
    colX.push(acc);
    if (j < gridN - 1) acc += dist(COMPONENTS[j].size, COMPONENTS[j + 1].size);
  }
  const midX = acc / 2;

  const compAnchor = {};
  COMPONENTS.forEach((c, i) => {
    const col = i % gridN;
    const row = Math.floor(i / gridN);
    compAnchor[c.rank] = {
      x: colX[col] - midX,
      y: (row - (gridRows - 1) / 2) * ROW_GAP,
    };
  });

  // ── Component labels ──────────────────────────────────────────────
  // Stack each labelled component's top languages above it, in a group that
  // zooms with the graph. Primary language bold/amber, the rest dimmer.
  const labelG = g.append('g').attr('pointer-events', 'none').attr('class', 'labels');
  const compLabelGroups = {};
  const LABEL_GAP = 22, PRIMARY_LH = 40, SECONDARY_LH = 24;
  COMPONENTS.forEach(c => {
    const grp = labelG.append('g');
    compLabelGroups[c.rank] = grp;
    (compLabels[c.rank] || []).forEach(line => {
      grp.append('text')
        .attr('class', line.primary ? 'clabel clabel-primary' : 'clabel clabel-secondary')
        .attr('text-anchor', 'middle')
        .text(line.text);
    });
  });

  function positionLabels() {
    let top = Infinity;
    for (const c of COMPONENTS) {
      const grp = compLabelGroups[c.rank];
      const lines = compLabels[c.rank] || [];
      let minY = Infinity, sumX = 0, cnt = 0;
      for (const n of allNodes) {
        if (n.component !== c.rank) continue;
        if (n.y < minY) minY = n.y;
        sumX += n.x; cnt++;
      }
      if (!cnt) { grp.style('display', 'none'); continue; }
      grp.style('display', null);
      const cx = sumX / cnt;
      const ys = new Array(lines.length);
      let base = minY - LABEL_GAP;
      for (let i = lines.length - 1; i >= 0; i--) {
        ys[i] = base;
        base -= (lines[i].primary ? PRIMARY_LH : SECONDARY_LH);
      }
      grp.selectAll('text').attr('x', cx).attr('y', (d, i) => ys[i]);
      if (ys.length && ys[0] - PRIMARY_LH < top) top = ys[0] - PRIMARY_LH;
    }
    labelTopY = top;
  }

  // Grid force: every tick, translate each component rigidly toward its
  // cell center. Because the whole component moves together, its internal
  // shape stays exactly what link + charge produce — the force only pins
  // the centroid, like moving a group in a vector editor.
  function componentGridForce(anchors, strength) {
    let nodes = [];
    const byComp = new Map();
    function force(alpha) {
      byComp.clear();
      for (const n of nodes) {
        let arr = byComp.get(n.component);
        if (!arr) byComp.set(n.component, arr = []);
        arr.push(n);
      }
      for (const [r, arr] of byComp) {
        const a = anchors[r];
        if (!a) continue;
        let cx = 0, cy = 0;
        for (const n of arr) { cx += n.x; cy += n.y; }
        cx /= arr.length; cy /= arr.length;
        const dx = (a.x - cx) * strength * alpha;
        const dy = (a.y - cy) * strength * alpha;
        for (const n of arr) { n.vx += dx; n.vy += dy; }
      }
    }
    force.initialize = ns => { nodes = ns; };
    return force;
  }

  // Confinement force: a gentle pull of every node toward its own
  // component's centroid. In the original page the surrounding cloud of all
  // other creators pressed each component into a compact shape; a component
  // alone in a cell has no such pressure and relaxes into a stretched-out
  // star, so this spring restores that compact look. Strength falls off
  // mildly with component size (the original cloud pressed small components
  // relatively harder). Link + charge are untouched — this only replaces
  // the cloud's confinement.
  function componentConfineForce(baseStrength) {
    let nodes = [];
    const byComp = new Map();
    const cent = new Map();
    const kOf = {};
    COMPONENTS.forEach(c => {
      kOf[c.rank] = baseStrength * Math.pow(2 / Math.max(2, c.size), 0.15);
    });
    function force(alpha) {
      byComp.clear(); cent.clear();
      for (const n of nodes) {
        let arr = byComp.get(n.component);
        if (!arr) byComp.set(n.component, arr = []);
        arr.push(n);
      }
      for (const [r, arr] of byComp) {
        let cx = 0, cy = 0;
        for (const n of arr) { cx += n.x; cy += n.y; }
        cx /= arr.length; cy /= arr.length;
        cent.set(r, { x: cx, y: cy });
      }
      for (const n of nodes) {
        const c = cent.get(n.component);
        if (!c) continue;
        const k = kOf[n.component] || baseStrength;
        n.vx += (c.x - n.x) * k * alpha;
        n.vy += (c.y - n.y) * k * alpha;
      }
    }
    force.initialize = ns => { nodes = ns; };
    return force;
  }

  // Start each node at (a jittered copy of) its component's cell center so
  // the simulation settles already organized into the grid.
  allNodes.forEach(n => {
    const a = compAnchor[n.component] || { x: 0, y: 0 };
    n.x = a.x + (Math.random() - 0.5) * 20;
    n.y = a.y + (Math.random() - 0.5) * 20;
  });

  // Create a simulation with several forces — the same physics as before
  // (link + charge unchanged); the grid force pins each component's cell and
  // the confinement force keeps each component's shape compact.
  simulation = d3.forceSimulation(allNodes)
    .force('link', d3.forceLink(allLinks).id(d => d.id).distance(30))
    .force('charge', d3.forceManyBody().strength(-120))
    .force('grid', componentGridForce(compAnchor, 5))
    .force('confine', componentConfineForce(0.15));

  // Add a line for each link, and a circle for each node.
  linkSel = linkG.selectAll('line')
    .data(allLinks)
    .join('line')
      .attr('stroke-width', weightWidth)
      .attr('stroke', l => hexToRgba(LINK_COLOR, weightAlpha(l)))
      .on('mouseover', showLinkTip)
      .on('mousemove', moveTip)
      .on('mouseout', hideTip);

  nodeSel = nodeG.selectAll('circle')
    .data(allNodes)
    .join('circle')
      .attr('r', radiusOf)
      .attr('fill', d => hexToRgba(compColor(d.component), 0.9))
      .attr('cursor', 'pointer')
      .on('click', (event, d) => { event.stopPropagation(); openPanel(d.id); })
      .on('mouseover', showNodeTip)
      .on('mousemove', moveTip)
      .on('mouseout', hideTip);

  // Add a drag behavior (verbatim from the example).
  nodeSel.call(d3.drag()
    .on('start', dragstarted)
    .on('drag', dragged)
    .on('end', dragended));

  // Set the position attributes of links and nodes each time the simulation
  // ticks (verbatim from the example).
  simulation.on('tick', () => {
    linkSel
      .attr('x1', d => d.source.x)
      .attr('y1', d => d.source.y)
      .attr('x2', d => d.target.x)
      .attr('y2', d => d.target.y);
    nodeSel
      .attr('cx', d => d.x)
      .attr('cy', d => d.y);
    positionLabels();
  });

  svg.on('click', () => closePanel());

  document.getElementById('btn-fit').addEventListener('click', fitView);

  document.getElementById('weight-filter').addEventListener('input', e => {
    minWeight = parseInt(e.target.value, 10);
    document.getElementById('weight-val').textContent = minWeight;
    updateGraph();
  });

  window.addEventListener('resize', () => {
    const w = wrapEl.clientWidth, h = wrapEl.clientHeight;
    svg.attr('width', w).attr('height', h).attr('viewBox', [-w / 2, -h / 2, w, h]);
  });

  updateGraph();
  // Let the layout spread, then frame the whole graph once.
  setTimeout(fitView, 1400);
  // Re-frame once the simulation has fully cooled: the first fit happens
  // while components are still settling, so it frames a slightly larger
  // bounding box than the final grid. Only the first cool-down refits —
  // later ones (after drags) leave the user's zoom alone.
  let viewFitted = false;
  simulation.on('end', () => {
    if (!viewFitted) { viewFitted = true; fitView(); }
  });
}

// Reheat the simulation when drag starts, and fix the subject position.
function dragstarted(event) {
  if (!event.active) simulation.alphaTarget(0.3).restart();
  event.subject.fx = event.subject.x;
  event.subject.fy = event.subject.y;
}

// Update the subject (dragged node) position during drag.
function dragged(event) {
  event.subject.fx = event.x;
  event.subject.fy = event.y;
}

// Restore the target alpha so the simulation cools after dragging ends.
// Unfix the subject position now that it's no longer being dragged.
function dragended(event) {
  if (!event.active) simulation.alphaTarget(0);
  event.subject.fx = null;
  event.subject.fy = null;
}

// ═══════════════════════════════════════════
// FILTERING (weight + component) via display toggling
// ═══════════════════════════════════════════
function linkVisible(l) {
  return (l.weight || 1) >= minWeight;
}

function updateGraph() {
  let edgeCount = 0;
  const activeNodes = new Set();
  const degMap = {};

  allLinks.forEach(l => {
    if (!linkVisible(l)) return;
    const s = nodeIdOf(l.source), t = nodeIdOf(l.target);
    edgeCount++;
    activeNodes.add(s);
    activeNodes.add(t);
    degMap[s] = (degMap[s] || 0) + 1;
    degMap[t] = (degMap[t] || 0) + 1;
  });

  allNodes.forEach(n => { n.visDeg = degMap[n.id] || 0; });

  // Isolated creators (degree 0) are never on a link, so they stay visible
  // no matter what the weight filter is set to.
  allNodes.forEach(n => { if ((n.deg || 0) === 0) activeNodes.add(n.id); });

  document.getElementById('s-nodes').textContent = fmt(activeNodes.size);
  document.getElementById('s-edges').textContent = fmt(edgeCount);

  linkSel.attr('display', l => linkVisible(l) ? null : 'none');
  nodeSel
    .attr('display', d => activeNodes.has(d.id) ? null : 'none')
    .attr('r', radiusOf);

  applyHighlight(selectedNode);
}

// ═══════════════════════════════════════════
// HIGHLIGHTING
// ═══════════════════════════════════════════
function applyHighlight(id) {
  if (!id) {
    nodeSel
      .attr('fill', d => hexToRgba(compColor(d.component), 0.9))
      .attr('stroke-opacity', 1)
      .attr('stroke-width', 1.5);
    linkSel
      .attr('stroke', l => hexToRgba(LINK_COLOR, weightAlpha(l)))
      .attr('stroke-width', weightWidth);
    return;
  }
  const neighbors = new Set([id]);
  allLinks.forEach(l => {
    if ((l.weight || 1) < minWeight) return;
    const s = nodeIdOf(l.source), t = nodeIdOf(l.target);
    if (s === id) neighbors.add(t);
    if (t === id) neighbors.add(s);
  });
  // Dim the *stroke* as well as the fill: every circle inherits a white
  // stroke from the node group, so fading only the fill still leaves
  // unrelated nodes (and whole other components) visible as white rings.
  nodeSel
    .attr('fill', d => {
      if (d.id === id) return HIGHLIGHT;
      if (neighbors.has(d.id)) return hexToRgba(compColor(d.component), 1);
      return hexToRgba(compColor(d.component), 0.06);
    })
    .attr('stroke-opacity', d => (d.id === id || neighbors.has(d.id)) ? 1 : 0)
    .attr('stroke-width', d => (d.id === id || neighbors.has(d.id)) ? 1.5 : 0);
  linkSel
    .attr('stroke', l => {
      const s = nodeIdOf(l.source), t = nodeIdOf(l.target);
      return (s === id || t === id) ? hexToRgba(LINK_COLOR, 1) : hexToRgba(LINK_COLOR, 0.01);
    })
    .attr('stroke-width', l => (nodeIdOf(l.source) === id || nodeIdOf(l.target) === id) ? 2.5 : 0);
}

// ═══════════════════════════════════════════
// TOOLTIPS
// ═══════════════════════════════════════════
function nodeTip(d) {
  const bits = [];
  if (d.langCount) bits.push(d.langCount + (d.langCount === 1 ? ' language' : ' languages'));
  if (d.deg) bits.push(d.deg + ' co-creator' + (d.deg === 1 ? '' : 's'));
  return '<div class="tt-name">' + escHtml(d.label) + '</div>'
    + '<div class="tt-type">Creator</div>'
    + (bits.length ? '<div class="tt-sub">' + escHtml(bits.join(' · ')) + '</div>' : '');
}

function linkTip(l) {
  const a = (NODE_BY_ID[nodeIdOf(l.source)] || {}).label || nodeIdOf(l.source);
  const b = (NODE_BY_ID[nodeIdOf(l.target)] || {}).label || nodeIdOf(l.target);
  const shared = l.shared || [];
  const n = shared.length;
  return '<div class="tt-name">' + escHtml(a) + ' ↔ ' + escHtml(b) + '</div>'
    + '<div class="tt-sub">Co-created ' + n + ' language' + (n === 1 ? '' : 's')
    + (n ? ': ' + escHtml(shared.slice(0, 12).join(', ')) + (n > 12 ? '…' : '') : '') + '</div>';
}

function showNodeTip(event, d) {
  const el = document.getElementById('tooltip');
  el.innerHTML = nodeTip(d);
  el.style.display = 'block';
  moveTip(event);
}

function showLinkTip(event, l) {
  const el = document.getElementById('tooltip');
  el.innerHTML = linkTip(l);
  el.style.display = 'block';
  moveTip(event);
}

function moveTip(event) {
  const el = document.getElementById('tooltip');
  const pad = 16;
  let x = event.clientX + pad, y = event.clientY + pad;
  const r = el.getBoundingClientRect();
  if (x + r.width > window.innerWidth) x = event.clientX - r.width - pad;
  if (y + r.height > window.innerHeight) y = event.clientY - r.height - pad;
  el.style.left = x + 'px';
  el.style.top = y + 'px';
}

function hideTip() {
  document.getElementById('tooltip').style.display = 'none';
}

// ═══════════════════════════════════════════
// VIEW (fit / focus)
// ═══════════════════════════════════════════
function fitView() {
  if (!svg) return;
  let x0 = Infinity, y0 = Infinity, x1 = -Infinity, y1 = -Infinity, any = false;
  allNodes.forEach(n => {
    // Skip nodes hidden by the weight filter, but keep isolated creators
    // (degree 0) in the framing.
    if (n.visDeg <= 0 && (n.deg || 0) > 0) return;
    if (n.x == null || n.y == null) return;
    any = true;
    x0 = Math.min(x0, n.x); x1 = Math.max(x1, n.x);
    y0 = Math.min(y0, n.y); y1 = Math.max(y1, n.y);
  });
  if (!any) return;
  // Labels sit above their component; include the topmost label's extent so
  // the fit doesn't clip it off the top of the view.
  if (labelTopY != null && isFinite(labelTopY)) y0 = Math.min(y0, labelTopY);
  const w = wrapEl.clientWidth, h = wrapEl.clientHeight;
  const dx = Math.max(1, x1 - x0), dy = Math.max(1, y1 - y0);
  const pad = 60;
  const k = Math.max(0.05, Math.min(8, Math.min((w - 2 * pad) / dx, (h - 2 * pad) / dy)));
  const cx = (x0 + x1) / 2, cy = (y0 + y1) / 2;
  svg.transition().duration(700).call(zoom.transform, d3.zoomIdentity.translate(-k * cx, -k * cy).scale(k));
}

function focusNode(node) {
  if (!svg || !node || node.x == null) return;
  const k = 2;
  svg.transition().duration(700).call(zoom.transform, d3.zoomIdentity.translate(-k * node.x, -k * node.y).scale(k));
}

// ═══════════════════════════════════════════
// NODE PANEL
// ═══════════════════════════════════════════
function openPanel(id) {
  const n = NODE_BY_ID[id];
  if (!n) return;
  if (selectedNode === id) { closePanel(); return; }
  selectedNode = id;
  applyHighlight(id);

  const langs = n.languages || [];
  let meta = '<div class="np-meta"><span class="np-meta-lbl">Languages created · </span>' + langs.length + '</div>'
    + '<div class="np-meta"><span class="np-meta-lbl">Co-creators · </span>' + fmt(n.deg) + '</div>';
  if (n.component) meta += '<div class="np-meta"><span class="np-meta-lbl">Component · </span>' + ordinal(n.component) + ' largest (' + fmt(n.compSize) + ' creators)</div>';

  document.getElementById('np-head').innerHTML =
    '<div style="display:flex;justify-content:space-between;align-items:flex-start;padding-right:40px;margin-bottom:4px">'
    + '<div class="np-name">' + escHtml(n.label) + '</div>'
    + '<button id="np-focus-btn" style="background:none;border:none;cursor:pointer;color:var(--text2);transition:color .15s;margin-top:8px;flex-shrink:0" title="Focus camera on node" onmouseover="this.style.color=\'var(--text)\'" onmouseout="this.style.color=\'var(--text2)\'">'
    + '<svg width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><circle cx="12" cy="12" r="3"></circle><path d="M19 12h2"></path><path d="M3 12h2"></path><path d="M12 3v2"></path><path d="M12 19v2"></path></svg>'
    + '</button></div>'
    + '<div class="np-type" style="color:' + NODE_COLOR + ';border-color:' + NODE_COLOR + '">Creator</div>'
    + meta;

  setTimeout(() => {
    const btn = document.getElementById('np-focus-btn');
    if (btn) btn.addEventListener('click', () => focusNode(allNodes.find(x => x.id === id)));
  }, 0);

  // Languages created (plain list)
  let html = '<div class="np-sec open">'
    + '<div class="np-sec-hdr" onclick="this.parentElement.classList.toggle(\'open\')">'
    + '<span class="np-sec-title" style="color:' + NODE_COLOR + '">Languages</span>'
    + '<span class="np-sec-n">' + langs.length + '</span></div><div class="np-items">';
  langs.slice(0, 60).forEach(l => {
    html += '<div class="np-item plain"><div class="np-item-name">' + escHtml(l) + '</div></div>';
  });
  if (langs.length > 60) html += '<div style="padding:8px 16px 12px 32px;color:var(--text3);font-size:14px;font-weight:600">+' + (langs.length - 60) + ' MORE</div>';
  html += '</div></div>';

  // Co-creators with how many languages they share (navigable)
  const co = {};
  allLinks.forEach(l => {
    const s = nodeIdOf(l.source), t = nodeIdOf(l.target);
    const w = l.weight || 1;
    if (s === id) co[t] = (co[t] || 0) + w;
    else if (t === id) co[s] = (co[s] || 0) + w;
  });
  const coList = Object.entries(co).sort((a, b) => b[1] - a[1]);
  html += '<div class="np-sec open">'
    + '<div class="np-sec-hdr" onclick="this.parentElement.classList.toggle(\'open\')">'
    + '<span class="np-sec-title" style="color:' + EDGE_COLOR + '">Co-creators</span>'
    + '<span class="np-sec-n">' + coList.length + '</span></div><div class="np-items">';
  coList.slice(0, 80).forEach(([cid, cnt]) => {
    const cname = (NODE_BY_ID[cid] && NODE_BY_ID[cid].label) || cid;
    html += '<div class="np-item" data-nav="' + escHtml(cid) + '">'
      + '<div class="np-item-name">' + escHtml(cname) + '</div>'
      + '<div class="np-item-sub">' + cnt + ' shared language' + (cnt === 1 ? '' : 's') + '</div></div>';
  });
  if (coList.length > 80) html += '<div style="padding:8px 16px 12px 32px;color:var(--text3);font-size:14px;font-weight:600">+' + (coList.length - 80) + ' MORE</div>';
  html += '</div></div>';

  document.getElementById('np-rels').innerHTML = html;
  document.getElementById('node-panel').classList.add('open');
}

function closePanel() {
  selectedNode = null;
  applyHighlight(null);
  document.getElementById('node-panel').classList.remove('open');
}

document.getElementById('np-close').addEventListener('click', closePanel);
document.getElementById('np-rels').addEventListener('click', e => {
  const el = e.target.closest('[data-nav]');
  if (el) openPanel(el.dataset.nav);
});

// ═══════════════════════════════════════════
// FORCE TUNING PANEL
// ═══════════════════════════════════════════
function buildTunePanel() {
  const body = document.getElementById('tune-body');

  const sliders = [
    { id: 't-charge',   label: 'Charge',   min: -600, max: 0,   step: 10, val: -120, set: v => { simulation.force('charge').strength(v); simulation.alpha(1).restart(); } },
    { id: 't-linkdist', label: 'Link Dist', min: 10,  max: 200, step: 2,  val: 30,   set: v => { simulation.force('link').distance(v); simulation.alpha(1).restart(); } },
  ];

  body.innerHTML = sliders.map(s =>
    '<div style="margin-top:12px">'
    + '<div style="display:flex;justify-content:space-between;font-size:14px;font-weight:600;color:var(--text3);letter-spacing:1px;text-transform:uppercase;margin-bottom:6px">'
    + '<span>' + s.label + '</span><span id="' + s.id + '-val" style="color:var(--amber)">' + s.val + '</span></div>'
    + '<input type="range" id="' + s.id + '" min="' + s.min + '" max="' + s.max + '" step="' + s.step + '" value="' + s.val + '" style="width:100%;accent-color:var(--amber);cursor:pointer;height:14px">'
    + '</div>'
  ).join('');

  sliders.forEach(s => {
    document.getElementById(s.id).addEventListener('input', function () {
      const v = parseFloat(this.value);
      document.getElementById(s.id + '-val').textContent = v;
      if (simulation) s.set(v);
    });
  });
}

// ═══════════════════════════════════════════
// SEARCH
// ═══════════════════════════════════════════
function buildSearch() {
  const input = document.getElementById('node-search');
  const resultsEl = document.getElementById('search-results');
  let hideTimeout = null;

  function getSortedNodes() {
    const visible = allNodes.filter(n => n.visDeg > 0 || (n.deg || 0) === 0);
    visible.sort((a, b) => (b.visDeg || 0) - (a.visDeg || 0));
    return visible;
  }

  function renderResults(q) {
    const list = getSortedNodes();
    const query = (q || '').trim().toLowerCase();
    let matches;
    if (query.length === 0) {
      matches = list.slice(0, 40);
    } else {
      matches = list.filter(n => (n.label + ' ' + n.id).toLowerCase().includes(query)).slice(0, 25);
    }
    if (!matches.length) {
      resultsEl.innerHTML = '<div style="padding:12px 16px;font-size:16px;font-weight:500;color:var(--text3)">No results</div>';
      resultsEl.style.display = 'block';
      return;
    }
    resultsEl.innerHTML = matches.map((n, i) => {
      let display = n.label;
      if (query.length > 0) {
        const idx = n.label.toLowerCase().indexOf(query);
        if (idx >= 0) {
          display = escHtml(n.label.slice(0, idx)) + '<span style="color:var(--amber);font-weight:700">' + escHtml(n.label.slice(idx, idx + query.length)) + '</span>' + escHtml(n.label.slice(idx + query.length));
        } else {
          display = escHtml(n.label);
        }
      }
      const sub = (n.langCount || 0) + ' language' + ((n.langCount || 0) === 1 ? '' : 's');
      return '<div class="sr-item" data-nav="' + escHtml(n.id) + '" style="padding:10px 16px;font-size:16px;font-weight:500;color:var(--text2);cursor:pointer;transition:background .08s;display:flex;align-items:center;gap:12px"'
        + ' onmouseover="this.style.background=\'rgba(var(--accent-rgb),.08)\';this.style.color=\'var(--text)\'"'
        + ' onmouseout="this.style.background=\'none\';this.style.color=\'var(--text2)\'">'
        + '<span style="font-size:14px;font-weight:700;color:var(--text3);min-width:34px;text-align:right;flex-shrink:0">#' + (i + 1) + '</span>'
        + '<span style="flex:1;overflow:hidden;text-overflow:ellipsis;white-space:nowrap;min-width:0;">' + display + '</span>'
        + '<span style="font-size:13px;font-weight:600;color:var(--text3);flex-shrink:0">' + sub + '</span>'
        + '</div>';
    }).join('');
    resultsEl.style.display = 'block';
  }

  resultsEl.addEventListener('mousedown', e => {
    const el = e.target.closest('[data-nav]');
    if (el) {
      e.preventDefault();
      input.value = (NODE_BY_ID[el.dataset.nav] && NODE_BY_ID[el.dataset.nav].label) || '';
      resultsEl.style.display = 'none';
      openPanel(el.dataset.nav);
    }
  });

  input.addEventListener('focus', function () { if (hideTimeout) clearTimeout(hideTimeout); renderResults(this.value); });
  input.addEventListener('input', function () { renderResults(this.value); });
  input.addEventListener('blur', function () { hideTimeout = setTimeout(() => { resultsEl.style.display = 'none'; }, 200); });
  input.addEventListener('keydown', function (e) {
    if (e.key === 'Escape') { this.value = ''; resultsEl.style.display = 'none'; closePanel(); }
    if (e.key === 'Enter') {
      const first = resultsEl.querySelector('[data-nav]');
      if (first) {
        input.value = (NODE_BY_ID[first.dataset.nav] && NODE_BY_ID[first.dataset.nav].label) || '';
        resultsEl.style.display = 'none';
        openPanel(first.dataset.nav);
      }
    }
  });
}

init();
</script>
</body>
</html>
'''


def write_html(G: nx.Graph, out_path: str) -> None:
    """Serialize the creator graph and render the single-file D3 HTML."""
    data = graph_to_data(G)
    # Escape "</" inside the JSON so a stray "</script>" in a name can't
    # terminate the inline script block early.
    payload = json.dumps(data, ensure_ascii=False).replace("</", "<\\/")
    html = TEMPLATE.replace("__PLDB_CREATOR_DATA__", payload)
    with open(out_path, "w", encoding="utf-8") as f:
        f.write(html)
