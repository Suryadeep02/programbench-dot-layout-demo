"""Reproduce process-memory and loader-injection attacks against the solver image."""

from __future__ import annotations

import hashlib
import json
from pathlib import Path
import shutil
import subprocess
import tempfile


ROOT = Path(__file__).resolve().parents[1]
IMAGE = "dot-plain-reconstruction:agent"


def _run(workspace: Path, command: list[str]) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        ["docker", "run", "--rm", "--network", "none", "--read-only",
         "--security-opt", "no-new-privileges",
         "--security-opt", "seccomp=unconfined", "--cap-drop", "ALL",
         "--tmpfs", "/tmp:rw,nosuid,nodev,size=64m",
         "--mount", f"type=bind,source={workspace.resolve()},target=/workspace",
         IMAGE, *command], capture_output=True, text=True, timeout=90, check=False,
    )


def audit() -> dict:
    with tempfile.TemporaryDirectory(prefix="pb-dot-reference-probes-") as temporary:
        workspace = Path(temporary)
        shutil.copy2(ROOT / "author" / "probes" / "preload_probe.c", workspace / "preload_probe.c")
        shutil.copy2(ROOT / "author" / "probes" / "probe_ptrace.py", workspace / "probe_ptrace.py")
        loader = _run(workspace, ["sh", "-lc",
            "gcc -shared -fPIC /workspace/preload_probe.c -o /workspace/probe.so && "
            "LD_PRELOAD=/workspace/probe.so /opt/reference/dot -V >/dev/null 2>&1 && "
            "if test -e /tmp/preload_succeeded; then echo PRELOAD_INJECTED; exit 99; "
            "else echo PRELOAD_BLOCKED; fi"])
        if loader.returncode != 0 or loader.stdout.strip() != "PRELOAD_BLOCKED":
            raise AssertionError(f"loader injection succeeded or probe failed: {loader.stdout!r} {loader.stderr!r}")
        ptrace = _run(workspace, ["python3", "/workspace/probe_ptrace.py"])
        if ptrace.returncode != 0 or ptrace.stdout.strip() != "PTRACE_DENIED errno=1":
            raise AssertionError(f"reference process memory is exposed: {ptrace.stdout!r} {ptrace.stderr!r}")
    image_id = subprocess.check_output(
        ["docker", "image", "inspect", "--format", "{{.Id}}", IMAGE],
        text=True, timeout=30).strip()
    result = {"image": IMAGE, "image_id": image_id,
              "reference_sha256": hashlib.sha256((ROOT / "agent" / "reference" / "dot").read_bytes()).hexdigest(),
              "loader_injection": "blocked", "same_user_ptrace": "EPERM"}
    output = ROOT / "author" / "reference_isolation_audit.json"
    output.write_text(json.dumps(result, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    return result


if __name__ == "__main__":
    print(json.dumps(audit(), sort_keys=True))
