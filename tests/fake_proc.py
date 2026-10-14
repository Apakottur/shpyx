from __future__ import annotations

from typing import Self

import pytest_mock


class _FakeStream:
    """A stdout/stderr stand-in that hands out queued byte chunks one read at a time."""

    def __init__(self, chunks: list[bytes]) -> None:
        self.chunks = list(chunks)

    def read(self, _size: int) -> bytes:
        return self.chunks.pop(0) if self.chunks else b""


class _FakeProc:
    """A `subprocess.Popen` stand-in that emits controlled output chunks through the stream readers."""

    def __init__(self, stdout_chunks: list[bytes], stderr_chunks: list[bytes]) -> None:
        self.stdout = _FakeStream(stdout_chunks)
        self.stderr = _FakeStream(stderr_chunks)
        self.returncode = 0

    def __enter__(self) -> Self:
        return self

    def __exit__(self, *exc_info: object) -> None:
        pass


def patch_fake_proc(
    mocker: pytest_mock.MockerFixture,
    *,
    stdout_chunks: list[bytes],
    stderr_chunks: list[bytes],
) -> None:
    proc = _FakeProc(stdout_chunks, stderr_chunks or [])
    mocker.patch("shpyx._execute._Process", return_value=proc)
