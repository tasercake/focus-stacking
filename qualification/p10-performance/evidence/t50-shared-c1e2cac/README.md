# Shared frozen T50 stage for the c1e2cac viewer comparison

The materializer ran from the clean `c1e2cac93ad41c02b328d87bdd5d01e1ce2b46eb`
checkout. The frozen generator, scalar oracle and performance targets
retain their recorded hashes. The sealed Debian package and its verification
receipt also matched their recorded hashes.

All 50 ordered 6000×4000 RGB16 focus TIFFs and both native 16-bit truth TIFFs
matched the frozen encoded hashes and both independent decoded pixel hashes.
The full staged set totals 2,775,174,405 bytes. The materialization
receipt SHA-256 is
`cd4942acd3127518340dd7f10a9c68d5768923beb45dfd36614ba7a11bf10eb4`.
The viewer receives the 50 focus TIFFs as its input stack. Both truth TIFFs
remain separate.

Generation took 225.105 seconds with peak RSS of
83,692 KiB. The owner held the shared performance
lock from 21:15:56 to 21:19:42 SGT on 2026-11-18 and limited generation to CPU14,
nice +12, idle I/O, and one numerical thread and decode worker. The generator
reserved 15 GiB. Available disk space was 118,914,519,040 bytes at entry and
111,740,186,624 bytes at exit. Available memory was 45,383,628 KiB at
entry and 44,187,780 KiB at exit. This run generated and verified
input data. The packaged viewer was identified by archive and sealed receipt
hashes. Application and device measurements are tracked by their consumers.

Both the exact packaged baseline and the isolated bounded-poll GUI candidate
are planned consumers of this same immutable stage. The owner removes the
corpus after both readers release and the coordinator clears cleanup.

[Stage receipt](shared-stage.json) · [Preflight](prepared-stage.json) ·
[Complete encoded and decoded records](materialization.json.gz) ·
[Exact command, resource logs, package verification and ownership](raw-stage.tar.gz)
