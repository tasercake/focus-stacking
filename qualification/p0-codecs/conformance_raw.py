"""Generate frozen suite Bayer data and independently check full Rust development."""

import argparse
import hashlib
import json
import sys
from pathlib import Path

import numpy as np
import PIL
import scipy
import tifffile

ROOT = Path(__file__).resolve().parents[2]
SUITE_SOURCE = ROOT / "pancake-conformance" / "src"
sys.path.insert(0, str(SUITE_SOURCE))

from pancake_conformance.fixtures import generate_fixture
from pancake_conformance.validators import validate_image


def file_hash(path):
    """Hash exact input, output or unchanged source bytes."""
    return hashlib.sha256(path.read_bytes()).hexdigest()


def prepare(output):
    """Use unchanged fixture code with its locked numerical/image dependencies."""
    fixture = generate_fixture("bayer_dng", output / "fixtures")
    result = {
        "fixture": fixture.name,
        "metadata": fixture.metadata,
        "fixture_generator_sha256": file_hash(
            SUITE_SOURCE / "pancake_conformance/fixtures.py"
        ),
        "validator_sha256": file_hash(
            SUITE_SOURCE / "pancake_conformance/validators.py"
        ),
        "versions": {
            "numpy": np.__version__,
            "scipy": scipy.__version__,
            "pillow": PIL.__version__,
            "tifffile": tifffile.__version__,
        },
        "inputs": {
            str(path.relative_to(output)): file_hash(path) for path in fixture.paths
        },
    }
    (output / "fixture-provenance.json").write_text(json.dumps(result, indent=2) + "\n")
    print(json.dumps(result))


def verify(output):
    """Enforce exact unchanged RAW-case output contract with independent libtiff."""
    path = output / "conformance-developed.tiff"
    if not path.is_file():
        raise AssertionError(
            "Complete Bayer-to-RGB16 output is missing; sensor parsing is insufficient"
        )
    result = validate_image(
        path, shape=[112, 160, 3], dtype="uint16", min_range=10000, genuine_16bit=True
    )
    pixels = tifffile.imread(path)
    promoted = output / "negative-promoted-8bit.tiff"
    tifffile.imwrite(
        promoted,
        (pixels // 257 * 257).astype(np.uint16),
        photometric="rgb",
        metadata=None,
    )
    try:
        validate_image(
            promoted,
            shape=[112, 160, 3],
            dtype="uint16",
            min_range=10000,
            genuine_16bit=True,
        )
    except AssertionError as error:
        if str(error) != "Image lost 16-bit precision":
            raise
    else:
        raise AssertionError("Independent validator accepted promoted 8-bit output")
    provenance = json.loads((output / "fixture-provenance.json").read_text())
    if (
        file_hash(SUITE_SOURCE / "pancake_conformance/fixtures.py")
        != provenance["fixture_generator_sha256"]
    ):
        raise AssertionError("Frozen fixture source changed")
    if (
        file_hash(SUITE_SOURCE / "pancake_conformance/validators.py")
        != provenance["validator_sha256"]
    ):
        raise AssertionError("Frozen validator source changed")
    for relative, digest in provenance["inputs"].items():
        if file_hash(output / relative) != digest:
            raise AssertionError("Generated RAW input bytes changed")
    result.update(
        {
            "status": "pass",
            "output_sha256": file_hash(path),
            "pixel_sha256": hashlib.sha256(pixels.astype("<u2").tobytes()).hexdigest(),
            "unique_u16_values": int(np.unique(pixels).size),
            "non_8bit_promoted_samples": int(np.count_nonzero(pixels % 257)),
            "source_unchanged": True,
            "fixture_inputs_unchanged": True,
            "negative_promoted_8bit_rejected": True,
            "scope": "RAW decode/development/export capability; not five-method stacking conformance",
        }
    )
    (output / "independent-developed-results.json").write_text(
        json.dumps(result, indent=2) + "\n"
    )
    print(json.dumps(result))


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("action", choices=("prepare", "verify"))
    parser.add_argument("output", type=Path)
    arguments = parser.parse_args()
    if arguments.action == "prepare":
        prepare(arguments.output)
    else:
        verify(arguments.output)
