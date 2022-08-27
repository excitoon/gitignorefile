# `gitignorefile`

![CI](https://github.com/excitoon/gitignorefile/workflows/CI/badge.svg)
[![PyPI version](https://badge.fury.io/py/gitignorefile.svg)](https://badge.fury.io/py/gitignorefile)

A spec-compliant `.gitignore` parser for Python.

## Installation

```
pip3 install gitignorefile
```

## Usage

### `gitignorefile.parse()`

Parse single `.gitignore` file. Suppose `/home/michael/project/.gitignore` contains the following:

```
__pycache__/
*.py[cod]
```

Then:

```python3
import gitignorefile

matches = gitignorefile.parse("/home/michael/project/.gitignore")
matches("/home/michael/project/main.py") # False
matches("/home/michael/project/main.pyc") # True
matches("/home/michael/project/dir/main.pyc") # True
matches("/home/michael/project/__pycache__") # True
```

### `gitignorefile.ignore()`

`shutil.copytree()` ignore function which checks if file is ignored by any `.gitignore` in the directory tree.

Example:

```python3
import shutil
import gitignorefile

shutil.copytree("/source", "/destination", ignore=gitignorefile.ignore())
```

### `gitignorefile.ignored()`

Checks if file is ignored by any `.gitignore` in the directory tree.

```python3
import gitignorefile

gitignorefile.ignored("/home/michael/project/main.py") # False
```

### `gitignorefile.Cache`

Caches `.gitignore` rules discovered in the directory tree.

```python3
import gitignorefile

matches = gitignorefile.Cache()
matches("/home/michael/project/main.py") # False
matches("/home/michael/project/main.pyc") # True
matches("/home/michael/project/dir/main.pyc") # True
matches("/home/michael/project/__pycache__") # True
```

## Credits

- https://github.com/snark/ignorance/ by Steve Cook
- https://github.com/mherrmann/gitignore_parser by Michael Herrmann
- https://github.com/bitranox/igittigitt by Robert Nowotny
