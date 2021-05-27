# shpyX - Configurable shell command execution in Python

shpyX is a library which aims to simplify shell execution in Python by providing an API for easily interacting
with the shell return code, outputs (i.e. stdio/stderr) and subprocess.

For example, suppose we want to run the following command:

```shell
cmd arg_1 arg_2
```

Suppose we also want to suppress all outputs if the command returns `0` and to raise a **Python** exception if the
return code is not `0`.
With shpyX, we can do all that with:

```python
import shpyx
shpyx.run("cmd arg_1 arg_2")
```

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

Get live output during a long command:

```
>>> result = shpyx.run("echo 'Hello'; sleep 10000", log_output=True)
Hello
```

## Motivation

I've been writing automation scripts for many years, mostly in Bash and Windows shell.

I love writing shell scripts, but in my opinion they become really hard to maintain once they become too big. I find
Python a much more pleasant environment for doing the following things than a bare shell:

1. String/list manipulation
2. Error handling
3. Flow control (loops and conditions)
4. Output piping and manipulation

A few years ago I found out that the Python standard library provides a simple way of doing so
via the `subprocess` module:

```python
import subprocess

cmd = "ls -l"
p = subprocess.Popen([cmd], shell=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
cmd_stdout, cmd_stderr = p.communicate()
```

I started with a simple function, which was used by my team, and over time encountered more and more requirements like:

- Inspect the return code
- See live command output (while it is being run)
- Gracefully handle commands that are stuck (due to blocking I/O, for example)
- Add formatted printing of every executed command and/or its output

The function gradually turned into a module which eventually turned into `shpyX`.

The goal of this project is to provide a friendly API for running shell commands, with emphasis on simplicity
and configurability.

## Security

The call to `subprocess.Popen` in this library uses `shell=True` which means that an actual system shell is being
created, and the subprocess has the permissions of the main Python process.

It is therefore not recommended running untrusted commands via `shpyX`.

For more info, see [security considerations](https://docs.python.org/3/library/subprocess.html#security-considerations).

## Contributing

Running the linters:

```shell
docker-compose up --build linters
```
