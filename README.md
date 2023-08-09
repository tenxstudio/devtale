# devtale

Automatically document repositories

## Installation

Create and enter to a conda env:

```bash
conda create -n devtale python=3.11 -y
conda activate devtale
```

Install requirements

```bash
pip install -r requirements.txt
```

## Usage

Currently we only support Python and PHP files.

To document a file

```bash
python cli.py -m -f -p [path/to/your/code/file] -o [path/to/save/output/docs]
```

To document files inside a folder

```bash
python cli.py -m -d -p [path/to/your/folder/] -o [path/to/save/output/docs]
```

To document a full repository

```bash
python cli.py -m -r -p [path/to/your/repository/] -o [path/to/save/output/docs]
```

Output is a JSON or set of JSON files with the same name as the source files.
