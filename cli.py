import getpass
import json
import logging
import os

import click

from devtale.utils import (
    fuse_tales,
    get_tale_index,
    get_tale_summary,
    get_unit_tale,
    split,
)

DEFAULT_OUTPUT_PATH = "devtale_demo/"
DEFAULT_MODEL_NAME = "gpt-3.5-turbo"
ALLOWED_EXTENSIONS = [".php"]

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


def document_folder(
    folder_path: str,
    output_path: str = DEFAULT_OUTPUT_PATH,
    model_name: str = DEFAULT_MODEL_NAME,
) -> None:
    if not os.path.exists(output_path):
        os.makedirs(output_path)

    tales = []

    logger.info(f"looking for dev files in folder {folder_path}")
    for filename in os.listdir(folder_path):
        file_path = os.path.join(folder_path, filename)

        if (
            os.path.isfile(file_path)
            and os.path.splitext(filename)[1] in ALLOWED_EXTENSIONS
        ):
            logger.info(f"processing {file_path}")
            file_tale = document_file(file_path)

            tales.append(
                {"file_name": filename, "file_summary": file_tale["file_docstring"]}
            )

    tales_index = get_tale_index(tales)

    save_path = os.path.join(output_path, folder_path)
    if not os.path.exists(save_path):
        os.makedirs(save_path)

    logger.info(f"saving index in {save_path}")
    with open(os.path.join(save_path, "README.md"), "w", encoding="utf-8") as file:
        file.write(tales_index)


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
    logger.info(f"save dev tale in: {save_path}")
    with open(save_path, "w") as json_file:
        json.dump(final_tale, json_file, indent=2)

    # logger.info("AI-Generate Dev Tale:")
    # pprint(final_tale)

    return final_tale

    # logger.info("add documentation to the code")
    # documented_code = add_tales(file_tales, code)

    # save_path = os.path.join(output_path, file_name)
    # logger.info(f"save documented file in {save_path}")
    # with open(save_path, "w") as file:
    #    file.write(documented_code)


@click.command()
@click.option(
    "-f",
    "--folder-path",
    "folder_path",
    required=True,
    help="The path to the folder that contains the code files",
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
def main(folder_path: str, output_path: str, model_name: str):
    if not os.environ.get("OPENAI_API_KEY"):
        os.environ["OPENAI_API_KEY"] = getpass.getpass(
            prompt="Enter your OpenAI API key: "
        )

    # document_file(file_path, output_path, model_name)
    document_folder(folder_path, output_path, model_name)


if __name__ == "__main__":
    main()
