"""Physical identity of the device selected by the pinned OpenCL reference."""

import ctypes
import json
import sys
from uuid import UUID


def reference_opencl(index):
    """Use ChimpStackr's actual device ordering without creating a GPU context."""
    # Run this preflight under the pinned reference interpreter and source root.
    from src.algorithms.stacking_algorithms.ocl import devices

    candidates = devices()
    if not 0 <= index < len(candidates):
        raise ValueError(
            f"OpenCL device index {index} absent ({len(candidates)} found)"
        )
    device = candidates[index]
    if "cl_khr_device_uuid" not in device.extensions.split():
        raise ValueError(f"{device.name} does not report a comparable physical UUID")
    # The pinned PyOpenCL wrapper cannot return the extension's byte array.
    # The native call is CL_DEVICE_UUID_KHR with CL_UUID_SIZE_KHR (16) bytes.
    driver = ctypes.CDLL("libOpenCL.so.1")
    get_info = driver.clGetDeviceInfo
    get_info.argtypes = [
        ctypes.c_void_p,
        ctypes.c_uint,
        ctypes.c_size_t,
        ctypes.c_void_p,
        ctypes.POINTER(ctypes.c_size_t),
    ]
    get_info.restype = ctypes.c_int
    identity = (ctypes.c_ubyte * 16)()
    size = ctypes.c_size_t()
    status = get_info(
        device.int_ptr, 0x106A, len(identity), identity, ctypes.byref(size)
    )
    if status != 0 or size.value != len(identity):
        raise ValueError(f"OpenCL UUID query failed ({status}, {size.value} bytes)")
    return {
        "name": device.name.strip(),
        "driver_version": device.driver_version,
        "index": index,
        "platform": device.platform.name,
        "uuid": f"GPU-{UUID(bytes=bytes(identity))}",
    }


if __name__ == "__main__":
    print(json.dumps(reference_opencl(int(sys.argv[1]))))
