# D150 Hybrid detail with the same registered inputs

The experiment isolates a real fusion gap on registered optical source pixels. Sealed Pancake retained about 79–80% of the pinned reference's native local detail and signed source projection. A prototype corrected an independently reproducible cross-scale selection error but degraded signed phase in both held-out real regions. Its source stays on the experimental branch.

## Controlled frequency response

At `2143eda2b308497caee96334357dd23d324e1e8e`, Hybrid selects on a modified-Laplacian focus map measured at full resolution and propagated to the entire pyramid. A sharp high frequency can therefore win a lower band where another frame contains stronger structure. The independent red at `5f7d5ae` fused two 257×9 RGB16 inputs using the real CPU job with identity registration. Both competed for period-two and period-sixteen structures on different optical planes. The period-two component is removed by the first binomial reduction. The contribution of the period-sixteen lower bands follows from the Gaussian reduction and bilinear expansion gain `cos⁶(π/16)`, which sets its minimum amplitude at 0.142418 for a known sharp input amplitude of 0.16.

| Exact locked CLI | Period-two signed amplitude | Period-sixteen signed amplitude |
| --- | ---: | ---: |
| Sealed `12f2151` | 0.137896 | 0.026919 |
| Prior clear-winner `b7a42b6` | 0.139999 | 0.019998 |
| Band-local prototype `3afdc19` | 0.139999 | 0.144618 |

The prototype retains the prior runner-up confidence and measures local signed coefficient variance on the downsampled detail levels. It uses the existing full-grid focus score at the finest level and the sealed soft combination for the base. The five CPU tests passed including the two frequencies, overlap reconstruction, repeated defocus, tied faint texture and memory-boundary handling. The new select path is defined in shared CubeCL. The prototype was built with two offline locked release jobs on Ryzen 9 7950X3D / Linux x86-64 / Rust 1.100.0. CLI SHA256 `bc44db38c3cb9dead468c2bf6651db0b6db175c7ec325eabb188e00c7b33e69c`. [Focused command output, lock and observations](raw-diagnostics.tar.gz)

## Real optical controls

The independent input-only plan picked four disjoint 96×96 holdouts from an unchanging twelve-patch grid. It ranks adjacent source pairs by the smaller native luma Laplacian response times positive normalized signed phase correlation. Source tiles were registered to common first-frame coordinates. It read no rendered image. The chosen adjacent pairs have signed correlation 0.454–0.642. The original slab `36..76` contains the source witnesses for two held-out regions and carries detail on those planes. Source D150 material is the [Amber mite focal-stack release](https://doi.org/10.6084/m9.figshare.14707077.v1). [Input-only preselection](heldout-plan.json)

All 150 borrowed native JPEGs matched the frozen manifest `6d417c9c00866755bdbc8e2fafc1421de8414e1ea9e75d2cfd7e96e2161a89ac` before and after the work. Exactly 40 full-size RGB16 TIFFs were prepared with one shared Lanczos4 warp and replicated boundaries from the independent registration task's maps, SHA256 `b5b862bf0ffa3b9a630373082f606ad8a8912d8d71e642d1b667a7928f58133a`. The raw archive contains the exact maps applied and the digests of their derived TIFFs. The stock executable was re-extracted and matched the sealed CLI SHA256 `32caffd65ed785b1883c39ec69cfd726f2a6f836e42c653a6385dacf80267055`. The live reference sourced checked-out `ab7a92708269c01c6094729f6cdfaf1415677364` with its existing pinned Python environment and observer. All four products ran `--cpu --method hybrid --kernel-size 6 --pyramid-levels 8 --scale-factor 6 --slab-size 40 --slab-overlap 4 --bit-depth 16` on the identical files without alignment or crop. All completed actual CPU work and produced 2304×1728 RGB16. This is a focused diagnostic. The frozen resource and speed gates require the complete prescribed protocol.

| Model | P90, region (670,675) | Signed source projection | P90, region (1505,1045) | Signed source projection |
| --- | ---: | ---: | ---: | ---: |
| Sealed Pancake | 0.04660 | 0.30889 | 0.05235 | 0.23739 |
| Previous clear-winner | 0.04733 | 0.31446 | 0.05334 | 0.24498 |
| Band-local prototype | 0.04855 | 0.30030 | 0.05276 | 0.18938 |
| Pinned reference | 0.05877 | 0.39216 | 0.06531 | 0.29854 |

The signed witness for each region is the optical source patch with the strongest pre-render measured P90 in the shared registered input set. Compared with sealed Pancake, the prototype raised unsigned detail 4.19% and 0.80% but reduced projection on the actual source phase by 2.8% and 20.2%. Actual reference and candidate alignment are absent from this comparison, so their gap persists under this identical fixed registration condition. One interrupted clear-winner attempt timed out after being suspended for a separate quiet measurement. The replay validated and reused only the completed stock results, and the interrupted comparison supplies no evidence. [Native and signed measurements](focused40-results.json)

The Hann-windowed octave diagnostic on the same stored images shows where unrestricted variance selection loses real phase. At 0.25–0.5 cycles/pixel, signed projection drops from 0.218 and 0.114 to 0.155 and 0.062. At 0.0625–0.125 cycles/pixel in region (1505,1045), sealed gives +0.184, band-local gives −0.004 and the pinned reference gives −0.036. Thus the pinned reference's stronger aggregate contrast cannot substitute for corroborating optical phase across every band. [Per-octave projections and energy](spectral-diagnostics.json)

## Coherence-gated selection

A follow-up correction can compare proposed winner coefficients with the corresponding local, signed, weighted consensus. For nondegenerate windows of coefficient vectors (s) and (c), multiply the existing clear-focus confidence by (max(0, (s\cdot c)/(\lVert s\rVert\lVert c\rVert))). The scalar distinguishes strong same-phase structure from an incoherent high-variance candidate without rewarding an absolute increase in contrast or using reference pixel values. Degenerate or nonpositive correlation retains the existing soft reconstruction. Compute the neighborhood from immutable selected and weighted inputs and yield a separate destination so output lanes never race with neighboring reads. Preserve source and budget bounds. The next red test needs a known same-phase multiscale scene and a stronger out-of-phase competitor, then a fresh optical holdout and CPU/physical GPU parity on identical sources. This design is unevaluated.

Physical GPU parity and full D150 quality for this prototype were unnecessary after the real controlled phase failure. Original JPEGs were borrowed read-only and released to their acquiring task. The derived full-canvas images and local outputs were authenticated before removal. An exact local CLI is retained for reproduction. [Cleanup and retained artifacts](cleanup.json)
