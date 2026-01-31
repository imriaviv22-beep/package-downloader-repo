from __future__ import annotations

from __future__ import annotations

from functools import lru_cache
from pathlib import Path
from threading import Event, Lock

import httpx
from pydantic import BaseModel, ConfigDict, Field

from package_downloader.config import AppConfig
from package_downloader.models import DownloadResult, DownloadStatus, PackageRecord
from package_downloader.repos.base import RepoDownloader


class PypiCsvRow(BaseModel):
    model_config = ConfigDict(extra="allow")

    pypi_name: str
    node_name: str


class PypiReleaseFile(BaseModel):
    filename: str
    url: str


class PypiResponse(BaseModel):
    releases: dict[str, list[PypiReleaseFile]] = Field(default_factory=dict)


class PyPIDownloader(RepoDownloader):
    def __init__(self, config: AppConfig) -> None:
        super().__init__(config)
        self.output_dir = self.config.paths.output_dir / "pypi"
        self.output_dir.mkdir(parents=True, exist_ok=True)
        self.temp_dir = self.config.paths.temp_dir / "pypi"
        self.temp_dir.mkdir(parents=True, exist_ok=True)
        self._inflight: dict[str, Event] = {}
        self._lock = Lock()
        self._cached_fetch = lru_cache(maxsize=self.config.pypi.cache_size)(self._fetch_pypi_payload)

    def _download(self, package: PackageRecord) -> DownloadResult:
        try:
            row = PypiCsvRow.model_validate(package.raw)
        except Exception as exc:
            return DownloadResult(
                package=package,
                status=DownloadStatus.SKIPPED,
                message=f"Invalid row for PyPI download: {exc}",
            )

        try:
            payload = self._get_pypi_payload(row.pypi_name)
        except Exception as exc:
            return DownloadResult(
                package=package,
                status=DownloadStatus.ERROR,
                message=f"PyPI API error: {exc}",
            )

        download_url = _find_release_url(payload, row.node_name)
        if not download_url:
            return DownloadResult(
                package=package,
                status=DownloadStatus.ERROR,
                message=f"Release not found for filename: {row.node_name}",
            )

        target_path = self.output_dir / row.node_name
        if target_path.exists():
            return DownloadResult(
                package=package,
                status=DownloadStatus.SKIPPED,
                message="File already exists.",
            )

        try:
            temp_path = self.temp_dir / row.node_name
            _download_file(download_url, temp_path)
        except Exception as exc:
            return DownloadResult(
                package=package,
                status=DownloadStatus.ERROR,
                message=f"Download failed: {exc}",
            )

        return DownloadResult(
            package=package,
            status=DownloadStatus.DOWNLOADED,
            temp_path=str(temp_path),
            final_path=str(target_path),
        )

    def _get_pypi_payload(self, pypi_name: str) -> PypiResponse:
        cache_key = pypi_name.strip()
        with self._lock:
            event = self._inflight.get(cache_key)
            if event:
                wait_event = event
                do_request = False
            else:
                wait_event = Event()
                self._inflight[cache_key] = wait_event
                do_request = True

        if not do_request:
            wait_event.wait()
            return self._cached_fetch(cache_key)

        try:
            payload = self._cached_fetch(cache_key)
        finally:
            with self._lock:
                wait_event.set()
                self._inflight.pop(cache_key, None)
        return payload

    def _fetch_pypi_payload(self, pypi_name: str) -> PypiResponse:
        api_url = f"https://pypi.org/pypi/{pypi_name}/json"
        response = httpx.get(api_url, timeout=30)
        response.raise_for_status()
        return PypiResponse.model_validate(response.json())


def _find_release_url(payload: PypiResponse, filename: str) -> str | None:
    for files in payload.releases.values():
        for file in files:
            if file.filename == filename:
                return file.url
    return None


def _download_file(url: str, target_path: Path) -> None:
    target_path.parent.mkdir(parents=True, exist_ok=True)
    with httpx.stream("GET", url, timeout=60) as response:
        response.raise_for_status()
        with target_path.open("wb") as handle:
            for chunk in response.iter_bytes():
                handle.write(chunk)
