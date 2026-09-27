import shutil
import subprocess

import pytest

from minigit_pkg.objects import hash_object, read_object, write_object


# Hashes printed by `git hash-object` for the same bytes
@pytest.mark.parametrize("content, expected", [
    (b"", "e69de29bb2d1d6434b8b29ae775ad8c2e48c5391"),
    (b"hello", "b6fc4c620b67d95f953a5c1c1230aaab5db5a1b0"),
    (b"hello world\n", "3b18e512dba79e4c8300dd08aeb37f8e728b8dad"),
])
def test_hash_matches_known_git_hashes(content, expected):
    assert hash_object(content) == expected


@pytest.mark.skipif(shutil.which("git") is None, reason="git is not installed")
@pytest.mark.parametrize("content", [
    b"hello world\n",
    b"windows line\r\nendings\r\n",
    bytes(range(256)),
    "unicode é中\U0001f600\n".encode(),
])
def test_hash_matches_git_hash_object(tmp_path, content):
    path = tmp_path / "file"
    path.write_bytes(content)
    # --no-filters stops git's line-ending settings from changing what it hashes
    result = subprocess.run(
        ["git", "hash-object", "--no-filters", str(path)],
        capture_output=True, text=True, check=True,
    )
    assert hash_object(content) == result.stdout.strip()


def test_read_rejects_corrupt_object(tmp_path):
    digest = write_object(b"original\n", str(tmp_path))
    (tmp_path / "objects" / digest).write_bytes(b"edited\n")
    with pytest.raises(ValueError, match="corrupt"):
        read_object(digest, str(tmp_path))


def test_write_then_read_round_trips(tmp_path):
    digest = write_object(b"some bytes\n", str(tmp_path))
    assert digest == hash_object(b"some bytes\n")
    assert (tmp_path / "objects" / digest).exists()
    assert read_object(digest, str(tmp_path)) == b"some bytes\n"
