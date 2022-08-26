# `gitignorefile`

![CI](https://github.com/excitoon/gitignorefile/workflows/CI/badge.svg)
[![PyPI version](https://badge.fury.io/py/gitignorefile.svg)](https://badge.fury.io/py/gitignorefile)

A spec-compliant `.gitignore` parser for Python.

## Installation

```
pip3 install gitignorefile
```

## Usage

Suppose `/home/michael/project/.gitignore` contains the following:

```
__pycache__/
*.py[cod]
```

Then:

```
>>> from gitignorefile import parse
>>> matches = parse('/home/michael/project/.gitignore')
>>> matches('/home/michael/project/main.py')
False
>>> matches('/home/michael/project/main.pyc')
True
>>> matches('/home/michael/project/dir/main.pyc')
True
>>> matches('/home/michael/project/__pycache__')
True
```

## Credits

- https://github.com/snark/ignorance/ by Steve Cook
- https://github.com/mherrmann/gitignore_parser by Michael Herrmann
- https://github.com/bitranox/igittigitt by Robert Nowotny
