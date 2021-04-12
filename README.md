# shpyX - Configurable shell command execution in Python

## Installation

Install with `pip`:

```shell
pip install shpyx
```

## Usage

Run a command:

```
>>> import shpyx
>>> shpyx.run("echo 'Hello world'")
ShellCmdResult(cmd="echo 'Hello world'", stdout='Hello world\n', stderr='', all_output='Hello world\n', return_code=0)
```

Run a command and print the output:

```
>>> shpyx.run("echo 'Hello world'", log_output=True)
Hello world
ShellCmdResult(cmd="echo 'Hello world'", stdout='Hello world\n', stderr='', all_output='Hello world\n', return_code=0)
```

Get partial output during long commands:

```
>>> result = shpyx.run("echo 'Hello'; sleep 10000", log_output=True)
Hello
```

## Motivation

Running shell commands in Python is often useful when the user is interested in combining shell and Python logic, or
managing the outcome of shell commands in Python.

The Python standard library provides a simple way of doing so via the `subprocess` module:

```python
import subprocess

cmd = "ls -l"
p = subprocess.Popen([cmd], shell=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
cmd_stdout, cmd_stderr = p.communicate()
```

While this is sufficient for many cases, we might also want to:

- Inspect the return code
- See live command output (while it is being run)
- Gracefully handle commands that are stuck (due to blocking I/O, for example)
- Add formatted printing of every executed command and/or its output

The goal of this project is to provide a friendly API for running shell commands, with emphasis on configurability.

You might also want to check out other packages that deal with similar problems, like
[bash](https://pypi.org/project/bash/) or [invoke](https://pypi.org/project/invoke/).

## Security

The call to `subprocess.Popen` in this library uses `shell=True` which means that an actual system shell is being
created. Untrusted commands should be checked twice before being run.

For more info, see [security considerations](https://docs.python.org/3/library/subprocess.html#security-considerations).

## Contributing

Running the linters:

```shell
docker-compose up --build linters
```
