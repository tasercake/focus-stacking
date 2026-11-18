"""Observe the isolated display's XWD framebuffer and deliver native XTest input."""

import ctypes
import mmap
import os
import shlex
import shutil
import struct
import time
from contextlib import contextmanager
from dataclasses import dataclass

import numpy as np
from pancake_conformance.linux_ui import isolated_desktop


@contextmanager
def observed_desktop(directory, environment):
    """Reuse the private X11/AT-SPI lane with a task-owned shared screen file."""
    directory = directory.resolve()
    wrapper = directory / "bin"
    pixels = directory / "screen"
    wrapper.mkdir(parents=True, exist_ok=False)
    pixels.mkdir(exist_ok=False)
    real_server = shutil.which("Xvfb")
    if real_server is None:
        raise ValueError("Xvfb is required for the isolated screen observation")
    entry = wrapper / "Xvfb"
    call = " ".join(map(shlex.quote, (real_server, "-fbdir", str(pixels))))
    entry.write_text(f'#!/bin/sh\nexec {call} "$@" -noreset\n')
    entry.chmod(0o700)
    old_path = os.environ["PATH"]
    os.environ["PATH"] = str(wrapper) + os.pathsep + old_path
    try:
        # isolated_desktop allocates the display and creates the service bus.
        # This entry point never attaches to the caller's DISPLAY.
        with isolated_desktop(directory, {**environment, "PATH": old_path}) as private:
            yield private, pixels / "Xvfb_screen0"
    finally:
        os.environ["PATH"] = old_path


class XwdScreen:
    """Read RGB pixels from Xvfb's actual presented screen, without a screenshot command."""

    def __init__(self, path):
        with path.open("rb") as handle:
            self.mapping = mmap.mmap(handle.fileno(), 0, access=mmap.ACCESS_READ)
        try:
            head = struct.unpack_from(">25I", self.mapping)
            header, version, kind, depth, self.width, self.height, x_offset, order = (
                head[:8]
            )
            bpp, stride, visual, red, green, blue, _, _, colors = head[11:20]
            if (version, kind, depth, x_offset, bpp, visual, red, green, blue) != (
                7,
                2,
                24,
                0,
                32,
                4,
                0xFF0000,
                0xFF00,
                0xFF,
            ) or order not in (0, 1):
                raise ValueError(
                    "unsupported Xvfb XWD format; require 24-bit truecolor in 32-bit pixels"
                )
            offset = header + 12 * colors
            if (
                header < 100
                or not self.width
                or not self.height
                or stride < 4 * self.width
            ):
                raise ValueError("invalid native screen geometry")
            if offset + stride * self.height > len(self.mapping):
                raise ValueError("truncated Xvfb framebuffer")
            dtype = "<u4" if order == 0 else ">u4"
            self.data = np.ndarray(
                (self.height, self.width),
                dtype=dtype,
                buffer=self.mapping,
                offset=offset,
                strides=(stride, 4),
            )
        except (ValueError, struct.error):
            self.mapping.close()
            raise

    def __enter__(self):
        return self

    def __exit__(self, *_):
        self.data = None
        self.mapping.close()

    def rgb(self, x, y, width, height):
        """Copy one attested screen rectangle using explicit row stride and RGB channels."""
        if not (
            0 <= x < x + width <= self.width and 0 <= y < y + height <= self.height
        ):
            raise ValueError("pixel rectangle lies outside the screen")
        packed = self.data[y : y + height, x : x + width].copy()
        return np.stack(
            ((packed >> 16) & 255, (packed >> 8) & 255, packed & 255), axis=-1
        ).astype(np.uint8)


@dataclass(frozen=True)
class Patch:
    """Expected independently reviewed RGB pixels at one screen rectangle."""

    x: int
    y: int
    rgb: np.ndarray
    tolerance: int

    def read(self, screen):
        height, width, _ = self.rgb.shape
        observed = screen.rgb(self.x, self.y, width, height)
        maximum = int(np.abs(observed.astype(np.int16) - self.rgb).max())
        return observed, maximum


