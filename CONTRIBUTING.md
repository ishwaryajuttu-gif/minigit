# Contributing

## Set up

Requires Python 3.10 or newer.

```bash
git clone https://github.com/ishwaryajuttu-gif/minigit.git
cd minigit
python -m pip install -e ".[test]"
```

The editable install means your edits take effect without reinstalling, and it installs pytest.

## Run the tests

```bash
python -m pytest
```

GitHub Actions runs the same tests on Linux, Windows and macOS (Python 3.10 and 3.14) for every pull request and every push to `main`. They need to pass before a merge.

## Code layout

- `minigit_pkg/objects.py` only hashes and reads/writes raw bytes on disk.
- `minigit_pkg/repository.py` owns `init`, `add`, `commit`, `log`, `checkout` and `config`.
- `minigit_pkg/cli.py` parses arguments and calls into `repository.py`.
- `tests/` has one file per area; add tests next to the code you change.

Keep that split: new behaviour goes in `repository.py`, and `cli.py` stays thin. See "Design decisions" in the [README](README.md).

## Making a change

1. Open an issue describing the change.
2. Branch from `main` (for example `feature/<name>`, `fix/<name>` or `docs/<issue>-<name>`).
3. Make one logical change per commit, with a message that says what changed.
4. Add or update tests, and update `CHANGELOG.md` under `## Unreleased`.
5. Open a pull request into `main`.

## Releases

Versions follow [Semantic Versioning](https://semver.org/). To release, set `version` in `pyproject.toml`, move the `## Unreleased` entries in `CHANGELOG.md` under the new version, and push an annotated `vX.Y.Z` tag.
