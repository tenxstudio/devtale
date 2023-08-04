import getpass
import json
import logging
import os
from pprint import pprint

import click

from dev_tales.utils import fuse_tales, get_tale_summary, get_unit_tale, split

DEFAULT_OUTPUT_PATH = "dev_tales_demo/"
DEFAULT_MODEL_NAME = "gpt-3.5-turbo"

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


def document_file(
    file_path: str,
    output_path: str = DEFAULT_OUTPUT_PATH,
    model_name: str = DEFAULT_MODEL_NAME,
) -> None:
    if not os.path.exists(output_path):
        os.makedirs(output_path)

    logger.info("read dev draft")
    file_name = os.path.basename(file_path)
    with open(file_path, "r") as file:
        code = file.read()

    logger.info("split dev draft ideas")
    docs = split(code, chunk_size=3000)

    logger.info("create tale sections")
    tales_list = []
    for idx, doc in enumerate(docs):
        tale = get_unit_tale(doc, model_name=model_name)
        tales_list.append(tale)
        logger.info(f"tale section {str(idx+1)}/{len(docs)} done.")

    logger.info("write dev tale")
    file_tales = fuse_tales(tales_list)

    logger.info("add dev tale summary")
    final_tale = get_tale_summary(file_tales)

    save_path = os.path.join(output_path, f"{file_name}.json")
    logger.info(f"save dev tale in: {file_path}")
    with open(save_path, "w") as json_file:
        json.dump(final_tale, json_file, indent=2)

    logger.info("AI-Generate Dev Tale:")
    pprint(final_tale)

    # logger.info("add documentation to the code")
    # documented_code = add_tales(file_tales, code)

    # save_path = os.path.join(output_path, file_name)
    # logger.info(f"save documented file in {save_path}")
    # with open(save_path, "w") as file:
    #    file.write(documented_code)


@click.command()
@click.option(
    "-f",
    "--file-path",
    "file_path",
    required=True,
    help="The file that contains that the code you want to document",
)
@click.option(
    "-o",
    "--output-path",
    "output_path",
    required=False,
    default=DEFAULT_OUTPUT_PATH,
    help="The destination folder where you want to save the document file",
)
@click.option(
    "-n",
    "--model-name",
    "model_name",
    required=False,
    default=DEFAULT_MODEL_NAME,
    help="The OpenAI model name you want to use. \
    https://platform.openai.com/docs/models",
)
def main(file_path: str, output_path: str, model_name: str):
    if not os.environ.get("OPENAI_API_KEY"):
        os.environ["OPENAI_API_KEY"] = getpass.getpass(
            prompt="Enter your OpenAI API key: "
        )

    document_file(file_path, output_path, model_name)


if __name__ == "__main__":
    main()
