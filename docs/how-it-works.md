# How it works

## Implementation details

shpyx is a wrapper around the excellent [subprocess](https://docs.python.org/3/library/subprocess.html) module, aiming
to concentrate all the different API functions (`Popen`/`communicate`/`poll`/`wait`) into a single function - `shpyx.run`.

The output streams (stdout and stderr) are each read by a dedicated thread, and decoded incrementally (UTF-8 by default,
see `decoder_factory`, typed as [`shpyx.DecoderFactory`](reference/api.md#shpyx.DecoderFactory)) as the output arrives.
This allows logging the live output, keeps the order of the combined output (`all_output`), and avoids deadlocks when a
command fills one pipe while shpyx waits on the other.

A `KeyboardInterrupt` (CTRL-C), or any other exception raised during the run, stops it promptly and kills the subprocess
along with all of its descendants (e.g. every command of a shell pipeline).

shpyx supports Linux, macOS and Windows. Other systems (e.g. FreeBSD) are treated as generic POSIX systems: `run` works
as usual, but `unix_raw` raises [`ShpyxOSNotSupportedError`](reference/api.md#shpyx.ShpyxOSNotSupportedError).

## Security

Never pass untrusted input to `shpyx.run`, whether the command is a string or a list. The subprocess has the permissions
of the main Python process.

When the command is a string, `subprocess.Popen` is called with `shell=True` (to support shell logic like bash piping).
An actual system shell is created, so shell syntax in the input (`;`, `|`, `$(...)`, ...) runs arbitrary commands.

When the command is a list, no shell is involved (with `unix_raw`, the arguments are shell-quoted before being passed to
`script`). This prevents shell injection, but not other attacks: untrusted input can still pick the program to run, or
inject options that make it run arbitrary code (e.g. `--upload-pack` for `git`).

For more info, see [security considerations](https://docs.python.org/3/library/subprocess.html#security-considerations).

## Alternatives

Relevant Python libraries:

- [subprocess](https://docs.python.org/3/library/subprocess.html)
- [shlex](https://docs.python.org/3/library/shlex.html)

Other 3rd-party libraries for running shell commands in Python:

- [sarge](https://github.com/vsajip/sarge)
- [sh](https://github.com/amoffat/sh)
- [invoke](https://github.com/pyinvoke/invoke)
