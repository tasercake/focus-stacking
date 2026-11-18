"""Verify native dispatch and presented-pixel acquisition on private Xvfb."""

import argparse
import json
import os
import selectors
import subprocess
from pathlib import Path

import numpy as np
from framebuffer import (
    Patch,
    XTestPointer,
    XwdScreen,
    observe_transition,
    observed_desktop,
    wait_pixels,
)
from pancake_conformance.macos_ui import MacOSUISession


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("directory", type=Path)
    args = parser.parse_args()
    directory = args.directory.resolve()
    directory.mkdir(parents=True, exist_ok=False)
    source = Path(__file__).with_name("x11_witness_fixture.c")
    binary = directory / "fixture"
    command = [
        "cc",
        "-std=c17",
        "-Wall",
        "-Wextra",
        "-Werror",
        str(source),
        "-lX11",
        "-o",
        str(binary),
    ]
    subprocess.run(command, check=True)
    with (
        observed_desktop(directory, os.environ) as (env, screen_path),
        XwdScreen(screen_path) as screen,
        (directory / "fixture.stderr").open("w") as errors,
        XTestPointer(env, screen) as pointer,
        subprocess.Popen(
            [str(binary)],
            env=env,
            text=True,
            stdout=subprocess.PIPE,
            stderr=errors,
            start_new_session=True,
        ) as server,
    ):
        try:
            with selectors.DefaultSelector() as selector:
                selector.register(server.stdout, selectors.EVENT_READ)
                if (
                    not selector.select(10)
                    or server.stdout.readline().strip() != "mapped"
                ):
                    raise ValueError("native fixture did not map")
            pointer.move(240, 200)
            pointer.settle()

            def click():
                pointer.button(1, True)
                pointer.button(1, False)
                pointer.flush()

            def patch(rgb):
                return Patch(285, 245, np.full((16, 16, 3), rgb, dtype=np.uint8), 0)

            before = [patch((16, 32, 64))]
            wait_pixels(screen, before, 2)
            sample = observe_transition(
                screen, click, before, [patch((136, 68, 34))], timeout=2
            )
            witnesses = sample.pop("witnesses")
            sample["observed_rgb"] = witnesses[0][0][0, 0].tolist()
            sample["observed_error"] = witnesses[0][1]
            sample["purpose"] = (
                "independent X11 fixture check, no Pancake application evidence"
            )
            sample["capture"] = "Xvfb XWD mapped screen, private XTest"
            (directory / "smoke.json").write_text(json.dumps(sample, indent=2) + "\n")
            print(json.dumps(sample))
        except (ValueError, TimeoutError):
            print(screen.rgb(285, 245, 1, 1).tolist())
            raise
        finally:
            MacOSUISession._reap(server)
    binary.unlink()


if __name__ == "__main__":
    main()
