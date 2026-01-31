from __future__ import annotations

from pathlib import Path

from package_downloader.models import ErrorRecord, RepoType


def error_log_path(errors_dir: Path, repo: RepoType) -> Path:
    return errors_dir / f"{repo.value}.errors.jsonl"


def append_error(errors_dir: Path, record: ErrorRecord) -> None:
    path = error_log_path(errors_dir, record.repo)
    path.parent.mkdir(parents=True, exist_ok=True)
    line = record.model_dump_json()
    path.open("a", encoding="utf-8").write(f"{line}\n")
