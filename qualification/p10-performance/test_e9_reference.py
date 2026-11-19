"""Independent contracts for the scoped E9 reference final combiner."""

import unittest
from types import SimpleNamespace

import numpy as np
from pancake_conformance.adapters.pancake.e9_reference import (
    _exposure_core,
    _gpu_result,
)


def plane(value):
    return np.full((2, 3, 3), value, dtype=np.float32)


class EqualBatchCpu(unittest.TestCase):
    def test_equal_mean_admits_then_combines_real_source_groups_once(self):
        partials = [plane(20), plane(80)]
        recorded_batches = []
        progress = []
        pauses = []

        def fuse(batch):
            recorded_batches.append([int(frame[0, 0, 0]) for frame in batch])
            return partials[len(recorded_batches) - 1]

        stack = SimpleNamespace(
            Algorithm=SimpleNamespace(
                is_cancelled=False, wait_if_paused=lambda: pauses.append(1)
            ),
            EXPOSURE_BATCH_SIZE=4,
            _emit_progress=lambda signals, callback, completed, total, elapsed: (
                progress.append((signals, callback, completed, total))
            ),
        )
        frames = [plane(index) for index in range(8)] + [plane(200)]
        signals, callback = object(), object()
        _exposure_core(
            stack, enumerate(frames), len(frames), signals, callback, fuse_batch=fuse
        )
        np.testing.assert_array_equal(stack.output_image, plane(100))
        self.assertEqual(recorded_batches, [[0, 1, 2, 3], [4, 5, 6, 7]])
        self.assertEqual(len(pauses), 9)
        self.assertEqual(
            progress, [(signals, callback, index, 9) for index in range(1, 10)]
        )
        np.testing.assert_array_equal(partials[0], plane(20))
        np.testing.assert_array_equal(partials[1], plane(80))

    def test_incomplete_multiframe_group_still_uses_original_fusion(self):
        stack = self.stack()
        groups = []

        def fuse(batch):
            groups.append(len(batch))
            return plane(20 if len(batch) == 4 else 100)

        _exposure_core(
            stack, enumerate([plane(10)] * 6), 6, None, None, fuse_batch=fuse
        )
        self.assertEqual(groups, [4, 2])
        np.testing.assert_array_equal(stack.output_image, plane(60))

    def test_singleton_empty_and_cancelled_control_paths(self):
        def unexpected(_batch):
            self.fail("there is no multisample group to fuse")

        stack = self.stack()
        _exposure_core(
            stack, iter([(0, plane(123))]), 1, None, None, fuse_batch=unexpected
        )
        np.testing.assert_array_equal(stack.output_image, plane(123))
        for cancelled, frames in ((False, []), (True, [plane(10)] * 4)):
            stack = self.stack()
            stack.Algorithm.is_cancelled = cancelled
            _exposure_core(
                stack, enumerate(frames), len(frames), None, None, fuse_batch=unexpected
            )
            self.assertEqual(stack.output_image, "untouched")

    @staticmethod
    def stack():
        return SimpleNamespace(
            Algorithm=SimpleNamespace(is_cancelled=False, wait_if_paused=lambda: None),
            EXPOSURE_BATCH_SIZE=4,
            _emit_progress=lambda *_: None,
            output_image="untouched",
        )


class DeviceArray:
    """A strict fake device array that records all arithmetic and transfers."""

    def __init__(self, data, events):
        self.data = data.copy()
        self.events = events

    def __iadd__(self, other):
        self.events.append(("add", other.data.dtype.name))
        self.data += other.data
        return self

    def __itruediv__(self, value):
        self.events.append(("divide", type(value).__name__, float(value)))
        self.data /= value
        return self


class EqualBatchOpenClContract(unittest.TestCase):
    def test_keeps_final_combine_on_reference_device_and_flushes_singleton(self):
        events = []

        def upload(array):
            events.append(("upload", int(array[0, 0, 0])))
            return DeviceArray(array, events)

        def flush():
            events.append(("flush",))
            fuser.partials.append(fuser.batch.pop())

        fuser = SimpleNamespace(
            g=SimpleNamespace(upload=upload),
            batch=[plane(200)],
            partials=[plane(20), plane(80)],
            _flush=flush,
        )
        result = _gpu_result(fuser)
        self.assertIsInstance(result, DeviceArray)
        np.testing.assert_array_equal(result.data, plane(100))
        self.assertEqual(
            events,
            [
                ("flush",),
                ("upload", 20),
                ("upload", 80),
                ("add", "float32"),
                ("upload", 200),
                ("add", "float32"),
                ("divide", "float32", 3.0),
            ],
        )

    def test_empty_and_single_partial_keep_original_return_semantics(self):
        fuser = SimpleNamespace(batch=[], partials=[], last=object())
        self.assertIsNone(_gpu_result(fuser))
        fuser.partials.append(plane(123))
        self.assertIs(_gpu_result(fuser), fuser.last)
