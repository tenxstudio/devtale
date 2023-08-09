# devtale

Generate documentation for entire repositories, single folders, and/or code files.

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

1- Create a `.env` file in the root directory and set your `OPENAI_API_KEY` there.\n

2- Execute the following command to document a folder or a file:

```bash
python cli.py -p [path/to/your/code/file/or/folder] -o [path/to/save/output/docs]
```

To document the code for an entire repository, include the `-r` flag.

> Note: only Python and PHP files are supported at the moment.

## GPT Consumption

We found that `gpt-3.5*` encounters limitations when tasked with extracting specific code components. This constraint compelled us to upgrade the model to `gpt-4` for the purpose of extracting code components and generating docstrings.

Using `gpt-4` for extraction is essential. As for generating docstrings, you can select another model and employ the `GPT-3.5*` version to decrease costs. However, please be cautious, as altering the version for docstring generation might lead to corrupted outcomes.

For generating top-level file summaries, folder-level READMEs, and the main README, we are utilizing the `text-davinci-003` model.
