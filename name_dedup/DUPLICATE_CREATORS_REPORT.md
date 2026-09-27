# PLDB Co-creation Network — Duplicate Creator Audit

Audit of the PLDB co-creation network (689 creators, 976 links, 220 connected
components) for creator nodes that most likely refer to the same real person
but were not merged by the dataset.

- **Method**: swarm of 7 review agents (one per component batch, each applying
  a graph-pattern investigation guideline) + 1 verification agent that
  web-checked every HIGH/MEDIUM candidate.
- **Result**: 7 unique candidate pairs, all 7 web-verified **confirmed**.
  0 LOW-confidence candidates.

## Two-stage method

The audit was not a single heuristic. It ran in two stages, and the second
stage (the exhaustive component review) is where most of the value came from.

1. **Deterministic lead generator** (`prep.py`): cheap pattern checks with
   hard thresholds (Jaccard ≥ 0.5, node degree ≤ 3, fuzzy ratio ≥ 0.85).
   Six lead types: NORM (identical after normalization), INIT (single-letter
   token expanded to a same-initial longer token), FUZZY (edit-similar),
   MISSING_EDGE (non-adjacent with a shared neighbor), ADJACENT (linked with
   similar names), RARE_LANG (similar names sharing a language). This produced
   20 leads, most of them MISSING_EDGE false positives.
2. **Swarm review**: 7 review agents, one per component batch (the 220
   components split into 7 batches), each given the full subgraph of every
   component in its batch (all nodes, links, languages) plus that batch's
   leads, and instructed to review **every connected component** (isolated
   nodes skipped). This exhaustive pass is where 4 of the 7 finds came from.

## Investigation patterns

| Tag | Pattern |
|---|---|
| P1 | **Missing-edge clique** (the graph-theory tell): two non-adjacent nodes that share neighbor(s). If they were one person, the subgraph would be a clique — the missing edge is the scar of an unmerged duplicate. |
| P2 | **Adjacent variants**: similar names that *are* linked — one person listed twice on the same language record. |
| P3 | **Shared-language corroboration**: both names credited with the same (especially rare) language. |
| P4 | **Name-variant matching**: honorifics, initial ↔ full name, accents/diacritics, nicknames (Dave/David, Dan/Daniel, …), middle initial dropped/added, whitespace variants. |

## Confirmed same-person pairs

| Pair | Patterns | Graph evidence | Verdict |
|---|---|---|---|
| **John G. Kemeny = John George Kemeny** | P1, P4 (initial expansion) | Both deg 1, not adjacent, share only Thomas E. Kurtz (Jaccard 1.00) — a triangle missing exactly one edge. BASIC/Dartmouth BASIC on one node, True BASIC on the other. | ✅ confirmed — Wikipedia: "John G. Kemeny" is the biography of John George Kemeny, co-developer of BASIC with Kurtz; Library of Congress authority file also uses "Kemeny, John G." |
| **Dan Weinreb = Daniel Weinreb** | P1, P4 (nickname) | Not linked to each other, both link to David A. Moon — "Dan Weinreb" via Common Lisp/Corman Common Lisp, "Daniel Weinreb" via Lisp Machine Lisp. | ✅ confirmed — Wikipedia redirects "Dan Weinreb" to "Daniel Weinreb". |
| **Dave Moon = David A. Moon** | P1, P4 (nickname + dropped middle initial) | Not adjacent, share Guy Steele — "Dave Moon" via Emacs, "David A. Moon" via Common Lisp/Corman Common Lisp/Lisp Machine Lisp. Missed by the deterministic lead generator (David A. Moon has deg 9 → low Jaccard). | ✅ confirmed — "Dave Moon" redirects to "David A. Moon"; his biography states TECO Emacs "was created and designed by Guy L. Steele Jr. and David Moon". |
| **Mary Fernandez = Mary Fernández** | P1, P4 (diacritics) | Not adjacent, both link to Dan Suciu — "Mary Fernandez" via UnQL, "Mary Fernández" via StruQL. | ✅ confirmed — DSL'99 paper credits "Mary Fernández, Dan Suciu, Igor Tatarinov"; Suciu's own publication list spells the same co-author "Mary Fernandez". |
| **Léon Bottou = Leon Bottou** | P4 (diacritics) | Mirror structure across components: DjVu component pairs "Léon Bottou" with "Yann LeCun"; Lush component pairs "Leon Bottou" with "Yann Le Cun". Lush was actually created by Léon Bottou and Yann LeCun. | ✅ confirmed — Wikipedia biography identifies him as "the original developer of the Lush programming language" and co-creator of DjVu with Yann LeCun. |
| **Yann Le Cun = Yann LeCun** | P4 (whitespace variant) | Same mirror structure as the Bottou pair (DjVu vs Lush components). | ✅ confirmed — birth name "Yann André Le Cun"; the surname is usually spelled LeCun. |
| **John W. Cowan = John Cowan** | P4 (dropped middle initial) | No shared neighbor (different components), but the W3C XML Information Set spec lists editor "John Cowan" with Richard Tobin, and XML 1.1 lists him among exactly the co-editors on the "John W. Cowan" node (Tim Bray, Jean Paoli, C. M. Sperberg-McQueen, Eve Maler, François Yergeau). | ✅ confirmed — W3C specs + Wikipedia's John Woldemar Cowan (XML 1.1 editor, creator of the Queue conlang). |

## Pattern breakdown

- **3 of 7 came straight from the deterministic leads**: Kemeny
  (INIT+MISSING_EDGE), Dan/Daniel Weinreb (FUZZY), Mary Fernandez/Fernández
  (FUZZY).
- **4 of 7 were found by the agents' component-by-component review**, not by
  the lead thresholds:
  - Dave Moon = David A. Moon (P1, but the threshold missed it because David
    A. Moon has degree 9, so his Jaccard with Dave Moon was too low).
  - Léon/Leon Bottou and Yann Le Cun/LeCun (a cross-component mirror: the
    DjVu component pairs "Léon Bottou" with "Yann LeCun" while the Lush
    component pairs "Leon Bottou" with "Yann Le Cun" — two structurally
    identical pairs with variant names).
  - John W. Cowan = John Cowan (pure name variant, the one find with no graph
    signal at all).
- **Graph theory contributed to 6 of 7**: P1 missing-edge on 4, mirror
  components on 2. Only Cowan was found without the graph.
- All 17+ structural false positives from the deterministic leads were
  rejected by the review agents (e.g. distinct co-authors who merely share a
  neighbor).

## Sources

- Dan Weinreb / Daniel Weinreb: https://en.wikipedia.org/wiki/Dan_Weinreb · https://en.m.wikipedia.org/wiki/Daniel_Weinreb
- Dave Moon / David A. Moon: https://en.wikipedia.org/wiki/Dave_Moon · https://en.wikipedia.org/wiki/David_A._Moon
- Mary Fernandez / Mary Fernández: https://usenix.org/legacy/events/dsl99/fernandez.html · https://homes.cs.washington.edu/~suciu/publications-with-Fernandez.html
- Léon Bottou / Leon Bottou: https://en.wikipedia.org/wiki/L%C3%A9on_Bottou
- Yann Le Cun / Yann LeCun: https://en.wikipedia.org/wiki/Yann_LeCun
- John W. Cowan / John Cowan: https://www.w3.org/TR/xml-infoset/ · https://www.w3.org/TR/xml11/ · https://en.wikipedia.org/wiki/John_W._Cowan
- John G. Kemeny / John George Kemeny: https://en.wikipedia.org/wiki/John_G._Kemeny · https://id.loc.gov/authorities/names/n79109161.html
