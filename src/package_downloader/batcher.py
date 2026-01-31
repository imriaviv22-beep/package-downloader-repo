from __future__ import annotations

from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path
from typing import Iterable

from rich.progress import (
    BarColumn,
    Progress,
    TaskID,
    TaskProgressColumn,
    TextColumn,
    TimeElapsedColumn,
    TimeRemainingColumn,
)

from package_downloader.config import AppConfig
from package_downloader.errors import append_error
from package_downloader.io import count_packages, iter_packages
from package_downloader.logging_utils import get_logger
from package_downloader.models import BatchResult, DownloadResult, DownloadStatus, ErrorRecord, OffsetState, PackageRecord, RepoType
from package_downloader.offsets import load_offset, save_offset
from package_downloader.repos.base import RepoDownloader

logger = get_logger(__name__)


def _run_batch(
    repo: RepoType,
    config: AppConfig,
    downloader: RepoDownloader,
    packages: list[PackageRecord],
    max_workers: int,
    fail_fast: bool,
    progress: Progress,
    task_id: TaskID,
) -> BatchResult:
    result = BatchResult()
    with ThreadPoolExecutor(max_workers=max_workers) as executor:
        future_map = {executor.submit(downloader.download, pkg): pkg for pkg in packages}
        for future in as_completed(future_map):
            pkg = future_map[future]
            try:
                download_result = future.result()
            except Exception as exc:
                logger.exception("Download error for package: %s", pkg.raw)
                result.errors += 1
                result.results.append(
                    DownloadResult(
                        package=pkg,
                        status=DownloadStatus.ERROR,
                        message=str(exc),
                    )
                )
                if fail_fast:
                    raise
            else:
                result.results.append(download_result)
                if download_result.status == DownloadStatus.ERROR:
                    logger.error(
                        "Download failed: %s",
                        download_result.message or "unknown error",
                    )
                    append_error(
                        config.paths.errors_dir,
                        ErrorRecord(
                            repo=repo,
                            message=download_result.message or "unknown error",
                            raw=download_result.package.raw,
                        ),
                    )
            progress.advance(task_id)
    return result


def run_downloads(
    repo: RepoType,
    input_file: Path,
    config: AppConfig,
    downloader: RepoDownloader,
) -> None:
    offset_state = load_offset(config.paths.offsets_dir, repo)
    offset = max(offset_state.offset, 0)
    total = count_packages(input_file, config.input)

    progress = Progress(
        TextColumn("[progress.description]{task.description}"),
        BarColumn(),
        TaskProgressColumn(),
        TimeElapsedColumn(),
        TimeRemainingColumn(),
    )

    with progress:
        task_id: TaskID = progress.add_task(f"{repo.value} downloads", total=total)
        if offset:
            progress.update(task_id, completed=min(offset, total))

        batch: list[PackageRecord] = []
        processed = 0
        for index, package in enumerate(iter_packages(input_file, config.input)):
            if index < offset:
                continue
            batch.append(package)
            if len(batch) >= config.download.batch_size:
                _run_batch(
                    repo,
                    config,
                    downloader,
                    batch,
                    max_workers=config.download.max_workers,
                    fail_fast=config.download.fail_fast,
                    progress=progress,
                    task_id=task_id,
                )
                processed += len(batch)
                offset_state = OffsetState(offset=offset + processed)
                save_offset(config.paths.offsets_dir, repo, offset_state)
                batch = []

        if batch:
            _run_batch(
                repo,
                config,
                downloader,
                batch,
                max_workers=config.download.max_workers,
                fail_fast=config.download.fail_fast,
                progress=progress,
                task_id=task_id,
            )
            processed += len(batch)
            offset_state = OffsetState(offset=offset + processed)
            save_offset(config.paths.offsets_dir, repo, offset_state)
