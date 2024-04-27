# Image Organizer

`pyimorg` is a command-line tool for organizing images.

## Installation

### Requirements

- [Python](https://www.python.org/) 3.8+

### Procedure

1. Run `python -m pip install git+https://github.com/DarkLight1337/pyimorg.git` to install the package from this repository.

## Usage

To avoid corrupting existing images, `pyimorg` never modifies the input directories; instead, it outputs the results in a new directory, copying the input images as necessary.

### Compare images

#### Syntax

```
pyimorg diff <src1_dir> <src2_dir> <out_dir>
```

#### Options

- `-h <hasher>` to specify the hash function for comparing image contents (`sha256` or `sha512`).
- `-t <num_threads>` to enable parallel computing via multithreading.

### Group by timestamp

#### Syntax

```
pyimorg groupby <src_dir> <out_dir>
```

#### Options

- `-g <group>` to specify the type of group (`year`, `month`, or `day`).
- `-t <num_threads>` to enable parallel computing via multithreading.

## Development

### Requirements

- [Python](https://www.python.org/) 3.8+
- [Poetry](https://python-poetry.org/) 1.4+

### Setup

1. Clone this repository to your machine.
2. Run `poetry lock --no-update && poetry install --with dev` to setup the Python enviroment.

### Lint

1. [Setup](#setup) the development environment.
2. Run `poetry run deptry . && poetry run ruff check . && poetry run pyright .` to lint the code.

### Test

1. [Setup](#setup) the development environment.
2. Run `poetry run -- pytest && coverage report && coverage html -d coverage --show-contexts` to test the code and output the coverage report.
