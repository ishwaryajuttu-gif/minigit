# Progress

## Status

Current release: **v1.1.1**. The commands `init`, `add`, `commit`, `log`, `config` and `checkout` work, and the blob hashes match `git hash-object`. The pytest suite passes on Linux, Windows and macOS in CI. See [CHANGELOG.md](../CHANGELOG.md) for what each version added.

## Next

Taken from "What I'd build next" in the [README](../README.md); none has been started.

- [ ] `status`: show staged vs. unstaged changes
- [ ] Branches, so `checkout` can move between lines of history
- [ ] A real line-by-line `diff`
- [ ] zlib compression, to match Git's on-disk format byte-for-byte

## Known limits

- There are no branches, so `HEAD` only moves forward; `checkout` never moves it back.
- Objects are stored uncompressed, so `.minigit/objects` is not byte-compatible with real Git.
