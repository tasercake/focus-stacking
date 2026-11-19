# E9 FFT twiddle experiment

Reusing each stage's sine and cosine values across independent butterflies
preserved the real E9 export and yielded no warm CUDA latency gain. The offset-
first branch remains experimental. [Phase and compiler attribution](../e9-cuda-phase-attribution/README.md)
records the first-use cost that motivated the test.

| Native CUDA build | Warm median |
| --- | ---: |
| Historical application control `12f2151` | 452.966 ms |
| FFT candidate `9a8c1a9` | 457.087 ms |

The median ratio was 1.00910 and the median candidate-minus-control difference
within pairs was +2.806 ms. Each binary completed two warmups and five measured
fresh-process launches in alternating order. The blocking Linux `wait4` timer
covered process creation through full process exit and used a separate deadline
for the run. The RTX 3090 at PCI `0000:01:00.0` had driver `580.178.04` and
recorded 69°C and P2 before and after. Both
process censuses were empty. All 14 jobs reported actual physical CUDA with
zero fallbacks and nine exact identity transforms. Each genuine 337 × 510
RGB16 TIFF matched the prior E9 file and decoded-pixel hashes.

The earlier run with the same 14 successful exports used Python's timed wait.
Its polling capped at 50 ms, so those recorded timings were excluded from the
comparison. The archive retains both raw runs. The nine ordered Balloons
photographs were hashed before and after every group. The download and cleanup
also verified the original source archive. Cleanup removed 71,500,200 bytes
across the source archive, notice, and photographs.

The test-only `c2274d9` expanded the actual checked FFT kernel and observed a
dynamic remainder instruction in the butterfly. Candidate `9a8c1a9` passed the
same test and the native CPU registration suite. The production patch changes
only the order of independent butterflies within each stage. The first-build
worktree also held a formatting change to the test-only expansion harness,
recorded separately at `8ca6d0c`. The candidate release CLI SHA-256 was
`35da6ae64db01c51f43497b68651c07a4e253eda87eb725d2550636cf632e0d7`.
Both binaries used the existing locked native CUDA profile and the same frozen
E9 job arguments. This experiment compares Pancake revisions. The frozen
ChimpStackr comparison retains its existing P10 results.

The [summary](summary.json) retains the binary identities, exact warm samples,
and archive inventory. The [raw archive](raw-records.tar.gz) retains the source
patch, CPU red and green logs, locked build, launch commands, CUDA completion
events, both timing methods, and cleanup receipts.