def read_patches(screen, patches):
    """Return observed bytes and errors only when all witness patches agree."""
    if not patches:
        raise ValueError("a timed event requires visible witness pixels")
    observations = tuple(patch.read(screen) for patch in patches)
    if any(
        error > patch.tolerance
        for (_, error), patch in zip(observations, patches, strict=True)
    ):
        return None
    return observations


def wait_pixels(screen, patches, timeout):
    """Wait for independent preparation witnesses to become visible."""
    deadline = time.monotonic() + timeout
    while time.monotonic() < deadline:
        if observations := read_patches(screen, patches):
            return observations
        time.sleep(0.001)
    raise TimeoutError("preparation pixels never matched the independent witnesses")


def observe_transition(screen, dispatch, before, after, *, timeout):
    """Time dispatch to the first independently observed correct screen pixels.

    Mapping and comparison happen continuously after native dispatch. Their
    observation delay makes the reported interval an upper bound on display.
    """
    if not read_patches(screen, before):
        raise ValueError("precondition pixels were not visible at dispatch")
    if read_patches(screen, after):
        raise ValueError(
            "requested post-state was already displayed before native input"
        )
    dispatched = time.monotonic_ns()
    dispatch()
    deadline = dispatched + int(timeout * 1_000_000_000)
    previous = dispatched
    maximum_gap = 0
    while time.monotonic_ns() < deadline:
        observations = read_patches(screen, after)
        now = time.monotonic_ns()
        maximum_gap = max(maximum_gap, now - previous)
        if observations:
            return {
                "dispatched_ns": dispatched,
                "presented_ns": now,
                "maximum_observation_gap_ns": maximum_gap,
                "witnesses": observations,
            }
        previous = now
        time.sleep(0.001)
    raise TimeoutError("native event did not present the expected pixels")


def _bind(library, name, arguments, result):
    function = getattr(library, name)
    function.argtypes = arguments
    function.restype = result
    return function


class XTestPointer:
    """Emit physical pointer events on the allocated private display only."""

    def __init__(self, environment, screen):
        self.screen = screen
        x11 = ctypes.CDLL("libX11.so.6")
        xtest = ctypes.CDLL("libXtst.so.6")
        pointer, integer = ctypes.c_void_p, ctypes.c_int
        self._flush = _bind(x11, "XFlush", [pointer], integer)
        self._sync = _bind(x11, "XSync", [pointer, integer], integer)
        self._close = _bind(x11, "XCloseDisplay", [pointer], integer)
        self._move = _bind(
            xtest,
            "XTestFakeMotionEvent",
            [pointer, integer, integer, integer, ctypes.c_ulong],
            integer,
        )
        self._button = _bind(
            xtest,
            "XTestFakeButtonEvent",
            [pointer, ctypes.c_uint, integer, ctypes.c_ulong],
            integer,
        )
        probe = _bind(
            xtest,
            "XTestQueryExtension",
            [pointer, *([ctypes.POINTER(integer)] * 4)],
            integer,
        )
        open_display = _bind(x11, "XOpenDisplay", [ctypes.c_char_p], pointer)
        self.display = open_display(environment["DISPLAY"].encode())
        if not self.display:
            raise ValueError("cannot connect to the private X11 display")
        extension = [integer() for _ in range(4)]
        if not probe(self.display, *(ctypes.byref(value) for value in extension)):
            self._close(self.display)
            raise ValueError("the private display does not support XTest")

    def __enter__(self):
        return self

    def __exit__(self, *_):
        self._close(self.display)

    def move(self, x, y):
        if not (0 <= x < self.screen.width and 0 <= y < self.screen.height):
            raise ValueError("pointer target lies outside the private display")
        if not self._move(self.display, 0, x, y, 0):
            raise ValueError("native XTest motion injection failed")

    def button(self, button, pressed):
        if not self._button(self.display, button, pressed, 0):
            raise ValueError("native XTest button injection failed")

    def flush(self):
        self._flush(self.display)

    def settle(self):
        self._sync(self.display, 0)
