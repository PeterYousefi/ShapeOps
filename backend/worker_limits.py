"""Resource ceilings for the disposable native CAD process, before CAD imports."""

import sys

MAX_RESULT_BYTES = 24 * 1024 * 1024
CPU_SECONDS = 25
LINUX_ADDRESS_SPACE_BYTES = 2560 * 1024 * 1024
LINUX_DATA_BYTES = 1024 * 1024 * 1024


def apply_limits(
    cpu_seconds=CPU_SECONDS,
    result_bytes=MAX_RESULT_BYTES,
    address_space_bytes=LINUX_ADDRESS_SPACE_BYTES,
):
    import resource

    def lower(kind, ceiling):
        soft, hard = resource.getrlimit(kind)
        new_hard = ceiling if hard == resource.RLIM_INFINITY else min(hard, ceiling)
        new_soft = new_hard if soft == resource.RLIM_INFINITY else min(soft, new_hard)
        resource.setrlimit(kind, (new_soft, new_hard))

    lower(resource.RLIMIT_CORE, 0)
    lower(resource.RLIMIT_CPU, cpu_seconds)
    lower(resource.RLIMIT_FSIZE, result_bytes)
    # Linux enforces mapped address space; macOS is not claimed to enforce this cap.
    if sys.platform == "linux":
        lower(resource.RLIMIT_AS, address_space_bytes)
        lower(resource.RLIMIT_DATA, LINUX_DATA_BYTES)
