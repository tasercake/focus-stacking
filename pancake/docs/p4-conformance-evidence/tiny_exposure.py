"""Independent one-pixel complete-job regression for native RGB16 exposure."""
import hashlib
import json
import os
from pathlib import Path
import subprocess
import sys

import numpy as np
import tifffile

case_dir = Path(sys.argv[1]).resolve()
binary = Path(sys.argv[2]).resolve()
backends = sys.argv[3:]
case_dir.mkdir(parents=False, exist_ok=False)
input_values = [7164, 13928, 19721, 26749, 13495, 20110, 25870, 32560, 58910]
inputs = []
shapes = []
for idx, code in enumerate(input_values):
    image = np.asarray([[[code, code + 2, code + 4]]], dtype=np.uint16)
    path = case_dir / f"frame-{idx:02}.tif"
    tifffile.imwrite(path, image, photometric="rgb", metadata=None)
    inputs.append(path)
    shapes.append(image.astype(np.float64))
truth = np.rint(np.mean([np.mean(shapes[index:index + 4], axis=0) for index in range(0, 9, 4)], axis=0)).astype(np.uint16)
input_hashes = {str(path): hashlib.sha256(path.read_bytes()).hexdigest() for path in inputs}
outcomes = []
for backend in backends:
    output = case_dir / f"result-{backend}.tif"
    request = [str(binary), f"--{backend}", "--input", *map(str, inputs),
               "--method", "exposure_fusion", "--bit-depth", "16", "--output", str(output)]
    events = case_dir / f"{backend}-events.jsonl"
    completed = subprocess.run(request, env={**os.environ, "CONFORMANCE_EVENTS_PATH": str(events)}, cwd=binary.parents[2],
                               capture_output=True, text=True, check=False)
    observed = tifffile.imread(output) if completed.returncode == 0 else np.asarray([])
    event_data = [json.loads(line) for line in events.read_text().splitlines()] if events.exists() else []
    preserved = all(hashlib.sha256(path.read_bytes()).hexdigest() == input_hashes[str(path)] for path in inputs)
    shape_ok = observed.dtype == np.uint16 and observed.shape == truth.shape
    errors = np.abs(observed.astype(np.int64) - truth) if shape_ok else np.asarray([-1])
    passed = (completed.returncode == 0 and shape_ok and int(errors.max()) <= 1 and preserved
              and any(event.get("completed") is True and event.get("actual_backend") == backend
                      and (backend != "gpu" or event.get("physical_gpu") is True) for event in event_data))
    outcomes.append({"backend": backend, "passed": passed, "returncode": completed.returncode, "argv": request,
                     "stdout": completed.stdout, "stderr": completed.stderr, "expected": truth.tolist(),
                     "actual": observed.tolist(), "dtype": str(observed.dtype), "max_error": int(errors.max()),
                     "source_hashes_preserved": preserved, "events": event_data})
result = {"binary_sha256": hashlib.sha256(binary.read_bytes()).hexdigest(), "source_sha256": input_hashes, "outcomes": outcomes}
(case_dir / "result.json").write_text(json.dumps(result, indent=2, sort_keys=True) + "\n")
for outcome in outcomes:
    print(outcome["backend"], "PASS" if outcome["passed"] else "FAIL", "max u16 code error", outcome["max_error"])
raise SystemExit(0 if all(outcome["passed"] for outcome in outcomes) else 1)
