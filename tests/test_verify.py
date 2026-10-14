"""
Test the command result verification.
"""

from __future__ import annotations

import signal

import pytest
import pytest_mock

import shpyx
from tests.fake_proc import patch_fake_proc
from tests.utils import SYSTEM, verify_result


def test_verify_stderr_disabled(capfd: pytest.CaptureFixture[str]) -> None:
    """Verify that contents in STDERR don't trigger an exception when `verify_stderr` is False."""
    output_by_platform = {
        "Windows": "1 \r\n",
        "Darwin": "1\n",
        "Linux": "1\n",
    }

    result = shpyx.run("echo 1 1>&2", log_output=True, verify_stderr=False)
    verify_result(result, return_code=0, stdout="", stderr=output_by_platform[SYSTEM])

    # The error message is logged in the STDOUT of the parent process.
    cap_stdout, cap_stderr = capfd.readouterr()
    assert (cap_stdout, cap_stderr) == (output_by_platform[SYSTEM], "")


def test_verify_stderr_enabled(capfd: pytest.CaptureFixture[str]) -> None:
    """Verify that contents in STDERR trigger an exception when `verify_stderr` is True."""
    output_by_platform = {
        "Windows": "1 \r\n",
        "Darwin": "1\n",
        "Linux": "1\n",
    }

    cmd = "echo 1 1>&2"
    with pytest.raises(shpyx.ShpyxVerificationError) as exc:
        shpyx.run(cmd, log_output=True, verify_stderr=True, use_signal_names=False)

    assert (
        exc.value.reason == f"The command '{cmd}' failed with return code 0.\n\n"
        f"Error output:\n{output_by_platform[SYSTEM]}\n"
        f"All output:\n{output_by_platform[SYSTEM]}"
    )

    # The error message is logged in the STDOUT of the parent process.
    cap_stdout, cap_stderr = capfd.readouterr()
    assert (cap_stdout, cap_stderr) == (output_by_platform[SYSTEM], "")


def test_verify_return_code_disabled() -> None:
    """When disabled, a non-zero return code should not trigger an error"""
    result = shpyx.run("exit 33", verify_return_code=False)
    verify_result(result, return_code=33, stdout="")


@pytest.mark.parametrize(
    ("return_code", "expected"),
    [
        # Killed by a signal.
        (-signal.SIGTERM, f"{-signal.SIGTERM} (SIGTERM)"),
        # Killed by a signal with an unknown name (not registered in the signal module).
        (-101, "-101"),
        # A regular exit code is not a signal, even if it matches a signal number.
        (signal.SIGTERM, f"{signal.SIGTERM}"),
    ],
)
def test_signal_names(mocker: pytest_mock.MockerFixture, return_code: int, expected: str) -> None:
    patch_fake_proc(mocker, stdout_chunks=[], stderr_chunks=[], returncode=return_code)
    with pytest.raises(shpyx.ShpyxVerificationError) as exc:
        shpyx.run("cmd")

    assert exc.value.reason.startswith(f"The command 'cmd' failed with return code {expected}.\n")


def test_signal_names_disabled(mocker: pytest_mock.MockerFixture) -> None:
    patch_fake_proc(mocker, stdout_chunks=[], stderr_chunks=[], returncode=-signal.SIGTERM)
    with pytest.raises(shpyx.ShpyxVerificationError) as exc:
        shpyx.Runner(use_signal_names=False).run("cmd")

    assert exc.value.reason.startswith(f"The command 'cmd' failed with return code {-signal.SIGTERM}.\n")
