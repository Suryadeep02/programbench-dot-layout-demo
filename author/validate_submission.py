"""Reject opaque oracle carryover and rebuild submitted source in a clean image."""

from __future__ import annotations

import hashlib
import json
import os
from pathlib import Path
import re
import shutil
import subprocess
import tempfile
import uuid


ROOT = Path(__file__).resolve().parents[1]
IGNORED_DIRECTORIES = {".git", ".codex", ".pytest_cache", "__pycache__", "build", ".venv"}
IGNORED_FILES = {"final.txt", ".DS_Store"}
MAX_FILE_BYTES = 1_000_000
MAX_TREE_BYTES = 5_000_000
MAX_FILES = 256
MAGIC = (b"\x7fELF", b"PK\x03\x04", b"\x1f\x8b", b"!<arch>\n",
         b"\xfd7zXZ", b"\x28\xb5\x2f\xfd", b"MZ")
LONG_BASE64 = re.compile(r"[A-Za-z0-9+/]{512,}={0,2}")
LONG_HEX_BYTES = re.compile(r"(?:0x[0-9A-Fa-f]{2}[\s,]*){128,}")


class SourceOnlyFailure(ValueError):
    """The candidate submitted files outside the stated source-only contract."""


class CandidateBuildFailure(RuntimeError):
    """The candidate source failed to produce an executable in its clean build."""


def _included_files(root: Path) -> tuple[list[Path], list[str]]:
    files: list[Path] = []
    errors: list[str] = []
    for directory, dirnames, filenames in os.walk(root, topdown=True, followlinks=False):
        parent = Path(directory)
        for name in list(dirnames):
            path = parent / name
            if path.is_symlink():
                errors.append(f"symlink directory is not allowed: {path.relative_to(root)}")
                dirnames.remove(name)
            elif name in IGNORED_DIRECTORIES:
                dirnames.remove(name)
        for name in filenames:
            if name in IGNORED_FILES:
                continue
            path = parent / name
            if path.is_symlink():
                errors.append(f"symlink file is not allowed: {path.relative_to(root)}")
            elif path.is_file():
                files.append(path)
            else:
                errors.append(f"nonregular file is not allowed: {path.relative_to(root)}")
    return sorted(files), errors


def scan_source(root: Path) -> list[str]:
    """Return concrete reasons a submission violates the source-only contract."""
    root = Path(root).resolve()
    if not root.is_dir():
        return ["submission is not a directory"]
    files, errors = _included_files(root)
    if root / "compile.sh" not in files:
        errors.append("compile.sh is missing")
    if len(files) > MAX_FILES:
        errors.append(f"source tree has {len(files)} files; maximum is {MAX_FILES}")
    total = 0
    for path in files:
        relative = path.relative_to(root).as_posix()
        size = path.stat().st_size
        total += size
        if size > MAX_FILE_BYTES:
            errors.append(f"source file is too large: {relative}")
            continue
        data = path.read_bytes()
        if data.startswith(MAGIC) or b"\x00" in data:
            errors.append(f"binary or archive payload is not source text: {relative}")
            continue
        try:
            content = data.decode("utf-8")
        except UnicodeDecodeError:
            errors.append(f"source file is not UTF-8 text: {relative}")
            continue
        if any(ord(character) < 32 and character not in "\t\r\n" for character in content):
            errors.append(f"source file contains binary control bytes: {relative}")
        if LONG_BASE64.search(content) or LONG_HEX_BYTES.search(content):
            errors.append(f"source file contains an opaque encoded payload: {relative}")
    if total > MAX_TREE_BYTES:
        errors.append(f"source tree is {total} bytes; maximum is {MAX_TREE_BYTES}")
    return errors[:20]


def source_digest(root: Path) -> str:
    files, errors = _included_files(root)
    if errors:
        raise ValueError(errors)
    hasher = hashlib.sha256()
    for path in files:
        name = path.relative_to(root).as_posix().encode("utf-8")
        data = path.read_bytes()
        hasher.update(len(name).to_bytes(8, "big"))
        hasher.update(name)
        hasher.update(len(data).to_bytes(8, "big"))
        hasher.update(data)
    return hasher.hexdigest()


def suspicious_binary(reference: bytes, candidate: bytes) -> bool:
    """Detect a verbatim, shifted, or lightly patched reference ELF."""
    if not candidate.startswith(b"\x7fELF") and b"\x7fELF" not in candidate[:128]:
        return False
    if candidate == reference:
        return True
    if len(reference) < 64 or len(candidate) < 64:
        return False
    reference_windows = {reference[offset:offset + 64]
                         for offset in range(0, len(reference) - 63, 512)}
    required = (len(reference_windows) + 1) // 2
    matches: set[bytes] = set()
    for offset in range(len(candidate) - 63):
        window = candidate[offset:offset + 64]
        if window in reference_windows:
            matches.add(window)
            if len(matches) >= required:
                return True
    return False


