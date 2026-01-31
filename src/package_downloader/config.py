from __future__ import annotations

from pathlib import Path
from typing import Any

import yaml
from pydantic import BaseModel, Field


class PathsConfig(BaseModel):
    offsets_dir: Path = Field(default=Path("data/offsets"))
    output_dir: Path = Field(default=Path("data/output"))
    temp_dir: Path = Field(default=Path("data/temp"))
    errors_dir: Path = Field(default=Path("data/errors"))


class DownloadConfig(BaseModel):
    batch_size: int = Field(default=50, ge=1)
    max_workers: int = Field(default=8, ge=1)
    fail_fast: bool = False
    verify_hash: bool = True


class InputConfig(BaseModel):
    has_header: bool = True


class PypiConfig(BaseModel):
    cache_size: int = Field(default=256, ge=1)


class MavenConfig(BaseModel):
    registries: list[str] = Field(default_factory=list)


class AppConfig(BaseModel):
    paths: PathsConfig = Field(default_factory=PathsConfig)
    download: DownloadConfig = Field(default_factory=DownloadConfig)
    input: InputConfig = Field(default_factory=InputConfig)
    pypi: PypiConfig = Field(default_factory=PypiConfig)
    maven: MavenConfig = Field(default_factory=MavenConfig)


def load_config(path: Path) -> AppConfig:
    raw = yaml.safe_load(path.read_text(encoding="utf-8")) or {}
    if not isinstance(raw, dict):
        raise ValueError("Config root must be a mapping.")
    return AppConfig.model_validate(raw)


def ensure_paths(config: AppConfig) -> None:
    config.paths.offsets_dir.mkdir(parents=True, exist_ok=True)
    config.paths.output_dir.mkdir(parents=True, exist_ok=True)
    config.paths.temp_dir.mkdir(parents=True, exist_ok=True)
    config.paths.errors_dir.mkdir(parents=True, exist_ok=True)
