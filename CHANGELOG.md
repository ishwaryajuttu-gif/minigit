# Changelog

All notable changes to minigit are recorded here. The format follows
[Keep a Changelog](https://keepachangelog.com/en/1.1.0/), and versions follow
[Semantic Versioning](https://semver.org/) from v1.0.1 onward.

## Unreleased

### Added
- `CHANGELOG.md`, `CONTRIBUTING.md` and `docs/PROGRESS.md`.

### Changed
- `.gitignore` also ignores `.env`, `.minigit/`, `.vscode/` and `.idea/`.

## [1.1.1] - 2026-09-27

### Added
- `--help` for every command.
- `python -m minigit_pkg` works the same as the `minigit` command.

## [1.1.0] - 2026-09-27

### Added
- `checkout` restores files from any commit and stages them.
- Commits record the author and date, and `log` shows them.
- `config` sets `user.name` and `user.email`, per repository or with `--global`.

## [1.0.1] - 2026-09-27

### Fixed
- Unicode file names in the index.
- Adding several files at once.
- File names that differ only in case.
- Corrupt objects are reported instead of being used.

## [1.0.0] - 2026-09-27

Tagged `v1.0`.

### Added
- pytest suite, run on Linux, Windows and macOS by GitHub Actions.
- pip packaging with a `minigit` command.
- MIT `LICENSE`.

### Fixed
- Duplicate index entries, crashes, empty commits and tree hashes that differed between operating systems.

## [0.4.0] - 2026-08-12

Tagged `v0.4`.

### Added
- `log` walks the commit history backward through parent pointers and prints it oldest to newest.

## [0.3.0] - 2026-08-12

Tagged `v0.3`.

### Added
- `commit` snapshots the staged files as a tree object, links it to the parent commit and updates `HEAD`.

## [0.2.0] - 2026-08-12

Tagged `v0.2`.

### Added
- `init` creates `.minigit/objects` and the index.
- `add` hashes and stages files; staging persists in `.minigit/index`.

## [0.1.0] - 2026-07-22

Tagged `v0.1`.

### Added
- Content-addressed blob storage, hash-matched against `git hash-object`.

[Unreleased]: https://github.com/ishwaryajuttu-gif/minigit/compare/v1.1.1...HEAD
[1.1.1]: https://github.com/ishwaryajuttu-gif/minigit/compare/v1.1.0...v1.1.1
[1.1.0]: https://github.com/ishwaryajuttu-gif/minigit/compare/v1.0.1...v1.1.0
[1.0.1]: https://github.com/ishwaryajuttu-gif/minigit/compare/v1.0...v1.0.1
[1.0.0]: https://github.com/ishwaryajuttu-gif/minigit/releases/tag/v1.0
[0.4.0]: https://github.com/ishwaryajuttu-gif/minigit/releases/tag/v0.4
[0.3.0]: https://github.com/ishwaryajuttu-gif/minigit/releases/tag/v0.3
[0.2.0]: https://github.com/ishwaryajuttu-gif/minigit/releases/tag/v0.2
[0.1.0]: https://github.com/ishwaryajuttu-gif/minigit/releases/tag/v0.1
