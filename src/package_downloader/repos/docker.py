from __future__ import annotations

import subprocess
from pathlib import Path

from pydantic import BaseModel, ConfigDict

from package_downloader.config import AppConfig
from package_downloader.models import DownloadResult, DownloadStatus, PackageRecord
from package_downloader.repos.base import RepoDownloader


class DockerCsvRow(BaseModel):
    model_config = ConfigDict(extra="allow")

    docker_repo_name: str
    docker_manifest: str


class DockerDownloader(RepoDownloader):
    def __init__(self, config: AppConfig) -> None:
        super().__init__(config)
        self.output_dir = self.config.paths.output_dir / "docker"
        self.output_dir.mkdir(parents=True, exist_ok=True)
        self.temp_dir = self.config.paths.temp_dir / "docker"
        self.temp_dir.mkdir(parents=True, exist_ok=True)

    def _download(self, package: PackageRecord) -> DownloadResult:
        try:
            row = DockerCsvRow.model_validate(package.raw)
        except Exception as exc:
            return DownloadResult(
                package=package,
                status=DownloadStatus.SKIPPED,
                message=f"Invalid row for Docker download: {exc}",
            )

        repo_name = row.docker_repo_name.strip()
        manifest = row.docker_manifest.strip()
        if not repo_name or not manifest:
            return DownloadResult(
                package=package,
                status=DownloadStatus.ERROR,
                message="docker_repo_name or docker_manifest is missing.",
            )

        image_ref = f"{repo_name}:{manifest}"
        filename = _sanitize_filename(f"{manifest}.tar")
        repo_dir = Path(*repo_name.split("/"))
        temp_path = self.temp_dir / repo_dir / filename
        target_path = self.output_dir / repo_dir / filename
        if target_path.exists():
            return DownloadResult(
                package=package,
                status=DownloadStatus.SKIPPED,
                message="File already exists.",
            )

        try:
            _docker_pull(image_ref)
            _docker_save(image_ref, temp_path)
        except Exception as exc:
            return DownloadResult(
                package=package,
                status=DownloadStatus.ERROR,
                message=f"Docker download failed: {exc}",
            )

        return DownloadResult(
            package=package,
            status=DownloadStatus.DOWNLOADED,
            temp_path=str(temp_path),
            final_path=str(target_path),
        )


def _docker_pull(image_ref: str) -> None:
    subprocess.run(["docker", "pull", image_ref], check=True, capture_output=True, text=True)


def _docker_save(image_ref: str, target_path: Path) -> None:
    target_path.parent.mkdir(parents=True, exist_ok=True)
    subprocess.run(
        ["docker", "save", image_ref, "-o", str(target_path)],
        check=True,
        capture_output=True,
        text=True,
    )


def _sanitize_filename(value: str) -> str:
    return (
        value.replace("/", "_")
        .replace("\\", "_")
        .replace(":", "_")
        .replace("@", "_")
    )
