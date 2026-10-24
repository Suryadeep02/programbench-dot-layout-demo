"""Audit the final solver image for reference readability and task leakage."""

from __future__ import annotations

import hashlib
import json
from pathlib import Path
import subprocess


ROOT = Path(__file__).resolve().parents[1]
IMAGE = "dot-plain-reconstruction:agent"


def _run(command: list[str], *, input_text: str | None = None) -> subprocess.CompletedProcess[str]:
    return subprocess.run(command, input=input_text, capture_output=True, text=True,
                          encoding="utf-8", errors="replace", timeout=60, check=False)


def audit() -> dict[str, object]:
    expected = {
        "/opt/reference/dot", "/opt/task/instruction.md",
        *{"/opt/task/docs/" + path.name for path in (ROOT / "agent" / "docs").iterdir() if path.is_file()},
    }
    inventory = _run(["docker", "run", "--rm", "--network", "none", "--read-only",
                      IMAGE, "find", "/opt", "-type", "f"])
    if inventory.returncode != 0:
        raise RuntimeError(inventory.stderr)
    found = set(inventory.stdout.splitlines())
    if found != expected:
        raise AssertionError(f"solver image /opt inventory differs: extra={found - expected}, missing={expected - found}")
    status = _run(["docker", "run", "--rm", "--network", "none", "--read-only",
                   IMAGE, "sh", "-c",
                   "id -u; stat -c '%a:%u:%g' /opt/reference/dot; "
                   "if head -c 4 /opt/reference/dot >/dev/null 2>&1; then echo readable; else echo denied; fi; "
                   "command -v dot || true; "
                   "find /usr/lib /usr/local/lib -name 'libgvc*' -o -name 'libcgraph*' -o -name 'libgvplugin*' 2>/dev/null; "
                   "find /workspace -mindepth 1 -maxdepth 2 -type f"])
    lines = status.stdout.splitlines()
    if status.returncode != 0 or lines[:3] != ["10001", "111:0:0", "denied"] or len(lines) != 3:
        raise AssertionError(f"solver permission or dependency check failed: {status.stdout!r} {status.stderr!r}")
    smoke = _run(["docker", "run", "--rm", "-i", "--network", "none", "--read-only",
                  IMAGE, "/opt/reference/dot", "-Tplain"], input_text="digraph { a -> b }\n")
    if smoke.returncode != 0 or not smoke.stdout.startswith("graph 1 ") or not smoke.stdout.endswith("stop\n"):
        raise AssertionError(f"execute-only reference failed: {smoke.stderr}")
    digest = _run(["docker", "run", "--rm", "--network", "none", "--read-only",
                   "--user", "0", IMAGE, "sha256sum", "/opt/reference/dot"])
    expected_hash = hashlib.sha256((ROOT / "agent" / "reference" / "dot").read_bytes()).hexdigest()
    if digest.returncode != 0 or digest.stdout.split()[0] != expected_hash:
        raise AssertionError("reference image binary hash differs from pinned agent copy")
    segments = _run(["docker", "run", "--rm", "--network", "none", "--read-only",
                     "--user", "0", IMAGE, "readelf", "-l", "/opt/reference/dot"])
    if segments.returncode != 0 or " INTERP " in segments.stdout or "Requesting program interpreter" in segments.stdout:
        raise AssertionError("reference has a dynamic loader; LD_PRELOAD can expose its memory")
    result = {"image": IMAGE, "task_file_count": len(found), "reference_sha256": expected_hash,
              "reference_executable": True, "reference_read_denied_to_solver": True,
              "reference_has_dynamic_loader": False,
              "graphviz_implementation_files_found": 0, "workspace_files_found": 0}
    (ROOT / "author" / "agent_image_audit.json").write_text(
        json.dumps(result, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    return result


if __name__ == "__main__":
    print(json.dumps(audit(), sort_keys=True))
