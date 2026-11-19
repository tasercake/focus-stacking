# Initial limited T50 launch stopped by its CPU environment

The first separately authorized package/reference execution started at
11:42 SGT on 2026-11-19 after an idle activity census. ChimpStackr warmed
successfully in 65.345993 s. It reproduced the prior expected 5998×3998
RGB16 bytes, pixels and alignment evidence. Its sampled process-tree
peak was 3,463,815,168 B with a maximum actual gap of 18.027744 ms.
This single warmup supplies no limited or frozen P10 verdict.
[Original typed pack](raw-invalid-launch.tar.gz) · [Summary](summary.json)

The exact Debian CLI exited 1 at startup in 6.700 ms. Its argv carried the
correct `--cpu` flag, but the scoped launcher simultaneously injected
`PANCAKE_RUNTIME=cpu`. The CLI rejected that environment value, which only
selects GPU runtimes. The stock runner translates the CPU group to no
environment override. The bounded wrapper failed before a valid candidate
stack, and the remaining eight jobs stayed unrun. The source, package,
and all 52 Stage6 hashes matched at terminal 11:44:12.421 SGT.

The correction uses the existing runtime mapping and preserves the CLI
argv, exact producer/inputs, sample interval, thresholds and pair
schedule. A no-spawn regression using both actual descriptors fails
on the original candidate environment and passes on the corrected one.
Any new attempt starts with ten fresh jobs, caches and raw receipts
under a new grant. [Correction and replay](../t50-weighted-11c-limited-prereg/README.md)
