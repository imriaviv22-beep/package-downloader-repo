from __future__ import annotations

import csv
from pathlib import Path
from typing import Iterable

from package_downloader.config import InputConfig
from package_downloader.models import PackageRecord


def iter_packages(path: Path, config: InputConfig) -> Iterable[PackageRecord]:
    if config.has_header:
        with path.open("r", encoding="utf-8", newline="") as handle:
            reader = csv.DictReader(handle)
            for row in reader:
                if row is None:
                    continue
                if any(value is not None and str(value).strip() for value in row.values()):
                    yield PackageRecord(
                        sha1_actual=row.get("sha1_actual") or None,
                        md5_actual=row.get("md5_actual") or None,
                        sha256=row.get("sha256") or None,
                        raw=row,
                    )
    else:
        with path.open("r", encoding="utf-8", newline="") as handle:
            reader = csv.reader(handle)
            for row in reader:
                if not row:
                    continue
                if any(value is not None and str(value).strip() for value in row):
                    raw = {f"column_{idx}": value for idx, value in enumerate(row)}
                    yield PackageRecord(raw=raw)


def count_packages(path: Path, config: InputConfig) -> int:
    return sum(1 for _ in iter_packages(path, config))
