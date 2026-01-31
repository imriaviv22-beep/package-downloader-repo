from __future__ import annotations

from pathlib import Path

import httpx
from pydantic import BaseModel, ConfigDict

from package_downloader.config import AppConfig
from package_downloader.models import DownloadResult, DownloadStatus, PackageRecord
from package_downloader.repos.base import RepoDownloader


class MavenCsvRow(BaseModel):
    model_config = ConfigDict(extra="allow")

    node_path: str
    node_name: str


class MavenDownloader(RepoDownloader):
    def __init__(self, config: AppConfig) -> None:
        super().__init__(config)
        self.output_dir = self.config.paths.output_dir / "maven"
        self.output_dir.mkdir(parents=True, exist_ok=True)
        self.temp_dir = self.config.paths.temp_dir / "maven"
        self.temp_dir.mkdir(parents=True, exist_ok=True)

    def _download(self, package: PackageRecord) -> DownloadResult:
        try:
            row = MavenCsvRow.model_validate(package.raw)
        except Exception as exc:
            return DownloadResult(
                package=package,
                status=DownloadStatus.SKIPPED,
                message=f"Invalid row for Maven download: {exc}",
            )

        registries = self.config.maven.registries
        if not registries:
            return DownloadResult(
                package=package,
                status=DownloadStatus.ERROR,
                message="No Maven registries configured.",
            )

        rel_path = f"{row.node_path.strip().strip('/')}/{row.node_name.strip()}"
        rel_path = rel_path.lstrip("/")

        temp_path = self.temp_dir / row.node_path / row.node_name
        target_path = self.output_dir / row.node_path / row.node_name
        if target_path.exists():
            return DownloadResult(
                package=package,
                status=DownloadStatus.SKIPPED,
                message="File already exists.",
            )

        for registry in registries:
            url = f"{registry.rstrip('/')}/{rel_path}"
            try:
                _download_file(url, temp_path)
            except httpx.HTTPStatusError as exc:
                if exc.response.status_code == 404:
                    continue
                return DownloadResult(
                    package=package,
                    status=DownloadStatus.ERROR,
                    message=f"Maven download error: {exc}",
                )
            except Exception as exc:
                return DownloadResult(
                    package=package,
                    status=DownloadStatus.ERROR,
                    message=f"Maven download error: {exc}",
                )
            return DownloadResult(
                package=package,
                status=DownloadStatus.DOWNLOADED,
                temp_path=str(temp_path),
                final_path=str(target_path),
            )

        return DownloadResult(
            package=package,
            status=DownloadStatus.ERROR,
            message="File not found in configured Maven registries.",
        )


def _download_file(url: str, target_path: Path) -> None:
    target_path.parent.mkdir(parents=True, exist_ok=True)
    with httpx.stream("GET", url, timeout=60, follow_redirects=True) as response:
        response.raise_for_status()
        with target_path.open("wb") as handle:
            for chunk in response.iter_bytes():
                handle.write(chunk)
