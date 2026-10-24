"""Red-team probe for execute-only reference memory disclosure."""

import ctypes
import os
from pathlib import Path
import signal
import subprocess


def main() -> None:
    child = subprocess.Popen(["/opt/reference/dot", "-Tplain"], stdin=subprocess.PIPE,
                             stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    try:
        libc = ctypes.CDLL(None, use_errno=True)
        attach = libc.ptrace(16, child.pid, None, None)
        if attach != 0:
            print(f"PTRACE_DENIED errno={ctypes.get_errno()}")
            return
        os.waitpid(child.pid, 0)
        memory_map = Path(f"/proc/{child.pid}/maps").read_text()
        mapping = next(line for line in memory_map.splitlines() if "/opt/reference/dot" in line)
        base = int(mapping.split("-", 1)[0], 16)
        ctypes.set_errno(0)
        word = libc.ptrace(2, child.pid, ctypes.c_void_p(base), None)
        error = ctypes.get_errno()
        print(f"PTRACE_READ word={word} errno={error}")
        libc.ptrace(17, child.pid, None, None)
        if error == 0:
            raise RuntimeError("reference code memory can be read by solver")
    finally:
        child.kill()
        child.wait()


if __name__ == "__main__":
    main()
