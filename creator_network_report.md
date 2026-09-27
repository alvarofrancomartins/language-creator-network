![Creator co-authorship network](featured.png)

Most computer languages are built alone. That is what I found: of the 1,182 languages in the Programming Language Database (PLDB) that name their creators, 85% list a single author.

A few weeks ago, I got curious about how people collaborate to create computer languages. Luckily, I found PLDB, which is a knowledge graph of computer languages. To work with it, I projected the graph down to people, linking creators whenever they share a language.

The network shows that when creators connect, they form closed groups. The 472 creators who co-created a language form 148 separate clusters (connected components). 136 of them (92%) are complete graphs: everyone in the group has co-created with everyone else. Most cliques are tiny: 84 pairs, 26 trios, 10 groups of four, 7 of five, 5 of six, 1 of seven, 2 of eight, 1 of ten. Those 148 clusters split into 106 (72%) built from a single language, 30 (20%) complete graphs spanning several languages, and 12 (8%) that are not complete.

Then there are these 12 clusters that break the pattern. These are held together only indirectly, by creators who bridge languages, since no single language credits them all. The largest is a 16-person cluster around ALGOL 60: 13 members share ALGOL 60, and Adriaan van Wijngaarden, credited on both ALGOL 60 and ALGOL 68, pulls in three ALGOL 68 authors. John Backus and Peter Naur also share BNF, Backus reaches Fortran, FP, FL, and Speedcoding, and John McCarthy reaches Lisp. Next, a 13-person IBM SQL cluster, where Donald Chamberlin spans SEQUEL 2, SQUARE, and SQL while Raymond Boyce shares only SQL and SQUARE, and Raymond Lorie bridges in GML through SEQUEL 2. A 9-person Bell Labs cluster has Ken Thompson, Dennis Ritchie, and Brian Kernighan tying awk, Go, B, and M4 together. Another 9-person cluster is Lisp, where Guy Steele alone spans Common Lisp and Scheme, Gerald Jay Sussman sits only in Scheme, and Richard Stallman reaches in through Emacs Lisp and Lisp Machine Lisp.

Overall, the network is sparse and fragmented. The 472 connected creators share 712 links, which represents only 0.64% of all possible pairs. Those links come from 176 multi-author languages. The largest cluster holds 16 people, 3% of the connected network. A null model confirms the fragmentation is real (a uniformly random graph with the same number of nodes and edges would have a cluster of ~400 people).

A side benefit of working with the graph was name resolution. When several people are all credited as creators of the same language, they form a complete graph, so a missing edge is a clue: two people who never collaborated, but maybe the same person was listed under two different names. Checking every connected component with a swarm of agents returned 7 confirmed same-person pairs:

- John G. Kemeny = John George Kemeny (BASIC)
- Dan Weinreb    = Daniel Weinreb
- Dave Moon      = David A. Moon
- Mary Fernandez = Mary Fernández
- Léon Bottou    = Leon Bottou
- Yann Le Cun    = Yann LeCun
- John W. Cowan  = John Cowan

I contributed these corrections back to the PLDB repo, and they were merged upstream, so the corrected spellings are now part of the dataset itself.

Two caveats: PLDB records creators for only 1,182 of its 3,850 languages, so most have no creator data (the ones without creator data are mostly corporate or committee-authored) and "collaboration" means only sharing a language, which says nothing about later contributors or maintainers. 