# devtale

Generate full documentation for your code repos.

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

> Note: only Python and PHP files are supported at the moment.

devtale currently supports only OpenAI's GPT.

- Create a `.env` file in the root directory and set your `OPENAI_API_KEY` there.

- Run the following to document a file or all file in directory:

```bash
python cli.py -p [path/to/your/code] -o [path/to/docs]
```

To document an entire repository include the `-r` (recursive) flag. The program returns a JSON file per code file with the documentation data; If you want to also add the documentation inside the code file include the `-f` (fuse) flag.

### Dependency on GPT-4

We found that `GPT-3.5` can't extract code components and generate docstring in a reliable manner, while `GPT-4` can do so. Hence, devtale currently only works with `GPT-4`. Beware that the cost associated to run devtale on a large code repositive may be prohibitive. To reduce this cost, devtale uses `text-davinci-003` for generating top-level file summaries and README files.
