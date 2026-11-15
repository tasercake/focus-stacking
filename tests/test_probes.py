import json
import sys

import numpy as np
import pytest


def test_numeric_wire_round_trips_complex_and_rejects_invalid_shapes():
    from stack_conformance.probes import encode_array, decode_array
    for image in (np.arange(6, dtype=np.uint16).reshape(2, 3),
                  np.array([[1 + 2j, 3 - 4j]], dtype=np.complex64)):
        encoded = json.loads(json.dumps(encode_array(image), allow_nan=False))
        actual = decode_array(encoded)
        np.testing.assert_array_equal(actual, image)
        assert actual.dtype == image.dtype
    with pytest.raises(ValueError, match="shape"):
        decode_array({"dtype": "float32", "shape": [2, 2], "data": [1]})
    with pytest.raises(ValueError, match="dtype"):
        decode_array({"dtype": "object", "shape": [1], "data": [1]})
    with pytest.raises(ValueError, match="range"):
        decode_array({"dtype": "uint8", "shape": [1], "data": [256]})


def test_probe_uses_external_protocol_and_freezes_input_digest(tmp_path):
    from stack_conformance.context import CaseContext
    from stack_conformance.target import TargetSpec
    adapter = tmp_path / "adapter.py"
    adapter.write_text('''import json,sys
from pathlib import Path
args = dict(zip(sys.argv[1::2], sys.argv[2::2]))
request = json.loads(Path(args["--request"]).read_text())
Path(args["--response"]).write_text(json.dumps({"schema_version":1,"ok":True,
 "arrays":request["arrays"],"values":{"scale":1.0}}))
''')
    target = TargetSpec("external", tmp_path, ("unused",), probe=(sys.executable, str(adapter)))
    ctx = CaseContext(target, tmp_path / "case")
    image = np.arange(6, dtype=np.float32).reshape(2, 3)
    result = ctx.probe("geometry.identity", arrays={"image": image}, options={"order": 1})
    assert result.ok and result.values == {"scale": 1.0} and result.error is None
    np.testing.assert_array_equal(result.arrays["image"], image)
    assert ctx.notes["requests"][0]["operation"] == "geometry.identity"
    assert len(ctx.notes["requests"][0]["arrays"]["image"]["sha256"]) == 64
    assert ctx.outputs
    with pytest.raises(RuntimeError, match="host"):
        CaseContext(target, tmp_path / "guest", environment={"CF_VM_GUEST": "1"}).probe("geometry.identity")


def test_numeric_baseline_preserves_complex_parts_and_integer_precision(tmp_path):
    from stack_conformance.baseline import Baseline
    output = tmp_path / "numbers.npy"
    np.save(output, np.array([[1 + 2j]], dtype=np.complex64))
    frozen = Baseline(tmp_path / "baseline", record=True)
    frozen.check("math", {"matrix": output})
    frozen.save({})
    replay = Baseline(tmp_path / "baseline")
    replay.check("math", {"matrix": output})
    np.save(output, np.array([[1 + 3j]], dtype=np.complex64))
    with pytest.raises(AssertionError, match="numeric"):
        replay.check("math", {"matrix": output})


def test_probe_contract_normalizes_only_case_paths_and_loopback_ports(tmp_path):
    from stack_conformance.probes import portable_options
    case = tmp_path / "case"
    actual = portable_options({"endpoint": "http://127.0.0.1:54321/releases?a=1",
                               "file": str(case / "download/file.zip"),
                               "remote": "https://example.com:443/releases"}, case)
    assert actual == {"endpoint": "http://127.0.0.1:{port}/releases?a=1",
                      "file": "{case}/download/file.zip", "remote": "https://example.com:443/releases"}
