from __future__ import annotations

from abc import ABC, abstractmethod
from hashlib import sha256
from pathlib import Path
from shutil import move

from package_downloader.config import AppConfig
from package_downloader.logging_utils import get_logger
from package_downloader.models import DownloadResult, DownloadStatus, PackageRecord


class RepoDownloader(ABC):
    def __init__(self, config: AppConfig) -> None:
        self.config = config

    def download(self, package: PackageRecord) -> DownloadResult:
        result = self._download(package)
        return self._finalize_download(result)

    @abstractmethod
    def _download(self, package: PackageRecord) -> DownloadResult:
        raise NotImplementedError

    def _finalize_download(self, result: DownloadResult) -> DownloadResult:
        logger = get_logger(__name__)
        if result.status != DownloadStatus.DOWNLOADED:
            return result
        if not result.temp_path or not result.final_path:
            return result

        temp_path = Path(result.temp_path)
        final_path = Path(result.final_path)
        expected = result.package.sha256 or ""

        if self.config.download.verify_hash and expected:
            actual = self._file_sha256(temp_path)
            if actual.lower() != expected.lower():
                temp_path.unlink(missing_ok=True)
                logger.warning(
                    "SHA256 mismatch for %s: expected=%s actual=%s",
                    result.final_path,
                    expected,
                    actual,
                )
                return DownloadResult(
                    package=result.package,
                    status=DownloadStatus.ERROR,
                    message="SHA256 mismatch.",
                )

        final_path.parent.mkdir(parents=True, exist_ok=True)
        move(str(temp_path), str(final_path))
        return result

    @staticmethod
    def _file_sha256(path: Path) -> str:
        digest = sha256()
        with path.open("rb") as handle:
            for chunk in iter(lambda: handle.read(1024 * 1024), b""):
                digest.update(chunk)
        return digest.hexdigest()
