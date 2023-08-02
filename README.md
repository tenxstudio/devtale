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

The result will be saved with the same name as the original file in the default folder `dev_tales_demo` unless you specify a different folder with the flag `-o [path/to/your/output/folder]`
