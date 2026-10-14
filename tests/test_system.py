"""
Test the platform system specific code.
"""

from __future__ import annotations

import sys

import pytest
import pytest_mock

import shpyx
from shpyx._system import System, get_system, get_unix_raw_cmd
from tests.utils import SEP, verify_result


@pytest.mark.parametrize(
    ("system", "expected"),
    [
        (System.LINUX, "script --return --quiet --command 'echo 1' /dev/null"),
        (System.DARWIN, "script -q /dev/null /bin/sh -c 'echo 1'"),
    ],
)
def test_unix_raw_cmd(mocker: pytest_mock.MockerFixture, system: System, expected: str) -> None:
    """Test the `script` command built for `unix_raw`, on every supported platform."""
    mocker.patch("shpyx._system.SYSTEM", system)
    assert get_unix_raw_cmd("echo 1") == expected


def test_unix_raw_windows(mocker: pytest_mock.MockerFixture) -> None:
    """`unix_raw` raises on Windows, which has no `script` utility."""
    mocker.patch("shpyx._system.SYSTEM", System.WINDOWS)
    mocker.patch("shpyx._system.platform.system", return_value="Windows")
    with pytest.raises(shpyx.ShpyxOSNotSupportedError, match="Unsupported system: Windows"):
        shpyx.run("echo 1", unix_raw=True)


def test_unsupported_system(mocker: pytest_mock.MockerFixture) -> None:
    """A system without specific support is detected as such, but plain commands still work on it."""
    mocker.patch("shpyx._system.platform.system", return_value="FreeBSD")
    assert get_system() is None

    mocker.patch("shpyx._system.SYSTEM", None)
    result = shpyx.run([sys.executable, "-c", "print(1)"])
    verify_result(result, stdout=f"1{SEP}")

    # Only `unix_raw` is unavailable, and only when used.
    with pytest.raises(shpyx.ShpyxOSNotSupportedError, match="Unsupported system: FreeBSD"):
        shpyx.run("echo 1", unix_raw=True)
