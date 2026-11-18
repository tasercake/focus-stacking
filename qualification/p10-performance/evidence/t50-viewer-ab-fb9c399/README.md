# Shared frozen T50 stage for the fb9c399 poll-only viewer comparison

The materializer ran from the clean `fb9c399a96658331cb76b843a1e565b503e94fdd`
checkout. The frozen generator, scalar oracle and performance targets
retain their recorded hashes. The sealed Debian package and its verification
receipt also matched their recorded hashes.

All 50 ordered 6000×4000 RGB16 focus TIFFs and both native 16-bit truth TIFFs
matched the frozen encoded hashes and both independent decoded pixel hashes.
The full staged set totals 2,775,174,405 bytes. The materialization
receipt SHA-256 is
`dd20ddfddf96aecccbf08e27d3d240a848efdfce927577ead0cf9c96261f78a4`.
Both viewer runs receive the same 50 focus TIFFs. The two truth TIFFs
remain separate.

Generation took 227.853 seconds with peak RSS of
83,688 KiB. The owner held the shared performance
lock from 23:08:33 to 23:12:21 SGT on 2026-11-18 and limited generation to CPU14,
nice +12, idle I/O, and one numerical thread and decode worker. The generator
reserved 15 GiB. Available disk space was 129,055,272,960 bytes at entry and
123,025,408,000 bytes at exit. Available memory was 44,590,924 KiB at
entry and 44,729,844 KiB at exit. This run generated and verified
input data. Only an ordinary release build was active in the prelaunch
census. The Debian package was identified by archive and package receipt
hashes.

The exact packaged stock viewer and the experimental nonblocking poll-only
viewer are the named readers of this stage. The owner removes the corpus
after both roles release it and the coordinator clears cleanup.

[Stage receipt](shared-stage.json) · [Preflight](prepared-stage.json) ·
[Complete encoded and decoded records](materialization.json.gz) ·
[Exact command, resource logs, package verification and ownership](raw-stage.tar.gz)
