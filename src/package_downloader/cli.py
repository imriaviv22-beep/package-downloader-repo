from __future__ import annotations

from pathlib import Path

import typer

from package_downloader.batcher import run_downloads
from package_downloader.config import ensure_paths, load_config
from package_downloader.logging_utils import setup_logging
from package_downloader.models import RepoType
from package_downloader.offsets import reset_offset
from package_downloader.repos import get_downloader

app = typer.Typer(add_completion=False, help="Download packages from package repos.")


@app.callback()
def main() -> None:
    """Package downloader CLI."""


@app.command()
def download(
    repo: RepoType = typer.Option(..., "--repo", help="Repo type (pypi, npm, etc)."),
    file: Path = typer.Option(
        ...,
        "--file",
        "-f",
        exists=True,
        dir_okay=False,
        readable=True,
        help="Path to the input CSV file.",
    ),
    reset: bool = typer.Option(
        False,
        "--reset-offset",
        help="Reset the saved offset for this repo before downloading.",
    ),
    no_verify: bool = typer.Option(
        False,
        "--no-verify",
        help="Disable SHA256 verification before moving to output.",
    ),
    config_path: Path = typer.Option(
        Path("configs/config.yaml"),
        "--config",
        "-c",
        exists=True,
        dir_okay=False,
        readable=True,
        help="Path to config YAML.",
    ),
) -> None:
    setup_logging()
    config = load_config(config_path)
    if no_verify:
        config.download.verify_hash = False
    ensure_paths(config)
    if reset:
        reset_offset(config.paths.offsets_dir, repo)
    downloader = get_downloader(repo, config)
    run_downloads(repo, file, config, downloader)
