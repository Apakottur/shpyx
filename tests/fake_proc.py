import pytest_mock


class _FakeStream:
    """A stdout/stderr stand-in that hands out queued byte chunks one read at a time."""

    def __init__(self, chunks: list[bytes]) -> None:
        self.chunks = list(chunks)

    def read(self) -> bytes:
        return self.chunks.pop(0) if self.chunks else b""

    def fileno(self) -> int:
        return 0

    def close(self) -> None:
        pass


class _FakeProc:
    """A `subprocess.Popen` stand-in that emits controlled output chunks through the read loop."""

    def __init__(self, stdout_chunks: list[bytes], stderr_chunks: list[bytes]) -> None:
        self.stdout = _FakeStream(stdout_chunks)
        self.stderr = _FakeStream(stderr_chunks)
        self.returncode = 0

    def poll(self) -> int | None:
        # Keep the read loop going while either stream still has queued chunks.
        return None if (self.stdout.chunks or self.stderr.chunks) else 0

    def communicate(self) -> tuple[bytes, bytes]:
        return b"", b""


def patch_fake_proc(
    mocker: pytest_mock.MockerFixture,
    *,
    stdout_chunks: list[bytes],
    stderr_chunks: list[bytes] | None = None,
) -> None:
    proc = _FakeProc(stdout_chunks, stderr_chunks or [])
    mocker.patch("src.runner.subprocess.Popen", return_value=proc)