ELF_INVENTORY_SCRIPT = """import json,os
paths=[]
total=0
for directory, dirs, files in os.walk('/workspace', followlinks=False):
    for name in files:
        path=os.path.join(directory,name)
        try:
            size=os.path.getsize(path)
            total+=size
            with open(path,'rb') as handle:
                if handle.read(4)==b'\\x7fELF': paths.append(path)
        except OSError:
            continue
if total>100_000_000 or len(paths)>30: raise SystemExit('candidate runtime assets exceed audit bounds')
print(json.dumps(paths))
"""


def audit_built_image(image: str) -> None:
    """Inspect compiled runtime artifacts without mounting the oracle into the image."""
    inventory = subprocess.run(
        ["docker", "run", "--rm", "--network", "none", "--read-only",
         "--cap-drop", "ALL", "--user", "10001:10001", image,
         "/usr/bin/python3", "-I", "-c", ELF_INVENTORY_SCRIPT],
        capture_output=True, text=True, timeout=60, check=False,
    )
    if inventory.returncode != 0:
        raise CandidateBuildFailure("candidate runtime asset audit failed: " + inventory.stderr[-500:])
    try:
        paths = json.loads(inventory.stdout)
    except json.JSONDecodeError as error:
        raise RuntimeError("runtime asset audit returned malformed inventory") from error
    if not isinstance(paths, list) or not all(isinstance(path, str) and path.startswith("/workspace/") for path in paths):
        raise RuntimeError("runtime asset audit returned invalid paths")
    reference = (ROOT / "agent" / "reference" / "dot").read_bytes()
    with tempfile.TemporaryDirectory(prefix="pb-dot-binary-audit-") as temporary:
        name = "dot-audit-" + uuid.uuid4().hex[:16]
        created = subprocess.run(["docker", "create", "--name", name, image, "/bin/true"],
                                 capture_output=True, text=True, timeout=30, check=False)
        if created.returncode != 0:
            raise RuntimeError("could not inspect candidate image: " + created.stderr[-500:])
        try:
            for index, path in enumerate(paths):
                destination = Path(temporary) / f"artifact-{index}"
                copied = subprocess.run(["docker", "cp", "-L", f"{name}:{path}", str(destination)],
                                        capture_output=True, text=True, timeout=30, check=False)
                if copied.returncode != 0:
                    raise CandidateBuildFailure(f"could not inspect built artifact {path}: {copied.stderr[-300:]}")
                data = destination.read_bytes()
                if suspicious_binary(reference, data):
                    raise CandidateBuildFailure(f"built artifact resembles the reference executable: {path}")
        finally:
            subprocess.run(["docker", "rm", "-f", name], capture_output=True,
                           text=True, timeout=30, check=False)


def build_submission(submission: Path, image: str) -> str:
    submission = Path(submission).resolve()
    errors = scan_source(submission)
    if errors:
        raise SourceOnlyFailure("source-only submission check failed: " + "; ".join(errors))
    digest = source_digest(submission)
    with tempfile.TemporaryDirectory(prefix="pb-dot-build-") as temporary:
        context = Path(temporary) / "source"
        shutil.copytree(submission, context, ignore=shutil.ignore_patterns(
            *IGNORED_DIRECTORIES, *IGNORED_FILES))
        if scan_source(context):
            raise RuntimeError("copied build context did not pass source-only scan")
        if source_digest(context) != digest:
            raise RuntimeError("source changed during clean-room copy")
        command = ["docker", "build", "--network=none", "--no-cache", "-f",
                   str(ROOT / "evaluator" / "Dockerfile.candidate"), "-t", image,
                   str(context)]
        try:
            result = subprocess.run(command, capture_output=True, text=True,
                                    encoding="utf-8", errors="replace", timeout=900,
                                    check=False)
        except subprocess.TimeoutExpired as error:
            raise CandidateBuildFailure("candidate clean-room build exceeded 15 minutes") from error
        if result.returncode != 0:
            message = "candidate clean-room build failed:\n" + (result.stdout + result.stderr)[-5000:]
            if "/workspace/compile.sh" in message:
                raise CandidateBuildFailure(message)
            raise RuntimeError("Docker build infrastructure failed:\n" + message)
    audit_built_image(image)
    return digest
