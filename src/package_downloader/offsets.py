from __future__ import annotations

from pathlib import Path

from package_downloader.models import OffsetState, RepoType


def _offset_path(offsets_dir: Path, repo: RepoType) -> Path:
    return offsets_dir / f"{repo.value}.offset.json"


def load_offset(offsets_dir: Path, repo: RepoType) -> OffsetState:
    path = _offset_path(offsets_dir, repo)
    if not path.exists():
        return OffsetState()
    try:
        return OffsetState.model_validate_json(path.read_text(encoding="utf-8"))
    except Exception:
        return OffsetState()


def save_offset(offsets_dir: Path, repo: RepoType, state: OffsetState) -> None:
    path = _offset_path(offsets_dir, repo)
    path.write_text(state.model_dump_json(indent=2), encoding="utf-8")


def reset_offset(offsets_dir: Path, repo: RepoType) -> None:
    path = _offset_path(offsets_dir, repo)
    if path.exists():
        path.unlink()
