Building a programming language is mostly a solo job. Of the 1,016 programming languages in the Programming Language Database (PLDB) that name their creators, 86% list a single author.

![Creator co-authorship network](featured.png)

A few weeks ago I got curious about how people collaborate to create programming languages. Then I came across PLDB, a public knowledge graph of programming languages. I projected the graph down to people, linking creators whenever they share a language. The results below are from a preliminary analysis.

The network shows that when creators connect, they form closed groups. Of the 1,096 named creators, 739 (67%) appear only as the sole author of a language, so they sit alone, unconnected to anyone. The other 357 connect into 121 components, 114 of them (94%) complete graphs. Most cliques are tiny: 72 pairs, 21 trios, 11 groups of four, and so on. 

The largest is a 16-person component spanning ALGOL 60, ALGOL 68, Fortran, FL, FP, Speedcoding, Lisp, Advice Taker, Elephant 2000, IT, Red, and Superplan. Next is a 9-person component over B, C, M4, awk, grep, Go, AMPL, Limbo, Newsqueak, ivy, and mawk, and a 9-person Lisp component over Common Lisp, Scheme, Emacs Lisp, Lisp Machine Lisp, Corman Common Lisp, Spice Lisp, Plot, and lunar.

Overall, the network is sparse and fragmented. I honestly expected more connections. The 1,096 creators share only 468 links, 0.08% of all possible pairs (0.74% among just the 357 creators who did collaborate). Those links come from 141 multi-author languages. The largest component holds 16 people, 1.5% of all creators.

The graph also helped me find duplicate names. When several people are all credited as creators of the same language, they form a complete graph, so a missing edge is a clue: maybe the same person was listed under two different names. Checking every connected component with a swarm of agents returned 7 confirmed same-person pairs: John G. Kemeny = John George Kemeny (BASIC), Yann Le Cun = Yann LeCun, and so on. I contributed these corrections back to the PLDB repo, and they were merged upstream, so the corrected spellings are now part of the dataset itself.

Two caveats on this. PLDB records creators for only 1,016 of its 3,460 programming languages (those tagged pl), and the rest have no creator entry at all. Counting labs as creators would enlarge the network, but a lab is not a person, so this stays a network of creators. Also, "collaboration" means only sharing a language, which says nothing about later contributors or maintainers.