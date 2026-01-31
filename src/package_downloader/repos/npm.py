from __future__ import annotations

from pathlib import Path

import httpx
from pydantic import BaseModel, ConfigDict

from package_downloader.config import AppConfig
from package_downloader.models import DownloadResult, DownloadStatus, PackageRecord
from package_downloader.repos.base import RepoDownloader


class NpmCsvRow(BaseModel):
    model_config = ConfigDict(extra="allow")

    npm_name: str
    npm_version: str


class NpmDownloader(RepoDownloader):
    def __init__(self, config: AppConfig) -> None:
        super().__init__(config)
        self.output_dir = self.config.paths.output_dir / "npm"
        self.output_dir.mkdir(parents=True, exist_ok=True)
        self.temp_dir = self.config.paths.temp_dir / "npm"
        self.temp_dir.mkdir(parents=True, exist_ok=True)

    def _download(self, package: PackageRecord) -> DownloadResult:
        try:
            row = NpmCsvRow.model_validate(package.raw)
        except Exception as exc:
            return DownloadResult(
                package=package,
                status=DownloadStatus.SKIPPED,
                message=f"Invalid row for NPM download: {exc}",
            )

        npm_name = row.npm_name.strip()
        npm_version = row.npm_version.strip()
        if not npm_name or not npm_version:
            return DownloadResult(
                package=package,
                status=DownloadStatus.ERROR,
                message="npm_name or npm_version is missing.",
            )

        base_name = _npm_base_name(npm_name)
        url = f"https://registry.npmjs.org/{npm_name}/-/{base_name}-{npm_version}.tgz"

        filename = f"{base_name}-{npm_version}.tgz"
        temp_path = self.temp_dir / filename
        target_path = self.output_dir / filename
        if target_path.exists():
            return DownloadResult(
                package=package,
                status=DownloadStatus.SKIPPED,
                message="File already exists.",
            )

        try:
            _download_file(url, temp_path)
        except Exception as exc:
            return DownloadResult(
                package=package,
                status=DownloadStatus.ERROR,
                message=f"NPM download failed: {exc}",
            )

        return DownloadResult(
            package=package,
            status=DownloadStatus.DOWNLOADED,
            temp_path=str(temp_path),
            final_path=str(target_path),
        )


def _npm_base_name(npm_name: str) -> str:
    if npm_name.startswith("@") and "/" in npm_name:
        return npm_name.split("/", 1)[1]
    return npm_name


def _download_file(url: str, target_path: Path) -> None:
    target_path.parent.mkdir(parents=True, exist_ok=True)
    with httpx.stream("GET", url, timeout=60, follow_redirects=True) as response:
        response.raise_for_status()
        with target_path.open("wb") as handle:
            for chunk in response.iter_bytes():
                handle.write(chunk)
