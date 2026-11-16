"""Versioned numeric hook protocol; no application or UI toolkit dependencies."""
from dataclasses import dataclass
import math
import re

import numpy as np


DTYPES = {np.dtype(name).name for name in (
    "bool", "int8", "uint8", "int16", "uint16", "int32", "uint32", "int64", "uint64",
    "float32", "float64", "complex64", "complex128")}


def portable_options(value, case_directory):
    """Preserve semantic inputs while removing run paths and local server ports."""
    if isinstance(value, dict):
        return {key: portable_options(item, case_directory) for key, item in value.items()}
    if isinstance(value, (list, tuple)):
        return [portable_options(item, case_directory) for item in value]
    if isinstance(value, str):
        value = value.replace(str(case_directory), "{case}")
        return re.sub(r"(https?://(?:127\.0\.0\.1|localhost)):\d+(?=/|$)", r"\1:{port}", value)
    return value


def encode_array(value):
    array = np.asarray(value)
    if array.dtype.name not in DTYPES:
        raise ValueError(f"unsupported numeric dtype: {array.dtype}")
    if not np.isfinite(array).all():
        raise ValueError("numeric arrays must be finite")
    result = {"dtype": array.dtype.name, "shape": list(array.shape)}
    if array.dtype.kind == "c":
        result.update(real=array.real.ravel().tolist(), imag=array.imag.ravel().tolist())
    else:
        result["data"] = array.ravel().tolist()
    return result


def decode_array(value):
    if not isinstance(value, dict) or value.get("dtype") not in DTYPES:
        raise ValueError("unsupported numeric dtype")
    shape = value.get("shape")
    if not isinstance(shape, list) or any(type(n) is not int or n < 0 for n in shape):
        raise ValueError("invalid numeric array shape")
    size = math.prod(shape)
    if len(shape) > 8 or size > 16_000_000:
        raise ValueError("numeric array shape exceeds protocol limit")
    dtype = np.dtype(value["dtype"])
    names = ("real", "imag") if dtype.kind == "c" else ("data",)
    for name in names:
        data = value.get(name)
        if not isinstance(data, list) or len(data) != size:
            raise ValueError("numeric array data does not match shape")
        if any(type(x) not in (int, float, bool) for x in data):
            raise ValueError("numeric array data must contain numbers")
        if dtype.kind in "iu":
            limits = np.iinfo(dtype)
            if any(not limits.min <= x <= limits.max or int(x) != x for x in data):
                raise ValueError("integer value outside dtype range")
        if dtype.kind == "b" and any(type(x) is not bool for x in data):
            raise ValueError("boolean dtype requires boolean values")
    if dtype.kind == "c":
        array = np.asarray(value["real"], dtype=np.float64) + 1j * np.asarray(value["imag"], dtype=np.float64)
        array = array.astype(dtype)
    else:
        array = np.asarray(value["data"], dtype=dtype)
    if not np.isfinite(array).all():
        raise ValueError("numeric arrays must be finite")
    return array.reshape(shape)


@dataclass
class ProbeResult:
    ok: bool
    arrays: dict
    values: dict
    error: dict | None = None

    @classmethod
    def decode(cls, response):
        if response.get("schema_version") != 1 or type(response.get("ok")) is not bool:
            raise ValueError("invalid component response schema")
        arrays, values = response.get("arrays", {}), response.get("values", {})
        if not isinstance(arrays, dict) or not isinstance(values, dict):
            raise ValueError("invalid component response values")
        error = response.get("error")
        if response["ok"] and error is not None:
            raise ValueError("successful component response contains error")
        if not response["ok"] and (not isinstance(error, dict) or not error.get("kind")):
            raise ValueError("failed component response requires error kind")
        return cls(response["ok"], {name: decode_array(array) for name, array in arrays.items()}, values, error)
