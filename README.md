# minigit

[![Tests](https://github.com/ishwaryajuttu-gif/minigit/actions/workflows/tests.yml/badge.svg)](https://github.com/ishwaryajuttu-gif/minigit/actions/workflows/tests.yml)

A from-scratch reimplementation of Git's core version-control engine — no real Git used internally. Built to understand *why* Git is designed the way it is, not just how to use it.

`minigit` supports the essential workflow — `init`, `add`, `commit`, `log` — and its file-hashing is byte-for-byte identical to real Git's, verified against `git hash-object` on every commit.

## Why this project

Most people use Git without ever thinking about what's actually happening under the hood. This project builds Git's storage engine from first principles — no shortcuts, no wrapping the real `git` binary — to answer one question: how do you turn "a folder of files that keeps changing" into a permanent, queryable history using nothing but hashing and disk I/O?

## Features

| Command | What it does |
|---|---|
| `init` | Creates a new repository (`.minigit/`) |
| `add <file>` | Stages a file for the next commit. Re-adding a changed file replaces its staged version; adding a tracked file that was deleted stages its removal |
| `commit -m "message"` | Snapshots staged files, links to the previous commit. Refuses if nothing changed since the last commit |
| `log` | Prints commit history, oldest to newest |

Like Git, commands work from any subfolder of the repository, and errors (such as a missing file or running outside a repository) print a message and exit with status 1.

## How it works

Everything in `minigit` is built on one idea: **content-addressed storage** — you hash a piece of data, and that hash becomes its permanent address. Three object types are layered on top of this single mechanism:

- **Blob** — a file's raw content. Stored as `"blob " + byte-length + "\0" + content`, then SHA-1 hashed. This exact format is what makes `minigit`'s hashes match `git hash-object` output on identical files.
- **Tree** — a snapshot of the staging area at commit time. Rather than inventing a new structure, the tree *is* the current `.minigit/index` content (a list of `filename → blob hash` pairs, one per file, sorted by path, with paths relative to the repository root), hashed and stored the same way a blob is. Because the order and line endings are fixed, the same files produce the same tree hash on every operating system.
- **Commit** — wraps a tree hash with a pointer to the parent commit and a message:
  ```
  tree <tree_hash>
  parent <parent_hash_or_empty>

  <message>
  ```
  Because each commit stores its parent's hash, an entire history can be reconstructed by walking backward from a single pointer — no need to store the full history in every commit.

`.minigit/HEAD` always holds the hash of the most recent commit. `log` starts there and walks the `parent` chain backward, collecting each commit until it reaches the first one (empty parent), then reverses the list to print oldest → newest.

## Design decisions

- **Modules are split by responsibility**: `objects.py` only knows about hashing and reading/writing raw bytes to disk — it has no concept of "commits" or "staging." `repository.py` owns the higher-level operations (`init`, `add`, `commit`, `log`) and is the only thing that understands the relationships between blobs, trees, and commits. `cli.py` is a thin layer that just parses arguments and calls into `repository.py`.
- **The tree format was deliberately *not* reinvented.** Since the staging index already describes "which files, which versions," the tree object is just that same content, hashed — one less format to invent and maintain.
- **Fixed-format fields come before the freeform message** in commit objects, so a multi-line commit message can never be mistaken for structured data during parsing.

## Usage

Requires Python 3.10 or newer. Install it with pip, which adds a `minigit` command:

```bash
git clone https://github.com/ishwaryajuttu-gif/minigit.git
cd minigit
python -m pip install .
```

Then use it in any folder:

```bash
mkdir myproject && cd myproject
minigit init
echo "hello world" > file.txt
minigit add file.txt
minigit commit -m "first commit"
minigit log
```

If you're changing minigit itself, install it with `python -m pip install -e ".[test]"` instead, so your edits take effect without reinstalling and pytest is installed too.

## Verified against real Git

```bash
minigit add file.txt
git hash-object file.txt
```
The hash written into `.minigit/index` matches `git hash-object`'s output exactly — proof that the blob format is implemented correctly, not approximated. The test suite checks this automatically against real `git hash-object` for text, binary, Unicode and Windows line-ending content.

## Testing

```bash
python -m pip install -e ".[test]"
python -m pytest
```

The tests in `tests/` cover every command, including staging and re-staging files, staged removals, subfolders, refusing empty commits, identical tree hashes regardless of the order files were added, `log` output, error messages and exit codes, and repositories created by earlier versions. GitHub Actions runs them on Linux, Windows and macOS with Python 3.10 and 3.14 for every pull request and every push to `main`.

## Project history

Built incrementally, with each stage tagged and pushed as its own milestone:

- `v0.1` — content-addressed blob storage, hash-matched against real Git
- `v0.2` — `init` + `add`, staging persisted to disk
- `v0.3` — `commit`, tree snapshots + parent-linked commit chain
- `v0.4` — `log`, backward traversal of commit history
- `v1.0` — cleanup and packaging *(current)*

## What I'd build next

- `status` — show staged vs. unstaged changes
- Branching and `checkout`
- A real line-by-line `diff`
- zlib compression, to match Git's on-disk format byte-for-byte

## Tech

Python, `hashlib` (SHA-1), no external dependencies. Tests use `pytest`.

## License

[MIT](LICENSE)