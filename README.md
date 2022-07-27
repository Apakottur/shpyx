# ShpyX

[![PyPI](https://img.shields.io/pypi/v/shpyx?logo=pypi&logoColor=white&style=for-the-badge)](https://pypi.org/project/shpyx/)
[![Downloads](https://img.shields.io/pypi/dm/shpyx?logo=pypi&logoColor=white&style=for-the-badge)](https://pypi.org/project/shpyx/)
[![Python](https://img.shields.io/pypi/pyversions/shpyx?logo=pypi&logoColor=white&style=for-the-badge)](https://pypi.org/project/shpyx/)

**shpyx** is a simple, clean and modern library for executing shell commands in Python.

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

## Usage examples

Run a command:

```python
>>> import shpyx
>>> shpyx.run("echo 'Hello world'")
ShellCmdResult(cmd="echo 'Hello world'", stdout='Hello world\n', stderr='', all_output='Hello world\n', return_code=0)
```

Run a command and print live output:

```python
>>> shpyx.run("echo 'Hello world'", log_output=True)
Hello world
ShellCmdResult(cmd="echo 'Hello world'", stdout='Hello world\n', stderr='', all_output='Hello world\n', return_code=0)
```

## Motivation

I've been writing automation scripts for many years, mostly in Bash.

I love Bash scripts, but in my opinion they become extremely hard to read, maintain and reason about once they grow
too big. I find Python to be a much more pleasant tool for "gluing" together pieces of a project and external Bash
commands.

Here are things that one might find nicer to do in Python than in bare Bash:

1. String/list manipulation
2. Error handling
3. Flow control (loops and conditions)
4. Output manipulation

The Python standard library provides the excellent [subprocess module](https://docs.python.org/3/library/subprocess.html)
, which can be used to run bash commands through Python:

```python
import subprocess

cmd = "ls -l"
p = subprocess.Popen([cmd], shell=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
cmd_stdout, cmd_stderr = p.communicate()
```

It's great for a very simple, single command, but becomes a bit tedious to use in more complex scenarios, when
one or more of the following is needed:

- Run many commands
- Inspect the return code
- See live command output (while it is being run)
- Gracefully handle commands that are stuck (due to blocking I/O, for example)
- Add formatted printing of every executed command and/or its output

This often leads to each project having their own "run" function, which encapsulates `subprocess.Popen`.

This library aims to provide a simple, typed and configurable `run` function, dealing with all the caveats of using
`subprocess.Popen`.

## Security

Essentially, `shpyx` is a wrapper around `subprocess.Popen`.
The call to `subprocess.Popen` uses `shell=True` which means that an actual system shell is being
created, and the subprocess has the permissions of the main Python process.

It is therefore not recommended running untrusted commands via `shpyX`.

For more info, see [security considerations](https://docs.python.org/3/library/subprocess.html#security-considerations).
