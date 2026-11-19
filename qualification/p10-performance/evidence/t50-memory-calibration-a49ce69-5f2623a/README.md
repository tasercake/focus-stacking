# Exact T50 Weighted CPU memory calibration

One fresh explicit CPU job each ran for pinned ChimpStackr
`ab7a92708269c01c6094729f6cdfaf1415677364`, standalone Pancake
`a49ce692371558ff40f72b0af77f5249d00dcedb`, and standalone scratch-alias
Pancake `5f2623ac85682233c20abe12fc691000568ad127` in that order.
The dispatcher was exact `7115ce33e54982ce0a99adee33963c7ac1f53982`.
All three used collector `df780846a4dcc40bf460bcaaba04f1538290e71c`,
the same 3 ms nominal interval, and the original 20 ms actual validity
rule. This calibration excludes the separately assembled `11cfcf8`
Debian package. [Exact operator and pins](../t50-memory-calibration-plan/README.md)
· [Typed summary](summary.json) · [Raw observations](raw-typed-calibration.tar.gz)

The reference and two Pancake jobs processed the same ordered 50
original native 6000×4000 RGB16 TIFFs with the unchanged frozen Weighted
Average CPU settings. The Ryzen 9 7950X3D host used worker CPUs 0–14 on
distinct cores, 15 worker threads, and the observed RSS sampler affinity
`[15]`. Each app began with an empty case-owned cache. OS file caches
followed normal host behavior. The monotonic timer ran from job spawn
through blocking `wait4` after the complete RGB16 export. The app loop
was terminal at 10:54:08.480 SGT on 2026-11-19. Source/provenance
postflight and the common lock were terminal at 10:54:11.609.

| Observation | ChimpStackr | a49 control | 5f scratch alias |
| --- | ---: | ---: | ---: |
| Whole-job elapsed | 64.701462 s | 25.987403 s | 26.196895 s |
| Observations inside job interval | 19,054 | 8,230 | 8,267 |
| Maximum actual RSS gap | 18.299821 ms | 8.791848 ms | 11.444256 ms |
| Cadence-eligible tree RSS peak | 3,458,846,720 B | 1,833,377,792 B | 1,830,785,024 B |

The archive independently reproduces each peak and gap from actual
timestamps, including the edges at spawn and exit. All three observations
met cadence without inference. The scratch alias used 2,592,768 B
(2.47 MiB) less peak tree RSS than a49, a ratio of 0.998586. The alias
took 0.209492 s longer, a wall ratio of 1.008061. Against the valid
reference observation, the alias achieved a wall ratio of 0.404889 and
an RSS ratio of 0.529305. The alias peak exceeded half the reference
by 101,361,664 B (96.67 MiB) in this diagnostic. The scratch alias was
left out of the release. These three jobs provide zero frozen schedule
or release credit.

The [earlier 8 ms triplet](../t50-weighted-triplet-0a9ae85-a49ce69/README.md)
used reference, packaged 0a and standalone a49. Its reference gap of
22.476502 ms left reference-relative RSS pending. The genuine 3 ms
measurements here demonstrate valid cadence under this quiet window.
The earlier a49 elapsed 25.506298 s. The differing order, producer
roster and sessions preclude attributing the between-run elapsed
difference to sampling overhead.

All three jobs completed on explicit CPU without fallback and yielded
genuine 5998×3998 RGB16. ChimpStackr's emitted crop was one pixel on every
edge. It produced 50 keyed first-reference identity maps and reported
CPU alignment, warp and fusion. Each Pancake arm emitted the same 50
ordered keyed maps and 50 sequential identity matrices. Their encoded
SHA-256 and decoded pixel SHA-256 were identical to each other and their
historical reviewed counterparts. The reference also repeated its
historical output hashes. Independent decoding verified all three
current images and their equality to the earlier reviewed exports.
[Independent image receipt](independent-image-receipt.json)

Both Pancake exports differed from the
reference by 11.099 u16 MAE and 20.702 u16 RMS, with a maximum difference
of 227. The exact sharp-truth oracle covered all 50 depth regions for
each arm. Whole-image sharp-truth MAE was 1083.931 for the reference and
1080.736 for either Pancake arm.

The Stage6 owner granted read-only custody for this run. The recorded
preflight and postflight reverified the 52 original hashes and ownership
marker. The borrower returned the loan after the last postflight read. The three
private derived TIFFs were rehashed after independent read release and
removed along with the three owned case caches. [Cleanup receipt](cleanup.json)

The archive includes exact scoped argv, producer and tool provenance,
actual RSS traces, completion/crop/maps, decoded hashes and 150
truth-region records. Every archived member was re-read byte for byte.
Zero original or derived TIFFs and zero ambient environment records
are included. [Checksums](SHA256SUMS)
