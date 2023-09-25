import json
import os

import click

from devtale.aggregators.python import PythonAggregator

DEFAULT_OUTPUT_PATH = "devtale_demo/"


def document_python_file(
    source_file: str, documentation_file: str, output_path: str = DEFAULT_OUTPUT_PATH
):
    aggregator = PythonAggregator()

    with open(documentation_file, "r") as file:
        documentation = json.load(file)

    with open(source_file, "r") as file:
        code = file.read()

    documented_code = aggregator.document(code=code, documentation=documentation)

    file_name = os.path.basename(source_file)
    save_path = os.path.join(output_path, file_name)
    with open(save_path, "w") as file:
        file.write(documented_code)


@click.command()
@click.option(
    "-s",
    "--source",
    "source",
    required=True,
    help="The path to the code file",
)
@click.option(
    "-d",
    "--documentation",
    "documentation",
    required=True,
    help="The path to the documentation JSON file",
)
@click.option(
    "-o",
    "--output-path",
    "output_path",
    required=False,
    default=DEFAULT_OUTPUT_PATH,
    help="The destination folder where you want to save the documentated source",
)
def main(source: str, documentation: str, output_path: str = DEFAULT_OUTPUT_PATH):
    document_python_file(source, documentation, output_path)


if __name__ == "__main__":
    main()
