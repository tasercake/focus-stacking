"""Run the real E9 reference CLI with equal final exposure-batch weights."""

import sys
import time
from pathlib import Path

import numpy as np


def _exposure_core(self, image_iter, total, signals, progress_callback, *, fuse_batch):
    """Keep the pinned CPU admission, batch fusion and lifecycle behavior."""
    batch = []
    intermediates = []
    for index, image in image_iter:
        self.Algorithm.wait_if_paused()
        if self.Algorithm.is_cancelled:
            return
        started = time.time()
        batch.append(image)
        if len(batch) >= self.EXPOSURE_BATCH_SIZE:
            intermediates.append(fuse_batch(batch))
            batch = []
        self._emit_progress(
            signals, progress_callback, index + 1, total, time.time() - started
        )

    if self.Algorithm.is_cancelled:
        return
    if batch:
        if len(batch) == 1:
            intermediates.append(batch[0].astype(np.float32))
        else:
            intermediates.append(fuse_batch(batch))
    if not intermediates:
        return
    if len(intermediates) == 1:
        self.output_image = intermediates[0]
        return

    combined = intermediates[0].copy()
    for image in intermediates[1:]:
        np.add(combined, image, out=combined)
    np.divide(combined, np.float32(len(intermediates)), out=combined)
    self.output_image = combined


def _gpu_result(self):
    """Combine pinned OpenCL partials on the fuser's existing device queue."""
    if self.batch:
        self._flush()
    if not self.partials:
        return None
    if len(self.partials) == 1:
        return self.last

    combined = self.g.upload(self.partials[0])
    for partial in self.partials[1:]:
        combined += self.g.upload(partial)
    combined /= np.float32(len(self.partials))
    return combined


def main():
    """Delegate decode, alignment, backend selection and TIFF export to the pin."""
    sys.path.insert(0, str(Path.cwd()))
    from src.cli import main as reference_main
    from src.algorithms.API import LaplacianPyramid
    from src.algorithms.stacking_algorithms.cpu import mertens_fuse_batch
    from src.algorithms.stacking_algorithms.ocl import ExposureGPU

    def exposure_core(stack, image_iter, total, signals, progress_callback):
        return _exposure_core(
            stack,
            image_iter,
            total,
            signals,
            progress_callback,
            fuse_batch=mertens_fuse_batch,
        )

    original_cpu = LaplacianPyramid._exposure_core
    original_gpu = ExposureGPU.result
    LaplacianPyramid._exposure_core = exposure_core
    ExposureGPU.result = _gpu_result
    try:
        return reference_main()
    finally:
        LaplacianPyramid._exposure_core = original_cpu
        ExposureGPU.result = original_gpu


if __name__ == "__main__":
    raise SystemExit(main())
