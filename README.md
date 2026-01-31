# Package Downloader

CLI for downloading package records from multiple repositories (PyPI, npm, Maven, Docker, etc). The harness (batching, concurrency, offsets, config, CLI) is implemented; some repos may still have stubbed logic.

## Requirements

- Python 3.12+
- uv
- Docker CLI (only for `docker` repo downloads)

## Setup

```bash
uv venv
uv pip install -e .
```

## Configuration

Edit `configs/config.yaml`.

| Key                    | Type         | Default        | Description                                   |
| ---------------------- | ------------ | -------------- | --------------------------------------------- |
| `paths.offsets_dir`    | string       | `data/offsets` | Per-repo offset files for resume.             |
| `paths.output_dir`     | string       | `data/output`  | Final download output root.                   |
| `paths.temp_dir`       | string       | `data/temp`    | Temporary downloads before verification/move. |
| `paths.errors_dir`     | string       | `data/errors`  | Per-repo JSONL error logs.                    |
| `download.batch_size`  | int          | `50`           | Number of rows per batch.                     |
| `download.max_workers` | int          | `8`            | Thread pool size per batch.                   |
| `download.fail_fast`   | bool         | `false`        | Stop on first error in a batch.               |
| `download.verify_hash` | bool         | `true`         | Verify SHA256 before moving to output.        |
| `input.has_header`     | bool         | `true`         | CSV includes a header row.                    |
| `pypi.cache_size`      | int          | `256`          | LRU size for PyPI JSON cache.                 |
| `maven.registries`     | list[string] | _(see config)_ | Ordered Maven registries to try.              |

## Input Files

- Full inputs: `data/input/full`
- Samples: `data/input/sample`

Each CSV row is preserved as a raw record and passed to the repo downloader.

## Usage

Run a download:

```bash
package-downloader download --repo pypi --file data/input/sample/pypi_2p.csv
```

Use a custom config:

```bash
package-downloader download --repo npm --file data/input/sample/npm_2p.csv --config configs/config.yaml
```

Disable hash verification:

```bash
package-downloader download --repo pypi --file data/input/sample/pypi_2p.csv --no-verify
```

Reset offset and restart:

```bash
package-downloader download --repo maven --file data/input/sample/maven_2p.csv --reset-offset
```

Example:

```bash
package-downloader download --repo pypi --file data/input/sample/pypi_2p.csv
package-downloader download --repo maven --file data/input/sample/maven_2p.csv
package-downloader download --repo npm --file data/input/sample/npm_2p.csv
package-downloader download --repo docker --file data/input/sample/docker_2p.csv --no-verify
```

## Output

- Downloads: `data/output/<repo>/...`
- Temp files: `data/temp/<repo>/...`
- Error logs: `data/errors/<repo>.errors.jsonl`
- Offsets: `data/offsets/<repo>.offset.json`

## Repo-Specific Notes

### PyPI

Uses the JSON API `https://pypi.org/pypi/<name>/json` and finds the release file by filename.

### npm

Downloads `https://registry.npmjs.org/<npm_name>/-/<npm_name_base>-<npm_version>.tgz`. Scoped packages use `npm_name_base` without the scope.

### Maven

Downloads from the first registry that contains the file. The relative path is `<node_path>/<node_name>`, and the directory structure is preserved in output.

### Docker

Uses the Docker CLI to `pull` and `save` as a tarball at `data/output/docker/<docker_repo_name>/<docker_manifest>.tar`.
