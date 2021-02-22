# shpyX - Configurable shell command execution in Python

## Installation
Install with `pip`:
```shell
pip install shpyx
```

## Usage
TODO


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
1. Inspect the return code
2. Handle commands that are stuck (due to blocking I/O, for example)
3. Handle signals by the main Python process
4. Add formatted printing of every executed cmd and it's output
5. etc

The goal of this project is to provide a friendly API for running shell commands, with emphasis on configurability.

You might also want to check out other packages that deal with similar problems, like
[bash](https://pypi.org/project/bash/) or [invoke](https://pypi.org/project/invoke/).

## Security
One must be cautious when running shell commands from Python, as the spawned shell gains the same permissions as Python
process.

**Check an untrusted command twice before running it!**

# Contributing
TODO
## Linters and tests
TODO
