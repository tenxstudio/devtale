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

### Terminal

> Note: currently, devtale only supports Python and PHP languages and GPT-4 as LLM.

- Create a `.env` file in the root directory and set your `OPENAI_API_KEY` there.

- Run the following to document a file or all file in directory:

```bash
python cli.py -p [path/to/your/code] -o [path/to/docs]
```

To document an entire repository include the `-r` (recursive) flag. The program returns a JSON file per code file with the documentation data; If you want to also add the documentation inside a copy of code file, then please include the `-f` (fuse) flag.

### Workflow

> Note: You must check the box _"Allow GitHub Actions to create and approve pull requests"_ in your repository's setting -> actions for this to work.

- In the repository setting -> Secrets and Variables -> Actions -> Create `OPENAI_API_KEY` repository secret

- Add the following step in your workflow

```bash
- name: Document
  uses: mystral-ai/devtale@v0.1
  with:
    OPENAI_API_KEY: ${{ secrets.OPENAI_API_KEY }}
    path: ${{ github.workspace }}
    recursive: true
    target_branch: main
```

The `recursive` option allows you to document the entire repository. Alternatively, you can specify a specific path to document a single file or folder and set `recursive` to `false`. The workflow action will automatically create the `devtale/documentation` branch and push a new pull request for your review towards the `target_branch`, including the added documentation.

### Dependency on GPT-4

We found that `GPT-3.5` can't extract code components and generate docstring in a reliable manner, while `GPT-4` can do so. Hence, devtale currently only works with `GPT-4`. Beware that the cost associated to run devtale on a large code repositive may be prohibitive. To reduce this cost, devtale uses `text-davinci-003` for generating top-level file summaries and README files.
