from __future__ import annotations

from package_downloader.config import AppConfig
from package_downloader.models import RepoType
from package_downloader.repos.base import RepoDownloader
from package_downloader.repos.docker import DockerDownloader
from package_downloader.repos.maven import MavenDownloader
from package_downloader.repos.npm import NpmDownloader
from package_downloader.repos.pypi import PyPIDownloader


_REGISTRY: dict[RepoType, type[RepoDownloader]] = {
    RepoType.PYPI: PyPIDownloader,
    RepoType.NPM: NpmDownloader,
    RepoType.MAVEN: MavenDownloader,
    RepoType.DOCKER: DockerDownloader,
}


def get_downloader(repo: RepoType, config: AppConfig) -> RepoDownloader:
    downloader_cls = _REGISTRY.get(repo)
    if not downloader_cls:
        raise ValueError(f"Unsupported repo type: {repo}")
    return downloader_cls(config)
