from __future__ import annotations

from datetime import datetime, timezone
from enum import Enum
from typing import Any

from pydantic import BaseModel, Field


class RepoType(str, Enum):
    PYPI = "pypi"
    NPM = "npm"
    MAVEN = "maven"
    DOCKER = "docker"


class DownloadStatus(str, Enum):
    DOWNLOADED = "downloaded"
    SKIPPED = "skipped"
    ERROR = "error"


class PackageRecord(BaseModel):
    sha1_actual: str | None = None
    md5_actual: str | None = None
    sha256: str | None = None
    raw: dict[str, Any] = Field(default_factory=dict)


class DownloadResult(BaseModel):
    package: PackageRecord
    status: DownloadStatus
    message: str | None = None
    temp_path: str | None = None
    final_path: str | None = None


class BatchResult(BaseModel):
    results: list[DownloadResult] = Field(default_factory=list)
    errors: int = 0


class OffsetState(BaseModel):
    offset: int = 0
    updated_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))


class ErrorRecord(BaseModel):
    repo: RepoType
    message: str
    raw: dict[str, Any] = Field(default_factory=dict)
    recorded_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
