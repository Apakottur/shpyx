<p align="center">
  <img src="https://github.com/Apakottur/shpyx/blob/main/shpyx.png?raw=true" />
</p>

[![PyPI](https://img.shields.io/pypi/v/shpyx?logo=pypi&logoColor=white&style=for-the-badge)](https://pypi.org/project/shpyx/)
[![Downloads](https://img.shields.io/pypi/dm/shpyx?logo=pypi&logoColor=white&style=for-the-badge)](https://pypi.org/project/shpyx/)
[![Python](https://img.shields.io/pypi/pyversions/shpyx?logo=pypi&logoColor=white&style=for-the-badge)](https://pypi.org/project/shpyx/)

**shpyx** is a simple, lightweight and typed library for running shell commands in Python.

Use `shpyx.run` to run a shell command in a subprocess:

```python
>>> import shpyx
>>> shpyx.run("echo 1").return_code
0
>>> shpyx.run("echo 1").stdout
'1\n'
>>> shpyx.run("echo 1").stderr
''
>>> shpyx.run("echo 1")
ShellCmdResult(cmd='echo 1', stdout='1\n', stderr='', all_output='1\n', return_code=0)
```

## Installation

Install with `pip`:

```shell
pip install shpyx
```

## How Tos

### Run a command

In string format:

```python
>>> shpyx.run("echo 1")
ShellCmdResult(cmd='echo 1', stdout='1\n', stderr='', all_output='1\n', return_code=0)
```

In list format:

```python
>>> shpyx.run(["echo", ["1"])
ShellCmdResult(cmd='echo 1', stdout='1\n', stderr='', all_output='1\n', return_code=0)
```

### Run a command and print live output

```python
>>> shpyx.run("echo 1", log_output=True)
1
ShellCmdResult(cmd='echo 1', stdout='1\n', stderr='', all_output='1\n', return_code=0)
```

### Run a command with shell specific logic

When the argument to `run` is a string, an actual shell is created in the subprocess and shell logic can be used.
For example, the pipe operator can be used in bash/sh:

```python
>>> shpyx.run("seq 1 5 | grep '2'")
ShellCmdResult(cmd="seq 1 5 | grep '2'", stdout='2\n', stderr='', all_output='2\n', return_code=0)
```

### Create a custom runner

Use a custom runner to override the execution defaults, and not have to pass them to every call.

For example, we can change the default value of `log_cmd`, so that all commands are logged:

```python
>>> shpyx.run("echo 1")
ShellCmdResult(cmd='echo 1', stdout='1\n', stderr='', all_output='1\n', return_code=0)

>>> shpyx.run("echo 1", log_cmd=True)
Running: echo 1
ShellCmdResult(cmd='echo 1', stdout='1\n', stderr='', all_output='1\n', return_code=0)

>>> runner = shpyx.Runner(log_cmd=True)
>>> runner.run("echo 1")
Running: echo 1
ShellCmdResult(cmd='echo 1', stdout='1\n', stderr='', all_output='1\n', return_code=0)
```

### Propagating terminal control sequences

Note: as of now this is only supported for Unix environments.

Some commands, like `psql`, might output special characters used for terminal management like cursor movement and
colors. For example, the `psql` command is used to start an interactive shell against a Postgres DB:

```python
shpyx.run(f"psql -h {host} -p {port} -U {user} -d {database}", log_output=True)
```

However, the above call will not work as good as running `psql` directly, due to terminal control sequences not being
properly propagated. To make it work well, we need to use the [script](https://man7.org/linux/man-pages/man1/script.1.html)
utility which will properly propagate all control sequences:

```python
# Linux:
shpyx.run(f"script -q -c 'psql -h {host} -p {port} -U {user} -d {database}'", log_output=True)
# MacOS:
shpyx.run(f"script -q psql -h {host} -p {port} -U {user} -d {database}", log_output=True)

```

shpyx provides a keyword argument that does this wrapping automatically, `unix_raw`:

```python
shpyx.run(f"psql -h {host} -p {port} -U {user} -d {database}", log_output=True, unix_raw=True)
```

The flag is disabled by default, and should only be used for interactive commands like `psql`.

## API Reference

The following arguments are supported by `Runner`:

| Name                 | Description                                                                | Default |
| -------------------- | -------------------------------------------------------------------------- | ------- |
| `log_cmd`            | Log the executed command.                                                  | `False` |
| `log_output`         | Log the live output of the command (while it is being executed).           | `False` |
| `verify_return_code` | Raise an exception if the shell return code of the command is not `0`.     | `True`  |
| `verify_stderr`      | Raise an exception if anything was written to stderr during the execution. | `False` |
| `use_signal_names`   | Log the name of the signal corresponding to a non-zero error code.         | `True`  |

The following arguments are supported by `run`:

| Name                 | Description                                                                | Default                  |
| -------------------- | -------------------------------------------------------------------------- | ------------------------ |
| `log_cmd`            | Log the executed command.                                                  | `Runner default`         |
| `log_output`         | Log the live output of the command (while it is being executed).           | `Runner default`         |
| `verify_return_code` | Raise an exception if the shell return code of the command is not `0`.     | `Runner default`         |
| `verify_stderr`      | Raise an exception if anything was written to stderr during the execution. | `Runner default`         |
| `use_signal_names`   | Log the name of the signal corresponding to a non-zero error code.         | `Runner default`         |
| `env`                | Environment variables to set during the execution of the command.          | `Same as parent process` |
| `exec_dir`           | Custom path to execute the command in (defaults to current directory).     | `Same as parent process` |
| `unix_raw`           | (UNIX ONLY) Whether to use the `script` Unix utility to run the command.   | `False`                  |

## Implementation details

`shpyx` is a wrapper around the excellent [subprocess](https://docs.python.org/3/library/subprocess.html) module, aiming
to concentrate all the different API functions (`Popen`/`communicate`/`poll`/`wait`) into a single function - `shpyx.run`.

While the core API logic is fully supported on both Unix and Windows systems, there is some OS specific code for minor quality-of-life
improvements.
For example, on non Windows systems, [fcntl](https://docs.python.org/3/library/fcntl.html) is used to configure the subprocess to
always be incorruptible (which means one can CTRL-C out of any command).

## Security

The call to `subprocess.Popen` uses `shell=True` when the input to `run` is a string (to support shell logic like bash piping).
This means that an actual system shell is being created, and the subprocess has the permissions of the main Python process.

It is therefore recommended not pass any untrusted input to `shpyx.run`.

For more info, see [security considerations](https://docs.python.org/3/library/subprocess.html#security-considerations).

## Useful links

Relevant Python libraries:

- [subprocess](https://docs.python.org/3/library/subprocess.html)
- [shlex](https://docs.python.org/3/library/shlex.html)

Other user libraries for running shell commands in Python:

- [sarge](https://github.com/vsajip/sarge)
- [sh](https://github.com/amoffat/sh)

## Contributing

To contribute simply open a PR with your changes.

Tests, linters and type checks are run in CI through GitHub Actions.

### Running checks locally

To run checks locally, start by installing all the development dependencies:

```shell
poetry install
```

To run the linters use `pre-commit`:

```shell
pre-commit run -a
```

To run the unit tests use `pytest`:

```shell
pytest -c tests/pytest.ini tests
```

To run type checks use `mypy`:

```shell
mypy --config-file shpyx/mypy.ini shpyx tests
```

To trigger a deployment of a new version upon merge, bump the version number in `pyproject.toml`.
