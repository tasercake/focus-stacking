# Inclusive RAW encoded byte boundary

The new native CPU image I/O test starts with the authenticated
36,352-byte Bayer DNG, then extends the logical file length with
`File::set_len` to exactly 268,435,456 bytes. The uncompressed strip
occupies offsets 512 through 36,351. The zero-filled trailer leaves
all declared TIFF metadata and pixels intact. Stock develops actual
160×112 U16 RGB with all 53,760 working f32 samples bitwise equal to
the unpadded decode. The existing 268,435,457-byte rejection remains
in the native target.

The saved `0a9ae85` shard 9/16 mutant changes the post-read greater-than
check at `raw.rs:70:14` to equality. Its separately built native test
binary exits 101 with `compressed RAW source exceeds the byte limit`.
The restored stock target passes all 29 tests. Exact input, source,
executable and patch hashes and logs are retained.

| Native test executable invocation | Exit | Wall time | Peak RSS |
| --- | ---: | ---: | ---: |
| Saved mutant, exact cap | 101 | 0.39 s | 315,792 KiB |
| Stock unpadded Bayer | 0 | 0.21 s | 51,020 KiB |
| Stock exact-cap Bayer | 0 | 0.43 s | 316,184 KiB |
| Stock cap plus one | 0 | <0.01 s | 23,296 KiB |
| Complete stock CPU image I/O target | 0 | 1.12 s | 318,632 KiB |

GNU time measured test executable invocations on logical CPUs 8 and 9,
outside compilation. A single exact-cap test used 0.22 s and about
259 MiB more than the unpadded control. The local ext4 fixture uses a
sparse trailer, and the genuine decoder still reads the full logical
length. Sanitizer overhead was unmeasured. Both offline locked Rust
1.100.0 builds used two jobs, empty wrappers and disabled incremental
compilation. To replay, unpack the archive into an owned directory
called `$scope`, create its `tmp` subdirectory, and run
`bash "$scope/replay.sh" "$scope"` from a clean `e97f137` checkout.
Every temporary fixture and the private target were removed after
verification. [Run receipt](receipt.json)
[Build, execution, replay and cleanup evidence](native-capture.tar.gz)
