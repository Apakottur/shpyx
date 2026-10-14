"""
Test the command output decoding.
"""

from __future__ import annotations

import codecs
from typing import TYPE_CHECKING

import pytest_mock

import shpyx
from tests.fake_proc import patch_fake_proc

if TYPE_CHECKING:
    from _typeshed import ReadableBuffer


def test_output_decoding(mocker: pytest_mock.MockerFixture) -> None:
    """
    Decoding must gracefully handle two separate hazards in a single run:
      1. A valid multibyte UTF-8 character split across two output stream reads.
      2. A genuinely invalid UTF-8 byte in the output (e.g. binary/Latin-1 data).
    """
    # '€' is b"\xe2\x82\xac". Split it across two reads, then feed a lone invalid byte (b"\xff").
    patch_fake_proc(mocker, stdout_chunks=[b"\xe2\x82", b"\xac", b"\xff"], stderr_chunks=[])

    result = shpyx.run("dummy_cmd")
    assert result.stdout == "€�"
    assert result.stderr == ""


def test_output_decoding_custom_decoder(mocker: pytest_mock.MockerFixture) -> None:
    """
    Test the `decoder_factory` argument.
    """

    class _AppendADecoder(codecs.IncrementalDecoder):
        # Custom decoder adding 'a' to each byte.

        def decode(self, input: ReadableBuffer, final: bool = False) -> str:  # noqa: A002, FBT001, FBT002, ARG002
            return "".join(f"{byte:c}a" for byte in bytes(input))

    # 'hi' -> 'h','a','i','a'
    patch_fake_proc(mocker, stdout_chunks=[b"hi"], stderr_chunks=[])

    result = shpyx.run("dummy_cmd", decoder_factory=_AppendADecoder)
    assert result.stdout == "haia"
