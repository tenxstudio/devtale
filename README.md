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

```bash
python cli.py -f [path/to/your/code/file]
```

Result is JSON file saved in `devtale_demo` with the same name as the input file.
