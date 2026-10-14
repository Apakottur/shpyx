from __future__ import annotations

import codecs
from collections.abc import Callable
from typing import IO, TYPE_CHECKING

if TYPE_CHECKING:
    import queue

# A callable that returns a fresh incremental decoder for a single command output stream.
_DecoderFactory = Callable[[], codecs.IncrementalDecoder]


def _default_decoder_factory() -> codecs.IncrementalDecoder:
    """
    Get the default output decoder factory:
        1. Decodes incrementally, so a valid multibyte character split across two reads (which are not aligned to
        character boundaries) is held until the next read completes it, rather than raising.
        2. Uses UTF-8.
        3. Replaces genuinely invalid bytes (e.g. binary data) with the Unicode replacement character instead of raising.
    """
    return codecs.getincrementaldecoder("utf-8")(errors="replace")


def _read_stream(stream: IO[bytes], stream_id: int, chunks: queue.SimpleQueue[tuple[int, bytes]]) -> None:
    """
    Read an output stream until EOF, pushing each chunk to a shared queue, followed by an empty chunk.
    """
    try:
        while chunk := stream.read(64 * 1024):
            chunks.put((stream_id, chunk))
    finally:
        chunks.put((stream_id, b""))


class _OutputStream:
    """
    A single output stream of a command (stdout or stderr), decoded and collected in parts while the command runs.
    The parts are joined once the command exits (for performance).
    """

    def __init__(self, decoder: codecs.IncrementalDecoder, all_output: list[str]) -> None:
        """
        Args:
            decoder: The stream decoder (decoders are stateful, so each stream must have its own).
            all_output: The parts of all the output streams, shared by all of them to keep the arrival order.
        """
        self._decoder = decoder
        self._parts: list[str] = []
        self._all_output = all_output

    def add(self, data: bytes, *, final: bool) -> str:
        """
        Decode a partial output chunk and collect it.

        Args:
            data: The partial output to add.
            final: Whether this is the last chunk, flushing any trailing incomplete bytes.

        Returns:
            The decoded output (possibly empty).
        """
        decoded_data = self._decoder.decode(data, final)
        self._parts.append(decoded_data)
        self._all_output.append(decoded_data)
        return decoded_data

    def text(self) -> str:
        """
        Concatenate all the collected parts.
        """
        return "".join(self._parts)
