# Exact T50 Weighted Average CPU diagnostic plan

Run one completed job per arm in this order after the canonical mutation
campaign exits and the coordinator grants an exclusive CPU and I/O window.
The primary comparison isolates the a49 resident-frame change against the
0a notice-bearing stock CLI. The pinned reference supplies an independent
elapsed and image comparison. The three first-launch samples are diagnostic
and confer zero frozen schedule or release credit. This preparation launched
no application or device, compiled nothing, and read or copied no corpus
media.

| Arm | Exact producer | Artifact to verify before and after |
| --- | --- | --- |
| ChimpStackr reference | `ab7a92708269c01c6094729f6cdfaf1415677364`, stock `-m src.cli` | Runtime lock `fda57ac5eea063aebcc278eb57a90228e6da32fe2d8f67d7025ac367f4b51036`; descriptor `e3e951b674bc0103f267575a99533cc33ead40e2af56671766f4fc71f3f12b76` |
| Stock Pancake | `0a9ae85b88519a795e3b6ba90860c3b3e664bcaa`, tree `fde57a0b461e3ea031ea969e1e841927bead17f9` | `linux-0a9ae85/pancake_0.1.0_amd64.deb` SHA-256 `c3516a65762b58889858857c8163744e86e82c9427a953730c0450580c5cc4c4`; extracted CLI SHA-256 `67f8bdab62b7a1014df34034fd1f3a8b7c04b65fb89a1333a5daebd324f048bd`, ELF Build ID `609b7b50fa04efd459e3f045077ab34c0d34ec46` |
| Resident Pancake | `a49ce692371558ff40f72b0af77f5249d00dcedb`, tree `965aa0c7dc33731d3aef94231afa3e59fc7bc330` | `artifacts/pancake-linux-native/a49ce69/pancake-cli` SHA-256 `43a05f9cfb6ac3f89c7153e6043cc9e79d33bfccd03054d20da54bd7d147c65e`, ELF Build ID `561328fa71c9ff497ce2040ebf619f24e1ec1f7e` |

