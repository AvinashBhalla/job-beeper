"""Safe retention and checksum manifest for local JobBeeper recovery snapshots.

Only explicitly date-stamped production snapshot families are eligible for
pruning. Current aliases, historical rollback files, and unrelated files are
never deletion candidates.
"""
from __future__ import annotations

import argparse
import hashlib
import os
import re
from datetime import datetime
from pathlib import Path

_PATTERNS = {
    "database": re.compile(r"^production-jobs-(\d{8})\.sqlite3$"),
    "config": re.compile(r"^production-config-(\d{8})\.json$"),
    "config_token": re.compile(r"^production-config-token-(\d{8})$"),
}


def _dated_files(directory: Path, pattern: re.Pattern[str]) -> list[Path]:
    found: list[tuple[str, Path]] = []
    for path in directory.iterdir():
        match = pattern.fullmatch(path.name)
        if not match or not path.is_file():
            continue
        stamp = match.group(1)
        try:
            datetime.strptime(stamp, "%Y%m%d")
        except ValueError:
            continue
        found.append((stamp, path))
    return [path for _, path in sorted(found, key=lambda item: item[0], reverse=True)]


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def rotate_snapshots(directory: str | Path, keep: int = 7) -> dict[str, int]:
    """Keep the newest dated production files per family and atomically write SHA256SUMS."""
    root = Path(directory)
    if not root.is_dir():
        raise ValueError(f"backup directory does not exist: {root}")
    if keep < 1:
        raise ValueError("keep must be at least 1")

    removed: dict[str, int] = {}
    retained: list[Path] = []
    for family, pattern in _PATTERNS.items():
        dated = _dated_files(root, pattern)
        for stale in dated[keep:]:
            stale.unlink()
        retained.extend(dated[:keep])
        removed[family] = max(0, len(dated) - keep)

    retained.sort(key=lambda path: path.name)
    manifest_tmp = root / ".SHA256SUMS.tmp"
    manifest = root / "SHA256SUMS"
    try:
        with manifest_tmp.open("w", encoding="utf-8", newline="\n") as stream:
            for path in retained:
                stream.write(f"{_sha256(path)}  {path.name}\n")
        os.chmod(manifest_tmp, 0o600)
        os.replace(manifest_tmp, manifest)
    finally:
        manifest_tmp.unlink(missing_ok=True)

    return removed


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--directory", required=True, type=Path)
    parser.add_argument("--keep", type=int, default=7)
    args = parser.parse_args()
    removed = rotate_snapshots(args.directory, args.keep)
    print("retention_removed=" + ",".join(f"{key}:{value}" for key, value in removed.items()))
    print(f"checksum_manifest={args.directory / 'SHA256SUMS'}")


if __name__ == "__main__":
    main()
