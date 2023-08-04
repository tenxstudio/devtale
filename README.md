# dev-tales

Automatically document repositories

## Installation

Create and enter to a conda env:

```bash
conda create -n dev-tales python=3.11 -y
conda activate dev-tales
```

Install requirements

```bash
pip install -r requirements.txt
```

## Usage

```bash
python cli.py -f [path/to/your/code/file]
```

Result is JSON file saved in `dev_tales_demo` with the same name as the input file.
