Most computer languages are built alone. That is what I found: of the 1,182 languages in the Programming Language Database (PLDB) that name their creators, 85% list a single author.

**Computer language co-authorship network**. PLDB is a knowledge graph of computer languages. I projected the graph down to people, linking creators whenever they share a language.

**When creators connect, they form closed groups**. The 472 creators who co-created a language form 148 separate clusters (connected components). 136 of them (92%) are complete graphs: everyone in the group has co-created with everyone else. Most cliques are tiny: 84 pairs, 26 trios, 10 groups of four, 7 of five, 5 of six, 1 of seven, 2 of eight, 1 of ten. Those 148 clusters split into 106 (72%) built from a single language, 30 (20%) complete graphs spanning several languages, and 12 (8%) that are not complete.

Only 12 clusters break the pattern. These are held together only indirectly, by creators who bridge languages, since no single language credits them all. The largest is a 16-person cluster around the ALGOL 60 committee: 13 members share ALGOL 60, and Adriaan van Wijngaarden, credited on both ALGOL 60 and ALGOL 68, pulls in three ALGOL 68 authors. John Backus and Peter Naur also share BNF, Backus reaches Fortran, FP, FL, and Speedcoding, and John McCarthy reaches Lisp. Next, a 13-person IBM SQL cluster, where Donald Chamberlin spans SEQUEL 2, SQUARE, and SQL while Raymond Boyce shares only SQL and SQUARE, and Raymond Lorie bridges in GML through SEQUEL 2. A 9-person Bell Labs cluster has Ken Thompson, Dennis Ritchie, and Brian Kernighan tying awk, Go, B, and M4 together. Another 9-person cluster is Lisp, where Guy Steele alone spans Common Lisp and Scheme, Gerald Jay Sussman sits only in Scheme, and Richard Stallman reaches in through Emacs Lisp and Lisp Machine Lisp.

**The network is sparse and fragmented**. The 472 connected creators share only 712 links, 0.64% of all possible pairs. Those links come from 176 multi-author languages, each a small clique: the largest has 13 creators, and 102 have just two. And 88.6% of all creators are credited on exactly one language.

There is no center. The largest cluster holds 16 people, 3% of the connected network. And that connected network is just 472 of the 1,312 creators; the other 840 have no co-creator at all.

**A null model confirms the fragmentation is real.** A uniformly random graph with the same 472 creators and 712 links would merge into one giant cluster of about 444 people, 94% of the connected network. The real network's largest cluster holds 16, so real collaboration is far more fragmented than random chance would produce.

**What this shows**. In this dataset, most languages have one creator. The collaborations that do exist are small, closed teams, and they are disconnected from each other.

Two caveats: PLDB records creators for only 1,182 of its 3,850 languages, so most have no creator data; and "collaboration" means only sharing a language, which says nothing about later contributors or maintainers. The languages without creator data are mostly corporate or committee-authored (VBScript, ABAP, VHDL, GLSL, and so on). 

**The missing edges hid duplicate names**. A side benefit of working with the graph was name resolution. When several people are all credited as creators of the same language, they form a complete graph, so a missing edge is a clue: two people who never collaborated, or the same person listed under two names. Checking every connected component with a swarm of agents turned up 7 confirmed same-person pairs:

- John G. Kemeny = John George Kemeny (BASIC)
- Dan Weinreb       = Daniel Weinreb
- Dave Moon          = David A. Moon
- Mary Fernandez = Mary Fernández
- Léon Bottou        = Leon Bottou
- Yann Le Cun         = Yann LeCun
- John W. Cowan  = John Cowan

Overall, the graph approach paid off twice: it showed how fragmented language creation is, and it recovered the people the data had recorded under two names.

I contributed these seven corrections back to PLDB, and they were merged upstream, so the corrected spellings are now part of the dataset itself.