Use each Pancake producer's own clean exact source checkout and separately
verify the common Cargo.lock SHA-256
`f523404bf033b0532dc46ce71aa515dc398f56c32e6aee1c3529cf90a27018dc`
and unchanged Pancake descriptor SHA-256
`84e2bd96f121395051cc8d626a06ebece7367171d59018158439d9ca2aaa10ac`.
Bind stock to the rootless extraction of the exact package and its
verification receipt SHA-256
`c0120fbd255f746f7a0987c36e84c37543dd5cc1a98212281ffb282d835bb21e`.
Bind a49 to the default release receipt at `80a5737`, including its locked
offline Rust 1.100.0 CLI build, with no extra Cargo features. Deployment of
that artifact is the sole producer change in this experiment. Record the
separate benchmark helper checkout and hashes. Fail an arm's identity check
if its own producer or executable fails authentication. The stock package's
376-case ledger remains attributable to 0a only.
[Exact package verification](../../../../pancake/docs/p9-linux-package-evidence/0a9ae85/package-verification.json) ·
[Resident producer proof at 80a5737](#resident-build-receipt)

## Shared stage and launch

1. Confirm the stage owner has released the corpus for read-only use and hold
   the common performance lock through the triplet. Reuse the live paths from
   the [stage6 receipt](../t50-stage6-e81079d/shared-stage.json). The
   materialization SHA-256 is
   `1d9be3f1cd20a01083b11c10c4d17ab75a4f3b6bb7e2ebef682824e345ba649d`.
   Check the ownership marker and all 52 frozen encoded and independent
   decoded digest records. Verify actual file sizes and stream encoded hashes
   before the first job and after the last truth review. The 50 distinct
   `focus_000.tif` through `focus_049.tif` are the only CLI inputs. Both
   generated truth TIFFs remain outside the input arguments. Shared inputs
   stay in place and the owner retains cleanup authority.
2. Reuse the authentication and target-argv construction in the
   [Weighted CPU pair operator](../t50-profile-priority-e810/weighted-cpu-pair.py.txt)
   with a small triplet dispatcher. The existing operator authenticates a
   single candidate and hard-codes e810 package hashes. Load the reference
   and two producer specs independently, verify each corresponding
   `_snapshot` and executable, and call `_run_sample` once with role
   `reference` and twice with role `candidate`, each into a separate
   arm root. Role selection controls the command, backend assertion and
   diagnostics. Preserve the existing `TargetSpec` arguments and use the
   runner's stock reference command for `T50`. Take the exact stage6
   pinned reference interpreter and 46-package inventory from
   [its setup receipt](../t50-stage6-e81079d/diagnostic-setup.json) if still
   available. Verify the clean source, descriptor, lock, interpreter and
   inventory outside the timed interval. The E9 and R50 adapters apply to
   their own profiles.
3. Run the replay under `taskset -c 0-14` using the unchanged
   `T50.weighted_average.cpu` profile from targets hash
   `58bb68533311c48696a3a844d80eef2f37a3c1f39649305948c838b7002663dc`.
   Use explicit CPU, align using first-reference Similarity, kernel 6,
   pyramid 8, scale factor 6, slab size and overlap 0, auto parameters
   off, auto crop on, TIFF RGB16 and quality-report off. Retain the actual
   ordered argv and settings. On this 16-core host CPUs 0–14 are on
   distinct cores and CPU15 is a distinct collector core. Use 15
   `NUMBA`, `OMP` and `RAYON` threads and one OpenBLAS thread for all
   arms. Place the RSS sampler on CPU15 and check the observed mask is
   exactly `[15]`. Parent/children retain the 0–14 mask. Log topology,
   ambient CPU and I/O census, elapsed quiet window, thermal/power state
   and effective memory constraints. Allow up to 300 seconds per arm
   with no overlap or retries. Prior stock and reference observations
   suggest about 2.5–3 minutes for three jobs, plus identity and image
   checks outside the timers. The deadlines allow up to 15 minutes of
   job execution. [Prior e810 diagnostic](../t50-weighted-cpu-e81079d/README.md)
4. Use a fresh process and separate initially empty case-owned application,
   compiler and JIT cache for each arm. Leave OS file cache behavior
   normal and disclose the fixed run order. Use the existing monotonic
   pre-spawn-to-`wait4` timer, including closed export and successful
   process drain. Retain raw sampler traces with the tested 8 ms nominal
   interval and the maximum actual RSS gaps across spawn, observations
   and exit. Mark an individual peak ineligible on a gap over 20 ms or
   incomplete process attribution. Keep observed lower bounds and all
   failures. The kernel parent-only RSS is diagnostic telemetry; the
   comparison uses the process-tree counter and only reports a valid RSS
   ratio when both observations qualify.

## Validation and retention

Use existing typed completion and TIFF decoders for all arms. Require a
single completed CPU job, exit 0, a drained session, no fallback or observer
error, and independently decoded genuine 5998×3998 RGB16 export. The
reference must account for the ordered 50 inputs, all three stages on CPU,
all 50 first-reference maps and its emitted `[1, 1, 1, 1]` crop. In the
historical unmodified Similarity job the reference sequential field is
`null`, and the completion shape precedes crop. Both Pancake jobs must
emit exactly 50 first-reference identity maps keyed in original path order
and a separate ordered list of exactly 50 identity matrices. Reuse the
[corrected map consumer](../t50-weighted-phase-preflight/weighted-phase-run.py.txt)
and its [schema tests](../t50-weighted-phase-preflight/test-control-schema.py.txt).
For this triplet, apply its map checks while accepting the measured output
digests on their own merits. The older output digest is available for an
additional comparison. Preserve a structural failure or changed geometry
before assigning any quality-adjusted speed difference.

Require both encoded and decoded equality between the two Pancake jobs.
Record each arm's channel count, extent, encoded and pixel hashes. Compare
each Pancake export with the measured stock reference and run the unchanged
[generated truth oracle](../registration-recheck/scale-recheck.py.txt) on
all three outputs after confirming the crop. Retain full-image MAE/RMS,
maximum absolute difference, changed-sample fraction and the 50 original
depth-strip detail/MAE records. The exact 0a-to-a49 output comparison is
separate from the numerical differences against ChimpStackr. The CLI's
export observes final weighted RGB, with no intermediate weight-map
witness in these settings.

Publish the observed a49/0a, 0a/reference and a49/reference elapsed ratios
with all three individual durations, memory validity, output proof and the
single-triplet scope. Keep the exit, tree-drain, typed events, sanitized
launch flags, hashes and raw RSS timestamps. Record tool and environment
identities with the explicit allowlisted controls only. Do not archive
ambient process environment, source TIFFs, exported TIFF bytes or caches.
Release the quiet lease when the last measured app and samplers exit and
confirm no overlapping workload. Retain raw observations, rehash outputs
and authenticate unchanged source after the offline pixel review, then
remove only the triplet-owned exports and caches. The canonical mutation
campaign and stage custodian govern shared input disposition.

Static verification matched both producer trees, locks, descriptor and
receipt pins, the stage receipt, and the historical native event shapes.
The existing five ordered-map tests passed against the archived stock event
and malformed variants without opening a TIFF. The current file hashes and
quiet lease are execution prerequisites.

### Resident build receipt

`git show 80a5737:qualification/p10-performance/evidence/t50-weighted-resident/README.md`
describes the exact a49 default CPU/wgpu CLI and separate CPU fixture proof.
`raw-host-records.tar.gz` at the same revision contains the
`default-release` build command, logs and ELF evidence.

## Prepared dispatch

Use the [read-only preflight and dispatcher](weighted-cpu-triplet.py.txt)
through the retained stage6 interpreter and this tool checkout's Python source
paths. Default invocation builds the three argv lists and verifies the source,
descriptors, lock and reference environment without opening any corpus file.
The independent sparse source anchors are each clean and contain only the
complete application source and pinned descriptor. Their roots are
`/tmp/pancake-worktrees.t3paqgWM/t50-weighted-triplet-stock-source` and
`/tmp/pancake-worktrees.t3paqgWM/t50-weighted-triplet-resident-source`.

Once the lease is explicitly granted, write a new receipt in the owned
diagnostic output parent. It must record true `exclusive_host_granted`,
`stage6_read_granted` and `mutation_terminal` fields, the exact `profile`,
`materialization_sha256` and `order` documented above, and the observed
grant/host census. Extract the exact package rootlessly into the private
scratch area with `dpkg-deb -x`. The dispatcher verifies the extracted
`usr/bin/pancake-cli`, both actual ELF build IDs and SHA-256 hashes on
each side of execution. The shared input paths are fixed by the stage
receipt. Keep the producer checkouts and both packaged ELFs untouched.

```sh
PYTHONPATH="$tool_worktree/qualification/p10-performance:$tool_worktree/pancake-conformance/src" \
  PYTHONDONTWRITEBYTECODE=1 OPENBLAS_NUM_THREADS=1 \
  taskset -c 0-14 env -u DISPLAY -u WAYLAND_DISPLAY \
  "$reference_python" -B "$triplet_script" --execute-diagnostic \
  --quiet-receipt "$quiet_receipt" --package "$notice_deb" \
  --stock-source "$stock_source" --stock-cli "$extracted/usr/bin/pancake-cli" \
  --resident-source "$resident_source" --resident-cli "$resident_cli" \
  --output "$new_triplet_artifact_root"
```

The output root is new and private. `children-terminal.json` identifies
the declared job loop's terminal boundary. Wait for the command and the
common lock to exit before any next quiet workload. Keep failed sample
records and check output digests before authenticated cleanup. The
[fixture tests](test-weighted-cpu-triplet.py.txt) use archived event JSON
and synthetic failures to check roles, input and map order, crop, lease
requirements and the unchanged RSS validity gate. They read no TIFFs.
