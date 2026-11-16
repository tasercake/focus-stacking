"""Reference-only service hooks calling original ChimpStackr functions.

The JSON boundary describes service operations, never Python symbol names.
No service implementation is substituted or copied from the application.
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path
import sys

import numpy as np

from ..probes import decode_array, encode_array


def _json_value(value):
    if isinstance(value, np.ndarray):
        return value.tolist()
    if isinstance(value, np.generic):
        return value.item()
    if isinstance(value, dict):
        return {key: _json_value(item) for key, item in value.items()}
    if isinstance(value, (list, tuple)):
        return [_json_value(item) for item in value]
    return value


def dispatch(operation, arrays, options):
    """Map reachable service operations to the reference service adapter."""
    if not operation.startswith("service."):
        raise ValueError(f"Unknown component operation: {operation}")
    # The launcher runs in target.root. Keep target modules out of generic code.
    sys.path.insert(0, str(Path.cwd()))
    from .chimpstackr_services import dispatch as service_dispatch
    return service_dispatch(operation, arrays, options)


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--request", type=Path, required=True)
    parser.add_argument("--response", type=Path, required=True)
    args = parser.parse_args(argv)
    try:
        request = json.loads(args.request.read_text())
        if request.get("schema_version") != 1:
            raise ValueError("unsupported component request schema")
        arrays = {name: decode_array(array) for name, array in request.get("arrays", {}).items()}
        output, values = dispatch(request["operation"], arrays, request.get("options", {}))
        response = {"schema_version": 1, "ok": True,
                    "arrays": {name: encode_array(array) for name, array in output.items()},
                    "values": _json_value(values)}
        serialized = json.dumps(response, allow_nan=False)
    except Exception as error:
        serialized = json.dumps({"schema_version": 1, "ok": False, "arrays": {}, "values": {},
                                 "error": {"kind": type(error).__name__, "message": str(error)}})
    args.response.parent.mkdir(parents=True, exist_ok=True)
    args.response.write_text(serialized + "\n")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
